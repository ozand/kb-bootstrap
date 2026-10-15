# ADR-028: Separate optional capability state from validation and authority

**Status**: Proposed
**Date**: 2026-10-13
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issues #121, #122, #127, #130; ADR-014, ADR-015, ADR-017, ADR-018, ADR-022

## Context

### Research record (before this draft)

At main `87e1a8c77aa595c325688a3f320ba63dea6cb785`, #122 is OPEN and its latest implementation receipt says ADR-015/`validate-core` is delivered while wider capability state/policy aggregation and migration remain outstanding. The Issue requires a Proposed decision and behavior matrix, distinguishes not configured/disabled/configured-available/configured-broken, says optional absence is not success for a required operation, and forbids a generic executable plugin framework.

Read-only source inspection at that exact baseline found: ADR-015 preserves legacy `validate` and initialization and adds only local profile/provenance/graph checks; `docs/VALIDATION_COMPOSITION.md` separates universal checks, consumer policy, and retrieval/index freshness; README still documents QMD prerequisites and generated QMD declarations; ADR-022 preserves distinct local-write/review and external-publication authority; the broader `docs/proposals/W01-tool-independent-core.md` remains Proposed and includes unaccepted schema, adapter, probe, and migration choices. No runtime behavior was exercised. No new owner question is required for this design-only proposal; acceptance is required before implementation.

### Scope

This proposal decides only how a future explicit local workflow distinguishes optional-operation selection from technical observation, and how those facts relate to existing validation gates. It does not resolve every W01 capability, data-policy, or adapter question.

This is a proposed decision only. It does not authorize a capability file, CLI change, probe, adapter dispatch, migration, policy engine, or runtime implementation.

## Decision

If separately accepted, represent configuration, technical observation, and operation authority as independent outcomes. Do not collapse them into one success/failure state.

| Dimension | Proposed state | Meaning and required evidence |
|---|---|---|
| Selection | `NOT CONFIGURED` | No explicit selection exists. Optional work is unavailable; no probe, install, fallback, or implicit selection occurs. |
| Selection | `DISABLED` | An explicit owner choice disables this operation. No probe, install, fallback, or implicit re-enable occurs. |
| Selection | `CONFIGURED` | A valid explicit selection exists. This is not evidence that its tool works or that its operation is authorized. |
| Observation | `NOT RUN` | No qualifying, scoped check was performed. Do not infer availability or failure. |
| Observation | `AVAILABLE` | A documented, bounded check observed the selected mechanism ready for its stated scope and time. Configuration alone cannot produce this state. |
| Observation | `BROKEN` | A documented check was actually attempted and observed a technical/configuration failure. Missing optional configuration alone is not `BROKEN`. |
| Operation authority | separate result | Apply ADR-022 at the operation boundary. Capability selection or availability never grants read, write, acquisition, egress, or publication authority. |

A consumer-required operation with no configuration or a failed check must be reported as unmet/blocked for that consumer workflow; optional absence is not a pass. The report must preserve the underlying state and identify which operation was required. No optional operation silently falls back to another adapter or hosted service.

Keep these validation/evidence gates distinct:

1. `validate-core` establishes only its accepted local profile, provenance, and graph checks (ADR-015).
2. Legacy `validate` retains its current QMD declaration/path checks; initialization and `doctor` behavior remain unchanged.
3. Consumer-owned policy remains the consumer's explicit validator.
4. Retrieval/index readiness requires separately recorded QMD registration/update/search evidence as documented in `VALIDATION_COMPOSITION.md`; declarations or an adapter probe do not prove freshness.
5. Repository identity/remote-publication checks remain explicit and fail-closed; local validation success does not bypass `doctor`, ADR-022 authority, or publication review.

This decision does not define a persisted schema, universal capability namespace, adapter plugin protocol, executable discovery mechanism, or aggregate release gate. Any such public format, dispatch surface, migration/default change, or new probe behavior requires a narrower accepted decision before implementation. `single` and `umbrella` remain layout choices, not capability presets or knowledge domains.

## Compatibility and migration

Existing consumers remain on current behavior. No legacy command, initialization output, skill, QMD registration, or publication preflight changes under this ADR. No migration is automatic. A future implementation must state the exact selected operation, required/optional status, evidence source and scope, and preserve old behavior unless a separately accepted compatibility plan changes it.

## Consequences

### What gets easier

Reports can distinguish absent optional tooling from attempted failure and from denied authority, while preserving the accepted core-only validation path.

### What gets harder

A workflow must retain more than one result and explain consumer-required failures without collapsing them into a generic green status. Readiness checks need bounded, operation-specific evidence.

### What does not change

ADR-015, legacy `validate`/initialization, ADR-017 local search, ADR-018/019 QMD boundaries, ADR-022 authority distinctions, and consumer-owned policy remain authoritative. This proposal implements none of the states.

## Alternatives Considered

- **Treat absent optional tools as success:** rejected because a consumer-required operation could be silently skipped.
- **Use one `AVAILABLE/BROKEN` capability flag:** rejected because it conflates selection, observation, consumer requirement, and authority.
- **Change legacy `validate` or initialization to infer optionality:** rejected because ADR-015 explicitly preserves their behavior and migration needs separate acceptance.
- **Add a generic plugin/capability registry now:** rejected because namespace, execution, migration, and policy contracts are not accepted and exceed this decision.

## Test Contract

| Claim if implemented | Test | Currently |
|---|---|---|
| Unconfigured and explicitly disabled operations cause no probe or fallback | `tests/test_capability_reporting.py::test_absent_and_disabled_do_not_probe_or_fallback` | not yet written |
| Configuration alone never reports availability; `BROKEN` requires an attempted check | `tests/test_capability_reporting.py::test_observation_requires_scoped_check` | not yet written |
| Consumer-required absence/failure is unmet, not successful optional skip | `tests/test_capability_reporting.py::test_required_operation_failure_is_not_pass` | not yet written |
| Capability outcomes do not bypass core/legacy validation or publication checks | `tests/test_capability_reporting.py::test_existing_validation_and_publication_gates_unchanged` | not yet written |
| Readiness, retrieval freshness, and ADR-022 authority remain distinct | `tests/test_capability_reporting.py::test_readiness_freshness_and_authority_are_independent` | not yet written |
| No optional install, network fallback, or arbitrary plugin execution occurs | `tests/test_capability_reporting.py::test_no_implicit_execution_or_fallback` | not yet written |

## Rollback

Before acceptance, withdraw this proposal. After acceptance, any change to the state model or compatibility boundary requires a superseding ADR. No runtime state or consumer data is introduced by this document.

## References

- Issue #122 and accepted-scope history in its comments, especially `5964643810`.
- `docs/proposals/W01-tool-independent-core.md` (Proposed; broader scope not accepted).
- `docs/VALIDATION_COMPOSITION.md`; `docs/adr/ADR-015-add-core-only-validation-without-changing-legacy-validate.md`.
- `docs/adr/ADR-018-add-an-explicit-bounded-lexical-qmd-adapter.md`; `docs/adr/ADR-022-require-explicit-scoped-operator-authority-for-external-actions.md`.
