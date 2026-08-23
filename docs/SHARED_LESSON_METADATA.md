# Shared lesson metadata, applicability, and provenance

This document defines the universal machine-validatable metadata contract for project-scoped and shared lessons created or consumed by `kb-bootstrap`. It does not require a particular registry repository or path and never changes existing lesson payloads automatically.

## Fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `scope` | string enum | Yes for new/updated lessons | Ownership scope: `workspace` or `project` |
| `applies_to` | array of repository IDs | Conditional | Repositories where the lesson is applicable; required and non-empty for `project`, optional for `workspace` |
| `source_repository` | repository ID | Yes | Repository where the underlying problem was first documented or reviewed |
| `observed_in` | array of repository IDs | Yes | One or more repositories where the problem was actually observed |
| `promoted_from` | lesson reference or `null` | No | Source project lesson when a reviewed promotion created this workspace lesson |

A repository ID is a public or sanitized `owner/repository` string. Machine-specific paths, remote URLs, credentials, private payloads, and runtime/session identifiers are not repository IDs.

A lesson reference is:

```yaml
promoted_from:
  repository: example/application
  lesson_id: PROJECT-0042
```

## Scope semantics

### `scope: workspace`

The lesson is owned by the workspace-global registry and may be considered for multiple repositories.

- `applies_to` may be omitted when broadly applicable.
- If `applies_to` is present, it is an explicit allowlist, not discovery evidence.
- `source_repository` identifies provenance; it does not transfer ownership back to that repository.
- `promoted_from` is present only after a separately reviewed/manual promotion.

### `scope: project`

The lesson is owned by one or more explicitly named project repositories rather than by the workspace-global registry.

- `applies_to` is required and must contain at least one repository ID.
- A project-scoped lesson must not be treated as globally applicable.
- In this shared registry, project scope is normally used for reviewed references or migration staging, not hidden local capture.

Any other scope value is invalid. Missing scope is tolerated only for unchanged legacy lessons; new or updated lessons must provide it. Consumers must not infer scope from a filesystem path or repository location.

## Provenance semantics

- `source_repository` answers where the lesson originated.
- `observed_in` records verified observations and must not be populated from guesses or broad repository discovery.
- `promoted_from` records one reviewed project lesson that produced a workspace lesson. It does not authorize synchronization, deletion, or future writes.
- Repeating a repository in `observed_in` is invalid.
- Every `applies_to` and `observed_in` entry must match `owner/repository` syntax and contain no URL, path separator other than `/`, credentials, or local drive prefix.

## Sanitized examples

### Workspace-global lesson

```yaml
scope: workspace
source_repository: example/tooling
observed_in:
  - example/tooling
  - example/application
promoted_from:
  repository: example/application
  lesson_id: PROJECT-0042
```

This lesson is workspace-owned. Promotion was reviewed manually; no automatic synchronization or dual write is implied.

### Project-scoped lesson

```yaml
scope: project
applies_to:
  - example/application
source_repository: example/application
observed_in:
  - example/application
promoted_from: null
```

This lesson is applicable only to the named project and must not be returned as globally applicable.

## Invalid examples

These must fail validation:

```yaml
scope: global            # invalid enum; use workspace
source_repository: C:/private/project
observed_in: []          # must contain at least one verified repository
```

```yaml
scope: project
applies_to: []           # project scope requires at least one repository
source_repository: https://token@example.invalid/repository
observed_in:
  - example/application
```

```yaml
scope: workspace
source_repository: example/tooling
observed_in:
  - example/tooling
  - example/tooling       # duplicate observation
promoted_from:
  repository: example/application
  lesson_id: ""           # incomplete reference
```

## Backward compatibility

Existing lessons without these fields remain readable until deliberately updated. Validation should report them as legacy metadata rather than inventing values. Any newly created or modified shared lesson must satisfy the full contract. Bulk migration requires a separate reviewed change and is not authorized by this document.

## Consumer integration

Any generated or existing repository may consume this contract through explicitly configured local or shared stores. `kb-bootstrap` must not infer registry paths, infer applicability, reserve shared IDs, or write to an external store automatically. Candidate preparation, ID allocation, promotion, and publication remain separate bounded or human-reviewed workflows.
