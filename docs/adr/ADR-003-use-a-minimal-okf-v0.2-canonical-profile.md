# ADR-003: Use a minimal OKF v0.2 canonical profile with separate graph integrity

**Status**: Accepted — Implemented
**Date**: 2026-09-12
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issue #59; ADR-001 (project-local lesson validator); ADR-002 (project-local lesson enablement)

## Context

Issue #59 requires generated canonical wiki guidance and deterministic validation to agree on an explicitly documented OKF v0.2-compatible profile. It excludes migration, repair, consumer rewrites, servers, and synchronization.

The public official OKF v0.2 specification was examined through an isolated browser window at `GoogleCloudPlatform/open-knowledge-format/SPEC.md`. External specification claims remain reported until exercised by local deterministic fixtures.

Reported OKF v0.2 conformance requires every non-reserved Markdown concept file to have parseable YAML frontmatter with a non-empty `type`. `type` is the only always-required key. `title`, `description`, `resource`, and `tags` are recommended or optional. Producers may add arbitrary fields; consumers must tolerate unknown types and additional keys. Optional provenance, trust, lifecycle, and computation families have internal rules when present. Lifecycle status values are `draft`, `stable`, and `deprecated`, with absent status interpreted as `stable`. `index.md` and `log.md` are reserved files and are not ordinary concepts.

Current generated guidance in `kb_bootstrap/templates/skills/kb-wiki-builder/SKILL.md` omits `type`, emits `status: active`, and presents repository-specific fields (`id`, `category`, dates, `environment`, and `error_signatures`) as an exact OKF template. The current graph validator checks links only. It rejects dead links, while reported OKF v0.2 conformance requires consumers to tolerate broken cross-links.

Project-local error lessons are a separate `PROJECT-XXXX` contract governed by ADR-001/ADR-002. Their schema is not the canonical wiki profile and remains unchanged.

## Decision

Define the **kb-bootstrap canonical OKF v0.2 profile** for ordinary canonical concept files under the configured canonical knowledge root, excluding any `raw/` directory and excluding reserved `index.md` and `log.md` files.

### Core conformance

An ordinary canonical concept passes the core profile when:

- it is UTF-8 Markdown;
- it begins with an exact YAML frontmatter block delimited by `---` lines;
- the frontmatter parses to a mapping;
- `type` is a non-empty string.

Unknown `type` values and unknown additional frontmatter keys are accepted. Scalar values are loaded as authored strings for profile type checks, avoiding YAML 1.1 boolean/date/number coercion. Validation is read-only and leaves source bytes unchanged; it does not claim to round-trip or transform metadata. Static symlinked roots, directories, and files fail closed. The validator rechecks paths immediately before reading, but like ordinary path-based filesystem tools it does not claim a race-free snapshot under concurrent replacement; consumers must validate a stable checkout.

### Generated guidance

The generated `kb-wiki-builder` guidance uses:

```yaml
type: <descriptive concept type>
title: <human-readable title>
description: <one-sentence summary>
tags: [tag1, tag2]
status: stable
```

Only `type` is labelled required by OKF. The other generated fields are recommended profile defaults. `id`, `category`, `created`, `updated`, `environment`, and `error_signatures` are not generated as canonical OKF requirements. Producers may retain them or any other fields as extensions.

### Optional-family validation

For this increment, deterministic validation covers the optional fields emitted by the generated guidance:

- `title` and `description`, when present, are strings;
- `tags`, when present, is a list of strings;
- `status`, when present, is one of `draft`, `stable`, or `deprecated`.

Other OKF v0.2 families (`sources`, `generated`, `verified`, `stale_after`, and Attested Computation fields) remain accepted as unknown/additional metadata in this minimal profile. Issue #62 owns the later bounded provenance/freshness profile. They are not partially validated here because incomplete validation would imply guarantees the increment does not provide.

### Reserved files

- `index.md` and `log.md` are reserved case-insensitively and excluded from ordinary concept-frontmatter validation at every directory level.
- This increment does not add structural validation for their optional/conventional body formats.
- A root `index.md` version declaration remains allowed and is not rewritten.

### Separate graph-integrity extension

Existing dead-link and orphan analysis remains the **kb-bootstrap graph-integrity extension**, separate from OKF conformance:

- dead links continue to fail `kb-bootstrap validate`;
- orphans continue to be warnings;
- case-insensitive `raw/` and `lessons/` directories remain excluded so graph analysis uses the same canonical content boundary.

Documentation must state that dead-link rejection is intentionally stricter than OKF v0.2 conformance. The validator report presents canonical-profile and graph-integrity results as separate sections so a user cannot mistake one for the other.

### CLI integration

The existing `kb-bootstrap validate --dir <canonical-root> --project-root <root>` command runs, with `--dir` defaulting to the generated canonical root `kb`:

1. canonical OKF v0.2 profile validation;
2. existing graph-integrity validation;
3. QMD collection declaration validation.

The overall command fails if any required local check fails. It does not migrate or repair input.

## Alternatives Considered

### Alternative 1 — Keep the current exact template and call it OKF

Rejected. It lacks required `type`, uses non-v0.2 lifecycle value `active`, and presents repository-specific extensions as universal requirements.

### Alternative 2 — Validate every optional OKF v0.2 family now

Rejected for this increment. It expands #59 into provenance, freshness, trust, computation, actor, timestamp, and attestation validation. Issue #62 explicitly owns bounded provenance/freshness semantics. A minimal coherent profile is simpler and avoids partial guarantees.

### Alternative 3 — Make dead links valid because OKF tolerates them

Rejected. Existing users rely on fail-closed graph integrity, and Issue #59 asks for explicit deviations/extensions rather than removal of local safeguards. The behavior remains but is named separately.

### Alternative 4 — Require a fixed type taxonomy

Rejected. OKF v0.2 intentionally has no central type registry and requires consumers to tolerate unknown types.

### Alternative 5 — Rewrite existing canonical files to the new profile

Rejected and explicitly out of scope. Validation reports mismatches only. Migration or repair requires a separate Issue and approval.

## Consequences

### What gets easier

- Generated canonical articles conform to the only universal required key.
- Producers and validators share one explicit field/status contract.
- Unknown human-authored extensions remain usable.
- Users can distinguish OKF conformance failures from stricter repository graph failures.
- Issue #62 can add provenance/freshness validation after the base profile is stable.

### What gets harder

- Existing generated canonical files using `status: active` or missing `type` will fail the new profile check until their owners update them through a separately authorized change.
- The validate command gains another report section and test surface.
- Optional OKF families are accepted but not semantically verified by this increment.
- Documentation must consistently distinguish lessons, canonical concepts, OKF conformance, and local graph integrity.

### What does not change

- Project-local/shared lesson schemas and IDs remain unchanged.
- Canonical file bodies remain free-form Markdown.
- Existing link graph and QMD declaration checks remain read-only.
- No automatic migration, metadata repair, source rewrite, network access, or consumer mutation is added.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Generated guidance includes required `type` and `status: stable` | focused skill/profile test | passing |
| Missing/empty `type` and malformed frontmatter fail deterministically | `tests/test_canonical_profile.py` invalid fixtures | passing |
| Unknown types and additional fields are accepted without mutation | `test_valid_minimal_and_unknown_metadata_pass_without_mutation` | passing |
| Generated optional fields use the documented types/status values | `test_generated_optional_fields_are_validated` | passing |
| Reserved files and raw/lesson directories are excluded case-insensitively | canonical profile and graph traversal tests | passing |
| Repeated validation produces byte-identical reports and does not rewrite inputs | canonical profile repeat/byte tests | passing |
| Graph dead links remain a separately labelled local failure | combined CLI/report tests | passing |
| Existing QMD and graph behavior remain covered | full repository suite | passing |

## Rollback

Revert the implementation PR to restore the previous guidance and validation behavior. No consumer content is automatically changed by this increment, so rollback does not require data restoration. Canonical files manually updated by consumers remain consumer-owned and are not reverted automatically.

## References

- GitHub issue #59
- Reported official specification: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
- Official repository: https://github.com/GoogleCloudPlatform/open-knowledge-format
- `kb_bootstrap/templates/skills/kb-wiki-builder/SKILL.md`
- `kb_bootstrap/graph_linter.py`
- `kb_bootstrap/cli.py`
- `tests/test_graph_linter.py`
