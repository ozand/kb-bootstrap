# ADR-007: Report the executing validator version from the package

**Status**: Proposed
**Date**: 2026-09-15
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issue #80; ADR-003 (minimal OKF v0.2 canonical profile); ADR-006 (canonical provenance/freshness validation)

## Context

Issue #80 requires two diagnostic signals: a top-level `kb-bootstrap --version` command and a stable validator-version identifier in the composite `validate` output. The confirmed failure mode is an operator invoking an older installed command while comparing its result with newer source behavior. The version must identify the validator implementation that actually executed without importing consumer projects or depending on consumer runtime state.

The current package version is declared statically in `pyproject.toml`. The `kb_bootstrap` directory has no `__init__.py`, so the runtime package exposes no version constant. The CLI has no `--version` option. The `validate` command prints four human-readable report sections to standard output and returns `0` only when all four checks pass.

A direct `importlib.metadata.version("kb-bootstrap")` lookup is attractive because it reads installed distribution metadata and is available in Python 3.8. It is not sufficient for this diagnostic contract. An uninstalled source checkout may have no matching distribution metadata, while an environment containing stale global or repository-local metadata may return a version that does not describe the Python files actually imported. In the audited development environment, stale repository metadata and an older installed distribution already disagreed with the current source version.

This decision must remain smaller than a version-management system. It must not add dynamic generation, source-control discovery, compatibility negotiation, consumer upgrades, or a new machine-readable validation format.

## Decision

Add a small package runtime version constant in `kb_bootstrap/__init__.py`:

```python
__version__ = "<current project version>"
```

The constant identifies the imported `kb_bootstrap` implementation. `pyproject.toml` remains the packaging and release metadata authority. A test must require the two static values to agree. Release preparation updates both values in one reviewed change. The implementation must not read generated `egg-info`, installed distribution metadata, Git tags, release APIs, the network, the current working directory, or consumer files to determine the runtime version.

This deliberate two-location static value is preferred to generated version modules or build-time tooling because the project has a small release process and must also report the executing source version from an uninstalled checkout. No automatic synchronization mechanism is added.

### Top-level CLI contract

Add one global option:

```text
kb-bootstrap --version
```

Its exact output contract is:

```text
kb-bootstrap <version>
```

- output is exactly one line terminated by a newline on standard output;
- standard error is empty;
- exit status is `0`;
- no subcommand, target repository, QMD installation, Git checkout, network, consumer import, or consumer configuration is required;
- normal `argparse` usage errors retain their existing exit status and stream behavior.

No aliases, JSON form, version constraint, upgrade check, or per-profile version option are added.

### Validation presentation contract

The composite `validate` command prints exactly one stable identity line before its existing report sections:

```text
Validator: kb-bootstrap <version>

=== Canonical OKF v0.2 Profile Validation ===
...
```

The line identifies only the executing `kb-bootstrap` implementation. It does not identify the version of the knowledge base, OKF specification, canonical profile, graph schema, QMD index, consumer validator, or consumer policy.

The identity line is printed for both passing and failing validation runs. Existing profile, provenance/freshness, graph-integrity, and QMD report text remains present and in its current order. Existing validation rules, evidence, result labels, standard-error behavior, and exit semantics remain unchanged: version presentation cannot turn a failed check into success or make an unavailable check appear to have run.

The current `validate` output is human-readable and has no JSON or other machine-readable mode. This ADR does not create one. Adding a new leading line is an intentional documented extension of that human-readable output. Callers that scrape presentation text must match labelled sections/results rather than assume the first line is a specific section heading.

### Execution environments

The same package constant is used in every supported mode:

- a wheel or sdist installation reports the constant shipped in that artifact;
- an editable installation reports the constant in the imported checkout;
- an uninstalled source checkout invoked with that checkout on `sys.path` reports its source constant;
- unrelated stale installed metadata cannot override the version of the imported source package.

There is no `unknown` or `uninstalled` fallback in this contract. A missing runtime constant is a broken package/build and must not be silently presented as an identified validator. The release/build tests prevent that state in supported artifacts.

### Safety boundaries and non-goals

Version reporting must not:

- import, execute, scan, upgrade, migrate, or rewrite a consumer project;
- inspect consumer `pyproject.toml`, schemas, validators, QMD state, or local runtime files;
- fetch Git tags, GitHub releases, package indexes, or any network resource;
- infer compatibility, freshness, correctness, policy conformance, or upgrade necessity from a version string;
- alter validation rules, output sections, result labels, error visibility, or exit codes;
- add profile/schema negotiation, minimum-version enforcement, update notifications, telemetry, or automatic synchronization;
- modify generated `egg-info`, caches, bytecode, `.pi/`, Herdr transcripts, or consumer state as part of version lookup.

Package upgrade/migration and a future machine-readable validation-output schema remain separate owner-governed work.

## Alternatives Considered

### Alternative 1 — Read `importlib.metadata.version("kb-bootstrap")` at runtime

Rejected as the runtime authority. It accurately describes a selected installed distribution when metadata is unambiguous, but it can fail in an uninstalled checkout or report stale/unrelated metadata instead of the implementation imported from source. That undermines the stale-binary diagnostic this issue exists to provide.

### Alternative 2 — Use installed metadata with `unknown` or `uninstalled` fallback

Rejected. The fallback preserves command availability but weakens the core claim: the output would not reliably identify the validator implementation. It also allows stale installed metadata to produce a confident but wrong version rather than taking the fallback.

### Alternative 3 — Make `pyproject.toml` the runtime lookup source

Rejected. Installed wheels do not need to ship the project file, and resolving it from the current working directory could read a consumer project's metadata. It would couple version reporting to filesystem layout and consumer context.

### Alternative 4 — Generate a version module or adopt `setuptools_scm`

Rejected as overengineering for the current project. It adds build configuration or a dependency to solve a two-value consistency problem already bounded by tests and a small release process.

### Alternative 5 — Provide only `kb-bootstrap --version`

Rejected because it requires the operator to remember a separate diagnostic command and does not place the executing validator identity in captured validation output. Issue #80 explicitly requires validation presentation.

### Alternative 6 — Add the version to standard error

Rejected. Version identity is normal report data, not an error. Writing it to standard error can break callers that treat any standard-error output as an operational failure.

### Alternative 7 — Append a new validation summary/footer

Rejected for this increment. A summary introduces a second overall result vocabulary and risks duplicating or contradicting four independently labelled validation sections. One identity line is smaller and does not reinterpret outcomes.

### Alternative 8 — Add version fields to every command or persisted JSON artifact

Rejected as unnecessary scope. Issue #80 targets the top-level diagnostic and composite validation presentation. Persisted schema changes and command-wide reporting require separate evidence and compatibility decisions.

## Consequences

### What gets easier

- Operators can identify the executing CLI directly with `kb-bootstrap --version`.
- Captured validation output carries the validator implementation version even when validation fails.
- Source, editable, wheel, and sdist execution use one runtime identity mechanism.
- Stale or unrelated installed distribution metadata cannot override the imported source identity.
- Version lookup remains offline and independent of consumers, Git, QMD, and runtime state.

### What gets harder

- Release preparation must update both `pyproject.toml` and `kb_bootstrap.__version__`.
- The human-readable `validate` output gains a leading line, so consumers that incorrectly assume a fixed first line must adapt.
- A missing or mismatched package constant is treated as a packaging defect rather than hidden behind `unknown`.
- Physical Python 3.8 and every installation/filesystem combination still require availability-specific verification; tests cannot claim unobserved environments.

### What does not change

- Canonical profile, provenance/freshness, graph integrity, QMD declaration, lesson, search, export, repository, and completion semantics remain unchanged.
- Validation exit codes and failure visibility remain unchanged.
- No consumer migration, package upgrade, release publication, network lookup, compatibility negotiation, automatic repair, or runtime-state mutation is added.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Top-level `--version` emits exactly one stdout line, no stderr, and exits 0 | `test_top_level_version_contract` | not yet written |
| Version reporting works from an unrelated directory without a consumer import or consumer files | `test_version_is_independent_of_consumer_directory` | not yet written |
| Source-checkout execution reports the imported package constant despite stale installed metadata | `test_source_checkout_version_ignores_distribution_metadata` | not yet written |
| Package runtime version equals static project metadata | `test_runtime_version_matches_pyproject` | not yet written |
| Built wheel and sdist metadata/package constant agree | clean build and isolated artifact smoke tests | not yet run |
| `validate` prints exactly one stable validator identity line before existing sections | `test_validate_reports_executing_validator_version` | not yet written |
| Validator identity is present on both valid and invalid runs | `test_validate_version_present_on_success_and_failure` | not yet written |
| Existing validation reports, errors, and exit codes remain unchanged apart from the identity line | focused CLI regressions and full suite | not yet run |
| Version lookup performs no metadata, Git, network, QMD, or consumer access | `test_version_path_uses_package_constant_only` | not yet written |
| Supported syntax remains compatible with Python 3.8 | compile/test in available runtimes; physical 3.8 when available | not yet run |

## Rollback

Revert the implementation commit and remove the CLI/presentation additions while retaining this decision record. No consumer repository or canonical content is migrated, so no data rollback is required. A published release containing the contract would require a separately authorized corrective release rather than rewriting the existing tag.

## References

- GitHub issue #80
- `pyproject.toml`
- `kb_bootstrap/cli.py`
- ADR-003
- ADR-006
