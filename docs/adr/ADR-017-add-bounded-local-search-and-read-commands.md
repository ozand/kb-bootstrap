# ADR-017: Add bounded canonical local search and read commands

**Status**: Proposed
**Date**: 2026-10-03
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #127; ADR-003, ADR-006, ADR-015

## Context

Issue #127 asks for compact discovery separated from reading selected evidence, a usable path without QMD/model/network, bounded outcomes, and no claim that a search hit is verified knowledge. The existing `search` invokes QMD directly; preserving it avoids changing its public semantics. ADR-003 defines canonical exclusions, ADR-006 makes freshness dependent on explicit `--now`, and ADR-015 requires an offline local path without QMD or subprocesses. The QMD adapter reproduction is a separately authorized follow-up; this proposal makes no new QMD claim.

## Decision

Add two additive file-only commands, `search-local` and `read-local`. Both require an explicit `--dir` canonical root; there is no default root, so an omitted scope cannot silently select a corpus. Neither command changes existing `search`, `validate`, generated QMD declarations, or QMD runtime state.

### `search-local`

`kb-bootstrap search-local <query> --dir <canonical-root> [--limit N]` performs literal Unicode `casefold` substring matching in eligible UTF-8 Markdown files. It uses no tokenizer, stemming, semantic model, network, or QMD. Paths are relative POSIX paths; directories use sorted depth-first traversal (directory entries are compared as their names plus `/`, files as their names), and emitted paths follow that deterministic traversal order; within each file, the first matching line is reported. It returns at most `--limit` records (default 10, maximum 100). Query UTF-8 length is at most 512 bytes; query must be non-empty and contain no NUL/control characters.

Each result has exactly `{kb, layer, path, title, match_line, snippet, snippet_truncated, revision, review, freshness}`. `kb` is the explicit root's basename (at most 512 UTF-8 bytes), a display label scoped to this single-root invocation, not a globally unique identity; collisions across invocations imply no shared origin. `layer` is the constant `canonical-selection`, not a profile-validation assertion. `path` is canonical-root-relative; paths over 512 UTF-8 bytes are rejected rather than truncated. `title` is the first usable authored Markdown heading or `unknown`; `match_line` is the 1-based line number of the first matching line; matching is line-by-line and never spans newlines. `snippet` is a UTF-8-safe prefix of that line, at most 512 bytes, and `snippet_truncated` states whether the line was longer; the snippet is only navigation text and need not contain the query. The three context fields are only authored scalar strings at the named top-level keys when present and safely readable, otherwise `unknown`; do not interpret or emit arbitrary YAML mappings/lists or assign ADR-006 freshness semantics. Each emitted text field is bounded to 512 UTF-8 bytes. Output does not include the absolute root or arbitrary surrounding document text. Records are navigation hints, not semantic validation, source verification, approval, or truth claims.

Finite ceilings: at most 1,000 eligible files inspected (including oversized files), 1 MiB per file, 16 MiB total file bytes read, 10,000 directory entries examined (including directories and excluded entries), 100 results, and 256 KiB total serialized JSON output. Entries are processed in the deterministic sorted depth-first order defined above. To bound enumeration without processing an arbitrary prefix, inspect at most the remaining entry budget plus one in a directory; if that reveals overflow, stop with `PARTIAL` and do not process that directory's entries. If any ceiling is reached before the eligible tree is exhausted, return explicit `PARTIAL` with `complete: false` and the limiting budget; never report an empty complete result. If the result limit is reached before exhaustion, return `PARTIAL` (`result_limit`), not a complete result. An oversized eligible file is counted as inspected, not read, and makes the scan partial. Invalid UTF-8 eligible Markdown blocks with a sanitized relative-path category rather than silently skipping content. `--limit` cannot exceed 100; all other ceilings are fixed, not user-configurable.

### `read-local`

`kb-bootstrap read-local <relative-path> --dir <canonical-root> [--max-bytes N]` reads one UTF-8 Markdown file selected beneath the explicit root. The default byte budget is 16 KiB; the hard maximum is 64 KiB. Read at most the requested budget plus three bytes of lookahead to determine whether content remains and to avoid splitting a UTF-8 code point; do not load the full file just to truncate it. Invalid UTF-8 within the returned prefix blocks; bytes beyond the bounded prefix are not validated. Return `{status, path, content, truncated}` with a relative path and bounded content; no section selector is included in this increment. Accept only normalized POSIX relative `.md` paths: reject absolute/drive paths, backslashes, empty or dot/parent components, symlinks, junctions/reparse points, nonregular files, and paths outside the root before content is returned.

### Shared canonical path and output policy

Both commands require a stable, locally controlled canonical root. Reject a root whose own basename is `raw`, `research`, or `lessons` case-insensitively. Exclude hidden directories and files, and any descendant directory named `raw`, `research`, or `lessons` case-insensitively; exclude `index.md` and `log.md` case-insensitively at every depth. This is an intentionally stricter selection policy for the proposed discovery commands, not a claim that ADR-003's profile validator uses identical hidden/research exclusions or that remaining files pass the canonical profile. `read-local` rejects a selected excluded/hidden path. Reject symlinks, junctions, reparse points, unsafe components, and nonregular files without intentionally reading through them. This is not a concurrent/hostile-writer-safe filesystem snapshot.

`search-local` emits `{status, complete, results, limiting_budget}` as required fields; `limiting_budget` is `null` except on budget-limited partial results. A blocked response has no results and may additionally contain one closed-category `reason` and bounded `path`; statuses are `COMPLETE`, `PARTIAL`, or `BLOCKED`. `read-local` emits `{status, path, content, truncated}` as required fields (blocked content is empty) with statuses `COMPLETE`, `TRUNCATED`, or `BLOCKED`; a blocked response may include one bounded closed-category `reason`, never source text. Search and read diagnostics have at most one bounded reason and an optional relative path (at most 512 UTF-8 bytes); no per-file error arrays or source content are emitted. JSON uses UTF-8 without ASCII escaping and total serialized output is capped at 256 KiB including escaping. If search output reaches this cap, return `PARTIAL` with limiting budget `output_bytes` and only complete records that fit. Exit codes are 0 for complete (including zero search hits), 1 for blocked/unavailable, 3 for partial/truncated, and 2 for CLI argument errors. Resource accounting lets callers distinguish no matches from incomplete coverage.

Missing provenance/review metadata is `unknown`; no metadata is synthesized and no clock is read. These commands do not invoke QMD, inspect/update an index, register collections, search raw data, expose a generic capability/adapter registry, rank semantic relevance, verify source truth, follow document links, perform cross-KB discovery, or write files. Existing `search` remains the explicit QMD-backed canonical/raw operation with its current contract.

### Success criteria

An operator can search and then read an explicitly selected canonical document while QMD, models, network, and optional executables are absent. Both commands stay within the explicit root and stated byte/entry/result/output bounds, disclose partial/truncated outcomes, preserve deterministic ordering, and do not mutate the tree. Discovery exclusions are an explicit proposed selection policy, not an assertion of parity with ADR-003 validation or a profile-validation result.

## Consequences

### What gets easier

- Compact local discovery and bounded reading work offline without QMD or a vector index.
- Search output points to evidence without conflating a match with verification.

### What gets harder

- Literal substring matching can miss synonyms and has no relevance ranking.
- Explicit root selection and strict limits can yield blocked or partial results callers must handle.
- UTF-8, path safety, metadata extraction, deterministic enumeration, and resource accounting add implementation and test surface.

### What does not change

- Legacy QMD `search`, QMD declarations/indexing, canonical validation, provenance semantics, and published artifacts remain unchanged.
- Raw/research/lesson access, QMD adapter execution, capability configuration, model acquisition, network access, and generic plugin systems are not added.

## Alternatives Considered

### Keep QMD as the only search path

Rejected because Issue #127 requires a useful local path with QMD absent and no model/network dependency.

### Add a SQLite/vector index or semantic fallback

Rejected because generated index state, dependencies, freshness semantics, and ranking exceed bounded file-only orientation.

### Use tokenized lexical ranking

Rejected because tokenizer, stemming, weighting, tie-breaking, and relevance semantics create a larger public contract. Literal matching is deterministic and testable.

### Default `--dir` to `kb`

Rejected because implicit corpus selection is unsafe for a read command; callers name the canonical root.

### Add raw mode

Rejected because raw access and authorization are unresolved; this increment is canonical-only.

### Do nothing

This preserves QMD-only search, leaving users without QMD/model/network no local discovery/read interface; Issue #127 requires a bounded offline path.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Explicit root is required and legacy search is unchanged | CLI parser/dispatch compatibility fixtures | not yet written |
| Literal Unicode casefold matching and path/first-line order are deterministic | synthetic Unicode and tie-order fixture | not yet written |
| Canonical exclusions and root basename rejection are enforced | case-insensitive raw/research/lessons/index/log/hidden fixtures | not yet written |
| Symlinks/reparse points and traversal block before outside reads | external sentinel plus Windows junction fixtures | not yet written |
| Entry/file/aggregate/query/result bounds yield explicit partial status | injected ceiling matrix and incomplete-scan assertions | not yet written |
| Read returns valid UTF-8 bounded prefix with truncation outcome | multibyte boundary and exact byte-budget fixtures | not yet written |
| Orientation records expose only bounded relative metadata and unknowns | schema/boundary/non-claim tests | not yet written |
| Commands work with QMD absent and do not mutate source | subprocess/byte-snapshot offline fixture | not yet written |

## Rollback

Revert the additive commands and their tests/documentation. No persisted index, consumer migration, or source mutation is introduced, so rollback requires no data restoration. Existing `search` remains available.

## References

- GitHub Issue #127
- ADR-003 (canonical selection exclusions/profile)
- ADR-006 (explicit-time freshness semantics)
- ADR-015 (offline core validation)
- `kb_bootstrap/qmd_search.py` (existing QMD-backed search)
- `docs/VALIDATION_COMPOSITION.md` (declarations versus runtime/index evidence)
