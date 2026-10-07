# ADR-021: Separate generated research progress from canonical lifecycle status

**Status**: Proposed
**Date**: 2026-10-07
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #132; ADR-003, ADR-005, ADR-009, ADR-017

## Context

Fresh synthetic characterization shows `new_research.py` creates `research/<date>_<slug>/brief.md` with `type: ResearchBrief` and `status: in-progress`; the report template emits `type: Report` and `status: stable`. `check_research.py --skip-validate` passes the synthetic workflow. The universal profile rejects the brief's status; graph lint includes it; graph export and published bundle block; ADR-017 local retrieval excludes the research path while finding the report. Source bytes remain unchanged. These observations are recorded in Issue #132 comments 6031454964, 6031242970, and PR #165 post-merge receipt 6032969712. They are synthetic local evidence, not consumer-corpus or QMD evidence.

ADR-003 validates present `status` only as `draft|stable|deprecated`. ADR-005 exports ordinary canonical concepts, each of which must pass ADR-003, and blocks links to non-node local Markdown targets. ADR-009 publishes selected profile-valid concepts plus reserved files. ADR-017 deliberately excludes every `research/` descendant from local retrieval, while ADR-003/005 may accept a generic canonical Concept in that directory. Directory location alone is not a document role.

The generated brief needs both a canonical lifecycle value and a workflow progress value. Rewriting `in-progress` to mean `draft` or accepting it as a canonical status would overload one field; excluding every research directory would also exclude legitimate canonical studies. The report template links to the brief, so the choice affects normal graph export and published bundle behavior.

### Problem statement

Represent the generated brief as profile-valid canonical draft content while separately retaining active workflow progress, without changing generic documents under `research/`, graph schema, bundle membership, or retrieval selection.

## Decision

This proposal recommends changing only future generated brief defaults to canonical `status: draft` plus a separate authored `workflow_status: in-progress`. Existing canonical profile, graph, bundle, and retrieval contracts remain unchanged. This is not implemented; owner acceptance is required before changing the template.

### What this IS

1. Keep `type: ResearchBrief`; generate canonical `status: draft` and a separate scalar `workflow_status: in-progress`. These fields express distinct dimensions. `workflow_status` is not canonical lifecycle, verification, freshness, or approval.
2. Keep the brief an ordinary profile-valid canonical document. ADR-003 continues to validate its canonical fields; no special path/type exception is introduced.
3. Keep it an ordinary node and valid target under ADR-005 graph rules. The report-to-brief link remains an ordinary local edge; JSON schema and edge semantics do not change.
4. Keep the brief eligible for ADR-009's existing published-bundle selection as a profile-valid Markdown concept. Bundle membership is not a claim that research is verified or complete.
5. Keep ADR-017 behavior unchanged: all descendants of a directory named `research` remain excluded from local retrieval, including the brief and generic canonical concepts there.
6. Keep `check_research.py` as an independent workflow-completeness check. Its success does not assert profile, graph export, published-bundle or retrieval readiness.
7. The new `workflow_status` field is an additive generator-template default, not an ADR-003 validated lifecycle field, verification signal, approval or freshness claim. Existing consumer bytes are preserved; there is no automatic migration, status rewrite, QMD indexing or consumer change.

### What this IS NOT

This proposal does not implement a non-canonical workflow node, profile exception, graph schema version, ZIP exception, blanket research exclusion, `in-progress` canonical status, verification claim, ADR-017 expansion, automatic migration or consumer rewrite. Existing generated briefs remain unchanged and continue to fail current validation until their owner edits them or a separately approved migration is defined. The proposed `workflow_status` field has no runtime semantics and does not alter ADR-003, which already tolerates unknown additional metadata.

### Success criteria

After acceptance and implementation, a newly generated brief has `status: draft` and `workflow_status: in-progress`; it passes the existing profile, is an ordinary graph node with a valid report edge, is selected in the existing bundle, remains excluded from local retrieval, and has source bytes preserved by checks. Generic Concepts under research paths retain current per-tool outcomes.

## Consequences

### What gets easier

Canonical lifecycle and active workflow progress are independently represented while the existing profile, graph, bundle, and report-link contracts remain reusable.

### What gets harder

The template adds a workflow-specific metadata field that downstream consumers must not confuse with verification. Existing briefs using `status: in-progress` remain invalid until owner remediation; no automatic repair is authorized.

### What does not change

ADR-003 status vocabulary, ADR-005 graph schema, ADR-009 selection rules, and ADR-017 retrieval exclusions remain unchanged. Until owner acceptance and a separately reviewed implementation, current runtime behavior remains authoritative. No QMD, model, network, or consumer operation is authorized.

## Alternatives Considered

- Keep `status: in-progress` and add a path/type exception in the profile: rejected because it creates a special canonical exception for one workflow artifact and requires the profile to identify a role from spoofable path/metadata.
- Exclude the brief from graph export and bundle: rejected because the generated report explicitly links to the brief, so export would block or require separate dangling-edge semantics; it also makes a `check_research.py`-accepted report unavailable in the published artifact.
- Add a separately typed workflow node/member: rejected for this proposal because it requires a new graph schema and publication membership contract.
- Exclude every `research/` directory: rejected because generic canonical Concepts there currently pass profile/export and have separately specified retrieval exclusion.
- Accept `in-progress` as a canonical status globally: rejected because it weakens ADR-003 for every concept.
- Leave the mismatch undocumented: rejected because the normal research checker can pass with validation skipped while profile/export/publication produce different outcomes.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| Generated brief uses canonical draft plus separate workflow progress | template render/profile fixture | not yet written; proposal only |
| Brief/report edge remains valid in graph export | linked brief/report export fixture | current rules support eligible targets; generated draft fixture not yet written |
| Bundle includes profile-valid draft brief without source mutation | bundle membership and byte fixture | not yet written |
| ADR-017 excludes research paths and outside canonical positive control remains retrievable | paired retrieval fixture | current behavior characterized; proposed template not implemented |
| Generic Concept under research retains its current profile/export/retrieval behavior | role matrix regression | existing characterization; no new contract implemented |

## Rollback

Withdraw this proposal if rejected. If accepted, implement only the additive generated-field change under a separately reviewed PR. Do not rewrite existing workflow briefs or consumer files automatically; any migration requires separate explicit authorization.

## References

- Issue #132 research records: https://github.com/ozand/kb-bootstrap/issues/132#issuecomment-6031454964; https://github.com/ozand/kb-bootstrap/issues/132#issuecomment-6031242970; https://github.com/ozand/kb-bootstrap/issues/132#issuecomment-6032969712
- ADR-003, ADR-005, ADR-009, ADR-017
- `kb_bootstrap/templates/skills/market-research/assets/brief-template.md`
- `kb_bootstrap/templates/skills/market-research/assets/report-template.md`
- `kb_bootstrap/templates/skills/market-research/scripts/new_research.py`
- `kb_bootstrap/templates/skills/market-research/scripts/check_research.py`
