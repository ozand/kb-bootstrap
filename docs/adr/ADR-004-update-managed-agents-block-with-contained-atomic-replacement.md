# ADR-004: Update the managed AGENTS.md block with contained atomic replacement

**Status**: Accepted — Implemented
**Date**: 2026-09-13
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issue #60; ADR-002 (bounded exclusive file installation); ADR-003 (stable-checkout validation boundary)

## Context

Issue #60 requires the explicitly managed governance block in `AGENTS.md` to remain safe under symlinks, path escape, concurrent modification, partial writes, and filesystem errors while preserving human-authored content.

The current `update_agents_file(path, repository)` implementation reads a path, validates managed markers, computes replacement text, creates parent directories, and writes directly through `Path.write_text`. It has four gaps:

1. no explicit project root bounds the target path;
2. path reads and writes follow symlinks;
3. a second actor can change the file after it is read and before it is written;
4. direct truncate/write can expose partial content after interruption.

The marker parser and generated block are already bounded: exactly one marked block is appended or replaced, malformed/duplicate/reversed markers block, and sequential tests verify preservation and idempotence. The hardening should retain this content contract rather than redesign governance instructions.

There is no portable cross-platform filesystem transaction that also serializes every external writer. Atomic rename/replacement can prevent partial destination bytes, but it cannot create a race-free snapshot after the final comparison. The command must therefore fail closed on detected changes and document a stable-checkout boundary.

## Decision

Extend the public command to require or accept an explicit project root:

```text
kb-bootstrap agents-governance \
  --repo owner/repository \
  --project-root <repository-root> \
  --file AGENTS.md
```

`--project-root` defaults to the current directory. `--file` must be a relative path contained by that root. Absolute paths, `..` escape, NULs, and paths outside the root are rejected with sanitized diagnostics.

### Preflight and path safety

Before reading or creating anything:

- inspect the lexical project-root and target path components;
- reject a symlinked project root, target, or existing parent component;
- require the project root to be an existing directory;
- require an existing target to be a regular file;
- allow creation only when the target parent already exists as a contained regular directory;
- do not create arbitrary parent directory trees.

The helper receives `project_root` and target path separately. It reports only stable relative names/categories, never absolute paths or file contents.

### Source observation

For an existing target, capture before planning:

- exact bytes;
- exact content bytes;
- stable file identity where available (`st_dev`, `st_ino`);
- mode bits to preserve.

Decode as UTF-8. Invalid UTF-8 blocks without mutation. Marker parsing and replacement preserve all bytes outside the marker range exactly. New managed text uses LF internally; surrounding CRLF or other bytes are not normalized. Because marker replacement is computed against decoded text, exact unmanaged UTF-8 bytes must compare equal before publication.

For a missing target, record the missing state. If a file appears before publication, fail closed and preserve it.

### Staging and publication

- Compute the complete new UTF-8 byte sequence in memory.
- If bytes are unchanged, return a successful no-op without staging.
- Create one uniquely named temporary file in the existing target directory using exclusive creation.
- Write all bytes, flush, and `fsync` the temporary file.
- Recheck target path safety and source state immediately before publication:
  - existing target must still be the same regular non-symlink file identity and exact bytes;
  - missing target must still be absent and non-symlink.
- For an existing target, publish with same-directory atomic `os.replace` and preserve original mode bits on the staged file before replacement.
- For a missing target, publish with the platform's hard-link exclusive no-overwrite primitive. If the filesystem or policy does not support hard links, fail closed with a sanitized atomic-update category rather than overwrite a race-created file.
- Remove owned temporary files on every failure. Never delete or overwrite a destination whose identity no longer matches the observed source state.

Atomicity means readers see either the complete old file or the complete new file at the replacement point. It does not mean the command locks out all future writers or provides a cross-process transaction after publication.

### Concurrent modification

A change detected before publication produces `RESULT: BLOCKED` and leaves the observed/current target untouched. The command does not retry automatically. Operators inspect the latest file and run the command again explicitly.

A writer changing the path after the final recheck remains a residual filesystem race. Same-directory replacement minimizes the window but does not eliminate it across platforms. Tests inject changes at every controllable seam, and documentation requires a stable checkout during the bounded operation.

### Managed content contract

The exact start/end markers and governance block content remain unchanged. Only the bounded text between one valid marker pair is replaced. Duplicate, missing, or reversed marker structures remain blocking. Existing file bytes outside the managed range must be preserved byte-for-byte.

## Alternatives Considered

### Alternative 1 — Continue direct `Path.write_text`

Rejected. It follows symlinks, has no containment boundary, cannot detect concurrent edits, and may expose partial content.

### Alternative 2 — Use a repository lock file

Rejected for this increment. Other editors do not honor it, stale-lock recovery adds policy, and it cannot replace source identity/content rechecks.

### Alternative 3 — Require callers to pass any absolute file path

Rejected. It makes repository governance capable of writing outside the explicit owner root and weakens sanitized reporting.

### Alternative 4 — Write a temporary file and call `os.replace` without rechecking

Rejected. It solves partial destination bytes but can still clobber a concurrent human edit or race-created target.

### Alternative 5 — Automatically merge a concurrent edit

Rejected. Merging human-authored instructions is a semantic decision and may silently corrupt governance. The safe response is fail closed and explicit retry.

### Alternative 6 — Build a generalized secure filesystem transaction layer

Rejected as overengineering. Issue #60 needs one bounded managed-file operation. Small private helpers are sufficient.

## Consequences

### What gets easier

- The command cannot intentionally escape the explicit repository root.
- Static symlinks and detected concurrent changes block before replacement.
- Readers do not observe a partially written destination during successful replacement.
- Human-authored content remains byte-stable outside the managed block.
- Failure reports remain deterministic and sanitized.

### What gets harder

- Callers need a stable project root and existing target parent directory.
- Existing files with invalid UTF-8 or ambiguous markers require manual correction.
- Atomic/exclusive publication differs for existing versus missing files and needs injected-failure tests.
- Concurrent writers after the final recheck remain a documented residual race.
- Mode preservation and Windows/POSIX filesystem behavior require bounded platform tests.

### What does not change

- The managed marker names and block text remain unchanged.
- Normal scaffold generation does not modify downstream `AGENTS.md`.
- The command does not edit unmanaged instructions, run GitHub operations, change repository permissions, or repair unrelated files.
- No persistent lock, daemon, network dependency, or generalized transaction service is added.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Contained regular target creation and update succeed | governance creation/update tests | passing |
| Absolute, escaping, NUL, unavailable-root, and missing-parent paths block without mutation | `test_absolute_escape_nul_missing_parent_and_unavailable_root_block` | passing |
| Project-root, parent, and target symlinks block before read/write | static and staged-parent symlink tests | passing |
| Unmanaged bytes and supported existing mode remain unchanged | `test_append_and_update_preserve_surrounding_bytes_and_mode` | passing |
| Detected concurrent modification preserves the foreign edit | `test_concurrent_modification_blocks_and_preserves_foreign_edit` | passing |
| Existing replacement is atomic and injected write/replace failures preserve old bytes | atomic/staging failure tests | passing |
| Missing-target publication never overwrites a race-created file and unsupported hard links fail cleanly | missing-target race/capability tests | passing |
| Temporary artifacts are cleaned and reports contain no private paths/content | cleanup and sanitized boundary tests | passing |
| Repeated unchanged update is a no-op | `test_repeated_update_is_idempotent` | passing |

## Rollback

Revert the implementation PR. No consumer file is automatically migrated by the framework. Files already updated by an explicitly invoked command remain valid managed-block files and are not automatically restored. Repository owners may use version control to revert an unwanted managed-block update.

## References

- GitHub issue #60
- `kb_bootstrap/agents_governance.py`
- `tests/test_agents_governance.py`
- `docs/AGENTS_GOVERNANCE_BLOCK.md`
- ADR-002
- ADR-003
