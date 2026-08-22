---
name: kb-lookup
description: Look up an error fix using deterministic project-local-first precedence and an optional explicitly configured read-only shared store. Use whenever a command fails or behavior is unexpected before retrying.
---

# kb-lookup — search for an error fix

Use this skill immediately after an error and before guessing or retrying.

## Store configuration

Read `lesson-stores.json` at the repository root. Do not discover lesson stores
from absolute paths, sibling directories, Git remotes, or machine-specific state.

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

1. If `local` is configured and available, search its `index.yaml` first.
2. If there is no local match and `shared` is explicitly configured as read-only,
   search its `index.yaml` second.
3. If the shared store is missing or unavailable, report that sanitized source as
   unavailable and finish the local result; do not perform hidden discovery or write.
4. If configuration is malformed or ambiguous, stop and report a blocking,
   sanitized configuration error.
5. For a match, read the referenced lesson and apply its `## Resolution` and
   `## Prevention` sections.

Report provenance as `local` or `shared` plus the lesson ID. Do not expose private
absolute paths or lesson payloads in receipts. Lookup never writes, synchronizes,
promotes, or publishes lessons.
