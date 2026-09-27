import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.cli import main
from kb_bootstrap.qmd_validator import validate_qmd_collections

SKILL = Path("kb_bootstrap/templates/skills/market-research")
SCRIPTS = SKILL / "scripts"


def run_script(name, *args, cwd=None):
    return subprocess.run(
        [sys.executable, str((SCRIPTS / name).resolve()), *args],
        capture_output=True, text=True, cwd=cwd, check=False,
    )


class MarketResearchPackagingTests(unittest.TestCase):
    def test_skill_files_follow_agent_skills_layout(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: market-research\n"))
        self.assertLess(len(text.splitlines()), 500)
        for ref in ["sources", "feature-matrix", "technology", "ux-patterns",
                    "positioning", "jtbd-cjm", "parallel-studies", "formats"]:
            self.assertTrue((SKILL / "references" / f"{ref}.md").is_file(), ref)
            self.assertIn(f"references/{ref}.md", text)
        for asset in ["brief-template.md", "report-template.md"]:
            self.assertTrue((SKILL / "assets" / asset).is_file())
        evals = json.loads((SKILL / "evals/evals.json").read_text(encoding="utf-8"))
        self.assertEqual(evals["skill_name"], "market-research")
        self.assertGreaterEqual(len(evals["evals"]), 2)

    def test_skill_is_project_neutral(self):
        for path in SKILL.rglob("*"):
            if path.is_file():
                content = path.read_text(encoding="utf-8").lower()
                self.assertNotIn("audiotext", content, str(path))

    def test_extractor_avoids_surf_mangled_syntax(self):
        js = (SCRIPTS / "extract_markdown.js").read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
        for forbidden in ["`", "#", "$"]:
            self.assertNotIn(forbidden, code)


class MarketResearchScaffoldTests(unittest.TestCase):
    def test_single_installs_skill_tree_and_research_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(sys, "argv", ["kb-bootstrap", "--target", directory, "--type", "single"]):
                main()
            skill = root / ".agents/skills/market-research"
            self.assertTrue((skill / "SKILL.md").is_file())
            self.assertTrue((skill / "scripts/capture_page.py").is_file())
            self.assertTrue((skill / "scripts/extract_markdown.js").is_file())
            self.assertTrue((skill / "assets/brief-template.md").is_file())
            self.assertFalse(list(skill.rglob("__pycache__")))
            for folder in ["kb/research", "kb/wiki/entities", "kb/wiki/concepts", "kb/wiki/reports"]:
                self.assertTrue((root / folder).is_dir(), folder)
            raw = (root / "qmd/collections/raw.yaml").read_text(encoding="utf-8")
            wiki = (root / "qmd/collections/wiki.yaml").read_text(encoding="utf-8")
            self.assertIn("../../kb/research/", raw)
            self.assertIn('"research/**"', wiki)
            _, valid = validate_qmd_collections(root)
            self.assertTrue(valid)


class MarketResearchScriptTests(unittest.TestCase):
    def make_study(self, root):
        (root / "kb/wiki/reports").mkdir(parents=True)
        (root / "kb/wiki/concepts").mkdir(parents=True)
        out = run_script("new_research.py", "Search Patterns", "--title", "Search patterns", cwd=root)
        self.assertEqual(out.returncode, 0, out.stderr)
        return root / out.stdout.strip()

    def test_new_research_fills_brief_template_and_refuses_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            study = self.make_study(Path(directory))
            brief = (study / "brief.md").read_text(encoding="utf-8")
            self.assertIn('title: "Search patterns"', brief)
            self.assertIn("## Dimensions", brief)
            self.assertTrue((study / "raw/img").is_dir())
            again = run_script("new_research.py", "Search Patterns", "--title", "x", cwd=directory)
            self.assertNotEqual(again.returncode, 0)

    def test_grep_claim_and_check_research(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            study = self.make_study(root)
            (study / "raw/001-product-a-search.md").write_text(
                '---\ntype: RawCapture\ntitle: "A"\nurl: "https://help.a.com/search"\n'
                "captured_at: 2026-01-01T00:00:00+00:00\ncaptured_by: \"t\"\nentity: \"a\"\n"
                "fidelity: full\n---\n\nSearch across all transcripts with filters.\n",
                encoding="utf-8",
            )
            found = run_script("grep_claim.py", str(study), "filters")
            self.assertEqual(found.returncode, 0)
            self.assertIn("001-product-a-search.md", found.stdout)
            missing = run_script("grep_claim.py", str(study), "voice enrollment")
            self.assertEqual(missing.returncode, 1)
            self.assertIn("NOT FOUND", missing.stdout)

            kb = str(root / "kb")
            failing = run_script("check_research.py", str(study), "--kb", kb, "--skip-validate")
            self.assertEqual(failing.returncode, 1)
            self.assertIn("report", failing.stdout)

            concept = root / "kb/wiki/concepts/search.md"
            concept.write_text("---\ntype: Concept\n---\n# S\n", encoding="utf-8")
            (root / f"kb/wiki/reports/{study.name}.md").write_text(
                f"---\ntype: Report\n---\n# R\n[brief](../../research/{study.name}/brief.md) "
                f"[c](../concepts/search.md) "
                f"[raw](../../research/{study.name}/raw/001-product-a-search.md)\n",
                encoding="utf-8",
            )
            ok = run_script("check_research.py", str(study), "--kb", str(root / "kb"),
                            "--min-screenshots", "0", "--skip-validate")
            self.assertIn("OK", ok.stdout.splitlines()[-1], ok.stdout)


if __name__ == "__main__":
    unittest.main()
