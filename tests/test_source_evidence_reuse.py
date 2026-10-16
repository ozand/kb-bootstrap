import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from kb_bootstrap.source_evidence_reuse import reuse_source_evidence


class SourceEvidenceReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "kb/research/source-study/raw").mkdir(parents=True)
        self.payload = b"# Existing captured page\nEvidence text.\n"
        (self.root / "kb/research/source-study/raw/page.md").write_bytes(self.payload)
        self.metadata = self.root / "source-capture.yaml"
        digest = hashlib.sha256(self.payload).hexdigest()
        self.record = {
            "schema": "kb-bootstrap.source-capture", "version": 1,
            "sources": [{
                "source_id": "stable-source-1",
                "origin": {"kind": "opaque-owner-reference", "reference": "PRIVATE-ORIGIN"},
                "original_revision": {"algorithm": "sha256", "digest": digest, "media_type": "text/markdown"},
                "original_retention": "retained",
                "capture": {
                    "method": "converted", "captured_at": "2026-10-15T12:34:56Z",
                    "converter": {"identity": "synthetic-selector", "version": "2", "parameters": {"mode": "excerpt", "range": [2, 4]}},
                },
                "fidelity": {"class": "exact", "coverage": "all-bytes", "losses": []},
                "representations": [{
                    "representation_id": "representation-1",
                    "revision": {"algorithm": "sha256", "digest": digest},
                    "media_type": "text/markdown", "raw_path": "research/source-study/raw/page.md", "retention": "retained",
                }],
            }],
        }
        self.metadata.write_text(yaml.safe_dump(self.record, sort_keys=False), encoding="utf-8")
        self.selected = ["research/source-study/raw/page.md"]

    def _reuse(self):
        return reuse_source_evidence(self.root, "source-capture.yaml", "kb", "stable-source-1", self.selected)

    def test_two_persisted_studies_reuse_the_same_declared_identity_and_time(self):
        studies = self.root / "kb/research"
        for name in ("study-a", "study-b"):
            folder = studies / name
            folder.mkdir(parents=True)
            (folder / "report.md").write_text(
                "# Synthetic study\n\nEvidence: [captured page](../source-study/raw/page.md)\n",
                encoding="utf-8",
            )
        results = [self._reuse(), self._reuse()]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["source_id"], "stable-source-1")
        self.assertEqual(results[0]["representations"][0]["representation_id"], "representation-1")
        self.assertEqual(results[0]["capture"], self.record["sources"][0]["capture"])
        self.assertEqual(results[0]["capture"]["converter"]["parameters"], {"mode": "excerpt", "range": [2, 4]})
        self.assertEqual(results[0]["capture"]["captured_at"], "2026-10-15T12:34:56Z")
        self.assertEqual(results[0]["original_revision"], self.record["sources"][0]["original_revision"])
        self.assertEqual(results[0]["status"], "AVAILABLE")
        rendered = repr(results[0])
        self.assertNotIn("PRIVATE-ORIGIN", rendered)
        self.assertNotIn("Evidence text", rendered)
        for name in ("study-a", "study-b"):
            report = studies / name / "report.md"
            self.assertIn("../source-study/raw/page.md", report.read_text(encoding="utf-8"))

    def test_legacy_rawcapture_is_not_promoted_from_descriptive_fields(self):
        result = reuse_source_evidence(self.root, None, "raw", "source-from-url-or-hash", [])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertNotIn("source_id", result)
        self.assertNotIn("representations", result)

    def test_invalid_complete_member_set_blocks(self):
        (self.root / "kb/research/source-study/raw/page.md").write_bytes(b"changed bytes\\n")
        result = self._reuse()
        self.assertEqual(result["status"], "BLOCKED")

    def test_read_only_and_no_discovery(self):
        paths = [self.metadata, self.root / "kb/research/source-study/raw/page.md"]
        before = [path.read_bytes() for path in paths]
        with patch("os.scandir", side_effect=AssertionError("discovery")), patch(
            "os.listdir", side_effect=AssertionError("discovery")
        ):
            result = self._reuse()
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual([path.read_bytes() for path in paths], before)

    def test_missing_timestamp_stays_unknown(self):
        del self.record["sources"][0]["capture"]["captured_at"]
        self.metadata.write_text(yaml.safe_dump(self.record, sort_keys=False), encoding="utf-8")
        result = self._reuse()
        self.assertNotIn("captured_at", result["capture"])
