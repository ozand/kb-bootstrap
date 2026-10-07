# W03 synthetic source and capture examples

**Status:** Illustrative data-only fixtures for ADR-023 and proposed ADR-024. All
origins, bytes, identifiers, timestamps, permission labels, and converter names
below are synthetic. Nothing is fetched or authorized.

## Literal byte fixtures

Each non-empty fenced payload below denotes exactly its UTF-8 content between the
fence lines, including the single LF after the visible text. Digests were computed
over those literal bytes, not over the Markdown fences or labels.

`shared.txt` (also used by two distinct origins):

```text
alpha
```

- bytes: `6`
- SHA-256: `b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060`

`partial.txt`:

```text
second paragraph
```

- bytes: `17`
- SHA-256: `82641ee88dd2e26449f7ca30f9ecafeac2ceaa73f5834fa17a1dd588a12872ef`

`summary.md`:

```markdown
Operator summary.
```

- bytes: `18`
- SHA-256: `2857c000e63dab3596026f2c317dedad64ca30163fe2b59d4466253ec4908c18`

`original-v2.txt`:

```text
alpha revised
```

- bytes: `14`
- SHA-256: `b3333cb058cf3b012832d31854e01497f684412e573690b33ff44391182e73aa`

`conversion-v2.txt`:

```text
ALPHA
```

- bytes: `6`
- SHA-256: `1921b918b15842c7fdb115078e610263fac85f159c1d8e0ecec3d89a0faa4005`

`empty.txt` is an empty UTF-8 text representation containing zero bytes (there is deliberately no payload fence whose
Markdown newline could be mistaken for content):

- bytes: `0`
- SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Records and expected distinctions

The following is one complete illustrative instance of the proposed envelope, not
an installed schema. Every `raw_path` is corpus-relative and can be independently
inventoried by unchanged ADR-010 raw-manifest v1. The two supplied timestamps are
synthetic fixture values; absent timestamps and metadata remain absent rather than
being inferred.

### Complete proposed instance

```yaml
schema: kb-bootstrap.source-capture
version: 1
sources:
- source_id: synthetic:letter-a
  origin: {kind: public-url, reference: "https://example.invalid/letter-a.txt"}
  original_revision: {algorithm: sha256, digest: b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060, media_type: text/plain, language: en}
  original_retention: retained
  capture: {method: direct, captured_at: "2026-01-02T03:04:05Z"}
  fidelity: {class: exact, coverage: all-bytes, losses: []}
  representations:
  - representation_id: direct-v1
    revision: {algorithm: sha256, digest: b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060}
    media_type: text/plain
    language: en
    raw_path: letter-a/shared.txt
    retention: retained
    coordinates: {local: {unit: unicode-code-point, range: [0, 5]}, original: {unit: line, range: [1, 2]}}
  - representation_id: direct-v1-copy
    revision: {algorithm: sha256, digest: b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060}
    media_type: text/plain
    raw_path: letter-a/shared-copy.txt
    retention: retained
  permissions: {access: owner-approved-local, retention: retained-by-owner, redistribution: unknown}
- source_id: synthetic:letter-b
  origin: {kind: bundle-relative, reference: supplied/letter-b.txt}
  original_revision: {algorithm: sha256, digest: b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060}
  original_retention: retained
  capture: {method: direct}
  fidelity: {class: exact, coverage: all-bytes, losses: []}
  representations:
  - representation_id: direct-v1
    revision: {algorithm: sha256, digest: b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060}
    media_type: text/plain
    raw_path: letter-b/shared.txt
    retention: retained
  permissions: {access: owner-approved-local, retention: retained-by-owner, redistribution: prohibited}
- source_id: synthetic:three-paragraph-note
  origin: {kind: opaque-owner-reference, reference: NOTE-7}
  original_revision: {opaque: supplied-revision-3, media_type: text/plain, language: en}
  original_retention: unknown
  capture: {method: converted, converter: {identity: synthetic-selector, version: "1", parameters: {selection: paragraph-2}}}
  fidelity: {class: partial, coverage: paragraph-2-only, losses: [paragraphs-1-and-3-omitted]}
  representations:
  - representation_id: paragraph-2-v1
    revision: {algorithm: sha256, digest: 82641ee88dd2e26449f7ca30f9ecafeac2ceaa73f5834fa17a1dd588a12872ef}
    media_type: text/plain
    raw_path: note-7/partial.txt
    retention: retained
    coordinates: {local: {unit: byte, range: [0, 17]}, original: unknown}
  permissions: {access: restricted, retention: retained-by-owner, redistribution: prohibited}
- source_id: synthetic:briefing
  origin: {kind: opaque-owner-reference, reference: BRIEF-9}
  original_revision: {opaque: owner-label-r1, media_type: audio/ogg, language: en}
  original_retention: reference-only
  capture: {method: manual-summary, captured_at: "2026-02-03T04:05:06+00:00"}
  fidelity: {class: manual-summary, coverage: selected-topics, losses: [wording, timing, non-selected-topics]}
  representations:
  - representation_id: operator-summary-v1
    revision: {algorithm: sha256, digest: 2857c000e63dab3596026f2c317dedad64ca30163fe2b59d4466253ec4908c18}
    media_type: text/markdown
    raw_path: briefing/summary.md
    retention: retained
    coordinates: {local: {unit: unicode-code-point, range: [0, 17]}, original: unknown}
  permissions: {access: restricted, retention: summary-only, redistribution: unknown}
- source_id: synthetic:missing-origin
  origin: {kind: unavailable, reason: no-safe-reference-supplied}
  original_revision: {opaque: unknown}
  original_retention: unknown
  capture: {method: blocked, reason: origin-unavailable}
  fidelity: {class: blocked, coverage: none, losses: [all-content-unavailable]}
  representations: []
  permissions: {access: unknown, retention: none, redistribution: unknown}
- source_id: synthetic:empty-control
  origin: {kind: bundle-relative, reference: supplied/empty.txt}
  original_revision: {algorithm: sha256, digest: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855, media_type: text/plain}
  original_retention: retained
  capture: {method: direct}
  fidelity: {class: unknown, coverage: unknown, losses: []}
  representations:
  - representation_id: empty-direct-v1
    revision: {algorithm: sha256, digest: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855}
    media_type: text/plain
    raw_path: empty/empty.txt
    retention: retained
    coordinates: {local: {unit: byte, range: [0, 0]}, original: unknown}
  permissions: {access: owner-approved-local, retention: retained-by-owner, redistribution: unknown}
```

The records use one nested shape. Local coordinates inherit the enclosing
representation identity/revision. Original coordinates remain separate and
unknown where unavailable. `letter-b` and the zero-byte control intentionally
omit `captured_at`; no time is implied. The blocked `[]` means known-no-output,
whereas the zero-byte control has one retained representation and `[0, 0)` range.
Its `class: unknown` records an attempted capture with one retained representation; it requires explicit representation presence and does not infer exact fidelity from matching digests.

### Changed original versus changed conversion

For `synthetic:letter-a`, two independent transitions demonstrate the revision
axes:

| Transition | Original revision | Representation revision | Meaning |
|---|---|---|---|
| baseline | `b6a98d9c…51060` | `b6a98d9c…51060` | exact `shared.txt` |
| new original, direct capture | `b3333cb0…e73aa` | `b3333cb0…e73aa` | original bytes changed to `original-v2.txt` |
| same baseline original, new conversion | `b6a98d9c…51060` | `1921b918…a4005` | converter output changed to `conversion-v2.txt`; original did not |

The final row would declare `method: converted`, converter identity/version/
parameters, and any case-normalization loss. Neither transition overwrites or
relabels the baseline, changes permissions, or implies deletion/refetch.

## Fixture assertions

1. Literal byte counts and SHA-256 values, including the zero-byte control,
   recompute exactly.
2. The two distinct origins using `shared.txt` retain separate `source_id` values.
3. Exact, partial, blocked, and manual-summary fidelity remain distinguishable.
4. Original and representation revision changes occupy independent axes.
5. Retained evidence has a safe relative path; reference-only or unavailable
   evidence does not claim successful reverse navigation.
6. Representation-local coordinates never stand in for unknown original
   coordinates, and permission labels remain independent of every revision.
7. The envelope and every source use the proposal's single nested shape; missing
   `representations`, `capture`, or `fidelity` is invalid.
8. `representations: []` is used only for the blocked record; unknown fidelity has
   one retained representation. The `letter-a` exact record has two representations,
   both matching its known original digest; partial/manual-summary rows declare at
   least one loss; line coordinates start at one while byte/code-point coordinates
   start at zero.
9. The zero-byte control is UTF-8 text (`text/plain`), not arbitrary binary.
