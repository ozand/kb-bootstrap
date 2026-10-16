import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / "kb_bootstrap/templates/skills/market-research/scripts"


class LocalStudyWorkflowE2ETests(unittest.TestCase):
    def run_script(self, name, *args, cwd):
        return subprocess.run(
            [sys.executable, str(SKILL_SCRIPTS / name), *map(str, args)],
            cwd=cwd, capture_output=True, text=True, check=False,
        )

    def test_local_study_import_review_and_filled_report_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kb = root / "kb"
            (kb / "wiki/concepts").mkdir(parents=True)
            (kb / "wiki/entities").mkdir()
            (kb / "wiki/reports").mkdir()
            created = self.run_script(
                "new_research.py", "synthetic-study", "--title", "Synthetic local study",
                "--kb", kb, cwd=root,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            study = root / created.stdout.strip()
            self.assertTrue((study / "brief.md").is_file())
            brief = (study / "brief.md").read_text(encoding="utf-8")
            brief = brief.replace("1. <!-- what exactly to find out -->",
                                  "1. Does the supplied local capture document feature X?")
            brief = brief.replace("Products / sources (priority first): <!-- names; add notable ones found on the way -->",
                                  "Products / sources (priority first): Synthetic Product, supplied local capture")
            brief = brief.replace("Out of scope: <!-- what is deliberately not studied -->",
                                  "Out of scope: live product behavior and external sources")
            (study / "brief.md").write_text(brief, encoding="utf-8")

            input_root = root / "provided"
            input_root.mkdir()
            source = input_root / "source.md"
            raw = (
                "---\n"
                "type: RawCapture\n"
                'title: "Synthetic Product feature notes"\n'
                'url: "https://example.test/local-snapshot"\n'
                'captured_at: "2026-10-16T10:00:00+00:00"\n'
                'captured_by: "synthetic-fixture"\n'
                'entity: "synthetic-product"\n'
                "fidelity: full\n"
                "---\n\n# Synthetic Product\n\nFeature X is documented in this supplied snapshot.\n"
            ).encode("utf-8")
            source.write_bytes(raw)
            source_digest = hashlib.sha256(raw).hexdigest()

            imported = self.run_script(
                "import_local_capture.py", study, "--input-root", input_root,
                "--input", "source.md", "--destination", "001-synthetic-product.md",
                cwd=root,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertIn("IMPORTED: raw/001-synthetic-product.md", imported.stdout)
            capture = study / "raw/001-synthetic-product.md"
            self.assertEqual(capture.read_bytes(), raw)
            self.assertEqual(hashlib.sha256(capture.read_bytes()).hexdigest(), source_digest)
            self.assertEqual(source.read_bytes(), raw)

            concept = kb / "wiki/concepts/feature-x.md"
            concept.write_text("---\ntype: Concept\ntitle: Feature X\n---\n# Feature X\n", encoding="utf-8")
            report = kb / "wiki/reports" / f"{study.name}.md"
            report.write_text(
                f"---\ntype: Report\ntitle: Synthetic local study\n---\n"
                f"# Synthetic local study\n"
                f"Brief: [brief](../../research/{study.name}/brief.md).\n"
                "Question/scope: feature X in the supplied synthetic snapshot only.\n"
                f"Selected source: [RawCapture](../../research/{study.name}/raw/001-synthetic-product.md).\n"
                "Finding: feature X is documented in the supplied snapshot. "
                "Unsupported claim: live UI behavior was not observed. "
                "Limitations: one synthetic local source; no external validation. "
                "Remaining work: inspect an independent source if authorized.\n"
                "Concept: [Feature X](../concepts/feature-x.md).\n",
                encoding="utf-8",
            )
            checked = self.run_script("check_research.py", study, "--kb", kb,
                                      "--min-screenshots", "0", "--skip-validate", cwd=root)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("OK", checked.stdout.splitlines()[-1])
            self.assertIn("raw pages: 1", checked.stdout)
            rendered_report = report.read_text(encoding="utf-8")
            for required in ("Question/scope:", "Selected source:", "Finding:",
                             "Unsupported claim:", "Limitations:", "Remaining work:"):
                self.assertIn(required, rendered_report)
            self.assertEqual(source.read_bytes(), raw)

            invalid_report = report.read_text(encoding="utf-8").replace(
                "../concepts/feature-x.md", "../concepts/missing-concept.md")
            report.write_text(invalid_report, encoding="utf-8")
            invalid = self.run_script("check_research.py", study, "--kb", kb,
                                      "--min-screenshots", "0", "--skip-validate", cwd=root)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("missing-concept.md", invalid.stdout + invalid.stderr)
            report.write_text(rendered_report, encoding="utf-8")

            blocked = self.run_script(
                "import_local_capture.py", study, "--input-root", input_root,
                "--input", "source.md", "--destination", "001-synthetic-product.md",
                cwd=root,
            )
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("BLOCKED", blocked.stdout)
            self.assertEqual(capture.read_bytes(), raw)

            # check_research.py validates structure/links, not semantic completeness;
            # the assertions above only establish this fixture includes the listed fields.


if __name__ == "__main__":
    unittest.main()
