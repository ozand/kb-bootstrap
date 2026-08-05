# Knowledge Base (OKF + QMD) Bootstrap Framework

A portable CLI tool to instantly initialize a local Knowledge Base (Raw -> Wiki OKF + QMD Semantic Search) and install the necessary AI Agent Skills in any repository, on any host.

## Agent Instructions: How to bootstrap a project

If a user asks you to "bootstrap the knowledge base", "setup KB", or gives you a link to this repository, follow these steps exactly:

1. **Install the CLI tool globally (if not already installed):**
   ```bash
   # From a local path
   pipx install /path/to/kb-bootstrap
   # OR from GitHub directly
   pipx install git+https://github.com/ozand/kb-bootstrap.git
   ```
   *(If `pipx` is unavailable, use `pip install --user ...`)*

2. **Navigate to the target project root:**
   ```bash
   cd /path/to/target/project
   ```

3. **Determine project type and execute:**
   - If the project is a single application/tool, run: `kb-bootstrap --type single`
   - If the project is a large monorepo or workspace (like `servers_team`), run: `kb-bootstrap --type umbrella`

4. **Verify:** Check that `.agents/skills/` contains the 4 generated skills (`kb-capture`, `kb-lookup`, `kb-wiki-builder`, `qmd-operator`) and that the `kb/` folder structure was created.

## Installation

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
