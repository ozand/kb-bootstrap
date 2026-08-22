import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.repository_manifest import (
    build_manifest,
    validate_manifest,
    validate_manifest_file,
    write_manifest,
)


class RepositoryManifestTests(unittest.TestCase):
    def matching_responses(self):
        return {
            ("git", "rev-parse", "--show-toplevel"): ("C:/work/project", True),
            (
                "gh",
                "repo",
                "view",
                "example/project",
                "--json",
                "nameWithOwner,defaultBranchRef",
                "--jq",
                '"\\(.nameWithOwner)\\t\\(.defaultBranchRef.name)"',
            ): ("example/project\tmain", True),
            ("git", "remote", "get-url", "origin"): (
                "https://token@github.com/example/project.git",
                True,
            ),
            ("git", "remote", "get-url", "upstream"): (
                "git@github.com:ozand/kb-bootstrap.git",
                True,
            ),
        }

    def test_build_manifest_is_sanitized_and_deterministic(self):
        responses = self.matching_responses()
        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.repository_manifest._run",
            side_effect=lambda command, cwd: responses[tuple(command)],
        ):
            manifest, errors = build_manifest(
                "example/project", cwd=Path(directory)
            )

        self.assertEqual(errors, [])
        self.assertEqual(
            manifest,
            {
                "schema_version": 1,
                "repository": "example/project",
                "default_branch": "main",
                "remotes": {
                    "origin": {"repository": "example/project"},
                    "upstream": {"repository": "ozand/kb-bootstrap"},
                },
            },
        )
        serialized = json.dumps(manifest, sort_keys=True)
        self.assertNotIn("token", serialized)
        self.assertNotIn("github.com", serialized)
        self.assertNotIn("C:/work", serialized)

    def test_write_and_validate_round_trip(self):
        responses = self.matching_responses()
        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.repository_manifest._run",
            side_effect=lambda command, cwd: responses[tuple(command)],
        ):
            output = Path(directory) / "repository-context.json"
            report, written = write_manifest(
                "example/project", output, cwd=Path(directory)
            )
            validation_report, valid = validate_manifest_file(output)
            content = output.read_text(encoding="utf-8")

        self.assertTrue(written)
        self.assertTrue(valid)
        self.assertIn("written", report)
        self.assertEqual(validation_report, "Repository context manifest is valid")
        self.assertTrue(content.endswith("\n"))
        self.assertEqual(content, json.dumps(json.loads(content), indent=2, sort_keys=True) + "\n")

    def test_mismatched_origin_blocks_without_writing(self):
        responses = self.matching_responses()
        responses[("git", "remote", "get-url", "origin")] = (
            "https://github.com/example/other.git",
            True,
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.repository_manifest._run",
            side_effect=lambda command, cwd: responses[tuple(command)],
        ):
            output = Path(directory) / "repository-context.json"
            report, written = write_manifest(
                "example/project", output, cwd=Path(directory)
            )

        self.assertFalse(written)
        self.assertFalse(output.exists())
        self.assertIn("origin does not match", report)

    def test_schema_rejects_extra_or_sensitive_fields(self):
        manifest = {
            "schema_version": 1,
            "repository": "example/project",
            "default_branch": "main",
            "remotes": {"origin": {"repository": "example/project"}},
            "cwd": "C:/private",
        }
        self.assertIn("manifest keys do not match schema", validate_manifest(manifest))

    def test_check_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repository-context.json"
            path.write_text("not json", encoding="utf-8")
            report, valid = validate_manifest_file(path)

        self.assertFalse(valid)
        self.assertIn("unreadable", report)


if __name__ == "__main__":
    unittest.main()
