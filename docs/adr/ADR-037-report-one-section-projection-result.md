# ADR-037: Report one section-projection operation result

**Status**: Proposed
**Date**: 2026-10-23
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issues #121, #122, #127; ADR-028, ADR-034

## Context

Accepted ADR-028 separates selection, scoped technical observation, required-operation fulfillment, validation, and authority. Accepted ADR-034 defines the bounded `project_section` operation and its finite result statuses. Neither defines a report contract that preserves these facts together for one operation already executed. Treating every non-`COMPLETE` result as broken would misclassify expected `TRUNCATED`, `BLOCKED`, `UNSUPPORTED`, `REVISION_MISMATCH`, `NOT_FOUND`, and `AMBIGUOUS` results. Treating a partial projection as fulfillment of a request for a complete section would also overstate the result.

This proposed decision defines only a Python API for reporting one caller-supplied selection and the original result of one already-executed `project_section`. It performs no operation, check, probe, retry, or verification. It adds no CLI, registry, persistence, serialization format, generic framework, clock/freshness rule, or authority. It does not modify ADR-028 or ADR-034.

## Decision

A future implementation exposes exactly:

```python
report_section_projection(
    *,
    selection_state: str,
    required: bool,
    result: Mapping[str, object] | None,
    technical_failure: str | None = None,
) -> dict[str, object]
```

`selection_state` is exactly `NOT_CONFIGURED`, `DISABLED`, or `CONFIGURED`. `required` must be a `bool` (not an integer). `result` is the unmodified result mapping returned by one invocation of ADR-034 `project_section`, or `None` when that operation was not invoked. `technical_failure` is either `None` or a non-empty bounded category string asserted by the caller to describe an attempted operation's technical execution failure; it is not evidence verified by this reporter. No executable, callback, configuration reference, or authority token is accepted.

The returned mapping has exactly these fields and types:

- `selection_state: str`: the supplied selection state.
- `required: bool`: the supplied requirement.
- `operation: str`: always `project_section`.
- `operation_status: str`: one of `NOT_RUN`, `COMPLETE`, `TRUNCATED`, `BLOCKED`, `UNSUPPORTED`, `REVISION_MISMATCH`, `NOT_FOUND`, `AMBIGUOUS`, `TECHNICAL_FAILURE`.
- `observation: str`: `UNKNOWN`, `AVAILABLE`, or `BROKEN`.
- `technical_failure: str | None`: supplied category only for `TECHNICAL_FAILURE`; otherwise `None`.
- `requirement_fulfilled: bool`: derived, never caller-supplied.

`result is None` means `NOT_RUN`; it cannot coexist with `technical_failure`. A non-None `result` must be an ADR-034 result mapping with one of its seven statuses. Those exact seven statuses are preserved as `operation_status`. `COMPLETE` yields `AVAILABLE`; `TRUNCATED` and all five ordinary non-complete outcomes yield `UNKNOWN`, never `BROKEN`. A technical exception can be represented only when `result is None` and a non-empty `technical_failure` category is asserted; this yields `TECHNICAL_FAILURE` and `BROKEN`. Because this is a report of one result, not an execution wrapper, that category remains a caller assertion and does not prove an attempt occurred.

A configured selection plus `COMPLETE` fulfills a required operation. `TRUNCATED` never fulfills it: the caller selected a complete projection and received only a bounded prefix. Every other combination is unfulfilled when required. Optional operations have `requirement_fulfilled: true` only when selection is not required; this field reports fulfillment, not success, availability, or authorization. `NOT_CONFIGURED` and `DISABLED` are selection facts and do not imply an attempted operation; any supplied result or technical failure with either is contradictory and rejected. A `CONFIGURED` selection with neither result nor technical failure is `NOT_RUN` / `UNKNOWN`.

The reporter rejects invalid types, unknown values, contradictory combinations, malformed ADR-034 mappings, or technical-failure categories outside 1–64 printable ASCII characters with `ValueError`; it does not coerce input. This fixed exception is the only failure contract. No wire format or stable serialization is promised. The caller's mappings are treated as assertions; the reporter authenticates no facts and grants no authority. No timestamps are recorded or freshness inferred.

### Example

```python
report_section_projection(
    selection_state="CONFIGURED", required=True,
    result={"status": "COMPLETE", "path": "guide.md"},
)
# {'selection_state': 'CONFIGURED', 'required': True,
#  'operation': 'project_section', 'operation_status': 'COMPLETE',
#  'observation': 'AVAILABLE', 'technical_failure': None,
#  'requirement_fulfilled': True}
```

A `TRUNCATED` result instead reports `operation_status="TRUNCATED"`, `observation="UNKNOWN"`, `requirement_fulfilled=False` when required. A `NOT_FOUND` result is likewise preserved, not labeled `BROKEN`.

## Test Contract

These are future tests, not written or run by this proposal:

| Claim | Focused test |
|---|---|
| All seven ADR-034 result statuses are preserved; only `COMPLETE` is `AVAILABLE`; ordinary outcomes including `TRUNCATED` never become `BROKEN` | `tests/test_section_projection_reporting.py::test_all_operation_statuses_map_without_collapsing_outcomes` |
| `COMPLETE` fulfills required configured selection; `TRUNCATED` does not; optional fulfillment does not claim availability | `tests/test_section_projection_reporting.py::test_requirement_fulfillment_is_separate_from_observation` |
| Unconfigured and disabled states report no operation; configured absence reports `NOT_RUN` / `UNKNOWN` | `tests/test_section_projection_reporting.py::test_selection_and_not_run_are_distinct` |
| Caller-asserted technical failure requires configured selection, no result, and a valid bounded category; it remains an assertion, not verified execution | `tests/test_section_projection_reporting.py::test_technical_failure_is_scoped_assertion` |
| Invalid types, statuses, malformed result mappings, and contradictory input raise `ValueError` | `tests/test_section_projection_reporting.py::test_invalid_and_contradictory_inputs` |

## Alternatives Considered

- Treat every non-`COMPLETE` status as `BROKEN`: rejected because ADR-034 defines expected partial, caller-input, revision, and unsupported outcomes that do not demonstrate technical failure.
- Treat `TRUNCATED` as fulfillment of a required projection: rejected because the operation explicitly reports partial content, not the complete selected section.
- Let the reporter invoke or retry the operation to establish a failure: rejected because this contract accepts only an already-produced result and adds no execution or probe.

## Consequences

The report keeps configured selection, the actual operation status, technical observation, and requirement fulfillment distinct. Partial output is not falsely reported as a complete required result, and ordinary user/input/revision outcomes do not imply a broken capability. A caller may assert a technical failure without this API proving execution; no report is an approval, security claim, or freshness guarantee.

## References

- [Issue #122](https://github.com/ozand/kb-bootstrap/issues/122) and research record posted before drafting: https://github.com/ozand/kb-bootstrap/issues/122#issuecomment-6355671290
- [ADR-028](ADR-028-separate-optional-capability-state-from-validation-and-authority.md)
- [ADR-034](ADR-034-project-one-explicit-bounded-markdown-section.md)
- `kb_bootstrap/section_projection.py` at base `bc5cffff615f72057df6c0c649c7f8a2da17b8c1`
