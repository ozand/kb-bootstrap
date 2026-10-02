# Research baseline and traceability

Prepared: 2026-09-28. Status: bounded synthesis for planning, not a benchmark report or an independent re-run of all cited systems.

## Evidence classes

The owner supplied product clarifications, five analytical review exports and a saved LinkedIn discussion. Their framing is retained below. The exports contain earlier analysis and references, not new implementation evidence. Source-derived observations, owner requirements and proposed design transfers must remain distinguishable.

Private consumer contents, their detailed operational data and full chat exports are deliberately not published here. The three domain scenarios are generic abstractions, not copied corpora. External code/model licences and redistribution rights need separate verification before reuse; a public link is not permission to bundle its content or weights.

## Supplied reviews

| ID | Supplied topic | Contribution to the programme | Limit |
|---|---|---|---|
| R01 | Initial kb-bootstrap code review | QMD registration/install leads, scaffold overwrite, link parsing, runtime/naming/packaging leads -> W02/W06/W11/W12 | Baseline 9717bc2; full suite and QMD end-to-end were not run in that review |
| R02 | Owner-intent and lifecycle analysis | Tool independence, sources-to-capture chain, synthesis vs source fact, revisions and handoff -> W01/W03/W05/W07/W08 | Recommendations are not accepted schema decisions |
| R03 | Three knowledge-base examples | Domain independence, human/agent readership, logical layers and consumer-owned profiles -> W05/W09/W10 | Do not copy private consumer schemas/data into universal requirements |
| R04 | OpenWiki and memory-library analysis | Versioned evidence, sparse updates, durable progress, bounded reads, layered context -> W06/W07/W08/W10 | OpenWiki baseline 771138461274e89072f07eb648452008be32280c; memory-library review baseline 5dff47edfe98aff763edbc7825b775841113ae00; no model/benchmark execution |
| R05 | Fastino/LinkedIn analysis | Optional extraction/classification/relation research, confidence/authority separation, measured ablations -> W09/W10 | Vendor/research results are not measurements on kb-bootstrap corpora |

The owner-stated intent in [Product intent](PRODUCT_INTENT.md) governs the proposed direction. The assistant's proposed implementation choices require review; do not quietly elevate them to owner decisions.

## Primary-source reading map

- [Karpathy's LLM wiki note](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): retained sources and maintained synthesis as the initial inspiration. Treat the method as inspiration, not an executable specification.
- [Open Knowledge Format](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md): portable Markdown/YAML, open types, source/trust/lifecycle metadata. Pin the reviewed revision when implementing compatibility; the old knowledge-catalog/okf location is not the current canonical home.
- [OpenWiki Claims interfaces](https://github.com/langchain-ai/openwiki/blob/771138461274e89072f07eb648452008be32280c/src/claims/core/types.ts) and [preflight](https://github.com/langchain-ai/openwiki/blob/771138461274e89072f07eb648452008be32280c/src/claims/brains/code/preflight.ts): deterministic source-version binding and changed/missing evidence classification. These do not establish semantic entailment, and the reviewed implementation grounds repository evidence rather than arbitrary external captures.
- [OpenWiki retrieval](https://github.com/langchain-ai/openwiki/blob/771138461274e89072f07eb648452008be32280c/src/retrieval/wiki.ts): bounded discovery/read separation. [LEDGER](https://github.com/langchain-ai/openwiki/blob/771138461274e89072f07eb648452008be32280c/evals/ledger/README.md): evolving-source evaluation; add coverage tests because claim health alone does not establish topic completeness.
- [OpenViking](https://github.com/volcengine/OpenViking): reading-depth tiers and canonical/derived separation. [Hindsight](https://github.com/vectorize-io/hindsight): retained evidence, consolidation and maintained question-oriented knowledge. These are transfer ideas, not reasons to adopt an entire memory platform.
- [QMD](https://github.com/tobi/qmd): optional lexical/vector/hybrid retrieval. [Surf](https://github.com/nicobailon/surf-cli): one collection implementation, not a local model or a guarantee of no external traffic.
- [GLiNER](https://github.com/urchade/GLiNER), [GLiNER2](https://github.com/fastino-ai/GLiNER2), [Fastino blog](https://fastino.ai/blog) and [research](https://fastino.ai/research): optional candidate extraction, classification, relations and evaluation research. Different models/packages/tasks are not interchangeable; verify versions, hardware assumptions and licences before an experiment.
- [Supplied LinkedIn post](https://www.linkedin.com/posts/gehm_agent-memory-is-highly-complex-but-getting-share-7503857736191754241-f0Hp/): discussion of structured memory and small extractors. The saved capture date is 2026-09-28; its publication metadata is blank. Do not invent a publication date or treat promotional claims as benchmark results.

## Transfers and cautions preserved from the reviews

Use deterministic bookkeeping around probabilistic analysis. Keep versioned evidence, work progress and retrieval projections distinct. Preserve existing facts without resubmitting all of them on every model turn, but do not infer that an unchanged fragment proves current truth.

A graph makes relationships queryable; it does not decide which knowledge is authoritative. Model confidence is not calibrated truth probability. Constrained output is not semantic correctness. Preserve corrections, retirement and the policy governing what may be discarded.

A local CPU model may reduce repeated expensive processing, but throughput and quality must be measured on the actual task and language. A classifier without evidence spans cannot manufacture them. PII detection is not publication permission. Relation/classification/security experiments do not enlarge #100's accepted local candidate scope automatically.

The supplied Fastino review discussed GLiNER2/2.5, Decide, GLiGuard, PII, Pioneer Agent and PROBE. It reported benchmark caveats rather than a universal improvement. No numerical performance claim is adopted as a release target here. Use [Evaluation plan](EVALUATION_PLAN.md) to establish a local baseline and record failures as well as gains.

## Updating this baseline

For a changed conclusion record the new source revision/date, what changed, which work-package assumption is affected, and whether a public contract needs reconsideration. Do not overwrite historical observations with a current claim without attribution. Raw source retention may require a separate permitted storage location; this public planning directory is not a dump of research originals.
