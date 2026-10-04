# ADR-019: Accept pinned QMD index selectors and inert model defaults

**Status**: Accepted
**Date**: 2026-10-04
**Authors**: Pi coding agent
**Supersedes**: None
**Amends**: ADR-018 (URI/config compatibility only, if accepted)
**Related**: Issue #127; ADR-018

## Context

Owner-consented real QMD 2.8.3 (facd35e) smoke registered and retrieved one invocation-owned synthetic canonical file. Plain search emitted `qmd://synthetic/welcome.md?index=smoke`. Startup persisted default embed/generate/rerank model URI configuration, although no model cache directory was observed. ADR-018's strict state/record gate does not explicitly admit either normal presentation. Collection add also discards authored ignore rules before indexing, so the smoke did not verify general excluded-layer indexed membership. No updates, models, installation or global collection operations were performed.

## Decision

Retain all ADR-018 boundaries and permit only these pinned compatibility forms after owner acceptance:

- A QMD result URI may have no query or exactly `index=<explicit-index>`. Names remain ADR-018 ASCII names; reject percent escapes, duplicates, other parameters, mismatched index and fragments. The selector is redundant origin metadata, not permission to select a different index. All existing collection/path/source checks remain required.
- Scratch/pre-provisioned config may additionally contain a `models` mapping with only `embed`, `generate`, `rerank` and their exact pinned QMD 2.8.3 built-in default URI strings. No custom URI, path, additional key, hook, alias or acquisition is admitted. The lexical adapter does not execute model operations; inert default settings are not model consent or readiness evidence.

Implementation must bind those strings to inspected pinned package defaults and test mismatch rejection. Versions, execution bounds, state paths, no fallback, canonical-only policy and separate smoke consent remain ADR-018. Do not edit its accepted decision text in place.

Real smoke evidence remains limited to allowlisted canonical registration/retrieval. Full ignore-policy membership needs a separately reviewed setup route; this decision does not authorize update or expand smoke commands.

## Consequences

### What gets easier

The strict adapter can consume actual pinned lexical output/config without relaxing origin or acquisition boundaries.

### What gets harder

Pinned default values and redundant index metadata need explicit compatibility tests.

### What does not change

No model execution, download, raw access, global state mutation, update hook, default change or general QMD compatibility is authorized.

## Alternatives Considered

- Reject normal pinned output: safe but unusable after successful real registration.
- Accept arbitrary URI queries/models: rejected because it expands scope and acquisition authority.
- Strip selectors or rewrite operator config: rejected because it hides provenance or mutates consumer state.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| Exact index selector accepted; all other queries rejected | URI selector matrix | not yet written |
| Only pinned inert defaults admitted | config defaults/custom URI/hook matrix | not yet written |
| Original ADR-018 boundaries preserved | adapter/process/local/legacy regressions | not yet written |
| Pinned lexical output consumed | consented synthetic smoke through adapter | not yet run |

## Rollback

Revert compatibility predicates; normal named-index output may fail closed again. Never remove operator config or model state. Scratch cleanup remains invocation-owned only.

## References

- ADR-018; Issue #127 smoke comment (2026-10-04).
- Installed `@tobilu/qmd` 2.8.3 source and consented synthetic output/config, not private operator state.
