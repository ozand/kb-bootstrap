import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.canonical_graph_export import build_canonical_graph
from kb_bootstrap.graph_linter import analyze_graph, validate


class GraphLinterTests(unittest.TestCase):
    def write(self, root, relative, content):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "index.md", "[Guide](guide.md)\n")
            self.write(root, "guide.md", "# Guide\n")
            report, is_valid = validate(root)
            self.assertTrue(is_valid)
            self.assertIn("DEAD LINKS: 0", report)

    def test_root_relative_link_matches_graph_export_from_nested_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "target.md", "---\ntype: Concept\n---\n# Target\n")
            self.write(root, "nested/source.md", "---\ntype: Concept\n---\n[Root](/target.md#part)\n")
            graph, _ = analyze_graph(root)
            report, is_valid = validate(root)
            data, _, export_valid = build_canonical_graph(root)
            self.assertTrue(is_valid and export_valid)
            self.assertIn(("nested/source.md", "target.md"), graph.edges())
            self.assertIn("DEAD LINKS: 0", report)
            self.assertIn('"target": "target.md"', data.decode("utf-8"))

    def test_root_relative_missing_reserved_excluded_and_unsafe_targets_fail(self):
        cases = (
            ("/missing.md", "missing.md"),
            ("/index.md", "index.md"),
            ("/raw/hidden.md", "raw/hidden.md"),
            ("/../outside.md", "[unsafe link target]"),
            ("%2e%2e/outside.md", "[unsafe link target]"),
            ("C:/outside.md", "[unsafe link target]"),
            ("\\\\server\\share\\outside.md", "[unsafe link target]"),
        )
        for link, marker in cases:
            with self.subTest(link=link), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write(root, "source.md", "[Target](%s)\n" % link)
                self.write(root, "index.md", "# Reserved\n")
                self.write(root, "raw/hidden.md", "# Hidden\n")
                report, is_valid = validate(root)
                self.assertFalse(is_valid)
                self.assertIn(marker, report)
                self.assertIn("Nodes (MD Files): 2", report)
                self.assertNotIn(str(root), report)

    def test_symlinked_canonical_root_fails_closed_when_available(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory) / "linked-root"
            target = Path(outside)
            self.write(target, "concept.md", "# Concept\n")
            try:
                root.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            report, is_valid = validate(root)
            self.assertFalse(is_valid)
            self.assertIn("[unsafe canonical root]", report)
            self.assertNotIn(str(target), report)

    def test_raw_and_lesson_directories_are_excluded_case_insensitively(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "index.md", "[Guide](guide.md)\n")
            self.write(root, "guide.md", "# Guide\n")
            for relative in ("raw/source.md", "Raw/source.md", "lessons/item.md", "Lessons/item.md"):
                self.write(root, relative, "[Missing](missing.md)\n")
            report, is_valid = validate(root)
            self.assertTrue(is_valid)
            self.assertIn("Nodes (MD Files): 2", report)
            self.assertIn("DEAD LINKS: 0", report)

    def test_orphans_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "index.md", "# Index\n")
            self.write(root, "orphan.md", "# Orphan\n")
            report, is_valid = validate(root)
            self.assertTrue(is_valid)
            self.assertIn("ORPHANS (0 Incoming Links): 2", report)
            self.assertIn("orphan.md", report)


if __name__ == "__main__":
    unittest.main()
