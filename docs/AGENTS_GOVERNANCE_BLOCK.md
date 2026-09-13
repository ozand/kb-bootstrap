# Managed AGENTS.md repository-governance block

Use the managed block when a downstream repository already has local `AGENTS.md`
instructions that must not be overwritten.

```bash
kb-bootstrap agents-governance \
  --repo example/consumer-project \
  --project-root . \
  --file AGENTS.md
```

The command manages only the text between these exact markers:

```text
<!-- kb-bootstrap:repository-governance:start -->
<!-- kb-bootstrap:repository-governance:end -->
```

Rules:

- if `AGENTS.md` does not exist, it is created with one managed block;
- if no managed block exists, one is appended after existing content;
- if one valid block exists, only its contents are replaced;
- repeated execution is idempotent and never creates a second block;
- `--file` is repository-relative and must remain inside the explicit `--project-root`;
- static symlinked roots, parents, or targets and path escapes block before mutation;
- the target parent must already exist; arbitrary directory trees are not created;
- every byte outside the managed markers is preserved, including surrounding CRLF bytes;
- existing file mode is preserved where the operating system supports POSIX-style mode bits;
- duplicate, missing, reversed, or invalid-UTF-8 content blocks without writing;
- a source identity/content recheck detects controllable concurrent edits before replacement;
- existing-file publication uses same-directory atomic replacement; missing-file publication uses exclusive hard-link creation and never overwrites a race-created file;
- filesystems or policies without hard-link support fail closed rather than using an overwriting fallback;
- owned temporary files are cleaned after write/replacement failures;
- the generated block contains only the explicit repository identity and public
  command guidance, never credentials or runtime data.

The command is explicitly invoked. Normal `kb-bootstrap` scaffolding does not
modify an existing downstream `AGENTS.md`. Run it against a stable checkout: the
bounded recheck protects detected edits before publication but is not a global
cross-process filesystem transaction.
