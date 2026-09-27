# Feature matrix (capability × product)

The core comparison table. Read when the brief asks what products can do.

## Build it

1. Rows = capabilities phrased as user-visible abilities ("Search inside transcripts with
   jump to timestamp"), not marketing names. 8–20 rows; group with bold sub-headers if more.
   Derive rows from the brief's questions and from the user's own product first, then add
   capabilities that several competitors share.
2. Columns = products. **First column is the user's own product** (from its code/docs),
   so gaps and advantages are visible at a glance.
3. Cell values — one legend for every study:
   - `✅ (UI)` — seen on a captured screenshot;
   - `✅ (docs)` — stated in a captured page, not seen;
   - `◐` — partial / only on some plans (say which in a footnote);
   - `—` — not found in captured sources. **Not found ≠ absent**; write this under the table.
4. Every non-`—` cell must be backed by a raw file: link it in the cell, or give per-product
   source lists right under the table. Run `grep_claim.py` for each cell before delivering.

## Template

```markdown
| Capability | OurProduct | [Product A](../entities/product-a.md) | [Product B](../entities/product-b.md) |
|---|---|---|---|
| **Ingest** | | | |
| Watch folders | ✅ (UI) | ✅ (UI) [raw 001](../../research/<folder>/raw/001-….md) | — |
| Cloud-drive import | — | ◐ Pro+ [raw 014](…) | ✅ (docs) [raw 020](…) |

✅ (UI) seen on a screenshot · ✅ (docs) described · ◐ partial/plan-gated · — not found in captured sources (not necessarily absent).
```

## Gotchas

- Filling a whole row with ✅ because "every product surely has it" is the most common
  error found in review. No source → `—`.
- Plan gating matters for positioning: "only on Enterprise" is a finding, not a ✅.
- Keep the own-product column honest: check the code; a missing feature is the point of
  the exercise.
- A product whose pages were all blocked gets no column — list it under Limitations.
