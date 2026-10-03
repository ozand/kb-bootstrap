# Tool-independent core and explicit capability evidence

**Status**: Proposed
**ADR number**: Unassigned
**Date**: 2026-09-28
**Related**: GitHub issues #121 and #122; ADR-003, ADR-006, ADR-009, ADR-014

## Context and scope

The product must support maintaining domain knowledge with ordinary Python and file
operations. QMD, Surf, GLiNER, GitHub, network access, and a particular agent runtime
are integrations, not prerequisites. This proposal records a decision for review; it
does not supersede an Accepted ADR, accept W09, define a persisted format, or authorize
runtime implementation.

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
| QMD | Both layouts generate declarations; missing declarations fail `validate` (`cli.py:480-523`, `qmd_validator.py`). Runtime registration/update remains separate per `VALIDATION_COMPOSITION.md`. | `search` is a stable operation and QMD can be one explicitly selected adapter. Declaration validity, selection, probe evidence, and operation authorization remain distinct. |
| Search | `search` directly uses QMD (`cli.py:137-149,311-315`). | Search reports its selected adapter and separate configuration, readiness-evidence, and authorization results. Core file reading remains available without search. |
| Collection/research | The packaged market-research skill requires Surf and describes QMD as optional. | `collect` is outside core; Surf can be one adapter, but no collector, browser, network, service, or model is selected implicitly. |
| Entity inference | `inspect-gliner` and checkpoint verification are explicit local commands (`cli.py:123-133,300-307`). | `entity-inference` is optional and GLiNER can be one adapter; no download, cloud fallback, or hidden inference occurs in core. |
| GitHub publication | `doctor` checks Git root, origin, `gh` default, and default branch (`repository_doctor.py`). | `remote-publication` is an operation and GitHub can be one adapter. Its existing doctor remains required for the GitHub path. |
| Bundle publication | ADR-009 requires an explicit output and exclusively creates a local ZIP. | Local artifact construction remains separate from remote publication and needs its own local-write authorization. |
| Layout | `single` and `umbrella` choose generated directory shapes (`cli.py:479-516`). | They are storage/layout choices only, never domain, sensitivity, tenancy, deployment, or capability presets. |

## Proposed decision

Define the **required core** as deterministic operations over explicitly bounded local
files: canonical read/edit guidance, canonical profile and provenance checks, graph
integrity, and local lesson validation when selected. It must remain usable offline and
must not invoke an optional executable, authenticate, access the network, register an
index, acquire a model, mutate a remote, or infer consumer policy.

Conversion, indexing, extraction, synthesis, viewing, collection, and inference can form
a broader **local-processing workflow** when they use explicitly selected local adapters;
naming them “local” does not make them part of the required core or grant permission to
read, execute, write, acquire a model, or use the network. Remote publication is not a
local-processing workflow merely because its client runs locally.

### Stable operations and adapter identity

Configuration identifies a stable operation such as `search`, `collect`,
`entity-inference`, or `remote-publication` separately from an adapter identity such as
QMD, Surf, GLiNER, or GitHub. Alternative adapters and consumer-owned names are allowed
as data identifiers, subject to an accepted extension contract. An unknown identifier
is never an executable name, import path, command template, discovery request, or
permission to load arbitrary plugin code. The required core never dispatches optional
adapters. A separately invoked integration/orchestration layer may dispatch only adapters
implemented and registered by reviewed code; an unsupported selection is reported as
invalid configuration without execution.

The exact public operation vocabulary, adapter namespace, registration mechanism,
versioning rules, and schema are still **proposals requiring owner review**. This
document does not choose a generic plugin protocol or a closed vendor inventory.

Counterexample: a consumer selecting `search` with adapter ID `acme-index` must not be
rejected merely because it is not QMD, but the string `acme-index` also must not cause
`acme-index`, a Python entry point, or downloaded code to execute. It remains unsupported
until reviewed product or consumer integration code binds that ID to an adapter.

### Independent configuration, observation, and authorization results

Each operation report preserves independent fields rather than collapsing them into one
capability state:

| Dimension | Result | Meaning |
|---|---|---|
| Configuration | `NOT CONFIGURED` | No adapter choice exists; core continues and a requiring operation is unmet. |
| Configuration | `DISABLED` | The owner explicitly recorded a refusal to use this operation/adapter. No probe or fallback runs. |
| Configuration | `CONFIGURED` | A syntactically valid adapter choice exists. This says nothing about readiness or permission. |
| Technical observation | `NOT RUN` | No authorized probe evidence was obtained. This is not failure or availability. |
| Technical observation | `AVAILABLE` | An authorized, scoped probe observed readiness for its declared scope and time. |
| Technical observation | `BROKEN` | An authorized probe ran and observed a technical/configuration failure. |
| Operation authorization | `NOT EVALUATED` | Applicable policy/authority was not evaluated. |
| Operation authorization | `ALLOWED` | The named operation, data, effects, and scope were authorized. |
| Operation authorization | `POLICY DENIED` | Policy forbids this operation/scope; configuration and technical observation are retained unchanged. |

`DISABLED` is only an explicit owner refusal. No choice remains `NOT CONFIGURED`.
Invalid configuration is reported as a configuration error, not `BROKEN`; `BROKEN`
requires an actually run probe. A policy denial is operation-level and neither disables
nor breaks the adapter. Exact policy-result naming and aggregation remain a W01/W09
decision requiring owner approval; `POLICY DENIED` is proposed here to preserve the
distinction.

Counterexamples:

- pressing Enter at an initializer without choosing search yields `NOT CONFIGURED`, not
  a fabricated `DISABLED`; only an explicit “do not use search” choice yields `DISABLED`;
- a configured GitHub adapter with no authorized network probe is `CONFIGURED` plus
  `NOT RUN`, not `BROKEN`; a separately authorized probe that receives a technical error
  may produce `BROKEN`;
- an available local inference adapter denied access to sensitive input stays
  `AVAILABLE`, while that inference request reports `POLICY DENIED`; it is not globally
  `DISABLED` and is not technically `BROKEN`.

### Probe authorization and offline behavior

Configuration, operation selection, and adapter enablement do not authorize a probe.
Pure file-only, side-effect-free inspection may run where the caller explicitly selected
that inspection. Any probe that starts a runtime or executable, loads model bytes, reads
credentials, contacts a service, or uses a network requires a separate authorization
whose scope identifies those effects. Without it, observation is `NOT RUN` (or the probe
operation is `POLICY DENIED` if policy was evaluated), never `BROKEN`.

Core validation does not probe adapters and works with network denied, credentials and
models absent, and optional binaries removed from `PATH`.

Counterexample: checking that a configured model path string is contained beneath an
authorized root may be passive inspection; importing the model runtime or opening model
weights is an active probe and cannot occur under that inspection permission.

### Gate and ownership separation

1. **Required core checks** — owned by kb-bootstrap; file-only and runnable offline.
2. **Consumer policy** — owned and versioned by the consumer; separately evaluated and
   reported. Capability configuration grants no data access, acquisition, disclosure,
   retention, network, or publication permission.
3. **Optional adapter evidence** — configuration and separately authorized observations;
   QMD declarations remain separate from registration, update, search, and freshness.
4. **Local artifact creation** — explicit exports such as ADR-009, preserving their
   existing fail-closed path, source, and exclusive-output rules plus local-write authority.
5. **Remote publication** — a separate explicit operation whose GitHub adapter still
   requires repository doctor and applicable consumer authorization.

An outbound-publication denial does not deny a separately authorized local export. A
trusted operator-selected external input/output root is eligible only when the accepted
contract of that specific operation permits it; this does not broaden existing exports.
In particular, ADR-009 output remains relative to and contained by its explicit project
root. An eligible root choice is not untrusted document metadata and grants no path
outside that bounded root. Absolute or traversal paths found inside documents cannot
select new roots or destinations.

Counterexamples:

- policy denying upload of a bundle leaves an independently authorized local ADR-009 ZIP
  possible; local ZIP success still makes no claim that upload is allowed or succeeded;
- `/mnt/approved-corpus` may be a bounded root only for an operation whose own accepted
  contract allows external roots; it is not a valid ADR-009 output root, and metadata
  containing `output: /tmp/leak` cannot authorize or redirect a write;
- recorded provenance for a remote corpus does not authorize fetching it: provenance
  describes origin, while acquisition needs a separate allowed operation.

Reports retain all gate labels and use `NOT RUN` where no evidence was obtained. They do
not silently run a later gate or collapse independent results into a single green result.

## Compatibility and migration

Accepted behavior remains binding until a later implementation decision is accepted.
Existing repositories remain in **legacy mode**: current `validate` still requires
generated QMD declarations, and current initialization, doctor, export, search,
collection, layouts, and skill contracts keep their behavior. This proposal changes no
default, template, file, CLI, adapter, or accepted ADR.

A possible future migration is inspect-first and no-overwrite. Existing QMD files could
suggest `search`/QMD as a proposed selection, but never imply `AVAILABLE`, permission to
probe, or permission to search. Ambiguous state blocks migration. Migration must not
rewrite content, change layout, register/update QMD, install software, acquire a model,
authenticate, use the network, or change Git/remotes.

Fresh initialization without a choice leaves an operation absent and therefore
`NOT CONFIGURED`. It records `DISABLED` only after explicit owner confirmation.

Counterexample: an old repository with valid `qmd.json` continues to pass or fail the
existing `validate` exactly as before; merely opening it under a future tool neither
writes a capabilities file nor probes QMD.

## Sequencing and acceptance

No persisted declaration or parser is authorized by this proposal. A first bounded
implementation proposal may expose a non-persistent characterization/report interface
and a core-only validation entry point without changing legacy commands. A persisted
file may be proposed only after separate acceptance of its schema, state semantics,
extension/namespace contract, compatibility policy, and exact generation/migration
behavior. Runtime implementation remains out of scope here.

Counterexample: hard-coding a provisional `kb-capabilities.json` parser now would turn
today's illustrative adapter names into a compatibility obligation before `acme-index`
namespacing and policy aggregation have been decided.

Acceptance cases for a later implementation proposal include:

- a minimal canonical KB passes core validation with optional binaries absent, no
  credentials/models, and network denied;
- no choice and explicit owner refusal report `NOT CONFIGURED` and `DISABLED`
  respectively, without probes;
- configured QMD with no probe permission reports `CONFIGURED`/`NOT RUN`; only an
  authorized failed probe reports `BROKEN`;
- policy denial preserves configuration and technical observation and separately reports
  the denied operation;
- an AVAILABLE QMD probe does not claim index freshness until explicit update and smoke
  evidence exists;
- adapter IDs cannot cause arbitrary command, import, discovery, download, or execution;
- disabled GLiNER/Surf never downloads, launches, probes, or falls back to a service;
- local export and remote publication retain independent authorization and evidence;
- trusted explicit roots remain bounded, and paths in content cannot expand authority;
- provenance alone never authorizes acquisition;
- legacy fixtures retain current outputs and behavior byte-for-byte for both layouts.

## W09 boundary and decisions still requiring approval

W09 at its immutable published proposal revision is context, not a dependency. Its broad
“local core” activities are treated here as a local-processing workflow, not additions
to the required deterministic core. Its outbound-publication and path rules require the
local-artifact and trusted-root distinctions above. W01 does not modify W09 or require
its unfinished follow-up.

For the first additive core-only validation slice, review the separate
[Proposed ADR-015](../adr/ADR-015-add-core-only-validation-without-changing-legacy-validate.md).
That slice needs only the local-check boundary and compatible CLI contract; it does
not depend on this wider proposal's capability vocabulary, adapter namespace,
authorization aggregation or persisted schema. Those remain separate decisions
requiring approval before their own implementation. Consumer policy remains consumer-owned and versioned;
no universal policy engine is introduced.

## Alternatives (not accepted defaults)

The following remain proposals for explicit review, not silently accepted defaults:

- keep QMD in universal validation;
- treat missing or broken optional tools as skipped success;
- auto-detect adapters or install/fetch fallbacks;
- use a closed product-vendor inventory;
- define a generic executable/plugin discovery protocol;
- persist a versioned declaration after its schema and extension contract are accepted;
- begin with only a non-persistent report and core-only command.

Their trade-offs include compatibility, evidence quality, portability, migration cost,
and execution/trust surface. Choosing among them requires an explicit later decision.

## Consequences and rollback

The proposed separation makes core maintenance portable and prevents configuration,
technical evidence, and authority from borrowing one another's success. It adds a more
precise reporting vocabulary and leaves schema/extension choices unresolved. Because
this revision changes documentation only, rollback is removal or further revision of
this proposal; legacy behavior and consumer files remain unchanged. This document can
be accepted, revised, or rejected only through owner-reviewed decision process; it
assigns no ADR number and does not self-approve.
