# ADR-026: Look up caller-selected retained evidence without discovery

**Status**: Accepted
**Date**: 2026-10-09
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #124; ADR-010, ADR-022, ADR-024, ADR-025

Owner acceptance: Issue #124, comment 6074593249 (2026-10-09), scoped to reviewed implementation contract at `7591abdb6f593a1e53ab4ffad9241b0944c4f9bd`; no implementation is authorized by this status change.

## Context

Issue #124 requires reverse navigation to available evidence and an honest unavailable result where the original was not retained. The accepted ADR-024 validator operates on explicit metadata, project root, ADR-010 corpus root, and selected representation paths. It performs bounded read-only checks and digest validation; it does not enumerate the corpus or dereference origin descriptors. ADR-010 makes manifests explicit inputs and raw paths corpus-relative. ADR-022 distinguishes local reads/writes, review, and external publication authority. No lookup API currently returns source-to-retained-representation references. This is directly inspected at main `73277fdb3e54184901f67268bc676a562b0a677a`; this ADR proposes a future read-only behavior, not an implementation.

### Problem statement

A caller needs a bounded way to navigate from an explicitly identified source record to the retained representation evidence that was actually validated, without scanning a repository, disclosing absolute paths or source bodies, or implying an unavailable original can be recovered.

## Decision

If accepted, provide a caller-directed read-only lookup over one explicitly supplied ADR-024 envelope and its explicitly selected retained bytes. It returns bounded evidence references and availability distinctions; it does not return payloads. This proposal does not authorize implementation.

### What this IS

1. The caller supplies a project root, metadata path relative to that root, ADR-010 corpus root relative to the project, one `source_id`, and the complete explicit path set for every representation declared retained anywhere in the supplied envelope. Validate the entire envelope and all those selected retained bytes with the existing ADR-024 validator, then filter the validated result to the requested source. Do not add a source-only validator mode. Do not discover metadata, manifests, source IDs, or corpus members.
2. Missing, duplicate, extra, unsafe, or digest-mismatched retained-member paths make the supplied envelope invalid and return `BLOCKED`; they are not an ordinary unavailable-source result. If the requested source validly has no retained representation (for example, reference-only/unknown original with no output), return an honest `UNAVAILABLE` result. The operation never silently omits a member to produce partial navigation.
3. The result contains the requested source ID, bounded validated origin kind/reference category without echoing the origin value, capture/fidelity classifications, and a deterministic list of that source's representation IDs, declared digests, and corpus-relative `raw_path` references. It contains no source body, raw representation bytes, absolute paths, host paths, or unbounded/unvalidated metadata strings.
4. Report original availability separately from representation availability. `representation-verified` means the exact selected representation bytes were read and matched their declared digest during whole-envelope validation. `original-retained-verified` is permitted only when the record declares `original_retention: retained`, the original revision has a known SHA-256, and a retained representation was actually validated with that digest under ADR-024's exact/retention rules. A coincidentally matching representation digest without the declared retained-original status is insufficient. `original-reference-only` and `original-unknown` remain distinct even if a representation exists; a digest alone never proves source truth.
5. Return only relative path references within the explicit corpus plus the observed validation status. Results are deterministic for unchanged explicit inputs. Bounds are inherited from ADR-024 and the validator: metadata <=8 MiB, <=1000 sources, <=100 representations/source, each selected file <=64 MiB, aggregate selected bytes <=256 MiB. Exceeding a bound blocks with a sanitized category; the operation does not truncate or silently omit evidence.
6. Read-only means no writes, repair, indexing, cache, registration, network access, origin dereference, archive extraction, or follow-up retrieval. A caller needing a different source must make a new explicit request. Tool availability and permission/retention labels do not grant read, write, review, acquisition, or publication authority.
7. ADR-025's proposed archive is not an input to this lookup. Archive reading/indexing/extraction is a separate decision and is not authorized here.

### What this IS NOT

This is not a tree-wide search, global source registry, cross-study identity service, graph/corroboration engine, user interface, public CLI, archive reader, source downloader, re-fetch operation, access-control engine, or raw-content response. It does not claim that an origin reference is reachable, that an original was retained, or that a validated representation is factually true. It changes no existing persisted schema or validator API; the proposed lookup result/status behavior itself remains a new operation contract pending owner acceptance. It does not change ADR-010 or ADR-024.

### Success criteria

For one requested source, a future implementation validates the complete explicitly supplied envelope and complete retained-member set, then returns only that source's validated bounded references in stable order. It distinguishes valid no-retained-evidence (`UNAVAILABLE`) from malformed or missing declared-retained evidence (`BLOCKED`), reports original availability separately from representation verification, and performs zero discovery, origin access, writes, or payload disclosure.

## Consequences

### What gets easier

A caller can navigate from a known source record to exact validated local evidence references and distinguish them from an unavailable or reference-only original.

### What gets harder

Callers must already know the metadata path, source ID, corpus root, and complete representation member selection. Each lookup revalidates selected bytes and can incur bounded I/O; it cannot provide global search or cached results.

### What does not change

ADR-010 remains the explicit raw inventory contract; ADR-024 remains the source/capture validation contract; ADR-022 authority distinctions remain; no origin fetch, source acquisition, consumer write, public schema, CLI, or archive extraction is introduced.

## Alternatives Considered

- **Scan all metadata and raw files for a matching source:** rejected because it expands scope, performs discovery, and conflicts with the explicit-input/no-tree-enumeration boundary.
- **Return all raw bytes in the lookup result:** rejected because navigation requires addressable references, not duplicated potentially sensitive payloads; it increases disclosure and unbounded output risk.
- **Fetch an origin when local bytes are missing:** rejected because references are non-dereferenced descriptors and network access is a separate external action requiring its own authority and contract.
- **Treat a matching representation digest as proof the original is retrievable or true:** rejected because a digest binds supplied bytes only; original retention and factual provenance are separate claims.
- **Index ADR-025 archives automatically:** rejected because ADR-025 proposes an output artifact, not a corpus store or reader, and archive discovery/extraction is outside this decision.
- **Do nothing:** leaves #124's reverse-navigation criterion without a bounded design, while existing metadata remains usable only through direct inspection.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| Lookup validates the full supplied envelope and every retained member before filtering to the caller's source | `tests/test_source_evidence_lookup.py::test_full_envelope_validated_before_source_filter` | Not yet written |
| Returned paths are relative, sorted, bounded, and contain no payload/absolute path | `tests/test_source_evidence_lookup.py::test_result_is_bounded_relative_and_payload_free` | Not yet written |
| Original-retained status requires the declared retained state plus a verified matching digest | `tests/test_source_evidence_lookup.py::test_original_retention_requires_declared_state_and_digest` | Not yet written |
| Valid no-retained-evidence is unavailable; missing/digest-mismatched declared-retained evidence blocks | `tests/test_source_evidence_lookup.py::test_unavailable_distinguished_from_invalid_retained_input` | Not yet written |
| No tree enumeration, origin dereference, cache, or write occurs | `tests/test_source_evidence_lookup.py::test_lookup_has_no_discovery_or_side_effects` | Not yet written |

## Rollback

Before acceptance, withdraw this proposal. If accepted and later implemented, revert only the lookup operation; no stored registry or generated state should require migration. Any future index, cache, archive reader, or broader navigation behavior requires a separate decision.

## References

- Issue #124 and updated research checkpoint: https://github.com/ozand/kb-bootstrap/issues/124#issuecomment-6071669577
- ADR-010, ADR-022, ADR-023 (superseded by ADR-024), ADR-024, proposed ADR-025
- `kb_bootstrap/source_capture_validation.py`; `docs/EVIDENCE_RETENTION.md`
