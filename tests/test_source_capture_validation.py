import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.source_capture_validation import validate_source_capture


class SourceCaptureValidationTests(unittest.TestCase):
    def fixture(self, root, *, payload=b"hello\n", digest=None, extra=None):
        digest = digest or hashlib.sha256(payload).hexdigest()
        (root / "record.yaml").write_text(
            "schema: kb-bootstrap.source-capture\nversion: 1\nsources:\n"
            "- source_id: source-1\n  origin: {kind: opaque-owner-reference, reference: SRC-1}\n"
            f"  original_revision: {{algorithm: sha256, digest: {digest}, media_type: text/plain}}\n"
            "  original_retention: retained\n  capture: {method: direct}\n"
            "  fidelity: {class: exact, coverage: all-bytes, losses: []}\n"
            "  representations:\n  - representation_id: rep-1\n"
            f"    revision: {{algorithm: sha256, digest: {digest}}}\n"
            "    media_type: text/plain\n    raw_path: note.txt\n    retention: retained\n"
            + (extra or ""), encoding="utf-8")
        (root / "raw").mkdir(exist_ok=True)
        (root / "raw" / "note.txt").write_bytes(payload)
        return validate_source_capture("record.yaml", root, "raw", ["note.txt"])

    def test_exact_selected_bytes_pass_and_inputs_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = self.fixture(root)
            self.assertEqual(before, (True, ()))
            self.assertEqual((root / "raw" / "note.txt").read_bytes(), b"hello\n")

    def test_exact_digest_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, extra="")
            path = root / "record.yaml"
            text = path.read_text(encoding="utf-8").replace(
                hashlib.sha256(b"hello\n").hexdigest(), "0" * 64)
            path.write_text(text, encoding="utf-8")
            valid, errors = validate_source_capture("record.yaml", root, "raw", ["note.txt"])
            self.assertFalse(valid)
            self.assertTrue(errors)

    def test_multirepresentation_exact_requires_every_digest_to_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "raw" / "copy.txt").write_bytes(b"other\n")
            # Insert the second representation after the first one in the list.
            path = root / "record.yaml"
            text = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(b"other\n").hexdigest()
            text = text.replace("    raw_path: note.txt\n    retention: retained\n",
                "    raw_path: note.txt\n    retention: retained\n"
                f"  - representation_id: rep-2\n    revision: {{algorithm: sha256, digest: {digest}}}\n"
                "    media_type: text/plain\n    raw_path: copy.txt\n    retention: retained\n")
            path.write_text(text, encoding="utf-8")
            valid, errors = validate_source_capture("record.yaml", root, "raw", ["note.txt", "copy.txt"])
            self.assertFalse(valid)
            self.assertIn("every exact representation must match original digest", errors[0])

    def test_reviewer_malformed_origin_reason_urls_and_original_revision_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "record.yaml"
            original = path.read_text(encoding="utf-8")
            bad_records = (
                original.replace("reference: SRC-1", "reference: http://host:abc/x"),
                original.replace("reference: SRC-1", "reference: http://a b/x"),
                original.replace("reference: SRC-1", "reference: https://exa mple.com/"),
                original.replace("method: direct", "method: blocked, reason: []"),
                original.replace("algorithm: sha256, digest:", "algorithm: invalid, digest:"),
            )
            for malformed in bad_records:
                with self.subTest(record=malformed[:80]):
                    path.write_text(malformed, encoding="utf-8")
                    valid, errors = validate_source_capture("record.yaml", root, "raw", ["note.txt"])
                    self.assertFalse(valid)
                    self.assertTrue(errors)

    def test_manual_summary_optional_tool_lineage_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "record.yaml"
            text = path.read_text(encoding="utf-8")
            text = text.replace("fidelity: {class: exact, coverage: all-bytes, losses: []}",
                "fidelity: {class: manual-summary, coverage: selected-topics, losses: [timing]}")
            direct_exact = text.replace("fidelity: {class: manual-summary, coverage: selected-topics, losses: [timing]}",
                "fidelity: {class: exact, coverage: all-bytes, losses: []}")
            direct_with_lineage = direct_exact.replace("capture: {method: direct}",
                "capture: {method: direct, converter: {identity: tool-1, version: '1'}}")
            path.write_text(direct_with_lineage, encoding="utf-8")
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", ["note.txt"])[0])
            text = text.replace("capture: {method: direct}", "capture: {method: manual-summary}")
            path.write_text(text, encoding="utf-8")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", ["note.txt"])[0])
            direct = text.replace("capture: {method: manual-summary}", "capture: {method: direct}")
            direct = direct.replace("class: manual-summary", "class: partial")
            direct = direct.replace("losses: [timing]", "losses: []")
            path.write_text(direct, encoding="utf-8")
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", ["note.txt"])[0])
            text = text.replace("capture: {method: manual-summary}",
                "capture: {method: manual-summary, converter: {identity: tool-1, version: '1'}}")
            path.write_text(text, encoding="utf-8")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", ["note.txt"])[0])
            converted = text.replace("method: manual-summary", "method: converted")
            converted = converted.replace("class: manual-summary", "class: partial")
            converted = converted.replace("losses: [timing]", "losses: [timing, wording]")
            converted = converted.replace("method: converted, converter: {identity: tool-1, version: '1'}", "method: converted")
            path.write_text(converted, encoding="utf-8")
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", ["note.txt"])[0])
            converted = converted.replace("capture: {method: converted}",
                "capture: {method: converted, converter: {identity: tool-1, version: '1'}}")
            path.write_text(converted, encoding="utf-8")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", ["note.txt"])[0])
            blocked = (
                "schema: kb-bootstrap.source-capture\nversion: 1\nsources:\n"
                "- source_id: blocked-1\n  origin: {kind: unavailable, reason: source-unavailable}\n"
                "  original_revision: {opaque: unknown}\n  original_retention: unknown\n"
                "  capture: {method: blocked, reason: access-not-provided}\n"
                "  fidelity: {class: blocked, coverage: none, losses: [all-content-unavailable]}\n"
                "  representations: []\n")
            path.write_text(blocked, encoding="utf-8")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", [])[0])
            blocked_lineage = blocked.replace("reason: access-not-provided}",
                "reason: access-not-provided, converter: {identity: tool-1, version: '1'}}")
            path.write_text(blocked_lineage, encoding="utf-8")
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", [])[0])
            for bad in ("identity: true, version: '1'", "identity: tool-1, version: 'bad value'"):
                malformed = text.replace("identity: tool-1, version: '1'", bad)
                path.write_text(malformed, encoding="utf-8")
                valid, errors = validate_source_capture("record.yaml", root, "raw", ["note.txt"])
                self.assertFalse(valid)
                self.assertTrue(errors)

    def test_bounded_path_iterable_stops_at_limit_plus_one(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            observed = []
            def paths():
                for index in range(100_010):
                    observed.append(index)
                    yield f"missing-{index}.txt"
            valid, errors = validate_source_capture("record.yaml", root, "raw", paths())
            self.assertFalse(valid)
            self.assertIn("count exceeds limit", errors[0])
            self.assertEqual(len(observed), 100_001)

    def test_nonretained_coordinate_shape_is_still_validated_without_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "record.yaml"
            text = path.read_text(encoding="utf-8").replace(
                "retention: retained", "retention: reference-only").replace(
                "raw_path: note.txt", "raw_path: missing.txt").replace(
                "    revision: {algorithm:", "    coordinates: {local: {unit: byte, range: [true, 2]}}\n    revision: {algorithm:")
            path.write_text(text, encoding="utf-8")
            valid, errors = validate_source_capture("record.yaml", root, "raw", [])
            self.assertFalse(valid)
            self.assertIn("coordinate", errors[0])

    def test_deep_manifest_is_rejected_without_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "manifest.json").write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
            valid, errors = validate_source_capture("record.yaml", root, "raw", ["note.txt"], "manifest.json")
            self.assertFalse(valid)
            self.assertTrue(errors)

    def test_no_tree_enumeration_occurs(self):
        from unittest.mock import patch
        import os
        import kb_bootstrap.source_capture_validation as validator
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with patch.object(os, "scandir", side_effect=AssertionError("tree enumeration")), \
                 patch.object(os, "listdir", side_effect=AssertionError("tree enumeration")):
                self.assertTrue(validate_source_capture("record.yaml", root, "raw", ["note.txt"])[0])

    def test_malformed_scalar_fields_do_not_raise(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "record.yaml"
            variants = (
                "version: true",
                "access: owner-approved",
                "original_retention: []",
                "class: []",
                "coverage: {}",
                "retention: true",
            )
            originals = path.read_text(encoding="utf-8")
            for before, after in (("version: 1", variants[0]),
                                  ("source_id: source-1", variants[1]),
                                  ("original_retention: retained", variants[2]),
                                  ("class: exact", variants[3]),
                                  ("coverage: all-bytes", variants[4]),
                                  ("retention: retained", variants[5])):
                with self.subTest(after=after):
                    path.write_text(originals.replace(before, after, 1), encoding="utf-8")
                    valid, errors = validate_source_capture("record.yaml", root, "raw", ["note.txt"])
                    self.assertFalse(valid)
                    self.assertTrue(errors)

    def test_malformed_permission_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "record.yaml"
            text = path.read_text(encoding="utf-8").replace(
                "  original_retention: retained",
                "  permissions: {access: true, retention: owner, redistribution: unknown}\n"
                "  original_retention: retained")
            path.write_text(text, encoding="utf-8")
            valid, errors = validate_source_capture("record.yaml", root, "raw", ["note.txt"])
            self.assertFalse(valid)
            self.assertIn("permission labels", errors[0])

    def test_blocked_record_and_malformed_path_are_checked_without_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "raw").mkdir()
            (root / "record.yaml").write_text(
                "schema: kb-bootstrap.source-capture\nversion: 1\nsources:\n"
                "- source_id: blocked-1\n  origin: {kind: unavailable, reason: source-unavailable}\n"
                "  original_revision: {opaque: unknown}\n  original_retention: unknown\n"
                "  capture: {method: blocked, reason: origin-unavailable}\n"
                "  fidelity: {class: blocked, coverage: none, losses: [all-content-unavailable]}\n"
                "  representations: []\n", encoding="utf-8")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", [])[0])
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", ["C:/outside"])[0])

    def test_duplicate_keys_aliases_and_unsafe_selected_paths_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "record.yaml").write_text("schema: x\nschema: y\n", encoding="utf-8")
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", [])[0])
            (root / "record.yaml").write_text("a: &a [1]\nb: *a\n", encoding="utf-8")
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", [])[0])
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", ["../escape"])[0])

    def test_empty_utf8_text_representation_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, payload=b"")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", ["note.txt"])[0])

    def test_retained_representation_must_be_selected_but_nonretained_is_not_opened(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "raw" / "note.txt").unlink()
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", ["note.txt"])[0])
            path = root / "record.yaml"
            text = path.read_text(encoding="utf-8").replace(
                "retention: retained", "retention: reference-only")
            path.write_text(text, encoding="utf-8")
            (root / "raw" / "note.txt").write_bytes(b"not-retained")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", [])[0])
            (root / "raw" / "extra.txt").write_text("unselected", encoding="utf-8")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", [])[0])

    def test_optional_manifest_is_explicit_and_digest_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "manifest.json").write_text(json.dumps({
                "schema": "kb-bootstrap.raw-manifest", "version": 1,
                "corpus": "raw", "algorithm": "sha256", "files": [{
                    "path": "note.txt", "sha256": hashlib.sha256(b"hello\n").hexdigest()}]}), encoding="utf-8")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", ["note.txt"], "manifest.json")[0])
            bad_path_manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            bad_path_manifest["files"][0]["path"] = "other.txt"
            (root / "manifest.json").write_text(json.dumps(bad_path_manifest), encoding="utf-8")
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", ["note.txt"], "manifest.json")[0])
            (root / "manifest.json").write_text(json.dumps({
                "schema": "kb-bootstrap.raw-manifest", "version": 1,
                "corpus": "raw", "algorithm": "sha256", "files": [{
                    "path": "note.txt", "sha256": hashlib.sha256(b"hello\n").hexdigest()}]}), encoding="utf-8")
            (root / "raw" / "unlisted.txt").write_text("extra", encoding="utf-8")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", ["note.txt"], "manifest.json")[0])
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            manifest["corpus"] = "wrong"
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", ["note.txt"], "manifest.json")[0])
            manifest["corpus"] = "raw"
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(validate_source_capture("record.yaml", root, "raw", ["note.txt"], "manifest.json")[0])
            manifest["files"][0]["sha256"] = "0" * 64
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertFalse(validate_source_capture("record.yaml", root, "raw", ["note.txt"], "manifest.json")[0])


class CompleteW03EnvelopeTests(unittest.TestCase):
    PAYLOADS = {
        "letter-a/shared.txt": b"alpha\n",
        "letter-a/shared-copy.txt": b"alpha\n",
        "letter-b/shared.txt": b"alpha\n",
        "note-7/partial.txt": b"second paragraph\n",
        "briefing/summary.md": b"Operator summary.\n",
        "empty/empty.txt": b"",
    }

    def load_complete_record(self, root):
        import re
        import yaml
        examples = Path(__file__).parents[1] / "docs" / "fixtures" / "W03-source-capture-examples.md"
        text = examples.read_text(encoding="utf-8")
        match = re.search(r"### Complete proposed instance\s+```yaml\n(.*?)\n```", text, re.S)
        self.assertIsNotNone(match, "complete W03 envelope fixture is present")
        record = yaml.safe_load(match.group(1))
        (root / "records").mkdir()
        (root / "raw").mkdir()
        (root / "records" / "complete.yaml").write_text(match.group(1) + "\n", encoding="utf-8")
        for relative, payload in self.PAYLOADS.items():
            target = root / "raw" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        return record

    def test_complete_w03_envelope_validates_bytes_manifest_and_immutability(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.load_complete_record(root)
            raw = root / "raw"
            paths = [rep["raw_path"] for source in record["sources"]
                     for rep in source["representations"] if rep["retention"] == "retained"]
            self.assertEqual((len(record["sources"]), sum(len(x["representations"]) for x in record["sources"])), (6, 6))
            self.assertEqual(len(paths), 6)
            for source in record["sources"]:
                for rep in source["representations"]:
                    data = (raw / rep["raw_path"]).read_bytes()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), rep["revision"]["digest"])
            self.assertEqual((raw / "letter-a/shared.txt").read_bytes(), (raw / "letter-a/shared-copy.txt").read_bytes())
            self.assertEqual((raw / "letter-a/shared.txt").read_bytes(), (raw / "letter-b/shared.txt").read_bytes())
            self.assertNotEqual(record["sources"][0]["source_id"], record["sources"][1]["source_id"])
            files = [root / "records" / "complete.yaml", *[raw / item for item in paths]]
            before = {item.relative_to(root).as_posix(): item.read_bytes() for item in files}
            manifest_files = [
                {"path": item, "sha256": hashlib.sha256((raw / item).read_bytes()).hexdigest()}
                for item in sorted(self.PAYLOADS)
            ]
            (root / "manifest.json").write_text(json.dumps({
                "schema": "kb-bootstrap.raw-manifest",
                "version": 1,
                "corpus": "raw",
                "algorithm": "sha256",
                "files": manifest_files,
            }), encoding="utf-8")
            expected = (True, ())
            self.assertEqual(validate_source_capture("records/complete.yaml", root, "raw", paths, "manifest.json"), expected)
            self.assertEqual(validate_source_capture("records/complete.yaml", root, "raw", paths, "manifest.json"), expected)
            self.assertEqual(before, {item.relative_to(root).as_posix(): item.read_bytes() for item in files})

    def test_complete_envelope_rejects_mixed_exact_representation(self):
        import yaml
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self.load_complete_record(root)
            changed_bytes = b"not alpha\n"
            record["sources"][0]["representations"][1]["revision"]["digest"] = hashlib.sha256(changed_bytes).hexdigest()
            (root / "raw" / record["sources"][0]["representations"][1]["raw_path"]).write_bytes(changed_bytes)
            (root / "records" / "complete.yaml").write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
            valid, errors = validate_source_capture("records/complete.yaml", root, "raw", list(self.PAYLOADS))
            self.assertFalse(valid)
            self.assertIn("every exact representation", errors[0])

    def test_capture_revision_update_keeps_original_and_prior_capture_unchanged(self):
        from copy import deepcopy
        import yaml
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            complete = self.load_complete_record(root)
            source = deepcopy(complete["sources"][2])
            old_bytes = self.PAYLOADS["note-7/partial.txt"]
            old_digest = hashlib.sha256(old_bytes).hexdigest()
            old_record = {"schema": "kb-bootstrap.source-capture", "version": 1, "sources": [source]}
            old_path = root / "records" / "old.yaml"
            old_yaml = yaml.safe_dump(old_record, sort_keys=False)
            old_path.write_text(old_yaml, encoding="utf-8")
            old_metadata_bytes = old_path.read_bytes()
            old_raw = root / "raw" / "note-7/partial.txt"
            old_raw.write_bytes(old_bytes)
            self.assertTrue(validate_source_capture("records/old.yaml", root, "raw", ["note-7/partial.txt"])[0])

            updated = deepcopy(source)
            new_bytes = b"SECOND PARAGRAPH\n"
            new_digest = hashlib.sha256(new_bytes).hexdigest()
            updated["representations"][0]["raw_path"] = "note-7/partial-v2.txt"
            updated["representations"][0]["revision"]["digest"] = new_digest
            updated["capture"]["captured_at"] = "2026-03-04T05:06:07Z"
            updated["capture"]["converter"]["version"] = "2"
            updated["fidelity"]["losses"] = ["paragraphs-1-and-3-omitted", "case-normalized"]
            new_record = {"schema": "kb-bootstrap.source-capture", "version": 1, "sources": [updated]}
            new_path = root / "records" / "new.yaml"
            new_path.write_text(yaml.safe_dump(new_record, sort_keys=False), encoding="utf-8")
            (root / "raw" / "note-7/partial-v2.txt").write_bytes(new_bytes)

            original_digest = source["original_revision"].get("digest")
            self.assertEqual(updated["source_id"], source["source_id"])
            self.assertEqual(updated["original_revision"], source["original_revision"])
            self.assertNotEqual(updated["representations"][0]["revision"]["digest"], old_digest)
            self.assertTrue(validate_source_capture("records/old.yaml", root, "raw", ["note-7/partial.txt"])[0])
            self.assertTrue(validate_source_capture("records/new.yaml", root, "raw", ["note-7/partial-v2.txt"])[0])
            self.assertEqual(old_raw.read_bytes(), old_bytes)
            self.assertEqual(old_path.read_bytes(), old_metadata_bytes)

            bad = deepcopy(new_record)
            bad["sources"][0]["representations"][0]["revision"]["digest"] = hashlib.sha256(b"stale bytes\n").hexdigest()
            bad_path = root / "records" / "bad.yaml"
            bad_path.write_text(yaml.safe_dump(bad, sort_keys=False), encoding="utf-8")
            invalid, errors = validate_source_capture("records/bad.yaml", root, "raw", ["note-7/partial-v2.txt"])
            self.assertFalse(invalid)
            self.assertIn("digest", errors[0])
            self.assertEqual(original_digest, source["original_revision"].get("digest"))

    def test_study_references_reuse_capture_identity_without_claiming_corroboration(self):
        record = self.load_complete_record(Path(tempfile.mkdtemp()))
        source = record["sources"][0]
        capture_identity = (source["source_id"], source["representations"][0]["representation_id"],
                            source["representations"][0]["revision"]["digest"])
        studies = [
            {"study_id": "study-a", "source_ref": capture_identity},
            {"study_id": "study-b", "source_ref": capture_identity},
        ]
        self.assertEqual(studies[0]["source_ref"], studies[1]["source_ref"])
        self.assertEqual(studies[0]["source_ref"][0], source["source_id"])
        self.assertNotIn("corroboration_count", studies[0])
        self.assertNotIn("corroboration_count", studies[1])
