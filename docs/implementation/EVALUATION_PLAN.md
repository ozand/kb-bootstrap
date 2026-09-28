# Evaluation plan: utility, update safety and optional helpers

Status: proposed evaluation specification. No benchmark has been run by creating this document. Owner: [W10 / #131](https://github.com/ozand/kb-bootstrap/issues/131).

## 1. Original synthetic corpus

Use short authored materials, not copied private documents or licensed books. Start with three scenarios and a small manually reviewed question/evidence matrix. Keep evaluator answers out of agent-visible inputs.

| Scenario | Source pattern | Necessary knowledge and edge cases |
|---|---|---|
| Project-management method | Two attributed descriptions, one case note, one revision | A method applies only under a stated condition; recommendation differs from fact; two sources disagree |
| Agent-system comparison | Two miniature fictional implementations and versioned notes | Same name refers to different components; observed code behaviour differs from a README statement; only one implementation changes |
| Infrastructure procedure | Synthetic observation, intended configuration and troubleshooting note | Desired state differs from observed state; instruction is not authorization; a formerly valid procedure is superseded |

Include Russian and mixed-language text, explicit negation, ambiguous names, a manual-summary capture, unavailable origin and a supplied converted-media representation. Fixture labels do not assert a real converter was run.

## 2. Baseline trace

At T0, import explicit local captures, describe what was examined, synthesize a small knowledge set, and answer known questions. At T1, change one source, add one contradictory source and leave other material unchanged. At T2, revoke or make one evidence record unavailable. Interrupt one processing step and resume in a second process without the original conversation.

| Check | Required observation |
|---|---|
| Capture fidelity | Exact/partial/summary/blocked are not conflated |
| Evidence trace | An answer can reach the correct available source revision or declare the gap |
| Deduplication | No duplicate entity/claim by accident; origin and independent evidence survive |
| Conditional meaning | Negation, conditions, dates and applicability are not dropped |
| Change impact | Affected material is identified without rewriting unaffected knowledge |
| Coverage | Important known topics remain answerable; silence is not counted as perfect accuracy |
| Handoff | Completed work is not repeated; unfinished checks remain visible |
| Separation | Raw/candidate/workflow data do not acquire canonical status through indexing |
| Permissions | Disallowed source or network fallback is not selected |
| Local/publication separation | Even with a remote or publication adapter configured, local import/read/update invokes no remote mutation or network egress; publication requires a separately authorized operation with an explicit target |
| Source containment | Reject untrusted absolute/drive/UNC references, parent traversal, symlinked source or ancestor, and outside-corpus targets before opening source contents, conversion or mutation; no outside contents reach output or receipts |
| Mutation safety | Pre-existing content survives invalid input and interrupted publication |

Deterministic checks should run without QMD, GLiNER, network or a live LLM. Human/model evaluations are a separately labelled layer. Judges can fail; unverified outcomes and evaluator completeness must be visible.

### Boundary fixtures for W01/W03/W04/W09

Configure a synthetic remote/publication adapter but provide no publication authorization. Run local import, read and update through instrumented network/publication interfaces and assert zero calls, including push, remote issue/PR creation and external inference. Add separately authorized, explicitly targeted publication and wrong/missing-target controls using local fakes only: the former selects exactly the authorized target, the latter blocks before invocation. If a requested operation or capability would require networking, it must return a truthful unavailable/blocked outcome rather than silently falling back. These tests observe application-side calls; they do not certify host-wide egress isolation.

For the proposed v1 local capture path, select the input root explicitly as an operator action, then test untrusted references within supplied records. Include POSIX absolute paths, Windows drive and UNC paths, `../` traversal, a source-file symlink, a symlinked ancestor and a sibling outside the selected root. Put a unique harmless sentinel in an outside fixture and use read/converter/write spies to verify rejection before opening that content or producing output. Assert that diagnostics and receipts contain neither the sentinel nor uncontrolled absolute paths. Include an ordinary permitted file as a positive control; report unsupported symlink fixtures as skipped, not passed. The operator may select an input root outside the Git checkout: that explicit choice is not the same as granting arbitrary metadata references access outside that root. These are acceptance fixtures to implement with the approved contracts, not claims that new enforcement already exists.

## 3. Metrics

Measure supported-answer rate and expected-topic coverage separately. Distinguish contradicted, formerly true but stale, unsupported and unanswered claims. Do not equate missing evidence with proven falsity.

Record evidence recall, relevant sources missed, irrelevant material read, repeated fetches/reads, changed documents correctly identified, unaffected documents rewritten, context volume and correction effort. For end-to-end runs record capture/conversion, retrieval, extraction, synthesis and review cost, not only LLM tokens.

Use identical questions/corpora across variants, fixed or recorded randomness, repeated runs where appropriate, disclosed cache state and a disjoint holdout. Agree numeric acceptance thresholds before looking at optional-model results; this document does not invent product performance targets.

## 4. Optional-model ablations

Compare baseline navigation/search with entity/classification hints, then separately authorized relation/attribute hints. Hold QMD configuration constant inside each comparison; test QMD absence as another explicit comparison rather than a hidden change.

Pin runtime, model digest, schema version, thresholds, chunk/overlap rules and decoding settings. Record actual CPU/GPU, thread count, input and schema lengths, language, throughput/latency distribution and peak memory. Serialization determinism does not prove identical ML predictions across hardware.

Early candidates assist ranking and navigation; they are not a hard exclusion filter. Measure false negatives before making selection more restrictive. Compare classifications lacking evidence spans separately from extraction tasks with coordinates.

Reuse #100/#101/#102 outputs when ready and #109's consented setup. Relations, Decide, GLiGuard and PII are separately scoped experiments, not silent changes to #100. No implicit model download, endpoint choice or confidential test data. PII non-detection cannot approve data egress.

## 5. Delivery evidence

Each report names fixture version, source/artifact revisions, exact commands, environment, measured results, uncertainty, failed cases, evaluator limits and retained evidence location. Mark skipped optional components explicitly. Keep payloads and internal operational details out of public logs.

A passing shape validator does not prove semantic quality. A successful local-model smoke does not prove denied host egress. A documents-only change does not count as a completed benchmark. Release review should assess correctness, coverage, compatibility and repeated-work reduction together.
