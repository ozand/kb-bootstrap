import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.local_handoff import check_record, load_record, save_record


def make_record():
    return {
        "schema": "kb-local-handoff/v1", "record_id": "study-1", "revision": 1,
        "study_ref": "study:synthetic", "objective": "Compare synthetic revisions",
        "scope": {"included": ["topic"], "excluded": []}, "materials": [],
        "outputs": [], "steps": [], "checks": {"run": [], "not_run": []},
        "retention": {"owner": "test", "storage_class": "runtime-ephemeral",
                      "storage_ref": "selected", "retention_rule": "temporary",
                      "access": "caller", "integrity": "sha256", "availability": "not-verified",
                      "disposal": "caller"}, "assumptions": [], "open_questions": []}


def _race_writer(path, label, expected, barrier, queue):
    from kb_bootstrap.local_handoff import _digest
    candidate = make_record()
    candidate["record_id"] = expected[0]
    candidate["revision"] = expected[1] + 1
    candidate["objective"] = label
    candidate["result_id"] = _digest(candidate)
    barrier.wait()
    result = save_record(path, candidate, expected_record_id=expected[0],
                         expected_revision=expected[1], expected_result_id=expected[2], permission=True)
    queue.put((label, result["status"]))


class LocalHandoffTests(unittest.TestCase):
    def test_strict_json_rejects_duplicate_float_bom_and_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            for raw in (b'{"schema":1,"schema":2}', b"\\xef\\xbb\\xbf{}", b'{"x":1.0}',
                        b'{"x":NaN}', b'{"revision":1e0}', b'{"x":"\\u0001"}',
                        b'{"x":"\\ud800"}'):
                path.write_bytes(raw)
                self.assertEqual(load_record(path)["status"], "invalid")

    def test_integer_token_bounds_and_json_types_are_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            for raw in (b'{"x":9223372036854775808}', b'{"x":-9223372036854775809}',
                        b'{"x":true}', b'{"x":{} }'):
                path.write_bytes(raw)
                self.assertEqual(load_record(path)["status"], "invalid")

    def test_wrong_typed_enums_return_closed_invalid_result(self):
        record = make_record()
        record["materials"] = [{"ref": "s", "revision": "r", "observation": [],
                                "observed_scope": "", "unread_remainder": "",
                                "analysis": "not-started", "analyzed_scope": "",
                                "unanalyzed_remainder": ""}]
        raw = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode()
        record["result_id"] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(check_record(record, lambda *a, **k: {"status": "passed"}),
                         {"status": "invalid", "reason": "invalid-record"})

    def test_load_does_not_follow_symlink(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            target = Path(folder) / "record.json"
            external = Path(outside) / "secret.json"
            external.write_text("{}", encoding="utf8")
            try:
                target.symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            self.assertEqual(load_record(target)["status"], "invalid")

    def test_accepted_outputs_require_distinct_evidence_refs(self):
        record = make_record()
        record["steps"] = []
        record["outputs"] = [
            {"ref": "output:a", "revision": "same", "standing": "accepted", "acceptance_evidence_ref": "evidence:a"},
            {"ref": "output:b", "revision": "same", "standing": "accepted", "acceptance_evidence_ref": "evidence:a"},
        ]
        record["result_id"] = hashlib.sha256(json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(check_record(record, lambda *a, **k: {"status": "passed"}),
                         {"status": "invalid", "reason": "invalid-record"})

    def test_create_load_and_permission_denied_before_io(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "record.json"
            result = save_record(target, make_record(), permission=False)
            self.assertEqual(result["status"], "denied")
            self.assertFalse(target.exists())
            created = save_record(target, make_record(), permission=True)
            self.assertEqual(created["status"], "created")
            self.assertEqual(load_record(target)["record"]["result_id"], created["result_id"])
            self.assertEqual(save_record(target, make_record(), permission=True)["status"], "conflict")
            malformed = make_record(); malformed["materials"] = [[]]
            self.assertEqual(save_record(Path(folder) / "bad.json", malformed, permission=True)["status"], "invalid")

    def test_accepted_output_checker_receives_distinct_identity_arguments(self):
        record = make_record()
        record["steps"] = []
        record["outputs"] = [
            {"ref": "output:a", "revision": "same", "standing": "accepted", "acceptance_evidence_ref": "evidence:a"},
            {"ref": "output:b", "revision": "same", "standing": "accepted", "acceptance_evidence_ref": "evidence:b"},
        ]
        raw = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode()
        record["result_id"] = hashlib.sha256(raw).hexdigest()
        calls = []
        result = check_record(record, lambda ref, revision, kind, *, acceptance_evidence_ref=None: (
            calls.append((ref, revision, kind, acceptance_evidence_ref)) or {"status": "passed"}
        ))
        self.assertEqual(result["status"], "checked")
        self.assertIn(("output:a", "same", "acceptance", "evidence:a"), calls)
        self.assertIn(("output:b", "same", "acceptance", "evidence:b"), calls)
        self.assertEqual(len([x for x in calls if x[2] == "acceptance"]), 2)

    def test_check_preserves_complete_history_but_derives_current_state(self):
        record = make_record()
        record["materials"] = [{"ref": "source:a", "revision": "r1", "observation": "read",
                                 "observed_scope": "whole", "unread_remainder": "",
                                 "analysis": "analyzed", "analyzed_scope": "whole",
                                 "unanalyzed_remainder": ""}]
        attempt = {"attempt_id": "done", "input_revisions": [{"ref": "source:a", "revision": "r1"}],
                   "output_revisions": [], "required_evidence": [], "observed_evidence": [],
                   "state": "complete", "observed_at": "synthetic"}
        record["steps"] = [{"step_id": "done", "intent": "check source", "input_revisions": attempt["input_revisions"],
                            "state": "complete", "output_revisions": [], "required_evidence": [],
                            "observed_evidence": [], "blocker": None, "next_step": None,
                            "attempts": [attempt], "current_resumability": "none"}]
        record["result_id"] = hashlib.sha256(json.dumps(record,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
        original = json.loads(json.dumps(record))
        result = check_record(record, lambda *args, **kwargs: {"status": "unavailable"})
        self.assertEqual(result["steps"][0]["historical_state"], "complete")
        self.assertEqual(result["steps"][0]["current_resumability"], "revalidation-required")
        self.assertEqual(record, original)

    def test_save_failure_outcomes_preserve_or_report_unknown(self):
        import kb_bootstrap.local_handoff as module
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            original = save_record(path, make_record(), permission=True)
            old_bytes = path.read_bytes()
            candidate = dict(original["record"]); candidate["revision"] = 2
            candidate["result_id"] = hashlib.sha256(json.dumps({k:v for k,v in candidate.items() if k!="result_id"},ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
            args = {"expected_record_id": original["record"]["record_id"], "expected_revision": 1,
                    "expected_result_id": original["result_id"], "permission": True}
            with patch.object(module.os, "replace", side_effect=OSError("precommit")):
                failed = save_record(path, candidate, **args)
            self.assertEqual(failed["status"], "io-error")
            self.assertEqual(path.read_bytes(), old_bytes)
            real_read = module._read_record
            calls = []
            def read_then_fail(target):
                calls.append(target)
                if len(calls) > 1:
                    raise OSError("postcommit readback unavailable")
                return real_read(target)
            with patch.object(module, "_read_record", side_effect=read_then_fail):
                unknown = save_record(path, candidate, **args)
            self.assertEqual(unknown["status"], "unknown")
            self.assertEqual(load_record(path)["record"]["revision"], 2)

    def test_attempt_limit_blocks_without_trimming(self):
        from kb_bootstrap.local_handoff import _history_conflict
        record = make_record()
        step = {"step_id": "bounded", "intent": "bounded", "input_revisions": [], "state": "pending",
                "output_revisions": [], "required_evidence": [], "observed_evidence": [], "blocker": None,
                "next_step": None, "current_resumability": "ready", "attempts": []}
        step["attempts"] = [{"attempt_id": "a%d" % i, "input_revisions": [], "output_revisions": [],
                             "required_evidence": [], "observed_evidence": [], "state": "pending",
                             "observed_at": "synthetic"} for i in range(20)]
        record["steps"] = [step]
        record["result_id"] = hashlib.sha256(json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        next_record = json.loads(json.dumps(record)); next_record["revision"] = 2
        next_record["steps"][0]["attempts"].append({"attempt_id": "a20", "input_revisions": [],
            "output_revisions": [], "required_evidence": [], "observed_evidence": [],
            "state": "pending", "observed_at": "synthetic"})
        next_record["result_id"] = hashlib.sha256(json.dumps({k:v for k,v in next_record.items() if k!="result_id"},ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
        self.assertTrue(_history_conflict(record, next_record))

    def test_two_process_same_baseline_has_one_winner(self):
        import multiprocessing
        from kb_bootstrap.local_handoff import _digest
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            initial = make_record()
            original = save_record(path, initial, permission=True)
            expected = (original["record"]["record_id"], original["record"]["revision"], original["result_id"])
            barrier = multiprocessing.Barrier(2)
            queue = multiprocessing.Queue()
            workers = [multiprocessing.Process(target=_race_writer,
                args=(str(path), name, expected, barrier, queue)) for name in ("winner-a", "winner-b")]
            for process in workers: process.start()
            for process in workers: process.join(10)
            self.assertTrue(all(not process.is_alive() and process.exitcode == 0 for process in workers))
            results = [queue.get(timeout=2) for _ in workers]
            self.assertEqual(sorted(status for _, status in results), ["conflict", "replaced"])
            stored = load_record(path)["record"]
            self.assertEqual(stored["revision"], 2)
            self.assertIn(stored["objective"], {"winner-a", "winner-b"})
            self.assertEqual(stored["result_id"], _digest(stored))

    def test_replacement_rejects_history_regression_and_allows_append(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            initial = make_record()
            initial["steps"] = [{"step_id": "old", "intent": "x", "input_revisions": [], "state": "pending",
                                 "output_revisions": [], "required_evidence": [], "observed_evidence": [],
                                 "blocker": None, "next_step": None, "attempts": [], "current_resumability": "ready"}]
            original = save_record(path, initial, permission=True)
            candidate = dict(original["record"])
            candidate["revision"] = 2
            candidate["steps"] = [{"step_id": "renamed", "intent": "x", "input_revisions": [], "state": "pending",
                                    "output_revisions": [], "required_evidence": [], "observed_evidence": [],
                                    "blocker": None, "next_step": None, "attempts": [], "current_resumability": "ready"}]
            candidate["result_id"] = hashlib.sha256(json.dumps({k:v for k,v in candidate.items() if k!="result_id"},ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
            args = {"expected_record_id": original["record"]["record_id"], "expected_revision": 1,
                    "expected_result_id": original["result_id"], "permission": True}
            self.assertEqual(save_record(path,candidate,**args)["status"],"conflict")
            self.assertEqual(load_record(path)["record"],original["record"])
            appended = dict(original["record"])
            appended["revision"] = 2
            appended["steps"].append({"step_id": "new", "intent": "next", "input_revisions": [], "state": "pending",
                                       "output_revisions": [], "required_evidence": [], "observed_evidence": [],
                                       "blocker": None, "next_step": None, "attempts": [], "current_resumability": "ready"})
            appended["result_id"] = hashlib.sha256(json.dumps({k:v for k,v in appended.items() if k!="result_id"},ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
            updated = save_record(path,appended,**args)
            self.assertEqual(updated["status"],"replaced")
            self.assertEqual(load_record(path)["record"]["revision"],2)
