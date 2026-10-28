# ADR-041: Distinguish safe reference targets from canonical graph nodes

**Status**: Proposed
**Date**: 2026-10-28
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #234; reverse-engineering #7; ADR-003; ADR-005

## Context

Issue #234 reports that the graph linter rejects links to existing reserved `index.md` and `log.md` files and reports reserved pages as permanent orphans. Reverse-engineering #7 also documents false dead-link failures for links to existing `lessons/SCHEMA.md`. The latter is within the framework issue's explicitly refined scope (comment 6457640826).

ADR-003 excludes reserved files from canonical frontmatter validation and excludes `lessons/` from canonical graph traversal. Exclusion from canonical nodes does not imply that a file cannot be a safe Markdown link destination. In the current graph linter, reserved Markdown files are already included in graph-node enumeration and are read as graph sources, including validation of their outgoing links; they are excluded only from `eligible_targets`. Lesson files are excluded from graph traversal and source enumeration. The correction must preserve both existing enumeration and source checks, while distinguishing safe existing destinations from canonical graph nodes and avoiding recursive lesson reads.

ADR-005 defines a separate versioned exporter contract and its own edge/node boundary. This proposal changes no exporter schema, exporter semantics, or ADR-005 contract. It also does not change canonical profile validation.

## Decision

If separately accepted, revise only graph-linter link-target classification so a safe existing Markdown file may be a reference destination without becoming a canonical graph node. Canonical graph nodes and safe reference targets remain distinct classes.

- Preserve existing graph node/source enumeration: every Markdown file currently enumerated remains a graph node and its outgoing links continue to be checked, including reserved `index.md` and `log.md` files at any depth. Eligible canonical Markdown files remain graph nodes and sources as before; no file is removed from the existing node/source set.
- Reserved `index.md` and `log.md` files, case-insensitively at any directory depth, remain nodes and may be safe link destinations if they exist as regular, non-symlink files within the canonical root. Valid incoming links are graph edges and count toward the existing incoming-link/orphan calculation. Their outgoing content remains checked as before; an invalid outgoing link from a reserved source remains a failure.
- A Markdown file under an excluded case-insensitive `lessons/` directory may be a safe destination if its explicit path resolves to an existing regular, non-symlink file within the root. The compatibility fixture is `lessons/SCHEMA.md`. Lesson files remain excluded from traversal, source enumeration, and graph nodes and provide no outgoing edges; only the explicit destination path is checked for existence and safety.
- Missing targets, unsafe/escaping paths, symlink traversal, unreadable eligible source files, and other unsafe targets remain failures. A safe reference destination is not a general exemption from safety or existence checks.
- Existing valid links are preserved. Validation remains read-only: no link/content removal, rewrite, or repair.
- Diagnostics/report sections and node enumeration remain stable; only a valid incoming link to an existing reserved node ceases to be dead and then contributes its ordinary incoming edge, potentially resolving that node's orphan status. Reserved nodes without valid incoming edges retain existing orphan behavior. Lesson targets are safe destinations but not graph nodes or edges, so they do not affect orphan counts. No public report format is added.

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

Canonical documents can link to existing reserved indexes and the lesson schema reference without false dead-link failures. Reserved pages remain nodes and sources; valid incoming links affect orphan status through the existing edge calculation, while reserved pages with no incoming links remain orphans.

### What gets harder

The linter must preserve a narrow distinction between canonical nodes and safe existing destinations while retaining path checks; tests must verify excluded content is not read as a graph source.

### What does not change

Canonical node membership, profile rules, lesson schema, safe-link syntax, graph source traversal, missing/unsafe failures, link contents, CLI, and ADR-005 exporter schema/behavior.

## Proposed test contract

Tests are proposed only; this ADR-preparation change does not implement them.

| Claim if accepted and implemented | Synthetic test | Currently |
|---|---|---|
| Existing reserved `index.md` remains a node/source; a valid incoming link is an edge and avoids dead-link failure without changing node count | `tests/test_graph_linter.py::test_existing_reserved_index_is_safe_reference_and_preserves_node` | not yet written |
| Invalid outgoing links from reserved `index.md` and `log.md` sources remain failures; their node/source enumeration is unchanged | `tests/test_graph_linter.py::test_reserved_sources_still_fail_on_invalid_outgoing_links` | not yet written |
| Existing `lessons/SCHEMA.md` is a safe destination; lesson content is not read or added as a node, and node count is unchanged | `tests/test_graph_linter.py::test_existing_lesson_schema_is_safe_reference_without_traversal` | not yet written |
| Missing reserved or lesson target remains a dead-link failure | `tests/test_graph_linter.py::test_missing_excluded_reference_target_remains_dead` | not yet written |
| Unsafe traversal and symlink targets remain fatal | `tests/test_graph_linter.py::test_unsafe_excluded_reference_targets_remain_dead` | existing coverage to verify/extend only if needed |
| Existing orphan semantics are retained: reserved nodes without valid incoming edges remain orphans; valid incoming links contribute ordinary edges | focused reserved-target graph tests | not yet written |
| Canonical links remain untouched; repository suite remains green | focused graph and full unittest suites | not yet verified |
| Exporter output and ADR-005 behavior remain unchanged | existing exporter tests, including node/edge compatibility | not yet verified |

## Rollback

Before acceptance, withdraw this proposal without runtime effect. If later implemented and reverted, restore prior link classification only. No consumer content has been changed; no migration or link repair is needed.

## References

- Issue #234 and scope refinement: https://github.com/ozand/kb-bootstrap/issues/234#issuecomment-6457640826
- Reverse-engineering #7: https://github.com/ozand/reverse-engineering/issues/7
- Research context #5: https://github.com/ozand/reverse-engineering/issues/5
- ADR-003; ADR-005; `kb_bootstrap/graph_linter.py`; `tests/test_graph_linter.py`
