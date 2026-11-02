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

If accepted, add a separately named opt-in command, `kb-bootstrap search-lessons <query> --project-root <root> --store <name> [--limit N]`. It searches exactly one explicitly named entry in `lesson-stores.json`; the selector does not cause enumeration or fallback. Generated `kb-lookup` guidance orchestrates configured local-first/shared-second lookup as described below. A caller may invoke one store explicitly without implying the other is selected.

Require a valid version-1 object and a unique, valid selected `local` or `shared` entry. `local.path` must resolve to a project-contained directory. `shared.path` must resolve exactly as configured, and search is permitted only when `read_only: true`; no home, environment, sibling, Git-remote, or conventional-root discovery is allowed. The selected store is complete only when its configured directory, `SCHEMA.md`, and `index.yaml` are present, regular, bounded, readable, and safe. Missing/malformed/ambiguous config, missing contract files, invalid or inconsistent index data, or an unavailable selected store returns a sanitized unavailable/blocked result, never a no-match. Do not expose paths, parser/OS diagnostics, or lesson text in blocked diagnostics.

Respect the two existing index layouts rather than inventing a common schema: project-local `index.yaml` is in the configured lessons directory, uses its configured `id_prefix`, and stores repository-root-relative `path` entries (as validated by `project_lesson_registry.py`); shared `index.yaml` is in the configured registry root, includes the existing `version`, `count`, and `lessons` contract, and points to `lessons/<filename>` entries (as validated by `lesson_registry.py`). `SCHEMA.md` is required as the existing lookup guidance requires, but its prose is not parsed as authority. Parse the selected index only, using existing PyYAML support with a 1 MiB index-byte cap, at most 1,000 entries, aliases disabled, duplicate keys rejected, and parser bounds of 10,000 nodes and 32 nested collections; malformed or over-budget indexes are unavailable. Validate every indexed ID/path, containment, file identity, and full index-to-file correspondence before searching. Search only regular `.md` entries explicitly listed by the index. A lesson-shaped eligible Markdown file in the configured lesson directory that is unindexed makes the store invalid/unavailable; it is not silently included or ignored. Ignore `SCHEMA.md` as documentation, not a lesson. Do not recursively discover or open files referenced by arbitrary metadata. The search must not read a candidate lesson body until the bounded index and directory inventory establish a complete valid selection.

Resolve selected paths without traversal or aliases; reject symlink/junction/reparse components, outside paths, malformed references, and nonregular files without following them. Inventory only the contract's direct lesson directory (no recursive discovery). Use stable sorted path ordering. Search UTF-8 Markdown body text only: when a file begins with YAML frontmatter, require its closing delimiter within a fixed bounded header budget, exclude the entire frontmatter block from matching and result text, and treat missing/malformed/over-budget frontmatter as an unavailable store. Files without an opening frontmatter delimiter are searched as Markdown body. This explicitly prevents metadata/signature canaries from being returned as matches or excerpts. Use literal Unicode casefold substring matching line by line and return at most the first matching body line per file. Results contain store name, lesson ID and bounded store-relative path plus a bounded matching body-line excerpt; no absolute paths, frontmatter, full documents, or arbitrary diagnostics are emitted. Results are navigation hints, not verified knowledge or approval.

Use fixed ceilings: 64 KiB configuration, 64 KiB `SCHEMA.md`, 1 MiB index, 1,000 index entries/files, 10,000 direct-directory entries, 1 MiB per Markdown file, 16 MiB aggregate Markdown bytes, 512 UTF-8 bytes per query, 100 results, 512 UTF-8 bytes per excerpt, and 256 KiB serialized output. Each frontmatter block is limited to 8 KiB and 256 lines. Bound parser work to the node/depth limits above. On any scan/result/output ceiling reached before complete validation/search, return an explicit `PARTIAL` result with `complete: false` and a closed-category `limiting_budget`; never report a complete no-match. A non-match is complete only after the entire selected store passes validation and search. Unsafe paths, unreadable content, invalid UTF-8, or invalid store/index state return no lesson results. Hard limits must be named constants and covered at boundary and one-over synthetic cases before implementation.

The generated `kb-lookup` flow must use the new command on local first. Search shared only if the local operation returns a **complete no-match** and an explicitly configured shared store is read-only. A local match ends lookup; local `PARTIAL`, `BLOCKED`, or unavailable prevents shared fallback and is reported distinctly, since those outcomes do not establish no local match. If local is not configured, follow the existing policy's explicit shared-only route. A shared unavailable/partial outcome remains distinct from a complete no-match. This preserves the routing policy's complete-local-first, explicit-shared fallback and unavailable-source distinction; never reinterpret incomplete work as an empty result.

This is a separate path from `lesson-lookup`, which continues to consume an explicit JSON export bundle. The command performs no QMD invocation, collection/index lookup or mutation, network access, model/inference work, capture, writes, migration, promotion, synchronization, or background discovery. No new dependency is proposed. ADR-017 `search-local` and its canonical `SKIP_DIRS` remain unchanged.

This proposal chooses explicit single-store command selection and complete-result fallback semantics; the accepted contract must retain the distinct project/shared index schemas, exclude all frontmatter from content search/output, and reject index-incomplete stores rather than silently widening eligible files.

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
| Only the explicitly selected configured store is searched; local/shared config errors and shared read-only requirements fail closed | `tests/test_lesson_search.py::test_explicit_store_selection_and_configuration_fail_closed` | not yet written |
| The selected store requires its configured directory, `SCHEMA.md`, bounded valid `index.yaml`, and complete index/file correspondence; malformed, duplicate, oversized, or incomplete index state is unavailable | `tests/test_lesson_search.py::test_store_contract_and_index_completeness` | not yet written |
| Only indexed eligible lessons are considered; unindexed lesson-shaped Markdown cannot become an unnoticed result | `tests/test_lesson_search.py::test_unindexed_lesson_blocks_store` | not yet written |
| Matching and non-matching Markdown body text work; frontmatter canary values neither match nor appear in excerpts | `tests/test_lesson_search.py::test_frontmatter_is_never_searched_or_returned` | not yet written |
| Traversal, escaping paths, symlink/junction/reparse components and invalid roots fail closed without outside reads | `tests/test_lesson_search.py::test_rejects_traversal_and_symlink_escape` | not yet written |
| Every entry, index, file, byte, query, result and output budget is enforced; over-budget results are partial, not complete | `tests/test_lesson_search.py::test_budgets_report_partial_not_complete` | not yet written |
| Local-to-shared fallback occurs only after complete local no-match; local partial/unavailable/match prevents fallback; shared-only requires explicit read-only configuration | `tests/test_lesson_search.py::test_fallback_requires_complete_local_no_match` | not yet written |
| `search-local` still excludes lesson roots/descendants and existing `lesson-lookup` still reads only its bundle | `tests/test_local_retrieval.py::test_search_local_excludes_lessons` and `tests/test_federated_lookup.py::test_lookup_bundle_contract_unchanged` | existing tests to verify; no implementation change proposed |
| Generated lookup guidance states the command and distinguishes complete no-match from partial/unavailable before shared fallback; JSON bundle lookup remains distinct | `tests/test_skill_templates.py::test_kb_lookup_documents_lesson_search_boundary` | not yet written |

Use synthetic invocation-owned fixtures only. Include canaries in YAML metadata fields such as `error_signatures` and `title`, body match/no-match controls, indexed/unindexed file pairs, and exact-limit/one-over cases for each budget. These proposed tests are falsifiable planning targets, not existing tests or implementation evidence.

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
