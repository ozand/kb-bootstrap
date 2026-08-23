import unittest

from kb_bootstrap.shared_metadata import validate_metadata


class SharedMetadataTests(unittest.TestCase):
    def test_workspace_metadata_is_valid(self):
        errors, warnings = validate_metadata(
            {
                "scope": "workspace",
                "source_repository": "example/tooling",
                "observed_in": ["example/tooling", "example/application"],
                "promoted_from": {
                    "repository": "example/application",
                    "lesson_id": "PROJECT-0042",
                },
            }
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_project_scope_requires_explicit_applicability(self):
        errors, _ = validate_metadata(
            {
                "scope": "project",
                "source_repository": "example/application",
                "observed_in": ["example/application"],
                "applies_to": [],
            }
        )
        self.assertIn("project scope requires non-empty applies_to", errors)

    def test_invalid_scope_and_private_path_are_rejected(self):
        errors, _ = validate_metadata(
            {
                "scope": "global",
                "source_repository": "C:/private/application",
                "observed_in": ["example/application"],
            }
        )
        self.assertIn("scope must be workspace or project", errors)
        self.assertIn(
            "source_repository must use sanitized owner/repository syntax", errors
        )

    def test_dot_segment_repository_ids_are_rejected(self):
        errors, _ = validate_metadata(
            {
                "scope": "workspace",
                "source_repository": "./..",
                "observed_in": ["example/application"],
            }
        )
        self.assertIn(
            "source_repository must use sanitized owner/repository syntax", errors
        )

    def test_duplicates_and_incomplete_promotion_are_rejected(self):
        errors, _ = validate_metadata(
            {
                "scope": "workspace",
                "source_repository": "example/tooling",
                "observed_in": ["example/tooling", "example/tooling"],
                "promoted_from": {
                    "repository": "example/application",
                    "lesson_id": "",
                },
            }
        )
        self.assertIn("observed_in entries must be unique", errors)
        self.assertIn(
            "promoted_from requires repository and PROJECT-XXXX lesson_id", errors
        )

    def test_promoted_from_rejects_wrong_scope_or_path_like_id(self):
        for lesson_id in ("KB-0001", "../../private", "arbitrary"):
            with self.subTest(lesson_id=lesson_id):
                errors, _ = validate_metadata(
                    {
                        "scope": "workspace",
                        "source_repository": "example/tooling",
                        "observed_in": ["example/tooling"],
                        "promoted_from": {
                            "repository": "example/application",
                            "lesson_id": lesson_id,
                        },
                    }
                )
                self.assertIn(
                    "promoted_from requires repository and PROJECT-XXXX lesson_id",
                    errors,
                )

    def test_legacy_missing_scope_is_reported_without_invention(self):
        errors, warnings = validate_metadata({}, legacy_ok=True)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["legacy lesson metadata has no scope"])


if __name__ == "__main__":
    unittest.main()
