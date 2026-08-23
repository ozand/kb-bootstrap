"""Prepare and validate sanitized shared lesson contribution candidates locally."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
ID_PATTERN = re.compile(r"^(?:KB|PROJECT)-\d{4}$")
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(token|password|secret|api[_-]?key|authorization)\s*[:=]"),
    re.compile(r"(?i)bearer\s+\S+"),
    re.compile(r"(?i)[a-z][a-z0-9+.-]*://[^\s/@]+:[^\s/@]+@"),
    re.compile(r"[A-Za-z]:[\\/]"),
    re.compile(r"(?:^|\s)/{1,2}\S+"),
    re.compile(r"(?:^|\s)\\{1,2}\S+"),
    re.compile(r"(?i)(session|checkpoint|runtime)[_-]?id\s*[:=]"),
]


def _repository(value: Any) -> bool:
    if not isinstance(value, str) or not REPOSITORY_PATTERN.fullmatch(value):
        return False
    owner, repository = value.split("/", 1)
    return owner not in {".", ".."} and repository not in {".", ".."}


def validate_candidate(candidate: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    target = candidate.get("target")
    metadata = candidate.get("metadata")
    content = candidate.get("content")
    preflight = candidate.get("preflight")

    if not isinstance(target, dict):
        errors.append("target must be an object")
    else:
        if not _repository(target.get("repository")):
            errors.append("target repository must use owner/repository syntax")
        branch = target.get("branch")
        if not isinstance(branch, str) or not BRANCH_PATTERN.fullmatch(branch) or branch.startswith(("/", ".")) or ".." in branch:
            errors.append("target branch is missing or invalid")
        destination = target.get("destination")
        if not isinstance(destination, str) or destination != "workspace-global-lessons":
            errors.append("target destination must be workspace-global-lessons")

    if not isinstance(preflight, dict):
        errors.append("preflight must be an object")
    else:
        if preflight.get("authenticated") is not True:
            errors.append("authenticated preflight is required")
        if preflight.get("repository_match") is not True:
            errors.append("repository preflight does not match target")
        if preflight.get("human_confirmed") is not True:
            errors.append("human confirmation is required")

    if not isinstance(metadata, dict):
        errors.append("metadata must be an object")
    else:
        if metadata.get("scope") != "workspace":
            errors.append("candidate scope must be workspace")
        if not _repository(metadata.get("source_repository")):
            errors.append("source_repository must use owner/repository syntax")
        observed = metadata.get("observed_in")
        if not isinstance(observed, list) or not observed or any(not _repository(item) for item in observed):
            errors.append("observed_in must contain sanitized repositories")
        elif len(set(observed)) != len(observed):
            errors.append("observed_in entries must be unique")
        promoted = metadata.get("promoted_from")
        if not isinstance(promoted, dict) or not _repository(promoted.get("repository")) or not isinstance(promoted.get("lesson_id"), str) or not ID_PATTERN.fullmatch(promoted.get("lesson_id", "")):
            errors.append("promoted_from must contain repository and lesson ID")

    if not isinstance(content, dict):
        errors.append("content must be an object")
    else:
        for field in ("title", "problem", "resolution", "prevention"):
            value = content.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"content {field} is required")
            elif any(pattern.search(value) for pattern in SENSITIVE_PATTERNS):
                errors.append(f"content {field} failed sanitization")

    return errors


def prepare_candidate(
    input_path: Union[str, Path], output_path: Union[str, Path]
) -> Tuple[str, bool]:
    source = Path(input_path)
    output = Path(output_path)
    if output.exists():
        return "RESULT: BLOCKED (candidate output already exists)", False
    try:
        candidate = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "RESULT: BLOCKED (candidate input is unavailable or invalid JSON)", False
    if not isinstance(candidate, dict):
        return "RESULT: BLOCKED (candidate input must be an object)", False

    errors = validate_candidate(candidate)
    if errors:
        lines = [f"RESULT: BLOCKED ({len(errors)} error(s))"]
        lines.extend(f"  - {error}" for error in errors)
        return "\n".join(lines), False

    prepared = {
        "version": 1,
        "status": "prepared-for-review",
        "target": {
            "repository": candidate["target"]["repository"],
            "branch": candidate["target"]["branch"],
            "destination": candidate["target"]["destination"],
        },
        "metadata": {
            "scope": candidate["metadata"]["scope"],
            "source_repository": candidate["metadata"]["source_repository"],
            "observed_in": candidate["metadata"]["observed_in"],
            "promoted_from": {
                "repository": candidate["metadata"]["promoted_from"]["repository"],
                "lesson_id": candidate["metadata"]["promoted_from"]["lesson_id"],
            },
        },
        "content": {
            field: candidate["content"][field]
            for field in ("title", "problem", "resolution", "prevention")
        },
        "receipt": {
            "repository": candidate["target"]["repository"],
            "branch": candidate["target"]["branch"],
            "destination": candidate["target"]["destination"],
            "preflight": "verified",
            "human_confirmation": "verified",
            "outcome": "prepared-for-review",
        },
    }
    if not output.parent.is_dir():
        return "RESULT: BLOCKED (candidate output parent is unavailable)", False
    try:
        with output.open("x", encoding="utf-8") as file:
            file.write(json.dumps(prepared, indent=2, sort_keys=True) + "\n")
    except FileExistsError:
        return "RESULT: BLOCKED (candidate output already exists)", False
    except OSError:
        return "RESULT: BLOCKED (candidate output cannot be created)", False
    return "\n".join(
        [
            "RESULT: OK",
            f"repository: {prepared['receipt']['repository']}",
            f"branch: {prepared['receipt']['branch']}",
            f"destination: {prepared['receipt']['destination']}",
            "outcome: prepared-for-review",
            "shared store write: no",
            "pull request created: no",
        ]
    ), True
