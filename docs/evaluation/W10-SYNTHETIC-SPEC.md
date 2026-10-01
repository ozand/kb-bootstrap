# W10-A synthetic evaluation specification

Status: **Draft; synthetic design only.** Refs #131/#121. This file defines an evaluation proposal, not an accepted production contract, implemented runner, benchmark result, or permission to use private data.

## Purpose and boundaries

The corpus is original fiction covering project management (`PM`), agent-system research (`AR`), and infrastructure operations (`IO`). It tests retrieval, conditions and negation, contradictions, duplicate names, unavailable evidence, revision impact, and interrupted handoff. It creates no persisted production schema and requires no network, model, QMD, GLiNER, download, or external service.

The authoring corpus is [W10-AGENT-INPUTS.md](W10-AGENT-INPUTS.md), not an agent-visible mount. Expected answers and grading evidence are physically separate in [W10-EVALUATOR-KEY.md](W10-EVALUATOR-KEY.md). Before constructing a sandbox, the future runner MUST materialize only the selected revision/phase fragments under the rules below. The agent receives that generated view and its selected question-manifest line, never the complete authoring corpus, this specification, or the evaluator key. For Q9, only process B additionally receives the specified handoff fragments after interruption. Reject paths, prompts, tool output, environment variables, indexes, and caches that expose withheld files or fragments outside the selected view. This is a proposed application boundary, not proof of host isolation.

## Fixture grammar and revisions

A fragment begins with an exact unique heading `### <ID>`; references use that ID and must resolve to exactly one heading in the input file. Its materialized bytes are the UTF-8 bytes of that heading, one LF, its following nonblank content lines through the last nonblank line before the next heading, and one LF. Fragments are concatenated in the explicit order below with one additional LF between them. No document title, section heading, handoff fragment, BOM, CR, trailing spaces, or final extra blank line is included.

The exact active sets and order are:

- T0: `PM-S1, PM-S2, PM-S3, AR-S1, AR-S2, AR-S3, AR-S4, IO-S1, IO-S2, IO-S3`.
- T1: `PM-S1R, PM-S2, PM-S3, PM-S4, AR-S1R, AR-S2, AR-S3, AR-S4, AR-S5, IO-S1, IO-S2, IO-S3R, IO-S4`.
- T1 history: `PM-S1, AR-S1, IO-S3`, in that order, and only for dual-revision questions.

T1 replaces the three history fragments in the active view; stale means retained in the separately labelled history channel, not active or silently co-present. Unchanged fragments are byte-identical. `AR-S4` is active in both revisions only as a blocked-evidence record: its unavailable artifact is never supplied. The fixture labels `exact capture`, `manual summary`, and `converted representation` describe supplied synthetic forms, not independent proof that a converter, capture tool, or runtime behaviour exists. Static code descriptions and supplied test-path observations remain distinct.

## Tasks and safe question delivery

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

The future runner may parse this withheld file only before sandbox construction. It MUST match exactly ten UTF-8/LF table rows with the anchored ASCII regular expression `^\| (Q(?:[1-9]|10)) \| ([^|\r\n]+) \| [^|\r\n]+ \|$`, reject duplicate/missing/out-of-order IDs, and serialize only capture groups 1 and 2 as `ID<TAB>Reader task<LF>` in Q1…Q10 order. The resulting question manifest SHA-256 is `9260c853e7a76abc925131b41f35e48f95570c6429e99e71a078fbf9627804b0`. Only the selected manifest line and declared revision label enter the evaluated prompt; the capability column, this specification, and the key remain withheld.

Q3, Q5, Q6, and Q8 receive active T0 followed by active T1 as separately labelled channels; the three T1-history IDs are available only in the T0 channel and are not duplicated into active T1; all other domain questions receive active T1 only. Q9 follows the special handoff procedure below. Retrieval evaluation asks for the smallest sufficient fragment-ID set before the answer.

## Deterministic baseline and proposed comparisons

Baseline `B0` has no optional tools: exact local input, direct file navigation/search, no QMD, no pre-extraction hints, no model service, and no network. The runner records fixture/result revision, question, returned fragment IDs, answer bytes, cache state, language, input/context lengths, elapsed time, peak memory when measurable, repeated reads, and manual correction effort. Deterministic document/reference checks can run now; answer generation and all performance values are unperformed.

Later, separately authorized experiments use identical inputs, questions, prompt, randomness policy, and fixed QMD condition within each comparison:

1. `A0`: no hints.
2. `A1`: entity/classification hints only.
3. `A2`: separately authorized relation/attribute hints.

Report QMD as one fixed value (`absent`, or a pinned version/config/index) across A0–A2; QMD-present versus QMD-absent is a separate comparison. Hints rank or navigate but never hard-filter the corpus. Measure relevant-source false negatives, including relevant fragments excluded before answer construction. Pin and report package/model digest, schema proposal revision, thresholds, chunk/overlap and decoding settings if an optional experiment is later approved. These are proposed ablations, **not performed runs**, endorsements, acquisition authority, or accepted contracts.

## Scoring

Semantic scoring is manual and may differ between judges; only the arithmetic after the claim labels are fixed is deterministic. The evaluator records the exact response and key revisions, judge identity or version, claim boundaries, supporting references, and the decisions used to derive Cq, Eq, Jq, and Dq. Disputed labels and any adjudication remain explicit; the formulas do not settle meaning, prove truth, or authorize silent changes to the key. Each key bullet is one equal-weight claim even when its required citation set contains several IDs. Let `Nq` be the required-claim count for question q: Q1–Q10 use `3,3,3,2,3,3,3,3,3,4`. For Q10, select and pad its four slots exactly as the key directs. For each q, let `Cq` be supported required claims present, `Eq` be distinct contradicted/invented/stale-as-current claim errors (each erroneous assertion counted once, capped at `Nq`), `Jq` be claims whose complete required ID set is cited on that claim and actually supports it, and `Dq` be required claims with at least one omitted required state/provenance qualifier. All variables are integers in `[0,Nq]`; an error cannot count in `Cq` or `Jq`.

The four per-question scores are:

- factuality `Fq = 40 × max(0, Cq − Eq) / Nq`;
- evidence coverage `Vq = 35 × Cq / Nq`;
- citation quality `Iq = 15 × Jq / Nq` (all IDs for a multi-ID claim are one all-or-zero unit);
- state/provenance discipline `Pq = 10 × (Nq − Dq) / Nq`, except an unanswered claim is also a qualifier defect, so blank answers have `Dq=Nq`.

The question score is `Sq=Fq+Vq+Iq+Pq`. The global score is the unweighted arithmetic mean `(S1+…+S10)/10`, not a pooled-claim score; retain exact rational values and round only the displayed category/question/global values to two decimals, half up. Controls: a blank response has `C=E=J=0, D=N` and scores `0`; a wholly correct, fully cited and qualified response has `C=J=N, E=D=0` and scores `100`; a response contradicting every required claim has `C=J=0, E=D=N` and scores `0`. Thus unsupported abstention cannot score well.

Separately report relevant-fragment recall as `required gold IDs returned / distinct required gold IDs` per question and its unweighted mean across questions; a multi-ID claim contributes each distinct ID here, unlike citation scoring. Also report relevant fragments missed by filtering, irrelevant fragments returned/read, contradicted, stale, unsupported and unanswered counts, changed fragments correctly identified, unaffected fragments incorrectly rewritten, and repeated reads. Thresholds and a holdout policy must be agreed before optional-model results are viewed; none is asserted here.

## Revision and interruption procedure

1. Materialize the exact active sets with the byte rule above; dual-revision questions receive the explicitly labelled history channel, never an implicit union.
2. For Q9, process A receives active T1 only. It cannot read `X-H1` or `X-H2`; the harness records `X-H1` only when the stated interruption occurs.
3. After interruption, process B starts without A's conversation history and receives, in order, active T1, then `X-H1`, then `X-H2`. Neither handoff fragment is domain evidence or part of the active-T1 digest. B recomputes SHA-256 over active-T1 bytes and repeats completed checks only on mismatch.
4. Each dual-revision question (Q3, Q5, Q6, Q8) produces one comparative response and one score Sq against its complete existing key. T0 and T1 label evidence within that response; they do not produce separately weighted scores or change Nq. Each of Q1–Q10 contributes exactly once to the global mean. Any optional single-revision diagnostic is reported outside that mean. A claim supported at T0 but superseded at T1 is `stale` when presented as current; a claim with no available support is `unsupported`; neither is automatically false for all time.

## Limitations

This tiny authored corpus cannot establish production quality, privacy, security, semantic correctness, CPU suitability, or general multilingual performance. Exact-ID retrieval is easier than open-world discovery. Human keys can be incomplete and judges can err, so disputed grading and evaluator omissions remain visible. No benchmark, inference, QMD run, model ablation, converter, publication, or consumer-data test was performed by this draft.
