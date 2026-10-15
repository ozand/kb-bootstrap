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

Each binding names one project-relative knowledge Markdown path and observed document revision, plus one or more explicit source/representation references already present in the supplied validated envelope. It copies no source body and mints no source or representation identity. A fragment/coordinate is optional and must be tied to the referenced representation revision; no relocation is inferred. Claim-level bindings are deferred; this increment binds documents only.

Each binding may include bounded consumer-authored applicability/scope/context qualifiers, a retention class and owner/policy reference, and review actor/attribution. These fields are descriptive only: they do not enforce retention/access, authenticate an actor, record a verifier event, or grant approval. Actor attribution follows ADR-006's sanitized, <=256-character string limit. OKF `sources`/footnotes remain compatible and need not be rewritten; this relation is not a replacement for ADR-006 provenance.

### Resolution and report

The caller supplies every path explicitly: the binding document, selected knowledge document, and the complete source/capture envelope and retained representation paths required by its existing validator. Reuse ADR-024 validation and ADR-026's caller-directed evidence lookup rather than adding a second envelope parser or lookup result contract. Validate all referenced inputs before reporting. Do not enumerate directories, dereference origins, fetch, index, cache, write, or use a system clock.

Classify each binding as `unchanged`, `changed`, `missing`, `inaccessible`, `unsupported`, or `malformed`, with a bounded reason and project-relative identity. These labels directly use #128's requested outcome distinctions; a missing/inaccessible reference is not deletion and malformed input is not silently skipped. Changed evidence creates a review item, not an automatic knowledge rewrite or lifecycle transition. Unchanged bindings remain unchanged. Added contradictory evidence may create a separate review item but cannot automatically resolve or merge claims.

Proposed fixed ceilings are: 8 MiB per binding document; at most 1000 document bindings; at most 100 evidence references per binding; at most 64 MiB for each selected knowledge/evidence file; at most 256 MiB combined selected knowledge and evidence bytes per invocation; at most 1000 report items; and at most 8 MiB serialized report bytes. The 8 MiB metadata, 64 MiB per-file and 256 MiB aggregate values reuse ADR-024's existing bounds; 1000 bindings/references and report limits are finite operational caps proposed here to prevent multiplication of that budget. These values are decision proposals, not current implementation guarantees. The resolver blocks with a sanitized outcome if any ceiling is exceeded; it does not emit a truncated report claiming complete inspection. Sort records by project-relative knowledge path, then source ID, representation ID and revision. No implementation may silently alter these bounds.

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
| The six #128 outcomes remain distinct and are ordered deterministically | `tests/test_evidence_binding.py::test_revision_outcome_matrix` | not yet written |
| Proposed file/count/aggregate/report ceilings block without incomplete-success claims | `tests/test_evidence_binding.py::test_fixed_resource_ceilings` | not yet written |
| Changed bytes create bounded review items; unchanged items remain unchanged | `tests/test_evidence_binding.py::test_changed_evidence_worklist_is_bounded` | not yet written |
| Optional fragment coordinates are tied to a representation revision; relocation is not guessed | `tests/test_evidence_binding.py::test_fragment_revision_and_ambiguity` | not yet written |
| Duplicate/reprinted evidence and generated lineage are not presented as independent corroboration | `tests/test_evidence_binding.py::test_duplicate_and_generated_lineage` | not yet written |
| Scope, retention and review attribution remain descriptive, not permission or verifier events | `tests/test_evidence_binding.py::test_descriptive_context_grants_no_authority` | not yet written |
| Digests do not imply semantic truth/freshness or trigger lifecycle mutation | `tests/test_evidence_binding.py::test_hash_is_identity_only` | not yet written |

## Rollback

Before acceptance, withdraw this proposal. If accepted and later implemented, reverting the resolver must not delete binding records, snapshots, prior versions or human-authored knowledge. Migration, retention and deletion remain explicit owner-controlled operations.

## References

- Issue #128 and its acceptance criteria.
- ADR-006, ADR-010, ADR-024, ADR-026; W05 guidance `docs/tasks/126-synthesis-guidance.md`.
- `kb_bootstrap/source_capture_validation.py`, `kb_bootstrap/raw_manifest.py`.
