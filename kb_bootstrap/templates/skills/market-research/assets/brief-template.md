---
type: ResearchBrief
title: {title_json}
started: {date}
issue: {issue}
status: draft
workflow_status: in-progress
---

# {title}

<!-- Write in the user's language. Delete hint comments when filling. -->

## Why
<!-- Which product decision this study informs; for which screen/feature/strategy. -->

## Our product today
<!-- What the user's product does in this area — from its code/docs, with paths. -->

## Questions
1. <!-- what exactly to find out -->

## Scope
- Products / sources (priority first): <!-- names; add notable ones found on the way -->
- Out of scope: <!-- what is deliberately not studied -->

## Dimensions
<!-- Keep only what the questions need. Each maps to a reference in the skill. -->
<!-- For validation and non-UX screenshot thresholds, follow step 7 of the market-research skill. -->
- [ ] Feature matrix — capability × product (references/feature-matrix.md)
- [ ] Technology, platforms, pricing (references/technology.md)
- [ ] UX/UI patterns with screenshots (references/ux-patterns.md)
- [ ] Positioning, strengths/weaknesses from reviews (references/positioning.md)
- [ ] JTBD and customer journey map (references/jtbd-cjm.md)

## Done when
- ≥ <N> products in the feature matrix; ≥ <N> raw pages, mostly docs/help/reviews, not home pages
- ≥ <N> screenshots of real UI for the key screens when UX is in scope
- every claim grounded in raw (`grep_claim.py`); follow step 7 of the market-research skill for study checks and report any unresolved WARN in Limitations
- report follows assets/report-template.md

## Result
Report: kb/wiki/reports/{date}_{slug}.md
