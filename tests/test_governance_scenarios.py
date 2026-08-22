import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.completion_validator import validate_completion
from kb_bootstrap.repository_doctor import inspect_repository


CONSUMER = "example/consumer"
UPSTREAM = "ozand/kb-bootstrap"
COMMIT = "a" * 40
PR_HEAD = "b" * 40


class GovernanceScenarioTests(unittest.TestCase):
    def test_origin_only_consumer_routing_passes(self):
        responses = {
            ("git", "rev-parse", "--show-toplevel"): ("C:/work/consumer", True),
            ("git", "remote", "get-url", "origin"): (
                "https://token@github.com/example/consumer.git",
                True,
            ),
            ("git", "remote", "get-url", "upstream"): ("", False),
            ("gh", "repo", "set-default", "--view"): (CONSUMER, True),
            (
                "gh", "repo", "view", CONSUMER, "--json",
                "nameWithOwner,defaultBranchRef", "--jq",
                '"\\(.nameWithOwner)\\t\\(.defaultBranchRef.name)"',
            ): (f"{CONSUMER}\tmain", True),
            ("git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"): (
                "origin/main", True
            ),
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.repository_doctor._run",
            side_effect=lambda command, cwd: responses[tuple(command)],
        ):
            report, valid = inspect_repository(CONSUMER, Path(directory))

        self.assertTrue(valid)
        self.assertIn("origin: example/consumer", report)
        self.assertIn("upstream: not configured", report)
        self.assertNotIn("token", report)

    def test_multi_remote_mismatch_blocks(self):
        responses = {
            ("git", "rev-parse", "--show-toplevel"): ("C:/work/consumer", True),
            ("git", "remote", "get-url", "origin"): (
                "https://github.com/example/consumer.git", True
            ),
            ("git", "remote", "get-url", "upstream"): (
                "https://github.com/ozand/kb-bootstrap.git", True
            ),
            ("gh", "repo", "set-default", "--view"): (CONSUMER, True),
            (
                "gh", "repo", "view", UPSTREAM, "--json",
                "nameWithOwner,defaultBranchRef", "--jq",
                '"\\(.nameWithOwner)\\t\\(.defaultBranchRef.name)"',
            ): (f"{UPSTREAM}\tmain", True),
            ("git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"): (
                "origin/main", True
            ),
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.repository_doctor._run",
            side_effect=lambda command, cwd: responses[tuple(command)],
        ):
            report, valid = inspect_repository(UPSTREAM, Path(directory))

        self.assertFalse(valid)
        self.assertIn("origin does not match requested target", report)
        self.assertIn("gh default repository does not match requested target", report)

    def test_explicit_upstream_task_passes_in_upstream_checkout(self):
        responses = {
            ("git", "rev-parse", "--show-toplevel"): ("C:/work/upstream", True),
            ("git", "remote", "get-url", "origin"): (
                "git@github.com:ozand/kb-bootstrap.git", True
            ),
            ("git", "remote", "get-url", "upstream"): ("", False),
            ("gh", "repo", "set-default", "--view"): (UPSTREAM, True),
            (
                "gh", "repo", "view", UPSTREAM, "--json",
                "nameWithOwner,defaultBranchRef", "--jq",
                '"\\(.nameWithOwner)\\t\\(.defaultBranchRef.name)"',
            ): (f"{UPSTREAM}\tmain", True),
            ("git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"): (
                "origin/main", True
            ),
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.repository_doctor._run",
            side_effect=lambda command, cwd: responses[tuple(command)],
        ):
            report, valid = inspect_repository(UPSTREAM, Path(directory))

        self.assertTrue(valid)
        self.assertIn("requested target: ozand/kb-bootstrap", report)
        self.assertIn("RESULT: OK", report)

    def test_wrong_repository_completion_commit_is_rejected(self):
        responses = {
            (
                "gh", "repo", "view", UPSTREAM, "--json",
                "nameWithOwner,defaultBranchRef", "--jq",
                '"\\(.nameWithOwner)\\t\\(.defaultBranchRef.name)"',
            ): (f"{UPSTREAM}\tmain", True),
            (
                "gh", "api", f"repos/{UPSTREAM}/commits/{COMMIT}",
                "--jq", ".sha",
            ): ("", False),
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.completion_validator._run",
            side_effect=lambda command, cwd: responses[tuple(command)],
        ):
            report, valid = validate_completion(UPSTREAM, COMMIT, cwd=Path(directory))

        self.assertFalse(valid)
        self.assertIn("commit is not available in the target repository", report)
        self.assertNotIn("token", report)

    def test_correct_upstream_pr_completion_path_is_accepted(self):
        pr_url = "https://github.com/ozand/kb-bootstrap/pull/42"
        responses = {
            (
                "gh", "repo", "view", UPSTREAM, "--json",
                "nameWithOwner,defaultBranchRef", "--jq",
                '"\\(.nameWithOwner)\\t\\(.defaultBranchRef.name)"',
            ): (f"{UPSTREAM}\tmain", True),
            (
                "gh", "api", f"repos/{UPSTREAM}/commits/{COMMIT}",
                "--jq", ".sha",
            ): (COMMIT, True),
            (
                "gh", "api", f"repos/{UPSTREAM}/compare/{COMMIT}...main",
                "--jq", ".status",
            ): ("diverged", True),
            (
                "gh", "pr", "view", "42", "--repo", UPSTREAM,
                "--json", "baseRepository,headRefOid,url", "--jq",
                '"\\(.baseRepository.nameWithOwner)\\t\\(.headRefOid)\\t\\(.url)"',
            ): (f"{UPSTREAM}\t{PR_HEAD}\t{pr_url}", True),
            (
                "gh", "api", f"repos/{UPSTREAM}/compare/{COMMIT}...{PR_HEAD}",
                "--jq", ".status",
            ): ("ahead", True),
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "kb_bootstrap.completion_validator._run",
            side_effect=lambda command, cwd: responses[tuple(command)],
        ):
            report, valid = validate_completion(
                UPSTREAM, COMMIT, pull_request=42, cwd=Path(directory)
            )

        self.assertTrue(valid)
        self.assertIn("pull request reachable: yes", report)
        self.assertIn(pr_url, report)
        self.assertIn("RESULT: OK", report)


if __name__ == "__main__":
    unittest.main()
