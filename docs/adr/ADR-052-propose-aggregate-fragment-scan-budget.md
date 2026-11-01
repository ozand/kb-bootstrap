# ADR-052: Propose an aggregate fragment scan-work budget

**Status**: Proposed
**Date**: 2026-11-01
**Authors**: Pi coding agent
**Supersedes**: ADR-051 (only its aggregate fragment scan-work limit and exhaustion behavior)
**Related**: Issue #128; ADR-024, ADR-026, ADR-031, ADR-035, ADR-036, ADR-042, ADR-051

## Context

Accepted ADR-051 bounds each retained representation to 64 MiB, each fragment to 64 KiB, the selected snapshots to ADR-031's 256 MiB aggregate, and fragment references to at most 999. It requests linear-time KMP for each fragment but has no aggregate scan-work cap. A caller may cite distinct fragments in many bindings against the same selected 64 MiB representation, so snapshot accounting does not account for repeated CPU search.

This gap was found by exact PR #266 review finding [4436839789](https://github.com/ozand/kb-bootstrap/pull/266#discussion_r4436839789) against accepted ADR-051 source `91b55c0c525ff5e6454981de0004797855ed5a22`; acceptance delta `d7706edfad32092fa723255f0b1c890b65613b0a` is also retained in open PR #266. Research checkpoint #128 comment [6562209746](https://github.com/ozand/kb-bootstrap/issues/128#issuecomment-6562209746) records the arithmetic before this proposal. At the existing maxima, 999 scans × 64 MiB = 65,998 MiB (about 64.45 GiB) of representation-byte scanning, despite the 256 MiB retained snapshot cap. The finding is confirmed. No consumer data was accessed.

## Decision

If accepted, supersede only ADR-051's aggregate scan-work limit/exhaustion clauses with the following bound; all other ADR-051 decisions, API, result shapes, revision rules, privacy/safety guards, and ADR-036/042 compatibility remain unchanged.

For every fragment continuity invocation, define scan work as the sum, over each fragment-bearing reference that has a validated explicit mapped current representation and a non-empty extracted baseline fragment, of `current_representation_byte_length + fragment_byte_length`. This conservatively bounds a linear-time KMP search plus per-pattern preprocessing. Count the full current representation length for every separate reference, even when references share one representation; searching it repeatedly is repeated work. Unmapped, mapped-current-missing, and empty-fragment observations require no KMP scan and contribute zero. All byte lengths come only from the same validated per-invocation snapshots used by the resolver; never stat, open, or infer extra paths to estimate the budget.

Set the invocation-wide maximum scan work to **256 MiB (268,435,456 byte-work units)**. Before starting any KMP search, validate/derive every eligible baseline fragment and current representation from the authorized snapshots, compute the complete sum with overflow-safe integer arithmetic, and compare it with the cap. If the sum exceeds the cap, return the resolver's ADR-036 report unchanged and companion `{"status":"BLOCKED","reason":"aggregate_scan_budget_exceeded"}` with no observations. Do not search a prefix of the references, emit partial outcomes, or mark any reference unique/unambiguous after budget exhaustion. Equality with the cap is permitted and all scans complete.

This preflight makes exhaustion deterministic and atomic: a caller receives either the complete ordered companion observations or one blocked companion result, never a partial result whose remaining rows could alter ambiguity. `aggregate_scan_budget_exceeded` is added to ADR-051's closed companion blocked-reason vocabulary. The ADR-036 report and ADR-042 composition input remain byte-for-byte unchanged even when companion scan work is blocked. No report reference paths are reopened, no caller paths or authority are added, and all trusted permission, expected-revision, path, snapshot, and existing selected-byte/report budgets remain authoritative.

## Consequences

At most 256 MiB of linear scan/preprocessing work is authorized for fragment matching per invocation, regardless of reference multiplicity. A complete selected evidence input may now yield an ADR-036 COMPLETE report alongside a companion BLOCKED result when the continuity operation's own aggregate budget is insufficient; the wrapper preserves that distinction without partial or false uniqueness claims. The limit is a proposed engineering ceiling, not a measured throughput guarantee.

## Test Contract

| Claim if accepted and implemented | Synthetic test |
|---|---|
| Budget cost is deterministic, includes one full representation length per mapped fragment plus pattern bytes, and counts repeated scans of a shared representation repeatedly | `tests/test_evidence_binding.py::test_fragment_scan_budget_cost` |
| Work exactly at 256 MiB completes all observations; work one byte over blocks before any matcher invocation and returns no observations | `tests/test_evidence_binding.py::test_fragment_scan_budget_atomic_exhaustion` |
| Mixed mapped, unmapped, missing-current and empty-fragment references use only eligible work; no prefix-search result or false unique outcome leaks on overflow | `tests/test_evidence_binding.py::test_fragment_scan_budget_mixed_references` |
| Blocked companion preserves the ADR-036 report unchanged, ADR-042 still receives its exact existing report shape, and no reads beyond the existing snapshots occur | `tests/test_evidence_review.py::test_fragment_scan_budget_composed_blocked_result` |

These are proposed synthetic tests, not implemented tests or runtime guarantees.

## Rollback

Before acceptance, withdraw this proposal; ADR-051 remains as recorded, with its scan-work gap explicitly unresolved. If accepted, this ADR supersedes only its stated scan budget/exhaustion clauses. No binding, report, snapshot, or consumer data migration/deletion is authorized.

## References

- Issue #128 and research checkpoint comment 6562209746.
- Accepted ADR-051 and exact review finding 4436839789.
- Accepted ADR-024, ADR-026, ADR-031, ADR-035, ADR-036, and ADR-042.
