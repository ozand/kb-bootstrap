"""Bounded end-to-end retrieval trace over each synthetic W10 question view."""
import hashlib
import json
import re
import tempfile
from pathlib import Path

from kb_bootstrap.local_retrieval import read_local, search_local
from kb_bootstrap.section_projection import project_section
from w10_fixture_support import (
    HANDOFF_IDS,
    QUESTION_IDS,
    extract_fragments,
    materialize_question_input,
)

INPUTS = Path("docs/evaluation/W10-AGENT-INPUTS.md")
SPEC = Path("docs/evaluation/W10-SYNTHETIC-SPEC.md")
KEY = Path("docs/evaluation/W10-EVALUATOR-KEY.md")
# Every query is a literal token from that question's reader-visible wording.
QUERY_RECIPE = {
    "Q1": ("Pulse",), "Q2": ("Pulse",), "Q3": ("Pulse",),
    "Q4": ("Relay",), "Q5": ("Relay",), "Q6": ("T1",),
    "Q7": ("cache",), "Q8": ("cache",),
    "Q9": ("interrupted", "complete", "repeated"),
    "Q10": ("evidence", "available"),
}
HEADING = re.compile(rb"(?m)^### ([A-Z]+-[A-Z0-9]+) [^\r\n]+$")
GOLD_ROW = re.compile(
    r"^\s*\| (Q(?:[1-9]|10)) \| (T0|T1|\*) \| ([^|]+) \|$", re.MULTILINE
)


def _project_returned(root, record):
    read, code = read_local(record["path"], root)
    assert code == 0 and read["status"] == "COMPLETE"
    content = read["content"].encode("utf-8")
    match = HEADING.search(content)
    assert match is not None
    source_id = match.group(1).decode("ascii")
    heading = match.group(0).decode("utf-8")[4:]
    digest = hashlib.sha256(content).hexdigest()
    projection = project_section(root, record["path"], digest, (heading,))
    assert projection["status"] == "COMPLETE"
    assert projection["observed_sha256"] == digest
    return source_id, len(content)


def _retrieve(root, question_id, question):
    assert question_id in QUESTION_IDS
    text = question.decode("utf-8").split("\t", 1)[1].strip()
    observed = set()
    calls = {"search": 0, "read": 0, "project": 0}
    returned_bytes = 0
    for query in QUERY_RECIPE[question_id]:
        assert re.search(r"(?<!\w)" + re.escape(query) + r"(?!\w)", text, re.I)
        result, code = search_local(query, root)
        calls["search"] += 1
        assert code == 0 and result["status"] == "COMPLETE"
        for record in result["results"]:
            source_id, byte_count = _project_returned(root, record)
            calls["read"] += 1
            calls["project"] += 1
            returned_bytes += byte_count
            observed.add(source_id)
    return observed, calls, returned_bytes


def _gold_sets(key_bytes):
    key = key_bytes.decode("utf-8")
    gold = {}
    for match in GOLD_ROW.finditer(key):
        question_id, revision, values = match.groups()
        gold.setdefault(question_id, {})[revision] = set(re.findall(r"[A-Z]+-[A-Z0-9]+", values))
    assert set(gold) == set(QUESTION_IDS)
    return gold


def test_all_w10_questions_trace_search_read_projection_and_causal_control():
    authoring = INPUTS.read_bytes()
    specification = SPEC.read_bytes()
    fragments = extract_fragments(authoring)
    rows = []
    roots = {}
    # Materialize and execute all question-visible views before opening the key.
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        for question_id in QUESTION_IDS:
            phases = ("A", "B") if question_id == "Q9" else (None,)
            for phase in phases:
                item = materialize_question_input(
                    authoring, specification, question_id, phase=phase
                )
                phase_label = phase or ""
                views = item.revision_views + item.handoff_views
                if question_id == "Q9":
                    view_root = base / question_id.lower() / phase_label
                    view_root.mkdir(parents=True)
                    all_ids = tuple(source_id for view in views for source_id in view.fragment_ids)
                    for source_id in all_ids:
                        (view_root / (source_id.lower() + ".md")).write_bytes(fragments[source_id])
                    observed, calls, returned_bytes = _retrieve(view_root, question_id, item.question)
                    row = {
                        "question": question_id, "phase": phase, "view": "phase-visible-set",
                        "declared_ids": list(all_ids), "observed_ids": sorted(observed),
                        "calls": calls, "returned_utf8_bytes": returned_bytes,
                    }
                    rows.append(row)
                    roots[(question_id, phase, "phase-visible-set")] = view_root
                else:
                    for view in views:
                        view_root = base / question_id.lower() / phase_label / view.label.lower()
                        view_root.mkdir(parents=True)
                        roots[(question_id, phase, view.label)] = view_root
                        for source_id in view.fragment_ids:
                            (view_root / (source_id.lower() + ".md")).write_bytes(fragments[source_id])
                        observed, calls, returned_bytes = _retrieve(view_root, question_id, item.question)
                        rows.append({
                            "question": question_id, "phase": phase, "view": view.label,
                            "declared_ids": list(view.fragment_ids),
                            "observed_ids": sorted(observed), "calls": calls,
                            "returned_utf8_bytes": returned_bytes,
                        })
        assert [row["question"] for row in rows if row["view"]]  # nonempty trace
        assert {row["question"] for row in rows} == set(QUESTION_IDS)
        assert all(sum(row["question"] == question_id for row in rows) >= 1 for question_id in QUESTION_IDS)
        for row in rows:
            assert set(row["observed_ids"]) <= set(row["declared_ids"])
            assert row["calls"]["search"] == len(QUERY_RECIPE[row["question"]])
            assert row["calls"]["read"] == row["calls"]["project"]
            assert row["calls"]["read"] <= row["calls"]["search"] * len(row["declared_ids"])
        q9_a = next(row for row in rows if row["question"] == "Q9" and row["phase"] == "A")
        q9_b = next(row for row in rows if row["question"] == "Q9" and row["phase"] == "B")
        assert tuple(q9_a["declared_ids"]) == tuple(
            materialize_question_input(authoring, specification, "Q9", phase="A").revision_views[0].fragment_ids
        )
        assert set(q9_b["declared_ids"]) == set(q9_a["declared_ids"]) | set(HANDOFF_IDS)
        assert not (set(q9_a["declared_ids"]) & set(HANDOFF_IDS))
        assert set(q9_b["observed_ids"]) <= set(q9_b["declared_ids"])

        # Evaluator data enters only after baseline searches, reads, and projections.
        gold = _gold_sets(KEY.read_bytes())
        for row in rows:
            declared = set(row["declared_ids"])
            if row["question"] == "Q9":
                relevant = gold["Q9"].get("T1", set()) if row["phase"] == "B" else set()
            else:
                relevant = gold[row["question"]].get(row["view"], set())
                if "*" in gold[row["question"]]:
                    relevant |= gold[row["question"]]["*"]
                relevant &= declared
            row["gold_ids"] = sorted(relevant)
            row["observed_gold_ids"] = sorted(set(row["observed_ids"]) & relevant)
            row["coverage"] = (len(set(row["observed_ids"]) & relevant) / len(relevant)) if relevant else None

        q9_expected = gold["Q9"]["T1"]
        q9_phase_a_observed = set().union(*(set(row["observed_ids"]) for row in rows
                                             if row["question"] == "Q9" and row["phase"] == "A"))
        q9_phase_b_observed = set().union(*(set(row["observed_ids"]) for row in rows
                                             if row["question"] == "Q9" and row["phase"] == "B"))
        q9_phase_coverage = {
            "A": len(q9_phase_a_observed & q9_expected) / len(q9_expected),
            "B": len(q9_phase_b_observed & q9_expected) / len(q9_expected),
            "expected_ids": sorted(q9_expected),
        }

        # Pick a truly retrieved relevant source only now, then remove it and rerun
        # the same visible query. The fixed gold denominator makes loss causal.
        control = next(
            (row for row in rows if row["coverage"] is not None and row["observed_gold_ids"]),
            None,
        )
        assert control is not None
        removed_id = control["observed_gold_ids"][0]
        control_root = roots[(control["question"], control["phase"], control["view"])]
        (control_root / (removed_id.lower() + ".md")).unlink()
        item = materialize_question_input(
            authoring, specification, control["question"], phase=control["phase"]
        )
        after, after_calls, after_bytes = _retrieve(control_root, control["question"], item.question)
        before_coverage = control["coverage"]
        after_coverage = len(after & set(control["gold_ids"])) / len(control["gold_ids"])
        assert removed_id not in after and after_coverage < before_coverage

    report = {
        "questions_executed": len(QUESTION_IDS),
        "q9_handoff_phase_retrieval_coverage": q9_phase_coverage,
        "trace_rows": rows,
        "negative_control": {
            "question": control["question"], "view": control["view"],
            "removed_returned_id": removed_id, "coverage_before": before_coverage,
            "coverage_after": after_coverage, "calls_after": after_calls,
            "returned_utf8_bytes_after": after_bytes,
        },
        "metric_limits": "logical search/read/project calls and returned UTF-8 bytes only; no physical-I/O or latency claim",
        "semantics": "retrieval coverage only; not answer correctness, precision, or model performance",
    }
    assert report["questions_executed"] == len(QUESTION_IDS)
    assert {row["question"] for row in rows} == set(QUESTION_IDS)
    for row in rows:
        assert set(row["observed_ids"]) <= set(row["declared_ids"])
        if row["coverage"] is not None:
            assert 0.0 <= row["coverage"] <= 1.0
        assert all(isinstance(value, int) and not isinstance(value, bool) and value >= 0
                   for value in row["calls"].values())
        assert isinstance(row["returned_utf8_bytes"], int) and row["returned_utf8_bytes"] >= 0
    assert after_calls["read"] == after_calls["project"]
    assert all(isinstance(value, int) and not isinstance(value, bool) and value >= 0
               for value in after_calls.values())
    assert isinstance(after_bytes, int) and after_bytes >= 0
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
    print("W10_FULL_TRACE_REPORT=" + rendered)
