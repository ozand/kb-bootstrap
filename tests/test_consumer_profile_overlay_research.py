from pathlib import Path


DOCUMENT = Path("docs/CONSUMER_CANONICAL_PROFILE_OVERLAY_RESEARCH.md")


def text() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


def section(content: str, heading: str, next_heading: str) -> str:
    start = content.index(heading)
    end = content.index(next_heading, start)
    return content[start:end]


def test_research_keeps_minimal_and_consumer_boundaries_separate():
    content = text()
    universal = section(
        content,
        "### Universal `kb-bootstrap` validation",
        "### Consumer-owned strict validation",
    )
    consumer = section(
        content,
        "### Consumer-owned strict validation",
        "### Separate concerns",
    )
    assert "minimal canonical OKF profile" in universal
    assert "additional required fields" in consumer
    assert "local enum vocabularies" in consumer
    assert "local ID field, pattern" in consumer
    assert "consumer content layers" in consumer
    assert "record shape and placement only" in consumer
    assert "ID-link syntax/target resolution is a separate" in consumer


def test_research_contains_self_contained_sanitized_audit_categories():
    content = text()
    audited = section(content, "## Audited consumer need", "## Responsibility boundary")
    for category in (
        "Required fields",
        "Enum constraints",
        "ID pattern",
        "Canonical layers",
        "Excluded layers",
        "Adjacent integrity",
    ):
        assert category in audited
    assert "anchored repository prefix followed by a fixed-width decimal sequence" in audited
    assert "method, practical-play, reusable-artifact, research, learning" in audited
    assert "without copying document content or consumer enum values" in audited


def test_each_primary_alternative_has_required_comparison_dimensions():
    content = text()
    alternatives = (
        ("### Alternative A", "### Alternative B"),
        ("### Alternative B", "### Alternative C"),
        ("### Alternative C", "### Alternative D"),
    )
    for start, end in alternatives:
        alternative = section(content, start, end)
        for attribute in (
            "Compatibility",
            "Maintenance",
            "Discoverability",
            "Failure safety",
        ):
            assert f"| {attribute} |" in alternative


def test_research_recommends_no_upstream_implementation_now():
    content = text()
    recommendation = section(content, "## Recommendation", "## Evidence gaps")
    evidence = section(content, "## Evidence gaps", "## Go/no-go matrix")
    assert "Do not add a generic profile-overlay implementation" in recommendation
    assert "two independent consumer repositories" in recommendation
    assert "at least two dated, independently reproducible workflow incidents" in recommendation
    assert "expected command, observed command/output, impact, and corrective action" in recommendation
    assert "Proposed ADR" in recommendation
    assert "only one consumer has been audited" in evidence
    assert "no dated post-documentation composition/discoverability incidents" in evidence


def test_research_separates_adjacent_workstreams_and_prohibits_mutation():
    content = text()
    separate = section(content, "### Separate concerns", "## Alternatives")
    for phrase in (
        "raw-capture schema validation",
        "raw-file hash or citation-ownership checks",
        "QMD registration",
        "syntax, target resolution, or graph export for non-standard ID links",
        "migration, repair, normalization",
        "ID allocation or automatic status promotion",
        "network retrieval or cross-repository synchronization",
    ):
        assert phrase in separate
    assert "Research-only recommendation" in content
    assert "No validator, profile format, migration, repair, or consumer mutation" in content


def test_research_contains_no_consumer_specific_values_or_private_paths():
    content = text()
    forbidden = (
        "PM-\\d",
        "PM-0001",
        "project-management |",
        "agentic-project-management",
        "T:/Code/projectmanagment-kb",
        "T:\\Code\\projectmanagment-kb",
        "lesson-stores.json",
    )
    for value in forbidden:
        assert value not in content
