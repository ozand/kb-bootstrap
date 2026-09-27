# Formats: raw captures and wiki documents

All documents are Markdown with YAML frontmatter (OKF v0.2 profile of kb-bootstrap: `type`
is required; `title`, `description`, `tags`, `status` recommended). Write wiki text in the
language the user works in; the headings below may be translated.

## raw/NNN-<slug>.md — one captured page (written by capture_page.py)

```markdown
---
type: RawCapture
title: "Product A — Search your meetings"
url: "https://help.product-a.com/..."
captured_at: 2026-09-27T10:15:00+03:00
captured_by: "agent-id"
entity: "product-a"           # slug of kb/wiki/entities/<slug>.md, "" if none
fidelity: full                # full | partial | blocked
---

# <page title>

<main content as Markdown; images as ![alt](img/NNN-k.png) or remote links>
```

`NNN` is the capture order inside the study; images of that page are `img/NNN-<k>.<ext>`.
raw is immutable: corrections and opinions go to wiki.

## wiki/entities/<slug>.md — product, company, technology

```markdown
---
type: Entity
title: "Product A"
description: "<what it is in one line>"
tags: [saas, meeting-notes]
status: draft
sources:
  - resource: ../../research/<folder>/raw/003-product-a-search.md
---

# Product A

## What it is
<2–4 sentences, facts only>

## Key capabilities
- <fact> ([raw 003](../../research/<folder>/raw/003-product-a-search.md))

## Patterns
- [<concept title>](../concepts/<concept-slug>.md)

## Research gaps
- <needs login / only marketing pages / …>
```

Slug: lowercase name, suffix only when needed (`product-a`, `product-a-api`). Reuse an
existing entity: extend it and add the study to `sources`.

## wiki/concepts/<slug>.md — pattern, approach, job

```markdown
---
type: Concept
title: "<pattern name>"
description: "<one line>"
tags: [ux, search]
status: draft
sources:
  - resource: ../../research/<folder>/raw/002-product-b-search.md
---

# <pattern name>

## Essence
## Where it appears
| Product | How | Evidence |
|---|---|---|
## Variants and trade-offs
## Fit for our product
<mark "(docs)" where the UI was not seen>
```

## wiki/reports/<YYYY-MM-DD>_<slug>.md

Name equals the study folder. Skeleton: [../assets/report-template.md](../assets/report-template.md).

## kb/wiki/index.md

List new documents under Reports / Concepts / Entities — one line each:
`- [Title](reports/<file>.md) — one-line hook`.
