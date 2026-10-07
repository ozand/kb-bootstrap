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
            self.assertIn("every exact representation", errors[0])

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
