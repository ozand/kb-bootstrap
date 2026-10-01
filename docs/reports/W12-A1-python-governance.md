# W12-A1 Python governance compatibility report

## Scope and result

Source revision was `7d471fc9ea6d30a5b154d614c331ac88b1b64968` (PR base
`9717bc29c7ab455cc8a7648c8f740e7f9959967a`). Issue #133, its zero comments,
the W12-A1 brief, ADR-004, `pyproject.toml`, governance documentation and the
existing governance tests were reviewed. The declared floor remains Python
3.8. The correction only replaces three `Path.stat(follow_symlinks=False)`
calls with the Python-3.8-compatible `os.stat(path, follow_symlinks=False)`;
the same no-follow observation is retained.

## Evidence

| Check | Result |
|---|---|
| Installed runtime | CPython 3.12.13 (GCC 13.3.0), exercised |
| Installed dependencies | networkx 3.7; PyYAML 6.0.3 |
| Python 3.8 / 3.9 | not installed; not tested |
| Python 3.10 / 3.11 / 3.13 shims | no selected interpreter; not tested |
| Old API reproduction | simulated compatibility check against the seed source: a path-like double rejecting `Path.stat(follow_symlinks=...)` raised the expected `TypeError`; exit 1 |
| Corrected compatibility tests | 3 run, 0 failures, 0 skips; exit 0 |
| Existing plus compatibility governance tests | 17 run, 0 failures, 0 skips; exit 0 |
| Full unittest discovery | 249 run, 0 failures, 0 skips; exit 0 |
| Diff whitespace check | exit 0 |

The reproduction is a simulation on CPython 3.12.13, not evidence from an
actual old interpreter. Official Python documentation could not be retrieved
because the environment's documentation request was rejected by its proxy;
this is an evidence limitation. The public GitHub API did provide live issue
#133 and showed no comments. No package installation or distribution-wide
compatibility claim was made.

## Commands

```text
python --version
python -c 'import networkx, yaml; print(networkx.__version__, yaml.__version__)'
python <inline seed-source simulated old-Path.stat reproduction>
python -m unittest -v tests.test_agents_governance_compatibility
python -m unittest -v tests.test_agents_governance tests.test_agents_governance_compatibility
python -m unittest discover -s tests -v
git diff --check
```

The compatibility cases cover successful identity/content observation without
the newer `Path.stat` keyword, preservation of unmanaged bytes, and continued
rejection of a symlink target. Existing tests continue to cover containment,
identity/race checks, atomic replacement, cleanup, mode and content
preservation. Naming, packaging, CI, dependencies and other W12 lanes remain
out of scope.
