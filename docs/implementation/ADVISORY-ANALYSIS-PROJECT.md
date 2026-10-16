# Advisory analysis — evidence-linked, progressive knowledge access

**Status:** advisory research summary; not product intent, accepted ADR, implementation contract, or benchmark.
**Prepared:** 2026-10-16
**Source:** operator-supplied ChatGPT project conversation “Анализ проекта” (project link recorded in the coordinating session; source was not copied into this repository).
**Scope:** selected recommendations relevant to #127 W06, #128 W07, and #131 W10 only.

## Summary

The conversation proposes a useful design lens: expose progressively richer views of existing evidence, and keep derived navigation structures separate from authoritative Markdown. This may inform future discovery/read UX, evidence impact analysis, and synthetic evaluations. It does not establish that any recommendation is correct for kb-bootstrap or authorize a schema, feature, dependency, QMD behavior, or roadmap reorder.

## Attributed observations and proposals

| Topic | Advisory proposal | Safe interpretation for this programme |
|---|---|---|
| Derived navigation | A document/section/passage projection can be derived from authoritative Markdown without rewriting the source. | Consider only as a disposable navigation projection; preserve source bytes and distinguish projection freshness from source truth. No index/config mutation is authorized here. |
| Section identity | A heading path plus occurrence/revision may help locate a section. | Treat as a candidate locator, not stable identity. Repeated headings, moved/renamed sections, and changed context must remain ambiguous or unresolved rather than silently matching. |
| Retrieval sequence | Local lexical selection may precede a richer optional hybrid/vector stage. | This is a possible pipeline, not a default or permission to change the accepted local search or QMD adapter. Any hybrid stage needs a separately accepted scope and evidence. |
| Evidence binding | Start with document-level evidence bindings before a claim registry. | This is consistent with the *proposal* in ADR-031, but ADR-031 remains Proposed. It does not accept that format or authorize implementation. |
| Freshness and meaning | Unchanged bytes do not prove current external freshness or semantic truth. | Keep byte/revision identity separate from external recapture, applicability review, and semantic support. Do not turn a digest match into a truth/freshness label. |
| Evaluation | Compare progressive views against known evidence and ambiguity cases. | #131 may use synthetic cases to test coverage, ambiguity, unchanged-source limitations, and useful reading depth. No model-quality or performance result is inferred from the source conversation. |

## Relationship to current work

- **#127 / ADR-017–019:** bounded local search/read and the optional lexical QMD adapter are already governed by accepted decisions. This note does not alter their result vocabulary, corpus selection, budgets, defaults, or adapter behavior. The actual indexed-membership smoke remains finite evidence, not proof of arbitrary configuration behavior.
- **#128 / ADR-031:** the document-level binding and read-only impact-report proposal remains Proposed. The advisory source is context only; it is not acceptance of ADR-031 or of fragment locators, schemas, or limits.
- **#131:** the synthetic evaluation issue can decide whether any of these ideas improve useful evidence navigation, but the conversation is not a local measurement. Optional-model experiments still require their existing consent and dependency gates.
- **Existing roadmap:** no package order, dependency, or acceptance criterion is changed by this note.

## Non-claims and limits

This summary is a selective paraphrase, not a complete transcript or independent validation of the source conversation. It contains no private consumer corpus, full conversation export, hidden sidebar/context, or source payload. The advisory does not establish factual correctness, owner preference, external freshness, semantic entailment, security, privacy, or measured utility. Section/passage navigation, hybrid retrieval, and claim-level work remain options requiring their own bounded decisions and evidence.

## References

- [Issue #127 — W06 bounded read/search](https://github.com/ozand/kb-bootstrap/issues/127)
- [Issue #128 — W07 evidence bindings and impact analysis](https://github.com/ozand/kb-bootstrap/issues/128)
- [Issue #131 — W10 synthetic evaluation](https://github.com/ozand/kb-bootstrap/issues/131)
- [ADR-017, ADR-018, ADR-019](../adr/INDEX.md) — accepted bounded local-search/QMD decisions
- [Proposed ADR-031, PR #191](https://github.com/ozand/kb-bootstrap/pull/191) — document-level evidence-binding proposal; not accepted
- [Evaluation plan](EVALUATION_PLAN.md)
