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

If accepted, define exact v1 JSON below. It is an observation, not authority, source truth, canonical knowledge, or proof merely because it parses. No implementation is authorized. The proposed v1 operation contract is intentionally local and bounded; future owner acceptance, not implementation discretion, decides whether to adopt it.

One UTF-8 JSON object, maximum 1 MiB, with exactly these keys and no unknown keys:
- `schema`: string exactly `kb-local-handoff/v1`.
- `record_id`: nonempty string <=128 UTF-8 bytes; stable caller-selected identity.
- `revision`: positive JSON integer (not boolean), incremented on successful save.
- `study_ref`: nonempty opaque string <=1024 bytes.
- `objective`: nonempty description <=2048 bytes.
- `scope`: object exactly `included`,`excluded`; each list <=32 nonempty strings <=256 bytes.
- `materials`: list <=100 objects exactly `ref`,`revision`,`observation`,`observed_scope`,`unread_remainder`,`analysis`,`analyzed_scope`,`unanalyzed_remainder`. Opaque ref/revision nonempty <=1024 bytes; ref unique. Observation `captured|partially-read|read`; analysis `not-started|partially-analyzed|analyzed`; scope/remainder strings <=512 bytes, empty allowed.
- `outputs`: list <=100 objects exactly `ref`,`revision`,`standing`,`acceptance_evidence_ref`; unique ref (so ref→revision is unambiguous), opaque ref/revision <=1024 bytes; standing `provisional|accepted`; evidence ref null or opaque string <=1024 bytes. Accepted standing requires nonnull evidence ref bound to that output revision.
- `steps`: list <=100 objects exactly `step_id`,`intent`,`input_revisions`,`state`,`output_revisions`,`required_evidence`,`observed_evidence`,`blocker`,`next_step`,`attempts`,`current_resumability`. Unique step ID <=128 bytes; intent <=1024; state `pending|partial|blocked|complete`; `partial` requires nonempty blocker/next step and an attempt with state `partial` plus at least one existing output revision or observed-evidence item. `complete` requires passing observed evidence for every required item. Blocker/next_step null or <=512; resumability `ready|blocked|revalidation-required|none`. Revision/evidence lists <=100; attempts <=20.
- `checks`: object exactly `run`,`not_run`, each <=100. Run item exactly `check,target,result,evidence_ref`; not-run exactly `check,target,reason`; strings <=512; result `passed|failed|unavailable`.
- `retention`: object exactly `owner,storage_class,storage_ref,retention_rule,access,integrity,availability,disposal`; strings <=512; availability `verified|not-verified|unavailable`. Descriptive, not permission/durability.
- `assumptions`,`open_questions`: lists <=32 strings <=512 bytes.
- `result_id`: lowercase 64-hex SHA-256 over compact UTF-8 JSON excluding this final key.
`study_state` is derived only, never input or persisted; its fixed statuses are `pending|partial|blocked|complete`. Study-state precedence: blocked if any step blocked; else partial if any step requires revalidation, any step partial, or a mixture of complete/pending; else pending if all pending or the step list is empty; else complete only if every nonempty step is historically complete with resumability `none`.

`input_revisions`/`output_revisions` items exactly `{ref,revision}`; `required_evidence` exactly `{ref,revision,kind}`; `observed_evidence` exactly `{ref,revision,result}`, result `passed|failed|unavailable`. `blocked` requires nonempty blocker. Every historical state is retained unchanged during checking. Pair values are opaque nonempty strings <=1024 bytes; `kind` same. Duplicate ref/revision pairs in any list are rejected. Attempts exactly `{attempt_id,input_revisions,output_revisions,required_evidence,observed_evidence,state,observed_at}`; ID unique <=128 bytes, same list rules, valid step state, descriptive timestamp <=64 bytes (not trusted time). Reject duplicate JSON keys at every level. Preserve top-level key order as listed and array order; never sort refs. Enforce UTF-8 byte limits; arbitrary nested values forbidden.

### Operations and boundaries

- **Load** reads only caller-selected file <=1 MiB; rejects invalid UTF-8, duplicate keys, malformed JSON, wrong types/keys/order/limits or digest mismatch. No session/directory discovery. Synthetic no-chat load proves no reference truth.
- **Check** accepts owner-selected checker and caller-selected inputs out of band; validates required references. Current completion requires matching input/output/evidence identities, required checks passed through owners, accepted standing with owner-validated evidence bound to output revision, and no blocker. Existence alone insufficient. Missing/stale/revoked/mismatch/failed blocks current resumability; unavailable/checker-error requires revalidation. History unchanged; no implicit save.
- **Retry** rechecks first. Identical step ID/intent/revisions may reuse a result only after successful revalidation; no duplicate completion or silent rerun. Same ID with differing intent/revisions conflicts.
- **Save** requires caller-selected destination and owner/storage/retention/access preconditions, including narrow local persistence permission established outside record. ADR-035 is read permission only. New record requires absent path and exclusive create; never overwrite. Replacement requires record ID, caller baseline result ID/revision, and currently stored identity/revision matching, re-read immediately under local exclusive-writer boundary before atomic same-directory replacement; revision increments exactly one. Stale baseline rejects. Validate candidate first; pre-replacement failure preserves prior authority. Post-replacement readback failure is unknown. No hostile filesystem or distributed-writer guarantee.
- No external writes/publication. Remote publication failure/lost acknowledgement is outside v1 and unknown; no retry/reconciliation defined.

Canonical payload is UTF-8, no BOM, compact `,`/`:` separators, no whitespace, no ASCII escaping except required JSON escapes, listed key order, no Unicode normalization. Hash encoded object without `result_id`; final object stores it last. Loader removes only final field and recomputes. Enforce bounds before digest. No serializer/runtime implementation included.

### Encoding, validation, and operations

Every object at every depth has this fixed key order: top level as listed; scope `included,excluded`; material and output order as listed; step order as listed; revision/evidence object orders as stated; attempt order as stated; checks `run,not_run`, their item orders as stated; retention order as stated. No optional keys; nullable values remain present. Load rejects any missing, extra, duplicate, or misordered key. Lists preserve caller order; no sorting. JSON input must be strict UTF-8 without BOM; reject unpaired surrogates, NUL and other Unicode C0 controls in strings, NaN/Infinity, all floats, and integer tokens outside signed 64-bit range. Integer-valued fields accept only JSON integer tokens (not booleans or exponent/fraction forms). All string fields are nonempty except explicitly nullable fields and scope/remainder fields; `blocker` must be nonnull for blocked state; optionality never means omitted. All limits are inclusive maximum UTF-8 bytes/counts as stated; duplicate IDs and duplicate ref/revision pairs are rejected.

Python-facing proposed signatures (return closed mappings, never raise for input/owner failures):
- `load_record(path) -> LoadResult`: exactly `{"status":"loaded","record":Record}` or `{"status":"invalid","reason":Reason}`. Reasons are `io-error|too-large|invalid-utf8|invalid-json|invalid-schema|digest-mismatch`. Reads only the selected file; record is validated JSON object including result_id.
- `check_record(record, checker) -> CheckResult`: checker is one callable `checker(ref: str, revision: str, kind: str) -> CheckObservation`; check all unique tuples required by referenced inputs, outputs, evidence, and acceptance; call once per unique `(ref,revision,kind)` in deterministic first-seen order. For `kind=input|output`, `passed` means the owner confirms this opaque identity and exact revision currently match its artifact. `kind=required:<kind>` means exact revision satisfies that owner's specified evidence check. `kind=acceptance` uses acceptance evidence ref and output revision; `passed` means owner confirms accepted standing bound to that exact output revision, not mere existence/hash. Output ref→revision is unique by output-ref uniqueness; accepted output needs a nonnull acceptance ref and it is checked once per distinct tuple. Attestation is a trust boundary: caller-selected checker is not authenticated by this contract; no registry/source grammar is defined. Observation is exactly `{"status": one of "passed","failed","missing","stale","revoked","unavailable","mismatch"}`. Wrong shape, exception or unexpected return is `checker-error`; it never passes. Result is `{"status":"checked","study_state":StudyState,"steps":[StepCheck...]}` or `{"status":"invalid","reason":Reason}`. StepCheck exactly `{"step_id":str,"historical_state":State,"current_resumability":Resumability,"evidence":[EvidenceCheck...]}`; EvidenceCheck exactly `{"ref":str,"revision":str,"kind":str,"status":EvidenceStatus}`; statuses `passed|failed|missing|stale|revoked|unavailable|mismatch|checker-error`. `failed|missing|stale|revoked|mismatch` -> blocked; unavailable/checker-error -> revalidation-required; passed all -> ready unless historical step is complete, then `none`. Check returns a derived view only; never changes record, historical state, attempts, or saves.
- `save_record(path, candidate, *, expected_record_id=None, expected_revision=None, expected_result_id=None, permission) -> SaveResult`: permission is an out-of-record caller decision for this exact path, action, owner, storage class, retention/access policy; denial returns `denied` before file inspection or write. Candidate is caller-supplied object without result_id; save validates, canonicalizes and computes it. SaveResult is exactly `{"status": SaveStatus,"record":Record|null,"result_id":str|null}`; statuses `created|replaced|denied|conflict|invalid|io-error|unknown`.

New absent-path save requires all expected fields null, revision 1, exclusive create; existing target returns conflict without reading/replacing. Replacement requires all three expected values present; under local exclusive-writer boundary read/validate current record, require exact record_id/revision/result_id match, then candidate record_id same and revision exactly current+1. Any mismatch is conflict and preserves bytes. Missing permission returns denied before target I/O. Candidate validation error is invalid. Pre-replacement I/O/atomic-replace failure is io-error and prior record remains authoritative; after successful replacement but failed readback returns unknown with null record/result_id, never retries or claims success. Success returns stored record and computed digest. No hostile filesystem/distributed guarantee; lock primitive is implementation-local, not a new service.

The owner-selected permission proposal is narrow local persistence for the named record/path and retention/access conditions from `docs/EVIDENCE_RETENTION.md`; it is outside JSON and distinct from ADR-035 validation-read permission. Denial forbids even inspecting the target. No policy engine/grant schema is defined.

## What this is not

No execution engine, CLI, daemon, plugin, generic lock/revision service, grant schema/policy engine, remote publisher, session discovery, transcript archive, source registry, knowledge promotion, deletion, or trust/canonicality claim. Proposed states are not owner-verified facts.

## Alternatives Considered

- Reuse the illustrative YAML vocabulary: rejected because JSON key, duplicate and digest rules need explicitness.
- Define a registry or grammar for references: rejected because identities remain owner-defined and caller-directed.
- Embed local write permission in the record: rejected because it would turn descriptive data into authority, contrary to ADR-022/035.
- Use distributed locks/CAS: rejected; no distributed guarantee is needed or claimed.

## Consequences

A later implementation has one bounded format and local save boundary; caller supplies checker and storage permission separately. Missing permission denies before I/O. Owner acceptance and required W09 decisions precede implementation.

## Test Contract

All tests below are future semantic tests, not written or run. `test_json_order_and_digest`: nested order, duplicate/unknown keys, invalid UTF-8/BOM/surrogates/control/nonfinite/float, limits and digest. `test_checker_outcomes_and_closed_results`: owner outcomes and malformed/exception mapping. `test_check_preserves_history`: historical state/attempts unchanged while current check blocks or requires revalidation. `test_step_state_matrix`: pending/partial/blocked/complete. `test_save_create_and_conflict`: revision-1 create, existing target conflict, permission denial before I/O. `test_save_compare_replace`: stored identity triple, stale rejection, revision increment and atomic replacement. `test_save_failure_outcomes`: pre-replace preservation and post-replace unknown. `test_synthetic_no_chat_and_privacy`: fixture without session discovery or prohibited data.

## Rollback

Before acceptance withdraw without migration. Reversal after acceptance requires superseding ADR; rollback does not delete records.

## References

- Issue #129 checkpoint: https://github.com/ozand/kb-bootstrap/issues/129#issuecomment-6374807260
- Accepted ADR-024, ADR-026, ADR-031, ADR-032, ADR-035; `docs/EVIDENCE_RETENTION.md`.
- W08 proposal/fixtures are design material, not accepted schema precedent. PR #137 remains unaccepted.

## Synthetic fixture

`docs/fixtures/ADR-038-local-handoff-example.json` supplies partial progress and a completed historical step with currently unavailable evidence. It is not owner-validated evidence or implementation.
