# Parallel studies and the consolidated market map

Read before splitting a large research across several agents, and before consolidating.

## Split

- One study per coherent product area (e.g. ingest, editor, search, privacy…), one agent,
  one issue, one branch/worktree each. 4–7 studies is manageable for one reviewer.
- All briefs share the same report skeleton ([../assets/report-template.md](../assets/report-template.md))
  and legend, so tables can be merged later. Put an umbrella issue above them.
- Write each brief with: the area as the user's product has it today (from code), the
  product list, the dimensions, done-criteria, and the parallel-mode rules below.

## Dispatch to another agent

- Reset its session first (a fresh context per study).
- Give the **absolute path** to this skill in its worktree —
  `<worktree>/.agents/skills/market-research/SKILL.md` — and tell it to read it fully. An
  agent started elsewhere does not discover the skill by name.
- Give the absolute path of the brief, its issue, branch, and the PR rules (open, do not merge).

## Parallel-mode rules (put them in every brief)

- Do not create or edit `kb/wiki/entities/*` or `kb/wiki/index.md` — write product facts
  into the report's "Draft product cards" section; consolidation creates the entities.
- Create only new concepts with a unique slug (`ls kb/wiki/concepts/` first); do not edit
  existing ones — describe additions in the report.

## Review each study before merging

1. `check_research.py` OK, no WARN.
2. Spot-check 4–6 claims with `grep_claim.py` — summary facts, a few ✅ cells, numbers.
   Any `NOT FOUND` → send it back with the exact list; expect this in about half of first
   submissions.
3. Look at 2 screenshots: real UI or marketing?

## Consolidate (separate study, after all merged)

- Report `kb/wiki/reports/<date>_market-map.md`: one capability × product matrix across all
  areas (merge rows, keep the legend), positioning of the user's product, prioritised
  opportunities (must/should/nice) with links to area reports.
- Create/update `kb/wiki/entities/` from the draft product cards (merge facts, keep raw links),
  update `kb/wiki/index.md`.
- Fix inconsistencies between area reports (the same product rated differently) by going
  back to raw, not by picking one.
