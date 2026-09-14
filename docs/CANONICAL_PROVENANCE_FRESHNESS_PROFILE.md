# Canonical provenance and freshness profile

This bounded profile extends the [kb-bootstrap canonical OKF v0.2 profile](OKF_V0_2_CANONICAL_PROFILE.md) for five optional fields: `generated`, `verified`, `sources`, `status`, and `stale_after`.

Validation is part of:

```bash
kb-bootstrap validate --dir kb --project-root .
```

Fresh/stale classification requires an explicit comparison instant:

```bash
kb-bootstrap validate \
  --dir kb \
  --project-root . \
  --now 2026-09-14T12:00:00Z
```

The system clock is never used. Without `--now`, freshness remains `unknown` even when a valid cutoff exists.

## Timestamp format

Every timestamp in this profile uses:

```text
YYYY-MM-DDTHH:MM:SS[.fraction](Z|+HH:MM|-HH:MM)
```

Timestamp strings are bounded to 128 characters. Date-only, naive, lowercase `z`, invalid calendar/offset, missing-second, whitespace, null, and other malformed forms fail. Numeric offsets are limited to `-14:00` through `+14:00`; minutes must be below 60 and `±14` requires `:00`. Values are normalized only in memory for comparison and never rewritten.

## Fields

### `generated`

Optional mapping:

```yaml
generated:
  by: reference-agent/1
  at: 2026-09-14T10:00:00Z
```

- `by`: required non-empty sanitized actor string;
- `at`: optional offset-aware timestamp;
- unknown extra keys are accepted.

Absence is valid and means no generated-provenance assertion.

### `verified`

Optional one event mapping or list:

```yaml
verified:
  - by: human:reviewer
    at: 2026-09-14T11:00:00Z
```

Each event requires sanitized `by` and valid `at`. A bare mapping counts as one event. An empty list is valid and means no recorded verification event. Validation does not convert or reorder the source representation.

### `sources`

Optional list:

```yaml
sources:
  - resource: https://example.com/public-document
    title: Public document
```

Each entry requires a non-empty sanitized `resource`. Unknown fields remain accepted. An empty list is valid and means no declared source entries.

Resources may be public `http`/`https` URLs without credentials and with a hostname, or bounded relative references. Relative references reject whitespace, backslashes, empty/dot/traversal segments, and percent-decoded control characters. Local absolute/drive/UNC paths, credential-bearing URLs, unsupported schemes, controls, and secret-like values block. The validator never opens or fetches a resource and does not claim it is reachable or trustworthy.

### `status`

Inherited from the canonical profile:

- `draft`;
- `stable`;
- `deprecated`.

Absence is interpreted by OKF as `stable` but is not inserted. Status is lifecycle metadata and does not determine freshness.

### `stale_after`

Optional offset-aware timestamp. It is the only metadata field used for freshness classification.

| Cutoff | Explicit `--now` | Freshness |
|---|---|---|
| absent | absent or present | `unknown` |
| valid | absent | `unknown` |
| valid | before cutoff | `fresh` |
| valid | equal/after cutoff | `stale` |
| malformed | any | `invalid` and validation failure |

`generated.at` and `verified[].at` do not change freshness.

## Actor and resource safety

Provenance values use native safe YAML scalar types, so unquoted booleans, numbers, and dates do not count as required strings. Required actor/resource strings are bounded to 256 characters and reject control characters, DEL, secret-like assignments, and absolute local paths. Actor values cannot be URLs. Reports do not echo actor, resource, or timestamp values.

These checks establish only bounded syntax and non-disclosure. They do not authenticate actors, authorize changes, score trust, or verify sources.

## Report

The command adds a separate deterministic section:

```text
=== Canonical Provenance/Freshness Profile ===
Concept files: N
Generated: present=X absent=Y invalid=Z
Verified: present=X absent=Y invalid=Z
Sources: present=X absent=Y invalid=Z
Freshness: fresh=X stale=Y unknown=Z invalid=W
Comparison time: explicit | absent
ERRORS: 0
Source mutation: no
```

Errors contain only relative concept paths and field categories. Unknown keys remain in the original Markdown and in canonical graph frontmatter payloads.

## Determinism and preservation

Repeated validation over stable unchanged inputs with the same `--now` produces an identical report. Validation does not migrate, repair, reorder, normalize, delete, or write frontmatter.

Canonical traversal uses the ADR-003 static symlink and stable-checkout boundary. The profile does not claim a race-free cross-process filesystem snapshot.

## Non-actions

This profile does not:

- use the system clock;
- fetch or dereference sources;
- authenticate actors or derive trust scores;
- refresh, migrate, repair, or rewrite canonical content;
- synthesize missing metadata;
- run background polling or synchronization;
- change QMD, graph-export schema, lesson stores, or external repositories;
- replace explicit human review.
