# W01-A: tool-independent core and capability decision

Status: execution brief, not a delivered design or accepted decision. Parent: #122; programme: #121. The owner requested parallel executors on 2026-09-28. This assignment is one bounded design slice, not authority to implement an entire epic.

Repository: `ozand/kb-bootstrap`. Branch: `codex/w01-core-capabilities`. Main baseline: `9717bc29c7ab455cc8a7648c8f740e7f9959967a`. Use this PR's seed/head as the working revision. Do not edit the planning PR #134, implementation PR #135, or another worker's branch.

## Read before drafting

Read issue #122 and comments, `docs/CONTRIBUTING_UPSTREAM.md`, `docs/VALIDATION_COMPOSITION.md`, `docs/adr/INDEX.md`, applicable Accepted ADRs, `kb_bootstrap/cli.py`, `qmd_validator.py`, `repository_doctor.py`, packaged skill instructions and historical #4/#6. Optional planning context is pinned at `30cdbdb14731caa3affee277f9e53547b7944999` in `docs/implementation/PRODUCT_INTENT.md`, `ARCHITECTURE_PROPOSAL.md` and `WORK_PACKAGES.md`. If that context is not available, use the live issue plus these requirements, record the gap and continue without merging the planning branch.

The product serves domain knowledge for people and agents. External originals, retained machine-readable material, curated knowledge, candidate analysis, progress and search projections have distinct roles. QMD, Surf, GLiNER, GitHub and an individual agent runtime are optional implementations, not prerequisites for proposed local knowledge maintenance. Current accepted behaviour is still binding until explicitly superseded.

## Deliverable and exclusive write scope

Create only `docs/proposals/W01-tool-independent-core.md` (target at most 180 lines). Keep this seed unchanged. Use a Proposed ADR structure with context, proposed decision, alternatives, compatibility/migration, tests, consequences and rollback. Leave its numeric ADR ID unassigned; D01 is a decision topic, not an ADR number. Do not edit shared ADR indexes, README, AGENTS.md, runtime code, tests, CLI defaults or templates.

Include:
- a source-referenced matrix of current behaviour versus proposed behaviour;
- capability states: not configured, explicitly disabled, configured/available, configured/broken; distinguish optional absence from consumer-required failure;
- separation of local structural/content checks, consumer policy, optional index readiness and explicit remote-publication checks;
- a migration strategy that does not silently bypass existing doctor/publication gates, reconfigure collections or install software;
- bounded first implementation and synthetic acceptance cases, including no optional binaries/network and configured-broken tools;
- an interface with W09 policy: record assumptions/questions rather than requiring its unfinished proposal or inventing access defaults;
- layout choices versus domains, and no mandatory plugin framework, service or model.

## Parallel coordination and safety

One writer per assigned branch/file. W09 owns a separate policy proposal; W12 owns a separate runtime slice. Cross-read public evidence when needed but do not alter others' output or assume their unmerged work is accepted. Existing #90-#92, #100-#102, #108/#109 retain their scopes. No real consumer data, model downloads, external inference, permission/remote changes, automatic ADR acceptance, force-push, merge, ready-state change or issue closure. Reviewing public repo evidence is authorized; this does not authorize processing private corpora.

## Verification and delivery contract

Verify the checkout contains the assigned PR seed/head. Check references, proposal status, internal consistency, allowed changed paths and `git diff --check`. Documentation checks are not runtime/model evidence. Explain outcome and remaining decisions in Russian; repository prose may remain English.

The final GitHub task comment MUST include the complete exact unified diff for the assigned file, including new-file content, inside a diff fence, plus patch SHA-256, final-newline convention, base/head IDs, changed paths and checks actually run/not run. Stage only the assigned file when producing a new-file diff; do not omit it as untracked. Keep the diff compact enough to fit in one comment (aim below 24 KiB); remove repetition rather than truncating the artifact. If the already authorized integration can update this existing PR branch, publication there is permitted, but still include the recoverable diff. Otherwise return the diff without claiming publication. Do not create another PR, configure credentials/remotes, or leave only a task-local SHA or make_pr metadata. A subsequent task is not assumed to retain this workspace.
