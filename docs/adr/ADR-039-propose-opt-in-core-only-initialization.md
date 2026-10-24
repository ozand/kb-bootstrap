# ADR-039: Propose opt-in core-only initialization

**Status**: Proposed
**Date**: 2026-10-24
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #122; ADR-015, ADR-016, ADR-028; Issue #122 comments `6379159840` and `6379661811`

## Context

Issue #122 asks for a fresh knowledge base that can be maintained locally without optional retrieval tools, while preserving existing consumers. Accepted ADR-015 adds `validate-core`; it does not change initialization. ADR-016 protects existing generated QMD and skill inventory on ordinary repeats and rejects force switching or template upgrades. ADR-028 separates optional selection, observations, required work and authority; an absent file is not proof that a capability was disabled or unavailable. Accepted wiki-builder guidance permits local core work and makes QMD steps conditional on selected retrieval/index work.

At researched base `bf69da5429bfd18d23c2122639c783bda1d22491`, initialization has root `--target`, `--type {single,umbrella}`, `--with-project-lessons`, and subcommands. Without a subcommand it scaffolds both layouts with QMD files and four skills. The repeat guard inventories generated files and blocks partial/conflicting repeats. This proposal changes none of that behavior by itself.

## Decision

If accepted, add exactly one opt-in root CLI flag, `--core-only`, selecting a fresh local-core scaffold. No flag means existing `init` behavior and artifact bytes remain unchanged. `single` and `umbrella` remain layout choices; core-only does not select a domain, deployment model, capability state, or readiness result.

The flag is valid only on root initialization invocation (no subcommand), before any subcommand token. If `--type` is omitted, existing default `single` applies. `--target` and `--type` placement and interpretation remain exactly as today; no command redesign is introduced. Example:

```text
kb-bootstrap --target ./my-kb --type single --core-only
```

With any subcommand, including `validate-core`, it is an argument error with exit status 2 and a message that `--core-only` is initialization-only. Placement after a subcommand is an ordinary argparse error. It is incompatible with `--with-project-lessons` and must produce an argument error; lessons and their store contract are outside this minimal scaffold. The project name continues to derive from target directory; no name option is added.

### Exact generated artifact set

A successful first core-only initialization creates only these managed paths (plus listed parent directories):

- Both layouts: `.agents/skills/kb-wiki-builder/SKILL.md`; `.gitignore` with existing additive generated-artifact rules; `kb/raw/.gitkeep`, `kb/research/.gitkeep`, `kb/wiki/entities/.gitkeep`, `kb/wiki/concepts/.gitkeep`, and `kb/wiki/reports/.gitkeep`. Parent directories: `.agents/skills`, `.agents/skills/kb-wiki-builder`, `kb`, `kb/raw`, `kb/research`, `kb/wiki`, and the four `kb/wiki/*` directories.
- `single`: common paths only.
- `umbrella`: common paths plus `kb/apps/`, `kb/systems/`, `kb/architecture/`.

Use existing wiki-builder source. Its workflow at the researched base explicitly makes local file-based work and `validate-core` sufficient, reports retrieval/index and universal checks separately, and keeps QMD steps conditional on selected retrieval/index work (source lines 82–89). No second skill variant or template wording change. Do not install `qmd-operator`, `kb-lookup`, or `market-research`: lookup requires a separately configured lesson store, and optional workflows are unnecessary for local core work. Do not create `qmd.json`, any `qmd/collections/*` file or directory, lesson store/configuration, capability selection file, or probe result.

The success receipt identifies this as a core-only scaffold and says QMD/lesson/research artifacts were not created. It reports created files, not tool availability, explicit disablement, retrieval readiness, policy compliance, publication readiness or authority. Absence means only "not configured by this scaffold"; consumers may configure optional workflows independently later.

### Fresh-target and ownership boundary

Core-only is fresh-target-only in v1. Target must not exist or must be an empty directory. Any pre-existing entry—including a legacy scaffold, QMD path, user file, or lesson data—blocks before first write with a fresh-target-only diagnostic. Do not infer a profile by inspecting paths, reuse an existing scaffold, or upgrade/switch modes. No persisted profile marker or capability registry is introduced. A successful first run is not repeat-idempotent: second run sees generated entries and blocks; user must choose a new empty target or manage it explicitly outside this command.

Preflight target before mutation. Never delete or overwrite existing consumer data. Preserve ADR-016 default-mode repeat contract unchanged. If initialization fails after writes begin, do not roll back by deleting files; report partial owned output may remain and direct operator to inspect generated paths. Promise neither multi-file atomicity nor hostile-writer safety.

## Alternatives considered

- Change ordinary initialization by default: rejected; changes existing artifacts and conflicts with ADR-015 compatibility.
- Omit tools based on environment probes: rejected; implicit selection/probes are out of scope and absence is not a capability state.
- Add profile/capability registry, selection document, dynamic plugin mechanism, or disabled marker: rejected as unnecessary persistent schema and broader than this workflow.
- Allow repeats/upgrades: rejected for v1; inferring ownership/mode without profile metadata is ambiguous, while ADR-016 default repeat remains unchanged.
- Reuse full-scaffold inventory for core-only: rejected because it creates QMD declarations and optional skills unnecessary to local core work.
- Install kb-lookup without its store: rejected; its instructions block when the store is absent and lookup is unnecessary to edit/read local KB files.

## Consequences

### What gets easier

A user creates and locally maintains a fresh KB with a deliberately small scaffold and runs `kb-bootstrap validate-core --dir ./my-kb/kb` without QMD, Surf, GitHub authentication, models or network access.

### What gets harder

The first version cannot re-enter a core-only target, resume partial initialization, or convert an existing target. Users must handle future optional-tool adoption explicitly. Static wiki-builder guidance still documents optional QMD; it does not dynamically reflect installed tools.

### What does not change

Legacy initialization output/repeat guard, `validate`, `validate-core`, doctor, publication checks, consumer policy, authority, QMD validators/adapters, retrieval behavior and existing consumer data remain unchanged. Core validation means only checks promised by ADR-015. This does not complete all W01 criteria.

## Future implementation test contract

Required tests if accepted; this proposal adds no tests/fixtures.

| Claim | Named test |
|---|---|
| Exact `single` output without optional tools | `tests/test_cli.py::test_core_only_single_creates_exact_allowlist_without_optional_tools` |
| Umbrella adds only its three layout directories | `tests/test_cli.py::test_core_only_umbrella_creates_exact_allowlist` |
| Local maintenance works without QMD/Surf/gh/network; no subprocess/probe/network invoked | `tests/test_cli.py::test_core_only_uses_local_core_without_optional_execution` |
| Flag placement and lessons incompatibility return argparse status 2 | `tests/test_cli.py::test_core_only_cli_placement_and_incompatible_options` |
| Default artifact bytes, skill inventory, and repeat behavior unchanged | `tests/test_cli.py::test_default_init_artifacts_and_repeat_are_unchanged` |
| Core repeat and cross-mode attempts block without mutation | `tests/test_cli.py::test_core_only_repeat_and_mode_switch_block_without_mutation` |
| Nonempty target/collision blocks pre-write, preserving user/QMD/lesson content | `tests/test_cli.py::test_core_only_requires_empty_target_and_preserves_collisions` |
| Interrupted initialization does not delete output and reports possible partial state | `tests/test_cli.py::test_core_only_partial_failure_does_not_delete_output` |
| Wiki-builder local path sufficient and QMD conditional | `tests/test_skill_governance.py::test_core_only_wiki_guidance_keeps_qmd_conditional` |

Tests must compare complete tree snapshots, verify default artifacts against pre-change baseline, and assert no capability/disabled state. They must not infer tool availability or network isolation from absent packages. No optional tool installation is in scope.

## Rollback

Before acceptance, withdraw the proposal with no runtime or consumer changes. If later implemented and rollback is required, remove only the additive option/branch; do not delete generated core scaffolds or modify existing targets. Preserve established default initializer and guard.

## References

- Issue #122 and research record comment `6383943588`.
- Accepted ADR-015, ADR-016, ADR-028; wiki-builder guidance correction in Issue #122 comments `6379159840` and `6379661811`. The exact researched skill at base `bf69da5429bfd18d23c2122639c783bda1d22491`, lines 82–89, explicitly conditions QMD on selected retrieval/index work.
- `kb_bootstrap/cli.py`, `kb_bootstrap/scaffold_repeat.py`, and `kb_bootstrap/templates/skills/kb-wiki-builder/SKILL.md` at base `bf69da5429bfd18d23c2122639c783bda1d22491`.
