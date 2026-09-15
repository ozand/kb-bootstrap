from pathlib import Path


GUIDE = Path("docs/EVIDENCE_RETENTION.md")
README = Path("README.md")
CONTRIBUTING = Path("docs/CONTRIBUTING_UPSTREAM.md")
CONTEXT_SCHEMA = Path("docs/REPOSITORY_CONTEXT_SCHEMA.md")
COMPOSITION = Path("docs/VALIDATION_COMPOSITION.md")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(content: str, start: str, end: str) -> str:
    begin = content.index(start)
    return content[begin:content.index(end, begin)]


def test_guide_defines_required_generic_terms_and_nonclaims():
    content = read(GUIDE)
    terms = section(content, "## Terms", "## Evidence classes")
    for term in (
        "Durable evidence",
        "Ephemeral evidence",
        "Retention policy",
        "Durable receipt",
    ):
        row = next(line for line in terms.splitlines() if f"**{term}**" in line)
        assert "Does not prove" not in row
    assert "A file is not durable merely because it currently exists" in terms
    assert "A receipt is not durable merely because it has a structured format" in terms


def test_guide_distinguishes_repository_external_and_runtime_evidence():
    content = read(GUIDE)
    evidence = section(content, "## Evidence classes", "## Durability and immutability")
    assert "### Repository-tracked evidence" in evidence
    assert "### Externally retained evidence" in evidence
    assert "### Runtime and ephemeral state" in evidence
    assert "not a repository audit database" in evidence
    assert "Never copy runtime state wholesale" in evidence


def test_retention_policy_requires_bounded_fields():
    content = read(GUIDE)
    checklist = section(content, "## Retention decision checklist", "## Durable receipt guidance")
    for field in (
        "Owner",
        "Evidence class",
        "Storage reference",
        "Retention",
        "Access",
        "Integrity/version",
        "Availability check",
        "Scope and limitations",
        "Disposal",
    ):
        assert f"**{field}:**" in checklist
    assert "classify the evidence as ephemeral or durability unknown" in checklist


def test_immutable_audit_record_requires_retention_and_integrity_policy():
    content = read(GUIDE)
    immutable = section(content, "## Durability and immutability", "## Retention decision checklist")
    assert "Durability and immutability are separate claims" in content
    assert "an explicit durable retention policy" in immutable
    assert "an explicit durable-receipt policy" in immutable
    assert "how its post-run availability is verified" in immutable
    assert "write-once, append-only, versioned-history, or tamper-evidence mechanism" in immutable
    assert "A Git commit provides a versioned tree identity" in immutable
    assert "not automatically a permanent, protected, signed" in immutable


def test_guide_rejects_sensitive_and_consumer_specific_payloads():
    content = read(GUIDE)
    receipt = section(content, "## Durable receipt guidance", "## Generic workflow")
    for phrase in (
        "credentials",
        "private payloads",
        "personal data",
        "token-bearing URLs",
        "absolute local paths",
        "raw transcripts",
        "runtime checkpoints",
    ):
        assert phrase in receipt
    for forbidden in (
        "projectmanagment-kb",
        "PM-0001",
        "candidate → companion",
        "3–6 clusters",
        "10 source rows",
        "T:/Code",
        "T:\\Code",
    ):
        assert forbidden not in content


def test_guide_is_advisory_and_does_not_add_storage_or_cleanup_behavior():
    content = read(GUIDE)
    nonclaims = section(content, "## Non-claims and failure handling", "If a future change")
    assert "does not implement retention automation" in nonclaims
    assert "manifest generator, receipt store, audit database" in nonclaims
    assert "does not prescribe consumer-specific schemas" in nonclaims
    assert "Do not delete or clean runtime state" in nonclaims
    assert "separate owner-authorized operations" in nonclaims


def test_existing_governance_docs_link_to_retention_guidance():
    assert "docs/EVIDENCE_RETENTION.md" in read(README)
    for path in (CONTRIBUTING, CONTEXT_SCHEMA, COMPOSITION):
        assert "EVIDENCE_RETENTION.md" in read(path)
    assert "VALIDATION_COMPOSITION.md" in read(GUIDE)
