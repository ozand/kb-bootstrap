# W12-A3: lesson-enablement identity compatibility — historical task

Parent: #133 / #121. Task baseline: `main@9717bc29c7ab455cc8a7648c8f740e7f9959967a`.

## Historical report (resolved on current main)

This task reported `project_lesson_enablement._file_identity` using the post-3.9 `Path.stat(follow_symlinks=False)` API and proposed replacing it with a no-follow-compatible operation while preserving device/inode identity and the existing symlink, exclusive-installation, and cleanup behavior.

That source change was delivered in commit [`fc78495823d62be8cfa305985c6605c5c6c5a1b0`](https://github.com/ozand/kb-bootstrap/commit/fc78495823d62be8cfa305985c6605c5c6c5a1b0), which changed the call to `os.stat(path, follow_symlinks=False)`. The task is historical; its proposed source and test changes are not outstanding work on current main.

This commit history establishes that the specific API call was corrected. It does **not** establish package installation or execution on Python 3.8 or 3.9, nor does it verify the full package's compatibility with those interpreters. Python 3.8 support and dependency-isolated installation remain separate evidence gaps under #133.
