# ADR-024: Require every exact representation to match the original

**Status**: Proposed
**Date**: 2026-10-07
**Authors**: Pi coding agent
**Supersedes**: ADR-023
**Related**: Issue #124; ADR-010, ADR-023

## Context

Post-acceptance review of ADR-023 identified two ambiguities before validator implementation: source-level `exact` permits multiple representations but does not define the digest comparison quantifier; the zero-byte fixture uses `application/octet-stream` while v1 is scoped to supplied Markdown/text. The owner-accepted ADR-023 superseded the earlier Proposed W03/PR #142 design, but these two points require a follow-on decision. See review comments on PR #172 and owner decision request in Issue #124. No validator is implemented.

### Problem statement

A validator must decide deterministically whether an `exact` source with multiple representations is valid, and fixtures must remain within the declared v1 media scope.

## Decision

This proposal supersedes ADR-023 only if accepted. Until then ADR-023 remains the recorded accepted decision, but validator implementation is paused on Issue #124.

### What this IS

1. `fidelity.class: exact` requires a known original SHA-256 equal to the SHA-256 of **every** retained representation. No primary-representation exception is defined. A transformed derivative cannot be included under source-level `exact`.
2. Keep v1 input and representation media scope to supplied UTF-8 Markdown/text. Represent the zero-byte control as `text/plain`, an empty `.txt` representation, zero bytes, and the SHA-256 of empty bytes. This does not authorize arbitrary binary representations.
3. Keep the original ADR-023 cross-field constraints, limits, non-dereference boundary, and ADR-010 path policy unless explicitly changed here; this proposal changes only the exact-representation rule and the zero-byte fixture’s media declaration.

### What this IS NOT

This proposal does not implement a schema or validator, add CLI/API behavior, authorize ingestion, conversion, publication, migration, consumer writes, network access, or optional models. It does not change ADR-010 or ownership assigned to #90, #91, W01/ADR-015, or W09/#130.

### Success criteria

- A multi-representation `exact` record passes only when every representation digest equals the known original digest.
- A record with one matching and one differing representation fails as `exact`.
- The synthetic complete-envelope fixture contains one `exact` source with two matching representation digests.
- The zero-byte fixture is valid UTF-8 text with zero bytes and the unchanged empty-byte SHA-256; no binary media scope is implied.

## Consequences

### What gets easier

Exactness has one deterministic interpretation across records with any allowed representation count.

### What gets harder

A source with an exact retained copy plus a transformed derivative cannot label the whole record `exact`; it needs a representation/fidelity arrangement permitted by the accepted contract.

### What does not change

All other ADR-023 v1 bounds and safety boundaries remain unchanged. No runtime behavior exists or is changed by this proposal.

## Alternatives Considered

- Require at least one representation to match: rejected because it allows a transformed derivative to coexist with source-level `exact` and leaves the meaning of the class ambiguous.
- Add a primary-representation identifier: rejected for this narrow correction because it adds a new persisted field and designation rule.
- Expand v1 to arbitrary binary: rejected because it broadens the accepted media contract beyond the supplied Markdown/text scope.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| Every exact representation matches original digest | Validator fixtures: all-match and mixed-match multi-representation cases | Not yet written; validator not implemented |
| Empty text fixture remains zero bytes with empty SHA-256 | Fixture byte-count/digest assertion | Proposed; not yet written |
| Other ADR-023 bounds remain unchanged | Existing contract fixture matrix plus regression comparison | Not yet written |

## Rollback

If rejected, withdraw this proposal and retain ADR-023 unchanged; do not implement validator behavior by guessing. If accepted, ADR-023 is marked `Superseded by ADR-024` with no other edits, and implementation remains a separately reviewed increment.

## References

- Issue #124, owner clarification request: https://github.com/ozand/kb-bootstrap/issues/124#issuecomment-6040634497
- PR #172 review findings on exact fidelity and zero-byte media scope
- ADR-023: Bound source-capture records to explicit byte representations
