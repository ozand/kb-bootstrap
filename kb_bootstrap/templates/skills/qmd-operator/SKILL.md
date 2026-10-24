---
name: qmd-operator
description: Manage local QMD semantic search, index collections, and execute semantic queries over raw documentation and system knowledge. Use when you need to search product documentation, update the semantic index after fetching new docs, or configure QMD collections.
---

# qmd-operator

Manage the local QMD (Semantic Search) workspace. This skill allows agents to configure QMD collections, update the vector index, and query the documentation.

## Repository governance gate

Search and query operations are read-only. Before changing QMD configuration, knowledge files, Issues, branches, or pull requests:

1. distinguish consumer-owned work from reusable upstream `kb-bootstrap` work;
2. name the target as `owner/repository` and run `kb-bootstrap doctor --repo <owner/repository>`;
3. stop unless the doctor returns `RESULT: OK`;
4. perform upstream framework work only in a separate verified checkout/worktree.

Before reporting a committed change complete, run `kb-bootstrap check-completion --repo <owner/repository> --commit <commit> [--pr <number>]`. Use sanitized repository, branch, commit, public URL, and verification results only.

## When to use

- You need to search for facts in product documentation.
- An operator has explicitly selected QMD retrieval and designated its intended
  collection and index.
- You need to perform separately authorized QMD collection maintenance.

QMD is optional. Do not update or register collections merely because files changed
or because a search was requested. Maintenance is a deliberate operation against
an explicitly selected intended QMD state; do not assume a globally selected index
is appropriate or available.

## Commands

### 1. Optional collection registration (explicit setup only)

`qmd/collections/*.yaml` is this project's declaration; QMD does not read it.
QMD searches only collections registered in its own registry. Register a collection
only as part of separately authorized setup in the explicitly intended QMD state;
registration may index files and is a mutation, not a search prerequisite to perform
automatically.

```bash
qmd collection add kb --name <project>-wiki --mask "**/*.md"
qmd collection add kb/raw --name <project>-raw --mask "**/*.md"
```

Until registration, QMD search can report `Collection not found`; do not respond
by silently registering or switching to ambient state. Legacy `kb-bootstrap search`
does not pass `--index`; the bounded `search-qmd` command requires its explicit
index and pre-provisioned state as described below.

### 2. Optional index maintenance (separate explicit operation)

QMD maintenance is not part of ordinary file changes or search. If the owner has
explicitly selected QMD maintenance, use the intended QMD state and follow the
operator's supported scope controls. `qmd update` may update more than one
collection in the selected index; it is not a collection selector. Do not invent a
collection flag or assume this command is scoped to one collection.

List configured collections only when needed for the explicitly selected
maintenance or troubleshooting operation:

```bash
qmd collection list
```

### 3. Search and Query

Generated projects declare two collections:

- `<project>-wiki` for canonical OKF knowledge; use this by default when QMD is
  explicitly selected. It excludes `kb/raw/` and `kb/research/`.
- `<project>-raw` for source captures under both `kb/raw/` and `kb/research/`; query it explicitly during research.

Legacy `kb-bootstrap search` and QMD `qmd search` retain their existing behavior.
The separate `kb-bootstrap search-qmd` command is an explicitly bounded lexical
adapter: it requires caller-supplied canonical `--dir`, `--collection`, `--index`,
and pre-provisioned `--state-dir`. It is read-only and does not register, update,
select an ambient index, or fall back to legacy search. Follow its CLI help and
accepted ADR-018/019 contract; do not conflate it with legacy `search`.

These collection paths describe search/index scope only. QMD indexing does not authorize
Git tracking, committing, pushing, or publication. Each source must separately pass the
owning repository's license, privacy, secret, and destination review before it is tracked.
Keep private, bulky, binary, books, repository clones, and other local-only source inputs
outside these collections and untracked. A consumer may choose `sources/` as a local
location, but its name does not itself exclude files from Git; verify local ignore and
tracking policy.

```bash
qmd search "<keywords>" -c <project>-wiki
qmd query "intent: <what you are looking for>\nlex: <keywords>" -c <project>-wiki
qmd search "<source keywords>" -c <project>-raw
```

### 4. Read a Document
If QMD returns a reference to a file (e.g., `qmd://my-app/raw/releases.md`), use the context-mode tools to read the actual file from the disk.

## Configuring a New Collection
To define what files belong to a specific context, create a YAML file in `qmd/collections/<name>.yaml`. Keep canonical and raw paths separate; do not point both collections at the same mixed corpus.

## Completion gate

Before reporting knowledge-base work complete, run the universal validator and
project tests required by the selected workflow. Retrieval/index freshness is a
separate gate: run registration, update, and smoke queries only when QMD retrieval
or maintenance was explicitly selected and authorized for the intended state.
Do not require QMD operations for ordinary file-based work or imply that
`search-qmd` performs maintenance. Do not claim QMD indexing success when QMD is
unavailable or a smoke query was not run. The `QMD Collection Validation` section
from `kb-bootstrap validate` checks repository declarations and paths only; it
does not prove runtime registration, index freshness, search completeness, or
relevance. Report universal conformance, any repository-owned policy validation,
and retrieval/index freshness as separate outcomes. See the upstream
[validation composition guidance](https://github.com/ozand/kb-bootstrap/blob/main/docs/VALIDATION_COMPOSITION.md).
