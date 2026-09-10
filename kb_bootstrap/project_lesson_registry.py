"""Read-only validation for the generated project-local lesson contract."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union

import yaml

FILENAME_PATTERN = re.compile(
    r"^(?P<id>[A-Za-z][A-Za-z0-9_-]*-\d{4})-[A-Za-z0-9._-]+\.md$"
)


def _load_yaml(path: Path) -> Dict[str, object]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def _frontmatter(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    parsed = yaml.safe_load(text[4:end])
    return parsed if isinstance(parsed, dict) else {}


def _relative_path(path: Path, project_root: Path) -> str:
    return path.relative_to(project_root).as_posix()


def validate_project_registry(
    root: Union[str, Path], project_root: Union[str, Path] = Path(".")
) -> Tuple[List[str], Dict[str, object]]:
    """Validate a project-local registry rooted at ``kb/lessons``.

    The index uses repository-root-relative ``path`` values and project-local
    IDs controlled by its ``id_prefix``. ``SCHEMA.md`` is documentation, not a
    lesson file.
    """
    lessons_dir = Path(root).resolve()
    repository_root = Path(project_root).resolve()
    errors: List[str] = []

    if not lessons_dir.is_dir():
        return ["project-local lessons directory is unavailable"], {}
    try:
        lessons_dir.relative_to(repository_root)
    except ValueError:
        return ["project-local lessons directory is outside the project root"], {}

    index_path = lessons_dir / "index.yaml"
    schema_path = lessons_dir / "SCHEMA.md"
    if not index_path.is_file():
        errors.append("project-local index.yaml is unavailable")
    if not schema_path.is_file():
        errors.append("project-local SCHEMA.md is unavailable")
    if errors:
        return errors, {}

    try:
        index = _load_yaml(index_path)
    except (OSError, UnicodeError, yaml.YAMLError):
        return ["project-local index.yaml is unavailable or invalid"], {}

    version = index.get("version")
    if version != 1:
        errors.append("project-local index version must be 1")
    if index.get("scope") != "project":
        errors.append("project-local index scope must be project")

    id_prefix = index.get("id_prefix")
    if not isinstance(id_prefix, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*-", id_prefix):
        errors.append("project-local index id_prefix is missing or invalid")
        id_prefix = ""

    raw_entries = index.get("lessons")
    entries = raw_entries if isinstance(raw_entries, list) else []
    if raw_entries is None:
        errors.append("project-local index lessons is unavailable")
    elif not isinstance(raw_entries, list):
        errors.append("project-local index lessons must be a list")

    index_ids: List[str] = []
    index_paths: List[str] = []
    referenced_files: Set[str] = set()
    for position, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(f"project-local index entry {position} is not an object")
            continue
        lesson_id = entry.get("id")
        lesson_path = entry.get("path")
        if not isinstance(lesson_id, str) or not id_prefix or not re.fullmatch(
            re.escape(id_prefix) + r"\d{4}", lesson_id
        ):
            errors.append(f"project-local index entry {position} has an invalid lesson ID")
        else:
            index_ids.append(lesson_id)
        if not isinstance(lesson_path, str) or not lesson_path.strip():
            errors.append(f"project-local index entry {lesson_id or position} has an invalid path")
            continue
        candidate = Path(lesson_path)
        if candidate.is_absolute() or "\\" in lesson_path:
            errors.append(f"project-local index entry {lesson_id or position} has an invalid path")
            continue
        if not lesson_path.startswith("kb/lessons/"):
            errors.append(f"project-local index entry {lesson_id or position} path must be under kb/lessons")
            continue
        resolved = (repository_root / candidate).resolve()
        try:
            resolved.relative_to(repository_root)
        except ValueError:
            errors.append(f"project-local index path escapes project root: {lesson_path}")
            continue
        normalized = _relative_path(resolved, repository_root)
        index_paths.append(normalized)
        referenced_files.add(normalized)
        if id_prefix and isinstance(lesson_id, str):
            expected_name = FILENAME_PATTERN.fullmatch(resolved.name)
            if not expected_name or expected_name.group("id") != lesson_id:
                errors.append(f"project-local index ID/path mismatch: {lesson_id}")

    for duplicate, count in sorted(Counter(index_ids).items()):
        if count > 1:
            errors.append(f"duplicate project-local lesson ID: {duplicate}")
    for duplicate, count in sorted(Counter(index_paths).items()):
        if count > 1:
            errors.append(f"duplicate project-local lesson path: {duplicate}")

    lesson_files: List[Path] = []
    for lesson_file in sorted(lessons_dir.glob("*.md")):
        if lesson_file.name == "SCHEMA.md":
            continue
        lesson_files.append(lesson_file)
        filename_match = FILENAME_PATTERN.fullmatch(lesson_file.name)
        if not filename_match:
            errors.append(f"project-local lesson filename has invalid ID format: {lesson_file.name}")
            continue
        filename_id = filename_match.group("id")
        if not id_prefix or not filename_id.startswith(id_prefix):
            errors.append(f"project-local lesson ID does not use id_prefix: {lesson_file.name}")
            continue
        try:
            metadata = _frontmatter(lesson_file)
        except (OSError, UnicodeError, yaml.YAMLError):
            errors.append(f"project-local lesson {filename_id} frontmatter is unavailable or invalid")
            continue
        if metadata.get("id") != filename_id:
            errors.append(f"project-local lesson {filename_id} filename/frontmatter ID mismatch")
        file_path = _relative_path(lesson_file, repository_root)
        if file_path not in referenced_files:
            errors.append(f"project-local lesson missing from index: {filename_id}")

    file_ids = []
    file_paths: Set[str] = set()
    for lesson_file in lesson_files:
        match = FILENAME_PATTERN.fullmatch(lesson_file.name)
        if match and id_prefix and match.group("id").startswith(id_prefix):
            file_ids.append(match.group("id"))
            file_paths.add(_relative_path(lesson_file, repository_root))

    for lesson_id in sorted(set(index_ids) - set(file_ids)):
        errors.append(f"project-local index references missing lesson: {lesson_id}")
    for lesson_path in sorted(set(index_paths) - file_paths):
        errors.append(f"project-local index references missing path: {lesson_path}")

    return errors, {
        "ids": sorted(set(index_ids) | set(file_ids)),
        "entries": len(entries),
        "files": len(lesson_files),
    }
