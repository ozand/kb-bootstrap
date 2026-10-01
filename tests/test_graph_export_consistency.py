"""Keep graph lint and export aligned at their bounded link boundaries."""

import json
import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.canonical_graph_export import build_canonical_graph
from kb_bootstrap.graph_linter import analyze_graph, validate


class GraphExportConsistencyTests(unittest.TestCase):
    def write_concept(self, root, name, body=""):
        path = root / name
        path.write_text("---\ntype: Concept\n---\n" + body, encoding="utf-8")
        return path

    def assert_consistent(self, body, expected_valid, expected_edges=()):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_concept(root, "source.md", body)
            self.write_concept(root, "target.md")
            before = {path.name: path.read_bytes() for path in root.iterdir()}

            graph, _ = analyze_graph(root)
            _, lint_valid = validate(root)
            data, _, export_valid = build_canonical_graph(root)

            self.assertEqual(lint_valid, expected_valid)
            self.assertEqual(export_valid, expected_valid)
            self.assertEqual(set(graph.edges()), set(expected_edges))
            if expected_valid:
                exported = {
                    (edge["source"], edge["target"])
                    for edge in json.loads(data)["edges"]
                }
                self.assertEqual(exported, set(expected_edges))
            else:
                self.assertEqual(data, b"")
            self.assertEqual(before, {
                path.name: path.read_bytes() for path in root.iterdir()
            })
            self.assertEqual(source.read_bytes(), before["source.md"])

    def test_long_and_mixed_fence_markers_hide_example_links(self):
        examples = (
            "````md\n```\n[Hidden](missing.md)\n````\n",
            "~~~~md\n```\n[Hidden](missing.md)\n~~~~\n",
            "````md\n~~~\n[Hidden](missing.md)\n````\n",
            "```md\n~~~~\n[Hidden](missing.md)\n```\n",
        )
        for body in examples:
            with self.subTest(body=body):
                self.assert_consistent(body, True)

    def test_body_is_not_reinterpreted_as_frontmatter(self):
        body = "---\n````md\n```\n[Hidden](missing.md)\n````\n---\n[Missing](missing.md)\n"
        self.assert_consistent(body, False)

    def test_malformed_external_scheme_hosts_are_ignored(self):
        for destination in (
            "https://[malformed/reference.md",
            "HTTPS://]/reference.md",
            "custom://[malformed/reference.md",
        ):
            with self.subTest(destination=destination):
                self.assert_consistent("[Remote](%s)\n" % destination, True)

    def test_external_classification_does_not_weaken_unsafe_targets(self):
        for destination in (
            "C:/outside.md",
            "C:\\outside.md",
            "https:\\example.invalid/reference.md",
            "https://example.invalid/bad\\reference.md",
        ):
            with self.subTest(destination=destination):
                self.assert_consistent("[Unsafe](%s)\n" % destination, False)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_concept(
                root, "source.md", "[Unsafe](https://example.invalid/control\x01.md)\n"
            )
            data, report, valid = build_canonical_graph(root)
            self.assertFalse(valid)
            self.assertEqual(data, b"")
            self.assertIn("control character", report)

    def test_local_missing_and_valid_counterexamples(self):
        self.assert_consistent("[Missing](missing.md)\n", False)
        self.assert_consistent(
            "[Target](target.md)\n", True, {("source.md", "target.md")}
        )


if __name__ == "__main__":
    unittest.main()
