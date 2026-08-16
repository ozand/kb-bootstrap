import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.graph_linter import validate


class GraphLinterTests(unittest.TestCase):
    def test_valid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text("[Guide](guide.md)\n", encoding="utf-8")
            (root / "guide.md").write_text("# Guide\n", encoding="utf-8")
            report, is_valid = validate(root)
            self.assertTrue(is_valid)
            self.assertIn("DEAD LINKS: 0", report)

    def test_broken_links_fail_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text("[Missing](missing.md)\n", encoding="utf-8")
            report, is_valid = validate(root)
            self.assertFalse(is_valid)
            self.assertIn("missing.md", report)

    def test_orphans_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text("# Index\n", encoding="utf-8")
            (root / "orphan.md").write_text("# Orphan\n", encoding="utf-8")
            report, is_valid = validate(root)
            self.assertTrue(is_valid)
            self.assertIn("ORPHANS (0 Incoming Links): 2", report)
            self.assertIn("orphan.md", report)


if __name__ == "__main__":
    unittest.main()
