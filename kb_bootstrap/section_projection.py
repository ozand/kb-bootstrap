"""Revision-scoped projection of one explicitly selected Markdown section (ADR-034)."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .local_retrieval import (
    MAX_FILE,
    MAX_OUTPUT,
    MAX_TEXT,
    checked_root,
    json_bytes,
    relative_markdown,
    safe_components,
)

MAX_HEADINGS = 256
MAX_HEADING_DEPTH = 6
MAX_TITLE_BYTES = 512
MAX_FRONTMATTER_LINES = 256
MAX_FRONTMATTER_BYTES = 8192
DEFAULT_SECTION_BYTES = 16384
MAX_SECTION_BYTES = 65536

_ATX = re.compile(r"^( {0,3})(#{1,6})( +)(.*)$")
_ATX_SHAPED = re.compile(r"^(?: {4,}|\t)#{1,6}(?:[ \t].*)?$")
_TAB_SEPARATOR = re.compile(r"^ {0,3}#{1,6}\t")
_CLOSING_HASHES = re.compile(r" +#+[ ]*$")
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(`+|~+)[ ]*$")


def _blocked():
    return {"status": "BLOCKED", "reason": "blocked"}


def _unsupported():
    return {"status": "UNSUPPORTED", "reason": "unsupported"}


def _decode_heading(line: str):
    if _ATX_SHAPED.match(line) or _TAB_SEPARATOR.match(line):
        raise ValueError("unsupported heading boundary")
    match = _ATX.match(line)
    if not match:
        return None
    level = len(match.group(2))
    title = match.group(4).strip(" ")
    title = _CLOSING_HASHES.sub("", title).rstrip(" ")
    if not title:
        raise ValueError("empty heading title")
    if len(title.encode("utf-8")) > MAX_TITLE_BYTES:
        raise ValueError("heading title too large")
    return level, title


def _frontmatter_end(lines):
    if not lines:
        return 0
    first = lines[0][:-2] if lines[0].endswith("\r\n") else lines[0][:-1] if lines[0].endswith(("\n", "\r")) else lines[0]
    if first != "---":
        return 0
    consumed_bytes = len(lines[0].encode("utf-8"))
    for index, raw_line in enumerate(lines[1:], start=1):
        if index + 1 > MAX_FRONTMATTER_LINES:
            raise ValueError("frontmatter line limit")
        consumed_bytes += len(raw_line.encode("utf-8"))
        if consumed_bytes > MAX_FRONTMATTER_BYTES:
            raise ValueError("frontmatter byte limit")
        line = raw_line[:-2] if raw_line.endswith("\r\n") else raw_line[:-1] if raw_line.endswith(("\n", "\r")) else raw_line
        if line == "---":
            return index + 1
    raise ValueError("unterminated frontmatter")


def _fence_open(line: str):
    match = _FENCE_OPEN.match(line)
    if not match:
        return None
    marker = match.group(1)
    tail = match.group(2)
    if marker[0] == "`" and "`" in tail:
        raise ValueError("invalid backtick fence opener")
    return marker[0], len(marker)


def _fence_close(line: str, marker: str, count: int):
    match = _FENCE_CLOSE.match(line)
    return bool(match and match.group(1)[0] == marker and len(match.group(1)) >= count)


def _parse(data: bytes):
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    logical = [line[:-2] if line.endswith("\r\n") else line[:-1] if line.endswith(("\n", "\r")) else line for line in lines]
    start = _frontmatter_end(lines)
    headings = []
    stack = []
    fence = None
    for index in range(start, len(logical)):
        line = logical[index]
        if fence:
            if _fence_close(line, *fence):
                fence = None
            continue
        opened = _fence_open(line)
        if opened:
            fence = opened
            continue
        if re.match(r"^ {0,3}(?:=+|-+)[ ]*$", line) and index > start and logical[index - 1].strip(" "):
            raise ValueError("setext heading")
        heading = _decode_heading(line)
        if heading is None:
            continue
        level, title = heading
        while stack and stack[-1][0] >= level:
            stack.pop()
        if len(stack) + 1 > MAX_HEADING_DEPTH:
            raise ValueError("heading depth limit")
        stack.append((level, title))
        if len(headings) >= MAX_HEADINGS:
            raise ValueError("heading count limit")
        headings.append({"level": level, "title": title, "path": tuple(x[1] for x in stack), "line": index + 1})
    if fence:
        raise ValueError("unterminated fence")
    return text, lines, headings


def _success_size(result):
    return len(json_bytes(result)) + 1 <= MAX_OUTPUT


def _utf8_prefix(text: str, budget: int) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= budget:
        return text
    prefix = raw[:budget]
    while prefix:
        try:
            return prefix.decode("utf-8")
        except UnicodeDecodeError as exc:
            prefix = prefix[:exc.start]
    return ""


def project_section(
    root,
    relative_path,
    expected_sha256,
    heading_path,
    occurrence=None,
    max_section_bytes=DEFAULT_SECTION_BYTES,
):
    """Return one bounded section from a caller-selected revision-scoped Markdown path."""
    if (
        not isinstance(expected_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        or not isinstance(heading_path, (list, tuple))
        or not heading_path
        or any(not isinstance(part, str) or not part for part in heading_path)
        or len(heading_path) > MAX_HEADING_DEPTH
        or (occurrence is not None and (not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1))
        or not isinstance(max_section_bytes, int)
        or isinstance(max_section_bytes, bool)
        or not 1 <= max_section_bytes <= MAX_SECTION_BYTES
    ):
        return _blocked()
    try:
        if any(len(part.encode("utf-8")) > MAX_TITLE_BYTES for part in heading_path):
            return _blocked()
    except UnicodeError:
        return _blocked()
    try:
        root_path, root_error = checked_root(root)
        relative = relative_markdown(relative_path)
        if root_error or relative is None:
            return _blocked()
        relative_name = relative.as_posix()
        if len(relative_name.encode("utf-8")) > MAX_TEXT:
            return _blocked()
        target = root_path.joinpath(*relative.parts)
        if not safe_components(target):
            return _blocked()
        import os
        import stat
        details = os.lstat(target)
        if not stat.S_ISREG(details.st_mode) or getattr(details, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            return _blocked()
        with open(target, "rb") as stream:
            data = stream.read(MAX_FILE + 1)
        if len(data) > MAX_FILE:
            return _blocked()
    except (OSError, ValueError, TypeError):
        return _blocked()
    try:
        data.decode("utf-8")
    except UnicodeError:
        return _blocked()
    observed = hashlib.sha256(data).hexdigest()
    if observed != expected_sha256:
        return {"status": "REVISION_MISMATCH", "observed_sha256": observed}
    try:
        text, lines, headings = _parse(data)
    except ValueError:
        return _unsupported()
    requested = tuple(heading_path)
    matches = [item for item in headings if item["path"] == requested]
    if not matches:
        return {"status": "NOT_FOUND", "reason": "not_found"}
    if occurrence is None and len(matches) > 1:
        return {"status": "AMBIGUOUS", "reason": "ambiguous"}
    selected_occurrence = occurrence if occurrence is not None else 1
    if selected_occurrence > len(matches):
        return {"status": "NOT_FOUND", "reason": "not_found"}
    selected = matches[selected_occurrence - 1]
    start_index = selected["line"] - 1
    end_index = len(lines)
    for following in headings:
        if following["line"] > selected["line"] and following["level"] <= selected["level"]:
            end_index = following["line"] - 1
            break
    section = "".join(lines[start_index:end_index])
    path_bytes = len(relative_name.encode("utf-8"))
    if any(len(part.encode("utf-8")) > MAX_TITLE_BYTES for part in selected["path"]):
        return _unsupported()
    result = {
        "status": "COMPLETE",
        "path": relative_name,
        "observed_sha256": observed,
        "heading_path": list(selected["path"]),
        "occurrence": selected_occurrence,
        "start_line": selected["line"],
        "end_line": end_index,
        "text": section,
        "truncated": False,
    }
    if path_bytes > MAX_TEXT:
        return _unsupported()
    prefix = _utf8_prefix(section, max_section_bytes)
    if prefix != section:
        result.update(status="TRUNCATED", text=prefix, truncated=True)
    if not _success_size(result):
        return _unsupported()
    return result
