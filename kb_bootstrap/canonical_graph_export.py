"""Deterministic read-only JSON export of the canonical Markdown graph."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set, Tuple, Union
from urllib.parse import unquote, urlsplit

from .canonical_profile import (
    _StringScalarLoader,
    _concept_files,
    _traverses_symlink,
    canonical_metadata_errors,
    validate_canonical_profile,
)

import yaml

LINK_START_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(")
FENCE_PATTERN = re.compile(r"^\s*(```|~~~)")
ENCODED_UNSAFE_PATTERN = re.compile(
    r"%(?:0[0-9a-f]|1[0-9a-f]|2e|2f|5c|7f)", re.IGNORECASE
)
DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[/\\]")
ARTIFACT_SCHEMA = "kb-bootstrap.canonical-graph"
ARTIFACT_PROFILE = "kb-bootstrap.okf-v0.2-minimal"


class _Document(NamedTuple):
    content: bytes
    frontmatter: str
    body: str


def _identity(path: Path) -> Tuple[int, int]:
    details = path.stat(follow_symlinks=False)
    return details.st_dev, details.st_ino


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _read_document(path: Path) -> Tuple[Optional[_Document], str]:
    if path.is_symlink() or _traverses_symlink(path) or not path.is_file():
        return None, "concept path is unavailable or unsafe"
    try:
        before = path.stat(follow_symlinks=False)
        content = path.read_bytes()
        after = path.stat(follow_symlinks=False)
        text = content.decode("utf-8")
    except (OSError, UnicodeError):
        return None, "concept is not readable UTF-8 Markdown"
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        return None, "concept changed while being read"
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None, "concept frontmatter is unavailable"
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None, "concept frontmatter is unavailable"
    frontmatter = "\n".join(lines[1:end])
    try:
        metadata = yaml.load(frontmatter, Loader=_StringScalarLoader)
    except yaml.YAMLError:
        return None, "frontmatter is invalid YAML"
    if not isinstance(metadata, dict):
        return None, "frontmatter must be a mapping"
    metadata_errors = canonical_metadata_errors(metadata)
    if metadata_errors:
        return None, metadata_errors[0]
    return _Document(content, frontmatter, "\n".join(lines[end + 1 :])), ""


def _relative_input(
    value: Union[str, Path], project_root: Path, category: str
) -> Tuple[Optional[Path], str]:
    relative = Path(value)
    if "\x00" in str(value):
        return None, f"{category} path is invalid"
    if relative.is_absolute() or ".." in relative.parts:
        return None, f"{category} path must be relative and contained"
    candidate = project_root / relative
    if _traverses_symlink(candidate):
        return None, f"{category} path traverses a symlink"
    if not _inside(candidate, project_root):
        return None, f"{category} path is outside the project root"
    return candidate.resolve(), ""


def _link_destinations(body: str) -> Tuple[List[str], List[str]]:
    """Extract bounded v1 links and report malformed recognized local syntax."""
    destinations: List[str] = []
    errors: List[str] = []
    visible_lines: List[str] = []
    fence: Optional[str] = None
    for line in body.splitlines():
        fence_match = FENCE_PATTERN.match(line)
        if fence_match:
            marker = fence_match.group(1)
            fence = None if fence == marker[:3] else marker[:3]
            continue
        if fence is not None:
            continue
        visible_lines.append(re.sub(r"`[^`]*`", "", line))
    visible_body = "\n".join(visible_lines)
    for match in LINK_START_PATTERN.finditer(visible_body):
        position = match.end()
        if position >= len(visible_body):
            continue
        if visible_body[position] == "<":
            close = visible_body.find(">", position + 1)
            if close == -1:
                if ".md" in visible_body[position:].casefold():
                    errors.append("malformed local Markdown link")
                continue
            destination = visible_body[position : close + 1]
            tail = close + 1
        else:
            tail = position
            unsupported = False
            while tail < len(visible_body) and not visible_body[tail].isspace() and visible_body[tail] != ")":
                if visible_body[tail] in "()":
                    unsupported = True
                    break
                tail += 1
            if unsupported or tail == position:
                continue
            destination = visible_body[position:tail]
        if tail < len(visible_body) and visible_body[tail] == ")":
            destinations.append(destination)
            continue
        if tail < len(visible_body) and visible_body[tail].isspace():
            closing = visible_body.find(")", tail)
            if closing != -1 and "(" not in visible_body[tail:closing]:
                destinations.append(destination)
                continue
        local_candidate = (
            destination[1:-1]
            if destination.startswith("<") and destination.endswith(">")
            else destination
        )
        if local_candidate.casefold().split("#", 1)[0].endswith(".md"):
            errors.append("malformed local Markdown link")
    return destinations, errors


def _local_target(
    raw: str,
    source: str,
    canonical_root: Path,
    node_paths: Set[str],
) -> Tuple[Optional[Tuple[str, Optional[str]]], str]:
    destination = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
    if not destination or destination.startswith("#"):
        return None, ""
    if any(ord(character) < 32 or ord(character) == 127 for character in destination):
        return None, "local link contains a control character"
    if "\\" in destination:
        return None, "local link path is invalid"
    if DRIVE_PATTERN.match(destination):
        return None, "local link path is absolute"
    parsed = urlsplit(destination)
    if parsed.scheme or destination.startswith("//"):
        return None, ""
    if parsed.query:
        return None, "local Markdown link query is unsupported"
    if ENCODED_UNSAFE_PATTERN.search(parsed.path):
        return None, "local link contains encoded traversal or separator"
    decoded_path = unquote(parsed.path)
    if not decoded_path.casefold().endswith(".md"):
        return None, ""

    source_path = Path(source)
    unresolved = (
        canonical_root / decoded_path.lstrip("/")
        if decoded_path.startswith("/")
        else canonical_root / source_path.parent / decoded_path
    )
    if _traverses_symlink(unresolved):
        return None, "local link target traverses a symlink"
    resolved = unresolved.resolve()
    try:
        relative = resolved.relative_to(canonical_root).as_posix()
    except ValueError:
        return None, "local link target escapes the canonical root"
    if relative not in node_paths:
        return None, "local Markdown link target is not an exported concept"
    fragment = parsed.fragment if parsed.fragment else None
    if fragment is not None and any(ord(character) < 32 or ord(character) == 127 for character in fragment):
        return None, "local link fragment contains a control character"
    return (relative, fragment), ""


def build_canonical_graph(
    canonical_root: Union[str, Path],
) -> Tuple[bytes, str, bool]:
    """Build stable JSON bytes without writing an output file."""
    root = Path(canonical_root).absolute()
    profile_report, profile_valid = validate_canonical_profile(root)
    if not profile_valid:
        return b"", "RESULT: BLOCKED (canonical profile validation failed)\n" + profile_report, False

    concept_files, traversal_errors = _concept_files(root.resolve())
    if traversal_errors:
        lines = [f"RESULT: BLOCKED ({len(traversal_errors)} traversal error(s))"]
        lines.extend(f"  - {error}" for error in traversal_errors)
        return b"", "\n".join(lines), False

    documents: Dict[str, _Document] = {}
    for concept in concept_files:
        relative = concept.relative_to(root.resolve()).as_posix()
        document, error = _read_document(concept)
        if error or document is None:
            return b"", f"RESULT: BLOCKED ({relative}: {error})", False
        documents[relative] = document

    node_paths = set(documents)
    nodes = [
        {"path": path, "frontmatter": documents[path].frontmatter}
        for path in sorted(documents)
    ]
    edge_values: Set[Tuple[str, str, Optional[str]]] = set()
    errors: List[str] = []
    for source in sorted(documents):
        raw_targets, syntax_errors = _link_destinations(documents[source].body)
        errors.extend(f"{source}: {error}" for error in syntax_errors)
        for raw_target in raw_targets:
            target, error = _local_target(raw_target, source, root.resolve(), node_paths)
            if error:
                errors.append(f"{source}: {error}")
            elif target is not None:
                edge_values.add((source, target[0], target[1]))
    if errors:
        errors.sort()
        lines = [f"RESULT: BLOCKED ({len(errors)} link error(s))"]
        lines.extend(f"  - {error}" for error in errors)
        return b"", "\n".join(lines), False

    edges = [
        {"source": source, "target": target, "fragment": fragment}
        for source, target, fragment in sorted(
            edge_values,
            key=lambda edge: (edge[0], edge[1], "" if edge[2] is None else edge[2]),
        )
    ]
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "version": 1,
        "profile": ARTIFACT_PROFILE,
        "nodes": nodes,
        "edges": edges,
    }
    data = (
        json.dumps(artifact, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")
    report = "\n".join(
        [
            "RESULT: OK",
            f"nodes: {len(nodes)}",
            f"edges: {len(edges)}",
            "source mutation: no",
        ]
    )
    return data, report, True


def write_canonical_graph(
    project_root: Union[str, Path],
    canonical_dir: Union[str, Path],
    output: Union[str, Path],
) -> Tuple[str, bool]:
    """Build and exclusively publish one contained JSON artifact."""
    raw_project_root = Path(project_root).absolute()
    if _traverses_symlink(raw_project_root) or not raw_project_root.resolve().is_dir():
        return "RESULT: BLOCKED (project root is unavailable or unsafe)", False
    root = raw_project_root.resolve()
    canonical_root, canonical_error = _relative_input(canonical_dir, root, "canonical")
    output_path, output_error = _relative_input(output, root, "output")
    if canonical_error:
        return f"RESULT: BLOCKED ({canonical_error})", False
    if output_error:
        return f"RESULT: BLOCKED ({output_error})", False
    assert canonical_root is not None and output_path is not None
    if not canonical_root.is_dir():
        return "RESULT: BLOCKED (canonical root is unavailable)", False
    if _inside(output_path, canonical_root):
        return "RESULT: BLOCKED (output must be outside the canonical root)", False
    if not output_path.parent.is_dir() or _traverses_symlink(output_path.parent):
        return "RESULT: BLOCKED (output parent is unavailable or unsafe)", False
    if output_path.exists() or output_path.is_symlink():
        return "RESULT: BLOCKED (output already exists)", False

    data, build_report, valid = build_canonical_graph(canonical_root)
    if not valid:
        return build_report, False

    parent_identity = _identity(output_path.parent)
    staged: Optional[Path] = None
    created: Optional[Tuple[Path, Tuple[int, int]]] = None
    cleanup_failed = False
    cleanup_warning = False
    try:
        if _traverses_symlink(output_path.parent) or _identity(output_path.parent) != parent_identity:
            raise OSError("unsafe output parent")
        descriptor, name = tempfile.mkstemp(
            prefix=".kb-bootstrap-graph-", suffix=".tmp", dir=str(output_path.parent)
        )
        staged = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if (
            _traverses_symlink(output_path.parent)
            or _identity(output_path.parent) != parent_identity
            or output_path.exists()
            or output_path.is_symlink()
        ):
            raise OSError("output changed before publication")
        installed_identity = _identity(staged)
        os.link(staged, output_path)
        created = (output_path, installed_identity)
        try:
            staged.unlink()
            staged = None
        except OSError:
            cleanup_warning = True
            staged = None
        created = None
    except OSError:
        if created is not None:
            path, installed_identity = created
            try:
                if path.is_file() and not path.is_symlink() and _identity(path) == installed_identity:
                    path.unlink()
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
        result = "RESULT: BLOCKED (graph output cannot be published exclusively"
        if cleanup_failed:
            result += "; cleanup is incomplete"
        return result + ")", False
    finally:
        if staged is not None:
            try:
                staged.unlink(missing_ok=True)
            except OSError:
                pass

    result = build_report + "\noutput: created"
    if cleanup_warning:
        result += "\nWARNING: output published; temporary cleanup is incomplete"
    return result, True
