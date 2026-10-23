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
- `outputs`: list <=100 objects exactly `ref`,`revision`,`standing`,`acceptance_evidence_ref`; unique ref, opaque ref/revision <=1024 bytes; standing `provisional|accepted`; evidence ref null or opaque string <=1024 bytes.
- `steps`: list <=100 objects exactly `step_id`,`intent`,`input_revisions`,`state`,`output_revisions`,`required_evidence`,`observed_evidence`,`blocker`,`next_step`,`attempts`,`current_resumability`. Unique step ID <=128 bytes; intent <=1024; state `pending|partial|blocked|complete`; `partial` requires a nonempty blocker or next step and bounded partial observation in an attempt; `complete` requires owner-checked required evidence. Blocker/next_step null or <=512; resumability `ready|blocked|revalidation-required|none`. Revision/evidence lists <=100; attempts <=20.
- `checks`: object exactly `run`,`not_run`, each <=100. Run item exactly `check,target,result,evidence_ref`; not-run exactly `check,target,reason`; strings <=512; result `passed|failed|unavailable`.
- `retention`: object exactly `owner,storage_class,storage_ref,retention_rule,access,integrity,availability,disposal`; strings <=512; availability `verified|not-verified|unavailable`. Descriptive, not permission/durability.
- `assumptions`,`open_questions`: lists <=32 strings <=512 bytes.
- `result_id`: lowercase 64-hex SHA-256 over compact UTF-8 JSON excluding this final key.
`study_state` is derived only, never input or persisted; its fixed statuses are `pending|partial|blocked|complete`.

`input_revisions`/`output_revisions` items exactly `{ref,revision}`; `required_evidence` exactly `{ref,revision,kind}`; `observed_evidence` exactly `{ref,revision,result}`, result `passed|failed|unavailable`. `partial` requires nonempty blocker or next step and an attempt with partial outcome; `blocked` requires a nonempty blocker; `complete` requires passing observations for every required item. This is historical observation, not proof. Study-state precedence: blocked if any step blocked; else partial if any partial or mixture of complete/pending; else pending if all pending; else complete if all complete. Pair values are opaque nonempty strings <=1024 bytes; `kind` same. Duplicate ref/revision pairs in any list are rejected. Attempts exactly `{attempt_id,input_revisions,output_revisions,required_evidence,observed_evidence,state,observed_at}`; ID unique <=128 bytes, same list rules, valid step state, descriptive timestamp <=64 bytes (not trusted time). Reject duplicate JSON keys at every level. Preserve top-level key order as listed and array order; never sort refs. Enforce UTF-8 byte limits; arbitrary nested values forbidden.

### Operations and boundaries

- **Load** reads only caller-selected file <=1 MiB; rejects invalid UTF-8, duplicate keys, malformed JSON, wrong types/keys/order/limits or digest mismatch. No session/directory discovery. Synthetic no-chat load proves no reference truth.
- **Check** accepts owner-selected checkers and caller-selected inputs out of band; revalidates each required evidence ref. Current completion requires matching input/output/evidence identities, required checks passed through owners, accepted standing with owner-validated evidence bound to output revision, and no blocker. Existence alone insufficient. Missing/stale/revoked/mismatch blocks current resumability; unavailable/checker-error requires revalidation. History unchanged; no implicit save.
- **Retry** rechecks first. Identical step ID/intent/revisions may reuse a result only after successful revalidation; no duplicate completion or silent rerun. Same ID with differing intent/revisions conflicts.
- **Save** requires caller-selected destination and owner/storage/retention/access preconditions, including narrow local persistence permission established outside record. ADR-035 is read permission only. New record requires absent path and exclusive create; never overwrite. Replacement requires record ID, caller baseline result ID/revision, and currently stored identity/revision matching, re-read immediately under local exclusive-writer boundary before atomic same-directory replacement; revision increments exactly one. Stale baseline rejects. Validate candidate first; pre-replacement failure preserves prior authority. Post-replacement readback failure is unknown. No hostile filesystem or distributed-writer guarantee.
- No external writes/publication. Remote publication failure/lost acknowledgement is outside v1 and unknown; no retry/reconciliation defined.

Canonical payload is UTF-8, no BOM, compact `,`/`:` separators, no whitespace, no ASCII escaping except required JSON escapes, listed key order, no Unicode normalization. Hash encoded object without `result_id`; final object stores it last. Loader removes only final field and recomputes. Enforce bounds before digest. No serializer/runtime implementation included.

### Encoding, validation, and operations

Every object at every depth has this fixed key order: top level as listed; scope `included,excluded`; material and output order as listed; step order as listed; revision/evidence object orders as stated; attempt order as stated; checks `run,not_run`, their item orders as stated; retention order as stated. No optional keys; nullable values remain present. Load rejects any missing, extra, duplicate, or misordered key. Lists preserve caller order; no sorting. JSON input must be strict UTF-8 without BOM; reject unpaired surrogates, NUL and other Unicode C0 controls in strings, NaN/Infinity, all floats, and integer tokens outside signed 64-bit range. Integer-valued fields accept only JSON integer tokens (not booleans or exponent/fraction forms). All string fields are nonempty except explicitly nullable fields and scope/remainder fields; `blocker` must be nonnull for blocked state; optionality never means omitted. All limits are inclusive maximum UTF-8 bytes/counts as stated; duplicate IDs and duplicate ref/revision pairs are rejected.

Python-facing proposed signatures (return closed mappings, never raise for input/owner failures):
- `load_record(path) -> LoadResult`: exactly `{"status":"loaded","record":Record}` or `{"status":"invalid","reason":Reason}`. Reasons are `io-error|too-large|invalid-utf8|invalid-json|invalid-schema|digest-mismatch`. Reads only the selected file; record is validated JSON object including result_id.
- `check_record(record, checker) -> CheckResult`: checker is one callable `checker(ref: str, revision: str, kind: str) -> CheckObservation`; called for each required evidence tuple. Observation is exactly `{"status": one of "passed","missing","stale","revoked","unavailable","mismatch"}`. Wrong shape, exception or unexpected return is `checker-error`; it never passes. Result is `{"status":"checked","study_state":StudyState,"steps":[StepCheck...]}` or `{"status":"invalid","reason":Reason}`. StepCheck exactly `{"step_id":str,"historical_state":State,"current_resumability":Resumability,"evidence":[EvidenceCheck...]}`; EvidenceCheck exactly `{"ref":str,"revision":str,"kind":str,"status":EvidenceStatus}`. Missing/stale/revoked/mismatch -> blocked; unavailable/checker-error -> revalidation-required; passed all -> ready unless historical step is complete, then `none`. Check returns a derived view only; never changes record, historical state, attempts, or saves.
- `save_record(path, candidate, *, expected_record_id=None, expected_revision=None, expected_result_id=None, permission) -> SaveResult`: permission is an out-of-record caller decision for this exact path, action, owner, storage class, retention/access policy; denial returns `denied` before file inspection or write. Candidate is caller-supplied object without result_id; save validates, canonicalizes and computes it. SaveResult is exactly `{"status": SaveStatus,"record":Record|null,"result_id":str|null}`; statuses `created|replaced|denied|conflict|invalid|io-error|unknown`.

New absent-path save requires all expected fields null, revision 1, exclusive create; existing target returns conflict without reading/replacing. Replacement requires all three expected values present; under local exclusive-writer boundary read/validate current record, require exact record_id/revision/result_id match, then candidate record_id same and revision exactly current+1. Any mismatch is conflict and preserves bytes. Missing permission returns denied before target I/O. Candidate validation error is invalid. Pre-replacement I/O/atomic-replace failure is io-error and prior record remains authoritative; after successful replacement but failed readback returns unknown with null record/result_id, never retries or claims success. Success returns stored record and computed digest. No hostile filesystem/distributed guarantee; lock primitive is implementation-local, not a new service.

`study_state` is not an input key and never persisted; it appears only in CheckResult. CheckResult returns exactly `{"status":"checked","study_state":StudyState,"steps":[...]}` where StudyState is `pending|partial|blocked|complete`. Steps are returned in record order. Invalid outer input returns `{"status":"invalid","reason":"invalid-record"}`. A checker exception/wrong return maps to per-reference `checker-error`, keeps other observations, and sets affected resumability to `revalidation-required`; it does not raise. Check every unique input revision (`kind=input`), output revision (`kind=output`), required evidence (`kind=required:<kind>`), and accepted output's acceptance evidence (`kind=acceptance`, revision=output revision); preserve deterministic traversal order (steps, then inputs, outputs, required evidence, acceptance evidence). EvidenceCheck includes `kind`; statuses are `passed|missing|stale|revoked|unavailable|mismatch|checker-error`. Missing/stale/revoked/mismatch yields blocked; unavailable/checker-error revalidation-required. A step already historically complete keeps that state; check derives its current resumability only. StudyState precedence is blocked if any derived step blocked; else partial if any partial or a mixture of complete/pending; else pending if all pending; else complete if all complete and currently ready.

New record creation starts at revision 1 with all expected baseline arguments null. If path exists, conflict without opening it. Replacement requires all three expected values; under the writer boundary, permission permitting, load and validate current stored record, compare record_id, revision and result_id exactly to expected triple, then require candidate same record_id and current revision + 1. Candidate contains no result_id; save computes digest after canonical serialization and returns persisted record/result identity on created/replaced only. Conflict/denied/invalid/io-error/unknown return null record and result_id. Denial precedes any path I/O. Candidate invalidity is invalid without write. Before atomic replacement errors are io-error and leave prior record authoritative; any uncertainty after replacement is unknown, with no automatic retry.

The owner-selected permission proposal is narrow local persistence for the named record/path and retention/access conditions from `docs/EVIDENCE_RETENTION.md`; it is outside JSON and distinct from ADR-035 validation-read permission. Denial forbids even inspecting the target. No policy engine/grant schema is defined.

### Current-check result and creation/replacement outcomes

`study_state` is derived only, never input/persisted; statuses `pending|partial|blocked|complete`. CheckResult: `{"status":"checked","study_state":StudyState,"steps":[StepCheck...]}` with steps in record order; invalid outer input is `{"status":"invalid","reason":"invalid-record"}`. A checker exception/wrong return maps to per-reference `checker-error`, keeps other observations, and never raises. Check every unique input/output revision (`kind=input|output`), required evidence (`kind=required:<kind>`), and accepted output acceptance evidence (`kind=acceptance`, output revision); order by step, inputs, outputs, required evidence, acceptance evidence. StepCheck is exactly `{step_id,historical_state,current_resumability,evidence}`; EvidenceCheck exactly `{ref,revision,kind,status}`. Evidence status is `passed|missing|stale|revoked|unavailable|mismatch|checker-error`; blocked for missing/stale/revoked/mismatch, revalidation-required for unavailable/checker-error. A historically complete step retains state and attempts; Check only derives resumability. Study state blocked if any blocked; else partial if any partial or mix of complete/pending; else pending if all pending; else complete if all complete and ready.

New absent-path save has all baseline arguments null and candidate revision 1; existing target conflicts without opening/replacing. Replacement requires all expected values, loads current stored record under writer boundary, compares exact record_id/revision/result_id, and requires candidate same record_id and revision current+1. Candidate has no result_id; save computes it. Success returns persisted record and digest. Conflict/denied/invalid/io-error/unknown return null record/result_id. Denial precedes path I/O. Pre-replacement errors preserve prior authority and return io-error; after replacement uncertainty returns unknown, no retry.

## Alternatives Considered

- Reuse the illustrative YAML vocabulary: rejected because JSON key, duplicate and digest rules need explicitness.
- Define a registry or grammar for references: rejected because these identities remain owner-defined and caller-directed.
- Embed local write permission in the record: rejected because it would turn descriptive data into authority and conflict with ADR-022/035 boundaries.
- Use distributed locks/CAS: rejected because no distributed guarantee is needed or claimed.

## Consequences

A later implementation has one bounded format and local save boundary; caller supplies evidence checker and storage permission separately. Missing permission denies before I/O. Owner acceptance and required W09 decisions precede implementation.

## Test Contract

All tests named below are future semantic tests, not written or run. `test_json_order_and_digest`: nested order, duplicate/unknown keys, invalid UTF-8/BOM/surrogates/control/nonfinite/float, bounds and digest. `test_checker_outcomes_and_closed_results`: each owner outcome and malformed/exception mapping. `test_check_preserves_history`: complete historical state/attempts unchanged while current status blocks or requires revalidation. `test_step_state_matrix`: pending/partial/blocked/complete invariants. `test_save_create_and_conflict`: revision-1 exclusive create, existing path conflict, permission denial before I/O. `test_save_compare_replace`: current triple CAS, stale rejection, increment and same-directory atomic replacement. `test_save_failure_outcomes`: pre-replace preservation and post-replace unknown. `test_synthetic_no_chat_and_privacy`: fixture loads without session discovery and contains no prohibited data.

## Rollback

Before acceptance withdraw without migration. Reversal after acceptance requires superseding ADR; rollback does not delete records.

## References

- Issue #129 checkpoint: https://github.com/ozand/kb-bootstrap/issues/129#issuecomment-6374807260
- Accepted ADR-024, ADR-026, ADR-031, ADR-032, ADR-035; `docs/EVIDENCE_RETENTION.md`.
- W08 proposal/fixtures are design material, not accepted schema precedent. PR #137 remains unaccepted.

## Synthetic fixtures

`docs/fixtures/ADR-038-local-handoff-example.json` supplies a pending partial-analysis step and a completed historical step whose current evidence can be stale. It is not owner-validated evidence or implementation.
