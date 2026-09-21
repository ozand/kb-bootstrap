# ADR-009: Publish an OKF bundle as an exclusive ZIP file

**Status**: Proposed
**Date**: 2026-09-21
**Authors**: Pi coding agent
**Supersedes**: ADR-008 (accepted directory-publication mechanism)
**Related**: GitHub issue #88; ADR-003 (minimal OKF profile); ADR-005 (exclusive graph publication); ADR-008 (logical published bundle)

## Context

ADR-008 correctly preserves `kb/raw/` and `kb/lessons/` in the working tree and defines a logical published bundle. Its directory-output publication mechanism, however, requires a same-parent directory rename to an absent target.

A post-acceptance research check established a cross-platform conflict: on POSIX, renaming a staging directory over a concurrently created empty destination directory can replace that destination. A pre-check does not close the race. Reserving the output name with `mkdir` avoids overwrite but exposes a partially populated directory if a later copy fails. Neither mechanism proves both no-overwrite and no partial visible publication.

The existing graph export already publishes one complete staged file through an exclusive hard-link operation and fails closed when hard links are unavailable. Issue #88 requires a published artifact excluding raw/lesson content, but does not require that artifact to be a directory.

## Decision

Supersede ADR-008's directory-output publication mechanism. The future opt-in command publishes one ZIP file:

```text
kb-bootstrap export-published-bundle \
  --project-root . --dir kb --output published-okf.zip
```

The ZIP is the complete published artifact. It contains only selected UTF-8 Markdown files with relative POSIX member paths: ordinary canonical concepts plus exact lowercase reserved `index.md` and `log.md` files. It excludes all non-Markdown files and every `raw` or `lessons` directory case-insensitively. Source discovery recognizes reserved filename variants case-insensitively: a non-lowercase variant blocks publication with a sanitized spelling-category diagnostic rather than being silently excluded or published as a concept. Working-tree source files remain authoritative and unchanged.

The output must be an absent regular-file path, relative to and contained by the explicit project root, outside the canonical root, with an existing non-symlinked parent. Directory output paths are rejected. The command stages one complete ZIP file in the output parent, flushes it, rechecks parent identity and target absence, then publishes with an exclusive hard link. Missing hard-link support, a race-created target, unsafe parent state, or a write failure blocks without overwrite. Owned staging files are removed where possible.

ZIP members are sorted by relative POSIX path and use `ZIP_STORED`. Each member uses fixed DOS-compatible timestamp `1980-01-01T00:00:00`, mode `0o644`, empty comment, no extra fields, and no directory entries. The exact source bytes are copied only after an identity/content recheck. This is a deterministic, single-file publication contract; it does not introduce an archive registry, automatic distribution, network upload, or extraction command.

### Bundle eligibility and report

ADR-008's source-selection, reserved-file, warning, and no-migration rules remain the intended policy except where this decision replaces directory output and case-variant handling with ZIP output and a blocking spelling rule. A source mutation, unsafe path, malformed ordinary concept, non-lowercase reserved variant, forbidden reserved frontmatter, or malformed ISO log date blocks publication. Readability policy warnings do not change exit status.

The command writes stdout only. Its report is deterministic: a heading, sorted `WARNING:` lines, selected concept/reserved counts, excluded-layer summary, sorted `ERROR:` lines when blocked, one `RESULT:` line, and `output: created` only after exclusive publication. Exit `0` means published; exit `1` means blocked; argparse usage remains exit `2`.

This report establishes only the local published-bundle profile, not universal strict OKF conformance, source truth, QMD readiness, policy compliance, or successful extraction by another tool.

### Compatibility and migration

No existing generated repository is rewritten. `kb/raw/`, `kb/lessons/`, QMD collections, lesson stores, raw search, current `validate`, and graph export retain their paths and behavior. A consumer choosing the new opt-in command must provide an explicit `.zip` output path and use the resulting file as its published artifact. It must not expect an output directory.

Agent-facing upgrade documentation remains a later issue-owned deliverable. It must tell agents to inspect first, run the command only with an explicit output path, preserve source trees, and defer publication when warnings/errors require owner remediation.

## Alternatives Considered

### Alternative 1 — Keep ADR-008 directory rename publication

Rejected. POSIX can replace a concurrent empty destination directory, violating no-overwrite.

### Alternative 2 — Reserve the directory with `mkdir`, then copy files

Rejected. It makes a partial directory visible if materialization fails after reservation.

### Alternative 3 — Weaken the directory safety guarantee

Rejected. Issue #88 requires a safe publication boundary; documenting a known partial/overwrite race is not fail-closed.

### Alternative 4 — Publish a TAR file

Rejected. The standard TAR metadata surface is larger. ZIP with explicitly fixed members and the existing file-publication primitive is smaller for the current supported contract.

### Alternative 5 — Publish a ZIP file

Chosen. One complete staged file can be published exclusively with the proven graph-export pattern and has no partially visible directory state.

## Consequences

### What gets easier

- The output is one complete, no-overwrite artifact.
- The publication primitive reuses existing tested file-safety patterns.
- Raw/lesson working-tree contracts remain untouched.

### What gets harder

- Consumers must extract or otherwise consume a ZIP artifact to browse its files.
- Deterministic ZIP metadata requires explicit implementation and tests.
- ADR-008's accepted directory-output contract is replaced and must be reflected in migration guidance.

### What does not change

- Canonical Markdown remains authoritative.
- No consumer migration, network publication, archive registry, automatic extraction, QMD update, source rewrite, or runtime-state cleanup is added.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Output ZIP includes only selected Markdown and excludes raw/lessons/non-Markdown | output member matrix | not yet written |
| ZIP bytes are identical on repeated runs from unchanged source | deterministic ZIP fixture | not yet written |
| Fixed member metadata contains no host timestamps, owner names, absolute paths, or directory entries | ZIP metadata inspection | not yet written |
| Existing/race-created output is preserved and staging is cleaned | exclusive hard-link/race fixture | not yet written |
| Unsupported hard links fail closed without output | hard-link failure fixture | not yet written |
| Source changes during read block publication without output | identity/content recheck fixture | not yet written |
| Reserved-file warnings/errors and report ordering are deterministic | bundle eligibility fixture matrix | not yet written |
| Current validate, graph export, QMD, and lesson workflows remain unchanged | full regression suite | not yet run after implementation |

## Rollback

Revert the future implementation commit. The command creates no source changes. A successfully published ZIP is a derived artifact and is not automatically deleted; its owner decides whether to remove it. ADR-008 remains in history as the superseded directory-publication decision.

## References

- GitHub issue #88
- ADR-005
- ADR-008
- `kb_bootstrap/canonical_graph_export.py`
- Python `os.link` and `zipfile` standard-library contracts
