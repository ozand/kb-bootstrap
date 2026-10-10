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

If accepted, capture publication retains explicitly selected captured Markdown and its required selected attachments as ordinary files under an explicit owner-repository study/raw path. The operation's successful local result is a complete set of new files in the selected working tree plus a sanitized file list suitable for review; Git staging, commit and remote push remain separate, explicit repository workflow actions.

### What this IS

1. The caller explicitly selects the owning repository root, existing study directory, accepted capture envelope, and complete set of Markdown/attachment members to retain. The operation does not infer a consumer repository from remotes, discover other studies, fetch origins, or choose an external destination.
2. Preserve captured Markdown bytes as supplied UTF-8; do not summarize or rewrite them. Keep the accepted ADR-024 envelope/provenance in a deterministic, bounded sidecar for the selected capture set, and preserve the existing `kb/research/<study>/raw/NNN-<slug>.md` relative-reference convention where the selected owner study uses it. Attachments are included only when explicitly selected and referenced by the capture. No format claims that Markdown equals an unavailable external original or proves lossless extraction.
3. Derive each new output path from an explicit safe study-relative target and selected basename/capture identity. Reject unsafe, duplicate, case-fold-colliding, or already-existing file paths; never overwrite, replace, renumber, or repair prior captures. Preserve every pre-existing target. The caller's selection is the complete publication set; no directory scan is used to silently add files.
4. Write only new, exclusively created files. Report each successfully created relative path and any blocked/partial outcome honestly. If a later member fails, preserve all pre-existing files and all newly created files from that attempt, report the exact bounded partial set, and require a new explicit reviewed operation to continue. Do not delete prior or partial capture files as automatic rollback and do not claim multi-file atomicity.
5. A successful local capture operation does not itself stage, commit, push, create a PR, or publish to a consumer repository. A separately authorized normal Git workflow may add exactly the reported selected capture/provenance files to a reviewable commit; unrelated workspace files are not implicitly included. Remote publication remains separately targeted and authorized under ADR-022 and repository contribution policy.
6. Reuse ADR-024 whole-envelope validation and ADR-010 path constraints for selected data without changing either contract. Preserve ADR-026's distinction between a retained representation and a verified retained original. Owner-authored permission/retention labels are descriptive only and do not authorize publication.

### What this IS NOT

This is not a ZIP/archive output or reader, generic importer, external acquisition or conversion engine, global source registry, automatic `git add`/commit/push, automatic publication to a consumer repository, source renumbering, overwrite/repair, or a transaction across multiple files. It does not assert Git tracking or remote publication merely because a working-tree file exists. It does not alter ADR-010 manifest v1, ADR-024 source-capture metadata, or the accepted ADR-025 historical text. If accepted, ADR-025 becomes superseded; its archive implementation is not authorized by this decision.

### Success criteria

A future implementation copies only the caller-selected captured Markdown and required selected attachments to the explicit owner-repository paths as ordinary readable files, preserves exact Markdown bytes and relative references, rejects all target/path collisions without overwriting, truthfully reports per-file partial outcomes, and performs no hidden discovery, network fetch, commit, push or consumer write. A separately authorized normal repository workflow can verify and commit exactly that selected set without staging unrelated files.

## Consequences

### What gets easier

People and tools can read captured Markdown directly in the owning repository and follow existing relative evidence links without extracting an archive.

### What gets harder

Each capture and required attachment is a separate filesystem operation, so a partial run can leave a reported partial set. Repository changes are reviewable/upstream or owner-repository changes, but commit and remote publication still require a distinct explicit workflow. Existing captures are immutable inputs; a changed capture needs a new path/revision rather than replacement.

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
| Selected Markdown bytes, metadata sidecar, attachment bytes, and relative references are preserved at explicit repository paths | `tests/test_capture_repository_publication.py::test_selected_markdown_and_attachments_are_retained_verbatim` | Not yet written |
| Existing, unsafe, duplicate, or case-fold-colliding destinations block without overwrite or renumbering | `tests/test_capture_repository_publication.py::test_existing_and_colliding_capture_paths_are_preserved` | Not yet written |
| Multi-file failure reports partial creation and preserves both prior and created files without claiming transactionality | `tests/test_capture_repository_publication.py::test_partial_capture_publication_is_honest_and_non_destructive` | Not yet written |
| Only explicitly selected capture files enter the reported set; no discovery or origin fetch occurs | `tests/test_capture_repository_publication.py::test_no_discovery_or_origin_access` | Not yet written |
| Local operation does not stage/commit/push or include unrelated repository changes | `tests/test_capture_repository_publication.py::test_capture_write_has_no_git_side_effects` | Not yet written |

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
