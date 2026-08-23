"""Read-only lookup across explicitly configured lesson stores."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

STORE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
LESSON_ID_PATTERN = re.compile(r"^(?:KB|PROJECT)-\d{4}$")
STORE_TYPES = {"local", "shared"}
MAX_STORE_BYTES = 1024 * 1024


def validate_config(config: Dict[str, Any]) -> Tuple[List[Dict[str, str]], List[str]]:
    errors: List[str] = []
    if config.get("version") != 1:
        errors.append("configuration version must be 1")
    raw_stores = config.get("stores")
    if not isinstance(raw_stores, list) or not raw_stores:
        return [], errors + ["configuration must contain explicit stores"]

    stores: List[Dict[str, str]] = []
    names = set()
    types = set()
    for raw in raw_stores:
        if not isinstance(raw, dict):
            errors.append("store configuration must be an object")
            continue
        name = raw.get("name")
        store_type = raw.get("type")
        path = raw.get("path")
        if not isinstance(name, str) or not STORE_NAME_PATTERN.fullmatch(name):
            errors.append("store name is missing or invalid")
            continue
        if name in names:
            errors.append(f"duplicate store name: {name}")
        names.add(name)
        if store_type not in STORE_TYPES:
            errors.append(f"store {name} type must be local or shared")
            continue
        if store_type in types:
            errors.append(f"multiple {store_type} stores are ambiguous")
        types.add(store_type)
        if not isinstance(path, str) or not path.strip() or "\x00" in path:
            errors.append(f"store {name} path is missing or invalid")
            continue
        configured_path = Path(path)
        windows_absolute = bool(re.match(r"^[A-Za-z]:[\\/]", path))
        if configured_path.is_absolute() or windows_absolute or ".." in configured_path.parts or configured_path.suffix.lower() != ".json":
            errors.append(f"store {name} path must be a relative JSON file")
            continue
        stores.append({"name": name, "type": store_type, "path": path})

    return sorted(stores, key=lambda store: (0 if store["type"] == "local" else 1, store["name"])), errors


def load_store(path: Path) -> Dict[str, Any]:
    stat = path.stat()
    if not path.is_file() or stat.st_size > MAX_STORE_BYTES:
        raise ValueError("store must be a bounded regular file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("store must be an object")
    return value


def _search_store(store: Dict[str, Any], query: str) -> List[Dict[str, str]]:
    lessons = store.get("lessons")
    if not isinstance(lessons, list):
        raise ValueError("store lessons must be a list")
    needle = query.casefold()
    results: List[Dict[str, str]] = []
    seen = set()
    for lesson in lessons:
        if not isinstance(lesson, dict):
            raise ValueError("lesson must be an object")
        lesson_id = lesson.get("id")
        title = lesson.get("title")
        terms = lesson.get("search_terms", [])
        if not isinstance(lesson_id, str) or not LESSON_ID_PATTERN.fullmatch(lesson_id):
            raise ValueError("lesson ID is invalid")
        if lesson_id in seen:
            raise ValueError("duplicate lesson ID")
        seen.add(lesson_id)
        expected_prefix = "PROJECT-" if store.get("store_type") == "local" else "KB-"
        if not lesson_id.startswith(expected_prefix):
            raise ValueError("lesson ID does not match store ownership")
        if not isinstance(title, str) or not title.strip() or "\n" in title or "\r" in title:
            raise ValueError("lesson title is invalid")
        if not isinstance(terms, list) or any(not isinstance(term, str) for term in terms):
            raise ValueError("lesson search_terms are invalid")
        haystack = " ".join([lesson_id, title, *terms]).casefold()
        if needle in haystack:
            results.append({"id": lesson_id, "title": title})
    return results


def _load_with_timeout(path: Path, timeout_seconds: float) -> Tuple[Dict[str, Any], str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "kb_bootstrap.federated_lookup", "--read-store", str(path)],
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {}, "timeout"
    except OSError:
        return {}, "unavailable"
    if result.returncode != 0:
        return {}, "unavailable"
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}, "unavailable"
    return (value, "") if isinstance(value, dict) else ({}, "unavailable")


def federated_lookup(
    config: Dict[str, Any],
    query: str,
    base_dir: Path,
    timeout_seconds: float = 2.0,
) -> Tuple[str, bool]:
    if not isinstance(query, str):
        return "RESULT: BLOCKED (query must be a string)", False
    query = query.strip()
    stores, errors = validate_config(config)
    if not query:
        errors.append("query is required")
    if not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0 or timeout_seconds > 30:
        errors.append("timeout must be finite, greater than 0, and at most 30 seconds")
    if errors:
        lines = [f"RESULT: BLOCKED ({len(errors)} error(s))"]
        lines.extend(f"  - {error}" for error in errors)
        return "\n".join(lines), False

    lines = ["=== Federated Lesson Lookup ===", "precedence: local, shared"]
    total_results = 0
    available_stores = 0
    for store in stores:
        path = (base_dir / store["path"]).resolve()
        try:
            path.relative_to(base_dir.resolve())
        except ValueError:
            lines.append(f"store {store['name']} ({store['type']}): unavailable")
            continue
        loaded, load_error = _load_with_timeout(path, timeout_seconds)
        if loaded:
            loaded = dict(loaded)
            loaded["store_type"] = store["type"]
        if load_error:
            lines.append(f"store {store['name']} ({store['type']}): {load_error}")
            continue
        try:
            results = _search_store(loaded, query)
        except ValueError:
            lines.append(f"store {store['name']} ({store['type']}): unavailable")
            continue
        available_stores += 1
        lines.append(f"store {store['name']} ({store['type']}): {len(results)} result(s)")
        for result in results:
            total_results += 1
            lines.append(f"[{store['type'].upper()}] {result['id']} — {result['title']}")
            lines.append(f"  provenance: store={store['name']}; type={store['type']}; lesson={result['id']}")
        if store["type"] == "local" and results:
            lines.append("shared fallback: skipped (local match found)")
            break

    if not available_stores:
        lines.append("RESULT: BLOCKED (all configured stores are unavailable)")
        return "\n".join(lines), False
    lines.append(f"results: {total_results}")
    lines.append("store writes: no")
    lines.append("RESULT: OK")
    return "\n".join(lines), True


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--read-store":
        try:
            print(json.dumps(load_store(Path(sys.argv[2]))))
            return 0
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            return 1

    parser = argparse.ArgumentParser(description="Read-only lookup across explicit lesson stores")
    parser.add_argument("--config", required=True, help="Explicit store configuration JSON")
    parser.add_argument("--query", required=True, help="Lookup query")
    parser.add_argument("--timeout", type=float, default=2.0, help="Per-store timeout in seconds")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("RESULT: BLOCKED (configuration is unavailable or invalid JSON)")
        return 1
    if not isinstance(config, dict):
        print("RESULT: BLOCKED (configuration must be an object)")
        return 1
    report, valid = federated_lookup(config, args.query, config_path.parent, args.timeout)
    print(report)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
