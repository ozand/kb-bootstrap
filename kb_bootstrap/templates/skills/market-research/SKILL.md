---
name: market-research
description: Research products, competitors and technologies from public web sources and store the study in the repository knowledge base — every analysed page captured as Markdown with screenshots under kb/research/<date>_<slug>/raw/, conclusions as entities, concepts and a report under kb/wiki/. Covers feature and technology matrices, UX/UI patterns, positioning and reviews, pricing, JTBD and customer journey maps, and multi-agent market maps. Use when the user asks to research, benchmark, compare or analyse competitors, alternatives, a market, UX references or a technology choice.
license: MIT
compatibility: Needs the surf browser CLI connected to Chrome/Chromium and Python 3.9+; kb-bootstrap and qmd are optional (validation, search).
metadata:
  author: ozand
  version: "2.0"
---

# market-research

A study is evidence first, conclusions second. Two layers in the repository, never in
`/tmp` or a chat message:

```
kb/research/<YYYY-MM-DD>_<slug>/   one folder per study
  brief.md                         question, scope, dimensions, done-criteria
  raw/NNN-<slug>.md                one captured page each — immutable evidence
  raw/img/NNN-<k>.<ext>            screenshots from that page
kb/wiki/                           conclusions shared by all studies (OKF frontmatter)
  entities/<slug>.md               products, companies, technologies
  concepts/<slug>.md               patterns, approaches, jobs
  reports/<YYYY-MM-DD>_<slug>.md   the result of one study
  index.md
```

`SKILL_DIR` below is the folder of this file (e.g. `.agents/skills/market-research`).

## Repository governance gate

Before creating a branch, commit, Issue or pull request, decide whether the study is
consumer-owned knowledge (the normal case — it belongs to the current project) or a change
to reusable upstream framework content, name the target `owner/repository`, and run
`kb-bootstrap doctor --repo <owner/repository>`; stop unless it prints `RESULT: OK`.
Upstream framework changes go in a separate verified checkout or worktree. Before claiming
a committed study complete, run
`kb-bootstrap check-completion --repo <owner/repository> --commit <commit> [--pr <number>]`.
If kb-bootstrap is not installed, verify `git remote -v` and `gh repo view` by hand.

## Workflow

Copy this checklist into your notes and tick it off:

- [ ] 0. Look up what is known: `qmd search "<topic>" -c <project>-wiki` (collection names
      are in `qmd/collections/*.yaml`) or `grep -ril "<topic>" kb/wiki`. Extend existing
      studies, entities and concepts instead of duplicating them. No `kb/wiki/`? Run
      `kb-bootstrap --type single` or create `kb/research/` and `kb/wiki/{entities,concepts,reports}/`.
- [ ] 1. Brief: `python3 SKILL_DIR/scripts/new_research.py <slug> --title "<title>" --issue <url>`,
      then fill it (template: [assets/brief-template.md](assets/brief-template.md)). Pick
      the dimensions the question needs — not all of them every time.
- [ ] 2. Find sources: read [references/sources.md](references/sources.md) once per study.
      Discover real articles with `python3 SKILL_DIR/scripts/find_links.py <site-or-search-url> --match <kw,kw> --window-id <id>`.
- [ ] 3. Capture every page you will rely on:
      `python3 SKILL_DIR/scripts/capture_page.py kb/research/<folder> <url> --entity <slug> --window-id <id> --images <N> --by "<agent>"`
- [ ] 4. Analyse per dimension — load only the references the brief needs:
      feature matrix → [references/feature-matrix.md](references/feature-matrix.md);
      technology, platforms, pricing → [references/technology.md](references/technology.md);
      UX/UI → [references/ux-patterns.md](references/ux-patterns.md);
      strengths, weaknesses, reviews → [references/positioning.md](references/positioning.md);
      JTBD and CJM → [references/jtbd-cjm.md](references/jtbd-cjm.md).
- [ ] 5. Write wiki: entities → concepts → report, formats in
      [references/formats.md](references/formats.md), report skeleton in
      [assets/report-template.md](assets/report-template.md). Add new docs to `kb/wiki/index.md`.
- [ ] 6. Ground every claim (below).
- [ ] 7. Check: `python3 SKILL_DIR/scripts/check_research.py kb/research/<folder>` → `OK`, then
      `kb-bootstrap validate --dir kb --project-root .` (0 errors) and `qmd update` if configured.
      Every `WARN` is unfinished work; if it cannot be fixed, say why in the report's Limitations.
      Re-read the brief's done-criteria and confirm each one.
- [ ] 8. Deliver one PR `docs(kb): <topic> (#<issue>)`; final message: report path, number of
      raw pages and screenshots, top conclusions.

Commit and push after every 3–4 products so a crash or context reset loses nothing.

Several agents on one market map, or one study split by product area? Read
[references/parallel-studies.md](references/parallel-studies.md) before dispatching.

## Ground every claim

Write only what captured raw pages say. Reviews of real studies found invented thresholds,
feature and plan names, export formats and statistics that no raw file contained — the
model "knew" them. For every fact in the summary, every ✅ cell, every number, every
product card:

```bash
python3 SKILL_DIR/scripts/grep_claim.py kb/research/<folder> "<key term>" [--raw 019,020]
```

Found on a page with a screenshot of it → ✅ (UI); found in text → ✅ (docs), wording
close to the source; `NOT FOUND` → delete it, move it to Limitations as a hypothesis, or
capture a page that states it. Claims about the user's own product are checked in its code
or docs, not taken from the brief.

## Gotchas

- Do not print page text into your context (`surf page.text`, `page.read` on long pages):
  a 272K-token session overflowed this way. `capture_page.py` writes to disk and prints one
  line; read the saved file in parts only when needed.
- Guessed help-center URLs are usually 404 — `capture_page.py` refuses them (exit 2); use
  `find_links.py` on the help-center home, a category or the site's own search page.
- Product home pages are marketing: one line of "what it is" at most. Real UI lives in help
  centers, docs, changelogs, public demos. `check_research.py` warns when most raw pages
  are home pages.
- Cloudflare / bot checks ("Just a moment…") are saved as one-line `fidelity: blocked`
  stubs. Never cite a stub; find the same content elsewhere (docs mirror, changelog, PDF).
- Never register, log in, enter personal data, bypass captchas or paywalls, or install
  apps. A blocked source is a finding, not an obstacle to get around.
- Use your own surf window (`surf window.new <url>` once, then `--window-id <id>`); other
  agents may share the browser.
- surf `js` mangles template literals, `#` and `$` — pass scripts with `surf js --file`
  (that is why the extractor is a separate file).
- `surf go` may time out on slow pages while the tab keeps loading; the scripts tolerate it.
- Raw files are immutable and their numbers are referenced by the wiki — never edit or
  renumber them after capture.
