# Task-routing guide exercise

This exercise evaluates the advisory [`TASK_ROUTING.md`](../../guides/TASK_ROUTING.md) added in commit `a93b465c3cc3507a2aad2473debd4414d0a2ab3e`.

All four inputs and the request in this directory are synthetic fixtures. Two readers knew the broad input types before applying the guide; the guide author also participated. This is a small, non-blind exercise, not a general usability or retrieval-quality evaluation.

The exercise asks readers to choose an existing procedure, retain suitable source evidence, propose a draft, state a needed check and stop condition, and say what the result would not establish. It used no application runtime, additional inference call, index update, external source or consumer data. Agent-reader responses were used. It does not establish accuracy, truth, runtime behavior, general model quality, or that a real workflow is validated.

## Reader observations

Both readers had prior exposure to the four broad input types; reader A also authored the guide, while reader B was independent. The exercise was not blind.

- **README (A and B):** draft a source-reported overview, retain the claim and unknown date/version, and check source coverage plus local policy. Neither reader treated it as code, performance, current behavior, or verified truth.
- **Specification (A and B):** retain clauses 2–4 with `SHALL`/`MAY`, draft status, and unresolved details. Neither inferred implementation, certification, or hardware behavior.
- **Measurement payload (A and B):** preserve each `reported`, `estimated`, or `unknown` record with value/null, unit, protocol/repetition fields and unknown revision. With no defined schema/importer, stop before normalization/import or promotion to `measured`; do not infer a real experiment from synthetic data.
- **Transcript excerpt (A and B):** use optional material classification only if already available, otherwise manual classification without installation. Retain speaker/time locators and missing-remainder uncertainty; treat the lesson as contextual and hypothetical, not a production or outage claim.

The guide led to differentiated handling, especially a stop on lossy measurement import and a no-install transcript fallback. This is one small, non-blind exercise, not evidence of accuracy, general usability, runtime behavior, or model quality. No application runtime, additional inference call, or index update was executed; agent-reader responses were the only reader inputs. No external sources or consumer workflows were used.
