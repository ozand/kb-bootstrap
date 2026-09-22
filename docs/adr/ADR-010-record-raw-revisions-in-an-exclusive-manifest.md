# ADR-010: Record raw source revisions in an exclusive manifest

**Status**: Proposed
**Date**: 2026-09-22
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issues #99, #100; ADR-003 (canonical boundary); ADR-005 (exclusive file publication); ADR-009 (published ZIP boundary)

## Context

Issue #99 needs a deterministic, read-only inventory before optional local entity mining can skip unchanged raw files. Existing `kb/raw/` is consumer-owned and indexed separately by QMD; it is excluded from the canonical profile and published ZIP. There is no raw-manifest format or command. The existing repository-context manifest is a different schema; graph export provides the relevant exclusive-file publication precedent.

A persisted format is costly to reverse. Paths and content digests can reveal private information; neither is anonymization. Discovery and comparison must not read outside one explicit corpus or convert raw data into canonical knowledge. This decision is proposed before any implementation and requires separate owner approval.

## Decision

Add an opt-in `raw-manifest` command with explicit project root, corpus directory, absent JSON output, and optional previous-manifest input. It is separate from `validate`, QMD, graph export, and entity inference:

```text
kb-bootstrap raw-manifest --project-root . --dir kb/raw --output raw-manifest.json
kb-bootstrap raw-manifest --project-root . --dir kb/raw --previous old.json --output new.json
```

No implicit previous-file discovery, in-place update, force flag, or default output. Project root, corpus, previous file, and output must be contained, regular where applicable, and non-symlinked. Both previous and output must be outside the corpus; output must be absent with an existing safe parent, and previous and output must differ. An empty corpus is valid. Scan all regular files recursively, including hidden, empty, binary, and non-Markdown files; there is no extension allowlist or content decoding. Any discovered symlinked file/directory or unreadable file blocks the whole run; do not silently omit it. The command never writes inside the corpus.

Version 1 is one UTF-8 JSON object with fixed key order and exactly these fields:

```json
{
  "schema": "kb-bootstrap.raw-manifest",
  "version": 1,
  "corpus": "kb/raw",
  "algorithm": "sha256",
  "files": [
    {"path": "notes/example.md", "sha256": "<64 lowercase hexadecimal characters>"}
  ]
}
```

`corpus` is project-root-relative and follows the same component policy as file paths. Each file path is corpus-root-relative POSIX with `/` separators; no absolute/empty/dot/parent segments, backslash, colon, Windows-invalid `< > " | ? *`, control/NUL characters, or path aliases are accepted. Reject components ending in a space or dot and Windows reserved device basenames (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, including the superscript `¹`, `²`, `³` forms, case-insensitively, with or without an extension). Sort files lexicographically by path; reject duplicate or case-fold-colliding names instead of silently overwriting across platforms. Preserve Unicode code points in names without Unicode normalization; reject exact or case-fold collisions. This is a conservative portable-name policy, not a promise that every supported filesystem can represent every Unicode name. SHA-256 hashes exact source bytes. Omit timestamps, file sizes, inode, machine paths, raw contents, model metadata, and execution receipts. Serialize fixed key order, two-space indentation, UTF-8 without ASCII escaping, and one final newline. Empty `files` is valid.

When `--previous` is provided, validate its complete schema (including rejection of duplicate JSON object keys), corpus identity, algorithm, sorted unique safe paths, and digests before comparing. Reject malformed, incompatible, or previous manifests larger than 64 MiB rather than interpreting them as source paths; never dereference entries in the previous file. The generated manifest must also stay within 64 MiB so every emitted v1 manifest remains a valid future input. Compare path/digest only: current-only `new`, prior-only `removed`, equal-path different-digest `changed`, equal-digest `unchanged`. Removed paths appear only in the stdout comparison report, never in the new manifest. With no previous input, all current files are `new`. The stdout report begins with `=== Raw Manifest ===`, followed by `new: N`, `changed: N`, `unchanged: N`, `removed: N` in that order, then sorted `<category>: <relative path>` lines (category order as above), then sorted `ERROR: <category>` lines when blocked, one `RESULT: OK | BLOCKED` line, and `output: created` only after exclusive publication. Success returns exit 0, a blocked input/publication returns 1, and argparse usage errors return 2. Paths in the manifest and comparison report may themselves be sensitive: they are deliberately shown as corpus-relative paths for navigation, never described as privacy-redacted. Operators must use private storage/access for both artifact and captured stdout; there is no count-only or redacted mode in v1. No raw contents, symlink targets, host paths, or untrusted exception text are emitted.

For each source, check path type and identity before/after reading exact bytes; detect observed replacement or content change and block before publication. Recheck the corpus and output-parent identity before publishing. This assumes a stable checkout and does **not** promise a race-free global filesystem snapshot. Stage complete output in its existing parent, flush/fsync, recheck target absence, publish via exclusive hard link, and clean owned staging where possible. Race-created targets and unsupported hard links block without overwrite. A successfully linked complete output remains published if staging cleanup alone fails, with a sanitized warning (ADR-005 precedent).

This manifest is a derived local artifact, not a retention receipt, privacy filter, archive, or authorization for publication. Its owner chooses storage/access/retention under `docs/EVIDENCE_RETENTION.md`; generated paths and hashes may be sensitive. No model, SQLite database, scheduler, network fetch, QMD update, raw rewrite, or canonical Markdown write is added.

## Alternatives Considered

- **SQLite as v1 public output:** rejected; a simple sorted JSON snapshot is inspectable and sufficient for path/digest classification. A future runtime may build its own index without making it authoritative.
- **Metadata-only `mtime`/size fast path:** rejected; metadata is not a content revision and changes across checkouts. Exact SHA-256 is required.
- **Latest-manifest in-place overwrite:** rejected; an absent new output and explicit previous input preserve prior evidence and avoid concurrent overwrite. Owners may select another filename on each run.
- **Skip unsafe/unreadable files with warnings:** rejected; silently incomplete manifests would misclassify omissions as removed.
- **Content-addressed ledger with run timestamps:** rejected for v1; one timestamp-free snapshot plus comparison report satisfies Issue #99 without a retention/database contract.
- **Text-only or Markdown-only input:** rejected; raw captures include binary and other file types; hashing exact bytes needs no decoder.
- **Embed entity or GLiNER records:** rejected; Issue #100 owns optional inference and candidate cards after this foundation.

## Consequences

### What gets easier

- Consumers can compare exact raw-file revisions without loading an ML model or QMD.
- New, changed, unchanged, and removed paths have explicit deterministic meaning.
- Derived outputs remain separate from authoritative source files and canonical publication.

### What gets harder

- Every included file must be read and hashed; large corpora incur I/O cost.
- Any unsafe or unreadable entry blocks the whole snapshot rather than producing a partial result.
- A public JSON schema, path policy, and no-overwrite output require compatibility management if changed later.
- Manifest storage and access must account for sensitive filenames and guessable digests.

### What does not change

- `kb/raw/`, `kb/lessons/`, QMD, `validate`, graph export, published ZIPs, lesson routing, and canonical Markdown remain unchanged.
- No new Python dependency, GLiNER requirement, network call, background scan, or automatic migration is introduced.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Identical corpus and options yield byte-identical ordered JSON | repeated snapshot fixture, including empty/binary/hidden files | not yet written |
| Path keys remain contained, POSIX-normalized, unique across case variants | path/collision fixture on supported filesystems | not yet written |
| SHA-256 revisions and four comparison categories are correct | new/changed/unchanged/removed matrix | not yet written |
| Malformed, incompatible, over-64-MiB, or unsafe previous manifest blocks; output obeys the same bound | previous-input and output-limit fixtures | not yet written |
| Symlink/unreadable/changed source blocks without dereference or partial output | source-safety and mutation fixture | not yet written |
| Existing/race-created output is preserved; unsupported hard links block | exclusive-publication fixture | not yet written |
| Source tree and existing validation/QMD/lesson workflows are unchanged | source byte/file-list check and full regression suite | not yet run after implementation |
| CLI stdout/exit and sanitization reflect actual artifact outcome | subprocess presentation fixture | not yet written |

## Rollback

Revert the future implementation PR. Existing manifests are derived consumer-owned outputs and are not deleted automatically. An adopted v1 format may require explicit migration for downstream readers; this is why owner approval precedes implementation.

## References

- GitHub issue #99 and its research comments
- GitHub issue #100 (downstream optional candidate extraction)
- ADR-003, ADR-005, ADR-009
- `kb_bootstrap/repository_manifest.py` (serialization precedent, different schema)
- `kb_bootstrap/canonical_graph_export.py` (exclusive publication precedent)
- `docs/EVIDENCE_RETENTION.md`
