"""Read-only scaffold repeat guard implementing ADR-016."""
from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath
from typing import Dict, List, Tuple

from .project_lesson_enablement import ARTIFACTS, inspect_project_lessons


QMD_PATHS = ("qmd.json", "qmd/collections/wiki.yaml", "qmd/collections/raw.yaml")
SINGLE_SKILLS = ("kb-wiki-builder", "qmd-operator", "kb-lookup")
TARGET_DIRS = (
    ".agents/skills/qmd-operator", ".agents/skills/kb-wiki-builder",
    ".agents/skills/kb-lookup", "qmd/collections", "kb/raw", "kb/research",
    "kb/wiki/entities", "kb/wiki/concepts", "kb/wiki/reports",
)
TARGET_MARKERS = (
    "kb/raw/.gitkeep", "kb/research/.gitkeep", "kb/wiki/entities/.gitkeep",
    "kb/wiki/concepts/.gitkeep", "kb/wiki/reports/.gitkeep",
)
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _slug(name):
    value = "".join(c.lower() if c.isalnum() or c in "._-" else "-" for c in name)
    return value.strip("-._") or "project"


def _text_payload(text: str) -> bytes:
    return text.replace("\n", os.linesep).encode("utf-8")


def qmd_payloads(layout, project_name):
    if layout not in ("single", "umbrella"):
        raise ValueError("unsupported layout")
    config = (
        "{\n  \"version\": \"1.0\",\n  \"workspace\": {\n"
        f"    \"name\": \"{project_name}_kb\",\n"
        "    \"collections_dir\": \"./qmd/collections\",\n"
        "    \"db_path\": \".qmd/vector.db\"\n  },\n"
        "  \"models\": {\n    \"embedding\": \"text-embedding-3-small\"\n  }\n}"
    )
    wiki = (f"name: {project_name}-wiki\npaths:\n  - ../../kb/\nexclude:\n"
            "  - \"raw/**\"\n  - \"research/**\"\n  - \"**/.DS_Store\"\n")
    raw = (f"name: {project_name}-raw\npaths:\n  - ../../kb/raw/\n"
           "  - ../../kb/research/\nexclude:\n  - \"**/.DS_Store\"\n")
    return {"qmd.json": _text_payload(config), QMD_PATHS[1]: _text_payload(wiki), QMD_PATHS[2]: _text_payload(raw)}


def _safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if (not name or "\\" in name or "\x00" in name or path.is_absolute()
            or path.as_posix() != name or any(part in ("", ".", "..") for part in path.parts)):
        raise ValueError("unsafe managed name")
    return name


def _components_safe(path: Path) -> bool:
    raw = Path(path)
    if ".." in raw.parts:
        return False
    absolute = Path(os.path.abspath(os.fspath(raw)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            continue
        except OSError:
            return False
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE:
            return False
    return True


def _inventory_files(package_root: Path) -> Dict[str, bytes]:
    skills = package_root / "templates" / "skills"
    sources = [(skills / skill / "SKILL.md", f".agents/skills/{skill}/SKILL.md")
               for skill in SINGLE_SKILLS]
    market = skills / "market-research"
    pending = [market]
    while pending:
        directory = pending.pop()
        if not _components_safe(directory):
            raise ValueError("package inventory is unsafe")
        try:
            with os.scandir(directory) as scan:
                entries = sorted(scan, key=lambda entry: entry.name)
        except OSError:
            raise ValueError("package inventory is unavailable") from None
        for entry in entries:
            path = Path(entry.path)
            if entry.name == "__pycache__":
                continue
            if not _components_safe(path):
                raise ValueError("package inventory is unsafe")
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
            elif entry.is_file(follow_symlinks=False) and path.suffix != ".pyc":
                sources.append((path, ".agents/skills/market-research/" + path.relative_to(market).as_posix()))
            elif entry.is_file(follow_symlinks=False):
                continue
            else:
                raise ValueError("package inventory contains unsafe entry")
    result = {}
    folded = set()
    for source, destination in sources:
        _safe_name(destination)
        if destination.casefold() in folded or not _components_safe(source):
            raise ValueError("package inventory is unsafe or colliding")
        folded.add(destination.casefold())
        try:
            before = os.stat(source, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & _REPARSE:
                raise ValueError("package inventory contains unsafe file")
            content = source.read_bytes()
            after = os.stat(source, follow_symlinks=False)
        except OSError:
            raise ValueError("package inventory is unavailable") from None
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("package inventory changed")
        result[destination] = content
    required = {f".agents/skills/{skill}/SKILL.md" for skill in SINGLE_SKILLS}
    required.add(".agents/skills/market-research/SKILL.md")
    if not required.issubset(result):
        raise ValueError("package inventory is incomplete")
    return dict(sorted(result.items()))


def _classify_file(root: Path, relative: str, expected: bytes) -> str:
    _safe_name(relative)
    path = root.joinpath(*relative.split("/"))
    if not _components_safe(path):
        return "unsafe"
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unavailable"
    if not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & _REPARSE:
        return "unsafe"
    if before.st_size != len(expected):
        return "content differs"
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            before_open = os.fstat(descriptor)
            chunks = []
            while True:
                chunk = os.read(descriptor, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            actual = b"".join(chunks)
            after_open = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after = os.stat(path, follow_symlinks=False)
    except OSError:
        return "unavailable"
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if identity(before) != identity(after) or identity(before_open) != identity(after_open) or identity(before) != identity(before_open):
        return "unavailable"
    return "matching" if actual == expected else "content differs"


def _gitignore_state(root: Path):
    path = root / ".gitignore"
    if not _components_safe(path):
        return "unsafe", "gitignore path unsafe"
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return "absent", ""
    except OSError:
        return "unavailable", "gitignore unavailable"
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE:
        return "unsafe", "gitignore unsafe"
    try:
        data = path.read_bytes()
        data.decode("utf-8")
    except (OSError, UnicodeError):
        return "unavailable", "gitignore unavailable or invalid"
    return ("present" if b"# kb-bootstrap generated artifacts" in data else "append"), ""


def _directory_state(root: Path, relative: str):
    path = root / relative
    if not _components_safe(path):
        return "unsafe"
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unavailable"
    if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE:
        return "unsafe"
    return "present"


def _marker_state(root: Path, relative: str):
    path = root / relative
    if not _components_safe(path):
        return "unsafe"
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unavailable"
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE:
        return "unsafe"
    return "present"


def _receipt(lines, result):
    return "\n".join(["=== Scaffold Repeat Guard ==="] + sorted(lines) + ["RESULT: " + result])


def preflight(target: Path, package_root: Path, layout: str, lessons_requested: bool = False):
    """Return (action, report); action is initialize, noop, or blocked."""
    if layout not in ("single", "umbrella"):
        return "blocked", _receipt(["layout unsupported"], "BLOCKED")
    lexical_target = Path(target)
    if not lexical_target.is_absolute():
        lexical_target = Path.cwd() / lexical_target
    if not _components_safe(lexical_target):
        return "blocked", _receipt(["target unsafe or unavailable"], "BLOCKED")
    raw_target = Path(os.path.abspath(os.fspath(lexical_target)))
    try:
        info = os.lstat(raw_target)
        if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE:
            return "blocked", _receipt(["target unsafe or unavailable"], "BLOCKED")
        exists = True
    except FileNotFoundError:
        exists = False
    except OSError:
        return "blocked", _receipt(["target unavailable"], "BLOCKED")
    try:
        expected = qmd_payloads(layout, _slug(raw_target.name))
        expected.update(_inventory_files(package_root))
    except (OSError, ValueError):
        return "blocked", _receipt(["trusted package inventory unavailable"], "BLOCKED")

    fixed = {name: ("missing" if not exists else _classify_file(raw_target, name, data))
             for name, data in expected.items()}
    lesson_state, lesson_errors = inspect_project_lessons(
        raw_target, package_root, require_initialized=False
    )
    if lesson_state == "blocked":
        return "blocked", _receipt(["lesson contract unavailable, unsafe, or invalid"], "BLOCKED")

    gitignore_state, gitignore_error = _gitignore_state(raw_target) if exists else ("absent", "")
    dirs = TARGET_DIRS + (("kb/apps", "kb/systems", "kb/architecture") if layout == "umbrella" else ())
    dir_states = {name: (_directory_state(raw_target, name) if exists else "missing") for name in dirs}
    marker_states = {name: (_marker_state(raw_target, name) if exists else "missing") for name in TARGET_MARKERS}
    problems = [f"{state}: {name}" for name, state in fixed.items() if state not in ("matching", "missing")]
    if gitignore_error:
        problems.append(gitignore_error)
    problems.extend(f"directory {state}: {name}" for name, state in dir_states.items() if state not in ("present", "missing"))
    problems.extend(f"marker {state}: {name}" for name, state in marker_states.items() if state not in ("present", "missing"))
    if problems:
        return "blocked", _receipt(problems, "BLOCKED")

    fixed_all_missing = all(state == "missing" for state in fixed.values())
    fixed_all_match = all(state == "matching" for state in fixed.values())
    if exists and fixed_all_match:
        # All additive state must already be complete; no repair is authorized.
        pending = []
        if lessons_requested and lesson_state == "absent":
            pending.append("project lessons absent; run enable-project-lessons explicitly")
        if gitignore_state != "present":
            pending.append("gitignore generated marker pending")
        pending.extend(f"directory {state}: {name}" for name, state in dir_states.items() if state != "present")
        pending.extend(f"marker {state}: {name}" for name, state in marker_states.items() if state != "present")
        if pending:
            return "blocked", _receipt(pending, "BLOCKED")
        return "noop", _receipt([], "OK (NO-OP)")
    if exists and not fixed_all_missing:
        return "blocked", _receipt(["scaffold partial or conflicting; no files changed"], "BLOCKED")
    action = "initialize"
    if lessons_requested and lesson_state == "absent":
        action = "initialize-lessons"
    elif lessons_requested and lesson_state == "valid":
        action = "initialize-preserve-lessons"
    return action, _receipt([], "OK (FIRST INIT)")
