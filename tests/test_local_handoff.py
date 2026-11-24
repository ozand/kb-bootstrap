import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.local_handoff import MAX_BYTES, check_record, load_record, save_record


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
    def test_save_invalid_path_types_are_closed_and_denial_precedes_io(self):
        import kb_bootstrap.local_handoff as module
        record = make_record()
        with patch.object(module.os, "open", side_effect=AssertionError("filesystem I/O")):
            denied = save_record(None, record, permission=False)
        self.assertEqual(denied["status"], "denied")
        for path in (None, 7, object(), "bad\x00path"):
            result = save_record(path, record, permission=True)
            self.assertEqual(result["status"], "invalid")
            self.assertIsNone(result["record"])
            self.assertIsNone(result["result_id"])

    def test_load_invalid_path_types_are_closed(self):
        for path in (None, 7, object(), "bad\x00path"):
            self.assertEqual(load_record(path)["status"], "invalid")

    def test_check_invalid_record_and_checker_are_closed(self):
        self.assertEqual(check_record(None, lambda *a, **k: {"status": "passed"}),
                         {"status": "invalid", "reason": "invalid-record"})
        record = make_record()
        record["steps"] = []
        record["result_id"] = __import__("kb_bootstrap.local_handoff", fromlist=["_digest"])._digest(record)
        self.assertEqual(check_record(record, None)["status"], "invalid")
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

    def test_check_revalidates_output_and_acceptance_without_changing_history(self):
        from kb_bootstrap.local_handoff import _digest, _validate

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            accepted_output = root / "accepted-output.txt"
            stable_output = root / "stable-output.txt"
            required_evidence = root / "required-evidence.txt"
            acceptance_evidence = root / "acceptance.json"
            accepted_output.write_bytes(b"accepted output revision 1\n")
            stable_output.write_bytes(b"unrelated stable output\n")
            required_evidence.write_bytes(b"required evidence revision 1\n")
            accepted_revision = hashlib.sha256(accepted_output.read_bytes()).hexdigest()
            stable_revision = hashlib.sha256(stable_output.read_bytes()).hexdigest()
            required_revision = hashlib.sha256(required_evidence.read_bytes()).hexdigest()
            acceptance_ref = "evidence:acceptance-a"

            def write_acceptance(status="accepted"):
                acceptance_evidence.write_text(json.dumps({
                    "status": status, "output_ref": "output:accepted-a",
                    "output_revision": accepted_revision,
                }, separators=(",", ":")), encoding="utf-8")

            write_acceptance()
            accepted_pair = {"ref": "output:accepted-a", "revision": accepted_revision}
            required_pair = {"ref": "evidence:required-a", "revision": required_revision,
                             "kind": "quality"}
            observed_required = {"ref": required_pair["ref"], "revision": required_revision,
                                 "result": "passed"}
            observed_acceptance = {"ref": accepted_pair["ref"], "revision": accepted_revision,
                                  "result": "passed"}

            def completed_step(step_id, output, *, evidence=()):
                outputs = [dict(output)]
                required = [dict(item) for item in evidence]
                observed = [dict(observed_required)] if required else []
                if output["ref"] == accepted_pair["ref"]:
                    observed.append(dict(observed_acceptance))
                attempt = {"attempt_id": step_id + "-attempt", "input_revisions": [],
                           "output_revisions": outputs, "required_evidence": required,
                           "observed_evidence": observed, "state": "complete",
                           "observed_at": "synthetic"}
                return {"step_id": step_id, "intent": "verify synthetic output",
                        "input_revisions": [], "state": "complete",
                        "output_revisions": outputs, "required_evidence": required,
                        "observed_evidence": observed, "blocker": None, "next_step": None,
                        "attempts": [attempt], "current_resumability": "none"}

            record = make_record()
            record["outputs"] = [
                {"ref": accepted_pair["ref"], "revision": accepted_revision,
                 "standing": "accepted", "acceptance_evidence_ref": acceptance_ref},
                {"ref": "output:stable", "revision": stable_revision,
                 "standing": "provisional", "acceptance_evidence_ref": None},
            ]
            record["steps"] = [
                completed_step("accepted-step", accepted_pair, evidence=[required_pair]),
                completed_step("unrelated-step", {"ref": "output:stable", "revision": stable_revision}),
            ]
            record["result_id"] = _digest(record)
            self.assertIsNone(_validate(record), _validate(record))
            record_path = root / "handoff.json"
            created = save_record(record_path, record, permission=True)
            self.assertEqual(created["status"], "created")
            original = load_record(record_path)["record"]
            original_bytes = record_path.read_bytes()
            original_snapshot = json.loads(json.dumps(original))
            original_history = [(step["step_id"], step["attempts"], step["state"])
                                for step in original["steps"]]

            cases = (
                ("baseline", None, None, "none", "complete", "passed", "passed", "passed"),
                ("changed-output", "changed-output", None, "blocked", "blocked", "mismatch", "passed", "passed"),
                ("missing-output", "missing-output", None, "blocked", "blocked", "missing", "passed", "passed"),
                ("revoked-acceptance", None, "revoked", "blocked", "blocked", "passed", "passed", "revoked"),
                ("required-check-unavailable", None, None, "revalidation-required", "partial", "passed", "unavailable", "passed"),
            )
            for (name, output_change, acceptance_status, expected_current, expected_study,
                 expected_output_status, expected_required_status, expected_acceptance_status) in cases:
                with self.subTest(case=name):
                    accepted_output.write_bytes(b"accepted output revision 1\n")
                    write_acceptance()
                    if output_change == "changed-output":
                        accepted_output.write_bytes(b"accepted output revision 2\n")
                    elif output_change == "missing-output":
                        accepted_output.unlink()
                    if acceptance_status == "revoked":
                        write_acceptance("revoked")

                    calls = []
                    def checker(ref, revision, kind, *, acceptance_evidence_ref=None):
                        calls.append((ref, revision, kind, acceptance_evidence_ref))
                        if kind == "output":
                            path = {"output:accepted-a": accepted_output,
                                    "output:stable": stable_output}.get(ref)
                            if path is None or not path.exists():
                                return {"status": "missing"}
                            return {"status": "passed" if hashlib.sha256(path.read_bytes()).hexdigest() == revision else "mismatch"}
                        if kind == "required:quality":
                            if name == "required-check-unavailable":
                                return {"status": "unavailable"}
                            if not required_evidence.exists():
                                return {"status": "missing"}
                            return {"status": "passed" if hashlib.sha256(required_evidence.read_bytes()).hexdigest() == revision else "mismatch"}
                        if kind == "acceptance":
                            if acceptance_evidence_ref != acceptance_ref or not acceptance_evidence.exists():
                                return {"status": "missing"}
                            evidence = json.loads(acceptance_evidence.read_text(encoding="utf-8"))
                            if evidence["status"] == "revoked":
                                return {"status": "revoked"}
                            if (evidence["output_ref"], evidence["output_revision"]) != (ref, revision):
                                return {"status": "mismatch"}
                            return {"status": "passed"}
                        return {"status": "mismatch"}

                    checked = check_record(original, checker)
                    accepted = checked["steps"][0]
                    unrelated = checked["steps"][1]
                    self.assertEqual(accepted["historical_state"], "complete")
                    self.assertEqual(accepted["current_resumability"], expected_current)
                    self.assertEqual(unrelated["historical_state"], "complete")
                    self.assertEqual(unrelated["current_resumability"], "none")
                    self.assertEqual(checked["study_state"], expected_study)
                    self.assertEqual(calls, [
                        ("output:accepted-a", accepted_revision, "output", None),
                        ("evidence:required-a", required_revision, "required:quality", None),
                        ("output:stable", stable_revision, "output", None),
                        ("output:accepted-a", accepted_revision, "acceptance", acceptance_ref),
                    ])
                    self.assertEqual(original, original_snapshot)
                    self.assertEqual(original, load_record(record_path)["record"])
                    self.assertEqual(record_path.read_bytes(), original_bytes)
                    self.assertEqual([(step["step_id"], step["attempts"], step["state"])
                                      for step in original["steps"]], original_history)
                    self.assertEqual(original["revision"], 1)
                    self.assertEqual(original["result_id"], created["result_id"])
                    evidence_status = {(item["ref"], item["kind"]): item["status"]
                                       for item in accepted["evidence"]}
                    self.assertEqual(evidence_status[("output:accepted-a", "output")], expected_output_status)
                    self.assertEqual(evidence_status[("evidence:required-a", "required:quality")],
                                     expected_required_status)
                    self.assertEqual(evidence_status[("output:accepted-a", "acceptance")],
                                     expected_acceptance_status)

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

    def test_save_rejects_oversize_payload_before_target_io(self):
        import kb_bootstrap.local_handoff as module

        exact = make_record()
        exact["objective"] = "x"
        exact["steps"] = [{
            "step_id": f"budget-{n}", "intent": "size-boundary", "input_revisions": [],
            "state": "pending", "output_revisions": [], "required_evidence": [],
            "observed_evidence": [], "blocker": None, "next_step": None,
            "attempts": [], "current_resumability": "ready",
        } for n in range(15)]

        def wire_size(record):
            value = dict(record)
            value.pop("result_id", None)
            digest = hashlib.sha256(json.dumps(value, ensure_ascii=False,
                separators=(",", ":")).encode("utf-8")).hexdigest()
            value["result_id"] = digest
            return len(json.dumps(value, ensure_ascii=False,
                separators=(",", ":")).encode("utf-8")) + 1

        gap = MAX_BYTES - wire_size(exact)
        for index in range(1500):
            step = exact["steps"][index % len(exact["steps"])]
            step["required_evidence"].append({
                "ref": str(index) + "é" * 250, "revision": '"' * 300, "kind": "check",
            })
            gap = MAX_BYTES - wire_size(exact)
            if 0 <= gap < 1200:
                break
        self.assertGreaterEqual(gap, 0)
        self.assertLess(gap, 1200)
        exact["objective"] += "x" * gap
        self.assertEqual(wire_size(exact), MAX_BYTES)

        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "record.json"
            created = save_record(target, exact, permission=True)
            self.assertEqual(created["status"], "created")
            baseline = target.read_bytes()
            self.assertEqual(len(baseline), MAX_BYTES)
            self.assertEqual(wire_size(load_record(target)["record"]), MAX_BYTES)

            over_create = dict(exact, objective=exact["objective"] + "x")
            over_replace = dict(over_create, revision=2)
            self.assertEqual(wire_size(over_create), MAX_BYTES + 1)
            self.assertEqual(wire_size(over_replace), MAX_BYTES + 1)
            denied = save_record(target, over_create, permission=False)
            self.assertEqual(denied["status"], "denied")
            with patch.object(module, "_reparse", side_effect=AssertionError("target inspected")), \
                 patch.object(module, "_exclusive_writer", side_effect=AssertionError("destination locked")), \
                 patch.object(module.os, "lstat", side_effect=AssertionError("filesystem inspected")), \
                 patch.object(module.tempfile, "mkstemp", side_effect=AssertionError("temporary file created")):
                rejected_create = save_record(Path(folder) / "new.json", over_create, permission=True)
                rejected_replace = save_record(target, over_replace,
                    expected_record_id=created["record"]["record_id"], expected_revision=1,
                    expected_result_id=created["result_id"], permission=True)
            self.assertEqual(rejected_create["status"], "invalid")
            self.assertEqual(rejected_replace["status"], "invalid")
            self.assertEqual(target.read_bytes(), baseline)
            self.assertFalse((Path(folder) / "new.json").exists())

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

    def test_platform_lock_imports_are_branch_local(self):
        import ast
        import kb_bootstrap.local_handoff as module
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf8"))
        top_imports = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
        self.assertNotIn("msvcrt", top_imports)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_exclusive_writer")
        branch = next(node for node in ast.walk(function) if isinstance(node, ast.If)
                      and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Attribute)
                      and node.test.left.attr == "name")
        windows_imports = {alias.name for node in ast.walk(branch.body[0]) if isinstance(node, ast.Import) for alias in node.names}
        posix_imports = {alias.name for node in ast.walk(branch.orelse[0]) if isinstance(node, ast.Import) for alias in node.names}
        self.assertIn("msvcrt", windows_imports)
        self.assertIn("fcntl", posix_imports)

    def test_fresh_process_revalidates_explicit_source_without_rewriting_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record_path = root / "handoff.json"
            source_path = root / "source.txt"
            source_path.write_bytes(b"synthetic source revision one\n")
            source_revision = hashlib.sha256(source_path.read_bytes()).hexdigest()
            record = make_record()
            record["materials"] = [{"ref": "source:a", "revision": source_revision,
                                    "observation": "read", "observed_scope": "whole",
                                    "unread_remainder": "", "analysis": "analyzed",
                                    "analyzed_scope": "whole", "unanalyzed_remainder": ""}]
            pair = {"ref": "source:a", "revision": source_revision}
            observed = {"ref": "source:a", "revision": source_revision, "result": "passed"}
            attempt = {"attempt_id": "complete-1", "input_revisions": [pair],
                       "output_revisions": [], "required_evidence": [],
                       "observed_evidence": [observed], "state": "complete",
                       "observed_at": "synthetic"}
            record["steps"] = [{"step_id": "step-1", "intent": "check synthetic source",
                                "input_revisions": [pair], "state": "complete",
                                "output_revisions": [], "required_evidence": [],
                                "observed_evidence": [observed], "blocker": None,
                                "next_step": None, "attempts": [attempt],
                                "current_resumability": "none"}]
            created = save_record(record_path, record, permission=True)
            self.assertEqual(created["status"], "created")
            initial_bytes = record_path.read_bytes()
            initial_record = load_record(record_path)["record"]

            child = """
import hashlib, json, sys
from pathlib import Path
from kb_bootstrap.local_handoff import check_record, load_record
record_path, source_path = map(Path, sys.argv[1:3])
loaded = load_record(record_path)
if loaded["status"] != "loaded":
    raise SystemExit("record did not load")
record = loaded["record"]
calls = []
def checker(ref, revision, kind, *, acceptance_evidence_ref=None):
    calls.append((ref, revision, kind, acceptance_evidence_ref))
    if (ref, kind, acceptance_evidence_ref) != ("source:a", "input", None):
        return {"status": "mismatch"}
    try:
        current = hashlib.sha256(source_path.read_bytes()).hexdigest()
    except OSError:
        return {"status": "missing"}
    return {"status": "passed" if current == revision else "mismatch"}
checked = check_record(record, checker)
print(json.dumps({"result_id": record["result_id"], "revision": record["revision"],
                  "checked": checked, "calls": calls}, sort_keys=True))
"""
            project_root = Path(__file__).resolve().parents[1]

            def check_in_fresh_process():
                try:
                    completed = subprocess.run(
                        [sys.executable, "-c", child, str(record_path), str(source_path)],
                        cwd=project_root, capture_output=True, text=True, timeout=30, check=True)
                except subprocess.TimeoutExpired as exc:
                    self.fail("fresh-process handoff check timed out: %s" % exc)
                return json.loads(completed.stdout)

            exact_call = ["source:a", source_revision, "input", None]
            unchanged = check_in_fresh_process()
            self.assertEqual(unchanged["calls"], [exact_call])
            self.assertEqual(unchanged["checked"]["study_state"], "complete")
            self.assertEqual(unchanged["checked"]["steps"][0]["historical_state"], "complete")
            self.assertEqual(unchanged["checked"]["steps"][0]["current_resumability"], "none")
            self.assertEqual(source_path.read_bytes(), b"synthetic source revision one\n")
            self.assertEqual(record_path.read_bytes(), initial_bytes)

            source_path.write_bytes(b"synthetic source revision two\n")
            changed_source = source_path.read_bytes()
            changed = check_in_fresh_process()
            self.assertEqual(changed["calls"], [exact_call])
            self.assertEqual(changed["checked"]["study_state"], "blocked")
            self.assertEqual(changed["checked"]["steps"][0]["historical_state"], "complete")
            self.assertEqual(changed["checked"]["steps"][0]["current_resumability"], "blocked")
            self.assertEqual(changed["checked"]["steps"][0]["evidence"][0]["status"], "mismatch")
            self.assertEqual(source_path.read_bytes(), changed_source)
            self.assertEqual(record_path.read_bytes(), initial_bytes)
            stored = load_record(record_path)["record"]
            self.assertEqual((changed["revision"], changed["result_id"]),
                             (initial_record["revision"], initial_record["result_id"]))
            self.assertEqual(stored["steps"][0]["attempts"], initial_record["steps"][0]["attempts"])

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
