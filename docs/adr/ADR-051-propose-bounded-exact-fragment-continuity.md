# ADR-051: Propose bounded exact fragment continuity observations

**Status**: Proposed
**Date**: 2026-11-01
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #128; ADR-024, ADR-026, ADR-031, ADR-035, ADR-036, ADR-040, ADR-042

## Context

Accepted ADR-031/036 bind a knowledge document to explicitly validated retained evidence. ADR-036's optional fragment is a representation-ID-bound inclusive UTF-8 line range. The current `resolve_evidence_binding` validates that locator against the baseline representation, then compares mapped current representations by digest. It does not extract/compare fragment bytes or report candidate locations. A changed representation digest therefore does not answer whether exact fragment bytes remain at the old location, uniquely moved, repeated, or absent. ADR-036's reference shape is closed and ADR-042 validates it strictly; changing either wire contract in this increment is out of scope.

Research was recorded before this draft in #128 comment [6561814106](https://github.com/ozand/kb-bootstrap/issues/128#issuecomment-6561814106). It was based on Issue #128, accepted ADR-031/036/040/042, and the resolver at `7499f3761a8b746ef29ac9c5ef72b421fb53f61b`. No consumer or user data was read. Current access already has trusted permission callbacks, caller-selected paths, full envelope validation, safe bounded selected-file reads, expected-revision checks, and no discovery/network/write. The proposal must preserve these seams and the immutable binding input.

## Decision

If accepted, add a narrowly scoped, read-only companion result for optional fragment continuity; do not change ADR-036 binding/report JSON or ADR-042 composition shapes. A companion row is explicitly keyed to the validated baseline `(binding_id, source_id, representation_id, observed_sha256, fragment locator)` and the caller's explicit current mapping when present. It reports only byte-continuity observations, not semantic meaning, truth, entailment, support, or unchanged context.

Continuity is assessable only when an explicit current mapping resolves to a retained representation in the fully validated current envelope. Missing mapping or absent mapped representation yields `unassessable_no_mapping` (even where the existing resolver classifies the evidence reference `missing`); it never implies deletion. Unsafe/inaccessible bytes, invalid UTF-8, invalid/out-of-range locator, baseline digest mismatch, malformed input, or exceeded bounds block the operation with no partial-success result. Empty extracted fragments are unassessable and block; they are never treated as matching everywhere.

For assessable input, extract the selected baseline line range from the exact validated UTF-8 representation bytes. The fragment is the byte slice from the first selected line's start through the last selected line's content end, excluding that final line's LF or CRLF delimiter; internal delimiters remain bytes. Its baseline byte offset is the start of the first selected line, zero-based from the representation beginning. No decoding normalization, Unicode normalization, whitespace folding, or newline conversion is performed. Search only the explicitly mapped, validated current representation bytes for exact occurrences of those fragment bytes. Enumerate overlapping matches with a linear-time prefix-function/KMP scan and report offsets in ascending byte position, zero-based from the current representation beginning; bind them to the observed current digest/path already established by the resolver.

The companion outcome is exactly one of: `exact_at_baseline_offset` (one match at the baseline byte offset), `unique_moved_match` (one match at a different offset), `ambiguous_exact_matches` (two or more matches, including overlaps), or `no_exact_match`. These names make no claim that the cited text remains semantically applicable. A match at the old offset is only byte continuity; it does not establish surrounding conditions, meaning, or correctness. No automatic relocation, binding rewrite, deletion inference, or semantic matching occurs.

Reuse the existing resolver's trusted authorization, validated envelope identities, safe selected-file read mechanism, path containment/reparse checks, expected-revision checks, and aggregate resource accounting. The companion must consume the same validated byte snapshots/read seam as the resolver, not reopen paths through a weaker helper or create a second caller-controlled path set. If the current resolver seam cannot safely provide those bytes without duplicate/unbounded reads, block and revise the design rather than bypassing guards. Search is restricted to the single mapped representation; no directory traversal, other representation, source discovery, origin access, network, cache, or write is permitted.

Proposed additional ceilings: 64 KiB extracted fragment bytes, 64 MiB searched representation bytes (no greater than the existing per-file cap), and at most 100 reported match offsets. Exceeding any bound blocks the whole companion result without truncation-as-success. Search must be linear in searched bytes plus emitted offsets; candidate offsets are sorted by byte position. The operation reuses existing selected-total limits and must account for each actual retained byte snapshot once, not double-count it merely because both resolver and companion consume it. The current resolver validates envelopes and later reads representations for fragments, while aggregate accounting currently uses file sizes; accepted ADR-024/031 contracts must control any snapshot reuse/accounting adjustment. Implementation must add a concrete shared-safe-read seam and prove composed workflow access counts; it must not merely restate limits or create a second unbounded read. These are proposed ceilings, not current runtime guarantees.

The companion output is transient and separate from both accepted report formats. It contains the exact baseline/current reference identities and digests needed to correlate the result with the resolver report, outcome, and bounded offsets only; it contains no representation payload, absolute path, or copied fragment text. It cannot be fed back as authority or mutate bindings/knowledge. ADR-040 lineage and ADR-042 worklist behavior remain separate; composition for a caller-facing workflow must preserve both outputs and their existing schemas without reinterpreting lineage or resolver states.

## Consequences

A reviewer can distinguish exact byte continuity at the original offset, one exact moved occurrence, duplicate/overlapping occurrences, and no exact match, while retaining the accepted resolver's explicit mapping and access boundaries. Identical fragment bytes can occur in unrelated contexts; this result intentionally cannot resolve that ambiguity semantically. Changed surrounding context remains a human review concern.

## Synthetic test contract

| Claim if accepted and implemented | Synthetic test |
|---|---|
| Direct and mapped fragment bytes are extracted from validated revisions only; no mapping is unassessable, not deletion | `tests/test_evidence_binding.py::test_fragment_continuity_mapping_states` |
| Exact bytes at old offset, one moved match, duplicate matches, overlapping matches, and no match produce their distinct outcomes and correct byte offsets | `tests/test_evidence_binding.py::test_fragment_continuity_exact_match_matrix` |
| Empty fragment, invalid UTF-8, out-of-range lines, stale expected revisions, unreadable input, and mapping mismatch do not yield partial success | `tests/test_evidence_binding.py::test_fragment_continuity_blocks_invalid_inputs` |
| Fragment/representation/occurrence bounds block; overlapping search is linear and results are deterministically ordered | `tests/test_evidence_binding.py::test_fragment_continuity_resource_bounds` |
| Integrated resolver plus companion plus ADR-042 composition preserves exact accepted wire shapes, checks permissions before reads, reads only explicitly selected snapshots, and performs no writes/network/discovery | `tests/test_evidence_review.py::test_composed_fragment_continuity_is_read_only` |

These are proposed cases, not implemented tests or guarantees. Direct and composed workflow cases must use synthetic fixtures and instrument file/network/process/write access; do not use consumer data.

## Non-goals

No changes to ADR-031/036/040/042, existing resolver outcomes or worklist schema; no text similarity, semantic equivalence, inference, automated relocation, binding/knowledge mutation, claim database, extra path discovery, lineage inference, lifecycle transition, or conclusion that absence of an exact fragment means deletion or retraction.

## Rollback

Before acceptance, withdraw this proposal. No runtime, consumer data, accepted ADR, or binding record is changed. If accepted and implemented, a superseding decision must preserve existing binding/report compatibility; no automatic migration or deletion is authorized.

## References

- Issue #128 and pre-edit research checkpoint comment 6561814106.
- Accepted ADR-024, ADR-026, ADR-031, ADR-035, ADR-036, ADR-040, and ADR-042.
- `kb_bootstrap/evidence_binding.py` at baseline `7499f3761a8b746ef29ac9c5ef72b421fb53f61b`.
