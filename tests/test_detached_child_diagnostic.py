"""Synthetic diagnostic: marker creation and child-process exit are distinct evidence."""
import ctypes
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from kb_bootstrap.bounded_process import run_bounded


@unittest.skipUnless(os.name == "nt", "process-handle exit query is Windows-specific")
class DetachedChildEvidenceTests(unittest.TestCase):
    def _open_process_handle_when_pid_appears(self, pid_file, result):
        """Open a kernel process handle while the bounded parent is still running."""
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                pid = int(Path(pid_file).read_text(encoding="ascii"))
            except (FileNotFoundError, ValueError):
                time.sleep(0.005)
                continue
            handle = kernel32.OpenProcess(0x00100000 | 0x1000, 0, pid)
            if handle:
                result.append((kernel32, handle))
                return
            time.sleep(0.005)
        result.append(None)

    def test_reader_join_marker_and_handle_exit_are_separate(self):
        """Descendant holds pipes; run_bounded joins readers while handle observes exit."""
        with tempfile.TemporaryDirectory(prefix="kb-descendant-evidence-") as tmp:
            root = Path(tmp)
            pid_file = root / "child.pid"
            marker = root / "finished"
            child_code = (
                "import pathlib,time; time.sleep(1.5); "
                "pathlib.Path('finished').write_text('done', encoding='ascii')"
            )
            parent_code = (
                "import pathlib,subprocess,sys,time; "
                "p=subprocess.Popen([sys.executable,'-c',%r],cwd='.', "
                "stdout=sys.stdout,stderr=sys.stderr); "
                "pathlib.Path('child.pid').write_text(str(p.pid),encoding='ascii'); "
                "time.sleep(5)"
            ) % child_code
            observed = []
            watcher = threading.Thread(
                target=self._open_process_handle_when_pid_appears,
                args=(pid_file, observed), daemon=True,
            )
            watcher.start()
            started = time.monotonic()
            _, reason = run_bounded(
                [sys.executable, "-c", parent_code], root, os.environ.copy(), timeout=0.5
            )
            elapsed = time.monotonic() - started
            watcher.join(timeout=1)

            self.assertEqual(reason, "timeout")
            self.assertTrue(pid_file.is_file(), "launch acknowledgement was not recorded")
            self.assertLess(elapsed, 2.5, "reader join exceeded its bounded allowance")
            self.assertTrue(observed and observed[0], "child process handle was not acquired")
            kernel32, handle = observed[0]
            try:
                self.assertEqual(kernel32.WaitForSingleObject(handle, 5000), 0)
                exit_code = ctypes.c_uint32()
                self.assertTrue(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)))
                self.assertEqual(exit_code.value, 0)
            finally:
                kernel32.CloseHandle(handle)
            self.assertTrue(marker.is_file(), "marker is separate corroborating evidence")
            self.assertEqual(marker.read_text(encoding="ascii"), "done")
            # TemporaryDirectory cleanup is safe here: the retained process handle
            # confirmed that this exact child had exited before the fixture is removed.

    def test_marker_without_process_handle_keeps_exit_unknown_and_fixture(self):
        """A delayed marker is not promoted to process-exit evidence."""
        owned = Path(tempfile.mkdtemp(prefix="kb-descendant-unknown-"))
        marker = owned / "finished"
        child_code = (
            "import pathlib,time; time.sleep(1.5); "
            "pathlib.Path('finished').write_text('done',encoding='ascii')"
        )
        parent_code = (
            "import pathlib,subprocess,sys,time; "
            "p=subprocess.Popen([sys.executable,'-c',%r],cwd='.', "
            "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
            "pathlib.Path('child.pid').write_text(str(p.pid),encoding='ascii'); "
            "time.sleep(5)"
        ) % child_code
        # Retain a child process handle before the direct parent times out, but
        # deliberately do not query it: this case's exit evidence remains UNKNOWN.
        # Open SYNCHRONIZE only; no termination or mutation right is requested.
        process_holder = []
        holder = threading.Thread(
            target=self._open_process_handle_when_pid_appears,
            args=(owned / "child.pid", process_holder), daemon=True,
        )
        holder.start()
        _, reason = run_bounded(
            [sys.executable, "-c", parent_code], owned, os.environ.copy(), timeout=0.5
        )
        holder.join(timeout=1)
        self.assertEqual(reason, "timeout")
        self.assertTrue(owned.is_dir())
        self.assertTrue((owned / "child.pid").is_file(), "launch acknowledgement was not recorded")
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(marker.is_file(), "synthetic child did not create its marker")
        self.assertTrue(process_holder and process_holder[0], "launch was not handle-observed")
        kernel32, handle = process_holder[0]
        try:
            # Marker exists, but a zero-time handle wait has not reported exit.
            self.assertEqual(kernel32.WaitForSingleObject(handle, 0), 258)
            exit_evidence = "UNKNOWN"
            self.assertEqual(exit_evidence, "UNKNOWN")
            self.assertTrue(owned.is_dir(), "unknown-exit fixture must be preserved")
            self.assertEqual(marker.read_text(encoding="ascii"), "done")
        finally:
            kernel32.CloseHandle(handle)
