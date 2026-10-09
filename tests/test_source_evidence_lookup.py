import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from kb_bootstrap.source_evidence_lookup import lookup_source_evidence


class SourceEvidenceLookupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw"
        self.raw.mkdir()
        self.metadata = self.root / "record.yaml"
        self.payloads = {
            "a.txt": b"alpha\n",
            "a-copy.txt": b"alpha\n",
            "partial.txt": b"paragraph two\n",
            "summary.md": b"Summary.\n",
            "empty.txt": b"",
        }
        for name, data in self.payloads.items():
            (self.raw / name).write_bytes(data)
        self.record = self._record()
        self._write()

    def _record(self):
        d = lambda name: hashlib.sha256(self.payloads[name]).hexdigest()
        return {
            "schema": "kb-bootstrap.source-capture",
            "version": 1,
            "sources": [
                {
                    "source_id": "source-a",
                    "origin": {"kind": "opaque-owner-reference", "reference": "SECRET-ORIGIN"},
                    "original_revision": {"algorithm": "sha256", "digest": d("a.txt")},
                    "original_retention": "retained",
                    "capture": {"method": "direct"},
                    "fidelity": {"class": "exact", "coverage": "all-bytes", "losses": []},
                    "representations": [
                        {"representation_id": "rep-a", "revision": {"algorithm": "sha256", "digest": d("a.txt")}, "media_type": "text/plain", "raw_path": "a.txt", "retention": "retained"},
                        {"representation_id": "rep-a-copy", "revision": {"algorithm": "sha256", "digest": d("a-copy.txt")}, "media_type": "text/plain", "raw_path": "a-copy.txt", "retention": "retained"},
                    ],
                },
                {
                    "source_id": "source-partial",
                    "origin": {"kind": "opaque-owner-reference", "reference": "PARTIAL-ORIGIN"},
                    "original_revision": {"opaque": "origin-rev-1", "media_type": "text/plain"},
                    "original_retention": "unknown",
                    "capture": {"method": "converted", "converter": {"identity": "selector", "version": "1"}},
                    "fidelity": {"class": "partial", "coverage": "paragraph-two", "losses": ["other-paragraphs"]},
                    "representations": [
                        {"representation_id": "partial-v1", "revision": {"algorithm": "sha256", "digest": d("partial.txt")}, "media_type": "text/plain", "raw_path": "partial.txt", "retention": "retained"},
                        {"representation_id": "unretained-v1", "revision": {"algorithm": "sha256", "digest": hashlib.sha256(b"not stored").hexdigest()}, "media_type": "text/plain", "raw_path": "never-open.txt", "retention": "reference-only"},
                    ],
                },
                {
                    "source_id": "source-reference-only",
                    "origin": {"kind": "opaque-owner-reference", "reference": "REF-ONLY"},
                    "original_revision": {"opaque": "original-1"},
                    "original_retention": "reference-only",
                    "capture": {"method": "blocked", "reason": "access-not-provided"},
                    "fidelity": {"class": "blocked", "coverage": "none", "losses": ["no-output"]},
                    "representations": [],
                },
                {
                    "source_id": "source-unavailable",
                    "origin": {"kind": "unavailable", "reason": "source-unavailable"},
                    "original_revision": {"opaque": "unknown"},
                    "original_retention": "unknown",
                    "capture": {"method": "blocked", "reason": "origin-unavailable"},
                    "fidelity": {"class": "blocked", "coverage": "none", "losses": ["no-origin"]},
                    "representations": [],
                },
            ],
        }

    def _write(self):
        self.metadata.write_text(yaml.safe_dump(self.record, sort_keys=False), encoding="utf-8")

    def _lookup(self, sid, paths):
        return lookup_source_evidence(self.root, "record.yaml", "raw", sid, paths)

    def test_full_envelope_validated_before_source_filter(self):
        result = self._lookup("source-partial", ["a.txt", "a-copy.txt", "partial.txt"])
        self.assertEqual(result["status"], "AVAILABLE")
        (self.raw / "a-copy.txt").write_bytes(b"corrupt\n")
        blocked = self._lookup("source-partial", ["a.txt", "a-copy.txt", "partial.txt"])
        self.assertEqual(blocked["status"], "BLOCKED")

    def test_result_is_bounded_relative_sorted_and_payload_free(self):
        result = self._lookup("source-a", ["a.txt", "a-copy.txt", "partial.txt"])
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["original_availability"], "original-retained-verified")
        reps = result["representations"]
        self.assertEqual([item["representation_id"] for item in reps], ["rep-a", "rep-a-copy"])
        rendered = repr(result)
        self.assertNotIn("SECRET-ORIGIN", rendered)
        self.assertNotIn("PARTIAL-ORIGIN", rendered)
        self.assertNotIn("alpha", rendered)
        self.assertNotIn(str(self.root), rendered)
        self.assertTrue(all(not Path(item["raw_path"]).is_absolute() for item in reps))
        self.assertNotIn("bytes", result)

    def test_original_retention_requires_declared_retained_and_matching_digest(self):
        result = self._lookup("source-partial", ["a.txt", "a-copy.txt", "partial.txt"])
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["original_availability"], "original-unknown")
        self.assertEqual(result["representations"][0]["availability"], "representation-verified")
        self.assertEqual(result["representations"][1]["availability"], "not-retained")
        self.assertFalse((self.raw / "never-open.txt").exists())

        self.record["sources"][1]["original_revision"] = {
            "algorithm": "sha256", "digest": hashlib.sha256(self.payloads["partial.txt"]).hexdigest()
        }
        self.record["sources"][1]["original_retention"] = "retained"
        self._write()
        retained = self._lookup("source-partial", ["a.txt", "a-copy.txt", "partial.txt"])
        self.assertEqual(retained["original_availability"], "original-retained-verified")

    def test_unavailable_distinguished_from_invalid_retained_input(self):
        result = self._lookup("source-reference-only", ["a.txt", "a-copy.txt", "partial.txt"])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["original_availability"], "original-reference-only")
        self.record["sources"][2]["capture"] = {"method": "manual-summary"}
        self.record["sources"][2]["fidelity"] = {"class": "manual-summary", "coverage": "selected-topics", "losses": ["omitted-topics"]}
        self.record["sources"][2]["representations"] = [
            {"representation_id": "summary-v1", "revision": {"algorithm": "sha256", "digest": hashlib.sha256(self.payloads["summary.md"]).hexdigest()}, "media_type": "text/markdown", "raw_path": "summary.md", "retention": "retained"}
        ]
        self._write()
        summary = self._lookup("source-reference-only", ["a.txt", "a-copy.txt", "partial.txt", "summary.md"])
        self.assertEqual(summary["status"], "AVAILABLE")
        self.assertEqual(summary["original_availability"], "original-reference-only")
        missing_source = self._lookup("absent", ["a.txt", "a-copy.txt", "partial.txt", "summary.md"])
        self.assertEqual(missing_source["status"], "BLOCKED")
        missing_member = self._lookup("source-partial", ["a.txt", "a-copy.txt", "summary.md"])
        self.assertEqual(missing_member["status"], "BLOCKED")
        self.assertEqual(self._lookup("source-unavailable", ["a.txt", "a-copy.txt", "partial.txt", "summary.md"])["origin_reason"], "source-unavailable")

    def test_no_tree_discovery_or_mutation(self):
        before = {path.relative_to(self.root).as_posix(): path.read_bytes() for path in [self.metadata, *[self.raw / name for name in self.payloads]]}
        with patch("os.scandir", side_effect=AssertionError("tree discovery")), patch("os.listdir", side_effect=AssertionError("tree discovery")):
            result = self._lookup("source-a", ["a.txt", "a-copy.txt", "partial.txt"])
        self.assertEqual(result["status"], "AVAILABLE")
        after = {path.relative_to(self.root).as_posix(): path.read_bytes() for path in [self.metadata, *[self.raw / name for name in self.payloads]]}
        self.assertEqual(before, after)
