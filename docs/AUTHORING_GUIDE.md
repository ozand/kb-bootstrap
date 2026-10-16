# Authoring clear project documentation

This guide is for contributors writing README explanations, setup instructions, and operational notes. Keep product behavior and local repository policy as the source of truth; this is a writing aid, not a validation contract.

## Start with the reader's problem

1. Name who is trying to do what, and the symptom or decision that brings them here.
2. State what the tool does and does not do before listing installation steps.
3. Give the shortest safe path to a useful result; move optional setup and advanced details later.
4. Separate facts, recommendations, limitations, and actions requiring permission.

## Make explanations checkable

- Define unfamiliar terms when they first matter; prefer one idea per paragraph.
- Put conditions next to the action they constrain. Preserve “only if,” “unless,” “not,” dates, and scope.
- Distinguish observed output from intended state, inference, and unknown information.
- Explain what a digest, status, or successful check proves—and what it does not prove.
- Use a small example only when it clarifies a real workflow; keep it consistent with the current commands and contracts.

## Review before publishing

- Verify every command, option, path, default, and version against the current implementation or accepted contract.
- Check that a novice can identify the next step and the stop condition without guessing.
- Keep warnings, prerequisites, permissions, and rollback limits visible near the relevant step.
- Remove repeated explanations, stale examples, unexplained acronyms, and claims stronger than the evidence.
- Ask a reader to summarize the key distinction or next action; treat one response as qualitative feedback, not proof of general usability.
