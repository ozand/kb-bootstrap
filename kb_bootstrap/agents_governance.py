"""Safely manage one repository-governance block in AGENTS.md."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple


START_MARKER = "<!-- kb-bootstrap:repository-governance:start -->"
END_MARKER = "<!-- kb-bootstrap:repository-governance:end -->"


def governance_block(repository: str) -> str:
    return "\n".join(
        [
            START_MARKER,
            "## Repository routing and completion safety",
            "",
            f"- Expected repository: `{repository}`.",
            f"- Run `kb-bootstrap doctor --repo {repository}` before GitHub mutations.",
            "- Use explicit `--repo` for every mutating `gh` command.",
            "- Keep consumer-specific work in the consumer repository; use a separate verified checkout or worktree for upstream framework changes.",
            f"- Before completion claims, run `kb-bootstrap check-completion --repo {repository} --commit <commit> [--pr <number>]`.",
            "- Fail closed on missing or mismatched repository, branch, pull request, or commit evidence.",
            "- Never include credentials, private payloads, runtime checkpoints, or unsanitized logs in receipts.",
            END_MARKER,
        ]
    )


def update_agents_file(path: Path, repository: str) -> Tuple[str, bool]:
    """Create or replace the managed block; preserve all other bytes exactly."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    start_count = existing.count(START_MARKER)
    end_count = existing.count(END_MARKER)

    if start_count != end_count or start_count > 1:
        return "AGENTS.md has malformed or conflicting governance markers", False
    if start_count == 1 and existing.index(END_MARKER) < existing.index(START_MARKER):
        return "AGENTS.md has malformed or conflicting governance markers", False

    block = governance_block(repository)
    if start_count == 1:
        start = existing.index(START_MARKER)
        end = existing.index(END_MARKER, start) + len(END_MARKER)
        updated = existing[:start] + block + existing[end:]
    else:
        if not existing:
            updated = block + "\n"
        else:
            separator = "\n" if existing.endswith("\n") else "\n\n"
            updated = existing + separator + block + "\n"

    if updated == existing:
        return "AGENTS.md governance block is already current", True

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return f"AGENTS.md governance block updated: {path}", True
