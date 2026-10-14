# ADR-031: Bind explicit knowledge items to retained evidence

**Status**: Proposed
**Date**: 2026-10-14
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #128; ADR-006, ADR-010, ADR-024, ADR-026

## Context

Issue #128 asks for a bounded review worklist when explicitly retained evidence changes, without regenerating the KB or treating hashes as semantic proof. Existing contracts cover adjacent but different relations: ADR-006 validates authored provenance/freshness fields at explicit time; ADR-010 inventories exact raw-file bytes; ADR-024 validates declared source/capture representations against bytes; ADR-026 looks up caller-selected validated evidence for one source without discovery. None binds a knowledge item to selected evidence revisions or classifies that binding for incremental review.

No runtime implementation is authorized by this Proposed record. W03 #124 and W09 #130 remain dependencies for implementation details; W05 #126's delivered guide supplies advisory distinctions only. Evidence is limited to repository contracts and #128 scope; no external inference, private corpus or model was used.

## Decision

If separately accepted, define one versioned optional local document containing document-level evidence bindings, and a read-only resolver that emits a bounded affected-item report. The knowledge-item selector is an explicit project-relative Markdown path plus the observed document revision; no global identity is minted. Evidence selectors reuse existing source and representation IDs/revisions from the caller-supplied, validated source/capture envelope. This proposal defines neither a second source registry nor a replacement envelope.

The binding is a new relation record, not a capture or retained-source file. ADR-027 concerns retention of already existing capture Markdown and does not authorize this new format; this ADR remains Proposed and requires owner acceptance before implementation or retention/publishing policy is inferred. W03 #124 and W09 #130 remain implementation dependencies; W05 #126's guide is advisory only.

### Binding contents

Each binding names one project-relative knowledge Markdown path and observed document revision, plus one or more explicit source/representation references already present in the supplied validated envelope. It copies no source body and mints no source or representation identity. A fragment/coordinate is optional and must be tied to the referenced representation revision; no relocation is inferred.

Optional scope/context fields are consumer-authored assertions, not inferred truth. OKF `sources`/footnotes remain compatible and need not be rewritten; this separate relation is not a replacement for ADR-006 provenance. No retention class or reviewer-identity schema is introduced by this increment.

### Resolution and report

The caller supplies every path explicitly: the binding document, selected knowledge document, and the complete source/capture envelope and retained representation paths required by its existing validator. Reuse ADR-024 validation and ADR-026's caller-directed evidence lookup rather than adding a second envelope parser or lookup result contract. Validate all referenced inputs before reporting. Do not enumerate directories, dereference origins, fetch, index, cache, write, or use a system clock.

Classify each binding as `unchanged`, `changed`, `missing`, `inaccessible`, `unsupported`, or `malformed`, with a bounded reason and project-relative identity. These are proposed design labels, not a committed API vocabulary. Missing or inaccessible evidence is not deletion; malformed input is not silently skipped. Changed evidence creates a review item, not an automatic claim rewrite or lifecycle transition. Unchanged bindings remain unchanged. Added contradictory evidence may create a separate review item but cannot automatically resolve or merge claims.

The implementation must use fixed finite limits for binding metadata, number of document/evidence references, selected file sizes, aggregate bytes and serialized output. Exact values, blocked/partial response shape, and ordering are owner-review questions for this proposal; no implementation may guess them. Incomplete inspection must never be reported as a complete empty worklist.

A digest proves byte identity only. It does not prove entailment, authority, independence, completeness, current external reality, source truth or semantic equivalence. Duplicate/reprinted sources do not become independent support; generated knowledge must preserve its upstream lineage and cannot self-confirm. A frozen capture cannot detect later website changes; recapture is a separate explicit input/action. Confirmation, revision and retraction remain human-governed lifecycle decisions with no fabricated verifier event.

## Consequences

### What gets easier

A reviewer can locate explicitly bound knowledge items affected by changed retained bytes without rescanning a corpus or treating unchanged documents as needing regeneration.

### What gets harder

Callers must provide complete explicit paths and maintain bindings; every run revalidates bounded bytes. Ambiguous fragments, changed context and contradictions remain review work rather than automatically resolved facts. A new versioned binding record needs compatibility and retention ownership.

### What does not change

ADR-006 provenance/freshness, ADR-010 raw manifests, ADR-024 source/capture validation and ADR-026 evidence lookup remain authoritative for their scopes. No network, crawling, inference, automatic canonical mutation, deletion, source acquisition, claim database, cross-study registry, entity identity service or publication is added.

## Alternatives Considered

### Require every sentence to be a persisted Claim

Rejected for this increment: it forces a broad canonical data-model migration when document-level bindings alone can produce an initial useful worklist.

### Infer evidence from links, hashes or directories

Rejected: discovery would silently expand scope, and hashes or links alone do not identify a validated retained representation or prove semantic support.

### Automatically relocate fragments or update knowledge

Rejected: ambiguous matches and surrounding-condition changes cannot be resolved from byte similarity; automatic edits would exceed the read-only review goal.

### Do nothing

This preserves current contracts but leaves no explicit binding relation for incremental impact review, the stated W07 goal.

## Test Contract

| Claim if accepted and implemented | Test | Currently |
|---|---|---|
| Only caller-selected inputs are read; no discovery, origin access or writes occur | `tests/test_evidence_binding.py::test_explicit_inputs_only_no_side_effects` | not yet written |
| Unchanged/changed/missing/inaccessible/unsupported/malformed outcomes remain distinct | `tests/test_evidence_binding.py::test_revision_outcome_matrix` | not yet written |
| Changed bytes create bounded review items; unchanged items remain unchanged | `tests/test_evidence_binding.py::test_changed_evidence_worklist_is_bounded` | not yet written |
| Optional fragment coordinates are tied to a representation revision; relocation is not guessed | `tests/test_evidence_binding.py::test_fragment_revision_and_ambiguity` | not yet written |
| Duplicate/reprinted evidence and generated lineage are not presented as independent corroboration | `tests/test_evidence_binding.py::test_duplicate_and_generated_lineage` | not yet written |
| Digests do not imply semantic truth/freshness or trigger lifecycle mutation | `tests/test_evidence_binding.py::test_hash_is_identity_only` | not yet written |

## Rollback

Before acceptance, withdraw this proposal. If accepted and later implemented, reverting the resolver must not delete binding records, snapshots, prior versions or human-authored knowledge. Migration, retention and deletion remain explicit owner-controlled operations.

## References

- Issue #128 and its acceptance criteria.
- ADR-006, ADR-010, ADR-024, ADR-026; W05 guidance `docs/tasks/126-synthesis-guidance.md`.
- `kb_bootstrap/source_capture_validation.py`, `kb_bootstrap/raw_manifest.py`.
