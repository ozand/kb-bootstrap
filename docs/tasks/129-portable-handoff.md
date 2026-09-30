# W08-A: portable handoff design

Status: task brief, not a new runtime contract. Refs #129/#121; base main 9717bc29c7ab455cc8a7648c8f740e7f9959967a.

Read live #129, retention policy and current completion/provenance contracts. Allowed outputs only docs/proposals/W08-portable-handoff.md and docs/fixtures/W08-interruption-examples.md. Draft a small Proposed record/flow and synthetic interruption examples. Distinguish captured/read/partially analyzed, provisional versus accepted outputs, pending/blocked/complete, and local artifacts versus GitHub publication. Completion needs matching existing evidence; saved text never grants authority.

Keep source/capture references abstract until W03 is accepted; don't invent a competing source schema. W05/W09 remain proposed dependencies. Specify explicit save/load/check, revision drift, retry idempotency, one-writer handling, privacy and retention without daemon, full transcript, mandatory claims registry or host-specific hooks. Include two-agent continuation and changed-source negative cases, not production code.

Only original synthetic data. No models, installations, network acquisition, consumer reads, shared-index edits, accepted-ADR changes, branch mutations, merge, ready-state change or issue closure. Coordinator publishes. Return the entire scope-checked diff including new files with full-index hashes, exact byte count/SHA-256, UTF-8/LF/final LF and an outer fence longer than internal fences. Report actual document checks and unresolved decisions.
