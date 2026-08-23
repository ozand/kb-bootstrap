# Reviewed lesson promotion and demotion workflow

This document defines a manual, review-required transfer between project-scoped and workspace-global lesson ownership. It extends the [lesson ownership and routing policy](LESSON_ROUTING_POLICY.md).

Promotion and demotion are not capture or lookup operations. They never run automatically, never write to both scopes in one operation, and never synchronize stores in the background.

## Boundaries and prerequisites

Before starting:

1. Identify the source scope and destination scope explicitly.
2. Identify the repository or external store that owns each scope.
3. Confirm that one reviewed destination is writable through its normal governance workflow.
4. Preserve the source unchanged until destination verification and review are complete.
5. Stop if ownership, authorization, destination, or review responsibility is ambiguous.

This workflow is separate from the [consumer versus kb-bootstrap upstream contribution workflow](CONTRIBUTING_UPSTREAM.md). That workflow decides which code/documentation repository owns a framework change. This workflow decides whether one sanitized lesson belongs at project or workspace scope. Reliability prerequisites for generated KB structure, documentation, and retained raw directories are tracked by Issues #4, #6, and #22; this workflow does not replace them. Future Issue #29 may prepare a contribution candidate, but it must consume this manual review policy and cannot authorize or automate a destination write.

## Required sanitization review

A reviewer must inspect the candidate before approving any destination write. Remove or generalize:

- credentials, tokens, secrets, and authentication material;
- personally identifiable information;
- private hostnames, repository URLs, filesystem paths, and internal network details;
- runtime/session state, transient IDs, timestamps, and unstable temporary values;
- private payloads, logs, prompts, or data not required to explain the lesson;
- project-specific names when the destination scope is workspace-global.

Keep only the smallest reproducible problem signature, resolution, prevention guidance, applicability, and non-sensitive provenance.

## Review record

Record a sanitized decision before writing:

```yaml
operation: promote | demote
source_scope: project | workspace
source_lesson_id: PUBLIC-ID
source_repository: owner/repository | external-store-name
destination_scope: project | workspace
destination_owner: owner/repository | external-store-name
reviewer: public-handle-or-team
actor: public-handle-or-team
decision: approved | rejected
rationale: short sanitized reason
destination_lesson_id: PUBLIC-ID | pending
```

Do not include lesson payloads, credentials, private paths, runtime state, or private identities in the record.

## Promotion: project to workspace

Use promotion only when the resolution is reusable across more than one repository and can be stated without project-private context.

1. Select one project lesson as the source; leave it unchanged.
2. Prepare a sanitized workspace candidate outside the destination store.
3. Review applicability, metadata, redaction, duplication, and destination ownership.
4. Record explicit approval and the one selected workspace destination.
5. Write the approved candidate only to that destination using its normal contribution/review process.
6. Verify the destination lesson ID, index entry, and retrievability.
7. Record a sanitized receipt. The project source remains until a separate retention decision is reviewed.

A rejection or unresolved ambiguity produces no destination write.

### Sanitized promotion fixture

```yaml
operation: promote
source_scope: project
source_lesson_id: PROJECT-0042
source_repository: example/application
destination_scope: workspace
destination_owner: shared-lessons
reviewer: knowledge-reviewers
actor: contributor
decision: approved
rationale: resolution applies to multiple Python repositories after path redaction
destination_lesson_id: KB-0123
```

Expected result: one new reviewed workspace lesson; the project lesson is preserved; no automatic second write or deletion occurs.

## Demotion: workspace to project

Use demotion when a shared lesson is too narrow, obsolete globally, or valid only for one project. Demotion does not silently delete or rewrite the shared source.

1. Select one workspace lesson as the source; leave it unchanged.
2. Prepare a project-scoped candidate with only the context needed by the target repository.
3. Review target ownership, applicability, sanitization, and the reason global scope is no longer appropriate.
4. Record explicit approval and the one selected project destination.
5. Write the approved candidate only to that project through its normal repository review process.
6. Verify its local ID, index entry, and lookup result.
7. Open a separate reviewed retraction/deprecation decision for the workspace source if needed. Until that decision completes, preserve the source.
8. Record a sanitized receipt.

A demotion write and shared-source retraction are two separate reviewed operations; they are never one cross-store transaction.

### Sanitized demotion fixture

```yaml
operation: demote
source_scope: workspace
source_lesson_id: KB-0099
source_repository: shared-lessons
destination_scope: project
destination_owner: example/application
reviewer: knowledge-reviewers
actor: maintainer
decision: approved
rationale: workaround depends on one application version and is not globally applicable
destination_lesson_id: PROJECT-0043
```

Expected result: one reviewed project lesson; the workspace source remains unchanged until a separate retraction/deprecation review.

## Blocking conditions

Stop without writing when:

- source or destination ownership cannot be verified;
- more than one destination is selected;
- approval is missing or the reviewer/actor is not identified;
- sanitization finds unresolved secrets, PII, private paths, payloads, or runtime state;
- the destination's normal contribution/review process is unavailable;
- the requested action requires automatic dual writes, synchronization, or a cross-repository transaction.

Report only the blocking category and sanitized ownership metadata.

## Destination verification and receipt

After an approved write, verify only the selected destination:

- destination owner and scope match the approval;
- destination lesson ID, frontmatter ID, and index ID agree;
- the lesson can be retrieved through the destination's normal lookup path;
- no unintended source mutation or second destination write occurred.

A minimal receipt contains:

```yaml
operation: promote | demote
source_scope: project | workspace
source_lesson_id: PUBLIC-ID
destination_scope: project | workspace
destination_owner: owner/repository | external-store-name
destination_lesson_id: PUBLIC-ID
reviewer: public-handle-or-team
actor: public-handle-or-team
result: verified | blocked
rationale: short sanitized reason
```

The receipt is evidence of a reviewed result, not authorization for future synchronization or promotion.
