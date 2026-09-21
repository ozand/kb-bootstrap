# ADR-008: Validate a logical published OKF bundle

**Status**: Superseded by ADR-009
**Date**: 2026-09-21
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issue #88; ADR-003 (minimal OKF profile); ADR-005 (canonical graph export)

## Context

Issue #88 requires raw captures and separate lesson registries to stay outside a published OKF bundle while preserving their established repository paths. Current consumer layouts keep them in `kb/raw/` and `kb/lessons/`; QMD declarations, lesson registries, generated skills, and migration guidance depend on those paths. Moving them would be a destructive compatibility break.

The official OKF v0.2 specification defines a bundle as a Markdown tree. Non-reserved Markdown concepts require frontmatter and `type`; exact lowercase `index.md` and `log.md` are reserved. An index is optional at any level; only a root index may carry an `okf_version` key in frontmatter. The specification says index sections and entries SHOULD follow its shown shape. A log is optional at any level; its date headings MUST use ISO `YYYY-MM-DD`, while newest-first ordering and prose entry form are illustrated format guidance rather than separately labelled MUST requirements.

ADR-003 intentionally validates ordinary concepts only and excludes raw, lessons, and reserved files. No current command produces or validates a published bundle boundary.

## Decision

Keep `kb/` as a working-tree root. Do not move, delete, rewrite, or automatically migrate `kb/raw/` or `kb/lessons/`.

Add a future opt-in `export-published-bundle` command, separate from the existing `validate` command. It validates one explicit canonical root and creates one explicit published-bundle directory containing only the eligible Markdown files. It never changes the working-tree source, QMD configuration, or lesson ownership.

```text
kb-bootstrap export-published-bundle \
  --project-root . --dir kb --output published-okf
```

The output path must be absent, repository-contained, outside `--dir`, and have an existing non-symlinked parent. The command creates a uniquely named staging directory in that parent, populates and flushes it, then uses a same-parent `os.rename` publication attempt. A target existing at rename time causes atomic failure without overwrite; owned staging content is removed where possible. The report is on stdout and has stable sections: `=== Published OKF Bundle Validation ===`, selected ordinary-concept count, selected reserved-file count, excluded-layer summary, and `RESULT: OK | BLOCKED`. Eligibility or source-safety failures return `1`; argument errors retain argparse exit `2`. Warnings do not change a successful exit.

The published artifact contains only Markdown: ordinary canonical concepts plus case-insensitive reserved `index.md`/`log.md`. It excludes every non-Markdown file and every `raw` or `lessons` directory case-insensitively. This matches the current ordinary-concept and graph-export classification, avoiding a new case-sensitive membership divergence. The exact-case spelling required by upstream is recorded as a local publication warning for a reserved case variant, not a reason to reclassify or hide it.

The existing `validate` command and graph export retain their current result semantics. They do not become a claim that all files under `kb/` form an OKF bundle.

### Reserved-file rules

For the future opt-in validator:

- `index.md` and `log.md` are optional and recognized case-insensitively for compatibility with current traversal and graph export;
- a root `index.md` may have no frontmatter, or a parseable mapping with optional string `okf_version: "0.2"`; unknown keys are copied unchanged and reported as a warning only;
- nested `index.md` must have no frontmatter per §8; every `log.md` must have no frontmatter under the §3.1 reserved-not-concept boundary and §9 log format;
- index headings/list entries are an opt-in readability policy, checked line-by-line outside both backtick and tilde fenced blocks; this is not a Markdown or link validator;
- every log date heading that is present must contain a valid ISO `YYYY-MM-DD`; heading level, newest-first order, and list entries are opt-in readability warnings rather than asserted OKF requirements;
- existing UTF-8, containment, relative-path, and symlink checks apply to every reserved file and its parent;
- diagnostics expose only relative POSIX paths and rule categories.

The line-oriented readability filter treats lines beginning with three or more matching backticks or tildes as fences and ignores headings/lists until the matching fence closes. Empty bodies pass. A root-index unknown key warns and remains copied; malformed frontmatter, forbidden nested/log frontmatter, malformed date headings, unsafe paths, or symlinks block before publication. The command does not validate a CommonMark AST, resolve index links, infer metadata, validate free-form prose, read outside the root, or fetch sources.

### Compatibility and migration

Existing consumers retain their working-tree layout and current `validate` behavior. The new export is opt-in and fails closed when published-bundle rules are not met. It reports remediation categories but never migrates files.

A later documentation increment must provide agents with versioned upgrade preflight, dry-run, owner/remediation mapping, and rollback or deferral guidance. No consumer should be told to relocate raw or lessons automatically.

## Alternatives Considered

### Alternative 1 — Physically move raw and lessons outside `kb/`

Rejected. It breaks QMD raw collections, lesson-store routing, generated skills, existing consumers, and relative links; it also risks loss of active capture and lesson state.

### Alternative 2 — Tighten the existing `validate` command immediately

Rejected. It changes established output and exit behavior for consumer working trees. A separate opt-in command makes the new claim explicit and migration measurable.

### Alternative 3 — Use exact-case reserved classification only

Rejected. It would diverge from existing profile and graph-export membership, producing inconsistent published and graph node sets. Case variants remain reserved for compatibility; the export emits a local publication warning that owners may remediate explicitly.

### Alternative 4 — Validate only UTF-8 for reserved files

Rejected. It cannot detect root-index frontmatter misuse or malformed log chronology.

### Alternative 5 — Build an archive/export now

Rejected. A bare validation report cannot enforce the requested published-content boundary for a later archive/copy operation. The selected output is one contained directory, not a generalized distribution format, copy pipeline, or artifact lifecycle.

## Consequences

### What gets easier

- Consumers can distinguish their working tree from an explicitly eligible published OKF view.
- Existing raw and lesson workflows keep their paths and owners.
- Reserved-file failures are diagnosed before a consumer claims a full OKF bundle.

### What gets harder

- Consumers that want to publish must meet explicit index/log rules or defer publication.
- Case variants of reserved filenames need an owner-controlled rename before publication.
- A new command and migration guidance add a small maintenance surface.

### What does not change

- Existing ordinary-concept validation, QMD declarations, raw retrieval, lesson schemas, graph export, source bytes, and consumer files remain unchanged. Published membership and graph export both retain the current case-insensitive reserved exclusion.
- No network, external publishing, archive creation, synchronization, automatic migration, or deletion is added.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Working-tree raw/lesson paths remain unchanged | initialization and project-lesson regression tests | passing baseline |
| Published output contains only Markdown and excludes raw/lessons without source mutation | boundary, non-Markdown, output-tree, and source-byte fixture test | not yet written |
| Root/nested reserved-file rules distinguish OKF requirements from local readability warnings | reserved index/log fixture matrix | not yet written |
| Case variants remain consistently excluded from the published and graph views and emit a publication warning | case-variant compatibility/export fixture | not yet written |
| Date, empty body, prose, backtick/tilde fences, list, duplicate-date, and order cases do not overclaim full Markdown validation | line-oriented log/index fixture matrix | not yet written |
| Unsafe/symlinked reserved files block with sanitized diagnostics and leave an absent output | symlink/publication fixture matrix | not yet written |
| New command stdout report and exit codes are deterministic and separate from existing `validate` | CLI presentation/exit fixture tests | not yet written |
| Existing `validate` and graph-export semantics remain unchanged | existing CLI/profile/export regression suite | not yet run after implementation |

## Rollback

Revert the future implementation commit. The validator is read-only and does not move or rewrite consumer files, so no content rollback is required. Any owner-performed filename correction remains owner-controlled.

## References

- GitHub issue #88
- Open Knowledge Format v0.2 specification, sections 3, 8, 9, 11, and 12
- ADR-003
- ADR-005
- `kb_bootstrap/canonical_profile.py`
