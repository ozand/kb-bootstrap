# W06: Synthetic pinned QMD indexed-membership evidence

## Observed run

Owner authorized exactly one hook-free update in a new synthetic TEMP corpus. Parent ran `tools/qmd_membership_smoke.py --consent-synthetic-update` on Windows with installed QMD 2.8.3 (facd35e), native Node launch and explicit named index/config/cache/SQLite paths. No collection add, installation, embed, hybrid/vector query, hooks, trust commands or global collection operation ran.

Result: **OK; 2 active canonical documents; 11 excluded fixtures; 13 lexical checks**. Read-only SQLite active membership equalled the two expected relative paths. Positive tokens returned hits; every negative token returned no hits. All source hashes were unchanged; no scratch model-cache directory appeared. Invocation-owned TEMP state was retained, not deleted.

Negatives include root/nested and mixed-case raw/research/lessons, hidden files/directories, reserved index/log and a non-Markdown file. Positives include a nested Unicode filename. The authored ignore patterns use ASCII case brackets; uppercase Markdown extension parity and all possible path/platform cases are not established by this finite fixture.

## Reproduction boundary

Ordinary pytest does not execute QMD. Two offline fixture/consent tests verify construction and refusal without explicit consent. Each future real run requires fresh owner consent to a new synthetic update; the CLI flag is a guard, not authorization by itself.

From the repository root with installed prerequisites and explicit consent:

```text
PYTHONPATH=. python tools/qmd_membership_smoke.py --consent-synthetic-update
```

All runtime commands use bounded process execution. Failures retain owned scratch and do not retry update. No operator config/cache/corpus contents are copied or inspected.

## Evidence limits

This is concrete membership/retrieval evidence for the tested pinned synthetic configuration, not proof that arbitrary consumer declarations are synchronized with QMD's registry. QMD `collection add` still overwrites ignore rules. Raw-mode registration spanning both kb/raw and kb/research is not implemented by this canonical-only fixture. Source truth, model readiness, global write isolation, process-tree termination and host-wide no-egress remain unverified.

Parent verification: full pytest **419 passed, 8 skipped**; offline focused **2 passed**. Independent read-only review approved the script before the single authorized update. Runtime product code is unchanged in this increment.
