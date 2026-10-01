"""Compatibility coverage for no-follow checkpoint file verification."""

import hashlib
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kb_bootstrap.gliner_checkpoint import verify_checkpoint


class _LegacyPath(type(Path())):
    """Path with the Python 3.8/3.9 stat and lstat calling convention."""

    def stat(self):
        return os.stat(self)

    def lstat(self):
        return os.lstat(self)

    # Modern pathlib predicates pass a keyword to self.stat internally.
    # Emulate the old predicates as well, so the double only rejects the
    # production call this regression targets, not modern host internals.
    def is_dir(self):
        try:
            return stat.S_ISDIR(self.stat().st_mode)
        except OSError:
            return False

    def is_file(self):
        try:
            return stat.S_ISREG(self.stat().st_mode)
        except OSError:
            return False

    def is_symlink(self):
        try:
            return stat.S_ISLNK(self.lstat().st_mode)
        except OSError:
            return False


def _digest(items):
    digest = hashlib.sha256()
    for name, data in sorted(items.items()):
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


class CheckpointStatCompatibilityTests(unittest.TestCase):
    def test_legacy_path_stat_api_accepts_valid_bytes_without_changing_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = {"config.json": b"{\"tiny\":true}\n", "weights.bin": b"\x00\xffseed"}
            for name, data in items.items():
                (root / name).write_bytes(data)

            legacy_file = _LegacyPath(root / "config.json")
            with self.assertRaises(TypeError):
                legacy_file.stat(follow_symlinks=False)
            with mock.patch("kb_bootstrap.gliner_checkpoint.Path", _LegacyPath):
                report, ok = verify_checkpoint(root, items, _digest(items))

            self.assertTrue(ok, report)
            self.assertIn("RESULT: OK (local byte comparison only)", report)
            self.assertEqual({name: (root / name).read_bytes() for name in items}, items)

    def test_legacy_path_stat_api_rejects_mismatched_digest_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"invented checkpoint bytes\n"
            checkpoint = root / "weights.bin"
            checkpoint.write_bytes(payload)

            with mock.patch("kb_bootstrap.gliner_checkpoint.Path", _LegacyPath):
                report, ok = verify_checkpoint(root, ["weights.bin"], "0" * 64)

            self.assertFalse(ok, report)
            self.assertIn("model digest does not match expected bytes", report)
            self.assertEqual(checkpoint.read_bytes(), payload)

    def test_legacy_path_stat_api_does_not_follow_checkpoint_symlink(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            foreign = Path(outside) / "foreign.bin"
            payload = b"outside bytes stay untouched"
            foreign.write_bytes(payload)
            link = root / "weights.bin"
            try:
                link.symlink_to(foreign)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")

            original_link = os.readlink(link)
            with mock.patch("kb_bootstrap.gliner_checkpoint.Path", _LegacyPath):
                report, ok = verify_checkpoint(
                    root, ["weights.bin"], _digest({"weights.bin": payload})
                )

            self.assertFalse(ok, report)
            self.assertIn("RESULT: BLOCKED", report)
            self.assertEqual(os.readlink(link), original_link)
            self.assertEqual(foreign.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
