# Knowledge Base (OKF + QMD) Bootstrap Framework

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
   - Check that `qmd.json` was created.

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
- Local `kb/raw/` directory.
- `qmd.json` for semantic search.
- All 4 Agent Skills (`qmd-operator`, `kb-wiki-builder`, `kb-capture`, `kb-lookup`) placed in `.agents/skills/`.

### Option 2: Umbrella Workspace
For a monorepo containing multiple servers or applications.
```bash
cd /path/to/umbrella-repo
kb-bootstrap --type umbrella
```
This generates:
- Global `qmd/collections/` configuration.
- Centralized `kb/apps/`, `kb/systems/`, and `kb/architecture/`.
- All 4 Agent Skills placed in the root `.agents/skills/`.
