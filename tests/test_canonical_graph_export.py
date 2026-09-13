import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kb_bootstrap.canonical_graph_export as MODULE
from kb_bootstrap.canonical_graph_export import (
    build_canonical_graph,
    write_canonical_graph,
)


def concept(root: Path, relative: str, frontmatter: str, body: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return path


class CanonicalGraphExportTests(unittest.TestCase):
    def test_schema_order_metadata_edges_fragments_and_deduplication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(
                root,
                "zeta.md",
                "type: Custom\nowner_team: platform",
                "[Alpha](alpha.md)\n[Section](alpha.md#part)\n[Again](alpha.md#part)\n",
            )
            concept(root, "alpha.md", "type: Concept\ntitle: Alpha")

            data, report, valid = build_canonical_graph(root)
            artifact = json.loads(data)

            self.assertTrue(valid)
            self.assertEqual(list(artifact), ["schema", "version", "profile", "nodes", "edges"])
            self.assertEqual([node["path"] for node in artifact["nodes"]], ["alpha.md", "zeta.md"])
            self.assertEqual(list(artifact["nodes"][0]), ["path", "frontmatter"])
            self.assertIn("owner_team: platform", artifact["nodes"][1]["frontmatter"])
            self.assertEqual(
                artifact["edges"],
                [
                    {"source": "zeta.md", "target": "alpha.md", "fragment": None},
                    {"source": "zeta.md", "target": "alpha.md", "fragment": "part"},
                ],
            )
            self.assertEqual(list(artifact["edges"][0]), ["source", "target", "fragment"])
            self.assertIn("nodes: 2", report)
            self.assertIn("edges: 2", report)

    def test_fragments_remain_exact_and_unsupported_parentheses_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(root, "target.md", "type: Concept")
            concept(root, "foo(bar).md", "type: Concept")
            concept(
                root,
                "source.md",
                "type: Concept",
                "[Encoded](target.md#frag%2Fpart)\n"
                "[Unicode](target.md#раздел)\n"
                "[Empty](target.md#)\n"
                "[Unsupported](foo(bar).md)\n"
                "[Angle](<foo(bar).md>)\n",
            )

            data, _, valid = build_canonical_graph(root)
            edges = json.loads(data)["edges"]

            self.assertTrue(valid)
            self.assertIn(
                {"source": "source.md", "target": "target.md", "fragment": "frag%2Fpart"},
                edges,
            )
            self.assertIn(
                {"source": "source.md", "target": "target.md", "fragment": "раздел"},
                edges,
            )
            self.assertIn(
                {"source": "source.md", "target": "target.md", "fragment": None},
                edges,
            )
            self.assertEqual(
                [edge for edge in edges if edge["target"] == "foo(bar).md"],
                [{"source": "source.md", "target": "foo(bar).md", "fragment": None}],
            )

    def test_repeated_export_is_byte_identical_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = concept(root, "overview.md", "type: Architecture\ncustom: value")
            original = source.read_bytes()

            first, _, first_valid = build_canonical_graph(root)
            second, _, second_valid = build_canonical_graph(root)

            self.assertTrue(first_valid and second_valid)
            self.assertEqual(first, second)
            self.assertEqual(hashlib.sha256(first).digest(), hashlib.sha256(second).digest())
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(first.endswith(b"\n"))

    def test_reserved_raw_lessons_and_external_links_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(
                root,
                "overview.md",
                "type: Concept",
                "[Web](https://example.com/x.md) [Mail](mailto:a@example.com) "
                "[Anchor](#part) [Text](notes.txt)\n",
            )
            (root / "index.md").write_text("# Index\n", encoding="utf-8")
            (root / "RAW/source.md").parent.mkdir()
            (root / "RAW/source.md").write_text("# Raw\n", encoding="utf-8")
            (root / "Lessons/item.md").parent.mkdir()
            (root / "Lessons/item.md").write_text("# Lesson\n", encoding="utf-8")

            data, _, valid = build_canonical_graph(root)
            artifact = json.loads(data)

            self.assertTrue(valid)
            self.assertEqual([node["path"] for node in artifact["nodes"]], ["overview.md"])
            self.assertEqual(artifact["edges"], [])
            self.assertNotIn("https://", data.decode())

    def test_dead_escape_encoded_query_and_symlink_links_block(self):
        fixtures = (
            "[Missing](missing.md)",
            "[Escape](../outside.md)",
            "[Encoded](%2e%2e/outside.md)",
            "[Query](other.md?view=1)",
        )
        for body in fixtures:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                concept(root, "source.md", "type: Concept", body)
                concept(root, "other.md", "type: Concept")

                data, report, valid = build_canonical_graph(root)

                self.assertFalse(valid)
                self.assertEqual(data, b"")
                self.assertIn("RESULT: BLOCKED", report)
                self.assertNotIn(str(root), report)

        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(directory)
            outside = Path(outside_directory) / "outside.md"
            outside.write_text("---\ntype: External\n---\n", encoding="utf-8")
            link = root / "linked.md"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            concept(root, "source.md", "type: Concept", "[Linked](linked.md)")

            data, report, valid = build_canonical_graph(root)

            self.assertFalse(valid)
            self.assertEqual(data, b"")
            self.assertIn("symlink", report)
            self.assertNotIn(str(outside), report)

    def test_profile_is_rechecked_on_exported_observed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = concept(root, "source.md", "type: Concept")
            real_read = MODULE._read_document

            def mutate_before_export(path):
                path.write_text("---\ntitle: Missing type\n---\n", encoding="utf-8")
                return real_read(path)

            with patch.object(MODULE, "_read_document", side_effect=mutate_before_export):
                data, report, valid = build_canonical_graph(root)

            self.assertFalse(valid)
            self.assertEqual(data, b"")
            self.assertIn("type must be a non-empty string", report)

    def test_malformed_profile_blocks_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            kb = project / "kb"
            kb.mkdir()
            (kb / "bad.md").write_text("---\ntitle: Missing type\n---\n", encoding="utf-8")

            report, valid = write_canonical_graph(project, "kb", "graph.json")

            self.assertFalse(valid)
            self.assertIn("canonical profile validation failed", report)
            self.assertFalse((project / "graph.json").exists())

    def test_output_is_contained_outside_source_and_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="private-export-") as directory:
            project = Path(directory)
            kb = project / "kb"
            concept(kb, "overview.md", "type: Concept")

            cases = (
                ("../graph.json", "output path must be relative"),
                ("kb/graph.json", "outside the canonical root"),
                ("missing/graph.json", "output parent"),
            )
            for output, message in cases:
                with self.subTest(output=output):
                    report, valid = write_canonical_graph(project, "kb", output)
                    self.assertFalse(valid)
                    self.assertIn(message, report)
                    self.assertNotIn(str(project), report)

            existing = project / "graph.json"
            existing.write_text("foreign", encoding="utf-8")
            report, valid = write_canonical_graph(project, "kb", "graph.json")
            self.assertFalse(valid)
            self.assertIn("output already exists", report)
            self.assertEqual(existing.read_text(encoding="utf-8"), "foreign")

    def test_successful_file_export_matches_in_memory_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            kb = project / "kb"
            concept(kb, "overview.md", "type: Concept\ncustom: retained")
            expected, _, expected_valid = build_canonical_graph(kb)

            report, valid = write_canonical_graph(project, "kb", "graph.json")

            self.assertTrue(expected_valid and valid)
            self.assertIn("output: created", report)
            self.assertEqual((project / "graph.json").read_bytes(), expected)

    def test_post_link_temp_cleanup_failure_reports_published_output(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            kb = project / "kb"
            concept(kb, "overview.md", "type: Concept")
            real_unlink = Path.unlink
            failures = {"count": 0}

            def fail_first_temp_unlink(path, *args, **kwargs):
                if path.name.startswith(".kb-bootstrap-graph-") and failures["count"] == 0:
                    failures["count"] += 1
                    raise OSError("injected")
                return real_unlink(path, *args, **kwargs)

            with patch.object(Path, "unlink", new=fail_first_temp_unlink):
                report, valid = write_canonical_graph(project, "kb", "graph.json")

            self.assertTrue(valid)
            self.assertIn("output: created", report)
            self.assertIn("temporary cleanup is incomplete", report)
            self.assertTrue((project / "graph.json").exists())
            self.assertEqual(len(list(project.glob(".kb-bootstrap-graph-*.tmp"))), 1)

    def test_malformed_local_links_block_while_code_images_and_unsupported_forms_are_ignored(self):
        malformed = (
            "[Missing](missing.md",
            "[Angle](<missing.md",
            "[Angle close](<target.md>",
            "[Angle title](<target.md> \"unterminated title",
            "[Title](target.md \"unterminated title",
        )
        for body in malformed:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                concept(root, "source.md", "type: Concept", body)
                concept(root, "target.md", "type: Concept")
                data, report, valid = build_canonical_graph(root)
                self.assertFalse(valid)
                self.assertEqual(data, b"")
                self.assertIn("malformed local Markdown link", report)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(root, "target.md", "type: Concept")
            concept(
                root,
                "source.md",
                "type: Concept",
                "`[Inline](missing.md)`\n"
                "![Image](missing.md)\n"
                "```markdown\n[Fenced](missing.md)\n```\n"
                "[Unsupported](foo(bar).md)\n"
                "[Real](target.md)\n",
            )
            data, _, valid = build_canonical_graph(root)
            self.assertTrue(valid)
            self.assertEqual(
                json.loads(data)["edges"],
                [{"source": "source.md", "target": "target.md", "fragment": None}],
            )

    def test_encoded_path_controls_block_and_root_relative_link_exports(self):
        for destination in ("target%00.md", "target%0A.md", "target%7F.md"):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                concept(root, "source.md", "type: Concept", f"[Unsafe]({destination})")
                data, report, valid = build_canonical_graph(root)
                self.assertFalse(valid)
                self.assertEqual(data, b"")
                self.assertIn("encoded traversal or separator", report)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(root, "target.md", "type: Concept")
            concept(root, "nested/source.md", "type: Concept", "[Root](/target.md)")
            data, _, valid = build_canonical_graph(root)
            self.assertTrue(valid)
            self.assertEqual(
                json.loads(data)["edges"],
                [{"source": "nested/source.md", "target": "target.md", "fragment": None}],
            )

    def test_publication_failures_cleanup_and_preserve_race_created_output(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            kb = project / "kb"
            concept(kb, "overview.md", "type: Concept")
            with patch.object(MODULE.os, "link", side_effect=OSError("unsupported")):
                report, valid = write_canonical_graph(project, "kb", "graph.json")
            self.assertFalse(valid)
            self.assertIn("cannot be published exclusively", report)
            self.assertFalse((project / "graph.json").exists())
            self.assertEqual(list(project.glob(".kb-bootstrap-graph-*.tmp")), [])

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            kb = project / "kb"
            concept(kb, "overview.md", "type: Concept")
            real_link = os.link

            def race_link(source, destination):
                Path(destination).write_text("foreign", encoding="utf-8")
                return real_link(source, destination)

            with patch.object(MODULE.os, "link", side_effect=race_link):
                report, valid = write_canonical_graph(project, "kb", "graph.json")
            self.assertFalse(valid)
            self.assertEqual((project / "graph.json").read_text(encoding="utf-8"), "foreign")
            self.assertEqual(list(project.glob(".kb-bootstrap-graph-*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
