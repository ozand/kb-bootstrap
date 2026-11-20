from pathlib import Path
import tempfile
from unittest.mock import patch

from kb_bootstrap.cli import main


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
    assert "only when QMD maintenance is explicitly selected" in content
    assert "`qmd update` is not a collection selector" in content
    assert "Legacy `kb-bootstrap search` remains distinct" in content
    assert "`kb-bootstrap search-qmd` adapter" in content
    assert "does not register collections, update the index" in content
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


def test_generated_wiki_guidance_marks_universal_conformance_not_run():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "consumer"
        with patch("sys.argv", ["kb-bootstrap", "--target", str(target)]):
            assert main() is None
        skill_path = target / ".agents/skills/kb-wiki-builder/SKILL.md"
        skill = skill_path.read_text(encoding="utf-8")
        legacy_guide = (skill_path.parent / "../qmd-operator/SKILL.md").resolve()
        assert legacy_guide.is_file()

    core_target = Path(tmp) / "core-only"
    with patch("sys.argv", ["kb-bootstrap", "--target", str(core_target), "--core-only"]):
        assert main() == 0
    core_skill_path = core_target / ".agents/skills/kb-wiki-builder/SKILL.md"
    core_skill = core_skill_path.read_text(encoding="utf-8")
    core_guide = (core_skill_path.parent / "../qmd-operator/SKILL.md").resolve()
    assert not core_guide.exists()

    assert "ordinary local file-based work without QMD retrieval/indexing" in skill
    assert "Read the explicitly selected target source directly from its local file" in skill
    assert "does not require QMD or context-mode" in skill
    assert "kb-bootstrap validate-core --dir kb" in skill
    assert "local profile/provenance/graph checks only" in skill
    assert "consumer policy compliance or publication readiness" in skill
    assert "Report each selected QMD action—search, registration, and index update—separately as **PASS**, **FAIL**, or **NOT RUN** according to what actually happened" in skill
    assert "A successful legacy `validate` does not establish QMD runtime/index readiness" in skill
    assert "Report universal kb-bootstrap conformance as **NOT RUN** unless `kb-bootstrap validate --dir kb --project-root .` actually ran; report its actual pass/fail independently" in skill
    assert "If QMD retrieval is selected and authorized" in skill
    assert "Search does not by itself authorize collection registration or index maintenance" in skill
    assert "Register or update only when QMD maintenance is separately selected and authorized" in skill
    assert "Report each selected QMD action—search, registration, and index update—separately as **PASS**, **FAIL**, or **NOT RUN**" in skill
    assert "Use **NOT RUN** only for an action not performed" in skill
    assert "a successful selected search remains a search result" in skill
    assert "Do not claim index freshness unless the required registration and update evidence was recorded" in skill
    assert "../qmd-operator/SKILL.md" in skill
    assert "installed sibling `../qmd-operator/SKILL.md` when present" in skill
    assert "[upstream guide](https://github.com/ozand/kb-bootstrap/blob/main/kb_bootstrap/templates/skills/qmd-operator/SKILL.md) otherwise" in skill
    assert "not a prerequisite for local work" in skill
    assert "installed sibling `../qmd-operator/SKILL.md` when present" in core_skill
    assert "[upstream guide](https://github.com/ozand/kb-bootstrap/blob/main/kb_bootstrap/templates/skills/qmd-operator/SKILL.md) otherwise" in core_skill
    assert "not a prerequisite for local work" in core_skill
    assert "qmd update" in skill
    assert "configured but broken selected QMD workflow is a failure" in skill
    assert "initialization retain their existing QMD declaration requirements" in skill
    assert "Core validation does not authorize skipping required consumer checks" in skill


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
