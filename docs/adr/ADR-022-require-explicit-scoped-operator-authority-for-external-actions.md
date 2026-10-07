# ADR-022: Require explicit scoped operator authority for external actions

**Status**: Accepted
**Date**: 2026-10-07
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #130; Issue #122; ADR-014, ADR-015, ADR-018; proposed policy in PR #137

## Context

Issue #130 requires execution/publication authority to remain distinct from sensitivity, applicability, read scope, local write/review, and tool availability. The current Proposed W09 policy in open PR #137 states that a configured adapter is availability, not consent, and that outbound operations need current authorization. It does not yet constitute an accepted contract. Accepted ADR-014 preserves ordinary `local-smoke-verified; host-egress-unverified` usability while requiring separately verified host-level egress denial before sensitive/private processing. Accepted ADR-015 authorizes an additive bounded `validate-core`; it does not authorize changing legacy validation or adding a generic capability engine. The broader W01 capability design in #122 is also not accepted. No current proposal grants authority to infer publication permission from a model score, classifier result, document instruction, or adapter configuration.

**Evidence strength:** repository status, accepted ADR text, and open PR/Issue states were directly inspected at the time of drafting. No runtime enforcement is claimed or measured by this document.

### Problem statement

A future operation must not treat presence/readiness of a tool, permission to read data, or permission to write a local artifact as authorization to acquire, execute an external action, send data, or publish. The precise representation and enforcement boundary need owner approval before implementation.

## Decision

**Only after separate owner acceptance**, require a current, explicit, operation-scoped operator authorization before an operation crosses an external-action boundary. This ADR proposes a decision contract, not an authorization engine or persisted schema.

### Scope and proposed distinctions

1. Keep technical state separate from authority: capability configuration/availability, a readiness probe (`NOT RUN` when unperformed), operation policy (`ALLOW`, `BLOCKED`, or `UNAVAILABLE`), and observed host-egress isolation are separate facts. A policy denial does not relabel a configured tool disabled or broken.
2. Treat these permissions as independent and non-transitive: read a selected source; write a local artifact to an exact target; review/approve it; acquire an asset; execute an external action; and transmit/publish to an exact destination. In particular, local export may be independently authorized when outbound publication is denied. A writer, reviewer, candidate, or publisher has no other role merely by implication.
3. An external-action authorization must be an explicit operator decision within the trusted interaction or delegated workflow that authorizes the operation, and be bounded to the actor/context, operation, data/revision scope, exact destination, purpose, and validity/revocation conditions. It may authorize a bounded sequence of steps; a new prompt at every technical boundary is not required when those steps remain within the current approved scope. Enforcement rechecks scope and any known expiry or revocation immediately before crossing the boundary. A config value, environment variable, document, adapter, prior receipt, model output, or untrusted prompt text cannot self-assert or widen operator approval. This ADR does not claim cryptographic identity proof or prescribe an identity platform. Authentication and representation for unattended/delegated workflows, revocation signaling, and reconciliation with W01 remain separate owner decisions; until accepted, such workflows cannot claim authority beyond an explicit existing operator-approved delegation.
4. Configuration, source text, paths, manifests, indexes, environment values, prior receipts, model outputs, classifier labels/non-detections, confidence scores, and tool availability never create or widen authority. Missing, conflicting, expired, or unverifiable authority blocks the external action with a sanitized result and no fallback route.
5. This requirement applies to future external actions; it does not insert policy checks into Accepted ADR-015's bounded core-only validation, change legacy `validate`, make optional local adapters mandatory, or grant authority to any remote adapter in #108.

### What this IS NOT

This proposal is not owner approval, implemented enforcement, a universal capability namespace, an identity/authentication design, a persisted grant/receipt schema, a host-firewall guarantee, or permission to process, acquire, publish, delete, or migrate real data. It does not supersede or weaken ADR-014 or retained ADR-011/013 requirements. Ordinary harmless smoke retains ADR-014's `local-smoke-verified; host-egress-unverified` label; sensitive/private processing still requires separately observed platform-scoped host egress denial. Intentional-client interception is not OS-level isolation.

### Success criteria if accepted

For each external action, missing approval or a mismatch in actor/context, operation, data/revision scope, exact destination, or purpose yields `BLOCKED`/`UNAVAILABLE`, zero outbound calls and remote writes; expired or revoked approval does likewise. A current matching operator decision permits only the named operation and target. An authorized local artifact can still be written under its separate local-write authority; capability readiness, probe state, policy result and host-isolation evidence remain distinguishable; and no document/model/metadata-derived value is accepted as authority.

## Consequences

### What gets easier

Reviewers can reason separately about an available mechanism, an allowed local result, and permission to cross an external boundary. A local artifact need not be conflated with its later publication.

### What gets harder

Every external-action path must identify and recheck an operator authority source, exact target and revocation state. W01 and W09 interface reconciliation is required; a missing authentication or delegation decision can block implementation.

### What does not change

Accepted ADR-014 ordinary/sensitive assurances, retained ADR-011/013 acquisition and peer constraints, ADR-015 core-only semantics, ADR-018 adapter scope, existing publication contracts, and #108's separate boundary remain in force. No action is authorized merely by this proposal.

## Alternatives Considered

- **Treat configured/readied tools or source metadata as consent:** rejected because mechanism availability and untrusted content do not identify an authorized actor, purpose, data scope, or destination.
- **Use only coarse repository roles (reader/writer/reviewer) as external-action consent:** rejected because those roles do not bind a specific action, data revision, purpose, or exact destination; a narrower operator decision is still required.
- **Couple local file output and remote publication into one permission:** rejected because a local-only artifact may be separately authorized without egress.
- **Require host egress denial for every harmless local operation:** rejected because it would contradict ADR-014's explicitly retained ordinary smoke distinction without proving more about the application-level authorization decision.
- **Add a universal persisted policy engine in this ADR:** rejected as broader than #130's bounded decision and dependent on unaccepted W01 choices.

## Test Contract

These are proposed synthetic tests, not tests already implemented or evidence of runtime enforcement.

| Claim | Test | Currently |
|---|---|---|
| Missing external-action authority causes zero calls/writes and no fallback | `tests/test_execution_authority.py::test_denied_external_action_has_no_side_effects` | not yet written |
| Matching current operator decision permits one outbound operation only to its named target | `tests/test_execution_authority.py::test_authorized_target_is_used_exactly` | not yet written |
| Wrong target, actor/context, operation, revision, or purpose is denied without calls/writes | `tests/test_execution_authority.py::test_mismatched_or_revoked_authority_is_denied` | not yet written |
| Local artifact permission is independent of denied publication | `tests/test_execution_authority.py::test_local_write_can_be_allowed_when_publication_is_denied` | not yet written |
| Configuration, readiness probe, policy result and host-egress evidence remain distinct | `tests/test_execution_authority.py::test_readiness_probe_and_policy_states_are_not_conflated` | not yet written |
| Source instructions, metadata and classifier results cannot grant external authority | `tests/test_execution_authority.py::test_untrusted_content_cannot_grant_action_authority` | not yet written |
| Config/document/model content cannot self-assert or widen operator approval; unattended automation without an accepted operator-approved delegation cannot claim authority | `tests/test_execution_authority.py::test_untrusted_grant_source_is_blocked` | not yet written |
| Core-only and legacy validation contracts do not gain new checks | `tests/test_core_authority_compatibility.py::test_validate_core_and_legacy_validate_unchanged` | not yet written |

## Rollback

Before acceptance, withdraw this proposal; no runtime state exists to migrate. After acceptance, amend it only through an explicitly superseding ADR. Any future grants, receipts, or stored consumer data require separately accepted representation, retention and rollback contracts; this ADR authorizes no deletion or automatic revocation migration.

## References

- Issue #130 acceptance criteria and W09 research comments.
- Issue #122 and accepted additive slice ADR-015; broader W01 capability proposal remains unaccepted.
- Accepted ADR-014; retained ADR-011/013 clauses; ADR-018; Issue #108.
- `docs/EVIDENCE_RETENTION.md` and proposed `docs/proposals/W09-data-policy.md` in open PR #137 (not accepted); Issue #130 research comments 6033516431 and 6033526619.
