# ADR-033: Import one explicit local RawCapture without inference

**Status**: Proposed
**Date**: 2026-10-16
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #125; ADR-024, ADR-026, ADR-027, ADR-029, ADR-030

## Context

Issue #125's first acceptance criterion asks for a synthetic study populated from
supplied local Markdown without Surf, QMD, or network. The existing
`new_research.py` creates a brief and empty `raw/img` layout but does not import
an existing file. Existing `capture_page.py` is an explicitly network-capable
Surf collector, not a local importer.

Accepted ADR-027 defines selected-existing-file Git retention, not a copier or
importer. ADR-029 defines exclusive creation for the existing Surf capture
writer, including truthful partial outcomes; it does not define how arbitrary
local Markdown becomes a RawCapture. ADR-030 permits identity-preserving reuse
only through a caller-supplied valid ADR-024 envelope and full retained-member
set. None authorizes the importer to synthesize source identity, provenance,
conversion metadata, or an ADR-024 envelope from a path, URL, title, or digest.

Research checkpoints before this draft are Issue #125 comments 6208527993
(initial scope) and 6208566869 (asset boundary). No runtime behavior was
exercised for this design decision.

### Problem statement

A local-only research workflow needs one bounded way to place a caller-selected,
already-described RawCapture Markdown file into an explicit study without
fetching, rewriting, overwriting, inventing provenance, or implying that the
file is an ADR-024 identity-verified source.

## Decision

If separately accepted and implemented, provide a caller-directed operation to
copy exactly one existing, caller-selected local Markdown file that already
conforms to the packaged `RawCapture` frontmatter convention into one explicit
absent `raw/<name>.md` destination under an existing selected study. Copy exact
bytes; do not parse/reserialize or modify frontmatter. The operation records no
new identity or capture metadata and makes no acquisition or publication claim.

### What this IS

1. The caller explicitly supplies an input root and one relative input path, an
   existing study root, and one absent destination directly beneath that study's
   existing `raw/` directory. The destination basename must match
   `NNN-<slug>.md`, where `NNN` is exactly three ASCII digits and `<slug>` is a
   non-empty lowercase ASCII sequence of letters/digits separated only by
   single hyphens, matching `check_research.py`. The caller chooses the name;
   the operation never scans to allocate or choose another number. Reject
   absolute/drive/UNC paths, parent traversal, symlinked files/ancestors,
   non-regular files, paths resolving
   outside the respective selected roots, and unsafe/colliding destinations
   before reading content or writing output.
2. Accept one UTF-8 Markdown file up to 64 MiB. Its first line must be `---`;
   frontmatter ends at the first subsequent line exactly `---`. Require exactly
   one each of `type`, `title`, `url`, `captured_at`, `captured_by`, `entity`,
   and `fidelity`; `type` must be the literal `RawCapture`. These are the fields
   emitted by the current capture writer. `title`, `url`, `captured_at`,
   `captured_by`, and `fidelity` must be non-empty one-line scalar strings;
   `entity` is a one-line scalar and may be empty, as the documented no-entity
   form permits. The only optional key is `tags`, using a one-line YAML inline
   list of plain lowercase tokens as in `formats.md`. The listed scalar forms
   accept only the documented plain or double-quoted single-line spelling. This
   is the only accepted collection form: reject collections for other keys, nested or
   block collections, aliases, duplicate/unknown keys, blank required values,
   tabs, multiline scalars, malformed quoting, invalid UTF-8, and extra document
   separators.
   `fidelity` is exactly `full`, `partial`, or `blocked`; `captured_at` must be
   an offset-aware ISO timestamp string. `url` is a non-empty string copied
   verbatim; it is never dereferenced or interpreted as identity. `captured_by`
   and `entity` are descriptive strings only. These syntax gates do not prove
   source truth, permission, or timestamp accuracy. Preserve source bytes
   exactly; do not append, repair, or reserialize frontmatter.
3. Create the destination exclusively, using the per-file no-overwrite and
   containment boundary accepted in ADR-029. If it already exists, a raced
   writer wins unchanged and the import blocks; do not retry or renumber. The
   operation never deletes an existing or newly created capture as rollback.
4. Do not claim general Markdown parsing. Accept only one-line inline
   `[label](target)` and `![alt](target)` constructs whose non-empty target has
   no whitespace, parentheses, or control characters. Block before copy if the
   file contains reference definitions/usages (`[label][id]`, `[id]: target`),
   HTML tags, or an image/link-like construct outside this subset; the check is
   deliberately conservative and must not rely on `check_research.py`'s
   permissive `local_links` as a containment proof. Classify drive (`C:`) and
   UNC (`\\\\server\\\\share`) forms before URI schemes and reject them; only
   a syntactically valid non-drive URI scheme is left uninterpreted and never
   fetched. Fragment-only links are likewise uninterpreted. Every other target
   is a local relative path: resolve it from the destination's parent, reject
   absolute/drive/UNC paths, `..`, symlinks, and any canonical
   resolution outside the selected study, then require the already-existing
   target to be a regular file. The importer accepts no attachment/input set,
   copies no images/binaries, and rewrites no links. This conservative
   source-relative to destination-relative check returns `UNSUPPORTED`/blocked
   if moving the file would make a reference unsafe or missing.
5. A successful copy is a local study file only. Git staging/commit under
   ADR-027, remote publication under ADR-022, and any consumer target remain
   separate operations and authority. No QMD update, canonical promotion, or
   new study/report schema is introduced.
6. If ADR-024 identity is needed, the caller must separately supply a valid
   existing envelope and its complete retained-member set to the ADR-030 reuse
   operation. Without that, the imported file is only a relative RawCapture
   reference; the importer infers no identity from its URL, path, title, or
   content digest.

### What this IS NOT

This is not a general Markdown/plain-text importer, attachment copier, Surf
adapter, web collector, converter, source registry, ID allocator, RawCapture to
ADR-024 bridge, envelope generator, sidecar, report generator, canonical wiki
writer, QMD/index operation, automatic Git action, network fallback, consumer
migration, or proof that the supplied bytes are a faithful external original.
It does not alter the existing Surf capture path. Importing arbitrary Markdown
without the listed `RawCapture` frontmatter, reference-style Markdown,
HTML-embedded asset syntax, or attachments is outside this first bounded
operation.

### Success criteria

A future implementation must demonstrate with synthetic local files that one
explicit valid RawCapture with accepted required/optional fields and a direct
`NNN-<slug>.md` destination can be copied byte-identically without Surf, QMD,
or network; unsafe/out-of-root paths, malformed/oversized frontmatter,
unsupported or escaping/missing local references, and existing/raced output
block without changing prior bytes; and the result carries no inferred identity,
new timestamp, or authorization claim. A valid supplied ADR-024 envelope can
still be reused separately through ADR-030; the importer itself neither creates
nor mutates that envelope.

## Consequences

### What gets easier

A later session can place one already-described local RawCapture into a study
without requiring Surf or an external service, while retaining the supplied bytes
and making no provenance inference.

### What gets harder

Callers must provide a valid RawCapture and choose a destination. Inputs with
missing metadata or local assets not already available at the destination remain
blocked; the operation cannot repair them, copy attachments, or choose a new
sequence number. Exact byte preservation also means the importer cannot redact
or normalize supplied content.

### What does not change

ADR-024 remains the source/capture envelope contract; ADR-026 remains
caller-directed lookup; ADR-027 remains selected-existing-file Git retention;
ADR-029 remains per-file exclusive output for the Surf writer; ADR-030 remains
explicit-envelope identity reuse. No existing consumer format, capture bytes,
network policy, QMD behavior, or canonical lifecycle is changed by this proposal.

## Alternatives Considered

- **Reference the input in place without copying it:** rejected for this bounded
  slice because a path outside the selected study is not a retained study-local
  artifact and may not be available when the study is handed off. The caller may
  still use an ordinary reference workflow outside this proposed operation.
- **Synthesize a fresh ADR-024 envelope from path, URL, title, or digest:**
  rejected because these values do not establish source identity, original
  revision, capture time, fidelity, or retention. ADR-030 expressly forbids
  inferred identity reuse.
- **Accept arbitrary Markdown and invent missing RawCapture frontmatter:**
  rejected because it would create provenance claims not present in the input.
  A broader plain-text importer needs a separately reviewed contract.
- **Copy local image attachments or rewrite Markdown links:** deferred because
  it expands this one-file operation into multi-file mapping, path rewriting,
  format interpretation, and partial-publication rules. Missing local targets
  therefore block rather than silently dangling or copying an implicit set.
- **Do nothing:** preserves the current state where the packaged study initializer
  does not import an already-saved local RawCapture; it leaves #125's first
  offline-population criterion without this bounded path.

## Test Contract

| Claim if implemented | Test | Currently |
|---|---|---|
| Valid required RawCapture fields and optional documented inline-list `tags` are accepted; missing, duplicate, unknown, malformed, multiline, or unsupported YAML syntax is rejected without rewriting bytes | `tests/test_local_rawcapture_import.py::test_frontmatter_subset_is_deterministic` | not yet written |
| Only direct `raw/NNN-<lowercase-slug>.md` absent destination names are accepted | `tests/test_local_rawcapture_import.py::test_destination_matches_capture_name_contract` | not yet written |
| Input/destination traversal, symlink, non-regular and outside-root paths block before content read/write | `tests/test_local_rawcapture_import.py::test_unsafe_paths_block_without_mutation` | not yet written |
| >64 MiB input blocks without output | `tests/test_local_rawcapture_import.py::test_oversized_capture_blocks` | not yet written |
| Existing/raced destination bytes are preserved; no retry/renumber occurs | `tests/test_local_rawcapture_import.py::test_existing_and_raced_targets_are_not_overwritten` | not yet written |
| Supported inline local links are contained/existing; reference-style/HTML/ambiguous forms and missing/escaping targets block; external URLs are not fetched | `tests/test_local_rawcapture_import.py::test_asset_reference_subset_fails_closed` | not yet written |
| Import does not mint identity, timestamps, or an envelope; explicit ADR-024 reuse remains a separate ADR-030 call | `tests/test_local_rawcapture_import.py::test_import_adds_no_provenance_or_identity` | not yet written |
| No QMD, Git staging/commit/push, or canonical output occurs | `tests/test_local_rawcapture_import.py::test_import_has_no_external_or_canonical_side_effects` | not yet written |

## Rollback

Before acceptance, withdraw this proposal; no runtime effect exists. If accepted
and later implemented, rollback may remove the operation but must not delete
imported captures or change their bytes. Any cleanup or migration of already
imported files remains a separate owner-authorized action. Changing the accepted
input/frontmatter, path, size, or asset policy requires a superseding ADR.

## References

- Issue #125 and research checkpoints 6208527993, 6208566869
- ADR-024, ADR-026, ADR-027, ADR-029, ADR-030
- `kb_bootstrap/templates/skills/market-research/scripts/new_research.py`
- `kb_bootstrap/templates/skills/market-research/scripts/capture_page.py`
- `kb_bootstrap/templates/skills/market-research/references/formats.md`
- `docs/implementation/WORK_PACKAGES.md` (W04)
