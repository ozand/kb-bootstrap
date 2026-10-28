"""Pure composition of ADR-036 resolver reports and ADR-040 lineage declarations."""
from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping

from .evidence_lineage import classify_evidence_lineage
from .source_capture_validation import TOKEN, _safe_relative

_MAX_REFERENCES = 999
_MAX_REPORT_BYTES = 8 * 1024 * 1024
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_BLOCKED = frozenset((
    "invalid_binding", "invalid_or_incomplete_envelope", "unsafe_or_inaccessible_path",
    "baseline_identity_mismatch", "resource_limit_exceeded", "serialization_limit_exceeded",
))
_STATES = {
    "unchanged": "byte_revision_matches",
    "changed": "byte_revision_differs",
    "missing": "current_mapping_absent",
}


def _fail():
    raise ValueError("invalid evidence review input")


def _plain_tree(value):
    if value is None or type(value) in (str, bool):
        return
    if type(value) is list:
        for item in value:
            _plain_tree(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _plain_tree(item)
        return
    _fail()


def _keys(value, required, optional=()):
    return (type(value) is dict and required <= value.keys()
            and not (value.keys() - required - set(optional)))


def _path(value):
    return _safe_relative(value)


def _validate_report(report):
    try:
        _plain_tree(report)
    except RecursionError:
        _fail()
    if type(report) is not dict or type(report.get("status")) is not str:
        _fail()
    if report["status"] == "BLOCKED":
        if (not _keys(report, {"status", "reason"}) or type(report["reason"]) is not str
                or report["reason"] not in _BLOCKED):
            _fail()
        return []
    if report["status"] != "COMPLETE" or not _keys(report, {"status", "knowledge", "references"}):
        _fail()
    knowledge = report["knowledge"]
    if not _keys(knowledge, {"path", "summary"}, {"observed_sha256"}):
        _fail()
    if not _path(knowledge["path"]) or knowledge["summary"] not in ("unchanged", "changed", "missing"):
        _fail()
    if "observed_sha256" in knowledge and (type(knowledge["observed_sha256"]) is not str
            or not _DIGEST.fullmatch(knowledge["observed_sha256"])):
        _fail()
    refs = report["references"]
    if type(refs) is not list or len(refs) > _MAX_REFERENCES:
        _fail()
    identities = []
    for ref in refs:
        if not _keys(ref, {"binding_id", "source_id", "representation_id", "observed_sha256",
                           "raw_path", "state", "reason"}, {"current"}):
            _fail()
        bid, sid, rid = ref["binding_id"], ref["source_id"], ref["representation_id"]
        digest, path, state = ref["observed_sha256"], ref["raw_path"], ref["state"]
        if (type(bid) is not str or not TOKEN.fullmatch(bid) or type(sid) is not str
                or not TOKEN.fullmatch(sid) or type(rid) is not str or not TOKEN.fullmatch(rid)
                or type(digest) is not str or not _DIGEST.fullmatch(digest) or not _path(path)
                or type(state) is not str or state not in _STATES or ref["reason"] != _STATES[state]):
            _fail()
        identity_order = (sid, rid, digest, bid)
        identities.append(identity_order)
        if "current" in ref:
            current = ref["current"]
            if not _keys(current, {"source_id", "representation_id"}, {"observed_sha256", "raw_path"}):
                _fail()
            if (type(current["source_id"]) is not str or not TOKEN.fullmatch(current["source_id"])
                    or type(current["representation_id"]) is not str
                    or not TOKEN.fullmatch(current["representation_id"])):
                _fail()
            present_digest, present_path = "observed_sha256" in current, "raw_path" in current
            if present_digest != present_path:
                _fail()
            if present_digest and (type(current["observed_sha256"]) is not str
                    or not _DIGEST.fullmatch(current["observed_sha256"]) or not _path(current["raw_path"])):
                _fail()
            if (state == "missing") == present_digest:
                _fail()
            if present_digest and (state == "unchanged") != (current["observed_sha256"] == digest):
                _fail()
        elif state != "missing":
            _fail()
        # Rows with repeated full ordering keys preserve evidence-array order.
    if identities != sorted(identities):
        _fail()
    states = [ref["state"] for ref in refs]
    summary = knowledge["summary"]
    if ((summary == "unchanged" and any(state != "unchanged" for state in states))
            or (summary == "missing" and ("missing" not in states or "changed" in states))
            or (summary == "changed" and "changed" not in states and "observed_sha256" not in knowledge)):
        _fail()
    try:
        if len(json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > _MAX_REPORT_BYTES:
            _fail()
    except (UnicodeError, ValueError, RecursionError):
        _fail()
    return refs


def compose_evidence_review_worklist(resolver_report, lineage_records, coverage_complete,
                                     reference_lineage_ids):
    """Compose a supplied ADR-036 report with explicitly mapped ADR-040 declarations.

    The helper does not authenticate report origin/currentness or verify lineage claims.
    It performs no I/O, permission checks, discovery, mutation, persistence, or lifecycle action.
    """
    refs = _validate_report(resolver_report)
    lineage_results = classify_evidence_lineage(lineage_records, coverage_complete)
    result_by_id = {item["id"]: item for item in lineage_results}
    if not isinstance(reference_lineage_ids, Mapping) or len(reference_lineage_ids) > _MAX_REFERENCES:
        _fail()
    allowed = {(ref["source_id"], ref["representation_id"]) for ref in refs}
    seen = set()
    mapping = {}
    for key, identifier in reference_lineage_ids.items():
        if (type(key) is not tuple or len(key) != 2 or any(type(part) is not str for part in key)
                or type(identifier) is not str or key not in allowed or key in seen
                or identifier not in result_by_id):
            _fail()
        seen.add(key)
        mapping[key] = identifier
    if resolver_report["status"] == "BLOCKED" and mapping:
        _fail()
    report_copy = copy.deepcopy(resolver_report)
    if report_copy["status"] == "BLOCKED":
        return {"resolver_report": report_copy, "knowledge_review_required": False, "worklist": []}
    worklist = []
    for ref in report_copy["references"]:
        lineage_id = mapping.get((ref["source_id"], ref["representation_id"]))
        if lineage_id is None:
            lineage = {"state": "unknown"}
        elif not coverage_complete:
            lineage = {"id": lineage_id, "state": "unknown"}
        else:
            lineage = copy.deepcopy(result_by_id[lineage_id])
        worklist.append({"reference": copy.deepcopy(ref),
                         "review_required": ref["state"] in ("changed", "missing"),
                         "lineage": lineage})
    return {"resolver_report": report_copy,
            "knowledge_review_required": resolver_report["knowledge"]["summary"] == "changed",
            "worklist": worklist}
