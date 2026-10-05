# W11 current document-role and link matrix

Characterization only, under issue #132. No runtime policy change is approved or implemented here. `tests/test_document_role_matrix.py` exercises actual profile reports, lint nodes/edges, JSON graph nodes/edges/fragments, ZIP members and local search paths on fresh synthetic files; every case compares source bytes and file membership before/after. These snapshots do not establish absence of transient writes.

## Roles

Each fixture also contains a valid ordinary source concept.

| Role | Profile | Lint source node | Graph export | Published bundle | Local retrieval |
|---|---|---|---|---|---|
| Ordinary `.MD` concept | pass | included | included | included | included |
| Generic valid Concept stored under research/ (not a research workflow) | pass | included | included | included | excluded |
| Research brief with `in-progress` | fail | included | blocked | blocked | excluded |
| Raw capture | excluded | excluded; eligible evidence target | excluded | excluded | excluded |
| Lesson | excluded | excluded; invalid target | excluded | excluded | excluded |
| Lowercase index/log | excluded | included | excluded | included | excluded |

Research workflow status remains authored `in-progress`: it is not rewritten to an OKF lifecycle. Its profile rejection is an observed unresolved mismatch, not permission to exclude every research directory or change the schema. ADR-017's retrieval exclusion deliberately is not ADR-003 validator parity.

## Links from an ordinary source

| Body syntax | Lint | Graph export | Bundle |
|---|---|---|---|
| Existing lowercase target | edge | edge | source retained |
| Existing target with fragment | edge, no fragment field | edge with authored fragment | source retained |
| Missing target | fail | blocked | source retained |
| Missing target inside inline code | fail | ignored | source retained |
| Missing target inside fence | ignored | ignored | source retained |
| External HTTPS `.md` | ignored | ignored | source retained |
| Existing target with title | ignored | edge | source retained |
| Existing uppercase `.MD` target | ignored | edge | source retained |
| Fragment-only anchor | ignored | ignored; no anchor validation | source retained |
| Raw evidence target | evidence link, pass | blocked non-node target | raw excluded, source retained |
| Lesson target | fail | blocked | lesson excluded, source retained |

Bundle membership checks do not establish graph integrity. ADR-005 explicitly defines a richer export grammar than the historical lint regex; differences are documented, not automatically normalized. Shared fence handling already exists. Inline/title/uppercase behavior needs a separately scoped contract assessment before changing lint parsing. No external links are fetched by this characterization.

## Scope and retention

This finite local matrix does not cover every Markdown grammar, research template expansion, QMD registration, hostile concurrent writers or every symlink platform. Existing safety regressions remain authoritative. No QMD/model/network/consumer operation is invoked.

Repository-tracked evidence owner: ozand/kb-bootstrap; path: this report and its tests; retention/disposal: repository history and owner-controlled amendments; access: public repository; integrity: containing Git commit. Runtime test stdout is ephemeral, not an immutable audit record. Observed parent execution on Windows: focused pytest 2 passed; full pytest 421 passed, 8 skipped; documented unittest 355 tests, OK, 8 skipped. These summaries are versioned with this report, not immutable runtime logs. GitHub comments are mutable supplemental communication, not independent retention guarantees.
