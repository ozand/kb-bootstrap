"""Generate and validate a sanitized repository-context manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .repository_doctor import REPOSITORY_PATTERN, _repository_from_remote, _run


SCHEMA_VERSION = 1
REQUIRED_KEYS = {
    "schema_version",
    "repository",
    "default_branch",
    "remotes",
}


def build_manifest(repository: str, cwd: Path = Path(".")) -> Tuple[Dict, List[str]]:
    """Build deterministic non-sensitive context for the explicitly named repository."""
    working_directory = cwd.resolve()
    errors: List[str] = []
    repository = repository.strip()

    if not REPOSITORY_PATTERN.fullmatch(repository):
        return {}, ["repository is missing or invalid; use owner/repository"]

    root_text, root_ok = _run(["git", "rev-parse", "--show-toplevel"], working_directory)
    command_cwd = Path(root_text).resolve() if root_ok else working_directory
    if not root_ok:
        errors.append("Git root is unavailable")

    repository_view, repository_ok = _run(
        [
            "gh",
            "repo",
            "view",
            repository,
            "--json",
            "nameWithOwner,defaultBranchRef",
            "--jq",
            '"\\(.nameWithOwner)\\t\\(.defaultBranchRef.name)"',
        ],
        command_cwd,
    )
    default_branch: Optional[str] = None
    if repository_ok and "\t" in repository_view:
        viewed_repository, default_branch = repository_view.split("\t", 1)
        if viewed_repository != repository:
            errors.append("GitHub repository identity does not match target")
    else:
        errors.append("GitHub repository identity or default branch is unavailable")

    remotes = {}
    for role in ("origin", "upstream"):
        remote_text, remote_ok = _run(
            ["git", "remote", "get-url", role], command_cwd
        )
        remote_repository = _repository_from_remote(remote_text) if remote_ok else None
        if remote_repository:
            remotes[role] = {"repository": remote_repository}
        elif role == "origin":
            errors.append("origin is missing, unsupported, or ambiguous")

    if remotes.get("origin", {}).get("repository") != repository:
        errors.append("origin does not match target repository")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "default_branch": default_branch,
        "remotes": remotes,
    }
    return manifest, errors


def validate_manifest(manifest: Dict) -> List[str]:
    """Return deterministic schema errors without reading local runtime state."""
    errors: List[str] = []
    if set(manifest) != REQUIRED_KEYS:
        errors.append("manifest keys do not match schema")
        return errors
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    repository = manifest.get("repository")
    if not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(repository):
        errors.append("repository must use owner/repository format")
    default_branch = manifest.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        errors.append("default_branch must be a non-empty string")
    remotes = manifest.get("remotes")
    if not isinstance(remotes, dict) or "origin" not in remotes:
        errors.append("remotes must contain origin")
    elif remotes.get("origin") != {"repository": repository}:
        errors.append("origin repository must match repository")
    if isinstance(remotes, dict):
        for role, value in remotes.items():
            if role not in {"origin", "upstream"}:
                errors.append(f"unsupported remote role: {role}")
            if not isinstance(value, dict) or set(value) != {"repository"}:
                errors.append(f"remote {role} must contain only repository")
            elif not REPOSITORY_PATTERN.fullmatch(str(value.get("repository", ""))):
                errors.append(f"remote {role} repository is invalid")
    return errors


def write_manifest(repository: str, output: Path, cwd: Path = Path(".")) -> Tuple[str, bool]:
    manifest, errors = build_manifest(repository, cwd)
    if not errors:
        errors.extend(validate_manifest(manifest))
    if errors:
        lines = ["Repository context manifest not written:"]
        lines.extend(f"  - {error}" for error in errors)
        return "\n".join(lines), False

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return f"Repository context manifest written: {output}", True


def validate_manifest_file(path: Path) -> Tuple[str, bool]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return f"Repository context manifest is unreadable: {error}", False
    if not isinstance(manifest, dict):
        return "Repository context manifest root must be an object", False
    errors = validate_manifest(manifest)
    if errors:
        lines = ["Repository context manifest is invalid:"]
        lines.extend(f"  - {error}" for error in errors)
        return "\n".join(lines), False
    return "Repository context manifest is valid", True
