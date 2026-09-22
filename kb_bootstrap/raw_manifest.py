"""Deterministic raw-source revision snapshots and exclusive publication."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .canonical_profile import _traverses_symlink
from .canonical_graph_export import _identity, _inside, _relative_input

SCHEMA = "kb-bootstrap.raw-manifest"
MAX_BYTES = 64 * 1024 * 1024
DIGEST = re.compile(r"^[0-9a-f]{64}$")
DEVICE = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.I)
INVALID = set(chr(92) + ':<>"|?*')
CATEGORIES = ("new", "changed", "unchanged", "removed")


def _safe_path(value: object) -> bool:
    if not isinstance(value, str) or not value or value.startswith("/"):
        return False
    for part in value.split("/"):
        if (not part or part in {".", ".."} or part.endswith((" ", "."))
                or DEVICE.match(part) or any(c in INVALID or ord(c) < 32 or ord(c) == 127
                                          or 0xD800 <= ord(c) <= 0xDFFF for c in part)):
            return False
    return True


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _signature(path: Path):
    details = path.stat(follow_symlinks=False)
    return details.st_dev, details.st_ino, details.st_size, details.st_mtime_ns


def _signature_from_descriptor(source):
    details = os.fstat(source.fileno())
    return details.st_dev, details.st_ino, details.st_size, details.st_mtime_ns


def _open_checked(path: Path, before):
    """Check the opened regular file before reading, not only its pathname."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        details = os.fstat(descriptor)
        observed = details.st_dev, details.st_ino, details.st_size, details.st_mtime_ns
        if not stat.S_ISREG(details.st_mode) or observed != before:
            raise OSError("source changed before read")
        return os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise


def _validate_manifest(value: object, corpus: str) -> Dict[str, str]:
    if not isinstance(value, dict) or list(value) != ["schema", "version", "corpus", "algorithm", "files"]:
        raise ValueError("previous manifest schema is invalid")
    if value["schema"] != SCHEMA or type(value["version"]) is not int or value["version"] != 1 or value["corpus"] != corpus or value["algorithm"] != "sha256":
        raise ValueError("previous manifest is incompatible")
    files = value["files"]
    if not isinstance(files, list):
        raise ValueError("previous manifest files are invalid")
    result: Dict[str, str] = {}
    folded = set()
    for item in files:
        if not isinstance(item, dict) or list(item) != ["path", "sha256"] or not _safe_path(item["path"]) or not isinstance(item["sha256"], str) or not DIGEST.fullmatch(item["sha256"]):
            raise ValueError("previous manifest entry is invalid")
        name = item["path"]
        if name in result or name.casefold() in folded:
            raise ValueError("previous manifest paths collide")
        result[name] = item["sha256"]
        folded.add(name.casefold())
    if list(result) != sorted(result):
        raise ValueError("previous manifest paths are unsorted")
    return result


def _scan(root: Path) -> Dict[str, str]:
    files: Dict[str, str] = {}
    folded = set()
    def failed(category: str):
        raise ValueError(category)
    def walk(directory: Path):
        try:
            before_directory = _signature(directory)
            if os.name == "posix":
                flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
                descriptor = os.open(directory, flags)
                try:
                    details = os.fstat(descriptor)
                    observed = (details.st_dev, details.st_ino, details.st_size, details.st_mtime_ns)
                    if not stat.S_ISDIR(details.st_mode) or observed != before_directory:
                        failed("corpus directory changed while scanning")
                    entries = [directory / name for name in os.listdir(descriptor)]
                finally:
                    os.close(descriptor)
            else:
                # Windows does not expose fd-based directory enumeration here.
                entries = list(directory.iterdir())
            if _signature(directory) != before_directory or _traverses_symlink(directory):
                failed("corpus directory changed while scanning")
            entries.sort(key=lambda path: path.name)
        except OSError:
            failed("corpus entry is unavailable")
        for path in entries:
            relative = path.relative_to(root).as_posix()
            if not _safe_path(relative) or relative.casefold() in folded:
                failed("corpus path is unsafe or colliding")
            folded.add(relative.casefold())
            if path.is_symlink() or _traverses_symlink(path):
                failed("corpus entry traverses a symlink")
            try:
                before = _signature(path)
                if path.is_dir():
                    walk(path)
                elif path.is_file():
                    digest = hashlib.sha256()
                    with _open_checked(path, before) as source:
                        for chunk in iter(lambda: source.read(1024 * 1024), b""):
                            digest.update(chunk)
                        if _signature(path) != before or _signature_from_descriptor(source) != before:
                            failed("corpus entry changed while being read")
                    files[relative] = digest.hexdigest()
                else:
                    failed("corpus entry is not a regular file or directory")
                if before != _signature(path):
                    failed("corpus entry changed while being read")
            except OSError:
                failed("corpus entry is unavailable or changed")
    walk(root)
    return dict(sorted(files.items()))


def _read_previous(path: Path, corpus: str) -> Dict[str, str]:
    if path.is_symlink() or _traverses_symlink(path) or not path.is_file():
        raise ValueError("previous manifest is unavailable or unsafe")
    try:
        before = _signature(path)
        if before[2] > MAX_BYTES:
            raise ValueError("previous manifest exceeds size limit")
        with _open_checked(path, before) as source:
            data = source.read(MAX_BYTES + 1)
            observed = _signature_from_descriptor(source)
        if len(data) > MAX_BYTES or before != observed or before != _signature(path):
            raise ValueError("previous manifest exceeds limit or changed")
        parsed = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
        return _validate_manifest(parsed, corpus)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("previous manifest is unreadable or invalid") from None


def _blocked(category: str) -> Tuple[str, bool]:
    lines = ["=== Raw Manifest ==="]
    lines.extend(f"{kind}: 0" for kind in CATEGORIES)
    lines.extend([f"ERROR: {category}", "RESULT: BLOCKED"])
    return "\n".join(lines), False


def _report(current: Dict[str, str], previous: Dict[str, str]) -> str:
    changes: Dict[str, List[str]] = {key: [] for key in CATEGORIES}
    for path, digest in current.items():
        kind = "new" if path not in previous else ("unchanged" if digest == previous[path] else "changed")
        changes[kind].append(path)
    changes["removed"] = sorted(set(previous) - set(current))
    lines = ["=== Raw Manifest ==="]
    lines.extend(f"{kind}: {len(changes[kind])}" for kind in CATEGORIES)
    for kind in CATEGORIES:
        lines.extend(f"{kind}: {path}" for path in sorted(changes[kind]))
    lines.append("RESULT: OK")
    return "\n".join(lines)


def write_raw_manifest(project_root: Union[str, Path], corpus_dir: Union[str, Path], output: Union[str, Path], previous: Optional[Union[str, Path]] = None) -> Tuple[str, bool]:
    """Scan a contained corpus and publish one new versioned manifest."""
    raw_project = Path(project_root).absolute()
    if _traverses_symlink(raw_project) or not raw_project.is_dir():
        return _blocked("project root is unavailable or unsafe")
    project = raw_project.resolve()
    if not _safe_path(str(corpus_dir).replace(os.sep, "/")) or not _safe_path(str(output).replace(os.sep, "/")):
        return _blocked("input path is invalid")
    corpus, corpus_error = _relative_input(corpus_dir, project, "corpus")
    destination, output_error = _relative_input(output, project, "output")
    if corpus_error or output_error:
        return _blocked(corpus_error or output_error)
    assert corpus is not None and destination is not None
    if not corpus.is_dir() or _traverses_symlink(corpus):
        return _blocked("corpus is unavailable or unsafe")
    if _inside(destination, corpus):
        return _blocked("output must be outside corpus")
    if not destination.parent.is_dir() or _traverses_symlink(destination.parent):
        return _blocked("output parent is unavailable or unsafe")
    if destination.exists() or destination.is_symlink():
        return _blocked("output already exists")
    corpus_name = corpus.relative_to(project).as_posix()
    if previous is not None:
        if not _safe_path(str(previous).replace(os.sep, "/")):
            return _blocked("previous path is invalid")
        prior_path, error = _relative_input(previous, project, "previous")
        if error:
            return _blocked(error)
        assert prior_path is not None
        if _inside(prior_path, corpus) or prior_path == destination:
            return _blocked("previous must be outside corpus and output")
    else:
        prior_path = None
    try:
        prior = _read_previous(prior_path, corpus_name) if prior_path is not None else {}
        current = _scan(corpus)
        manifest = {"schema": SCHEMA, "version": 1, "corpus": corpus_name, "algorithm": "sha256", "files": [{"path": path, "sha256": digest} for path, digest in current.items()]}
        data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(data) > MAX_BYTES:
            raise ValueError("generated manifest exceeds size limit")
    except ValueError as error:
        return _blocked(str(error))
    except (OSError, UnicodeError):
        return _blocked("corpus or manifest is unavailable or unsafe")
    report = _report(current, prior)
    corpus_identity = _identity(corpus)
    parent_identity = _identity(destination.parent)
    staged: Optional[Path] = None
    published = False
    try:
        if (_traverses_symlink(corpus) or _identity(corpus) != corpus_identity
                or _traverses_symlink(destination.parent) or _identity(destination.parent) != parent_identity):
            raise OSError("input changed")
        descriptor, name = tempfile.mkstemp(prefix=".kb-bootstrap-raw-", suffix=".tmp", dir=str(destination.parent))
        staged = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if (_traverses_symlink(corpus) or _identity(corpus) != corpus_identity
                or _traverses_symlink(destination.parent) or _identity(destination.parent) != parent_identity
                or destination.exists() or destination.is_symlink()):
            raise OSError("input changed")
        os.link(staged, destination)
        published = True
    except OSError:
        return report.replace(
            "RESULT: OK",
            "ERROR: raw manifest cannot be published exclusively\nRESULT: BLOCKED",
        ), False
    finally:
        if staged is not None:
            try:
                staged.unlink()
            except OSError:
                if published:
                    report = report.replace(
                        "=== Raw Manifest ===\n",
                        "=== Raw Manifest ===\nWARNING: output published; temporary cleanup is incomplete\n",
                        1,
                    )
    return report + "\noutput: created", True
