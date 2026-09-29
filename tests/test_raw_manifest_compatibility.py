import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.raw_manifest import _signature


class RawManifestCompatibilityTests(unittest.TestCase):
    @staticmethod
    def expected_signature(path):
        details = os.stat(path, follow_symlinks=False)
        return details.st_dev, details.st_ino, details.st_size, details.st_mtime_ns

    def test_regular_file_signature_preserves_all_identity_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.write_bytes(b"content")

            signature = _signature(source)

            self.assertEqual(signature, self.expected_signature(source))
            self.assertEqual(len(signature), 4)

    def test_symlink_signature_does_not_follow_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            link = Path(directory) / "link"
            target.write_bytes(b"target content")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")

            self.assertEqual(_signature(link), self.expected_signature(link))
            self.assertNotEqual(_signature(link), self.expected_signature(target))

    def test_signature_avoids_unsupported_path_stat_keyword(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.write_bytes(b"content")
            original_stat = Path.stat

            def old_path_stat(path):
                return original_stat(path)

            with patch.object(Path, "stat", old_path_stat):
                signature = _signature(source)

            self.assertEqual(signature, self.expected_signature(source))


if __name__ == "__main__":
    unittest.main()
