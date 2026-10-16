"""Read-only, caller-directed reuse of validated source identity."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .source_capture_validation import MAX_REPRESENTATIONS, MAX_SOURCES, _validate_source_capture

_MAX_SELECTED = MAX_REPRESENTATIONS * MAX_SOURCES


def reuse_source_evidence(
    project_root: str | Path,
    metadata_path: str | Path | None,
    corpus_root: str | Path,
    source_id: str,
    selected_paths: Iterable[str],
) -> dict[str, Any]:
    """Return bounded declared identity only after whole-envelope validation.

    A missing metadata path represents legacy RawCapture-only evidence; it is
    not upgraded from its URL, title, path, or content digest.
    """
    if metadata_path is None:
        return {"status": "UNAVAILABLE", "reason": "explicit source envelope not supplied"}
    if not isinstance(source_id, str) or not source_id:
        return {"status": "BLOCKED", "reason": "source identifier is invalid"}
    try:
        selected = []
        for path in selected_paths:
            if len(selected) >= _MAX_SELECTED:
                return {"status": "BLOCKED", "reason": "selected path count exceeds limit"}
            if not isinstance(path, str):
                return {"status": "BLOCKED", "reason": "selected paths are invalid"}
            selected.append(path)
    except (TypeError, ValueError):
        return {"status": "BLOCKED", "reason": "selected paths are invalid"}
    valid, errors, record = _validate_source_capture(
        metadata_path, project_root, corpus_root, selected
    )
    if not valid or record is None:
        return {"status": "BLOCKED", "reason": errors[0] if errors else "source envelope is invalid"}
    matches = [source for source in record["sources"] if source["source_id"] == source_id]
    if len(matches) != 1:
        return {"status": "BLOCKED", "reason": "requested source is missing or ambiguous"}
    source = matches[0]
    representations = [
        {
            "representation_id": rep["representation_id"],
            "digest": rep["revision"]["digest"],
            "raw_path": rep["raw_path"],
        }
        for rep in sorted(source["representations"], key=lambda item: item["representation_id"])
    ]
    # Preserve every accepted capture field (including converter lineage) from
    # the already validated snapshot; do not regenerate timestamps or serialize.
    capture = dict(source["capture"])
    return {
        "status": "AVAILABLE" if any(rep["retention"] == "retained" for rep in source["representations"]) else "UNAVAILABLE",
        "source_id": source["source_id"],
        "original_revision": dict(source["original_revision"]),
        "original_retention": source["original_retention"],
        "capture": capture,
        "representations": representations,
        "original_availability": (
            "original-retained-verified" if source["original_retention"] == "retained"
            else "original-reference-only" if source["original_retention"] == "reference-only"
            else "original-unknown"
        ),
    }
