"""Validate sanitized shared lesson applicability/provenance metadata."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PROJECT_LESSON_PATTERN = re.compile(r"^PROJECT-\d{4}$")
VALID_SCOPES = {"workspace", "project"}


def _repository(value: Any) -> bool:
    if not isinstance(value, str) or not REPOSITORY_PATTERN.fullmatch(value):
        return False
    owner, repository = value.split("/", 1)
    return owner not in {".", ".."} and repository not in {".", ".."}


def validate_metadata(metadata: Dict[str, Any], legacy_ok: bool = False) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    scope = metadata.get("scope")

    if scope is None and legacy_ok:
        warnings.append("legacy lesson metadata has no scope")
        return errors, warnings
    if scope not in VALID_SCOPES:
        errors.append("scope must be workspace or project")

    source = metadata.get("source_repository")
    if not _repository(source):
        errors.append("source_repository must use sanitized owner/repository syntax")

    observed = metadata.get("observed_in")
    if not isinstance(observed, list) or not observed:
        errors.append("observed_in must contain at least one repository")
    elif any(not _repository(item) for item in observed):
        errors.append("observed_in entries must use sanitized owner/repository syntax")
    elif len(set(observed)) != len(observed):
        errors.append("observed_in entries must be unique")

    applies_to = metadata.get("applies_to")
    if scope == "project" and (not isinstance(applies_to, list) or not applies_to):
        errors.append("project scope requires non-empty applies_to")
    if applies_to is not None:
        if not isinstance(applies_to, list) or any(
            not _repository(item) for item in applies_to
        ):
            errors.append("applies_to entries must use sanitized owner/repository syntax")
        elif len(set(applies_to)) != len(applies_to):
            errors.append("applies_to entries must be unique")

    promoted = metadata.get("promoted_from")
    if promoted is not None:
        if not isinstance(promoted, dict):
            errors.append("promoted_from must be null or an object")
        elif (
            not _repository(promoted.get("repository"))
            or not isinstance(promoted.get("lesson_id"), str)
            or not PROJECT_LESSON_PATTERN.fullmatch(promoted.get("lesson_id", ""))
        ):
            errors.append("promoted_from requires repository and PROJECT-XXXX lesson_id")

    return errors, warnings


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_shared_metadata.py <metadata.json>")
        return 2

    path = Path(argv[1])
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("RESULT: BLOCKED (metadata is unavailable or invalid JSON)")
        return 1

    if not isinstance(metadata, dict):
        print("RESULT: BLOCKED (metadata must be an object)")
        return 1

    errors, warnings = validate_metadata(metadata)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        print(f"RESULT: BLOCKED ({len(errors)} error(s))")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("RESULT: OK")
    print(f"scope: {metadata['scope']}")
    print("provenance: sanitized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
