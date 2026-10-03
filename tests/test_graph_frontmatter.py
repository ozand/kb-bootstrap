"""Keep YAML frontmatter separate from Markdown fence recognition."""

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.canonical_graph_export import build_canonical_graph
from kb_bootstrap.graph_linter import analyze_graph, validate


class GraphFrontmatterRegressionTests(unittest.TestCase):
    def write_concept(self, root, name, body=""):
        path = root / name
        path.write_text("---\ntype: Concept\n---\n" + body, encoding="utf-8")
        return path

    def test_yaml_fence_scalars_do_not_hide_body_links(self):
        cases = (
            ("[Missing](missing.md)\n", False),
            ("[Real](target.md)\n", True),
            ("```md\n[Hidden](example.md)\n```\n[Missing](missing.md)\n", False),
            ("```md\n[Hidden](example.md)\n```\n[Real](target.md)\n", True),
        )
        for marker in ("```", "~~~"):
            for scalar_prefix in ("", "  ---\n"):
                for newline in ("\n", "\r\n"):
                    for body, expected_valid in cases:
                        with self.subTest(marker=marker, scalar_prefix=scalar_prefix,
                                          newline=newline, body=body):
                            with tempfile.TemporaryDirectory() as directory:
                                root = Path(directory)
                                source = root / "source.md"
                                header = "---\ntype: Concept\nnotes: |-\n" + scalar_prefix
                                header += "  " + marker + "\n---\n"
                                source.write_bytes((header + body).replace("\n", newline).encode())
                                self.write_concept(root, "target.md")
                                before = {p.name: p.read_bytes() for p in root.iterdir()}
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
                                self.assertEqual(before, {
                                    p.name: p.read_bytes() for p in root.iterdir()
                                })
                                self.assertEqual(lint_valid, expected_valid)
                                self.assertEqual(export_valid, expected_valid)
                                self.assertEqual(graph.graph["invalid_targets"],
                                                 set() if expected_valid else {"missing.md"})
                                self.assertEqual(set(graph.edges()),
                                                 {("source.md", "target.md")} if expected_valid else set())
                                if expected_valid:
                                    self.assertEqual(json.loads(data)["edges"], [
                                        {"source": "source.md", "target": "target.md", "fragment": None}
                                    ])
                                else:
                                    self.assertEqual(data, b"")

    def test_frontmatter_link_checks_are_preserved(self):
        # Only fence interpretation changes, not the linter's pre-existing
        # scan of link syntax in metadata. Export still scans Markdown body only.
        for destination in ("target.md", "missing.md"):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source.md"
                source.write_text(
                    "---\ntype: Concept\nnotes: |-\n  ```\n"
                    "  [Metadata](%s)\n---\n# Body\n" % destination,
                    encoding="utf-8",
                )
                self.write_concept(root, "target.md")
                before = source.read_bytes()
                graph, _ = analyze_graph(root)
                _, lint_valid = validate(root)
                data, _, export_valid = build_canonical_graph(root)
                self.assertEqual(lint_valid, destination == "target.md")
                self.assertEqual(graph.graph["invalid_targets"],
                                 set() if lint_valid else {"missing.md"})
                self.assertEqual(set(graph.edges()),
                                 {("source.md", "target.md")} if lint_valid else set())
                self.assertTrue(export_valid)
                self.assertEqual(json.loads(data)["edges"], [])
                self.assertEqual(source.read_bytes(), before)

    def test_non_frontmatter_delimiters_do_not_disable_body_fences(self):
        # Only an initial pair of exact '---' lines delimits frontmatter.
        documents = (
            "# Heading\n---\n```md\n[Hidden](example.md)\n```\n---\n",
            "--- \n```md\n[Hidden](example.md)\n```\n---\n",
            "\n---\n```md\n[Hidden](example.md)\n```\n---\n",
            "---\n```md\n[Hidden](example.md)\n```\n",
        )
        for document in documents:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "source.md").write_text(document + "[Missing](missing.md)\n",
                                                encoding="utf-8")
                graph, _ = analyze_graph(root)
                self.assertEqual(graph.graph["invalid_targets"], {"missing.md"})
                self.assertFalse(validate(root)[1])

    def test_body_separator_does_not_reset_an_open_fence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_concept(root, "source.md",
                               "```md\n---\n[Hidden](example.md)\n```\n[Missing](missing.md)\n")
            graph, _ = analyze_graph(root)
            self.assertEqual(graph.graph["invalid_targets"], {"missing.md"})
            self.assertFalse(validate(root)[1])


if __name__ == "__main__":
    unittest.main()
