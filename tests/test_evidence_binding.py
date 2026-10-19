import hashlib
import json
import tempfile
import unittest
import stat
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap import evidence_binding

from kb_bootstrap.evidence_binding import PermissionError, resolve_evidence_binding, _fragment_valid


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binding_root = self.root / "knowledge"
        self.binding_root.mkdir()
        self.binding_path = self.binding_root / "binding.json"
        self.knowledge_path = self.binding_root / "topic.md"
        self.knowledge = b"# Topic\nBound statement.\n"
        self.knowledge_path.write_bytes(self.knowledge)
        self.base_project = self.root / "base-project"
        self.current_project = self.root / "current-project"
        self.base_corpus = "corpus"
        self.current_corpus = "corpus"
        (self.base_project / self.base_corpus).mkdir(parents=True)
        (self.current_project / self.current_corpus).mkdir(parents=True)
        self.base_bytes = b"Evidence baseline.\n"
        self.current_bytes = self.base_bytes
        (self.base_project / self.base_corpus / "evidence.md").write_bytes(self.base_bytes)
        (self.current_project / self.current_corpus / "evidence.md").write_bytes(self.current_bytes)
        self.base_meta = self.base_project / "capture.yaml"
        self.current_meta = self.current_project / "capture.yaml"
        self._write_envelope(self.base_meta, "source-base", "rep-base", self.base_bytes)
        self._write_envelope(self.current_meta, "source-current", "rep-current", self.current_bytes)
        self.binding = {
            "schema": "kb-bootstrap.evidence-bindings",
            "version": 1,
            "knowledge": {"path": "topic.md", "sha256": sha(self.knowledge)},
            "bindings": [{
                "binding_id": "binding-1",
                "evidence": [{
                    "source_id": "source-base",
                    "representation_id": "rep-base",
                    "observed_sha256": sha(self.base_bytes),
                    "current": {"source_id": "source-current", "representation_id": "rep-current"},
                }],
            }],
        }
        self._write_binding()

    def _write_envelope(self, path, source_id, representation_id, payload, retention="retained"):
        digest = sha(payload)
        if retention == "retained":
            original = f"original_revision: {{algorithm: sha256, digest: {digest}, media_type: text/plain}}\n  original_retention: retained\n"
            fidelity = "fidelity: {class: exact, coverage: all-bytes, losses: []}\n"
        else:
            original = "original_revision: {opaque: unknown}\n  original_retention: reference-only\n"
            fidelity = "fidelity: {class: partial, coverage: excerpt, losses: [unverified]}\n"
        text = (
            "schema: kb-bootstrap.source-capture\nversion: 1\nsources:\n"
            f"- source_id: {source_id}\n"
            f"  origin: {{kind: opaque-owner-reference, reference: {source_id}}}\n"
            f"  {original}"
            "  capture: {method: direct}\n"
            f"  {fidelity}"
            "  representations:\n"
            f"  - representation_id: {representation_id}\n"
            f"    revision: {{algorithm: sha256, digest: {digest}}}\n"
            f"    media_type: text/markdown\n    raw_path: evidence.md\n    retention: {retention}\n"
        )
        path.write_text(text, encoding="utf-8")

    def _add_reference_only_source(self, metadata_path, source_id, representation_id, path):
        text = metadata_path.read_text(encoding="utf-8")
        digest = sha(self.base_bytes)
        text += (
            f"- source_id: {source_id}\n"
            f"  origin: {{kind: opaque-owner-reference, reference: {source_id}}}\n"
            "  original_revision: {opaque: unknown}\n"
            "  original_retention: reference-only\n"
            "  capture: {method: direct}\n"
            "  fidelity: {class: partial, coverage: excerpt, losses: [unverified]}\n"
            "  representations:\n"
            f"  - representation_id: {representation_id}\n"
            f"    revision: {{algorithm: sha256, digest: {digest}}}\n"
            "    media_type: text/markdown\n"
            f"    raw_path: {path}\n"
            "    retention: reference-only\n"
        )
        metadata_path.write_text(text, encoding="utf-8")

    def _write_binding(self):
        self.binding_path.write_text(json.dumps(self.binding), encoding="utf-8")

    def resolve(self, **kwargs):
        args = dict(
            project_root=self.binding_root,
            binding_path="binding.json",
            knowledge_path="topic.md",
            baseline_metadata_path="capture.yaml",
            baseline_project_root=self.base_project,
            baseline_corpus_root=self.base_corpus,
            baseline_selected_paths=["evidence.md"],
            current_metadata_path="capture.yaml",
            current_project_root=self.current_project,
            current_corpus_root=self.current_corpus,
            current_selected_paths=["evidence.md"],
            authorize_validation_read=lambda: True,
            authorize_processing_and_report=lambda: True,
        )
        args.update(kwargs)
        return resolve_evidence_binding(**args)

    def test_complete_unchanged_mapping_emits_exact_bounded_report(self):
        report = self.resolve()
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["knowledge"]["summary"], "unchanged")
        self.assertEqual(report["references"][0]["state"], "unchanged")
        self.assertEqual(report["references"][0]["reason"], "byte_revision_matches")
        self.assertEqual(report["references"][0]["raw_path"], "evidence.md")
        self.assertEqual(report["references"][0]["current"]["raw_path"], "evidence.md")
        self.assertNotIn("Evidence baseline", repr(report))
        self.assertNotIn(str(self.root), repr(report))

    def test_changed_evidence_and_missing_mapping(self):
        changed = b"Evidence changed.\n"
        (self.current_project / self.current_corpus / "evidence.md").write_bytes(changed)
        self._write_envelope(self.current_meta, "source-current", "rep-current", changed)
        report = self.resolve()
        self.assertEqual(report["knowledge"]["summary"], "changed")
        self.assertEqual(report["references"][0]["reason"], "byte_revision_differs")

        self.binding["bindings"][0]["evidence"][0].pop("current")
        self._write_binding()
        missing = self.resolve()
        self.assertEqual(missing["knowledge"]["summary"], "missing")
        self.assertEqual(missing["references"][0]["reason"], "current_mapping_absent")

    def test_changed_knowledge_precedes_missing_references(self):
        self.knowledge_path.write_bytes(b"# Topic\nRevised.\n")
        self.binding["bindings"][0]["evidence"][0].pop("current")
        self._write_binding()
        report = self.resolve()
        self.assertEqual(report["knowledge"]["summary"], "changed")
        self.assertEqual(report["references"][0]["state"], "missing")

    def test_binding_strict_json_and_mapping_validation(self):
        self.binding_path.write_text('{"schema":"kb-bootstrap.evidence-bindings","schema":"x"}', encoding="utf-8")
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})
        self._write_binding()
        self.binding["unknown"] = True
        self._write_binding()
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})
        self.binding.pop("unknown")
        self.binding["bindings"][0]["evidence"][0]["current"] = None
        self._write_binding()
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})

        self.binding["bindings"][0]["evidence"][0]["current"] = {
            "source_id": "source-current", "representation_id": "rep-current"
        }
        self.binding["bindings"][0]["binding_id"] = "dup"
        self.binding["bindings"].append({"binding_id": "dup", "evidence": [dict(self.binding["bindings"][0]["evidence"][0])]})
        self._write_binding()
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})
        self.binding["bindings"] = self.binding["bindings"][:1]
        self.binding["nested"] = {"unexpected": True}
        self._write_binding()
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})
        self.binding.pop("nested")
        self.binding["bindings"][0]["evidence"].append(dict(self.binding["bindings"][0]["evidence"][0]))
        self._write_binding()
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})
        self.binding["bindings"][0]["evidence"].pop()

        duplicate_nested = json.dumps(self.binding).replace(
            '"source_id": "source-current", "representation_id": "rep-current"',
            '"source_id": "source-current", "source_id": "source-current", "representation_id": "rep-current"',
        )
        self.binding_path.write_text(duplicate_nested, encoding="utf-8")
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})

    def test_baseline_digest_mismatch_blocks_before_report(self):
        self.binding["bindings"][0]["evidence"][0]["observed_sha256"] = "0" * 64
        self._write_binding()
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "baseline_identity_mismatch"})

    def test_current_reference_only_target_blocks_as_unsupported_binding(self):
        self._add_reference_only_source(self.current_meta, "source-current-ref", "rep-current-ref", "not-selected.md")
        self.binding["bindings"][0]["evidence"][0]["current"] = {
            "source_id": "source-current-ref", "representation_id": "rep-current-ref"
        }
        self._write_binding()
        result = self.resolve(current_selected_paths=["evidence.md"])
        self.assertEqual(result, {"status": "BLOCKED", "reason": "invalid_binding"})

    def test_baseline_reference_only_target_blocks_as_identity_mismatch(self):
        self._add_reference_only_source(self.base_meta, "source-base-ref", "rep-base-ref", "not-selected.md")
        self.binding["bindings"][0]["evidence"][0].update(
            source_id="source-base-ref", representation_id="rep-base-ref",
            observed_sha256=sha(self.base_bytes),
        )
        self._write_binding()
        result = self.resolve(baseline_selected_paths=["evidence.md"])
        self.assertEqual(result, {"status": "BLOCKED", "reason": "baseline_identity_mismatch"})

    def test_unreferenced_nonretained_current_entry_does_not_block(self):
        # A valid but unrelated reference-only representation does not expand the selected set.
        self._add_reference_only_source(self.current_meta, "source-unused", "rep-unused", "never-open.txt")
        report = self.resolve(current_selected_paths=["evidence.md"])
        self.assertEqual(report["status"], "COMPLETE")
        self.assertNotIn("never-open.txt", repr(report))

    def test_revision_outcome_matrix_keeps_mixed_rows_and_sorts(self):
        # Three explicit references exercise unchanged, changed, and missing together.
        baseline_b = b"Baseline B.\n"
        baseline_c = b"Baseline C.\n"
        current_b = b"Current B.\n"
        for name, payload in (("b.md", baseline_b), ("c.md", baseline_c)):
            (self.base_project / self.base_corpus / name).write_bytes(payload)
        (self.current_project / self.current_corpus / "b.md").write_bytes(current_b)
        self._write_multi_envelopes(baseline_b, baseline_c, current_b)
        first = self.binding["bindings"][0]["evidence"][0]
        first["current"] = {"source_id": "source-current", "representation_id": "rep-current"}
        self.binding["bindings"] = [{"binding_id": "b1", "evidence": [first]},
                                      {"binding_id": "b2", "evidence": [
            {"source_id": "source-b", "representation_id": "rep-b", "observed_sha256": sha(baseline_b),
             "current": {"source_id": "source-b-current", "representation_id": "rep-b-current"}},
            {"source_id": "source-c", "representation_id": "rep-c", "observed_sha256": sha(baseline_c)},
        ]}]
        self._write_binding()
        report = self.resolve(baseline_selected_paths=["evidence.md", "b.md", "c.md"],
                              current_selected_paths=["evidence.md", "b.md"])
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["knowledge"]["summary"], "changed")
        self.assertEqual([(r["source_id"], r["state"]) for r in report["references"]],
                         [("source-b", "changed"), ("source-base", "unchanged"), ("source-c", "missing")])
        self.assertNotIn("current", report["references"][2])
        self.assertEqual(report["references"][2]["reason"], "current_mapping_absent")

    def _write_multi_envelopes(self, baseline_b, baseline_c, current_b):
        self._write_envelope(self.base_meta, "source-base", "rep-base", self.base_bytes)
        for source_id, rep_id, path, payload in (("source-b", "rep-b", "b.md", baseline_b),
                                                  ("source-c", "rep-c", "c.md", baseline_c)):
            self._write_one_envelope_source(self.base_meta, source_id, rep_id, path, payload, append=True)
        self._write_envelope(self.current_meta, "source-current", "rep-current", self.current_bytes)
        self._write_one_envelope_source(self.current_meta, "source-b-current", "rep-b-current", "b.md", current_b, append=True)

    def _write_one_envelope_source(self, metadata, source_id, rep_id, path, payload, append=False):
        digest = sha(payload)
        source = (
            f"- source_id: {source_id}\n  origin: {{kind: opaque-owner-reference, reference: {source_id}}}\n"
            f"  original_revision: {{algorithm: sha256, digest: {digest}, media_type: text/plain}}\n"
            "  original_retention: retained\n  capture: {method: direct}\n"
            "  fidelity: {class: exact, coverage: all-bytes, losses: []}\n  representations:\n"
            f"  - representation_id: {rep_id}\n    revision: {{algorithm: sha256, digest: {digest}}}\n"
            f"    media_type: text/markdown\n    raw_path: {path}\n    retention: retained\n")
        if append:
            with metadata.open("a", encoding="utf-8") as stream:
                stream.write(source)
        else:
            metadata.write_text("schema: kb-bootstrap.source-capture\nversion: 1\nsources:\n" + source, encoding="utf-8")

    def test_fragment_line_bounds_are_enforced_by_resolver(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 2}
        self._write_binding()
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})
        ref["fragment"]["end_line"] = 1
        self._write_binding()
        self.assertEqual(self.resolve()["status"], "COMPLETE")

    def test_fragment_line_bounds_follow_adr036_lf_and_crlf_rule(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 2}
        self._write_binding()
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})
        ref["fragment"]["end_line"] = 1
        self._write_binding()
        self.assertEqual(self.resolve()["status"], "COMPLETE")

    def test_fixed_resource_ceilings_fail_without_partial_report(self):
        with patch.object(evidence_binding, "MAX_FILE_BYTES", 8):
            self.knowledge_path.write_bytes(b"x" * 9)
            self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "resource_limit_exceeded"})
        self.knowledge_path.write_bytes(self.knowledge)
        with patch.object(evidence_binding, "MAX_SELECTED_TOTAL", 1):
            self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "resource_limit_exceeded"})
        with patch.object(evidence_binding, "MAX_REPORT_BYTES", 10):
            self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "serialization_limit_exceeded"})
        with patch.object(evidence_binding, "MAX_REPORT_ITEMS", 1):
            self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "resource_limit_exceeded"})

    def test_fragment_line_bounds_follow_adr036_lf_and_crlf_rule(self):
        cases = (
            (b"one\n", 1),
            (b"one\r\n", 1),
            (b"one\r", 1),
            (b"", 0),
            (b"one\ntwo", 2),
        )
        for payload, maximum in cases:
            with self.subTest(payload=payload):
                if maximum:
                    valid = {"representation_id": "rep", "start_line": maximum, "end_line": maximum}
                    self.assertTrue(_fragment_valid(valid, payload))
                invalid = {"representation_id": "rep", "start_line": 1, "end_line": maximum + 1}
                self.assertFalse(_fragment_valid(invalid, payload))

    def test_permission_denial_precedes_any_file_open(self):
        with patch("kb_bootstrap.raw_manifest.os.open", side_effect=AssertionError("must not open")):
            with self.assertRaises(PermissionError):
                self.resolve(authorize_validation_read=lambda: False)

    def test_processing_denial_is_outside_wire_after_validation_reads(self):
        with self.assertRaises(PermissionError):
            self.resolve(authorize_processing_and_report=lambda: False)

    def test_processing_or_report_denial_does_not_return_report(self):
        with self.assertRaises(PermissionError):
            self.resolve(authorize_processing_and_report=lambda: False)

    def test_expected_revision_mismatch_is_sanitized_outside_wire(self):
        with self.assertRaisesRegex(ValueError, "^expected input revision mismatch$"):
            self.resolve(expected_revisions={"knowledge": "0" * 64})

    def test_metadata_revision_mismatch_precedes_envelope_validation(self):
        self.base_meta.write_text("invalid yaml: [", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "^expected input revision mismatch$"):
            self.resolve(expected_revisions={"baseline_metadata": "0" * 64})

    def test_selected_file_expected_revision_checks_validated_snapshot(self):
        expected = {"selected_files": {"baseline:evidence.md": "0" * 64}}
        with self.assertRaisesRegex(ValueError, "^expected input revision mismatch$"):
            self.resolve(expected_revisions=expected)

    def test_review_actor_uses_sanitized_actor_contract(self):
        self.binding["bindings"][0]["review_actor"] = "https://user@example.test"
        self._write_binding()
        self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "invalid_binding"})

    def test_reparse_point_components_block_before_open(self):
        with patch.object(Path, "lstat", return_value=SimpleNamespace(st_file_attributes=0x400, st_mode=stat.S_IFDIR)):
            self.assertTrue(evidence_binding._traverses_reparse_point(self.binding_root))
            self.assertEqual(self.resolve(), {"status": "BLOCKED", "reason": "unsafe_or_inaccessible_path"})

    def test_selected_root_and_input_paths_are_explicit(self):
        self.assertEqual(self.resolve(project_root=self.binding_root, binding_path="../binding.json"),
                         {"status": "BLOCKED", "reason": "invalid_binding"})
        self.assertEqual(self.resolve(project_root=self.binding_root / "missing"),
                         {"status": "BLOCKED", "reason": "unsafe_or_inaccessible_path"})


if __name__ == "__main__":
    unittest.main()
