from pathlib import Path


GUIDE = Path("docs/VALIDATION_COMPOSITION.md")
README = Path("README.md")
MIGRATION = Path("docs/MIGRATING_EXISTING_CONSUMERS.md")
QMD_SKILL = Path("kb_bootstrap/templates/skills/qmd-operator/SKILL.md")
WIKI_SKILL = Path("kb_bootstrap/templates/skills/kb-wiki-builder/SKILL.md")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(content: str, start: str, end: str) -> str:
    return content[content.index(start):content.index(end, content.index(start))]


def test_guide_names_three_independent_owned_gates():
    content = read(GUIDE)
    gates = section(content, "## The three gates", "## Recommended sequence")
    expected = {
        "Universal kb-bootstrap conformance": "`kb-bootstrap`",
        "Repository-owned policy validation": "Consumer repository",
        "Retrieval/index freshness": "Consumer runtime and retrieval tool",
    }
    for label, owner in expected.items():
        row = next(line for line in gates.splitlines() if f"**{label}**" in line)
        assert owner in row
        assert "What it can establish" not in row
        assert "What it does not establish" not in row
    assert "different owners, evidence, and outcomes" in content
    assert "A successful result from one gate is not evidence that another gate passed" in content


def test_guide_rejects_profile_engine_and_cross_gate_claims():
    content = read(GUIDE)
    non_claims = section(content, "## Non-claims", "Each owner remains")
    assert "does not provide a universal profile engine" in content
    forbidden_positive_claims = (
        "OKF conformance proves repository policy compliance",
        "QMD declaration validation proves runtime registration or index freshness",
        "a successful QMD query proves canonical or policy validity",
        "`stale_after` classification proves factual or semantic freshness",
    )
    for phrase in forbidden_positive_claims:
        assert f"- {phrase};" in non_claims
        assert phrase not in content[: content.index("## Non-claims")]


def test_guide_uses_generic_placeholders_and_incomplete_states():
    content = read(GUIDE)
    assert "python -m <consumer_validator> --root kb" in content
    assert "<consumer repository>" in content
    assert "PASS | FAIL | NOT RUN" in content
    assert "VERIFIED | INCOMPLETE | BLOCKED" in content
    assert "not a `kb-bootstrap` command or public output contract" in content


def test_guide_separates_qmd_declarations_from_runtime_evidence():
    content = read(GUIDE)
    assert "checks repository declaration syntax" in content
    assert "does not prove that a collection is registered, indexed, fresh, searchable, complete, or relevant" in content
    assert "`qmd collection add` and `qmd update` mutate local QMD runtime/index state" in content
    assert "qmd search \"<canonical smoke query>\" -c <project>-wiki" in content
    assert "qmd search \"<raw smoke query>\" -c <project>-raw" in content


def test_consumer_guidance_links_to_composition_page():
    readme = read(README)
    migration = read(MIGRATION)
    qmd_skill = read(QMD_SKILL)
    wiki_skill = read(WIKI_SKILL)
    assert "docs/VALIDATION_COMPOSITION.md" in readme
    assert "VALIDATION_COMPOSITION.md" in migration
    for skill in (qmd_skill, wiki_skill):
        assert "docs/VALIDATION_COMPOSITION.md" in skill
        assert "separate outcomes" in skill


def test_guidance_remains_consumer_independent_and_documentation_only():
    combined = "\n".join(
        read(path) for path in (GUIDE, README, MIGRATION, QMD_SKILL, WIKI_SKILL)
    )
    for forbidden in (
        "projectmanagment-kb",
        "PM-0001",
        "agentic-project-management",
        "T:/Code",
        "T:\\Code",
    ):
        assert forbidden not in combined
