# ADR-035: Require explicit local policy for evidence reading

**Status**: Proposed
**Date**: 2026-10-19
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #130; ADR-014, ADR-017, ADR-022, ADR-024, ADR-026, ADR-031

## Context

Accepted ADR-031 specifies a future caller-directed, read-only resolver for one knowledge document and validated baseline/current evidence envelopes. Its paths, bindings, qualifiers, hashes, and output do not authorize reading. W09/#130 requires sensitivity, applicability, access, and write/review authority to remain distinct. Accepted ADR-022 governs external actions; ADR-014 preserves the ordinary-smoke versus sensitive-data host-egress distinction. Open PR #137 is a Proposed broader policy, not an accepted universal policy engine. This ADR proposes only a narrow read-eligibility boundary for future ADR-031 use; it does not accept PR #137, define universal sensitivity taxonomy, or implement enforcement.

## Decision

If accepted, a future ADR-031 resolver may read caller-selected knowledge and evidence files only when the consumer's explicitly selected local policy permits the requested data sensitivity, knowledge applicability, reader scope, and exact selected root/revision for that read. These are separate policy facts: applicability does not grant access; read permission does not grant review, write, publication, or action authority. ADR-022 continues to govern any external action.

The caller must explicitly select the local policy and input roots through the existing trusted operator workflow; this is an explicit owner/operator declaration, not cryptographic identity proof or a new authentication mechanism. For example, the caller may select the binding document, knowledge document, and required envelope members under three already permitted input classes/roots. A relative path found in a binding or source that names a fourth root is refused; metadata cannot add it. Binding fields, paths, hashes, source instructions, frontmatter, classifier results, model confidence, probe state, configuration, or prior receipts cannot create or widen permission. Reuse ADR-017/024/026 path-containment and full-envelope validation contracts; this ADR adds no path or evidence schema. Missing, conflicting, revoked, or unverifiable policy permission blocks the read and any dependent derivation with a sanitized result; no hosted fallback, alternate root, or implicit retry is allowed. Revocation blocks new reads/derivations but does not silently delete retained data.

Treat evidence bodies and derived metadata—including filenames, hashes, bindings, indexes, query text, logs, and resolver reports—as potentially sensitive. A consumer policy owner selects permitted local storage/access and retention for these artifacts. This ADR defines no retention schema, deletion operation, universal store, or guarantee of erasure from Git history, backups, or downstream copies. Retraction, archival, supersession, and deletion remain distinct owner-governed operations under the applicable policy.

This contract does not claim that a local-only client test proves OS-level egress denial. ADR-014 remains binding: ordinary harmless smoke may establish only `local-smoke-verified; host-egress-unverified`; sensitive/private processing still requires separately verified host-level denied egress. No policy allow result substitutes for that evidence.

### What this is not

This ADR is not a policy engine, authorization/grant format, identity provider, persisted consumer policy schema, universal sensitivity taxonomy, resolver implementation, or approval of PR #137/W01. It does not modify ADR-031's normative contract, add CLI flags, change ADR-014/022, authorize real sensitive data processing, or weaken ADR-011/013 retained requirements.

## Consequences

### What gets easier

A future resolver can distinguish evidence identity/selection from consumer permission to read it, without treating descriptive metadata as authority.

### What gets harder

Callers and consumer owners must select and maintain a policy plus exact roots and scopes. Missing or unverifiable policy state blocks reads; no universal policy representation is provided.

### What does not change

ADR-031 remains read-only and caller-directed. ADR-017/024/026 own bounded paths and evidence validation; ADR-022 owns external-action authority; ADR-014 owns the ordinary/sensitive egress distinction. No runtime behavior is implemented here.

## Alternatives Considered

### Treat binding or path possession as permission

Rejected because identifiers and caller-supplied paths select inputs but do not establish sensitivity approval or reader authority.

### Reuse external-action authority as read permission

Rejected because ADR-022 keeps read, local write, review, and external actions independent; conflating them grants more authority than required.

### Define a universal policy engine or persisted grant format now

Rejected because W01 and W09 representation/identity questions remain owner decisions; a generic engine exceeds this bounded resolver-specific boundary.

### Treat local-only testing as proof of sensitive-data safety

Rejected because client interception cannot prove host-level denied egress; ADR-014 explicitly requires independent host evidence for sensitive/private processing.

## Test Contract

| Claim if accepted and implemented | Synthetic test | Currently |
|---|---|---|
| Explicitly selected binding/knowledge/envelope roots may be read only within their permitted scopes; a path named by untrusted metadata cannot add a fourth root | `test_untrusted_binding_cannot_grant_read` | not yet written |
| Missing, conflicting, revoked, or unverifiable local policy blocks new reads/derivations before access, without implicit deletion of prior data | `test_policy_denial_blocks_before_read` | not yet written |
| Read permission does not imply review, local-write, publication, or external-action authority | `test_read_scope_is_non_transitive` | not yet written |
| Resolver outputs and metadata are treated as potentially sensitive; absent an owner-selected local retention/access rule, no storage destination is inferred | `test_report_requires_explicit_retention_rule` | not yet written |
| Local client interception does not satisfy the sensitive host-egress gate | `test_local_client_probe_not_host_isolation` | not yet written |

## Rollback

Before acceptance, withdraw this proposal; no runtime or consumer state is changed. If accepted, any reversal requires a superseding ADR and must preserve existing consumer policy and retained records. No data is deleted by rollback.

## References

- Issue #130 and research checkpoint: https://github.com/ozand/kb-bootstrap/issues/130#issuecomment-6264244488
- Accepted ADR-014, ADR-017, ADR-022, ADR-024, ADR-026, ADR-031
- Proposed W09 policy in PR #137 (unaccepted); proposed W01 capability work in #122 (unaccepted)
- `docs/EVIDENCE_RETENTION.md`
