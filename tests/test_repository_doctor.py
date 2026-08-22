import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.repository_doctor import _repository_from_remote, inspect_repository


class RepositoryDoctorTests(unittest.TestCase):
    def test_remote_parser_returns_only_repository_identity(self):
        self.assertEqual(
            _repository_from_remote("https://github.com/example/project.git"),
            "example/project",
        )
        self.assertEqual(
            _repository_from_remote("git@github.com:example/project.git"),
            "example/project",
        )
        self.assertIsNone(_repository_from_remote("https://example.com/private.git"))

    def test_matching_repository_passes(self):
        responses = {
            ("git", "rev-parse", "--show-toplevel"): ("C:/work/project", True),
            ("git", "remote", "get-url", "origin"): (
                "https://github.com/example/project.git",
                True,
            ),
            ("git", "remote", "get-url", "upstream"): ("", False),
            ("gh", "repo", "set-default", "--view"): ("example/project", True),
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
            (
                "git",
                "symbolic-ref",
                "--short",
                "refs/remotes/origin/HEAD",
            ): ("origin/main", True),
        }

        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.repository_doctor._run",
            side_effect=lambda command, cwd: responses[tuple(command)],
        ):
            report, is_valid = inspect_repository(
                "example/project", cwd=Path(directory)
            )

        self.assertTrue(is_valid)
        self.assertIn("RESULT: OK", report)
        self.assertIn("upstream: not configured", report)
        self.assertNotIn("https://", report)

    def test_mismatch_blocks_without_mutation_commands(self):
        commands = []

        def fake_run(command, cwd):
            commands.append(command)
            values = {
                ("git", "rev-parse", "--show-toplevel"): ("C:/work/project", True),
                ("git", "remote", "get-url", "origin"): (
                    "https://github.com/example/other.git",
                    True,
                ),
                ("git", "remote", "get-url", "upstream"): ("", False),
                ("gh", "repo", "set-default", "--view"): ("example/other", True),
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
                (
                    "git",
                    "symbolic-ref",
                    "--short",
                    "refs/remotes/origin/HEAD",
                ): ("origin/main", True),
            }
            return values[tuple(command)]

        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.repository_doctor._run", side_effect=fake_run
        ):
            report, is_valid = inspect_repository(
                "example/project", cwd=Path(directory)
            )

        self.assertFalse(is_valid)
        self.assertIn("RESULT: BLOCKED", report)
        self.assertIn("origin does not match", report)
        self.assertIn("gh default repository does not match", report)
        self.assertFalse(any(command[:2] == ["gh", "issue"] for command in commands))
        self.assertFalse(any(command[:2] == ["git", "remote"] and "set-url" in command for command in commands))

    def test_missing_target_blocks_before_success(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.repository_doctor._run",
            return_value=("", False),
        ):
            report, is_valid = inspect_repository(None, cwd=Path(directory))

        self.assertFalse(is_valid)
        self.assertIn("requested target is missing or invalid", report)
        self.assertIn("RESULT: BLOCKED", report)


if __name__ == "__main__":
    unittest.main()
