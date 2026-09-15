# Repository-owned canonical profile overlay research

## Status

Research-only recommendation. No validator, profile format, migration, repair, or consumer mutation is implemented by this document.

Source: sanitized live-consumer audit of `ozand/projectmanagment-kb`, 2026-09-15.

## Question

Should `kb-bootstrap` add a generic profile overlay that lets a repository require local frontmatter fields, enums, identifiers, and canonical layers beyond the minimal OKF v0.2 profile?

## Existing upstream boundary

The `kb-bootstrap` canonical profile remains deliberately minimal and consumer-independent:

- ordinary canonical concepts require a non-empty `type`;
- recommended common fields are checked when present;
- unknown metadata and unknown concept types are accepted without rewriting source;
- `raw/`, `lessons/`, and reserved `index.md` / `log.md` files are excluded;
- stricter graph integrity and provenance/freshness are separate report sections;
- validation is read-only, deterministic, static-symlink-aware, and assumes a stable checkout.

This boundary must not gain consumer-specific IDs, vocabularies, directory names, or review workflows.

## Audited consumer need

The audited repository has a real stricter local model. The audit established the following sanitized policy categories without copying document content or consumer enum values:

| Audited category | Sanitized observation | Ownership implication |
|---|---|---|
| Required fields | Every canonical record requires local identity/title, taxonomy, evidence, lifecycle, date, tag, and environment fields in addition to the upstream `type` requirement. Some fields are conditional on document kind or time sensitivity. | The consumer decides which fields are required and when conditional fields apply. |
| Enum constraints | Local domain, knowledge-kind, lifecycle, and evidence fields use closed repository vocabularies. | Exact values and lifecycle mappings remain consumer policy; they do not extend OKF enums. |
| ID pattern | Canonical records use one anchored repository prefix followed by a fixed-width decimal sequence, with uniqueness and no-reuse expectations. | Prefix, width, allocation, uniqueness, and no-reuse rules remain repository-owned. |
| Canonical layers | Canonical records are divided into named method, practical-play, reusable-artifact, research, learning, and AI/agent areas under the canonical root. | Layer names and permitted document kinds remain consumer-owned placement policy. |
| Excluded layers | Raw captures are a separate source layer; project lessons are a separate optional contract rather than canonical concepts. | Raw and lesson validation must not be inferred from canonical overlay validation. |
| Adjacent integrity | The consumer also requires source disposition, raw hashes, citation ownership, review policy, and ID-based links. | These are separate validators/workflows, not evidence for a general canonical profile rule engine. |

The observed corpus used its local fields consistently enough to demonstrate an enforcement need, while the current upstream validator intentionally cannot prove those fields, vocabularies, identifiers, or layers. These requirements demonstrate the need for local policy enforcement. They do not demonstrate that the exact policy is portable to other consumers.

## Responsibility boundary

### Universal `kb-bootstrap` validation

Owns only reusable format and safety rules:

- minimal canonical OKF profile;
- bounded optional provenance/freshness profile;
- standard supported link integrity/export;
- canonical/raw/lesson exclusion boundaries;
- deterministic read-only reporting and path safety.

### Consumer-owned strict validation

Owns repository policy:

- additional required fields;
- local enum vocabularies;
- local ID field, pattern, uniqueness, and no-reuse policy;
- consumer content layers and placement rules;
- local editorial/review states;
- domain-specific evidence rules;
- repository-specific source-accounting ledgers.

A consumer may expose one local validation command that composes several labelled checks, but the canonical profile overlay itself should validate record shape and placement only. Cross-file ID-link syntax/target resolution is a separate consumer graph-integrity check and must not be silently implied by an overlay pass.

A consumer validator should run after the universal validator and label its results separately. A universal pass does not prove the local policy, and a local policy failure does not redefine OKF conformance.

### Separate concerns

A canonical overlay must not absorb:

- raw-capture schema validation;
- raw-file hash or citation-ownership checks;
- QMD registration, update, retrieval, or freshness;
- syntax, target resolution, or graph export for non-standard ID links unless separately governed;
- migration, repair, normalization, or source rewriting;
- ID allocation or automatic status promotion;
- network retrieval or cross-repository synchronization.

## Alternatives

### Alternative A — Consumer-owned executable validator

The consumer documents its profile and owns a small deterministic executable validator or wrapper.

| Attribute | Assessment |
|---|---|
| Compatibility | Strong: upstream minimal semantics remain unchanged. |
| Maintenance | Local duplication is possible, but ownership is explicit. |
| Discoverability | Requires a clear command in consumer `AGENTS.md` and README. |
| Failure safety | Strong: the consumer can fail closed on its exact policy. |
| Trust surface | Small: no upstream loading or execution of consumer policy. |

This is the recommended current approach.

### Alternative B — Declarative consumer profile interpreted by `kb-bootstrap`

The consumer supplies an explicit data-only profile to a generic upstream engine.

| Attribute | Assessment |
|---|---|
| Compatibility | Feasible only as explicit opt-in; malformed/unknown versions must block. |
| Maintenance | Shared mechanics could reduce duplication across several consumers. |
| Discoverability | Strong if invoked through one documented CLI option. |
| Failure safety | Requires a bounded schema, path containment, parser limits, deterministic errors, and safe pattern semantics. |
| Trust surface | Materially larger: persisted public profile schema, versioning, parsing, regex/pattern, path, and compatibility contracts. |

This is not justified by one consumer. Implementing it would require a new Issue, Proposed ADR, separate owner approval, fixtures from more than one consumer or measured duplication pain, and a clearly bounded profile schema.

If later justified, the smallest acceptable design would use an explicit repository-relative profile path only; no discovery, parent search, URL, include, import, hook, plugin, expression, subprocess, or network behavior. It would be data-only, versioned, read-only, duplicate-key rejecting, bounded in size/depth/count, source preserving, deterministic, and fail closed on unsafe paths, overlaps, unsupported policy keys, or unknown versions. Arbitrary regular expressions and a generalized rule engine should be avoided.

### Alternative C — Documentation-only policy

The consumer records required fields and vocabularies in human-readable documentation.

| Attribute | Assessment |
|---|---|
| Compatibility | Strong and non-invasive. |
| Maintenance | Low implementation cost. |
| Discoverability | Depends on agents and humans reading the document. |
| Failure safety | Weak: required fields and enums are not mechanically enforced. |
| Trust surface | Minimal. |

Documentation remains the normative explanation, but it is insufficient as the only enforcement mechanism where a repository calls fields required.

### Alternative D — Executable plugins or a general rule engine

Rejected. Loading consumer code or supporting arbitrary predicates, hooks, expressions, and cross-file rules would introduce unnecessary execution, supply-chain, compatibility, and security complexity.

## Recommendation

### Current decision

**Do not add a generic profile-overlay implementation to `kb-bootstrap` from the evidence currently available.**

The audited repository should own a small strict validator or wrapper, invoked explicitly after the universal `kb-bootstrap` validation. It can enforce its local fields, enums, IDs, layers, and review policy without changing upstream semantics.

This recommendation preserves product simplicity:

- one universal minimal validator;
- one explicit consumer validator where needed;
- no hidden discovery;
- no upstream consumer vocabulary;
- no plugin or rule engine;
- no automatic migration or repair.

### Reconsideration threshold

Open a later upstream implementation Issue only when at least one condition is observed and documented:

1. two independent consumer repositories have materially similar overlay requirements and duplicate the same validation mechanics; or
2. consumer-owned validator duplication causes a measured maintenance, compatibility, or adoption incident; or
3. after corrected consumer documentation and one explicit local validation command are released, at least two dated, independently reproducible workflow incidents show that operators or agents omitted/mis-composed the universal and local checks; each incident must record the expected command, observed command/output, impact, and corrective action.

The later evidence must include sanitized fixtures from the participating consumers, stable required fields/enums/layer rules, a named owner for each policy, compatibility observations, and proof that a small declarative mechanism solves the problem without consumer-specific leakage. Any such public profile-format implementation requires a Proposed ADR and separate owner approval before code changes because it adds a persisted validation contract and trust boundary.

## Evidence gaps

Before any upstream implementation:

- only one consumer has been audited;
- no second independent consumer demand is recorded;
- no measured duplication/maintenance incident exists;
- the audited consumer has active moving work and no pinned clean migration baseline for this purpose;
- its exact local validator is not yet a single complete executable contract;
- no dated post-documentation composition/discoverability incidents meeting the threshold above are recorded;
- conditional fields and local lifecycle mapping still require consumer decisions;
- raw validation, source hashes, ID links, QMD, and repair are separate unresolved workstreams.

These gaps block a credible upstream API/profile commitment, not the consumer's ability to create its own validator.

## Go/no-go matrix

| Proposed next action | Verdict | Reason |
|---|---|---|
| Consumer documents and implements a local strict validator | Go, under a consumer-owned Issue and its governance | Exact local policy and ownership stay local. |
| `kb-bootstrap` documents how to compose a local validator after core validation | Potential small future documentation increment if requested | No new profile format is required. |
| `kb-bootstrap validate --profile ...` implementation | No-go now | One consumer and no measured duplication pain are insufficient. |
| Auto-discovered repository profile | No-go | Hidden ownership and precedence ambiguity. |
| Plugin/hook/rule-engine validation | No-go | Overengineering and code-execution risk. |
| Automatic metadata migration or repair | No-go | Separate owner-authorized mutation boundary. |

## Verification of this research

This artifact is complete when reviewers can confirm that it:

- distinguishes universal and consumer-owned validation;
- covers required fields, enums, ID patterns, and content-layer boundaries;
- compares at least two alternatives across compatibility, maintenance, discoverability, and failure safety;
- gives a clear current recommendation and measurable reconsideration threshold;
- separates canonical overlay work from raw/hash/link/QMD/repair concerns;
- contains no implementation, migration, normalization, or consumer rewrite;
- contains only sanitized examples and no private consumer payloads.

## References

- `docs/OKF_V0_2_CANONICAL_PROFILE.md`
- `docs/CANONICAL_PROVENANCE_FRESHNESS_PROFILE.md`
- ADR-003 — minimal OKF v0.2 canonical profile
- ADR-005 — versioned deterministic canonical graph JSON export
- ADR-006 — explicit-time canonical provenance/freshness validation
- GitHub Issue #78
