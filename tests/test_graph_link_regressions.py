"""W11-A: ignore external/code examples without weakening local link checks."""

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.canonical_graph_export import build_canonical_graph
from kb_bootstrap.graph_linter import analyze_graph, validate


class GraphLinkRegressionTests(unittest.TestCase):
    def write_concept(self, root, name, body=""):
        path = root / name
        path.write_text("---\ntype: Concept\n---\n" + body, encoding="utf-8")
        return path

    def test_four_case_matrix_matches_export_without_io_side_effects(self):
        cases = (
            ("[Remote](https://example.invalid/reference.md)\n", True, False),
            ("```markdown\n[Example](missing.md)\n```\n", True, False),
            ("[Missing](missing.md)\n", False, False),
            ("[Target](target.md)\n", True, True),
        )
        for body, expected_valid, has_edge in cases:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write_concept(root, "source.md", body)
                self.write_concept(root, "target.md")
                before = {path.name: path.read_bytes() for path in root.iterdir()}
                with ExitStack() as stack:
                    for target in (
                        "socket.socket", "socket.create_connection",
                        "socket.getaddrinfo", "urllib.request.urlopen",
                        "subprocess.Popen",
                    ):
                        stack.enter_context(patch(
                            target, side_effect=AssertionError("unexpected external IO")
                        ))
                    graph, _ = analyze_graph(root)
                    _, lint_valid = validate(root)
                    data, _, export_valid = build_canonical_graph(root)
                self.assertEqual(lint_valid, expected_valid)
                self.assertEqual(export_valid, expected_valid)
                self.assertEqual(
                    set(graph.edges()),
                    {("source.md", "target.md")} if has_edge else set(),
                )
                self.assertEqual(
                    graph.graph["invalid_targets"],
                    set() if expected_valid else {"missing.md"},
                )
                if expected_valid:
                    self.assertEqual(json.loads(data)["edges"], [
                        {"source": "source.md", "target": "target.md", "fragment": None}
                    ] if has_edge else [])
                else:
                    self.assertEqual(data, b"")
                self.assertEqual(before, {
                    path.name: path.read_bytes() for path in root.iterdir()
                })

    def test_fence_closers_match_character_length_and_whitespace(self):
        examples = (
            "~~~md\n[Hidden](missing.md)\n~~~\n",
            "````md\n```\n[Hidden](missing.md)\n````\n",
            "~~~md\n```\n[Hidden](missing.md)\n~~~\n",
            "```md\n~~~\n[Hidden](missing.md)\n```\n",
            "```md\n```not-a-closer\n[Hidden](missing.md)\n```\n",
            "   ```md\n[Hidden](missing.md)\n  ````\t\n",
            "```md\n[One](one.md)\n```\n~~~md\n[Two](two.md)\n~~~\n",
        )
        for example in examples:
            with self.subTest(example=example), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write_concept(root, "source.md", example + "[Real](target.md)\n")
                self.write_concept(root, "target.md")
                graph, _ = analyze_graph(root)
                self.assertEqual(graph.graph["invalid_targets"], set())
                self.assertEqual(set(graph.edges()), {("source.md", "target.md")})

    def test_unclosed_fence_does_not_expose_code_as_links(self):
        for marker in ("```", "~~~"):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write_concept(root, "source.md", marker + "md\n[Hidden](missing.md)\n")
                graph, _ = analyze_graph(root)
                self.assertEqual(graph.graph["invalid_targets"], set())
                self.assertEqual(list(graph.edges()), [])

    def test_missing_body_link_after_fence_still_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_concept(
                root, "source.md",
                "```md\n[Hidden](example.md)\n```\n[Missing](missing.md)\n",
            )
            graph, _ = analyze_graph(root)
            self.assertEqual(graph.graph["invalid_targets"], {"missing.md"})
            self.assertFalse(validate(root)[1])

    def test_external_schemes_bypass_local_target_resolution(self):
        destinations = (
            "https://example.invalid/reference.md",
            "HTTPS://example.invalid/reference.md",
            "mailto:user@example.invalid.md",
            "urn:example:reference.md",
            "https://[malformed/reference.md",
        )
        for destination in destinations:
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write_concept(root, "source.md", "[Remote](%s)\n" % destination)
                with patch("kb_bootstrap.graph_linter._target_path",
                           side_effect=AssertionError("external URI resolved as local")):
                    graph, _ = analyze_graph(root)
                self.assertEqual(graph.graph["invalid_targets"], set())
                self.assertEqual(list(graph.edges()), [])

    def test_drive_unc_and_unsafe_local_targets_still_fail(self):
        destinations = (
            "C:/outside.md", "C:\\outside.md", "//server/share/outside.md",
            "../outside.md", "%2e%2e/outside.md", "target%00.md",
        )
        for destination in destinations:
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write_concept(root, "source.md", "[Unsafe](%s)\n" % destination)
                graph, _ = analyze_graph(root)
                self.assertEqual(graph.graph["invalid_targets"], {"[unsafe link target]"})
                self.assertEqual(list(graph.edges()), [])


if __name__ == "__main__":
    unittest.main()
