import json
import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.contribution_candidate import prepare_candidate, validate_candidate


def valid_candidate():
    return {
        "target": {
            "repository": "example/shared-lessons",
            "branch": "contrib/project-0042",
            "destination": "workspace-global-lessons",
        },
        "preflight": {
            "authenticated": True,
            "repository_match": True,
            "human_confirmed": True,
        },
        "metadata": {
            "scope": "workspace",
            "source_repository": "example/application",
            "observed_in": ["example/application", "example/tooling"],
            "promoted_from": {
                "repository": "example/application",
                "lesson_id": "PROJECT-0042",
            },
        },
        "content": {
            "title": "Portable process startup failure",
            "problem": "A process cannot locate an explicitly required executable.",
            "resolution": "Validate the executable during preflight and fail closed.",
            "prevention": "Keep the dependency check deterministic and documented.",
        },
    }


class ContributionCandidateTests(unittest.TestCase):
    def test_successful_preparation_writes_only_local_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            output = root / "candidate.json"
            source.write_text(json.dumps(valid_candidate()), encoding="utf-8")

            report, valid = prepare_candidate(source, output)

            self.assertTrue(valid)
            self.assertTrue(output.is_file())
            prepared = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(prepared["status"], "prepared-for-review")
            self.assertEqual(prepared["receipt"]["outcome"], "prepared-for-review")
            self.assertEqual(prepared["receipt"]["preflight"], "verified")
            self.assertEqual(prepared["receipt"]["human_confirmation"], "verified")
            self.assertNotIn("preflight", prepared)
            self.assertIn("shared store write: no", report)
            self.assertIn("pull request created: no", report)

    def test_extra_unvalidated_fields_are_not_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = valid_candidate()
            candidate["content"]["private_config"] = "password=private-value"
            candidate["metadata"]["runtime_state"] = "session_id=private"
            candidate["target"]["remote_url"] = "https://token@example.invalid/repo"
            source = root / "input.json"
            output = root / "candidate.json"
            source.write_text(json.dumps(candidate), encoding="utf-8")

            _, valid = prepare_candidate(source, output)

            self.assertTrue(valid)
            prepared = json.loads(output.read_text(encoding="utf-8"))
            self.assertNotIn("private_config", prepared["content"])
            self.assertNotIn("runtime_state", prepared["metadata"])
            self.assertNotIn("remote_url", prepared["target"])
            self.assertNotIn("private-value", output.read_text(encoding="utf-8"))

    def test_wrong_target_blocks_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = valid_candidate()
            candidate["preflight"]["repository_match"] = False
            source = root / "input.json"
            output = root / "candidate.json"
            source.write_text(json.dumps(candidate), encoding="utf-8")

            report, valid = prepare_candidate(source, output)

            self.assertFalse(valid)
            self.assertIn("repository preflight does not match target", report)
            self.assertFalse(output.exists())

    def test_missing_auth_or_confirmation_blocks(self):
        for field in ("authenticated", "human_confirmed"):
            with self.subTest(field=field):
                candidate = valid_candidate()
                candidate["preflight"][field] = False
                errors = validate_candidate(candidate)
                self.assertTrue(any("required" in error for error in errors))

    def test_ambiguous_branch_or_destination_blocks(self):
        candidate = valid_candidate()
        candidate["target"]["branch"] = "../unsafe"
        candidate["target"]["destination"] = "local-and-shared"
        errors = validate_candidate(candidate)
        self.assertIn("target branch is missing or invalid", errors)
        self.assertIn("target destination must be workspace-global-lessons", errors)

    def test_sanitization_failure_blocks_without_copying_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = valid_candidate()
            candidate["content"]["resolution"] = "api_key=private-value"
            source = root / "input.json"
            output = root / "candidate.json"
            source.write_text(json.dumps(candidate), encoding="utf-8")

            report, valid = prepare_candidate(source, output)

            self.assertFalse(valid)
            self.assertIn("content resolution failed sanitization", report)
            self.assertNotIn("private-value", report)
            self.assertFalse(output.exists())

    def test_paths_protocol_credentials_and_bearer_token_fail_sanitization(self):
        for value in (
            "read /home/user/private.txt",
            "read //etc/passwd",
            r"read \\server\private",
            "Authorization: private",
            "Bearer private-token",
            "postgres://user:pass@db",
        ):
            with self.subTest(value=value):
                candidate = valid_candidate()
                candidate["content"]["problem"] = value
                errors = validate_candidate(candidate)
                self.assertIn("content problem failed sanitization", errors)

    def test_exclusive_creation_handles_race_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            output = root / "candidate.json"
            source.write_text(json.dumps(valid_candidate()), encoding="utf-8")

            original_exists = Path.exists
            calls = {"count": 0}

            def racing_exists(path):
                if path == output and calls["count"] == 0:
                    calls["count"] += 1
                    output.write_text("preserve", encoding="utf-8")
                    return False
                return original_exists(path)

            from unittest.mock import patch
            with patch("kb_bootstrap.contribution_candidate.Path.exists", racing_exists):
                report, valid = prepare_candidate(source, output)

            self.assertFalse(valid)
            self.assertIn("output already exists", report)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")

    def test_missing_output_parent_blocks_without_creating_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            output = root / "missing" / "candidate.json"
            source.write_text(json.dumps(valid_candidate()), encoding="utf-8")

            report, valid = prepare_candidate(source, output)

            self.assertFalse(valid)
            self.assertIn("output parent is unavailable", report)
            self.assertFalse(output.parent.exists())

    def test_output_creation_os_error_blocks_without_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            output = root / "candidate.json"
            source.write_text(json.dumps(valid_candidate()), encoding="utf-8")

            from unittest.mock import patch
            original_open = Path.open

            def failing_output_open(path, *args, **kwargs):
                if path == output:
                    raise PermissionError
                return original_open(path, *args, **kwargs)

            with patch("kb_bootstrap.contribution_candidate.Path.open", failing_output_open):
                report, valid = prepare_candidate(source, output)

            self.assertFalse(valid)
            self.assertIn("output cannot be created", report)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            output = root / "candidate.json"
            source.write_text(json.dumps(valid_candidate()), encoding="utf-8")
            output.write_text("preserve", encoding="utf-8")

            report, valid = prepare_candidate(source, output)

            self.assertFalse(valid)
            self.assertIn("output already exists", report)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
