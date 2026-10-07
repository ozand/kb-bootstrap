"""Canonical generated QMD project/collection naming (ADR-020)."""

import hashlib
import re


_SIMPLE_NAME = re.compile(r"^[a-z0-9_-]+$")
_PREFIX_RUNS = re.compile(r"[^a-z0-9_-]+")
_GENERATED_COLLECTION = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
GENERATED_COLLECTION_MAX_LENGTH = 64
GENERATED_PROJECT_MAX_LENGTH = GENERATED_COLLECTION_MAX_LENGTH - len("-wiki")


def project_slug(basename):
    """Return the deterministic portable base used for generated QMD names."""
    if not isinstance(basename, str):
        raise TypeError("project basename must be text")
    if (
        len(basename) <= GENERATED_PROJECT_MAX_LENGTH
        and _SIMPLE_NAME.fullmatch(basename)
        and basename.strip("-._") == basename
    ):
        return basename

    lower = basename.lower()
    readable = _PREFIX_RUNS.sub("-", lower).strip("-._")[:46].strip("-._")
    prefix = readable or "p"
    digest = hashlib.sha256(basename.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def is_valid_generated_collection_name(name):
    """Check the bounded ASCII grammar used only for generated collections."""
    return (
        isinstance(name, str)
        and len(name) <= GENERATED_COLLECTION_MAX_LENGTH
        and _GENERATED_COLLECTION.fullmatch(name) is not None
    )
