from pathlib import Path
import re


ADR_DIR = Path("docs/adr")
INDEX = ADR_DIR / "INDEX.md"
ADR_PATTERN = re.compile(r"^ADR-(\d{3})-(.+)\.md$")
INDEX_ROW_PATTERN = re.compile(
    r"^\| ADR-(\d{3}) \| (.+) \| (Proposed|Accepted|Accepted — Implemented|Superseded by ADR-\d{3}) \|$"
)


def adr_files():
    return sorted(path for path in ADR_DIR.glob("ADR-*.md") if ADR_PATTERN.match(path.name))


def index_rows():
    rows = {}
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        match = INDEX_ROW_PATTERN.match(line)
        if match:
            number, title, status = match.groups()
            rows[number] = (title, status)
    return rows


def test_adr_index_and_files_match_both_directions():
    files = {ADR_PATTERN.match(path.name).group(1): path for path in adr_files()}
    rows = index_rows()
    assert rows.keys() == files.keys()


def test_adr_headers_match_index_and_required_sections_exist():
    rows = index_rows()
    required_sections = (
        "## Context",
        "## Decision",
        "## Alternatives Considered",
        "## Consequences",
        "## Test Contract",
    )

    for path in adr_files():
        content = path.read_text(encoding="utf-8")
        number = ADR_PATTERN.match(path.name).group(1)
        title_line = content.splitlines()[0]
        assert title_line.startswith(f"# ADR-{number}: ")
        title = title_line.removeprefix(f"# ADR-{number}: ")
        status_match = re.search(r"^\*\*Status\*\*: (.+)$", content, re.MULTILINE)
        assert status_match is not None
        assert rows[number] == (title, status_match.group(1))
        for heading in required_sections:
            assert heading in content


def test_implemented_adr_007_has_executable_test_evidence():
    content = (ADR_DIR / "ADR-007-report-the-executing-validator-version-from-the-package.md").read_text(
        encoding="utf-8"
    )
    assert "**Status**: Accepted — Implemented" in content
    assert "test_top_level_version_contract" in content
    assert "test_validate_reports_version_once_on_success_and_failure" in content
    assert "| passing |" in content
    assert "not yet run" in content
