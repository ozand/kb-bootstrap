# Draft: synthesis and lesson review guidance

> **Status: DRAFT / NON-NORMATIVE.** This guide is an explanatory aid for people and agents. It does not define a schema, change a validator, authorize publication, or replace a repository owner's review policy. The examples are invented illustrations, not benchmark fixtures, consumer excerpts, or measured results.

## Purpose and boundaries

Synthesis reorganizes evidence from multiple sources into reusable concepts, explanations, procedures, decisions, and lessons. It is more than placing one summary beside each source. A useful synthesis shows how claims relate while preserving who said what, under which conditions, at which version, and with what uncertainty.

This guide applies equally to human and agent-assisted drafting. It offers review questions and neutral working representations, not a required folder layout or universal ontology. A consumer continues to own its domain types, relation vocabulary, identifiers, directories, editorial states, and acceptance authority. The minimal OKF profile still permits producer-defined fields and unknown types; its provenance checks establish bounded syntax, not source truth or actor authority.

The guide does **not** create a claims database, graph service, canonical writer, model runtime, policy engine, or persisted synthesis format. Any future machine-readable synthesis or review artifact needs its own public contract and approval. Unresolved design work must not be anticipated by silently persisting an illustrative structure.

## Keep the epistemic labels visible

Every material statement in a synthesis should remain distinguishable as one of these kinds. The labels may be prose, footnotes, or consumer-owned metadata; these names are not a mandated enum.

| Kind | Meaning | Minimum review question |
|---|---|---|
| Source-stated fact | A checkable assertion attributed to a particular source. It reports what the source states, not that the assertion is universally true. | Is the source and relevant version or date identifiable? |
| Attributed recommendation | Advice, preference, or requirement made by a named source or authority. | Whose recommendation is it, and within what scope? |
| Local synthesis | A new conclusion produced by relating stated premises. | Are the premises cited and is the inference explicitly labelled? |
| Hypothesis | A proposed explanation or prediction that has not been established. | What observation could support or disconfirm it? |
| Operational observation | A recorded result from a bounded run, inspection, or incident. | What environment, procedure, time, and limitations bounded the observation? |

A sentence can contain more than one kind only if the boundary is clear. For example: “The runbook recommends a ten-minute interval; in a staging trial the check completed in six minutes; therefore the interval appears feasible for that staging configuration.” The first clause is attributed advice, the second is an observation, and the last is synthesis. The last clause is neither a quotation nor independent observation.

Use quotation marks only for actual, traceable quoted text. Paraphrases remain attributed. A source's confident wording does not turn a claim into an observation by the synthesizer, and agreement between two copied pages does not establish two observations.

## A reviewable synthesis process

### 1. Define the question and ownership boundary

State the question, intended audience, time/version boundary, and consumer that can accept the result. Separate reusable scope (“could this help several projects?”) from access scope (“who may read this source?”). Broad applicability never makes restricted material publishable, and public access never makes a claim broadly applicable.

Stop before drafting if source access or authority to prepare the draft is ambiguous. An authorized provisional draft need not wait for assignment of its final accepting reviewer; acceptance and publication still require their proper approval. Record unknowns rather than inventing an owner or policy.

### 2. Inventory sources without flattening them

Give each source a stable local reference sufficient to navigate back to the captured revision. Record origin, revision/date when known, and relevant context. Preserve the source representation; do not rewrite a historical report so it appears to contain later guidance.

Source handling involves different questions:

1. **Exact-file deduplication:** are the original bytes identical?
2. **Normalized representation equivalence:** are the representations equal after a specified normalization, without erasing their distinct source identity or provenance?
3. **Capture similarity:** do captures substantially overlap or derive from one another?
4. **Entity identity:** do two names refer to the same real-world thing?
5. **Claim equivalence:** do two statements make the same assertion with the same conditions, polarity, and scope?

Success at one level does not prove another. Two differently formatted captures may be the same revision; one document may mention two distinct entities with similar names; two claims may look similar while differing by a negation or version. When identity is unresolved, retain separate candidates and state the ambiguity.

Track derivation groups. Mirrors, quotations, generated summaries, and copied tickets retain their individual origin links, but a chain copied from one root is one evidential lineage, not independent corroboration. Count independence only when the underlying observation or authority is genuinely independent and that independence is reviewable.

### 3. Extract claims with qualifiers intact

For each relevant claim, keep:

- its epistemic kind and source reference;
- subject and asserted relation in ordinary language;
- polarity, including `not`, `never`, and absence claims;
- preconditions, environment, scope, version, and time;
- exceptions and counterexamples;
- uncertainty and stated confidence, without converting either into certainty;
- conflicts with other claims and any known shared lineage.

Do not shorten “feature Q is unavailable before release 5 when safe mode is enabled” to “feature Q is available in release 5.” The shortened form loses negation, a version boundary, and a condition. Do not merge “recommended” with “required,” “not observed” with “impossible,” or “no evidence found” with “false.”

### 4. Relate claims, then write the inference

Group claims by the question they answer, not merely by source or shared nouns. State the premises before or beside the conclusion. A synthesis should be reproducible as reasoning:

1. source A states premise P under condition C;
2. observation B records Q under condition D;
3. C and D overlap only in a named way;
4. therefore the draft infers R for that overlap;
5. exception E and disagreement F remain unresolved.

If a premise changes, readers must be able to find the conclusions that depend on it. Where the consumer supports claim footnotes or OKF source references, reuse them rather than inventing a parallel provenance system.

### 5. Produce a candidate, not accepted knowledge

Agent- or human-generated synthesis is a **candidate output** until the owning review process accepts it. Review should check source fidelity, inference validity, provenance, sanitization, applicability, contradictions, and local vocabulary. Acceptance may create reviewed knowledge under the consumer's normal lifecycle; it does not retroactively make every premise true.

Keep these transitions distinct:

```text
source material -> extracted claims -> synthesis candidate -> reviewed knowledge
                                                        != permission to act
```

A candidate cannot approve itself. A model's proposal, confidence, tool request, or captured prompt is not human approval. Reviewed knowledge that an action is normally useful is still not authorization to execute it. Credentials, current role, change window, target ownership, and explicit approval are separate operational controls. Likewise, metadata such as `generated`, `verified`, or `status` does not authenticate an actor or grant permission.

### 6. Revisit instead of silently rewriting

When new evidence arrives, preserve the earlier report as a historical record. Create a new reviewable revision, correction, or superseding guidance according to consumer policy. Show which premise, condition, or observation changed. Deprecation is a lifecycle decision, not an erasure of disagreement.

## Three graphs with different meanings

“Graph” here means a conceptual view; it does not require a service or persisted schema.

| View | Nodes and edges answer | It must not imply |
|---|---|---|
| Navigation graph | Where can a reader move among documents, topics, indexes, and related material? | That a link proves a claim or identity |
| Provenance graph | Which source revision, observation, or derivation supports or produced a claim? | That several descendants are independent corroboration |
| Inferred candidate graph | Which proposed entities, claim equivalences, causal links, or conclusions might be useful after review? | That candidates are canonical facts, merged identities, or authorized actions |

One edge may appear in more than one view only with separately understood meanings. A hyperlink is navigation by default. Reviewers should reject an export or diagram that visually turns an unreviewed inference into provenance or collapses a copied-source cluster into multiple confirmations.

## Illustrative examples

All names, versions, events, and measurements below are synthetic.

### Project management: a schedule recommendation

**Question:** Should the “Northstar” pilot reserve a second review day?

- **Source-stated fact:** planning note P7 states that the pilot has two approval groups and targets release train 3.
- **Attributed recommendation:** the invented governance handbook H2 recommends one review day per independent approval group, unless both groups use a joint session.
- **Operational observation:** retrospective R4 records that one earlier pilot using separate sessions waited an extra day; it does not report projects using joint sessions.
- **Disagreement:** meeting record M9 says the two Northstar groups expect a joint session, while the current calendar lists separate sessions. Neither representation has been confirmed as authoritative.
- **Local synthesis:** *If* Northstar uses separate sessions, P7 plus H2 supports reserving two review days. This is a conditional inference, not a handbook quotation or a prediction that delay will occur.
- **Hypothesis:** a joint session could make the second day unnecessary. Confirmation of the session format would test the applicability condition.

Review outcome: retain both schedule representations and the conditional branches. Do not merge “joint” and “separate,” convert H2 into a mandatory local rule, or count P7's quotation of H2 as another recommendation source. The project owner decides its calendar and vocabulary.

### Agent research: duplicated claims and version scope

**Question:** Does fictional tool “Lumen” 4.2 support offline index refresh?

- Manual A states that refresh is unavailable offline in version 4.1.
- Release note B states that 4.2 adds offline refresh when a local manifest already exists.
- Blog C repeats B's sentence and links to B; summary D was generated from C.
- Lab observation E records one successful 4.2 refresh with a pre-existing manifest and one failure without it.
- Hypothesis F proposes that manifest presence is the controlling condition; the two trials are too narrow to establish all causes.

The synthesis candidate says: “For the observed 4.2 setup, offline refresh succeeded when a local manifest existed. This is consistent with B. A concerns 4.1 and is not a contradiction. C and D are descendants of B, so they add navigation paths but no independent corroboration. General support without a manifest remains unsupported by these materials.”

Review must preserve versions, the manifest condition, both observations, and F's hypothesis status. “Lumen” is not silently equated with another similarly named tool. Even after acceptance, this knowledge cannot authorize an agent to modify an index or enable network access.

### Infrastructure: conflicting evidence and action authority

**Question:** Why did synthetic service “Harbor” restart, and should its memory limit change?

- Alert record A observes a restart at 14:03 in staging and labels the reason “memory threshold.”
- Node record B observes host maintenance at 14:02 and no threshold event, but its clock may differ by up to two minutes.
- Runbook C recommends raising the limit only after two confirmed memory-pressure incidents on the same service version.
- Configuration record D states that staging runs Harbor 8.0; the only earlier memory incident used 7.8.

Candidate synthesis: A and B conflict about cause; timing uncertainty prevents ordering them conclusively. “Memory pressure” remains a candidate cause, not a confirmed cause. C's two-incident condition is unmet for version 8.0, so the evidence does not support its recommended limit change. The next diagnostic step may be to compare clock-corrected event records, subject to access and change approval.

The last sentence is guidance, not permission to query a host, change a limit, or use credentials. An infrastructure owner must authorize any action through the normal operational process.

## Lesson candidate and review

A lesson captures a reusable, reviewed account of a problem and response. It is not merely a successful command or a generalized incident summary. In prose or consumer-owned fields, preserve:

- **context:** environment, component, version, and triggering conditions;
- **observation:** what was directly seen and how;
- **cause status:** suspected, supported, confirmed, disproved, or unresolved, with the evidence for that status;
- **attempted remedy:** what was tried, including failed or partial attempts;
- **verification:** the bounded check and result after the remedy;
- **applicability:** where and when reuse is justified;
- **counterexamples and exclusions:** cases where it failed, was not tested, or should not be used;
- **provenance:** the sanitized incident/source lineage and review origin.

Illustrative lesson candidate:

> **Context:** Harbor 8.0 staging workers using queue mode “paced” sometimes stop accepting jobs after a configuration reload.
>
> **Observation:** In two sanitized staging trials, workers retained an expired lease after reload; a third trial in mode “burst” did not reproduce it.
>
> **Cause status:** Supported, not confirmed: lease invalidation during paced-mode reload explains the recorded state, but scheduler timing was not isolated.
>
> **Attempted remedy:** Restarting the whole node restored work but disrupted unrelated workers. Refreshing only the affected worker lease restored work in both reproductions.
>
> **Verification:** After lease refresh, ten synthetic jobs completed in each reproduction; no production or long-duration test was performed.
>
> **Applicability:** Candidate guidance for Harbor 8.0, paced mode, and the observed reload path only.
>
> **Counterexamples:** Burst mode did not reproduce; Harbor 7.x and 8.1 were not tested.
>
> **Provenance:** Two trials share one synthetic test plan and therefore count as repeated observations, not two independent source lineages.

Reviewers should confirm that the lesson does not overstate causality, hide the disruptive failed remedy, or broaden versions. They should also check redaction, ownership, duplication, and whether the destination scope is appropriate.

Lesson reuse scope remains separate from access and ownership. Existing project and workspace lesson IDs remain local to their owners. Capture resolves exactly one destination; lookup behavior is unchanged; project-to-workspace promotion or demotion remains a separate, manual, reviewed operation. Promotion itself does not delete its source; continued retention is subject to a separately reviewed retention, retraction, or deletion decision under existing contracts. Promotion does not create automatic synchronization, dual writes, or authority for future action.

## Reviewer checklist

### Evidence and reasoning

- [ ] Each consequential statement is recognizable as source-stated fact, attributed recommendation, synthesis, hypothesis, or operational observation.
- [ ] Every synthesis exposes its material premises and is not presented as a quotation or independent observation.
- [ ] Negation, conditions, versions, dates, exceptions, uncertainty, and disagreements survived condensation.
- [ ] Exact duplicates, similar captures, entity identity, and claim equivalence were evaluated separately.
- [ ] Copied or derived sources retain origin links and are not counted as independent corroboration.
- [ ] Unresolved identity and conflicting evidence remain visible rather than being silently merged.

### Ownership and lifecycle

- [ ] The consumer still owns domain vocabulary, folders, identifiers, editorial states, and acceptance.
- [ ] Candidate output is visibly distinct from reviewed knowledge.
- [ ] Historical evidence was preserved; updates use an explicit revision, correction, or lifecycle decision.
- [ ] Any lesson retains context, observation, cause status, remedies, verification, applicability, counterexamples, and provenance.
- [ ] Reusable scope was not confused with source access, store ownership, or promotion status.

### Safety and non-actions

- [ ] No prompt, recommendation, candidate, graph edge, lifecycle label, or reviewed knowledge is treated as permission to act.
- [ ] Publication, execution, mutation, and promotion each require their normal current authority.
- [ ] The draft does not introduce a persisted schema, universal taxonomy, graph service, migration, or automatic writer.
- [ ] Illustrations are not represented as benchmark fixtures, ground truth, or measured performance.

## Relationship to current contracts

Use this guide alongside, not instead of:

- [the minimal OKF v0.2 canonical profile](../OKF_V0_2_CANONICAL_PROFILE.md), which keeps types and extensions open;
- [the bounded provenance/freshness profile](../CANONICAL_PROVENANCE_FRESHNESS_PROFILE.md), whose syntactic validation does not prove truth, trust, or authority;
- [lesson ownership and routing](../LESSON_ROUTING_POLICY.md), which requires one explicit capture destination;
- [reviewed lesson promotion and demotion](../LESSON_PROMOTION_WORKFLOW.md), which preserves one-owner writes and manual review;
- [shared lesson metadata](../SHARED_LESSON_METADATA.md), which distinguishes ownership, origin, observation, and applicability;
- [consumer-overlay research](../CONSUMER_CANONICAL_PROFILE_OVERLAY_RESEARCH.md), which leaves stricter local vocabularies and review policies with consumers.

Those documents remain authoritative within their stated scopes. This draft neither changes them nor resolves future persisted-artifact or policy decisions. Its examples are explanatory only and are intentionally independent of any benchmark-fixture work.
