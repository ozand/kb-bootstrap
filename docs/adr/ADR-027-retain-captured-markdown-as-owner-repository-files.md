# ADR-027: Retain captured Markdown as owner-repository files

**Status**: Proposed
**Date**: 2026-10-10
**Authors**: Pi coding agent
**Supersedes**: ADR-025 (only if this ADR is accepted)
**Related**: Issue #124; Issue #125; ADR-010, ADR-022, ADR-024, ADR-025, ADR-026

## Context

The owner clarified in Issue #124 comment 6093093713 that capture publication means the captured original Markdown files are sent into the repository too, rather than packaged only in a ZIP. This is a different publication target and product outcome from Accepted ADR-025's archive artifact. ADR-025 is immutable and remains historically Accepted until a superseding ADR is accepted; this proposal does not rewrite it. At main `d68c93e4e10ef89c9c1ba5d8a30f51fe576ed9e0`, the packaged market-research flow already stores `RawCapture` Markdown under `kb/research/<study>/raw/NNN-<slug>.md` and refers to it from reports using relative paths. The current capture helper writes directly and chooses a next number by scanning; that behavior is observed prior art, not proof of exclusive/no-overwrite publication. ADR-010 inventories bytes but does not publish captures. Issue #125 owns collector-independent importing and must be coordinated without turning this decision into an importer redesign.

### Problem statement

A capture retained for repository use must remain an ordinary readable Markdown file at a stable repository-relative evidence path, committed through the normal repository workflow, without silently replacing or renumbering prior captures or implying that a helper's local file write automatically authorizes a Git commit, push, or consumer publication.

## Decision

If accepted, repository capture retention prepares an explicit selected set of existing repository capture files and then uses the ordinary reviewable Git workflow to make exactly that set tracked in the owning repository. It adds no new copier or metadata format.

### What this IS

1. The caller explicitly selects the owning repository root, an existing study directory, and the complete set of already captured `RawCapture` Markdown files to retain. Preserve the established repository form `kb/research/<study>/raw/NNN-<slug>.md` where used. The operation does not infer a consumer repository from remotes, discover other studies, fetch origins, or choose an external destination.
2. Prepare a bounded sorted list of selected repository-relative paths and exact blob digests from the working tree. Preserve selected Markdown bytes, existing frontmatter and relative references exactly; do not summarize or rewrite. No new sidecar schema is defined. If an accepted ADR-024 envelope is explicitly selected or required for validation, select that existing file explicitly and preserve/validate its original bytes; `RawCapture` frontmatter is not itself treated as an ADR-024 envelope. Do not create an ADR-024 sidecar or metadata reserialization. No format claims that Markdown is a byte-identical unavailable external original or proves lossless extraction.
3. Existing selected files are preserved byte-for-byte. This ADR defines no copier or output-path allocator. Creating a new capture or attachment is outside this decision and must use an existing separately authorized capture path or a separately accepted no-overwrite rule. Do not scan studies to expand the selected set.
4. Remote push/PR remains a distinct explicit, exactly targeted operation under ADR-022 and repository contribution policy. The helper does not stage, commit, or push; no consumer repository is inferred or modified.
5. ADR-024 validation may be applied to an explicitly selected existing envelope when required, but this decision does not rewrite its metadata, create a sidecar, widen its UTF-8-only contract, or copy unsupported media. ADR-026 continues to distinguish retained representation evidence from a verified retained original. Permission/retention labels do not authorize repository delivery.

### What this IS NOT

This is not a ZIP/archive output or reader, generic importer, external acquisition or conversion engine, global source registry, automatic `git add`/commit/push, automatic publication to a consumer repository, source renumbering, overwrite/repair, copier, or transaction across multiple files. It does not claim an untracked working-tree file is repository-retained. It does not alter ADR-010 manifest v1, ADR-024 source-capture metadata, or ADR-025's accepted historical text. If accepted, ADR-025 becomes superseded; its archive implementation is not authorized by this decision.

### Success criteria

A future workflow prepares an explicit set of existing owner-repository `RawCapture` Markdown/provenance paths, verifies their current blob identities, stages exactly those paths, verifies the staged path/blob set contains no unrelated path, and commits them so the selected captured Markdown is tracked. It leaves source bytes and metadata unchanged and performs no discovery, origin fetch, new file copy, consumer write, or implicit push.

## Consequences

### What gets easier

People and tools can read captured Markdown directly as tracked files in the owning repository and follow existing relative evidence links; no archive extraction or new copy step is required.

### What gets harder

The selected-file manifest and Git staging/commit boundary must be checked carefully to prevent unrelated files entering the commit. Existing captures are immutable; a changed capture needs a new path/revision rather than replacement. Remote publication remains a separate authorization boundary.

### What does not change

ADR-010 remains a read-only exact-byte inventory. ADR-024 remains the source/capture validation contract. ADR-026 remains caller-directed read-only lookup. No source fetch, consumer migration, hidden commit/push, global scan, model, dependency, or CLI is introduced by this decision.

## Alternatives Considered

- **Keep ZIP as the only published capture artifact:** rejected because the owner's clarified outcome is that captured Markdown itself is retained as repository files and remains directly readable; an archive alone does not meet that outcome.
- **Write captures to multiple paths and claim all-or-nothing publication:** rejected because the existing repository contracts provide exclusive single-file publication, not a multi-file transaction; a failure can leave earlier files visible.
- **Overwrite or renumber old captures when a new capture arrives:** rejected because it breaks stable references and conflicts with #125's preserve-old-captures/no-renumber requirement.
- **Have the helper automatically commit or push:** rejected because local file-write, review, commit, and remote publication are distinct actions and ADR-022 keeps authority separate.
- **Do nothing:** leaves #124's clarified product intent unsatisfied while treating an archive package as the retained repository capture.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| Explicit RawCapture paths and blob identities are prepared without rewriting files | `tests/test_capture_repository_delivery.py::test_selected_capture_blob_manifest_is_exact` | Not yet written |
| Git delivery stages/commits only selected paths with expected blobs | `tests/test_capture_repository_delivery.py::test_git_commit_contains_only_selected_capture_blobs` | Not yet written |
| Unrelated files and pre-existing captures remain excluded and unchanged | `tests/test_capture_repository_delivery.py::test_unselected_and_existing_files_are_preserved` | Not yet written |
| Selected ADR-024 metadata, when present, remains byte-identical | `tests/test_capture_repository_delivery.py::test_selected_provenance_bytes_are_unchanged` | Not yet written |
| No discovery, origin fetch, implicit copy, remote push, or consumer targeting occurs | `tests/test_capture_repository_delivery.py::test_delivery_selection_has_no_external_side_effects` | Not yet written |

## Rollback

Before acceptance, withdraw this proposal and retain ADR-025 unchanged. If accepted, ADR-025 is marked `Superseded by ADR-027` without changing its normative body. Any implementation must preserve already-created capture files on rollback; no consumer files, commits, or remote branches are automatically deleted or rewritten.

## References

- Issue #124 owner clarification: https://github.com/ozand/kb-bootstrap/issues/124#issuecomment-6093093713
- Issue #124 research checkpoint: https://github.com/ozand/kb-bootstrap/issues/124#issuecomment-6093122555
- Issue #125 acceptance and scope
- ADR-010, ADR-022, ADR-024, ADR-025, ADR-026
- `kb_bootstrap/templates/skills/market-research/scripts/capture_page.py`
- `kb_bootstrap/templates/skills/market-research/references/formats.md`
- `docs/CONTRIBUTING_UPSTREAM.md`
