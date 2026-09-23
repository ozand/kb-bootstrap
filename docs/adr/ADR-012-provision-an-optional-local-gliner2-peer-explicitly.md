# ADR-012: Provision an optional local GLiNER2 peer explicitly

**Status**: Superseded by ADR-013
**Date**: 2026-09-23
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issues #109, #100, #108; ADR-010 (raw manifest); ADR-011 (local inference)

## Context

Issue #100 and accepted ADR-011 define optional local-only inference using a separately installed Python >=3.10 runtime and a complete local checkpoint. This project and the owner currently have neither an installed GLiNER2 environment nor a verified checkpoint. A tool that merely asks for an existing path leaves ordinary users unable to exercise the local workflow. Issue #109 owns progressive setup; Issue #108 separately owns any HTTP inference service.

GLiNER2's upstream package reports an optional `[local]` inference extra with PyTorch and public checkpoints on a model hub. Explicit one-time model acquisition therefore uses network, while inference must not implicitly download or call a hosted API. Model licenses, size and cache behavior differ by selected checkpoint and must be reviewed before fetching. A package import or process exit is not proof of model loading, rendered predictions, or network denial.

## Decision

Keep GLiNER2 outside core `kb-bootstrap` dependencies and preserve Python >=3.8 core behavior. Provide an **opt-in separate setup companion** with three progressively available levels:

1. **Inspect (offline, read-only):** check an explicitly named Python >=3.10 environment, `gliner2[local]` availability/version, explicit local checkpoint directory, required files, model-card/license receipt, and canonical checkpoint digest from ADR-011. Report missing requirements without installing, downloading, or reading raw content. A missing environment returns actionable steps, not a silent fallback.
2. **Provision (explicitly consented):** on a separate command with an explicit checkpoint identifier/revision and destination, display the exact trusted package index/repository, pinned package and transitive dependency versions with lockfile/artifact hashes, model source and immutable revision, known/unknown total size, target and license metadata **before any network request or destination mutation**. One explicit approval authorizes only the displayed bounded package set and separately one exact model revision/destination; retries or redirects outside those sources require renewed approval and cannot widen scope silently. Missing/ambiguous model license or click-through terms block until the owner explicitly records acceptance; no license acceptance is inferred from a package name. No credentials in arguments, reports or tracked files. Install packages only into a new dedicated environment created by this setup operation; never upgrade or modify an existing Python environment. Stage incomplete files in a dedicated owner-selected location. An expected model digest must come from an authenticated, independently obtained publisher manifest or an explicitly supplied/confirmed owner value before download; a digest computed only after downloading is insufficient to establish expected identity. The setup receipt distinguishes `publisher-authenticated` from `owner-supplied` expected digests; matching an owner-supplied digest proves consistency with that owner's value, not independent publisher authenticity. Verify exact downloaded model assets against that prior expected digest before making the checkpoint eligible for Issue #100. When no trustworthy expected digest exists, setup remains inspection-only. Declined consent produces no download. Cleanup is limited to owned, identifiable staging; a foreign, pre-existing partial or occupied destination is preserved and reported rather than removed blindly.
3. **Advanced execution recipe (optional):** document reproducible isolated-environment options and a bounded local model smoke on sanitized text under denied network. Support only platforms whose execution and negative egress tests were actually observed; unsupported hosts report `unverified` rather than implying an OS sandbox. No Docker/ONNX/Ray/server is mandatory in v1.

Setup and inference are different contracts. Setup may access only the explicitly approved package/checkpoint sources after consent; `validate`, `raw-manifest`, and Issue #100's inference never install, select, or download models. Issue #100 consumes an explicit verified local model path and digest; #109 does not generate entity cards, access a raw corpus, or set up a remote endpoint. Setup evidence is a sanitized local receipt: requested model identifier/revision, digest/version, completion and limitations, not raw model bytes, private absolute paths, tokens or personal data. The receipt is not proof of long-term artifact retention or model quality. No claim of a ready-to-use model is made until real local smoke and missing-asset failure are observed.

Issue #109 is **not complete** after inspection-only guidance. Its required user-testable outcome is a user starting without GLiNER2 or checkpoint, explicitly approving a pinned acquisition, preparing an isolated runtime and complete checkpoint, then verifying a local model smoke under denied network. Deliver these in order as bounded reviewable PR increments under the same open Issue: (1) offline preflight, (2) consented provisioning with safe failure/rollback, (3) verified local smoke and setup receipt. Do not mark the Issue review-ready or remove `in progress` while later required increments are outstanding. Advanced engine choices (Docker, ONNX, Ray or remote service) are not a substitute for the required local path; they remain optional only after this acceptance is met. No previously created consumer repository is rewritten by default.

## Alternatives Considered

- **Require users to supply preinstalled checkpoints indefinitely:** rejected because the owner has no such environment, and #100's prerequisite would be unusable without an onboarding path.
- **Install GLiNER2 or download a default model during ordinary bootstrap/inference:** rejected; it changes Python/runtime requirements, hides network and size/license decisions and contradicts ADR-011.
- **Add GLiNER2/PyTorch to core `pyproject.toml`:** rejected; the Python 3.8+ lightweight core must work with no optional ML runtime.
- **Bundle a checkpoint with the kb-bootstrap wheel:** rejected due to model size, licensing, update and platform costs.
- **Make Docker or a GLiNER HTTP service the only supported setup path:** rejected; the owner has no verified Docker engine or authorized service, and network inference is a separate trust-boundary decision under #108.

## Consequences

### What gets easier

- A user with no ML environment can discover requirements, approve a specific checkpoint acquisition, and reach a verifiable local setup without changing normal core workflows.
- Issue #100 can consume model path/digest evidence instead of silently downloading a mutable model.

### What gets harder

- Setup needs separate Python/runtime compatibility, checkpoint integrity, license, download and interrupted-setup tests.
- Consent and cache ownership introduce a bounded operational surface; model quality and network isolation remain independent claims.

### What does not change

- Core installation, `kb/raw/`, QMD, lessons, canonical validation/publication and ADR-011's local inference no-download rule are unchanged.
- Issue #108's remote endpoint remains a separate disabled-by-default proposal requiring its own superseding ADR and explicit consent.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Core Python >=3.8 commands run without `gliner2` and do not trigger setup | clean-core install/CLI subprocess fixture | not yet written |
| Offline inspection reports absent/incompatible environment and model without network or writes | missing-runtime/checkpoint fixture and network monitor | not yet written |
| Declined consent never starts acquisition or mutates destination | consent-denied fixture | not yet written |
| Explicit scoped consent pins source/revision, locked dependency artifacts and independently expected checkpoint digest | controlled acquisition and trust-source/mismatch fixtures | not yet written |
| Missing/ambiguous/click-through license metadata blocks until recorded owner acceptance | license gate fixture | not yet written |
| Interrupted setup never changes an existing Python environment or overwrites occupied/partial destinations, and cleans only owned staging | failure/restart/foreign-environment/staging fixture | not yet written |
| Local smoke succeeds on sanitized input and fails for missing assets while egress is denied | real-model, platform-scoped runtime verification | not yet run |
| Evidence contains no private paths, credentials or raw payload and names limitations | receipt and CLI presentation fixture | not yet written |
| Existing QMD, lessons, raw-manifest and bundle behavior remains unchanged | full regression suite | not yet run after implementation |

## Rollback

Revert the setup companion change. Any explicitly downloaded model is owner-managed, not automatically deleted on rollback; cleanup requires confirmation of its location and ownership. Issue #100's local-only inference rule and #108's separate remote decision remain intact.

## References

- GitHub issues #109, #100, #108
- ADR-010, ADR-011; `docs/EVIDENCE_RETENTION.md`
- GLiNER2 upstream README/pyproject (reported package requirements; actual local installation not yet verified)
