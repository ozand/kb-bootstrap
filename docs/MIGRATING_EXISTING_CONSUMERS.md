# Migrating existing consumer repositories to kb-bootstrap 0.2.0

Migrate one explicitly selected consumer repository at a time. Do not scan or
modify the whole workspace automatically.

## Prerequisites

- Install `kb-bootstrap` 0.2.0 in an isolated environment.
- Know the consumer repository identity in `owner/repository` form.
- Start from the selected consumer repository root.
- Review its local `AGENTS.md`, `CLAUDE.md`, and repository-specific instructions.
- Preserve live `.pi/`, `.agents/`, credentials, and other runtime state. Never use
  a broad untracked-file stash as a generic backup.

Record a narrow backup outside the repository for files you intend to change, for
example `AGENTS.md`, `.git/config`, and existing QMD configuration. Do not copy
credentials into migration receipts.

## 1. Verify repository identity

```bash
kb-bootstrap doctor --repo example/consumer-project
```

Stop unless the command returns `RESULT: OK`. The sanitized receipt may include
repository, default branch, and result; omit remote URLs and runtime data.

## 2. Generate and validate repository context

```bash
kb-bootstrap manifest \
  --repo example/consumer-project \
  --output repository-context.json

kb-bootstrap manifest \
  --output repository-context.json \
  --check
```

Review the file before committing. It must contain only schema version, repository,
default branch, and sanitized origin/upstream roles.

## 3. Adopt the managed AGENTS.md block

Inspect `AGENTS.md` before modification. Then explicitly run:

```bash
kb-bootstrap agents-governance \
  --repo example/consumer-project \
  --file AGENTS.md
```

The command may create or update only the delimited kb-bootstrap block. Content
outside the markers must remain unchanged. Duplicate, missing, or reversed markers
block migration without writing; resolve them manually instead of deleting local
instructions.

Verify the diff:

```bash
git diff -- AGENTS.md
```

## 4. Configure and verify downstream push safety

Set checkout and branch defaults to the consumer `origin`:

```bash
git config --local remote.pushDefault origin
git config --local branch.<branch>.pushRemote origin
```

Verify before a real push:

```bash
git config --local --get remote.pushDefault
git config --local --get branch.<branch>.pushRemote
git push --dry-run
```

Both config values must resolve to `origin`. Do not include token-bearing push URLs
in reports. Upstream framework contributions continue through a separate verified
checkout/worktree with explicit remote, branch, `--repo`, `--base`, and `--head`.

## 5. Verify knowledge-base structure

Do not replace project taxonomy or unrelated QMD content during this governance
migration. If the consumer already uses the 0.2.0 dual collection layout, run:

```bash
kb-bootstrap validate --dir kb --project-root .
```

If it still uses legacy `default.yaml`, plan the QMD migration as a separately
reviewed change; do not combine it with AGENTS.md or push-configuration recovery.

## 6. Test and prepare review

Run the consumer repository's documented tests. Review only the explicitly changed
files, then create a consumer-owned commit and pull request with explicit targets.

Before a completion claim:

```bash
kb-bootstrap check-completion \
  --repo example/consumer-project \
  --commit <commit-id> \
  --pr <number>
```

## Rollback and failure handling

- If `doctor` fails, change nothing; correct repository/default configuration first.
- If manifest generation fails, no manifest should be written. Remove only an
  uncommitted manifest created by this migration after inspecting it.
- If AGENTS.md markers are malformed, restore the narrow backup or fix markers
  manually; never overwrite the full file with a generated template.
- To roll back push defaults, restore the recorded previous values. If a key was
  previously absent, remove only that key with `git config --local --unset <key>`.
- Do not use force pushes, history rewrites, broad stashes, or workspace-wide
  cleanup as migration rollback.
- Stop and request review whenever ownership, repository identity, or preservation
  policy is ambiguous.

## Sanitized migration receipt

For each selected consumer, record only:

- public repository identity;
- doctor result and default branch;
- manifest validation result;
- whether the managed block was created/updated/unchanged;
- sanitized push-default result;
- tests and pull-request URL.

Never record credentials, private payloads, local paths, runtime checkpoints,
object listings, or unsanitized command output.
