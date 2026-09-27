# Where evidence lives

Read once per study, before capturing. Goal: pages that show or state the thing you will
claim, not pages that advertise it.

## By question — best source first

| You need | Go to | Notes |
|---|---|---|
| What a screen looks like, how a feature works | help center / knowledge base article (`help.`, `support.`, `docs.`, `guide.`, `/hc/`) | articles embed real UI screenshots — capture with `--images 3-4` |
| Exact capabilities, limits, formats, API | developer docs, API reference, "limits"/"quotas" pages | limits and numbers are only trustworthy from here |
| When a feature appeared, how it changed | changelog, release notes, "what's new", GitHub releases | gives dates; good for "is this new/mature" |
| Price, plan gating ("Business only") | pricing page, plan comparison table | capture the table; plans change often — note the capture date |
| Architecture, local vs cloud, models | docs "how it works", security/privacy whitepaper, GitHub README (open source) | vendor claims — mark as described, not verified |
| Security, compliance (SOC 2, GDPR, HIPAA, local laws) | trust center, security page, DPA | a certificate claim is the vendor's statement, not proof |
| Real user pain, strengths, weaknesses | G2 / Capterra / Trustpilot review pages (public part), Reddit, product forums, GitHub issues, app-store reviews | quote closely; one review is an anecdote — note how many sources agree |
| Jobs and situations of use (JTBD) | reviews ("I use it to…"), case studies, templates galleries, community "how I use X" posts | case studies are curated — say so |
| Market list of players | "alternatives to X" pages, comparison articles, awesome-lists on GitHub | use only to discover names; verify each product at its own source |

## Finding the article instead of guessing

1. `find_links.py <help-center-home> --match <keyword,keyword>` — lists same-site links.
2. If the home page has no useful links, use the site's own search:
   `find_links.py "https://help.example.com/search?q=speaker" --match speaker`.
3. Still nothing: web search `site:help.example.com <keyword>` in the browser window, then
   `find_links.py` on the results page.

## Fidelity of what you capture

- `full` — the article text is there.
- `partial` — short or truncated page; check the file before relying on it.
- `blocked` — login, paywall, bot check; recorded as a stub. Look for the same content in
  docs mirrors, changelogs, public PDFs, or cached copies of the vendor's own docs.

Marketing home pages: capture at most one per product, for the one-line "what it is".
