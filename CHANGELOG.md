# Changelog

## Unreleased

### Research decisions

- Keep cross-repository lesson promotion as one-owner, explicitly reviewed operations; prefer idempotent evidence, read-only reconciliation, and separately authorized compensation over distributed transactions.
- Define measurable incident, recovery-time, adoption, and audit thresholds before implementing a reconciliation receipt or reconsidering automatic coordination.

## 0.3.0 — 2026-09-12

### Project-local lessons

- Add the public `kb-bootstrap enable-project-lessons --target <repository-root>` command for bounded post-init enablement without rerunning the initializer or rewriting unrelated QMD and skill configuration.
- Install the four project-local contract files when fully absent, return a deterministic no-op when complete and valid, and fail closed on partial, malformed, conflicting, path-escaping, or symlinked state.
- Stage writes and install each file exclusively without overwriting existing destinations; use compensating rollback that removes only files still identified as created by this invocation.

### Search diagnostics

- `kb-bootstrap search` appends QMD's own one-line diagnostic to
  `QMD search is unavailable` instead of reporting the bare phrase. The bare
  phrase covered three different faults with one word: `qmd` not on PATH, the
  collection never registered with `qmd collection add`, and the collection
  registered in a different QMD index than the one QMD selects for the project
  directory. The stable prefix is kept; only the suffix is new.
- Document the missing registration step. `qmd/collections/*.yaml` and
  `qmd.json` are kb-bootstrap declarations that QMD does not read; `qmd update`
  re-indexes only collections already registered. The README pipeline and the
  `qmd-operator` skill now run `qmd collection add` before `qmd update`.

### Research decisions

- Retain repository-scoped `PROJECT-XXXX` and `KB-XXXX` identifiers; require
  scope, owner, and provenance at identity-safe interchange boundaries, and defer
  global immutable IDs until documented incident/interchange thresholds are met.

### Universal lesson workflows

- Make `kb-bootstrap` the owner of universal shared lesson metadata, registry
  identity/index validation, fail-closed ID guidance, and explicit local/shared
  lookup orchestration.
- Add explicit canonical/raw QMD search, local shared-contribution candidate preparation,
  and bounded offline shared-lesson caching.
- Add a separate validator and CLI command for generated project-local `PROJECT-XXXX`
  registries without changing the shared `KB-XXXX` registry contract.
- Keep every consumer repository optional and independently configured; no
  workspace-specific repository or filesystem path is required.

### Documentation and migration

- Clarify that repository placement is independent from `single` or `umbrella`
  content topology.
- Document staged existing-consumer migration plus deterministic lesson routing,
  promotion/demotion, lookup-bundle, candidate, cache, shared metadata, and identity policies.
- Add ADR-001 for the project-local validator and ADR-002 for bounded post-init enablement.

## 0.2.1 — 2026-08-23

### Repository governance safeguards

- Fix pull-request completion validation by reading the PR base repository, head
  commit, and public URL through fields supported by the GitHub API.
- Preserve fail-closed behavior for unavailable PRs, wrong repositories, and
  commits not reachable from the associated PR head.

## 0.2.0 — 2026-08-22

### Knowledge-base scaffolding

- Generate separate project-derived canonical (`<project>-wiki`) and raw
  (`<project>-raw`) QMD collections.
- Validate Markdown links and QMD collection names/paths with one structural
  validation command.
- Preserve empty `kb/raw/` directories with `.gitkeep`.
- Add opt-in project-local lessons with an explicit capture/lookup store contract.

### Repository governance safeguards

- Add a read-only repository doctor that blocks missing or mismatched targets.
- Add completion commit validation against the target default branch or associated
  pull request.
- Add deterministic sanitized repository-context manifests.
- Add explicit management of one delimited repository-governance block in
  downstream `AGENTS.md` without overwriting local instructions.
- Document consumer/upstream contribution separation and downstream push safety.
- Require repository preflight and completion validation in packaged agent skills.
- Add regression fixtures for origin-only, multi-remote, explicit upstream, and
  completion containment scenarios.

### Migration considerations

- Existing consumers should regenerate or manually adopt `qmd/collections/wiki.yaml`
  and `qmd/collections/raw.yaml`; the old single `default.yaml` collection is no
  longer generated.
- Run `kb-bootstrap doctor --repo owner/repository` before GitHub mutations.
- Use `kb-bootstrap agents-governance` only when explicitly choosing to manage the
  delimited block in an existing `AGENTS.md`.
- Project-local lessons remain opt-in through `--with-project-lessons`.
