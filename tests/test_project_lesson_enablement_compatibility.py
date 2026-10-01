import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.project_lesson_enablement import _file_identity


class ProjectLessonEnablementCompatibilityTests(unittest.TestCase):
    def test_file_identity_avoids_newer_path_stat_keyword(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact"
            path.write_bytes(b"identity")

            with patch.object(
                Path,
                "stat",
                side_effect=TypeError(
                    "stat() got an unexpected keyword argument 'follow_symlinks'"
                ),
            ):
                identity = _file_identity(path)

            stat = os.stat(path, follow_symlinks=False)
            self.assertEqual(identity, (stat.st_dev, stat.st_ino))

    def test_file_identity_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_bytes(b"identity")
            link = root / "link"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")

            link_stat = os.stat(link, follow_symlinks=False)
            target_stat = os.stat(target, follow_symlinks=False)
            self.assertEqual(
                _file_identity(link), (link_stat.st_dev, link_stat.st_ino)
            )
            self.assertNotEqual(_file_identity(link), _file_identity(target))


if __name__ == "__main__":
    unittest.main()
