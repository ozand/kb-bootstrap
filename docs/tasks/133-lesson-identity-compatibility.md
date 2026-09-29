# W12-A3: lesson-enablement identity compatibility

Parent: #133 / #121. Source baseline main@9717bc29c7ab455cc8a7648c8f740e7f9959967a.

Reproduce `project_lesson_enablement._file_identity` calling the post-3.9 `Path.stat(follow_symlinks=False)` API. Replace only the incompatible operation with a compatible no-follow equivalent using the existing `os` import. Preserve device/inode identity checks, symlink rejection, exclusive installation, cleanup ownership, and valid existing-state behavior under accepted ADR-002.

Exclusive writes: `kb_bootstrap/project_lesson_enablement.py` and new `tests/test_project_lesson_enablement_compatibility.py`. Existing tests, raw_manifest, governance, graph/checkpoint modules, CLI/templates/dependencies and all Proposed contracts are read-only.

Use synthetic temporary paths. Reproduce old-keyword rejection before editing; verify identity for regular files and symlinks (when supported), happy-path additive enablement and the existing failure/cleanup tests. Run focused and full tests on available runtimes. Clearly distinguish simulation from actual Python 3.8/3.9 execution. No installations/downloads/models or private consumer data.

Return the COMPLETE exact two-file full-index diff FIRST, including new tests, then byte length/SHA-256, base/result/file hashes and actual commands/results. Check the complete changed set before export. Coordinator publishes; no remote/credential/permission/branch changes, merge/readiness/issue closure. This routine existing-contract compatibility fix does not approve W02 safe-repeat or any new schema.
