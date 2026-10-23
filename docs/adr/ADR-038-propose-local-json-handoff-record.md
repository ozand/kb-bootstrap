# ADR-038: Propose a bounded local JSON handoff record

**Status**: Proposed
**Date**: 2026-10-23
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #129; ADR-010, ADR-021, ADR-022, ADR-024, ADR-026, ADR-031, ADR-032, ADR-035

## Context

Accepted ADR-032 defines progress observations, not a persisted format. Issue #129 asks another process to continue from a supplied local record and retained artifacts without chat history. This proposal chooses one JSON shape and save/load/check contract. ADR-035 permits scoped validation reads, not local persistence. W09/#130 remains open; broader PR #137 is not accepted. W03/#124 owns evidence interpretation; no source registry is duplicated.

Research checkpoint: https://github.com/ozand/kb-bootstrap/issues/129#issuecomment-6374807260. ADR-032 controls historical/current completion distinction, independent reading/analysis axes, opaque references, retry revalidation, and local writer boundaries.

## Decision

If accepted, define exact v1 JSON below. It is an observation, not authority, source truth, canonical knowledge, or proof merely because it parses. No implementation is authorized.

One UTF-8 JSON object, maximum 1 MiB, with exactly these keys and no unknown keys:
- `schema`: string exactly `kb-local-handoff/v1`.
- `record_id`: nonempty string <=128 UTF-8 bytes; stable caller-selected identity.
- `revision`: positive JSON integer (not boolean), incremented on successful save.
- `study_ref`: nonempty opaque string <=1024 bytes.
- `objective`: nonempty description <=2048 bytes.
- `scope`: object exactly `included`,`excluded`; each list <=32 nonempty strings <=256 bytes.
- `materials`: list <=100 objects exactly `ref`,`revision`,`observation`,`observed_scope`,`unread_remainder`,`analysis`,`analyzed_scope`,`unanalyzed_remainder`. Opaque ref/revision nonempty <=1024 bytes; ref unique. Observation `captured|partially-read|read`; analysis `not-started|partially-analyzed|analyzed`; scope/remainder strings <=512 bytes, empty allowed.
- `outputs`: list <=100 objects exactly `ref`,`revision`,`standing`,`acceptance_evidence_ref`; unique ref, opaque ref/revision <=1024 bytes; standing `provisional|accepted`; evidence ref null or opaque string <=1024 bytes.
- `steps`: list <=100 objects exactly `step_id`,`intent`,`input_revisions`,`state`,`output_revisions`,`required_evidence`,`observed_evidence`,`blocker`,`next_step`,`attempts`,`current_resumability`. Unique step ID <=128 bytes; intent <=1024; state `pending|blocked|complete`; blocker/next_step null or <=512; resumability `ready|blocked|revalidation-required|none`. Revision/evidence lists <=100; attempts <=20.
- `checks`: object exactly `run`,`not_run`, each <=100. Run item exactly `check,target,result,evidence_ref`; not-run exactly `check,target,reason`; strings <=512; result `passed|failed|unavailable`.
- `retention`: object exactly `owner,storage_class,storage_ref,retention_rule,access,integrity,availability,disposal`; strings <=512; availability `verified|not-verified|unavailable`. Descriptive, not permission/durability.
- `assumptions`,`open_questions`: lists <=32 strings <=512 bytes.
- `result_id`: lowercase 64-hex SHA-256 over compact UTF-8 JSON excluding this final key.

`input_revisions`/`output_revisions` items exactly `{ref,revision}`; `required_evidence` exactly `{ref,revision,kind}`; `observed_evidence` exactly `{ref,revision,result}`, result `passed|failed|unavailable`. Pair values are opaque nonempty strings <=1024 bytes; `kind` same. Duplicate ref/revision pairs in any list are rejected. Attempts exactly `{attempt_id,input_revisions,output_revisions,required_evidence,observed_evidence,state,observed_at}`; ID unique <=128 bytes, same list rules, valid step state, descriptive timestamp <=64 bytes (not trusted time). Reject duplicate JSON keys at every level. Preserve top-level key order as listed and array order; never sort refs. Enforce UTF-8 byte limits; arbitrary nested values forbidden.

### Operations and boundaries

- **Load** reads only caller-selected file <=1 MiB; rejects invalid UTF-8, duplicate keys, malformed JSON, wrong types/keys/order/limits or digest mismatch. No session/directory discovery. Synthetic no-chat load proves no reference truth.
- **Check** accepts owner-selected checkers and caller-selected inputs out of band; revalidates needed refs. Current completion requires matching input/output/evidence identities, required checks passed through owners, accepted standing with owner-validated evidence bound to output revision, and no blocker. Existence alone insufficient. Missing/stale/revoked/unavailable blocks or requires revalidation. History unchanged; no implicit save.
- **Retry** rechecks first. Identical step ID/intent/revisions may reuse a result only after successful revalidation; no duplicate completion or silent rerun. Same ID with differing intent/revisions conflicts.
- **Save** requires caller-selected destination and owner/storage/retention/access preconditions, including narrow local persistence permission established outside record. ADR-035 is read permission only. New record requires absent path and exclusive create; never overwrite. Replacement requires record ID, caller baseline result ID/revision, and currently stored identity/revision matching, re-read immediately under local exclusive-writer boundary before atomic same-directory replacement; revision increments exactly one. Stale baseline rejects. Validate candidate first; pre-replacement failure preserves prior authority. Post-replacement readback failure is unknown. No hostile filesystem or distributed-writer guarantee.
- No external writes/publication. Remote publication failure/lost acknowledgement is outside v1 and unknown; no retry/reconciliation defined.

Canonical payload is UTF-8, no BOM, compact `,`/`:` separators, no whitespace, no ASCII escaping except required JSON escapes, listed key order, no Unicode normalization. Hash encoded object without `result_id`; final object stores it last. Loader removes only final field and recomputes. Enforce bounds before digest. No serializer/runtime implementation included.

## What this is not

No execution engine, CLI, daemon, plugin, generic lock/revision service, grant schema/policy engine, remote publisher, session discovery, transcript archive, source registry, knowledge promotion, deletion, or trust/canonicality claim. Proposed states are not owner-verified facts.

## Alternatives Considered

- Reuse ADR-032 illustrative YAML: rejected; JSON parsing, duplicate/unknown keys and byte identity remain unspecified.
- Define reference grammar/registry: rejected; identities belong to owner interfaces; discovery exceeds scope.
- Let record grant write authority: rejected; ADR-022/035 separate selection/read/write; W09 remains open.
- Distributed CAS/lock service: rejected; only local exclusive writer boundary, no hostile/distributed guarantee.

## Consequences

A later implementation can test one bounded shape and local save boundary. Caller supplies checkers and storage permission separately; missing policy blocks save. Owner acceptance and required W09 decisions precede implementation.

## Test Contract

Future semantic tests, not written: schema/limits/order/digest and duplicate/unknown rejection; synthetic no-chat load; independent observation/analysis; completion requires owner-validated evidence, matching revisions and passing checks; stale/revoked evidence preserves history but blocks current resumability; retry revalidates without duplication; stale baseline rejects after reading current identity; exclusive create never overwrites; pre-replacement failure preserves record; no external writes; fixture excludes sensitive content.

## Rollback

Before acceptance withdraw without migration. Reversal after acceptance requires superseding ADR; rollback does not delete records.

## References

- Issue #129 checkpoint: https://github.com/ozand/kb-bootstrap/issues/129#issuecomment-6374807260
- Accepted ADR-024, ADR-026, ADR-031, ADR-032, ADR-035; `docs/EVIDENCE_RETENTION.md`.
- W08 proposal/fixtures are design material, not accepted schema precedent. PR #137 remains unaccepted.

## Synthetic fixture

`docs/fixtures/ADR-038-local-handoff-example.json` is a pending example with independent reading/analysis scopes; its digest excludes final `result_id`. It proves no implementation or approval.
