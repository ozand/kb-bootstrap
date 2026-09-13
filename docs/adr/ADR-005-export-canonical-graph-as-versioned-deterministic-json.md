# ADR-005: Export the canonical graph as versioned deterministic JSON

**Status**: Accepted — Implemented
**Date**: 2026-09-13
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issue #61; ADR-003 (minimal OKF v0.2 canonical profile); ADR-004 (contained atomic file updates)

## Context

Issue #61 requires an optional, read-only, byte-deterministic JSON export of the canonical Markdown graph. Canonical Markdown remains authoritative. The export must preserve or deterministically handle unknown metadata, fail safely on malformed input, and introduce no server, daemon, or synchronization.

ADR-003 defines the canonical concept boundary and frontmatter profile. Ordinary canonical concepts are Markdown files with a non-empty `type`; case-insensitive `raw`/`lessons` directories and reserved `index.md`/`log.md` files are excluded; unknown types and additional metadata are accepted; static symlinks fail closed; validation assumes a stable checkout.

The existing NetworkX graph linter is a report implementation, not a suitable export contract. Its link regex does not retain fragments, its directed graph collapses repeated link observations, it has different node boundaries, and it does not expose validated frontmatter. Export should not make those accidental details into a persisted schema.

JSON cannot losslessly represent all YAML syntax, comments, quoting, anchors, tags, or scalar distinctions. A parsed `metadata` object would require a new conversion contract. Omitting metadata would not satisfy the Issue's preservation requirement. The smallest precise representation is the exact UTF-8 frontmatter payload as a JSON string.

## Decision

Add an explicit public command:

```text
kb-bootstrap export-graph \
  --dir kb \
  --project-root . \
  --output canonical-graph.json
```

The command is optional and separate from `validate`. It reads one explicit canonical root and writes one explicit output. It never updates Markdown, QMD, lessons, indexes, or external stores.

### Schema

Version 1 has this exact top-level shape and key order:

```json
{
  "schema": "kb-bootstrap.canonical-graph",
  "version": 1,
  "profile": "kb-bootstrap.okf-v0.2-minimal",
  "nodes": [],
  "edges": []
}
```

A node has fixed key order:

```json
{
  "path": "architecture/overview.md",
  "frontmatter": "type: Architecture\ntitle: Overview"
}
```

An edge has fixed key order:

```json
{
  "source": "architecture/overview.md",
  "target": "setup/install.md",
  "fragment": "windows"
}
```

`fragment` is either the exact authored fragment text without the leading `#` or JSON `null`. Version 1 does not percent-decode fragments; an empty trailing `#` is treated as `null`.

The export contains no absolute source/output path, timestamp, hostname, username, inode, random identifier, raw/lesson content, external URL, QMD state, or Markdown body.

### Node boundary and metadata

- Nodes are ordinary canonical concepts using the ADR-003 boundary.
- Case-insensitive `raw`/`lessons` directories and reserved `index.md`/`log.md` files at every level are excluded.
- Static symlinked roots, non-excluded directories, and concept files block the export.
- Every included concept must pass the minimal canonical profile.
- `frontmatter` is the exact text between the opening and closing exact `---` lines, excluding delimiters. Line endings in this payload are normalized to `\n` by the parsing contract so JSON is platform-deterministic; original source bytes remain unchanged.
- Unknown and human-authored fields therefore remain represented in source order and spelling. This is not a YAML semantic round trip and does not make JSON authoritative.
- Nodes are sorted lexicographically by normalized relative POSIX `path`.

### Link and edge semantics

Version 1 recognizes a bounded inline Markdown link grammar outside inline/fenced code and image syntax. Its destination is either an angle-bracket destination or an unquoted, whitespace-free local path ending case-insensitively in `.md`, optionally followed by `#fragment`. Unsupported valid Markdown forms such as bare destinations containing parentheses are ignored rather than claimed as parsed; angle brackets may be used for paths containing spaces or parentheses. A recognized local-looking `.md` opener with missing closing destination/title syntax blocks as malformed instead of silently disappearing.

- Relative paths resolve from the source concept's directory.
- Paths beginning with `/` resolve from the canonical root.
- Separators serialize as `/`; `.` segments are normalized.
- Absolute filesystem paths, NULs, backslashes, `..` escapes beyond the canonical root, percent-encoded separators/traversal, and targets traversing symlinks block the export.
- Fragment-only, external-scheme, protocol-relative, non-Markdown, code/image references, and unsupported valid inline-link forms are ignored and are not emitted; malformed recognized local-link syntax blocks.
- A local Markdown target must exist and be one of the exported nodes. Missing, reserved, excluded, or otherwise non-node local targets block as a graph-integrity error rather than emitting a dangling edge.
- Exact duplicate `(source, target, fragment)` edges are de-duplicated.
- Different fragments remain distinct edges.
- Edges are sorted lexicographically by source, target, then fragment, treating `null` before strings.

These link rules are a versioned export grammar, not a claim to parse every valid Markdown construct. Unsupported/ignored link classes are documented rather than guessed.

### JSON serialization

JSON bytes are produced with:

- UTF-8;
- fixed object key insertion order;
- `ensure_ascii=False`;
- `allow_nan=False`;
- two-space indentation;
- one final newline;
- no generated time or environment-dependent values.

Repeated in-memory export of a stable unchanged tree must be byte-for-byte identical.

### Input and output safety

`--project-root` defaults to the current directory. `--dir` and `--output` are project-root-relative contained paths. Absolute, NUL, escaping, missing-parent, non-regular, and static symlinked paths block with sanitized diagnostics.

The output must be outside the canonical source root so it cannot become a future concept/input. Existing output blocks; v1 has no force/overwrite option.

The complete JSON is staged in the existing output directory, flushed, and fsynced. Publication uses an exclusive hard-link no-overwrite primitive. Unsupported hard links fail closed. Race-created output is preserved. Owned temporary files are cleaned where possible. Once exclusive hard-link publication succeeds, the complete output is authoritative even if unlinking the staging link fails; the command returns success with a sanitized `temporary cleanup is incomplete` warning rather than reporting publication failure. The residual owned temporary link may require manual cleanup.

Input traversal and output publication assume a stable checkout and do not claim a race-free cross-process filesystem snapshot after final path checks.

## Alternatives Considered

### Alternative 1 — Export parsed YAML as a JSON `metadata` object

Rejected for v1. JSON cannot represent all YAML syntax and scalar/tag behavior without a larger conversion and compatibility contract. It risks silently losing unknown human metadata.

### Alternative 2 — Omit frontmatter and export only paths/edges

Rejected. It fails the Issue requirement to preserve or deterministically handle unknown metadata and makes the graph less useful for machine analysis.

### Alternative 3 — Export complete Markdown bodies

Rejected. It increases payload and disclosure risk, duplicates canonical source, and is unnecessary for graph interchange.

### Alternative 4 — Reuse the NetworkX graph object directly

Rejected. Its node boundary, link grammar, duplicate handling, and fragment loss are not a stable export contract.

### Alternative 5 — Include reserved `index.md`/`log.md` as nodes

Rejected for v1. ADR-003 excludes them from ordinary canonical concepts. A future schema can add an explicit reserved-node class if demonstrated demand exists.

### Alternative 6 — Export dangling edges as nodes or warnings

Rejected. Current kb-bootstrap graph integrity treats dead local links as errors. Failing closed avoids creating machine data that appears complete while pointing outside the exported node set.

### Alternative 7 — Write to stdout only

Rejected for this increment. Issue #61 asks for a durable export artifact and byte comparisons. One explicit contained output path is simpler than dual output modes.

### Alternative 8 — Overwrite an existing output atomically

Rejected. The command is optional and derived output may be reviewed or versioned. Exclusive creation prevents accidental or concurrent overwrite; callers explicitly remove/rename old outputs before a new export.

## Consequences

### What gets easier

- Consumers receive a small versioned deterministic graph artifact.
- Unknown frontmatter remains visibly represented without a lossy YAML-to-JSON mapping.
- Graph paths/fragments have stable normalized semantics.
- Repeated exports can be compared by exact bytes or digest.
- Canonical Markdown remains the only source of truth.

### What gets harder

- Consumers must parse the frontmatter string separately if they need structured metadata.
- Unsupported Markdown link forms are omitted by documented rule.
- Dead links and links to excluded/reserved concepts block export.
- Existing output must be removed or renamed explicitly.
- Filesystems without hard-link support cannot publish the export and receive a safe blocked result.
- Path-based validation retains a documented stable-checkout race boundary.

### What does not change

- `kb-bootstrap validate` behavior and reports remain unchanged.
- Canonical and lesson schemas, QMD indexing, source Markdown, and external repositories remain unchanged.
- No UI, API, server, daemon, synchronization, identity allocation, migration, or repair is introduced.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Versioned schema and fixed node/edge key order | export schema snapshot test | passing |
| Repeated stable input produces byte-identical JSON | repeated in-memory and file export tests | passing |
| Unknown frontmatter is represented and source bytes remain unchanged | metadata/source preservation test | passing |
| Canonical profile boundaries and malformed input fail closed | valid/invalid traversal fixtures | passing |
| Relative/root links, fragments, deduplication, and sorting are deterministic | edge normalization fixtures | passing |
| External/non-Markdown/code/image links are ignored and dead/escaping/encoded/symlink/malformed targets block | link safety fixtures | passing |
| Output is contained, exclusive, and race-created content is preserved | output path/race tests | passing |
| Write/link/fsync failures leave no owned partial output; published-output temp cleanup failure is warned | output failure tests | passing |
| Existing validate behavior remains unchanged | current profile/graph/QMD tests | passing |

## Rollback

Revert the implementation PR. Existing exported JSON files are derived consumer-owned artifacts and are not automatically deleted. Canonical Markdown requires no rollback because export never modifies it.

## References

- GitHub issue #61
- ADR-003
- ADR-004
- `kb_bootstrap/canonical_profile.py`
- `kb_bootstrap/graph_linter.py`
- `docs/OKF_V0_2_CANONICAL_PROFILE.md`
