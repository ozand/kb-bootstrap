import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.canonical_provenance import (
    _safe_actor,
    _safe_resource,
    parse_timestamp,
    validate_canonical_provenance,
)


def concept(root: Path, relative: str, frontmatter: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n# Example\n", encoding="utf-8")
    return path


class CanonicalProvenanceTests(unittest.TestCase):
    def test_all_optional_fields_absent_is_valid_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = concept(root, "concept.md", "type: Concept\ncustom: retained")
            original = source.read_bytes()

            first, first_valid = validate_canonical_provenance(root)
            second, second_valid = validate_canonical_provenance(root)

            self.assertTrue(first_valid and second_valid)
            self.assertEqual(first, second)
            self.assertIn("Generated: present=0 absent=1 invalid=0", first)
            self.assertIn("Verified: present=0 absent=1 invalid=0", first)
            self.assertIn("Sources: present=0 absent=1 invalid=0", first)
            self.assertIn("Freshness: fresh=0 stale=0 unknown=1 invalid=0", first)
            self.assertEqual(source.read_bytes(), original)

    def test_valid_families_unknown_keys_and_empty_lists_pass_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = concept(
                root,
                "concept.md",
                "type: Concept\n"
                "generated:\n  by: agent/1\n  at: 2026-09-14T10:00:00Z\n  extra: kept\n"
                "verified:\n  - by: human:reviewer\n    at: 2026-09-14T11:00:00+00:00\n"
                "sources:\n  - resource: https://example.com/public\n    title: Public source\n"
                "stale_after: 2026-09-15T00:00:00Z\n"
                "unknown_family:\n  nested: value",
            )
            original = source.read_bytes()

            report, valid = validate_canonical_provenance(
                root, "2026-09-14T12:00:00Z"
            )

            self.assertTrue(valid)
            self.assertIn("Generated: present=1 absent=0 invalid=0", report)
            self.assertIn("Verified: present=1 absent=0 invalid=0", report)
            self.assertIn("Sources: present=1 absent=0 invalid=0", report)
            self.assertIn("Freshness: fresh=1 stale=0 unknown=0 invalid=0", report)
            self.assertNotIn("agent/1", report)
            self.assertNotIn("example.com", report)
            self.assertEqual(source.read_bytes(), original)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(root, "empty.md", "type: Concept\nverified: []\nsources: []")
            report, valid = validate_canonical_provenance(root)
            self.assertTrue(valid)
            self.assertIn("Verified: present=1", report)
            self.assertIn("Sources: present=1", report)
            self.assertIn("unknown=1", report)

    def test_verified_mapping_is_one_valid_event(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(
                root,
                "concept.md",
                "type: Concept\nverified:\n  by: human:reviewer\n  at: 2026-09-14T11:00:00Z",
            )

            report, valid = validate_canonical_provenance(root)

            self.assertTrue(valid)
            self.assertIn("Verified: present=1 absent=0 invalid=0", report)

    def test_fresh_stale_boundary_and_absent_now_are_deterministic(self):
        cases = (
            (None, "unknown=1"),
            ("2026-09-14T11:59:59Z", "fresh=1"),
            ("2026-09-14T12:00:00Z", "stale=1"),
            ("2026-09-14T12:00:01+00:00", "stale=1"),
        )
        for now, expected in cases:
            with self.subTest(now=now), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                concept(root, "concept.md", "type: Concept\nstale_after: 2026-09-14T12:00:00Z")

                report, valid = validate_canonical_provenance(root, now)

                self.assertTrue(valid)
                self.assertIn(expected, report)

    def test_arbitrary_fractional_precision_preserves_freshness_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(
                root,
                "concept.md",
                "type: Concept\nstale_after: 2026-09-14T12:00:00.1234568Z",
            )

            report, valid = validate_canonical_provenance(
                root, "2026-09-14T12:00:00.1234567Z"
            )

            self.assertTrue(valid)
            self.assertIn("fresh=1", report)

    def test_strict_timestamp_matrix(self):
        valid = (
            "2026-09-14T12:00:00Z",
            "2026-09-14T12:00:00.123+03:00",
            "2026-09-14T12:00:00-05:30",
        )
        invalid = (
            "2026-09-14T12:00:00." + "1" * 110 + "Z",
            "0001-01-01T00:00:00+14:00",
            "9999-12-31T23:59:59-14:00",
            "2026-09-14",
            "2026-09-14T12:00Z",
            "2026-09-14T12:00:00",
            "2026-09-14T12:00:00z",
            "2026-02-30T12:00:00Z",
            "2026-09-14T12:00:00+00:60",
            "2026-09-14T12:00:00+01:99",
            "2026-09-14T12:00:00+14:01",
            "2026-09-14T12:00:00+23:00",
            "2026-09-14T12:00:00+24:00",
            " 2026-09-14T12:00:00Z",
        )
        for value in valid:
            with self.subTest(value=value):
                self.assertIsNotNone(parse_timestamp(value))
        for value in invalid:
            with self.subTest(value=value):
                self.assertIsNone(parse_timestamp(value))

    def test_invalid_now_blocks_before_traversal(self):
        with patch("kb_bootstrap.canonical_provenance._concept_files") as traversal:
            report, valid = validate_canonical_provenance("missing", "2026-09-14")

        self.assertFalse(valid)
        self.assertIn("--now must be an offset-aware timestamp", report)
        traversal.assert_not_called()

    def test_invalid_status_is_rejected_by_provenance_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(root, "invalid.md", "type: Concept\nstatus: active")

            report, valid = validate_canonical_provenance(root)

            self.assertFalse(valid)
            self.assertIn("status must be draft, stable, or deprecated", report)

    def test_duplicate_provenance_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(
                root,
                "invalid.md",
                "type: Concept\ngenerated:\n  by: agent/1\n  by: agent/2",
            )

            report, valid = validate_canonical_provenance(root)

            self.assertFalse(valid)
            self.assertIn("frontmatter is invalid YAML", report)
            self.assertIn("provenance fields are unavailable", report)
            self.assertNotIn("agent/1", report)
            self.assertNotIn("agent/2", report)

    def test_malformed_frontmatter_does_not_claim_absent_families_are_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "invalid.md").write_text("---\ntype: [\n---\n", encoding="utf-8")

            report, valid = validate_canonical_provenance(root)

            self.assertFalse(valid)
            self.assertIn("Generated: present=0 absent=0 invalid=0", report)
            self.assertIn("Verified: present=0 absent=0 invalid=0", report)
            self.assertIn("Sources: present=0 absent=0 invalid=0", report)
            self.assertIn("Freshness: fresh=0 stale=0 unknown=0 invalid=1", report)

    def test_malformed_null_and_missing_required_family_values_fail(self):
        fixtures = (
            ("generated: null", "generated must be a mapping"),
            ("generated: {}", "generated.by is missing or unsafe"),
            ("generated:\n  by: true", "generated.by is missing or unsafe"),
            ("generated:\n  by: 42", "generated.by is missing or unsafe"),
            ("generated:\n  by: agent/1\n  at: 2026-09-14", "generated.at"),
            ("verified: null", "verified must be a mapping or list"),
            ("verified: [{}]", "verified event 1.by"),
            ("verified:\n  by: human:reviewer", "verified event 1.at"),
            ("sources: null", "sources must be a list"),
            ("sources: [{}]", "source 1.resource"),
            ("sources: [{resource: public, last_modified: 2026-09-14}]", "source 1.last_modified"),
            ("usage_window: {from: 2026-09-14T12:00:00Z}", "usage_window.to"),
            ("stale_after: null", "stale_after"),
            ("stale_after: 2026-09-14", "stale_after"),
        )
        for fragment, expected in fixtures:
            with self.subTest(fragment=fragment), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = concept(root, "invalid.md", f"type: Concept\n{fragment}")
                original = source.read_bytes()

                first, first_valid = validate_canonical_provenance(root, "2026-09-14T12:00:00Z")
                second, second_valid = validate_canonical_provenance(root, "2026-09-14T12:00:00Z")

                self.assertFalse(first_valid or second_valid)
                self.assertEqual(first, second)
                self.assertIn(expected, first)
                self.assertEqual(source.read_bytes(), original)

    def test_actor_and_resource_safety_blocks_without_echoing_values(self):
        fixtures = (
            ("generated:\n  by: https://example.com/actor", "generated.by"),
            ("generated:\n  by: http:actor", "generated.by"),
            ("generated:\n  by: https:/actor", "generated.by"),
            ("generated:\n  by: mailto:actor@example.com", "generated.by"),
            ("generated:\n  by: urn:actor", "generated.by"),
            ("generated:\n  by: ssh:actor", "generated.by"),
            ("generated:\n  by: tel:123", "generated.by"),
            ("generated:\n  by: C:/private/actor", "generated.by"),
            ("generated:\n  by: 'token=private'", "generated.by"),
            ("sources:\n  - resource: file:///private/path", "source 1.resource"),
            ("sources:\n  - resource: https://user:pass@example.com/doc", "source 1.resource"),
            ("sources:\n  - resource: C:/private/source", "source 1.resource"),
            ("sources:\n  - resource: ../private.md", "source 1.resource"),
            ("sources:\n  - resource: docs/../private.md", "source 1.resource"),
            ("sources:\n  - resource: docs/%00private.md", "source 1.resource"),
            ("sources:\n  - resource: docs/%2e%2e/private.md", "source 1.resource"),
            ("sources:\n  - resource: https://example.com/docs/%2e%2e/private.md", "source 1.resource"),
            ("sources:\n  - resource: https://example.com/docs%2fprivate.md", "source 1.resource"),
            ("sources:\n  - resource: https://example.com/docs/%252e%252e/private.md", "source 1.resource"),
            ("sources:\n  - resource: https://example.com/%00private.md", "source 1.resource"),
            ("sources:\n  - resource: https://example.com/%2500private.md", "source 1.resource"),
            ("sources:\n  - resource: https://exa%6dple.com/private.md", "source 1.resource"),
            ("sources:\n  - resource: https://example.com:bad/private.md", "source 1.resource"),
            ("sources:\n  - resource: 'https://@example.com/doc'", "source 1.resource"),
            ("sources:\n  - resource: 'http://[bad'", "source 1.resource"),
            ("sources:\n  - resource: 'http://exa：mple.com/private.md'", "source 1.resource"),
            ("sources:\n  - resource: docs//private.md", "source 1.resource"),
            ("sources:\n  - resource: '../docs/private.md'", "source 1.resource"),
            ("sources:\n  - resource: 'docs/private file.md'", "source 1.resource"),
            ("sources:\n  - resource: docs\\private.md", "source 1.resource"),
        )
        for fragment, expected in fixtures:
            with self.subTest(fragment=fragment), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                concept(root, "invalid.md", f"type: Concept\n{fragment}")

                report, valid = validate_canonical_provenance(root)

                self.assertFalse(valid)
                self.assertIn(expected, report)
                self.assertNotIn("example.com", report)
                self.assertNotIn("C:/", report)
                self.assertNotIn("private", report)

    def test_adr047_resource_classes_and_blocked_references(self):
        accepted = (
            "https://example.com/public",
            "docs/source_v1.md",
            "./docs/source_v1.md",
            "/bundle/docs/source_v1.md",
            "docs/%41-source.md",
            "scope:managed collection / research",
            "scope:" + "é" * 256,
        )
        rejected = (
            "",
            "/",
            "//server/share",
            "/docs//source.md",
            "docs//source.md",
            "./../source.md",
            "docs/%2e%2e/source.md",
            "docs/%2Fsource.md",
            "docs/%5csource.md",
            "docs/%FF.md",
            "docs/%GG.md",
            "docs/%2500.md",
            "docs/%00.md",
            "docs/a?b",
            "docs/a#b",
            "C:/private.md",
            "ftp://example.com/source",
            "scope:",
            "scope: padded ",
            "scope:bad\nvalue",
            "scope:" + "a" * 257,
        )
        for resource in accepted:
            with self.subTest(resource=resource):
                self.assertTrue(_safe_resource(resource))
        for resource in rejected:
            with self.subTest(resource=resource):
                self.assertFalse(_safe_resource(resource))

    def test_actor_compatibility_and_canonical_convention(self):
        accepted = (
            "agent", "producer/1.0", "human:reviewer_1", "process:batch+2",
            "Ada Lovelace", "legacy actor label", "human:",
        )
        rejected = (
            "", "http:actor", "https://example.com/actor", "C:/actor", "token=secret",
        )
        for actor in accepted:
            with self.subTest(actor=actor):
                self.assertTrue(_safe_actor(actor))
        for actor in rejected:
            with self.subTest(actor=actor):
                self.assertFalse(_safe_actor(actor))

    def test_actor_rule_is_shared_by_generated_verified_and_source_author(self):
        actors = ("Ada Lovelace", "agent/2", "human:reviewer", "process:sync")
        for actor in actors:
            with self.subTest(actor=actor), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                concept(
                    root,
                    "concept.md",
                    "type: Concept\n"
                    f"generated: {{by: '{actor}'}}\n"
                    f"verified: [{{by: '{actor}', at: 2026-09-14T00:00:00Z}}]\n"
                    f"sources: [{{resource: source, author: '{actor}'}}]",
                )
                report, valid = validate_canonical_provenance(root)
                self.assertTrue(valid)
                self.assertNotIn(actor, report)

    def test_shared_source_windows_and_authors_validate_without_affecting_freshness(self):
        metadata = (
            "type: Concept\n"
            "generated:\n  by: legacy producer\n"
            "usage_window:\n  from: 2026-09-14T12:00:00+02:00\n"
            "  to: 2026-09-14T10:00:00Z\n  extension: kept\n"
            "sources:\n  - resource: /bundle/source.md\n"
            "    author: human:reviewer\n"
            "    last_modified: 2026-09-14T14:00:00+04:00\n"
            "    usage_window:\n      from: 2026-09-14T10:00:00-05:00\n"
            "      to: 2026-09-14T15:00:00Z\n"
            "      usage_count: 0\n"
            "stale_after: 2026-09-14T12:00:00Z\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = concept(root, "concept.md", metadata)
            original = source.read_bytes()
            first, valid = validate_canonical_provenance(root, "2026-09-14T11:59:59Z")
            second, second_valid = validate_canonical_provenance(root, "2026-09-14T11:59:59Z")
            self.assertTrue(valid and second_valid)
            self.assertEqual(first, second)
            self.assertIn("fresh=1", first)
            self.assertNotIn("source.md", first)
            self.assertEqual(source.read_bytes(), original)

    def test_last_modified_and_usage_window_invalid_cases_are_sanitized(self):
        fixtures = (
            ("usage_window: null", "usage_window must be a mapping"),
            ("usage_window: {from: 2026-09-14T12:00:00Z}", "usage_window.to"),
            ("usage_window: {from: null, to: 2026-09-14T12:00:00Z}", "usage_window.from"),
            ("usage_window: {from: 2026-09-14T12:00:00, to: 2026-09-14T12:00:00Z}", "usage_window.from"),
            ("usage_window: {from: 2026-09-14T12:00:01Z, to: 2026-09-14T12:00:00Z}", "usage_window bounds are reversed"),
            ("sources: [{resource: public, usage_window: {from: 2026-09-14T12:00:00Z}}]", "source 1.usage_window.to"),
            ("sources: [{resource: public, last_modified: 2026-09-14}]", "source 1.last_modified"),
            ("sources: [{resource: public, author: https://example.com/private}]", "source 1.author"),
        )
        for fragment, expected in fixtures:
            with self.subTest(fragment=fragment), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                concept(root, "concept.md", f"type: Concept\n{fragment}")
                report, valid = validate_canonical_provenance(root, "2026-09-14T12:00:00Z")
                self.assertFalse(valid)
                self.assertIn(expected, report)
                self.assertNotIn("example.com", report)
                self.assertNotIn("private", report)

    def test_resource_metadata_is_never_opened_or_networked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            concept(root, "concept.md", "type: Concept\nsources: [{resource: /bundle/not-real, author: Ada Lovelace}]")
            original_open = Path.open
            opened_paths = []

            def recording_open(path, *args, **kwargs):
                opened_paths.append(path)
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", recording_open), patch(
                "urllib.request.urlopen", side_effect=AssertionError("network used")
            ):
                report, valid = validate_canonical_provenance(root)
            self.assertTrue(valid)
            self.assertIn("Sources: present=1", report)
            self.assertEqual(opened_paths, [root / "concept.md"])

    def test_safe_relative_resource_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            concept(
                root,
                "concept.md",
                "type: Concept\nsources:\n  - resource: docs/public-source_v1.md",
            )

            report, valid = validate_canonical_provenance(root)

            self.assertTrue(valid)
            self.assertIn("Sources: present=1 absent=0 invalid=0", report)

    def test_report_diagnostics_do_not_echo_actor_resource_or_timestamp_canaries(self):
        canaries = ("ACTOR_CANARY_7x", "RESOURCE_CANARY_8y", "TIME_CANARY_9z")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(
                root,
                "concept.md",
                "type: Concept\n"
                f"generated: {{by: '{canaries[0]}'}}\n"
                f"sources: [{{resource: '{canaries[1]}', last_modified: '{canaries[2]}'}}]",
            )
            report, valid = validate_canonical_provenance(root)
            self.assertFalse(valid)
            for canary in canaries:
                self.assertNotIn(canary, report)

    def test_validation_does_not_use_wall_clock_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept(
                root,
                "concept.md",
                "type: Concept\nsources:\n  - resource: https://example.com/public\n"
                "stale_after: 2026-09-14T12:00:00Z",
            )
            report, valid = validate_canonical_provenance(root)

            self.assertTrue(valid)
            self.assertIn("unknown=1", report)
            self.assertNotIn("now()", Path("kb_bootstrap/canonical_provenance.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
