# ADR-041: Distinguish safe reference targets from canonical graph nodes

**Status**: Proposed
**Date**: 2026-10-28
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #234; reverse-engineering #7; ADR-003; ADR-005

## Context

Issue #234 reports that the graph linter rejects links to existing reserved `index.md` and `log.md` files and reports reserved pages as permanent orphans. Reverse-engineering #7 also documents false dead-link failures for links to existing `lessons/SCHEMA.md`. The latter is within the framework issue's explicitly refined scope (comment 6457640826).

ADR-003 excludes reserved files from canonical frontmatter validation and excludes `lessons/` from canonical graph traversal. Exclusion from canonical nodes does not imply that a file cannot be a safe Markdown link destination. The current graph linter conflates safe path existence with eligibility as a graph node: reserved files are traversed but excluded from `eligible_targets`; lesson files are excluded from traversal. The distinction must preserve fail-closed path safety and avoid turning lesson content into canonical nodes or recursively reading it.

ADR-005 defines a separate versioned exporter contract and its own edge/node boundary. This proposal changes no exporter schema, exporter semantics, or ADR-005 contract. It also does not change canonical profile validation.

## Decision

If separately accepted, revise only graph-linter link-target classification so a safe existing Markdown file may be a reference destination without becoming a canonical graph node. Canonical graph nodes and safe reference targets remain distinct classes.

- Eligible canonical Markdown files remain graph nodes and the only files whose content is read as graph sources.
- Reserved `index.md` and `log.md` files, case-insensitively at any directory depth, may be safe link destinations if they exist as regular, non-symlink files within the canonical root. A link to one does not make it a canonical node or graph orphan.
- A Markdown file under an excluded case-insensitive `lessons/` directory may be a safe destination if its explicit path resolves to an existing regular, non-symlink file within the root. The compatibility fixture is `lessons/SCHEMA.md`. Lesson files are not traversed/read for content, are not graph nodes, and provide no outgoing edges.
- Missing targets, unsafe/escaping paths, symlink traversal, unreadable eligible source files, and other unsafe targets remain failures. A safe reference destination is not a general exemption from safety or existence checks.
- Existing valid links are preserved. Validation remains read-only: no link/content removal, rewrite, or repair.
- Diagnostics/report sections remain stable except these links cease to be dead and reserved files cease to be graph orphans. No public report format is added.

This bounded compatibility correction does not change canonical concepts, lessons policy/schema, recursive lesson inspection, general Markdown parsing, QMD, canonical profile checks, or exporter behavior. Any exporter change requires demonstrated failure in an existing ADR-005 test and a separately scoped decision; none is proposed here.

## Alternatives considered

### Treat every existing Markdown file as a canonical graph node

Rejected: this would expand graph source traversal into excluded lessons and reserved files, broadly change topology/orphans, and erase ADR-003's canonical boundary.

### Require authors to remove valid links

Rejected: safe existing destinations would remain incorrectly reported as dead.

### Read lesson files to validate their links or schema

Rejected: only explicit target existence/safety is needed; reading excluded content expands scope without need.

### Weaken missing-target or path-safety failures

Rejected: missing and unsafe paths remain fatal; only classification of existing safe references changes.

### Change the canonical exporter

Rejected: ADR-005 has a separate contract and no exporter failure is established here.

## Consequences

### What gets easier

Canonical documents can link to existing reserved indexes and the lesson schema reference without false dead-link failures; reserved pages do not generate structural orphan noise.

### What gets harder

The linter must preserve a narrow distinction between canonical nodes and safe existing destinations while retaining path checks; tests must verify excluded content is not read as a graph source.

### What does not change

Canonical node membership, profile rules, lesson schema, safe-link syntax, graph source traversal, missing/unsafe failures, link contents, CLI, and ADR-005 exporter schema/behavior.

## Proposed test contract

Tests are proposed only; this ADR-preparation change does not implement them.

| Claim if accepted and implemented | Synthetic test | Currently |
|---|---|---|
| Existing reserved `index.md` is a safe reference, not a canonical node or orphan | `tests/test_graph_linter.py::test_existing_reserved_index_is_safe_reference_not_orphan` | not yet written |
| Existing `lessons/SCHEMA.md` is safe; lesson content is not read or added as a node | `tests/test_graph_linter.py::test_existing_lesson_schema_is_safe_reference_without_traversal` | not yet written |
| Missing reserved or lesson target remains a dead-link failure | `tests/test_graph_linter.py::test_missing_excluded_reference_target_remains_dead` | not yet written |
| Unsafe traversal and symlink targets remain fatal | `tests/test_graph_linter.py::test_unsafe_excluded_reference_targets_remain_dead` | existing coverage to verify/extend only if needed |
| Canonical links remain untouched; repository suite remains green | focused graph and full unittest suites | not yet verified |
| Exporter remains as defined in ADR-005 | existing exporter tests | not yet verified |

## Rollback

Before acceptance, withdraw this proposal without runtime effect. If later implemented and reverted, restore prior link classification only. No consumer content has been changed; no migration or link repair is needed.

## References

- Issue #234 and scope refinement: https://github.com/ozand/kb-bootstrap/issues/234#issuecomment-6457640826
- Reverse-engineering #7: https://github.com/ozand/reverse-engineering/issues/7
- Research context #5: https://github.com/ozand/reverse-engineering/issues/5
- ADR-003; ADR-005; `kb_bootstrap/graph_linter.py`; `tests/test_graph_linter.py`
