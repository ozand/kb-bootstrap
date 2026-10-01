"""Exercise bounded list-container handling for shared Markdown fences."""

import json
import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.canonical_graph_export import build_canonical_graph
from kb_bootstrap.graph_linter import analyze_graph, validate


class GraphContainerFenceTests(unittest.TestCase):
    def assert_graph(self, body, valid, edges=(), frontmatter="type: Concept"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.md"
            source.write_text(
                "---\n" + frontmatter + "\n---\n" + body, encoding="utf-8"
            )
            (root / "target.md").write_text(
                "---\ntype: Concept\n---\n", encoding="utf-8"
            )
            before = {path.name: path.read_bytes() for path in root.iterdir()}

            graph, _ = analyze_graph(root)
            _, lint_valid = validate(root)
            data, _, export_valid = build_canonical_graph(root)

            self.assertEqual(lint_valid, valid)
            self.assertEqual(export_valid, valid)
            self.assertEqual(set(graph.edges()), set(edges))
            if valid:
                exported = {
                    (edge["source"], edge["target"])
                    for edge in json.loads(data)["edges"]
                }
                self.assertEqual(exported, set(edges))
            else:
                self.assertEqual(data, b"")
            self.assertEqual(
                before, {path.name: path.read_bytes() for path in root.iterdir()}
            )

    def test_wide_ordered_marker_makes_five_space_fence_relative(self):
        self.assert_graph(
            "100. Example:\n\n     ````md\n"
            "     [Hidden](missing.md)\n     ````\n",
            True,
        )

    def test_outdent_ends_unclosed_list_fence_and_exposes_missing_link(self):
        self.assert_graph(
            "100. Example:\n\n     ```md\n"
            "     [Hidden](missing.md)\n\n[Outside](outside-missing.md)\n",
            False,
        )

    def test_outdent_ends_unclosed_list_fence_and_keeps_valid_link(self):
        self.assert_graph(
            "100. Example:\n\n     ```md\n"
            "     [Hidden](missing.md)\n\n[Outside](target.md)\n",
            True,
            {("source.md", "target.md")},
        )

    def test_unclosed_top_level_fence_keeps_ordinary_eof_behavior(self):
        self.assert_graph(
            "```md\n[Hidden](missing.md)\n\n[Still hidden](missing.md)\n",
            True,
        )

    def test_blank_lines_do_not_end_list_fence_before_explicit_close(self):
        self.assert_graph(
            "100. Example:\n\n     ~~~~md\n\n"
            "     [Hidden](missing.md)\n\n     ~~~~\n"
            "\n[Outside](missing.md)\n",
            False,
        )

    def test_sibling_list_item_ends_unclosed_fence(self):
        self.assert_graph(
            "100. Example:\n\n     ````md\n"
            "     ```\n     [Hidden](missing.md)\n"
            "101. [Outside](missing.md)\n",
            False,
        )

    def test_frontmatter_fence_text_does_not_change_container_state(self):
        self.assert_graph(
            "100. Example:\n\n     ```md\n"
            "     [Hidden](missing.md)\n\n[Outside](missing.md)\n",
            False,
            frontmatter="type: Concept\nnotes: |-\n  ```",
        )

    def test_container_fence_closing_rules_and_list_exit(self):
        bodies = (
            "9. Example:\n\n   ~~~~md\n   ```\n"
            "   [Hidden](missing.md)\n   ~~~~\n\n[Missing](missing.md)\n",
            "123456789) Example:\n           ```md\n"
            "           [Hidden](missing.md)\n           ```\n"
            "[Missing](missing.md)\n",
            "* Example:\n  ````md\n  ```\n"
            "  [Hidden](missing.md)\n  ````\n[Missing](missing.md)\n",
        )
        for body in bodies:
            with self.subTest(body=body):
                self.assert_graph(body, False)
                # A valid outside link must remain visible while Hidden stays
                # suppressed; invalid-only assertions could conceal that bug.
                valid_body = body.replace("[Missing](missing.md)", "[Target](target.md)")
                self.assert_graph(valid_body, True, {("source.md", "target.md")})

    def test_nested_wide_list_fence_keeps_visible_sibling(self):
        self.assert_graph(
            "- Outer\n\n  100. Example\n\n       ````md\n"
            "       ```\n       [Hidden](missing.md)\n       ````\n"
            "  [Sibling](target.md)\n",
            True, {("source.md", "target.md")},
        )

    def test_nested_unclosed_fence_exits_at_sibling_and_top_level(self):
        prefix = "- Outer\n  - Inner\n\n    ```md\n    [Hidden](missing.md)\n\n"
        for outside in ("  - [Outside]", "  [Outside]", "[Outside]"):
            with self.subTest(outside=outside):
                self.assert_graph(prefix + outside + "(target.md)\n", True,
                                  {("source.md", "target.md")})
                self.assert_graph(prefix + outside + "(outside-missing.md)\n", False)

    def test_non_one_ordered_marker_cannot_interrupt_paragraph(self):
        for marker in ("2.", "100)"):
            prefix = "Paragraph\n" + marker + " ~~~\n"
            indent = " " * (len(marker) + 1)
            self.assert_graph(prefix + indent + "[Missing](missing.md)\n", False)
            self.assert_graph(prefix + indent + "[Target](target.md)\n", True,
                              {("source.md", "target.md")})

    def test_ordered_fence_starts_after_blank_or_marker_one(self):
        for prefix in ("Paragraph\n\n2. ~~~\n", "Paragraph\n1. ~~~\n"):
            self.assert_graph(prefix + "   [Hidden](missing.md)\n   ~~~\n\n"
                              + "[Target](target.md)\n", True,
                              {("source.md", "target.md")})

    def test_list_body_links_remain_visible(self):
        self.assert_graph("100. [Missing](missing.md)\n", False)
        self.assert_graph(
            "100. [Target](target.md)\n",
            True,
            {("source.md", "target.md")},
        )

    def test_standalone_five_space_fence_is_not_reclassified(self):
        self.assert_graph(
            "     ```md\n     [Missing](missing.md)\n     ```\n",
            False,
        )


if __name__ == "__main__":
    unittest.main()
