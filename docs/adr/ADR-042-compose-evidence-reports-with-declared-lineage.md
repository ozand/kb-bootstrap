# ADR-042: Compose evidence binding reports with declared lineage

**Status**: Proposed
**Date**: 2026-10-28
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #128; ADR-031, ADR-035, ADR-036, ADR-040

## Context

Accepted ADR-031/035/036 provide a caller-directed, policy-gated, read-only resolver. ADR-040 provides a separate pure caller-declared lineage classifier. Neither composes the report into a lineage-aware worklist. ADR-040 leaves integration separate; ADR-036 is a strict wire contract, so integration must not alter either API or wire format.

Source IDs or equal digests do not establish genealogy. The caller must explicitly map each resolver reference identity to a lineage record. Complete classification describes declarations only, not verified origin, independence, truth, entailment, completeness or authority.

## Decision

If accepted, add one pure in-memory function:

`compose_evidence_review_worklist(resolver_report, lineage_records, coverage_complete, reference_lineage_ids)`

The resolver report must be a JSON-compatible plain mapping/list tree of string-keyed objects, arrays, strings, booleans and null, with exactly one of these ADR-036 v1 shapes; unknown/missing fields or wrong types raise `ValueError`. Reject non-JSON values and non-string object keys. `BLOCKED` has exactly `status: BLOCKED` and `reason`, one of `invalid_binding`, `invalid_or_incomplete_envelope`, `unsafe_or_inaccessible_path`, `baseline_identity_mismatch`, `resource_limit_exceeded`, or `serialization_limit_exceeded`. `COMPLETE` has exactly `status: COMPLETE`, `knowledge`, and `references`; knowledge has `path`, `summary`, and optional `observed_sha256`, with no other fields. Summary is `unchanged`, `changed`, or `missing`; digest, when present, is 64 lowercase hex characters. Enforce ADR-031 summary precedence: `unchanged` requires every reference unchanged; `missing` requires at least one missing reference and no changed reference; `changed` is valid with a changed reference or independently changed knowledge. Each reference has exactly `binding_id`, `source_id`, `representation_id`, `observed_sha256`, `raw_path`, `state`, `reason`, and optional `current`. State/reason pairs are exactly `unchanged`/`byte_revision_matches`, `changed`/`byte_revision_differs`, or `missing`/`current_mapping_absent`. `current` has exactly either explicit `source_id` and `representation_id` only, or those two plus `observed_sha256` and `raw_path`; partial combinations are invalid. IDs, digests and relative paths follow ADR-036/031. References are bounded to 999, with order by baseline source ID, representation ID, observed digest, binding ID and evidence-array position. Do not sort or normalize supplied rows. ADR-036/031 remain normative for field constraints.

The runtime resolver adds `knowledge.observed_sha256`, absent from ADR-036's illustrative JSON sample but present in its actual report contract; accept it only as the optional exact digest field above and preserve it unchanged. Do not recalculate or reinterpret any report value. The helper cannot establish that a supplied report was produced by the resolver or is current.

Pass the complete lineage graph and coverage flag to `classify_evidence_lineage`; its exact bounds, validation and result shapes remain authoritative. `reference_lineage_ids` is a mapping of at most 999 two-string `(source_id, representation_id)` tuple keys to IDs valid under ADR-040. Keys must exist in COMPLETE rows; every mapped ID must exist in classifier output. Repeated identities across bindings share one mapping. Unmapped rows are allowed. No mapping is inferred from IDs, digests, paths or content. Inputs are not mutated; `resolver_report` in the result is a deep copy preserving its values and ordering. Worklist rows are derived from that copy, so nested reference values are not aliased to caller-owned report objects.

Validation order is fixed: (1) validate the whole resolver report shape and caps; (2) run the lineage classifier on the whole graph, validating it even when report status is BLOCKED; (3) validate the entire mapping's type, tuple key shape, string values, reference membership and lineage-ID membership; (4) compose. Any invalid input raises `ValueError` and returns no result. Thus malformed graph/mapping still rejects a valid BLOCKED report. For BLOCKED reports, the reference set is empty and the only valid mapping is empty. This deterministic order prevents status short-circuiting from hiding invalid auxiliary input.

For BLOCKED, return the deep-copied report unchanged, `knowledge_review_required: false`, and an empty worklist; do not interpret its reason. For COMPLETE, emit one row per reference in validated resolver order. Each row has exactly `reference`, `review_required`, and `lineage`; `reference` is a deep copy of the full original reference value, unchanged. `review_required` is true only for `changed` or `missing`; preserve unchanged rows. An unmapped row receives `lineage: {"state": "unknown"}`. A mapped row with incomplete coverage receives `{"id": <mapped ID>, "state": "unknown"}`, matching ADR-040's unknown record shape and exposing no roots/count. With complete coverage, mapped rows receive the classifier result (`id`, `state`, `root_ids`, `root_count`) unchanged. Add `knowledge_review_required`, true exactly when the validated knowledge summary is `changed`, even if all references are unchanged. Missing lineage never changes resolver state or review status.

Complete output has exactly `resolver_report`, `knowledge_review_required`, and `worklist`; each worklist row has exactly `reference`, `review_required`, and `lineage`. It is `{"resolver_report": <deep-copied report>, "knowledge_review_required": <bool>, "worklist": [<rows>]}`. Blocked output uses the same top-level keys, false and an empty list. Enforce ADR-036's total report ceiling of 1000 items, including its one document summary: at most 999 reference rows. Reject excess rather than truncate. Repeated identities across bindings remain valid under ADR-036; one mapping applies to each row. Do not reinterpret blocked reasons or permission exceptions.

The helper performs no I/O, discovery, resolver invocation, path/permission validation, lineage inference, persistence, mutation or lifecycle action. Caller invokes the accepted resolver and supplies its report. Output is transient; the helper cannot authenticate assertions or prove report origin.

## Consequences

Caller can present byte-revision observations beside declared lineage in one transient worklist without changing APIs. Caller maintains mapping; unmapped references and incomplete lineage stay unknown. The helper cannot establish report authenticity/currentness; use the resolver under existing policy.

ADR-031/035/036 input, policy, I/O, report and permission contracts remain unchanged. ADR-040 graph validation/classification remains unchanged. No ancestry verification, semantic support, corroboration, truth score, automatic merge, discovery, consumer write, retention, lifecycle transition or approval is introduced.

## Alternatives Considered

### Orchestrate resolver

Rejected: wrapping file access, strict binding validation, permission preconditions and failure behavior creates another policy surface. Pure projection keeps checks authoritative.

### Join by ID, digest, path or content

Rejected: these do not establish genealogy or explicit correspondence; caller supplies a separate mapping.

### Extend ADR-036 wire/report

Rejected: changing its strict accepted contract conflates byte identity and declared lineage.

### Omit unchanged references

Rejected: omission hides observations. Unchanged rows remain present.

## Test Contract

| Claim if accepted and implemented | Synthetic test | Currently |
|---|---|---|
| Changed/missing require review; unchanged rows persist; lineage leaves resolver rows unchanged | `tests/test_evidence_review.py::test_worklist_preserves_resolver_rows_and_marks_review` | not yet written |
| Unmapped lineage is unknown without an ID; mapped incomplete lineage retains only ADR-040's ID/state unknown shape; no root counts or automatic ID inference | `tests/test_evidence_review.py::test_unmapped_or_incomplete_lineage_is_unknown` | not yet written |
| Changed knowledge requires review despite unchanged references | `tests/test_evidence_review.py::test_changed_knowledge_requires_review` | not yet written |
| Exact ADR-036 COMPLETE/BLOCKED report shapes, nested fields, states, reasons, digest/path formats, ordering and caps are validated before composition | `tests/test_evidence_review.py::test_report_validation_uses_adr036_contract` | not yet written |
| BLOCKED with empty mapping passes through with no partial worklist; malformed lineage or non-empty mapping still rejects in the specified validation order | `tests/test_evidence_review.py::test_blocked_report_validates_all_inputs_before_passthrough` | not yet written |
| Invalid, extraneous, dangling, or malformed explicit mappings reject composition | `tests/test_evidence_review.py::test_invalid_reference_lineage_mapping_is_rejected` | not yet written |
| Inputs are not mutated; returned report and nested reference rows are deep-copied values | `tests/test_evidence_review.py::test_composition_does_not_mutate_or_alias_inputs` | not yet written |
| Report cap rejects rather than truncates | `tests/test_evidence_review.py::test_report_bound_is_not_truncated` | not yet written |

These future synthetic runtime tests are not implementation/verification claims. ADR alone authorizes no implementation; runtime work needs separate scoped authorization after acceptance.

## Rollback

Before acceptance, withdraw this proposal. If accepted and implemented, removing the helper must not alter reports, lineage inputs, bindings or authored knowledge. Existing contracts remain independently usable.

## References

- Issue #128 bounded-review and duplicate/generated-lineage criteria.
- Accepted ADR-031, ADR-035, ADR-036 and ADR-040.
- `kb_bootstrap/evidence_binding.py`; `kb_bootstrap/evidence_lineage.py`.
