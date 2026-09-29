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
3. A representation `revision` is the SHA-256 of its exact retained bytes. A
   conversion can change while the original does not, and vice versa.
4. `fidelity` declares `exact`, `partial`, `manual-summary`, or `blocked` plus
   coverage and losses. Length and a matching media type do not prove fidelity.
5. Representation-local `coordinates` inherit the identity and revision of their
   containing representation. Optional original coordinates are separate and may
   be unknown; converters must not invent them.
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
- `original_retention`: required and independent of representation retention;
  it is `retained`, `reference-only`, or `unknown`. It says whether original
  bytes, rather than a derived representation, are locally retained.
- `capture`: a required capture-attempt object with a `method` of `direct`,
  `converted`, `manual-summary`, or `blocked`. `captured_at` is optional and must
  be omitted when no trustworthy observation was supplied. Converted records
  include required converter `identity` and `version`; deterministic `parameters`
  are optional metadata and must not be fabricated. Model-derived output must say
  so in the identity and remains distinct from a manual summary. A `blocked`
  capture contains a bounded `reason` and requires `representations: []`.
- `fidelity`: a required capture-attempt object with `class`, a declared
  `coverage`, and a `losses` array. `exact`
  requires byte-for-byte identity with the available original; `partial` names
  included scope; `manual-summary` never claims extraction; `blocked` records no
  successful capture. Use `class: unknown`, `coverage: unknown`, and declared
  losses (possibly `[]`) when fidelity was not established; omission is invalid.
- `representations`: a required array of zero or more records containing a unique
  `representation_id`, exact-byte `revision: {algorithm: sha256, digest: ...}`,
  `media_type`, optional `language`, and `retention` (`retained` or
  `reference-only`). Retained bytes require a safe corpus-relative `raw_path`;
  reference-only records prohibit it. A retained zero-byte payload is a normal
  record whose SHA-256 is the empty-byte digest; it is not an empty array.
- `coordinates`: optional within a representation. Local coordinates inherit that
  containing record's `representation_id` and `revision`; they do not repeat them.
  Separately labelled original coordinates address the parent `original_revision`
  and may be `unknown`.
- `permissions`: independent owner declarations for `access`, `retention`, and
  `redistribution`, each allowing an explicit `unknown`. These are labels for
  policy evaluation, not authorization created by this document.

Timestamps, when supplied, are offset-aware RFC 3339 observations rather than
revision identities. Repeated uses refer to the same `source_id` and revision;
study-specific notes do not mint a second source. Distinct origins remain distinct
even when their bytes and SHA-256 digests match.

`representations` is always present. `[]` means the capture attempt is known to
have produced no representation; a missing array is invalid, not “unknown”. A
retained zero-byte payload instead has one representation with digest
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` and a
`raw_path`. Unknown scalar facts use the explicit `unknown` value where allowed;
an empty `losses: []` means no losses were declared, not that fidelity is known.

All coordinate ranges are half-open `[start, end)`. `byte` and
`unicode-code-point` offsets are zero-based; byte offsets address the exact UTF-8
payload bytes, while code-point offsets address decoded Unicode scalar values.
`line` numbers are one-based and line ranges are half-open. An LF terminator is a
byte/code point for byte and code-point ranges, but is not a separate line; a
terminal LF therefore does not create another addressable content line.

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
