# ADR-034: Project one explicit bounded Markdown section

**Status**: Proposed
**Date**: 2026-10-16
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #127; ADR-017, ADR-018, ADR-019, ADR-021

## Context

Issue #127 separates compact discovery from reading selected evidence. Accepted ADR-017 provides bounded `search-local` and `read-local`; the latter returns a bounded document prefix and deliberately has no section selector. `search-local` returns navigation records with a matching line/snippet, not a section. A reader that needs one portion of a known document must currently read from its beginning or use an external parser. ADR-017 also explicitly excludes `research/`, `raw/`, `lessons/`, hidden paths, and reserved index/log files from its canonical selection. This proposal does not change those boundaries.

At main `356b5d4e69910c98e6dd11cdee3f4abb5d8207c7`, direct source inspection confirmed the current `read_local` returns `{status,path,content,truncated}` and does not identify Markdown sections. The current README describes the same document-level behavior. ADR-021 keeps research working-state files excluded from ADR-017 local retrieval. ADR-018/019 govern the separate optional QMD adapter and do not authorize QMD use for this operation. The research checkpoint in Issue #127 comment 6220226154 records these observations and distinguishes them from the proposed section projection.

### Problem statement

A caller that already selected one eligible Markdown file needs a bounded way to project one authored section without scanning for documents, rewriting source bytes, or treating a heading locator as a stable semantic identity.

## Decision

If separately accepted, add one read-only section-projection module operation for a single explicitly selected Markdown document under ADR-017's existing canonical root and path-selection rules. This first slice defines no CLI or public command. It does not alter `read-local`, `search-local`, QMD behavior, or research/raw access.

### Outcomes

The result is a bounded in-memory mapping with required field `status`. `BLOCKED` covers invalid roots, paths, selectors, unsafe/non-regular files, invalid UTF-8, and content that cannot be read safely; it includes a closed-category `reason` and contains no section text. `REVISION_MISMATCH` means the file was read and hashed within bounds but its digest differs from the supplied expected digest; it includes the observed digest and no section text. `NOT_FOUND`, `AMBIGUOUS`, and `UNSUPPORTED` contain a closed-category `reason` and no section text or section locator. `COMPLETE` and `TRUNCATED` contain `path`, `observed_sha256`, `heading_path`, resolved `occurrence`, inclusive `start_line`/`end_line`, `text`, and `truncated`; `COMPLETE` has `truncated: false`, `TRUNCATED` has `truncated: true`. No status includes fields that cannot be observed for that outcome. All outcomes preserve the caller's expected digest as input context, not as observed evidence.

### What this IS

1. The module operation receives an explicit canonical root and one normalized relative Markdown path accepted by ADR-017, the caller's expected lowercase 64-hex-character SHA-256 of the complete selected document, an exact heading path represented as an ordered sequence of non-empty title strings, an optional positive 1-based occurrence number for that exact heading path, and an optional `max_section_bytes` integer from 1 through 65,536 (default 16,384). Zero, negative values, values above 65,536, non-integers, and booleans return `BLOCKED`. Invalid path/selector/digest or budget type/range returns `BLOCKED` without section text. Validate the root and path with ADR-017's existing safety and canonical-selection predicates; do not enumerate directories or follow document links. Read only that caller-selected document, bounded to 1 MiB, matching ADR-017's per-file search ceiling. Compute SHA-256 over the complete selected bytes within that cap; if the observed digest differs from the caller's expected digest, return `REVISION_MISMATCH`, include the observed digest, and return no section content.
2. Accept UTF-8 Markdown only. Parse a deliberately narrow ATX heading grammar: a line with zero to three leading ASCII spaces, followed by one through six `#` characters, followed by one or more ASCII spaces, then a non-empty title. A heading-shaped line with four or more leading ASCII spaces or a leading tab, or with a tab instead of the required separator spaces, returns `UNSUPPORTED` rather than being interpreted differently by another parser. After trimming, an empty title also returns `UNSUPPORTED`. Recognize headings only outside a single optional initial YAML frontmatter block and outside closed fenced code blocks. Frontmatter is opaque, bounded to 256 lines and 8 KiB, and ends at the first subsequent line exactly `---`; malformed or unterminated frontmatter returns `UNSUPPORTED`. Do not parse or return frontmatter values. A code fence opens with up to three leading spaces followed by at least three backticks or tildes; it closes only with the same marker, at least the opener's marker count, up to three leading spaces, and optional trailing spaces. Unterminated fences return `UNSUPPORTED`. Bound the parsed document to 256 headings and 6 levels of heading ancestry, matching the maximum ATX heading levels; each heading title is at most 512 UTF-8 bytes. Exceeding a count, depth, or title limit returns `UNSUPPORTED`. Do not implement general CommonMark. Setext headings, indented code, malformed/unterminated frontmatter or fences, or unsupported constructs that make section boundaries uncertain return `UNSUPPORTED`; never guess a section span. Invalid UTF-8 returns `BLOCKED` as an unreadable selected file, before heading parsing. Preserve source text and line endings exactly in the returned slice.
3. A section begins at its selected heading line and ends immediately before the next recognized heading of the same or higher level, or at end of document; descendant headings remain within the selected section. After the required separator, trim leading/trailing ASCII spaces from the title. If the resulting title ends with a run of `#` characters preceded by at least one ASCII space, remove that closing run and trim trailing ASCII spaces again; `#` characters not separated from the title are retained as title text. Preserve internal spaces and all other characters exactly. For example, `#  Foo  ###` yields title `Foo`; `## Foo  bar` yields `Foo  bar`; `   ### X` yields title `X`. A line indented four or more spaces (or with a leading tab) that otherwise matches the ATX marker/separator form is unsupported, not a heading; return `UNSUPPORTED` rather than silently treating a possible code block as prose. The heading path is the ordered ancestor heading titles plus the selected title under this grammar. Match titles exactly as decoded Unicode strings; do not case-fold, normalize Unicode, slugify, or infer aliases. `occurrence`, when supplied, counts identical full heading paths in document order. Zero matches returns `NOT_FOUND`; occurrence greater than the count returns `NOT_FOUND`; when occurrence is omitted and the exact heading path matches more than once, return `AMBIGUOUS`. If unsupported syntax prevents determining the complete match set or selected span, return `UNSUPPORTED` rather than claiming a unique result.
4. `COMPLETE` and `TRUNCATED` return only the success fields defined in Outcomes. The selected section includes its heading and ends before the next same-or-higher heading. `max_section_bytes` bounds UTF-8 text bytes; truncation returns the longest valid UTF-8 prefix that fits and never splits a code point. A limit smaller than the next complete UTF-8 code point returns an empty `TRUNCATED` text while preserving the resolved locator. Each heading-path component is at most 512 UTF-8 bytes, the path has at most 6 components, and the serialized UTF-8 mapping is at most 256 KiB including JSON escaping; exceeding an output metadata bound returns `UNSUPPORTED` without section text. No absolute root, arbitrary frontmatter, or surrounding document text is emitted.
5. The locator `(relative path, observed document digest, exact heading path, occurrence, line range)` is a revision-scoped navigation address only. It is not a persisted ID, semantic identity, claim/evidence binding, proof of source truth, freshness, review, or approval. Any document byte change invalidates the caller's expected revision; renamed or restructured headings require an explicit new selection. Source Markdown is never modified.
6. The operation performs no QMD calls, index reads/writes, caching, embeddings, network access, external inference, source discovery, or consumer migration. It adds no registry or persisted schema. This proposal defines only a module contract, not a CLI or command. Owner acceptance is required before runtime implementation; this Proposed ADR alone is not runtime authorization.

### What this IS NOT

This is not a general Markdown/CommonMark parser, document search engine, heading index, passage registry, chunk database, semantic locator, stable section ID, automatic link rewriter, cache, QMD/vector/hybrid retrieval, research/raw/lesson access, evidence verification, freshness evaluation, or source-truth claim. It does not expand ADR-017 canonical path eligibility or change accepted command semantics.

### Success criteria

- A caller-selected eligible file is read only after ADR-017 path checks and within the fixed 1 MiB input cap.
- A matching expected digest yields the exact uniquely selected section with deterministic heading path, occurrence, and source line range; a stale digest yields `REVISION_MISMATCH` and no section text.
- Frontmatter and closed code fences cannot contribute headings. Unsupported or malformed boundaries fail explicitly.
- Duplicate heading paths require a supplied occurrence; omission with duplicates returns `AMBIGUOUS`, never guessed content.
- Returned text is UTF-8-safe and within the requested bounded output; truncation is explicit.
- Source bytes remain unchanged and the operation performs no directory discovery, QMD/index operation, network access, or cache write.

## Consequences

### What gets easier

Callers can inspect a selected portion of an already located canonical Markdown document without reading the whole document prefix or introducing a section index.

### What gets harder

The narrow parser intentionally rejects common Markdown heading forms and malformed boundaries; callers must provide an exact revision and heading selector. Heading edits invalidate locators, and bounded section output may be truncated.

### What does not change

ADR-017 path selection, `search-local`, `read-local`, their result contracts and budgets, ADR-018/019 QMD boundaries, ADR-021 research exclusions, source bytes, and consumer state remain unchanged. A section hit is navigation, not validation or verification.

## Alternatives Considered

### Add a public CLI selector in the same increment

Deferred because the current deliverable is only the bounded projection contract; CLI names, flags, argument grammar, and presentation can be decided in a separate implementation increment after owner acceptance.

### Extend `read-local` with an optional section selector

Rejected for this proposal because it changes an accepted command's result semantics and mixes document-prefix reads with a separate parsing contract. A separate additive module operation can preserve `read-local` behavior.

### Build a section/heading index

Rejected because it introduces persisted or cached derived state, invalidation, and freshness semantics where reading one selected bounded file suffices.

### Use heading slugs or normalized titles as identifiers

Rejected because duplicate headings, Unicode normalization, and edits can collide or change; a caller-selected document digest plus exact heading path and occurrence makes revision dependence explicit without minting identity.

### Parse full CommonMark

Rejected for this bounded increment because a complete parser expands dependency/runtime and syntax compatibility scope. Unsupported boundary syntax must be reported, not guessed.

### Do nothing

Preserves the current bounded document read. It leaves callers to read from the beginning or use another parser when they need one selected section; this remains acceptable if section projection is not worth its parser and locator costs.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Existing ADR-017 path exclusions and explicit-root checks remain in force | `tests/test_section_projection.py::test_existing_path_policy_is_reused` | not yet written |
| Expected revision mismatch is distinct from an unsafe/invalid request and returns no section text; exact matching revision yields deterministic locator | `tests/test_section_projection.py::test_revision_scoped_locator` | not yet written |
| ATX headings inside frontmatter and fenced blocks are ignored; separator/indent/title normalization is deterministic; malformed or unsupported boundary syntax fails closed | `tests/test_section_projection.py::test_atx_grammar_and_frontmatter_fence_boundaries` | not yet written |
| Duplicate heading paths return `AMBIGUOUS` if occurrence is omitted; explicit valid occurrence selects deterministically | `tests/test_section_projection.py::test_duplicate_heading_occurrence` | not yet written |
| Section end follows next same-or-higher heading and inclusive source lines remain exact | `tests/test_section_projection.py::test_section_boundary_and_source_lines` | not yet written |
| Input, parser, heading-path, serialized-output, and explicit `max_section_bytes` bounds are enforced with explicit `TRUNCATED`/`UNSUPPORTED`/`BLOCKED` outcomes | `tests/test_section_projection.py::test_document_and_section_budgets` | not yet written |
| Invalid UTF-8 and unsafe/unreadable paths return `BLOCKED`; parser-boundary syntax failures return `UNSUPPORTED`; no failure outcome includes section text or unavailable locator fields | `tests/test_section_projection.py::test_error_outcome_fields_and_utf8_boundary` | not yet written |
| No directory discovery, QMD, network, cache, or source mutation occurs | `tests/test_section_projection.py::test_projection_is_read_only_and_selected_only` | not yet written |

## Rollback

Before acceptance, withdraw this proposal; no runtime behavior exists. If accepted and later implemented, revert only the additive section-projection module operation and tests. No persisted index or generated cache requires migration, and no source or consumer file is changed.

## References

- Issue #127 and research checkpoint comment 6220226154.
- ADR-017 (bounded canonical local search/read); ADR-018 and ADR-019 (separate QMD adapter); ADR-021 (research lifecycle/retrieval boundary).
- `kb_bootstrap/local_retrieval.py`, README local search/read documentation.
