# Architecture proposal and decision gates

**Status: Proposed design direction, not an Accepted ADR or implemented API.** Read [Product intent](PRODUCT_INTENT.md) first. No new command names or schema examples below constitute a supported interface.

## 1. Separate five responsibilities

| Responsibility | Content | Authority and recoverability |
|---|---|---|
| Sources and evidence | Origin descriptors, retained snapshots, conversions, fragments and observations | A source card is not the original; preserve access/retention and observed versions |
| Curated knowledge | Concepts, procedures, decisions, reports, lessons and necessary provenance/review records | Consumer-owned; human edits and review history are not disposable generated output |
| Candidate analysis | Predicted mentions, relations, classifications and proposed synthesis changes | Derived suggestions, never automatic accepted facts or authorization |
| Work progress | Study scope, completed steps, unresolved checks and handoff references | Operational state; completion requires durable referenced output |
| Retrieval projections | QMD/FTS indexes, embeddings and navigation projections | Rebuildable where inputs/configuration are retained; may lag authoritative content |

These are logical roles, not mandatory folder names or services. A raw corpus may be local-only while sanitized knowledge is Git-tracked. `sources/` can hold descriptors in one consumer and original material in another; the role must be declared rather than inferred from the name. Existing layouts are not migrated by this proposal.

Not everything beside Markdown is a cache. Evidence bindings and accepted review decisions may be indispensable authoritative records. Conversely, persistence does not make a search index canonical knowledge.

## 2. Minimal lifecycle

```text
receive explicit source/capture
 -> validate and retain its available representation
 -> record what was actually examined
 -> propose additions, refinements, links, conflicts or retractions
 -> apply the consumer's review/authority policy
 -> publish the accepted local change safely
 -> update optional retrieval projections
```

An agent may synthesize a conclusion supported jointly by several materials. It must not present that conclusion as a direct source quote. Keep source-stated facts, attributed recommendations, synthesis, hypotheses and observations distinct. Preserve scope, versions, conditions, uncertainty and conflicting evidence.

Exact byte duplicates, near-duplicate captures, entity identity and equivalent claims are different questions. Merging representation must preserve provenance. Reprints do not create independent corroboration. Retained generated knowledge must preserve upstream lineage rather than confirm itself circularly.

Three graphs remain distinct: navigation/subject relationships, provenance/dependency relationships, and model-predicted candidate relationships. A link is not automatically a typed relation or supporting evidence.

## 3. Source and capture contract (W03)

Define stable source identity separately from original revision, capture revision and transformation version. A bounded record should account for origin, observation/capture time, media/language, retained representation, converter/runtime/parameters, coverage, losses and access/retention classification. Exact field names and requiredness require an ADR.

Bind fragments to a specific representation revision. Page/slide/time/region coordinates are useful when actually available; do not manufacture them. A manual summary and a model description of an image are interpretations, not exact extraction. A long text does not prove complete capture. Missing origin data stays unknown.

Start with explicitly supplied local Markdown/text and an origin descriptor. Reuse ADR-010 raw hashes. Do not expand its schema in place. Recording external origins is not permission for a validator to open arbitrary paths or network resources. Conversion engines, external path adapters and network collectors are later separately bounded integrations.

The proposed v1 local importer uses an explicitly operator-selected input root, which may be outside the Git checkout. Untrusted records cannot broaden that selection: reject absolute/drive/UNC references, parent traversal, symlinked files or ancestors, and outside-corpus targets before opening their contents, conversion or mutation. Safe path-metadata inspection needed for this gate is distinct from reading source contents. The [evaluation boundary fixtures](EVALUATION_PLAN.md#boundary-fixtures-for-w01w03w04w09) include positive controls, outside-content sentinels and read/converter/write observation; reports must not leak rejected contents or uncontrolled paths. This is a proposed contract and test requirement, not an assertion of current enforcement.

## 4. Capability and completion model (W01/W06)

Document separate states for not configured, explicitly disabled, configured/available and configured/broken capabilities. Not configured is not a false success; configured failure is not silently skipped. Core content checks must eventually work without optional tooling, while a declared required consumer check remains binding.

Separate local content validation, consumer policy, repository publication identity and retrieval/index readiness. Existing command defaults and reports remain current until an approved migration changes them. Keep the current remote doctor/publication checks; design a separate local ownership/path boundary instead of weakening them covertly.

In the proposed local-core flow, import/read/update cannot trigger remote publication or network egress merely because a remote or adapter is configured. Publication is a separate authorized, explicitly targeted operation. Test both no-authorization and wrong/missing-target cases plus an authorized fake-target control, as specified in the [evaluation plan](EVALUATION_PLAN.md#boundary-fixtures-for-w01w03w04w09).

Use compact discovery followed by selected reading. Default knowledge retrieval excludes evidence/workflow layers according to the accepted consumer boundary; raw reads are explicit. Return origin/layer and available revision/review state. Budget exhaustion is explicit, not silent content loss. A named but unavailable tool never triggers cloud fallback or unrestricted corpus selection.

Progressive disclosure (abstract, overview, full text) is a reading-depth choice orthogonal to sources/raw/wiki. Both evidence and knowledge can have these reading levels. Additional summaries are projections whose freshness and lossiness matter.

## 5. Incremental review (W07)

Start with document-level evidence bindings and optional important claim-level records, not a mandatory registry of every sentence. Use deterministic local resolvers to bind material to versions. Changed, missing, inaccessible and malformed are different states.

The first implementation produces a read-only affected-item report. A changed hash creates review work, not automatic retraction; an unchanged hash proves neither semantic correctness nor completeness. Changed surrounding conditions or new contradictory evidence may matter even if a cited fragment is unchanged. A frozen web capture does not notice an external website change without separately authorized recapture.

Later mutation protocols may support confirm/revise/add/retract proposals with explicit authority and preserved historical evidence. Any new persisted review/claim schema needs a compatibility and rollback plan. It must not overwrite human text or fabricate verification events.

## 6. Portable progress (W08)

Retain task scope, source revisions, material examined, completed artifacts, pending proposals, checks and a bounded next step. Keep it independent of the original agent transcript. Save-before-handoff is useful even where no compaction hook exists.

Mark work complete only after outputs and required records exist. Specify interruption recovery and single-writer/concurrency boundaries. An explicit local save/check/load workflow is sufficient initially; no daemon, queue service or cross-machine transaction is required. Progress records are owned operational artifacts, not universal knowledge.

## 7. Policy across the entire route (W09)

Apply policy to originals, conversion, indexes, queries, candidate extraction, synthesis, viewers, publication and backups. Sensitivity, applicability, reader access and write/review authority are independent. A source that contains instructions is still data; a documented procedure does not authorize execution.

Maintain ADR-014's distinction between local smoke verification and separately demonstrated denied egress for sensitive processing. Model scores and PII non-detections do not authorize release. Filenames, hashes and candidate spans may disclose information.

Distinguish supersession, retraction, archival and deletion. Retention must specify owner, permitted location/access, duration or deletion rule, integrity and post-run availability. Do not promise to erase every historical Git copy. Version transition policies themselves with owner, rationale and review date.

## 8. Decision gates

| Gate | Decision needed | Lead work |
|---|---|---|
| D01 | Optionality, local/publication checks, report/default compatibility | W01 |
| D02 | Safe scaffold repeat and explicit template upgrade semantics | W02 |
| D03 | Source/capture/fragment identities and transformation provenance | W03 |
| D04 | Collector-independent import interface | W04 |
| D05 | Persisted synthesis/review additions, if actually necessary | W05 with existing #101 |
| D06 | Bounded read/search interface and adapter/index selection | W06 |
| D07 | Evidence bindings and read-only impact report schema | W07 |
| D08 | Portable progress record and publication/recovery boundary | W08 |
| D09 | Execution/publication/retention policy and enforcement scope | W09 |

Use narrowly scoped ADRs only where a new public/persisted/safety contract is introduced. Do not require a new ADR to fix a regression within an accepted contract. Do not invent acceptance on the owner's behalf. Do not renumber or rewrite Accepted ADRs.

Existing #90 owns provenance reference alignment, #91 pure-OKF/attestation decisions, #92 migration, #100 candidate peer, #101 entity identity, #102 candidate navigation, #109 local provisioning and #108 remote inference. W10 experiments never silently expand those scopes.

## 9. Phasing and boundary tests

First characterize regressions, write the product/policy decisions and build synthetic tests. Then deliver explicit local capture and read paths. Next add bounded change-impact and handoff. Evaluate optional models only after those baselines exist and setup is consented. Review [Work packages](WORK_PACKAGES.md) for the actual graph of tasks and [Evaluation plan](EVALUATION_PLAN.md) for acceptance scenarios.

Unknowns intentionally left for decisions include external-corpus access, exact ID and fragment format, allowed review automation, mapping existing consumer schemas, selective source recapture, and cross-KB access. Do not resolve them implicitly in a convenience wrapper.
