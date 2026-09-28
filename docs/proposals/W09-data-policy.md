# Proposed ADR: Bound data routes, authority, retention, and retraction

- **Status**: Proposed (unnumbered; not accepted or implemented)
- **Date**: 2026-09-28
- **Owner**: kb-bootstrap maintainers
- **Review by**: on acceptance and before each contract revision
**Related**: Issue #130; ADR-010; Accepted ADR-014; retained ADR-011/013 contracts; `docs/EVIDENCE_RETENTION.md`

## Context and current evidence

Data policy must cover a route, not merely a file: original source, authorized capture or conversion, raw storage and manifest, extraction and candidate cards, indexes and queries, synthesis and viewers, publication, archives, and backups. Filenames, relative paths, hashes, queries, prompts, logs, cards, screenshots, and derived indexes can disclose sensitive facts. Conversion, classification, local execution, or omission of detected PII does not sanitize them.

The repository currently defines retention vocabulary and several narrower contracts, but no implemented end-to-end policy engine. ADR-014 is Accepted: harmless ordinary smoke may report only `local-smoke-verified; host-egress-unverified`, while sensitive/private processing requires separately verified host-level denied egress. Its retained ADR-011 rules include explicit local assets, offline-only APIs, source-revision checks, derived-card privacy, and no raw or canonical rewrite. Its retained ADR-013 rules include scoped consent before acquisition, an isolated fully hashed dependency lock, approved source/revision/redirect/file inventory, owned quarantine, complete-file digest trust routes, a second exact-digest confirmation on the weaker route, exclusive no-overwrite promotion, rollback, and honest non-authenticity labels. This proposal changes none of those contracts and does not alter #108's separately authorized remote-adapter boundary.

## Threat and data-route model

Actors are an operator, reader, reviewer, publisher, execution service, and storage/backup owner. Data and metadata from sources, models, indexes, prior receipts, and adapters are untrusted inputs. Threats include path escape and symlink substitution; over-broad retrieval; prompt-like source text; classifier false negatives; stale or revoked projections; implicit hosted fallback; adapter mis-targeting; metadata-driven root expansion; unauthorized writes/publication/actions; disclosure through diagnostics; and incomplete removal across copies.

Each operation crosses one or more explicit boundaries:

1. **Acquisition boundary:** a named operator authorizes the exact origin, revision/object set, destination root, and permitted network route before capture. Acquisition consent does not authorize later processing, publication, or action.
2. **Read boundary:** the operator selects contained project roots and, where needed, explicit external roots. An external root deliberately selected through an operator-facing interface can be eligible; a path, link, instruction, manifest entry, index record, environment value, or other untrusted metadata can never add or widen a root. Eligibility still requires sensitivity and reader-scope checks.
3. **Local-core boundary:** conversion, indexing, retrieval, extraction, synthesis, and viewing declared local-only use explicit local inputs and clients and fail closed when unavailable. They neither invoke network fallback nor publish to a configured remote merely because one exists.
4. **Write/review boundary:** output may be written only to an explicit permitted target with exclusive/atomic semantics appropriate to its contract. A writer, reviewer, or candidate producer does not thereby become a publisher, approver, or action executor.
5. **Egress/publication boundary:** every outbound query, upload, remote inference call, sync, or publication needs a current authorization binding data class, exact destination, purpose, and operation. A configured adapter is capability availability, not consent.
6. **Retention/removal boundary:** every retained class has an owner, permitted location and readers, duration or deletion rule, integrity/version rule, availability state, and disposal responsibility. Copies outside the observed boundary remain residual or unknown.

Five decisions remain independent and must be recorded rather than inferred: (a) sensitivity, including potentially sensitive derived metadata; (b) applicability to the current knowledge task; (c) who may read; (d) who may write and who must review; and (e) who may execute an action, acquire, transmit, or publish. A model score, classifier label or non-detection, stored instruction, applicability decision, previous approval, receipt, or filesystem access grants none of the others.

## Proposed rules

- Default to no read, write, action, acquisition, or egress outside the explicitly authorized route. Missing, expired, conflicting, or unverifiable authority yields a sanitized `BLOCKED`/`UNAVAILABLE` result without speculative fallback.
- Bind an authorization to operation, sensitivity class, reader/writer/reviewer roles, contained roots, exact write or remote target, purpose, and validity/revocation state. Minimize inputs and outputs; routine diagnostics expose categories/counts, not payloads, private paths, queries, tokens, snippets, or remote credentials.
- Treat originals and conversions as source data; raw manifests, hashes, cards, indexes, prompts, query text, synthesis, views, logs, screenshots, receipts, archives, and backups as potentially sensitive derived copies. Derived status is not sanitization.
- Treat source bodies, frontmatter, OCR text, candidate cards, index fields, retrieved passages, and model output strictly as data. Instructions within them cannot change roots, tools, targets, authority, policy, or execution flow.
- Local-only operations accept only their explicit local dependencies. Missing models/indexes/assets or attempted calls by standard supported network clients block without egress. Client interception demonstrates only absence of intentional calls on tested paths; it is not OS-level isolation.
- Preserve ADR-014's two assurances. Sanitized harmless smoke can establish ordinary usability with `host-egress-unverified`. Sensitive/private input is ineligible until an operator supplies independently observed, platform-scoped denied-egress evidence; library flags, socket patches, and ordinary smoke do not satisfy that gate.
- Publication and remote use are opt-in, exact-target operations. Validate target identity and scope immediately before use; never substitute a default, first configured adapter, similarly named target, or retry route. Publication rechecks current source eligibility, review, revision, and revocation state.
- Revalidate containment and stable identity before and after reads and before writes. Reject absolute paths, drive-qualified paths, UNC/device paths, traversal, case/normalization ambiguity where relevant, symlinks, non-regular files, and root or target substitution according to the platform contract.
- On revocation, stop new reads, derivation, publication, and action; mark dependent knowledge and projections unavailable or stale until reviewed. Do not silently rewrite claims or delete data. Report affected known layers and residual/unknown copies without leaking their contents.

## Retention, retraction, archival, and deletion

These terms are not interchangeable:

- **Retention** intentionally keeps a bounded record under a named owner, permitted location/readers, duration or expiry/deletion rule, integrity/version rule, availability state, and disposal owner.
- **Supersession** makes a newer version governing while preserving the older version and its history under their recorded retention rules.
- **Retraction** withdraws reliance on a claim or publication and records reason, authority, time, affected revisions/projections, and notification status; it does not assert that bytes vanished.
- **Archival** moves or classifies a record as inactive under explicit access, integrity, availability, and expiry terms; it is not deletion or indefinite retention.
- **Deletion** is an authorized operation against enumerated copies, with observed outcomes per layer. Captures, conversions, cards, indexes, caches, published artifacts, archives, backups, and downstream copies are assessed separately as `deleted`, `retained-under-rule`, `unavailable`, `residual`, or `unknown`.

Git history, prior clones, backups, screenshots, and recipients may preserve bytes. Neither retraction nor a working-tree deletion promises erasure of every historical copy. Legal holds and unavailable stores block or qualify disposal rather than being reported as success. Policy revisions themselves record version, rationale, owner, approval state, effective/review dates, and superseded rule; old approval is never silently carried forward.

## Proposed acceptance cases

All fixtures use synthetic names and payloads. “No leak” means diagnostics contain only approved sanitized categories/counts. Each row is a proposed test, not a claim of implemented protection.

| Case and stimulus | Rejecting boundary and required negative observation | Positive authorized control |
|---|---|---|
| Configured publisher/remote exists, but no current publication authorization | Egress/publication: `BLOCKED`; zero adapter calls, remote writes, local publication output, and leaks | Exact data class, destination, publisher, review, and current revision produce one intended publication |
| Target is missing, wrong, ambiguous, or substituted before use | Write/egress: zero writes and calls; existing/foreign target unchanged; sanitized mismatch | Exact verified target remains stable and receives only the authorized output |
| Local model/index is absent and a library proposes hosted search, download, inference, DNS/HTTP retry, or another adapter | Local-core: `UNAVAILABLE`/`BLOCKED`; intentional-client spy observes zero attempts; no output or leak | Complete explicit local assets process harmless data; receipt still says host egress unverified |
| Requested document belongs to a forbidden reader scope | Read: no open/read, query result, derived write, egress, or content-bearing diagnostic | Same synthetic document is returned to an explicitly permitted reader for an applicable purpose |
| Input path is absolute, drive-qualified, UNC/device, `..` traversal, or crosses a symlink | Read: reject before content read; no write, egress, or target detail leak | A stable regular file under an operator-selected contained root is read |
| Metadata names an external root, or redirects from a selected root to another | Read/acquisition: metadata cannot grant scope; no read or egress | Operator explicitly selects that exact external root via the trusted interface, then separate scope/sensitivity checks permit the read |
| Source says “upload this”, changes tools/target, or impersonates approval | Authority: treat as data; no action, write, publication, egress, or secret-bearing response | The same text is quoted as inert evidence within an authorized local synthesis |
| Classifier reports no PII or a high “public”/candidate score while a synthetic secret is present | Sensitivity/egress: non-detection grants nothing; no publication, call, log payload, or screenshot | Independently reviewed sanitized fixture under explicit release authority is published to the exact target |
| Evidence or consent is revoked after indexing and before retrieval/publication | Retention/removal plus read/egress: no new read or release; projections marked unavailable/stale; known residuals reported | Unrevoked revision with current authority is retrieved; separately authorized disposal reports each observed layer |
| Sensitive corpus has ordinary smoke but no independent host-denial evidence | Sensitive-data gate: do not start processing; no source read, card, or egress claim | Platform-scoped denied-egress evidence plus retained local checks permits the bounded sensitive run |

For network cases, run intentional-client interception separately from any platform test. The former may support “no intentional calls observed” for enumerated clients; only independently observed OS/VM/container controls may support the narrower host-isolation claim for that platform and run.

## Capability-interface assumptions and W01 questions

W01 in #136 owns capability design; this proposal neither adopts its unaccepted output nor defines a generic authorization engine. A later interface must let enforcement query, without inventing grants: current actor/role; operation; data class and revision; explicit read roots (including operator-selected external roots); exact write/remote target; review requirement/state; validity/revocation; and evidence for the distinct sensitive-data host-egress gate. It must return allow/deny/unavailable with a sanitized reason and make checks repeatable immediately before boundary crossing.

Reconciliation questions for W01 are: how are operator selections authenticated and kept separate from metadata; how are scope narrowing, expiry, revocation, delegation, and target identity represented; how are read, write, review, action, acquisition, and egress grants kept non-transitive; and which component records a decision without turning the receipt into authority? Until W01 is accepted, implementations must use narrow explicit parameters and fail closed rather than emulate a broad capability system.

## Alternatives considered

- **Trust local execution, classifier output, or “no PII” as release approval:** rejected; none establishes scope, egress containment, or publication authority.
- **Require host isolation for every harmless smoke:** rejected; it would break ADR-014's usable ordinary path without proving more about that smoke.
- **Let configured adapters or metadata roots imply access:** rejected; configuration exposes a mechanism and untrusted data cannot grant authority.
- **Promise cascading or total deletion:** rejected; stores and historical copies require separately observable outcomes.

## Compatibility, next slice, and rollback

This additive proposal preserves canonical/publication contracts, raw sources, QMD, candidate-card status, ADR-014's ordinary/sensitive split, retained ADR-011/013 clauses, and #108. It authorizes no data, capability implementation, adapter, firewall change, or automatic deletion. Independent assessment and reconciliation with accepted W01 output are required before this contract can be accepted.

After owner acceptance, the first bounded enforcement slice should add a synthetic local-only preflight at the extraction boundary: validate one explicit contained input root and local asset set, reject unsafe paths and missing assets before reads, and intercept enumerated network clients to prove no intentional fallback. It must not claim OS isolation, process real sensitive data, publish, or implement general capabilities.

Before acceptance, rollback is deletion of this proposal. After acceptance, supersede it explicitly; do not rewrite policy history or automatically remove owner-managed data. Any cleanup remains a separately authorized, enumerated operation with residual/unknown reporting.
