# ADR-025: Publish a source capture as one exclusive archive

**Status**: Proposed
**Date**: 2026-10-09
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #124; ADR-005, ADR-009, ADR-010, ADR-022, ADR-024

## Context

Issue #124 requires explicit capture publication that preserves existing content and does not overwrite, and forbids implying multi-file atomicity. Accepted ADR-023/024 define source/capture records and selected UTF-8 representations; the implemented validator reads only caller-selected members from an explicit ADR-010 corpus root and never discovers files or dereferences origins. ADR-010 owns raw-manifest v1 and its safe path rules. ADR-005 and ADR-009 demonstrate staged publication of one complete file through an exclusive hard link. ADR-009's published OKF ZIP format excludes `raw/` and `lessons/`, so its format and eligibility rules cannot represent capture publication. These are directly inspected repository contracts at main `73277fdb3e54184901f67268bc676a562b0a677a`; no writer/publication behavior is implemented by this proposal.

### Problem statement

A future explicitly authorized local operation needs to publish one bounded, deterministic artifact containing a validated source-capture envelope and its selected retained UTF-8 representations, without overwriting a prior artifact or pretending a set of corpus writes is transactional.

## Decision

If accepted, publish one versioned source-capture archive as one complete file at an explicit absent, contained output path. This proposal does not authorize implementation.

### What this IS

1. The caller supplies one ADR-024-valid metadata envelope, one explicit ADR-010 corpus root, and an explicit finite selection of representation members referenced by that envelope. No tree discovery, implicit manifest lookup, origin retrieval, or unselected file inclusion occurs.
2. The archive contains exactly one metadata member and the selected representation members. Use a fixed versioned layout: `source-capture/metadata.yaml` plus `source-capture/representations/<ADR-010-relative-path>` for each selected representation. Reject a path collision with the metadata member, duplicate/case-fold-colliding archive member paths, unreferenced selected members, missing retained members, and any member not referenced by the supplied envelope. The metadata remains ADR-024 YAML; archive paths do not replace its corpus-relative `raw_path` values and do not assert that the archive is already an extractable ADR-010 corpus.
3. Serialize archive members in lexicographic POSIX path order with deterministic ZIP metadata: stored (uncompressed) members, fixed timestamp, fixed regular-file mode, no comments or extra fields. Include exact UTF-8 member bytes and verify each selected member's declared SHA-256 before archive construction. Bound metadata, member count, each member size and aggregate uncompressed bytes; over-limit inputs block without publication. Concrete numerical caps are implementation detail to be fixed from existing ADR-024/validator caps before implementation, not widened silently.
4. The destination is an explicit project-relative regular-file path outside the supplied source corpus, with an existing safe non-symlink parent and absent final component. Stage the complete archive in that same parent, flush/fsync, recheck parent identity and target absence, then publish with the existing exclusive hard-link mechanism. Existing/race-created targets are preserved; unsupported hard links or changed/unsafe inputs block. Remove only the operation's owned staging file where possible and report incomplete cleanup without deleting unrelated paths.
5. The published archive is one locally authorized derived artifact. ADR-022's local-write authority remains separate from review or external publication; metadata permissions/retention labels, adapter availability, and this ADR do not grant authority. The owner selects storage, access, and retention under `docs/EVIDENCE_RETENTION.md`.
6. A future implementation must state the stable-checkout assumptions and filesystem race limits of the reused publication mechanism. It must not claim cross-process snapshot isolation or a multi-file transaction.

### What this IS NOT

This is not ADR-009's published OKF bundle, not an in-place `kb/raw` installer, not an archive extraction/importer, not an atomic multi-file corpus transaction, and not an acquisition, conversion, retry, migration, synchronization, or network-publication mechanism. It does not alter ADR-010 manifest v1, ADR-024 record semantics, or existing consumer files. It does not establish source truth, original availability, authorization, or durable retention.

### Success criteria

A future bounded implementation produces byte-deterministic archives from the same explicit metadata/member bytes; rejects unsafe, unselected, missing, colliding, malformed, digest-mismatched, or over-limit inputs; publishes only to an absent safe target; preserves any pre-existing/race-created output; and leaves every source byte unchanged. Failure before exclusive publication leaves no visible partial archive.

## Consequences

### What gets easier

A capture and its selected evidence can be reviewed or transferred as one complete local artifact without placing a metadata sidecar beside consumer content.

### What gets harder

The archive is a new versioned format and duplicates selected bytes. It is not directly consumed by the current corpus-root validator; a future reader/extractor requires separate design and authorization. ZIP metadata determinism and resource limits must be tested. Hard-link publication is unavailable on some filesystems and then fails closed.

### What does not change

ADR-010 path and manifest rules, ADR-024 capture record semantics, ADR-022 authority distinctions, source-corpus contents, and the exclusion of automatic acquisition or consumer migration remain unchanged.

## Alternatives Considered

- **Write metadata and representations as several corpus files:** rejected because multiple visible writes are not atomic, can expose incomplete state, and conflict with preservation/no-overwrite behavior.
- **Reuse ADR-009's OKF ZIP profile:** rejected because that profile intentionally excludes raw/source-capture content; only its single-file exclusive publication mechanism is relevant prior art.
- **Publish a directory by reservation or rename:** rejected because reservation exposes partial contents and directory rename has replacement races on supported platforms, as documented in ADR-009.
- **Overwrite or repair an existing target:** rejected because capture evidence may be owner-retained and ADR-010/ADR-009 establish explicit no-overwrite output semantics.
- **Do nothing:** leaves #124's explicit publication-preservation criterion without a design, while callers continue to need a bounded publication contract.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| Only explicit envelope members and selected bytes enter the deterministic archive | `tests/test_source_capture_archive.py::test_exact_explicit_members_and_stable_archive_bytes` | Not yet written |
| Unsafe/colliding/unreferenced/missing/digest-mismatched/over-limit members block | `tests/test_source_capture_archive.py::test_invalid_member_selection_blocks_without_output` | Not yet written |
| Existing and race-created destinations are preserved | `tests/test_source_capture_archive.py::test_exclusive_output_preserves_existing_and_race_target` | Not yet written |
| Failure before publication leaves no partial target and source bytes unchanged | `tests/test_source_capture_archive.py::test_failure_preserves_sources_and_publishes_no_partial_archive` | Not yet written |
| Authority, no-origin-dereference, and no-discovery boundaries hold | `tests/test_source_capture_archive.py::test_no_origin_access_or_tree_discovery` | Not yet written |

## Rollback

Before acceptance, withdraw this proposal. If accepted and later implemented, revert only the implementation and retain any owner-created archives; never delete consumer artifacts or rewrite existing files automatically. Reversing the archive format after adoption requires a superseding ADR and an explicit compatibility plan.

## References

- Issue #124 and updated research checkpoint: https://github.com/ozand/kb-bootstrap/issues/124#issuecomment-6071669577
- ADR-005, ADR-009, ADR-010, ADR-022, ADR-023 (superseded by ADR-024), ADR-024
- `kb_bootstrap/source_capture_validation.py`; `kb_bootstrap/canonical_graph_export.py`; `docs/EVIDENCE_RETENTION.md`
