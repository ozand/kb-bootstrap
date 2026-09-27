# UX/UI patterns

Read when the brief asks how screens look and behave.

## Evidence

- Capture help-center articles for each key screen in the brief with `--images 3-4`.
  Target: 4+ screenshots per key screen, from at least 2 different products.
- A screenshot counts only if it shows the product UI. Hero banners, illustrations, logos
  and stock photos are not evidence — delete them from `raw/img/` if captured, together
  with their links.
- Say what a screenshot proves and what it does not ("the list shows name, status,
  duration; density on thousands of rows is not visible").

## Describe a pattern (goes into a concept card)

```markdown
## Essence
<one paragraph: the problem the pattern solves and how>

## Where it appears
| Product | How | Evidence |
|---|---|---|
| [Product A](../entities/product-a.md) | filter chips above the list, reset button | ![](../../research/<folder>/raw/img/012-2.png) [raw 012](…) |

## Variants and trade-offs
- <variant A vs B, when each fits>

## Fit for our product
<concrete: which screen, what changes; "(docs)" where the UI was not seen>
```

## Report section

Group by screen or task (list, search, detail page, settings…), not by product. For each:
2–4 patterns, screenshot links, one line on applicability. Add a gallery: per key screen,
the list of screenshot links with one-line captions.

## Gotchas

- Many screenshots of one product are one data point, not a market pattern — say so.
- Mobile/responsive behaviour is rarely documented; do not claim it without evidence.
