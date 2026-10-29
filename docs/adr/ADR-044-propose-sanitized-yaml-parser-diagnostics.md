# ADR-044: Propose sanitized YAML parser diagnostics for canonical frontmatter

**Status**: Proposed
**Date**: 2026-11-02
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #232; ADR-003; ADR-006; ADR-015

## Context

Issue #232 reports that canonical validation reduces malformed YAML frontmatter to `frontmatter is invalid YAML`. That stable diagnostic does not identify a likely syntax category or where to inspect. ADR-003 establishes malformed frontmatter as a validation failure; ADR-006 requires category-only, payload-free reporting; ADR-015 reuses those checks and preserves the separate `validate-core` contract. None authorizes parser text or source excerpts. A narrow category plus numeric frontmatter-local line is a disclosure refinement that needs an explicit decision before implementation.

This proposal concerns only the existing canonical profile diagnostic emitted by `_frontmatter` and surfaced by current validation reports. It adds no framework, schema, CLI option, output mode, or new data access.

## Decision

If accepted, retain the exact existing diagnostic prefix `frontmatter is invalid YAML` and append a fixed YAML error category and, when safely available, a one-based line explicitly labeled `frontmatter line`. Example shape:

```text
wiki/entities/example.md: frontmatter is invalid YAML (scanner error at frontmatter line 5)
```

The example illustrates presentation only; category and line must come from the actual parse failure. The category is selected by exception type with this closed mapping: `yaml.scanner.ScannerError` → `scanner error`; `yaml.parser.ParserError` → `parser error`; any other `yaml.YAMLError` subtype → `YAML error`. Test the specific scanner/parser types before the generic fallback. Do not derive labels from exception text or class names.

A line may be appended only from `problem_mark.line`, converted from zero-based to one-based. Accept only an integer that is not a boolean and is within `0..frontmatter_line_count` inclusive; the upper bound accommodates a parser mark at end-of-input. The displayed number is therefore `1..frontmatter_line_count+1`. It is local to the exact string parsed from lines between the opening and closing frontmatter delimiters: the first parsed YAML line is line 1, and document/body lines are not counted. Do not use `context_mark`, offsets, columns, or infer a location. If the problem mark is absent, malformed, or out of bounds, omit the line and show only the fixed category. The existing relative file path remains as-is.

Never display or serialize `str(exc)`, `problem`, `context`, either mark's buffer/name, source excerpt, scalar/key content, absolute path, or any other parser-derived text. Unknown YAML exception subclasses receive only the fixed generic category. Source bytes remain unchanged.

No changes are authorized to validation traversal or read bounds, error categories outside malformed YAML, report sections, command selection, CLI exit codes, legacy `validate` behavior, JSON/output formats, stdout/stderr routing, configuration, autofix, dependencies, or other consumers of canonical profile/provenance reports. This is ordinary human-readable report text, not a new machine-readable contract. Independent review and explicit ADR acceptance are required before code changes; this proposal itself authorizes no runtime change.

## Alternatives considered

### Print PyYAML's error message

Rejected: parser wording is version-dependent and may include user-authored scalar text, excerpts, and context. Sanitizing arbitrary message text cannot establish a closed non-disclosure boundary.

### Keep category-only diagnostics

Rejected for this bounded proposal because it does not provide the requested actionable location/category. ADR-006's safety constraint can be preserved with fixed categories and a validated numeric mark without exposing parser text.

### Add a general diagnostic framework or output schema

Rejected: one existing parse failure needs a fixed label and optional local line. A reusable framework, schema, CLI mode, and broader report changes add no demonstrated value and widen compatibility scope.

## Consequences

- Operators can distinguish scanner, parser, and other YAML failures and locate the relevant frontmatter line without seeing authored content.
- The stable prefix remains available to existing human-readable report consumers; appended text may affect consumers that compare the entire line rather than the existing prefix.
- Missing or invalid parser marks produce a useful category without a line; no location is guessed.
- This does not claim that line context alone explains the correction, or that YAML syntax is the only possible validation failure.
- No accepted ADR is rewritten, and no runtime behavior changes until this decision is accepted and independently reviewed.

## Test contract if accepted and implemented

Use synthetic fixtures only. Cover actual scanner and parser failures, the unknown-`YAMLError` fallback, correct frontmatter-local numbering, missing and invalid marks, and a mark at end-of-input. Include a secret canary in malformed scalar/context text and assert that it never appears. Include a real malformed unquoted `: ` scalar; do not treat an em dash or any other valid YAML value as invalid merely to create a fixture. Assert the unchanged diagnostic prefix, deterministic fixed labels, no line when the mark is unusable, and unchanged source bytes.

Exercise the existing canonical profile/provenance report path and the existing CLI command(s) that surface it. Verify legacy `validate` and `validate-core` exit behavior and report composition remain unchanged. No tests, code, schema, dependencies, or consumer changes are part of this documentation proposal.

## References

- Issue #232: https://github.com/ozand/kb-bootstrap/issues/232
- ADR-003: [minimal canonical profile](ADR-003-use-a-minimal-okf-v0.2-canonical-profile.md)
- ADR-006: [canonical provenance and freshness](ADR-006-validate-canonical-provenance-with-explicit-time.md)
- ADR-015: [core-only validation](ADR-015-add-core-only-validation-without-changing-legacy-validate.md)
- `kb_bootstrap/canonical_profile.py` (`_frontmatter`)
