---
name: kb-capture
description: Record a recurring or non-obvious error lesson in exactly one explicitly configured lesson store. Use after resolving an error that was not already documented and is likely to recur.
---

# kb-capture — record an error lesson

Use this skill after resolving a recurring or non-obvious error. Follow the [lesson ownership and routing policy](https://github.com/ozand/kb-bootstrap/blob/main/docs/LESSON_ROUTING_POLICY.md); that document is the normative ownership and routing policy. This skill provides capture-specific operational checks and does not add another destination.

## Repository governance gate

Before writing a lesson:

1. Classify the destination as consumer-owned project knowledge or an explicitly configured upstream/shared contribution.
2. Resolve one explicit repository target in `owner/repository` form. Do not infer it from a remote name or machine path.
3. Run `kb-bootstrap doctor --repo <owner/repository>` and stop if it does not return `RESULT: OK`.
4. For upstream/shared work, use a separate verified checkout or worktree; never write from the consumer branch by convenience.

After committing or opening a pull request, run `kb-bootstrap check-completion --repo <owner/repository> --commit <commit> [--pr <number>]` before claiming Issue completion. Stop on missing or mismatched evidence. Receipts may contain only sanitized repository, branch, commit, public URL, and test results.

## Lesson-store preflight

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

Local capture is supported only when all three contract items exist:

- configured `local.path` directory;
- `<local.path>/SCHEMA.md`;
- `<local.path>/index.yaml`.

If any item is absent, stop with `RESULT: BLOCKED (local lesson contract unavailable)` without printing the resolved path or writing any file.

1. Read the configured local store's `SCHEMA.md` and `index.yaml`.
2. Search and compare existing lessons for equivalent symptoms, causes, and
   resolutions before drafting. If an equivalent lesson already covers the fix,
   do not create a duplicate; report the existing lesson ID.
3. Ground the draft in the available error and resolution evidence. Record the
   relevant evidence in the lesson body when useful; the existing schema does not
   require new evidence metadata. If evidence is missing, contradictory, or cannot
   be checked, stop without writing rather than inventing details.
4. Allocate the next unused repository-local ID using the configured `id_prefix`.
5. Create a draft at the configured local store path with matching frontmatter.
6. Add one matching entry to that store's `index.yaml`.
7. Validate that the filename ID, frontmatter ID, and index ID are identical and
   unique before reporting success. If any required check fails, stop and do not
   report a successful capture.

Capture only sanitized error signatures. Do not record credentials, private
payloads, runtime state, or unstable temporary values. These checks guide the
agent's pre-write comparison and validation; they do not add schema fields or
replace the repository's existing validator.
