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
            ("/raw/missing.md", "raw/missing.md"),
            ("/lessons/item.md", "lessons/item.md"),
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
                self.write(root, "lessons/item.md", "# Lesson\n")
                report, is_valid = validate(root)
                self.assertFalse(is_valid)
                self.assertIn(marker, report)
                self.assertIn("Nodes (MD Files): 2", report)
                self.assertNotIn(str(root), report)

    def test_existing_reserved_index_is_safe_reference_and_preserves_node(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "source.md", "[Index](nested/INDEX.md)\n")
            self.write(root, "nested/INDEX.md", "# Index\n")
            graph, _ = analyze_graph(root)
            report, is_valid = validate(root)
            self.assertTrue(is_valid, report)
            self.assertEqual(graph.number_of_nodes(), 2)
            self.assertIn(("source.md", "nested/INDEX.md"), graph.edges())
            self.assertIn("ORPHANS (0 Incoming Links): 1", report)

    def test_reserved_sources_still_fail_on_invalid_outgoing_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "index.md", "[Missing](missing.md)\n")
            self.write(root, "nested/log.md", "[Missing](missing-too.md)\n")
            graph, _ = analyze_graph(root)
            report, is_valid = validate(root)
            self.assertFalse(is_valid)
            self.assertEqual(graph.number_of_nodes(), 2)
            self.assertIn("missing.md", report)
            self.assertIn("nested/missing-too.md", report)

    def test_existing_lesson_schema_is_safe_reference_without_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "source.md", "[Schema](lessons/SCHEMA.md)\n")
            self.write(root, "lessons/SCHEMA.md", "[Missing](missing.md)\n")
            graph, _ = analyze_graph(root)
            report, is_valid = validate(root)
            self.assertTrue(is_valid, report)
            self.assertEqual(graph.number_of_nodes(), 1)
            self.assertEqual(graph.number_of_edges(), 0)
            self.assertNotIn("missing.md", report)

    def test_missing_excluded_reference_target_remains_dead(self):
        for target in ("nested/index.md", "lessons/SCHEMA.md"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write(root, "source.md", f"[Target]({target})\n")
                report, is_valid = validate(root)
                self.assertFalse(is_valid)
                self.assertIn(target, report)

    def test_unsafe_excluded_reference_symlink_remains_dead(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            self.write(Path(outside), "secret.md", "# Outside\n")
            (root / "lessons").mkdir()
            try:
                (root / "lessons" / "SCHEMA.md").symlink_to(Path(outside) / "secret.md")
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            self.write(root, "source.md", "[Schema](lessons/SCHEMA.md)\n")
            report, is_valid = validate(root)
            self.assertFalse(is_valid)
            self.assertIn("[unsafe link target]", report)

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

    def test_links_to_existing_raw_captures_are_evidence_not_dead(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "reports/study.md",
                       "[capture](../research/2026-01-01_x/raw/001-page.md) [top](../raw/src.md)\n")
            self.write(root, "research/2026-01-01_x/raw/001-page.md", "[Missing](missing.md)\n")
            self.write(root, "raw/src.md", "# Source\n")
            report, is_valid = validate(root)
            self.assertTrue(is_valid, report)
            self.assertIn("DEAD LINKS: 0", report)
            self.assertIn("EVIDENCE LINKS (to raw/ captures): 2", report)
            self.assertIn("Nodes (MD Files): 1", report)

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
