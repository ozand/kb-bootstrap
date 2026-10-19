# ADR-032: Preserve evidence-bound progress across research handoffs

**Status**: Proposed
**Date**: 2026-10-19
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #129; ADR-010, ADR-021, ADR-022, ADR-026, ADR-027; ADR-031 (Accepted W07 evidence bindings, optional to base W08 progress)

## Context

Issue #129 asks W08 to define portable progress so a later process can continue from retained artifacts without replaying chat or refetching sources. Its bounded first task is a Proposed contract with synthetic interruption examples; it is not runtime implementation or acceptance of a persisted format.

The self-contained W08 proposal and fixtures in this packet are refreshed from PR #143's reviewed correction head `756006957fa9b553d46f7ac1f16b46182680035c` and its retained receipt (Issue #129 comments `6182114080` and `5881300221`; PR #143 description records exact artifact hashes and reports 14 focused contract tests). PR #143 is still open/unmerged; its design/tests are not part of current main and no runtime handoff behavior is established. This replacement packet carries the synthetic proposal/fixtures into current main for review rather than depending on absent PR-only paths.

Accepted ADR-022 governs scoped authority for external actions; it does not grant any authority through handoff records. Accepted ADR-021 keeps operational research progress distinct from canonical knowledge lifecycle status. Accepted ADR-027 governs selected retained captures, not W08 serialization. ADR-031 is accepted but remains an optional W07 evidence-binding interface, not a prerequisite for basic W08 progress. W03/W05/W09 dependency contracts and W08 persistence semantics remain bounded proposals, not accepted implementation inputs.

### Problem statement

A proposed handoff must preserve bounded, inspectable progress tied to the exact artifact revisions and evidence observed, while preventing a saved summary, interrupted write, stale evidence, or lost remote acknowledgement from being mistaken for verified current completion or authorization.

## Decision

W08 proposes a caller-selected, versioned local handoff record whose current progress is checked against opaque dependency-owned artifact and evidence references before continuation. The record is a resumability aid, not canonical knowledge, an authority grant, or proof beyond checks explicitly observed.

The co-located `docs/proposals/W08-portable-handoff.md` and `docs/fixtures/W08-interruption-examples.md` are detailed **Proposed design materials** for review. Their illustrative vocabulary is not an accepted schema, interface, runtime contract, or implementation. This ADR records the bounded rationale and decision boundaries; it does not create a second serialization or duplicate W03/W05/W09 reference schemas.

### What this IS

1. The proposed record describes bounded objective/scope, material actually captured/read/analyzed, output standing, steps and attempts, checks, blockers, next action, and retention/privacy metadata. The proposal and synthetic examples are the source for candidate vocabulary, not a contract to implement unchanged.
2. Source, capture, output, and evidence identities/revisions remain opaque values owned and interpreted only by their respective accepted interfaces. W08 records observations; it does not duplicate those contracts or infer equivalence.
3. A current completion view requires matching input/output revisions and required evidence to exist, match, and pass through the owning interfaces. Historical completed attempts remain history while current resumability may be blocked or require revalidation after drift, expiry, revocation, or unavailability.
4. A retry of the same step first revalidates current artifact/evidence availability, revision, and validity. It may reuse an identical prior result only when those checks pass; it does not silently rerun expensive work or reuse unavailable evidence.
5. The illustrative local save identity is computed over exact payload bytes excluding its own result-identity envelope field. A single local writer compares the loaded baseline before replacement; this is not a distributed lock or cross-system transaction guarantee. The example is not an accepted serialization or hash implementation contract.
6. Local save and remote publication are distinct. A lost remote acknowledgement leaves publication outcome unknown; an authorized actor must reconcile the exact intended remote object read-only before any separately authorized retry.
7. Persisted records, if later accepted, must follow the owner, storage class, retention, access, integrity, availability, and disposal vocabulary in `docs/EVIDENCE_RETENTION.md`.

### What this IS NOT

This ADR does not accept or freeze the illustrative serialization; implement save/load/check commands, a daemon, host lifecycle hook, lock service, or remote publisher; discover chat sessions or broad runtime directories; define W03/W05/W09 schemas; authorize writes/publication; establish durable availability or immutability; promote proposals into accepted knowledge or QMD; or require W07 claim-level bindings for basic progress. No private transcript, prompt, credential, consumer corpus, or runtime state is included in the synthetic materials.

### Success criteria if a later implementation is proposed

Synthetic tests for a separately accepted implementation should show continuation without prior chat using explicitly retained artifacts; completion gated on matching required output/evidence; distinct partial, pending, blocked, and complete observations; stale revisions/unavailable evidence fail closed without erasing history; identical retries do not duplicate or bypass revalidation; competing stale local writers cannot overwrite the selected record; publication interruption remains unknown until authorized reconciliation; and privacy/retention fields do not imply durable evidence or authority. These are design expectations, not evidence that runtime behavior exists or passes.

## Consequences

### What gets easier

Reviewers can trace W08's proposed safety properties and synthetic interruption cases in current main, distinguish them from owner acceptance/implementation, and inspect source proposal and examples without depending on an unmerged PR.

### What gets harder

Future implementation must coordinate with owner-approved W03/W05/W09 contracts, keep current resumability distinct from historical completion, and test each observable evidence boundary. The proposal remains blocked wherever those interfaces cannot provide a qualifying check; a compact handoff cannot promise availability or cross-system atomicity.

### What does not change

Accepted ADR-010 remains the raw-source revision foundation; ADR-021 keeps generated research progress distinct from canonical lifecycle status; ADR-022 keeps external actions under explicit scoped authority; ADR-026 remains caller-directed lookup; ADR-027 governs retention of selected existing captures. ADR-031 is accepted but optional for base progress. No runtime, migration, consumer write, data acquisition, or canonical promotion is authorized.

## Alternatives Considered

- **Treat the W08 proposal alone as an accepted public contract:** rejected because #129 defers implementation until public record semantics are accepted; prose/fixtures are not owner acceptance. This ADR records rationale without converting them to Accepted.
- **Make the progress record a transcript or chat-session export:** rejected because it would couple continuation to a host-specific format and retain unnecessary private/runtime content instead of references to retained evidence.
- **Infer completion from saved text, a successful local write, or a published link:** rejected because none independently establishes matching revisions, required evidence, acceptance, or current authorization.
- **Use a distributed transaction/lock or automatic remote retry:** rejected because no accepted cross-system coordination interface exists and a lost acknowledgement cannot prove remote absence.
- **Do nothing:** preserves only unmerged design material, leaving no current-main review packet to inform a later owner decision; it remains acceptable to reject this proposal and keep implementation out of scope.

## Test Contract

| Claim | Test | Current evidence/status |
|---|---|---|
| ADR numbering/index and mandatory sections remain structurally consistent | `tests/test_adr_lifecycle.py::test_adr_index_and_files_match_both_directions`; `test_adr_headers_match_index_and_required_sections_exist` | Existing lifecycle tests; run for this refresh |
| Proposal and fixtures are explicitly labeled Proposed/synthetic and remain linked from ADR-032 | Manual exact-path review of the two co-located W08 documents | Documentation review only; not automated |
| Synthetic examples represent bounded reading vs analysis, external observed acceptance vs granting it, and result identity excluding its own envelope field | W08 proposal and fixture Cases 1 and 7 | Documentation fixtures only; no runtime test |
| Historical attempts survive drift/expiry while current resumability blocks or revalidates; retries revalidate evidence | W08 fixture Cases 2–4 | Documentation fixtures only; no runtime test |
| Lost publication acknowledgement remains unknown and requires authorized read-only reconciliation before retry | W08 fixture Case 6 | Documentation fixture only; no publisher/runtime test |
| W08 does not implement W03/W05/W09, runtime storage, or authority | Exact changed-file scope and manual non-claim review | Source scope only; no runtime enforcement claim |

## Rollback

Because this ADR and linked W08 materials are Proposed, they may be amended or withdrawn before acceptance; their numbers/references remain reserved if withdrawn. Removing this packet does not authorize or remove runtime behavior, rewrite consumer data, or alter historical evidence. After owner acceptance, any reversal must use a superseding ADR and preserve historical decisions.

## References

- Issue #129 and research/design checkpoint comments `6182114080` and `6264224858`.
- PR #143 reviewed W08 correction head `756006957fa9b553d46f7ac1f16b46182680035c` and its retained design/verification receipt (PR description; Issue comment `5881300221`). PR #143 remains unmerged; this is source provenance, not merged-main evidence.
- `docs/proposals/W08-portable-handoff.md` and `docs/fixtures/W08-interruption-examples.md` in this Proposed packet.
- `docs/EVIDENCE_RETENTION.md`.
- Accepted ADR-010, ADR-021, ADR-022, ADR-026, ADR-027; ADR-031 (accepted W07 evidence binding, optional to base W08 progress).
