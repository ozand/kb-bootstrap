# Changelog

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
