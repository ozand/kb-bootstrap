"""Bounded read-only validation for explicitly supplied ADR-023/024 records."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

import yaml

from .raw_manifest import DIGEST, MAX_BYTES as MAX_MANIFEST_BYTES, _open_checked, _safe_path, _signature, _signature_from_descriptor
from .canonical_profile import _traverses_symlink

SCHEMA = "kb-bootstrap.source-capture"
MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_YAML_EVENTS = 200_000
MAX_YAML_DEPTH = 64
MAX_SOURCES = 1000
MAX_REPRESENTATIONS = 100
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
LABEL = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
OPAQUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")


class _UniqueLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in mapping:
            raise ValueError("duplicate or non-string mapping key")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _bad(message: str) -> Tuple[bool, Tuple[str, ...]]:
    return False, (message,)


def _events(text: str) -> Optional[str]:
    count = 0
    depth = 0
    try:
        for event in yaml.parse(text, Loader=yaml.SafeLoader):
            count += 1
            if count > MAX_YAML_EVENTS:
                return "metadata exceeds parser event limit"
            if isinstance(event, yaml.events.AliasEvent):
                return "YAML aliases are not supported"
            if isinstance(event, (yaml.events.MappingStartEvent, yaml.events.SequenceStartEvent)):
                depth += 1
                if depth > MAX_YAML_DEPTH:
                    return "metadata exceeds nesting limit"
            elif isinstance(event, (yaml.events.MappingEndEvent, yaml.events.SequenceEndEvent)):
                depth -= 1
    except yaml.YAMLError:
        return "metadata is invalid YAML"
    return None


def _safe_relative(value: object) -> bool:
    if not _safe_path(value) or value.startswith("\\\\") or ":" in value:
        return False
    return all(part not in {".", ".."} and not any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in part)
               for part in value.split("/"))


def _read_regular(root: Path, relative: str, limit: int) -> Tuple[Optional[bytes], str]:
    if not _safe_relative(relative):
        return None, "path is unsafe"
    candidate = root.joinpath(*relative.split("/"))
    try:
        if _traverses_symlink(candidate) or not candidate.is_file() or candidate.is_symlink():
            return None, "path is unavailable or unsafe"
        before = _signature(candidate)
        if before[2] > limit:
            return None, "file exceeds size limit"
        with _open_checked(candidate, before) as stream:
            data = stream.read(limit + 1)
            after = _signature_from_descriptor(stream)
        if len(data) > limit or before != after or before != _signature(candidate):
            return None, "file changed or exceeds size limit"
        return data, ""
    except (OSError, ValueError):
        return None, "file is unavailable or unsafe"


def _origin(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    kind = value.get("kind")
    if kind == "unavailable":
        return (set(value) == {"kind", "reason"} and isinstance(value.get("reason"), str)
                and value["reason"] in {"no-safe-reference-supplied", "source-unavailable", "access-not-provided"})
    reference = value.get("reference")
    if not isinstance(reference, str) or not reference:
        return False
    size = _utf8_size(reference)
    if size is None or size > 2048:
        return False
    if any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in reference):
        return False
    if kind == "opaque-owner-reference":
        return set(value) == {"kind", "reference"} and bool(OPAQUE.fullmatch(reference))
    if kind == "bundle-relative":
        return set(value) == {"kind", "reference"} and _safe_relative(reference) and "?" not in reference and "#" not in reference
    if kind == "public-url":
        from urllib.parse import urlsplit
        try:
            parts = urlsplit(reference)
            host = parts.hostname
            return (set(value) == {"kind", "reference"} and parts.scheme.lower() in {"http", "https"}
                    and bool(host) and not any(char.isspace() for char in host)
                    and parts.username is None and parts.password is None
                    and (parts.port is None or 1 <= parts.port <= 65535)
                    and not parts.query and not parts.fragment)
        except ValueError:
            return False
    return False


def _utf8_size(value: str) -> Optional[int]:
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError:
        return None


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    from datetime import datetime
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _digest_record(value: Any, *, original: bool = False) -> Optional[str]:
    if not isinstance(value, dict):
        return None
    allowed = {"algorithm", "digest", "media_type", "language", "observed_at"} if original else {"algorithm", "digest"}
    if set(value) - allowed or value.get("algorithm") != "sha256":
        return None
    if original and "observed_at" in value and not _timestamp(value["observed_at"]):
        return None
    if original and "media_type" in value and (not isinstance(value["media_type"], str) or not value["media_type"]):
        return None
    digest = value.get("digest")
    return digest if isinstance(digest, str) and DIGEST.fullmatch(digest) else None


def _coordinate(value: Any, data: Optional[bytes]) -> bool:
    if value == "unknown":
        return True
    if not isinstance(value, dict) or set(value) - {"unit", "range"} or not {"unit", "range"} <= set(value):
        return False
    unit, bounds = value["unit"], value["range"]
    if not isinstance(unit, str) or unit not in {"byte", "unicode-code-point", "line"} or not isinstance(bounds, list) or len(bounds) != 2:
        return False
    start, end = bounds
    if type(start) is not int or type(end) is not int or start > end:
        return False
    minimum = 1 if unit == "line" else 0
    if start < minimum:
        return False
    if data is not None:
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            return False
        line_count = 0 if not text else len(text.split("\n")) - (1 if text.endswith("\n") else 0)
        maximum = len(data) if unit == "byte" else len(text) if unit == "unicode-code-point" else line_count + 1
        if end > maximum:
            return False
    return True


def validate_source_capture(metadata_path: str | Path, project_root: str | Path,
                            corpus_root: str | Path, selected_paths: Iterable[str],
                            manifest_path: str | Path | None = None) -> Tuple[bool, Tuple[str, ...]]:
    """Validate supplied metadata and exactly the caller-selected raw members.

    Metadata and optional manifest paths are project-relative. ``corpus_root``
    is a project-relative ADR-010 corpus directory; each selected/raw member path
    is relative to that corpus. No tree discovery or origin dereference occurs.
    """
    if not isinstance(metadata_path, (str, Path)) or not isinstance(project_root, (str, Path)) or not isinstance(corpus_root, (str, Path)):
        return _bad("metadata, project, and corpus paths are invalid")
    raw_root = Path(project_root).absolute()
    if _traverses_symlink(raw_root) or not raw_root.is_dir():
        return _bad("project root is unavailable or unsafe")
    root = raw_root.resolve()
    try:
        corpus_path = Path(corpus_root)
        if corpus_path.is_absolute() or ".." in corpus_path.parts or not _safe_relative(corpus_path.as_posix()):
            return _bad("corpus root must be relative and contained")
        corpus = root.joinpath(*corpus_path.parts)
        if _traverses_symlink(corpus) or not corpus.is_dir():
            return _bad("corpus root is unavailable or unsafe")
        corpus_identity = _signature(corpus)
        metadata_path = Path(metadata_path)
        if metadata_path.is_absolute() or ".." in metadata_path.parts:
            return _bad("metadata path must be relative and contained")
        metadata_name = metadata_path.as_posix()
        metadata, error = _read_regular(root, metadata_name, MAX_METADATA_BYTES)
        if error:
            return _bad("metadata " + error)
        assert metadata is not None
        text = metadata.decode("utf-8")
    except (UnicodeError, ValueError, OSError):
        return _bad("metadata is not valid UTF-8")
    event_error = _events(text)
    if event_error:
        return _bad(event_error)
    try:
        record = yaml.load(text, Loader=_UniqueLoader)
    except (yaml.YAMLError, ValueError):
        return _bad("metadata is invalid or has duplicate keys")
    if not isinstance(record, dict) or set(record) != {"schema", "version", "sources"} or record.get("schema") != SCHEMA or type(record.get("version")) is not int or record["version"] != 1:
        return _bad("metadata schema or version is unsupported")
    sources = record["sources"]
    if not isinstance(sources, list) or len(sources) > MAX_SOURCES:
        return _bad("source count is invalid or exceeds limit")
    try:
        requested = []
        for path in selected_paths:
            if len(requested) >= MAX_SOURCES * MAX_REPRESENTATIONS:
                return _bad("selected path count exceeds limit")
            if not isinstance(path, str) or not _safe_relative(path):
                return _bad("selected path is unsafe")
            requested.append(path)
    except (TypeError, ValueError):
        return _bad("selected paths are invalid")
    if len(requested) > MAX_SOURCES * MAX_REPRESENTATIONS:
        return _bad("selected path count exceeds limit")
    if len({path.casefold() for path in requested}) != len(requested):
        return _bad("selected paths collide")
    selected: Dict[str, bytes] = {}
    total_bytes = 0
    for path in requested:
        data, error = _read_regular(corpus, path, MAX_FILE_BYTES)
        if error:
            return _bad("selected file " + error)
        assert data is not None
        total_bytes += len(data)
        if total_bytes > MAX_TOTAL_BYTES:
            return _bad("selected files exceed aggregate size limit")
        try:
            data.decode("utf-8")
        except UnicodeError:
            return _bad("selected file is not UTF-8 text")
        selected[path] = data
    if manifest_path is not None:
        if not isinstance(manifest_path, (str, Path)):
            return _bad("manifest path is invalid")
        manifest_path = Path(manifest_path)
        if manifest_path.is_absolute() or ".." in manifest_path.parts:
            return _bad("manifest path must be relative and contained")
        raw_manifest, error = _read_regular(root, manifest_path.as_posix(), MAX_MANIFEST_BYTES)
        if error:
            return _bad("manifest " + error)
        try:
            manifest = json.loads(raw_manifest.decode("utf-8"), object_pairs_hook=_json_pairs)
        except (UnicodeError, ValueError, json.JSONDecodeError, RecursionError):
            return _bad("manifest is invalid")
        if not _manifest_matches(manifest, selected, corpus_path.as_posix()):
            return _bad("manifest does not match selected paths and digests")

    if metadata_name in {corpus_path.as_posix() + "/" + path for path in requested}:
        return _bad("metadata path cannot also be a raw representation")
    if manifest_path is not None and Path(manifest_path).as_posix() in {
        corpus_path.as_posix() + "/" + path for path in requested
    }:
        return _bad("manifest path cannot be a raw representation")
    source_ids: Set[str] = set()
    all_referenced: Set[str] = set()
    checked_retained: Set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            return _bad("source record is invalid")
        sid = source.get("source_id")
        if not isinstance(sid, str) or not TOKEN.fullmatch(sid) or sid in source_ids:
            return _bad("source identifier is invalid or duplicated")
        source_ids.add(sid)
        if not _origin(source.get("origin")):
            return _bad("origin descriptor is invalid")
        allowed_source = {"source_id", "origin", "original_revision", "original_retention", "capture", "fidelity", "representations", "permissions"}
        if set(source) - allowed_source or not {"source_id", "origin", "original_revision", "original_retention", "capture", "fidelity", "representations"} <= set(source):
            return _bad("source fields are unsupported or required fields are missing")
        if "permissions" in source:
            permissions = source["permissions"]
            if (not isinstance(permissions, dict) or set(permissions) != {"access", "retention", "redistribution"}
                    or any(not isinstance(item, str) or not item
                           or _utf8_size(item) is None or _utf8_size(item) > 128
                           or any(ord(char) < 32 or ord(char) == 127 for char in item)
                           for item in permissions.values())):
                return _bad("permission labels are invalid")
        original = source.get("original_revision")
        original_digest = _digest_record(original, original=True)
        if (not isinstance(original, dict)
                or set(original) - {"algorithm", "digest", "media_type", "language", "observed_at", "opaque"}
                or (original_digest is None and (not isinstance(original.get("opaque"), str) or not original["opaque"]))
                or ("opaque" in original and set(original) - {"opaque", "media_type", "language", "observed_at"})):
            return _bad("original revision is invalid")
        if "observed_at" in original and not _timestamp(original["observed_at"]):
            return _bad("original observation time is invalid")
        if "opaque" in original and not (original["opaque"] == "unknown" or (isinstance(original["opaque"], str) and OPAQUE.fullmatch(original["opaque"]))):
            return _bad("opaque original revision is invalid")
        if "media_type" in original and (not isinstance(original["media_type"], str) or not original["media_type"]):
            return _bad("original media type is invalid")
        retention = source.get("original_retention")
        if not isinstance(retention, str) or retention not in {"retained", "reference-only", "unknown"}:
            return _bad("original retention is invalid")
        if retention == "retained" and original_digest is None:
            return _bad("retained original requires a known original digest")
        capture, fidelity, reps = source.get("capture"), source.get("fidelity"), source.get("representations")
        if not isinstance(capture, dict) or not isinstance(fidelity, dict) or not isinstance(reps, list):
            return _bad("capture, fidelity, and representations are required")
        method, cls = capture.get("method"), fidelity.get("class")
        if (set(capture) - {"method", "captured_at", "converter", "reason"}
                or set(fidelity) != {"class", "coverage", "losses"}
                or not isinstance(method, str) or method not in {"direct", "converted", "manual-summary", "blocked"}
                or not isinstance(cls, str) or cls not in {"exact", "partial", "manual-summary", "blocked", "unknown"}):
            return _bad("capture method or fidelity class is invalid")
        if "captured_at" in capture and not _timestamp(capture["captured_at"]):
            return _bad("capture time is invalid")
        if len(reps) > MAX_REPRESENTATIONS:
            return _bad("representation count exceeds limit")
        if cls == "blocked":
            reason = capture.get("reason")
            if (method != "blocked" or reps or not isinstance(reason, str)
                    or reason not in {"origin-unavailable", "access-not-provided", "conversion-failed", "unsupported-input"}
                    or set(capture) - {"method", "reason"}):
                return _bad("blocked capture is inconsistent")
        elif method == "blocked" or not reps:
            return _bad("non-blocked capture requires representations")
        coverage, losses = fidelity.get("coverage"), fidelity.get("losses")
        if not isinstance(coverage, str) or not (coverage == "unknown" or LABEL.fullmatch(coverage)) or not isinstance(losses, list) or len(losses) > 64 or any(not isinstance(loss, str) or not LABEL.fullmatch(loss) for loss in losses) or len(set(losses)) != len(losses):
            return _bad("fidelity coverage or losses are invalid")
        if cls == "exact" and (original_digest is None or coverage != "all-bytes" or losses):
            return _bad("exact fidelity requires known original bytes, all-bytes coverage, and no losses")
        if cls in {"partial", "manual-summary"} and not losses:
            return _bad("partial fidelity requires declared losses")
        if cls == "unknown" and coverage != "unknown":
            return _bad("unknown fidelity requires unknown coverage")
        if cls == "blocked" and ((source.get("origin") or {}).get("kind") != "unavailable") and capture.get("reason") == "origin-unavailable":
            return _bad("origin-unavailable reason requires an unavailable origin")
        if cls == "manual-summary" and method != "manual-summary":
            return _bad("manual-summary fidelity requires manual-summary method")
        if method in {"direct", "manual-summary", "blocked"} and "converter" in capture:
            return _bad("converter metadata is only valid for converted captures")
        if method == "manual-summary" and cls != "manual-summary":
            return _bad("manual-summary method requires manual-summary fidelity")
        if method == "blocked" and (set(capture) - {"method", "reason"} or cls != "blocked"):
            return _bad("blocked capture has unsupported or inconsistent metadata")
        if method != "blocked" and "reason" in capture:
            return _bad("capture reason is only valid for blocked records")
        if method != "converted" and method not in {"direct", "manual-summary", "blocked"}:
            return _bad("capture method is unsupported")
        if method == "converted":
            converter = capture.get("converter")
            if (not isinstance(converter, dict) or set(converter) - {"identity", "version", "parameters"}
                    or not isinstance(converter.get("identity"), str) or not TOKEN.fullmatch(converter["identity"])
                    or not isinstance(converter.get("version"), str) or not TOKEN.fullmatch(converter["version"])):
                return _bad("converted capture requires converter identity and version")
        rep_ids: Set[str] = set()
        rep_digests: list[str] = []
        rep_paths: Set[str] = set()
        for rep in reps:
            if not isinstance(rep, dict):
                return _bad("representation is invalid")
            rid = rep.get("representation_id")
            digest = _digest_record(rep.get("revision"))
            path = rep.get("raw_path")
            if not isinstance(rid, str) or not TOKEN.fullmatch(rid) or rid in rep_ids or digest is None or not isinstance(path, str) or not _safe_relative(path):
                return _bad("representation identifier, revision, or path is invalid")
            if set(rep) - {"representation_id", "revision", "media_type", "language", "raw_path", "retention", "coordinates"} or not {"representation_id", "revision", "media_type", "raw_path", "retention"} <= set(rep):
                return _bad("representation fields are unsupported or required fields are missing")
            if (not isinstance(rep.get("media_type"), str) or rep.get("media_type") not in {"text/plain", "text/markdown"}
                    or not isinstance(rep.get("retention"), str) or rep.get("retention") not in {"retained", "reference-only", "unknown"}):
                return _bad("representation media type or retention is unsupported")
            if path in rep_paths:
                return _bad("representation path is duplicated")
            rep_ids.add(rid)
            rep_digests.append(digest)
            if path.casefold() in {existing.casefold() for existing in all_referenced | rep_paths}:
                return _bad("representation paths collide")
            rep_paths.add(path)
            all_referenced.add(path)
            if path in selected:
                data = selected[path]
                if rep.get("retention") == "retained":
                    checked_retained.add(path)
                if hashlib.sha256(data).hexdigest() != digest:
                    return _bad("representation digest does not match selected bytes")
                coords_value = rep.get("coordinates", {})
                if not isinstance(coords_value, dict) or set(coords_value) - {"local", "original"}:
                    return _bad("coordinates are invalid")
                if "local" in coords_value and not _coordinate(coords_value["local"], data):
                    return _bad("local coordinate is invalid")
            elif rep.get("retention") == "retained":
                return _bad("retained representation is unavailable")
            if "coordinates" in rep:
                coords = rep["coordinates"]
                if not isinstance(coords, dict) or set(coords) - {"local", "original"}:
                    return _bad("coordinates are invalid")
                if "local" in coords and not _coordinate(coords["local"], selected.get(path)):
                    return _bad("local coordinate is invalid")
                if "original" in coords and not _coordinate(coords["original"], None):
                    return _bad("original coordinate is invalid")
        if cls == "exact" and any(
            digest != original_digest
            for rep, digest in zip(reps, rep_digests)
            if rep.get("retention") == "retained"
        ):
            return _bad("every exact representation must match original digest")
        if retention == "retained" and not any(
            rep_digest == original_digest and rep.get("retention") == "retained"
            for rep, rep_digest in zip(reps, rep_digests)
        ):
            return _bad("retained original requires a matching retained representation")
    expected_retained = {
        rep["raw_path"]
        for source in sources
        for rep in source.get("representations", [])
        if isinstance(rep, dict) and rep.get("retention") == "retained"
    }
    if expected_retained != set(requested):
        return _bad("selected paths must exactly match retained representations")
    try:
        if _traverses_symlink(corpus) or _signature(corpus) != corpus_identity:
            return _bad("corpus root changed during validation")
    except OSError:
        return _bad("corpus root is unavailable")
    return True, ()


def _json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _manifest_matches(manifest: Any, selected: Dict[str, bytes], corpus: str) -> bool:
    if not isinstance(manifest, dict) or set(manifest) != {"schema", "version", "corpus", "algorithm", "files"}:
        return False
    if type(manifest.get("version")) is not int or manifest.get("version") != 1:
        return False
    if not isinstance(manifest.get("corpus"), str) or not isinstance(manifest.get("schema"), str) or not isinstance(manifest.get("algorithm"), str):
        return False
    try:
        encoded_size = len(json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError, UnicodeEncodeError):
        return False
    if encoded_size > MAX_MANIFEST_BYTES:
        return False
    if manifest.get("schema") != "kb-bootstrap.raw-manifest" or manifest["version"] != 1 or manifest.get("algorithm") != "sha256" or manifest.get("corpus") != corpus:
        return False
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) > 2_000_000:
        return False
    actual = {}
    folded = set()
    for item in files:
        if (not isinstance(item, dict) or set(item) != {"path", "sha256"}
                or not _safe_relative(item.get("path")) or not isinstance(item.get("sha256"), str)
                or not DIGEST.fullmatch(item["sha256"])):
            return False
        path = item["path"]
        if path in actual or path.casefold() in folded:
            return False
        actual[path] = item["sha256"]
        folded.add(path.casefold())
    return all(actual.get(path) == hashlib.sha256(data).hexdigest() for path, data in selected.items())
