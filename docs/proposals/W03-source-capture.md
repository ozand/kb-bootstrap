# W03 source and capture provenance contract

**Status:** Proposed design only; not an accepted production contract.
**Scope:** W03-A / Issue #124. This proposal does not authorize ingestion,
conversion, validation, publication, or migration.

## Purpose and boundaries

A record describes a supplied origin and the representations made from it without
collapsing six independent facts:

1. `source_id` is the stable logical identity assigned by the owner. It can group
   revisions and reuse across studies, but is not evidence of common authorship or
   independent corroboration.
2. `original_revision` identifies one observed revision of the original by a
   digest when bytes are available, or by an explicit opaque owner label when they
   are not. It is never a path, URI, timestamp, or capture digest.
3. `representation_revision` is the SHA-256 of the exact retained representation
   bytes. A conversion can change while the original does not, and vice versa.
4. `fidelity` declares `exact`, `partial`, `manual-summary`, or `blocked` plus
   coverage and losses. Length and a matching media type do not prove fidelity.
5. `coordinates` address a named representation revision. Optional original
   coordinates are separate and may be unknown; converters must not invent them.
6. `permissions` records owner declarations about access, retention, and
   redistribution. It does not follow from possession, fidelity, or a digest.

The contract is descriptive metadata, not a domain ontology or a trust score.
Already readable source code can remain byte-exact; Markdown is a reading surface,
not a mandatory conversion target. Images, tables, regions, pages, slides, and
timecodes may remain as retained representations with media-appropriate
coordinates.

## Proposed data-only shape

The proposed envelope has `schema: kb-bootstrap.source-capture`, `version: 1`, and
one `sources` array. Unknown schema names or versions would block a future
validator rather than be guessed. Each source entry contains:

- `source_id`: owner-scoped, non-secret logical identifier; it must not contain a
  private absolute path.
- `origin`: a supplied, non-dereferenced descriptor with `kind` and `reference`.
  A public URL, safe bundle-relative reference, or opaque owner reference can be
  represented; the record grants no permission to open it. If no safe reference
  is available, use `kind: unavailable` and an explicit `reason`.
- `original_revision`: either `{algorithm: sha256, digest: ...}` computed from
  available original bytes or `{opaque: ...}` supplied by the owner, plus optional
  `observed_at`, `media_type`, and `language`. Unknown values stay absent or
  explicitly `unknown`; a capture timestamp is not substituted.
- `representations`: zero or more records containing a unique `representation_id`,
  exact-byte `revision: {algorithm: sha256, digest: ...}`, `media_type`, optional
  `language`, and `retention` (`retained` or `reference-only`). Retained bytes are
  addressed by a safe corpus-relative `raw_path`; reference-only records have no
  `raw_path` and do not pretend reverse navigation succeeded.
- `capture`: `captured_at` and a `method` of `direct`, `converted`,
  `manual-summary`, or `blocked`. Converted records include converter
  `identity`, `version`, and deterministic `parameters`; model-derived output must
  say so in the identity and remains distinct from a manual summary. `blocked`
  records contain a bounded reason category and no representation revision.
- `fidelity`: `class`, a declared `coverage`, and a `losses` array. `exact`
  requires byte-for-byte identity with the available original; `partial` names
  included scope; `manual-summary` never claims extraction; `blocked` records no
  successful capture. Unknown fidelity is represented explicitly, not upgraded
  from text length or converter success.
- `coordinates`: optional mappings from representation-local, half-open units to
  separately labelled original coordinates. Every local coordinate names the
  representation and its digest. Original coordinates may be `unknown`.
- `permissions`: independent owner declarations for `access`, `retention`, and
  `redistribution`, each allowing an explicit `unknown`. These are labels for
  policy evaluation, not authorization created by this document.

Timestamps, when supplied, are offset-aware RFC 3339 observations rather than
revision identities. Repeated uses refer to the same `source_id` and revision;
study-specific notes do not mint a second source. Distinct origins remain distinct
even when their bytes and SHA-256 digests match.

## ADR-010 relationship and lifecycle

ADR-010 raw-manifest v1 remains byte-for-byte unchanged. Its corpus-relative path
and exact-byte digest can inventory each retained `raw_path`; the W03 metadata may
point to that path and repeat the same computed digest, but neither format is
embedded in or inferred from the other. A raw manifest proves neither origin,
fidelity, coordinates, permissions, nor retention history.

A new original revision does not erase an older capture. A new conversion of the
same original creates a new representation revision without changing the original
revision. Unchanged bytes do not trigger deletion, re-fetch, or a permission
change. Any future publication operation must be explicit and no-overwrite; this
design performs none.

## Deterministic validation boundary (future, unaccepted)

A future validator could parse only explicitly supplied metadata and retained
local bytes, reject duplicate keys and malformed/unknown versions, recompute each
retained representation digest, and cross-check an explicitly supplied ADR-010 v1
entry. It must not dereference an origin, probe a reference-only resource, infer
permissions, rewrite bytes, or resolve unknown original coordinates. A missing
retained representation yields an honest unavailable result for reverse
navigation. Validation behavior, limits, diagnostics, and publication mechanics
require separate acceptance and are not specified as production behavior here.

## Open integration questions

- **W01 / #122:** Which capability vocabulary will express capture, conversion,
  coordinate, and reverse-navigation support without turning these descriptive
  fields into capability claims? Until W01 is reconciled, this proposal defines no
  capability advertisement or conformance level.
- **W09:** Which authority defines permission labels, retention duties, sensitive
  reference handling, redistribution decisions, and deletion? Until W09 is
  reconciled, the labels above remain owner declarations with no policy effect.
- **#90:** Which eventual canonical reference shapes can be reused for `origin`
  without permitting dereference or changing #90's ownership? This proposal does
  not extend the accepted canonical provenance schema.

The synthetic fixture document demonstrates distinctions only. It is not an
installed schema, validation corpus, or evidence about a real source.
