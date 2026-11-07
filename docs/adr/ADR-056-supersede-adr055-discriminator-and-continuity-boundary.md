# ADR-056: Refine ADR-055 discriminator types and continuity scope

**Status**: Accepted
**Date**: 2026-11-07
**Authors**: Pi coding agent
**Supersedes**: ADR-055 (only its discriminator type-classification and diagnostic/continuity combination clauses)
**Related**: Issue #128; ADR-031, ADR-036, ADR-042, ADR-051, ADR-052, ADR-055

Technical acceptance: accepted under the owner's standing delegation recorded in [AGENTS.md](../../AGENTS.md), authorized by Issue #223, after independent exact-head review 15ff passed commit `ed1bbda76d50c87c0c1c278a40f430d0ffe04f7e`. Acceptance applies only to ADR-056's two named refinements. No runtime implementation, issue completion, rollout, or consumer migration is claimed or authorized by this record.

## Context

Accepted ADR-055 defines an opt-in malformed-versus-unsupported diagnostic proposal while preserving ADR-036's closed v1 resolver report. Exact-head review of PR #276 found two narrow ambiguities: wrong-typed JSON binding discriminators could be labeled unsupported, and the wording about callers needing both diagnostics and continuity did not state whether both features can be used together. This ADR proposes only those corrections. The checkpoint was recorded before drafting in [Issue #128 comment 6701285796](https://github.com/ozand/kb-bootstrap/issues/128#issuecomment-6701285796).

## Decision

If accepted, replace only the corresponding ADR-055 rules as follows; all other ADR-055 provisions remain unchanged.

### Binding discriminator classification

After decoding UTF-8 JSON, rejecting duplicate keys, requiring a top-level object, and requiring exactly the existing v1 top-level key set, validate discriminator types before comparing supported values:

1. `schema` must be a string. `version` must have exact integer type (`type(version) is int`); JSON booleans are not integers for this contract and are malformed.
2. A missing/wrong-typed `schema` or `version` is `malformed_input`.
3. Only with both discriminator fields type-correct, a schema string other than `kb-bootstrap.evidence-bindings` or an integer version other than `1` is `unsupported_schema`.
4. For the recognized pair, validate the existing v1 nested schema. Any invalid/missing/extra nested fields or values are malformed under ADR-055.

This is classification ordering only. It adds no JSON/YAML grammar, parser capability, fallback, version probing, or accepted input. The source-capture YAML outer discriminator follows the already specified ADR-055 type-correct ordering; this ADR does not change it.

### Diagnostic and continuity call boundary

Within this increment, the diagnostic entry point and `resolve_evidence_binding_with_fragment_continuity` are alternative entry points, not composable features. A caller may invoke either one for a given resolver operation. The caller must not invoke both to simulate combined output: that would perform two resolver operations and is outside this contract. ADR-055's diagnostic entry point does not add diagnostic data to the continuity wrapper; the continuity entry point does not add continuity observations to the diagnostic wrapper. A caller needing both has no supported one-call operation under ADR-055/056 and must use one feature or neither until a separately reviewed architecture decision explicitly defines a combined single-operation API.

The ADR-036 resolver report and ADR-042 composer remain unchanged. No wrapper/API, signature, report shape, callback, path, read, permission or infrastructure is added by this clarification. Existing continuity behavior and ADR-051/052 companion contracts remain unchanged.

## Consequences

Malformed versus unsupported classification has a deterministic type-first boundary for binding JSON, including explicit rejection of boolean versions. The feature-combination boundary is also explicit: no double-read workaround and no implicit combined API. ADR-055 remains accepted in all other respects; ADR-056 remains Proposed until independent review and delegated acceptance. Neither ADR authorizes runtime implementation by itself; implementation requires its separate task scope and review.

## Alternatives Considered

### Coerce discriminator types

Rejected because coercion would make malformed inputs ambiguous and could treat JSON booleans as integer versions.

### Add a combined diagnostic-and-continuity API now

Rejected because this correction stage only resolves review ambiguity; combining two existing operation contracts introduces a new API and integration scope not required to resolve either P2 finding.

### Call both current entry points separately

Rejected because it duplicates the resolver operation and conflicts with the no-double-call/read constraint.

## Test Contract

| Claim if accepted and implemented | Synthetic case |
|---|---|
| For exact outer binding shape, absent or non-string schema and absent/non-integer version (including `true`/`false`) classify as malformed; correctly typed unknown schema/version classify as unsupported | Binding discriminator type/order matrix |
| Recognized v1 discriminator continues through existing nested validation; malformed nested content is not unsupported | Valid-v1 and malformed-nested controls |
| YAML envelope type/order and all ADR-055 fixed reason/sanitization rules remain unchanged | YAML regression matrix |
| The diagnostic API and continuity API are mutually alternative for this scope; neither silently calls the other and no two-call combined recipe is documented | API-boundary contract test/documentation check |
| Existing resolver v1 report and ADR-042 composer contracts remain unchanged; no wrapper or wire format is added | V1 report/composer compatibility controls |

These are future synthetic test requirements, not implementation or runtime test claims.

## Rollback

Before acceptance, withdraw this proposal. If accepted, it supersedes only the named ADR-055 clauses; the rest of ADR-055 remains Accepted. No implementation, consumer migration, issue completion, or rollout is implied.

## References

- Issue #128 checkpoint comment 6701285796.
- Accepted ADR-055 and PR #276 review comments 4499672677 and 4499672700.
