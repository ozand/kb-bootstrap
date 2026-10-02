"""Executable smoke coverage for a small, synthetic domain knowledge base."""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.canonical_graph_export import write_canonical_graph
from kb_bootstrap.canonical_profile import validate_canonical_profile
from kb_bootstrap.canonical_provenance import validate_canonical_provenance
from kb_bootstrap.graph_linter import validate as validate_graph


class DomainKnowledgeBaseSmokeTests(unittest.TestCase):
    """Exercise the existing core validators and canonical graph exporter together."""

    NOW = "2026-09-29T12:00:00Z"

    @staticmethod
    def _write(root: Path, relative: str, content: bytes) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    @staticmethod
    def _snapshot(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    @staticmethod
    def _unexpected_io(*_args, **_kwargs):
        raise AssertionError("core validation/export attempted subprocess or network I/O")

    def test_synthetic_project_management_kb_smoke_path(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            kb = project / "kb"

            planning_bytes = (
                b"# Synthetic planning note P7\n\n"
                b"Northstar has two approval groups for release train 3.\n"
            )
            review_bytes = (
                b"# Synthetic review log R4\n\n"
                b"A prior pilot with separate sessions waited one extra day.\n"
            )
            planning = self._write(kb, "raw/planning-note-p7.md", planning_bytes)
            review = self._write(kb, "raw/review-log-r4.md", review_bytes)

            recommendation = self._write(
                kb,
                "schedule-recommendation.md",
                b"---\n"
                b"type: Recommendation\n"
                b"title: Conditional Northstar review schedule\n"
                b"status: draft\n"
                b"scope: synthetic Northstar pilot, release train 3\n"
                b"conditions:\n"
                b"  - approval groups use separate sessions\n"
                b"sources:\n"
                b"  - resource: raw/planning-note-p7.md\n"
                b"    title: Synthetic planning note P7\n"
                b"  - resource: raw/review-log-r4.md\n"
                b"    title: Synthetic review log R4\n"
                b"verified:\n"
                b"  by: human:test-reviewer\n"
                b"  at: 2026-09-28T09:00:00Z\n"
                b"stale_after: 2026-10-31T00:00:00Z\n"
                b"---\n\n"
                b"# Conditional Northstar review schedule\n\n"
                b"If the two groups use separate sessions, reserve two review days.\n\n"
                b"Evidence is identified by the two local sources in frontmatter.\n\n"
                b"This recommendation uses the [review-session concept](review-session.md).\n",
            )
            evidence_index = self._write(
                kb,
                "index.md",
                b"# Evidence navigation\n\n"
                b"[Planning note P7](raw/planning-note-p7.md)\n\n"
                b"[Review log R4](raw/review-log-r4.md)\n",
            )
            concept = self._write(
                kb,
                "review-session.md",
                b"---\n"
                b"type: Concept\n"
                b"title: Review session\n"
                b"status: stable\n"
                b"sources:\n"
                b"  - resource: raw/planning-note-p7.md\n"
                b"---\n\n"
                b"# Review session\n\n"
                b"A synthetic scheduling unit used by an approval group.\n\n"
                b"See the [conditional recommendation](schedule-recommendation.md).\n",
            )

            self.assertNotEqual(planning_bytes, review_bytes)
            self.assertNotEqual(
                hashlib.sha256(planning_bytes).digest(),
                hashlib.sha256(review_bytes).digest(),
            )
            before = self._snapshot(project)

            with patch.object(subprocess, "run", side_effect=self._unexpected_io), \
                 patch.object(subprocess, "Popen", side_effect=self._unexpected_io), \
                 patch.object(socket, "create_connection", side_effect=self._unexpected_io), \
                 patch.object(socket.socket, "connect", side_effect=self._unexpected_io):
                profile_report, profile_valid = validate_canonical_profile(kb)
                provenance_report, provenance_valid = validate_canonical_provenance(
                    kb, self.NOW
                )
                graph_report, graph_valid = validate_graph(kb)

                self.assertTrue(profile_valid, profile_report)
                self.assertIn("Concept files: 2", profile_report)
                self.assertTrue(provenance_valid, provenance_report)
                self.assertIn("Sources: present=2 absent=0 invalid=0", provenance_report)
                self.assertIn("Freshness: fresh=1 stale=0 unknown=1 invalid=0", provenance_report)
                self.assertTrue(graph_valid, graph_report)
                self.assertIn("EVIDENCE LINKS (to raw/ captures): 2", graph_report)
                self.assertIn("DEAD LINKS: 0", graph_report)
                self.assertEqual(self._snapshot(project), before)

                export_report, export_valid = write_canonical_graph(
                    project, "kb", "canonical-graph.json"
                )

            self.assertTrue(export_valid, export_report)
            after_export = self._snapshot(project)
            self.assertEqual(
                set(after_export) - set(before), {"canonical-graph.json"}
            )
            self.assertEqual(
                {path: after_export[path] for path in before}, before
            )
            self.assertEqual(planning.read_bytes(), planning_bytes)
            self.assertEqual(review.read_bytes(), review_bytes)
            self.assertEqual(recommendation.read_bytes(), before["kb/schedule-recommendation.md"])
            self.assertEqual(concept.read_bytes(), before["kb/review-session.md"])
            self.assertEqual(evidence_index.read_bytes(), before["kb/index.md"])

            artifact = json.loads(after_export["canonical-graph.json"])
            self.assertEqual(
                [node["path"] for node in artifact["nodes"]],
                ["review-session.md", "schedule-recommendation.md"],
            )
            self.assertEqual(
                artifact["edges"],
                [
                    {
                        "source": "review-session.md",
                        "target": "schedule-recommendation.md",
                        "fragment": None,
                    },
                    {
                        "source": "schedule-recommendation.md",
                        "target": "review-session.md",
                        "fragment": None,
                    },
                ],
            )

            review.unlink()
            with patch.object(subprocess, "run", side_effect=self._unexpected_io), \
                 patch.object(subprocess, "Popen", side_effect=self._unexpected_io), \
                 patch.object(socket, "create_connection", side_effect=self._unexpected_io), \
                 patch.object(socket.socket, "connect", side_effect=self._unexpected_io):
                missing_report, missing_valid = validate_graph(kb)

            self.assertFalse(missing_valid)
            self.assertIn("raw/review-log-r4.md", missing_report)
            self.assertIn("DEAD LINKS (1):", missing_report)


if __name__ == "__main__":
    unittest.main()
