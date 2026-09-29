# W03 synthetic source and capture examples

**Status:** Illustrative data-only fixtures for the Proposed W03-A design. All
origins, bytes, identifiers, timestamps, permission labels, and converter names
below are synthetic. Nothing is fetched or authorized.

## Literal byte fixtures

Each fenced payload below denotes exactly its UTF-8 content between the fence
lines, including the single LF after the visible text. Digests were computed over
those literal bytes, not over the Markdown fences or labels.

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

## Records and expected distinctions

These compact pseudo-records intentionally omit envelope repetition. A digest is
always SHA-256; every `raw_path` is corpus-relative and can be independently
inventoried by unchanged ADR-010 raw-manifest v1.

### Exact, retained, and known coordinates

```yaml
source_id: synthetic:letter-a
origin: {kind: public-url, reference: "https://example.invalid/letter-a.txt"}
original_revision: {digest: b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060, media_type: text/plain, language: en}
representation_id: direct-v1
representation_revision: b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060
raw_path: letter-a/shared.txt
retention: retained
capture: {method: direct, captured_at: "2026-01-02T03:04:05Z"}
fidelity: {class: exact, coverage: all-bytes, losses: []}
coordinates: {representation: {unit: unicode-code-point, range: [0, 5]}, original: {unit: line, range: [1, 2]}}
permissions: {access: owner-approved-local, retention: retained-by-owner, redistribution: unknown}
```

Reverse navigation resolves the retained six bytes. The local range addresses
`direct-v1` at its stated digest; the original line range is a distinct claim.

### Duplicate bytes, distinct origin

```yaml
source_id: synthetic:letter-b
origin: {kind: bundle-relative, reference: supplied/letter-b.txt}
original_revision: {digest: b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060}
representation_id: direct-v1
representation_revision: b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060
raw_path: letter-b/shared.txt
retention: retained
fidelity: {class: exact, coverage: all-bytes, losses: []}
permissions: {access: owner-approved-local, retention: retained-by-owner, redistribution: prohibited}
```

The digest equals `letter-a`, but `source_id` and origin differ; these records must
not be merged or counted as independent corroboration merely from byte equality.

### Partial conversion and unknown original coordinates

```yaml
source_id: synthetic:three-paragraph-note
origin: {kind: opaque-owner-reference, reference: NOTE-7}
original_revision: {opaque: supplied-revision-3, media_type: text/plain, language: en}
representation_id: paragraph-2-v1
representation_revision: 82641ee88dd2e26449f7ca30f9ecafeac2ceaa73f5834fa17a1dd588a12872ef
raw_path: note-7/partial.txt
retention: retained
capture: {method: converted, converter: {identity: synthetic-selector, version: "1", parameters: {selection: paragraph-2}}}
fidelity: {class: partial, coverage: paragraph-2-only, losses: [paragraphs-1-and-3-omitted]}
coordinates: {representation: {unit: byte, range: [0, 17]}, original: unknown}
permissions: {access: restricted, retention: retained-by-owner, redistribution: prohibited}
```

Seventeen bytes do not establish completeness. The representation coordinates are
known; no page, line, or byte position is invented for the unavailable original.

### Manual summary, reference-only original

```yaml
source_id: synthetic:briefing
origin: {kind: opaque-owner-reference, reference: BRIEF-9}
original_revision: {opaque: owner-label-r1, media_type: audio/ogg, language: en}
representation_id: operator-summary-v1
representation_revision: 2857c000e63dab3596026f2c317dedad64ca30163fe2b59d4466253ec4908c18
raw_path: briefing/summary.md
retention: retained
capture: {method: manual-summary, captured_at: "2026-02-03T04:05:06+00:00"}
fidelity: {class: manual-summary, coverage: selected-topics, losses: [wording, timing, non-selected-topics]}
coordinates: {representation: {unit: unicode-code-point, range: [0, 17]}, original: unknown}
original_retention: reference-only
permissions: {access: restricted, retention: summary-only, redistribution: unknown}
```

Reverse navigation reaches only the summary; the original audio is honestly
unavailable. This is neither an extraction nor a model-derived description.

### Blocked capture and missing origin

```yaml
source_id: synthetic:missing-origin
origin: {kind: unavailable, reason: no-safe-reference-supplied}
original_revision: {opaque: unknown}
representations: []
capture: {method: blocked, reason: origin-unavailable}
fidelity: {class: blocked, coverage: none, losses: [all-content-unavailable]}
permissions: {access: unknown, retention: none, redistribution: unknown}
```

There is no digest, coordinate, or retained evidence to fabricate, and reverse
navigation returns unavailable without trying a path or network reference.

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

1. Literal byte counts and SHA-256 values recompute exactly.
2. The two distinct origins using `shared.txt` retain separate `source_id` values.
3. Exact, partial, blocked, and manual-summary fidelity remain distinguishable.
4. Original and representation revision changes occupy independent axes.
5. Retained evidence has a safe relative path; reference-only or unavailable
   evidence does not claim successful reverse navigation.
6. Representation-local coordinates never stand in for unknown original
   coordinates, and permission labels remain independent of every revision.
