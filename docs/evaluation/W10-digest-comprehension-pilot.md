# W10 bounded comprehension pilot — digest identity and limits

**Issue:** #131 · **Status:** one qualitative role observation; not a benchmark, score, novice study, or evidence of population comprehension.
**Date:** 2026-10-16
**Base:** `d72e63e22bec336f90635783cedacc7bd57a68ee`
**Purpose:** observe whether one already-authorized Pi role can explain exact-byte digest equality and distinguish it from truth, authority, freshness, and race-free snapshot claims.

## Source shown

Public committed documentation only; no synthetic substitute was created.

`README.md`, raw-manifest section (lines 324–331 at base above):

> The report classifies new, changed, unchanged, and removed paths. Output paths and hashes may disclose sensitive metadata: store the manifest and captured stdout privately. Existing outputs are never overwritten; neither QMD nor GLiNER is required. Run only on a stable, locally controlled checkout: static symlinks and observed source changes block, but on Windows a hostile concurrent directory replacement may be enumerated before a post-enumeration check detects it. This is not a race-free filesystem snapshot or an adversarial-writer-safe scanner. See ADR-010.

`docs/adr/ADR-010-record-raw-revisions-in-an-exclusive-manifest.md`, lines 40–46, provides the definition:

> SHA-256 hashes exact source bytes.

> Compare path/digest only: current-only `new`, prior-only `removed`, equal-path different-digest `changed`, equal-digest `unchanged`.

> This manifest is a derived local artifact, not a retention receipt, privacy filter, archive, or authorization for publication.

SHA-256 of the committed source files at that revision: README `376af89889cd3e4b9b1a01fbcd8e12f5079ce6c3fd49aadd394c01c88f062919`; ADR-010 `a49427e603313bd076888f0ce5e7ec1c5460a4e33a7af97fde80e9bfaea690c5`.

## Prompt

> In your own words, what does equal path+SHA-256 establish in this manifest? Name at least three conclusions it does not justify, and explain why the stable-checkout condition matters. If the excerpt leaves a point unspecified, say so.

The reader saw only the source excerpt and question, not this report's observation checklist or expected answer.

## Verbatim response

> Если в двух сравниваемых манифестах путь одинаков и SHA-256 совпадает, это означает, что для этого пути совпал вычисленный отпечаток точных байтов исходного файла. По правилу из отрывка такой путь классифицируется как unchanged. Само по себе это НЕ доказывает, что содержимое безопасно или истинно, что его разрешено хранить или публиковать, что манифест является подтверждением хранения, либо что файл был проверен в race-free снимке. Манифест — производный локальный артефакт, а не фильтр приватности, архив или разрешение на публикацию. Работа со стабильным checkout важна потому, что сканирование не защищено от враждебной параллельной записи: статические symlink и замеченные изменения блокируются, но на Windows подменённую одновременно директорию могут перечислить до того, как последующая проверка обнаружит изменение. Поэтому источник должен оставаться под локальным контролем и стабильным во время запуска. Отрывок не уточняет, кто создал ожидаемый манифест и насколько ему можно доверять; этого вывода делать нельзя.

## Observation and limits

The response correctly connects equal path+digest with exact-byte identity and the `unchanged` classification; it rejects truth, safety, authorization, retention-receipt, and race-free-snapshot inferences; it explains the stable-checkout caveat and reports manifest trust/creator as unspecified. The response does not explicitly address external freshness. **No material comprehension gap was observed for this bounded question.** The response is in Russian while the source is English; it remains attributed to one Pi role session (`01a1427c-7993-7426`), not a human/novice measurement. Prior project/task context may have primed familiarity with hashing; this is not an independent first-exposure or generalization test. No score, efficacy claim, or README failure is inferred. Issue #206's reader-gap-dependent criterion is therefore not evidenced as met by this observation.

No model was acquired or new inference service provisioned for this observation. It records one response from the already-authorized Pi role session only; no QMD operation, consumer data, runtime evaluation harness, or new scoring/schema was used.
