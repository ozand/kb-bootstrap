# ADR-011: Extract local entity candidate cards with an optional peer

**Status**: Proposed
**Date**: 2026-09-23
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: GitHub issues #100, #99, #101, #102; ADR-003, ADR-009, ADR-010

## Context

Issue #100 asks for local, opt-in GLiNER2/GLiNER2.5 inference over revision-verified raw captures, producing per-file candidate cards. Issue #99 and ADR-010 already provide a versioned SHA-256 raw manifest; QMD handles separate retrieval and the canonical graph represents authored links, not model inferences. Core `kb-bootstrap` supports Python >=3.8, while upstream GLiNER2 reports Python >=3.10 and a heavy optional `[local]` inference extra. The upstream API and checkpoint behavior have not been exercised locally; its docs are reported, not product evidence.

The Issue requires spans, confidence, classification, provenance, local-only model loading, no raw rewrites and no hidden downloads. Extracted text may itself be personal or confidential; a derived card is not sanitized simply because inference happened locally. A string naming a model revision is not evidence that its files are unchanged. This new runtime and persisted artifact contract must be approved independently before implementation.

## Decision

Provide a **separately installed, opt-in local peer** (Python >=3.10) with its own command, never imported by core `kb-bootstrap` and never added to its base dependencies. It consumes an explicit, validated ADR-010 v1 manifest, a project-contained corpus, an explicit local model directory, and a project-contained JSON schema of entity labels and optional document-classification labels. It produces one versioned derived candidate card per selected source file. An absent peer, model, schema, or raw manifest never affects existing `validate`, `raw-manifest`, graph export, published ZIP, QMD, or lessons.

No remote model identifier, implicit checkpoint selection, model installation, network download, cloud API, remote inference, or `trust_remote_code` is permitted. The peer accepts only an existing contained local directory, sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` before loading the optional runtime, passes `local_files_only=True` to every supported model/config/tokenizer load, and blocks if the tested GLiNER2 version cannot honor those parameters. The peer's contract is **no intentional network or fallback model acquisition**: only local paths and offline-only library APIs are accepted. A network-denied integration smoke test must observe that a complete local checkpoint runs and an incomplete checkpoint fails without network attempts. This is not proof of a general OS egress firewall: the peer cannot attest an operator's host isolation, and environment flags alone are not a security boundary. For sensitive raw data the operator must separately run the peer in a verified network-denied environment; until such a deployment is tested, do not claim adversarial egress isolation or approve use on sensitive sources. The tool does not claim to verify that host boundary or fail merely because it cannot see one. Record runtime library version, model digest, schema digest and extraction parameters in each card. A real model smoke under denied network, including missing assets and fallback attempts, is required before claiming local-only behavior.

The model digest is SHA-256 of a canonical stream: enumerate every checkpoint regular file (including config, tokenizer and weights), reject symlinks/non-regular/unsafe/case-fold-colliding relative POSIX names, sort names lexicographically, then hash for each file `uint64_be(len(UTF8(path))) || UTF8(path) || uint64_be(len(bytes)) || bytes`. Hash a stable checked read and recheck the directory before use; compare the digest with an explicit expected 64-character lowercase hex revision. No model path or model file bytes enter cards.

The peer checks source bytes against the manifest SHA-256 before extraction, does not write to the corpus or canonical root, and requires a stable locally controlled checkout (ADR-010). Only explicit manifest paths are processed; no implicit full-corpus discovery or GLiNER download. For large UTF-8 text use an explicit bounded chunk/overlap policy and global Unicode-code-point half-open offsets. Binary/non-UTF-8 files are reported as skipped/unsupported, never decoded heuristically or silently omitted; their manifest entries remain unchanged.

### Candidate card contract

A card is a **derived suggestion**, never an OKF concept, a reviewed entity, or a verified fact. Version 1 is UTF-8 JSON with fixed key order and a final newline:

```json
{
  "schema": "kb-bootstrap.entity-candidate-card",
  "version": 1,
  "status": "derived_candidate",
  "source": {"corpus": "kb/raw", "path": "notes/example.md", "sha256": "<source digest>"},
  "extractor": {"provider": "gliner2", "runtime_version": "<version>", "model_sha256": "<checkpoint digest>", "schema_sha256": "<schema digest>", "chunk_size": 384, "chunk_overlap": 64},
  "classification": [],
  "candidates": [{"label": "service", "start": 10, "end": 22, "score": "0.9412"}]
}
```

`classification` is a list of `{ "label": "incident", "score": "0.9412" }` document-level predictions, distinct from candidate entity type (`label`) and card `status`. The explicit schema lists allowed entity and document-classification labels, descriptions, separate fixed thresholds for each task, chunk size/overlap and overlap policy. Below-threshold results are omitted from the card and not reported individually; the report counts only files processed, files skipped and accepted predictions. Unknown labels or malformed/non-finite scores block. A score is a finite value in [0,1], serialized as a fixed four-decimal ASCII string with half-even rounding; this is a model score, not a calibrated probability. Each span's `start`/`end` indexes original decoded text by Unicode code points (`[start,end)`) and must satisfy `0 <= start < end <= len(text)`. Sort classifications by `(label,score)` and candidates by `(start,end,label,score)` using numeric score comparison before formatting; de-duplicate only identical records. No matched text, snippets, raw bodies, absolute paths or PII excerpts appear in cards or routine diagnostics. The included corpus-relative `source.path` and digest may still be sensitive derived metadata: output location/access/retention are owner-controlled under `docs/EVIDENCE_RETENTION.md`.

Card identity binds `(corpus, source path, source SHA-256, model digest, schema digest, runtime version, parameters)`; serializing the same validated records twice yields identical bytes, but ML inference across unpinned runtime/hardware is **not** claimed byte-identical. Output paths use collision-resistant hashes of card identity rather than raw names; cards live in an explicit existing directory outside the corpus and canonical root, published exclusively from same-parent staging with no overwrite. Repeated runs against an existing identical card may report a deterministic no-op after verifying its complete bytes; conflicting existing content blocks. Removed/changed source revisions do not automatically delete prior cards; a separate explicit consumer determines stale status.

The peer reports only sanitized counts/categories on stdout, with `RESULT: OK | BLOCKED`; absent optional installation, missing checkpoint, revision mismatch, invalid schema/manifest, unsafe output or unavailable hard links block with exit 1; argument errors remain exit 2. A `status: derived_candidate` card is not proof that a person, service, or relation exists. No alias merge, relation extraction, PII redaction, automatic canonical write, QMD update, model training or LLM review is included.

## Alternatives Considered

- **Make GLiNER2 a core Python dependency or run it inside `validate`:** rejected; Python 3.10+/PyTorch would break the Python 3.8+ core and turn probabilistic suggestions into structural gates.
- **Use QMD or a remote LLM for entity extraction:** rejected as the v1 inference backend; QMD retrieves text rather than emitting typed source spans, and sending private raw content to a remote service violates the local-only requirement.
- **Store matched text/snippets in cards by default:** rejected; extracted spans can contain PII. Offsets and source revision suffice for owner-authorized navigation.
- **Trust a user-entered model revision without checking checkpoint bytes:** rejected; mutable weights/config could silently change candidate meaning.
- **Produce SQLite/entity identities or auto-merge aliases:** rejected; #101 owns identity/review, and the optional peer only supplies per-source candidate mentions.
- **Write inferred nodes to the canonical graph or publish with OKF:** rejected; authored links and curated concepts are distinct from probabilistic output.
- **Auto-download or use a model Hub identifier when local path is missing:** rejected; inference must fail closed and remain local/offline.

## Consequences

### What gets easier

- An opt-in consumer can locally pre-sort raw files by candidate entity mentions without requiring remote LLM calls.
- #101 can consume source-revision-linked cards; #102 can navigate them without changing the canonical OKF layer.
- Core `kb-bootstrap` remains usable on Python 3.8+ with no ML installation.

### What gets harder

- A separately installed Python 3.10+ ML runtime and explicitly provisioned local checkpoint need their own compatibility and license checks.
- Hashing model assets and raw inputs costs I/O; inference costs CPU/GPU and may yield false positives or negatives.
- Cards and manifest paths/hashes need private access/retention; format changes require versioning or migration.
- Determinism of serialization does not prove repeatable model predictions across different hardware or package versions.

### What does not change

- Source `kb/raw/`, QMD, lessons, canonical Markdown, existing validation/graph/bundle commands, raw manifest v1, and the Python 3.8+ core dependency contract remain unchanged.
- No hosted GLiNER API, scheduled processing, PII-free certification, model download, automatic source rewrite, or canonical promotion is introduced.

## Test Contract

| Claim in Decision | Test | Currently |
|---|---|---|
| Core runs without GLiNER2/PyTorch; peer has isolated Python >=3.10 installation | clean-core subprocess plus optional-runtime environment check | not yet written |
| Only explicit local checkpoint is used; no intentional network/download/remote code | network-denied real-model smoke and absent-model fixture | not yet run |
| Model/schema/runtime/source fingerprints and changed-source rejection are truthful | digest/revision mismatch and manifest fixture matrix | not yet written |
| Long input yields valid global Unicode-code-point offsets; binary input is explicit skip | long/chunk/Unicode and unsupported-input fixtures | not yet written |
| Cards contain no raw matched text and remain derived, sorted and byte-stable for pinned fixture records | card schema, repeat serialization, privacy fixtures | not yet written |
| Existing/race-created output is preserved; source/canonical trees unchanged | exclusive-publication and source-invariance fixtures | not yet written |
| CLI absence/error/blocked/success stdout and exits are observable | subprocess presentation fixture | not yet written |
| Existing QMD, lessons, raw-manifest, graph and bundle behavior unchanged | full regression suite | not yet run after implementation |

## Rollback

Remove the optional peer installation and revert its implementation PR. Existing candidate cards are derived owner-managed data and are not automatically deleted. A published card schema cannot be changed silently; downstream consumers require an explicit migration or a new version.

## References

- GitHub issues #99, #100, #101, #102
- ADR-003, ADR-005, ADR-009, ADR-010
- `kb_bootstrap/raw_manifest.py`; `docs/EVIDENCE_RETENTION.md`
- Public GLiNER2 README, `pyproject.toml`, and long-context/NER tutorials (reported upstream APIs; local behavior unverified)
