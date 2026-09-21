# Knowledge Base (OKF + QMD) Bootstrap Framework

Current release: **0.4.0**. See [CHANGELOG.md](CHANGELOG.md) for release notes and the [existing-consumer migration procedure](docs/MIGRATING_EXISTING_CONSUMERS.md) for staged adoption and rollback guidance.

A portable CLI tool to instantly initialize a local Knowledge Base architecture in any repository. This framework combines the **Open Knowledge Format (OKF)** for structured documentation and **QMD** for semantic search.

## Core Concepts

- **[Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)**: A vendor-neutral Markdown and YAML-frontmatter format. The [kb-bootstrap canonical profile](docs/OKF_V0_2_CANONICAL_PROFILE.md) requires non-empty `type`, recommends `title`, `description`, `tags`, and `status: stable`, accepts unknown extensions, and keeps stricter dead-link checks separate from OKF conformance.
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

The read-only `kb-bootstrap search` wrapper resolves the QMD executable through the
host `PATH` before invoking it without a shell. This supports Windows executable
shims and paths containing spaces while preserving argument boundaries. Supported
runtimes are Python 3.8+ and an installed `qmd` executable; verify availability
with `qmd --version`, then run a representative search from the project root:

```text
kb-bootstrap search "how is setup configured?" --project-root .
```

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
2. **Choose the content layout and execute:**
   - One application/tool knowledge layout: `kb-bootstrap --type single`
   - Multi-application/workspace knowledge layout: `kb-bootstrap --type umbrella`

   `single` and `umbrella` describe the generated knowledge content topology. They do not describe where the repository is hosted or deployed.

3. **Verify the generated scaffold:**
   - Check that `.agents/skills/` contains `kb-lookup`, `kb-wiki-builder`, and `qmd-operator`; `kb-capture` is generated only with `--with-project-lessons`.
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

Repository receipts and examples must contain only sanitized metadata such as repository names, remote roles, branch names, commit IDs, and public URLs. Never include credentials, tokens, private payloads, local runtime state, or unsanitized logs. A manifest or receipt is durable only when its owner, storage class, retention/expiry, access, integrity/version, and post-run availability are explicit; `.pi/`, Herdr transcripts, caches, and temporary output are not a repository audit database. See [durable and ephemeral evidence](docs/EVIDENCE_RETENTION.md).

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
kb-bootstrap agents-governance --repo example/consumer-project --project-root . --file AGENTS.md
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

Once installed, the `kb-bootstrap` command is available globally in your terminal. Navigate to the root of the repository that will own the generated files and run it.

### Identify the executing validator

Use `kb-bootstrap --version` to print the version of the executing `kb_bootstrap` package implementation. This is useful when a captured validation result may have come from an older binary:

```text
kb-bootstrap --version
# kb-bootstrap 0.4.0
```

`kb-bootstrap validate` begins with `Validator: kb-bootstrap <version>`. The line identifies the validator implementation only; it does not identify the knowledge base, OKF profile, QMD index, or consumer policy version. Validation sections and exit status retain their existing meanings.

### Repository placement and content topology

Repository placement and generated content topology are separate choices:

- **Standalone placement:** the knowledge base has its own repository. Example: create an empty `product-knowledge` repository, enter its root, and run `kb-bootstrap --type single` or `--type umbrella` according to the content it will hold.
- **Embedded placement:** the knowledge base lives inside an existing product repository. Example: enter the existing application repository root and run `kb-bootstrap --type single` so that repository owns its `kb/`, QMD configuration, and generated skills.

Placement determines which repository owns the generated files, Issues, commits, and pull requests. The command does not create a repository, select a deployment model, or infer ownership from a parent workspace. If the intended repository root or owner is ambiguous, resolve it before running the generator.

The current `--type single|umbrella` option selects only the **content topology**:

- `single` creates the layout for one application or tool.
- `umbrella` creates centralized areas for multiple applications and systems.

Both topologies work in either standalone or embedded placement. No separate standalone/embedded generator modes are needed. A future `--layout` name could be a compatibility alias for `--type`; it would not introduce new behavior and is not currently implemented.

### Option 1: Single Content Layout (Default)
For knowledge centered on one application or tool.
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
- Read-only/search skills (`qmd-operator`, `kb-wiki-builder`, `kb-lookup`) placed in `.agents/skills/`; `kb-capture` is omitted until `--with-project-lessons` creates its local contract.

Collection names are derived from the target directory name. Use `<project>-wiki` for canonical answers by default and query `<project>-raw` explicitly when inspecting source evidence.

Use the read-only search wrapper when mode labeling and validated collection selection are required:

```bash
# Canonical is the default.
kb-bootstrap search "how is setup configured?" --project-root .

# Raw research requires explicit opt-in.
kb-bootstrap search "original error trace" --mode raw --project-root .
```

The wrapper runs `qmd search` against exactly one matching collection. Raw results are marked `[RAW]` and include sanitized QMD collection/source provenance. Missing or ambiguous mode collections block before QMD is called. The wrapper does not update indexes, write source files, canonicalize, or promote results.

### Optional project-local lessons

Project-local lesson storage is opt-in and belongs to the target repository:

```bash
kb-bootstrap --type single --with-project-lessons
```

The option adds:

- `.agents/skills/kb-capture/SKILL.md` — capture instructions enabled only with the complete local contract.
- `kb/lessons/SCHEMA.md` — the project-local Markdown/frontmatter contract.
- `kb/lessons/index.yaml` — the deterministic local lesson catalogue using `PROJECT-XXXX` IDs.
- `lesson-stores.json` — explicit capture and lookup routing; the generated default selects exactly one local capture store.

Without `--with-project-lessons`, these files and the `kb-capture` skill are not generated. For a repository that was already initialized without them, use the narrow post-init operation `kb-bootstrap enable-project-lessons --target .`; it adds only the project-local lesson contract and does not rerun initialization or rewrite QMD and unrelated skills. Complete valid contracts produce a deterministic no-op, while partial, malformed, conflicting, path-escaping, or symlinked state blocks before mutation. Generated `kb-lookup` instructions block when no lesson stores are configured, search a complete configured local store first, then an explicitly configured read-only shared store. The tool does not discover shared stores, write to two stores, synchronize lessons, or publish promotion candidates automatically. See the [lesson ownership and routing policy](docs/LESSON_ROUTING_POLICY.md) for the canonical ownership categories, deterministic examples, and sanitized failure rules. Cross-scope changes use the separate manual [reviewed lesson promotion and demotion workflow](docs/LESSON_PROMOTION_WORKFLOW.md). A consumer may prepare a local, write-free artifact through the [reviewed shared contribution candidate workflow](docs/SHARED_CONTRIBUTION_CANDIDATE.md); publication remains a separate explicitly authorized action. Disconnected consumers may also opt into a bounded [offline shared lesson cache](docs/OFFLINE_LESSON_CACHE.md) with explicit lesson IDs, provenance/version/freshness metadata, and read-only refresh/check/prune behavior.

The universal lesson metadata, registry identity, configured-store lookup, contribution-candidate, and offline-cache contracts are owned by `kb-bootstrap`. Any repository may opt into them using explicit local paths and configuration; no particular consumer repository is required. See the [shared lesson metadata contract](docs/SHARED_LESSON_METADATA.md). The project-local scaffold and routing history are tracked in [#24](https://github.com/ozand/kb-bootstrap/issues/24), [#25](https://github.com/ozand/kb-bootstrap/issues/25), and [#28](https://github.com/ozand/kb-bootstrap/issues/28).

Universal validation and lookup commands:

```bash
kb-bootstrap validate-shared-metadata --input lesson-metadata.json
kb-bootstrap validate-lesson-registry --root path/to/lesson-registry
kb-bootstrap validate-lesson-registry --root path/to/lesson-registry --next-id
kb-bootstrap lesson-lookup --config lookup-bundle.json --query "timeout" --timeout 2
```

These commands require explicit files/directories, perform no hidden store discovery, and do not write lessons, indexes, registries, or external repositories. [`lookup-bundle.json`](docs/LESSON_LOOKUP_BUNDLE.md) is a separate read-only search input containing at most one explicit local JSON store and one explicit shared JSON store; it is not the generated capture-routing `lesson-stores.json`. Local results take precedence, and the shared store is queried only when local lookup has no match.

Lesson identity remains repository-owned: `PROJECT-XXXX` and `KB-XXXX` are globally distinguished by scope, owner repository, and provenance. The bounded [lesson identity research](docs/LESSON_IDENTITY_RESEARCH.md) recommends against UUID/ULID or distributed allocation until measurable evidence thresholds are met. The related [promotion reconciliation research](docs/PROMOTION_RECONCILIATION_RESEARCH.md) recommends preserving one-owner writes and using read-only reconciliation plus separately authorized compensating actions before considering distributed transactions.

### Validate the generated knowledge base

Run structural validation from the project root:

```bash
kb-bootstrap validate --dir kb --project-root .
```

The command performs four read-only checks:

1. [Canonical OKF v0.2 profile validation](docs/OKF_V0_2_CANONICAL_PROFILE.md) under `--dir` (default `kb`): every ordinary canonical concept needs exact YAML frontmatter and a non-empty `type`; generated optional fields are type-checked; unknown types/metadata are accepted without source mutation; case-insensitive `raw`/`lessons` directories and case-insensitive reserved `index.md`/`log.md` files at every level are excluded; static symlinked paths fail closed, and validation assumes a stable checkout rather than a concurrent filesystem snapshot.
2. The separate [canonical provenance/freshness profile](docs/CANONICAL_PROVENANCE_FRESHNESS_PROFILE.md): validates optional `generated`, `verified`, `sources`, `status`, and `stale_after`. Fresh/stale classification uses only explicit `--now <offset-aware timestamp>`; without it freshness is `unknown` and the system clock is not read.
3. The separately labelled kb-bootstrap graph-integrity extension under `--dir`: dead links fail, while orphan nodes are reported as warnings. This is intentionally stricter than OKF v0.2, which tolerates broken cross-links.
4. QMD collection validation under `--project-root`: `qmd/collections/*.yaml` must contain valid, unique names and at least one existing configured path. Invalid collection syntax or missing target paths fail validation.

Validation never migrates, repairs, normalizes, or rewrites canonical files.

Interpret this as the universal conformance/declaration gate only. A consumer may also require a separate repository-owned policy validator, and QMD registration/index freshness requires separate runtime evidence. One passing gate does not prove either of the others. See [validation composition for consumer repositories](docs/VALIDATION_COMPOSITION.md) for the ownership matrix, generic commands, reporting example, and non-claims.

For optional machine-readable analysis, create a versioned deterministic JSON graph without changing Markdown:

```bash
kb-bootstrap export-graph --project-root . --dir kb --output canonical-graph.json
```

The [canonical graph export contract](docs/CANONICAL_GRAPH_EXPORT.md) includes sorted ordinary concept nodes, exact normalized frontmatter payloads, and sorted normalized internal Markdown-link edges. Existing outputs, malformed/dead/escaping/symlinked local inputs, and unsafe paths block without overwrite; no UI, server, QMD update, or background process is involved.

Structural validation does not update the QMD index. Complete the actual verification pipeline:

```bash
# 1. Structural validation
kb-bootstrap validate --dir kb --project-root .

# 2. Project tests
python -m pytest -q  # replace with the repository's documented test command

# 3. QMD registration (once per machine per collection), indexing, and retrieval smoke tests
qmd collection add kb --name <project>-wiki --mask "**/*.md"
qmd collection add kb/raw --name <project>-raw --mask "**/*.md"
qmd update
qmd search "<canonical query>" -c <project>-wiki
qmd search "<source query>" -c <project>-raw
```

`qmd/collections/*.yaml` and `qmd.json` are this package's declarations, checked by `kb-bootstrap validate`; QMD itself does not read them. QMD keeps its own collection registry (`~/.config/qmd/index.yml`, or a project-local `.qmd/index.yml`, or a named index selected with `qmd --index <name>`), and `qmd update` re-indexes only collections already registered there. Until `qmd collection add` has been run for `<project>-wiki`, `qmd search -c <project>-wiki` answers `Collection not found` and `kb-bootstrap search` reports it as `QMD search is unavailable: Collection not found: <project>-wiki`. `kb-bootstrap search` queries whichever index QMD selects for the project directory; it does not pass `--index`, so a collection registered under a named index is not visible to it.

Only report QMD rollout as successful when `qmd collection add`, `qmd update`, and both smoke searches were actually executed. Report universal conformance, repository-owned policy validation, and retrieval/index freshness as separate outcomes; do not infer one from another. QMD commands use the official CLI entry points: `qmd collection add`, `qmd update`, `qmd query`, `qmd search`, and `qmd collection list`. This package does not replace QMD or implement a Python search index.

### Option 2: Umbrella Content Layout
For knowledge spanning multiple servers or applications in one owning repository.
```bash
cd /path/to/umbrella-repo
kb-bootstrap --type umbrella
```
This generates:
- Root `qmd.json` and the same project-derived `<project>-wiki` / `<project>-raw` collection split used by the single layout.
- Centralized `kb/apps/`, `kb/systems/`, `kb/architecture/`, and retained `kb/raw/` directories.
- Anchored `.gitignore` rules that preserve canonical and sanitized Markdown knowledge.
- Read-only/search skills placed in the root `.agents/skills/`; `kb-capture` is added only with `--with-project-lessons`.
