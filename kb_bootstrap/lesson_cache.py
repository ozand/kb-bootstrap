"""Opt-in read-only cache of explicitly selected shared lessons."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
LESSON_ID_PATTERN = re.compile(r"^KB-\d{4}$")
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T[0-9:.+-]+Z?)?$")
CONTENT_FIELDS = ("title", "problem", "resolution", "prevention")
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(token|password|secret|api[_-]?key|authorization)\s*[:=]"),
    re.compile(r"(?i)bearer\s+\S+"),
    re.compile(r"(?i)[a-z][a-z0-9+.-]*://[^\s/@]+:[^\s/@]+@"),
    re.compile(r"[A-Za-z]:[\\/]"),
    re.compile(r"(?:^|[\s\"'\[{(:=])/{1,2}\S+"),
    re.compile(r"(?:^|[\s\"'\[{(:=])\\{1,2}\S+"),
]


def _repository(value: Any) -> bool:
    if not isinstance(value, str) or not REPOSITORY_PATTERN.fullmatch(value):
        return False
    owner, repository = value.split("/", 1)
    return owner not in {".", ".."} and repository not in {".", ".."}


def _load(path: Path, label: str) -> Tuple[Dict[str, Any], List[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}, [f"{label} is unavailable or invalid JSON"]
    if not isinstance(value, dict):
        return {}, [f"{label} must be an object"]
    return value, []


def _content(value: Any, lesson_id: str) -> Tuple[Dict[str, str], List[str]]:
    if not isinstance(value, dict):
        return {}, [f"lesson {lesson_id} content must be an object"]
    sanitized: Dict[str, str] = {}
    errors: List[str] = []
    for field in CONTENT_FIELDS:
        item = value.get(field)
        if not isinstance(item, str) or not item.strip():
            errors.append(f"lesson {lesson_id} content {field} is required")
        elif any(pattern.search(item) for pattern in SENSITIVE_PATTERNS):
            errors.append(f"lesson {lesson_id} content {field} failed sanitization")
        else:
            sanitized[field] = item
    return sanitized, errors


def validate_source(source: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    errors: List[str] = []
    if source.get("version") != 1:
        errors.append("source version must be 1")
    repository = source.get("source_repository")
    if not _repository(repository):
        errors.append("source_repository must use owner/repository syntax")
    registry_version = source.get("registry_version")
    if not isinstance(registry_version, str) or not VERSION_PATTERN.fullmatch(registry_version):
        errors.append("registry_version is missing or invalid")
    generated_at = source.get("generated_at")
    if not isinstance(generated_at, str) or not DATE_PATTERN.fullmatch(generated_at):
        errors.append("generated_at is missing or invalid")

    lessons = source.get("lessons")
    if not isinstance(lessons, list):
        errors.append("source lessons must be a list")
        lessons = []
    by_id: Dict[str, Dict[str, Any]] = {}
    for lesson in lessons:
        if not isinstance(lesson, dict):
            errors.append("source contains a non-object lesson")
            continue
        lesson_id = lesson.get("id")
        if not isinstance(lesson_id, str) or not LESSON_ID_PATTERN.fullmatch(lesson_id):
            errors.append("source contains an invalid lesson ID")
            continue
        if lesson_id in by_id:
            errors.append(f"source contains duplicate lesson ID: {lesson_id}")
            continue
        lesson_version = lesson.get("version")
        updated = lesson.get("updated")
        if not isinstance(lesson_version, str) or not VERSION_PATTERN.fullmatch(lesson_version):
            errors.append(f"lesson {lesson_id} version is missing or invalid")
        if not isinstance(updated, str) or not DATE_PATTERN.fullmatch(updated):
            errors.append(f"lesson {lesson_id} updated metadata is missing or invalid")
        content, content_errors = _content(lesson.get("content"), lesson_id)
        errors.extend(content_errors)
        by_id[lesson_id] = {
            "id": lesson_id,
            "lesson_version": lesson_version,
            "source_updated": updated,
            "content": content,
        }
    return by_id, errors


def _validate_allowlist(allowlist: List[str]) -> List[str]:
    if not allowlist:
        return ["allowlist must contain at least one lesson ID"]
    if any(not LESSON_ID_PATTERN.fullmatch(item) for item in allowlist):
        return ["allowlist contains an invalid lesson ID"]
    if len(set(allowlist)) != len(allowlist):
        return ["allowlist contains duplicate lesson IDs"]
    return []


def _existing_entries(cache: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    if not cache:
        return {}, []
    if cache.get("version") != 1 or not _repository(cache.get("source_repository")):
        return {}, ["existing cache metadata is invalid"]
    entries = cache.get("entries")
    if not isinstance(entries, list):
        return {}, ["existing cache entries must be a list"]
    by_id: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not LESSON_ID_PATTERN.fullmatch(entry["id"]):
            return {}, ["existing cache contains an invalid lesson entry"]
        if entry["id"] in by_id:
            return {}, [f"existing cache contains duplicate lesson ID: {entry['id']}"]
        by_id[entry["id"]] = entry
    return by_id, []


def _fresh_entry(source: Dict[str, Any], lesson: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": lesson["id"],
        "source_repository": source["source_repository"],
        "registry_version": source["registry_version"],
        "lesson_version": lesson["lesson_version"],
        "source_updated": lesson["source_updated"],
        "freshness": "fresh",
        "content": lesson["content"],
    }


def sync_cache(
    source_path: Union[str, Path],
    cache_path: Union[str, Path],
    allowlist: List[str],
    prune: bool = False,
) -> Tuple[str, bool]:
    source_file = Path(source_path).resolve()
    cache_file = Path(cache_path).resolve()
    errors = _validate_allowlist(allowlist)
    if source_file == cache_file:
        errors.append("source and cache paths must differ")
    if not cache_file.parent.is_dir():
        errors.append("cache parent directory is unavailable")
    source, source_errors = _load(source_file, "source bundle")
    errors.extend(source_errors)
    lessons: Dict[str, Dict[str, Any]] = {}
    if not source_errors:
        lessons, contract_errors = validate_source(source)
        errors.extend(contract_errors)
    missing = sorted(set(allowlist) - set(lessons))
    if missing:
        errors.append("allowlist references unavailable lessons: " + ", ".join(missing))

    cache: Dict[str, Any] = {}
    existing: Dict[str, Dict[str, Any]] = {}
    if cache_file.exists():
        cache, cache_errors = _load(cache_file, "existing cache")
        errors.extend(cache_errors)
        if not cache_errors:
            existing, existing_errors = _existing_entries(cache)
            errors.extend(existing_errors)
            if cache.get("source_repository") != source.get("source_repository"):
                errors.append("existing cache source conflicts with selected source")
    if errors:
        lines = [f"RESULT: BLOCKED ({len(errors)} error(s))"]
        lines.extend(f"  - {error}" for error in errors)
        return "\n".join(lines), False

    result_entries = {} if prune else dict(existing)
    refreshed = []
    for lesson_id in allowlist:
        result_entries[lesson_id] = _fresh_entry(source, lessons[lesson_id])
        refreshed.append(lesson_id)
    for lesson_id, entry in list(result_entries.items()):
        source_lesson = lessons.get(lesson_id)
        if lesson_id not in allowlist:
            if source_lesson is None:
                entry = dict(entry)
                entry["freshness"] = "unavailable"
                result_entries[lesson_id] = entry
            elif entry.get("lesson_version") != source_lesson.get("lesson_version"):
                entry = dict(entry)
                entry["freshness"] = "stale"
                result_entries[lesson_id] = entry

    prepared = {
        "version": 1,
        "source_repository": source["source_repository"],
        "registry_version": source["registry_version"],
        "source_generated_at": source["generated_at"],
        "selection": sorted(allowlist),
        "entries": [result_entries[key] for key in sorted(result_entries)],
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=cache_file.parent, delete=False) as temp:
            temporary = Path(temp.name)
            temp.write(json.dumps(prepared, indent=2, sort_keys=True) + "\n")
        os.replace(temporary, cache_file)
    except OSError:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        return "RESULT: BLOCKED (cache cannot be written)", False

    pruned = sorted(set(existing) - set(result_entries))
    return "\n".join(
        [
            "RESULT: OK",
            f"source repository: {source['source_repository']}",
            f"refreshed: {', '.join(sorted(refreshed))}",
            f"pruned: {', '.join(pruned) if pruned else 'none'}",
            "shared store write: no",
            "cache authority: read-only copy",
        ]
    ), True


def check_cache(
    source_path: Union[str, Path], cache_path: Union[str, Path], allowlist: List[str]
) -> Tuple[str, bool]:
    source, source_errors = _load(Path(source_path), "source bundle")
    cache, cache_errors = _load(Path(cache_path), "cache")
    errors = _validate_allowlist(allowlist) + source_errors + cache_errors
    lessons: Dict[str, Dict[str, Any]] = {}
    entries: Dict[str, Dict[str, Any]] = {}
    if not source_errors:
        lessons, contract_errors = validate_source(source)
        errors.extend(contract_errors)
    if not cache_errors:
        entries, entry_errors = _existing_entries(cache)
        errors.extend(entry_errors)
    if source and cache and source.get("source_repository") != cache.get("source_repository"):
        errors.append("cache source conflicts with selected source")
    if errors:
        lines = [f"RESULT: BLOCKED ({len(errors)} error(s))"]
        lines.extend(f"  - {error}" for error in errors)
        return "\n".join(lines), False

    stale = []
    unavailable = []
    for lesson_id in allowlist:
        source_lesson = lessons.get(lesson_id)
        cached = entries.get(lesson_id)
        if source_lesson is None or cached is None:
            unavailable.append(lesson_id)
        elif cached.get("lesson_version") != source_lesson.get("lesson_version"):
            stale.append(lesson_id)
    if stale or unavailable:
        lines = ["RESULT: STALE"]
        lines.append("stale: " + (", ".join(stale) if stale else "none"))
        lines.append("unavailable: " + (", ".join(unavailable) if unavailable else "none"))
        lines.append("shared store write: no")
        return "\n".join(lines), False
    return "\n".join(["RESULT: OK", "freshness: fresh", "shared store write: no"]), True
