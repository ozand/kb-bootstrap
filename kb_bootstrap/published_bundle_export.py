"""Build and exclusively publish a deterministic Markdown-only OKF ZIP bundle."""
from __future__ import annotations

import datetime
import io
import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

import yaml

from .canonical_profile import (IGNORED_DIRS, RESERVED_FILENAMES, _StringScalarLoader,
    _traverses_symlink, canonical_metadata_errors)
from .canonical_graph_export import _inside, _relative_input


class _Member(NamedTuple):
    path: Path
    relative: str
    content: bytes
    identity: Tuple[int, int, int, int]
    kind: str


_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _signature(path: Path) -> Tuple[int, int, int, int]:
    details = os.stat(str(path), follow_symlinks=False)
    return details.st_dev, details.st_ino, details.st_size, details.st_mtime_ns


def _identity(path: Path) -> Tuple[int, int]:
    details = os.stat(str(path), follow_symlinks=False)
    return details.st_dev, details.st_ino


def _stable_bytes(path: Path):
    if path.is_symlink() or _traverses_symlink(path) or not path.is_file():
        return None, None, "path is unavailable or unsafe"
    try:
        before = _signature(path)
        content = path.read_bytes()
        after = _signature(path)
        content.decode("utf-8")
    except (OSError, UnicodeError):
        return None, None, "file is not readable UTF-8 Markdown"
    if before != after:
        return None, None, "file changed while being read"
    return content, after, ""


def _frontmatter(content: bytes):
    lines = content.decode("utf-8").splitlines()
    if not lines or lines[0] != "---":
        return None, False, ""
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None, True, "frontmatter is invalid YAML"
    try:
        metadata = yaml.load("\n".join(lines[1:end]), Loader=_StringScalarLoader)
    except yaml.YAMLError:
        return None, True, "frontmatter is invalid YAML"
    if not isinstance(metadata, dict):
        return None, True, "frontmatter must be a mapping"
    return metadata, True, ""


def _visible_lines(content: bytes) -> List[str]:
    visible: List[str] = []
    fence: Optional[str] = None
    for line in content.decode("utf-8").splitlines():
        match = _FENCE.match(line)
        if match:
            marker = match.group(1)[0]
            fence = marker if fence is None else (None if fence == marker else fence)
            continue
        if fence is None:
            visible.append(line)
    return visible


def _reserved_result(relative: str, content: bytes, root: bool):
    errors: List[str] = []
    warnings: List[str] = []
    metadata, has_frontmatter, error = _frontmatter(content)
    filename = Path(relative).name
    if error:
        errors.append(f"{relative}: {error}")
    elif filename == "index.md" and root and has_frontmatter:
        version = metadata.get("okf_version")
        if version is not None and version != "0.2":
            errors.append(f"{relative}: okf_version must be the string 0.2")
        if any(key != "okf_version" for key in metadata):
            warnings.append(f"{relative}: root index has unknown metadata")
    elif has_frontmatter:
        errors.append(f"{relative}: reserved file must not have frontmatter")
    visible = _visible_lines(content)
    if filename == "index.md" and visible:
        has_heading = any(line.lstrip().startswith("#") for line in visible)
        has_list = any(line.lstrip().startswith(("- ", "* ", "+ ")) for line in visible)
        if not has_heading and not has_list:
            warnings.append(f"{relative}: index has no heading or list entry")
    if filename == "log.md":
        dates = []
        for line in visible:
            match = _HEADING.match(line)
            if match and re.match(r"^\d{4}[-/]", match.group(1)):
                if not _DATE.match(match.group(1)):
                    errors.append(f"{relative}: log date heading is invalid")
                    continue
                try:
                    dates.append(datetime.datetime.strptime(match.group(1), "%Y-%m-%d").date())
                except ValueError:
                    errors.append(f"{relative}: log date heading is invalid")
        if any(later > earlier for earlier, later in zip(dates, dates[1:])):
            warnings.append(f"{relative}: log dates are not newest-first")
    return errors, warnings


def build_published_bundle(canonical_root: Union[str, Path]) -> Tuple[bytes, str, bool]:
    raw_root = Path(canonical_root).absolute()
    root = raw_root.resolve()
    errors: List[str] = []
    warnings: List[str] = []
    members: List[_Member] = []
    ignored = {value.casefold() for value in IGNORED_DIRS}
    if _traverses_symlink(raw_root) or not root.is_dir():
        return b"", "RESULT: BLOCKED (canonical root is unavailable or unsafe)", False
    for directory, directories, filenames in os.walk(root):
        current = Path(directory)
        if current.is_symlink() or _traverses_symlink(current):
            errors.append(f"{current.relative_to(root).as_posix()}: symlinked directory is not allowed")
            directories[:] = []
            continue
        retained = []
        for name in sorted(directories):
            candidate = current / name
            relative = candidate.relative_to(root).as_posix()
            if candidate.is_symlink():
                errors.append(f"{relative}: symlinked directory is not allowed")
            elif name.casefold() not in ignored:
                retained.append(name)
        directories[:] = retained
        for name in sorted(filenames):
            if not name.casefold().endswith(".md"):
                continue
            path = current / name
            relative = path.relative_to(root).as_posix()
            if "\\" in relative or any(ord(character) < 32 for character in relative):
                errors.append(f"{relative}: bundle member path is unsafe")
                continue
            if path.is_symlink():
                errors.append(f"{relative}: symlinked file is not allowed")
                continue
            lowered = name.casefold()
            if lowered in RESERVED_FILENAMES and name not in RESERVED_FILENAMES:
                errors.append(f"{relative}: reserved filename must use exact lowercase")
                continue
            content, identity, error = _stable_bytes(path)
            if error:
                errors.append(f"{relative}: {error}")
                continue
            if name in RESERVED_FILENAMES:
                item_errors, item_warnings = _reserved_result(relative, content, current == root)
                errors.extend(item_errors)
                warnings.extend(item_warnings)
                kind = name
            else:
                metadata, has_frontmatter, error = _frontmatter(content)
                if error or not has_frontmatter or metadata is None:
                    errors.append(f"{relative}: {error or 'missing exact YAML frontmatter'}")
                    continue
                errors.extend(f"{relative}: {message}" for message in canonical_metadata_errors(metadata))
                kind = "concept"
            members.append(_Member(path, relative, content, identity, kind))
    errors.sort()
    warnings.sort()
    concepts = sum(member.kind == "concept" for member in members)
    reserved = len(members) - concepts
    lines = ["=== Published OKF Bundle Validation ==="]
    lines.extend(f"WARNING: {warning}" for warning in warnings)
    lines.extend([f"Concept files: {concepts}", f"Reserved files: {reserved}", "Excluded layers: raw/, lessons/"])
    if errors:
        lines.extend(f"ERROR: {error}" for error in errors)
        lines.append("RESULT: BLOCKED")
        return b"", "\n".join(lines), False
    for member in members:
        try:
            if _signature(member.path) != member.identity or member.path.read_bytes() != member.content:
                lines.append(f"ERROR: {member.relative}: file changed while building bundle")
                lines.append("RESULT: BLOCKED")
                return b"", "\n".join(lines), False
        except OSError:
            lines.append(f"ERROR: {member.relative}: file changed while building bundle")
            lines.append("RESULT: BLOCKED")
            return b"", "\n".join(lines), False
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for member in sorted(members, key=lambda item: item.relative):
            info = zipfile.ZipInfo(member.relative, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            info.create_system = 3
            info.extra = b""
            info.comment = b""
            archive.writestr(info, member.content)
    lines.append("RESULT: OK")
    return stream.getvalue(), "\n".join(lines), True


def write_published_bundle(project_root: Union[str, Path], canonical_dir: Union[str, Path], output: Union[str, Path]):
    raw_project = Path(project_root).absolute()
    if _traverses_symlink(raw_project) or not raw_project.resolve().is_dir():
        return "RESULT: BLOCKED (project root is unavailable or unsafe)", False
    project = raw_project.resolve()
    canonical_root, canonical_error = _relative_input(canonical_dir, project, "canonical")
    output_path, output_error = _relative_input(output, project, "output")
    if canonical_error:
        return f"RESULT: BLOCKED ({canonical_error})", False
    if output_error:
        return f"RESULT: BLOCKED ({output_error})", False
    if not canonical_root.is_dir():
        return "RESULT: BLOCKED (canonical root is unavailable)", False
    if _inside(output_path, canonical_root):
        return "RESULT: BLOCKED (output must be outside the canonical root)", False
    if output_path.suffix.casefold() != ".zip":
        return "RESULT: BLOCKED (output must end with .zip)", False
    if not output_path.parent.is_dir() or _traverses_symlink(output_path.parent):
        return "RESULT: BLOCKED (output parent is unavailable or unsafe)", False
    if output_path.exists() or output_path.is_symlink():
        return "RESULT: BLOCKED (output already exists)", False
    data, report, valid = build_published_bundle(canonical_root)
    if not valid:
        return report, False
    parent_identity = _identity(output_path.parent)
    staged: Optional[Path] = None
    cleanup_warning = False
    try:
        if _traverses_symlink(output_path.parent) or _identity(output_path.parent) != parent_identity:
            raise OSError("unsafe output parent")
        descriptor, name = tempfile.mkstemp(prefix=".kb-bootstrap-bundle-", suffix=".tmp", dir=str(output_path.parent))
        staged = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if _traverses_symlink(output_path.parent) or _identity(output_path.parent) != parent_identity or output_path.exists() or output_path.is_symlink():
            raise OSError("output changed before publication")
        os.link(staged, output_path)
        try:
            staged.unlink()
        except OSError:
            cleanup_warning = True
        staged = None
    except OSError:
        if staged is not None:
            try:
                staged.unlink()
            except OSError:
                pass
        return report + "\nRESULT: BLOCKED (bundle output cannot be published exclusively)", False
    result = report + "\noutput: created"
    if cleanup_warning:
        result += "\nWARNING: output published; temporary cleanup is incomplete"
    return result, True
