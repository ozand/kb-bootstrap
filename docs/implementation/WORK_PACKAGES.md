# Work packages and execution order

Status: planned work, not implementation completion. Parent: [#121](https://github.com/ozand/kb-bootstrap/issues/121). Issue bodies carry detailed scope and checklists; this page provides routing and dependencies. Refresh live Issues/PRs before starting.

## New work

| Package | Issue | First deliverable | Implementation prerequisites |
|---|---|---|---|
| W01 core/capabilities | [#122](https://github.com/ozand/kb-bootstrap/issues/122) | Proposed optionality and compatibility decision | Accepted D01 |
| W02 safe scaffold | [#123](https://github.com/ozand/kb-bootstrap/issues/123) | Synthetic overwrite reproduction, then update contract | Accepted D02 for new behaviour |
| W03 source/capture | [#124](https://github.com/ozand/kb-bootstrap/issues/124) | Source/representation contract and fixtures | W01/W09 decisions; D03 |
| W04 research import | [#125](https://github.com/ozand/kb-bootstrap/issues/125) | Import supplied local capture without Surf | Accepted W03/W01; D04; coordinate W11 |
| W05 synthesis/profiles | [#126](https://github.com/ozand/kb-bootstrap/issues/126) | Guide and synthetic domain examples | W03/W09 for new records; D05 only if needed |
| W06 retrieval | [#127](https://github.com/ozand/kb-bootstrap/issues/127) | QMD reproduction and bounded read/search design | W01/W09/W11 boundaries; D06 |
| W07 incremental review | [#128](https://github.com/ozand/kb-bootstrap/issues/128) | Evidence-binding design, then read-only impact report | Accepted W03/W05/W09; D07 |
| W08 progress/handoff | [#129](https://github.com/ozand/kb-bootstrap/issues/129) | Portable record and interruption fixtures | Accepted W03/W05/W09; D08 |
| W09 policy | [#130](https://github.com/ozand/kb-bootstrap/issues/130) | Threat model/policy proposal | D09 before new enforcement semantics |
| W10 evaluation | [#131](https://github.com/ozand/kb-bootstrap/issues/131) | Original synthetic fixture specification | Baseline independent; model runs need #100/#109 readiness |
| W11 layers/links | [#132](https://github.com/ozand/kb-bootstrap/issues/132) | Current-behaviour matrix and failing/safe cases | Reproduction now; decision only for contract changes |
| W12 portability | [#133](https://github.com/ozand/kb-bootstrap/issues/133) | Separate Python/name/distribution reproductions | Reproduction now; support-floor changes need approval |

D01-D09 are decision topics in [Architecture proposal](ARCHITECTURE_PROPOSAL.md), not reserved ADR numbers. Dependencies on a decision do not mean waiting for every implementation task in that work package.

## Suggested first wave

Run narrow reproductions for W02, W11 and one W12 slice. In parallel, draft W01/W09 decisions and W05 guidance; W10 can prepare synthetic fixtures. Separate checkouts/branches prevent overlapping modifications. W01, W02, W06 and W11 may all touch `cli.py` or templates; coordinate ownership rather than merging parallel broad edits.

A safe first Codex assignment is W11's characterization test for external Markdown links and code fences. Another is W12-A's minimum-runtime reproduction. Neither requires a real source corpus or a downloaded model.

## Following waves

After accepted capability/source/policy contracts, implement a minimal local capture path and collector-independent research import. Provide bounded file reading and optional retrieval adapters. Use those outputs to exercise read-only impact analysis and portable handoff. Add model ablations last, comparing against an unchanged baseline.

Do not create a dependency cycle: core ingestion/retrieval/evaluation must not require #100 or #109. ML setup consumes the core; it is not a prerequisite for it. #108 remote inference stays independent and disabled unless separately authorized.

## Existing issues: reuse instead of duplicate

At planning time the following were open and already owned relevant work:

| Existing issue | Boundary to preserve |
|---|---|
| [#90](https://github.com/ozand/kb-bootstrap/issues/90) | OKF resource forms, actor convention and usage-window freshness |
| [#91](https://github.com/ozand/kb-bootstrap/issues/91) | Pure-OKF result interpretation and Attested Computation decision |
| [#92](https://github.com/ozand/kb-bootstrap/issues/92) | Staged alignment migration guidance |
| [#100](https://github.com/ozand/kb-bootstrap/issues/100) | Optional local entity candidate peer; not canonical writes/relations/PII |
| [#101](https://github.com/ozand/kb-bootstrap/issues/101) | Mention/entity separation, alias review and identity history |
| [#102](https://github.com/ozand/kb-bootstrap/issues/102) | Bounded read-only candidate navigation |
| [#109](https://github.com/ozand/kb-bootstrap/issues/109) | Consented optional local runtime/model provisioning |
| [#108](https://github.com/ozand/kb-bootstrap/issues/108) | Separate authorized remote inference adapter |

ADR-010 and #99 provide the raw-revision foundation: verify current code and completion evidence before reuse. Historical #4/#6 explain the current QMD coupling; do not silently reinterpret that behaviour. ADR-014 only supersedes specified portions of ADR-011/013; the remaining contracts still matter.

## Completion and deferral

For every slice record actual source commit, exact changes, tests run, checks not run, unresolved decisions and PR location. Keep an implementation issue open when only its design is delivered. W11/W12 cover independent slices and must not be closed by one partial fix. An accepted design still is not evidence of deployed functionality.

Do not select a project licence as cleanup, perform consumer migrations or copy private analysis. A useful deferred outcome records the missing evidence and revisit condition instead of introducing a speculative framework. No time or throughput target is claimed until measured under [Evaluation plan](EVALUATION_PLAN.md).
