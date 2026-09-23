"""ADR-011 canonical byte framing; no model, network or package is needed."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.gliner_checkpoint import verify_checkpoint


def expected(items):
    digest = hashlib.sha256()
    for name, data in sorted(items.items()):
        path = name.encode("utf-8")
        digest.update(len(path).to_bytes(8, "big") + path)
        digest.update(len(data).to_bytes(8, "big") + data)
    return digest.hexdigest()


class CheckpointTests(unittest.TestCase):
    def test_exact_framed_bytes_and_sanitized_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            items = {"nested/tokenizer.json": b"{}", "config.json": b"", "weights.bin": b"\x00\xff"}
            for name, data in items.items():
                (root / name).write_bytes(data)
            report, ok = verify_checkpoint(root, reversed(list(items)), expected(items))
            self.assertTrue(ok, report)
            self.assertIn("model sha256: " + expected(items), report)
            self.assertIn("publisher authenticity: not verified", report)
            self.assertIn("acquisition plan and owner consent: not verified", report)
            self.assertNotIn(directory, report)
            self.assertEqual({name: (root / name).read_bytes() for name in items}, items)

    def test_mismatch_missing_extra_and_invalid_names_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_bytes(b"{}")
            digest = expected({"config.json": b"{}"})
            for names, check in [(["config.json"], "0" * 64), (["missing"], digest),
                                 (["../escape"], digest), (["config.json", "CONFIG.json"], digest)]:
                report, ok = verify_checkpoint(root, names, check)
                self.assertFalse(ok, report)
                self.assertIn("RESULT: BLOCKED", report)
                self.assertNotIn(directory, report)
            (root / "extra.txt").write_bytes(b"foreign")
            report, ok = verify_checkpoint(root, ["config.json"], digest)
            self.assertFalse(ok, report)
            self.assertEqual((root / "extra.txt").read_bytes(), b"foreign")

    def test_symlink_and_nonregular_file_block(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / "config.json").write_bytes(b"{}")
            link = root / "weights.bin"
            try:
                link.symlink_to(Path(outside) / "foreign")
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            report, ok = verify_checkpoint(root, ["config.json", "weights.bin"], "0" * 64)
            self.assertFalse(ok, report)
            self.assertNotIn(outside, report)

    def test_cli_fixture_stdout_and_exit(self):
        import os
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            (model / "config.json").write_bytes(b"{}")
            command = [sys.executable, "-m", "kb_bootstrap.cli", "verify-gliner-checkpoint",
                       "--model-dir", directory, "--file", "config.json",
                       "--expected-model-digest", expected({"config.json": b"{}"})]
            passed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(passed.returncode, 0, passed.stderr + passed.stdout)
            self.assertIn("RESULT: OK (local byte comparison only)", passed.stdout)
            self.assertNotIn(directory, passed.stdout)
            (model / "config.json").write_bytes(b"changed")
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertIn("RESULT: BLOCKED", failed.stdout)
            self.assertEqual(failed.stderr, "")
