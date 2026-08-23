# Opt-in offline shared lesson cache

`kb-bootstrap lesson-cache` stores an explicitly selected, read-only local copy of sanitized shared lessons. The shared registry remains authoritative.

The command never discovers or copies lessons by default. Every operation requires one or more repeated `--lesson KB-XXXX` allowlist entries.

## Source bundle

The source is a sanitized JSON export supplied through an explicitly selected path. It contains:

- `source_repository` in `owner/repository` form;
- `registry_version`;
- `generated_at` freshness timestamp;
- lessons with ID, version, updated timestamp, and sanitized title/problem/resolution/prevention.

The cache does not use a live registry path and never writes to the source.

## Create or refresh

```bash
kb-bootstrap lesson-cache \
  --source shared-export.json \
  --cache cache/shared-lessons.json \
  --lesson KB-0001 \
  --lesson KB-0007
```

Only allowlisted lessons are refreshed. Existing unselected entries remain and are marked `stale` or `unavailable` when the source no longer matches them.

The local cache records:

- source repository;
- registry version and source generation time;
- explicit selection;
- lesson version and source update date;
- `fresh`, `stale`, or `unavailable` status;
- sanitized read-only content.

## Check freshness without writing

```bash
kb-bootstrap lesson-cache \
  --source shared-export.json \
  --cache cache/shared-lessons.json \
  --lesson KB-0001 \
  --check
```

The check reports `RESULT: STALE` when the selected cached lesson is missing, unavailable, or has a different source version. It does not alter the cache or source.

## Explicit prune

```bash
kb-bootstrap lesson-cache \
  --source shared-export.json \
  --cache cache/shared-lessons.json \
  --lesson KB-0001 \
  --prune
```

Prune removes only local cached entries outside the allowlist. It never deletes or modifies authoritative shared lessons.

## Fail-closed behavior

The command blocks and preserves an existing cache when:

- the allowlist is empty, duplicated, or malformed;
- an allowlisted lesson is unavailable;
- source provenance, version, freshness, lesson identity, or content is invalid;
- source and cache paths are the same;
- an existing cache names another source;
- cache metadata conflicts or contains duplicate IDs;
- the cache parent directory is unavailable;
- atomic local replacement fails.

Content is whitelisted and checked for credentials, protocol-auth URLs, machine paths, and runtime/session identifiers. Diagnostics report only source repository, lesson IDs, freshness categories, and operation outcome.

Cached entries are read-only copies. Authoritative edits, capture, promotion, publication, automatic synchronization, and dual writes remain out of scope.
