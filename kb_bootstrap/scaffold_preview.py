"""Read-only current-package scaffold preview implementing ADR-046."""
from __future__ import annotations

import os
import stat
from pathlib import Path

from .project_lesson_enablement import inspect_project_lessons
from .qmd_names import project_slug
from .scaffold_repeat import (
    _classify_file, _components_safe, _inventory_files, qmd_payloads,
)

CORE_FILES = (
    ".agents/skills/kb-wiki-builder/SKILL.md", ".gitignore",
    "kb/raw/.gitkeep", "kb/research/.gitkeep",
    "kb/wiki/entities/.gitkeep", "kb/wiki/concepts/.gitkeep",
    "kb/wiki/reports/.gitkeep",
)
CORE_DIRS = (
    ".agents", ".agents/skills", ".agents/skills/kb-wiki-builder",
    "kb", "kb/raw", "kb/research", "kb/wiki", "kb/wiki/entities",
    "kb/wiki/concepts", "kb/wiki/reports",
)


def _target_state(target: Path):
    raw = Path(os.path.abspath(os.fspath(target)))
    if ".." in target.parts or not _components_safe(raw):
        return None
    current = Path(raw.anchor)
    for part in raw.parts[1:]:
        current /= part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return raw
        except OSError:
            return None
        if current != raw and not stat.S_ISDIR(info.st_mode):
            return None
    try:
        info = os.lstat(raw)
    except FileNotFoundError:
        return raw
    except OSError:
        return None
    if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        return None
    return raw


def _expected(target: Path, package_root: Path, layout: str, core_only: bool):
    if core_only:
        result = {}
        result[CORE_FILES[0]] = (package_root / "templates/skills/kb-wiki-builder/SKILL.md").read_bytes()
        result[".gitignore"] = b"\n# kb-bootstrap generated artifacts\n/models/\n/artifacts/\n/kb/raw/**/*.log\n/kb/raw/**/*.bin\n/kb/raw/**/*.jsonl\n"
        for relative in CORE_FILES[2:]:
            result[relative] = b""
        if layout == "umbrella":
            for relative in ("kb/apps/.gitkeep", "kb/systems/.gitkeep", "kb/architecture/.gitkeep"):
                result[relative] = b""
        return dict(sorted(result.items()))
    result = qmd_payloads(layout, project_slug(target.name))
    result.update(_inventory_files(package_root))
    return dict(sorted(result.items()))


def preview(target_arg: str, package_root: Path, layout: str, core_only: bool = False):
    """Return stable sanitized text and status; never writes or walks the target."""
    target = Path(target_arg)
    root = _target_state(target)
    if root is None:
        lines = ["RESULT: BLOCKED", "unsafe: target"]
        counts = {name: 0 for name in ("matching", "missing", "content differs", "unsafe", "unavailable")}
        counts["unsafe"] = 1
        return _report(lines, counts), 1
    try:
        expected = _expected(root, package_root, layout, core_only)
    except (OSError, ValueError):
        counts = {name: 0 for name in ("matching", "missing", "content differs", "unsafe", "unavailable")}
        counts["unavailable"] = 1
        return _report(["unavailable: package inventory", "RESULT: BLOCKED"], counts), 1

    entries = []
    exists = root.exists()
    for name, payload in expected.items():
        state = _classify_file(root, name, payload) if exists else "missing"
        entries.append((name, state))
    lesson_state = "valid"
    if exists and not core_only:
        lesson_state, _ = inspect_project_lessons(root, package_root, require_initialized=False)
        if lesson_state == "blocked":
            entries.append(("delegated lesson state", "unsafe"))
    counts = {name: 0 for name in ("matching", "missing", "content differs", "unsafe", "unavailable")}
    for _, state in entries:
        counts[state] += 1
    if counts["unsafe"] or counts["unavailable"]:
        result, code = "BLOCKED", 1
    elif counts["missing"] or counts["content differs"]:
        result, code = "CHANGES REQUIRED", 1
    else:
        result, code = "READY", 0
    lines = [f"{state}: {path}" for path, state in sorted(entries)]
    lines.append(f"delegated lessons: {lesson_state}" if not core_only else "delegated lessons: not selected")
    lines.append(f"COUNTS: matching={counts['matching']} missing={counts['missing']} content differs={counts['content differs']} unsafe={counts['unsafe']} unavailable={counts['unavailable']}")
    lines.append("RESULT: " + result)
    return "\n".join(lines), code


def _report(lines, counts):
    lines.append(f"COUNTS: matching={counts['matching']} missing={counts['missing']} content differs={counts['content differs']} unsafe={counts['unsafe']} unavailable={counts['unavailable']}")
    return "\n".join(lines)
