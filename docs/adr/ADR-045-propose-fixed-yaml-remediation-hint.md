# ADR-045: Propose a fixed remediation hint for malformed YAML frontmatter

**Status**: Proposed
**Date**: 2026-10-30
**Authors**: Pi coding agent
**Supersedes**: ADR-044 only for the addition of the fixed hint specified below
**Related**: Issue #232; ADR-003; ADR-006; ADR-015; ADR-044

## Context

Issue #232 asks for actionable help when canonical frontmatter YAML is malformed. Accepted ADR-044 implements a narrower disclosure contract: preserve the diagnostic prefix and append only a fixed YAML category and a validated frontmatter-local line. It explicitly excludes remediation advice. A single source-independent hint addresses the remaining request without exposing parser details, input contents, or adding data access. This proposal does not change ADR-044's other contracts.

## Decision

If accepted, append exactly this fixed text to every existing malformed-frontmatter-YAML diagnostic:

```text
check quoting; quote scalar values containing ': '
```

The hint is always appended on this error, regardless of YAML category, line availability, or whether the input actually contains an unquoted colon-space scalar. It is generic advice, not a detected cause. Preserve ADR-044's exact prefix, category, and eligible line, in that order; append the hint inside the same final parenthetical, separated by `; hint: `. For example:

```text
file.md: frontmatter is invalid YAML (scanner error at frontmatter line 5; hint: check quoting; quote scalar values containing ': ')
```

The fixed wording is the entire change. Do not inspect source beyond the existing YAML parse, include `str(exc)`, parser problem/context/marks beyond ADR-044's existing line rule, source excerpts, or scalar/key values to select, suppress, or alter the hint. The colon-space inside the constant is not input data. Keep ADR-044's fixed categories, bounded line handling, non-disclosure rules, and unchanged source bytes.

Valid YAML receives no hint. Other frontmatter failures, including non-YAML schema errors, and all other diagnostics remain unchanged. No configuration or optional toggle, new error category, framework/API/schema, dependency, autofix, CLI/output change, report/traversal/read-bound change, or change to legacy `validate` or `validate-core` behavior is authorized. ADR-044 remains unchanged and authoritative except that its exclusion of remediation wording is superseded by this one fixed appended constant. This is a proposal only: independent review and explicit acceptance are required before runtime changes.

## Alternatives Considered

### Keep ADR-044 unchanged

Rejected for this bounded follow-up because Issue #232 explicitly requests actionable guidance, and one constant hint can be added without disclosing parser text or source content.

### Infer whether the hint applies from the source or parser message

Rejected: examining parsed input or exception details to tailor advice adds unnecessary disclosure and risks claiming a cause that was not established. Uniform advice avoids that decision entirely.

### Add configurable hints, error codes, or automated correction

Rejected: none is required to answer the request; each broadens runtime/API behavior beyond one deterministic diagnostic suffix.

## Consequences

- A fixed hint accompanies each malformed-YAML diagnostic without claiming it identified the actual cause.
- ADR-044's category/line disclosure limits and all other behavior remain intact; exact diagnostic lines gain the prescribed suffix.
- No implementation is authorized until independent review and explicit acceptance.

## Test Contract if accepted and implemented

Use synthetic inputs only. Cover these malformed-YAML cases through the existing canonical profile/provenance report path:

1. An actual scanner error from malformed YAML containing an unquoted `: ` scalar.
2. A distinct actual parser error.
3. An otherwise generic `yaml.YAMLError` subtype with a missing problem mark.
4. An otherwise generic `yaml.YAMLError` subtype with an invalid/out-of-bounds problem mark.

For every case, assert the exact fixed `; hint: check quoting; quote scalar values containing ': '` suffix is identical, while ADR-044's existing prefix, fixed category, and eligible frontmatter-local line remain unchanged. The generic cases must omit the line according to ADR-044. Include secret canaries in source/parser context and assert no leak; assert source bytes are unchanged. Assert valid YAML (including a valid em-dash scalar) receives no hint, and non-YAML frontmatter diagnostics remain unchanged. Exercise only the existing CLI paths and verify `validate` and `validate-core` behavior remains unchanged. Documentation proposal adds no runtime test or behavior itself.
