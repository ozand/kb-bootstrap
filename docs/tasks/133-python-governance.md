# W12-A1: minimum-Python compatibility of managed governance files

Status: execution brief, not an implementation or test claim. Parent: #133; programme: #121. The owner requested parallel executors on 2026-09-28. This is one representative runtime slice, not all Python support, names, packaging or CI work.

Repository: `ozand/kb-bootstrap`. Branch: `codex/w12-python-compatibility`. Main baseline: `9717bc29c7ab455cc8a7648c8f740e7f9959967a`. Verify this PR's assigned seed/head before work. Do not modify PR #134/#135 or another executor's branch. In particular `graph_linter.py`, `canonical_graph_export.py` and their tests are read-only for this task.

## Read and reproduce

Read issue #133 and comments, `pyproject.toml`, `docs/CONTRIBUTING_UPSTREAM.md`, `docs/AGENTS_GOVERNANCE_BLOCK.md`, Accepted ADR-004, `kb_bootstrap/agents_governance.py` and `tests/test_agents_governance.py`. Keep the public support floor, atomic replacement, ownership, no-overwrite/race safeguards, permissions and symlink semantics unchanged.

The reported lead is `Path.stat(follow_symlinks=False)` in `_identity` and `_observe`, while metadata declares Python >=3.8. Verify relevant standard-library API versions against official documentation available through existing tools; do not infer actual interpreter execution from documentation alone. Separate source API compatibility from installation of networkx/PyYAML and the entire distribution.

Use already installed interpreters and dependencies only. If Python 3.8/3.9 is unavailable, explicitly record not tested on those interpreters. A narrow shim that rejects the newer stat keyword can characterize the API regression, but must be labelled simulated compatibility rather than a real minimum-runtime pass. Missing optional tools or unavailable official pages should yield recorded evidence gaps, not software installation or guessed claims.

## Exclusive write scope and deliverable

Only these paths may be changed:
1. `kb_bootstrap/agents_governance.py` - the minimum correction for confirmed old-runtime stat-API incompatibility, preserving no-follow observations and all safety logic;
2. `tests/test_agents_governance_compatibility.py` - focused regression/positive/negative cases using synthetic files;
3. `docs/reports/W12-A1-python-governance.md` - compact evidence matrix, exact runtimes exercised, dependency limits and remaining W12 work.

Keep this task brief unchanged. Prefer a small compatibility-preserving change using existing standard-library APIs, not a helper framework or broad refactor. Existing `tests/test_agents_governance.py` must stay unchanged and keep passing. Reproduce before fixing; verify the new tests fail for the old implementation for the claimed reason and pass afterwards. Include real symlink/identity and managed-block preservation controls where supported. Do not weaken tests to achieve a pass. If a fix changes an accepted public/safety contract, deliver the characterization and decision needed instead of implementing it.

No support-floor or dependency changes, CLI/template changes, package cleanup, name normalization, license selection, workflows or fixes in other modules. Inventory other compatibility leads only in the report. Completing this slice does not close #133 or certify all Python support. Keep the whole delta compact (aim under 24 KiB) so the complete artifact fits in one PR comment.

## Verification

Run the old and new governance-focused tests on the actual installed Python(s), full `python -m unittest discover -s tests -v` when supported, and `git diff --check`. Report commands, exit codes, counts/failures/skips, Python/dependency versions and exact tested revision. Compare working-tree status and allowed changed files; do not run destructive cleanup. Record missing interpreters, dependencies and packaging checks honestly. Do not fetch real consumer data or use external model inference. Do not add/download interpreters, packages or models in this task.

## Durable delivery and parallel boundaries

Provide a Russian final report plus the COMPLETE exact unified diff for the three allowed paths in a diff fence, with SHA-256 and final-newline convention. Include new-file contents by staging only allowed paths before exporting the diff. Never return a truncated patch or only a local SHA, make_pr metadata, or links to the unchanged seed. If an already authorized interface supports updating this existing PR branch, it is allowed, but the recoverable patch is still required. Otherwise return the patch and state not published. No new PR/branch, remote/credential/permission changes, force-push, merge, marking ready or closing issues. Do not assume another cloud task can access this workspace. W01 and W09 draft separate proposed contracts; do not depend on their unaccepted results or edit their files.
