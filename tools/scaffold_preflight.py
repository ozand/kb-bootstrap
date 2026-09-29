"""Prototype read-only preflight for the ordinary scaffold-managed file set.

This diagnostic building block is intentionally not wired into the public CLI.
It compares only three generated QMD payloads, three single-file skills, and the
installed ``market-research`` package tree.  Lesson, AGENTS, and gitignore
checks remain delegated and are not performed here; even an all-matching result
is therefore not authorization to initialize or update a scaffold.

The inspector uses directory descriptors and ``O_NOFOLLOW`` when the platform
provides them.  These checks bound reads and narrow symlink races, but cannot
make a multi-path snapshot or prevent a concurrent writer changing a file after
it has been checked.  Platforms lacking the required descriptor operations
report affected comparisons as ``unavailable`` rather than following paths.
"""

from __future__ import annotations

import errno
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping


GENERATED_QMD_PATHS = frozenset(
    {"qmd.json", "qmd/collections/wiki.yaml", "qmd/collections/raw.yaml"}
)
_SINGLE_SKILLS = ("kb-wiki-builder", "qmd-operator", "kb-lookup")
STATUSES = frozenset({"matching", "content-differs", "missing", "unsafe", "unavailable"})


@dataclass(frozen=True, order=True)
class Inspection:
    """One sanitized result; ``path`` is always a validated relative name."""

    path: str
    status: str


def _managed_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError("invalid managed path")
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or not path.parts
        or name != path.as_posix()
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ValueError("invalid managed path")
    return name



def _inventory_files(root: Path) -> tuple[Path, ...]:
    """Enumerate trusted regular files deterministically and fail on incomplete traversal."""
    files: list[Path] = []
    pending = [Path(root)]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as scan:
            entries = sorted(scan, key=lambda entry: entry.name)
        child_directories: list[Path] = []
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root)
            if "__pycache__" in relative.parts:
                continue
            if entry.is_symlink():
                raise ValueError("trusted inventory contains an unsafe entry")
            if entry.is_dir(follow_symlinks=False):
                child_directories.append(path)
                continue
            if entry.is_file(follow_symlinks=False):
                if path.suffix != ".pyc":
                    files.append(path)
                continue
            raise ValueError("trusted inventory contains an unsafe entry")
        pending.extend(reversed(child_directories))
    return tuple(files)

def _build_managed_file_map(
    installed_package_root: Path,
    generated_qmd_payloads: Mapping[str, bytes],
) -> dict[str, bytes]:
    """Return expected bytes for the bounded ordinary managed-file inventory.

    ``installed_package_root`` is the trusted ``kb_bootstrap`` package directory.
    The consumer tree is never consulted.  Exactly the three current generated
    QMD destinations must be supplied by the caller.
    """

    if set(generated_qmd_payloads) != GENERATED_QMD_PATHS:
        raise ValueError("generated QMD payloads must contain exactly the three expected paths")

    result: dict[str, bytes] = {}
    for name, payload in generated_qmd_payloads.items():
        name = _managed_name(name)
        if not isinstance(payload, bytes):
            raise TypeError("managed payload must be bytes")
        result[name] = payload

    skills = Path(installed_package_root) / "templates" / "skills"
    sources: list[tuple[Path, str]] = [
        (skills / skill / "SKILL.md", f".agents/skills/{skill}/SKILL.md")
        for skill in _SINGLE_SKILLS
    ]
    market = skills / "market-research"
    entrypoint = market / "SKILL.md"
    if (market.is_symlink() or not market.is_dir()
            or entrypoint.is_symlink() or not entrypoint.is_file()):
        raise ValueError("required research inventory is unavailable")
    for source in _inventory_files(market):
        relative = source.relative_to(market)
        sources.append((source, f".agents/skills/market-research/{relative.as_posix()}"))

    for source, destination in sources:
        destination = _managed_name(destination)
        if source.is_symlink() or not source.is_file():
            raise ValueError("trusted inventory file is unavailable")
        result[destination] = source.read_bytes()
    return dict(sorted(result.items()))


def build_managed_file_map(
    installed_package_root: Path,
    generated_qmd_payloads: Mapping[str, bytes],
) -> dict[str, bytes]:
    """Build the trusted fixed inventory, returning only sanitized failures."""
    try:
        return _build_managed_file_map(installed_package_root, generated_qmd_payloads)
    except OSError:
        raise ValueError("trusted inventory is unavailable") from None


def _descriptor_support() -> bool:
    return (all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK"))
            and os.open in os.supports_dir_fd)


def _open_target(target: Path) -> int:
    """Traverse every component without resolving through an ancestor symlink."""
    path = Path(target)
    if not path.is_absolute():
        path = Path.cwd() / path
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            following = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _classify_at(root_fd: int, name: str, expected: bytes, size_limit: int) -> str:
    if len(expected) > size_limit:
        return "unavailable"
    try:
        directory_fd = os.dup(root_fd)
    except OSError:
        return "unavailable"
    try:
        parts = PurePosixPath(name).parts
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        for part in parts[:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        file_fd = os.open(parts[-1], flags, dir_fd=directory_fd)
        try:
            info = os.fstat(file_fd)
            if not stat.S_ISREG(info.st_mode):
                return "unsafe"
            if info.st_size > size_limit:
                return "unavailable"
            chunks: list[bytes] = []
            remaining = size_limit + 1
            while remaining:
                chunk = os.read(file_fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            actual = b"".join(chunks)
            if len(actual) > size_limit:
                return "unavailable"
            return "matching" if actual == expected else "content-differs"
        finally:
            os.close(file_fd)
    except FileNotFoundError:
        return "missing"
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            return "unsafe"
        return "unavailable"
    finally:
        os.close(directory_fd)


def inspect_managed_files(
    target: Path,
    managed_files: Mapping[str, bytes],
    *,
    size_limit: int,
) -> tuple[Inspection, ...]:
    """Inspect only ``managed_files`` below ``target`` without modifying either.

    Results are deterministically sorted and contain no contents or absolute
    paths.  A missing target produces ``missing`` for every managed destination.
    """

    if not isinstance(size_limit, int) or isinstance(size_limit, bool) or size_limit < 0:
        raise ValueError("size_limit must be a non-negative integer")
    expected: dict[str, bytes] = {}
    for name, payload in managed_files.items():
        name = _managed_name(name)
        if not isinstance(payload, bytes):
            raise TypeError("managed payload must be bytes")
        if name in expected:
            raise ValueError("duplicate managed path")
        expected[name] = payload

    if not _descriptor_support():
        return tuple(Inspection(name, "unavailable") for name in sorted(expected))

    try:
        root_fd = _open_target(target)
    except FileNotFoundError:
        return tuple(Inspection(name, "missing") for name in sorted(expected))
    except OSError as error:
        status = "unsafe" if error.errno in (errno.ELOOP, errno.ENOTDIR) else "unavailable"
        return tuple(Inspection(name, status) for name in sorted(expected))
    try:
        return tuple(
            Inspection(name, _classify_at(root_fd, name, expected[name], size_limit))
            for name in sorted(expected)
        )
    finally:
        os.close(root_fd)
