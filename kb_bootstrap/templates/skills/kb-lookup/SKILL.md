---
name: kb-lookup
description: Look up an error fix using deterministic project-local-first precedence and an optional explicitly configured read-only shared store. Use whenever a command fails or behavior is unexpected before retrying.
---

# kb-lookup — search for an error fix

Use this skill immediately after an error and before guessing or retrying. Follow the [lesson ownership and routing policy](https://github.com/ozand/kb-bootstrap/blob/main/docs/LESSON_ROUTING_POLICY.md); that document is the normative ownership and routing policy. This skill provides lookup-specific operational checks and never creates another store.

## Repository governance gate

Lookup is read-only, but any follow-up edit, capture, Issue mutation, commit, or pull request must first:

1. distinguish the consumer repository from an upstream/shared repository;
2. name the target explicitly as `owner/repository`;
3. run `kb-bootstrap doctor --repo <owner/repository>` and fail closed unless it returns `RESULT: OK`;
4. use a separate verified checkout/worktree for upstream changes.

Before claiming a follow-up complete, require `kb-bootstrap check-completion --repo <owner/repository> --commit <commit> [--pr <number>]`. Do not expose private paths, credentials, payloads, or runtime state in the result.

## Store configuration

Read `lesson-stores.json` at the repository root when it exists. Do not discover lesson stores
from absolute paths, sibling directories, Git remotes, or machine-specific state.

If the file is absent, report `RESULT: BLOCKED (no lesson stores configured)` and stop lookup without exposing paths. This generated skill does not imply that a local lesson store exists.

Supported entries are:

```json
{
  "version": 1,
  "capture_store": "local",
  "local": {"path": "kb/lessons"},
  "shared": {"path": "an-explicitly-configured-path", "read_only": true}
}
```

The `shared` entry is optional and must be explicitly configured. It is lookup-only.

## Lookup order

Use lookup for a current error or unexpected behavior to find an applicable,
previously recorded fix; do not apply a lesson whose symptom or context does not
match the current problem.

Use `kb-bootstrap search-lessons` for Markdown stores; `lesson-lookup` remains an
explicit JSON export-bundle command and does not search configured directories.

1. Search one explicitly configured store at a time, local first, using its
   `index.yaml` first: `kb-bootstrap search-lessons "<query>" --project-root . --store local`.
2. A local match ends lookup. Search explicitly configured shared only after a
   successful search with a complete `COMPLETE` result and no matches (a
   no-match result, not an operational error):
   `kb-bootstrap search-lessons "<query>" --project-root . --store shared`.
   Shared search requires `read_only: true`.
3. `PARTIAL`, `UNAVAILABLE`, or blocked local outcomes due to a local lookup error
   do not establish no-match; report them distinctly and never fall back to shared.
   Shared unavailable/partial likewise is not a complete no-match.
4. If local is not configured, shared-only routing is permitted only when its path
   is explicitly configured and read-only. Do not discover another store.
5. For a match, use its store-relative path and ID to inspect the lesson; results
   contain a bounded body excerpt and never expose frontmatter.
6. For an applicable match, read the lesson and apply its `## Resolution` and
   `## Prevention` sections.

Report provenance as `local` or `shared` plus the lesson ID. Do not expose private
absolute paths or lesson payloads in receipts. Lookup never writes, synchronizes,
promotes, or publishes lessons.
