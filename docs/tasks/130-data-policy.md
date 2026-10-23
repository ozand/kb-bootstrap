# W09-A: data policy and negative-case design

Status: execution brief only. Parent: #130; programme: #121. The owner requested parallel executors on 2026-09-28. This is a bounded policy proposal, not production enforcement, certification or approval of a new contract.

Repository: `ozand/kb-bootstrap`. Branch: `codex/w09-data-policy`. Main baseline: `9717bc29c7ab455cc8a7648c8f740e7f9959967a`. Work from this PR's seed/head. Do not modify #134, #135 or other workers' branches.

## Read before drafting

Read issue #130 and comments, `docs/CONTRIBUTING_UPSTREAM.md`, `docs/EVIDENCE_RETENTION.md`, `docs/adr/INDEX.md`, Accepted ADR-014 and the ADR-011/013 clauses it retains. Inspect relevant source/candidate/publication contracts and #108/#109 boundaries. Optional planning context: commit `30cdbdb14731caa3affee277f9e53547b7944999`, `docs/implementation/ARCHITECTURE_PROPOSAL.md` and `EVALUATION_PLAN.md`. Missing optional context is a recorded limitation, not a reason to merge an unrelated PR.

## Deliverable and exclusive write scope

Create only `docs/proposals/W09-data-policy.md` (target at most 180 lines). Keep this seed unchanged. Use an unnumbered Proposed ADR structure: current evidence, threat model, proposed rules, alternatives, acceptance cases, compatibility and rollback. D09 is a topic, not an assigned ADR number. Do not edit existing retention guidance, shared indexes, AGENTS.md, runtime code, templates or CI; propose later amendments by reference.

Cover these concrete requirements:
- separate sensitivity, applicability, reader scope, write/review authority and permission to execute actions;
- cover originals, conversion, raw, indexes, queries, extraction, synthesis, viewers, publication and backups;
- distinguish explicit authorized capture/acquisition from local-core operations that must not silently make network calls or publish to configured remotes;
- preserve ADR-014 ordinary `local-smoke-verified; host-egress-unverified` and the separate verified-host boundary for sensitive processing; do not turn all sanitized work into mandatory host isolation or infer safety from library flags;
- no classifier/PII non-detection, candidate score or stored source instruction grants egress or action authority;
- retention, supersession, retraction, archival and deletion are different; record owner, permitted location/access, duration, integrity, availability, residual/unknown copies and revision of the policy itself;
- no promise to erase every past Git copy;
- externally located source roots may be explicitly selected by an operator; untrusted metadata must not broaden them.

Include a deterministic negative-case matrix for unauthorized publication even with a configured adapter, wrong/missing target, network fallback, forbidden read scope, absolute/drive/UNC/traversal/symlink paths, malicious source instructions, classifier false negative and revoked evidence. State the boundary that rejects each case, observable no-read/no-write/no-egress/no-leak outcome, and positive authorized control. These are proposed tests, not claimed implemented protection. Separate intentional-client interception from OS-level egress evidence.

Record assumptions/questions for W01's capability design rather than blocking on its unfinished proposal or inventing a generic authorization engine. Identify one bounded next enforcement slice after owner acceptance.

## Parallel coordination and safety

One writer per branch and assigned file. W01 owns capabilities, W12 a separate runtime slice. Read public evidence but do not amend other outputs or shared ADR numbering. Use synthetic examples only; no actual consumer/infrastructure data. No deletion of source data, model/dependency downloads, external inference, firewall/permission/remote changes, new remote adapter, auto-acceptance, force-push, merge, ready-state change or issue closure.

## Verification and durable delivery

Verify the assigned PR seed/head, check references and consistency with retained ADR clauses, inspect only allowed changed paths and run `git diff --check`. Do not call proposed tests passed. Final explanation in Russian; repository prose may remain English.

In the final GitHub task comment include the COMPLETE exact unified diff for the new file (stage only that path so it is included), patch SHA-256 and newline convention, base/head IDs, changed paths and actual checks/limitations. Aim below 24 KiB; no truncated patch, summary-only result or links to unchanged baseline files. Publication to this existing PR branch via an already authorized interface is permitted, but the recoverable diff is still required. Missing terminal remotes do not justify credentials, environment changes or a new PR. Do not rely on a task-local SHA or make_pr metadata: another isolated task may not retain it.
