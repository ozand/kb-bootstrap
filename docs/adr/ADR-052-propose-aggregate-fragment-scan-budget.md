# ADR-052: Bound aggregate fragment scan work

**Status**: Accepted
**Date**: 2026-11-01
**Authors**: Pi coding agent
**Supersedes**: ADR-051 (only its aggregate fragment scan-work limit and exhaustion behavior)
**Related**: Issue #128; ADR-024, ADR-026, ADR-031, ADR-035, ADR-036, ADR-042, ADR-051

Technical acceptance: the coordinator accepts this narrowly scoped decision under the owner's standing delegation recorded in [AGENTS.md](../../AGENTS.md), authorized by Issue #223. Independent review a5e passed proposed source `913be2599f4e2ce0408c2e2666dc1e6a89191f8b` against baseline `7499f3761a8b746ef29ac9c5ef72b421fb53f61b`. This combined PR revision reconciles that separately reviewed proposal with the already accepted ADR-051 lifecycle in one index change; it does not rewrite ADR-051's normative decision. ADR-051 is superseded only for aggregate scan-work budgeting/exhaustion; its other accepted provisions remain in force. Acceptance authorizes no runtime implementation before independent review of this combined exact source.

## Context

Accepted ADR-051 bounds each retained representation to 64 MiB, each fragment to 64 KiB, the selected snapshots to ADR-031's 256 MiB aggregate, and fragment references to at most 999. It requests linear-time KMP for each fragment but has no aggregate scan-work cap. A caller may cite distinct fragments in many bindings against the same selected 64 MiB representation, so snapshot accounting does not account for repeated CPU search.

This gap was found by exact PR #266 review finding [4436839789](https://github.com/ozand/kb-bootstrap/pull/266#discussion_r4436839789) against accepted ADR-051 source `91b55c0c525ff5e6454981de0004797855ed5a22`; acceptance delta `d7706edfad32092fa723255f0b1c890b65613b0a` is also retained in open PR #266. Research checkpoint #128 comment [6562209746](https://github.com/ozand/kb-bootstrap/issues/128#issuecomment-6562209746) records the arithmetic before this proposal. At the existing maxima, 999 scans × 64 MiB = 65,998 MiB (about 64.45 GiB) of representation-byte scanning, despite the 256 MiB retained snapshot cap. The finding is confirmed. No consumer data was accessed.

## Decision

This ADR supersedes only ADR-051's aggregate scan-work limit/exhaustion clauses with the following bound; all other ADR-051 decisions, API, result shapes, revision rules, privacy/safety guards, and ADR-036/042 compatibility remain unchanged.

Bound preparation as well as KMP search. A continuity invocation accepts at most the existing 999 fragment-bearing references. For baseline line extraction, group locators by the exact validated baseline representation snapshot identity and scan each distinct baseline snapshot at most once to locate requested line ranges. Sort that snapshot's at-most-999 bounded line-range descriptors by start line, end line, then ADR-036 report order; stream line boundaries once and extract requested ranges without scanning the full representation per locator or retaining a whole-file line-offset index. Descriptor and active-range memory is bounded by 999 locators and the 64 KiB per-fragment/64 MiB aggregate extracted-byte caps. Cap the sum of distinct baseline snapshot bytes traversed at the existing ADR-031 selected-byte ceiling of **256 MiB**; cap total extracted fragment/pattern bytes at **64 MiB**. The existing 999-reference ceiling and 64 KiB per-fragment ceiling imply a maximum of 65,470,464 extracted bytes, below this aggregate cap. If either cap would be exceeded, return the deterministic blocked result below before producing any observations. The extracted fragments and per-reference metadata are temporary, bounded to those ceilings, and discarded when the call returns.

Define total scan work as the sum of: (a) the byte length of each unique baseline representation snapshot traversed once for line extraction; (b) the byte length of every extracted fragment copied/processed for each reference; and (c) for every eligible mapped-current search, the full current representation byte length plus that reference's fragment byte length for KMP prefix-table preparation. Thus repeated references to one current representation count its full byte length for every scan; pattern preprocessing is not free; and KMP must continue scanning after the 100th match far enough to detect a 101st overlapping occurrence, which also remains linear in the counted current bytes. Unmapped, absent mapped-current, and empty-fragment observations have no KMP cost, though any required baseline locator extraction is still counted. All lengths and snapshot identities come only from the same already-authorized validated per-call snapshots; no stat/open/report-path lookup or new caller path is permitted.

Set the invocation-wide total scan-work maximum to **512 MiB (536,870,912 byte-work units)**. This bounds baseline traversal (at most 256 MiB), fragment extraction/pattern bytes (at most 64 MiB), and repeated mapped-current KMP work within one finite total. Use checked/saturating accumulation with a sentinel maximum of `cap + 1`: before each addition, if the operand exceeds `cap - accumulated`, set the accumulator to `cap + 1` and stop cost preparation. Never rely on machine-integer wraparound. At `cap + 1`, return the resolver's ADR-036 report unchanged and companion `{"status":"BLOCKED","reason":"aggregate_scan_budget_exceeded"}` with no observations. Equality with the cap is permitted. Complete all extraction, checked budget accounting, and bound validation before invoking any KMP matcher; if any preflight limit fails, no matcher runs and no prefix of observations is emitted. After successful preflight, run every KMP search, collecting all outcomes privately; publish the complete ordered observation list only after all searches complete. Any match-offset overflow or search failure blocks the whole companion with no observations; never mark a partial scan as `unique_moved_match` or otherwise imply uniqueness without scanning the full mapped representation.

This sequence bounds repeated-locator extraction and makes budget exhaustion deterministic and atomic: either every eligible exact scan completes or the companion returns one blocked result with no partial observations. `aggregate_scan_budget_exceeded` is added to ADR-051's closed companion blocked-reason vocabulary. The ADR-036 report and ADR-042 composition input remain byte-for-byte unchanged even when companion work blocks. No report reference paths are reopened, no caller paths or authority are added, and trusted permission, expected-revision, path, snapshot, and existing selected-byte/report budgets remain authoritative.

## Alternatives Considered

### Retain only per-file and aggregate snapshot limits

Rejected: these limit retained bytes, not repeated CPU scanning of one permitted representation across many references.

### Truncate observations when a per-reference search budget expires

Rejected: a prefix-only search cannot establish uniqueness or ambiguity and would produce partial output. Exhaustion blocks the companion atomically.

## Consequences

At most 512 MiB of counted linear scan/preprocessing work is authorized per invocation, including at most 256 MiB of distinct baseline snapshot traversal, at most 64 MiB of fragment extraction/pattern bytes, and the remaining budget for repeated current-representation searches. A complete selected evidence input may yield an ADR-036 COMPLETE report alongside a companion BLOCKED result when continuity preparation or search exhausts its own aggregate budget; the wrapper preserves that distinction without partial or false uniqueness claims. The limits are proposed engineering ceilings, not measured throughput guarantees.

## Test Contract

| Claim if accepted and implemented | Synthetic test |
|---|---|
| Repeated locators for one baseline snapshot trigger one bounded line-extraction pass, extracted pattern bytes stay under their limit, and repeated current scans count fully | `tests/test_evidence_binding.py::test_fragment_scan_budget_repeated_locator_preflight` |
| Checked/saturating `cap + 1` accumulation never wraps; arithmetic overflow and one-byte-over cases block before any matcher call and return no observations | `tests/test_evidence_binding.py::test_fragment_scan_budget_saturates_before_search` |
| Cost includes unique baseline traversal, extracted fragment bytes and each mapped current representation plus pattern preprocessing; repeated current representation references are charged repeatedly | `tests/test_evidence_binding.py::test_fragment_scan_budget_cost` |
| Work exactly at 512 MiB completes every observation; work above the cap blocks atomically without a prefix-search result or false unique outcome | `tests/test_evidence_binding.py::test_fragment_scan_budget_atomic_exhaustion` |
| Mixed mapped, unmapped, missing-current and empty-fragment references account for extraction and KMP work correctly; no partial outcome leaks on overflow | `tests/test_evidence_binding.py::test_fragment_scan_budget_mixed_references` |
| Blocked companion preserves ADR-036 report unchanged, ADR-042 receives its exact existing shape, and no reads beyond authorized snapshots occur | `tests/test_evidence_review.py::test_fragment_scan_budget_composed_blocked_result` |

These are proposed synthetic tests, not implemented tests or runtime guarantees.

## Rollback

This decision supersedes only ADR-051's stated scan budget/exhaustion clauses. No binding, report, snapshot, or consumer data migration/deletion is authorized.

## References

- Issue #128 and research checkpoint comment 6562209746.
- Accepted ADR-051 and exact review finding 4436839789.
- Accepted ADR-024, ADR-026, ADR-031, ADR-035, ADR-036, and ADR-042.
