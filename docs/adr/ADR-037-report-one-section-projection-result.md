# ADR-037: Report one section-projection operation result

**Status**: Accepted
**Date**: 2026-10-23
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issues #121, #122, #127; ADR-028, ADR-034

## Context

Accepted ADR-028 separates selection, scoped technical observation, required-operation fulfillment, validation, and authority. Accepted ADR-034 defines `project_section` and seven finite returned statuses. A report must preserve the actual operation result without conflating an ordinary incomplete/user-input outcome with technical breakage, or a partial projection with fulfillment of a request for the complete section.

This Proposed decision defines only a Python function that reports one selection and one already-produced ADR-034 result. It performs no operation, check, probe, retry, or verification. It adds no CLI, registry, persistence, serialization format, generic framework, time/freshness rule, or authority. It does not modify ADR-028 or ADR-034.

## Decision

A future implementation exposes exactly:

```python
report_section_projection(
    *,
    selection_state: str,
    required: bool,
    result: Mapping[str, object] | None,
) -> dict[str, object]
```

`selection_state` is exactly `NOT_CONFIGURED`, `DISABLED`, or `CONFIGURED`; `required` must be a real `bool`, not an integer. `result` is either `None` or the mapping returned by one `project_section` invocation. `None` means exactly that the operation was not invoked. A mapping means the operation returned an ordinary result. The reporter never accepts an exception, execution callback, error label, configuration reference, or authority token. ADR-034 currently maps expected read/runtime input errors to `BLOCKED`; this proposal does not invent a technical-exception status or infer `BROKEN` from those outcomes.

The output has exactly seven fields and no source payload:

- `selection_state: str`: input selection state.
- `required: bool`: input requirement.
- `operation: str`: always `project_section`.
- `operation_status: str`: `NOT_RUN`, `COMPLETE`, `TRUNCATED`, `BLOCKED`, `UNSUPPORTED`, `REVISION_MISMATCH`, `NOT_FOUND`, or `AMBIGUOUS`.
- `observation: str`: `NOT_RUN`, `UNKNOWN`, or `AVAILABLE`.
- `requirement_satisfied: bool`: derived as below; never caller supplied.

Mapping status is preserved exactly. `COMPLETE` maps to `AVAILABLE`; each of `TRUNCATED`, `BLOCKED`, `UNSUPPORTED`, `REVISION_MISMATCH`, `NOT_FOUND`, and `AMBIGUOUS` maps to `UNKNOWN`. `result=None` maps to `NOT_RUN` for both operation status and observation. Thus an uninvoked operation is not mislabeled as an attempted operation with an unknown result. This `UNKNOWN` value for an invoked, ordinary non-complete result is a scoped refinement not defined in accepted ADR-028; its compatibility with the ADR-028 observation vocabulary requires explicit owner acceptance. It does not amend ADR-028 by implication.

Only a `CONFIGURED` selection with `COMPLETE` satisfies a required operation. `TRUNCATED` is partial section content and never satisfies a request for the complete projection. Any required operation with `NOT_RUN` or any other returned status is unsatisfied. When `required=False`, `requirement_satisfied` is always true vacuously; that value claims neither operation success nor availability. For `NOT_CONFIGURED` or `DISABLED`, `result` must be `None`; supplying an operation result contradicts the selection state. `CONFIGURED` with `result=None` is valid and reports `NOT_RUN`.

The reporter validates only the result envelope needed to classify the returned ADR-034 status. It rejects a non-mapping, unknown status, missing required keys, extra keys, wrong types, and malformed bounded values with `ValueError`; it does not coerce. Exact permitted result keys and checks are:

| Status | Exact keys | Value constraints |
|---|---|---|
| `BLOCKED` | `status`, `reason` | reason exactly `blocked` |
| `UNSUPPORTED` | `status`, `reason` | reason exactly `unsupported` |
| `NOT_FOUND` | `status`, `reason` | reason exactly `not_found` |
| `AMBIGUOUS` | `status`, `reason` | reason exactly `ambiguous` |
| `REVISION_MISMATCH` | `status`, `observed_sha256` | lowercase 64-hex string |
| `COMPLETE` | `status`, `path`, `observed_sha256`, `heading_path`, `occurrence`, `start_line`, `end_line`, `text`, `truncated` | path non-empty string; digest lowercase 64-hex; heading path non-empty list of non-empty strings (at most 6 components, each at most 512 UTF-8 bytes); occurrence positive integer excluding bool; line numbers positive integers excluding bool with end >= start; text string; truncated exactly `False` |
| `TRUNCATED` | same nine keys as `COMPLETE` | same constraints except truncated exactly `True` |

The reporter additionally rejects strings that cannot be UTF-8 encoded, a `text` value exceeding ADR-034's 65,536-byte section budget, or any supplied mapping whose compact UTF-8 JSON representation exceeds ADR-034's 256-KiB result bound. It inspects but never returns `path`, `text`, or any result mapping value. It does not re-run projection, re-parse Markdown, or authenticate that the mapping truly came from `project_section`. These envelope checks do not replace ADR-034's operation validation.

### Example

This shows a valid `COMPLETE` shape; the ellipsis is explanatory and is not a literal result value:

```python
result = {
    "status": "COMPLETE", "path": "guide.md",
    "observed_sha256": "a" * 64, "heading_path": ["Setup"],
    "occurrence": 1, "start_line": 1, "end_line": 4,
    "text": "# Setup\\n\\nSteps\\n", "truncated": False,
}
report_section_projection(selection_state="CONFIGURED", required=True, result=result)
# operation_status=COMPLETE, observation=AVAILABLE, requirement_satisfied=True
```

The reporter does not execute `project_section` in this example or in any other use.

## Test Contract

These are future tests, not written or run by this proposal:

| Claim | Focused test |
|---|---|
| All seven ADR-034 statuses are preserved; only `COMPLETE` is `AVAILABLE`; ordinary outcomes, including `TRUNCATED`, are never `BROKEN` | `tests/test_section_projection_reporting.py::test_all_operation_statuses_map_without_collapsing_outcomes` |
| Required configured `COMPLETE` satisfies; `TRUNCATED` does not; optional satisfaction is vacuous and makes no success claim | `tests/test_section_projection_reporting.py::test_requirement_satisfaction_is_separate_from_observation` |
| `None` is `NOT_RUN`; a returned non-complete status is `UNKNOWN`; disabled/unconfigured selection cannot carry a result | `tests/test_section_projection_reporting.py::test_not_run_and_returned_unknown_are_distinct` |
| Every status accepts exactly its ADR-034 result shape and invalid/extra/missing fields or bounds raise `ValueError` | `tests/test_section_projection_reporting.py::test_result_shapes_and_rejections` |
| The report never includes the input section text or path and adds no execution/probe | `tests/test_section_projection_reporting.py::test_report_is_metadata_only_and_does_not_execute` |

## Alternatives Considered

- Add a technical-exception/BROKEN input to this report: rejected for this bounded first version. ADR-034 returns finite statuses and currently sanitizes expected read/runtime input errors as `BLOCKED`; a caller-labeled exception field would add an unverified assertion path without being needed to report its actual results. ADR-028's general technical observation model remains unchanged.
- Treat every non-`COMPLETE` status as `BROKEN`: rejected because ADR-034 defines ordinary bounded, unsupported, revision, and selector outcomes, not a general technical-failure signal.
- Treat `TRUNCATED` as satisfying a required complete projection: rejected because the selected section was returned only as a bounded prefix.
- Let the reporter invoke or retry projection: rejected because the API is a pure report of an existing result.

## Consequences

The report separates selection, operation status, observation, and requirement satisfaction without returning source content. It cannot establish that input claims are authentic. The scoped `UNKNOWN` refinement and its relation to ADR-028 require owner acceptance; no accepted contract changes until then. The report grants no authority and makes no freshness, security, or execution guarantee.

## References

- [Issue #122](https://github.com/ozand/kb-bootstrap/issues/122); research posted before this revision: https://github.com/ozand/kb-bootstrap/issues/122#issuecomment-6355792975
- [ADR-028](ADR-028-separate-optional-capability-state-from-validation-and-authority.md)
- [ADR-034](ADR-034-project-one-explicit-bounded-markdown-section.md)
- `kb_bootstrap/section_projection.py` at base `bc5cffff615f72057df6c0c649c7f8a2da17b8c1`
