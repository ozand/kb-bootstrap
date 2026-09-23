"""Offline ADR-011 checkpoint-byte digest for an explicitly selected file set."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Iterable, Tuple, Union

from .canonical_profile import _traverses_symlink
from .raw_manifest import _open_checked, _safe_path, _signature, _signature_from_descriptor

_HEX = re.compile(r"[0-9a-f]{64}\Z")
_MAX_FILES = 256


def _blocked(message: str) -> Tuple[str, bool]:
    return "=== GLiNER Checkpoint ===\nERROR: " + message + "\nRESULT: BLOCKED", False


def verify_checkpoint(
    directory: Union[str, Path], files: Iterable[str], expected_digest: str
) -> Tuple[str, bool]:
    """Hash exact approved regular files without model parsing or network access."""
    try:
        names = list(files)
        if (not names or len(names) > _MAX_FILES or len(names) != len(set(names))
                or len({name.casefold() for name in names if isinstance(name, str)}) != len(names)
                or any(not _safe_path(name) for name in names)):
            return _blocked("approved file list is invalid")
        if not isinstance(expected_digest, str) or not _HEX.fullmatch(expected_digest):
            return _blocked("expected model digest must be lowercase SHA-256")
        root = Path(directory).absolute()
        if _traverses_symlink(root) or not root.is_dir():
            return _blocked("checkpoint directory is unavailable or unsafe")
        root_before = _signature(root)
        wanted = set(names)
        allowed_folders = {"/".join(name.split("/")[:depth]) for name in names
                           for depth in range(1, len(name.split("/")))}
        actual = set()
        seen = set()
        folder_signatures = {}
        for current, directories, filenames in os.walk(root, followlinks=False):
            folder = Path(current)
            if _traverses_symlink(folder) or not folder.is_dir():
                return _blocked("checkpoint directory changed or is unsafe")
            folder_signatures[folder] = _signature(folder)
            for name in directories + filenames:
                entry = folder / name
                relative = entry.relative_to(root).as_posix()
                if (not _safe_path(relative) or relative.casefold() in seen
                        or _traverses_symlink(entry)):
                    return _blocked("checkpoint entry is unsafe")
                seen.add(relative.casefold())
                if name in directories and relative not in allowed_folders:
                    return _blocked("checkpoint has missing, extra or non-regular files")
                if name in filenames:
                    if not entry.is_file() or relative not in wanted:
                        return _blocked("checkpoint has missing, extra or non-regular files")
                    actual.add(relative)
        if actual != wanted:
            return _blocked("checkpoint has missing, extra or non-regular files")
        digest = hashlib.sha256()
        for name in sorted(names):
            path = root.joinpath(*name.split("/"))
            before = _signature(path)
            if not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
                return _blocked("checkpoint entry is not a regular file")
            encoded = name.encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
            digest.update(before[2].to_bytes(8, "big"))
            with _open_checked(path, before) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                if _signature_from_descriptor(stream) != before or _signature(path) != before:
                    return _blocked("checkpoint changed during verification")
        if _signature(root) != root_before or any(
            _traverses_symlink(folder) or _signature(folder) != before
            for folder, before in folder_signatures.items()
        ):
            return _blocked("checkpoint changed during verification")
        observed = digest.hexdigest()
        if observed != expected_digest:
            return _blocked("model digest does not match expected bytes")
        return (
            "=== GLiNER Checkpoint ===\n"
            + f"files: {len(names)}\nmodel sha256: {observed}\n"
            + "selected directory bytes match supplied digest; acquisition plan and owner consent: not verified\n"
            + "publisher authenticity: not verified; model loading: not tested; network isolation: not tested\n"
            + "RESULT: OK (local byte comparison only)",
            True,
        )
    except (OSError, UnicodeError, OverflowError, ValueError):
        return _blocked("checkpoint is unavailable, changed or unsafe")
