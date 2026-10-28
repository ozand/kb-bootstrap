"""Classify caller-declared evidence lineage without certifying independence."""

from collections import deque
from collections.abc import Mapping
import unicodedata

MAX_RECORDS = 1000
MAX_UPSTREAM_IDS = 100
MAX_ID_LENGTH = 256
KINDS = frozenset(("independent", "generated", "reprint"))


def _valid_id(value):
    return (
        type(value) is str
        and 1 <= len(value) <= MAX_ID_LENGTH
        and not any(unicodedata.category(char) == "Cc" for char in value)
    )


def classify_evidence_lineage(records, coverage_complete):
    """Classify a bounded lineage graph supplied as a list of mappings.

    Each mapping has exactly ``id``, ``kind`` and ``upstream_ids``. IDs are
    opaque case-sensitive strings; independent records have no upstreams,
    generated/reprint records have at least one. Invalid input raises
    ``ValueError`` for the whole call.

    Complete coverage returns records sorted by ID with ``state: classified``,
    sorted declared ``root_ids``, and matching ``root_count``. Incomplete
    coverage returns only sorted IDs and ``state: unknown``. This is declared
    ancestry, not verified independence, genealogy, truth, or completeness.
    Inputs are not mutated; the helper performs no I/O or discovery.
    """
    if type(records) is not list or type(coverage_complete) is not bool:
        raise ValueError("invalid lineage input")
    if len(records) > MAX_RECORDS:
        raise ValueError("invalid lineage input")

    by_id = {}
    for record in records:
        if not isinstance(record, Mapping) or set(record) != {"id", "kind", "upstream_ids"}:
            raise ValueError("invalid lineage input")
        identifier, kind, upstream_ids = (
            record["id"], record["kind"], record["upstream_ids"]
        )
        if not _valid_id(identifier) or identifier in by_id:
            raise ValueError("invalid lineage input")
        if type(kind) is not str or kind not in KINDS:
            raise ValueError("invalid lineage input")
        if type(upstream_ids) is not list or len(upstream_ids) > MAX_UPSTREAM_IDS:
            raise ValueError("invalid lineage input")
        if any(not _valid_id(upstream) for upstream in upstream_ids):
            raise ValueError("invalid lineage input")
        if len(set(upstream_ids)) != len(upstream_ids) or identifier in upstream_ids:
            raise ValueError("invalid lineage input")
        if (kind == "independent") != (not upstream_ids):
            raise ValueError("invalid lineage input")
        by_id[identifier] = (kind, tuple(upstream_ids))

    for _, upstream_ids in by_id.values():
        if any(upstream not in by_id for upstream in upstream_ids):
            raise ValueError("invalid lineage input")

    dependents = {identifier: [] for identifier in by_id}
    remaining = {}
    roots = {}
    for identifier, (kind, upstream_ids) in by_id.items():
        remaining[identifier] = len(upstream_ids)
        if kind == "independent":
            roots[identifier] = frozenset((identifier,))
        else:
            roots[identifier] = frozenset()
        for upstream in upstream_ids:
            dependents[upstream].append(identifier)

    ready = deque(sorted(
        identifier for identifier, count in remaining.items() if count == 0
    ))
    visited = 0
    while ready:
        identifier = ready.popleft()
        visited += 1
        for dependent in dependents[identifier]:
            roots[dependent] = roots[dependent] | roots[identifier]
            remaining[dependent] -= 1
            if remaining[dependent] == 0:
                ready.append(dependent)
    if visited != len(by_id):
        raise ValueError("invalid lineage input")

    if not coverage_complete:
        return [{"id": identifier, "state": "unknown"} for identifier in sorted(by_id)]
    return [
        {
            "id": identifier,
            "state": "classified",
            "root_ids": sorted(roots[identifier]),
            "root_count": len(roots[identifier]),
        }
        for identifier in sorted(by_id)
    ]
