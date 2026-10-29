# ADR-043: Clarify ADR-041's lesson schema destination

**Status**: Proposed
**Date**: 2026-10-29
**Authors**: Pi coding agent
**Supersedes**: A single destination-scope sentence in ADR-041, only if accepted
**Related**: Issue #234; ADR-003; ADR-041

## Context

Accepted ADR-041 distinguishes safe reference destinations from canonical graph nodes. Its Decision says: “A Markdown file under an excluded case-insensitive `lessons/` directory may be a safe destination if its explicit path resolves to an existing regular, non-symlink file within the root.” Read literally, this allows every such lesson Markdown file as a link destination.

The owner’s explicit Issue #234 scope refinement instead names only `lessons/SCHEMA.md`. The already-merged implementation in `kb_bootstrap/graph_linter.py` likewise recognizes the exact normalized root-relative string `lessons/SCHEMA.md`; it does not authorize arbitrary lesson files, nested schema paths, or case variants. This proposal resolves that text/runtime mismatch by preserving the narrower owner-authorized scope, not by expanding runtime access.

## Decision

If accepted, supersede only the quoted ADR-041 destination-scope sentence above with this bounded rule:

- A link may target the existing root-relative path spelled exactly `lessons/SCHEMA.md`. The link target is compared using that exact path and case; only this path qualifies. It must resolve to an existing regular file within the canonical root, and no component may traverse a symlink.
- This exception checks only the explicitly named path for existence and safety. It does not read the target file’s contents, enumerate it, traverse it, or add it as a graph node, source, or edge.
- All other links into excluded `lessons/` remain rejected as dead/invalid targets, including other Markdown files, nested `lessons/**/SCHEMA.md`, and case variants such as `Lessons/SCHEMA.md` or `lessons/schema.md`. Missing paths, non-regular files, and symlink/escaping paths remain rejected.

This clarification records the existing implementation and owner-narrowed scope. It authorizes no runtime change. ADR-041 remains accepted and unchanged as historical text; only the quoted sentence is proposed for replacement upon acceptance of this ADR. No other ADR-041 decision or consequence is superseded. In particular, reserved `index.md`/`log.md` behavior, canonical graph nodes/sources, ordinary graph edges and orphan counting, diagnostics, safety checks, read-only behavior, and the ADR-005 exporter contract remain as ADR-041 states.

## Alternatives Considered

### Allow every safe Markdown file below excluded lessons

Rejected: it broadens the explicit owner refinement and differs from the merged exact-path runtime behavior.

### Rewrite accepted ADR-041 in place

Rejected: accepted ADR history must remain unchanged. This ADR proposes an explicit, reviewable, sentence-scoped clarification.

### Leave the contradiction unresolved

Rejected: the accepted wording and implemented owner-scoped behavior would remain ambiguous for later reviewers and maintainers.

## Consequences

The accepted contract, if this ADR is accepted, will unambiguously permit only the exact root-relative `lessons/SCHEMA.md` destination. It will not change behavior or grant access to other lesson paths. The earlier broad sentence remains visible in ADR-041 as historical accepted text, with this ADR identifying its scoped replacement.

## Test Contract

No tests or runtime changes are introduced by this documentation proposal. Existing runtime behavior is already covered by the merged ADR-041 implementation; these are the relevant compatibility claims for independent review and future regression checks:

| Claim | Expected behavior |
|---|---|
| Exact existing root-relative `lessons/SCHEMA.md` link | Accepted as a safe destination without reading contents, adding nodes/edges, or traversing lessons |
| Other lesson Markdown target or nested schema path | Rejected; no new lessons destination is enabled |
| Case-variant path or filename | Rejected; the exception is exact-spelling and case-sensitive at the normalized link-target comparison |
| Missing exact schema target, non-regular target, or symlink/escaping path | Rejected |
| Reserved sources, graph nodes/edges/orphan behavior, and exporter contract | Unchanged from ADR-041 / ADR-005 |

The existing merged tests and reviewer evidence may be used to assess those claims. This proposal does not claim additional test coverage or implementation.

## References

- Issue #234 owner scope refinement: https://github.com/ozand/kb-bootstrap/issues/234#issuecomment-6457640826
- Accepted ADR-041: [ADR-041](ADR-041-distinguish-safe-reference-targets-from-canonical-graph-nodes.md)
- Merged exact-path implementation: `kb_bootstrap/graph_linter.py`, `is_lesson_schema = target == "lessons/SCHEMA.md"`
