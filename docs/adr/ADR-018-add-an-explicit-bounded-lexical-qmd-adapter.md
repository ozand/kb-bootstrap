# ADR-018: Add an explicit bounded lexical QMD adapter

**Status**: Proposed
**Date**: 2026-10-04
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #127; ADR-017, ADR-015

## Context

ADR-017 delivered offline discovery/read without changing legacy QMD `search`. The legacy wrapper has unbounded captured output/runtime and accepts unvalidated list members, which can crash or mislabel origins. Its collection suffix is not proof of indexed membership. Read-only source inspection found installed `@tobilu/qmd` 2.8.3: plain `search` dispatches directly to FTS, while vector/hybrid operations invoke model paths. Startup can still write config/SQLite state. No installed-QMD command or isolated membership smoke has been executed for this proposal.

## Decision

After specific owner acceptance, add `search-qmd` as a separate canonical-only lexical accelerator. Preserve legacy `search` and ADR-017 commands. No automatic fallback, raw access, collection registration, update, model operation, acquisition, cloud request, cross-KB discovery or capability registry is added to the runtime adapter.

Require explicit `--dir` canonical root, `--collection`, `--index`, `--state-dir`, and positional query; no ambient default index or suffix-based authority. The state directory must be an existing operator-designated directory containing a pre-provisioned named config and database. Index and collection names use only ASCII letters, digits, `_` and `-` (1–64 characters). Fix the layout: QMD_CONFIG_DIR=`<state>/config`, named config `<state>/config/<index>.yml`, XDG_CACHE_HOME=`<state>/cache`, INDEX_PATH=`<state>/cache/qmd/<index>.sqlite`; pass global `--index <index>` explicitly. Require existing regular config/DB and exactly the selected collection mapped to the explicit root, with no update hooks, local overrides, extra collections or unrecognized configuration affecting execution. Failure of these checks is FAILED, not permission to register or normalize state. Pass explicit QMD_CONFIG_DIR, XDG_CACHE_HOME and INDEX_PATH derived beneath it; reject symlink/reparse/escaping state paths before invocation. This bounds intended state selection, not a filesystem sandbox or proof of no egress. Optional tool absence never widens the corpus.

Use installed QMD 2.8.3's lexical CLI contract for the initial tested adapter; other versions require compatibility evidence, not silent substitution. Resolve `qmd` from PATH once and run that same executable's bounded `--version` before search. Accept only the documented version presentation carrying semver exactly `2.8.3`, not a range or substring match; fixtures must lock the observed pinned version-output grammar before implementation is declared compatible. Missing executable is OPTIONAL_UNAVAILABLE; unparseable/mismatched version is FAILED. Prefer documented `--format json`, not an undocumented compatibility spelling. Run the adapter from an invocation-owned empty scratch cwd with no ancestor `.qmd` override; do not use the consumer root as external cwd. Remove inherited QMD/INDEX_PATH/XDG overrides before setting the specified paths. Delete only this empty owned cwd after confirmed process exit; preserve it if exit is uncertain. Registration/index construction is an explicit separately authorized setup operation, never performed by search-qmd. The adapter may cause QMD-owned startup bookkeeping in the selected state directory and must not describe external QMD execution as zero-write.

## Execution and result bounds

Resolve an installed executable without acquiring it. Invoke plain `search` with a validated collection and query after `--`, JSON mode and a bounded result limit (default 10, maximum 100). Query rules match ADR-017. Use no shell interpolation. Windows shims need a reviewed argument-preserving launch path; do not claim shell-free launching a CMD shim is equivalent to invoking a native executable.

Limit each external invocation to 15 seconds, stdout to 1 MiB and stderr to 64 KiB, enforced while draining both streams rather than after unbounded capture. On timeout/output overflow terminate the invocation, drain only bounded owned buffers, and report FAILED with a static reason. This is not a guarantee that all descendants have stopped; no background retry or index repair. Emit at most 256 KiB UTF-8 JSON, including newline.

Output has status `OK`, `OPTIONAL_UNAVAILABLE`, or `FAILED`, and `results` plus one optional static `reason`. Exit 0 means valid bounded records (including no hits); exit 1 means absent/failed external tool; argument errors exit 2. Distinguish executable absence, launch failure, timeout, output limit, nonzero exit, malformed JSON and invalid records; never echo external stderr or arbitrary titles into diagnostics.

Require a JSON list of at most the requested limit with dictionary members, string `file`/`title`, and finite numeric non-boolean `score`. Accept irrelevant extra fields but never relay body/context. Validate every `qmd://<collection>/<relative-path>` against the explicitly selected collection and normalized contained Markdown path. Confirm existing regular source files and apply ADR-017 canonical-selection exclusions before a record acquires that label. Fail the entire response on an invalid member; do not convert missing or unsafe origin into a canonical result. Return only bounded collection/path/title/score fields and `layer: canonical-selection`; label index freshness and source verification `unknown`. A collection name or successful query does not verify corpus membership, index freshness, review or source truth.

## Separately consented synthetic smoke

Architecture acceptance authorizes implementation and mocked/synthetic subprocess tests, NOT execution of installed QMD or registration. Request a separate affirmative smoke consent covering installed QMD 2.8.3, a newly created invocation-owned TEMP corpus/state/cwd, exact commands `--version`, `collection add`, and plain lexical `search`, with config/DB/cache overrides under that TEMP root. No acquisition, model inference, embeddings, update hooks, trust commands, servers or external corpora. Collection add immediately indexes files and is a mutation, not a readiness probe.

Before registering, construct hook-free scratch config with verified QMD 2.8.3 inclusion/exclusion syntax. Reject parent `.qmd` discovery and ambient override inheritance; use explicit named index. Retain synthetic positive canonical fixtures and negative raw/research/lessons/hidden/reserved fixtures, verify actual indexed membership and lexical retrieval, and prove declarations are not automatically consumed as runtime registry. Scratch indexing uses the same canonical-selection exclusions as ADR-017, deliberately stricter than generated wiki declarations where they differ. Raw declaration mismatch is recorded, not repaired or exercised as raw access in this slice.

No model-cache artifacts and unchanged owned sentinels are necessary observations, not proof of host-wide no-egress or total write isolation. Host-level network denial requires separately authorized infrastructure; do not change firewall settings implicitly. If execution cannot satisfy a consented no-egress requirement, report environment unavailable rather than claim source inspection established it. Clean only invocation-owned scratch outputs after containment and alias-removal checks; preserve unknown state. Retain a sanitized issue comment with exact runtime/version, test outcomes and limitations, never operator config/cache contents.

## Alternatives Considered

- Harden legacy `search` in place: rejected here because ADR-017 preserves it and existing consumers rely on its output/diagnostics.
- Generic capability registry or adapter framework: rejected as unnecessary for one explicit lexical operation.
- Automatic local fallback or QMD installation: rejected because absence must not expand scope or grant acquisition authority.
- Model-backed hybrid search: rejected because model provisioning/egress/quality gates are separate decisions.
- Run against ambient index: rejected because registration and startup can mutate operator-owned state.

## Consequences

### What gets easier

- Explicit lexical acceleration has finite runtime/output and distinguishes tool absence from failed execution.
- Navigation results cannot acquire a canonical label solely from a collection suffix.

### What gets harder

- A single pinned CLI, state layout, process termination and registration membership need real platform evidence.
- External startup bookkeeping remains possible; safety boundaries must not be marketed as a sandbox.

### What does not change

- Offline commands remain usable; legacy QMD behavior, canonical validation and consumer data are unchanged.
- No raw adapter, global index administration, provisioning or no-egress attestation is authorized.

## Test Contract

| Claim | Named evidence | Currently |
|---|---|---|
| Legacy search/local commands unchanged | CLI dispatch regression | not yet written |
| Absence differs from launch/runtime/version failure | synthetic executable/outcome fixtures | not yet written |
| Timeout/stdout/stderr bounded while executing | deterministic noisy/hanging subprocess fixtures | not yet written |
| Strict records and origin prevent mislabelling/crashes | scalar/member/URI/traversal/nonfinite-score matrix | not yet written |
| No ambient config/index or source mutation by wrapper | env/argv and path/reparse sentinel tests | not yet written |
| UTF-8 JSON/query limits and option-like arguments safe | presentation/argument-boundary fixtures | not yet written |
| Pinned real lexical membership matches selected policy | separately consented scratch QMD 2.8.3 smoke | not run; consent required |
| No unexpected model/global artifacts in smoke | scoped before/after observations, not host-wide isolation | not run; consent required |

## Rollback

Revert the additive adapter; offline/legacy commands remain. Do not remove operator-owned QMD state. Smoke cleanup is limited to verified invocation-owned scratch; no global registry repair or consumer migration occurs.

## References

- Issue #127; ADR-017; `kb_bootstrap/qmd_search.py`
- Installed package manifest and dist source inspected read-only: `@tobilu/qmd` 2.8.3.
- Public upstream source inspected: `tobi/qmd` commit `26b703c5daa8037df089a8104cbf7eeab4e51874`; https://github.com/tobi/qmd/tree/26b703c5daa8037df089a8104cbf7eeab4e51874
- Source inspection is not execution, platform membership verification or acquisition consent.

