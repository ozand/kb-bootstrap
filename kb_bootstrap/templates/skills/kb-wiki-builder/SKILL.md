---
name: kb-wiki-builder
description: Extract verifiable facts from raw documentation (kb/*/raw) and generate structured canonical OKF Markdown files in the wiki layer. Use when transitioning scraped data or release notes into permanent structured knowledge.
---

# kb-wiki-builder

Automates the transition of information from raw, unprocessed text to structured canonical knowledge using the Open Knowledge Format (OKF).

## Repository governance gate

Before writing canonical knowledge:

1. decide whether the article is consumer-owned knowledge or a reusable upstream framework change;
2. name the repository target explicitly and run `kb-bootstrap doctor --repo <owner/repository>`;
3. fail closed unless the doctor returns `RESULT: OK`;
4. use a separate verified checkout/worktree for upstream changes, never the consumer branch.

Before claiming a committed article or framework update complete, run `kb-bootstrap check-completion --repo <owner/repository> --commit <commit> [--pr <number>]`. Keep evidence sanitized and omit credentials, private payloads, local runtime state, and unsanitized logs.

## When to use

- You have just fetched new raw documentation or release notes into the `raw/` directory.
- You need to update the canonical wiki files based on the new raw data.
- The user asks you to extract facts and create a structured overview for a product.

## Rules for Extraction

1. **No Hallucination:** Only extract claims that are explicitly stated in the `raw/` files. Do not invent features or guess compatibility.
2. **OKF Format:** All generated wiki concept files MUST follow the kb-bootstrap canonical OKF v0.2 profile. `type` is the only always-required OKF key; unknown types and additional human-authored keys are allowed.
3. **Location:** Save the generated files in the canonical knowledge root (e.g., `kb/overview.md` or `kb/apps/<app>/overview.md`), NEVER in `raw/`.

## OKF Markdown Template

Use this profile-aligned structure for generated ordinary concept files:

```markdown
---
type: "<Descriptive concept type, e.g. Concept, Architecture, Setup>"
title: "<Clear, descriptive title>"
description: "<One-sentence summary>"
tags: [tag1, tag2]
status: stable
# Optional provenance/freshness example — include only fields backed by evidence:
# generated:
#   by: "<public producer/version or human:id>"
#   at: YYYY-MM-DDTHH:MM:SSZ
# sources:
#   - resource: "<public URL or sanitized relative reference>"
# stale_after: YYYY-MM-DDTHH:MM:SSZ
---

# <Title>

## Описание (Overview)
Brief description of the concept or component.

## Ключевые возможности / Факты (Key Facts)
- Fact 1
- Fact 2

## References (Источники)
- [Raw Source Name](./raw/<source_file>.md)
```

`type` must be a non-empty string. `title`, `description`, `tags`, and `status` are recommended generated defaults. When present, `tags` is a list of strings and `status` is `draft`, `stable`, or `deprecated`. `generated`, `sources`, and `stale_after` are optional: include them only from verified sanitized evidence, use timestamps with an explicit UTC offset, never invent a producer/source/cutoff, and never fetch a source during validation. `verified` may be added only for an actual confirmation event and requires `by` plus an offset-aware `at`. Preserve unknown or human-authored frontmatter keys; do not normalize or delete them. `index.md` and `log.md` are reserved files rather than ordinary concepts. Project-local error lessons under `kb/lessons/` use their separate lesson schema and are not canonical OKF concepts.

## Collection boundaries

Generated projects separate retrieval into:

- `<project>-raw` for source captures under `kb/raw/`;
- `<project>-wiki` for canonical OKF Markdown under `kb/` excluding `raw/`.

Use the raw collection to gather evidence and the wiki collection to verify the resulting canonical article.

## Workflow

1. Read the target source from `<project>-raw` via QMD or context-mode tools.
2. Draft the OKF document based on the template.
3. Write the file to its proper canonical location.
4. Run the mandatory completion gate:
   - `kb-bootstrap validate --dir kb --project-root .`;
   - the project test command;
   - `qmd update`, followed by smoke searches in `<project>-wiki` and `<project>-raw`.

Do not report completion if validation/tests fail or if the QMD update/search steps were not actually verified. Treat universal kb-bootstrap conformance, repository-owned policy validation, and retrieval/index freshness as separate outcomes; one pass does not prove another. The upstream [validation composition guidance](https://github.com/ozand/kb-bootstrap/blob/main/docs/VALIDATION_COMPOSITION.md) defines the reporting boundary.
