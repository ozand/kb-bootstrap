# Managed AGENTS.md repository-governance block

Use the managed block when a downstream repository already has local `AGENTS.md`
instructions that must not be overwritten.

```bash
kb-bootstrap agents-governance \
  --repo example/consumer-project \
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
- every byte outside the managed markers is preserved;
- duplicate, missing, or reversed markers block the update without writing;
- the generated block contains only the explicit repository identity and public
  command guidance, never credentials or runtime data.

The command is explicitly invoked. Normal `kb-bootstrap` scaffolding does not
modify an existing downstream `AGENTS.md`.
