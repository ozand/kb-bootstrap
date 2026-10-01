# W11-A: Markdown-link regression task

Status: execution brief only; no implementation or passing test result is claimed by this seed commit.

Parent work package: [#132](https://github.com/ozand/kb-bootstrap/issues/132). Programme: [#121](https://github.com/ozand/kb-bootstrap/issues/121).

The owner authorized starting this one bounded Codex task on 2026-09-28. Target repository: `ozand/kb-bootstrap`. Work branch: `codex/132-markdown-link-regressions`. Initial base: `9717bc29c7ab455cc8a7648c8f740e7f9959967a` on `main`. Keep the planning PR [#134](https://github.com/ozand/kb-bootstrap/pull/134) and its branch unchanged. This task does not accept any new architecture proposal or authorize the rest of the epic.

## Read before editing

Read the current issue and comments, applicable repository instructions, [contribution workflow](../CONTRIBUTING_UPSTREAM.md), [ADR index](../adr/INDEX.md), [canonical profile](../OKF_V0_2_CANONICAL_PROFILE.md) and [graph export contract](../CANONICAL_GRAPH_EXPORT.md). Inspect ADR-003, ADR-005 and ADR-009, plus `kb_bootstrap/graph_linter.py`, `kb_bootstrap/canonical_graph_export.py` and their existing tests.

The planning documents from #134 may not be on main yet. Optional background: [Task A at the pinned planning commit](https://github.com/ozand/kb-bootstrap/blob/156f4724a0d4c4183d8b3dc72850f21694b188f3/docs/implementation/AGENT_TASKS.md). This brief is self-contained; do not merge or copy the planning PR just to start.

## Task

Reproduce and characterize exactly these four cases in a small temporary synthetic KB:

1. A body link to an external HTTPS URL ending in `.md`.
2. A link to `missing.md` inside a fenced code example.
3. An ordinary body link to a genuinely missing local Markdown concept.
4. An ordinary body link to a valid existing local Markdown concept.

Compare the graph linter and graph export outcomes against their accepted contracts. A suspected inconsistency is a research lead, not proof of a bug. If the first two cases violate an existing contract, make the smallest correction and add focused regression tests. Retain the third case as a failing integrity check and the fourth as a valid edge. Reuse existing parsing code only where its semantics really match; do not introduce a broad parser rewrite or new dependency.

If the desired behaviour requires changing a public contract rather than fixing a regression, record the precise decision needed and return the reproduction/characterization without implementing that policy change. Do not commit deliberately failing tests as though the implementation were finished.

## Scope boundaries

- Preserve existing raw evidence-link handling from #120, lesson exclusions, reserved-file rules, path containment and symlink protections.
- Do not change canonical layer traversal, research brief status, bundle format, public CLI semantics, QMD configuration or other portions of #132.
- Do not fetch external link targets during validation or tests. Use synthetic data only; do not read or change consumer repositories.
- Do not install models, invoke additional inference services, alter permissions/remotes, force-push, merge, or close #132/#121. Existing configured Codex execution is the authorized coding task; model-provisioning experiments are not.
- Make changes only on this work branch. If pushing is unavailable, return a patch/task result and clearly state that it was not published.

## Verification and delivery

Run relevant focused tests and the repository's existing suite (`python -m unittest discover -s tests -v`) when the environment supports it. Record missing dependencies or checks not run instead of implying success. Verify that source files are unchanged by lint/export operations and that external targets are never fetched. Run `git diff --check` and inspect the changed-file list before delivery.

Expected deliverables are a narrow patch on this PR, synthetic regression tests, a compact before/after outcome matrix, and actual commands/results. The final report should include base/head commits, changed paths, governing contract, any remaining decision, checks not run and the PR/task link. Explain results in Russian for the owner. Keep this PR in draft pending owner review; completing this slice does not complete all of #132.
