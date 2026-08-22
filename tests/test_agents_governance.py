import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.agents_governance import (
    END_MARKER,
    START_MARKER,
    update_agents_file,
)


class AgentsGovernanceTests(unittest.TestCase):
    def test_creates_new_agents_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AGENTS.md"
            report, valid = update_agents_file(path, "example/project")
            content = path.read_text(encoding="utf-8")

        self.assertTrue(valid)
        self.assertIn("updated", report)
        self.assertEqual(content.count(START_MARKER), 1)
        self.assertEqual(content.count(END_MARKER), 1)
        self.assertIn("Expected repository: `example/project`", content)

    def test_append_and_update_preserve_surrounding_bytes(self):
        prefix = "# Local instructions\n\nKeep this text.\n"
        suffix = "\n# Local footer\nDo not change.\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AGENTS.md"
            path.write_text(prefix, encoding="utf-8")
            _, valid = update_agents_file(path, "example/first")
            first = path.read_text(encoding="utf-8")
            path.write_text(first + suffix, encoding="utf-8")

            _, valid = update_agents_file(path, "example/second")
            updated = path.read_text(encoding="utf-8")

        self.assertTrue(valid)
        self.assertTrue(updated.startswith(prefix))
        self.assertTrue(updated.endswith(suffix))
        self.assertIn("example/second", updated)
        self.assertNotIn("example/first", updated)
        self.assertEqual(updated.count(START_MARKER), 1)

    def test_repeated_update_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AGENTS.md"
            update_agents_file(path, "example/project")
            first = path.read_bytes()
            report, valid = update_agents_file(path, "example/project")
            second = path.read_bytes()

        self.assertTrue(valid)
        self.assertIn("already current", report)
        self.assertEqual(first, second)

    def test_malformed_or_duplicate_markers_block_without_writing(self):
        cases = [
            f"before\n{START_MARKER}\nmissing end\n",
            f"{END_MARKER}\ntext\n{START_MARKER}\n",
            f"{START_MARKER}\na\n{END_MARKER}\n{START_MARKER}\nb\n{END_MARKER}\n",
        ]
        for content in cases:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "AGENTS.md"
                path.write_text(content, encoding="utf-8")
                before = path.read_bytes()
                report, valid = update_agents_file(path, "example/project")
                after = path.read_bytes()

                self.assertFalse(valid)
                self.assertIn("malformed or conflicting", report)
                self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
