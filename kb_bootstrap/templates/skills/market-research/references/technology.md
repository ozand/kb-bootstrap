# Technology, platforms, pricing

Read when the brief asks how products are built or delivered, or what they cost.

## Table (one row per product)

```markdown
| Product | Engine / models | Deployment | Platforms | API / integrations | Pricing entry point | Sources |
|---|---|---|---|---|---|---|
| OurProduct | … | local server | web, desktop | REST, CLI | — | code |
| Product A | "Whisper-based" (docs) | cloud SaaS | web, iOS, Android | REST, Zapier | Free / $X per user | [raw 003](…), [raw 007](…) |
```

- **Engine / models**: only what the vendor states (docs, README, blog). "Uses GPT-4" in a
  marketing line is a claim — mark `(vendor claim)`.
- **Deployment**: cloud SaaS / on-prem container / local app / hybrid. This often decides
  privacy positioning.
- **Pricing**: entry paid plan and the plan where the studied feature appears; capture the
  pricing page and note the capture date — prices drift.
- **API**: public API, webhooks, SDKs, CLI, notable integrations (CRM, storage, chat).

## Gotchas

- Do not infer technology from job postings or guesses ("probably uses X"). Unknown is a
  valid cell value.
- Benchmarks and accuracy numbers from vendors are marketing unless the method is
  published; compare quality only with your own test on the same data — recommend such a
  test instead of ranking.
- Open-source products: the README and release notes are primary sources; star counts are
  not quality.
