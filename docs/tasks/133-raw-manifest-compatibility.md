# W12-A2: raw-manifest stat compatibility

Parent: #133 / #121. Source baseline: main@9717bc29c7ab455cc8a7648c8f740e7f9959967a.

## Task
Reproduce the use of the post-3.9 `Path.stat(follow_symlinks=False)` API in `raw_manifest._signature`. Make the minimal compatibility-preserving replacement using the already imported `os`, retaining no-follow behavior and all device/inode/size/mtime comparisons. This is a bug-fix slice of the existing ADR-010 contract, not implementation of Proposed W03/W08.

Allowed writes: `kb_bootstrap/raw_manifest.py` and new `tests/test_raw_manifest_compatibility.py` only. Read existing raw-manifest tests and ADR-010. Do not change graph export, governance, lesson enablement, checkpoint verification, dependencies, schemas, CLI, or other tests.

## Evidence
Use temporary synthetic files to prove regular-file signatures, symlink no-follow semantics where supported, and compatibility when Path.stat rejects the newer keyword. Reproduce before fixing, run new and existing raw-manifest tests plus full tests on the available interpreter. A simulated old API is not an actual Python 3.8 run. Other modules may still prevent end-to-end old-Python support: report that limit rather than broadening scope.

References: Python pathlib documents the keyword as added in 3.10; Python 3.8 os.stat documents follow_symlinks. No installation or runtime download is authorized.

## Delivery
Verify the entire changed set. Return the complete exact full-index diff FIRST in the final GitHub comment, then byte count, SHA-256, base/result, file hashes and short actual test receipt. Coordinator publishes to this branch after checking. No remote, credential, permission, branch, merge, ready-state or issue-state changes. No private corpora, optional models or network source collection. Do not hide unexpected changes behind a filtered diff.
