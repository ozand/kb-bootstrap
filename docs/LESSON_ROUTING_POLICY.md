# Lesson ownership and routing policy

This policy defines where knowledge belongs and how lesson capture and lookup select stores. It applies to generated `kb-capture` and `kb-lookup` skills and to operators using the same `lesson-stores.json` contract.

## Ownership categories

### Canonical project knowledge

Reviewed documentation under the owning repository's normal knowledge tree (`kb/` excluding `kb/raw/` and `kb/lessons/`). It explains the project or system and is searched through the canonical `<project>-wiki` collection. It is not an error-lesson capture destination.

### Project-scoped lessons

Recurring or non-obvious fixes that apply to one repository. The repository owns the lesson files, schema, index, Issues, commits, and review history. Local capture is available only when `lesson-stores.json` selects a complete project-local store containing its directory, `SCHEMA.md`, and `index.yaml`.

### Workspace-global lessons

Sanitized lessons intended for reuse across multiple repositories. This is an external store owned and governed outside the generated project. A project may use it only when it is explicitly configured. Generated project lookup treats it as read-only; generated capture never silently writes to it.

## Capture routing

Every capture operation must resolve exactly one explicit destination before writing.

1. Read `lesson-stores.json` from the repository root.
2. Read `capture_store` and resolve exactly one store with that name.
3. Confirm the selected store's required contract and contribution workflow are available.
4. Write only to that selected store.

Block without writing when configuration is missing, names an unavailable store, selects more than one destination, conflicts with repository ownership, or requires an unavailable external contribution workflow. Report only a sanitized category and result; do not print credentials, private paths, lesson payloads, or runtime state.

Automatic dual writes, mirroring, synchronization, and promotion are prohibited. Moving a lesson between project and workspace scope is a separate reviewed operation, not part of capture.

## Lookup routing

Lookup is read-only and deterministic:

1. Search a complete explicitly configured local store first.
2. If there is no local match, search an explicitly configured shared store only when it is marked read-only.
3. If a configured source is unavailable, report the source category as unavailable without exposing its path.
4. If configuration is missing, conflicting, or ambiguous, block rather than infer another store.

Lookup never creates stores, changes capture ownership, writes lessons, promotes matches, or performs background discovery.

## Deterministic examples

### Local-only

```json
{
  "version": 1,
  "capture_store": "local",
  "local": {"path": "kb/lessons"}
}
```

- Capture destination: `local`, after validating its directory, schema, and index.
- Lookup order: `local` only.
- Sanitized result identifies the source as `local`; it does not disclose the resolved path.

### Shared-only lookup

```json
{
  "version": 1,
  "shared": {"path": "explicitly-configured-store", "read_only": true}
}
```

- Capture: blocked because no `capture_store` is selected.
- Lookup order: `shared` only.
- The project does not create, discover, or write to the external store.

### Local-first with shared fallback

```json
{
  "version": 1,
  "capture_store": "local",
  "local": {"path": "kb/lessons"},
  "shared": {"path": "explicitly-configured-store", "read_only": true}
}
```

- Capture destination: `local` only.
- Lookup order: `local`, then `shared` when there is no local match.
- No operation writes to both stores.

### Ambiguous or conflicting

Examples include a missing `capture_store`, an unknown selected store, multiple selected destinations, a writable shared lookup store, or ownership that cannot be verified.

- Capture result: blocked without writing.
- Lookup result: blocked when deterministic read order cannot be established.
- Receipt: sanitized reason category only; no private path or payload.

## Relationship to generated skills

- `kb-capture` implements the single-destination capture rules and is generated only with the opt-in project-local lesson contract.
- `kb-lookup` implements read-only local-first/shared-second lookup and blocks when no deterministic store configuration exists.

The skills retain operational checks specific to their capability. This document is the normative ownership and routing policy. Manual promotion and demotion between scopes are defined separately and always require explicit review; they are never inferred from lookup or capture.
