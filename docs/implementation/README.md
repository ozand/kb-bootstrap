# Knowledge lifecycle implementation programme

Date: 2026-09-28. Planning baseline: `9717bc29c7ab455cc8a7648c8f740e7f9959967a` (package version 0.4.0). Target: `ozand/kb-bootstrap`, default branch `main`.

**Status: planning package for review. No runtime feature or new public schema is implemented by these documents.**

Tracking: [epic #121](https://github.com/ozand/kb-bootstrap/issues/121). The owner's request authorizes preparing implementation documents and Issues. It does not by itself approve new schema details, model downloads, network endpoints, migrations or automatic publication.

## Reading order

| Document | Purpose |
|---|---|
| [Product intent](PRODUCT_INTENT.md) | Owner requirements, domain independence and explicit non-goals |
| [Architecture proposal](ARCHITECTURE_PROPOSAL.md) | Logical boundaries, lifecycle, compatibility and decision gates |
| [Work packages](WORK_PACKAGES.md) | Actual Issues, dependencies, parallel work and completion rules |
| [Agent tasks](AGENT_TASKS.md) | Copyable bounded Codex/agent tasks and verification receipt |
| [Research baseline](RESEARCH_BASELINE.md) | Attribution, provenance and limits of the supplied reviews |
| [Evaluation plan](EVALUATION_PLAN.md) | Synthetic scenarios, changing-source traces and optional-model comparisons |

## What changes in the product framing

A knowledge base may cover project-management practice, comparative research or a managed environment. It need not document software being developed. People and agents use the same retained knowledge. Sources, readable captures, synthesized knowledge, work progress and search projections have different roles. QMD, Surf, GLiNER-family models and agent hosts are replaceable, optional capabilities.

This is a target direction, not a claim that current commands already satisfy it. In particular, existing QMD validation/completion coupling remains current behaviour until W01 is accepted and implemented.

## Starting work

Safe first tasks are reproductions in #123, #132 and #133; documentation/decision work in #122, #126 and #130; and synthetic fixture design in #131. These are not invitations to implement the whole epic. Select one narrow slice from [Agent tasks](AGENT_TASKS.md).

Work that introduces a persisted/public contract begins with a Proposed ADR. Accepted ADRs stay authoritative until specifically superseded. A bug fix preserving an already accepted contract does not require an unrelated redesign. A documents-only PR does not close an implementation issue.

## Existing work and ownership

Reuse #90-#92 and #100-#102/#109. #108 remains a separate opt-in remote adapter and is not needed by the local core. ADR-010/raw-manifest is a foundation to verify and reuse, not reimplement. The [ADR index](../adr/INDEX.md), [contribution workflow](../CONTRIBUTING_UPSTREAM.md), [validation composition](../VALIDATION_COMPOSITION.md) and [retention policy](../EVIDENCE_RETENTION.md) remain relevant.

No private consumer payload, full conversation export or model asset is included. Domain examples are synthetic. Issues are cross-linked tracking units, not claims that another agent has started execution. See the live epic/PR for delivery and execution status.
