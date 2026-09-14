# ADR-006: Validate canonical provenance and classify freshness with explicit time

**Status**: Accepted — Implemented
**Date**: 2026-09-14
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issue #62; ADR-003 (minimal OKF v0.2 canonical profile); ADR-005 (deterministic canonical graph export)

## Context

Issue #62 extends the canonical OKF v0.2 profile with bounded semantics for `generated`, `verified`, `sources`, `status`, and `stale_after`. It requires deterministic outcomes for absent, unknown, fresh, stale, and malformed states while preserving source/unknown metadata and introducing no migration, repair, source retrieval, or synchronization.

ADR-003 already defines canonical traversal/frontmatter parsing and validates `status` as `draft`, `stable`, or `deprecated`. It accepts unknown optional families without semantic guarantees. The public OKF v0.2 specification findings recorded during Issue #59 establish the remaining field shapes:

- `generated` is optional; when present it has required `by` and optional `at`;
- `verified` is optional and may be one mapping or a list of events, each with `by` and `at`;
- `sources` is optional and each entry requires `resource`;
- `stale_after` is optional and denotes an absolute instant;
- all timestamp-valued keys use ISO 8601 date-times with explicit UTC offsets.

Using the current wall clock would make reports change without source changes and would prevent byte-identical repeated validation. Fetching source URLs or interpreting actor identity would expand trust and network boundaries beyond the Issue.

## Decision

Extend the existing `kb-bootstrap validate` command with a separately labelled canonical provenance/freshness report. Add an optional deterministic comparison input:

```text
kb-bootstrap validate \
  --dir kb \
  --project-root . \
  [--now 2026-09-14T12:00:00Z]
```

No separate validation command is added. Core profile, provenance/freshness, graph integrity, and QMD declarations remain separate report sections and contribute independently to the overall exit code.

### Timestamp grammar

Every timestamp validated by this profile must match:

```text
YYYY-MM-DDTHH:MM:SS[.fraction](Z|+HH:MM|-HH:MM)
```

Timestamp strings are bounded to 128 characters. Parsing additionally rejects invalid calendar dates, times, and offset ranges. Numeric offsets are bounded to `-14:00` through `+14:00`; minutes must be below 60 and a 14-hour offset must use minute `00`. Lowercase `z`, date-only values, missing seconds, whitespace, naive date-times, and trailing text are invalid. Values are normalized only in memory to aware UTC for comparison; authored source text is never rewritten.

### `generated`

`generated` is optional.

When present:

- it must be a mapping;
- `by` is required and must be a non-empty sanitized string;
- `at` is optional; when present it must match the timestamp grammar;
- unknown additional keys are accepted and untouched.

Absent `generated` is valid and means no generated-provenance assertion. Missing `generated.at` is valid and means generation time is unknown.

### `verified`

`verified` is optional.

When present it may be:

- one event mapping; or
- a list of event mappings.

Each event requires:

- non-empty sanitized string `by`;
- valid timestamp `at`.

A bare mapping is treated as one event for validation only. An empty list is valid and means no recorded verification events. Event order and source representation are never rewritten. Unknown event keys are accepted.

### `sources`

`sources` is optional.

When present:

- it must be a list;
- an empty list is valid and means no declared source entries;
- each entry must be a mapping;
- each entry requires a non-empty sanitized string `resource`;
- unknown fields such as `id`, `title`, credibility signals, and producer extensions are accepted and untouched.

The validator never opens, fetches, resolves, or verifies a source resource.

### Bounded actor/resource safety

Required actor/resource strings:

- must be at most 256 characters;
- must contain no NUL, C0 controls, or DEL;
- must not contain credential-bearing URL userinfo;
- must not be a Windows drive/UNC path or an absolute local filesystem path;
- actor values must not be URLs;
- source resources may be `http`/`https` URLs without userinfo and with a hostname, or bounded relative references whose segments match `[A-Za-z0-9][A-Za-z0-9._@+-]*`;
- relative references reject whitespace, backslashes, query/fragment delimiters, percent escapes, and empty/dot/traversal segments; URL paths reject decoded controls, backslashes, and dot/traversal segments;
- `file`, `data`, `javascript`, and unsupported URL schemes are rejected.

Provenance families are parsed with native safe YAML scalar types so unquoted booleans, numbers, or dates do not masquerade as required strings; the core ADR-003 authored-string loader remains unchanged. Reports identify only the file and field category. They never echo actor/resource/timestamp values or document contents. Validation does not assert that accepted actors exist or resources are reachable/trustworthy.

### `status`

ADR-003 remains authoritative:

- present value: `draft`, `stable`, or `deprecated`;
- absent value: interpreted by OKF as `stable` but not inserted;
- explicit null or any other value: invalid.

Status is lifecycle metadata and does not determine freshness.

### `stale_after` and freshness

`stale_after` is optional. When present it must match the timestamp grammar. Explicit null is invalid.

Freshness is determined only by `stale_after` and explicit `--now`:

| `stale_after` | `--now` | Outcome |
|---|---|---|
| absent | absent or present | `unknown` |
| valid | absent | `unknown` |
| valid | before cutoff | `fresh` |
| valid | equal to cutoff | `stale` |
| valid | after cutoff | `stale` |
| malformed | any | validation error / `invalid` |

`generated.at` and `verified[].at` are validation/provenance signals only and do not affect freshness in this profile.

`--now` is optional but, when provided, must match the same strict timestamp grammar. Invalid `--now` blocks the provenance/freshness validation deterministically before classification. The system clock is never read.

### Report

The separate section reports deterministic counts and relative file paths/categories only:

```text
=== Canonical Provenance/Freshness Profile ===
Concept files: N
Generated: present=X absent=Y invalid=Z
Verified: present=X absent=Y invalid=Z
Sources: present=X absent=Y invalid=Z
Freshness: fresh=X stale=Y unknown=Z invalid=W
Comparison time: explicit | absent
Source mutation: no
```

Errors are sorted by relative POSIX path and stable field category. If frontmatter cannot be parsed, the freshness category is `invalid` and optional-family counts remain unavailable rather than falsely attributing each family as invalid. Duplicate YAML mapping keys are rejected by the provenance parser. Actor/resource/timestamp payloads are not printed.

### Unknown metadata and source preservation

Unknown keys at concept, family, event, and source-entry levels remain accepted. Validation is read-only and compares/parses in memory only. It does not normalize, reorder, delete, synthesize, or write any frontmatter.

The canonical graph JSON export continues to preserve the LF-normalized authored frontmatter payload; this profile adds validation but does not change its export schema.

## Alternatives Considered

### Alternative 1 — Use the system clock implicitly

Rejected. Identical source would produce different results over time and across machines. Explicit `--now` makes freshness repeatable and testable.

### Alternative 2 — Report validation only and never classify fresh/stale

Rejected. Issue #62 explicitly requires fresh and stale fixtures/outcomes. Explicit time provides classification without nondeterminism.

### Alternative 3 — Add a separate provenance CLI command

Rejected for this increment. The fields belong to the same canonical concepts already read by `validate`. A separate labelled report preserves one gate without duplicating traversal semantics.

### Alternative 4 — Derive freshness from generated or verified timestamps

Rejected. OKF v0.2 defines `stale_after` as the freshness cutoff. Generation/verification recency is a separate signal and no threshold is specified.

### Alternative 5 — Fetch and validate source resources

Rejected. It adds network/auth/privacy/availability behavior, breaks offline determinism, and is explicitly out of scope.

### Alternative 6 — Require every optional family

Rejected. OKF v0.2 permits their absence. Absence is valid and yields unknown provenance/freshness rather than an error.

### Alternative 7 — Normalize or repair metadata

Rejected. It would mutate human-authored canonical source and violate Issue #62.

### Alternative 8 — Validate all optional credibility and attestation fields

Rejected as scope expansion. This increment validates only the five named families and their minimal internal requirements.

## Consequences

### What gets easier

- Producers and consumers share explicit shapes for the five fields.
- Fresh/stale outcomes are deterministic and independent of machine clock/timezone.
- Malformed/unsafe provenance blocks without leaking values.
- Unknown extensions and source bytes remain untouched.
- Offline validation remains one command with clearly separated report sections.

### What gets harder

- Callers wanting fresh/stale classification must provide `--now` explicitly.
- Sources/actors may be syntactically accepted without being reachable or trustworthy.
- Existing concepts with malformed optional fields will fail validation even though the families were previously ignored.
- Timestamp and sanitization fixtures add validation surface.
- Stable-checkout/path-race limits from ADR-003 remain.

### What does not change

- `type`, generated default fields, canonical traversal, graph integrity, QMD declarations, lessons, and JSON export schema remain unchanged.
- No system clock, network, source retrieval, migration, repair, refresh, synchronization, UI, server, identity allocation, or automatic human-review decision is added.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| All five fields absent are valid with unknown freshness | `test_all_optional_fields_absent_is_valid_unknown` | passing |
| Generated/verified/source valid forms and unknown keys pass without mutation | valid-family and safe-relative-resource fixtures | passing |
| Malformed/null/missing-required/duplicate-key values fail deterministically | invalid-family and duplicate-key fixtures | passing |
| Strict offset-aware timestamps and malformed values are distinguished | timestamp matrix | passing |
| Explicit now yields fresh/boundary-stale/after-stale; absent cutoff stays unknown | freshness matrix | passing |
| Unsafe actors/resources block without value/path leakage and no network is used | sanitization/network tests | passing |
| Repeated reports and source bytes are identical | determinism/preservation test | passing |
| Existing validate/profile/graph/QMD and graph export remain compatible | focused/full regression suites | passing (206 tests) |

## Rollback

Revert the implementation PR. No canonical source or consumer repository is automatically changed, so no data migration rollback is required. Concepts manually corrected by owners remain owner-controlled and are not reverted automatically.

## References

- GitHub issue #62
- ADR-003
- ADR-005
- `docs/OKF_V0_2_CANONICAL_PROFILE.md`
- Official public OKF v0.2 specification: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
- `kb_bootstrap/canonical_profile.py`
- `kb_bootstrap/canonical_graph_export.py`
