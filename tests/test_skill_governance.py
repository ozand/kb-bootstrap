import unittest
from pathlib import Path


SKILLS_ROOT = Path("kb_bootstrap/templates/skills")
SKILLS = ["kb-capture", "kb-lookup", "kb-wiki-builder", "qmd-operator"]
ROUTING_POLICY = Path("docs/LESSON_ROUTING_POLICY.md")
PROMOTION_WORKFLOW = Path("docs/LESSON_PROMOTION_WORKFLOW.md")


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

    def test_lesson_skills_have_sanitized_fail_closed_contract(self):
        capture = (SKILLS_ROOT / "kb-capture/SKILL.md").read_text(encoding="utf-8")
        lookup = (SKILLS_ROOT / "kb-lookup/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("all three contract items exist", capture)
        self.assertIn("RESULT: BLOCKED (local lesson contract unavailable)", capture)
        self.assertIn("RESULT: BLOCKED (no lesson stores configured)", lookup)
        self.assertIn("does not imply that a local lesson store exists", lookup)
        self.assertNotIn("T:\\Code", capture)
        self.assertNotIn("T:\\Code", lookup)
        self.assertNotIn(".workspace-kb", capture)
        self.assertNotIn(".workspace-kb", lookup)

    def test_lesson_skills_reference_canonical_routing_policy(self):
        capture = (SKILLS_ROOT / "kb-capture/SKILL.md").read_text(encoding="utf-8")
        lookup = (SKILLS_ROOT / "kb-lookup/SKILL.md").read_text(encoding="utf-8")
        policy_url = "https://github.com/ozand/kb-bootstrap/blob/main/docs/LESSON_ROUTING_POLICY.md"

        self.assertIn(policy_url, capture)
        self.assertIn(policy_url, lookup)
        self.assertIn("normative ownership and routing policy", capture)
        self.assertIn("normative ownership and routing policy", lookup)

    def test_routing_policy_covers_deterministic_ownership_contract(self):
        policy = ROUTING_POLICY.read_text(encoding="utf-8")

        for heading in [
            "### Canonical project knowledge",
            "### Project-scoped lessons",
            "### Workspace-global lessons",
            "### Local-only",
            "### Shared-only lookup",
            "### Local-first with shared fallback",
            "### Ambiguous or conflicting",
        ]:
            self.assertIn(heading, policy)
        self.assertIn("exactly one explicit destination", policy)
        self.assertIn("Automatic dual writes", policy)
        self.assertIn("Automatic dual writes, mirroring, synchronization, and promotion are prohibited", policy)
        self.assertIn("Search a complete explicitly configured local store first", policy)
        self.assertIn("sanitized category and result", policy)

    def test_promotion_workflow_requires_manual_sanitized_single_destination(self):
        workflow = PROMOTION_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("## Promotion: project to workspace", workflow)
        self.assertIn("## Demotion: workspace to project", workflow)
        self.assertIn("explicit approval", workflow)
        self.assertIn("personally identifiable information", workflow)
        self.assertIn("private hostnames", workflow)
        self.assertIn("runtime/session state", workflow)
        self.assertIn("one selected workspace destination", workflow)
        self.assertIn("one selected project destination", workflow)
        self.assertIn("never one cross-store transaction", workflow)
        self.assertIn("### Sanitized promotion fixture", workflow)
        self.assertIn("### Sanitized demotion fixture", workflow)
        self.assertIn("[consumer versus kb-bootstrap upstream contribution workflow](CONTRIBUTING_UPSTREAM.md)", workflow)
        self.assertIn("Issues #4, #6, and #22", workflow)
        self.assertIn("Future Issue #29 may prepare a contribution candidate", workflow)

    def test_promotion_workflow_receipt_is_sanitized_and_verifiable(self):
        workflow = PROMOTION_WORKFLOW.read_text(encoding="utf-8")

        for field in [
            "source_scope",
            "source_lesson_id",
            "destination_scope",
            "destination_owner",
            "destination_lesson_id",
            "reviewer",
            "actor",
            "result",
            "rationale",
        ]:
            self.assertIn(field, workflow)
        self.assertIn("no unintended source mutation or second destination write occurred", workflow)
        self.assertIn("The receipt is evidence of a reviewed result", workflow)

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
