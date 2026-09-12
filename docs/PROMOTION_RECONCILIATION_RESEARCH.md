# Research: reconciliation after cross-repository lesson-promotion failures

## Decision summary

Do not introduce distributed transactions, automatic rollback, cross-repository locks, or background synchronization for lesson promotion.

Continue to preserve one-owner writes and explicit review. If incident evidence later justifies implementation, the first bounded option should be an idempotent operation receipt plus read-only reconciliation guidance and separately authorized compensating actions. A receipt must describe intended and observed state; it must never authorize a retry by itself.

## Evidence base and limitations

This research evaluates the current repository contracts:

- reviewed promotion and demotion workflow;
- write-free shared contribution candidate preparation;
- explicit repository ownership preflight;
- commit/PR completion containment;
- shared metadata and registry validation;
- one-destination capture and promotion policy.

Within the repository history, current policy documents, and one bounded local knowledge-base search examined for this research, no confirmed sanitized incident was found where an approved promotion partially wrote two authoritative lesson stores, deleted a source before destination verification, or required atomic rollback across repositories. Repository history includes wrong-owner workflow corrections and GitHub CLI compatibility failures, but those are governance/tooling failures rather than evidence that lesson stores need a distributed transaction.

A bounded local knowledge-base search found no matching indexed incident record. The `workspace-kb` collection was available on 2026-09-12 and the query class covered cross-repository promotion, reconciliation, idempotent receipts, compensation, and distributed transactions; result count was zero. This is an evidence limitation and not proof that no incident exists.

There is no measured incident rate, recovery-time distribution, duplicate-publication count, authorization-drift count, or unrecoverable-loss record. The recommendation therefore defaults to the least complex safe mechanism and defines explicit thresholds for reconsideration.

## Current workflow and gap

The existing manual workflow prescribes a strong failure-isolation boundary:

1. The source remains unchanged while a candidate is prepared.
2. Candidate preparation is local and write-free.
3. A human approves one explicit destination.
4. Only the destination repository's normal contribution workflow may write.
5. The workflow requires destination identity, index membership, and retrieval to be verified by the operator.
6. Source deletion, demotion, or shared retraction is a separate reviewed operation.
7. A sanitized result receipt records the reviewed outcome.

This avoids the most dangerous transaction shape: one operation mutating two authoritative stores.

The current receipt is not sufficient for deterministic reconciliation. It records source/destination IDs and a result, but it does not define:

- a stable operation identity;
- source candidate digest and destination content digest;
- intended state versus observed state;
- repository/branch/commit or PR containment evidence for each attempted write;
- attempt number, prior receipt, supersession, or reconciliation status;
- authorization expiry or whether the original reviewer approved a retry;
- whether a compensating action was separately approved and completed.

These are potential future receipt fields, not fields authorized for implementation by this research Issue.

## Failure taxonomy

| Stage | Concrete failure | Observable state | Safe default response |
|---|---|---|---|
| Source selection | Source ID, owner, or scope is ambiguous | No authoritative source tuple | Block; write nothing |
| Candidate preparation | Sanitization, metadata, or output creation fails | Source unchanged; no destination write | Correct candidate locally or abandon |
| Review | Approval missing, expired, or for another destination | Candidate may exist; no authorized write | Block; obtain a new explicit review |
| Destination preflight | Repository, branch, identity, or permissions mismatch | No safe destination write | Block; do not change target automatically |
| Destination branch/commit | Local destination change exists but commit fails | Destination worktree may be dirty; source unchanged | Preserve worktree evidence; retry only after repository-local review |
| Push | Commit exists locally but push result is unavailable | Destination remote state unknown | Reconcile remote commit/branch/PR read-only before retry |
| Pull request | Push succeeded but PR creation/result is unavailable | Destination branch may exist without PR | Discover exact branch/commit read-only; create PR only with fresh authorization |
| Merge | PR exists but merge fails or result is unavailable | PR may be open, merged, or conflicted | Query PR and default branch; do not replay merge blindly |
| Destination validation | Merge/write succeeded but registry or retrieval validation fails | Destination contains invalid or incomplete lesson | Keep source; open a destination-owned corrective action |
| Receipt recording | Destination verified but final receipt write fails | Product state is correct; governance evidence incomplete | Reconstruct a receipt from authoritative repository evidence; do not republish lesson |
| Source retention | Destination verified but source-retention decision is pending | Both source and promoted lesson exist by design | No action; duplication is not partial failure |
| Source retraction | Separate approved retraction fails | Destination remains; source remains | Reconcile/retry retraction independently; never roll back destination automatically |
| Authorization changes | Actor/reviewer permission changes between attempts | Prior approval may no longer be valid | Require current authorization; old receipt is evidence only |

## State model for reconciliation

A future read-only reconciler should classify, not mutate:

| State | Meaning | Allowed next step |
|---|---|---|
| `prepared` | Candidate exists locally; no destination evidence | Review or discard candidate |
| `approved` | One destination approved; no write evidence | Run destination workflow once with current authorization |
| `destination-unknown` | An attempt occurred but remote state is unavailable | Query repository/branch/PR/commit before any retry |
| `destination-pending` | Branch or PR exists but is not merged | Continue that same destination workflow; do not create a duplicate |
| `destination-invalid` | Destination write exists but validation failed | Destination-owned corrective Issue/PR |
| `destination-verified` | Destination content and containment are verified | Record/finalize receipt; preserve source |
| `receipt-incomplete` | Destination is verified but receipt is absent/incomplete | Reconstruct evidence-only receipt |
| `retraction-pending` | Separate source retraction was approved but not completed | Reconcile only the retraction operation |
| `complete` | Destination verified and required receipts exist | No action |
| `superseded` | A reviewed replacement operation owns further action | Follow replacement reference; do not replay old operation |

The reconciler must never infer success from a candidate, local commit, push output, HTTP status, or receipt alone. The authoritative observation depends on the claimed layer: repository/PR containment for publication, registry validation for stored identity, lookup output for retrievability, and current authorization for a new mutation.

## Options comparison

| Option | Recovery capability | Safety | Complexity | Offline/local fit | Recommendation |
|---|---|---|---|---|---|
| Current manual workflow and minimal receipt | Human can inspect each repository | Strong one-owner boundary; weak deterministic replay evidence | Low | Strong | Keep as baseline |
| Idempotent operation receipt plus read-only reconciliation | Detects existing branch/PR/commit/destination and prevents blind duplicate retries | Strong if receipt is evidence-only and repository observations are authoritative | Medium | Strong; reconciliation can be local plus explicit GitHub reads | First implementation to consider if thresholds are met |
| Explicit compensating actions | Corrects destination or retracts source through normal owner workflow | Strong when separately authorized; never automatic | Medium | Strong | Use only for a concrete verified state |
| Automatic saga/orchestrator | Could sequence retries and compensations | Expands authorization and background-write surface | High | Weak | No-go without sustained incident evidence |
| Distributed transaction/two-phase commit | Attempts atomic commit across repositories/stores | Poor fit for Git repositories and human PR review; coordinator becomes critical authority | Very high | Poor | No-go |

## Illustrative future receipt profile (not a supported contract)

This section records candidate design dimensions for comparison only. It is not an accepted schema, public contract, implementation authorization, or ADR decision; any implementation requires a new Issue and ADR.

If a future Issue authorizes a persisted reconciliation format, the minimum candidate profile could include:

```yaml
receipt_version: 1
operation_id: immutable-public-id
operation: promote | demote | retract
source:
  scope: project | workspace
  owner: owner/repository | external-store-name
  lesson_id: PUBLIC-ID
  candidate_digest: sha256-public-content
intent:
  destination_scope: project | workspace
  destination_owner: owner/repository | external-store-name
  destination_branch: public-branch
approval:
  reviewer: public-handle-or-team
  actor: public-handle-or-team
  decision: approved
  approved_digest: sha256-public-content
attempt:
  number: 1
  prior_receipt: null | immutable-public-id
observed:
  state: prepared | approved | destination-unknown | destination-pending | destination-invalid | destination-verified | receipt-incomplete | retraction-pending | complete | superseded
  destination_lesson_id: PUBLIC-ID | pending
  commit: public-commit | null
  pull_request: public-url | null
  content_digest: sha256-public-content | null
reconciliation:
  checked_at: RFC3339 timestamp
  checked_by: public-handle-or-team
  superseded_by: null | immutable-public-id
```

This profile is illustrative research, not a new supported data format. A future ADR must decide exact fields, versioning, storage ownership, digest canonicalization, and compatibility before implementation.

### Idempotency rules

If a future implementation is authorized, the following rules should be evaluated:

- `operation_id` identifies one reviewed intent, not one process invocation.
- The approved candidate digest, source tuple, destination owner, and destination branch are immutable for that operation.
- A retry must first reconcile authoritative destination state using the same operation identity.
- If the destination already contains the approved digest under a verified lesson ID, the operation advances to `destination-verified`; it does not write again.
- If an existing branch/PR contains a different digest, block as a conflict; do not overwrite or open a second PR.
- A new attempt increments `attempt.number` and references prior evidence; it does not erase failed/unknown attempts.
- A superseded operation cannot be replayed.
- Receipt presence alone never proves authorization, publication, merge, registry validity, or retrieval.

## Compensating actions

Compensation is a new owner-authorized operation, not transaction rollback.

| Verified state | Possible compensation | Required owner |
|---|---|---|
| Wrong unmerged destination branch/PR | Close the PR or delete the branch only through the destination owner's normal, explicitly authorized repository workflow | Destination repository |
| Merged invalid destination lesson | Correct or deprecate through a new destination PR | Destination repository |
| Duplicate destination lessons | Choose canonical lesson; deprecate duplicate through review | Destination repository |
| Source was retracted too early | Restore the source through a source-owner-approved recovery PR if the required history is available | Source repository |
| Promotion should be reversed | Run reviewed demotion/deprecation workflow | Each affected owner, as separate operations |
| Receipt contains wrong public metadata | Supersede receipt without rewriting history | Receipt owner |

Automatic deletion, force push, source mutation, shared-store write, or dual-store rollback remains prohibited.

## Security, authorization, and replay boundaries

### Authorization

- A prior approval authorizes only its immutable source digest, operation, destination owner, and destination branch.
- Authorization is checked again immediately before every mutation; a historical receipt cannot grant current access.
- Source and destination owners authorize their own operations independently.
- A reconciliation reader needs read-only access only; it must not acquire mutation credentials by default.

### Replay

- Reject a replay when the operation is complete, superseded, targets different immutable intent, or lacks current authorization.
- Reconcile branch, commit, PR, destination lesson ID, digest, registry entry, and lookup result before retry.
- Unknown remote state is a blocking state, not permission to repeat the write.
- Attempt history is append-only; do not rewrite failed or unknown evidence into success.

### Data and privacy

- Receipts contain only sanitized public repository metadata, public IDs, bounded digests, states, and public URLs.
- Never include credentials, authenticated remote URLs, private payloads, raw lesson content, local paths, runtime/session data, or private identities.
- Digest canonicalization must be defined before it is trusted; a hash of different serialization forms is not equality evidence.

### Failure isolation

- One operation writes to one owner at a time.
- Source preservation means destination failures do not require source rollback.
- Retraction/deletion is always a separate operation and receipt.
- A destination correction never silently changes the source.
- Reconciliation failure cannot authorize mutation or change product state.

## Go/no-go thresholds

Threshold windows are rolling 12-month periods. A confirmed incident is one unique sanitized incident record with stage, intended owner, observed state, recovery action, elapsed recovery time, outcome, and evidence of causality; duplicate reports count once. Recovery time runs from first detection to verified restoration or accepted containment. "Adopt" means an independent repository completed the same reviewed workflow with a merged, attributable result. "More than two authoritative systems" means at least three systems that must commit the same indivisible operation. Maintainer hours must come from recorded incident/recovery notes. Missing measurements make a threshold not evaluable and therefore preserve the no-go default; they do not count as zero incidents.

### Implement an idempotent receipt profile and read-only reconciler only if one condition is met

1. At least two confirmed sanitized promotion incidents within 12 months reached `destination-unknown`, created duplicate destination work, or required manual reconstruction of branch/PR/commit state.
2. One confirmed incident required more than two hours of maintainer recovery because the existing receipt could not link approved intent to authoritative destination evidence.
3. Two independent consumer repositories adopt promotion and require a shared machine-readable receipt for the same destination workflow.
4. A compliance or audit requirement explicitly requires immutable attempt/supersession evidence that the current receipt cannot provide.

A qualifying incident record must include sanitized stage, intended owner, observed state, recovery action, elapsed recovery time, duplicate/loss outcome, and which missing receipt field would have changed the result.

### Permit automated compensating actions only if all conditions are met

- at least three confirmed incidents of the same compensable state occur within 12 months;
- the compensation is reversible, destination-owner authorized, and tested in a disposable repository;
- false-positive compensation has a bounded, demonstrated recovery path;
- an accepted ADR defines authorization, concurrency, replay, audit, and rollback controls.

### Consider distributed transactions only if all conditions are met

The conditions below are conjunctive: every condition must be satisfied by recorded evidence.

- more than two authoritative systems must commit one indivisible business operation;
- preserving the source and reconciling destination state cannot meet a documented recovery objective;
- at least five confirmed partial-commit incidents occur within 12 months despite idempotent receipts and read-only reconciliation;
- the incidents cause unrecoverable loss or a measured cumulative recovery cost greater than 40 maintainer-hours;
- a prototype demonstrates atomicity, offline/PR workflow compatibility, authorization isolation, coordinator recovery, and a simpler design cannot meet the requirement.

Absent all these conditions, distributed transactions remain a no-go.

## Recommendation

**No-go for distributed transactions, automatic saga orchestration, and automatic compensation.**

The current one-owner/manual-review workflow is proportionate to the available evidence. Preserve the source, reconcile authoritative destination state before retry, and use separate explicitly reviewed compensating actions when a concrete verified state requires correction.

If measurable evidence crosses the first threshold, create a separate implementation Issue and ADR for a versioned idempotent receipt plus read-only classification. Do not combine receipt persistence, reconciliation reads, and compensating writes into one increment.

## Non-actions

This research does not:

- add or change a supported receipt schema;
- implement a reconciler, coordinator, saga, lock, or transaction service;
- retry a branch, push, pull request, merge, lesson publication, or retraction;
- write to project, shared, cache, candidate, or consumer stores;
- change authorization, repository ownership, routing, lesson IDs, or promotion behavior;
- create background work or synchronization.
