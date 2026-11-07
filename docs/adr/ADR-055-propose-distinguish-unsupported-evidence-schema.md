# ADR-055: Propose distinct malformed and unsupported evidence schema outcomes

**Status**: Proposed
**Date**: 2026-11-07
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #128; ADR-024, ADR-026, ADR-031, ADR-036, ADR-042, ADR-051, ADR-052

## Context

Issue #128 requires malformed, unsupported, inaccessible and missing evidence to remain distinguishable. Accepted ADR-031/036 currently require malformed or unsupported binding/envelope inputs to block; ADR-036 defines closed `BLOCKED.reason` values and ADR-042 accepts only those values. The resolver currently collapses well-formed unsupported schema versions into the same blocked reason as malformed records. This proposal is only a diagnostic classification design; it changes no runtime behavior until separately authorized implementation follows acceptance and review.

The pre-edit research checkpoint is [Issue #128 comment 6700824266](https://github.com/ozand/kb-bootstrap/issues/128#issuecomment-6700824266). It records the exact source collapse, current-main baseline, synthetic control attempted and missing PyYAML dependency. No consumer data or inference was used.

## Decision

If accepted and separately authorized for implementation, add a closed diagnostic distinction at input validation boundaries: `malformed_input` for structurally invalid input, and `unsupported_schema` only for an input that is structurally well-formed under the existing outer grammar but declares an unrecognized schema discriminator or version. Keep inaccessible/unsafe as its existing separate diagnostic. Do not add malformed or unsupported as per-reference states. Missing remains the existing valid-input outcome only; parse, structure, unsupported version and access failures are never deletion evidence.

Recognition is deliberately exact and bounded. The only supported binding pair remains `schema="kb-bootstrap.evidence-bindings"`, integer `version=1`; the only supported source-capture envelope pair remains the exact existing schema constant and integer `version=1`. For binding JSON, first require valid UTF-8 JSON, a top-level object, unique keys, and exactly the existing v1 top-level key set before classifying a discriminator/version mismatch as unsupported. For a recognized binding discriminator/version, validate all existing nested fields and reject unknown fields, bad types, invalid identifiers, and invalid values as malformed. No alternative version syntax, aliases, open-ended keys, new parser features, or recursive version probing are added.

For source-capture YAML, only the existing top-level `schema`, `version`, and `sources` envelope shape is recognized. Invalid UTF-8/YAML, duplicate keys, non-mapping roots, missing/extra envelope keys, or an invalid version type are malformed. When the exact envelope keys and type-correct schema/version fields are present but the schema string or integer version is unrecognized, classify unsupported before validating v1-only nested `sources`. Recognized v1 then follows the existing complete ADR-024 validation unchanged. This classification order is not a permissive parse: no unsupported record is processed or partially validated for evidence.

Errors expose only one fixed closed reason code; never include paths, input fragments, parser messages, OS text, identifiers or user-controlled values. Existing permission denials remain trusted exceptions outside report serialization; existing unsafe/inaccessible inputs retain the fixed inaccessible reason. Boundaries and byte/count caps remain unchanged. Do not change what is read, path policy, fallback/default behavior, accepted schema, or envelope validation capabilities.

### Compatibility and rollout

This distinction adds public blocked-reason values. ADR-036's current blocked enum and ADR-042's strict composer reject unknown values, so this is **not** asserted to be backward-compatible. An implementation must not silently emit the new values under the old closed contract. The proposed staged contract is: first, a separately reviewed compatibility update to ADR-036 and ADR-042 (or a new explicitly versioned diagnostic/report contract) defines the two new reason values and reader behavior; keep old v1 producers emitting only old values until updated consumers are released. Then implement producer classification and composer acceptance together under the accepted compatibility decision. Existing standalone resolver consumers and ADR-051/052 wrapper consumers must continue to receive the original resolver report unchanged; the companion's blocked reason vocabulary remains independent. No mixed deployment may cause an old composer to receive an unrecognized report. If a versioned report envelope is required by review, v1 wire shape remains unchanged and a new version is opt-in; do not assume all consumers upgrade atomically. No consumer migration, fallback mapping, or reason collapse is authorized by this proposal.

## Consequences

Operators can tell malformed input from a valid-but-unsupported schema only after the compatibility contract is accepted and deployed. Unsupported input still blocks; the resolver does not guess, downgrade, or infer. Until compatible consumers are available, current behavior remains unchanged.

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
| Fixed diagnostics contain no caller-controlled data; no partial report is returned | Sanitization/leakage controls |
| Direct resolver reports, continuity wrapper's embedded ADR-036 report, and ADR-042 composition preserve exact accepted shapes across rollout; old/new report consumers are tested per staged compatibility contract | Direct and composed compatibility matrix |

These are proposed synthetic test requirements, not implemented tests or runtime guarantees. Include a compatible consumer and a legacy consumer case; verify legacy producers remain within old reason enums until rollout permits new values.

## Rollback

Before acceptance, withdraw this proposal. Acceptance alone authorizes no implementation. If implemented under a later accepted compatibility decision, rollback must preserve v1 behavior and must not turn malformed, unsupported, inaccessible or missing into one another; retain old consumer compatibility until its explicitly reviewed migration.

## References

- Issue #128 and checkpoint comment 6700824266.
- Accepted ADR-031/036/042/051/052 and `kb_bootstrap/evidence_binding.py`, `kb_bootstrap/source_capture_validation.py`.
