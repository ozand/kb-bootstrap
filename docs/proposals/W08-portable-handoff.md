# W08 portable research handoff (Proposed)

Status: **Proposed design only**. This document is an independent W08-A design
input for Issue #129; it is not an accepted schema, runtime contract, or
implementation. W03, W05, and W09 decisions are not accepted by this document.

## Purpose and boundaries

A portable progress record lets another process continue a bounded research
study from retained, explicitly referenced material without chat history. It
records operational observations and intentions, not truth, approval, or
authority. In particular, saving or loading a record does not:

- prove that a source was read or a check passed;
- accept a proposal, complete a study, or authorize the next mutation;
- publish anything to GitHub or promote anything into canonical knowledge;
- replace source, output, provenance, completion, or retention contracts; or
- make a local artifact durable, immutable, public, or safe to disclose.

The design adds no daemon, full transcript, mandatory claims registry,
host-specific hook, search-index write, distributed transaction, or automatic
promotion. The record contains references to retained artifacts, never embedded
source bodies or a second source schema.

## Proposed vocabulary

These axes are independent and must not be collapsed into one `status` field.

### Material observation

For each opaque source/capture reference, record one of:

- `captured`: the referenced revision was retained, but reading is not claimed;
- `read`: the bounded material identified by the reference was read;
- `partially-read`: a stated subset was read and the unread remainder is named;
- `partially-analyzed`: a stated subset was analyzed and the remainder is named.

`captured` does not imply `read`; partial reading does not imply analysis; `read`
does not imply analysis; and partial analysis never implies whole-source
analysis. A later accepted W03 contract must define reference identity, revision
comparison, and what it means for a capture to be retained. W08 only consumes
those opaque values.

### Output standing

- `provisional`: a candidate revision that has not been accepted;
- `accepted`: an output revision accepted through the future W05-owned process.

Acceptance is an externally evidenced observation, not a transition W08 may
perform. After the W05-owned interface verifies evidence bound to the exact
output revision, a progress save may record the newly observed standing; the
save neither grants nor causes acceptance. Canonical promotion and GitHub
publication are separate, explicitly authorized operations.

### Work state

- `pending`: the step has not satisfied its declared outcome;
- `blocked`: the step cannot proceed and names the missing decision or evidence;
- `complete`: the step's output and every required evidence reference exist and
  match the revisions recorded by the step.

Interruption is not a fourth outcome. An interrupted in-flight operation remains
`pending` (or becomes `blocked` when a prerequisite is known to be absent), with
a sanitized observation explaining the safe resume point.

## Minimal record shape

The following is illustrative vocabulary, not an approved serialization schema:

```yaml
record_version: proposed-w08-v1
record_id: <stable study-local identifier>
study_ref: <opaque study identity>
objective: <bounded objective>
scope:
  included: [<bounded category>]
  excluded: [<bounded category>]
baseline_id: <digest of the last successfully loaded record, or genesis>
materials:
  - ref: <opaque W03-owned source/capture reference>
    revision: <opaque W03-owned revision>
    observation: captured | partially-read | read | partially-analyzed
    analyzed_scope: <bounded description or none>
    remainder: <bounded description or none>
outputs:
  - ref: <opaque W05-owned output reference>
    revision: <opaque output revision>
    standing: provisional | accepted
    acceptance_evidence_ref: <reference or none>
steps:
  - step_id: <stable identifier within this record>
    intent: <bounded action>
    input_revisions: [<reference plus revision>]
    state: pending | blocked | complete
    output_revisions: [<reference plus revision>]
    required_evidence: [<evidence kind plus reference and expected revision>]
    observed_evidence: [<reference plus observed revision and result>]
    blocker: <sanitized reason or none>
    next_step: <one bounded action or none>
    attempts: [<append-only prior observation with revisions, evidence and time>]
    current_resumability: ready | blocked | revalidation-required | none
checks:
  run: [<check identity, bounded target, result, evidence reference>]
  not_run: [<check identity and reason>]
publication:
  local_revision: <record revision>
  github_state: not-requested | pending | unknown | published | failed
  github_ref: <sanitized public reference or none>
retention:
  owner: <named owner>
  evidence_class: repository-tracked | externally-retained | runtime-ephemeral
  storage_reference: <sanitized relative or approved reference>
  retention_rule: <duration, expiry, deletion, or repository-history rule>
  access: <read/amend/dispose boundary>
  integrity: <digest or version mechanism>
  availability: verified | not-verified | unavailable
  disposal: <owner and rule>
assumptions: [<unaccepted dependency assumption>]
interface_questions: [<question for W03, W05, or W09>]
```

Fields holding references do not define the referenced object's syntax. A
consumer must preserve unknown reference values without interpreting them until
their owning contract is accepted. `analyzed_scope` and `remainder` are bounded
descriptions, not copied content or a claim registry.

## Save, load, check, and continue

1. **Load.** Read one explicitly selected record and its integrity identifier.
   Validate the proposed record version and internal uniqueness of `step_id`.
   Resolve only the artifact references needed for the next bounded step. Do not
   discover chat sessions, scan broad runtime directories, or infer progress.
2. **Check.** Compare every needed material/output/evidence revision through its
   owning interface. A missing artifact, unavailable comparison, changed
   revision, or mismatched evidence fails closed for each affected step. Preserve
   unaffected history and every prior attempt. Derive current resumability as
   `blocked` or `revalidation-required` without rewriting a historical
   `complete` attempt, and state what must be re-read, re-analyzed, or decided.
   Never silently replay a stale conclusion.
3. **Continue.** Choose one declared `next_step` whose inputs still match. A new
   agent needs the record and referenced retained artifacts, not the prior chat.
   Current authorization must be checked separately before any write or
   publication.
4. **Save.** Build a complete candidate in a new local temporary artifact,
   validate it, and replace the owned record atomically only if its
   `baseline_id` still equals the loaded revision. Compute the result identity
   over the exact UTF-8 payload bytes between the envelope boundaries, excluding
   the envelope's `result_id` field itself; store that digest in the envelope and
   use it as the next save's baseline. Failure before replacement leaves the
   prior record authoritative for the local workflow and reports the candidate
   as incomplete.
5. **Re-check.** Reload the saved bytes, recompute their identity, and check
   referenced revisions and completion predicates. Report unavailable checks as
   unavailable, not passing.

The operation must compare a caller-supplied baseline and must use one exclusive
writer (for example, a local owner-scoped lock plus atomic replacement). A second
writer with a stale baseline is rejected without overwrite and reloads before
retrying. This serializes one local record only; it makes no distributed-lock or
cross-system atomicity claim.

The identity boundary is byte-exact rather than a semantic reserialization. For
example, the synthetic payload consisting of the five UTF-8 bytes `demo\n` has
SHA-256 `eb9c26baee47f19e4993a77bca936d0ff09e355a82d3db79bf154ebff1a80604`.
An illustrative envelope may therefore carry that value as `result_id` outside
those five bytes. This example defines neither an accepted serialization nor a
dependency-owned reference format. As a negative control, hashing envelope bytes
that already contain `result_id` is invalid because it makes the identity
self-referential.

### Retry idempotency

`step_id` is stable across retries. A retry with the same step ID and identical
input/output revisions first revalidates current artifact and evidence
availability, revisions, and validity through their owning interfaces. Only if
those checks pass does it observe the existing step rather than appending
another completion; it does not automatically rerun the expensive work. An
unavailable, expired, revoked, superseded, or mismatched item makes current
resumability blocked or revalidation-required while preserving the old attempt.
The same ID with different intent or revisions is a conflict and must be
rejected or represented as an explicitly new step. External writes need their
own accepted idempotency rules; this record cannot supply them.

### Completion predicate

A current completion view may be `complete` only when, at check time:

1. all declared input and output references exist;
2. their observed revisions equal the recorded revisions;
3. every declared required check ran against those revisions and passed;
4. every required evidence reference exists and matches its expected revision;
5. the owning contract permits the claimed output standing; and
6. no unresolved blocker applies to the step.

A historical attempt may truthfully remain recorded as having completed against
its then-observed revisions and evidence. That history does not establish
current completion after drift, expiry, revocation, or loss of availability. A
study-level current completion view is derived only when all required steps
satisfy the predicate now. Text saying “done,” a saved summary, a successful
save, a local commit, or a GitHub URL is insufficient. If evidence is missing or
cannot be checked, current resumability is `blocked` or `revalidation-required`,
never implicit completion.

## Publication and accepted knowledge

Local save and GitHub publication are two operations with separate outcomes. A
successful local save records `github_state: not-requested` unless an explicitly
authorized publisher later updates it from separately checked evidence. An
publication with a lost acknowledgement preserves the local record but leaves
the remote outcome `unknown`; it proves neither failure nor absence of a remote
object. Before any retry, an authorized actor must reconcile the exact intended
remote object through a read-only operation. Only authoritative evidence may
then record `published` or `failed`; no retry is implicit. A published proposal
remains provisional unless the W05-owned acceptance evidence is independently
observed. Neither publication nor acceptance automatically promotes content to
the canonical KB or a rebuildable search index.

## Handoff without host assumptions

Before planned handoff, compaction, or shutdown, an agent should explicitly run
save and re-check, then provide the record reference and result identity. A host
may offer a lifecycle hook that invokes this operation, but correctness must not
depend on that hook: hooks can be absent, late, or interrupted. After an
unplanned interruption, the next process loads the last successfully replaced
record and checks referenced artifacts. Unsaved conversational context is
treated as unavailable rather than reconstructed or claimed.

## Privacy and retention

Retain only bounded summaries and sanitized references. Exclude raw prompts,
chat/full transcripts, credentials, tokens, personal or confidential payloads,
private hostnames, absolute paths, environment dumps, broad runtime directories,
and source excerpts. A path or digest can itself be sensitive and must remain
inside the approved access boundary.

Every persisted record uses the owner, class, storage, retention/expiry, access,
integrity/version, availability, and disposal vocabulary of
`docs/EVIDENCE_RETENTION.md`. Missing policy fields mean runtime-ephemeral or
durability unknown. Saving does not create a durable receipt; repository tracking
does not promise immutability or indefinite availability; cleanup/deletion needs
separate owner authorization. Search indexes remain rebuildable derivatives and
must not be used as the only progress record.

## Unaccepted assumptions and interface questions

The proposal intentionally records these dependencies instead of deciding them:

1. **W03 assumption:** it will provide opaque source/capture identity, immutable
   or comparable revision values, retained-availability observations, and a way
   to determine which progress is affected by revision change. Questions: Is
   sub-source scope addressable? How are unavailable and deleted revisions
   distinguished? What exact comparison result is safe to persist?
2. **W05 assumption:** it will distinguish provisional and accepted output and
   expose an acceptance-evidence reference bound to one output revision.
   Questions: Can acceptance be withdrawn/superseded? Which evidence and checks
   are required before an accepted standing can be observed?
3. **W09 assumption:** it will govern authority, publication permission, privacy,
   retention, and disposal at each storage boundary. Questions: Who may create,
   update, publish, supersede, and delete a handoff record? Which sanitized
   metadata may cross from local storage to GitHub?
4. **Completion interface:** which existing completion evidence applies to a
   research output before and after publication, and how is revision containment
   checked without equating publication with acceptance?
5. **Concurrency interface:** is a filesystem lock plus compare-and-replace an
   acceptable single-host one-writer boundary, or must the accepted contract use
   another owner-scoped primitive?

Until those questions are accepted, implementations and migrations are out of
scope and fixtures below are tests of design behavior only.
