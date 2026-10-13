# ADR-029: Create new research captures with exclusive paths

**Status**: Proposed
**Date**: 2026-10-13
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #125; ADR-010, ADR-022, ADR-024, ADR-027

## Context

At main `2a9161dbf11047f7331c7b4771a096a5eb633d7f`, the packaged `capture_page.py` uses `next_number()` to scan `raw/NNN-*.md`, then writes image targets with `Path.write_bytes()` and Markdown with `Path.write_text()`. Neither reserves the chosen number nor requires an absent destination. A synthetic local reproduction imported this script without Surf/network: two threads scanned an empty raw directory before a barrier, both selected 001, then wrote different bytes to the same path; one payload replaced the other. A second synthetic collision pre-created the chosen path and the existing Markdown write replaced it. The reproducible receipt is Issue #125 comment 6154274412; no full Surf capture or symlink test was run.

Accepted ADR-027 covers selecting existing RawCapture files for Git retention. It explicitly excludes a new copier/output allocator and says creation of a new capture is outside its scope absent a separately authorized path or no-overwrite rule. Issue #125 criterion 5 separately requires no renumber/overwrite and concurrent allocation/publication that cannot overwrite another capture. ADR-010 and ADR-024 are not capture-writer contracts and do not authorize origin access.

### Problem statement

A new research capture must not silently replace an existing or concurrently created capture/image at its selected path, and a path inside the study must not escape through a symlinked ancestor.

## Decision

If separately accepted, the existing `capture_page.py` writer will create only the candidate Markdown and image paths derived by its existing numbering/slug convention when those exact targets are absent and their parent paths remain within the explicitly selected study without symlink traversal. It will not overwrite, renumber, retry with a different ID, or follow a raced-in target. A collision or unsafe parent blocks that output and reports a sanitized failure.

The guarantee is per file, not a transaction over Markdown plus images. If an earlier selected image was exclusively created before a later output fails, preserve that created file and report partial output truthfully; never remove a target unless ownership of that exact created file is positively established. No all-or-nothing publication or concurrent directory snapshot is claimed.

### What this IS

- Use the current explicit study directory and existing candidate naming convention; no global allocator or persistent ID registry.
- Use exclusive creation for each selected output, including images, so a race-created target is preserved and the attempted file fails.
- Reject symlinked/escaping study, raw, or image path components before writing; do not create or repair directory structure outside existing documented setup behavior.
- Keep Surf collection and image selection behavior unchanged; this contract concerns local output safety only.
- Emit an honest sanitized result distinguishing complete success, blocked-before-write, and partial creation when an owned earlier file exists.

### What this IS NOT

No new capture format/schema, copy/import service, automatic Git staging/commit/push, retry/renumber allocator, rollback deletion, multi-file atomicity, network policy change, consumer publication, or process for resolving capture identity across studies. ADR-027 remains limited to existing-file selection and Git delivery.

## Consequences

### What gets easier

A selected capture path cannot silently replace prior or racing capture evidence; callers can distinguish a blocked write from partial image creation.

### What gets harder

A collision now stops instead of finding another sequence number, and interrupted multi-file captures may leave owned partial files that require explicit later review. Symlink/path checks and output receipts add writer complexity.

### What does not change

Existing captured Markdown and numbering remain untouched. No automatic retry, remote publication, consumer write, new dependency, external acquisition, ADR-024 envelope conversion, or claim of multi-file atomicity is introduced.

## Alternatives Considered

- **Keep scan-then-write:** rejected because the reproduced concurrent scan selected the same number twice and a later write replaced the prior bytes.
- **On collision, silently choose the next free number:** rejected because it hides a concurrent identity conflict and can renumber evidence without explicit caller confirmation.
- **Write images and Markdown as one atomic transaction:** rejected because existing contracts offer no transaction across multiple paths and rollback could delete a raced or previously owned file.

## Test Contract

| Claim if implemented | Test | Currently |
|---|---|---|
| Existing Markdown candidate is preserved and capture fails | `tests/test_capture_page.py::test_existing_markdown_target_is_not_overwritten` | not yet written |
| Concurrent writers cannot replace one another's selected output | `tests/test_capture_page.py::test_racing_markdown_creation_preserves_winner` | not yet written |
| Selected image targets use the same exclusive/no-overwrite rule | `tests/test_capture_page.py::test_existing_image_target_is_not_overwritten` | not yet written |
| Symlinked or escaping parent components block before writes | `tests/test_capture_page.py::test_symlinked_output_parent_blocks` | not yet written |
| Failure after an owned image creation reports partial outcome and preserves bytes | `tests/test_capture_page.py::test_later_markdown_failure_reports_partial_without_deleting` | not yet written |
| Existing Surf capture collection, names, and frontmatter remain compatible | `tests/test_capture_page.py::test_successful_capture_format_is_unchanged` | not yet written |

## Rollback

Before acceptance, withdraw this proposal; no runtime state changes. After acceptance, reverting implementation must not delete captures or images already created. Changing collision, numbering, symlink, or partial-output semantics requires a superseding ADR.

## References

- Issue #125 acceptance criteria and research/reproduction comments 6154255408, 6154274412.
- Issue #124 and accepted ADR-027, which excludes new capture creation from its existing-file Git-retention boundary.
- `kb_bootstrap/templates/skills/market-research/scripts/capture_page.py`; `tests/test_market_research_skill.py`.
