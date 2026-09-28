# W10-A synthetic evaluation specification

Status: **Draft; synthetic design only.** Refs #131/#121. This file defines an evaluation proposal, not an accepted production contract, implemented runner, benchmark result, or permission to use private data.

## Purpose and boundaries

The corpus is original fiction covering project management (`PM`), agent-system research (`AR`), and infrastructure operations (`IO`). It tests retrieval, conditions and negation, contradictions, duplicate names, unavailable evidence, revision impact, and interrupted handoff. It creates no persisted production schema and requires no network, model, QMD, GLiNER, download, or external service.

The agent-visible corpus is only [W10-AGENT-INPUTS.md](W10-AGENT-INPUTS.md). Expected answers and grading evidence are physically separate in [W10-EVALUATOR-KEY.md](W10-EVALUATOR-KEY.md). A future runner MUST copy or mount only the inputs file into the evaluated agent's readable sandbox; this specification and the evaluator key stay outside it. The runner must reject paths, prompts, tool output, environment variables, indexes, and caches that expose either withheld file. This is a proposed application boundary, not proof of host isolation.

## Fixture grammar and revisions

A fragment begins with an exact unique heading `### <ID>`; references use that ID and must resolve to exactly one heading in the input file. Text between that heading and the next heading of equal or higher level is the fragment. `T0` uses every fragment marked `T0`. `T1` keeps unmentioned T0 fragments byte-identical, replaces fragments explicitly marked `T1 replaces …`, and adds fragments marked `T1 adds …`. A replacement makes the earlier fragment stale, not absent. `AR-S4` is unavailable in both revisions: only its blocked-record text is visible, so answers may describe the gap but may not invent its contents.

The fixture labels `exact capture`, `manual summary`, and `converted representation` describe supplied synthetic forms; they do not claim a converter or capture tool ran. Raw inputs, notes, candidate statements, and handoff state do not become canonical merely because retrieval finds them.

## Tasks

For each selected revision, give concise answers with fragment IDs and preserve uncertainty, provenance type, conditions, dates, and negation.

| ID | Reader task | Required capability |
|---|---|---|
| Q1 | Under what conditions should the Northstar team use the Pulse review, and is it mandatory? | conditional meaning, conflicting recommendation |
| Q2 | Who facilitates Pulse, and what evidence limits the answer? | contradiction, absent evidence |
| Q3 | What changed for Pulse from T0 to T1, and what stayed unchanged? | stale/update impact |
| Q4 | Compare the two components named Relay without merging them. | duplicate names, cross-repository identity |
| Q5 | Which Relay claim is supported by observed behaviour rather than only a README? | raw/canonical and evidence quality |
| Q6 | At T1, which agent-research material must be revisited? | targeted impact, negation |
| Q7 | What is the desired and observed cache state, and may the agent run the repair? | desired/observed/authentication separation |
| Q8 | Which cache recovery procedure is current at T1, including its conditions? | supersession, conditions, mixed language |
| Q9 | Resume the interrupted work: what is complete, what remains, and what must not be repeated? | two-process handoff |
| Q10 | List important claims that cannot be concluded from available evidence. | missing evidence, calibrated abstention |

For Q3, Q6, and Q8 the runner supplies both revisions. Other questions are scored at the stated revision (default T1). Retrieval evaluation additionally asks the system to return the smallest sufficient fragment-ID set before answering.

## Deterministic baseline and proposed comparisons

Baseline `B0` has no optional tools: exact local input, direct file navigation/search, no QMD, no pre-extraction hints, no model service, and no network. The runner records fixture/result revision, question, returned fragment IDs, answer bytes, cache state, language, input/context lengths, elapsed time, peak memory when measurable, repeated reads, and manual correction effort. Deterministic document/reference checks can run now; answer generation and all performance values are unperformed.

Later, separately authorized experiments use identical inputs, questions, prompt, randomness policy, and fixed QMD condition within each comparison:

1. `A0`: no hints.
2. `A1`: entity/classification hints only.
3. `A2`: separately authorized relation/attribute hints.

Report QMD as one fixed value (`absent`, or a pinned version/config/index) across A0–A2; QMD-present versus QMD-absent is a separate comparison. Hints rank or navigate but never hard-filter the corpus. Measure relevant-source false negatives, including relevant fragments excluded before answer construction. Pin and report package/model digest, schema proposal revision, thresholds, chunk/overlap and decoding settings if an optional experiment is later approved. These are proposed ablations, **not performed runs**, endorsements, acquisition authority, or accepted contracts.

## Scoring

The evaluator performs claim-level review against the withheld key.

- **Factuality (40 points):** 2 points for each supported required claim, normalized to 40; subtract the same normalized claim weight for each contradiction, invented fact, or stale claim stated as current. Floor 0.
- **Evidence coverage (35 points):** weighted required claims present / weighted required claims in the key. Unsupported abstention does not satisfy a supported claim. Thus an empty answer scores 0 here.
- **Citation quality (15 points):** weighted required fragment IDs correctly cited / required IDs; a citation that does not support its claim earns 0 and counts as an irrelevant read.
- **State/provenance discipline (10 points):** preserves conditions, negation, revision, desired-vs-observed status, unavailable/manual-summary labels, and non-authorization. Deduct one point per omitted required qualifier, floor 0.

Overall score is the sum. Also report, without hiding them in the aggregate: supported-answer rate; expected-topic coverage; relevant-fragment recall; relevant fragments missed by filtering; irrelevant fragments returned/read; contradicted, stale, unsupported, and unanswered claim counts; changed fragments correctly identified; unaffected fragments incorrectly marked/re-written; and repeated reads. A response cannot pass merely by making no false statements. Thresholds and a holdout policy must be agreed before optional-model results are viewed; none is asserted here.

## Revision and interruption procedure

1. Materialize T0 and run the tasks; retain answers and the list of consulted IDs.
2. Materialize T1 by the declared replacements/additions only. Verify the unchanged-fragment hashes remain equal.
3. Stop after the first handoff event in `X-H1`. Start a clean second process with input plus handoff state but without conversation history. It must use `X-H2`, avoid repeating completed checks, and expose unfinished work.
4. Score T0 and T1 separately. A T0 claim contradicted by T1 is `stale`; a claim with no available support is `unsupported`; neither is automatically `false` for all time.

## Limitations

This tiny authored corpus cannot establish production quality, privacy, security, semantic correctness, CPU suitability, or general multilingual performance. Exact-ID retrieval is easier than open-world discovery. Human keys can be incomplete and judges can err, so disputed grading and evaluator omissions remain visible. No benchmark, inference, QMD run, model ablation, converter, publication, or consumer-data test was performed by this draft.
