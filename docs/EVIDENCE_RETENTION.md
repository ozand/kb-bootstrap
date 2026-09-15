# Durable and ephemeral evidence

This guide defines generic evidence and retention terminology for repository and batch workflows. It does not define a manifest schema, receipt store, audit database, retention service, or consumer-specific pipeline.

## Terms

| Term | Meaning | Does not prove |
|---|---|---|
| **Durable evidence** | A bounded, sanitized record intentionally retained by a named owner in a defined storage class for a stated period or deletion rule, and independently available after the producing process ends. | That the record is immutable, complete, truthful, authorized, or available forever. |
| **Ephemeral evidence** | Transient output used for live execution, diagnosis, supervision, or handoff and lacking an explicit durable retention decision. | Post-run availability, audit retention, immutability, or independent verification. |
| **Retention policy** | An explicit owner, storage class/location, retention duration or deletion/expiry rule, access scope, integrity/version rule, and disposal responsibility. | That every stored payload is safe or that retention itself establishes correctness. |
| **Durable receipt** | A small sanitized summary intentionally retained under an explicit policy, identifying a bounded operation/result and the evidence scope, verification status, and limitations. | That every underlying step succeeded or that referenced evidence is accessible and valid without separate verification. |

A file is not durable merely because it currently exists. A receipt is not durable merely because it has a structured format. Durability requires an explicit retention decision and a post-run availability boundary.

## Evidence classes

### Repository-tracked evidence

Sanitized evidence committed and versioned in the repository that owns the workflow, such as a bounded review note, manifest, test summary, or delivery receipt.

Repository tracking can provide version history and commit identity. It does not by itself guarantee indefinite retention, write-once storage, deletion resistance, branch protection, independent availability, or tamper resistance. State the repository owner, retained path/category, governing retention/history policy, and integrity reference.

### Externally retained evidence

A sanitized record stored in an explicitly approved external system with a named owner, access boundary, retention/expiry rule, and integrity or version mechanism.

An external URL, object ID, or record reference proves only that a pointer was reported. Availability, access, integrity, and retention remain `NOT VERIFIED` until independently observed at the claimed layer.

### Runtime and ephemeral state

Examples include:

- `.pi/` state and Pi session artifacts;
- Herdr panes, buffers, and transcripts;
- stdout and stderr;
- caches, checkpoints, temporary files, local build outputs, and unretained run logs.

These artifacts may be valuable operational state and must not be deleted casually. They are not a repository audit database and are not durable evidence by default. They may rotate, be truncated, become inaccessible, or disappear when a process, session, worktree, or host is removed.

Never copy runtime state wholesale into a repository or receipt. It can contain credentials, private payloads, prompts, personal data, absolute paths, host details, or unrelated session content.

## Durability and immutability are separate claims

A durable record may still be corrected, superseded, deleted under policy, or changed by an authorized owner.

Calling an artifact an **immutable audit record** requires all of the following:

1. an explicit durable retention policy;
2. an explicit durable-receipt policy that states what bounded receipt is retained, where, by whom, for how long, and how its post-run availability is verified; and
3. a stated write-once, append-only, versioned-history, or tamper-evidence mechanism with a verification procedure and named owner.

If those properties are not defined, call the artifact a manifest, execution record, transient summary, or durable receipt according to what is actually established. A Git commit provides a versioned tree identity; it is not automatically a permanent, protected, signed, independently retained, or legally authoritative audit record.

## Retention decision checklist

Before claiming durable evidence, record:

- **Owner:** repository, team, or approved evidence system responsible for the record.
- **Evidence class:** repository-tracked, externally retained, or runtime-ephemeral.
- **Storage reference:** sanitized relative repository path/category or approved external reference; never a private absolute path or token-bearing URL.
- **Retention:** duration, expiry, deletion rule, or repository-history policy.
- **Access:** who may read, amend, supersede, or dispose of it.
- **Integrity/version:** commit ID, content digest, append-only version, or other bounded verification mechanism.
- **Availability check:** `VERIFIED`, `NOT VERIFIED`, or `UNAVAILABLE`, with the observation date when relevant.
- **Scope and limitations:** exactly which operation/result is covered and which stronger claims are not supported.
- **Disposal:** owner and rule for deletion, expiration, supersession, or legal hold where applicable.

If the retention fields are absent or ambiguous, classify the evidence as ephemeral or durability unknown. Do not upgrade the claim because the workflow calls the artifact a manifest or receipt.

## Durable receipt guidance

A durable receipt should contain only the minimum sanitized evidence needed to identify and review the bounded result:

```yaml
# Illustrative vocabulary, not a kb-bootstrap schema or command contract.
receipt_status: durable | ephemeral | unknown
operation: <bounded public operation category>
result: pass | fail | blocked | incomplete
owner: <repository or approved team/system>
evidence_class: repository-tracked | externally-retained | runtime-ephemeral
retention_reference: <sanitized policy/reference or none>
integrity_reference: <public commit or content digest, when applicable>
availability: verified | not-verified | unavailable
scope: <short bounded claim>
limitations: <short sanitized non-claim>
```

Do not include credentials, cookies, private payloads, personal data, private hostnames, token-bearing URLs, absolute local paths, raw transcripts, prompts, environment dumps, runtime checkpoints, or unrelated object listings.

A durable receipt reports evidence; it does not authorize a retry, mutation, deletion, deployment, or promotion. Historical approval or a prior receipt does not replace current authorization.

## Generic workflow

1. Produce the operational output needed for the run.
2. Sanitize the bounded result; do not copy the full runtime transcript.
3. Classify the evidence as repository-tracked, externally retained, or runtime-ephemeral.
4. Decide the owner, retention, access, integrity/version, availability, and disposal policy.
5. Retain only the approved evidence or durable receipt.
6. Verify the retained record at the claimed storage/availability layer.
7. Report the durable and ephemeral portions separately, including `NOT VERIFIED` or `UNKNOWN` where evidence is missing.

## Generic examples

### Repository-tracked

```text
Evidence class: repository-tracked
Owner: <owning repository>
Record: <sanitized relative report category>
Retention: <repository history or documented expiry rule>
Integrity: <public commit ID>
Availability: VERIFIED | NOT VERIFIED
Limitations: <bounded non-claim>
```

### Externally retained

```text
Evidence class: externally retained
Owner: <approved evidence system/team>
Reference: <sanitized record reference>
Retention: <named policy or expiry>
Access/integrity: VERIFIED | NOT VERIFIED
Limitations: <bounded non-claim>
```

### Ephemeral runtime evidence

```text
Evidence class: runtime-ephemeral
Source: <tool output/session/cache category>
Retention policy: none specified
Durable receipt: none
Audit status: NOT DURABLE / NOT VERIFIED
```

## Non-claims and failure handling

- `.pi/`, Herdr transcripts, caches, temporary files, stdout, stderr, and checkpoints are not a repository audit database.
- `RESULT: OK` is execution output, not retention proof.
- A Git-tracked record is versioned repository evidence, not an automatic immutability or indefinite-retention guarantee.
- An external reference is not verified durable evidence until its access, integrity, owner, and retention are observed.
- A durable receipt does not prove every underlying step or semantic claim.
- Missing retention or availability evidence must be reported as ephemeral, unknown, `NOT VERIFIED`, or `UNAVAILABLE`, not success.
- Do not delete or clean runtime state merely because it is classified as ephemeral; preservation and cleanup are separate owner-authorized operations.
- This guidance does not prescribe consumer-specific schemas, outcome vocabularies, batch sizes, source limits, ID formats, agent topology, or pipeline implementation.
- This guidance does not implement retention automation, a manifest generator, receipt store, audit database, migration, deletion, or cleanup.

If a future change adds a persisted receipt schema, retention system, immutable storage guarantee, or trust/access boundary, it requires a separately governed architecture decision before implementation.

## Related guidance

Validation-result independence is documented separately in [Validation Composition](VALIDATION_COMPOSITION.md). Passing a validation gate and retaining its evidence are different claims.
