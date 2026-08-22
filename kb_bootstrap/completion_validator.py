"""Read-only completion commit validation for GitHub Issues and pull requests."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _run(command: List[str], cwd: Path) -> Tuple[str, bool]:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip(), result.returncode == 0


def _compare_status(repository: str, base: str, head: str, cwd: Path) -> Optional[str]:
    output, ok = _run(
        [
            "gh",
            "api",
            f"repos/{repository}/compare/{base}...{head}",
            "--jq",
            ".status",
        ],
        cwd,
    )
    return output if ok and output in {"ahead", "behind", "diverged", "identical"} else None


def validate_completion(
    repository: str,
    commit: str,
    pull_request: Optional[int] = None,
    cwd: Path = Path("."),
) -> Tuple[str, bool]:
    """Accept a commit only when reachable from the target default branch or PR."""
    working_directory = cwd.resolve()
    errors: List[str] = []
    repository = repository.strip()
    commit = commit.strip()

    if not REPOSITORY_PATTERN.fullmatch(repository):
        errors.append("repository is missing or invalid; use owner/repository")
    if not COMMIT_PATTERN.fullmatch(commit):
        errors.append("commit is missing or invalid; use a 7-40 character hexadecimal ID")
    if pull_request is not None and pull_request < 1:
        errors.append("pull request number must be positive")

    default_branch = None
    canonical_commit = None
    default_reachable = False
    pr_reachable = False
    pr_url = None

    if not errors:
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
            working_directory,
        )
        if repository_ok and "\t" in repository_view:
            viewed_repository, default_branch = repository_view.split("\t", 1)
            if viewed_repository != repository:
                errors.append("GitHub repository identity does not match target")
        else:
            errors.append("GitHub repository identity or default branch is unavailable")

    if not errors:
        canonical_commit, commit_ok = _run(
            [
                "gh",
                "api",
                f"repos/{repository}/commits/{commit}",
                "--jq",
                ".sha",
            ],
            working_directory,
        )
        if not commit_ok or not re.fullmatch(r"[0-9a-fA-F]{40}", canonical_commit):
            canonical_commit = None
            errors.append("commit is not available in the target repository")

    if not errors and canonical_commit and default_branch:
        status = _compare_status(
            repository, canonical_commit, default_branch, working_directory
        )
        default_reachable = status in {"ahead", "identical"}

    if not default_reachable and not errors and pull_request is not None:
        pr_view, pr_ok = _run(
            [
                "gh",
                "pr",
                "view",
                str(pull_request),
                "--repo",
                repository,
                "--json",
                "baseRepository,headRefOid,url",
                "--jq",
                '"\\(.baseRepository.nameWithOwner)\\t\\(.headRefOid)\\t\\(.url)"',
            ],
            working_directory,
        )
        if pr_ok and pr_view.count("\t") == 2:
            pr_repository, pr_head, pr_url = pr_view.split("\t", 2)
            if pr_repository != repository:
                errors.append("pull request base repository does not match target")
            elif not re.fullmatch(r"[0-9a-fA-F]{40}", pr_head):
                errors.append("pull request head commit is unavailable")
            else:
                status = _compare_status(
                    repository, canonical_commit, pr_head, working_directory
                )
                pr_reachable = status in {"ahead", "identical"}
        else:
            errors.append("associated pull request is unavailable")

    if not errors and not default_reachable and not pr_reachable:
        errors.append(
            "commit is not reachable from the default branch or associated pull request"
        )

    lines = [
        "=== Completion Validation ===",
        f"repository: {repository or 'missing'}",
        f"commit: {canonical_commit or commit or 'missing'}",
        f"default branch: {default_branch or 'unavailable'}",
        f"default reachable: {'yes' if default_reachable else 'no'}",
        f"pull request: {pull_request if pull_request is not None else 'not provided'}",
        f"pull request reachable: {'yes' if pr_reachable else 'no'}",
    ]
    if pr_url:
        lines.append(f"pull request URL: {pr_url}")
    if errors:
        lines.append(f"RESULT: BLOCKED ({len(errors)} error(s))")
        lines.extend(f"  - {error}" for error in errors)
    else:
        lines.append("RESULT: OK")
    return "\n".join(lines), not errors
