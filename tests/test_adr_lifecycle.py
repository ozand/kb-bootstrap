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
    seen = set()
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        match = INDEX_ROW_PATTERN.match(line)
        if match:
            number, title, status = match.groups()
            assert number not in seen, f"duplicate ADR-{number} index row"
            seen.add(number)
            rows[number] = (title, status)
    return rows


def test_index_rows_reject_duplicate_adr_numbers():
    from unittest.mock import patch

    duplicate_index = "| ADR-020 | Example | Accepted |\n| ADR-020 | Example | Accepted |\n"
    with patch.object(Path, "read_text", return_value=duplicate_index):
        try:
            index_rows()
        except AssertionError as error:
            assert "duplicate ADR-020 index row" in str(error)
        else:
            raise AssertionError("duplicate ADR index rows were silently overwritten")


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


def test_superseded_adr_008_and_implemented_adr_009_have_executable_evidence():
    superseded = (ADR_DIR / "ADR-008-validate-a-logical-published-okf-bundle.md").read_text(
        encoding="utf-8"
    )
    implemented = (ADR_DIR / "ADR-009-publish-an-okf-bundle-as-an-exclusive-zip-file.md").read_text(
        encoding="utf-8"
    )
    assert "**Status**: Superseded by ADR-009" in superseded
    assert "**Status**: Accepted — Implemented" in implemented
    assert "tests/test_published_bundle_export.py" in implemented
    assert "passing" in implemented
