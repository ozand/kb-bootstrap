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
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.WaitForSingleObject.restype = ctypes.c_uint32
        kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        kernel32.GetExitCodeProcess.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
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
        root = Path(tempfile.mkdtemp(prefix="kb-descendant-evidence-"))
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

        handle = None
        wait_result = None
        exit_query_ok = False
        exit_code = ctypes.c_uint32(0xFFFFFFFF)
        if observed and observed[0]:
            kernel32, handle = observed[0]
        try:
            self.assertEqual(reason, "timeout")
            self.assertTrue(pid_file.is_file(), "launch acknowledgement was not recorded")
            self.assertLess(elapsed, 2.5, "reader join exceeded its bounded allowance")
            self.assertIsNotNone(handle, "child process handle was not acquired")
            wait_result = kernel32.WaitForSingleObject(handle, 5000)
            self.assertEqual(wait_result, 0)
            exit_query_ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            self.assertTrue(exit_query_ok)
            self.assertEqual(exit_code.value, 0)
            self.assertTrue(marker.is_file(), "marker is separate corroborating evidence")
            self.assertEqual(marker.read_text(encoding="ascii"), "done")
        finally:
            if handle is not None:
                kernel32.CloseHandle(handle)
        # Explicit cleanup happens only after confirmed wait + exit status.
        self._remove_confirmed_fixture(root, wait_result, exit_query_ok, exit_code.value)

    @staticmethod
    def _remove_confirmed_fixture(path, wait_result, exit_query_ok, exit_code):
        import shutil

        if wait_result != 0 or not exit_query_ok or exit_code != 0:
            return False
        shutil.rmtree(path)
        return True

    def test_unconfirmed_exit_evidence_preserves_owned_fixture(self):
        """Wait or exit-query failure/nonzero code must not trigger fixture cleanup."""
        cases = (
            ("wait-failure", 258, True, 0),
            ("exit-query-failure", 0, False, 0),
            ("nonzero-exit", 0, True, 7),
        )
        for label, wait_result, exit_query_ok, exit_code in cases:
            with self.subTest(evidence=label):
                owned = Path(tempfile.mkdtemp(prefix=f"kb-descendant-{label}-"))
                removed = self._remove_confirmed_fixture(
                    owned, wait_result, exit_query_ok, exit_code
                )
                self.assertFalse(removed)
                self.assertTrue(owned.is_dir(), f"{label} must preserve the owned fixture")

    def test_marker_without_process_handle_keeps_exit_unknown_and_fixture(self):
        """A delayed marker is not promoted to process-exit evidence."""
        owned = Path(tempfile.mkdtemp(prefix="kb-descendant-unknown-"))
        marker = owned / "finished"
        release = owned / "release-child"
        child_code = "\n".join((
            "import pathlib,time",
            "pathlib.Path('finished').write_text('done',encoding='ascii')",
            "release=pathlib.Path('release-child')",
            "deadline=time.monotonic()+10",
            "while not release.exists() and time.monotonic()<deadline:",
            "    time.sleep(.01)",
        ))
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
            # Release only this owned synthetic child, then confirm its exact
            # process handle is signaled before TemporaryDirectory cleanup.
            release.write_text("release", encoding="ascii")
            self.assertEqual(kernel32.WaitForSingleObject(handle, 5000), 0)
        finally:
            kernel32.CloseHandle(handle)
