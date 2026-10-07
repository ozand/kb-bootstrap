# ADR-020: Derive portable QMD names with digests for lossy inputs

**Status**: Accepted
**Date**: 2026-10-07
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #133; ADR-016, ADR-018

Owner acceptance: #133 comment 6038730839 (2026-10-07).

## Context

Synthetic reproduction on current `main` shows `project_slug()` preserves Unicode alphanumerics, while `qmd_validator.py` accepts ASCII-only collection names. Initializing basenames `Пример проекта` and `équipe` succeeds but produces collections rejected by the repository validator. Distinct basenames `A B` and `A@B` both normalize to `a-b`; punctuation-only `!!!` maps to `project`. These are source/validator observations from fresh synthetic targets, not QMD runtime behavior. The repeat guard independently generates expected QMD payloads; ADR-016 requires a conflicting repeat to block without repair or normalization. ADR-018 bounds adapter index/collection names to ASCII letters/digits/underscore/hyphen, 1–64 characters.

This decision intentionally does not preserve every legacy ASCII result: uppercase, punctuation-containing and otherwise lossy basenames receive digests on a fresh initialization. Only already-lowercase ASCII basenames that need no normalization retain their previous generated base exactly. Existing initialized directories are not rewritten by this decision.

### Problem statement

Initialization should emit QMD identifiers accepted by local validation and ADR-018 bounds. Lossy normalization should distinguish different source basenames in the ordinary case; preserve prior output only for already-lowercase simple ASCII names. Existing initialized collections must never be silently renamed.

## Decision

This decision chooses deterministic ASCII-compatible generated identifiers, with a digest when normalization is lossy or exceeds the portable prefix bound.

### What this IS

1. Preserve the current `project_slug()` output exactly (baseline `1fd6ece65ff7103f84581467528a0c8f6ff9c23d`) only when the original basename is already lowercase ASCII matching `[a-z0-9_-]+`, at most 59 characters, and unchanged by the baseline `.strip("-._")`. Inputs requiring lowercasing, punctuation replacement, Unicode handling, boundary-separator trimming, fallback, or truncation are lossy and take the digest path. This intentionally changes output for such inputs on a new initialization; it does not authorize rewriting an existing target.
2. For lossy input, first lowercase the basename, then derive an ASCII readable prefix by mapping runs outside `[a-z0-9_-]` to `-`, trim separators, cap the prefix at 46 characters, and append `-` plus the first 12 lowercase hex characters of SHA-256 over the original basename's UTF-8 bytes. If the prefix is empty, use `p`. Distinct lossy basenames such as `A B` and `A@B` therefore receive different digests in the ordinary case. A 48-bit prefix has a non-zero collision probability; this proposal does not add a registry, collision search, or collision-resolution fallback. The residual collision risk must remain explicit.
3. Keep generated suffixes `-wiki` and `-raw`; a base of at most 59 leaves both collection names within ADR-018's 64-character limit. This collection bound does not assert a QMD workspace-name limit.
4. Make the generator and validator use the same documented ASCII grammar and length ceiling for generated collection identifiers.

### What this IS NOT

This accepted decision authorizes only fresh generator outputs and matching generated-name validation changes as specified above. It does not rename or rewrite existing QMD files/config, migrate consumers, guarantee zero hash collisions, validate QMD's own undocumented name limits, or change ADR-016's no-op/block repeat behavior. Existing custom names remain owner-authored; old lossy generated names that differ from this rule remain subject to existing ADR-016 repeat preflight and can block without migration. No automatic migration is authorized.

### Success criteria

Cyrillic/accented, uppercase, punctuation-only, empty-normalized, overlength basenames deterministically produce validator-valid bounded names; already-simple lowercase ASCII names remain byte-compatible. `A B` and `A@B` do not collapse to the same generated name under this rule, subject to the recorded residual 48-bit digest collision risk; owner acceptance does not make that collision probability zero. Repeat preflight never rewrites existing names.

## Consequences

### What gets easier

Generated collection names pass the local ASCII validator and fit ADR-018's stated bound; lossy source basenames are distinguishable in the usual case.

### What gets harder

Lossy names are less readable and legacy generated names may need owner-led migration. A 48-bit digest makes collisions unlikely, not impossible.

### What does not change

No automatic registration, QMD execution, consumer migration, existing-name rewrite, or public persisted schema change is authorized. QMD runtime behavior for newly generated identifiers still requires separate runtime verification.

## Alternatives Considered

- Reject non-ASCII/punctuation basenames: avoids ambiguous coercion but makes initialization fail for valid repository directory names.
- Transliterate Unicode: requires a transliteration table/dependency and still needs a policy for collisions.
- Keep lossy slug without digest: reproduced `A B`/`A@B` collision remains.
- Hash every basename: maximizes distinction but needlessly changes familiar ASCII collection names.

## Test Contract

| Claim | Test | Currently |
|---|---|---|
| Unicode/space/punctuation and empty-normalized inputs yield ASCII bounded names | `tests/test_scaffold_repeat.py::test_project_slug_portable_name_matrix` | not yet written |
| Lossy names use deterministic source-derived digests; 48-bit collision risk is explicitly accepted, not eliminated | `tests/test_scaffold_repeat.py::test_lossy_name_digest_and_collision_controls` | not yet written |
| Simple ASCII names retain generated bytes | `tests/test_scaffold_repeat.py::test_simple_ascii_name_compatibility` | not yet written |
| Generator and validator agree on generated grammar/length without tightening legacy custom collection validation | `tests/test_qmd_validator.py::test_generated_collection_name_contract` | not yet written |
| Repeat preflight never normalizes existing collections | `tests/test_scaffold_repeat.py::test_existing_lossy_collection_repeat_blocks_without_writes` | not yet written |

## Rollback

Before implementation, an owner may supersede or withdraw this decision. After implementation, reversal requires a superseding ADR and compatibility plan; never restore prior behavior by rewriting consumer collections automatically. Rollback of code must preserve the ADR-016 no-overwrite boundary and never migrate consumer files.

## References

- Issue #133 research record: https://github.com/ozand/kb-bootstrap/issues/133#issuecomment-6030918453
- `kb_bootstrap/cli.py:39-44,525-576`; `kb_bootstrap/scaffold_repeat.py:26-49`
- `kb_bootstrap/qmd_validator.py:10,66`; ADR-016; ADR-018
