#!/usr/bin/env python3
"""Produce one explicit RawCapture from caller-supplied local UTF-8 text."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

# Packaged scripts are copied into user workspaces; do not leave bytecode beside them.
_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    import import_local_capture as capture
finally:
    sys.dont_write_bytecode = _dont_write_bytecode

MAX_BYTES = capture.MAX_BYTES
DESTINATION = capture.DESTINATION


def _blocked(message: str, status: str = "BLOCKED"):
    raise capture.ImportErrorResult(status, message)


def _metadata(values: dict[str, str]) -> bytes:
    required = ("title", "url", "captured_at", "captured_by")
    for key in required:
        if not values[key]:
            _blocked(f"{key} is required")
    for key, value in values.items():
        if any(unicodedata.category(ch) == "Cc" or ch in "\u2028\u2029\r\n" for ch in value):
            _blocked(f"{key} must be a single line without controls")
    if values["fidelity"] not in {"full", "partial", "blocked"}:
        _blocked("fidelity must be full, partial, or blocked")
    fields = [
        "---", "type: RawCapture",
        *(f"{key}: {json.dumps(values[key], ensure_ascii=False)}"
          for key in ("title", "url", "captured_at", "captured_by", "entity")),
        f"fidelity: {values['fidelity']}", "---",
    ]
    try:
        return ("\n".join(fields) + "\n").encode("utf-8")
    except UnicodeEncodeError:
        _blocked("metadata cannot be represented as UTF-8")


def _exclusive_publish(destination: Path, data: bytes, study: Path) -> None:
    """Publish exclusively; classify partial only after this call owns the file."""
    root, target = study.absolute(), destination.absolute()
    try:
        if os.path.commonpath((str(root), str(target))) != str(root):
            _blocked("destination escapes selected study")
    except ValueError:
        _blocked("destination escapes selected study")
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current = current / part
        if current.is_symlink():
            _blocked("study path contains a symlink")
    for part in target.relative_to(root).parts[:-1]:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            _blocked("destination parent is unavailable or unsafe")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(str(target), flags, 0o666)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
    except OSError as exc:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise capture.PartialCopyError("exclusive destination write was partial") from exc
    try:
        os.close(descriptor)
    except OSError as exc:
        raise capture.PartialCopyError("exclusive destination close was partial") from exc


def produce_capture(study_dir: Path, input_root: Path, input_relative: str,
                    destination_name: str, *, title: str, url: str,
                    captured_at: str, captured_by: str, entity: str,
                    fidelity: str) -> tuple[str, str]:
    study, root = study_dir.absolute(), input_root.absolute()
    if (capture._unsafe_input_spelling(input_relative) or "\\\\" in input_relative
            or any(part in {"", ".", ".."} for part in input_relative.split("/"))):
        _blocked("input path uses an unsafe spelling")
    if not DESTINATION.fullmatch(destination_name):
        _blocked("destination name must match NNN-<lowercase-slug>.md")
    try:
        capture._reject_symlink_ancestors(study, "study")
        capture._reject_symlink_ancestors(root, "input root")
        if study.is_symlink() or not study.is_dir():
            _blocked("selected study is unavailable or unsafe")
        raw = study / "raw"
        if raw.is_symlink() or not raw.is_dir():
            _blocked("study raw directory is unavailable or unsafe")
        source = capture._contained_regular(root, Path(input_relative), root_label="input")
        with source.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            _blocked("input exceeds 64 MiB limit")
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _blocked("input is not UTF-8")
        if data.startswith(b"\xef\xbb\xbf"):
            _blocked("UTF-8 BOM is unsupported")
        for char in text:
            if unicodedata.category(char) == "Cc" and char not in "\t\n\r":
                _blocked("input contains unsupported control characters")
        values = {"title": title, "url": url, "captured_at": captured_at,
                  "captured_by": captured_by, "entity": entity, "fidelity": fidelity}
        header = _metadata(values)
        output = header + data
        if len(output) > MAX_BYTES:
            _blocked("generated RawCapture exceeds 64 MiB limit")
        # Validate the exact emitted format through the accepted importer parser.
        body = capture._validate_frontmatter(output)
        destination = raw / destination_name
        capture._validate_links(body, destination, study)
        if destination.exists() or destination.is_symlink():
            _blocked("destination already exists")
        try:
            _exclusive_publish(destination, output, study)
        except FileExistsError:
            _blocked("destination already exists")
        except capture.PartialCopyError:
            _blocked(f"destination may contain partial output: {destination.relative_to(study).as_posix()}", "PARTIAL")
        except capture.ImportErrorResult:
            raise
        except OSError:
            _blocked("destination is unavailable or unsafe")
        return "CREATED", destination.relative_to(study).as_posix()
    except capture.ImportErrorResult:
        raise
    except (OSError, ValueError):
        _blocked("input or study path is unavailable or unsafe")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study_dir", type=Path)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--input", required=True, dest="input_relative")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--url", required=True, help="caller-provided unverified source reference")
    parser.add_argument("--captured-at", required=True)
    parser.add_argument("--captured-by", required=True)
    parser.add_argument("--entity", required=True)
    parser.add_argument("--fidelity", required=True, choices=("full", "partial", "blocked"))
    args = parser.parse_args(argv)
    try:
        status, relative = produce_capture(
            args.study_dir, args.input_root, args.input_relative, args.destination,
            title=args.title, url=args.url, captured_at=args.captured_at,
            captured_by=args.captured_by, entity=args.entity, fidelity=args.fidelity,
        )
    except capture.ImportErrorResult as exc:
        print(f"{exc.status}: {exc}")
        return 2
    print(f"{status}: {relative} (caller-provided metadata; source not verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
