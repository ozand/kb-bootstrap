# Tool-independent core and explicit capability states

**Status**: Proposed
**ADR number**: Unassigned
**Date**: 2026-09-28
**Related**: GitHub issues #121 and #122; ADR-003, ADR-006, ADR-009, ADR-014

## Context

The product must support maintaining domain knowledge with ordinary Python and file
operations. QMD, Surf, GLiNER, GitHub, network access, and a particular agent runtime
are integrations, not prerequisites. This proposal records a decision for review; it
does not supersede an Accepted ADR or authorize implementation.

Current behavior is coupled in several observable places. `kb_bootstrap/cli.py` makes
QMD declaration validation part of `validate`, initializes `qmd.json` and two QMD
collections for both layouts, and installs QMD- and Surf-oriented skills. The QMD
validator checks declarations and paths, not the QMD executable or index. Repository
doctor separately invokes Git and `gh` and fails closed when publication identity
cannot be established. `docs/VALIDATION_COMPOSITION.md` already separates universal
conformance, consumer policy, and retrieval/index freshness. ADR-009 keeps publication
as an explicit local export and excludes network distribution; ADR-014 makes local
inference optional and forbids implicit model acquisition.

### Observed and proposed behavior

| Concern | Current, source-grounded behavior | Proposed behavior |
|---|---|---|
| Canonical files | `validate` runs profile, provenance, graph, then QMD declarations (`cli.py:259-277`). | A core validation entry point runs only local canonical structure, metadata, provenance, and graph checks. |
| QMD | Both layouts generate declarations; missing declarations fail `validate` (`cli.py:480-523`, `qmd_validator.py`). Runtime registration/update remains separate per `VALIDATION_COMPOSITION.md`. | QMD is a named optional capability. Declaration validity and runtime readiness are distinct results and never implied by core PASS. |
| Search | `search` directly uses QMD (`cli.py:137-149,311-315`). | Search reports the selected capability state; disabled/not-configured is unavailable, while configured/broken is an error. Core file reading remains available. |
| Collection/research | The packaged market-research skill requires Surf and describes QMD as optional. | Collection is outside core; enabled guidance may name Surf, but no collector, browser, network, service, or model is selected implicitly. |
| Entity inference | `inspect-gliner` and checkpoint verification are explicit local commands (`cli.py:123-133,300-307`). | GLiNER remains opt-in; no download, cloud fallback, or hidden inference occurs in any core operation. |
| GitHub publication | `doctor` checks Git root, origin, `gh` default, and default branch (`repository_doctor.py`). | Publication preflight remains a separate required gate whenever a workflow publishes to GitHub; local work does not call or bypass it. |
| Bundle publication | ADR-009 requires an explicit output and exclusively creates a local ZIP. | Local bundle construction remains separate from remote publication; success makes no claim about upload, policy, or retrieval. |
| Layout | `single` and `umbrella` choose generated directory shapes (`cli.py:479-516`). | They are storage/layout choices only, never domain, sensitivity, tenancy, deployment, or capability presets. |

## Proposed decision

Define the **core** as local, deterministic operations over explicitly bounded files:
canonical read/edit guidance, canonical profile and provenance checks, graph integrity,
local lesson validation when selected, and explicit local exports. Core operations
must not invoke an optional executable, authenticate, access the network, register an
index, acquire a model, mutate a remote, or infer consumer policy.

Use a small, versioned project declaration (provisionally `kb-capabilities.json`) with
a closed set of product capabilities: `qmd`, `surf`, `gliner`, and `github-publication`.
This is configuration for known integrations, not a generic plugin/executable protocol.
Unknown keys fail declaration validation rather than being executed. Exact file schema
and CLI spelling remain implementation-review details, but every known capability has
one of these externally reportable states:

| State | Meaning | Required outcome |
|---|---|---|
| **not configured** | No explicit selection exists. | Report `NOT CONFIGURED`; core continues. A consumer gate requiring it fails as unmet. |
| **explicitly disabled** | The owner recorded that it must not be used. | Report `DISABLED`; do not probe, install, prompt, access network, or fall back. A requiring gate fails as unmet. |
| **configured / available** | Configuration is valid and the bounded readiness probe succeeds. | Report `AVAILABLE`; use only after the caller explicitly selects the capability operation. |
| **configured / broken** | It was selected, but configuration, executable, credentials, model bytes, or probe fails. | Report `BROKEN` with a bounded remediation category and fail that capability/consumer gate; never skip or downgrade to absence. |

“Optional” describes whether core requires a capability, not whether failure can be
called success. Reports must retain each state. A consumer-defined workflow may require
one or more capabilities and combine their outcomes, but must name its policy owner and
version and must not relabel a core result. No upstream universal profile engine is
introduced.

### Gate and ownership separation

1. **Core local checks** — owned by kb-bootstrap; file-only and runnable offline.
2. **Consumer policy** — owned and versioned by the consumer; separately invoked and
   reported. No access or retention default is inferred.
3. **Optional capability readiness** — one result per explicitly selected integration;
   QMD declaration validation remains separate from registration/update/search evidence.
4. **Local publication artifact** — explicit exports such as ADR-009, with their existing
   fail-closed path, source, and exclusive-output rules.
5. **Remote publication** — an explicit workflow whose GitHub path still requires the
   existing repository doctor and any consumer authorization checks. Local success cannot
   satisfy this gate.

The command/report composition must preserve these labels and must use `NOT RUN` where
no evidence was obtained. It must not silently run a later gate or collapse it into a
single green result.

## Compatibility and migration

Accepted behavior remains binding until an implementation ADR/change is accepted.
Therefore existing repositories without the new declaration stay in **legacy mode**:
the current `validate` command still requires generated QMD declarations, and existing
doctor, export, search, collection, and skill contracts keep their behavior.

Migration is explicit and inspect-first. A future migration command may produce a plan
from existing declarations, but must not infer runtime availability. An owner confirms
the known capability states before one exclusive, no-overwrite declaration write.
Existing QMD files imply only proposed `qmd: configured`, never AVAILABLE. Partial or
ambiguous state blocks. Migration does not rewrite collections or content, change the
layout, register/update QMD, install an executable, acquire a model, authenticate, or
change Git/remotes. Rollout documentation must show old and new commands side by side.

Fresh initialization may offer explicit capability selection and otherwise emit all
optional capabilities as disabled (not silently configured). It may omit integration
files and skills for disabled capabilities. `single`/`umbrella` selection is orthogonal.

## First implementation and acceptance

The first bounded implementation should add only the declaration parser/report and a
new core-only validation command; it should not change `validate` defaults, generated
templates, search backends, or publication behavior. A later reviewed increment may
change initialization and migration after compatibility fixtures establish exact bytes.

Synthetic acceptance cases:

- a minimal canonical KB passes core validation with PATH stripped of optional binaries,
  no credentials/models, and network denied;
- no declaration and explicit-disabled each produce their distinct state without probes;
- configured QMD with a missing binary, invalid declaration, or failed readiness probe is
  BROKEN and fails a QMD-required consumer gate, while core results remain independently
  reported;
- an available QMD probe does not claim index freshness until explicit update and smoke
  evidence exists;
- disabled GLiNER/Surf never downloads, launches, or falls back to a service;
- local bundle export neither runs repository doctor nor claims remote publication, while
  a GitHub publication workflow still blocks when doctor fails;
- legacy fixtures retain current `validate`, initialization, doctor, export, and search
  behavior byte-for-byte; both layouts pass the same core cases;
- every report distinguishes PASS, FAIL/BROKEN, NOT CONFIGURED, DISABLED, and NOT RUN.

## W09 assumptions to reconcile before acceptance

W09 is independently defining data policy. This proposal assumes only that policy is
consumer-owned and explicitly versioned, and that capability enablement grants no data
access, disclosure, retention, network, or publication permission. Reconcile who may
enable a capability, which data classes it may read/send, required evidence/retention,
and whether policy denial maps to DISABLED or a separately labelled blocked operation.
Do not accept this decision by importing or depending on W09's unfinished output.

## Alternatives

- **Keep QMD in universal validation:** rejected because local maintenance would still
  require integration configuration.
- **Treat missing/broken tools as skipped success:** rejected because it hides required
  consumer failures and destroys evidence.
- **Auto-detect capabilities or install fallbacks:** rejected because results become
  environment-dependent and may trigger network/model/software side effects.
- **Build a generic plugin framework:** rejected; the bounded known-capability declaration
  is sufficient and has a smaller execution/trust surface.

## Consequences and rollback

Core maintenance becomes portable and gate reports become more truthful, at the cost of
an additional declaration/state vocabulary and a deliberate migration. Integrations
remain useful but cannot borrow core PASS. If implementation proves incompatible, remove
the new parser/core command and declaration from fresh generation; legacy behavior and
consumer files remain unchanged. This Proposed document can be revised or rejected only
through independent review; it assigns no ADR number and does not self-approve.
