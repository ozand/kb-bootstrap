"""Characterize the generated market-research report across existing gates."""
import contextlib
import hashlib
import os
import io
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
            rendered += "\nSynthetic capture recorded.\n\n[concept](../concepts/product.md)\n"
            report.write_text(rendered, encoding="utf-8")
            concept = root / "wiki/concepts/product.md"
            concept.parent.mkdir(parents=True)
            concept.write_text(CONCEPT, encoding="utf-8")
            project_collections = workspace / "qmd/collections"
            project_collections.mkdir(parents=True)
            (project_collections / "wiki.yaml").write_text(
                "name: synthetic-wiki\npaths:\n  - ../../kb/wiki/\n", encoding="utf-8"
            )
            (project_collections / "raw.yaml").write_text(
                "name: synthetic-raw\npaths:\n  - ../../kb/research/\n", encoding="utf-8"
            )
            outside = root / "outside.md"
            outside.write_text(
                "---\ntype: Concept\ntitle: Workflow control\ndescription: Positive retrieval control.\n"
                "tags: [synthetic]\nstatus: stable\n---\nSynthetic study retrieval control.\n",
                encoding="utf-8",
            )

            before = {
                path.relative_to(workspace).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in workspace.rglob("*") if path.is_file()
            }
            checker_script = assets / "scripts/check_research.py"
            checker_globals = runpy.run_path(str(checker_script), run_name="synthetic_check_research")
            checker_module = SimpleNamespace(**checker_globals)
            validator_runs = []
            source_root = str(package)
            environment = os.environ.copy()
            environment["PYTHONPATH"] = source_root + os.pathsep + environment.get("PYTHONPATH", "")
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            actual_run = subprocess.run

            def run_validator(args, **kwargs):
                result = actual_run(
                    [sys.executable, "-m", "kb_bootstrap.cli", *args[1:]],
                    cwd=workspace, env=environment, capture_output=True, text=True, check=False,
                )
                validator_runs.append((args, result.returncode, result.stdout, result.stderr))
                return result

            checker_output = io.StringIO()
            with patch.object(checker_module.shutil, "which", return_value="kb-bootstrap"), patch.object(
                checker_module.subprocess, "run", side_effect=run_validator
            ), patch.object(sys, "argv", [
                     "check_research.py", str(study), "--kb", str(root),
                     "--min-screenshots", "0",
                 ]), contextlib.redirect_stdout(checker_output):
                checker_exit = checker_module.main()
            checker = SimpleNamespace(
                returncode=checker_exit, stdout=checker_output.getvalue(), stderr=""
            )
            self.assertEqual(len(validator_runs), 1)
            self.assertEqual(validator_runs[0][0][1:3], ["validate", "--dir"])
            self.assertEqual(validator_runs[0][1], 0, validator_runs[0][2] + validator_runs[0][3])
            profile, profile_ok = validate_canonical_profile(root)
            graph, _ = analyze_graph(root)
            lint_report, lint_ok = validate(root)
            graph_data, graph_report, graph_ok = build_canonical_graph(root)
            bundle, bundle_report, bundle_ok = build_published_bundle(root)
            report_results, report_code = search_local("Synthetic characterization report", root)
            brief_results, brief_code = search_local("Synthetic study", root)
            after = {
                path.relative_to(workspace).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in workspace.rglob("*") if path.is_file()
            }

            brief_path = brief.relative_to(root).as_posix()
            report_path = report.relative_to(root).as_posix()
            concept_path = concept.relative_to(root).as_posix()
            outside_path = outside.relative_to(root).as_posix()
            self.assertEqual(checker.returncode, 0, checker.stdout + checker.stderr)
            self.assertIn("OK", checker.stdout)
            self.assertTrue(profile_ok, profile)
            self.assertIn("ERRORS: 0", profile)
            self.assertTrue(lint_ok, lint_report)
            self.assertIn((report_path, brief_path), graph.edges)
            self.assertEqual({brief_path, report_path, concept_path, outside_path}, set(graph.nodes))
            self.assertTrue(graph_ok, graph_report)
            graph_value = json.loads(graph_data)
            self.assertIn({"source": report_path, "target": brief_path, "fragment": None}, graph_value["edges"])
            self.assertTrue(bundle_ok, bundle_report)
            with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
                self.assertIn(brief_path, archive.namelist())
                self.assertIn(report_path, archive.namelist())
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
