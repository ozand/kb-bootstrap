# ADR-001: Validate project-local lesson registries with a separate schema-aware command

**Status**: Accepted — Implemented
**Date**: 2026-09-10
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issue #65

## Context

Issue #65 reports that the existing `validate-lesson-registry` command validates the shared `KB-XXXX` registry schema, while the generator creates a different project-local `PROJECT-XXXX` schema under `kb/lessons/`. This is **verified** in `kb_bootstrap/lesson_registry.py:13-14,33-127`, `kb_bootstrap/cli.py:298-313`, `kb_bootstrap/templates/lessons/index.yaml:1-4`, and `kb_bootstrap/templates/lessons/SCHEMA.md:23-31`. The current command expects `root/lessons/` and `root/index.yaml`; the generated project-local contract uses `kb/lessons/index.yaml` and does not contain the shared registry's top-level `count` field.

The repository already has separate shared-registry tests and generator contract tests. No project-local validator exists in the current CLI or package. **Verified.** Changing the generator to emit the shared layout would alter an existing generated data contract. A dedicated validator addresses the reported defect while preserving both schemas. **Theory grounded in the verified file contracts.**

### Problem statement

A generated project-local lessons store must have a deterministic, read-only validator that checks its own documented contract without treating it as a shared `KB-XXXX` registry.

### Prior art

The existing `validate_registry()` function and `tests/test_lesson_registry.py` provide the repository's current pattern for fail-closed registry validation, ID consistency, index/file matching, and deterministic error reporting. They validate a different schema and therefore are reusable as a pattern, not as the project-local validator's contract.

## Decision

The project-local lessons contract is validated by a separate schema-aware validator and CLI command. The existing shared-registry validator remains unchanged in scope.

### What this IS

- A read-only validator for the generated project-local `kb/lessons/` contract.
- Validation of `PROJECT-XXXX` IDs using the configured `id_prefix`.
- Validation of index entries, lesson paths relative to the repository root, filename/frontmatter/index agreement, and exclusion of `SCHEMA.md` from lesson-file discovery.
- Explicit CLI help that distinguishes project-local validation from shared-registry validation.

### What this IS NOT

- It is not a migration of project-local lessons to the shared `KB-XXXX` schema.
- It does not change the generated project-local files or allocate IDs.
- It does not discover external lesson stores, synchronize stores, or write to repositories.
- It does not replace or broaden the existing shared-registry validator.

### Success criteria

- A valid generated project-local registry passes.
- Missing, malformed, conflicting, or inconsistent project-local registry data fails closed with sanitized diagnostics.
- Shared-registry validation continues to pass its existing tests.
- The CLI help names the schema validated by each command.

## Consequences

### What gets easier

- Agents can validate generated project-local lessons without knowing the shared registry layout.
- Shared and project-local lesson contracts remain explicit and cannot be silently conflated.
- Failures in filenames, frontmatter, index entries, and path references become actionable before capture or lookup workflows rely on them.

### What gets harder

- The package now has two registry validators and two schemas that contributors must understand.
- New project-local schema fields may require updates to both the validator and its fixtures.
- CLI documentation and tests must keep the two validation scopes distinct.

### What does not change

- Existing shared `KB-XXXX` registry behavior and ID allocation remain unchanged.
- Project-local lesson capture remains opt-in and single-destination.
- Validation remains read-only and does not publish or synchronize lessons.

## Alternatives Considered

### Alternative 1 — Make the project-local scaffold use the shared registry layout

This would reuse the existing validator but would change the generated `PROJECT-XXXX` contract, index location, and schema. It conflicts with the existing project-local template and would create migration/compatibility work for generated consumers. **Rejected.**

### Alternative 2 — Add a scope flag to one validator

A single command with a scope switch could expose both schemas, but it would increase branching in the existing validator and make the current shared command's contract less explicit. A separate command keeps the two public contracts clear. **Rejected for this increment.**

### Alternative 3 — Do nothing

Generated project-local registries remain unverifiable by the package's registry tooling, and the current help continues to leave the schema boundary ambiguous. **Rejected.**

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| A valid project-local registry passes | `tests/test_project_lesson_registry.py::test_valid_project_registry` | passing |
| `PROJECT-XXXX` and configured `id_prefix` are enforced | `tests/test_project_lesson_registry.py::test_id_prefix_and_id_validation` | passing |
| Index paths resolve from the repository root and agree with files/frontmatter | `tests/test_project_lesson_registry.py::test_path_filename_frontmatter_consistency` | passing |
| Malformed frontmatter fails closed | `tests/test_project_lesson_registry.py::test_malformed_frontmatter_closing_delimiter_is_rejected` | passing |
| Symlinked contract or lesson paths fail closed before content is trusted | `tests/test_project_lesson_registry.py::test_symlink_contract_file_is_rejected`, `test_symlink_lesson_is_rejected`, `test_symlinked_lessons_directory_is_rejected` | passing |
| `SCHEMA.md` is not treated as a lesson | `tests/test_project_lesson_registry.py::test_schema_file_is_excluded` | passing |
| Shared validation remains unchanged | `tests/test_lesson_registry.py` | passing |
| CLI help distinguishes project-local and shared schemas | `tests/test_cli.py::test_registry_help_names_schema`, `tests/test_project_lesson_registry.py::test_cli_help_names_project_local_schema` | passing |

## Rollback

Revert the implementation, tests, ADR, and index changes. No external state or generated consumer files are changed by this increment. The new validator and command are additive; removing them restores the current behavior, but the project-local validation gap returns.

## References

- GitHub issue #65: project-local versus shared lesson registry validation
- `kb_bootstrap/lesson_registry.py`
- `kb_bootstrap/cli.py`
- `kb_bootstrap/templates/lessons/index.yaml`
- `kb_bootstrap/templates/lessons/SCHEMA.md`
- `tests/test_lesson_registry.py`
- `tests/test_cli.py`
