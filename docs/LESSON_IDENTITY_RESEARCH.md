# Lesson identity research: local IDs versus global IDs

## Decision summary

Keep the existing scope-local identifiers:

- project lesson: `PROJECT-XXXX` within its owning repository;
- shared lesson: `KB-XXXX` within its owning shared registry.

Treat identity across repositories as the tuple:

```text
(scope, owner repository, lesson ID)
```

Use existing provenance (`source_repository`, `observed_in`, and `promoted_from`) to trace movement and reuse. Do not add UUIDs, ULIDs, a distributed allocator, or migrate existing IDs now.

## Evidence base and limitations

This recommendation is based on the current `kb-bootstrap` contracts for local and shared registries, federated lookup, offline cache/export, and reviewed promotion. No confirmed sanitized incident has been identified where a validated `(scope, owner repository, lesson ID)` tuple was retained at the relevant boundary but still referred to more than one lesson.

Current implementation provides only partial provenance. Federated lookup reports the explicitly configured store name, store type, and lesson ID; its store format does not require or validate an authoritative owner repository or scope. The offline cache validates and copies a top-level `source_repository`, registry version, lesson version, and lesson ID, but does not carry or validate the lesson scope or bind the owner to a registry identity. The shared metadata validator can validate scope and provenance as a separate object, but lookup and cache do not consume that object. Therefore no current lookup/cache result alone proves the complete `(scope, owner repository, lesson ID)` tuple.

No external system comparison is used as evidence for this decision. The recommendation is based on the repository's current schemas, validators, lookup/cache behavior, and the bounded alternatives analysis below.

This is a bounded design decision, not a statistical proof that collisions can never occur. Missing or unvalidated owner or scope metadata remains an insufficient interchange boundary and must fail closed rather than be repaired by guessing.

## Current identity model

A local ID is unique inside one explicitly owned store. It becomes globally unambiguous when combined with its owner:

```text
project:example/application:PROJECT-0042
workspace:example/shared-lessons:KB-0123
```

The serialized form above is an explanatory reference, not a replacement ID stored in filenames or frontmatter.

The intended cross-repository identity is the tuple above, but current runtime formats implement only parts of it. Federated lookup returns configured store name/type plus the local lesson ID, which is useful provenance only when the configuration is trusted externally. The cache retains `source_repository` and version/freshness metadata, but not a validated scope or registry-owner binding. The separate shared metadata and promotion contracts define the missing scope/provenance fields; wiring those fields into lookup/cache is a future implementation and is outside this research issue. Until then, consumers must treat missing or unvalidated scope/owner data as insufficient for identity merging and must not merge by lesson ID alone.

## Alternatives

| Alternative | Collision risk | Traceability | Migration cost | Compatibility | Coordination cost |
|---|---|---|---|---|---|
| Local IDs + explicit owner/provenance | Low when the owner tuple is retained; ambiguous only if provenance is discarded | Strong: human-readable owner and source relationship | None | Fully compatible with current files, indexes, lookup, cache, and promotion | Low; allocation remains local |
| Namespaced stored ID such as `owner/repo:PROJECT-0042` | Low | Strong | High: filenames, frontmatter, indexes, links, and tools must change | Breaks current ID patterns and portability when repositories move/rename | Medium |
| UUID | Very low | Weak without separate provenance; identifier itself is opaque | High: migration and dual-ID compatibility required | Broad library support, but poor fit for human-edited filenames and receipts | Low allocation coordination, high migration burden |
| ULID | Very low | Weak without provenance; time ordering can reveal creation timing | High | Similar migration burden to UUID; longer filenames and references | Low allocation coordination, high migration burden |
| Central/distributed numeric allocator | Low only while the service is available and authoritative | Medium; still needs provenance | Very high | Introduces an online dependency into offline/local workflows | High; service, authorization, availability, and reconciliation required |

## Collision analysis

`PROJECT-0001` can legitimately exist in many repositories. This is not a collision when references include the owning repository and scope. It becomes ambiguous only when an export or federated result drops owner provenance.

`KB-0001` can also exist in separate shared registries. The same rule applies: shared lesson references must retain the registry owner.

Therefore the current risk is primarily a **provenance-loss problem**, not an ID-generation problem. Replacing local IDs with UUID/ULID does not remove the need for source, scope, applicability, and promotion provenance.

## Interoperability, federation, and export evaluation

### Federated lookup

Current federated lookup is not sufficient by itself to establish a globally unambiguous identity. It returns:

- configured store name and type;
- local lesson ID.

The store schema does not require an owner repository or scope. The configured store name must therefore be treated as a non-authoritative routing/provenance label, not as proof of registry ownership. A consumer must not merge results by lesson ID alone; an owner/scope-bearing metadata record or equivalent trusted boundary is required.

### Offline export/cache

Current cache behavior provides partial provenance: entries retain `source_repository`, `registry_version`, `lesson_version`, lesson ID, and freshness. It does not retain or validate a `scope` field or prove that `source_repository` is the authoritative owner of the `KB-XXXX` registry. Therefore the cache is sufficient for the current bounded read-only copy workflow, but not by itself for a global identity claim. An export intended for identity merging must carry and validate scope, owner, and lesson ID together; otherwise it is insufficient and must fail closed at that boundary.

### External interchange

This is a required-format design assessment, not a claim that the current lookup/cache serializers already emit the full tuple. JSON, YAML, Markdown frontmatter, cache bundles, and lookup receipts can carry scope, repository owner, and local ID as separate fields, but identity-safe interchange requires an explicit scope-bearing owner field in addition to the local ID. A format that only accepts one opaque identifier would require an explicit adapter or immutable alias; it would not justify rewriting filenames, frontmatter, and indexes before that requirement exists.

Repository renames or transfers may change the owner component. This can be handled with an explicit bounded alias mapping at the interchange boundary while preserving the lesson's local ID. Silent inference from a current remote or filesystem path remains unsafe.

### Promotion

Sufficient with the current model because a promoted shared lesson receives its destination-owned `KB-XXXX` and records the source tuple through:

```yaml
promoted_from:
  repository: example/application
  lesson_id: PROJECT-0042
```

Promotion is a new reviewed lesson in a different scope, not an identity-preserving move that requires the same global ID.

## Compatibility and migration cost

Changing identifiers would require coordinated updates to:

- lesson filenames and frontmatter;
- registry indexes and count/identity validation;
- Markdown references and receipts;
- generated skills and examples;
- cached exports and federated lookup fixtures;
- existing consumer repositories.

A compatibility period would likely require two IDs per lesson and reconciliation rules. No confirmed collision incident currently justifies this cost.

## Go/no-go threshold

Reopen the decision and consider adding a global immutable identifier only if at least one of these measurable conditions is met:

1. Two confirmed, sanitized incidents within 12 months where a validated scope, owner repository, and local ID were all present at the relevant interchange boundary but still could not identify the intended lesson.
2. A required external interchange format cannot carry owner repository, scope, and local ID together.
3. A repository rename/move requirement demonstrates that owner-based aliases cannot preserve references with a bounded mapping table.
4. More than two independent authoritative shared registries must merge lessons automatically and a fixture proves validated provenance tuples cannot resolve identity safely.

Even when a threshold is met, the first option should be an additional immutable alias field while preserving current human-readable IDs. A distributed allocator remains out of scope unless offline allocation itself is proven insufficient.

## Recommendation

**No-go for global ID implementation now.**

Continue using local IDs plus mandatory owner/scope/provenance. Strengthen validation at interchange boundaries rather than replacing identifiers. This is the simplest compatible design and preserves repository ownership and offline operation.

## Non-actions

This research does not:

- change `PROJECT-XXXX` or `KB-XXXX`;
- add an ID field;
- allocate IDs;
- migrate lessons or indexes;
- write to consumer repositories or shared stores;
- introduce a service or cross-repository transaction.
