# ADR-036: Define a minimal JSON format for evidence binding

**Status**: Proposed
**Date**: 2026-10-19
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #128; Accepted ADR-031; ADR-006, ADR-017, ADR-024, ADR-026

## Context

Accepted ADR-031 defines the normative resolver contract but leaves the exact binding input and report serialization open. Issue #128 asks for a minimal versioned evidence-binding schema and local-only resolver. This proposal supplies only JSON field shapes and parsing rules complementary to ADR-031. It does not revise ADR-031, authorize implementation, or accept W09/#130 policy or runtime behavior.

ADR-031 remains authoritative for one knowledge document per invocation, complete validated baseline/current envelopes, baseline identity/digest checks, explicit mapping without identity inference, `BLOCKED` for malformed/unsupported inputs, the three reference states, summary precedence, path safety, privacy limits, and resource caps. On any conflict, ADR-031 and accepted ADR-024/026 win. No new registry, schema for source envelopes, CLI, policy engine, or runtime is proposed.

## Decision

If accepted, use one UTF-8 JSON object as an optional caller-selected binding input, separate from the complete baseline/current envelopes and their retained bytes. The v1 top-level shape is:

```json
{
  "schema": "kb-bootstrap.evidence-bindings",
  "version": 1,
  "knowledge": {"path": "kb/notes/topic.md", "sha256": "<64 lowercase hex>"},
  "bindings": []
}
```

`knowledge.path` is the single normalized project-relative Markdown path; `sha256` is its expected exact-byte digest. `bindings` is a bounded array. Each entry contains a stable-in-this-file `binding_id`, baseline `source_id`, `representation_id`, and `observed_sha256`. It may contain `current`, an object with explicit current `source_id` and `representation_id`; omission means no mapping and therefore `missing`. Duplicate `(source_id, representation_id)` pairs in one binding document are rejected; each distinct binding ID must have unique values. Optional `applicability`, `scope`, and `context` are consumer-authored descriptive strings, each at most 2048 UTF-8 bytes and containing no forbidden control characters; optional `retention_class` and `owner_policy_ref` are bounded non-empty strings at most 256 UTF-8 bytes. Optional `review_actor` is a sanitized attribution string at most 256 UTF-8 bytes following ADR-006's actor convention; it is not authenticated identity. These qualifiers grant no read, retention, review, or publication authority. Explicit null, incomplete mapping objects, duplicate IDs/pairs, malformed values, unknown fields, duplicate JSON keys, or unsupported schema/version block the invocation before a report. IDs and digests are strings only; the resolver observes actual bytes through ADR-024/026 and requires each binding's digest to equal its validated baseline representation digest.

Optional `fragment` is a revision-bound locator with `representation_id` matching the binding's baseline representation and positive one-based inclusive `start_line`/`end_line` integers (`start_line <= end_line`). Coordinates apply to the exact validated UTF-8 text bytes of that representation after decoding; LF and CRLF each delimit one line, and lone CR is ordinary line content. Invalid UTF-8 or an out-of-range line blocks the invocation. The locator is navigation metadata only; no relocation or semantic support is inferred. V1 omits fragment relocation and richer coordinate systems; consumers needing those require a later accepted format decision.

The binding example is illustrative only:

```json
{
  "schema": "kb-bootstrap.evidence-bindings", "version": 1,
  "knowledge": {"path": "kb/notes/topic.md", "sha256": "<observed-doc-sha256>"},
  "bindings": [{"binding_id": "b1", "source_id": "s1", "representation_id": "r1",
    "observed_sha256": "<observed-baseline-sha256>",
    "current": {"source_id": "s1-current", "representation_id": "r2"},
    "fragment": {"representation_id": "r1", "start_line": 4, "end_line": 7}}]
}
```

The ephemeral JSON report contains no source payloads or absolute paths:

```json
{
  "status": "COMPLETE",
  "knowledge": {"path": "kb/notes/topic.md", "summary": "changed"},
  "references": [{"binding_id": "b1", "state": "changed", "reason": "digest_changed"}]
}
```

`status` is `COMPLETE` or `BLOCKED`. A blocked response contains a bounded reason and no partial reference list. A complete response emits one report item per reference plus exactly one document summary item, so the total cap of 1000 report items permits at most 999 references across the binding document; if the binding count exceeds that effective cap, block without truncation. Sort reference items by source ID, representation ID, revision, then binding ID as a deterministic tie-break. Each reference emits only `unchanged`, `changed`, or `missing`. The document summary follows ADR-031 precedence: any changed knowledge revision or reference yields `changed`; else any missing reference yields `missing`; else `unchanged`. Output is a transient result, not a second persisted binding format, cache, approval, or authority record. It uses ADR-031's other ceilings; exceeding any cap blocks without truncation-as-success.

V1 parsing rejects duplicate object keys, unknown fields, malformed types, unsupported versions, and non-UTF-8 input. All paths use ADR-010/017/024/026 validation; this ADR creates no alternate path rule. Canonical JSON byte serialization is not required for the binding input; hashes always refer to observed file bytes, not model-supplied or reserialized JSON digests.

## Consequences

### What gets easier

A caller and reviewer can exchange one small versioned binding object and a bounded machine-readable report while keeping source envelopes and retained payloads under their existing contracts.

### What gets harder

The format creates a compatibility surface: field names, strict unknown-field rejection, duplicate-key rejection, and the limited line-based fragment locator must be versioned deliberately. Baseline/current envelopes remain necessary and validation can block the whole invocation.

### What does not change

Accepted ADR-031 semantics and caps remain authoritative. No runtime, CLI, persistence location, registry, policy engine, network behavior, or consumer migration is added. Hashes remain byte identity, not truth or semantic equivalence.

## Alternatives Considered

### Put source envelopes inside the binding object

Rejected because ADR-024/026 own the complete evidence envelope; duplication risks divergent validation and identity semantics.

### Encode current IDs by matching baseline IDs automatically

Rejected because identifiers are envelope-scoped; explicit mapping is required and does not prove semantic equivalence.

### Emit payloads or absolute paths in the report

Rejected because the report is navigation/review metadata and can itself be sensitive; no source body or host path is needed.

### Add a generic extensible registry or policy fields

Rejected because the bounded task is a binding/report format; authority, retention, and policy remain separate contracts and unknown fields fail closed in v1.

## Test Contract

| Claim if accepted and implemented | Synthetic test | Currently |
|---|---|---|
| V1 accepts the illustrated document and rejects unknown version/field, duplicate key, null mapping, duplicate binding ID, or duplicate source/representation pair | `test_binding_json_v1_strict_shape` | not yet written |
| Optional qualifiers remain bounded descriptive strings with no authority; actor attribution is not authentication | `test_qualifier_bounds_and_non_authority` | not yet written |
| Each baseline reference exists and its declared digest equals validated baseline bytes before current comparison | `test_binding_matches_validated_baseline` | not yet written |
| Missing mapping yields `missing`; explicit mapping yields deterministic unchanged/changed states | `test_explicit_current_mapping_matrix` | not yet written |
| Knowledge drift affects summary before missing/unchanged aggregation | `test_document_summary_precedence` | not yet written |
| Fragment locator is tied to representation ID and valid one-based line range; relocation is not inferred | `test_fragment_locator_bounds_and_revision` | not yet written |
| Malformed/unsupported inputs and exceeded ADR-031 ceilings block without partial-success output | `test_blocked_no_partial_report` | not yet written |
| Report is bounded to at most 999 references plus one document summary, sorted deterministically including binding-ID ties, payload-free, relative-path-only, and transient | `test_report_shape_bounds_and_no_payload` | not yet written |

## Rollback

Before acceptance, withdraw this proposal; no runtime or consumer data is changed. If accepted and later reversed, use a superseding ADR and preserve records already authored under the accepted format. No automatic deletion or migration is authorized.

## References

- Issue #128 and research checkpoint: https://github.com/ozand/kb-bootstrap/issues/128#issuecomment-6266256828
- Accepted ADR-031, ADR-010, ADR-017, ADR-024, ADR-026
- `docs/EVIDENCE_RETENTION.md`
