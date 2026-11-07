import hashlib
import json
import os
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
            baseline_corpus_root=kwargs.pop("baseline_corpus_root", self.base_corpus),
            baseline_selected_paths=["evidence.md"],
            current_metadata_path="capture.yaml",
            current_project_root=self.current_project,
            current_corpus_root=kwargs.pop("current_corpus_root", self.current_corpus),
            current_selected_paths=["evidence.md"],
            authorize_validation_read=lambda: True,
            authorize_processing_and_report=lambda: True,
        )
        args.update(kwargs)
        return resolve_evidence_binding(**args)

    def diagnostic(self, **kwargs):
        args = dict(
            project_root=self.binding_root, binding_path="binding.json", knowledge_path="topic.md",
            baseline_metadata_path="capture.yaml", baseline_project_root=self.base_project,
            baseline_corpus_root=self.base_corpus, baseline_selected_paths=["evidence.md"],
            current_metadata_path="capture.yaml", current_project_root=self.current_project,
            current_corpus_root=self.current_corpus, current_selected_paths=["evidence.md"],
            authorize_validation_read=lambda: True, authorize_processing_and_report=lambda: True,
        )
        args.update(kwargs)
        return evidence_binding.resolve_evidence_binding_with_input_diagnostic(**args)

    def test_opt_in_input_diagnostic_binding_matrix_and_legacy_parity(self):
        cases = [
            ("valid", "COMPLETE", "NOT_APPLICABLE"),
            ("unsupported", "BLOCKED", "unsupported_schema"),
            ("wrong_type", "BLOCKED", "malformed_input"),
            ("boolean_version", "BLOCKED", "malformed_input"),
            ("extra_key", "BLOCKED", "malformed_input"),
            ("unsupported_schema", "BLOCKED", "unsupported_schema"),
        ]
        for case, report_status, diagnostic_reason in cases:
            with self.subTest(case=case):
                self.binding = json.loads(json.dumps(self.binding))
                if case in {"unsupported", "unsupported_schema"}:
                    self.binding["version"] = 2 if case == "unsupported" else 1
                    self.binding["schema"] = "kb-bootstrap.evidence-bindings-next"
                elif case == "wrong_type":
                    self.binding["schema"] = 3
                elif case == "boolean_version":
                    self.binding["version"] = True
                elif case == "extra_key":
                    self.binding["extra"] = "private marker"
                self._write_binding()
                old = self.resolve()
                result = self.diagnostic()
                self.assertEqual(result["resolver_report"], old)
                self.assertEqual(old["status"], report_status)
                if report_status == "COMPLETE":
                    self.assertEqual(result["input_diagnostic"], {"status": "NOT_APPLICABLE"})
                else:
                    self.assertEqual(result["input_diagnostic"], {"status": "CLASSIFIED", "reason": diagnostic_reason})
                    self.assertNotIn("private marker", json.dumps(result))
                self.binding = json.loads(json.dumps({
                    "schema": "kb-bootstrap.evidence-bindings", "version": 1,
                    "knowledge": {"path": "topic.md", "sha256": sha(self.knowledge)},
                    "bindings": [{"binding_id": "binding-1", "evidence": [{
                        "source_id": "source-base", "representation_id": "rep-base",
                        "observed_sha256": sha(self.base_bytes),
                        "current": {"source_id": "source-current", "representation_id": "rep-current"},
                    }]}],
                }))

    def test_opt_in_input_diagnostic_duplicate_json_and_access_denial(self):
        self.binding_path.write_text('{"schema":"kb-bootstrap.evidence-bindings","schema":"secret","version":1}', encoding="utf-8")
        result = self.diagnostic()
        self.assertEqual(result["resolver_report"], {"status": "BLOCKED", "reason": "invalid_binding"})
        self.assertEqual(result["input_diagnostic"], {"status": "CLASSIFIED", "reason": "malformed_input"})
        self.assertNotIn("secret", json.dumps(result))
        with patch("kb_bootstrap.raw_manifest.os.open") as open_spy:
            with self.assertRaises(PermissionError):
                self.diagnostic(authorize_validation_read=lambda: False)
        open_spy.assert_not_called()

    def test_opt_in_input_diagnostic_reads_binding_once(self):
        original = evidence_binding._read_selected
        binding_reads = []

        def counted(root, relative, limit):
            if relative == "binding.json":
                binding_reads.append(relative)
            return original(root, relative, limit)

        with patch.object(evidence_binding, "_read_selected", side_effect=counted):
            result = self.diagnostic()
        self.assertEqual(result["resolver_report"], self.resolve())
        self.assertEqual(binding_reads, ["binding.json"])

    def test_opt_in_input_diagnostic_invalid_utf8_yaml_is_malformed(self):
        invalid_metadata = bytes([255])
        self.base_meta.write_bytes(invalid_metadata)
        self.assertEqual(self.base_meta.read_bytes(), invalid_metadata)
        legacy = self.resolve()
        self.assertEqual(legacy, {"status": "BLOCKED", "reason": "invalid_or_incomplete_envelope"})

        from kb_bootstrap import source_capture_validation
        original = source_capture_validation._read_regular
        metadata_reads = []

        def counted(root, relative, limit):
            if relative == "capture.yaml":
                metadata_reads.append((Path(root), relative))
            return original(root, relative, limit)

        with patch.object(source_capture_validation, "_read_regular", side_effect=counted):
            result = self.diagnostic()
        self.assertEqual(result["resolver_report"], legacy)
        self.assertEqual(result["input_diagnostic"], {"status": "CLASSIFIED", "reason": "malformed_input"})
        self.assertEqual(len(metadata_reads), 1)
        observed_root, relative = metadata_reads[0]
        self.assertTrue(os.path.samefile(observed_root, self.base_project))
        self.assertEqual(relative, "capture.yaml")

    def test_opt_in_input_diagnostic_baseline_digest_mismatch_is_not_classified(self):
        original = self.base_meta.read_text(encoding="utf-8")
        self.base_meta.write_text(
            original.replace(
                f"    revision: {{algorithm: sha256, digest: {sha(self.base_bytes)}}}",
                f"    revision: {{algorithm: sha256, digest: {'f' * 64}}}",
            ),
            encoding="utf-8",
        )
        legacy = self.resolve()
        result = self.diagnostic()
        self.assertEqual(legacy, {"status": "BLOCKED", "reason": "invalid_or_incomplete_envelope"})
        self.assertEqual(result["resolver_report"], legacy)
        self.assertEqual(
            result["input_diagnostic"],
            {"status": "NOT_CLASSIFIED", "reason": "invalid_or_incomplete_envelope"},
        )

    def test_opt_in_input_diagnostic_current_unsupported_after_valid_baseline(self):
        self.current_meta.write_text(
            "\n".join(("schema: kb-bootstrap.source-capture", "version: 2", "sources: []", "")),
            encoding="utf-8",
        )
        legacy = self.resolve()
        self.assertEqual(legacy, {"status": "BLOCKED", "reason": "invalid_or_incomplete_envelope"})
        result = self.diagnostic()
        self.assertEqual(result["resolver_report"], legacy)
        self.assertEqual(result["input_diagnostic"], {"status": "CLASSIFIED", "reason": "unsupported_schema"})

    def test_opt_in_input_diagnostic_malformed_capture_sources_are_classified(self):
        malformed_records = ("sources: null", "sources: [null]")
        for sources in malformed_records:
            with self.subTest(sources=sources):
                self.base_meta.write_text(
                    "\n".join((
                        "schema: kb-bootstrap.source-capture", "version: 1", sources, "",
                    )),
                    encoding="utf-8",
                )
                legacy = self.resolve()
                self.assertEqual(
                    legacy, {"status": "BLOCKED", "reason": "invalid_or_incomplete_envelope"}
                )
                result = self.diagnostic()
                self.assertEqual(result["resolver_report"], legacy)
                self.assertEqual(
                    result["input_diagnostic"],
                    {"status": "CLASSIFIED", "reason": "malformed_input"},
                )

    def test_opt_in_input_diagnostic_binding_count_limits_are_unclassified(self):
        cases = (
            ("bindings", "MAX_BINDINGS", 1),
            ("references", "MAX_REFERENCES", 1),
        )
        for name, limit_name, limit in cases:
            with self.subTest(name=name):
                if name == "bindings":
                    self.binding["bindings"] = [
                        {"binding_id": f"b{index}", "evidence": [{
                            "source_id": "source-base", "representation_id": "rep-base",
                            "observed_sha256": sha(self.base_bytes),
                        }]}
                        for index in range(3)
                    ]
                else:
                    self.binding["bindings"][0]["evidence"] = [
                        {"source_id": f"s{index}", "representation_id": f"r{index}",
                         "observed_sha256": sha(self.base_bytes)}
                        for index in range(3)
                    ]
                self._write_binding()
                with patch.object(evidence_binding, limit_name, limit):
                    legacy = self.resolve()
                    result = self.diagnostic()
                self.assertEqual(legacy, {"status": "BLOCKED", "reason": "invalid_binding"})
                self.assertEqual(result["resolver_report"], legacy)
                self.assertEqual(
                    result["input_diagnostic"],
                    {"status": "NOT_CLASSIFIED", "reason": "invalid_binding"},
                )

    def test_opt_in_input_diagnostic_yaml_limits_remain_unclassified(self):
        from kb_bootstrap import source_capture_validation
        cases = (
            ("events", {"MAX_YAML_EVENTS": 5}, "\n".join(("schema: kb-bootstrap.source-capture", "version: 1", "sources: []", ""))),
            ("depth", {"MAX_YAML_EVENTS": 200000, "MAX_YAML_DEPTH": 0}, "\n".join(("schema: kb-bootstrap.source-capture", "version: 1", "sources: []", ""))),
        )
        for name, limits, metadata in cases:
            with self.subTest(name=name):
                self.base_meta.write_text(metadata, encoding="utf-8")
                with patch.multiple(source_capture_validation, **limits):
                    legacy = self.resolve()
                    result = self.diagnostic()
                self.assertEqual(legacy, {"status": "BLOCKED", "reason": "invalid_or_incomplete_envelope"})
                self.assertEqual(result["resolver_report"], legacy)
                self.assertEqual(
                    result["input_diagnostic"],
                    {"status": "NOT_CLASSIFIED", "reason": "invalid_or_incomplete_envelope"},
                )

    def test_opt_in_input_diagnostic_malformed_nested_capture_matrix(self):
        original = self.base_meta.read_text(encoding="utf-8")
        malformed = {
            "source_id_type": original.replace("source_id: source-base", "source_id: []"),
            "origin_shape": original.replace("origin: {kind: opaque-owner-reference, reference: source-base}", "origin: []"),
            "representation_container": original.replace("representations:\n", "representations: null\n").replace(
                "  - representation_id: rep-base\n    revision:", "  revision:"
            ),
            "unknown_source_key": original.replace("- source_id: source-base", "- unknown: marker\n  source_id: source-base"),
            "missing_source_field": original.replace("  origin: {kind: opaque-owner-reference, reference: source-base}\n", ""),
            "duplicate_source_id": original.replace(
                "  origin: {kind: opaque-owner-reference, reference: source-base}\n",
                "  source_id: duplicate\n  origin: {kind: opaque-owner-reference, reference: source-base}\n",
            ),
            "malformed_coordinates": original.replace(
                "    revision: {algorithm:",
                "    coordinates: {local: {unit: byte, range: [true, 2]}}\n    revision: {algorithm:",
            ),
        }
        for name, value in malformed.items():
            with self.subTest(name=name):
                self.base_meta.write_text(value, encoding="utf-8")
                legacy = self.resolve()
                self.assertEqual(legacy, {"status": "BLOCKED", "reason": "invalid_or_incomplete_envelope"})
                result = self.diagnostic()
                self.assertEqual(result["resolver_report"], legacy)
                self.assertEqual(
                    result["input_diagnostic"],
                    {"status": "CLASSIFIED", "reason": "malformed_input"},
                )
        self.base_meta.write_text(original, encoding="utf-8")

    def test_opt_in_input_diagnostic_later_resource_block_not_classified(self):
        legacy = self.resolve()
        result = self.diagnostic()
        self.assertEqual(result["resolver_report"], legacy)
        with patch.object(evidence_binding, "MAX_SELECTED_TOTAL", 1):
            legacy_block = self.resolve()
            result_block = self.diagnostic()
        self.assertEqual(legacy_block, {"status": "BLOCKED", "reason": "resource_limit_exceeded"})
        self.assertEqual(result_block["resolver_report"], legacy_block)
        self.assertEqual(
            result_block["input_diagnostic"],
            {"status": "NOT_CLASSIFIED", "reason": "resource_limit_exceeded"},
        )

    def test_opt_in_input_diagnostic_yaml_unsupported_and_composer_compatibility(self):
        from kb_bootstrap.evidence_review import compose_evidence_review_worklist
        self.base_meta.write_text("schema: kb-bootstrap.source-capture\nversion: 2\nsources: []\n", encoding="utf-8")
        result = self.diagnostic()
        self.assertEqual(result["resolver_report"], self.resolve())
        self.assertEqual(result["input_diagnostic"], {"status": "CLASSIFIED", "reason": "unsupported_schema"})
        self.assertEqual(result["resolver_report"], {"status": "BLOCKED", "reason": "invalid_or_incomplete_envelope"})
        self.base_meta.write_text(
            "schema: kb-bootstrap.source-capture\\nversion: 1\\nsources: []\\n", encoding="utf-8"
        )
        self._write_envelope(self.base_meta, "source-base", "rep-base", self.base_bytes)
        self.current_meta.write_text(
            "schema: kb-bootstrap.source-capture\\nversion: 1\\nsources: []\\n", encoding="utf-8"
        )
        self._write_envelope(self.current_meta, "source-current", "rep-current", self.current_bytes)
        self._write_binding()
        result = self.diagnostic()
        legacy = self.resolve()
        self.assertEqual(result["resolver_report"], legacy)
        self.assertEqual(
            compose_evidence_review_worklist(result["resolver_report"], [], True, {}),
            compose_evidence_review_worklist(legacy, [], True, {}),
        )

    def test_complete_unchanged_mapping_emits_exact_bounded_report(self):
        (self.base_project / "raw/baseline").mkdir(parents=True)
        (self.current_project / "raw/current").mkdir(parents=True)
        (self.base_project / "raw/baseline/evidence.md").write_bytes(self.base_bytes)
        (self.current_project / "raw/current/evidence.md").write_bytes(self.current_bytes)
        self._write_envelope(self.base_meta, "source-base", "rep-base", self.base_bytes)
        self._write_envelope(self.current_meta, "source-current", "rep-current", self.current_bytes)
        report = self.resolve(baseline_corpus_root="raw/baseline", current_corpus_root="raw/current")
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["knowledge"]["summary"], "unchanged")
        self.assertEqual(report["references"][0]["state"], "unchanged")
        self.assertEqual(report["references"][0]["reason"], "byte_revision_matches")
        self.assertEqual(report["references"][0]["raw_path"], "raw/baseline/evidence.md")
        self.assertEqual(report["references"][0]["current"]["raw_path"], "raw/current/evidence.md")
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
        self.assertEqual([r["raw_path"] for r in report["references"]],
                         ["corpus/b.md", "corpus/evidence.md", "corpus/c.md"])
        self.assertEqual(report["references"][0]["current"]["raw_path"], "corpus/b.md")
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

    def _fragment_args(self):
        return dict(
            project_root=self.binding_root, binding_path="binding.json", knowledge_path="topic.md",
            baseline_metadata_path="capture.yaml", baseline_project_root=self.base_project,
            baseline_corpus_root=self.base_corpus, baseline_selected_paths=["evidence.md"],
            current_metadata_path="capture.yaml", current_project_root=self.current_project,
            current_corpus_root=self.current_corpus, current_selected_paths=["evidence.md"],
            authorize_validation_read=lambda: True, authorize_processing_and_report=lambda: True,
        )

    def test_fragment_range_extracts_multiline_and_crlf_bytes(self):
        payload = b"one\r\ntwo\r\nthree"
        extracted = evidence_binding._fragment_ranges(payload, [(1, 2, "a"), (2, 3, "b")])
        self.assertEqual(bytes(extracted["a"][0]), b"one\r\ntwo")
        self.assertEqual(extracted["a"][1], 0)
        self.assertEqual(bytes(extracted["b"][0]), b"two\r\nthree")
        self.assertEqual(extracted["b"][1], 5)

    def test_fragment_scan_budget_addition_saturates_without_wraparound(self):
        cap = evidence_binding.MAX_FRAGMENT_SCAN_WORK
        self.assertEqual(evidence_binding._checked_scan_add(cap, 0, cap), cap)
        self.assertEqual(evidence_binding._checked_scan_add(cap, 1, cap), cap + 1)
        self.assertEqual(evidence_binding._checked_scan_add(cap + 1, 0, cap), cap + 1)

    def test_fragment_range_budget_preflights_before_materializing_slices(self):
        payload = b"x" * 40000
        ranges = [(1, 1, "first"), (1, 1, "repeat-a"), (1, 1, "repeat-b")]
        with patch.object(evidence_binding, "MAX_FRAGMENT_TOTAL_BYTES", 100000), patch(
                "builtins.memoryview", side_effect=AssertionError("slice must not be materialized")):
            with self.assertRaises(OverflowError):
                evidence_binding._fragment_ranges(payload, ranges)
        oversized = b"z" * (evidence_binding.MAX_FRAGMENT_BYTES + 1)
        with patch("builtins.memoryview", side_effect=AssertionError("oversized slice must not be materialized")):
            with self.assertRaises(OverflowError):
                evidence_binding._fragment_ranges(oversized, [(1, 1, "oversized")])

    def test_fragment_continuity_not_applicable_and_current_missing(self):
        result = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(result["fragment_continuity"], {"status": "NOT_APPLICABLE", "observations": []})
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 1}
        ref["current"] = {"source_id": "absent", "representation_id": "absent"}
        self._write_binding()
        result = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(result["fragment_continuity"]["observations"][0]["outcome"], "unassessable_current_missing")

    def test_fragment_continuity_exact_and_overlapping_matches(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 1}
        self._write_binding()
        result = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(result["resolver_report"], self.resolve())
        observation = result["fragment_continuity"]["observations"][0]
        self.assertEqual(observation["outcome"], "exact_at_baseline_offset")
        self.assertEqual(observation["current_offsets"], [0])
        self.assertEqual(evidence_binding._kmp_offsets(b"aaaa", b"aa"), [0, 1, 2])

    def test_fragment_continuity_moved_missing_and_no_mapping(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 1}
        self.current_bytes = b"prefix\n" + self.base_bytes
        (self.current_project / self.current_corpus / "evidence.md").write_bytes(self.current_bytes)
        self._write_envelope(self.current_meta, "source-current", "rep-current", self.current_bytes)
        self._write_binding()
        moved = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(moved["fragment_continuity"]["observations"][0]["outcome"], "unique_moved_match")
        self.current_bytes = b"different\n"
        (self.current_project / self.current_corpus / "evidence.md").write_bytes(self.current_bytes)
        self._write_envelope(self.current_meta, "source-current", "rep-current", self.current_bytes)
        self._write_binding()
        absent = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(absent["fragment_continuity"]["observations"][0]["outcome"], "no_exact_match")
        ref.pop("current")
        self._write_binding()
        no_mapping = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(no_mapping["fragment_continuity"]["observations"][0]["outcome"], "unassessable_no_mapping")

    def test_fragment_continuity_baseline_snapshot_read_once(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 1}
        second = dict(ref)
        second["fragment"] = dict(ref["fragment"])
        self.binding["bindings"].append({"binding_id": "binding-2", "evidence": [second]})
        self._write_binding()
        from kb_bootstrap import source_capture_validation
        original = source_capture_validation._read_regular
        calls = []
        expected_root = (self.base_project / self.base_corpus).resolve()
        def counted(root, relative, limit):
            key = (Path(root).resolve(), Path(relative).as_posix())
            calls.append(key)
            return original(root, relative, limit)
        with patch.object(source_capture_validation, "_read_regular", side_effect=counted):
            result = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(result["fragment_continuity"]["status"], "COMPLETE")
        matching_reads = [key for key in calls if key == (expected_root, "evidence.md")]
        self.assertEqual(len(matching_reads), 1)
        self.assertTrue(calls)

    def test_fragment_continuity_repeated_locators_prepare_each_snapshot_once(self):
        payload = b"".join(f"{index:04d}".encode("ascii") + b"x" * 1019 + b"\n" for index in range(2048))
        (self.base_project / self.base_corpus / "evidence.md").write_bytes(payload)
        (self.current_project / self.current_corpus / "evidence.md").write_bytes(payload)
        self._write_envelope(self.base_meta, "source-base", "rep-base", payload)
        self._write_envelope(self.current_meta, "source-current", "rep-current", payload)
        first = self.binding["bindings"][0]["evidence"][0]
        first["observed_sha256"] = sha(payload)
        first["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 1}
        bindings = [self.binding["bindings"][0]]
        for index in range(1, 20):
            ref = dict(first)
            ref["fragment"] = dict(first["fragment"])
            bindings.append({"binding_id": f"binding-{index + 1}", "evidence": [ref]})
        self.binding["bindings"] = bindings
        self._write_binding()

        from kb_bootstrap import source_capture_validation
        original_sha256 = source_capture_validation.hashlib.sha256
        original_ranges = evidence_binding._fragment_ranges
        digest_lengths = []
        baseline_ranges = []
        matcher_calls = []
        def counted_sha256(data=b"", *args, **kwargs):
            if data == payload:
                digest_lengths.append(len(data))
            return original_sha256(data, *args, **kwargs)
        def counted_ranges(data, references, extracted_total=0, **kwargs):
            if data == payload:
                baseline_ranges.append(len(references))
            return original_ranges(data, references, extracted_total, **kwargs)
        original_matcher = evidence_binding._kmp_offsets
        def counted_matcher(text, pattern):
            matcher_calls.append(len(text))
            return original_matcher(text, pattern)
        with patch.object(source_capture_validation.hashlib, "sha256", side_effect=counted_sha256), \
                patch.object(evidence_binding, "_fragment_ranges", side_effect=counted_ranges), \
                patch.object(evidence_binding, "_kmp_offsets", side_effect=counted_matcher):
            result = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(result["resolver_report"]["status"], "COMPLETE")
        self.assertEqual(result["fragment_continuity"]["status"], "COMPLETE")
        self.assertEqual(len(result["fragment_continuity"]["observations"]), 20)
        self.assertEqual(digest_lengths.count(len(payload)), 2)
        self.assertEqual(baseline_ranges, [20])
        self.assertEqual(len(matcher_calls), 20)

        with patch.object(evidence_binding, "MAX_FRAGMENT_SCAN_WORK", 1), patch.object(
                evidence_binding, "_kmp_offsets", side_effect=AssertionError("preflight must block before KMP")):
            blocked = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(blocked["resolver_report"]["status"], "COMPLETE")
        self.assertEqual(blocked["fragment_continuity"], {
            "status": "BLOCKED", "reason": "aggregate_scan_budget_exceeded"
        })

    def test_fragment_continuity_empty_fragment_is_unassessable(self):
        payload = b"\nEvidence after blank line.\n"
        (self.base_project / self.base_corpus / "evidence.md").write_bytes(payload)
        (self.current_project / self.current_corpus / "evidence.md").write_bytes(payload)
        self._write_envelope(self.base_meta, "source-base", "rep-base", payload)
        self._write_envelope(self.current_meta, "source-current", "rep-current", payload)
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["observed_sha256"] = sha(payload)
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 1}
        self._write_binding()
        standalone = self.resolve()
        self.assertEqual(standalone["status"], "COMPLETE")
        with patch.object(evidence_binding, "_kmp_offsets", side_effect=AssertionError("empty fragments must not search")):
            combined = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(combined["resolver_report"], standalone)
        self.assertEqual(combined["fragment_continuity"]["status"], "COMPLETE")
        observation = combined["fragment_continuity"]["observations"][0]
        self.assertEqual(observation["outcome"], "unassessable_empty_fragment")
        self.assertEqual(observation["current_offsets"], [])
        self.assertEqual(observation["current"], {
            "source_id": "source-current",
            "representation_id": "rep-current",
            "observed_sha256": sha(payload),
        })

        ref.pop("current")
        self._write_binding()
        with patch.object(evidence_binding, "_kmp_offsets", side_effect=AssertionError("empty fragments must not search")):
            unmapped = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(unmapped["fragment_continuity"]["status"], "COMPLETE")
        unmapped_observation = unmapped["fragment_continuity"]["observations"][0]
        self.assertEqual(unmapped_observation["outcome"], "unassessable_empty_fragment")
        self.assertIsNone(unmapped_observation["current"])
        self.assertEqual(unmapped_observation["current_offsets"], [])

    def test_fragment_continuity_invalid_range_preserves_resolver_block(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 2}
        self._write_binding()
        standalone = self.resolve()
        self.assertEqual(standalone, {"status": "BLOCKED", "reason": "invalid_binding"})
        with patch.object(evidence_binding, "_kmp_offsets", side_effect=AssertionError("invalid range must not search")):
            combined = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(combined["resolver_report"], standalone)
        self.assertEqual(combined["fragment_continuity"], {"status": "BLOCKED", "reason": "resolver_blocked"})

    def test_fragment_continuity_duplicate_matches_and_permission_denial(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 1}
        self.current_bytes = self.base_bytes + self.base_bytes
        (self.current_project / self.current_corpus / "evidence.md").write_bytes(self.current_bytes)
        self._write_envelope(self.current_meta, "source-current", "rep-current", self.current_bytes)
        self._write_binding()
        result = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        observation = result["fragment_continuity"]["observations"][0]
        self.assertEqual(observation["outcome"], "ambiguous_exact_matches")
        self.assertEqual(observation["current_offsets"], [0, len(self.base_bytes)])
        denied = self._fragment_args()
        denied["authorize_validation_read"] = lambda: False
        with patch("kb_bootstrap.raw_manifest.os.open", side_effect=AssertionError("denied operation must not read")):
            with self.assertRaises(PermissionError):
                evidence_binding.resolve_evidence_binding_with_fragment_continuity(**denied)

    def test_fragment_continuity_budget_exact_cap_and_match_limit_are_atomic(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 1}
        self._write_binding()
        current_size = len(self.current_bytes)
        pattern_size = len(evidence_binding._fragment_ranges(self.base_bytes, [(1, 1, "ref")])["ref"][0])
        work = len(self.base_bytes) + pattern_size + current_size + pattern_size
        with patch.object(evidence_binding, "MAX_FRAGMENT_SCAN_WORK", work):
            complete = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(complete["fragment_continuity"]["status"], "COMPLETE")
        with patch.object(evidence_binding, "MAX_FRAGMENT_SCAN_WORK", work - 1):
            overflow = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(overflow["fragment_continuity"], {"status": "BLOCKED", "reason": "aggregate_scan_budget_exceeded"})
        self.current_bytes = self.base_bytes * 101
        (self.current_project / self.current_corpus / "evidence.md").write_bytes(self.current_bytes)
        self._write_envelope(self.current_meta, "source-current", "rep-current", self.current_bytes)
        self._write_binding()
        too_many = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(too_many["fragment_continuity"], {"status": "BLOCKED", "reason": "match_limit_exceeded"})
        self.assertNotIn("observations", too_many["fragment_continuity"])

    def test_fragment_continuity_budget_blocks_before_matcher(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 1}
        self._write_binding()
        with patch.object(evidence_binding, "MAX_FRAGMENT_SCAN_WORK", 1), patch.object(
                evidence_binding, "_kmp_offsets", side_effect=AssertionError("matcher must not run")):
            result = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(result["fragment_continuity"], {"status": "BLOCKED", "reason": "aggregate_scan_budget_exceeded"})
        self.assertEqual(result["resolver_report"]["status"], "COMPLETE")

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

    def test_processing_denial_precedes_any_file_open_after_validation_read_allowed(self):
        events = []
        validation_read_calls = []
        processing_report_calls = []

        def allow_validation_read():
            events.append("validation_read")
            validation_read_calls.append(True)
            return True

        def deny_processing_report():
            events.append("processing_report")
            processing_report_calls.append(True)
            return False

        with patch("kb_bootstrap.raw_manifest.os.open") as open_spy:
            with self.assertRaisesRegex(PermissionError, "^evidence processing/report denied$"):
                self.resolve(authorize_validation_read=allow_validation_read,
                             authorize_processing_and_report=deny_processing_report)

        self.assertEqual(events, ["validation_read", "processing_report"])
        self.assertEqual(validation_read_calls, [True])
        self.assertEqual(processing_report_calls, [True])
        open_spy.assert_not_called()

    def test_processing_denial_is_outside_wire_after_validation_reads(self):
        with self.assertRaises(PermissionError):
            self.resolve(authorize_processing_and_report=lambda: False)

    def test_processing_or_report_denial_does_not_return_report(self):
        with self.assertRaises(PermissionError):
            self.resolve(authorize_processing_and_report=lambda: False)

    def test_expected_revision_mismatch_is_sanitized_outside_wire(self):
        with self.assertRaisesRegex(ValueError, "^expected input revision mismatch$"):
            self.resolve(expected_revisions={"knowledge": "0" * 64})

    def test_combined_error_priority_preserves_input_order(self):
        ref = self.binding["bindings"][0]["evidence"][0]
        ref["fragment"] = {"representation_id": "rep-base", "start_line": 1, "end_line": 2}
        bad_identity = {
            "source_id": "source-missing", "representation_id": "rep-missing", "observed_sha256": "0" * 64,
        }
        self.binding["bindings"][0]["evidence"] = [dict(ref), bad_identity]
        self._write_binding()
        standalone_first = self.resolve()
        self.assertEqual(standalone_first, {"status": "BLOCKED", "reason": "invalid_binding"})
        combined_first = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(combined_first["resolver_report"], standalone_first)
        self.assertEqual(combined_first["fragment_continuity"], {"status": "BLOCKED", "reason": "resolver_blocked"})

        self.binding["bindings"][0]["evidence"] = [dict(bad_identity), dict(ref)]
        self._write_binding()
        standalone_identity_first = self.resolve()
        self.assertEqual(standalone_identity_first, {"status": "BLOCKED", "reason": "baseline_identity_mismatch"})
        combined_identity_first = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**self._fragment_args())
        self.assertEqual(combined_identity_first["resolver_report"], standalone_identity_first)
        self.assertEqual(combined_identity_first["fragment_continuity"], {"status": "BLOCKED", "reason": "resolver_blocked"})

    def test_combined_invalid_identity_precedes_report_limit(self):
        references = []
        selected_paths = []
        for index in range(100):
            path = "evidence.md" if index == 0 else f"evidence-{index:03}.md"
            payload = self.base_bytes if index == 0 else f"Evidence {index}.\n".encode()
            if index:
                (self.base_project / self.base_corpus / path).write_bytes(payload)
                self._write_one_envelope_source(self.base_meta, f"source-{index:03}", f"rep-{index:03}", path, payload, append=True)
            references.append({
                "source_id": "source-base" if index == 0 else f"source-{index:03}",
                "representation_id": "rep-base" if index == 0 else f"rep-{index:03}",
                "observed_sha256": sha(payload),
            })
            selected_paths.append(path)
        references[0].update(source_id="source-missing", representation_id="rep-missing", observed_sha256="0" * 64)
        self.binding["bindings"] = [
            {"binding_id": f"binding-{group}", "evidence": [dict(reference) for reference in references]}
            for group in range(10)
        ]
        self._write_binding()
        args = self._fragment_args()
        args["baseline_selected_paths"] = selected_paths
        standalone = evidence_binding.resolve_evidence_binding(**args)
        self.assertEqual(standalone, {"status": "BLOCKED", "reason": "baseline_identity_mismatch"})
        with patch.object(evidence_binding, "_kmp_offsets", side_effect=AssertionError("invalid identity must not search")):
            combined = evidence_binding.resolve_evidence_binding_with_fragment_continuity(**args)
        self.assertEqual(combined["resolver_report"], standalone)
        self.assertEqual(combined["fragment_continuity"], {"status": "BLOCKED", "reason": "resolver_blocked"})

    def test_combined_report_limit_preserves_stale_revision_priority(self):
        references = []
        selected_paths = []
        for index in range(100):
            path = "evidence.md" if index == 0 else f"evidence-{index:03}.md"
            payload = self.base_bytes if index == 0 else f"Evidence {index}.\n".encode()
            if index:
                (self.base_project / self.base_corpus / path).write_bytes(payload)
                self._write_one_envelope_source(self.base_meta, f"source-{index:03}", f"rep-{index:03}", path, payload, append=True)
            references.append({
                "source_id": "source-base" if index == 0 else f"source-{index:03}",
                "representation_id": "rep-base" if index == 0 else f"rep-{index:03}",
                "observed_sha256": sha(payload),
            })
            selected_paths.append(path)
        self.binding["bindings"] = [
            {"binding_id": f"binding-{group}", "evidence": [dict(reference) for reference in references]}
            for group in range(10)
        ]
        self._write_binding()
        stale_revisions = (
            {"binding": "0" * 64},
            {"knowledge": "0" * 64},
            {"baseline_metadata": "0" * 64},
            {"selected_files": {"baseline:evidence-001.md": "0" * 64}},
        )
        for expected in stale_revisions:
            with self.subTest(expected=expected):
                args = self._fragment_args()
                args["baseline_selected_paths"] = selected_paths
                args["expected_revisions"] = expected
                with self.assertRaisesRegex(ValueError, "^expected input revision mismatch$"):
                    evidence_binding.resolve_evidence_binding(**args)
                with self.assertRaisesRegex(ValueError, "^expected input revision mismatch$"):
                    evidence_binding.resolve_evidence_binding_with_fragment_continuity(**args)

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
