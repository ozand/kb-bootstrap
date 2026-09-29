# Product intent: retained knowledge for people and agents

Status: synthesis of the owner's stated intent, prepared for review on 2026-09-28. This is not an accepted technical schema. Related: [epic #121](https://github.com/ozand/kb-bootstrap/issues/121).

## Owner-stated requirements

`kb-bootstrap` should help create and maintain domain knowledge bases. Its value is retaining the useful result of acquiring, understanding, deduplicating, connecting and updating information so later people and agents do not repeat the same work.

The central cycle is:

```text
External originals / sources
  -> retained machine-readable representations and necessary attachments
  -> investigation, comparison, distillation and linking
  -> reusable knowledge with evidence and applicability
  -> use, questions, research, observations and reviewed lessons
  -> controlled updates
```

Originals can live outside the knowledge repository. They may be presentations, images, PDFs, recordings, books, websites, APIs or already-readable files. Markdown is the common reading surface; necessary visual evidence and original coordinates must not disappear merely to obtain text. Converting already-readable code or text into a redundant summary is not inherently required.

Raw means not yet synthesized into the accepted knowledge layer, not necessarily a byte-identical original. The process must distinguish an exact capture, lossy extraction, manual summary and model-generated interpretation. Source collection should preserve the material actually used in research, where retention is permitted, rather than leave only a search URL and a final answer.

Distillation is not one summary per source. Several sources may update one concept, procedure, entity or explanation; one source may inform several concepts. Duplicate representations should not create duplicate knowledge, but independent provenance, versions and disagreements must survive.

Knowledge is organized by meaningful types, relationships and applicability. Domain vocabularies belong to the knowledge-base owner. Repository placement, content layout, knowledge domain, readership and access scope are independent choices.

People and agents are both readers and contributors. A later agent should discover relevant knowledge, read a bounded portion, inspect its limits and reach the underlying evidence when authorized. Useful output should remain usable after the producing session ends.

Research captures and experience-derived lessons feed the same lifecycle. A local lesson may be generalized for use across domains or repositories, but broader applicability does not imply broader publication rights. Existing reviewed local/shared lesson ownership remains relevant.

## Optional tools, not product identity

QMD can accelerate discovery over raw material and synthesized knowledge. It does not own the knowledge or establish its truth. A file/index reading path remains possible without it.

Surf is one way to collect rendered web content. Other browsers, APIs, MCP tools and supplied files can fulfill the same capture contract. A collector's implementation must not define the meaning of a valid source.

GLiNER-family models are possible local helpers for entity/relation extraction, classification and routing. Their value on the owner's corpora is unmeasured. Models propose candidates; they do not independently establish entity identity, semantic truth, review approval or permission to disclose data.

Local CPU-capable processing is valuable for cost and confidentiality. Actual performance needs measurement. Confidential data must not be routed to external services merely because a preferred local tool is absent. Local executables alone do not establish a no-egress security boundary.

## Synthetic acceptance domains

- Project-management knowledge: methods, roles, artifacts, conditions and attributed recommendations, with optional AI applications.
- Agent-system research: retained implementation sources, comparative patterns and evidence-backed conclusions about particular revisions.
- Managed infrastructure: observed state, software knowledge, operational procedures and sanitized evidence with strict access boundaries.

These are test scenarios, not permission to copy real consumer data. A common framework should support their differences rather than force one software-project ontology or directory tree.

## Non-goals for this programme

No mandatory graph database, vector database, memory server, cloud model, permanent background agent or specific agent framework. No mass rewrite of existing bases. No full transcript dumping into canonical knowledge. No automatic promotion of predictions to accepted facts. No guarantee that an extraction model, content hash or graph path establishes semantic correctness.

The initial programme is a small set of contracts, guidance, deterministic helpers and evaluation fixtures. Search adapters and ML experiments remain separate. Concrete new fields, commands, storage choices and review policies are proposals until accepted under [Architecture proposal](ARCHITECTURE_PROPOSAL.md).
