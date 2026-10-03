# ADR-015: Add core-only validation without changing legacy validate

**Status**: Proposed
**Date**: 2026-10-03
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #122, #121; ADR-003, ADR-006, ADR-009, ADR-014

## Context

Issue #122 requires a tool-independent local validation path while preserving existing consumer behaviour. Current `validate` composes profile, provenance, graph and QMD declarations; these declarations do not prove QMD executable/index readiness. W01's wider adapter/schema proposal unnecessarily couples a useful local-only slice to unused namespace and policy decisions. The existing local validators can be reused without a new registry, plugin framework or capability file. This proposal is not implementation approval.

## Decision

Only after owner acceptance, add `validate-core` as an explicitly invoked, nonpersistent CLI operation using existing canonical profile, provenance and graph checks. Use `--dir` (default `kb`) and `--now` (optional explicit offset-aware time), matching existing validation arguments and diagnostics. Do not add strict/policy options absent from the current composed CLI. Exit 0 only if all local checks pass, 1 for validation failure, 2 for argument syntax errors. No QMD declaration/runtime/index check, GitHub doctor/authentication, subprocess, network, model, adapter dispatch or automatic fix occurs in this operation. Existing `validate` and initialization remain unchanged, including legacy QMD declaration requirements.

Report each invoked local check separately; success means these checks passed, not universal OKF conformity, source truth, policy authorization, retrieval freshness or publication readiness. Existing consumer-selected policy remains explicit, not inferred. No capability state aggregation or persisted configuration is introduced. `single`/`umbrella` remain layout choices.

## Alternatives Considered

- Change `validate` defaults: rejected for this slice because existing consumers rely on composed validation.
- Require full adapter namespace/schema before local-only validation: rejected as an unused dependency of this operation.
- Generic plugin/capability registry: rejected as speculative execution and migration surface.
- Require users to call private Python helpers: rejected because a supported CLI is the requested user-testable path.

## Consequences

### What gets easier

- A user validates a bounded local KB without configuring QMD or GitHub.

### What gets harder

- Two explicit commands must be documented without implying core success completes a consumer's publication or retrieval gates.

### What does not change

- Accepted profile/provenance/graph/path boundaries, legacy validation and consumer ownership. W01 adapter identifiers/states/schema/migration remain separately unaccepted design; this ADR does not authorize them.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| Minimal KB works without QMD/gh/models/network | CLI fixture with absent optional tools and network/subprocess spies | not yet written |
| Invalid local input still fails with separate check output | profile/provenance/graph negative fixtures and captured stdout | not yet written |
| Legacy validate keeps its QMD declaration gate | legacy default and missing-QMD fixture | not yet written |
| No source mutation or automatic configuration | source-tree before/after fixture | not yet written |
| Core success is not retrieval/publication readiness | presentation/nonclaim assertions | not yet written |

## Rollback

Revert the additive command; no generated configuration or consumer migration occurs. No model or network acquisition is authorized by accepting this decision.

## References

- Issue #122; docs/proposals/W01-tool-independent-core.md
- docs/VALIDATION_COMPOSITION.md; ADR-003, ADR-006, ADR-009, ADR-014
