"""Read-only repository identity preflight for GitHub-backed work."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _run(command: List[str], cwd: Path) -> Tuple[str, bool]:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip(), result.returncode == 0


def _repository_from_remote(remote: str) -> Optional[str]:
    """Return owner/name without exposing credentials or transport details."""
    value = remote.strip().replace("\\", "/")
    if not value:
        return None
    if value.endswith(".git"):
        value = value[:-4]
    if "github.com/" in value:
        value = value.split("github.com/", 1)[1]
    elif "github.com:" in value:
        value = value.split("github.com:", 1)[1]
    else:
        return None
    repository = "/".join(value.strip("/").split("/")[-2:])
    return repository if REPOSITORY_PATTERN.fullmatch(repository) else None


def inspect_repository(
    requested_target: Optional[str], cwd: Path = Path("."),
) -> Tuple[str, bool]:
    """Return a sanitized report and fail closed on missing or mismatched identity."""
    working_directory = cwd.resolve()
    errors: List[str] = []

    git_root_text, git_root_ok = _run(
        ["git", "rev-parse", "--show-toplevel"], working_directory
    )
    git_root = Path(git_root_text).resolve() if git_root_ok else None
    command_cwd = git_root or working_directory

    origin_text, origin_ok = _run(
        ["git", "remote", "get-url", "origin"], command_cwd
    )
    upstream_text, upstream_ok = _run(
        ["git", "remote", "get-url", "upstream"], command_cwd
    )
    gh_default, gh_default_ok = _run(
        ["gh", "repo", "set-default", "--view"], command_cwd
    )
    origin = _repository_from_remote(origin_text) if origin_ok else None
    upstream = _repository_from_remote(upstream_text) if upstream_ok else None

    target = requested_target.strip() if requested_target else ""
    if not target or not REPOSITORY_PATTERN.fullmatch(target):
        errors.append("requested target is missing or invalid; use owner/repository")

    default_branch = None
    if target and REPOSITORY_PATTERN.fullmatch(target):
        repository_view, view_ok = _run(
            [
                "gh",
                "repo",
                "view",
                target,
                "--json",
                "nameWithOwner,defaultBranchRef",
                "--jq",
                '"\\(.nameWithOwner)\\t\\(.defaultBranchRef.name)"',
            ],
            command_cwd,
        )
        if view_ok and "\t" in repository_view:
            viewed_repository, default_branch = repository_view.split("\t", 1)
            if viewed_repository != target:
                errors.append("GitHub repository identity does not match requested target")
        else:
            errors.append("GitHub repository identity or default branch is unavailable")

    local_default, local_default_ok = _run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        command_cwd,
    )
    if local_default_ok and local_default.startswith("origin/"):
        local_default = local_default.split("/", 1)[1]
    else:
        local_default = None

    if not git_root_ok:
        errors.append("Git root is unavailable")
    if not origin:
        errors.append("origin is missing, unsupported, or ambiguous")
    elif target and origin != target:
        errors.append("origin does not match requested target")
    if not gh_default_ok or not REPOSITORY_PATTERN.fullmatch(gh_default):
        errors.append("gh default repository is missing or ambiguous")
    elif target and gh_default != target:
        errors.append("gh default repository does not match requested target")
    if not local_default:
        errors.append("local origin default branch is unavailable")
    elif default_branch and local_default != default_branch:
        errors.append("local origin default branch does not match GitHub")

    lines = [
        "=== Repository Doctor ===",
        f"cwd: {working_directory}",
        f"git root: {git_root if git_root else 'unavailable'}",
        f"origin: {origin or 'unavailable'}",
        f"upstream: {upstream or 'not configured'}",
        f"gh default: {gh_default if gh_default_ok else 'unavailable'}",
        f"requested target: {target or 'missing'}",
        f"default branch: {default_branch or 'unavailable'}",
        f"local origin default: {local_default or 'unavailable'}",
    ]
    if errors:
        lines.append(f"RESULT: BLOCKED ({len(errors)} error(s))")
        lines.extend(f"  - {error}" for error in errors)
    else:
        lines.append("RESULT: OK")
    return "\n".join(lines), not errors
