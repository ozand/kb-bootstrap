"""Caller-directed, read-only lookup of validated retained source evidence."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from .source_capture_validation import _validate_source_capture

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MAX_SELECTED = 1000 * 100


def _blocked(reason: str) -> dict[str, Any]:
    return {"status": "BLOCKED", "reason": reason}


def lookup_source_evidence(
    project_root: str | Path,
    metadata_path: str | Path,
    corpus_root: str | Path,
    source_id: str,
    selected_paths: Iterable[str],
) -> dict[str, Any]:
    """Validate one complete explicit envelope, then project one source.

    Callers provide the complete selected path set for every retained member
    declared in the envelope. No discovery, origin access, or writes occur.
    Concurrent hostile mutation is outside the stable-checkout contract.
    """
    if not isinstance(source_id, str) or not source_id:
        return _blocked("source identifier is invalid")
    if not isinstance(metadata_path, (str, Path)):
        return _blocked("metadata path is invalid")
    try:
        selected = []
        for path in selected_paths:
            if len(selected) >= _MAX_SELECTED:
                return _blocked("selected path count exceeds limit")
            if not isinstance(path, str):
                return _blocked("selected paths are invalid")
            selected.append(path)
    except (TypeError, ValueError):
        return _blocked("selected paths are invalid")

    valid, errors, record = _validate_source_capture(
        metadata_path, project_root, corpus_root, selected
    )
    if not valid or record is None:
        # Internal validator errors contain sanitized categories only.
        return _blocked(errors[0] if errors else "source envelope is invalid")

    matches = [item for item in record["sources"] if item["source_id"] == source_id]
    if len(matches) != 1:
        return _blocked("requested source is missing or ambiguous")
    source = matches[0]

    original = source["original_revision"]
    original_digest = None
    if original.get("algorithm") == "sha256":
        candidate = original.get("digest")
        if isinstance(candidate, str) and _DIGEST.fullmatch(candidate):
            original_digest = candidate

    representations = []
    verified_representation = False
    verified_original = False
    for rep in sorted(source["representations"], key=lambda item: item["representation_id"]):
        retained = rep["retention"] == "retained"
        if retained:
            verified_representation = True
            if original_digest is not None and rep["revision"]["digest"] == original_digest:
                verified_original = True
        representations.append({
            "representation_id": rep["representation_id"],
            "digest": rep["revision"]["digest"],
            "raw_path": rep["raw_path"],
            "availability": "representation-verified" if retained else "not-retained",
        })

    retention = source["original_retention"]
    if retention == "retained" and original_digest is not None and verified_original:
        original_availability = "original-retained-verified"
    elif retention == "reference-only":
        original_availability = "original-reference-only"
    else:
        original_availability = "original-unknown"

    result: dict[str, Any] = {
        "status": "AVAILABLE" if verified_representation else "UNAVAILABLE",
        "source_id": source["source_id"],
        "origin_kind": source["origin"]["kind"],
        "capture_method": source["capture"]["method"],
        "fidelity_class": source["fidelity"]["class"],
        "original_availability": original_availability,
        "representations": representations,
    }
    if source["origin"]["kind"] == "unavailable":
        result["origin_reason"] = source["origin"]["reason"]
    return result
