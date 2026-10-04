# W08 synthetic interruption examples

Status: **Proposed fixtures only**. All names, references, revisions, digests,
agents, and results below are invented. They do not identify consumer data,
actual source content, a live GitHub operation, or an accepted contract. Each
case applies the design in `docs/proposals/W08-portable-handoff.md`.

## Common synthetic study

```yaml
record_version: proposed-w08-v1
record_id: study-synthetic-river
study_ref: study:synthetic-river
objective: compare two invented public notices for a terminology proposal
scope:
  included: [notice headings, defined terms]
  excluded: [attachments, author identity, canonical publication]
retention:
  owner: synthetic-research-owner
  evidence_class: runtime-ephemeral
  storage_reference: local-owned-record/synthetic-river
  retention_rule: delete only after an owner-approved disposition decision
  access: owner can read/amend/dispose; continuation agent gets explicit read access
  integrity: sha256 of exact UTF-8 payload bytes excluding the result-id envelope
  availability: not-verified
  disposal: synthetic-research-owner under the stated rule
assumptions:
  - W03 source identity and revision comparison are not accepted
  - W05 output acceptance evidence is not accepted
  - W09 publication and retention permissions are not accepted
```

Every field and value in these fixtures is illustrative, not accepted. The
`source:*`, `capture:*`, `output:*`, and evidence strings are opaque placeholders;
they deliberately do not define or duplicate the dependency-owned schemas.

## Case 1 — resume after interruption with no chat history

**Baseline `R0`:** `genesis`. Agent A has retained two captures. It reads all of
the first and only section `heading` of the second, then is interrupted before
analysis or publication.

```yaml
baseline_id: genesis
result_id: R0
materials:
  - {ref: capture:amber, revision: rev-a1, observation: read,
     analyzed_scope: none, remainder: analysis not started}
  - {ref: capture:blue, revision: rev-b1, observation: partially-read,
     analyzed_scope: none,
     remainder: defined-terms section not read; analysis not started}
outputs: []
steps:
  - step_id: retain-inputs
    state: complete
    input_revisions: [source:amber@rev-a1, source:blue@rev-b1]
    output_revisions: [capture:amber@rev-a1, capture:blue@rev-b1]
    required_evidence: [retained-artifacts@set-1]
    observed_evidence: [retained-artifacts@set-1:pass]
    next_step: read the defined-terms section of capture:blue@rev-b1
  - step_id: compare-terms
    state: pending
    input_revisions: [capture:amber@rev-a1, capture:blue@rev-b1]
    output_revisions: []
    required_evidence: [comparison-check@not-yet-created]
    observed_evidence: []
    blocker: none
    next_step: read the defined-terms section of capture:blue@rev-b1
checks:
  run: [record-shape:R0:pass, retained-artifacts:set-1:pass]
  not_run: [comparison-check:not analyzed, publication-check:not requested]
publication: {local_revision: R0, github_state: not-requested, github_ref: none}
```

**Continuation:** Agent B receives only `R0` and explicit access to the two
retained captures. It reloads `R0`, observes both revisions still match, reads
the named remainder, performs the comparison, and saves `R1` using `R0` as the
compare-and-replace baseline. It does not refetch either source and does not need
Agent A's chat.

```yaml
baseline_id: R0
result_id: R1
materials:
  - {ref: capture:amber, revision: rev-a1, observation: read,
     analyzed_scope: headings and defined terms, remainder: none}
  - {ref: capture:blue, revision: rev-b1, observation: read,
     analyzed_scope: headings and defined terms, remainder: none}
outputs:
  - {ref: output:term-note, revision: out-1, standing: provisional,
     acceptance_evidence_ref: none}
steps:
  - {step_id: retain-inputs, state: complete,
     input_revisions: [source:amber@rev-a1, source:blue@rev-b1],
     output_revisions: [capture:amber@rev-a1, capture:blue@rev-b1],
     required_evidence: [retained-artifacts@set-1],
     observed_evidence: [retained-artifacts@set-1:pass], next_step: none}
  - {step_id: compare-terms, state: complete,
     input_revisions: [capture:amber@rev-a1, capture:blue@rev-b1],
     output_revisions: [output:term-note@out-1],
     required_evidence: [comparison-check@cmp-1],
     observed_evidence: [comparison-check@cmp-1:pass], next_step: none}
checks:
  run: [record-shape:R1:pass, revision-match:set-1:pass,
        comparison-check:cmp-1:pass]
  not_run: [acceptance-check:no W05 evidence, publication-check:not requested]
publication: {local_revision: R1, github_state: not-requested, github_ref: none}
```

Expected: continuation succeeds; the output remains provisional and the study is
not declared accepted, published, or canonical.

## Case 2 — source revision changed after completed analysis (negative)

Start from `R1`, but the W03-owned comparison reports `capture:blue@rev-b2`
instead of recorded `rev-b1`.

```yaml
baseline_id: R1
result_id: R2-drift
observed_change: capture:blue expected rev-b1, observed rev-b2
affected_steps:
  - step_id: compare-terms
    attempts:
      - {attempt: cmp-attempt-1, historical_state: complete,
         input_revisions: [capture:amber@rev-a1, capture:blue@rev-b1],
         output_revisions: [output:term-note@out-1],
         observed_evidence: [comparison-check@cmp-1:pass]}
    current_resumability: blocked
    blocker: recorded input revision does not match retained input
    next_step: obtain permission and re-read the bounded material at rev-b2
preserved_history: retain-inputs and cmp-attempt-1 remain historical observations
checks:
  run: [record-shape:R1:pass, revision-match:capture-blue:fail]
  not_run: [comparison-check:stale input, publication-check:blocked]
publication: {local_revision: R2-drift, github_state: not-requested, github_ref: none}
```

Expected: no stale analysis is replayed, no output is accepted or published, and
the changed material returns to bounded re-read/re-analysis. The record does not
guess whether `rev-b2` is equivalent.

## Case 3 — matching output but expired completion evidence (negative)

The provisional bytes `output:term-note@out-1` exist, but `comparison-check@cmp-1`
has expired and is unavailable after interruption.

```yaml
baseline_id: R1
result_id: R3-missing-evidence
step_id: compare-terms
attempts:
  - {attempt: cmp-attempt-1, historical_state: complete,
     output_revisions: [output:term-note@out-1],
     observed_evidence: [comparison-check@cmp-1:pass]}
current_resumability: blocked
current_required_evidence: [comparison-check@cmp-1]
blocker: required evidence is unavailable
checks:
  run: [output-revision:out-1:pass, evidence-availability:cmp-1:fail]
  not_run: [acceptance-check:no evidence, publication-check:not requested]
```

Expected: saved text and a matching output revision do not imply current
completion. The historical attempt is not erased. The next process may rerun
the bounded check only with current authorization.

## Case 4 — repeated completed step is idempotent

Agent B retries `compare-terms` after `R1` because it did not receive the save
acknowledgement.

```yaml
baseline_id: R1
result_id: R1
retry:
  step_id: compare-terms
  input_revisions: [capture:amber@rev-a1, capture:blue@rev-b1]
  output_revisions: [output:term-note@out-1]
decision: existing identical completed step observed; no append and no rewrite
checks:
  run: [step-identity:pass, input-output-revisions:pass,
        evidence-availability:cmp-1:pass, evidence-revision:cmp-1:pass,
        evidence-validity:cmp-1:pass]
  not_run: [comparison-work:not rerun after current evidence revalidation,
            publication-check:not requested]
```

Expected: the result stays byte-identical `R1`. If evidence is unavailable,
expired, revoked, superseded, or revision-mismatched, the old attempt remains in
history but is not currently reusable; the retry does not automatically rerun
the comparison. Reusing `compare-terms` with `out-2`, different inputs, or
different intent is a conflict, not an update.

## Case 5 — two agents contend for one record

Agents C and D both load `R1`. C acquires the owner-scoped writer boundary and
saves a bounded question update as `R4`. D then attempts compare-and-replace with
baseline `R1`.

```yaml
writer_c: {baseline_id: R1, save_result: success, result_id: R4}
writer_d: {baseline_id: R1, save_result: rejected-stale-baseline,
           observed_current_id: R4, result_id: none}
record_after_attempts: R4
next_step_for_d: reload R4, reconcile explicitly, and request a new write
```

Expected: D cannot overwrite C and no merged/distributed transaction is claimed.
If the exclusive writer primitive is unavailable, both writers stop without a
write; they do not use last-writer-wins.

## Case 6 — interruption during publication

An authorized coordinator begins publishing local `R1`, but interruption occurs
before independently observing a GitHub object containing `out-1`.

```yaml
baseline_id: R1
result_id: R5-publication-incomplete
publication:
  local_revision: R1
  github_state: unknown
  github_ref: none
owned_output: output:term-note@out-1 remains local and provisional
checks:
  run: [local-output-revision:out-1:pass]
  not_run: [github-containment-check:acknowledgement lost; outcome unknown,
            acceptance-check:no W05 evidence]
next_step: authorized coordinator reconciles the exact intended remote object read-only
```

Expected: local progress is preserved, but neither publication nor failure is
proven. An authorized read-only reconciliation must precede a separately
authorized retry, preventing an avoidable duplicate. There is no implicit retry,
acceptance, canonical promotion, index update, or completion claim.

## Case 7 — accepted-standing claim does not match evidence (negative)

A candidate save changes `standing` to `accepted`, but its evidence reference is
missing and no W05-owned check can bind acceptance to `out-1`.

```yaml
baseline_id: R1
result_id: none
candidate_claim: output:term-note@out-1 standing accepted
save_result: rejected
reason: acceptance evidence absent or unavailable
preserved_record: R1 with standing provisional
```

Expected: save cannot manufacture acceptance. Publication, if separately proven,
would still not cure the missing acceptance evidence or promote canonical data.
If a later W05-owned check instead verifies acceptance evidence bound to `out-1`,
a save may record that external observation; the save does not grant acceptance.

## Fixture-wide privacy and retention assertions

- No fixture contains source bodies, real people, credentials, tokens, prompts,
  transcripts, absolute paths, private hosts, runtime directory copies, models,
  or consumer data.
- `runtime-ephemeral` plus `availability: not-verified` is not durable evidence.
  The explicit owner and disposal rule do not silently upgrade that class.
- A future durable classification requires all policy fields and an independent
  availability check at the claimed layer.
- No case deletes runtime state, writes a search index, publishes to GitHub,
  accepts W03/W05/W09, or authorizes another operation.
