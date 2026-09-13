"""Safely manage one repository-governance block in AGENTS.md."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from typing import NamedTuple, Optional, Tuple, Union


START_MARKER = "<!-- kb-bootstrap:repository-governance:start -->"
END_MARKER = "<!-- kb-bootstrap:repository-governance:end -->"
_START_BYTES = START_MARKER.encode("utf-8")
_END_BYTES = END_MARKER.encode("utf-8")


class _Observation(NamedTuple):
    identity: Tuple[int, int]
    mode: int
    content: bytes


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


def _traverses_symlink(path: Path) -> bool:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            return True
    return False


def _contained_target(
    file_path: Union[str, Path], project_root: Union[str, Path]
) -> Tuple[Optional[Path], str]:
    raw_root = Path(project_root).absolute()
    relative = Path(file_path)
    if "\x00" in str(file_path):
        return None, "managed file path is invalid"
    if relative.is_absolute() or ".." in relative.parts:
        return None, "managed file path must be relative and contained"
    if _traverses_symlink(raw_root):
        return None, "project root traverses a symlink"
    root = raw_root.resolve()
    if not root.is_dir():
        return None, "project root is unavailable"
    target = root / relative
    if _traverses_symlink(target):
        return None, "managed file path traverses a symlink"
    try:
        target.resolve().relative_to(root)
    except ValueError:
        return None, "managed file path is outside the project root"
    if not target.parent.is_dir():
        return None, "managed file parent directory is unavailable"
    if _traverses_symlink(target.parent):
        return None, "managed file parent traverses a symlink"
    if target.exists() and not target.is_file():
        return None, "managed file is not a regular file"
    return target, ""


def _identity(path: Path) -> Tuple[int, int]:
    details = path.stat(follow_symlinks=False)
    return details.st_dev, details.st_ino


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink() and not _traverses_symlink(path)


def _observe(path: Path) -> Tuple[Optional[_Observation], str]:
    if path.is_symlink() or _traverses_symlink(path) or not path.is_file():
        return None, "managed file is unavailable or unsafe"
    try:
        before = path.stat(follow_symlinks=False)
        content = path.read_bytes()
        after = path.stat(follow_symlinks=False)
    except OSError:
        return None, "managed file is unavailable or unsafe"
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        return None, "managed file changed while being read"
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return None, "managed file is not valid UTF-8"
    return _Observation(
        (after.st_dev, after.st_ino), stat.S_IMODE(after.st_mode), content
    ), ""


def _updated_content(existing: bytes, repository: str) -> Tuple[Optional[bytes], str]:
    start_count = existing.count(_START_BYTES)
    end_count = existing.count(_END_BYTES)
    if start_count != end_count or start_count > 1:
        return None, "AGENTS.md has malformed or conflicting governance markers"
    if start_count == 1 and existing.index(_END_BYTES) < existing.index(_START_BYTES):
        return None, "AGENTS.md has malformed or conflicting governance markers"

    block = governance_block(repository).encode("utf-8")
    if start_count == 1:
        start = existing.index(_START_BYTES)
        end = existing.index(_END_BYTES, start) + len(_END_BYTES)
        return existing[:start] + block + existing[end:], ""
    if not existing:
        return block + b"\n", ""
    separator = b"\n" if existing.endswith(b"\n") else b"\n\n"
    return existing + separator + block + b"\n", ""


def _source_matches(path: Path, observation: _Observation) -> bool:
    current, error = _observe(path)
    return not error and current == observation


def _write_staged(
    parent: Path,
    content: bytes,
    mode: Optional[int],
    parent_identity: Tuple[int, int],
) -> Path:
    if (
        parent.is_symlink()
        or _traverses_symlink(parent)
        or _identity(parent) != parent_identity
    ):
        raise OSError("unsafe parent")
    descriptor, name = tempfile.mkstemp(
        prefix=".kb-bootstrap-agents-", suffix=".tmp", dir=str(parent)
    )
    path = Path(name)
    try:
        if (
            parent.is_symlink()
            or _traverses_symlink(parent)
            or _identity(parent) != parent_identity
        ):
            raise OSError("parent changed during staging")
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            path.chmod(mode)
        return path
    except BaseException:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def update_agents_file(
    path: Union[str, Path],
    repository: str,
    project_root: Union[str, Path] = Path("."),
) -> Tuple[str, bool]:
    """Create or replace the managed block inside one contained AGENTS.md file."""
    target, path_error = _contained_target(path, project_root)
    if path_error or target is None:
        return f"RESULT: BLOCKED ({path_error})", False

    existed = target.exists()
    observation: Optional[_Observation] = None
    existing = b""
    if existed:
        observation, observation_error = _observe(target)
        if observation_error or observation is None:
            return f"RESULT: BLOCKED ({observation_error})", False
        existing = observation.content

    updated, marker_error = _updated_content(existing, repository)
    if marker_error or updated is None:
        return f"RESULT: BLOCKED ({marker_error})", False
    if updated == existing:
        return "AGENTS.md governance block is already current", True

    staged: Optional[Path] = None
    created_target: Optional[Tuple[Path, Tuple[int, int]]] = None
    cleanup_failed = False
    parent_identity = _identity(target.parent)
    try:
        staged = _write_staged(
            target.parent,
            updated,
            observation.mode if observation is not None else None,
            parent_identity,
        )
        if (
            target.parent.is_symlink()
            or _traverses_symlink(target.parent)
            or _identity(target.parent) != parent_identity
        ):
            raise OSError("unsafe parent")
        if existed:
            if observation is None or not _source_matches(target, observation):
                return "RESULT: BLOCKED (AGENTS.md changed before replacement)", False
            os.replace(staged, target)
            staged = None
        else:
            if target.exists() or target.is_symlink():
                return "RESULT: BLOCKED (AGENTS.md appeared before creation)", False
            installed_identity = _identity(staged)
            os.link(staged, target)
            created_target = (target, installed_identity)
            staged.unlink()
            staged = None
            created_target = None
    except OSError:
        if created_target is not None:
            created, installed_identity = created_target
            try:
                if (
                    _regular_file(created)
                    and _identity(created) == installed_identity
                ):
                    created.unlink()
                else:
                    cleanup_failed = True
            except OSError:
                cleanup_failed = True
        if staged is not None:
            try:
                staged.unlink(missing_ok=True)
            except OSError:
                cleanup_failed = True
            staged = None
        result = "RESULT: BLOCKED (AGENTS.md cannot be updated atomically"
        if cleanup_failed:
            result += "; cleanup is incomplete"
        return result + ")", False
    finally:
        if staged is not None:
            try:
                staged.unlink(missing_ok=True)
            except OSError:
                pass

    return "AGENTS.md governance block updated", True
