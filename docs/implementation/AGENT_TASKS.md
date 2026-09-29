# Bounded tasks for Codex and other agents

Status: task prompts, not evidence that any job has been dispatched or started. Parent: [#121](https://github.com/ozand/kb-bootstrap/issues/121). Before merge, use the explicit planning branch/PR linked from the epic; do not assume these documents already exist on `main`.

## Common task contract

Use this preamble with one task below:

```text
Work only in ozand/kb-bootstrap. Read AGENTS.md, docs/implementation/README.md,
the selected Issue and current comments, docs/adr/INDEX.md and relevant accepted
contracts. Verify repository identity and current main before work. Use one
separate task branch/worktree. Treat the September analysis as research leads,
not current passing tests or approval of every proposed design.

Do one bounded slice. Use synthetic data only. Do not modify consumer repos,
download models, call external inference, alter remotes, force-push, auto-merge,
or close broader Issues. Preserve public contracts unless an accepted scoped
successor explicitly authorizes the change. A regression fix within an accepted
contract needs focused tests, not unrelated redesign. New contracts need a
Proposed ADR and owner review before implementation.

Return a focused PR or patch, reproduction evidence, actual tests/results,
checks not run, compatibility impact and remaining decisions. Do not label a
proposal implemented or a model score verified truth.
```

## Task A: initial regression characterization (W11, #132)

```text
Characterize only Markdown-link handling in graph_linter and graph export.
Inspect accepted contracts first. Add small synthetic cases for an external
URL ending in .md, a link inside a fenced block, an ordinary missing local
link and a valid existing local link. Record current outcomes and whether the
contract declares them correct. Do not broaden bundle/raw/lesson semantics.
If a narrow fix clearly restores an accepted contract, include it with the
regression and safe counterexample. Otherwise return tests plus a documented
decision question, without redefining the contract. Do not implement W01-W10.
```

## Task B: independent portability reproduction (W12-A, #133)

```text
Investigate the declared minimum Python version versus actual dependency
installation and Path.stat usage. Test the declared minimum in an isolated
environment when available; distinguish a missing interpreter from a failing
test. Cover one representative command and a modern supported interpreter.
Prefer a minimal compatibility-preserving patch only when justified. Do not
raise requires-python or clean unrelated files without an explicit decision.
Return a separate PR; completing this slice does not complete all of #133.
```

## Task C: optionality decision (W01, #122)

```text
Produce a documentation-only Proposed ADR and migration matrix separating local
knowledge operations from optional QMD/Surf/GLiNER and remote-publication checks.
Inspect historical #4/#6 and current validation/skills. Specify not-configured,
disabled, available and configured-broken outcomes. Preserve publication safety
and consumer-required checks. Compare compatibility alternatives and recommend
one, but leave the decision Proposed. No production code or schema changes.
```

## Task D: safe repeated initialization (W02, #123)

```text
In a temporary synthetic consumer, initialize, modify one generated QMD config
and skill, and rerun. Record exact before/after paths and hashes. Propose safe
repeat/conflict/upgrade behaviour with failure tests and migration implications.
Do not rerun initialization on any real consumer. Implement only a separately
accepted narrow contract; otherwise submit the reproduction and Proposed ADR.
```

## Task E: source/capture contract (W03, #124)

```text
Draft a versioned data-only contract and original fixtures distinguishing source
identity, original revision, capture revision, transformation and source card.
Start with supplied local Markdown/text plus explicit provenance. Include partial,
blocked and manual-summary representations and references to original coordinates
only when known. Reuse ADR-010 without changing its v1 schema. No converter,
network collector, automatic fetch or confidential input. Design-only until accepted.
```

## Task F: evaluation baseline (W10, #131)

```text
Prepare original synthetic PM, agent-research and infrastructure scenarios using
docs/implementation/EVALUATION_PLAN.md. Specify reader questions, supporting
fragments, contradictions and a two-revision change trace. Separate agent-visible
inputs from evaluator answers. No real consumer excerpts, optional-model download
or claimed benchmark result. Return the fixture specification and deterministic
checks that can already run against existing functionality.
```

## Later implementation task template

```text
Implement only the accepted slice of Issue <number>. Name the governing Accepted
ADR and verified prerequisite outputs. Reproduce current behaviour before editing.
Add normal, malformed, unavailable-capability, mutation-safety and compatibility
tests appropriate to this slice. Keep optional integrations absent in core tests.
Do not expand into an unaccepted public schema. Return the verification receipt
below and leave unrelated acceptance boxes untouched.
```

## Verification receipt

Record repository, task/Issue, base and head commit, governing contract, changed paths, before/after reproduction, commands/results, checks not run, security/privacy boundary tested, migration/rollback implications and PR URL. Separate structural correctness from semantic review and model/runtime measurements. Never include credentials, private source contents, unrestricted paths or full transcripts.

## Cloud result delivery

A completed cloud chat and a published GitHub commit are separate delivery stages. The official [cloud environment guide](https://learn.chatgpt.com/docs/environments/cloud-environment) describes a final answer plus diff and a separate PR or follow-up step; the [cloud workflow](https://learn.chatgpt.com/docs/cloud) requires inspecting the result before publication. A missing shell remote alone does not establish a broken environment. Never add credentials, widen permissions or recreate an environment just to make terminal push possible.

Local artifact delivery does not require remote publication. Report the verified local base and result commit IDs, the complete retained patch and actual test results, and state that GitHub publication is absent or unverified. Only a claim that the result was published to GitHub requires verification there of the target repository, PR head and changed-file list. A local commit ID, `make_pr` metadata or links to unchanged seed files do not prove publication. Use supported platform publication when separately authorized; never mutate a remote merely to make a local-result delivery claim.

Before exporting, inspect the entire base-to-result changed-file set, including untracked/new files, and verify that every changed path is authorized. If any path is outside scope, stop, report the complete mismatch and do not produce a filtered patch or claim a reproducible result. Once the set passes, export the complete diff from the verified base to the result, including new files; check the export command's exit status before hashing, because empty output after a Git error is not an artifact. Preserve the exact patch bytes without truncation. State the byte length, SHA-256 and newline convention used for those bytes, and put the patch in an unambiguous outer Markdown fence longer than every fence contained in the patch (for example, four backticks only when the longest inner fence is three). Report the base/result IDs and complete changed-path list alongside it.

An authorized coordinator can publish those checked bytes as an exact patch. Applying them to the stated base can establish content and resulting-tree equivalence, but different author, committer, timestamp, parent or other commit metadata produces a different commit ID; do not claim commit-ID equivalence unless the published commit itself is identical and verified. Do not infer publication from the patch, `make_pr`, or the local result SHA. Do not infer that a new PR comment can access an earlier task's local commit; if the artifact is absent, return that limitation without reconstructing it or reusing old test results as new evidence. A new implementation attempt requires an explicit decision and must not be labelled recovery of the original artifact.

## Dispatching and reviewing with Codex

Paste one task into a Codex environment connected to this repository. GitHub access from another tool does not prove that a Codex environment is configured. Do not assign all packages at once.

The official [GitHub integration guide](https://developers.openai.com/codex/integrations/github/) documents `@codex review` in a PR comment after repository setup; other `@codex` PR comments can request tasks using that PR as context. A mention is a request, not proof of execution. Confirm the bot response/task link before claiming a run started. A review does not implement an Issue or accept an ADR. This package does not enable integrations or change permissions.
