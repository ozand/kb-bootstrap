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

If separately accepted, define a versioned, optional, local evidence-binding document and a read-only resolver. The binding records explicit knowledge-item identity, explicit source/representation identities and observed revision digests for retained UTF-8 Markdown/text. It may include consumer-authored scope/context, retention classification and review attribution. The resolver consumes only caller-selected binding, knowledge-item and existing source/capture evidence inputs and emits a bounded affected-item report. It does not discover files or mutate canonical knowledge.

### Binding contents

Each binding names one stable knowledge-item reference and one or more evidence references. A reference reuses an existing source ID and, when applicable, representation ID and its declared/validated digest; it does not mint a competing source identity or copy source bodies. Revision digest records the observed exact bytes for the cited retained representation. A binding may retain a relative fragment/coordinate only when paired with the representation revision to which it applies; no automatic relocation is assumed.

Optional scope/context fields describe where the knowledge item applies; they are authored assertions, not inferred truth. Retention class and review identity are descriptive metadata only: they confer no access, retention, verification, approval or execution authority. OKF `sources`/footnotes remain compatible and need not be rewritten; the sidecar is an optional relation, not a replacement for ADR-006 provenance.

### Resolution and report

The caller supplies every input path explicitly, including the selected knowledge item, binding document, required manifest/envelope and retained representation paths. Validate the complete binding and all selected evidence before reporting. Do not enumerate directories, dereference origins, fetch, index, cache, write, or use a system clock.

Report each binding deterministically as `unchanged`, `changed`, `missing`, `inaccessible`, `unsupported`, or `malformed`, with a bounded reason and relative identity. Missing or inaccessible evidence is not deletion; malformed input is not silently skipped. Changed evidence creates a review item, not an automatic claim rewrite or lifecycle transition. Unsupported representation type is distinct from malformed bytes. Unchanged bindings remain unchanged; added contradictory evidence may create a separate review item but cannot automatically resolve or merge claims.

Apply fixed finite limits to metadata bytes, item/reference counts, per-file and aggregate evidence bytes, and serialized report bytes. Exceeding any limit blocks or returns an explicitly incomplete report according to the final accepted contract; it never reports a complete empty worklist after incomplete inspection. Deterministic ordering is by stable knowledge-item identity then evidence identity. Exact bounds and output status vocabulary are left as explicit owner-review questions in this proposal, not guessed runtime behavior.

A digest proves byte identity only. It does not prove entailment, authority, independence, completeness, current external reality, source truth or semantic equivalence. Duplicate/reprinted sources do not become independent support; generated knowledge must preserve its upstream lineage and cannot self-confirm. A frozen capture cannot detect later website changes; recapture is a separate explicit input/action. Confirmation, revision and retraction remain human-governed lifecycle decisions with no fabricated verifier event.

## Consequences

### What gets easier

A reviewer can locate explicitly bound knowledge items affected by changed retained bytes without rescanning a corpus or treating unchanged documents as needing regeneration.

### What gets harder

Callers must provide complete explicit paths and maintain bindings; every run revalidates bounded bytes. Ambiguous fragments, changed context and contradictions remain review work rather than automatically resolved facts. A new versioned sidecar format needs compatibility and retention ownership.

### What does not change

ADR-006 provenance/freshness, ADR-010 raw manifests, ADR-024 source/capture validation and ADR-026 evidence lookup remain authoritative for their scopes. No network, crawling, inference, automatic canonical mutation, deletion, source acquisition, claim database, cross-study registry, entity identity service or publication is added.

## Alternatives Considered

### Require every sentence to be a persisted Claim

Rejected for this increment: it forces a broad canonical data-model migration when document-level bindings plus optional important-claim references can produce a useful worklist.

### Infer evidence from links, hashes or directories

Rejected: discovery would silently expand scope, and hashes or links alone do not identify a validated retained representation or prove semantic support.

### Automatically relocate fragments or update claims

Rejected: ambiguous matches and surrounding-condition changes cannot be resolved from byte similarity; automatic edits would exceed the read-only review goal.

### Do nothing

This preserves current contracts but leaves no explicit binding relation for incremental impact review, the stated W07 goal.

## Test Contract

| Claim if accepted and implemented | Test | Currently |
|---|---|---|
| Only caller-selected inputs are read; no discovery, origin access or writes occur | `tests/test_evidence_binding.py::test_explicit_inputs_only_no_side_effects` | not yet written |
| Unchanged/changed/missing/inaccessible/unsupported/malformed outcomes remain distinct | `tests/test_evidence_binding.py::test_revision_outcome_matrix` | not yet written |
| Changed bytes create bounded review items; unchanged items remain unchanged | `tests/test_evidence_binding.py::test_changed_evidence_worklist_is_bounded` | not yet written |
| Fragment coordinates are revision-bound; ambiguous relocation is not guessed | `tests/test_evidence_binding.py::test_fragment_revision_and_ambiguity` | not yet written |
| Duplicate/circular lineage is not counted as independent evidence | `tests/test_evidence_binding.py::test_duplicate_and_generated_lineage` | not yet written |
| Digests do not imply semantic truth/freshness or trigger lifecycle mutation | `tests/test_evidence_binding.py::test_hash_is_identity_only` | not yet written |

## Rollback

Before acceptance, withdraw this proposal. If accepted and later implemented, reverting the resolver must not delete bindings, snapshots, prior versions or human-authored knowledge. Migration, retention and deletion remain explicit owner-controlled operations.

## References

- Issue #128 and its acceptance criteria.
- ADR-006, ADR-010, ADR-024, ADR-026; W05 guidance `docs/tasks/126-synthesis-guidance.md`.
- `kb_bootstrap/source_capture_validation.py`, `kb_bootstrap/raw_manifest.py`.
