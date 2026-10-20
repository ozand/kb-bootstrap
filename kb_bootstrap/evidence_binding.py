"""Caller-directed, read-only evidence binding resolution (ADR-031/035/036)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

from .source_capture_validation import (
    MAX_FILE_BYTES,
    MAX_METADATA_BYTES,
    TOKEN,
    _safe_relative,
    _validate_source_capture,
)
from .raw_manifest import _open_checked, _signature, _signature_from_descriptor
from .canonical_profile import _traverses_symlink
from .local_retrieval import relative_markdown
from .canonical_provenance import _safe_actor

SCHEMA = "kb-bootstrap.evidence-bindings"
MAX_BINDING_BYTES = MAX_METADATA_BYTES
MAX_BINDINGS = 1000
MAX_REFERENCES = 100
MAX_REPORT_ITEMS = 1000
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_SELECTED_TOTAL = 256 * 1024 * 1024
DIGEST = re.compile(r"^[0-9a-f]{64}$")


class PermissionError(Exception):
    """Trusted caller/policy precondition refused processing outside the report wire."""


def _permission(check: Optional[Callable[[], bool]], message: str) -> None:
    """Fail outside the ADR-036 report wire when trusted host policy denies an operation."""
    if not callable(check):
        raise PermissionError(message)
    try:
        allowed = check()
    except Exception:
        raise PermissionError(message) from None
    if allowed is not True:
        raise PermissionError(message)


def _traverses_reparse_point(path: Path) -> bool:
    """Reject symlink/junction/reparse components before resolving or opening a path."""
    try:
        absolute = path.absolute()
        current = Path(absolute.anchor)
        for part in absolute.parts[1:]:
            current /= part
            details = current.lstat()
            attributes = getattr(details, "st_file_attributes", 0)
            reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            if current.is_symlink() or attributes & reparse_flag:
                return True
        return False
    except (OSError, ValueError):
        return True


def _safe_root(value: str | Path) -> Optional[Path]:
    if not isinstance(value, (str, Path)):
        return None
    try:
        raw = Path(value)
        if not raw.is_absolute() or _traverses_reparse_point(raw) or _traverses_symlink(raw) or not raw.is_dir():
            return None
        return raw.resolve()
    except (OSError, TypeError, ValueError):
        return None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _blocked(reason: str) -> dict:
    return {"status": "BLOCKED", "reason": reason}


def _keys(value: Any, required: set[str], optional: set[str] = set()) -> bool:
    return isinstance(value, dict) and required <= set(value) and not (set(value) - required - optional)


def _string(value: Any, maximum: int, *, nonempty: bool = True) -> bool:
    if not isinstance(value, str) or (nonempty and not value):
        return False
    try:
        if len(value) > maximum:
            return False
        return not any(ord(ch) < 32 or ord(ch) == 127 or 0xD800 <= ord(ch) <= 0xDFFF for ch in value)
    except (UnicodeError, TypeError):
        return False


def _validate_binding(value: Any) -> Optional[str]:
    if not _keys(value, {"schema", "version", "knowledge", "bindings"}):
        return "invalid_binding"
    if value["schema"] != SCHEMA or type(value["version"]) is not int or value["version"] != 1:
        return "invalid_binding"
    knowledge = value["knowledge"]
    if not _keys(knowledge, {"path", "sha256"}) or not _safe_relative(knowledge["path"]):
        return "invalid_binding"
    path = PurePosixPath(knowledge["path"])
    if path.as_posix() != knowledge["path"] or path.suffix.casefold() != ".md":
        return "invalid_binding"
    if not isinstance(knowledge["sha256"], str) or not DIGEST.fullmatch(knowledge["sha256"]):
        return "invalid_binding"
    bindings = value["bindings"]
    if not isinstance(bindings, list) or len(bindings) > MAX_BINDINGS:
        return "invalid_binding"
    binding_ids = set()
    for binding in bindings:
        optional = {"applicability", "scope", "context", "retention_class", "owner_policy_ref", "review_actor"}
        if not _keys(binding, {"binding_id", "evidence"}, optional):
            return "invalid_binding"
        bid = binding["binding_id"]
        if not isinstance(bid, str) or not TOKEN.fullmatch(bid) or bid in binding_ids:
            return "invalid_binding"
        binding_ids.add(bid)
        for name in ("applicability", "scope", "context"):
            if name in binding and not _string(binding[name], 2048):
                return "invalid_binding"
        for name in ("retention_class", "owner_policy_ref", "review_actor"):
            if name in binding and not _string(binding[name], 256):
                return "invalid_binding"
        if "review_actor" in binding and not _safe_actor(binding["review_actor"]):
            return "invalid_binding"
        refs = binding["evidence"]
        if not isinstance(refs, list) or not 1 <= len(refs) <= MAX_REFERENCES:
            return "invalid_binding"
        seen_pairs = set()
        for ref in refs:
            if not _keys(ref, {"source_id", "representation_id", "observed_sha256"}, {"current", "fragment"}):
                return "invalid_binding"
            sid, rid, observed = ref["source_id"], ref["representation_id"], ref["observed_sha256"]
            if not isinstance(sid, str) or not TOKEN.fullmatch(sid) or not isinstance(rid, str) or not TOKEN.fullmatch(rid):
                return "invalid_binding"
            if not isinstance(observed, str) or not DIGEST.fullmatch(observed) or (sid, rid) in seen_pairs:
                return "invalid_binding"
            seen_pairs.add((sid, rid))
            if "current" in ref:
                current = ref["current"]
                if not _keys(current, {"source_id", "representation_id"}):
                    return "invalid_binding"
                if not isinstance(current["source_id"], str) or not TOKEN.fullmatch(current["source_id"]):
                    return "invalid_binding"
                if not isinstance(current["representation_id"], str) or not TOKEN.fullmatch(current["representation_id"]):
                    return "invalid_binding"
            if "fragment" in ref:
                fragment = ref["fragment"]
                if not _keys(fragment, {"representation_id", "start_line", "end_line"}):
                    return "invalid_binding"
                if fragment["representation_id"] != rid:
                    return "invalid_binding"
                start, end = fragment["start_line"], fragment["end_line"]
                if type(start) is not int or type(end) is not int or start < 1 or end < start:
                    return "invalid_binding"
    return None


def _read_selected(root: Path, relative: str, limit: int) -> Tuple[Optional[bytes], str]:
    if not _safe_relative(relative):
        return None, "unsafe_or_inaccessible_path"
    candidate = root.joinpath(*relative.split("/"))
    try:
        if (_traverses_reparse_point(candidate) or _traverses_symlink(candidate)
                or not candidate.is_file() or candidate.is_symlink()):
            return None, "unsafe_or_inaccessible_path"
        before = _signature(candidate)
        if before[2] > limit:
            return None, "resource_limit_exceeded"
        with _open_checked(candidate, before) as stream:
            data = stream.read(limit + 1)
            after = _signature_from_descriptor(stream)
        if len(data) > limit or before != after or before != _signature(candidate):
            return None, "unsafe_or_inaccessible_path"
        return data, ""
    except (OSError, ValueError):
        return None, "unsafe_or_inaccessible_path"


def _envelope(project_root, metadata_path, corpus_root, selected_paths):
    project = _safe_root(project_root)
    if project is None:
        return None, None, "unsafe_or_inaccessible_path"
    corpus_relative = Path(corpus_root) if isinstance(corpus_root, (str, Path)) else None
    if corpus_relative is None or corpus_relative.is_absolute() or ".." in corpus_relative.parts:
        return None, None, "unsafe_or_inaccessible_path"
    corpus = project.joinpath(*corpus_relative.parts)
    if _traverses_reparse_point(corpus) or _traverses_symlink(corpus) or not corpus.is_dir():
        return None, None, "unsafe_or_inaccessible_path"
    try:
        if Path(metadata_path).is_absolute() or ".." in Path(metadata_path).parts:
            return None, None, "unsafe_or_inaccessible_path"
    except TypeError:
        return None, None, "unsafe_or_inaccessible_path"
    metadata = project / Path(metadata_path)
    if _traverses_reparse_point(metadata) or _traverses_symlink(metadata):
        return None, None, "unsafe_or_inaccessible_path"
    if any(_traverses_reparse_point(corpus / Path(path)) or _traverses_symlink(corpus / Path(path))
           for path in selected_paths):
        return None, None, "unsafe_or_inaccessible_path"
    valid, errors, record = _validate_source_capture(
        metadata_path, project, corpus_relative, selected_paths
    )
    if not valid or record is None:
        return None, None, "invalid_or_incomplete_envelope"
    return record, corpus, ""


def _index(record):
    sources = {}
    for source in record["sources"]:
        reps = {rep["representation_id"]: rep for rep in source["representations"]}
        sources[source["source_id"]] = (source, reps)
    return sources


def _validated_rep(source_index, source_id, representation_id):
    found = source_index.get(source_id)
    return None if found is None else found[1].get(representation_id)


def _fragment_valid(fragment, data: Optional[bytes]) -> bool:
    if fragment is None:
        return True
    if data is None:
        return False
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        return False
    line_count = 0 if not text else text.count("\n") + (0 if text.endswith("\n") else 1)
    return fragment["end_line"] <= line_count


def resolve_evidence_binding(
    *,
    project_root: str | Path,
    binding_path: str | Path,
    knowledge_path: str,
    baseline_metadata_path: str | Path,
    baseline_project_root: str | Path,
    baseline_corpus_root: str | Path,
    baseline_selected_paths: Iterable[str],
    current_metadata_path: str | Path,
    current_project_root: str | Path,
    current_corpus_root: str | Path,
    current_selected_paths: Iterable[str],
    expected_revisions: Optional[Dict[str, Any]] = None,
    authorize_validation_read: Callable[[], bool] = lambda: False,
    authorize_processing_and_report: Callable[[], bool] = lambda: False,
) -> dict:
    """Resolve one explicit binding document; permission checks are trusted host preconditions.

    The host binds both no-argument callbacks to the exact operation, roots, paths, and
    expected revisions supplied by its trusted interaction. These assertions are neither
    credentials nor a persisted grant. Validation and processing/report permission are
    checked before any filesystem access; denial raises PermissionError outside the ADR-036
    report wire.
    """
    if (not isinstance(baseline_selected_paths, (list, tuple))
            or not isinstance(current_selected_paths, (list, tuple))
            or len(baseline_selected_paths) > 100000
            or len(current_selected_paths) > 100000
            or any(not isinstance(path, str) or not _safe_relative(path)
                   for path in (*baseline_selected_paths, *current_selected_paths))):
        return _blocked("invalid_binding")
    if expected_revisions is not None:
        if (not isinstance(expected_revisions, dict)
                or any(not isinstance(key, str) or not isinstance(value, str) or not DIGEST.fullmatch(value)
                       for key, value in expected_revisions.items() if key != "selected_files")):
            raise ValueError("expected revision request is invalid")
        file_expectations = expected_revisions.get("selected_files", {})
        if (not isinstance(file_expectations, dict)
                or any(not isinstance(key, str) or not isinstance(value, str) or not DIGEST.fullmatch(value)
                       for key, value in file_expectations.items())):
            raise ValueError("expected revision request is invalid")
    _permission(authorize_validation_read, "evidence validation read denied")
    _permission(authorize_processing_and_report, "evidence processing/report denied")
    if not isinstance(knowledge_path, str) or relative_markdown(knowledge_path) is None:
        return _blocked("invalid_binding")
    if not isinstance(binding_path, (str, Path)) or not isinstance(baseline_metadata_path, (str, Path)) or not isinstance(current_metadata_path, (str, Path)):
        return _blocked("invalid_binding")
    if not isinstance(baseline_project_root, (str, Path)) or not isinstance(current_project_root, (str, Path)):
        return _blocked("invalid_binding")
    binding_path = Path(binding_path)
    if binding_path.is_absolute() or ".." in binding_path.parts:
        return _blocked("invalid_binding")
    try:
        expected_set = set(expected_revisions or {})
    except (TypeError, ValueError):
        raise ValueError("expected revision request is invalid")
    if not expected_set <= {"binding", "knowledge", "baseline_metadata", "current_metadata", "selected_files"}:
        raise ValueError("expected revision request is invalid")
    path_values = [binding_path.as_posix(), knowledge_path,
                   Path(baseline_metadata_path).as_posix(), Path(current_metadata_path).as_posix()]
    path_values.extend(baseline_selected_paths)
    path_values.extend(current_selected_paths)
    if not all(isinstance(path, str) and _safe_relative(path) for path in path_values):
        return _blocked("invalid_binding")
    # Binding and knowledge paths share one explicitly selected project root; envelopes keep
    # their own explicitly selected roots. No root is inferred from a file or current directory.
    base_root = _safe_root(project_root)
    if base_root is None:
        return _blocked("unsafe_or_inaccessible_path")
    binding_relative = binding_path.as_posix()
    binding_bytes, error = _read_selected(base_root, binding_relative, MAX_BINDING_BYTES)
    if error:
        return _blocked(error)
    assert binding_bytes is not None
    try:
        binding = json.loads(binding_bytes.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, ValueError, json.JSONDecodeError, RecursionError):
        return _blocked("invalid_binding")
    try:
        if len(json.dumps(binding, ensure_ascii=False).encode("utf-8")) > MAX_BINDING_BYTES:
            return _blocked("resource_limit_exceeded")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        return _blocked("invalid_binding")
    invalid = _validate_binding(binding)
    if invalid:
        return _blocked(invalid)
    knowledge = binding["knowledge"]
    if knowledge["path"] != knowledge_path:
        return _blocked("invalid_binding")
    knowledge_bytes, error = _read_selected(base_root, knowledge_path, MAX_FILE_BYTES)
    if error:
        return _blocked(error)
    assert knowledge_bytes is not None
    try:
        knowledge_bytes.decode("utf-8")
    except UnicodeError:
        return _blocked("unsafe_or_inaccessible_path")
    observed_knowledge = hashlib.sha256(knowledge_bytes).hexdigest()
    if expected_revisions is not None:
        observed_inputs = {"binding": hashlib.sha256(binding_bytes).hexdigest(),
                           "knowledge": observed_knowledge}
        for name, observed_value in observed_inputs.items():
            expected_value = expected_revisions.get(name)
            if expected_value is not None and expected_value != observed_value:
                raise ValueError("expected input revision mismatch")

    # Compare trusted expected metadata revisions immediately after the authorized metadata
    # read, before envelope correspondence, fragment checks, or report derivation.
    for name, metadata_path, project_root_arg in (
        ("baseline_metadata", baseline_metadata_path, baseline_project_root),
        ("current_metadata", current_metadata_path, current_project_root),
    ):
        expected_value = (expected_revisions or {}).get(name)
        if expected_value is not None:
            metadata_root = _safe_root(project_root_arg)
            if metadata_root is None:
                return _blocked("unsafe_or_inaccessible_path")
            metadata_data, read_error = _read_selected(metadata_root, Path(metadata_path).as_posix(), MAX_METADATA_BYTES)
            if read_error or metadata_data is None or hashlib.sha256(metadata_data).hexdigest() != expected_value:
                raise ValueError("expected input revision mismatch")

    baseline, baseline_corpus, reason = _envelope(
        baseline_project_root, baseline_metadata_path, baseline_corpus_root, baseline_selected_paths
    )
    if reason:
        return _blocked(reason)
    current, current_corpus, reason = _envelope(
        current_project_root, current_metadata_path, current_corpus_root, current_selected_paths
    )
    if reason:
        return _blocked(reason)
    assert baseline is not None and current is not None and baseline_corpus is not None and current_corpus is not None
    # Caller-known selected-file revisions are checked against the validator's exact byte
    # snapshot digests. Keys are explicitly scoped as '<side>:<relative-path>' and cannot
    # add paths or trigger reads.
    selected_expectations = (expected_revisions or {}).get("selected_files", {})
    selected_allowed = {
        *(f"baseline:{path}" for path in baseline_selected_paths),
        *(f"current:{path}" for path in current_selected_paths),
    }
    if set(selected_expectations) - selected_allowed:
        raise ValueError("expected revision request is invalid")
    for side, record, expected_paths in (
        ("baseline", baseline, baseline_selected_paths),
        ("current", current, current_selected_paths),
    ):
        observed = {rep["raw_path"]: rep["revision"]["digest"]
                    for source in record["sources"] for rep in source["representations"]
                    if rep["retention"] == "retained"}
        for path in expected_paths:
            expected_digest = selected_expectations.get(f"{side}:{path}")
            if expected_digest is not None and observed.get(path) != expected_digest:
                raise ValueError("expected input revision mismatch")
    baseline_index, current_index = _index(baseline), _index(current)

    # Validate all binding correspondences and fragment bounds before deriving any report.
    for binding_item in binding["bindings"]:
        for ref in binding_item["evidence"]:
            rep = _validated_rep(baseline_index, ref["source_id"], ref["representation_id"])
            if (rep is None or rep["retention"] != "retained"
                    or rep["revision"]["digest"] != ref["observed_sha256"]):
                return _blocked("baseline_identity_mismatch")
            if ref.get("fragment") is not None:
                fragment_bytes, fragment_error = _read_selected(
                    baseline_corpus, rep["raw_path"], MAX_FILE_BYTES
                )
                if (fragment_error or fragment_bytes is None
                        or hashlib.sha256(fragment_bytes).hexdigest() != rep["revision"]["digest"]):
                    return _blocked("baseline_identity_mismatch")
                if not _fragment_valid(ref.get("fragment"), fragment_bytes):
                    return _blocked("invalid_binding")
            mapping = ref.get("current")
            if mapping is not None:
                target = _validated_rep(current_index, mapping["source_id"], mapping["representation_id"])
                if target is not None and target["retention"] != "retained":
                    return _blocked("invalid_binding")

    # Enforce ADR-031's aggregate selected knowledge/evidence bytes across both envelopes.
    total = len(knowledge_bytes)
    for record, corpus_root in ((baseline, baseline_corpus), (current, current_corpus)):
        for source in record["sources"]:
            for representation in source["representations"]:
                if representation["retention"] != "retained":
                    continue
                path = corpus_root.joinpath(*representation["raw_path"].split("/"))
                try:
                    total += os.stat(path, follow_symlinks=False).st_size
                except OSError:
                    return _blocked("unsafe_or_inaccessible_path")
                if total > MAX_SELECTED_TOTAL:
                    return _blocked("resource_limit_exceeded")
    refs = []
    if sum(len(b["evidence"]) for b in binding["bindings"]) + 1 > MAX_REPORT_ITEMS:
        return _blocked("resource_limit_exceeded")
    for binding_item in binding["bindings"]:
        for ref in binding_item["evidence"]:
            base_rep = _validated_rep(baseline_index, ref["source_id"], ref["representation_id"])
            current_map = ref.get("current")
            current_rep = None
            current_source = None
            if current_map is not None:
                current_pair = current_index.get(current_map["source_id"])
                if current_pair is not None:
                    current_source = current_pair[0]
                    current_rep = current_pair[1].get(current_map["representation_id"])
            item = {
                "binding_id": binding_item["binding_id"],
                "source_id": ref["source_id"],
                "representation_id": ref["representation_id"],
                "observed_sha256": base_rep["revision"]["digest"],
                "raw_path": (Path(baseline_corpus_root) / base_rep["raw_path"]).as_posix(),
            }
            if current_map is None:
                state, why = "missing", "current_mapping_absent"
            elif current_rep is None:
                state, why = "missing", "current_mapping_absent"
                item["current"] = {"source_id": current_map["source_id"],
                                    "representation_id": current_map["representation_id"]}
            else:
                current_digest = current_rep["revision"]["digest"]
                item["current"] = {
                    "source_id": current_source["source_id"],
                    "representation_id": current_rep["representation_id"],
                    "observed_sha256": current_digest,
                    "raw_path": (Path(current_corpus_root) / current_rep["raw_path"]).as_posix(),
                }
                if current_digest == ref["observed_sha256"]:
                    state, why = "unchanged", "byte_revision_matches"
                else:
                    state, why = "changed", "byte_revision_differs"
            item["state"], item["reason"] = state, why
            refs.append(item)
    if total > MAX_SELECTED_TOTAL:
        return _blocked("resource_limit_exceeded")
    summary = "changed" if observed_knowledge != knowledge["sha256"] or any(r["state"] == "changed" for r in refs) else "missing" if any(r["state"] == "missing" for r in refs) else "unchanged"
    binding_order = {item["binding_id"]: index for index, item in enumerate(binding["bindings"])}
    refs.sort(key=lambda r: (r["source_id"], r["representation_id"], r["observed_sha256"], r["binding_id"], binding_order[r["binding_id"]]))
    report = {"status": "COMPLETE", "knowledge": {"path": knowledge_path, "observed_sha256": observed_knowledge, "summary": summary}, "references": refs}
    try:
        serialized = json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError):
        return _blocked("invalid_binding")
    if len(serialized) > MAX_REPORT_BYTES:
        return _blocked("serialization_limit_exceeded")
    return report
