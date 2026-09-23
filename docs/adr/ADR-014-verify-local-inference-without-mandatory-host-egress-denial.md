# ADR-014: Verify ordinary local inference without mandatory host egress denial

**Status**: Accepted
**Date**: 2026-09-23
**Authors**: Pi coding agent
**Supersedes**: ADR-011, ADR-013
**Related**: Issues #100, #109, #108; ADR-010, ADR-012

## Context

ADR-011 requires a real model smoke under denied network before claiming local-only behavior; ADR-013 also refuses to mark setup complete without observed OS egress denial. That conflates two different assurances: whether the installed code intentionally makes network calls and whether the operating system prevents *any* process from doing so. A model file is data, but the optional runtime and dependencies execute code. Source review, pinned packages, explicit local paths and offline-only library APIs can make the ordinary workflow verifiably free of intentional downloads; they cannot prove that a compromised process cannot transmit data. Windows firewall probes did not establish host isolation: the observed firewall profiles were OFF. Requiring a host firewall/VM for every ordinary model setup prevents the user from exercising a local model without improving what software checks actually attest. The owner approved separating those assurances. ADR-011/013 cannot be edited in place because they are Accepted; this decision supersedes both, preserving their other contracts.

## Decision

**Only upon separate acceptance**, supersede ADR-011 and ADR-013, changing strictly (a) ADR-011's denied-network smoke prerequisite for an ordinary local inference claim and (b) ADR-013's OS-denied-network prerequisite for ordinary setup readiness. Until acceptance both remain binding; ADR-012 stays superseded by ADR-013. Preserve every other ADR-011 peer/card schema, provenance, privacy, offline API and canonical framed model-byte digest rule. Preserve every other ADR-013 rule: isolated fully hashed dependency lock, license and exact source/revision/redirect/file consent before any request, owned quarantine, complete-file digest trust routes, second exact-digest owner confirmation on the weaker route, exclusive no-overwrite promotion, rollback and non-authenticity labeling. No change to Issue #108's separate remote adapter.

For ordinary, sanitized local setup, mark only `local-smoke-verified; host-egress-unverified` when an installed pinned runtime loads the explicit complete checkpoint with verified ADR-011 digest from disk, performs real inference on harmless sample text, fails on incomplete assets and exercises no intentional download or network fallback. Record tested runtime version and checkpoint digest; this label never means `secure`, publisher-authenticated, or isolated from egress. Set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` before importing the optional runtime; use supported `local_files_only=True` for every model/config/tokenizer load, otherwise fail closed. Check the real supported version's API and perform negative tests that detect attempts to call standard network clients; do not treat a Python socket patch as OS network denial. The smoke receipt retains the exact readiness label and records `host egress isolation: unverified` unless independently established; it never claims publisher authenticity from a post-download digest.

For sensitive/private raw corpora, the operator must separately verify host-level denied egress before use and keep the evidence outside the model receipt. Software flags and tests do not certify a hostile or compromised dependency. The ordinary smoke does not read a raw corpus, write canonical knowledge, authorize a specific download, or prove all possible network paths are blocked. Absent a tested platform control, report the sensitive-data security boundary as `unverified`, not ready for sensitive processing; do not silently reinterpret ordinary smoke as that approval. Issue #109 still requires acquisition, isolated environment and a real local smoke before it is complete; an inspection-only helper remains insufficient.

## Alternatives Considered

- Require an OS-denied environment for every ordinary smoke: stronger egress proof when configured correctly, but unnecessary for checking local model usability; it blocked setup on the current host.
- Claim offline environment flags or socket monkeypatches isolate the process: rejected because dependencies and native code can use other network paths.
- Remove offline-only runtime settings and rely on trust in open source: rejected; missing model assets may trigger implicit downloads.
- Use a remote GLiNER endpoint: rejected for local inference; #108 owns the separate raw-data trust boundary.

## Consequences

### What gets easier

- A user can locally verify a model and harmless sample without configuring a firewall or VM on an ordinary host.

### What gets harder

- Local usability and egress containment must be reported separately. A compromised runtime can transmit data unless the operator supplies a verified host boundary; sensitive raw remains gated and cannot inherit ordinary readiness.

### What does not change

- No default GLiNER2/core dependency, hidden model acquisition, raw/canonical rewrite, remote inference, or silent publisher-authentication claim. ADR-011 candidate-card and ADR-013 acquisition contracts otherwise remain in force under this superseding decision.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Ordinary smoke loads complete real model and returns harmless predictions | pinned-runtime real-model fixture | not yet run |
| Missing asset fails without fallback | incomplete-checkpoint negative smoke | not yet run |
| No intentional network requests in local inference path | offline flags, local-only API, network-client interception fixture | not yet written |
| Ordinary readiness is explicitly local-smoke-verified, not secure or egress-isolated | exact receipt label plus tested runtime/digest fixture | not yet written |
| Standard-client interception does not claim OS isolation | sanitized receipt assertion and documentation review | not yet written |
| Sensitive raw remains gated on independently verified host denial | guidance/receipt state fixture; platform-scoped egress test if used | not yet run |
| Acquisition consent/digest/lock and core independence remain intact | ADR-013 setup fixture and clean-core regression | not yet run |

## Rollback

Before acceptance, withdraw this proposal; ADR-011/013 remain binding. After acceptance, a future superseding ADR can restore mandatory OS-denied smoke; existing model files are owner-managed and never silently deleted.

## References

- ADR-011, ADR-013; GitHub issues #100, #109, #108
- Local firewall probe incident recorded on #109 (no host network-isolation evidence)
