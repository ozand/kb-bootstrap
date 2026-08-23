"""Read-only canonical and raw QMD search wrapper."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Tuple, Union

from .qmd_validator import _collection_values


def _run(command: List[str], cwd: Path) -> Tuple[str, bool]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return "", False
    return result.stdout.strip(), result.returncode == 0


def _mode_collection(project_root: Path, mode: str) -> Tuple[str, str]:
    collections_dir = project_root / "qmd" / "collections"
    suffix = "-raw" if mode == "raw" else "-wiki"
    matches = []
    if collections_dir.is_dir():
        for collection_file in sorted(collections_dir.glob("*.yaml")):
            name, paths, _ = _collection_values(collection_file)
            if name.endswith(suffix) and paths:
                matches.append(name)

    if len(matches) != 1:
        label = "raw" if mode == "raw" else "canonical"
        return "", f"{label} collection is missing or ambiguous"
    return matches[0], ""


def search_qmd(
    query: str,
    mode: str = "canonical",
    project_root: Union[str, Path] = Path("."),
    limit: int = 5,
) -> Tuple[str, bool]:
    """Search one validated QMD collection without modifying the index or sources."""
    root = Path(project_root).resolve()
    query = query.strip()
    errors = []

    if mode not in {"canonical", "raw"}:
        errors.append("mode must be canonical or raw")
    if not query:
        errors.append("query is required")
    if limit < 1:
        errors.append("limit must be positive")

    collection = ""
    if not errors:
        try:
            collection, collection_error = _mode_collection(root, mode)
        except (OSError, UnicodeError):
            collection_error = f"{mode} collection is unavailable"
        if collection_error:
            errors.append(collection_error)

    results = []
    if not errors:
        output, ok = _run(
            [
                "qmd",
                "search",
                "-c",
                collection,
                "--format",
                "json",
                "-n",
                str(limit),
                "--",
                query,
            ],
            root,
        )
        if not ok:
            errors.append("QMD search is unavailable")
        else:
            try:
                parsed = json.loads(output)
                if not isinstance(parsed, list):
                    raise ValueError
                results = parsed
            except (json.JSONDecodeError, ValueError):
                errors.append("QMD search returned an invalid result")

    lines = [
        "=== QMD Search ===",
        f"mode: {mode}",
        f"collection: {collection or 'unavailable'}",
    ]
    if errors:
        lines.append(f"RESULT: BLOCKED ({len(errors)} error(s))")
        lines.extend(f"  - {error}" for error in errors)
        return "\n".join(lines), False

    result_label = "RAW" if mode == "raw" else "CANONICAL"
    lines.append(f"results: {len(results)}")
    for result in results:
        file_value = str(result.get("file", "unavailable"))
        source = file_value if file_value.startswith("qmd://") else "unavailable"
        title = str(result.get("title", "untitled"))
        score = result.get("score", "unavailable")
        lines.extend(
            [
                f"[{result_label}] {title}",
                f"  provenance: collection={collection}; source={source}",
                f"  score: {score}",
            ]
        )
    lines.append("RESULT: OK")
    return "\n".join(lines), True
