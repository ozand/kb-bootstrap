"""Q3 synthetic retrieval/read/projection path without answer-key query leakage."""
import hashlib
import re
import tempfile
from pathlib import Path

from kb_bootstrap.local_retrieval import read_local, search_local
from kb_bootstrap.section_projection import project_section
from w10_fixture_support import extract_fragments, materialize_question_input


INPUTS = Path("docs/evaluation/W10-AGENT-INPUTS.md")
SPEC = Path("docs/evaluation/W10-SYNTHETIC-SPEC.md")
EXPECTED = {
    "T0": {"PM-S1", "PM-S2", "PM-S3"},
    "T1": {"PM-S1R", "PM-S2", "PM-S3", "PM-S4"},
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run_visible_query(root: Path, question: str):
    # The query is taken only from the agent-visible question, never the key.
    match = re.search(r"\bPulse\b", question)
    assert match is not None
    query = match.group(0)
    result, code = search_local(query, root)
    assert code == 0

    observed = set()
    sections = {}
    for record in result["results"]:
        read, read_code = read_local(record["path"], root)
        assert read_code == 0
        assert read["status"] == "COMPLETE"
        content = read["content"].encode("utf-8")
        heading = re.search(rb"(?m)^### (PM-S1R?|PM-S2|PM-S3|PM-S4) .+$", content)
        assert heading is not None
        source_id = heading.group(1).decode("ascii")
        observed.add(source_id)
        heading_text = heading.group(0).decode("utf-8")[4:]
        projection = project_section(root, record["path"], _sha(content), (heading_text,))
        assert projection["status"] == "COMPLETE"
        assert projection["observed_sha256"] == _sha(content)
        assert projection["text"].encode("utf-8") == content
        sections[source_id] = projection
    return observed, sections


def test_q3_searches_visible_question_then_reads_and_projects_revision_evidence():
    authoring = INPUTS.read_bytes()
    specification = SPEC.read_bytes()
    fragments = extract_fragments(authoring)
    # The existing fixture helper defines the agent-visible dual-revision Q3.
    q3 = materialize_question_input(authoring, specification, "Q3")
    assert [view.label for view in q3.revision_views] == ["T0", "T1"]
    question = q3.question.decode("utf-8").split("\t", 1)[1].strip()

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "kb"
        root.mkdir()
        roots = {}
        observed_by_revision = {}
        for view in q3.revision_views:
            expected = EXPECTED[view.label]
            assert expected <= set(view.fragment_ids)
            revision_root = root / view.label.lower()
            revision_root.mkdir()
            roots[view.label] = revision_root
            # Expose the full agent-visible revision, including distractors;
            # expected IDs do not control corpus membership.
            for source_id in view.fragment_ids:
                target = revision_root / f"{source_id.lower()}.md"
                target.write_bytes(fragments[source_id])

            observed, sections = _run_visible_query(revision_root, question)
            coverage = len(observed & expected) / len(expected)
            assert observed <= set(view.fragment_ids)
            assert set(sections) == observed
            observed_by_revision[view.label] = observed

        # A missing required T0 source is a real retrieval miss, not silently
        # removed from the denominator or counted as successful coverage.
        missing_id = next(iter(EXPECTED["T0"] & observed_by_revision["T0"]))
        missing_path = roots["T0"] / f"{missing_id.lower()}.md"
        missing_path.unlink()
        observed, _ = _run_visible_query(roots["T0"], question)
        assert missing_id not in observed
        missing_coverage = len(observed & EXPECTED["T0"]) / len(EXPECTED["T0"])
        assert missing_coverage < 1.0

        # A same-path byte revision invalidates the earlier expected digest.
        old_path = roots["T0"] / "pm-s1.md"
        old_bytes = fragments["PM-S1"]
        old_digest = _sha(old_bytes)
        old_path.write_bytes(fragments["PM-S1R"])
        heading = next(line.removeprefix("### ") for line in fragments["PM-S1R"].decode().splitlines()
                       if line.startswith("### PM-S1R "))
        mismatch = project_section(roots["T0"], "pm-s1.md", old_digest, (heading,))
        assert mismatch == {"status": "REVISION_MISMATCH", "observed_sha256": _sha(fragments["PM-S1R"])}
