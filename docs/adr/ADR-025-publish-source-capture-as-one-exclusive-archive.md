# ADR-025: Publish a source capture as one exclusive archive

**Status**: Superseded by ADR-027
**Date**: 2026-10-09
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #124; ADR-005, ADR-009, ADR-010, ADR-022, ADR-024

Owner acceptance: Issue #124, comment 6091429872 (2026-10-10), for this exact archive contract; implementation authorization is separately bounded by the same comment.

## Context

Issue #124 requires explicit capture publication that preserves existing content and does not overwrite, and forbids implying multi-file atomicity. Accepted ADR-023/024 define source/capture records and selected UTF-8 representations; the implemented validator reads only caller-selected members from an explicit ADR-010 corpus root and never discovers files or dereferences origins. ADR-010 owns raw-manifest v1 and its safe path rules. ADR-005 and ADR-009 demonstrate staged publication of one complete file through an exclusive hard link. ADR-009's published OKF ZIP format excludes `raw/` and `lessons/`, so its format and eligibility rules cannot represent capture publication. These are directly inspected repository contracts at main `73277fdb3e54184901f67268bc676a562b0a677a`; no writer/publication behavior is implemented by this proposal.

### Problem statement

A future explicitly authorized local operation needs to publish one bounded, deterministic artifact containing a validated source-capture envelope and its selected retained UTF-8 representations, without overwriting a prior artifact or pretending a set of corpus writes is transactional.

## Decision

If accepted, publish one versioned source-capture archive as one complete file at an explicit absent, contained output path. This proposal does not authorize implementation.

### What this IS

1. The caller supplies one ADR-024-valid metadata envelope, one explicit ADR-010 corpus root, and the complete explicit selection of every representation member declared retained anywhere in that envelope. Non-retained/reference-only/unknown metadata entries remain in the envelope but contribute no bytes. No tree discovery, implicit manifest lookup, origin retrieval, or unselected file inclusion occurs.
2. The archive contains exactly one metadata member plus every retained representation member. Use a fixed versioned layout: `source-capture/v1/metadata.yaml` plus `source-capture/v1/representations/<ADR-010-relative-path>` for each retained representation. Reject a path collision with the metadata member, duplicate/case-fold-colliding archive member paths, missing or extra selected members, and any member not referenced by a retained representation in the supplied envelope. The metadata remains ADR-024 YAML; archive paths do not replace its corpus-relative `raw_path` values and do not assert that the archive is already an extractable ADR-010 corpus.
3. Validate the complete envelope and all retained members using the existing ADR-024 validator before archive construction; do not add a source-only validation mode or validator API. Serialize archive members in lexicographic POSIX path order with deterministic ZIP metadata: stored (uncompressed) members, fixed DOS timestamp `1980-01-01T00:00:00`, regular-file mode `0o644`, no comments, and no extra fields. Use ZIP64 records only when standard ZIP32 field limits require them; otherwise use ZIP32. Include exact UTF-8 member bytes and verify each retained member's declared SHA-256. Enforce the existing ADR-024 limits unchanged: metadata <=8 MiB; <=1,000 sources; <=100 representations/source; <=100,000 retained representation members (the validator's selected-path cap); each member <=64 MiB; aggregate uncompressed representation bytes <=256 MiB. Also cap the final archive file at 300 MiB, including metadata, representation bytes, member names, ZIP headers, and ZIP64 records; reject rather than truncate if exceeded. The 300 MiB output ceiling is specific to this archive contract and is not a new validator/member-byte allowance.
4. The destination is an explicit project-relative regular-file path outside the supplied source corpus, with an existing safe non-symlink parent and absent final component. Stage the complete archive in that same parent, flush/fsync, recheck parent identity and target absence, then publish with the existing exclusive hard-link mechanism. Existing/race-created targets are preserved; unsupported hard links or changed/unsafe inputs block. Remove only the operation's owned staging file where possible and report incomplete cleanup without deleting unrelated paths.
5. The published archive is one locally authorized derived artifact. ADR-022's local-write authority remains separate from review or external publication; metadata permissions/retention labels, adapter availability, and this ADR do not grant authority. The owner selects storage, access, and retention under `docs/EVIDENCE_RETENTION.md`.
6. A future implementation must state the stable-checkout assumptions and filesystem race limits of the reused publication mechanism. It must not claim cross-process snapshot isolation or a multi-file transaction.

### What this IS NOT

This is not ADR-009's published OKF bundle, not an in-place `kb/raw` installer, not an archive extraction/importer, not an atomic multi-file corpus transaction, and not an acquisition, conversion, retry, migration, synchronization, or network-publication mechanism. It does not alter ADR-010 manifest v1, ADR-024 record semantics, or existing consumer files. It does not establish source truth, original availability, authorization, or durable retention.

### Success criteria

A future bounded implementation produces byte-deterministic archives from the same explicit metadata/all-retained-member bytes; rejects unsafe, extra, missing, colliding, malformed, digest-mismatched, or over-limit inputs; preserves valid non-retained metadata without inventing bytes; publishes only to an absent safe target; preserves any pre-existing/race-created output; and leaves every source byte unchanged. Failure before exclusive publication leaves no visible partial archive.

## Consequences

### What gets easier

A capture and its selected evidence can be reviewed or transferred as one complete local artifact without placing a metadata sidecar beside consumer content.

### What gets harder

The archive is a new versioned format and duplicates selected bytes. It is not directly consumed by the current corpus-root validator; a future reader/extractor requires separate design and authorization. ZIP metadata determinism, the 300 MiB container cap, and reuse of ADR-024's unchanged content/count caps must be tested. Hard-link publication is unavailable on some filesystems and then fails closed.

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
| The complete envelope is validated and all retained members, but no non-retained payloads, enter the deterministic archive | `tests/test_source_capture_archive.py::test_complete_envelope_and_all_retained_members` | Not yet written |
| ADR-024 count/byte caps are unchanged and final ZIP output is capped at 300 MiB | `tests/test_source_capture_archive.py::test_member_and_archive_caps_block_before_publication` | Not yet written |
| Unsafe/colliding/extra/missing/digest-mismatched members block | `tests/test_source_capture_archive.py::test_invalid_member_selection_blocks_without_output` | Not yet written |
| Existing and race-created destinations are preserved | `tests/test_source_capture_archive.py::test_exclusive_output_preserves_existing_and_race_target` | Not yet written |
| Failure before publication leaves no partial target and source bytes unchanged | `tests/test_source_capture_archive.py::test_failure_preserves_sources_and_publishes_no_partial_archive` | Not yet written |
| Authority, no-origin-dereference, and no-discovery boundaries hold | `tests/test_source_capture_archive.py::test_no_origin_access_or_tree_discovery` | Not yet written |

## Rollback

Before acceptance, withdraw this proposal. If accepted and later implemented, revert only the implementation and retain any owner-created archives; never delete consumer artifacts or rewrite existing files automatically. Reversing the archive format after adoption requires a superseding ADR and an explicit compatibility plan.

## References

- Issue #124 and updated research checkpoint: https://github.com/ozand/kb-bootstrap/issues/124#issuecomment-6071669577
- ADR-005, ADR-009, ADR-010, ADR-022, ADR-023 (superseded by ADR-024), ADR-024
- `kb_bootstrap/source_capture_validation.py`; `kb_bootstrap/canonical_graph_export.py`; `docs/EVIDENCE_RETENTION.md`
