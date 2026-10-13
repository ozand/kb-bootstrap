# ADR-030: Reuse source identity only through an explicit capture envelope

**Status**: Proposed
**Date**: 2026-10-13
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #125; Issues #124, #122; ADR-024, ADR-026, ADR-027

## Context

Issue #125 asks whether an existing source snapshot may be reused across studies without changing identity, inventing a new fetch time, or implying independent corroboration. Main `2a9161d` has two distinct existing representations: `RawCapture` Markdown and the accepted ADR-024 source-capture envelope. They are not interchangeable.

**Verified at base:** `capture_page.py` writes RawCapture fields `title`, `url`, `captured_at`, `captured_by`, `entity`, `fidelity` and a relative raw Markdown file; it does not write ADR-024 `source_id`, original revision, representation ID/digest, or original-retention fields. ADR-024 validation instead requires an explicit envelope, project root, corpus root, and complete selected retained paths; it validates exact selected bytes without scanning or fetching origins. ADR-026 requires whole-envelope validation before filtering a caller-supplied source ID and reports original and representation availability separately. ADR-027 covers Git retention of selected existing files but defines no copier, identity bridge, or sidecar. The existing cross-study reference example is test-local, not a persisted study contract.

**Reported by owner:** Issue #125's current `next_number()` plus ordinary writes can overwrite a colliding candidate, including a synthetic concurrent allocator race (comments 6154274412 and 6154279656). This proposal does not address new-file allocation or repair the writer. That is a separate #125 decision.

### Problem statement

A future reuse workflow needs a falsifiable boundary for when an existing capture carries an accepted stable source identity and when it is only a legacy file reference. Treating a RawCapture URL, title, path, or matching digest as the identity bridge would invent provenance and could conflate distinct origins.

## Decision

If separately accepted and implemented, a caller may claim identity-preserving source reuse only when it explicitly supplies an existing ADR-024 envelope and the complete caller-selected retained member set, then validates that envelope under ADR-024 before using ADR-026 lookup semantics. A `RawCapture` file without such an explicit accepted link remains a legacy repository-relative evidence reference; it is not promoted by inference to a verified ADR-024 source identity.

### What this IS

1. A reuse request explicitly identifies the owning repository root, existing ADR-024 metadata path, corpus root, requested `source_id`, and complete retained-member path selection. Paths are repository-relative/explicit under existing ADR-024/026 contracts; no folder discovery or origin dereference occurs.
2. Validate the complete supplied envelope and every declared retained member before filtering to the requested source, reusing accepted ADR-024 validation and ADR-026 caller-directed lookup behavior. Reuse declared `source_id`, representation IDs, original revision descriptor, representation digests, capture metadata and relative paths exactly as recorded. Existing `captured_at` stays the recorded capture time; absent time remains unknown and is not regenerated or reported as a new fetch.
3. A valid legacy RawCapture without an explicit ADR-024 linkage may still be referenced as a repository-relative file in study material, but the system reports that identity-preserving envelope reuse is unavailable. It does not derive `source_id` from URL, title, path, content digest, or another heuristic.
4. Reusing one validated source reference in multiple studies preserves shared identity; reuse alone is not independent corroboration and does not create a count, score, or truth claim.
5. Malformed metadata, incomplete/extra retained-member selection, digest mismatch, missing requested source or unavailable explicit envelope is reported distinctly as blocked/unavailable per existing validator/lookup results. No partial-member result silently upgrades an incomplete envelope.

### What this IS NOT

This decision defines no importer implementation, new public API, persisted study-reference schema, sidecar, global registry, RawCapture-to-envelope mapping format, copier, allocator, capture writer, attachment writer, automatic acquisition, source discovery, content-digest deduplication, fetch, origin access, automatic Git add/commit/push, consumer import, corroboration engine, or promotion. It does not make legacy RawCapture invalid as human-readable evidence. It does not solve #125's separately reported new-capture collision/overwrite hazard or assert hostile concurrent-filesystem safety.

### Success criteria

- With a supplied valid ADR-024 envelope and full selected retained bytes, repeated study references retain the same declared source/representation identity and capture timestamp.
- Without explicit accepted linkage from a legacy RawCapture to such an envelope, identity-reuse status is unavailable rather than inferred from URL/title/path/hash.
- Reuse does not update timestamps, modify existing RawCapture bytes, fetch an origin, create a sidecar, or claim corroboration.
- An incomplete or invalid retained-member set cannot produce a verified reuse reference.

## Consequences

### What gets easier

Studies can refer to the same explicitly validated source identity without treating a repeat appearance as a new acquisition or independent corroboration.

### What gets harder

Legacy RawCapture-only studies cannot claim ADR-024 identity continuity without an owner-supplied explicit linkage or envelope; they remain usable as ordinary relative file references. Callers must supply complete envelope context and retained paths.

### What does not change

ADR-024 remains the source-capture record contract; ADR-026 remains caller-directed whole-envelope lookup; ADR-027 remains selected-existing-file Git retention. No RawCapture format, writer, study schema, network behavior, collector, or consumer data changes under this proposal. Proposed ADR-028 and the broader W01 capability proposal remain independent and are not dependencies for this narrow decision.

## Alternatives Considered

- **Infer identity from URL or title:** rejected because these are descriptive capture fields, not a stable identity key; mutable/reused URLs and titles can refer to changed or distinct sources.
- **Infer identity from content digest:** rejected because equal bytes can arise from distinct origins (explicitly represented in the W03 fixture); digest equality proves byte equality only, not source identity.
- **Treat RawCapture path as an ADR-024 envelope:** rejected because its frontmatter lacks ADR-024 identity/revision/retention fields and cannot pass the accepted envelope validator without fabricating data.
- **Add a sidecar or global bridge registry now:** rejected because it introduces another persisted identity contract and migration/ownership rules beyond the bounded reuse gap.
- **Do nothing:** preserves legacy references but leaves identity-preserving reuse unavailable; this remains an honest state for captures without an explicit validated envelope.

## Test Contract

| Claim if implemented | Test | Currently |
|---|---|---|
| Explicit envelope reuse preserves source/representation IDs and capture time across two study references | `tests/test_source_capture_reuse.py::test_reuse_preserves_explicit_identity_and_capture_time` | not yet written |
| Legacy RawCapture without explicit envelope link is not promoted by URL/title/path/hash | `tests/test_source_capture_reuse.py::test_legacy_rawcapture_has_no_inferred_source_identity` | not yet written |
| Whole retained set and digest validation precede reuse status | `tests/test_source_capture_reuse.py::test_incomplete_or_mismatched_member_set_blocks_reuse` | not yet written |
| Reuse performs no discovery/fetch/write and leaves bytes unchanged | `tests/test_source_capture_reuse.py::test_reuse_is_read_only_and_non_dereferencing` | not yet written |
| Shared source reuse is not asserted as independent corroboration | `tests/test_source_capture_reuse.py::test_shared_identity_does_not_create_corroboration_claim` | not yet written |

## Rollback

Before acceptance, withdraw this Proposed ADR without runtime effect. If accepted and implemented later, revert only the reuse operation/reporting. Existing RawCapture and ADR-024 files remain untouched; no registry or migration is required by this decision.

## References

- Issue #125 and research checkpoint: https://github.com/ozand/kb-bootstrap/issues/125#issuecomment-6154349381
- Issue #124 W03 scope and revision fixtures
- `docs/fixtures/W03-source-capture-examples.md`
- ADR-024, ADR-026, ADR-027
- `kb_bootstrap/templates/skills/market-research/scripts/capture_page.py`
- `kb_bootstrap/templates/skills/market-research/references/formats.md`
- `tests/test_source_capture_validation.py`
- `tests/test_source_evidence_lookup.py`
