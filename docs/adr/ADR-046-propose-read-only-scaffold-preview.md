# ADR-046: Propose a read-only scaffold preview

**Status**: Proposed — not accepted, not implemented

**Date**: 2026-11-03

**Authors**: Pi coding agent

**Supersedes**: None

**Related**: Issue #123, #121; ADR-002, ADR-004, ADR-016, ADR-039

## Context

Accepted ADR-016 makes ordinary initialization conservative: it initializes a wholly absent managed scaffold, reports a complete matching scaffold as a zero-write no-op, and blocks partial or conflicting state before mutation. It intentionally adds no updater, adoption workflow, or preview interface. ADR-039 adds a distinct, opt-in, fresh-empty-target `--core-only` mode; it does not replace or infer the ordinary scaffold mode.

Issue #123 asks for a read-only preview before any separately explicit update is considered. This proposal specifies preview only. It authorizes no update command, template replacement, adoption, or migration. Preview compares current state to what this installed package would generate now; it has no historical baseline, so it cannot establish whether differing bytes are user edits or an older template.

## Decision

If accepted, add one `preview` CLI subcommand using the existing argparse subcommand style:

```text
kb-bootstrap preview --target PATH [--type {single,umbrella}] [--core-only]
```

`--target` is required and identifies the sole explicitly selected root; no current-directory default. `--type` is explicit and selects exactly one existing ordinary layout, defaulting to `single` as ordinary initialization does. `--core-only` explicitly selects ADR-039's exact core-only artifact set; absence selects ordinary initialization's fixed QMD outputs and trusted packaged skills plus existing delegated lesson state. This is a preview-subcommand option selecting only the observed inventory; it does not invoke initialization. Mode choices come only from flags, never consumer-file inference. The preview command does not accept `--with-project-lessons`; reject unsupported arguments before inspecting the target. No name, format, updater, or force option is added. The selection is explicitly supplied after the `preview` token, for example `kb-bootstrap preview --target ./my-kb --type umbrella` or `kb-bootstrap preview --target ./my-kb --core-only`.

The subcommand must not call ordinary initialization or its writers. Reuse the existing expected-byte renderers/inventory and read-only state classifiers where their contracts match; any necessary pure helper extraction must preserve ADR-016 behavior. Ordinary `kb-bootstrap --target ...` and `--core-only` initialization behavior and bytes remain unchanged. Preview is an observation, not authorization or proof that the target is safe to mutate later.

## Target and comparison boundary

Require an explicit target root. Resolve its path for containment checks without creating the target or missing parents. A nonexistent target is valid preview input and reports all expected managed files as `missing`; it does not create the root, parent directories, caches, staging, or markers. Check the caller's target path components with no-follow metadata before deriving its canonical root; do not resolve through a symlink/reparse ancestor. Escaping/traversal, symlinked or reparse ancestors/destinations, non-regular expected files, or a target that cannot be safely classified make the overall result blocked. Do not open content beneath an ancestor already known unsafe. An unreadable or changing expected file is `unavailable`; continue safe classifications only as permitted by the existing classifier, but never label the overall result ready when any item is unavailable.

For ordinary mode, expected files are exactly the current ADR-016 map: three generated QMD files plus files from the trusted installed package inventory, excluding the inventory's existing cache artifacts. For core-only mode, use the exact ADR-039 allowlist for the selected layout. Compare only these expected relative paths. Do not recursively walk the consumer target and do not inspect unlisted files. Thus preview cannot detect a removed file absent from the current package inventory, prove completeness of a historical installation, or classify unlisted consumer files as conflicts/removals.

Use `project_slug(target.name)` and the current existing renderer rules for generated QMD names/bytes. Render solely from the explicit target basename, selected layout/mode, and installed package; do not infer configuration from consumer contents. Classify delegated lesson state through its existing read-only ADR-002 contract, not byte equality. Do not introduce a registry, manifest, baseline, persistent output, or second rendering implementation.

## Report and result contract

Emit stable UTF-8 text, not JSON or a persisted schema. List entries in stable lexical order by relative POSIX path and category, with only these states: `matching`, `missing`, `content differs`, `unsafe`, and `unavailable`. Include aggregate counts for those five categories and one final result:

- `RESULT: READY` when the entire selected expected inventory matches, delegated state is valid, and no path is unsafe/unavailable;
- `RESULT: CHANGES REQUIRED` when at least one expected file is missing or differs, with no unsafe/unavailable classifications;
- `RESULT: BLOCKED` if target/inventory/delegated state cannot be classified safely, including any unsafe or unavailable item.

Exit status is 0 for READY; 1 for CHANGES REQUIRED or BLOCKED; argparse syntax errors exit 2. `READY` means only that current expected bytes match the selected inventory. For an absent root it is necessarily CHANGES REQUIRED. No status says an update is safe, authorized, complete, or historically recoverable. Report relative paths and categories only: no file contents, diffs, hashes, absolute paths, exception text, environment details, or private values. Do not include arbitrary target names in diagnostic text. Aggregate counts do not replace per-path entries. Inventory size is bounded by the installed package inventory and the fixed generated set, not by a target-tree traversal. Do not read a destination whose size differs from its expected payload length; equal-size comparisons read no more than the expected payload bytes. Thus the content-read bound is derived from trusted expected package/rendered payload sizes, not arbitrary consumer file sizes.

The preview operation performs no writes under the target or its ancestors: no directory creation, files, staging, cleanup, lock files, bytecode, cache, or configuration. It does not spawn external tools, make network calls, run QMD, or invoke Git. In-process runtime effects outside the target that are inherent to loading the CLI are not a consumer-write allowance. The explicit target is operator-selected input; this command is not permission to inspect sensitive private corpora, and ordinary documentation/tests should use synthetic trees. Do not claim host-level race resistance or hostile-writer security: comparison is a bounded observation of a stable, locally controlled tree, not a lock and not a promise that state stays unchanged after reporting.

## Alternatives Considered

- `init --dry-run`: rejected because ordinary initialization currently has writers interleaved with setup. A distinct read-only subcommand makes the no-writer boundary auditable and cannot accidentally turn a flag-placement mistake into initialization.
- Reuse ordinary repeat preflight as a preview command without a separate report contract: rejected because ADR-016's actions (`initialize`, `noop`, `blocked`) do not describe each expected path's comparison state, while preview must expose a sorted path inventory.
- Scan the entire target for generated-looking or missing files: rejected because unlisted files are consumer-owned and current package contents cannot provide a historical deletion baseline.
- Emit content diffs or hashes: rejected because current bytes may contain private content; categories and counts suffice for this bounded proposal.
- Infer mode from existing files or silently select core-only: rejected because selection must be explicit and absent configuration is not evidence of capability state (ADR-028/039).
- Add a historical registry, adoption flow, generic updater, repair or force option: rejected as new persisted schema and broader authority, explicitly outside this preview.

## Consequences

Preview gives an operator a bounded view of expected current-package paths before any future, separately approved update is designed. An absent or partial scaffold can be described without making it. Differences remain unexplained; there is no old-version baseline and no automatic reconciliation. `READY` is not an updater precondition or a guarantee against later filesystem change. Existing first initialization, repeat no-op/block behavior, core-only fresh-target restrictions, lesson enablement, managed AGENTS behavior, and gitignore handling are unchanged.

## Test Contract

Required if this proposal is accepted; no tests or runtime implementation are included here.

| Claim | Named test |
|---|---|
| Explicit target and layout/mode selection; no subcommand/default ambiguity | `tests/test_scaffold_preview.py::test_preview_requires_explicit_target_and_selects_one_layout_mode` |
| A complete ordinary single and umbrella scaffold reports sorted matching paths, exact aggregate counts, READY, and status 0 | `tests/test_scaffold_preview.py::test_preview_reports_complete_ordinary_inventory` |
| `--core-only` reports only ADR-039 allowlist for both layouts and does not include QMD or optional skills | `tests/test_scaffold_preview.py::test_preview_core_only_uses_exact_adr039_inventory` |
| Missing target and partial target report expected missing paths without creating target or ancestors | `tests/test_scaffold_preview.py::test_preview_missing_and_partial_targets_are_read_only` |
| Edited expected bytes are content-differs; no content, hashes, or absolute paths leak | `tests/test_scaffold_preview.py::test_preview_differences_are_sanitized` |
| Unlisted files, including user additions and files not in current package inventory, are not read, reported, or treated as removed managed paths | `tests/test_scaffold_preview.py::test_preview_ignores_unlisted_consumer_paths` |
| Unsafe target/ancestor/destination prevents opening descendant content; unsafe report blocks without leaking paths | `tests/test_scaffold_preview.py::test_preview_unsafe_paths_block_before_content_open` |
| Unreadable/unstable expected file yields unavailable and BLOCKED, never READY; unequal-size files are classified without reading their contents | `tests/test_scaffold_preview.py::test_preview_unavailable_never_reports_ready` |
| Repeated identical preview is deterministic and produces no target/ancestor tree or metadata change | `tests/test_scaffold_preview.py::test_preview_is_repeatable_and_writes_nothing` |
| No subprocess, external tool, network, staging, or mutating init primitive is invoked | `tests/test_scaffold_preview.py::test_preview_invokes_no_external_or_mutating_operations` |
| Legacy ordinary init and `--core-only` init output, bytes, parsing, and repeat behavior stay unchanged | `tests/test_scaffold_repeat.py::test_default_init_artifacts_and_repeat_are_unchanged`; `tests/test_cli.py::test_core_only_single_creates_exact_allowlist_without_optional_tools` |

Use synthetic temporary targets and snapshots/spies. Include matching, absent, partial, edited, unsafe and unavailable cases. The preview test suite must establish that only the expected inventory is inspected; it must not use arbitrary recursive consumer scans as expected behavior. Test actual supported-host behavior and report platform-unavailable safety checks honestly. Ordinary tests must not access private corpora or install optional tools.

## Rollback

Before acceptance, withdraw this proposal with no runtime or consumer changes. If later accepted and implemented, rollback removes only the additive preview interface/helpers; do not change ordinary init or delete consumer data. No preview needs a data rollback. An updater, if ever proposed, requires its own separately scoped accepted contract.

## References

- Accepted ADR-016, ADR-039; Issue #123 and owner comments.
- `kb_bootstrap/cli.py`, `kb_bootstrap/scaffold_repeat.py`, `kb_bootstrap/project_lesson_enablement.py` at proposal base `bf2319aeb164f4c0ecb87870648cf2289e4a5131`.
