"""Safely enable the existing project-local lessons contract post-init."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Union

from .project_lesson_registry import validate_project_registry

ARTIFACTS = (
    "kb/lessons/SCHEMA.md",
    "kb/lessons/index.yaml",
    "lesson-stores.json",
    ".agents/skills/kb-capture/SKILL.md",
)
INITIALIZED_MARKERS = (
    "qmd.json",
    "qmd/collections/wiki.yaml",
    "qmd/collections/raw.yaml",
    ".agents/skills/kb-lookup/SKILL.md",
)


def _traverses_symlink(path: Path) -> bool:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            return True
    return False


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _regular_file(path: Path) -> bool:
    return path.is_file() and not _traverses_symlink(path)


def _file_identity(path: Path) -> Tuple[int, int]:
    stat = path.stat(follow_symlinks=False)
    return stat.st_dev, stat.st_ino


def _routing_errors(path: Path) -> List[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ["lesson routing contract is unavailable or invalid"]
    if not isinstance(data, dict):
        return ["lesson routing contract must be an object"]

    errors: List[str] = []
    if data.get("version") != 1:
        errors.append("lesson routing version must be 1")
    if data.get("capture_store") != "local":
        errors.append("lesson routing capture_store must be local")
    local = data.get("local")
    if not isinstance(local, dict) or local.get("path") != "kb/lessons":
        errors.append("lesson routing local path must be kb/lessons")
    shared = data.get("shared")
    if shared is not None:
        if not isinstance(shared, dict) or shared.get("read_only") is not True:
            errors.append("lesson routing shared store must be explicitly read-only")
        else:
            shared_path = shared.get("path")
            if not isinstance(shared_path, str) or not shared_path.strip():
                errors.append("lesson routing shared path must be a non-empty string")
            else:
                candidate = Path(shared_path)
                if candidate.is_absolute() or "\\" in shared_path or ".." in candidate.parts:
                    errors.append("lesson routing shared path must be relative and contained")
    return errors


def _capture_skill_errors(path: Path) -> List[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return ["kb-capture skill is unavailable or invalid"]
    if len(lines) < 3 or lines[0] != "---":
        return ["kb-capture skill is unavailable or invalid"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return ["kb-capture skill is unavailable or invalid"]
    if not any(line.strip() == "name: kb-capture" for line in lines[1:end]):
        return ["kb-capture skill identity is invalid"]
    return []


def _template_plan(package_dir: Path) -> Tuple[Dict[str, bytes], List[str]]:
    sources = {
        "kb/lessons/SCHEMA.md": package_dir / "templates/lessons/SCHEMA.md",
        "kb/lessons/index.yaml": package_dir / "templates/lessons/index.yaml",
        "lesson-stores.json": package_dir / "templates/lessons/lesson-stores.json",
        ".agents/skills/kb-capture/SKILL.md": package_dir
        / "templates/skills/kb-capture/SKILL.md",
    }
    plan: Dict[str, bytes] = {}
    for relative, source in sources.items():
        if not _regular_file(source):
            return {}, [f"template is unavailable: {relative}"]
        try:
            plan[relative] = source.read_bytes()
        except OSError:
            return {}, [f"template is unavailable: {relative}"]
    return plan, []


def _format(status: str, artifacts: Tuple[str, ...] = (), errors: List[str] = None) -> str:
    if errors:
        lines = [f"RESULT: BLOCKED ({len(errors)} error(s))"]
        lines.extend(f"  - {error}" for error in errors)
        return "\n".join(lines)
    lines = ["RESULT: OK", f"project lessons: {status}"]
    lines.extend(f"artifact: {artifact}" for artifact in artifacts)
    lines.append("external writes: no")
    return "\n".join(lines)


def enable_project_lessons(
    target: Union[str, Path], package_dir: Union[str, Path]
) -> Tuple[str, bool]:
    """Enable project-local lessons without touching unrelated repository files."""
    raw_target = Path(target).absolute()
    package_root = Path(package_dir).absolute()
    if _traverses_symlink(raw_target):
        return _format("blocked", errors=["target traverses a symlink"]), False
    target_root = raw_target.resolve()
    if not target_root.is_dir():
        return _format("blocked", errors=["target repository is unavailable"]), False

    marker_errors = []
    for relative in INITIALIZED_MARKERS:
        marker = target_root / relative
        if not _inside(marker, target_root) or not _regular_file(marker):
            marker_errors.append(f"initialized marker is unavailable: {relative}")
    if marker_errors:
        return _format("blocked", errors=marker_errors), False

    destinations = {relative: target_root / relative for relative in ARTIFACTS}
    states = []
    destination_errors = []
    for relative, destination in destinations.items():
        if not _inside(destination, target_root) or _traverses_symlink(destination):
            destination_errors.append(f"artifact path is unsafe: {relative}")
            continue
        if destination.exists():
            if not destination.is_file():
                destination_errors.append(f"artifact is not a regular file: {relative}")
            states.append(True)
        else:
            states.append(False)
    if destination_errors:
        return _format("blocked", errors=destination_errors), False
    if any(states) and not all(states):
        return _format("blocked", errors=["project lesson contract is partial or conflicting"]), False

    if all(states):
        errors, _ = validate_project_registry(target_root / "kb/lessons", target_root)
        errors.extend(_routing_errors(target_root / "lesson-stores.json"))
        errors.extend(
            _capture_skill_errors(target_root / ".agents/skills/kb-capture/SKILL.md")
        )
        if errors:
            return _format("blocked", errors=errors), False
        return _format("already enabled", ARTIFACTS), True

    plan, template_errors = _template_plan(package_root)
    if template_errors:
        return _format("blocked", errors=template_errors), False

    created_dirs: List[Path] = []
    created_files: List[Tuple[Path, Tuple[int, int]]] = []
    temp_files: List[Path] = []
    try:
        for relative in ARTIFACTS:
            destination = destinations[relative]
            missing = []
            parent = destination.parent
            while parent != target_root and not parent.exists():
                missing.append(parent)
                parent = parent.parent
            if parent != target_root and (
                not _inside(parent, target_root) or _traverses_symlink(parent)
            ):
                raise OSError("unsafe destination parent")
            for directory in reversed(missing):
                if directory.exists() or directory.is_symlink():
                    raise OSError("destination parent appeared during installation")
                if _traverses_symlink(directory.parent):
                    raise OSError("unsafe destination parent")
                directory.mkdir()
                if directory.is_symlink() or not _inside(directory, target_root):
                    raise OSError("unsafe created destination parent")
                created_dirs.append(directory)

        for position, relative in enumerate(ARTIFACTS, start=1):
            destination = destinations[relative]
            temporary = destination.parent / f".kb-bootstrap-enable-{position}.tmp"
            if _traverses_symlink(destination.parent):
                raise OSError("unsafe destination parent")
            if temporary.exists() or temporary.is_symlink():
                raise OSError("temporary artifact already exists")
            with open(temporary, "xb") as stream:
                stream.write(plan[relative])
                stream.flush()
                os.fsync(stream.fileno())
            temp_files.append(temporary)

        for relative in ARTIFACTS:
            destination = destinations[relative]
            temporary = temp_files[0]
            if _traverses_symlink(destination.parent):
                raise OSError("unsafe destination parent")
            if destination.exists() or destination.is_symlink():
                raise FileExistsError("destination appeared during installation")
            installed_identity = _file_identity(temporary)
            os.link(temporary, destination)
            created_files.append((destination, installed_identity))
            temporary.unlink()
            temp_files.pop(0)

        errors, _ = validate_project_registry(target_root / "kb/lessons", target_root)
        errors.extend(_routing_errors(target_root / "lesson-stores.json"))
        errors.extend(
            _capture_skill_errors(target_root / ".agents/skills/kb-capture/SKILL.md")
        )
        if errors:
            raise OSError("installed contract failed validation")
    except OSError:
        cleanup_failed = False
        for temporary in temp_files:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                cleanup_failed = True
        for created, identity in reversed(created_files):
            try:
                if _regular_file(created) and _file_identity(created) == identity:
                    created.unlink()
                else:
                    cleanup_failed = True
            except OSError:
                cleanup_failed = True
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                if directory.exists():
                    cleanup_failed = True
        error = "project lesson contract could not be installed"
        if cleanup_failed:
            error += "; cleanup is incomplete"
        return _format("blocked", errors=[error]), False

    return _format("enabled", ARTIFACTS), True
