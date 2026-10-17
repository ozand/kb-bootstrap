import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.section_projection import (
    DEFAULT_SECTION_BYTES,
    MAX_FILE,
    MAX_HEADINGS,
    MAX_FRONTMATTER_BYTES,
    MAX_OUTPUT,
    MAX_TITLE_BYTES,
    project_section,
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SectionProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "kb"
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def project(self, data, path="guide.md", selector=("Guide",), **kwargs):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return project_section(self.root, path, digest(data), selector, **kwargs)

    def test_projects_section_with_descendants_and_exact_inclusive_lines(self):
        data = b"# Guide\nintro\n## Child\nbody\n# Next\nend\n"
        result = self.project(data)
        self.assertEqual(result, {
            "status": "COMPLETE", "path": "guide.md", "observed_sha256": digest(data),
            "heading_path": ["Guide"], "occurrence": 1, "start_line": 1,
            "end_line": 4, "text": "# Guide\nintro\n## Child\nbody\n", "truncated": False,
        })

    def test_exact_heading_normalization_examples(self):
        for source, title in (("#  Foo  ###", "Foo"), ("## Foo  bar", "Foo  bar"), ("   ### X", "X")):
            with self.subTest(source=source):
                result = self.project((source + "\nbody\n").encode(), selector=(title,))
                self.assertEqual(result["status"], "COMPLETE")
                self.assertEqual(result["heading_path"], [title])

    def test_nested_path_and_occurrence_selection(self):
        data = b"# A\n## Same\nfirst\n# B\n## Same\nsecond\n"
        result = self.project(data, selector=("B", "Same"))
        self.assertEqual(result["heading_path"], ["B", "Same"])
        self.assertEqual(result["text"], "## Same\nsecond\n")

    def test_duplicate_full_paths_are_ambiguous_and_occurrence_selects(self):
        data = b"# A\n## Same\none\n## Same\ntwo\n"
        target = self.root / "guide.md"
        target.write_bytes(data)
        ambiguous = project_section(self.root, "guide.md", digest(data), ("A", "Same"))
        second = project_section(self.root, "guide.md", digest(data), ("A", "Same"), occurrence=2)
        self.assertEqual(ambiguous, {"status": "AMBIGUOUS", "reason": "ambiguous"})
        self.assertEqual(second["text"], "## Same\ntwo\n")
        missing = project_section(self.root, "guide.md", digest(data), ("A", "Same"), occurrence=3)
        self.assertEqual(missing, {"status": "NOT_FOUND", "reason": "not_found"})

    def test_missing_heading_and_wrong_ancestry(self):
        data = b"# A\n## B\n"
        self.assertEqual(self.project(data, selector=("B",)), {"status": "NOT_FOUND", "reason": "not_found"})

    def test_frontmatter_and_fenced_code_headings_are_ignored(self):
        data = b"---\ntitle: fake\n---\n# Real\n```md\n# Fake\n```\nbody\n# Next\n"
        result = self.project(data, selector=("Real",))
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["text"], "# Real\n```md\n# Fake\n```\nbody\n")

    def test_tilde_fences_and_longer_closers(self):
        data = b"# Real\n~~~lang\n# Fake\n~~~~\nbody\n# Next\n"
        result = self.project(data, selector=("Real",))
        self.assertEqual(result["status"], "COMPLETE")
        self.assertIn("# Fake", result["text"])
        self.assertNotIn("# Next", result["text"])

    def test_unterminated_frontmatter_or_fence_is_unsupported(self):
        for data in (b"---\ntitle: x\n# heading\n", b"# A\n```\n# fake\n"):
            with self.subTest(data=data):
                result = self.project(data)
                self.assertEqual(result, {"status": "UNSUPPORTED", "reason": "unsupported"})

    def test_heading_grammar_rejects_ambiguous_tab_and_four_space_forms(self):
        for heading in ("\t# Heading", "#\tHeading", "    # Heading", "#    "):
            with self.subTest(heading=heading):
                data = (heading + "\nbody\n").encode()
                self.assertEqual(self.project(data), {"status": "UNSUPPORTED", "reason": "unsupported"})

    def test_setext_heading_is_unsupported(self):
        self.assertEqual(self.project(b"Title\n-----\nbody\n"), {"status": "UNSUPPORTED", "reason": "unsupported"})

    def test_crlf_section_bytes_and_line_numbers_are_preserved(self):
        data = b"# Guide\r\nbody\r\n# Next\r\n"
        result = self.project(data)
        self.assertEqual(result["text"], "# Guide\r\nbody\r\n")
        self.assertEqual((result["start_line"], result["end_line"]), (1, 2))

    def test_revision_mismatch_has_observed_hash_only_no_reason_or_text(self):
        data = b"# Guide\nsecret\n"
        self.project(data)
        result = project_section(self.root, "guide.md", "0" * 64, ("Guide",))
        self.assertEqual(result, {"status": "REVISION_MISMATCH", "observed_sha256": digest(data)})

    def test_invalid_utf8_blocks_even_when_expected_digest_is_stale(self):
        data = b"# Guide\n\xff"
        self.project(data)
        self.assertEqual(project_section(self.root, "guide.md", "0" * 64, ("Guide",)),
                         {"status": "BLOCKED", "reason": "blocked"})

    def test_invalid_utf8_blocks_before_parser_and_returns_closed_fields(self):
        data = b"# Guide\n\xff"
        self.assertEqual(self.project(data), {"status": "BLOCKED", "reason": "blocked"})

    def test_input_validation_is_blocked(self):
        data = b"# Guide\n"
        self.project(data)
        cases = [
            ("../guide.md", digest(data), ("Guide",), {}),
            ("guide.md", "A" * 64, ("Guide",), {}),
            ("guide.md", digest(data), (), {}),
            ("guide.md", digest(data), ("",), {}),
            ("guide.md", digest(data), ("Guide",), {"occurrence": 0}),
            ("guide.md", digest(data), ("Guide",), {"occurrence": True}),
            ("guide.md", digest(data), ("Guide",), {"max_section_bytes": False}),
            ("guide.md", digest(data), ("Guide",), {"max_section_bytes": 65537}),
        ]
        for path, sha, selector, kwargs in cases:
            with self.subTest(path=path, sha=sha, selector=selector, kwargs=kwargs):
                self.assertEqual(project_section(self.root, path, sha, selector, **kwargs),
                                 {"status": "BLOCKED", "reason": "blocked"})

    def test_path_policy_exclusions_and_hidden_paths_block(self):
        data = b"# Guide\n"
        for path in (".hidden.md", "raw/page.md", "research/page.md", "lessons/page.md", "index.md", "log.md"):
            with self.subTest(path=path):
                self.assertEqual(self.project(data, path), {"status": "BLOCKED", "reason": "blocked"})

    def test_symlink_target_blocks_without_reading_target(self):
        outside = Path(self.temp.name) / "outside.md"
        outside.write_bytes(b"# Guide\nsecret\n")
        link = self.root / "guide.md"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        result = project_section(self.root, "guide.md", digest(outside.read_bytes()), ("Guide",))
        self.assertEqual(result, {"status": "BLOCKED", "reason": "blocked"})

    def test_file_size_ceiling_blocks(self):
        data = b"# Guide\n" + b"x" * (MAX_FILE + 1)
        self.assertEqual(self.project(data), {"status": "BLOCKED", "reason": "blocked"})

    def test_frontmatter_line_and_byte_ceilings(self):
        too_many_lines = b"---\n" + b"x\n" * 256 + b"---\n# Guide\n"
        too_many_bytes = b"---\n" + b"x" * 8193 + b"\n---\n# Guide\n"
        for data in (too_many_lines, too_many_bytes):
            with self.subTest(length=len(data)):
                self.assertEqual(self.project(data), {"status": "UNSUPPORTED", "reason": "unsupported"})

    def test_frontmatter_byte_boundary_counts_original_lf_and_crlf_bytes(self):
        for newline in (b"\n", b"\r\n"):
            payload_size = MAX_FRONTMATTER_BYTES - 2 * len(b"---") - 3 * len(newline)
            valid = b"---" + newline + b"x" * payload_size + newline + b"---" + newline + b"# Guide" + newline
            over = b"---" + newline + b"x" * (payload_size + 1) + newline + b"---" + newline + b"# Guide" + newline
            with self.subTest(newline=newline):
                self.assertEqual(self.project(valid)["status"], "COMPLETE")
                self.assertEqual(self.project(over), {"status": "UNSUPPORTED", "reason": "unsupported"})

    def test_heading_count_depth_and_title_limits(self):
        cases = [
            (b"# A\n" * (MAX_HEADINGS + 1), ("A",)),
            (("# " + "x" * (MAX_TITLE_BYTES + 1) + "\n").encode(), ("Guide",)),
        ]
        for data, selector in cases:
            with self.subTest(length=len(data)):
                self.assertEqual(self.project(data, selector=selector),
                                 {"status": "UNSUPPORTED", "reason": "unsupported"})

    def test_heading_path_limit_blocks(self):
        selector = tuple(f"L{i}" for i in range(7))
        data = b"# A\n"
        self.assertEqual(self.project(data, selector=selector), {"status": "BLOCKED", "reason": "blocked"})

    def test_heading_path_component_utf8_byte_limit_blocks_before_file_access(self):
        data = b"# Guide\n"
        target = self.root / "guide.md"
        target.write_bytes(data)
        at_limit = "é" * (MAX_TITLE_BYTES // 2)
        result = project_section(self.root, "guide.md", digest(data), (at_limit,))
        with patch("builtins.open", side_effect=AssertionError("must reject selector before file access")):
            blocked = project_section(self.root, "guide.md", digest(data), (at_limit + "é",))
        self.assertEqual(result, {"status": "NOT_FOUND", "reason": "not_found"})
        self.assertEqual(blocked, {"status": "BLOCKED", "reason": "blocked"})

    def test_utf8_safe_byte_truncation_and_empty_prefix(self):
        data = "# Guide\nAé🙂Z\n".encode()
        target = self.root / "guide.md"
        target.write_bytes(data)
        result = project_section(self.root, "guide.md", digest(data), ("Guide",), max_section_bytes=12)
        self.assertEqual(result["status"], "TRUNCATED")
        self.assertLessEqual(len(result["text"].encode()), 12)
        self.assertTrue(result["text"].encode().decode())
        minimum = project_section(self.root, "guide.md", digest(data), ("Guide",), max_section_bytes=1)
        self.assertEqual(minimum["status"], "TRUNCATED")
        self.assertEqual(minimum["text"], "#")

    def test_default_and_max_section_budgets_are_bounded(self):
        self.assertEqual(DEFAULT_SECTION_BYTES, 16384)
        data = b"# Guide\n" + b"x" * 70000
        self.assertEqual(self.project(data, max_section_bytes=65536)["status"], "TRUNCATED")

    def test_truncation_happens_before_serialized_output_ceiling(self):
        data = b"# Guide\n" + b"\x00" * 50000
        target = self.root / "guide.md"
        target.write_bytes(data)
        result = project_section(self.root, "guide.md", digest(data), ("Guide",), max_section_bytes=1024)
        self.assertEqual(result["status"], "TRUNCATED")
        self.assertEqual(len(result["text"].encode()), 1024)
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode()) + 1, MAX_OUTPUT)

    def test_no_directory_enumeration_or_source_mutation(self):
        data = b"# Guide\nbody\n"
        original = self.root / "guide.md"
        original.write_bytes(data)
        before = original.read_bytes()
        with patch("pathlib.Path.iterdir", side_effect=AssertionError("enumeration forbidden")), \
             patch("pathlib.Path.glob", side_effect=AssertionError("enumeration forbidden")), \
             patch("pathlib.Path.rglob", side_effect=AssertionError("enumeration forbidden")):
            result = project_section(self.root, "guide.md", digest(data), ("Guide",))
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(original.read_bytes(), before)

    def test_serialized_success_mapping_respects_output_ceiling(self):
        data = b"# Guide\nbody\n"
        result = self.project(data)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode()) + 1,
                             MAX_OUTPUT)


if __name__ == "__main__":
    unittest.main()
