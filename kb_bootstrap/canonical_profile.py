"""Read-only validation for the kb-bootstrap canonical OKF v0.2 profile."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Union

import yaml


class _StringScalarLoader(yaml.SafeLoader):
    """Load frontmatter mappings without YAML 1.1 scalar coercion."""


_StringScalarLoader.yaml_implicit_resolvers = {
    key: list(value) for key, value in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
for first_character, resolvers in list(_StringScalarLoader.yaml_implicit_resolvers.items()):
    _StringScalarLoader.yaml_implicit_resolvers[first_character] = [
        (tag, expression)
        for tag, expression in resolvers
        if tag
        not in {
            "tag:yaml.org,2002:bool",
            "tag:yaml.org,2002:float",
            "tag:yaml.org,2002:int",
            "tag:yaml.org,2002:timestamp",
        }
    ]

RESERVED_FILENAMES = {"index.md", "log.md"}
IGNORED_DIRS = {"raw", "lessons"}
VALID_STATUSES = {"draft", "stable", "deprecated"}


def _traverses_symlink(path: Path) -> bool:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            return True
    return False


def _frontmatter(path: Path) -> Tuple[Dict[str, object], str]:
    if path.is_symlink() or _traverses_symlink(path):
        return {}, "symlinked path is not allowed"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}, "cannot read UTF-8 Markdown"
    if not lines or lines[0] != "---":
        return {}, "missing exact YAML frontmatter"
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, "missing exact YAML frontmatter"
    try:
        parsed = yaml.load("\n".join(lines[1:end]), Loader=_StringScalarLoader)
    except yaml.YAMLError:
        return {}, "frontmatter is invalid YAML"
    if not isinstance(parsed, dict):
        return {}, "frontmatter must be a mapping"
    return parsed, ""


def _concept_files(
    base_path: Path, ignore_dirs: Iterable[str] = IGNORED_DIRS
) -> Tuple[List[Path], List[str]]:
    ignored = {directory.casefold() for directory in ignore_dirs}
    files: List[Path] = []
    errors: List[str] = []
    for root, directories, filenames in os.walk(base_path):
        root_path = Path(root)
        if root_path.is_symlink() or _traverses_symlink(root_path):
            relative_root = root_path.relative_to(base_path).as_posix()
            errors.append(f"{relative_root}: symlinked directory is not allowed")
            directories[:] = []
            continue
        retained = []
        for directory in sorted(directories):
            path = root_path / directory
            relative = path.relative_to(base_path).as_posix()
            if path.is_symlink():
                errors.append(f"{relative}: symlinked directory is not allowed")
                continue
            if directory.casefold() in ignored:
                continue
            retained.append(directory)
        directories[:] = retained
        for filename in sorted(filenames):
            if not filename.casefold().endswith(".md") or filename.casefold() in RESERVED_FILENAMES:
                continue
            path = root_path / filename
            relative = path.relative_to(base_path).as_posix()
            if path.is_symlink():
                errors.append(f"{relative}: symlinked file is not allowed")
                continue
            files.append(path)
    return files, errors


def canonical_metadata_errors(metadata: Dict[str, object]) -> List[str]:
    """Return minimal profile errors for one already parsed frontmatter mapping."""
    errors: List[str] = []
    concept_type = metadata.get("type")
    if not isinstance(concept_type, str) or not concept_type.strip():
        errors.append("type must be a non-empty string")

    for field in ("title", "description"):
        value = metadata.get(field)
        if field in metadata and not isinstance(value, str):
            errors.append(f"{field} must be a string")

    tags = metadata.get("tags")
    if "tags" in metadata and (
        not isinstance(tags, list)
        or any(not isinstance(tag, str) for tag in tags)
    ):
        errors.append("tags must be a list of strings")

    status = metadata.get("status")
    if "status" in metadata and (
        not isinstance(status, str) or status not in VALID_STATUSES
    ):
        errors.append("status must be draft, stable, or deprecated")
    return errors


def validate_canonical_profile(
    base_dir: Union[os.PathLike, str] = "docs",
) -> Tuple[str, bool]:
    """Validate ordinary canonical concepts without rewriting source files."""
    raw_base_path = Path(base_dir).absolute()
    base_path = raw_base_path.resolve()
    errors: List[str] = []
    concept_files: List[Path] = []

    if _traverses_symlink(raw_base_path):
        errors.append("canonical root traverses a symlink")
    elif not base_path.is_dir():
        errors.append("canonical root is unavailable")
    else:
        concept_files, traversal_errors = _concept_files(base_path)
        errors.extend(traversal_errors)

    for concept in concept_files:
        relative = concept.relative_to(base_path).as_posix()
        metadata, error = _frontmatter(concept)
        if error:
            errors.append(f"{relative}: {error}")
            continue

        errors.extend(
            f"{relative}: {metadata_error}"
            for metadata_error in canonical_metadata_errors(metadata)
        )

    lines = [
        "=== Canonical OKF v0.2 Profile Validation ===",
        f"Concept files: {len(concept_files)}",
        "Reserved/index files: excluded",
        "Raw and lesson directories: excluded",
    ]
    if errors:
        lines.append(f"ERRORS ({len(errors)}):")
        lines.extend(f"   - {error}" for error in errors)
    else:
        lines.append("ERRORS: 0")
    lines.extend(
        [
            "",
            "Profile: type is required; unknown types and additional metadata are accepted.",
            "Source mutation: no",
        ]
    )
    return "\n".join(lines), not errors
