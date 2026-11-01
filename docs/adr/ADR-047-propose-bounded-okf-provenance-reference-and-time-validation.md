# ADR-047: Propose bounded OKF provenance reference and time validation

**Status**: Proposed — pending independent review and owner decision
**Date**: 2026-11-04
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #90; ADR-003, ADR-006; Issues #88, #92; [OKF v0.2 specification](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)

## Context

Issue #90 requests bounded validation for OKF provenance reference forms, actor conventions, `sources[].last_modified`, and shared/per-source `usage_window` timestamps. The current [ADR-006 profile](../CANONICAL_PROVENANCE_FRESHNESS_PROFILE.md) intentionally rejects percent escapes, leading-slash bundle-root paths, dot segments, and scope descriptors; it does not validate `last_modified` or `usage_window`, and its actor rule is narrower than OKF's producer/version, `human:`, and `process:` convention. The official OKF v0.2 specification defines source-resource classes and usage-window placement, but does not define a syntax for scope descriptors or a filesystem resolution/security implementation. This proposal defines only the deterministic lexical validation needed for #90; it does not turn metadata into authority to access resources.

## Decision proposed

If accepted, extend only the `kb-bootstrap validate` provenance/freshness report. These rules are additive to ADR-006 and apply to recognized provenance fields; all unrecognized frontmatter and nested extension keys remain accepted and untouched as required by ADR-003. Missing optional fields remain valid/unknown. Invalid recognized fields fail the provenance section with existing sanitized file-relative path and field-category diagnostics. No accepted ADR is rewritten.

### `sources[].resource`: lexical classes, no resolution

Keep ADR-006's currently accepted public HTTP(S) URLs and plain relative references valid. Additionally accept:

1. **Bundle-root reference**: `/` followed by one or more non-empty path segments, interpreted only as a logical name relative to a hypothetical bundle root.
2. **Relative reference**: a sequence of non-empty segments, optionally beginning with `./`; parent segments (`..`) are not allowed. A single leading `./` is removed for comparison only; authored text is never rewritten.
3. **Scope descriptor**: `scope:` followed by 1–256 printable, non-whitespace-leading/trailing Unicode characters, with no C0/DEL controls. The payload is opaque descriptive text, not a path, selector, executable query, or resolvable identifier.
4. **Public URL**: existing ADR-006 HTTP(S) form: hostname required; no userinfo; valid port; no controls, backslashes, or dot/traversal URL path segments.

For path references, path segments use ASCII `[A-Za-z0-9][A-Za-z0-9._@+-]*` after percent-decoding each segment exactly once as strict UTF-8. Reject malformed escapes, invalid UTF-8, decoded separators (`/` or `\\`), controls/DEL, empty segments, `.` or `..` segments except the single leading `./`, and any segment not matching the ASCII allowlist. Reject query and fragment delimiters in path references, backslashes, drive/UNC/absolute local paths, credentials, and unsupported URI schemes. Percent-encoding is accepted only when its one-time decoded segment passes this grammar; do not recursively decode or canonicalize URL hosts/paths. Reject reserved URI schemes other than HTTP(S) rather than guessing whether a colon-prefixed value is a scope; scopes must use the explicit `scope:` prefix. The new scope form is not reinterpreted as an actor or URI.

These are lexical classes only. The validator MUST NOT dereference, stat, open, fetch, resolve symlinks for, test existence of, or infer identity from any resource. In particular it does not prove that a bundle-relative path belongs to a bundle, that a URL is public/reachable, or that a scope is meaningful. No filesystem path is derived from metadata.

### Actors

Apply one bounded convention to `generated.by`, `verified[].by`, and `sources[].author`: a non-empty sanitized string of at most 256 characters, with no C0/DEL controls or surrounding whitespace, in exactly one of these forms:

- agent: `<producer>` or `<producer>/<version>`;
- human: `human:<id>`;
- automated process: `process:<id>`.

`<producer>`, `<version>`, and `<id>` are non-empty opaque identifiers containing only ASCII letters, digits, `.`, `_`, `@`, `+`, and `-`. The components are not authenticated identities. For compatibility, an unqualified producer identifier remains valid; retain all currently accepted values that meet this convention and the existing bound/safety rules. Do not accept URL, path, drive/UNC, credential-bearing, or unsupported-scheme values as actors. Actor values must never appear in diagnostics, including dynamic error text.

### Declared source time and usage windows

`last_modified` is optional on each source entry. When present it must be a string matching ADR-006's existing strict offset-aware timestamp grammar and 128-character bound. It is a producer-declared metadata value, not an observed server fact, and does not affect `stale_after` freshness, trust, or verification.

`usage_window` is optional at the concept level and optional on each source entry. Each present value must be a mapping containing required `from` and `to` values, both valid ADR-006 offset-aware timestamps; unknown additional keys remain accepted. Missing `from`/`to`, explicit null, non-mappings, and malformed/naive timestamps are invalid. A source-level window takes precedence for describing that source's usage period; otherwise the concept-level window applies. A present window with no `usage_count` remains valid metadata. When both bounds are valid, require `from <= to`; equality denotes a single-instant window. The closed bounds describe the declared observation period only and do not drive freshness. No current clock is consulted.

`generated.at`, `verified[].at`, and `stale_after` retain exactly their ADR-006 meanings. `stale_after` remains the only freshness cutoff and is classified solely against explicit `--now`; `last_modified` and usage-window bounds do not change freshness or lifecycle status. No status values or report exit behavior change.

### Reports, preservation, and compatibility

Keep the existing deterministic report format and error categories; do not add a wire format, new counters, or resource/actor/timestamp values. Use existing concept-relative POSIX paths and stable field categories only. Unknown metadata at every level remains accepted and preserved. Validation stays read-only: no migration, repair, normalization write, metadata synthesis, raw capture, inference, network/local resource access, retention change, or canonical graph mutation. ADR-006 remains authoritative except for the specific resource and actor acceptance rules above and the additional `last_modified` / `usage_window` validation rules; all other ADR-006 clauses remain in force.

## Alternatives considered

- **Resolve bundle paths or fetch URLs to establish identity/existence** — rejected: violates #90 safety, introduces local/network access, and confuses a logical reference with verified evidence.
- **Treat every non-URL string as a scope** — rejected: ambiguous, breaks safe rejection of unsupported schemes, and hides path mistakes. Require the explicit `scope:` prefix.
- **Permit parent traversal and normalize against the concept directory** — rejected: would introduce scope-dependent filesystem interpretation. Only bundle-root and non-traversing relative logical references are accepted.
- **Use `last_modified` or usage-window bounds to classify freshness** — rejected: OKF identifies these as source credibility/usage signals, while ADR-006 defines freshness from `stale_after` and explicit time; no recency policy is requested by #90.
- **Make fields required or rewrite legacy metadata** — rejected: optionality and read-only preservation are existing compatibility contracts.

## Consequences

Existing valid provenance remains valid; only the listed logical reference forms and recognized optional timestamps gain validation. Malformed recognized `last_modified`/`usage_window` fields that were previously ignored will now fail the separate provenance section. A passing check establishes bounded syntax only, not truth, independence, actor identity, source existence, reachability, trust, or currentness. The change requires focused synthetic fixture tests before runtime implementation; Issue #92 migration guidance is pending/maintained separately and is not delivered by this ADR.

## Proposed test contract

- Accept and reject every resource class and unsafe class; exercise percent encoding, one-time decoding, traversal/control/separator rejection, scopes, and preservation of existing valid HTTP(S)/relative values.
- Accept agent/version, `human:`, and `process:` actor forms; reject malformed/unsafe forms without echoing values.
- Accept valid `last_modified`, shared and source-level windows, offsets, source override, equal bounds, and absent metadata; reject malformed, naive, missing, null, or reversed bounds.
- Repeat reports with the same explicit `--now` and assert byte-identical output; assert `last_modified` and windows do not affect freshness.
- Spy on network access and metadata-derived local opens/existence checks; assert none occur. Use canary metadata and byte snapshots to prove diagnostics do not leak values and source bytes remain unchanged.
- Preserve legacy CLI/provenance/profile/graph behavior and unknown frontmatter; no unrelated suite expansion.

## Review and decision gate

This is a Proposed ADR, not owner approval, runtime authorization, routine GO, or an assertion of implementation. Independent review and an explicit owner decision are required before any runtime change. Acceptance of this proposal would authorize only the bounded semantics described here; implementation and migration remain separately reviewable work.
