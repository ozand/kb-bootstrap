# Migrating existing consumer repositories to kb-bootstrap

Migrate one explicitly selected consumer repository at a time. Do not scan or
modify the whole workspace automatically.

## Prerequisites

- Install the intended `kb-bootstrap` version in an isolated environment and record that version in the migration evidence.
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
  --project-root . \
  --file AGENTS.md
```

The command may create or update only the delimited kb-bootstrap block. Content
outside the markers must remain unchanged. The file path must be relative to the
explicit project root. Path escapes, static symlinks, concurrent source changes,
duplicate/missing/reversed markers, invalid UTF-8, and atomic publication failures
block migration without overwriting the current file; resolve them manually instead
of deleting local instructions.

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
migration. If the consumer already uses the dual collection layout, run:

```bash
kb-bootstrap validate --dir kb --project-root .
```

If it still uses legacy `default.yaml`, plan the QMD migration as a separately
reviewed change; do not combine it with AGENTS.md or push-configuration recovery.

This command establishes only the universal kb-bootstrap conformance and repository-declaration results it reports. Run any repository-owned policy validator separately. QMD registration, indexing, and retrieval freshness also require separate runtime observations. Follow [validation composition](VALIDATION_COMPOSITION.md) and record each required gate with its own label, owner, evidence, and outcome rather than treating one pass as proof of another.

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

## OKF alignment compatibility preflight

This section describes implemented behavior only. It does not migrate content or make
an existing repository conform. Select one consumer checkout with its owner; do not
read or validate its content until that owner permits it. The commands below are
capabilities, not steps this guide runs automatically.

| Behavior and source | Compatibility and detection | Remediation owner and rollback/deferral |
|---|---|---|
| Minimal OKF v0.2 profile (ADR-003; #88) | `validate` checks ordinary Markdown concepts for UTF-8, parseable mapping frontmatter, and non-empty `type`; unknown types and extra keys are accepted. It reports profile results separately from graph/QMD checks. Inspect the report on an owner-authorized stable checkout; validation is read-only, but assumes no concurrent replacement. | Project owner reviews any failing concept and edits it manually after preserving its authored bytes and unknown metadata. Keep a versioned, access-controlled backup/commit before changes; revert only that reviewed change to roll back. Defer when ownership or preservation is unclear. |
| Reserved files and published bundle boundary (ADR-009; #88) | `index.md`/`log.md` are reserved case-insensitively in the concept boundary; the opt-in `export-published-bundle` validates and exports Markdown concepts plus permitted exact-lowercase reserved files to an exclusive ZIP. Raw and lesson trees remain in the working tree and are excluded from the artifact. Use `validate` or the explicit export only with owner permission; neither is an automatic migration. | Project owner reviews reserved-file diagnostics and decides any manual change. Preserve source bytes and unknown metadata; retain the original versioned checkout and archive the produced ZIP under owner retention policy. Roll back by discarding only the new ZIP or reverting reviewed edits; defer rather than relocating raw/lesson content. |
| Canonical graph links and graph JSON (ADR-005; #89) | Relative links resolve from their source; leading `/` links resolve from the selected canonical root. Unsafe or unresolved local Markdown targets fail graph integrity. `export-graph` is optional, read-only, and keeps its graph result distinct from pure profile conformance. Inspect the separate report on an authorized checkout. | Project owner reviews and manually edits an authored link if appropriate; preserve original bytes/version first and revert that narrow edit if needed. Defer graph cleanup independently; a graph failure is not by itself an OKF-profile failure. |
| Implemented provenance/freshness profile (ADR-006) | `validate` separately reports bounded `generated`, `verified`, `sources`, `status`, and `stale_after` checks. `--now` provides explicit comparison time; without it freshness is unknown. Resources are not fetched or opened; values are not echoed, source text is not rewritten, and unknown keys are preserved. Use the report only with project-owner authorization. | Project owner manually reviews any metadata change, retaining authored bytes and unknown fields in a versioned backup. Roll back only reviewed edits. Missing optional metadata may remain unknown; defer any ambiguous resource or actor interpretation. |
| Additional provenance proposals (#90) and Attested Computation/result interpretation (#91) | Not delivered by the accepted ADRs above: proposed scope-bearing/resource forms, actor conventions, `sources.last_modified`/`usage_window`, and Attested Computation are not implied by current validation. Do not present them as validated or infer guarantees from the profile report. | No migration action is authorized by this guide. Defer until the applicable implementation and owner-reviewed contract are accepted; preserve existing metadata unchanged. |

For each row, detection is limited to the explicitly selected checkout and the
commands documented by the installed version. No step infers ownership from paths,
reads arbitrary resources, or automatically repairs content. Keep backups and
versioned records only under the consumer owner's retention policy; do not place raw
corpus material, credentials, or private payloads in reports or migration receipts.

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
