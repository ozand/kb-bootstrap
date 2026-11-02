# ADR-053: Search one explicitly selected configured lesson store as bounded Markdown

**Status**: Proposed
**Date**: 2026-11-06
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #268; Issue #127; ADR-017, ADR-018, ADR-026; `docs/LESSON_ROUTING_POLICY.md`; `docs/LESSON_LOOKUP_BUNDLE.md`

## Context

Issue #268 identifies a gap: generated lesson lookup guidance names configured stores, but the reusable CLI has no bounded path that searches the configured Markdown files themselves. Read-only source inspection on fresh `main` (`a29ec90bb77f591e14119bb1715b441fec3162c4`) verified that `lesson-lookup` consumes an explicit JSON lookup bundle of exported records, while ADR-017 `search-local` excludes `lessons` at the root and below it. `kb_bootstrap/local_retrieval.py` implements the same `SKIP_DIRS` exclusion. The issue's description of the gap is therefore confirmed.

The routing policy requires explicit deterministic configuration, local-before-shared lookup, shared read-only status, sanitized unavailable outcomes, and no background discovery or writes. Generated `lesson-stores.json` currently demonstrates `local.path`; the JSON lookup bundle is a different contract. Directory search must not reinterpret that bundle, infer a store, or relax canonical retrieval. The primary use is local CLI guidance from generated `kb-lookup`; selection and source identity must remain visible to the caller without exposing absolute paths or unbounded lesson content.

This is a design proposal only. It is not an accepted contract, implementation, security guarantee, or evidence from any consumer corpus. The research checkpoint is retained on Issue #268. No private consumer store was accessed.

## Decision

If accepted, add a separately named opt-in command, `kb-bootstrap search-lessons <query> --project-root <root> --store <name> [--limit N]`. The command reads the generated `lesson-stores.json` under the explicitly supplied project root and resolves exactly one named `local` or `shared` entry. `--store` is required: no default, fallback, store enumeration, or automatic selection. The local store may be selected only when its configured path is present and valid. A shared store may be selected only when explicitly configured with `read_only: true`; it remains read-only. Missing/malformed/ambiguous configuration, unknown names, writable shared entries, or unavailable stores block with a closed-category reason. Do not echo raw paths or parser/OS diagnostics.

Resolve the selected store path from its explicit configuration. Permit a normalized relative path contained beneath the project root or an absolute path explicitly written in the selected shared-store configuration; never derive or search sibling, parent, home, environment, or conventional roots. Canonicalize and verify the configured directory before reading. Reject traversal, path aliases, symlink/junction/reparse components, and escapes; do not follow them. The command is read-only and makes no concurrent/hostile-writer snapshot guarantee.

Traverse only regular `.md` files within that selected store, with stable sorted depth-first ordering. Exclude hidden entries and `index.md`/`log.md` as navigation metadata; unlike canonical search, the selected lesson store's own root is allowed to be named `lessons`. Never pass it to `search-local`, never remove or weaken ADR-017 `SKIP_DIRS`, and never change existing search/read/lesson-lookup behavior.

Use literal Unicode casefold substring matching, line-by-line, with the first matching line per file. Default result limit 10, maximum 100. Fix hard ceilings in the contract: 10,000 directory entries examined, 1,000 eligible Markdown files, 1 MiB per file, 16 MiB total file bytes, 512 UTF-8 bytes per query, 512 bytes per result text field, and 256 KiB serialized JSON output. When an eligible tree remains but any scan/result/output ceiling is hit, return `PARTIAL`, `complete: false`, and a closed-category `limiting_budget`; never claim complete/no-match. Unsafe/unreadable paths or invalid UTF-8 block without returning source excerpts. Use only relative store paths in results; do not emit absolute roots, full documents, arbitrary frontmatter, or arbitrary diagnostics. Emit at most one bounded matching-line excerpt per result as navigation text, not verified knowledge or approval.

The command performs no QMD invocation, collection/index lookup or mutation, network access, model/inference work, capture, writes, migration, promotion, synchronization, or background discovery. It does not consume the JSON export bundle used by `lesson-lookup`. Generated `kb-lookup` guidance may invoke it only when the user has an explicit configured store and query; retain the current bundle-based `lesson-lookup` route as a distinct path. No new dependency is proposed.

This proposal selects the explicit `--store` UX and these fixed ceilings to make the outcome independently testable while preserving current boundaries. Any implementation must follow this exact accepted contract or return for a separately scoped design decision.

## Alternatives Considered

### Reuse `search-local` by allowing a lessons root

Rejected because ADR-017's canonical selection deliberately excludes lesson paths; broadening it would change an accepted search contract and blur canonical knowledge with error lessons.

### Extend `lesson-lookup` to read configured directories

Rejected because that command has an explicit JSON export-bundle contract and existing callers; changing its input/storage semantics would be incompatible and conflate bundles with source stores.

### Discover configured or conventional stores automatically

Rejected because lookup policy requires explicit deterministic configuration and background discovery is out of scope. Requiring one named store prevents ambiguity and makes the selected trust/data boundary legible.

### Add QMD or indexed/semantic lesson search

Rejected because it adds index state, optional tooling/model/network surfaces, and a larger contract where bounded local text search is sufficient.

## Consequences

### What gets easier

- A caller can perform explicit bounded literal lookup over configured Markdown lessons without routing lesson paths through canonical search or exporting a JSON bundle first.
- Generated guidance can point to a single observable command and source-selection boundary.

### What gets harder

- Configuration validation, filesystem containment, symlink handling, deterministic limits, and honest partial-result reporting create a separate CLI and test surface.
- Search is literal and bounded; large stores may produce partial results and require narrower store/user action rather than implying exhaustive coverage.

### What does not change

- ADR-017 search-local/read-local behavior, including the canonical `SKIP_DIRS` and all path, traversal, and output rules, remains unchanged.
- `lesson-lookup` remains an explicit JSON export-bundle lookup. Lesson capture ownership, routing, generated schemas, stores, and consumer data remain unchanged.
- No private stores, QMD collections, models, networks, indexes, writes, migrations, synchronization, or promotion are added.

## Test Contract

| Claim if accepted and implemented | Synthetic test | Currently |
|---|---|---|
| Only the explicitly named configured local or read-only shared store is selected; malformed, ambiguous, missing, unknown, or writable shared configuration blocks | `tests/test_lesson_search.py::test_explicit_store_selection_and_configuration_fail_closed` | not yet written |
| Literal matching finds eligible Markdown and does not return nonmatching, hidden, metadata, or non-Markdown files | `tests/test_lesson_search.py::test_matches_only_eligible_markdown` | not yet written |
| Traversal, escaping paths, symlink/junction/reparse components and invalid roots fail closed without outside reads | `tests/test_lesson_search.py::test_rejects_traversal_and_symlink_escape` | not yet written |
| Entry/file/per-file/aggregate-byte/result/output limits are enforced and disclose partial outcomes without claiming completeness | `tests/test_lesson_search.py::test_budgets_report_partial_not_complete` | not yet written |
| Unsafe file/invalid UTF-8 results do not emit lesson text or absolute paths | `tests/test_lesson_search.py::test_blocked_results_are_sanitized` | not yet written |
| `search-local` still excludes lesson roots/descendants and existing `lesson-lookup` still reads only its bundle | `tests/test_local_retrieval.py::test_search_local_excludes_lessons` and `tests/test_federated_lookup.py::test_lookup_bundle_contract_unchanged` | existing tests to verify; no implementation change proposed |
| Generated `kb-lookup` guidance names the accepted Markdown command and distinguishes JSON bundle lookup | `tests/test_skill_templates.py::test_kb_lookup_documents_lesson_search_boundary` | not yet written |

Tests use invocation-owned synthetic directory fixtures only. These proposed test names are planning targets, not existing tests or implementation evidence.

## Rollback

If accepted and implemented, remove only the additive command and its generated guidance/tests. No index, persisted state, or consumer data migration is introduced; canonical search and JSON bundle lookup remain available unchanged.

## References

- GitHub Issue #268 and its pre-edit research checkpoint: https://github.com/ozand/kb-bootstrap/issues/268#issuecomment-6580606830
- Accepted ADR-017: `docs/adr/ADR-017-add-bounded-local-search-and-read-commands.md`
- `kb_bootstrap/local_retrieval.py` (`SKIP_DIRS` and bounded canonical local retrieval)
- `docs/LESSON_ROUTING_POLICY.md`
- `docs/LESSON_LOOKUP_BUNDLE.md`
- `kb_bootstrap/templates/lessons/lesson-stores.json`
- `kb_bootstrap/cli.py` (`lesson-lookup` command and dispatch)
