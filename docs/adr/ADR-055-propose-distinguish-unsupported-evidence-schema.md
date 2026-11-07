# ADR-055: Propose distinct malformed and unsupported evidence schema outcomes

**Status**: Superseded by ADR-056
**Date**: 2026-11-07
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #128; ADR-024, ADR-026, ADR-031, ADR-036, ADR-042, ADR-051, ADR-052

Technical acceptance: accepted under the owner's standing delegation recorded in [AGENTS.md](../../AGENTS.md), authorized by Issue #223, after independent exact-head review a453 passed commit `3369219d0fff52eee8cc9f668b6114346947b32d`. Acceptance applies only to this ADR-055 decision. No runtime implementation, issue completion, rollout, or consumer migration is claimed or authorized by this record.

## Context

Issue #128 requires malformed, unsupported, inaccessible and missing evidence to remain distinguishable. Accepted ADR-031/036 currently require malformed or unsupported binding/envelope inputs to block; ADR-036 defines closed `BLOCKED.reason` values and ADR-042 accepts only those values. The resolver currently collapses well-formed unsupported schema versions into the same blocked reason as malformed records. This proposal is only a diagnostic classification design; it changes no runtime behavior until separately authorized implementation follows acceptance and review.

The pre-edit research checkpoint is [Issue #128 comment 6700824266](https://github.com/ozand/kb-bootstrap/issues/128#issuecomment-6700824266). It records the exact source collapse, current-main baseline, synthetic control attempted and missing PyYAML dependency. No consumer data or inference was used.

## Decision

If accepted and separately authorized for implementation, add a closed diagnostic distinction at input validation boundaries: `malformed_input` for structurally invalid input, and `unsupported_schema` only for an input that is structurally well-formed under the existing outer grammar but declares an unrecognized schema discriminator or version. Keep inaccessible/unsafe as its existing separate diagnostic. Do not add malformed or unsupported as per-reference states. Missing remains the existing valid-input outcome only; parse, structure, unsupported version and access failures are never deletion evidence.

Recognition is deliberately exact and bounded. The only supported binding pair remains `schema="kb-bootstrap.evidence-bindings"`, integer `version=1`; the only supported source-capture envelope pair remains the exact existing schema constant and integer `version=1`. For binding JSON, first require valid UTF-8 JSON, a top-level object, unique keys, and exactly the existing v1 top-level key set before classifying a discriminator/version mismatch as unsupported. For a recognized binding discriminator/version, validate all existing nested fields and reject unknown fields, bad types, invalid identifiers, and invalid values as malformed. No alternative version syntax, aliases, open-ended keys, new parser features, or recursive version probing are added.

For source-capture YAML, only the existing top-level `schema`, `version`, and `sources` envelope shape is recognized. Invalid UTF-8/YAML, duplicate keys, non-mapping roots, missing/extra envelope keys, or an invalid version type are malformed. When the exact envelope keys and type-correct schema/version fields are present but the schema string or integer version is unrecognized, classify unsupported before validating v1-only nested `sources`. Recognized v1 then follows the existing complete ADR-024 validation unchanged. This classification order is not a permissive parse: no unsupported record is processed or partially validated for evidence.

Errors expose only one fixed closed reason code; never include paths, input fragments, parser messages, OS text, identifiers or user-controlled values. Existing permission denials remain trusted exceptions outside report serialization; existing unsafe/inaccessible inputs retain the fixed inaccessible reason. Boundaries and byte/count caps remain unchanged. Do not change what is read, path policy, fallback/default behavior, accepted schema, or envelope validation capabilities.

### Backward-compatible API and rollout

Do not add either diagnostic code to ADR-036's `BLOCKED.reason` enum and do not change `resolve_evidence_binding` or `compose_evidence_review_worklist`. Those remain the v1 API and closed wire contract. Use one separately named, explicitly opt-in API with the same keyword-only input parameters:

```python
resolve_evidence_binding_with_input_diagnostic(**same_resolver_inputs) -> dict
```

It returns exactly `{"resolver_report": <existing ADR-036 v1 report>, "input_diagnostic": <diagnostic>}`. `resolver_report` is byte-for-byte/structurally the result the existing resolver would return for the same inputs: existing BLOCKED codes remain `invalid_binding` or `invalid_or_incomplete_envelope` as applicable, and COMPLETE is unchanged. On a complete report, diagnostic is exactly `{"status":"NOT_APPLICABLE"}`. On a BLOCKED report caused by binding/envelope decoding or validation, diagnostic is exactly `{"status":"CLASSIFIED","reason":"malformed_input"}` or `{"status":"CLASSIFIED","reason":"unsupported_schema"}`. For any other block (including unsafe/inaccessible, baseline mismatch, limit, serialization), it is exactly `{"status":"NOT_CLASSIFIED","reason":<the existing v1 blocked reason>}`. Trusted permission denials remain exceptions and produce no wrapper. The sidecar has no user-controlled fields and is not itself an ADR-036 report.

Implement the opt-in path as one resolver operation: the same existing validation steps set a private per-call diagnostic classification alongside their existing v1 block reason. Do not parse/read a second time, call the resolver twice, or reopen report paths. The old entry point continues to return its exact old report. This requires no ADR-036 or ADR-042 update because the v1 report and every value passed to the composer remain unchanged.

Deterministic direct use: a caller opting into the new entry point inspects `input_diagnostic`; existing callers continue using `resolve_evidence_binding`. Deterministic composition: pass only `result["resolver_report"]` from the opt-in API to the existing `compose_evidence_review_worklist`, with the same explicit lineage arguments; its result and accepted validation are unchanged. Existing `resolve_evidence_binding_with_fragment_continuity` stays untouched and returns its accepted wrapper; callers needing both features may pass its unchanged `resolver_report` to the composer and use this diagnostic entry point separately only if the host provides the same explicit authorization and inputs in one authorized operation. Do not call the resolver twice to join outputs. This ADR does not add diagnostic support to the continuity wrapper; that would require separate scope and review.

Rollout is consumer-first without a coordinated deployment assumption: release readers of the new separately named API/sidecar first (or keep it unavailable); old consumers continue calling the existing function and receive only the v1 contract. Then enable the new entry point only for callers that explicitly opt in and understand the wrapper. The existing composer never receives the wrapper; it receives only the unchanged nested v1 report. A legacy consumer may ignore the new API entirely and needs no update. There is no global default/API alias switch, no v1-to-new conversion, and no mixed-version negotiation. If a caller cannot preserve this explicit selection, it must stay on the existing API. This is a complete additive path and does not depend on an atomic fleet migration or future ADR-036/042 changes.

## Consequences

Operators can distinguish malformed input from a valid-but-unsupported schema through the proposed opt-in diagnostic once separately authorized implementation is delivered. Unsupported input still blocks; the resolver does not guess, downgrade, or infer. Until then, existing behavior remains unchanged. ADR-055 is Accepted as an architecture decision; its test contract is future implementation evidence, not evidence that runtime behavior exists.

## Alternatives Considered

### Return malformed for every non-v1 record

Rejected because it preserves the current diagnostic collapse and does not satisfy #128's operator distinction.

### Parse unsupported records permissively or fall back to v1

Rejected because unknown fields/versions could be misinterpreted and safety/meaning cannot be inferred.

### Add per-reference malformed/unsupported states

Rejected by accepted ADR-031: invalid invocation inputs block as a whole and do not produce partial observations.

## Test Contract

| Claim if accepted and implemented | Synthetic case |
|---|---|
| Exact recognized v1 binding and envelope retain existing valid outcomes | Valid binding/envelope direct-resolver control |
| Malformed JSON/YAML, duplicate keys, wrong shape/type, missing fields and unknown fields produce only `malformed_input` | Malformed binding/envelope matrix |
| Exact outer shape with a type-correct but unsupported discriminator/version yields `unsupported_schema`, without parsing or using payload as evidence | Unsupported binding/envelope matrix |
| Unreadable/unsafe paths retain the inaccessible reason; missing mapping/declaration remains missing and is not reclassified | Inaccessible and missing/deleted controls |
| Fixed diagnostic contains no caller-controlled data; v1 report is exactly the old resolver result and no partial report is returned | Sanitization and v1 parity controls |
| Existing resolver and strict composer signatures/output remain unchanged; opt-in wrapper is not accepted as an ADR-036 report | Legacy API and rejection-boundary controls |
| Opt-in direct call classifies malformed versus unsupported while preserving the corresponding legacy BLOCKED reason in `resolver_report`; complete and non-input blocks use exact sidecar shapes | Direct diagnostic matrix |
| One operation performs one set of reads; no second resolver call or report-path reopen is used | Single-operation/read-audit control |
| Passing only the opt-in result's nested `resolver_report` to ADR-042 yields the same composition as passing the legacy resolver result; continuity wrapper remains byte-for-byte unchanged | Direct and composed compatibility matrix |
| Legacy callers need no upgrade, new callers select the opt-in name explicitly, and no global default/alias or mixed-version negotiation is introduced | Legacy/new caller coexistence control |

These are proposed synthetic test requirements, not implemented tests or runtime guarantees. Include a compatible consumer and a legacy consumer case; verify legacy producers remain within old reason enums until rollout permits new values.

## Rollback

Before acceptance, withdraw this proposal. Acceptance alone authorizes no implementation. If implemented, removing the opt-in entry point must leave the existing v1 function, report, composer, and continuity wrapper unchanged. It must not turn malformed, unsupported, inaccessible or missing into one another. No migration of existing consumers or persisted data is required or authorized.

## References

- Issue #128 and checkpoint comment 6700824266.
- Accepted ADR-031/036/042/051/052 and `kb_bootstrap/evidence_binding.py`, `kb_bootstrap/source_capture_validation.py`.
