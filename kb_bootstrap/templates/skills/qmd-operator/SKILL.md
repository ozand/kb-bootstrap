---
name: qmd-operator
description: Manage local QMD semantic search, index collections, and execute semantic queries over raw documentation and system knowledge. Use when you need to search product documentation, update the semantic index after fetching new docs, or configure QMD collections.
---

# qmd-operator

Manage the local QMD (Semantic Search) workspace. This skill allows agents to configure QMD collections, update the vector index, and query the documentation.

## When to use

- You need to search for facts in product documentation.
- You just downloaded raw release notes or docs into `kb/raw/` (or `kb/apps/<app>/raw/`) and need to update the QMD index.
- You need to create a new QMD collection.

## Commands

### 1. Update the Index
After adding new files to the knowledge base:
```bash
qmd update
```

List configured collections:
```bash
qmd collection list
```

### 2. Search and Query
Generated projects use two collections:

- `<project>-wiki` for canonical OKF knowledge; use this by default.
- `<project>-raw` for source captures; query it explicitly during research.

```bash
qmd search "<keywords>" -c <project>-wiki
qmd query "intent: <what you are looking for>\nlex: <keywords>" -c <project>-wiki
qmd search "<source keywords>" -c <project>-raw
```

### 3. Read a Document
If QMD returns a reference to a file (e.g., `qmd://my-app/raw/releases.md`), use the context-mode tools to read the actual file from the disk.

## Configuring a New Collection
To define what files belong to a specific context, create a YAML file in `qmd/collections/<name>.yaml`. Keep canonical and raw paths separate; do not point both collections at the same mixed corpus.

## Completion gate

Before reporting knowledge-base work complete:

1. Run `kb-bootstrap validate --dir kb --project-root .`.
2. Run the project test command.
3. Run `qmd update`, then smoke-test `qmd search` against both `<project>-wiki` and `<project>-raw`.

Do not claim QMD indexing success when QMD is unavailable or a smoke query was not run.
