"""Metadata-only reporting for one existing section projection result (ADR-037)."""
from __future__ import annotations

import re
from typing import Dict, Mapping, Optional

from .local_retrieval import MAX_OUTPUT, json_bytes
from .section_projection import MAX_HEADING_DEPTH, MAX_SECTION_BYTES, MAX_TITLE_BYTES

_SELECTION_STATES = {"NOT_CONFIGURED", "DISABLED", "CONFIGURED"}
_REASON_STATUSES = {
    "BLOCKED": "blocked",
    "UNSUPPORTED": "unsupported",
    "NOT_FOUND": "not_found",
    "AMBIGUOUS": "ambiguous",
}
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_SUCCESS_KEYS = {
    "status", "path", "observed_sha256", "heading_path", "occurrence",
    "start_line", "end_line", "text", "truncated",
}


def _utf8(value):
    if not isinstance(value, str):
        raise ValueError("expected string")
    try:
        return value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("string is not valid UTF-8") from exc


def _positive_integer(value):
    return type(value) is int and value > 0


def _validate_result(result):
    if not isinstance(result, Mapping):
        raise ValueError("result must be a mapping")
    status = result.get("status")
    if not isinstance(status, str):
        raise ValueError("invalid result status")
    if status in _REASON_STATUSES:
        expected = {"status", "reason"}
        if set(result) != expected or result.get("reason") != _REASON_STATUSES[status]:
            raise ValueError("invalid reason result shape")
        _utf8(status)
        _utf8(result["reason"])
    elif status == "REVISION_MISMATCH":
        if set(result) != {"status", "observed_sha256"}:
            raise ValueError("invalid revision mismatch result shape")
        if not isinstance(result["observed_sha256"], str) or not _DIGEST.fullmatch(result["observed_sha256"]):
            raise ValueError("invalid observed digest")
    elif status in ("COMPLETE", "TRUNCATED"):
        if set(result) != _SUCCESS_KEYS:
            raise ValueError("invalid successful result shape")
        if not _utf8(result["path"]):
            raise ValueError("path must be non-empty")
        digest = result["observed_sha256"]
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise ValueError("invalid observed digest")
        headings = result["heading_path"]
        if not isinstance(headings, list) or not headings or len(headings) > MAX_HEADING_DEPTH:
            raise ValueError("invalid heading path")
        for heading in headings:
            if not _utf8(heading) or len(_utf8(heading)) > MAX_TITLE_BYTES:
                raise ValueError("invalid heading component")
        if not _positive_integer(result["occurrence"]):
            raise ValueError("invalid occurrence")
        if not _positive_integer(result["start_line"]) or not _positive_integer(result["end_line"]):
            raise ValueError("invalid line numbers")
        if result["end_line"] < result["start_line"]:
            raise ValueError("end line precedes start line")
        text = _utf8(result["text"])
        if len(text) > MAX_SECTION_BYTES:
            raise ValueError("section text exceeds byte limit")
        if type(result["truncated"]) is not bool or result["truncated"] != (status == "TRUNCATED"):
            raise ValueError("truncated flag disagrees with status")
    else:
        raise ValueError("unknown result status")
    try:
        if len(json_bytes(dict(result))) + 1 > MAX_OUTPUT:
            raise ValueError("result exceeds JSON byte limit")
    except (TypeError, ValueError, UnicodeError) as exc:
        if isinstance(exc, ValueError) and str(exc) == "result exceeds JSON byte limit":
            raise
        raise ValueError("result is not compact JSON") from exc
    return status


def report_section_projection(
    *,
    selection_state: str,
    required: bool,
    result: Optional[Mapping[str, object]],
) -> Dict[str, object]:
    """Report selection and an already-produced ADR-034 result without executing it."""
    if not isinstance(selection_state, str) or selection_state not in _SELECTION_STATES:
        raise ValueError("invalid selection state")
    if type(required) is not bool:
        raise ValueError("required must be bool")
    if result is not None and selection_state != "CONFIGURED":
        raise ValueError("only configured selection may have a result")
    status = "NOT_RUN" if result is None else _validate_result(result)
    observation = "NOT_RUN" if status == "NOT_RUN" else "AVAILABLE" if status == "COMPLETE" else "UNKNOWN"
    satisfied = not required or (selection_state == "CONFIGURED" and status == "COMPLETE")
    return {
        "selection_state": selection_state,
        "required": required,
        "operation": "project_section",
        "operation_status": status,
        "observation": observation,
        "requirement_satisfied": satisfied,
    }
