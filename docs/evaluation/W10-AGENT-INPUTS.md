# W10-A agent inputs

Status: **Draft; wholly synthetic agent-visible fixture.** No expected answers appear here. Revision instructions are defined by the external runner; fragment IDs are stable citations.

## Project-management fixture

### PM-S1 — T0 exact capture
Northstar team note, 2026-04-03: “Pulse” is a 20-minute review for a delivery group **only when** it has at least two active workstreams sharing one release dependency. It is not a daily stand-up. Mira Volkova facilitates during the April pilot. The note recommends, but does not require, holding Pulse on Tuesday.

### PM-S2 — T0 manual summary
Summary written 2026-04-04; original workshop recording is unavailable. A participant remembered that Pulse was “обязательный для всех проектов” and that Morgan Lee facilitated. Exact wording and the speaker cannot be checked.

### PM-S3 — T0 case note
Northstar had one active workstream on 2026-04-08. Команда не проводила Pulse; it used its normal weekly review. No missed dependency was recorded in this case note.

### PM-S1R — T1 replaces PM-S1
Northstar team note, revision 2026-05-02: “Pulse” is a 20-minute review for a delivery group **only when** it has at least three active workstreams sharing one release dependency. It is not a daily stand-up. Mira Volkova facilitates during the May pilot. Tuesday remains a recommendation, not a requirement.

### PM-S4 — T1 adds contradictory exact capture
Programme memo, 2026-05-03: teams with two or more active workstreams should trial Pulse even without a shared release dependency. This is the programme lead's recommendation; it does not amend the Northstar method note and does not make Pulse mandatory.

## Agent-system research fixture

### AR-S1 — T0 exact capture, repository Finch
`finch/tools/relay.py`, revision `f1`: component `Relay` reads a local queue. In the supplied test transcript, retry is attempted twice after the initial failure (three attempts total); it does not send HTTP requests. This observation covers only the supplied test path.

### AR-S2 — T0 README capture, repository Finch
`finch/README.md`, revision `f1`: “Relay retries three times and then uploads the batch.” No code location or execution evidence accompanies this sentence.

### AR-S3 — T0 exact capture, repository Lark
`lark/ui/relay.ts`, revision `l7`: component `Relay` is a status-view renderer. It reads a provided JSON object, does not read a queue, and has no retry loop. Same display name, different repository and role.

### AR-S4 — blocked evidence record
The Finch CI artifact for revision `f1` is unavailable (`retention expired`). No log body, exit status, or network trace was retained. Do not treat the missing artifact as a successful or failed run.

### AR-S1R — T1 replaces AR-S1
`finch/tools/relay.py`, revision `f2`: component `Relay` reads a local queue. Retry is disabled when `offline=true`; otherwise one retry follows the initial failure (two attempts total). The supplied test transcript covers `offline=true` and shows one attempt with no HTTP request. It does not cover `offline=false`.

### AR-S5 — T1 adds mixed-language review note
Review note for Finch `f2`: “README ещё описывает upload; кодовый путь изменён. Не считать отсутствие HTTP в offline-тесте доказательством для online режима.” Lark revision `l7` was not changed or re-tested.

## Infrastructure fixture

### IO-S1 — T0 intended configuration
Cache node `Cedar` policy, 2026-06-01: desired package is `cachebox 4.2`; service should listen on loopback only. The policy is an intended state, not evidence of the node's observed state and not authorization to change it.

### IO-S2 — T0 synthetic observation
Sanitized inspection, 2026-06-02: Cedar reports `cachebox 4.1`; listener `127.0.0.1:7400`; health is degraded. Collection did not inspect firewall rules. “No external listener observed” is limited to this supplied socket listing.

### IO-S3 — T0 troubleshooting note
Procedure P7, 2026-06-02: if health is degraded **and** free disk is above 15%, restart once; do not purge the cache. Operator approval is required before restart. If disk evidence is absent, stop and collect it.

### IO-S3R — T1 replaces IO-S3
Procedure P8, 2026-06-10; P7 is superseded. Если health=degraded и свободно не менее 20%, first validate the local index. Restart once only if validation reports `clean`, and only with operator approval. **Не очищать cache.** If disk or validation evidence is absent, stop; do not infer a safe repair.

### IO-S4 — T1 adds converted representation
Supplied converted-monitor image text, timestamp 2026-06-11: `Cedar / cachebox 4.2 / health degraded / free 23%`. Conversion coordinates are not available. No validation result, listener listing, or operator approval appears in this representation.

## Interrupted handoff fixture

### X-H1 — first-process event
At T1, process A verified the exact presence and revision labels of `PM-S1R`, `PM-S4`, `AR-S1R`, and `IO-S3R`. It then recorded `AR-S4` as unavailable. It was interrupted before checking `AR-S5`, `IO-S4`, unchanged Lark material, or answering Q3/Q6/Q8. No canonical answer was written.

### X-H2 — retained handoff state
Resume token `synthetic-handoff-02`. Retained active-T1 input SHA-256: `8d080ddec4ecdfdf42fa5d082c7192cfb8e38bda038b058197bd4c41963f3cb0`. Completed: revision-label check for `PM-S1R`, `PM-S4`, `AR-S1R`, `IO-S3R`; availability check for `AR-S4`. Remaining: inspect `AR-S5`, `IO-S4`, verify `AR-S3` is unchanged, then answer Q3/Q6/Q8 with citations. Do not repeat completed checks unless a recomputed active-T1 input hash differs. The digest covers only the non-handoff active-T1 material defined in the specification, so this digest-bearing fragment is not in its own hash input. This workflow note is not domain evidence and is not a canonical answer.
