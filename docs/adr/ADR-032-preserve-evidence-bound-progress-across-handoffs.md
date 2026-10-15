# ADR-032: Preserve evidence-bound progress across research handoffs

**Status**: Proposed
**Date**: 2026-10-15
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #129; ADR-010, ADR-021, ADR-022, ADR-026, ADR-027; ADR-031 (proposed W07 evidence bindings)

## Context

Issue #129 asks W08 to define portable progress so a later process can continue
from retained artifacts without replaying chat or refetching sources. The first
bounded task is a proposed contract and synthetic interruption fixtures, not an
implementation. Existing artifacts already state a versioned illustrative
record, save/load/check behavior and interruption cases in
`docs/proposals/W08-portable-handoff.md` and
`docs/fixtures/W08-interruption-examples.md` (PR #143). The correction artifact
was independently checked against its exact baseline: all 10 YAML blocks parsed,
the synthetic digest reproduced, six review findings addressed, and 14 focused
contract tests passed (Issue #129 comment 5881300221). These are documentation
and fixture checks; no runtime handoff behavior is established.

A persistent record format and its authority, evidence, retention, and concurrency
boundaries are reversal-worthy public-contract choices. ADR-032 records the
existing proposal's design rationale and non-goals so it can be reviewed before
any implementation. It does not approve the proposed schema. W03 (#124), W05
(#126), and W09 (#130) remain dependency-owned; their absence or future change
must not be papered over by W08. ADR-031 is Proposed and concerns W07 evidence
bindings, not a prerequisite registry for ordinary W08 progress.

### Problem statement

A proposed handoff must preserve bounded, inspectable progress tied to the exact
artifact revisions and evidence observed, while preventing a saved summary,
interrupted write, stale evidence, or lost remote acknowledgement from being
mistaken for verified current completion or authorization.

## Decision

W08 proposes a caller-selected, versioned local handoff record whose current
progress is checked against opaque dependency-owned artifact and evidence
references before continuation. The record is a resumability aid, not canonical
knowledge, an authority grant, or proof beyond the checks explicitly observed.

### What this IS

1. The proposed record describes bounded objective/scope, material actually
   captured/read/analyzed, output standing, steps and attempts, checks, blockers,
   next action, and retention/privacy metadata. The exact illustrative vocabulary
   and examples remain in the W08 proposal and fixtures; this ADR does not define
   a second serialization or reference schema.
2. Source, capture, output, and evidence identities/revisions are opaque values
   owned and interpreted only by their accepted W03/W05 interfaces. W08 records
   observations; it does not duplicate those contracts or infer equivalence.
3. A current completion view requires matching input/output revisions and all
   required evidence to exist, match, and pass through the owning interfaces.
   Historical completed attempts may remain truthful history while current
   resumability is blocked or requires revalidation after drift, expiry, revocation,
   or unavailability.
4. A retry of the same step first revalidates current artifact/evidence
   availability, revision, and validity. It may reuse an identical prior result
   only when those checks pass; it does not silently rerun expensive work or
   reuse unavailable evidence.
5. A local save candidate is identified from exact payload bytes excluding its
   own result-identity envelope field. A single local writer compares the loaded
   baseline before replacement; this is not a distributed lock or cross-system
   transaction guarantee.
6. Local save and remote publication are distinct. A lost remote acknowledgement
   leaves publication outcome unknown; an authorized actor must reconcile the
   exact intended remote object read-only before any separately authorized retry.
7. Persisted records follow owner, storage class, retention, access, integrity,
   availability, and disposal vocabulary from `docs/EVIDENCE_RETENTION.md`.

### What this IS NOT

This decision does not accept or freeze the illustrative record serialization;
implement save/load/check commands, a daemon, host lifecycle hook, lock service, or
remote publisher; discover chat sessions or broad runtime directories; define
W03/W05/W09 schemas; authorize writes/publication; establish durable availability
or immutability; promote proposals into accepted knowledge or QMD; or require W07
claim-level bindings for basic progress. No private transcript, prompt, credential,
consumer corpus, or runtime state is copied into the record.

### Success criteria

Before any implementation is proposed as conforming, its synthetic tests must
show: continuation without prior chat using explicitly retained artifacts;
completion gated on matching required output/evidence; distinct partial, pending,
blocked, and complete observations; stale revisions and unavailable evidence
fail closed without erasing history; identical retries do not duplicate or bypass
revalidation; competing stale local writers cannot overwrite the selected record;
publication interruption remains unknown until authorized reconciliation; and
privacy/retention fields do not imply durable evidence or authority. These criteria
are design requirements, not evidence that a runtime currently satisfies them.

## Consequences

### What gets easier

Reviewers can trace the handoff proposal to one numbered decision and distinguish
its intended safety properties from implementation or owner acceptance. The
existing proposal and fixtures remain the single detailed design source.

### What gets harder

Future implementation must coordinate with the owning W03/W05/W09 contracts,
keep current resumability distinct from historical completion, and test each
observable evidence boundary. The proposal remains blocked wherever those
interfaces cannot provide a check; a compact handoff cannot promise availability
or cross-system atomicity.

### What does not change

ADR-010 remains the raw-source revision foundation; ADR-021 keeps generated
research progress distinct from canonical lifecycle status; ADR-022 keeps
external actions under explicit scoped authority; ADR-026 remains caller-directed
lookup; ADR-027 governs retention of selected existing captures. ADR-031 remains
Proposed and is not accepted or required by this ADR. No runtime, migration,
consumer write, data acquisition, or canonical promotion is authorized.

## Alternatives Considered

- **Treat the W08 proposal alone as the accepted public contract:** rejected
  because Issue #129 explicitly defers implementation until public record
  semantics are accepted, while a prose proposal is not itself owner acceptance.
  This ADR records the choice for review without converting it to Accepted.
- **Make the progress record a transcript or chat-session export:** rejected
  because it would couple continuation to a host-specific format and retain
  unnecessary private/runtime content instead of references to retained evidence.
- **Infer completion from saved text, a successful local write, or a published
  link:** rejected because none independently establishes matching revisions,
  required evidence, acceptance, or current authorization.
- **Use a distributed transaction/lock or automatic remote retry:** rejected
  because the existing proposal has no accepted cross-system coordination
  interface and a lost acknowledgement cannot prove remote absence.
- **Do nothing:** leaves no reviewable decision rationale for the already drafted
  W08 proposal and makes later implementation vulnerable to treating illustrative
  fields as an accepted schema.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| The detailed proposal and fixtures remain the referenced W08 design source, with no duplicate schema introduced here | `tests/test_adr_lifecycle.py::test_every_adr_is_listed_in_index` plus exact-path review | Structural test exists; reference review not automated |
| Current completion is bound to matching revisions and required evidence; stale/unavailable evidence is not implicit success | Synthetic W08 interruption cases in `docs/fixtures/W08-interruption-examples.md` | Documentation fixtures parsed and independently reviewed; no runtime test |
| Historical attempts survive drift/expiry while current resumability blocks or revalidates | W08 fixture cases 2–4 | Documentation fixtures parsed and independently reviewed; no runtime test |
| Lost publication acknowledgement remains unknown and is reconciled before retry | W08 fixture case 6 | Documentation fixture parsed and independently reviewed; no publisher/runtime test |
| The ADR remains Proposed and index/file references remain consistent | `tests/test_adr_lifecycle.py` | Existing lifecycle suite; run for this change |

## Rollback

Because this ADR is Proposed, it may be amended or withdrawn before acceptance;
its number remains reserved if withdrawn. Removing this proposal does not remove or
rewrite the W08 proposal/fixtures, authorize implementation, or change any retained
record. After acceptance, any reversal must use a superseding ADR and preserve the
historical decision.

## References

- Issue #129 and research checkpoint comment 6182114080
- PR #143, W08 proposal and interruption fixtures; exact correction verification:
  Issue #129 comment 5881300221
- `docs/proposals/W08-portable-handoff.md`
- `docs/fixtures/W08-interruption-examples.md`
- `docs/EVIDENCE_RETENTION.md`
- ADR-010, ADR-021, ADR-022, ADR-026, ADR-027
- ADR-031 (Proposed W07 evidence bindings; separate scope)
