import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.completion_validator import validate_completion


REPOSITORY = "example/project"
COMMIT = "a" * 40
PR_HEAD = "b" * 40


class CompletionValidatorTests(unittest.TestCase):
    def run_validation(self, responses, pull_request=None):
        commands = []

        def fake_run(command, cwd):
            commands.append(command)
            return responses[tuple(command)]

        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.completion_validator._run", side_effect=fake_run
        ):
            report, is_valid = validate_completion(
                REPOSITORY, COMMIT, pull_request, cwd=Path(directory)
            )
        return report, is_valid, commands

    @staticmethod
    def base_responses():
        return {
            (
                "gh",
                "repo",
                "view",
                REPOSITORY,
                "--json",
                "nameWithOwner,defaultBranchRef",
                "--jq",
                '"\\(.nameWithOwner)\\t\\(.defaultBranchRef.name)"',
            ): (f"{REPOSITORY}\tmain", True),
            (
                "gh",
                "api",
                f"repos/{REPOSITORY}/commits/{COMMIT}",
                "--jq",
                ".sha",
            ): (COMMIT, True),
        }

    def test_commit_reachable_from_default_branch_passes(self):
        responses = self.base_responses()
        responses[
            (
                "gh",
                "api",
                f"repos/{REPOSITORY}/compare/{COMMIT}...main",
                "--jq",
                ".status",
            )
        ] = ("ahead", True)

        report, is_valid, commands = self.run_validation(responses)

        self.assertTrue(is_valid)
        self.assertIn("default reachable: yes", report)
        self.assertIn("RESULT: OK", report)
        self.assertFalse(any(command[:2] == ["gh", "issue"] for command in commands))

    def test_commit_reachable_only_from_associated_pr_passes(self):
        responses = self.base_responses()
        responses[
            (
                "gh",
                "api",
                f"repos/{REPOSITORY}/compare/{COMMIT}...main",
                "--jq",
                ".status",
            )
        ] = ("diverged", True)
        responses[
            (
                "gh",
                "pr",
                "view",
                "12",
                "--repo",
                REPOSITORY,
                "--json",
                "baseRepository,headRefOid,url",
                "--jq",
                '"\\(.baseRepository.nameWithOwner)\\t\\(.headRefOid)\\t\\(.url)"',
            )
        ] = (f"{REPOSITORY}\t{PR_HEAD}\thttps://github.com/example/project/pull/12", True)
        responses[
            (
                "gh",
                "api",
                f"repos/{REPOSITORY}/compare/{COMMIT}...{PR_HEAD}",
                "--jq",
                ".status",
            )
        ] = ("ahead", True)

        report, is_valid, _ = self.run_validation(responses, pull_request=12)

        self.assertTrue(is_valid)
        self.assertIn("pull request reachable: yes", report)
        self.assertIn("RESULT: OK", report)

    def test_unreachable_commit_blocks(self):
        responses = self.base_responses()
        responses[
            (
                "gh",
                "api",
                f"repos/{REPOSITORY}/compare/{COMMIT}...main",
                "--jq",
                ".status",
            )
        ] = ("diverged", True)

        report, is_valid, _ = self.run_validation(responses)

        self.assertFalse(is_valid)
        self.assertIn("not reachable", report)
        self.assertIn("RESULT: BLOCKED", report)

    def test_wrong_repository_or_missing_commit_blocks(self):
        responses = self.base_responses()
        repository_command = next(
            command for command in responses if command[:3] == ("gh", "repo", "view")
        )
        responses[repository_command] = ("example/other\tmain", True)

        report, is_valid, commands = self.run_validation(responses)

        self.assertFalse(is_valid)
        self.assertIn("identity does not match", report)
        self.assertFalse(any(command[:2] == ["gh", "pr"] for command in commands))

    def test_invalid_inputs_block_without_external_commands(self):
        with patch("kb_bootstrap.completion_validator._run") as run:
            report, is_valid = validate_completion("wrong", "not-a-commit")

        self.assertFalse(is_valid)
        self.assertIn("RESULT: BLOCKED", report)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
