# ADR-031: Bind explicit knowledge items to retained evidence

**Status**: Accepted
**Date**: 2026-10-19
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #128; ADR-006, ADR-010, ADR-024, ADR-026

Owner acceptance: Issue #128, comment 6258638640 (2026-10-19), explicitly accepts the reviewed normative text in PR #215 at `408984c5306605e5074336234e1c96ba2ff7198a`. The coordinator record reports the operator's instruction and is not an owner-authored GitHub approval or independent authentication evidence.

## Context

Issue #128 asks for a bounded review worklist when explicitly retained evidence changes, without regenerating the KB or treating hashes as semantic proof. Existing contracts cover adjacent but different relations: ADR-006 validates authored provenance/freshness fields at explicit time; ADR-010 inventories exact raw-file bytes; ADR-024 validates declared source/capture representations against bytes; ADR-026 looks up caller-selected validated evidence for one source without discovery. None binds a knowledge item to selected evidence revisions or classifies that binding for incremental review.

No runtime implementation is authorized by this Proposed record. The #128 design-only task is independent of W03 #124 and W05 #126 runtime implementation; W09 #130 policy decisions remain a prerequisite before any implementation that persists or processes these bindings. W05 #126 is closed and its delivered guide supplies advisory distinctions only. Evidence is limited to repository contracts and #128 scope; no external inference, private corpus or model was used. The design is informed by the W01 proposal-baseline refresh recorded in the #128 research checkpoint; no W01 files or contracts are changed here.

## Decision

If separately accepted, define one versioned optional local binding document for exactly one knowledge Markdown document, and a read-only resolver that emits bounded per-reference observations and one affected-item summary. The caller supplies the binding document, that knowledge document, and complete baseline and current source/capture envelopes with every retained representation path required by ADR-024. Both envelopes must validate in full; an invalid or incomplete envelope blocks the invocation under ADR-026 rather than becoming per-binding missing/inaccessible results. The resolver performs no discovery.

The binding names the knowledge document by normalized project-relative path and observed SHA-256. If the selected document digest differs from the bound digest, the invocation reports `changed` for the knowledge item and requires review; evidence-reference observations are still reported against the supplied envelopes. Each evidence reference names a baseline envelope's source ID, representation ID and observed digest. Before comparison, the referenced source and representation must exist in the fully validated baseline envelope, and the binding's digest must equal that representation's validated observed digest; otherwise the invocation is `BLOCKED`. To compare revisions, the caller supplies an explicit baseline-to-current mapping for each reference, naming the current source and representation IDs. IDs are not matched across envelopes unless that mapping says so; no cross-envelope identity or mapping is inferred. A missing mapping or mapped current reference is reported as `missing`; mapped evidence whose validated digest differs is `changed`; equal digest is `unchanged`. The mapping is an explicit caller assertion of correspondence, not proof of semantic equivalence. This proposal defines neither a second source registry nor a replacement envelope.

The binding is a new relation record, not a capture or retained-source file. ADR-027 concerns retention of already existing capture Markdown and does not authorize this new format; this ADR remains Proposed and requires owner acceptance before implementation or retention/publishing policy is inferred. W03 #124 and W09 #130 remain implementation dependencies; W05 #126's guide is advisory only.

### Binding contents

The binding document applies to exactly one knowledge Markdown path and observed document SHA-256. A caller supplies that one path per invocation; all entries in the binding document therefore refer to the same document and its explicitly recorded baseline revision. The resolver verifies the path is normalized, project-relative, contained, regular and non-symlinked before reading; absolute paths, traversal, symlink/junction/reparse traversal and non-regular files are rejected before content access. Apply the same checks to the binding document and to selected knowledge/evidence paths, consistent with ADR-010's portable path policy and ADR-017's stricter read-path policy. It copies no source body and mints no source or representation identity. A fragment/coordinate, if present, is tied to the named baseline representation revision; relocation is not inferred. Claim-level bindings are deferred; this increment binds one document only.

Each binding may include bounded consumer-authored applicability/scope/context qualifiers, a retention class and owner/policy reference, and review actor/attribution. These fields are descriptive only: they do not enforce retention/access, authenticate an actor, record a verifier event, or grant approval. Actor attribution follows ADR-006's sanitized, <=256-character string limit. OKF `sources`/footnotes remain compatible and need not be rewritten; this relation is not a replacement for ADR-006 provenance.

### Resolution and report

The caller supplies every path explicitly: the binding document, its one selected knowledge document, both complete source/capture envelopes, and the complete retained-representation path sets required by ADR-024 for each envelope. Reuse ADR-024 validation and ADR-026's caller-directed whole-envelope validation boundary; do not add a second envelope parser or weaken validation to obtain per-reference availability. Validate all caller inputs before reporting. Do not enumerate directories, dereference origins, fetch, index, cache, write, or use a system clock.

Emit one observation per valid evidence reference as `unchanged`, `changed`, or `missing`, with a bounded reason and project-relative identity. `Inaccessible` is represented by a sanitized invocation-level `BLOCKED` result because full envelope/path validation cannot safely establish a per-reference association; invalid/missing declared retained files likewise block the whole invocation per ADR-026. Malformed or unsupported binding/envelope input blocks the whole invocation before any report; it is never emitted as a per-reference state or silently skipped. A reference with no explicit current mapping or no mapped current item is `missing`; this is not deletion. The single document summary has deterministic precedence: invocation-level blocked input yields `BLOCKED` and no partial report; otherwise a changed knowledge-document revision or any `changed` evidence reference yields `changed` and requires review; otherwise any `missing` reference yields `missing`; only a knowledge document matching its bound digest and all evidence references `unchanged` yields `unchanged`. Each per-reference state remains in the report, so aggregation does not hide mixed outcomes. Changed knowledge or evidence creates a review item, not an automatic knowledge rewrite or lifecycle transition. Added contradictory evidence may create a separate review item but cannot automatically resolve or merge claims.

Proposed fixed ceilings are: 8 MiB per binding document; at most 1000 bindings; at most 100 evidence references per binding; at most 64 MiB for each selected knowledge/evidence file; at most 256 MiB combined selected knowledge and evidence bytes across both envelopes per invocation; at most 1000 report items; and at most 8 MiB serialized report bytes. The 8 MiB metadata, 64 MiB per-file and 256 MiB aggregate values reuse ADR-024's existing bounds; 1000 bindings/references and report limits are finite operational caps proposed here to prevent multiplication of that budget. These values are decision proposals, not current implementation guarantees. The resolver blocks with a sanitized outcome if any ceiling is exceeded; it does not emit a truncated report claiming complete inspection. Sort observations by source ID, representation ID and revision, then emit the one document summary. No implementation may silently alter these bounds.

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
| Only caller-selected inputs are read; one knowledge document per invocation; all binding/knowledge paths are contained regular non-symlink files; no discovery, origin access or writes occur | `tests/test_evidence_binding.py::test_explicit_inputs_only_no_side_effects` | not yet written |
| Each baseline binding must match its validated baseline representation; malformed/unsupported inputs block, and only unchanged/changed/missing per-reference outcomes are emitted | `tests/test_evidence_binding.py::test_revision_outcome_matrix` | not yet written |
| A changed knowledge digest makes the document summary `changed` even when every evidence reference is unchanged | `tests/test_evidence_binding.py::test_changed_knowledge_with_unchanged_evidence` | not yet written |
| Proposed file/count/aggregate/report ceilings block without incomplete-success claims | `tests/test_evidence_binding.py::test_fixed_resource_ceilings` | not yet written |
| Changed evidence bytes create bounded review items; unchanged references remain unchanged | `tests/test_evidence_binding.py::test_changed_evidence_worklist_is_bounded` | not yet written |
| Optional fragment coordinates are tied to a representation revision; relocation is not guessed | `tests/test_evidence_binding.py::test_fragment_revision_and_ambiguity` | not yet written |
| Duplicate/reprinted evidence and generated lineage are not presented as independent corroboration | `tests/test_evidence_binding.py::test_duplicate_and_generated_lineage` | not yet written |
| Scope, retention and review attribution remain descriptive, not permission or verifier events | `tests/test_evidence_binding.py::test_descriptive_context_grants_no_authority` | not yet written |
| Digests do not imply semantic truth/freshness or trigger lifecycle mutation | `tests/test_evidence_binding.py::test_hash_is_identity_only` | not yet written |

## Rollback

Before acceptance, withdraw this proposal. If accepted and later implemented, reverting the resolver must not delete binding records, snapshots, prior versions or human-authored knowledge. Migration, retention and deletion remain explicit owner-controlled operations.

## References

- Issue #128 and its acceptance criteria and research checkpoint.
- ADR-006, ADR-010, ADR-017, ADR-024, ADR-026; W05 guidance `docs/tasks/126-synthesis-guidance.md`.
- `kb_bootstrap/source_capture_validation.py`, `kb_bootstrap/raw_manifest.py`.
