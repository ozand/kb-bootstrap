# Validation composition for consumer repositories

`kb-bootstrap` provides universal, consumer-independent checks. A repository may require additional local policy validation and separate retrieval/index verification. These are three independent gates with different owners, evidence, and outcomes.

A successful result from one gate is not evidence that another gate passed.

## The three gates

| Gate | Owner | What it can establish | What it does not establish |
|---|---|---|---|
| **Universal kb-bootstrap conformance** | `kb-bootstrap` | Minimal canonical OKF structure, bounded provenance/freshness metadata syntax, supported local-link integrity, and QMD declaration/path validity. | Consumer-required fields, local enums or IDs, repository-specific link grammars, semantic fidelity, QMD registration, index freshness, or retrieval quality. |
| **Repository-owned policy validation** | Consumer repository | The local schema, identifiers, vocabularies, placement, evidence, or editorial rules implemented by that repository's explicit validator. | Universal OKF conformance unless the universal validator was also run; QMD index freshness; semantic truth beyond the local validator's stated evidence. |
| **Retrieval/index freshness** | Consumer runtime and retrieval tool | Collection registration, an explicitly executed index update, and representative retrieval observations in the named environment. | Canonical conformance, local policy compliance, source correctness, or complete retrieval quality. |

`kb-bootstrap` does not discover or interpret a consumer-local profile and does not provide a universal profile engine for consumer policy. The consumer owns its local validator, schema, version, command, and result contract.

## Recommended sequence

Run only the gates required by the consumer's workflow, but report each required gate separately:

```text
1. Universal conformance and repository declarations
2. Repository-owned policy validation
3. Retrieval/index registration, update, and smoke verification
4. A labelled summary that preserves each separate outcome
```

### 1. Universal kb-bootstrap conformance

```bash
kb-bootstrap validate --dir kb --project-root .
```

When deterministic canonical cutoff classification is required, provide an explicit comparison instant:

```bash
kb-bootstrap validate \
  --dir kb \
  --project-root . \
  --now 2026-09-15T12:00:00Z
```

The command emits separate canonical profile, provenance/freshness, graph-integrity, and QMD declaration sections. Interpret each section only within its documented boundary.

`Freshness: fresh` means only that the authored `stale_after` cutoff is after the explicit `--now` instant. It does not prove that facts are current, sources are reachable, a human verified the content, or a retrieval index is fresh.

### 2. Repository-owned policy validation

A consumer may run its own explicit command after universal validation. The following is a placeholder, not a `kb-bootstrap` command or public output contract:

```bash
python -m <consumer_validator> --root kb
```

The consumer must document what the command checks and which repository/version owns the policy. Examples of possible local concerns include required fields, local ID uniqueness, controlled vocabularies, placement rules, or repository-specific references. These examples do not create an upstream schema.

### 3. Retrieval/index freshness

#### Optional manual QMD declarations for an existing core-only KB

Core-only initialization intentionally creates no QMD configuration, and it cannot
be rerun to add it. If the KB owner chooses QMD, first inspect and back up any
existing `qmd.json` and `qmd/collections/` files. Preserve their bytes; do not
replace, merge, or rerun initialization over an existing target. Resolve partial
or conflicting declarations by owner review before editing. Create only absent
files in the consumer's own change. This recipe declares configuration only; it
does not install QMD, register collections, update an index, search, establish
availability, or authorize those runtime actions.

For either `single` or `umbrella`, the core-only layout has the shared `kb/wiki/`,
`kb/raw/`, and `kb/research/` paths. An owner choosing the minimal dual-collection
layout can create these declarations, replacing `<project>` with the intended
QMD collection slug:

`qmd.json`:

```json
{
  "version": "1.0",
  "workspace": {
    "name": "<project>_kb",
    "collections_dir": "./qmd/collections",
    "db_path": ".qmd/vector.db"
  },
  "models": {
    "embedding": "text-embedding-3-small"
  }
}
```

`qmd/collections/wiki.yaml`:

```yaml
name: <project>-wiki
paths:
  - ../../kb/wiki
```

`qmd/collections/raw.yaml`:

```yaml
name: <project>-raw
paths:
  - ../../kb/raw
  - ../../kb/research
```

If using an ordinary legacy scaffold only as a reference, run its default
initializer in a separate, absent, disposable directory owned by the caller;
never target the existing KB. Compare only its `qmd.json` and collection path
declarations. Its generated collection paths and name reflect that other target
and its broader layout: adapt them to the actual core-only KB and chosen slug,
never copy them blindly. No scaffold rerun is required for the manual example.

After reviewing the declarations, check them without invoking QMD:

```bash
kb-bootstrap validate --dir kb --project-root .
```

This legacy validator checks recognized collection names and paths, including
path existence, but is not a general YAML syntax validator. Alongside its other
universal checks, it does not validate `qmd.json` or perform QMD runtime
operations.
`validate-core` remains the separate core-only check and does not validate QMD
declarations. Publication, doctor, and consumer-owned policy checks are unchanged.
Only if the owner separately chooses runtime work should they consult the
[qmd-operator guide](../kb_bootstrap/templates/skills/qmd-operator/SKILL.md) and
act deliberately under their permissions in the intended environment.

For generated QMD collections, verify runtime state explicitly:

```bash
qmd collection list

# Register only when the intended collection is absent.
qmd collection add kb --name <project>-wiki --mask "**/*.md"
qmd collection add kb/raw --name <project>-raw --mask "**/*.md"

qmd update
qmd search "<canonical smoke query>" -c <project>-wiki
qmd search "<raw smoke query>" -c <project>-raw
```

`qmd collection add` and `qmd update` mutate local QMD runtime/index state. Run them deliberately in the intended QMD index and environment, only when QMD maintenance is explicitly selected. `qmd update` is not a collection selector and may update more than one collection in the selected index; do not invent a collection-scoping option.

Legacy `kb-bootstrap search` remains distinct from the separately bounded
`kb-bootstrap search-qmd` adapter. `search-qmd` requires explicit collection,
index, canonical directory, and pre-provisioned state; it performs read-only
search and does not register collections, update the index, select ambient state,
or fall back to legacy search. Optional QMD retrieval does not make QMD maintenance
a default step for ordinary file-based work.

The `=== QMD Collection Validation ===` section from `kb-bootstrap validate` checks repository declaration syntax, unique names, and configured paths only. It does not prove that a collection is registered, indexed, fresh, searchable, complete, or relevant.

A successful smoke query proves only the observed query result in the named index/environment. It does not prove universal conformance or consumer policy compliance.

## Generic reporting example

This shape is consumer guidance, not a new `kb-bootstrap` output contract:

```text
=== Universal kb-bootstrap Conformance ===
owner: kb-bootstrap
result: PASS | FAIL | NOT RUN
evidence: <command and sanitized result>

=== Repository-Owned Policy Validation ===
owner: <consumer repository>
result: PASS | FAIL | NOT RUN
evidence: <consumer command and sanitized result>

=== Retrieval / Index Freshness ===
owner: <consumer runtime/tool>
registration: PASS | FAIL | NOT RUN
update: PASS | FAIL | NOT RUN
canonical smoke: PASS | FAIL | NOT RUN
raw smoke: PASS | FAIL | NOT RUN
result: VERIFIED | INCOMPLETE | BLOCKED
evidence: <named index/environment and sanitized observations>
```

Use `NOT RUN` or `INCOMPLETE` when qualifying evidence was not obtained. Do not infer a result from another gate and do not collapse omitted checks into success.

A consumer may define an overall release gate, but its summary must retain the three underlying outcomes. For example, a repository may require all three gates for a knowledge publication while another repository without QMD may require only universal and local policy validation.

## Non-claims

This composition does not mean that:

- OKF conformance proves repository policy compliance;
- unknown consumer metadata was inspected merely because it was preserved;
- QMD declaration validation proves runtime registration or index freshness;
- a successful QMD query proves canonical or policy validity;
- `stale_after` classification proves factual or semantic freshness;
- `kb-bootstrap` provides a universal consumer profile engine;
- any step automatically migrates, repairs, normalizes, indexes, or rewrites consumer content.

Each owner remains responsible for the check it defines and the evidence it claims. If a validation report or receipt must remain available after the run, separately apply the [durable and ephemeral evidence guidance](EVIDENCE_RETENTION.md); a passing command or runtime transcript does not establish retention.
