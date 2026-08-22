---
name: kb-capture
description: Record a recurring or non-obvious error lesson in exactly one explicitly configured lesson store. Use after resolving an error that was not already documented and is likely to recur.
---

# kb-capture — record an error lesson

Use this skill after resolving a recurring or non-obvious error.

## Preflight

1. Find `lesson-stores.json` at the repository root.
2. Read `capture_store` and resolve exactly one configured store with that name.
3. Stop without writing when:
   - `lesson-stores.json` is absent;
   - `capture_store` is absent or names an unavailable store;
   - multiple destinations are selected or the configuration is ambiguous;
   - the selected store is shared and its explicit contribution workflow is unavailable.
4. Never infer a workspace path, discover a shared store in the background, or write
   to local and shared stores in one operation.

The generated project-local contract uses:

```json
{
  "version": 1,
  "capture_store": "local",
  "local": {"path": "kb/lessons"}
}
```

## Capture into the local store

1. Read `kb/lessons/SCHEMA.md` and `kb/lessons/index.yaml`.
2. Allocate the next unused repository-local ID using the configured `id_prefix`.
3. Create `kb/lessons/PROJECT-XXXX-<slug>.md` with matching frontmatter.
4. Add one matching entry to `kb/lessons/index.yaml`.
5. Validate that the filename ID, frontmatter ID, and index ID are identical and
   unique before reporting success.

Capture only sanitized error signatures. Do not record credentials, private
payloads, runtime state, or unstable temporary values.
