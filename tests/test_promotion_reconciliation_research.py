import unittest
from pathlib import Path


DOCUMENT = Path("docs/PROMOTION_RECONCILIATION_RESEARCH.md")


class PromotionReconciliationResearchTests(unittest.TestCase):
    def test_failure_taxonomy_covers_every_promotion_stage(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        for stage in (
            "Source selection",
            "Candidate preparation",
            "Review",
            "Destination preflight",
            "Destination branch/commit",
            "Push",
            "Pull request",
            "Merge",
            "Destination validation",
            "Receipt recording",
            "Source retention",
            "Source retraction",
            "Authorization changes",
        ):
            self.assertIn(stage, text)
        self.assertIn("no confirmed sanitized incident", text)
        self.assertIn("result count was zero", text)
        self.assertIn("This is an evidence limitation and not proof", text)

    def test_options_compare_receipts_reconciliation_compensation_and_transactions(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        for option in (
            "Current manual workflow and minimal receipt",
            "Idempotent operation receipt plus read-only reconciliation",
            "Explicit compensating actions",
            "Automatic saga/orchestrator",
            "Distributed transaction/two-phase commit",
        ):
            self.assertIn(option, text)
        self.assertIn("## State model for reconciliation", text)
        self.assertIn("## Illustrative future receipt profile (not a supported contract)", text)
        self.assertIn("not an accepted schema, public contract, implementation authorization, or ADR decision", text)
        self.assertIn("## Compensating actions", text)

    def test_security_authorization_replay_and_isolation_are_explicit(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        for heading in (
            "### Authorization",
            "### Replay",
            "### Data and privacy",
            "### Failure isolation",
        ):
            self.assertIn(heading, text)
        self.assertIn("historical receipt cannot grant current access", text)
        self.assertIn("Unknown remote state is a blocking state", text)
        self.assertIn("One operation writes to one owner at a time", text)

    def test_measurable_thresholds_default_against_distributed_transactions(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        self.assertIn("rolling 12-month periods", text)
        self.assertIn("A confirmed incident is one unique sanitized incident record", text)
        self.assertIn("Missing measurements make a threshold not evaluable", text)
        self.assertIn("At least two confirmed sanitized promotion incidents within 12 months", text)
        self.assertIn("more than two authoritative systems", text)
        self.assertIn("at least five confirmed partial-commit incidents", text)
        self.assertIn("greater than 40 maintainer-hours", text)
        self.assertIn("conditions below are conjunctive", text)
        self.assertIn("Absent all these conditions, distributed transactions remain a no-go", text)
        self.assertIn("**No-go for distributed transactions", text)

    def test_research_does_not_implement_or_authorize_mutation(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        self.assertIn("## Non-actions", text)
        self.assertIn("does not", text)
        self.assertIn("add or change a supported receipt schema", text)
        self.assertIn("implement a reconciler, coordinator, saga, lock, or transaction service", text)
        self.assertIn("write to project, shared, cache, candidate, or consumer stores", text)
        self.assertIn("create background work or synchronization", text)


if __name__ == "__main__":
    unittest.main()
