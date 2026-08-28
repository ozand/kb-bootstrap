import unittest
from pathlib import Path


DOCUMENT = Path("docs/LESSON_IDENTITY_RESEARCH.md")


class LessonIdentityResearchTests(unittest.TestCase):
    def test_research_compares_required_alternatives_and_dimensions(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        for alternative in (
            "Local IDs + explicit owner/provenance",
            "Namespaced stored ID",
            "UUID",
            "ULID",
            "Central/distributed numeric allocator",
        ):
            self.assertIn(alternative, text)
        for dimension in (
            "Collision risk",
            "Traceability",
            "Migration cost",
            "Compatibility",
            "Coordination cost",
        ):
            self.assertIn(dimension, text)

    def test_existing_ids_and_provenance_are_explicitly_evaluated(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        self.assertIn("(scope, owner repository, lesson ID)", text)
        self.assertIn("## Interoperability, federation, and export evaluation", text)
        self.assertIn("### External interchange", text)
        self.assertIn("source_repository", text)
        self.assertIn("promoted_from", text)
        self.assertIn("A consumer must not merge results by lesson ID alone", text)

    def test_recommendation_and_measurable_threshold_are_present(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        self.assertIn("## Go/no-go threshold", text)
        self.assertIn("Two confirmed, sanitized incidents within 12 months", text)
        self.assertIn("**No-go for global ID implementation now.**", text)

    def test_evidence_limitations_and_rename_handling_are_explicit(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        self.assertIn("## Evidence base and limitations", text)
        self.assertIn("No confirmed sanitized incident", text)
        self.assertIn("agent-maintained wiki systems", text)
        self.assertIn("Repository renames or transfers", text)
        self.assertIn("explicit bounded alias mapping", text)
        self.assertIn("fail closed rather than be repaired by guessing", text)

    def test_research_does_not_authorize_implementation_or_migration(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        self.assertIn("## Non-actions", text)
        self.assertIn("does not", text)
        self.assertIn("change `PROJECT-XXXX` or `KB-XXXX`", text)
        self.assertIn("migrate lessons or indexes", text)
        self.assertIn("introduce a service", text)


if __name__ == "__main__":
    unittest.main()
