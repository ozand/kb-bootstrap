#!/usr/bin/env python3
"""Copy one explicitly selected RawCapture Markdown file into a study."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

MAX_BYTES = 64 * 1024 * 1024
DESTINATION = re.compile(r"^[0-9]{3}-(?:[a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
KEY = re.compile(r"^[a-z_]+$")
TAG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED = {"type", "title", "url", "captured_at", "captured_by", "entity", "fidelity"}


class ImportErrorResult(ValueError):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


class PartialCopyError(OSError):
    pass


def _fail(status: str, message: str):
    raise ImportErrorResult(status, message)


def _reject_symlink_ancestors(path: Path, label: str) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            _fail("BLOCKED", f"{label} path contains a symlink")


def _contained_regular(root: Path, rel: Path, *, root_label: str) -> Path:
    if rel.is_absolute() or not rel.parts or any(p in {"", ".", ".."} for p in rel.parts):
        _fail("BLOCKED", f"{root_label} path is unsafe")
    _reject_symlink_ancestors(root, root_label)
    current = root
    if current.is_symlink() or not current.is_dir():
        _fail("BLOCKED", f"{root_label} root is unavailable or unsafe")
    for part in rel.parts[:-1]:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            _fail("BLOCKED", f"{root_label} parent is unavailable or unsafe")
    target = current / rel.parts[-1]
    if target.is_symlink() or not target.is_file():
        _fail("BLOCKED", f"{root_label} file is unavailable or unsafe")
    try:
        target.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        _fail("BLOCKED", f"{root_label} file escapes selected root")
    return target


def _parse_scalar(value: str):
    value = value.strip()
    if not value or any(ord(ch) < 32 and ch != "\t" for ch in value):
        _fail("BLOCKED", "frontmatter scalar is blank or contains controls")
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except (ValueError, json.JSONDecodeError):
            _fail("BLOCKED", "frontmatter quoting is malformed")
        if not isinstance(parsed, str) or "\n" in parsed or "\r" in parsed:
            _fail("BLOCKED", "frontmatter scalar must be one line")
        return parsed
    if value.startswith(("'", "[", "{", "|", ">", "&", "*", "!")):
        _fail("BLOCKED", "frontmatter scalar syntax is unsupported")
    if any(ch in value for ch in "[]{}#") or ": " in value:
        _fail("BLOCKED", "frontmatter scalar syntax is unsupported")
    if "\t" in value:
        _fail("BLOCKED", "frontmatter tabs are unsupported")
    return value


def _parse_tags(value: str):
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        _fail("BLOCKED", "tags must use a single-line inline list")
    body = value[1:-1].strip()
    if not body:
        return []
    items = [part.strip() for part in body.split(",")]
    if any(not TAG.fullmatch(item) for item in items):
        _fail("BLOCKED", "tags contain unsupported values")
    return items


def _validate_frontmatter(data: bytes):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _fail("BLOCKED", "input is not UTF-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        _fail("BLOCKED", "frontmatter must begin on the first line")
    closing = next((i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---"), None)
    if closing is None:
        _fail("BLOCKED", "frontmatter closing separator is missing")
    fields = {}
    for line in lines[1:closing]:
        raw = line.rstrip("\r\n")
        if not raw or "\t" in raw or raw[:1].isspace() or ":" not in raw:
            _fail("BLOCKED", "frontmatter line syntax is unsupported")
        key, value = raw.split(":", 1)
        if not KEY.fullmatch(key) or key in fields:
            _fail("BLOCKED", "frontmatter has an invalid or duplicate key")
        fields[key] = _parse_tags(value) if key == "tags" else (
            "" if key == "entity" and not value.strip() else _parse_scalar(value)
        )
    if set(fields) - (REQUIRED | {"tags"}) or not REQUIRED <= set(fields):
        _fail("BLOCKED", "frontmatter keys are unsupported or incomplete")
    if fields["type"] != "RawCapture":
        _fail("BLOCKED", "frontmatter type is not RawCapture")
    if fields["fidelity"] not in {"full", "partial", "blocked"}:
        _fail("BLOCKED", "fidelity value is unsupported")
    from datetime import datetime
    try:
        stamp = datetime.fromisoformat(fields["captured_at"].replace("Z", "+00:00"))
    except ValueError:
        _fail("BLOCKED", "captured_at is not an ISO timestamp")
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        _fail("BLOCKED", "captured_at must include an offset")
    body = text[sum(len(line) for line in lines[:closing + 1]):]
    if re.search(r"(?m)^---\s*$", body):
        _fail("BLOCKED", "extra document separator is unsupported")
    return body


def _validate_links(body: str, destination_md: Path, study: Path):
    if (re.search(r"(?im)^\s*\[[^]]+\]\s*:", body)
            or re.search(r"<[^>]+>", body)
            or re.search(r"!\[[^]\n]*\]\s*[^ (\n]", body)):
        _fail("UNSUPPORTED", "reference definitions, HTML, or image-like syntax are unsupported")
    pattern = re.compile(r"!?\[([^]\n]*)\]\(([^)\n]*)\)")
    matches = list(pattern.finditer(body))
    scrubbed = pattern.sub("", body)
    if re.search(r"!?\[[^]\n]*\](?:\[[^]\n]*\])?", scrubbed):
        _fail("UNSUPPORTED", "unsupported link-like Markdown syntax")
    for match in matches:
        target = match.group(2)
        if not target or any(ch.isspace() or unicodedata.category(ch) == "Cc" or ch in "()" for ch in target):
            _fail("UNSUPPORTED", "inline link target syntax is unsupported")
        if target.startswith("#"):
            continue
        if re.match(r"^[A-Za-z]:", target) or target.startswith("\\\\"):
            _fail("UNSUPPORTED", "drive and UNC link targets are unsupported")
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
            continue
        candidate = Path(target)
        if candidate.is_absolute() or ".." in candidate.parts:
            _fail("UNSUPPORTED", "local link target escapes or is absolute")
        resolved = (destination_md.parent / candidate)
        try:
            resolved.relative_to(destination_md.parent)
        except ValueError:
            _fail("UNSUPPORTED", "local link target escapes study")
        current = destination_md.parent
        for part in candidate.parts:
            current = current / part
            if current.is_symlink():
                _fail("UNSUPPORTED", "local link target uses a symlink")
        try:
            resolved_real = resolved.resolve(strict=True)
            resolved_real.relative_to(study.resolve(strict=True))
        except (OSError, ValueError):
            _fail("UNSUPPORTED", "local link target is missing or outside study")
        if not resolved_real.is_file():
            _fail("UNSUPPORTED", "local link target is not a regular file")


def _exclusive_copy(destination: Path, data: bytes, study: Path) -> None:
    root = study.absolute()
    target = destination.absolute()
    try:
        if os.path.commonpath((str(root), str(target))) != str(root):
            _fail("BLOCKED", "destination escapes selected study")
    except ValueError:
        _fail("BLOCKED", "destination escapes selected study")
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current = current / part
        if current.is_symlink():
            _fail("BLOCKED", "study path contains a symlink")
    relative = target.relative_to(root)
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            _fail("BLOCKED", "destination parent is unavailable or unsafe")
    if target.is_symlink():
        _fail("BLOCKED", "destination is a symlink")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(target), flags, 0o666)
    try:
        stream = os.fdopen(fd, "wb", closefd=False)
        stream.write(data)
        stream.close()
        os.close(fd)
    except OSError as exc:
        try:
            if 'stream' in locals():
                stream.close()
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
        if target.exists() and not target.is_symlink():
            raise PartialCopyError("exclusive destination write was partial") from exc
        raise


def import_capture(study_dir: Path, input_root: Path, input_relative: str,
                   destination_name: str) -> tuple[str, str]:
    study = study_dir.absolute()
    root = input_root.absolute()
    if not DESTINATION.fullmatch(destination_name):
        _fail("BLOCKED", "destination name must match NNN-<lowercase-slug>.md")
    try:
        _reject_symlink_ancestors(study, "study")
        _reject_symlink_ancestors(root, "input root")
        study_resolved = study.resolve(strict=True)
        raw = study / "raw"
        if study.is_symlink() or not study_resolved.is_dir() or raw.is_symlink() or not raw.is_dir():
            _fail("BLOCKED", "selected study or raw directory is unavailable or unsafe")
        source = _contained_regular(root, Path(input_relative), root_label="input")
        destination = raw / destination_name
        if destination.is_symlink() or destination.exists():
            _fail("BLOCKED", "destination already exists")
        with source.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            _fail("BLOCKED", "input exceeds 64 MiB limit")
        body = _validate_frontmatter(data)
        _validate_links(body, destination, study)
        destination_identity = os.stat(raw, follow_symlinks=False)
        if raw.is_symlink() or not raw.is_dir() or os.stat(raw, follow_symlinks=False) != destination_identity:
            _fail("BLOCKED", "study raw directory changed during validation")
        try:
            _exclusive_copy(destination, data, study)
        except FileExistsError:
            _fail("BLOCKED", "destination already exists")
        except PartialCopyError:
            _fail("PARTIAL", f"destination may contain a partial copy: {destination.relative_to(study).as_posix()}")
        except ImportErrorResult:
            raise
        except OSError:
            _fail("BLOCKED", "destination is unavailable or unsafe")
        return "IMPORTED", destination.relative_to(study).as_posix()
    except ImportErrorResult:
        raise
    except (OSError, ValueError):
        _fail("BLOCKED", "input or study path is unavailable or unsafe")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study_dir", type=Path)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--input", required=True, dest="input_relative")
    parser.add_argument("--destination", required=True)
    args = parser.parse_args(argv)
    try:
        status, relative = import_capture(args.study_dir, args.input_root,
                                          args.input_relative, args.destination)
    except ImportErrorResult as exc:
        print(f"{exc.status}: {exc}")
        return 2
    print(f"{status}: {relative}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
