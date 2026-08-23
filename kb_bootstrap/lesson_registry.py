"""Read-only validation and fail-closed ID allocation for lesson registries."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

ID_PATTERN = re.compile(r"^KB-(\d{4})$")
FILENAME_PATTERN = re.compile(r"^(KB-\d{4})-[A-Za-z0-9._-]+\.md$")


def _frontmatter(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    parsed = yaml.safe_load(text[4:end])
    return parsed if isinstance(parsed, dict) else {}


def _index(path: Path) -> Dict[str, object]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def validate_registry(root: Path) -> Tuple[List[str], Dict[str, object]]:
    errors: List[str] = []
    lessons_dir = root / "lessons"
    index_path = root / "index.yaml"
    if not lessons_dir.is_dir() or not index_path.is_file():
        return ["registry lessons directory or index is unavailable"], {}

    try:
        index = _index(index_path)
    except (OSError, UnicodeError, yaml.YAMLError):
        return ["registry index is unavailable or invalid"], {}

    raw_entries = index.get("lessons")
    entries = raw_entries if isinstance(raw_entries, list) else []
    if raw_entries is not None and not isinstance(raw_entries, list):
        errors.append("index lessons must be a list")

    index_ids: List[str] = []
    index_files: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("index contains a non-object lesson entry")
            continue
        lesson_id = entry.get("id")
        file_name = entry.get("file")
        if not isinstance(lesson_id, str) or not ID_PATTERN.fullmatch(lesson_id):
            errors.append("index contains an invalid lesson ID")
        else:
            index_ids.append(lesson_id)
        if not isinstance(file_name, str) or not file_name.startswith("lessons/"):
            errors.append(f"index entry {lesson_id or 'unknown'} has an invalid file reference")
        else:
            index_files.append(file_name)
            filename_match = FILENAME_PATTERN.fullmatch(Path(file_name).name)
            file_id = filename_match.group(1) if filename_match else None
            if isinstance(lesson_id, str) and file_id != lesson_id:
                errors.append(f"index ID/file mismatch: {lesson_id}")

    for duplicate, count in sorted(Counter(index_ids).items()):
        if count > 1:
            errors.append(f"duplicate lesson ID: {duplicate}")
    for duplicate, count in sorted(Counter(index_files).items()):
        if count > 1:
            match = FILENAME_PATTERN.fullmatch(Path(duplicate).name)
            reference = match.group(1) if match else "unknown"
            errors.append(f"duplicate lesson file entry for ID: {reference}")

    file_ids: List[str] = []
    file_refs: Set[str] = set()
    for lesson_file in sorted(lessons_dir.glob("*.md")):
        filename_match = FILENAME_PATTERN.fullmatch(lesson_file.name)
        filename_id = filename_match.group(1) if filename_match else ""
        if not filename_id:
            errors.append(f"lesson filename has invalid ID format: {lesson_file.name}")
            continue
        try:
            metadata = _frontmatter(lesson_file)
        except (OSError, UnicodeError, yaml.YAMLError):
            errors.append(f"lesson {filename_id} frontmatter is unavailable or invalid")
            continue
        frontmatter_id = metadata.get("id")
        if frontmatter_id != filename_id:
            errors.append(f"lesson {filename_id} filename/frontmatter ID mismatch")
        file_ids.append(filename_id)
        file_refs.add(f"lessons/{lesson_file.name}")

    for duplicate, count in sorted(Counter(file_ids).items()):
        if count > 1:
            errors.append(f"duplicate lesson ID: {duplicate}")

    index_id_set = set(index_ids)
    file_id_set = set(file_ids)
    for lesson_id in sorted(file_id_set - index_id_set):
        errors.append(f"lesson missing from index: {lesson_id}")
    for lesson_id in sorted(index_id_set - file_id_set):
        errors.append(f"index references missing lesson: {lesson_id}")
    for file_ref in sorted(set(index_files) - file_refs):
        matching_id = next(
            (entry.get("id") for entry in entries if isinstance(entry, dict) and entry.get("file") == file_ref),
            "unknown",
        )
        if matching_id in file_id_set:
            errors.append(f"index file reference mismatch: {matching_id}")

    count = index.get("count")
    if not isinstance(count, int) or count != len(entries) or count != len(file_ids):
        errors.append(
            f"index count drift: declared={count if isinstance(count, int) else 'invalid'}; entries={len(entries)}; files={len(file_ids)}"
        )

    return errors, {
        "ids": sorted(file_id_set | index_id_set),
        "entries": len(entries),
        "files": len(file_ids),
    }


def next_id(root: Path) -> Tuple[Optional[str], List[str]]:
    errors, summary = validate_registry(root)
    if errors:
        return None, errors
    numbers = [int(match.group(1)) for lesson_id in summary["ids"] if (match := ID_PATTERN.fullmatch(lesson_id))]
    candidate = (max(numbers) + 1) if numbers else 1
    if candidate > 9999:
        return None, ["lesson ID space is exhausted"]
    lesson_id = f"KB-{candidate:04d}"
    if lesson_id in summary["ids"]:
        return None, [f"lesson ID collision: {lesson_id}"]
    return lesson_id, []


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate shared lesson registry identity and index consistency")
    parser.add_argument("--root", required=True, help="Explicit registry root containing lessons/ and index.yaml")
    parser.add_argument("--next-id", action="store_true", help="Print the next ID only when registry state is valid")
    args = parser.parse_args()
    root = Path(args.root)

    if args.next_id:
        lesson_id, errors = next_id(root)
        if errors:
            print(f"RESULT: BLOCKED ({len(errors)} error(s))")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("RESULT: OK")
        print(f"next lesson ID: {lesson_id}")
        return 0

    errors, summary = validate_registry(root)
    if errors:
        print(f"RESULT: BLOCKED ({len(errors)} error(s))")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("RESULT: OK")
    print(f"lesson files: {summary['files']}")
    print(f"index entries: {summary['entries']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
