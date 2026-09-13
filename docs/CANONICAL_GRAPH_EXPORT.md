# Deterministic canonical graph JSON export

`kb-bootstrap export-graph` creates one optional read-only JSON artifact derived from canonical Markdown. Markdown remains the source of truth; the export is not read back, synchronized, or treated as an editable database.

```bash
kb-bootstrap export-graph \
  --project-root . \
  --dir kb \
  --output canonical-graph.json
```

## Schema version 1

```json
{
  "schema": "kb-bootstrap.canonical-graph",
  "version": 1,
  "profile": "kb-bootstrap.okf-v0.2-minimal",
  "nodes": [
    {
      "path": "architecture/overview.md",
      "frontmatter": "type: Architecture\ntitle: Overview"
    }
  ],
  "edges": [
    {
      "source": "architecture/overview.md",
      "target": "setup/install.md",
      "fragment": "windows"
    }
  ]
}
```

Object keys use the displayed order. Nodes sort by relative POSIX path. Edges sort by source, target, then fragment, with `null` before strings. Exact duplicate edges are removed; links to distinct fragments remain separate.

JSON is UTF-8, uses two-space indentation, keeps Unicode, includes no non-finite numbers, and ends with one newline. It contains no generation timestamp, machine path, username, inode, QMD state, Markdown body, raw/lesson content, or external URL.

## Canonical boundary

Nodes use the [canonical OKF v0.2 profile](OKF_V0_2_CANONICAL_PROFILE.md):

- ordinary canonical `.md` concepts only;
- case-insensitive `raw`/`lessons` directories excluded;
- case-insensitive `index.md`/`log.md` excluded at every level;
- static symlink roots/directories/files rejected;
- malformed or invalid canonical concepts block the complete export.

Each node stores the exact frontmatter payload between the `---` delimiters, normalized to LF for platform-deterministic JSON. Unknown and human-authored keys therefore remain represented in source order and spelling. This is not a YAML semantic round trip and does not modify source bytes.

## Link grammar

Version 1 exports standard inline Markdown links to local `.md` concepts:

- relative paths resolve from the source document;
- `/path.md` resolves from the canonical root;
- optional `#fragment` is stored separately without `#`, exactly as authored and without percent decoding; an empty trailing `#` becomes `null`;
- exact duplicate source/target/fragment edges are de-duplicated.

External schemes, protocol-relative links, fragment-only links, non-Markdown links, inline/fenced code references, image syntax, and unsupported valid inline-link forms are ignored. Version 1 supports angle-bracket destinations and unquoted whitespace-free bare paths; use angle brackets for local paths containing spaces or parentheses. A recognized local-looking `.md` opener with unterminated destination or title syntax blocks as malformed rather than silently dropping an edge. Local Markdown links with queries, missing/non-exported targets, absolute filesystem paths, backslashes, NULs, encoded separators/traversal, escapes outside the canonical root, or symlink targets block the export. The error report contains only relative source names and categories.

This is a deliberately bounded link grammar, not a complete CommonMark parser.

## Output safety

`--dir` and `--output` are repository-relative and contained by `--project-root`. The output must be outside the canonical root, its parent must already exist, and existing/symlinked outputs are not overwritten.

The command stages complete JSON in the output directory, flushes and fsyncs it, and publishes through exclusive hard-link creation. Filesystems or policies without hard-link support fail closed. Race-created outputs remain untouched, and owned temporary files are cleaned where possible. If exclusive publication succeeds but removing the staging hard link fails, the complete output remains successful and the command emits `WARNING: output published; temporary cleanup is incomplete`; the owned temporary link may require manual cleanup.

The command assumes a stable checkout. It checks static symlinks and controllable path changes but does not claim a race-free cross-process filesystem snapshot.

## Validation and determinism

Run the export twice to separate new files and compare exact bytes or SHA-256 hashes:

```bash
kb-bootstrap export-graph --project-root . --dir kb --output graph-a.json
kb-bootstrap export-graph --project-root . --dir kb --output graph-b.json
```

Both outputs must be byte-identical when canonical inputs are unchanged. Source Markdown and unrelated paths must retain their original bytes.

## Non-actions

The command does not:

- modify, repair, migrate, or normalize canonical Markdown;
- export raw/project-lesson content or external URLs;
- update QMD;
- overwrite an existing output;
- allocate identities or write across repositories;
- run a UI, HTTP API, server, daemon, or background synchronization.
