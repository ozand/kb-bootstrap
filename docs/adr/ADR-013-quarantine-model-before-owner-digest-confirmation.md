# ADR-013: Quarantine a consented checkpoint before confirming its full digest

**Status**: Accepted
**Date**: 2026-09-23
**Authors**: Pi coding agent
**Supersedes**: ADR-012
**Related**: ADR-011 (local inference), ADR-012 (optional setup), Issue #109

## Context

ADR-012 requires an independently obtained expected full checkpoint digest **before** any model download. The publisher's pinned model revision exposes a Git LFS SHA-256 for weights and Git blob object IDs for other files, but not ADR-011's framed stream SHA-256 across every checkpoint file. A Git commit, LFS digest, or locally computed post-download digest is not that prior full expected digest. No prior owner value has been supplied. Consequently #109 cannot provide a usable setup from no checkpoint under ADR-012 as written; it must remain inspection-only. This is a proposed change of acquisition trust boundary, not approval to download. **Until this ADR is separately accepted, ADR-012 alone governs and no post-download-digest acquisition is permitted.** Acceptance will change ADR-012's status/index to `Superseded by ADR-013` without rewriting its historical decision.

## Decision

**Only upon acceptance**, supersede ADR-012 as the governing setup decision. Carry forward its isolated, optional, pinned package environment, fully hashed dependency artifacts, explicit license gate, and ADR-011's no-download inference contract. Replace its mandatory prior full-checkpoint-digest gate for model acquisition with one of two explicit verification routes: an independently authenticated prior full digest (the stronger existing route), or the following weaker quarantine/owner-confirmed route when that prior digest is unavailable. Never switch routes silently:

1. Before any network request or destination mutation, show exact publisher HTTPS origin, explicit model ID, full immutable commit revision, **closed exact relative file list** (including any ancillary file selected for the checkpoint), known/unknown total size, license terms, dedicated staging/destination and retention limits. Require explicit consent to that one acquisition. Fetch exact files at that full revision over certificate-validated HTTPS; validate repository/revision/source metadata against the approved plan. Follow a redirect only if its exact HTTPS origin was disclosed and approved before acquisition; otherwise stop and request fresh consent. Do not log signed redirect URLs or credentials. Reject unlisted files; the hashed directory contains exactly the approved file set. Absent license acceptance, controlled source, immutable revision, redirect approval or consent, make no request.
2. Download exclusively into new, owned, non-executable quarantine staging. Reject redirects or extra sources outside disclosed scope, unsafe names, symlinks, incomplete files, occupied destinations and hash mismatches against any publisher-provided per-file checksum. No model import, deserialization or execution in quarantine. Preserve foreign state on failure; clean only identified owned staging.
3. Compute ADR-011's canonical SHA-256 on **all** staged regular checkpoint files: sorted safe relative POSIX paths, each framed by `uint64_be(path UTF-8 length) || path UTF-8 || uint64_be(file length) || file bytes`. Present the digest, exact file inventory, pinned source/revision and trust limitations; require a **second explicit owner confirmation of that exact digest** before exclusive no-overwrite promotion. The receipt labels this `owner-confirmed-post-download`, never `publisher-authenticated`. This verifies local identity for later no-download runs, **not** independent publisher authenticity or model safety. The independently authenticated prior-digest route remains available under this ADR, and must not be relabeled as a post-download owner confirmation.
4. No automatic confirmation, model default, extraction of raw content, canonical write, remote service, or claim of usable model merely because download/hash succeeded. Acquired bytes are not independently authenticated as publisher-approved by the weaker route: the owner explicitly accepts this residual supply-chain risk; do not import/deserialize them until promotion and the isolated smoke. Mark ready only after a real model smoke on sanitized text in an observed network-denied environment, plus incomplete-checkpoint failure. When OS network denial is unavailable, report `unverified` and do not mark setup complete.

Issue #109's full outcome remains mandatory; inspection alone does not close it. A specific download still needs its own scope and informed consent after this ADR is accepted.

## Alternatives Considered

- Keep the prior expected full digest mandatory: strongest authentication, but none is currently published or supplied; #109 remains blocked. Preserve this path when a manifest later exists.
- Treat the publisher's Git commit/LFS hash as the full digest: rejected because it omits non-LFS files and uses a different hashing contract.
- Download and self-hash, then automatically promote: rejected because a post-download hash alone does not establish publisher authenticity or informed owner choice.
- Allow arbitrary model hub API/cache fallback: rejected because it defeats scoped consent, quarantine and no-download inference.

## Consequences

### What gets easier

- An owner starting without a checkpoint can authorize one pinned acquisition and explicitly bind its observed complete bytes for future offline runs.

### What gets harder

- Two deliberate approvals, owned staging, per-file provenance and genuine OS-level egress tests add work. A malicious upstream can still supply a malicious checkpoint; confirmation is not publisher attestation or code safety.

### What does not change

- GLiNER2 remains optional outside core; ADR-011 inference remains local/no-download; #108 remote endpoint stays separate. Existing foreign directories are never silently overwritten or deleted.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| No request or mutation before scoped license/acquisition consent | denied-consent and network spy fixture | not yet written |
| Pin closed file inventory and approved HTTPS redirect origins | changed-commit/extra-file/redirect fixtures | not yet written |
| Only pinned source/revision and owned quarantine may change | redirect/extra-file/occupied-destination/interruption fixtures | not yet written |
| Digest matches ADR-011 framed bytes, not per-file-hash manifest | multi-file canonical digest and mismatch fixture | not yet written |
| No promotion before second exact-digest confirmation | mismatched/declined owner confirmation fixture | not yet written |
| Receipt distinguishes owner-confirmed from publisher-authenticated | sanitized receipt and redaction fixture | not yet written |
| Model ready only after real denied-network local smoke | complete and missing-asset smoke on supported isolated host | not yet run |
| Core, QMD and raw remain independent | clean-core regression and immutable-source checks | not yet run for this change |

## Rollback

Withdraw this Proposed ADR without effect. If accepted later, supersede it to restore the stronger prior-digest gate; downloaded artifacts are owner-managed and require explicit identified cleanup. Never remove foreign directories or assume a rollback can undo network transfer.

## References

- ADR-011, ADR-012; Issue #109; PR #112 (inspection only)
- Hugging Face model tree API for `fastino/gliner2.5-small-v1` at `7e6f537f10337497069276892a5ef435028252ce` (reported candidate, not approved default)
