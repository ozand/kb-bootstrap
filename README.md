# Knowledge Base (OKF + QMD) Bootstrap Framework

Current release: **0.2.0**. See [CHANGELOG.md](CHANGELOG.md) for release notes and migration considerations.

A portable CLI tool to instantly initialize a local Knowledge Base architecture in any repository. This framework combines the **Open Knowledge Format (OKF)** for structured documentation and **QMD** for semantic search.

## Core Concepts

- **[Open Knowledge Format (OKF)](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)**: A standard for structuring knowledge. We split data into a `raw/` layer (unprocessed scrapes, logs, release notes) and a `wiki/` layer (Markdown files with strict YAML frontmatter like `id`, `category`, and `tags`).
- **[QMD (Quality Markdown Search)](https://github.com/tobi/qmd)**: A CLI tool for blazing-fast local semantic search (RAG) over your markdown files. It indexes your `raw/` and `wiki/` layers so agents can instantly find context.

## Prerequisites & System Requirements

Before using this framework, ensure your host environment has the required toolchain. If an AI agent is performing the setup, it should verify and install these dependencies first.

1. **[Python 3.8+](https://www.python.org/downloads/)**
   - Required to run the `kb-bootstrap` CLI tool.
   - *Verification:* `python --version`

2. **[pipx](https://pipx.pypa.io/stable/)** (Highly Recommended)
   - Used to install Python CLI tools globally in isolated environments without breaking system packages.
   - *Installation:* 
     - Ubuntu/Debian: `sudo apt update && sudo apt install pipx && pipx ensurepath`
     - macOS: `brew install pipx && pipx ensurepath`
     - Windows: `python -m pip install --user pipx` then `python -m pipx ensurepath`

3. **[QMD (Quality Markdown Search)](https://github.com/tobi/qmd)**
   - The core engine for semantic search across the knowledge base.
   - *Installation:* Currently, QMD is distributed via Go.
     - Prerequisite: [Install Go](https://go.dev/doc/install)
     - Install QMD: `go install github.com/tobi/qmd@latest`
     - *(Ensure your Go binary path `~/go/bin` is in your system `$PATH`)*

---

## Agent Instructions: How to bootstrap a project

If a user asks you to "bootstrap the knowledge base", "setup KB", or gives you a link to this repository, follow this exact sequence:

### Phase 1: Environment Check
1. Verify `python` and `pipx` are installed. If missing, guide the user to install them or run the installation commands if you have host access.
2. Verify `qmd` is available (`qmd --version`). If missing, instruct the user to install Go and run `go install github.com/tobi/qmd@latest`.

### Phase 2: Tool Installation
1. **Install the CLI tool globally:**
   ```bash
   pipx install git+https://github.com/ozand/kb-bootstrap.git
   ```
   *(If `pipx` fails, fallback to `python -m pip install --user git+https://github.com/ozand/kb-bootstrap.git`)*

### Phase 3: Project Initialization
1. **Navigate to the target project root:**
   ```bash
   cd /path/to/target/project
   ```
2. **Determine project type and execute:**
   - Single application/tool: `kb-bootstrap --type single`
   - Large monorepo/workspace (like `servers_team`): `kb-bootstrap --type umbrella`

3. **Verify Deployment:**
   - Check that `.agents/skills/` contains the 4 generated skills (`kb-capture`, `kb-lookup`, `kb-wiki-builder`, `qmd-operator`).
   - Check that `qmd.json`, `qmd/collections/wiki.yaml`, and `qmd/collections/raw.yaml` were created.
   - Run `kb-bootstrap validate --dir kb --project-root .`.
   - Run the project test command.
   - Run `qmd update`, then smoke-test both generated collections with `qmd search`.

## Repository remote and issue-routing policy

A project initialized by `kb-bootstrap` may have both its own repository and this framework configured as Git remotes. Treat the remote names as ownership boundaries:

- `origin` is the current consumer project's repository. Project-specific knowledge, configuration, documentation, and defects belong there.
- `upstream` is optional and identifies the framework or source repository from which the consumer was derived. Reusable CLI, generator, packaged-template, and framework-documentation defects belong there.
- In an origin-only repository, route all project work to `origin` unless the user explicitly names another repository.
- In a multi-remote repository, classify the task by the files and behavior it owns; do not infer ownership from whichever remote the GitHub CLI selects.
- An explicit user request to contribute upstream overrides the normal consumer route only after the upstream repository identity is verified.

Before creating, editing, closing, or commenting on an Issue, verify the Git root, the relevant remote URL, the target repository, and its default branch.

Configure and verify the GitHub CLI default repository once for each checkout:

```bash
# This changes only the local gh repository selection; it does not change Git remotes.
gh repo set-default example/consumer-project
gh repo set-default --view

# Safe read-only verification.
gh repo view --json nameWithOwner,defaultBranchRef
```

The reported repository and default branch must match the intended target. If authentication or repository identity cannot be verified, stop before any mutation. Do not use commands that print authentication tokens as verification evidence.

A verified default makes read-only discovery convenient, but every mutating GitHub command must still include an explicit repository target:

```bash
# Consumer-owned mutation
gh issue create --repo example/consumer-project

# Reusable framework mutation
gh issue create --repo example/kb-bootstrap

# The same requirement applies to edits, comments, closures, and PR creation.
gh issue comment 123 --repo example/consumer-project --body "Sanitized status"
gh pr create --repo example/kb-bootstrap
```

If remote identity is missing, ambiguous, or does not match the intended Issue repository, stop without mutating GitHub or Git state and ask for clarification. Completion evidence must come from the repository that owns the Issue: a commit that exists only in a consumer checkout does not complete an upstream Issue.

Repository receipts and examples must contain only sanitized metadata such as repository names, remote roles, branch names, commit IDs, and public URLs. Never include credentials, tokens, private payloads, local runtime state, or unsanitized logs.

Run the read-only repository preflight before GitHub mutations or completion claims:

```bash
kb-bootstrap doctor --repo example/consumer-project
```

The doctor reports the current directory, Git root, sanitized `origin`/`upstream` identities, `gh` default repository, requested target, and local/remote default branches. It exits non-zero when identity is missing, ambiguous, or mismatched. It never changes remotes, branches, GitHub defaults, Issues, or pull requests.

For changes discovered in a generated consumer repository, follow the separate [consumer and upstream contribution workflow](docs/CONTRIBUTING_UPSTREAM.md). Consumer-specific work stays in the consumer checkout; reusable framework work uses a separate verified upstream checkout or worktree and an explicitly targeted pull request. Configure and verify downstream Git push precedence using the [push safety guide](docs/PUSH_SAFETY.md); `kb-bootstrap` never changes push defaults or remote URLs automatically.

Downstream tools can generate and validate a sanitized, machine-readable repository context:

```bash
kb-bootstrap manifest --repo example/consumer-project --output repository-context.json
kb-bootstrap manifest --output repository-context.json --check
```

See the [repository context manifest schema](docs/REPOSITORY_CONTEXT_SCHEMA.md) for the exact deterministic fields and omission rules.

To add repository-routing guidance without overwriting a downstream project's local instructions, explicitly manage one delimited block:

```bash
kb-bootstrap agents-governance --repo example/consumer-project --file AGENTS.md
```

See the [managed AGENTS.md block contract](docs/AGENTS_GOVERNANCE_BLOCK.md). Normal scaffolding does not rewrite an existing `AGENTS.md`.

## Installation (Manual)

Since this is packaged as a standard Python tool, you can install it globally or via `pipx` from any location (or directly from GitHub once pushed):

```bash
# Install locally in editable mode (if you are in the source folder)
pip install -e .

# Or install globally using pipx (Recommended for multi-host use)
pipx install /path/to/kb-bootstrap
```

*When published to a remote Git repository, you can install it on any host via:*
```bash
pipx install git+https://github.com/ozand/kb-bootstrap.git
```

## Usage

Once installed, the `kb-bootstrap` command is available globally in your terminal. Navigate to the root of the project where you want to create the knowledge base and run:

### Option 1: Single Project (Default)
For a standalone application repository.
```bash
cd /path/to/your-project
kb-bootstrap --type single
```
This generates:
- Local `kb/raw/` directory retained by `kb/raw/.gitkeep` in fresh Git checkouts.
- Root `qmd.json` with `collections_dir` set to `./qmd/collections`.
- `qmd/collections/<project>-wiki` configuration in `wiki.yaml`, indexing canonical Markdown under `kb/` while excluding `kb/raw/`.
- `qmd/collections/<project>-raw` configuration in `raw.yaml`, indexing source captures under `kb/raw/`.
- Anchored `.gitignore` rules for generated top-level artifacts and large raw files without hiding `kb/models/` or sanitized raw Markdown.
- All 4 Agent Skills (`qmd-operator`, `kb-wiki-builder`, `kb-capture`, `kb-lookup`) placed in `.agents/skills/`.

Collection names are derived from the target directory name. Use `<project>-wiki` for canonical answers by default and query `<project>-raw` explicitly when inspecting source evidence.

### Optional project-local lessons

Project-local lesson storage is opt-in and belongs to the target repository:

```bash
kb-bootstrap --type single --with-project-lessons
```

The option adds:

- `kb/lessons/SCHEMA.md` — the project-local Markdown/frontmatter contract.
- `kb/lessons/index.yaml` — the deterministic local lesson catalogue using `PROJECT-XXXX` IDs.
- `lesson-stores.json` — explicit capture and lookup routing; the generated default selects exactly one local capture store.

Without `--with-project-lessons`, these files are not generated and the existing scaffold output is preserved. Generated `kb-capture` instructions refuse missing or ambiguous destinations. Generated `kb-lookup` instructions search a configured local store first, then an explicitly configured read-only shared store. The tool does not discover shared stores, write to two stores, synchronize lessons, or publish promotion candidates automatically.

This capability depends on the generator and routing contracts tracked in [#4](https://github.com/ozand/kb-bootstrap/issues/4), [#24](https://github.com/ozand/kb-bootstrap/issues/24), and [#25](https://github.com/ozand/kb-bootstrap/issues/25), plus shared-registry metadata and identity work in `ozand/workspace-registry` [#50](https://github.com/ozand/workspace-registry/issues/50) and [#51](https://github.com/ozand/workspace-registry/issues/51). Demand evidence remains tracked separately in [#27](https://github.com/ozand/kb-bootstrap/issues/27).

### Validate the generated knowledge base

Run structural validation from the project root:

```bash
kb-bootstrap validate --dir kb --project-root .
```

The command performs both checks:

1. Markdown graph validation under `--dir`: dead links fail, while orphan nodes are reported as warnings. The graph linter excludes `raw/` directories.
2. QMD collection validation under `--project-root`: `qmd/collections/*.yaml` must contain valid, unique names and at least one existing configured path. Invalid collection syntax or missing target paths fail validation.

Structural validation does not update the QMD index. Complete the actual verification pipeline:

```bash
# 1. Structural validation
kb-bootstrap validate --dir kb --project-root .

# 2. Project tests
python -m pytest -q  # replace with the repository's documented test command

# 3. QMD indexing and retrieval smoke tests
qmd update
qmd search "<canonical query>" -c <project>-wiki
qmd search "<source query>" -c <project>-raw
```

Only report QMD rollout as successful when `qmd update` and both smoke searches were actually executed. QMD commands use the official CLI entry points: `qmd update`, `qmd query`, `qmd search`, and `qmd collection list`. This package does not replace QMD or implement a Python search index.

### Option 2: Umbrella Workspace
For a monorepo containing multiple servers or applications.
```bash
cd /path/to/umbrella-repo
kb-bootstrap --type umbrella
```
This generates:
- Root `qmd.json` and the same project-derived `<project>-wiki` / `<project>-raw` collection split used by the single layout.
- Centralized `kb/apps/`, `kb/systems/`, `kb/architecture/`, and retained `kb/raw/` directories.
- Anchored `.gitignore` rules that preserve canonical and sanitized Markdown knowledge.
- All 4 Agent Skills placed in the root `.agents/skills/`.
