# ADR-002: Enable project lessons with an atomic additive command

**Status**: Accepted — Implemented
**Date**: 2026-09-11
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: ADR-001 (separate project-local validator), GitHub issue #67

## Context

Issue #67 requires a safe post-initialization operation for repositories that were initialized before project-local lessons were enabled. The current `--with-project-lessons` path lives inside the full initializer in `kb_bootstrap/cli.py`. After creating lesson artifacts, that initializer rewrites `qmd.json`, both QMD collection declarations, and always-available generated skills. A full rerun therefore has a broader mutation boundary than the requested operation.

The project-local contract established by #28 consists of four artifacts:

- `kb/lessons/SCHEMA.md`;
- `kb/lessons/index.yaml`;
- root `lesson-stores.json`;
- `.agents/skills/kb-capture/SKILL.md`.

ADR-001 and merged Issue #65 provide a separate read-only validator for the project-local registry. The templates already provide canonical initial bytes. No current command enables only this contract, and no requirement authorizes modifying existing lessons, routing, QMD declarations, unrelated skills, human-authored files, shared stores, or external repositories.

The mutation must fail closed. A partially present contract is ambiguous: filling its missing files could combine incompatible human/generated state. An existing complete contract may contain real lesson data or local routing decisions and must not be overwritten. Symlink traversal would cross the explicit repository boundary. Multiple direct writes could leave a partial contract after failure.

## Decision

Add an explicit public command:

```text
kb-bootstrap enable-project-lessons --target <repository-root>
```

The command uses one bounded helper that performs a complete read-only preflight before mutation.

### What this IS

- An additive post-init operation for an already initialized `kb-bootstrap` repository.
- A four-artifact contract installation when all four artifacts are absent.
- A deterministic successful no-op when all four artifacts exist and the project-local registry plus routing contract are valid.
- A fail-closed result when the target is not initialized, the contract is partial, any destination/path component traverses a symlink, an existing contract is malformed/conflicting, or an atomic write cannot complete.
- A bounded installation with per-file exclusive no-overwrite publication and compensating rollback: stage all four files inside their destination directories, publish only to absent destinations, and on failure remove only files still proven to have been installed by this invocation plus all owned temporary files.
- A sanitized receipt listing only stable relative artifact names and whether the result was `enabled` or `already enabled`.

### What this IS NOT

- It is not a full initializer rerun.
- It does not rewrite or normalize an existing project-lessons contract.
- It does not alter QMD configuration, unrelated skills, `AGENTS.md`, `.gitignore`, existing lesson content, shared stores, or external repositories.
- It does not repair partial contracts or infer which side of a conflict is authoritative.
- It does not change lesson IDs, schema ownership, lookup semantics, promotion, caching, or synchronization.

A repository is considered already initialized only when the established bootstrap markers `qmd.json`, `qmd/collections/wiki.yaml`, `qmd/collections/raw.yaml`, and `.agents/skills/kb-lookup/SKILL.md` are regular non-symlinked files inside the explicit target.

The routing contract is accepted only when it selects exactly the local store, with version `1`, `capture_store: local`, and `local.path: kb/lessons`, and does not define a writable shared destination. The project-local registry must pass the ADR-001 validator. Existing complete contract bytes are preserved exactly.

## Alternatives Considered

### Alternative 1 — Rerun the initializer with `--with-project-lessons`

Rejected. It has already been observed to rewrite unrelated QMD declarations and generated skills. Its mutation boundary is incompatible with Issue #67.

### Alternative 2 — Fill whichever contract files are missing

Rejected. A partial contract may contain user-authored or version-skewed state. Guessing how to complete it can create a false-valid routing/schema combination. The safe response is a sanitized blocking result.

### Alternative 3 — Overwrite all four artifacts from templates

Rejected. Existing indexes can contain lessons, routing can include reviewed local configuration, and generated skills may be locally extended. Overwrite would destroy valid consumer state.

### Alternative 4 — Write files directly in sequence

Rejected. A failure after one or more direct writes leaves a partial contract. Staging plus per-file exclusive publication and compensating removal bounds the failure. There is no portable all-or-nothing filesystem transaction across the four destination paths, so the command does not claim global atomic visibility.

### Alternative 5 — Add another initializer flag or generator mode

Rejected. Placement and lifecycle are not content topology modes. A distinct command makes the narrow post-init intent and mutation boundary explicit.

## Consequences

### What gets easier

- Existing initialized consumers can enable local lesson capture without risking unrelated QMD or skill configuration.
- Agents receive deterministic enabled/already-enabled/blocked receipts.
- Partial, malformed, conflicting, path-escaping, and symlinked state cannot be silently combined with templates.
- The resulting registry can be verified by the existing project-local validator.

### What gets harder

- The CLI owns a second lifecycle operation in addition to initialization.
- Four-artifact installation needs staging, exclusive publication, ownership-aware rollback, and injected-failure tests.
- Complete existing contracts require both routing validation and project registry validation before the command may report a no-op.
- Consumers with partial contracts must resolve them explicitly rather than receiving automatic repair.

### What does not change

- Default initialization remains unchanged and project lessons remain opt-in.
- Existing lesson data, IDs, capture routing, lookup precedence, shared-store policy, and consumer ownership remain unchanged.
- No network, GitHub, QMD indexing, external-store write, or background operation is added.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Eligible initialized repository receives exactly four artifacts | `tests/test_project_lesson_enablement.py::test_enables_only_project_lesson_contract` | passing |
| Resulting registry passes ADR-001 validation | `tests/test_project_lesson_enablement.py::test_enables_only_project_lesson_contract` | passing |
| Complete valid contract is a deterministic byte-preserving no-op | `tests/test_project_lesson_enablement.py::test_complete_contract_is_idempotent_no_op` | passing |
| Unrelated QMD and skills remain byte-for-byte unchanged | `tests/test_project_lesson_enablement.py::test_enables_only_project_lesson_contract` | passing |
| Partial, malformed, conflicting, escaping, or symlinked state blocks before mutation | focused rejection cases in `tests/test_project_lesson_enablement.py` | passing |
| Injected replacement failure leaves no owned partial contract or temporary files and preserves foreign replacements | `tests/test_project_lesson_enablement.py::test_atomic_failure_rolls_back`, `test_race_replacement_is_not_deleted_during_rollback` | passing |
| CLI exposes the explicit post-init command and sanitized receipt | `tests/test_project_lesson_enablement.py::test_cli_enablement_receipt`, `test_receipt_is_sanitized` | passing |

## Rollback

Before release, revert the implementation PR. After consumers run the command, framework rollback removes only the command from future versions; it must not automatically delete consumer-owned lesson artifacts. A consumer that wants to undo an unused empty contract may explicitly remove the four files, but any contract containing lessons or local edits requires consumer review. No automatic rollback command is introduced.

## References

- GitHub issue #67
- GitHub issues #28 and #65
- ADR-001
- `kb_bootstrap/cli.py`
- `kb_bootstrap/project_lesson_registry.py`
- `kb_bootstrap/templates/lessons/`
- `kb_bootstrap/templates/skills/kb-capture/SKILL.md`
