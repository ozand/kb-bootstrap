# ADR-040: Classify caller-declared evidence lineage without certifying independence

**Status**: Proposed
**Date**: 2026-10-25
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #128; ADR-031, ADR-035, ADR-036

## Context

Issue #128 requires duplicate/reprinted sources not to become independent support and generated knowledge to retain upstream lineage without self-confirmation. Accepted ADR-031/036 provide explicit byte-revision bindings and reports, not source genealogy. At the exact design baseline `d6c17940e28f5ef86d6912d24a02c0601b00388b`, `kb_bootstrap/evidence_binding.py` validates caller-selected baseline/current envelopes and classifies references by byte digest/mapping. Equal or different digests establish byte identity/change only; source IDs and content do not establish independent origins or ancestry. ADR-036 rejects unknown fields, so this proposal does not extend its JSON format.

This record proposes one small pure classification contract, not a runtime implementation or claim that caller assertions are true. It is limited to explicit lineage declarations for one bounded invocation. Unknown coverage must remain unknown; a declared independent root is not verified independent evidence.

## Decision

If separately accepted, add a pure in-memory helper that accepts a list of lineage-record mappings and a boolean `coverage_complete`. Each mapping has exactly three keys: `id`, `kind` (`independent`, `generated`, or `reprint`), and `upstream_ids` (a list). An ID is a case-sensitive opaque string of 1–256 Unicode characters with no control characters. Each record ID is unique; each upstream ID uses the same rule and refers to one record in this input. An independent record has an empty upstream list and declares itself a root. A generated or reprint record has at least one upstream and declares no new root. Reprints therefore alias declared ancestry; generated records inherit declared ancestry but cannot corroborate their own upstreams as additional roots. This is caller-declared classification, not verification of source genealogy, semantic derivation, or actual independence.

The helper accepts at most 1000 records and at most 100 upstream IDs per record. It rejects the whole call with `ValueError` on a non-list input, mapping with missing/extra keys, wrong value types, invalid/duplicate ID, invalid kind, duplicate edge, missing referenced ID, kind/upstream mismatch, self-edge, cycle, non-boolean coverage value, or exceeded bound. It returns no partial classifications for invalid graphs. Cycle validation and root propagation must handle every graph within these bounds, including a 1000-record chain, without recursion-depth-dependent rejection. Input list order and edge order do not affect results. For complete coverage, the result is one record per input ID sorted by ID; each record has `id`, `state: classified`, sorted `root_ids`, and `root_count == len(root_ids)`. Each root ID is an independent record reachable by following upstream edges, including the record itself when it is independent. The empty graph returns an empty result. Root IDs and result records use case-sensitive Unicode code-point lexicographic order. The helper performs no IO, discovery, hashing, content comparison, model inference, persistence, or mutation.

For structurally valid input with `coverage_complete == true`, a generated/reprint node with one declared root has one declared lineage root; multiple roots remain multiple roots and are not collapsed into a claim of independent corroboration. With `coverage_complete == false`, every result record instead has `state: unknown` and contains only `id` and `state`; no root IDs/count or independence classification is exposed. Locally supplied edges cannot certify that omitted upstream records or duplicate origins are absent. The boolean is a caller assertion, not evidence that coverage is complete.

The result says only which declared independent record IDs are reachable through the submitted edges, conditional on caller-asserted completeness. It does not certify independent support, truth, entailment, authority, non-duplication, corpus completeness, or verification. In particular, callers may mislabel a reprint as independent or omit shared origins; this helper cannot detect that. It does not change ADR-031/036 binding states, reasons, summary precedence, report shape, or source envelope validation. Integration with a future resolver is a separate decision and must not silently reinterpret byte equality as lineage.

### Synthetic falsification cases

Synthetic records `a: independent`, `g: generated -> [a]`, and `r: reprint -> [g]` yield root `[a]`, count 1 for all three; `g` and `r` add no root. Independent `a` and `b` with generated `g -> [a,b]` yield roots `[a,b]`, count 2, not a verified-quorum result. A valid 1000-record chain uses an independent root followed by alternating generated/reprint records, each with exactly its predecessor as upstream; every record classifies to the one root. Incomplete coverage yields `unknown` even for the apparent `a` root. Missing IDs, duplicate IDs/edges, self-edges, cycles, independent nodes with parents, generated/reprint nodes without parents, invalid coverage type, 1001 records, and 101 edges each reject the entire input. Permuting records/edges leaves output identical. These are proposed contract cases, not implemented fixtures or tests.

## Alternatives Considered

### Treat equal bytes or metadata as proof of lineage

Rejected: byte identity and caller metadata do not prove shared or distinct origins. Similarity, URL, title, or content heuristics add unreviewable inference and can both miss reprints and merge unrelated evidence.

### Add lineage fields to ADR-036 bindings or change the resolver report

Rejected: ADR-036 is an accepted strict JSON wire contract. Its purpose is byte-revision binding/reporting; expanding it would change a public format and conflate lineage with observed evidence identity.

### Build a general provenance graph, discovery, or duplicate-detection service

Rejected: registries, transitive discovery across invocations, ontology, content matching, and verified-origin claims exceed this bounded caller-supplied classifier and require new ownership/trust decisions.

### Treat each generated document as a fresh independent source

Rejected: that permits generated material to self-confirm and breaks the explicit upstream chain required by #128.

## Consequences

### What gets easier

A future caller can preserve explicit declared upstream chains and avoid counting generated/reprint records as new declared roots, with deterministic synthetic falsification cases.

### What gets harder

Callers must supply stable IDs, complete bounded edge lists, and an explicit coverage assertion; the helper cannot repair incomplete or dishonest lineage. Multiple declared roots still require human interpretation.

### What does not change

ADR-031/036 runtime and wire contracts, evidence-binding outcomes, retained evidence, canonical Markdown, provenance authority, and lifecycle decisions remain unchanged. No automatic truth score, support/quorum decision, document rewrite, or issue-acceptance claim is introduced.

## Test Contract

| Claim if accepted and implemented | Synthetic test | Currently |
|---|---|---|
| Generated and reprint nodes inherit roots without adding a root; multiple roots remain explicit | `tests/test_evidence_lineage.py::test_generated_and_reprint_inherit_declared_roots` | not yet written |
| Invalid references, duplicate IDs/edges, kind mismatch, self-edge and cycles reject the whole input | `tests/test_evidence_lineage.py::test_invalid_or_cyclic_graph_is_rejected` | not yet written |
| Incomplete coverage yields unknown without root counts; caller assertion is not verification | `tests/test_evidence_lineage.py::test_incomplete_coverage_never_classifies_independence` | not yet written |
| Fixed record/edge limits reject rather than truncate, while a valid maximum-depth chain propagates its single declared root without recursion-depth-dependent failure | `tests/test_evidence_lineage.py::test_graph_limits_and_maximum_chain` | not yet written |
| Permuting input records/edges produces byte-for-byte equivalent result | `tests/test_evidence_lineage.py::test_lineage_classification_is_order_independent` | not yet written |

## Rollback

Before acceptance, withdraw this proposal. No runtime or consumer data is changed. If later implemented and reversed, remove only the helper contract implementation; do not delete caller-authored lineage records or modify accepted ADR-031/036.

## References

- Issue #128, especially its duplicate/reprint and generated-lineage acceptance criterion.
- Accepted ADR-031, ADR-035, ADR-036.
- `kb_bootstrap/evidence_binding.py` at baseline `d6c17940e28f5ef86d6912d24a02c0601b00388b`.
