"""Characterize the generated market-research report across existing gates."""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.canonical_graph_export import build_canonical_graph
from kb_bootstrap.canonical_profile import validate_canonical_profile
from kb_bootstrap.graph_linter import analyze_graph, validate
from kb_bootstrap.local_retrieval import search_local
from kb_bootstrap.published_bundle_export import build_published_bundle

CONCEPT = (
    "---\ntype: Concept\ntitle: Product\ndescription: Synthetic concept.\n"
    "tags: [synthetic]\nstatus: stable\n---\nSynthetic product marker.\n"
)
RAW = (
    "---\ntype: RawCapture\nurl: https://example.invalid/docs\n"
    "captured_at: 2026-10-07T00:00:00Z\nfidelity: full\n---\n"
    "Synthetic evidence.\n"
)


class GeneratedResearchReportTests(unittest.TestCase):
    def test_rendered_report_checker_and_readonly_tool_outcomes(self):
        package = Path(__file__).parents[1]
        assets = package / "kb_bootstrap/templates/skills/market-research"
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "kb"
            (root / "wiki").mkdir(parents=True)
            creator = assets / "scripts/new_research.py"
            created = subprocess.run(
                [sys.executable, str(creator), "synthetic-study", "--title",
                 "Synthetic study", "--kb", str(root)],
                cwd=workspace, capture_output=True, text=True, check=True,
            )
            study = Path(created.stdout.strip())
            brief = study / "brief.md"
            raw = study / "raw/001-docs.md"
            raw.write_text(RAW, encoding="utf-8")
            report = root / "wiki/reports" / f"{study.name}.md"
            report.parent.mkdir(parents=True)
            template = (assets / "assets/report-template.md").read_text(encoding="utf-8")
            rendered = template.replace("<title>", "Synthetic study")
            rendered = rendered.replace(
                "<one sentence: what was studied and the main conclusion>",
                "Synthetic characterization report",
            )
            rendered = rendered.replace(
                "../../research/<YYYY-MM-DD>_<slug>/brief.md",
                "../../" + brief.relative_to(root).as_posix(),
            )
            rendered += (
                "\nSynthetic sources: [capture](../../" + raw.relative_to(root).as_posix()
                + ")\n\n[concept](../../wiki/concepts/product.md)\n"
            )
            report.write_text(rendered, encoding="utf-8")
            concept = root / "wiki/concepts/product.md"
            concept.parent.mkdir(parents=True)
            concept.write_text(CONCEPT, encoding="utf-8")
            outside = root / "outside.md"
            outside.write_text(
                "---\ntype: Concept\ntitle: Workflow control\ndescription: Positive retrieval control.\n"
                "tags: [synthetic]\nstatus: stable\n---\nSynthetic study retrieval control.\n",
                encoding="utf-8",
            )

            before = {
                path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob("*") if path.is_file()
            }
            checker = subprocess.run(
                [sys.executable, str(assets / "scripts/check_research.py"), str(study),
                 "--kb", str(root), "--min-screenshots", "0", "--skip-validate"],
                cwd=workspace, capture_output=True, text=True, check=False,
            )
            profile, profile_ok = validate_canonical_profile(root)
            graph, _ = analyze_graph(root)
            _, lint_ok = validate(root)
            graph_data, graph_report, graph_ok = build_canonical_graph(root)
            bundle, bundle_report, bundle_ok = build_published_bundle(root)
            report_results, report_code = search_local("Synthetic characterization report", root)
            brief_results, brief_code = search_local("Synthetic study", root)
            after = {
                path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob("*") if path.is_file()
            }

            brief_path = brief.relative_to(root).as_posix()
            report_path = report.relative_to(root).as_posix()
            concept_path = concept.relative_to(root).as_posix()
            outside_path = outside.relative_to(root).as_posix()
            self.assertEqual(checker.returncode, 0, checker.stdout + checker.stderr)
            self.assertIn("OK", checker.stdout)
            self.assertTrue(profile_ok is False)
            self.assertIn(f"{brief_path}: status must be draft, stable, or deprecated", profile)
            self.assertTrue(lint_ok)
            self.assertEqual({brief_path, report_path, concept_path, outside_path}, set(graph.nodes))
            self.assertFalse(graph_ok)
            self.assertEqual(graph_data, b"")
            self.assertIn("status must be draft, stable, or deprecated", graph_report)
            self.assertFalse(bundle_ok)
            self.assertEqual(bundle, b"")
            self.assertIn("status must be draft, stable, or deprecated", bundle_report)
            self.assertEqual(report_code, 0)
            self.assertIn(report_path, {row["path"] for row in report_results["results"]})
            self.assertEqual(brief_code, 0)
            self.assertIn("Synthetic study", brief.read_text(encoding="utf-8"))
            brief_hits = {row["path"] for row in brief_results["results"]}
            self.assertNotIn(brief_path, brief_hits)
            self.assertIn(outside_path, brief_hits)
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
