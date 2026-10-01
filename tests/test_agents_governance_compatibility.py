import os
import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.agents_governance import _identity, _observe, update_agents_file


class _OldPythonPath:
    """Path-like test double without Path.stat's newer keyword argument."""

    def __init__(self, path):
        self.path = Path(path)

    def __fspath__(self):
        return os.fspath(self.path)

    def absolute(self):
        return self.path.absolute()

    def is_file(self):
        return self.path.is_file()

    def is_symlink(self):
        return self.path.is_symlink()

    def read_bytes(self):
        return self.path.read_bytes()

    def stat(self, *args, **kwargs):
        if "follow_symlinks" in kwargs:
            raise TypeError("stat() got an unexpected keyword argument 'follow_symlinks'")
        return self.path.stat(*args, **kwargs)


class AgentsGovernanceCompatibilityTests(unittest.TestCase):
    def test_identity_and_observation_do_not_require_path_stat_keyword(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AGENTS.md"
            path.write_bytes(b"# human instructions\n")
            compatibility_path = _OldPythonPath(path)

            identity = _identity(compatibility_path)
            observation, error = _observe(compatibility_path)

        self.assertEqual(error, "")
        self.assertIsNotNone(observation)
        self.assertEqual(identity, observation.identity)
        self.assertEqual(observation.content, b"# human instructions\n")

    def test_update_preserves_identity_safety_and_unmanaged_bytes(self):
        prefix = b"# human instructions\r\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            path.write_bytes(prefix)

            report, valid = update_agents_file(
                "AGENTS.md", "example/project", project_root=root
            )
            updated = path.read_bytes()

        self.assertTrue(valid, report)
        self.assertTrue(updated.startswith(prefix))
        self.assertEqual(updated.count(b"kb-bootstrap:repository-governance:start"), 1)

    def test_symlink_target_remains_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside.md"
            target = root / "AGENTS.md"
            outside.write_bytes(b"outside\n")
            try:
                target.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")

            report, valid = update_agents_file(
                "AGENTS.md", "example/project", project_root=root
            )

            self.assertFalse(valid)
            self.assertIn("symlink", report)
            self.assertEqual(outside.read_bytes(), b"outside\n")


if __name__ == "__main__":
    unittest.main()
