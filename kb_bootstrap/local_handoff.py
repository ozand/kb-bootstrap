"""Strict local JSON research handoff operations (ADR-038)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional

SCHEMA = "kb-local-handoff/v1"
MAX_BYTES = 1024 * 1024
DIGEST = re.compile(r"^[0-9a-f]{64}$")
_LOCK = threading.RLock()

def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-finite number")


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _digest(record):
    payload = {key: value for key, value in record.items() if key != "result_id"}
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _safe_text(value, limit, *, empty=False):
    if not isinstance(value, str) or (not empty and not value):
        return False
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return len(encoded) <= limit and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def _reparse(path):
    try:
        absolute = Path(path).absolute()
        current = Path(absolute.anchor)
        for part in absolute.parts[1:]:
            current /= part
            details = current.lstat()
            flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            if current.is_symlink() or getattr(details, "st_file_attributes", 0) & flag:
                return True
        return False
    except (OSError, ValueError):
        return True


def _ordered(value, keys):
    return isinstance(value, dict) and list(value) == list(keys)


def _string_list(value, count, size, *, empty=False):
    return (isinstance(value, list) and len(value) <= count
            and all(_safe_text(item, size, empty=empty) for item in value))

def _validate_inner(record):
    top = ("schema", "record_id", "revision", "study_ref", "objective", "scope",
           "materials", "outputs", "steps", "checks", "retention", "assumptions",
           "open_questions", "result_id")
    if not _ordered(record, top) or not isinstance(record.get("schema"), str) or record["schema"] != SCHEMA:
        return "invalid-schema"
    if (not _safe_text(record["record_id"], 128)
            or type(record["revision"]) is not int or not 1 <= record["revision"] <= 2**63-1
            or not _safe_text(record["study_ref"], 1024)
            or not _safe_text(record["objective"], 2048)):
        return "invalid-schema"
    scope = record["scope"]
    if (not _ordered(scope, ("included", "excluded"))
            or not _string_list(scope["included"], 32, 256)
            or not _string_list(scope["excluded"], 32, 256)):
        return "invalid-schema"
    if not isinstance(record["materials"], list) or len(record["materials"]) > 100:
        return "invalid-schema"
    material_refs = set()
    for item in record["materials"]:
        keys = ("ref", "revision", "observation", "observed_scope", "unread_remainder",
                "analysis", "analyzed_scope", "unanalyzed_remainder")
        if not _ordered(item, keys):
            return "invalid-schema"
        if (not isinstance(item["observation"], str)
                or item["observation"] not in {"captured", "partially-read", "read"}
                or not isinstance(item["analysis"], str)
                or item["analysis"] not in {"not-started", "partially-analyzed", "analyzed"}):
            return "invalid-schema"
        if (not _safe_text(item["ref"], 1024) or item["ref"] in material_refs
                or not _safe_text(item["revision"], 1024)
                or any(not _safe_text(item[k], 512, empty=True) for k in
                       ("observed_scope", "unread_remainder", "analyzed_scope", "unanalyzed_remainder"))):
            return "invalid-schema"
        material_refs.add(item["ref"])
    if not isinstance(record["outputs"], list) or len(record["outputs"]) > 100:
        return "invalid-schema"
    output_refs, acceptance_refs = set(), set()
    for item in record["outputs"]:
        if not _ordered(item, ("ref", "revision", "standing", "acceptance_evidence_ref")):
            return "invalid-schema"
        ref, revision, standing, evidence = (item[k] for k in ("ref", "revision", "standing", "acceptance_evidence_ref"))
        if (not _safe_text(ref, 1024) or ref in output_refs or not _safe_text(revision, 1024)
                or not isinstance(standing, str) or standing not in {"provisional", "accepted"}):
            return "invalid-schema"
        output_refs.add(ref)
        if evidence is not None and not _safe_text(evidence, 1024):
            return "invalid-schema"
        if standing == "accepted":
            if evidence is None or evidence in acceptance_refs:
                return "invalid-schema"
            acceptance_refs.add(evidence)
    def pairs(value, expected, fields):
        if not isinstance(value, list) or len(value) > 100:
            return False
        seen = set()
        for entry in value:
            if not _ordered(entry, fields):
                return False
            identity = tuple(entry[k] for k in ("ref", "revision"))
            if (not all(_safe_text(entry[k], 1024) for k in ("ref", "revision"))
                    or identity in seen):
                return False
            seen.add(identity)
            if expected and not all(_safe_text(entry[k], 1024) for k in expected):
                return False
            if "result" in entry and (not isinstance(entry["result"], str)
                                       or entry["result"] not in {"passed", "failed", "unavailable"}):
                return False
        return True

    if not isinstance(record["steps"], list) or len(record["steps"]) > 100:
        return "invalid-schema"
    steps, outputs = set(), {(x["ref"], x["revision"]) for x in record["outputs"]}
    materials = {(x["ref"], x["revision"]) for x in record["materials"]}
    for step in record["steps"]:
        keys = ("step_id", "intent", "input_revisions", "state", "output_revisions",
                "required_evidence", "observed_evidence", "blocker", "next_step", "attempts",
                "current_resumability")
        if not _ordered(step, keys):
            return "invalid-schema"
        sid = step["step_id"]
        if not _safe_text(sid, 128) or sid in steps or not _safe_text(step["intent"], 1024):
            return "invalid-schema"
        steps.add(sid)
        state = step["state"]
        if not isinstance(state, str) or state not in {"pending", "partial", "blocked", "complete"}:
            return "invalid-schema"
        if (not isinstance(step["current_resumability"], str)
                or step["current_resumability"] not in {"ready", "blocked", "revalidation-required", "none"}):
            return "invalid-schema"
        if any(step[k] is not None and not _safe_text(step[k], 512) for k in ("blocker", "next_step")):
            return "invalid-schema"
        if state == "blocked" and step["blocker"] is None:
            return "invalid-schema"
        if not pairs(step["input_revisions"], (), ("ref", "revision")):
            return "invalid-schema"
        if not pairs(step["output_revisions"], (), ("ref", "revision")):
            return "invalid-schema"
        if any((x["ref"], x["revision"]) not in outputs | materials for x in step["input_revisions"] + step["output_revisions"]):
            return "invalid-schema"
        if not pairs(step["required_evidence"], ("kind",), ("ref", "revision", "kind")):
            return "invalid-schema"
        if not pairs(step["observed_evidence"], ("result",), ("ref", "revision", "result")):
            return "invalid-schema"
        attempts = step["attempts"]
        if not isinstance(attempts, list) or len(attempts) > 20:
            return "invalid-schema"
        attempt_ids = set()
        for attempt in attempts:
            attempt_keys = ("attempt_id", "input_revisions", "output_revisions", "required_evidence",
                            "observed_evidence", "state", "observed_at")
            if not _ordered(attempt, attempt_keys):
                return "invalid-schema"
            aid = attempt["attempt_id"]
            if (not _safe_text(aid, 128) or aid in attempt_ids or not isinstance(attempt["state"], str)
                    or attempt["state"] not in {"pending", "partial", "blocked", "complete"}):
                return "invalid-schema"
            attempt_ids.add(aid)
            if not _safe_text(attempt["observed_at"], 64):
                return "invalid-schema"
            if (not pairs(attempt["input_revisions"], (), ("ref", "revision"))
                    or not pairs(attempt["output_revisions"], (), ("ref", "revision"))
                    or not pairs(attempt["required_evidence"], ("kind",), ("ref", "revision", "kind"))
                    or not pairs(attempt["observed_evidence"], ("result",), ("ref", "revision", "result"))):
                return "invalid-schema"
            if attempt["state"] == "partial" and not (attempt["output_revisions"] or attempt["observed_evidence"]):
                return "invalid-schema"
        if state == "partial":
            if not (step["blocker"] or step["next_step"]):
                return "invalid-schema"
            if not any(a["state"] == "partial" for a in attempts):
                return "invalid-schema"
        if state == "complete":
            observed = {(x["ref"], x["revision"]): x["result"] for x in step["observed_evidence"]}
            if any(observed.get((r["ref"], r["revision"])) != "passed" for r in step["required_evidence"]):
                return "invalid-schema"
    checks = record["checks"]
    if not _ordered(checks, ("run", "not_run")):
        return "invalid-schema"
    if any(not isinstance(checks[k], list) or len(checks[k]) > 100 for k in ("run", "not_run")):
        return "invalid-schema"
    for item in checks["run"]:
        if (not _ordered(item, ("check", "target", "result", "evidence_ref"))
                or any(not _safe_text(item[k], 512) for k in ("check", "target", "result", "evidence_ref"))
                or not isinstance(item["result"], str)
                or item["result"] not in {"passed", "failed", "unavailable"}):
            return "invalid-schema"
    for item in checks["not_run"]:
        if not _ordered(item, ("check", "target", "reason")) or any(not _safe_text(item[k], 512) for k in ("check", "target", "reason")):
            return "invalid-schema"
    retention = record["retention"]
    retention_keys = ("owner", "storage_class", "storage_ref", "retention_rule", "access", "integrity", "availability", "disposal")
    if not _ordered(retention, retention_keys) or any(not _safe_text(retention[k], 512) for k in retention_keys):
        return "invalid-schema"
    if retention["availability"] not in {"verified", "not-verified", "unavailable"}:
        return "invalid-schema"
    for key in ("assumptions", "open_questions"):
        if not _string_list(record[key], 32, 512):
            return "invalid-schema"
    if not isinstance(record["result_id"], str) or not DIGEST.fullmatch(record["result_id"]):
        return "invalid-schema"
    if _digest(record) != record["result_id"]:
        return "digest-mismatch"
    return None


def _validate(record):
    try:
        return _validate_inner(record)
    except (KeyError, TypeError, ValueError, UnicodeError, OverflowError):
        return "invalid-schema"


def _decode(data):
    if len(data) > MAX_BYTES:
        return None, "too-large"
    try:
        text = data.decode("utf-8", errors="strict")
        if text.startswith("﻿"):
            return None, "invalid-utf8"
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant,
                           parse_float=lambda _: (_ for _ in ()).throw(ValueError("float")),
                           parse_int=lambda s: int(s) if len(s.lstrip("-")) <= 19 and -(2**63) <= int(s) <= 2**63-1 else (_ for _ in ()).throw(ValueError("integer")))
    except UnicodeDecodeError:
        return None, "invalid-utf8"
    except (ValueError, json.JSONDecodeError, RecursionError):
        return None, "invalid-json"
    validation_error = _validate(value)
    if validation_error:
        return None, validation_error
    if _canonical(value) + bytes((10,)) != data:
        return None, "invalid-schema"
    return value, None


def _read_record(path):
    target = Path(path)
    if _reparse(target):
        raise OSError("unsafe path")
    before = os.stat(target, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
        raise ValueError("too large or not regular")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(target, flags)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        signature = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        opened = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if not stat.S_ISREG(info.st_mode) or signature != opened:
            raise OSError("changed")
        data = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(data) > MAX_BYTES or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != signature:
        raise OSError("changed or too large")
    return data

def load_record(path):
    try:
        data = _read_record(path)
    except TypeError:
        return {"status": "invalid", "reason": "invalid-schema"}
    except OSError:
        return {"status": "invalid", "reason": "io-error"}
    except ValueError as error:
        reason = "too-large" if "large" in str(error) else "invalid-schema"
        return {"status": "invalid", "reason": reason}
    record, error = _decode(data)
    if error:
        return {"status": "invalid", "reason": error}
    return {"status": "loaded", "record": record}


def _history_ok(old, new):
    new_steps = {step["step_id"]: step for step in new["steps"]}
    for previous in old["steps"]:
        candidate = new_steps.get(previous["step_id"])
        if candidate is None or candidate["attempts"][:len(previous["attempts"])] != previous["attempts"]:
            return False
        if len(candidate["attempts"]) < len(previous["attempts"]):
            return False
    return True


def _required_tuples(record):
    for step in record["steps"]:
        for item in step["input_revisions"]:
            yield item["ref"], item["revision"], "input", None
        for item in step["output_revisions"]:
            yield item["ref"], item["revision"], "output", None
        for item in step["required_evidence"]:
            yield item["ref"], item["revision"], "required:" + item["kind"], None
    for output in record["outputs"]:
        if output["standing"] == "accepted":
            yield output["ref"], output["revision"], "acceptance", output["acceptance_evidence_ref"]


def _resumability(state, statuses):
    if state == "blocked":
        return "blocked"
    if any(status in {"failed", "missing", "stale", "revoked", "mismatch"} for status in statuses):
        return "blocked"
    if any(status in {"unavailable", "checker-error"} for status in statuses):
        return "revalidation-required"
    if state == "complete":
        return "none"
    return "ready"

def check_record(record, checker):
    error = _validate(record)
    if error:
        return {"status": "invalid", "reason": "invalid-record"}
    observations, evidence = {}, {}
    for ref, revision, kind, acceptance_ref in _required_tuples(record):
        key = (ref, revision, kind, acceptance_ref)
        if key in observations:
            continue
        try:
            result = checker(ref, revision, kind, acceptance_evidence_ref=acceptance_ref)
            status = result.get("status") if isinstance(result, dict) and list(result) == ["status"] else None
            if status not in {"passed", "failed", "missing", "stale", "revoked", "unavailable", "mismatch"}:
                status = "checker-error"
        except Exception:
            status = "checker-error"
        observations[key] = status
        evidence[key] = {"ref": ref, "revision": revision, "kind": kind, "status": status}
    results, states = [], []
    for step in record["steps"]:
        relevant_keys = []
        for item in step["input_revisions"]:
            relevant_keys.append((item["ref"], item["revision"], "input", None))
        for item in step["output_revisions"]:
            relevant_keys.append((item["ref"], item["revision"], "output", None))
        for item in step["required_evidence"]:
            relevant_keys.append((item["ref"], item["revision"], "required:" + item["kind"], None))
        for output in record["outputs"]:
            if output["standing"] == "accepted" and any(
                    item["ref"] == output["ref"] and item["revision"] == output["revision"]
                    for item in step["output_revisions"]):
                relevant_keys.append((output["ref"], output["revision"], "acceptance",
                                      output["acceptance_evidence_ref"]))
        relevant = [observations[key] for key in relevant_keys]
        current = _resumability(step["state"], relevant)
        states.append((step["state"], current))
        results.append({"step_id": step["step_id"], "historical_state": step["state"],
                        "current_resumability": current,
                        "evidence": [evidence[key] for key in relevant_keys]})
    study = "pending"
    if states:
        if any(current == "blocked" for _, current in states):
            study = "blocked"
        elif any(current == "revalidation-required" or state == "partial" for state, current in states):
            study = "partial"
        elif all(state == "complete" and current == "none" for state, current in states):
            study = "complete"
        elif all(state == "pending" for state, _ in states):
            study = "pending"
        else:
            study = "partial"
    return {"status": "checked", "study_state": study, "steps": results}

def _payload(candidate):
    value = dict(candidate)
    value.pop("result_id", None)
    digest = hashlib.sha256(_canonical(value)).hexdigest()
    value["result_id"] = digest
    return value, digest, _canonical(value) + bytes((10,))


def _history_conflict(current, candidate):
    old_order = [step["step_id"] for step in current["steps"]]
    new_order = [step["step_id"] for step in candidate["steps"]]
    old = {step["step_id"]: step for step in current["steps"]}
    new = {step["step_id"]: step for step in candidate["steps"]}
    if new_order[:len(old_order)] != old_order:
        return True
    for sid, previous in old.items():
        later = new[sid]["attempts"]
        prior = previous["attempts"]
        if later[:len(prior)] != prior or len(later) > 20:
            return True
        if len(later) < len(prior):
            return True
    return False


def save_record(path, candidate, *, expected_record_id=None, expected_revision=None,
                expected_result_id=None, permission):
    if permission is not True:
        return {"status": "denied", "record": None, "result_id": None}
    if not isinstance(candidate, dict):
        return {"status": "invalid", "record": None, "result_id": None}
    try:
        supplied = dict(candidate)
        supplied.pop("result_id", None)
        candidate_record, digest, data = _payload(supplied)
        candidate_record["result_id"] = digest
    except (TypeError, ValueError, UnicodeError, RecursionError):
        return {"status": "invalid", "record": None, "result_id": None}
    error = _validate(candidate_record)
    if error:
        return {"status": "invalid", "record": None, "result_id": None}
    target = Path(path)
    try:
        if _reparse(target.parent) or (target.exists() and _reparse(target)):
            return {"status": "conflict", "record": None, "result_id": None}
        with _LOCK:
            if expected_record_id is None and expected_revision is None and expected_result_id is None:
                if candidate_record["revision"] != 1:
                    return {"status": "invalid", "record": None, "result_id": None}
                temporary = None
                try:
                    fd, name = tempfile.mkstemp(prefix=".handoff-", suffix=".tmp", dir=str(target.parent))
                    temporary = Path(name)
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(data); stream.flush(); os.fsync(stream.fileno())
                    if _reparse(target.parent):
                        return {"status": "io-error", "record": None, "result_id": None}
                    os.link(temporary, target)
                    return {"status": "created", "record": candidate_record, "result_id": digest}
                except FileExistsError:
                    return {"status": "conflict", "record": None, "result_id": None}
                except OSError:
                    return {"status": "io-error", "record": None, "result_id": None}
                finally:
                    if temporary is not None:
                        try:
                            temporary.unlink()
                        except OSError:
                            pass
            if any(value is None for value in (expected_record_id, expected_revision, expected_result_id)):
                return {"status": "conflict", "record": None, "result_id": None}
            try:
                current, read_error = _decode(_read_record(target))
                if read_error or current is None:
                    return {"status": "conflict", "record": None, "result_id": None}
            except (OSError, ValueError):
                return {"status": "conflict", "record": None, "result_id": None}
            if (current["record_id"], current["revision"], current["result_id"]) != (
                    expected_record_id, expected_revision, expected_result_id):
                return {"status": "conflict", "record": None, "result_id": None}
            if (candidate_record["record_id"] != current["record_id"]
                    or candidate_record["revision"] != current["revision"] + 1
                    or _history_conflict(current, candidate_record)):
                return {"status": "conflict", "record": None, "result_id": None}
            descriptor, temporary = tempfile.mkstemp(prefix=".handoff-", suffix=".tmp", dir=str(target.parent))
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data); stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass
            try:
                verified, verify_error = _decode(_read_record(target))
                if verify_error or verified["result_id"] != digest:
                    raise OSError("post replace verification failed")
            except Exception:
                return {"status": "unknown", "record": None, "result_id": None}
            return {"status": "replaced", "record": verified, "result_id": digest}
    except OSError:
        return {"status": "io-error", "record": None, "result_id": None}
