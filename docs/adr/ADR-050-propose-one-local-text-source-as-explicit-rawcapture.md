# ADR-050: Propose one local text source as an explicit RawCapture

**Status**: Proposed
**Date**: 2026-11-06
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #125; ADR-024, ADR-027, ADR-029, ADR-030, ADR-033

## Context

Issue #125 asks for an offline way to populate a synthetic study from supplied local text or Markdown without Surf, QMD, or network. Accepted ADR-033 and its importer cover exactly one already-described RawCapture; they do not accept arbitrary text or invent the required RawCapture metadata. The existing `capture_page.py` is a separate Surf collector. The direct importer has focused unit/CLI coverage (the issue's exact reviewed correction reports 15 focused tests passing), but no ordinary-text producer exists.

ADR-024 constrains source-capture envelopes and exact representations; it is not permission to fabricate an envelope. ADR-029 defines exclusive per-file publication, no overwrite/renumber/retry, truthful partial output, and no multi-file transaction, under the accepted stable-checkout boundary. ADR-030 prohibits inferring identity or reuse. ADR-033 requires the current RawCapture fields and conservative body/link subset and explicitly excludes a generic text importer. This proposal adds a separate, caller-asserted conversion into that RawCapture form; it does not change those contracts or make assertions independently verified.

## Problem statement

A caller-supplied local text/Markdown body needs a narrow, offline route into the existing RawCapture/import workflow without treating the path, body, or producer as evidence of origin, authorship, acquisition time, completeness, or truth.

## Decision

If separately accepted, add one standard-library-only packaged script, adjacent to the market-research scripts, that reads one explicitly selected local UTF-8 text/Markdown file and creates one caller-named RawCapture under an explicitly selected existing study's `raw/` directory. The output must satisfy ADR-033's existing RawCapture grammar and 64 MiB bound, so the already accepted importer and research checker can consume it. The producer is not a general Markdown parser or a replacement for Surf.

1. **Explicit inputs and metadata.** The caller supplies an input root and relative source path, existing study root, exact absent destination basename `NNN-<slug>.md`, and every RawCapture field: non-empty one-line `title`, non-empty one-line `url`/source reference, an explicitly entered offset-aware ISO `captured_at`, non-empty one-line `captured_by`, one-line `entity` (which may be empty), and `fidelity` exactly `full`, `partial`, or `blocked`. The accepted RawCapture format requires `captured_at`; there is no `unknown` sentinel in this proposal, so a caller without a defensible timestamp must not invoke the producer. A caller may enter a local reference such as a repository-relative label for `url`; the tool does not validate that it identifies an origin. These are caller assertions copied into the output, not authenticated facts. No current-time, file-mtime, path-name, title, identity, entity, fidelity, completeness, or provenance defaults/inference are allowed. Missing/invalid metadata blocks before publication. The tool creates no ADR-024 envelope, source identity, revision, or corroboration claim.
2. **Input bytes and fidelity.** Input is one regular, non-symlinked file selected by relative path beneath an explicit existing input root, at most 64 MiB. Read bytes once; decode strictly as UTF-8 for validation, reject invalid UTF-8 and a leading UTF-8 BOM (do not strip it), and never Unicode-normalize, replacement-decode, or rewrite the body. Preserve every body byte, including CRLF, bare CR, LF, and absence/presence of final newline. Output consists of producer-generated RawCapture frontmatter encoded as UTF-8 with fixed LF delimiters, immediately followed by the original body bytes. Thus the body bytes are exact; the whole output is not byte-identical to the input and does not satisfy ADR-024 `exact` representation semantics merely by preserving the body. Reject Unicode category `Cc` characters except horizontal tab (U+0009), LF (U+000A), and CR (U+000D); therefore NUL, DEL and C1 controls block, while Markdown line endings remain byte-preserved. Total emitted file size, including header, must not exceed 64 MiB.
3. **Format and integration boundary.** Generate only the documented ADR-033 RawCapture frontmatter using explicit caller values; do not reinterpret or repair the body. Before publication, apply the ADR-033 constraints needed for the produced RawCapture to be importable: no extra document separator, unsupported/reference-style/HTML/image-like Markdown, invalid inline-target syntax, missing or escaping local links relative to the final destination, or symlinked linked targets. URI-looking targets are never dereferenced. `BLOCKED` means input/metadata/path/collision is unsafe or invalid; `UNSUPPORTED` means body syntax or links exceed the accepted subset; neither writes a destination. On success, report only that the local RawCapture was created, not that the source was fetched or verified. Then an operator may separately invoke the ADR-033 importer and existing checker; those operations retain their own contracts and outcomes.
4. **Path safety and publication.** Require a relative, non-drive/non-UNC input path with no empty, `.` or `..` component; reject symlinked roots, ancestors, source, and unsafe/non-regular files. Destination is exactly one direct child of the selected existing `raw/` directory and matches ADR-033's caller-selected `NNN-<slug>.md` grammar. Reject symlinked study/raw parents, traversal, and any existing target. Use the per-file exclusive-create/no-overwrite behavior of ADR-029; never allocate a number, retry, renumber, replace, or delete an output as rollback. If failure occurs after exclusive creation starts, preserve any file that may have been created and report `PARTIAL` without claiming success. This is not multi-file atomicity, a stable-filesystem snapshot, or protection against hostile concurrent ancestor replacement; guarantee remains no stronger than ADR-029's stable-checkout boundary.
5. **No external actions.** No Surf/browser, URL dereference, network, QMD, model, dependency, attachment/image copy, Git staging/commit/push, canonical write, migration, or consumer access. Source bytes are read-only. Output is a local working-tree artifact; source eligibility and repository publication review remain separate under ADR-027 and the market-research skill.

## What this is not

This is not arbitrary Markdown acceptance, a general importer, source-capture envelope, verified source record, URL fetch, adapter/plugin framework, study/report generator, timestamp service, text normalizer, attachment copier, link rewriter, or evidence of truth, authorship, permission, completeness, screenshot provenance, or external-byte fidelity. It does not alter `capture_page.py`, importer behavior, RawCapture schema, or existing accepted ADRs. A limitation of the existing contract remains: RawCapture requires a capture timestamp, and this producer cannot truthfully represent an unknown timestamp. A future choice to add an explicit unknown timestamp form needs a separate contract decision; do not silently invent a time. Acceptance of this proposal alone does not authorize implementation; implementation and the ADR's acceptance require independent review under the delegated #125 architecture/technical acceptance authority.

## Alternatives considered

- **Require the caller to prepare a RawCapture manually:** safe and already compatible, but does not provide the requested direct local-text producer path.
- **Feed arbitrary text to the ADR-033 importer:** rejected because it would require the importer to invent mandatory RawCapture fields or weaken its accepted grammar.
- **Store text without RawCapture frontmatter:** rejected for this bounded slice because the existing importer and research checker require RawCapture; a new capture type/schema would widen scope and lack a current consumer.
- **Infer fields from path, file metadata, or current time:** rejected because those values cannot establish source identity, capture time, provenance, fidelity, or permission.
- **Normalize line endings, strip BOM, or decode with replacement:** rejected because these silently alter the caller's body and invalidate byte-fidelity claims.
- **Add a framework CLI, dependency, source registry, or generic plugin API:** rejected; one packaged script and stdlib cover the demonstrated local operation.

## Acceptance criteria if accepted and implemented

- Synthetic UTF-8 text and Markdown input with explicit fields produces a valid RawCapture whose body suffix is byte-for-byte equal to source bytes for LF, CRLF, bare CR and no-final-newline cases.
- BOM, invalid UTF-8, controls outside the permitted tab/newline set, missing/incomplete metadata, oversize source/output, unsafe source/destination paths, unsupported body/link forms, and existing/raced destinations yield the specified sanitized state without overwriting existing bytes.
- No timestamp, identity, provenance, fidelity, or content claim is inferred; source bytes remain unchanged and no external access occurs.
- An end-to-end synthetic test invokes the producer, then the accepted ADR-033 importer, then the existing research checker on a correctly prepared study; it verifies successful integration and collision preservation without Surf, QMD, network, or consumer data. Checker success is structural validation only, not semantic truth or completeness verification.

## Test contract

| Claim | Test | Status |
|---|---|---|
| Body byte preservation and exact newline/BOM/UTF-8/control policy | Direct producer fixture matrix | Not implemented; Proposed only |
| Explicit metadata, format limits and rejection states | Direct producer tests | Not implemented; Proposed only |
| Path containment and exclusive collision/race behavior | Synthetic filesystem tests, including preserved winner bytes | Not implemented; Proposed only |
| Actual producer → ADR-033 importer → checker composition | Synthetic subprocess integration test | Not implemented; Proposed only |
| No external access, inference or source mutation | Synthetic offline tests and source byte comparison | Not implemented; Proposed only |

No tests are added by this documentation-only proposal and no runtime behavior is claimed.

## Rollback

Before acceptance, withdraw this proposal without runtime effect. If accepted and later implemented, revert only the producer operation/tests; never delete or rewrite generated RawCapture files. Existing RawCapture/importer contracts remain authoritative unless a separately accepted ADR explicitly supersedes them.

## References

- Issue #125: https://github.com/ozand/kb-bootstrap/issues/125
- Research-before-edit checkpoint: https://github.com/ozand/kb-bootstrap/issues/125#issuecomment-6561808635
- ADR-024, ADR-027, ADR-029, ADR-030, ADR-033
- `kb_bootstrap/templates/skills/market-research/scripts/capture_page.py`
- `kb_bootstrap/templates/skills/market-research/scripts/import_local_capture.py`
- `kb_bootstrap/templates/skills/market-research/scripts/check_research.py`
- `kb_bootstrap/templates/skills/market-research/references/formats.md`
