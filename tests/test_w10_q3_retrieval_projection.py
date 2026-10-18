"""End-to-end synthetic Q3 path through existing W10 and local read APIs."""
import hashlib
import tempfile
from pathlib import Path

from kb_bootstrap.local_retrieval import read_local, search_local
from kb_bootstrap.section_projection import project_section
from w10_fixture_support import T0_IDS, T1_IDS, materialize_question_input


INPUTS = Path("docs/evaluation/W10-AGENT-INPUTS.md")
SPEC = Path("docs/evaluation/W10-SYNTHETIC-SPEC.md")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_q3_retrieves_reads_and_projects_evidence_per_revision():
    authoring = INPUTS.read_bytes()
    specification = SPEC.read_bytes()
    # Q3 is dual-revision: use the fixture's separate views, never a union.
    t0 = materialize_question_input(authoring, specification, "Q3").revision_views[0]
    t1 = materialize_question_input(authoring, specification, "Q3").revision_views[1]

    expected = {
        "T0": {"PM-S1", "PM-S2", "PM-S3"},
        "T1": {"PM-S1R", "PM-S2", "PM-S3", "PM-S4"},
    }
    assert t0.fragment_ids == T0_IDS
    assert t1.fragment_ids == T1_IDS
    assert expected["T0"] <= set(t0.fragment_ids)
    assert expected["T1"] <= set(t1.fragment_ids)

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "kb"
        root.mkdir()
        selected = {}
        for view in (t0, t1):
            relative = f"q3/{view.label.lower()}.md"
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(view.content)

            # Discover each expected source by search result, then read and
            # project only the path actually returned; never seed lookup with
            # the expected path.
            retrieved_ids = set()
            for fragment_id in sorted(expected[view.label]):
                result, code = search_local(fragment_id, root)
                assert code == 0
                record = next(item for item in result["results"]
                              if item["path"] == relative)
                read, read_code = read_local(record["path"], root)
                assert read_code == 0
                assert read["status"] == "COMPLETE"
                assert read["content"] == view.content.decode("utf-8")
                retrieved_ids.add(fragment_id)
            assert retrieved_ids == expected[view.label]
            selected[view.label] = (target, view.content, retrieved_ids)

            # Fixture evidence coverage is a finite ID-set ratio, not answer
            # correctness or semantic quality. The denominator is this view's
            # declared Q3 evidence only.
            assert len(retrieved_ids) / len(expected[view.label]) == 1.0

            # Each fragment has its own exact heading. Project a real section
            # using the content's observed digest and assert the returned bytes.
            for fragment_id in sorted(expected[view.label]):
                heading = next(line.removeprefix("### ") for line in view.content.decode().splitlines()
                               if line.startswith(f"### {fragment_id} "))
                section = project_section(root, relative, _sha(view.content), (heading,))
                assert section["status"] == "COMPLETE"
                assert section["observed_sha256"] == _sha(view.content)
                assert section["text"].startswith(f"### {heading}\n")
                assert fragment_id in section["text"]

        # A same-path revision replacement invalidates the prior expected
        # digest. This demonstrates byte-revision mismatch only, not semantic
        # staleness or external freshness.
        old_target, old_bytes, _ = selected["T0"]
        old_digest = _sha(old_bytes)
        new_bytes = selected["T1"][1]
        old_target.write_bytes(new_bytes)
        mismatch = project_section(root, "q3/t0.md", old_digest, ("PM-S1 — Pulse",))
        assert mismatch == {"status": "REVISION_MISMATCH", "observed_sha256": _sha(new_bytes)}
