# Knowledge Base (OKF + QMD) Bootstrap Framework

## When you need a project knowledge base

Project knowledge gets scattered across notes, source files, and team handoffs. `kb-bootstrap` creates a local knowledge-base layout in a repository, with structured Markdown conventions and optional search tooling. Use it when you want a consistent place to organize and retrieve project knowledge; it does not write or validate your domain's facts for you.

The framework combines the **Open Knowledge Format (OKF)** for structured documentation with **QMD** as an optional local search tool. QMD is not required for every local check: use `search-local` and `read-local` for bounded file-only discovery and reading when QMD is unavailable.

`validate-core --dir kb` (optionally `--now <offset-aware-time>`) checks canonical structure, provenance, and graph integrity without QMD configuration, model, or network operation. It does not check retrieval/index freshness, source truth, or publication readiness. Legacy `validate` still requires its QMD declaration checks.

For contributors writing project explanations or setup instructions, see the short [authoring guide](docs/AUTHORING_GUIDE.md).

Current release: **0.4.0**. See [CHANGELOG.md](CHANGELOG.md) for release notes and the [existing-consumer migration procedure](docs/MIGRATING_EXISTING_CONSUMERS.md) for staged adoption and rollback guidance.

## Caller-declared evidence lineage

The pure `kb_bootstrap.evidence_lineage.classify_evidence_lineage(records, coverage_complete)` helper classifies explicitly supplied lineage records; it does not inspect sources or verify independence. For example:

```python
from kb_bootstrap.evidence_lineage import classify_evidence_lineage

records = [
    {"id": "source-a", "kind": "independent", "upstream_ids": []},
    {"id": "draft", "kind": "generated", "upstream_ids": ["source-a"]},
    {"id": "copy", "kind": "reprint", "upstream_ids": ["draft"]},
]
print(classify_evidence_lineage(records, coverage_complete=True))
```

With complete caller-asserted coverage, each record reports the reachable declared root IDs. With incomplete coverage, the result is `unknown` without root counts. These declarations do not establish actual ancestry, support, truth, or independent evidence; the helper is separate from the evidence-binding resolver.

## Core Concepts

- **[Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)**: A vendor-neutral Markdown and YAML-frontmatter format. The [kb-bootstrap canonical profile](docs/OKF_V0_2_CANONICAL_PROFILE.md) requires non-empty `type`, recommends `title`, `description`, `tags`, and `status: stable`, accepts unknown extensions, and keeps stricter dead-link checks separate from OKF conformance.
- **[QMD (Quality Markdown Search)](https://github.com/tobi/qmd)**: An optional CLI for local semantic search. For bounded file-only discovery when QMD is unavailable, use `search-local` and `read-local`; neither command changes QMD state.

## Prerequisites & System Requirements

The CLI and local file-only commands require Python. Install QMD only if you want QMD-backed semantic search; it is not required for `validate-core`, `search-local`, or `read-local`. If an AI agent is performing setup, it must not install tools without the user's authorization.

1. **[Python 3.8+](https://www.python.org/downloads/)**
   - Required to run the `kb-bootstrap` CLI tool.
   - *Verification:* `python --version`

2. **[pipx](https://pipx.pypa.io/stable/)** (Highly Recommended)
   - Used to install Python CLI tools globally in isolated environments without breaking system packages.
   - *Installation:* 
     - Ubuntu/Debian: `sudo apt update && sudo apt install pipx && pipx ensurepath`
     - macOS: `brew install pipx && pipx ensurepath`
     - Windows: `python -m pip install --user pipx` then `python -m pipx ensurepath`

3. **Optional: [QMD (Quality Markdown Search)](https://github.com/tobi/qmd)**
   - Needed only for the QMD-backed `search` command; local `search-local` / `read-local` and `validate-core` work without it.
   - The npm installation requires [Node.js 22 or newer](https://nodejs.org/).
     - If desired and authorized, install QMD globally: `npm install -g @tobilu/qmd` (or `bun install -g @tobilu/qmd`).
     - Ensure the installed `qmd` executable is available on your system `PATH`.

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

If a user asks to bootstrap a knowledge base, first identify the target repository and the operation they need. Do not install tools or write files until the user authorizes those actions.

### Phase 1: Choose the needed capability
1. Verify Python is available for the CLI. `pipx` is an optional installation method, not a product prerequisite.
2. Ask whether the user needs QMD-backed search. QMD is optional: `validate-core`, `search-local`, and `read-local` do not require it. If QMD is wanted, report the Node.js 22+ requirement and request authorization before installing anything.

### Phase 2: Install only when authorized
Install the CLI only if requested and authorized. The default installs the current `main` tip:
```bash
pipx install git+https://github.com/ozand/kb-bootstrap.git
```
For a reproducible install of the older published v0.4.0 release, pin its tag explicitly:
```bash
pipx install git+https://github.com/ozand/kb-bootstrap.git@v0.4.0
```
The pinned release predates current unreleased `main` changes; it is not the latest `main` code. If `pipx` is unavailable, explain the alternative and wait for authorization rather than silently falling back to a global/user-site install.

### Phase 3: Project Initialization
1. **Navigate to the target project root:**
   ```bash
   cd /path/to/target/project
   ```
2. **Choose the content layout and execute:**
   - One application/tool knowledge layout: `kb-bootstrap --type single`
   - Multi-application/workspace knowledge layout: `kb-bootstrap --type umbrella`

   `single` and `umbrella` describe the generated knowledge content topology. They do not describe where the repository is hosted or deployed.

3. **Verify only the requested setup:**
   - Check that the expected generated skills and files exist.
   - Run `kb-bootstrap validate-core --dir kb` for local structural checks, or `validate` when the repository's QMD declarations are configured and required.
   - Run the project's documented test command when requested or appropriate.
   - Update/search QMD only when the user requested QMD setup and authorized the index operation; QMD updates can write local index state.

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

### Opt in to a local-core scaffold

For a fresh or empty target, `--core-only` creates the local knowledge folders and only the `kb-wiki-builder` skill. It creates no QMD files or optional lookup, capture, or research tools; the receipt says `NOT_CONFIGURED`, not disabled or unavailable. The flag is initialization-only, does not support repeats or mode conversion, and blocks rather than overwriting a nonempty target. `--type single|umbrella` still selects content layout, not a domain. The ordinary initialization command below remains unchanged when this flag is omitted.

```bash
kb-bootstrap --target ./my-kb --type single --core-only
# Add and edit ordinary Markdown under ./my-kb/kb/wiki/.
kb-bootstrap validate-core --dir ./my-kb/kb
kb-bootstrap read-local concepts/example.md --dir ./my-kb/kb
kb-bootstrap search-local "example" --dir ./my-kb/kb
```

`validate-core` checks universal local structure and graph integrity. Any consumer-owned policy check and any optional retrieval/index readiness check remain separate; none is implied by this workflow.

### Option 1: Single Content Layout (Default)
For knowledge centered on one application or tool.
```bash
cd /path/to/your-project
kb-bootstrap --type single
```

Repeating initialization is read-only: an exact matching scaffold reports a no-op; conflicting, partial, unsafe, or unavailable managed paths block without automatic repair or template upgrade. If project lessons are requested on a repeat but their four-artifact contract is absent, run `kb-bootstrap enable-project-lessons --target .` explicitly. A first-initialization I/O failure may leave files created by that invocation; inspect the target before retrying. This is a guard against accidental overwrites, not a transaction or protection against concurrent/hostile writers: run it against a stable target you control. It does not roll back or delete consumer-owned files.

This generates:
- Local `kb/raw/` directory retained by `kb/raw/.gitkeep` in fresh Git checkouts.
- Root `qmd.json` with `collections_dir` set to `./qmd/collections`.
- `qmd/collections/<project>-wiki` configuration in `wiki.yaml`, indexing canonical Markdown under `kb/` while excluding `kb/raw/`.
- `qmd/collections/<project>-raw` configuration in `raw.yaml`, indexing source captures under `kb/raw/` and research-study captures under `kb/research/`.
- Anchored `.gitignore` rules for generated top-level artifacts and large raw files without hiding `kb/models/` or sanitized raw Markdown.
- Read-only/search skills (`qmd-operator`, `kb-wiki-builder`, `kb-lookup`) placed in `.agents/skills/`; `kb-capture` is omitted until `--with-project-lessons` creates its local contract.
- The `market-research` skill in `.agents/skills/market-research/` and its layout: `kb/research/<YYYY-MM-DD>_<slug>/` (brief + immutable `raw/` page captures with screenshots) and `kb/wiki/{entities,concepts,reports}/` for conclusions. See [Research studies](#research-studies-market-research-skill).

Collection names are derived from the target directory name. Use `<project>-wiki` for canonical answers by default and query `<project>-raw` explicitly when inspecting source evidence.

QMD raw indexing is a search configuration, not Git tracking or publication approval. `kb/research/` is intended for tracked public research evidence only after each source is individually reviewed for license, privacy, secrets, and repository eligibility. Keep private, bulky, binary, book, repository-clone, and other non-public source inputs outside tracked research; a consumer may use a local-only `sources/` area, but its name does not itself ignore files, so verify the repository's ignore/tracking policy and keep such inputs untracked. Existing ignore rules for selected bulky `kb/raw/` extensions do not make other files approved for publication.

Use the read-only search wrapper when mode labeling and validated collection selection are required:

```bash
# Canonical is the default.
kb-bootstrap search "how is setup configured?" --project-root .

# Raw research requires explicit opt-in.
kb-bootstrap search "original error trace" --mode raw --project-root .
```

For bounded offline discovery from canonical Markdown, use `search-local` and read a selected file separately with `read-local`. Both commands require an explicit canonical root; they do not use QMD, include raw/research/lesson layers, or assert that a matching line is verified knowledge. Canonical discovery is limited to visible Markdown files; budget exhaustion reports `PARTIAL` rather than claiming a complete search:

```bash
kb-bootstrap search-local "connection timeout" --dir kb
kb-bootstrap read-local "services/api.md" --dir kb --max-bytes 16384
```

Local search uses literal Unicode case-folded substring matching and returns relative paths, a matched line/snippet, and available authored context. Resource ceilings can produce `PARTIAL`/exit 3; inspect `limiting_budget` before treating no returned match as complete. Reads return a bounded UTF-8 prefix and disclose truncation. See [ADR-017](docs/adr/ADR-017-add-bounded-local-search-and-read-commands.md) for the full contract. The existing `search` command remains the QMD-backed canonical/raw wrapper.

Python callers that already selected a canonical Markdown file can project one exact section by heading path:

```python
import hashlib
from pathlib import Path
from kb_bootstrap.section_projection import project_section

root = Path("kb")
relative_path = "services/api.md"
source_bytes = (root / relative_path).read_bytes()
result = project_section(root, relative_path, hashlib.sha256(source_bytes).hexdigest(), ["Setup", "Timeouts"])
if result["status"] == "COMPLETE":
    print(result["text"])
```

The digest binds this call to the supplied file bytes; it does not establish source truth, freshness, or approval. The result includes a revision-scoped locator. A stale expected digest returns `REVISION_MISMATCH` with the observed digest and no section text. This Python API is not a CLI option and does not perform QMD lookup or discovery; see [ADR-034](docs/adr/ADR-034-project-one-explicit-bounded-markdown-section.md) for limits and outcomes.

A caller can report the metadata for an already-produced projection result without executing the projection again:

```python
from kb_bootstrap.section_projection_reporting import report_section_projection

already_produced = {
    "status": "COMPLETE", "path": "guide.md", "observed_sha256": "a" * 64,
    "heading_path": ["Setup"], "occurrence": 1, "start_line": 1,
    "end_line": 2, "text": "# Setup\nSteps\n", "truncated": False,
}
report = report_section_projection(
    selection_state="CONFIGURED", required=True, result=already_produced
)
print(report)
# {'selection_state': 'CONFIGURED', 'required': True, 'operation': 'project_section',
#  'operation_status': 'COMPLETE', 'observation': 'AVAILABLE',
#  'requirement_satisfied': True}
```

The report contains exactly these six fields, preserves ordinary projection outcomes, and never includes section text or path. It is a pure metadata report: it does not read files, run projection, or grant authority. See [ADR-037](docs/adr/ADR-037-report-one-section-projection-result.md).

For a caller-authorized, read-only evidence-impact check, use the Python API with explicit JSON binding input and complete baseline/current source envelopes. The trusted host must bind its policy decisions to this exact operation, purpose, input roots, and any expected revisions; callbacks below are not credentials or a persisted grant. The example assumes the files and envelopes already exist and that the caller has computed any expected digests independently.

```python
from pathlib import Path
from kb_bootstrap.evidence_binding import resolve_evidence_binding

# The integration supplies these callbacks from the trusted operator workflow.
result = resolve_evidence_binding(
    project_root=Path("kb").resolve(),
    binding_path="bindings/topic.json",
    knowledge_path="wiki/concepts/topic.md",
    baseline_metadata_path="captures/baseline.yaml",
    baseline_project_root=Path(".").resolve(),
    baseline_corpus_root="raw/baseline",
    baseline_selected_paths=["evidence.md"],  # Relative to raw/baseline
    current_metadata_path="captures/current.yaml",
    current_project_root=Path(".").resolve(),
    current_corpus_root="raw/current",
    current_selected_paths=["evidence.md"],  # Relative to raw/current
    # Optional caller-known digests: binding, knowledge, baseline_metadata,
    # current_metadata, and selected_files keyed as '<side>:<relative-path>'.
    # Selected-file entries only check already validated bytes; they add no reads.
    authorize_validation_read=trusted_host_validation_read,
    authorize_processing_and_report=trusted_host_processing_and_report,
)
print(result["status"], result.get("knowledge"), result.get("references"))
```

The resolver has no CLI, does no discovery or QMD/network access, and writes no files. It reads exactly the explicitly selected binding, knowledge, metadata, and envelope-selected retained evidence files; ensure each input is authorized for this operation. Its JSON report is ephemeral. Hashes bind observed bytes only, not entailment, source truth, freshness, review, or approval. A denied host precondition raises `PermissionError` outside the ADR-036 report; these callbacks do not authenticate the caller, enforce revocation, or provide host-egress isolation. See [ADR-031](docs/adr/ADR-031-bind-explicit-knowledge-items-to-retained-evidence.md), [ADR-035](docs/adr/ADR-035-require-explicit-local-policy-for-evidence-reading.md), and [ADR-036](docs/adr/ADR-036-define-json-evidence-binding-input-and-report.md) for limits and boundaries.

To build a transient worklist, pass the report returned by the resolver and the complete caller-declared graph to the pure ADR-042 composition helper. Mapping is explicit; matching IDs or digests does not infer ancestry. The resolver result below is the output of the preceding call; this example performs no extra file access:

```python
from kb_bootstrap.evidence_review import compose_evidence_review_worklist

lineage = [
    {"id": "source-origin", "kind": "independent", "upstream_ids": []},
    {"id": "source-reprint", "kind": "reprint", "upstream_ids": ["source-origin"]},
]
review = compose_evidence_review_worklist(
    resolver_report=result,
    lineage_records=lineage,
    coverage_complete=True,
    reference_lineage_ids={
        (result["references"][0]["source_id"], result["references"][0]["representation_id"]): "source-reprint"
    } if result["status"] == "COMPLETE" and result["references"] else {},
)
for item in review["worklist"]:
    if item["review_required"]:
        print(item["reference"]["source_id"], item["reference"]["state"], item["lineage"])
```

The example identity pair must be replaced with an actual COMPLETE report row. Unmapped lineage remains `unknown`; incomplete declared coverage exposes no roots. The helper validates but cannot authenticate a supplied report or verify ancestry, independence, truth, completeness, or authority. Its output does not grant permission or approve a lifecycle change. See [ADR-040](docs/adr/ADR-040-classify-caller-declared-evidence-lineage.md) and [ADR-042](docs/adr/ADR-042-compose-evidence-reports-with-declared-lineage.md).

For the explicit bounded lexical QMD 2.8.3 adapter, use a pre-provisioned, hook-free named state directory:

```bash
kb-bootstrap search-qmd "connection timeout" --dir kb --collection wiki --index project --state-dir /path/to/qmd-state
```

The state layout is `config/project.yml` and `cache/qmd/project.sqlite`; see [ADR-018](docs/adr/ADR-018-add-an-explicit-bounded-lexical-qmd-adapter.md) and [ADR-019](docs/adr/ADR-019-accept-pinned-qmd-index-selectors-and-inert-model-defaults.md). Search never registers collections or installs QMD/models. Missing QMD reports `OPTIONAL_UNAVAILABLE`; invalid state, timeout, excessive output or invalid records report `FAILED`, without automatic fallback. External QMD startup can write bookkeeping in the selected state; this is not a zero-write or no-egress sandbox. Hits are navigation, not source verification or index-freshness evidence. Real smoke verified only a synthetic one-file allowlist; general QMD exclusion membership remains unverified because `collection add` overwrites authored ignore rules.

The wrapper runs `qmd search` against exactly one matching collection. Raw results are marked `[RAW]` and include sanitized QMD collection/source provenance. Missing or ambiguous mode collections block before QMD is called. The wrapper does not update indexes, write source files, canonicalize, or promote results.

### Research studies (market-research skill)

`market-research` runs competitive, technology and UX studies from public web sources: every analysed page is captured as Markdown (+ product screenshots) under `kb/research/<date>_<slug>/raw/`, conclusions become entities, concepts and a report under `kb/wiki/`. The skill covers feature and technology matrices, UX/UI patterns, positioning from public reviews, JTBD and customer journey maps, and multi-agent market maps with a consolidation step. It requires the [surf](https://github.com/nicobailon/surf-cli) browser CLI connected to Chrome/Chromium and Python 3.9+.

The raw QMD collection indexes both `kb/raw/` and `kb/research/`; the wiki collection excludes both. These paths describe search scope only and do not authorize Git tracking, committing, pushing, or publication. Track a research capture only after an individual review confirms it is eligible for the intended repository and destination, including license, privacy, and secret checks. Keep private, bulky, binary, books, repository clones, and other local source inputs in a local-only `sources/` area; do not track or publish them through this research workflow. A Markdown format, QMD index entry, capture helper output, or existing filename is not approval to publish.

Agents started outside the project do not discover project skills by name; when dispatching a study to another agent, pass the absolute path to `.agents/skills/market-research/SKILL.md`. To make it available in every session on a machine, link the installed copy into the user skill folders, e.g. `ln -s "$(python -c 'import kb_bootstrap,os;print(os.path.dirname(kb_bootstrap.__file__))')/templates/skills/market-research" ~/.agents/skills/market-research`.

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

To create an opt-in published artifact without relocating consumer layers, export a new contained ZIP path:

```bash
kb-bootstrap export-published-bundle --project-root . --dir kb --output published-okf.zip
```

The ZIP contains eligible canonical Markdown plus exact lowercase `index.md` and `log.md`, excluding `raw/`, `lessons/`, and non-Markdown files. It never rewrites the working tree, QMD configuration, or lesson routing, and fails closed on unsafe paths, invalid reserved structure, source changes, existing outputs, or unsupported exclusive publication.

Raw-file revision inventory is a separate, opt-in operation. It hashes exact bytes under one explicit corpus root and publishes a new JSON snapshot outside that corpus without rewriting sources:

```bash
kb-bootstrap raw-manifest --project-root . --dir kb/raw --output raw-first.json
kb-bootstrap raw-manifest --project-root . --dir kb/raw --previous raw-first.json --output raw-second.json
```

The report classifies new, changed, unchanged, and removed paths. Output paths and hashes may disclose sensitive metadata: store the manifest and captured stdout privately. Existing outputs are never overwritten; neither QMD nor GLiNER is required. Run only on a stable, locally controlled checkout: static symlinks and observed source changes block, but on Windows a hostile concurrent directory replacement may be enumerated before a post-enumeration check detects it. This is not a race-free filesystem snapshot or an adversarial-writer-safe scanner. See [ADR-010](docs/adr/ADR-010-record-raw-revisions-in-an-exclusive-manifest.md).

Optional GLiNER2 setup can be inspected without downloading a model or changing the core Python environment:

```bash
# Run this command using the optional peer environment's Python interpreter.
python -m kb_bootstrap.cli inspect-gliner --model-dir /path/to/local-checkpoint
```

The result checks only the **current Python interpreter**, discoverability of a module named `gliner2` (not installation or version of the distribution), and a local `config.json`. It does not execute a user-supplied interpreter. It does **not** verify complete model assets, license, checkpoint digest, successful inference or network isolation; path checks assume a stable, locally controlled directory, not adversarial concurrent replacement. Missing requirements block with sanitized categories. Issue #109 requires separately consented, pinned provisioning and a real local model smoke before setup is complete; remote HTTP inference is a separate Issue #108 decision.

For an existing **locally controlled** directory, compare its entire selected file set against a previously established full-byte digest:

```bash
kb-bootstrap verify-gliner-checkpoint --model-dir /path/to/checkpoint \
  --file config.json --file model.safetensors --file tokenizer.json \
  --expected-model-digest <64-lowercase-hex-sha256>
```

List **every** file present in that directory, including nested and ancillary files; unlisted files block. The digest is ADR-011's length-framed stream over sorted relative POSIX names and actual file bytes, not a Git commit or single weight hash. A match proves only that the selected directory bytes match the supplied digest: it does **not** validate the acquisition plan, approved inventory, owner consent, publisher authenticity, model loading or denied network. It does not establish checkpoint eligibility. No acquisition or promotion occurs. Stable locally controlled directory required; Windows concurrent directory replacement is not adversarial-writer-safe. See [ADR-011](docs/adr/ADR-011-extract-local-entity-candidate-cards-as-an-optional-peer.md) and [ADR-013](docs/adr/ADR-013-quarantine-model-before-owner-digest-confirmation.md).

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

### Local research handoff (ADR-038)

This Python API carries bounded progress in one explicitly selected local JSON record. Create it after retaining intended source bytes and before analysis; save/check before handoff, then provide the next process only the record and explicitly retained artifacts. Prior chat is unnecessary. References stay opaque; loading is not a trust or truth claim.

The following synthetic temporary-directory example captures UTF-8 source before creating a revision-1 record. It prints statuses only, not source text or ephemeral directory paths:

```python
import hashlib
import tempfile
from pathlib import Path
from kb_bootstrap.local_handoff import save_record, load_record, check_record

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    retained = root / "source.txt"
    retained.write_bytes(b"Synthetic source, section A.\\n")  # capture before work
    revision = hashlib.sha256(retained.read_bytes()).hexdigest()
    record = {
        "schema": "kb-local-handoff/v1", "record_id": "demo-1", "revision": 1,
        "study_ref": "study:demo", "objective": "Inspect synthetic source",
        "scope": {"included": ["section A"], "excluded": []},
        "materials": [{"ref": "source:demo", "revision": revision,
            "observation": "captured", "observed_scope": "", "unread_remainder": "section A",
            "analysis": "not-started", "analyzed_scope": "", "unanalyzed_remainder": "section A"}],
        "outputs": [], "steps": [], "checks": {"run": [], "not_run": []},
        "retention": {"owner": "demo caller", "storage_class": "runtime-ephemeral",
            "storage_ref": "temporary demo", "retention_rule": "discard on exit",
            "access": "caller", "integrity": "sha256", "availability": "not-verified",
            "disposal": "caller"}, "assumptions": [], "open_questions": [],
    }
    path = root / "handoff.json"
    saved = save_record(path, record, permission=True)  # caller authorized synthetic local path
    loaded = load_record(path)
    checked = check_record(loaded["record"], lambda *a, **k: {"status": "unavailable"})
    print(saved["status"], loaded["status"], checked["study_state"])
```

The owner checker must attest current opaque input/output/evidence revisions; `passed` is not authenticated by the record. `permission=True` represents an out-of-record caller decision for this exact local path and retention/access boundary; it is not a policy engine. ADR-035 read permission does not grant write permission. Use synthetic/local-only data; sensitive processing needs separately verified permissions and safeguards.

There is no CLI, daemon, session discovery, remote publication, transcript copying, QMD/index write, or knowledge promotion. Replacement preserves historical attempt prefixes under a local compare-and-replace boundary serialized across local processes by an advisory sidecar lock derived from the selected target path. The sibling lock file is an operational artifact in the selected parent directory and persists to avoid stale-lock cleanup/inode races; it contains no record payload. Advisory locking assumes cooperating processes and a stable local filesystem; it makes no distributed or hostile-writer guarantee. Follow the selected owner's retention/access policy.
