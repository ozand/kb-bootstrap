# W03-A: source and capture contract design

Status: execution brief, not an accepted contract. Refs #124 and #121.

Read live #124, ADR-010, provenance work #90, and existing source/capture guidance. Target only ozand/kb-bootstrap. Base main: 9717bc29c7ab455cc8a7648c8f740e7f9959967a.

Allowed outputs: docs/proposals/W03-source-capture.md and docs/fixtures/W03-source-capture-examples.md. Produce a compact Proposed contract and original synthetic examples: exact/partial/blocked/manual-summary, distinct origins with duplicate bytes, changed original versus changed conversion, retained versus reference-only evidence, known versus unknown original coordinates. Reuse raw-manifest v1 unchanged. Do not impose a domain ontology or force readable code into Markdown. Digests must be computed from the literal fixture bytes, never invented.

W01/W09 are unaccepted and being reconciled. Record interface questions; do not implement their drafts. No production code, schemas installed as normative, collectors, converters, model/software installation, private sources, network acquisition, shared indexes or other PR edits. Local fixture computations are permitted.

Before delivery verify the entire changed-file set. Return the complete diff including new files in an outer fence longer than inner fences, exact byte length/SHA-256/LF convention and actual document/fixture checks. Publication is coordinator-only; no branch mutations, merge, ready-state change or issue closure. Keep under 24 KiB where practical. A task-local SHA is not a published result.
