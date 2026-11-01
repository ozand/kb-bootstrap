# ADR-048: Propose reviewed deferral of Attested Computation validation

**Status**: Proposed
**Date**: 2026-11-05
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #91; ADR-003, ADR-005, ADR-006, ADR-047; `docs/OKF_V0_2_CANONICAL_PROFILE.md`; `docs/VALIDATION_COMPOSITION.md`

## Context

Issue #91 explicitly permits either a bounded opt-in Attested Computation validator or a reviewed deferral with measurable revisit criteria. ADR-003 deliberately accepts unknown/additional metadata, including Attested Computation fields, without semantically validating it: incomplete validation would imply guarantees the profile does not provide. ADR-005's deterministic canonical graph, ADR-006/ADR-047's separate provenance/freshness section, the canonical profile section, graph-integrity extension, and QMD declaration section remain distinct. Existing CLI result labels must not be reinterpreted as a full pure-OKF conformance claim.

No concrete user operation currently demonstrates that computation evaluation is blocked by its absence, and no bounded computation subset/input-output contract, fixtures, or threat model is established. Introducing execution now would create a new security boundary without evidence that the existing core needs it. The deferral is a decision not to validate or evaluate these fields now; it does not cancel the possible need or grant implementation authority.

## Decision

Propose deferring Attested Computation semantic validation and evaluation. Make no runtime, CLI, report-label, schema, or other public-semantic change. Do not add an evaluator or attestation, verification, trust, or security claim. Unknown/additional computation fields continue to be permitted as metadata under ADR-003; their presence is not proof that a computation is valid, ran, or produced a verified result.

Keep canonical profile validation, bounded provenance/freshness, canonical graph/provenance exports, graph-integrity results, and optional QMD declaration/retrieval results separate under their existing contracts. Preserve current CLI section/result labels and source bytes. Passing existing profile checks does not constitute full pure-OKF conformance or computation validation. A graph-integrity failure remains a local extension result and must not be recast as an OKF profile failure; conversely, a profile result does not establish graph integrity, computation validity, or retrieval quality.

Revisit this decision only when a concrete evidence package is presented for independent review, containing all of:

1. A specific open user issue or request demonstrating a real user operation blocked by the absence of computation validation/evaluation.
2. A named, closed subset of computation fields plus a bounded input/output contract, including explicit resource limits and deterministic behavior.
3. A threat model and proposal for read-only inputs, strict allowlisting, and a deterministic synthetic positive/negative fixture set; it must explain why structural validation alone is insufficient and how unsafe execution, resource exhaustion, and false verification claims are prevented.

The review event is the next actual user request matching these triggers, or review whenever a proposed profile/contract change touches these fields; no calendar date or scheduled monitoring is implied. Meeting a trigger authorizes review only, not implementation. Any future execution, evaluator, new report semantics, or security boundary requires separately scoped owner permission and its own accepted ADR before implementation. A pure structural validator, if later proposed, may be considered separately under a technically delegated and specifically scoped ADR; this proposal grants no general code-execution permission. Arbitrary expressions, general-purpose evaluators, and implicit execution are rejected as out of scope and unnecessary absent the evidence above.

This ADR records a proposed decision deliverable only. Issue #91 remains OPEN and paused after delivery unless a governing owner policy or separately verified owner authorization explicitly permits a completion/closure decision. It is neither cancelled nor closed by this proposal.

## Alternatives Considered

- **Implement a computation validator/evaluator now** — rejected: there is no demonstrated blocked operation, bounded field subset, test contract, or threat model; execution would introduce a new security boundary without established need.
- **Treat field presence or successful syntax/profile validation as verified computation** — rejected: accepted unknown metadata is not semantic validation, evidence of execution, or proof of output correctness.
- **Claim full pure-OKF conformance or merge local graph/QMD results into it** — rejected: this exceeds existing profile scope and conflates independently labelled checks and their evidence.
- **Permanently cancel computation validation** — rejected: #91 explicitly allows measured deferral, not cancellation; concrete demand and a bounded safe contract can reopen review.

## Consequences

No runtime behavior, report text, field acceptance, metadata, source data, or CLI labels change. Existing inputs containing computation fields remain preserved and tolerated as unknown/additional metadata, but receive no computation-specific validation or execution. Existing profile, provenance/freshness, graph-integrity, and optional retrieval results retain their documented meanings and do not become a full pure-OKF claim. This decision makes no runtime-completion or whole-programme completion claim. Future implementation remains a separate, security-sensitive decision and authorization.

## Test Contract

This documentation-only proposal adds no tests and does not claim computation tests passed. Existing section labels and source-data preservation can evidence only the currently bounded checks and no-rewrite behavior; they do not show that computation fields were validated or executed. Any later implementation proposal must first add synthetic positive/negative fixtures for the named closed field subset and input/output contract, deterministic and resource-bound behavior, strict allowlisting/read-only guarantees, and explicit separation of computation outcomes from canonical profile, provenance/freshness, graph-integrity, and QMD results. Fixtures must not falsely label an unexecuted or unverified output as verified. The implementation's fourth acceptance criterion is conditional on implementation and must not be reported as unmet merely because this ADR defers implementation.

## References

- Issue #91: https://github.com/ozand/kb-bootstrap/issues/91
- Accepted ADR-003, ADR-005, ADR-006, ADR-047
- `docs/OKF_V0_2_CANONICAL_PROFILE.md`
- `docs/VALIDATION_COMPOSITION.md`
