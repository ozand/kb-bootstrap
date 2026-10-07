# ADR-023: Bound source-capture records to explicit byte representations

**Status**: Proposed
**Date**: 2026-10-07
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #124; PR #142; ADR-006, ADR-010, ADR-014, ADR-015; Issues #90, #91, #122, #130

## Context

Issue #124 requires a versioned source/capture/conversion contract. PR #142 proposes an envelope with source identity, original revision, capture attempt, fidelity, representations, coordinates, and owner permission declarations; its fixtures distinguish duplicate bytes from distinct origins, partial extraction, manual summary, blocked capture, and zero-byte payloads. The W03 proposal remains unaccepted and no runtime validator exists.

The earlier six example/shape inconsistencies were corrected in PR #142 at `7ee38696c4f3a3f6c4c7ddd82d847837a4f64249`. Current review identifies remaining implementability choices around origin grammar, cross-field cardinality, original-vs-representation retention, coordinate scope, safe paths, and identifier scope. These are design observations, not runtime failures. ADR-010 already defines a conservative portable corpus-relative path and exact-byte SHA-256 manifest; it must remain unchanged.

### Problem statement

A future bounded local validator needs deterministic rules that distinguish unavailable originals, absent captures, zero-byte retained representations, partial/manual outputs, and unknown coordinates without fetching references, inventing metadata, or treating permission labels as authorization.

## Decision

This proposal recommends a descriptive v1 record for explicitly supplied local Markdown/text plus an owner-supplied origin descriptor. It does not authorize ingestion or implementation before owner acceptance.

### What this IS

1. Keep one versioned envelope and nested source/representation shape from PR #142. For v1, `source_id`, `representation_id`, converter `identity` and `version` are non-empty printable ASCII tokens matching `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`; `/`, `\\`, controls and whitespace are forbidden. `source_id` is unique within the envelope only; `representation_id` is unique within its source. Neither is a global registry key.
2. Keep `original_revision` distinct from each representation's SHA-256 over exact supplied bytes. If original bytes are unavailable, use an owner-supplied opaque revision or `unknown`; do not substitute a capture time, path, or representation digest. `original_retention` describes original bytes only; representation `raw_path` describes representation bytes only. `original_retention: retained` requires at least one retained representation whose exact-byte revision equals the known original SHA-256; if the original digest is unknown, retained-original status is not asserted. `reference-only` and `unknown` do not claim local original bytes.
3. Require `capture`, `fidelity`, and `representations`. Missing required fields are invalid. `representations: []` means known no output and is valid only for `method: blocked`, `fidelity.class: blocked`, with `reason` from `origin-unavailable|access-not-provided|conversion-failed|unsupported-input`. `exact`, `partial`, and `manual-summary` require at least one representation; `unknown` requires a recorded attempt and may have zero or more representations. A retained zero-byte file is one representation with the SHA-256 of empty bytes and a safe `raw_path`, not an empty array.
4. `fidelity.class` is one of `exact|partial|manual-summary|blocked|unknown`. `coverage` is a non-empty printable UTF-8 string of at most 128 bytes, or `unknown`; `losses` is a list of at most 64 non-empty printable UTF-8 strings, each at most 128 bytes. No C0/DEL controls are allowed. `exact` requires byte-identical original and representation digests; `partial` and `manual-summary` require at least one declared loss or a specific coverage statement. `unknown` requires a recorded attempt and `coverage: unknown`; `losses: []` means none declared, not proof of exactness. `manual-summary` is never extraction. Converted output requires converter identity/version; manual-summary may carry optional tool identity/version as descriptive lineage, but that is not authority or proof.
5. Treat `captured_at` and `original_revision.observed_at` as optional supplied offset-aware timestamps. Absence means unknown, never inferred. A blocked attempt may omit time.
6. Permit non-dereferenced origins only as bounded descriptors. Every reference is capped at 2048 UTF-8 bytes. A public URL's scheme is HTTP or HTTPS case-insensitively; a hostname is required; userinfo, query and fragments are forbidden to avoid credential-bearing or sensitive query payloads. Control characters and invalid URL syntax are forbidden. A relative/bundle reference uses ADR-010-safe normalized POSIX components; it may not be absolute or contain `.`/`..`, query or fragment. An opaque reference is a non-empty owner-supplied printable ASCII token matching `[A-Za-z0-9][A-Za-z0-9._:-]{0,255}` and is not a path or URI. An unavailable origin has `kind: unavailable`, `reason` from the closed set `no-safe-reference-supplied|source-unavailable|access-not-provided`, and no `reference` key. These syntax/size limits do not make a reference safe to dereference; the validator never opens, resolves or fetches any origin, and diagnostics never echo its value.
7. In v1, define coordinate units only as `byte`, `unicode-code-point`, and `line`; use half-open ranges, zero-based byte/code-point offsets and one-based line numbers. `byte` addresses the exact retained UTF-8 representation bytes; `unicode-code-point` addresses decoded Unicode scalar values; `line` addresses LF-delimited lines, excludes the LF terminator as a separate line, and a terminal LF creates no extra line. Ranges must have integer `0 <= start <= end` and stay within the known representation length when that representation is locally available; unavailable coordinate bases remain `unknown`. Local coordinates inherit their containing representation ID/revision. Original coordinates bind to `original_revision` or remain `unknown`. Unsupported page/slide/time/region coordinates remain unknown rather than being guessed.
8. Require every retained representation path to follow ADR-010's corpus-relative component/collision safety policy, including normalized POSIX form, portable component restrictions, and case-fold collision rejection within the envelope. This reuse does not require an ADR-010 manifest; when an explicit compatible manifest is supplied, a future validator may cross-check that each retained path exists in it with the same digest, but must not discover one implicitly. A manifest proves bytes/path inventory only, not origin, fidelity, permissions, or retention history.
9. Keep permission and retention values as owner-authored descriptive labels with no authorization effect. W01/ADR-015 does not require a capability registry for validating an explicitly supplied record; no capability conformance claim is emitted. W09/#130 still owns retention/access policy and any enforcement. #90 owns canonical resource forms; #91 owns Attested Computation/pure-OKF interpretation. These boundaries remain separate.
10. Enforce unique `source_id` values within one envelope and unique `representation_id` values within one source; duplicates block. IDs are opaque scoped labels, not globally allocated identifiers. No registry, deduplication or cross-envelope identity inference is introduced.
11. Bound the envelope to at most 1000 sources, 100 representations per source and 8 MiB UTF-8 serialized metadata. All limits are byte limits, not Unicode character counts. `source_id`, `representation_id`, converter identity/version and opaque IDs use the ASCII grammar above; `coverage` and each loss label are at most 128 UTF-8 bytes; the losses array has at most 64 entries. Oversized or malformed records block, never truncate; diagnostics identify only field/category and never echo origin values, IDs, labels or source content.
12. Limit v1 implementation scope to supplied local Markdown/text and metadata. No external discovery, network acquisition, PDF/OCR/ASR/model conversion, automatic publication, migration or consumer writes.

### What this IS NOT

This proposal is not an installed schema, validator, retention policy, authorization system, source-truth assertion, or permission to ingest private consumers. It does not amend ADR-010, #90, #91, ADR-014, or ADR-015, and does not resolve W01/W09 ownership decisions.

### Success criteria

Synthetic records validate deterministically for exact, partial, manual-summary, blocked, unknown, reference-only original, duplicate bytes/different origins, changed revisions, missing origin, and zero-byte representation. Malformed cross-field combinations, unsafe paths, unsupported versions, and duplicate identifiers block without mutation or dereference. Existing ADR-010 v1 remains byte-compatible.

## Consequences

### What gets easier

Readers can distinguish original revision, retained representation bytes, transformation, declared fidelity, coordinates, and owner labels without treating a digest or permission field as authority.

### What gets harder

A validator must enforce cross-field constraints, safe path parity with ADR-010, and a deliberately limited coordinate vocabulary. Unsupported media coordinates remain unknown until a later decision.

### What does not change

No runtime behavior, raw-manifest schema, canonical provenance schema, QMD/index behavior, model dependency, or consumer data changes before separate owner acceptance.

## Alternatives Considered

- Treat `representations: []` and missing `representations` as equivalent: rejected because known blocked/no-output differs from unspecified data.
- Infer completeness from byte length or matching media type: rejected because partial output can have any length.
- Treat permission labels as authorization: rejected because metadata possession does not establish owner authority.
- Dereference origin references during validation: rejected because it introduces network/local access and unstable results.
- Generalize coordinates to every media format in v1: rejected because page/slide/time/region bases require separate explicit conventions; unknown is safer than invented precision.
- Replace or embed ADR-010 raw-manifest: rejected because it already owns an independent exact-byte inventory contract.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| One nested versioned envelope and bounded source/representation identifiers | schema/duplicate-ID fixture matrix | not yet written |
| Cross-field capture/fidelity/representation cardinality is deterministic | valid/invalid combination fixtures including zero-byte and blocked | not yet written |
| Exact-byte digests and ADR-010 path policy are reused without schema changes | digest/path parity fixtures | not yet written |
| Coordinates use declared bases/half-open ranges or explicit unknown | byte/code-point/line/unknown fixture matrix | partial examples in PR #142; full tests not yet written |
| Origins are never dereferenced and permission labels do not authorize | no-network/no-open and authority-negative fixtures | not yet written |
| Existing sources remain unchanged | before/after file-byte snapshot | not yet written for a validator |

## Rollback

Withdraw this proposal if rejected. If accepted, implement in a separate scoped PR; do not migrate existing captures or modify ADR-010. Any later coordinate/media expansion requires a follow-up decision.

## References

- Issue #124 and research record https://github.com/ozand/kb-bootstrap/issues/124#issuecomment-6033889044
- PR #142 at `7ee38696c4f3a3f6c4c7ddd82d847837a4f64249`
- ADR-010, ADR-006, ADR-014, ADR-015; Issues #90, #91, #122, #130
