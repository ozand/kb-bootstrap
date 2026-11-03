# ADR-053: Search one explicitly selected configured lesson store as bounded Markdown

**Status**: Accepted
**Date**: 2026-11-06
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #268; Issue #127; ADR-017, ADR-018, ADR-026; `docs/LESSON_ROUTING_POLICY.md`; `docs/LESSON_LOOKUP_BUNDLE.md`

Technical acceptance: authorized under owner delegation. Independent review `independent9b57` returned PASS for exact proposed revision `ddc1f995aad93a790577bd2034537bbfc52b8520`. This acceptance changes lifecycle status only; it does not implement the command or authorize publication.

## Context

Issue #268 identifies a gap: generated lesson lookup guidance names configured stores, but the reusable CLI has no bounded path that searches the configured Markdown files themselves. Read-only source inspection on fresh `main` (`a29ec90bb77f591e14119bb1715b441fec3162c4`) verified that `lesson-lookup` consumes an explicit JSON lookup bundle of exported records, while ADR-017 `search-local` excludes `lessons` at the root and below it. `kb_bootstrap/local_retrieval.py` implements the same `SKIP_DIRS` exclusion. The issue's description of the gap is therefore confirmed.

The routing policy requires explicit deterministic configuration, local-before-shared lookup, shared read-only status, sanitized unavailable outcomes, and no background discovery or writes. Generated `lesson-stores.json` currently demonstrates `local.path`; the JSON lookup bundle is a different contract. Directory search must not reinterpret that bundle, infer a store, or relax canonical retrieval. The primary use is local CLI guidance from generated `kb-lookup`; selection and source identity must remain visible to the caller without exposing absolute paths or unbounded lesson content.

This is an accepted design contract, not yet an implementation, security guarantee, or evidence from any consumer corpus. The research checkpoint is retained on Issue #268. No private consumer store was accessed.

## Decision

Add a separately named opt-in command, `kb-bootstrap search-lessons <query> --project-root <root> --store <name> [--limit N]`. It searches exactly one explicitly named entry in `lesson-stores.json`; the selector does not cause enumeration or fallback. Generated `kb-lookup` guidance orchestrates configured local-first/shared-second lookup as described below. A caller may invoke one store explicitly without implying the other is selected.

Require a valid version-1 object and a unique, valid selected `local` or `shared` entry. `local.path` is interpreted relative to the directory containing `lesson-stores.json` and must resolve within the explicit project root. Existing routing examples do not define a distinct base for relative shared paths; this proposal explicitly defines a relative `shared.path` against the same configuration directory, while an absolute shared path is used only when that exact path is configured. Shared search is permitted only when `read_only: true`. No home, environment, sibling, Git-remote, or conventional-root discovery is allowed. This is an explicit path-resolution choice for the proposed command, not a claim that prior guidance already specified the base. A project-local store is complete only when its configured directory, `SCHEMA.md`, and `index.yaml` are present, regular, bounded, readable, and safe, as required by generated `kb-lookup`. A shared registry is complete when its configured registry root, `index.yaml`, and `lessons/` directory are present and safe, matching `lesson_registry.py`; do not require shared `SCHEMA.md`. Missing/malformed/ambiguous config, missing contract files, invalid or inconsistent index data, or an unavailable selected store returns a sanitized unavailable/blocked result, never a no-match. Do not expose paths, parser/OS diagnostics, or lesson text in blocked diagnostics.

Respect the two existing index layouts rather than inventing a common schema. For a project-local store, require `version: 1`, `scope: project`, a valid `id_prefix` matching `[A-Za-z][A-Za-z0-9_-]*-`, a `lessons` list, unique IDs matching that prefix plus four digits, and repository-root-relative `path` entries whose normalized files remain within the configured lessons directory; each entry ID must match filename ID and frontmatter `id`. These are the invariants in `project_lesson_registry.py`, with its documented `SCHEMA.md` exclusion. For a shared store, follow `lesson_registry.py`: `index.yaml` at registry root has `count` and `lessons`; entries use unique `KB-XXXX` IDs and `file: lessons/KB-XXXX-...md`; each listed file and frontmatter ID must agree, and `count` must equal both entry and discovered valid lesson-file counts. That validator reads but does not constrain an index `version` field, so do not require one. Do not require extra scope or metadata keys not checked by that validator.

For a project store, `SCHEMA.md` remains required by existing lookup guidance, but its prose is not parsed as authority. Shared registry validation does not require `SCHEMA.md`. Parse only the selected index, using existing PyYAML support with a 1 MiB cap, at most 1,000 entries, aliases disabled, duplicate keys rejected, and parser bounds of 10,000 nodes and 32 nested collections. These stricter search-reader parser rules are explicit input constraints for this command; they do not claim the current validators reject aliases or duplicate keys. Parse JSON `lesson-stores.json` with duplicate object keys rejected as well. Malformed or over-budget inputs are unavailable. Validate indexed IDs/paths, containment, file identity, frontmatter ID, and complete index-to-file correspondence before exposing results. Match the existing validator inventories: project stores inspect direct `*.md` entries except `SCHEMA.md`; shared stores inspect direct `lessons/*.md`. Invalid or unindexed filename-defined lesson candidates make the selected store unavailable, never silently omitted or searched. Do not recursively discover or open files referenced by arbitrary metadata. Do not expose results until the bounded index and complete direct-file inventory validate.

Resolve selected paths without traversal or aliases; reject symlink/junction/reparse components, outside paths, malformed references, and nonregular files without following them. Inventory only the contract's direct lesson directory (no recursive discovery). Use stable sorted path ordering. Search UTF-8 Markdown body text only. Lesson files must have valid YAML frontmatter under the existing registry contract: require a closing delimiter within a fixed bounded header budget, exclude the entire frontmatter block from matching and result text, and treat missing/malformed/over-budget frontmatter as an unavailable store. Reject duplicate frontmatter keys and aliases rather than trusting parser last-key-wins or alias behavior. Validate `id` against filename/index; do not require or semantically inspect non-ID metadata fields. This follows the existing filename/frontmatter ID invariant without expanding the lesson schema and prevents metadata/signature canaries from being returned. Use literal Unicode casefold substring matching line by line and return at most the first matching body line per file. Results contain store name, lesson ID and bounded store-relative path plus a bounded matching body-line excerpt; no absolute paths, frontmatter, full documents, or arbitrary diagnostics are emitted. Results are navigation hints, not verified knowledge or approval.

Use fixed ceilings: 64 KiB configuration, 64 KiB project `SCHEMA.md`, 1 MiB index, 1,000 index entries/files, 10,000 direct-directory entries, 1 MiB actual bytes read per Markdown file, 16 MiB aggregate source bytes read (configuration, schema when applicable, index, and Markdown together), 512 UTF-8 bytes per query, 100 results, 512 UTF-8 bytes per excerpt, and 256 KiB serialized output. Each frontmatter block is limited to 8 KiB and 256 lines. Bound parser work to the node/depth limits above. Account actual bytes read, not unique files: every validation/header/body read counts toward per-file and aggregate budgets, including repeated reads; preferably retain a bounded invocation-owned snapshot to avoid duplicate reads. Configuration, schema, and index bytes count each time read as well. On any ceiling reached before complete validation/search, return `PARTIAL`, never a complete no-match. Unsafe paths, unreadable content, invalid UTF-8, or invalid store/index state return no lesson results. Cover each hard limit at boundary and one-over in synthetic tests. As ADR-017 states for canonical retrieval, this is not a concurrent or hostile-writer-safe filesystem snapshot; no stronger race-free guarantee is claimed.

The generated `kb-lookup` flow must use the new command on local first. Search shared only if the local operation returns a **complete no-match** and an explicitly configured shared store is read-only. A local match ends lookup; local `PARTIAL`, `BLOCKED`, or unavailable prevents shared fallback and is reported distinctly, since those outcomes do not establish no local match. If local is not configured, follow the existing policy's explicit shared-only route. A shared unavailable/partial outcome remains distinct from a complete no-match. This preserves the routing policy's complete-local-first, explicit-shared fallback and unavailable-source distinction; never reinterpret incomplete work as an empty result.

This is a separate path from `lesson-lookup`, which continues to consume an explicit JSON export bundle. The command performs no QMD invocation, collection/index lookup or mutation, network access, model/inference work, capture, writes, migration, promotion, synchronization, or background discovery. No new dependency is proposed. ADR-017 `search-local` and its canonical `SKIP_DIRS` remain unchanged.

This accepted contract requires explicit single-store command selection and complete-result fallback semantics; implementation must retain the distinct project/shared index schemas, exclude all frontmatter from content search/output, and reject index-incomplete stores rather than silently widening eligible files.

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

| Claim of this accepted contract if implemented | Synthetic test | Currently |
|---|---|---|
| Only the explicitly selected configured store is searched; local/shared config errors and shared read-only requirements fail closed | `tests/test_lesson_search.py::test_explicit_store_selection_and_configuration_fail_closed` | not yet written |
| Project/shared index schemas enforce their existing ID, path, frontmatter, count (shared only), and complete direct-file correspondence invariants without undocumented required fields or an unsupported shared version requirement | `tests/test_lesson_search.py::test_project_and_shared_registry_contracts` | not yet written |
| Duplicate JSON/index/frontmatter keys, YAML aliases, and oversized/deep parser inputs fail closed | `tests/test_lesson_search.py::test_duplicate_keys_aliases_and_parser_bounds` | not yet written |
| Project store requires its documented `SCHEMA.md`; shared store follows its validator-required root/index/lessons shape without a new `SCHEMA.md` or `version` requirement | `tests/test_lesson_search.py::test_project_and_shared_required_files` | not yet written |
| The selected store requires bounded valid `index.yaml` and complete index/file correspondence; malformed, oversized, or incomplete state is unavailable | `tests/test_lesson_search.py::test_store_contract_and_index_completeness` | not yet written |
| Only indexed eligible lessons are considered; unindexed lesson-shaped Markdown cannot become an unnoticed result | `tests/test_lesson_search.py::test_unindexed_lesson_blocks_store` | not yet written |
| Matching and non-matching Markdown body text work; frontmatter canary values neither match nor appear in excerpts | `tests/test_lesson_search.py::test_frontmatter_is_never_searched_or_returned` | not yet written |
| Traversal, escaping paths, symlink/junction/reparse components and invalid roots fail closed without outside reads | `tests/test_lesson_search.py::test_rejects_traversal_and_symlink_escape` | not yet written |
| Every entry, index, file, byte, query, result and output budget is enforced; over-budget results are partial, not complete | `tests/test_lesson_search.py::test_budgets_report_partial_not_complete` | not yet written |
| Relative shared paths resolve from the `lesson-stores.json` directory; local-to-shared fallback occurs only after complete local no-match; local partial/unavailable/match prevents fallback; shared-only requires explicit read-only configuration | `tests/test_lesson_search.py::test_fallback_requires_complete_local_no_match` | not yet written |
| `search-local` still excludes lesson roots/descendants and existing `lesson-lookup` still reads only its bundle | `tests/test_local_retrieval.py::test_search_local_excludes_lessons` and `tests/test_federated_lookup.py::test_lookup_bundle_contract_unchanged` | existing tests to verify; no implementation change proposed |
| Generated lookup guidance states the command and distinguishes complete no-match from partial/unavailable before shared fallback; JSON bundle lookup remains distinct | `tests/test_skill_templates.py::test_kb_lookup_documents_lesson_search_boundary` | not yet written |

Use synthetic invocation-owned fixtures only. Include separate project/shared fixtures; missing/extra entries, mismatched filename/frontmatter/index IDs, invalid filename-defined candidate files, project `scope`/`id_prefix` failures, shared count drift, and valid minimal fixtures proving no undocumented fields are required. Include duplicate JSON/YAML keys and alias cases, `error_signatures`/`title` frontmatter canaries plus body match/no-match controls, indexed/unindexed file pairs, relative shared-path resolution, and exact-limit/one-over cases that count repeated validation/body reads. These proposed tests are falsifiable planning targets, not existing tests or implementation evidence.

## Rollback

If a future implementation is reverted, remove only the additive command and its generated guidance/tests. No index, persisted state, or consumer data migration is introduced; canonical search and JSON bundle lookup remain available unchanged.

## References

- GitHub Issue #268 and its pre-edit research checkpoint: https://github.com/ozand/kb-bootstrap/issues/268#issuecomment-6580606830
- Accepted ADR-017: `docs/adr/ADR-017-add-bounded-local-search-and-read-commands.md`
- `kb_bootstrap/local_retrieval.py` (`SKIP_DIRS` and bounded canonical local retrieval)
- `docs/LESSON_ROUTING_POLICY.md`
- `docs/LESSON_LOOKUP_BUNDLE.md`
- `kb_bootstrap/templates/lessons/lesson-stores.json`
- `kb_bootstrap/templates/skills/kb-lookup/SKILL.md` (complete-local-no-match fallback and required store files)
- `kb_bootstrap/project_lesson_registry.py` (project-local index/file/frontmatter invariants)
- `kb_bootstrap/lesson_registry.py` (shared index/file/frontmatter/count invariants)
- `kb_bootstrap/cli.py` (`lesson-lookup` command and dispatch)
