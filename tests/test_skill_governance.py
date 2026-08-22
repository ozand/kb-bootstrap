import unittest
from pathlib import Path


SKILLS_ROOT = Path("kb_bootstrap/templates/skills")
SKILLS = ["kb-capture", "kb-lookup", "kb-wiki-builder", "qmd-operator"]


class SkillGovernanceTests(unittest.TestCase):
    def test_all_packaged_skills_require_shared_governance_checks(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                content = (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("## Repository governance gate", content)
                self.assertIn("kb-bootstrap doctor --repo <owner/repository>", content)
                self.assertIn("RESULT: OK", content)
                self.assertIn("kb-bootstrap check-completion --repo <owner/repository>", content)
                self.assertRegex(content, r"separate verified checkout(?:/| or )worktree")

    def test_skills_fail_closed_and_distinguish_consumer_upstream(self):
        capture = (SKILLS_ROOT / "kb-capture/SKILL.md").read_text(encoding="utf-8")
        lookup = (SKILLS_ROOT / "kb-lookup/SKILL.md").read_text(encoding="utf-8")
        wiki = (SKILLS_ROOT / "kb-wiki-builder/SKILL.md").read_text(encoding="utf-8")
        qmd = (SKILLS_ROOT / "qmd-operator/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("consumer-owned", capture)
        self.assertIn("Stop on missing or mismatched evidence", capture)
        self.assertIn("consumer repository from an upstream/shared repository", lookup)
        self.assertIn("fail closed", lookup)
        self.assertIn("consumer-owned knowledge", wiki)
        self.assertIn("fail closed", wiki)
        self.assertIn("consumer-owned work", qmd)
        self.assertIn("stop unless", qmd)

    def test_qmd_dual_collection_guidance_is_preserved(self):
        qmd = (SKILLS_ROOT / "qmd-operator/SKILL.md").read_text(encoding="utf-8")
        wiki = (SKILLS_ROOT / "kb-wiki-builder/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("<project>-wiki", qmd)
        self.assertIn("<project>-raw", qmd)
        self.assertIn("qmd update", qmd)
        self.assertIn("<project>-wiki", wiki)
        self.assertIn("<project>-raw", wiki)
        self.assertIn("kb-bootstrap validate --dir kb --project-root .", wiki)


if __name__ == "__main__":
    unittest.main()
