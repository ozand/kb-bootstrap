"""Consistency tests for the offline W10 test fixture materializer."""

import hashlib
from pathlib import Path

import pytest

from w10_fixture_support import (
    ACTIVE_T1_SHA256,
    ACTIVE_T1_SIZE,
    ALL_IDS,
    DUAL_REVISION_QUESTIONS,
    HANDOFF_IDS,
    QUESTION_IDS,
    QUESTION_MANIFEST_SHA256,
    QUESTION_MANIFEST_SIZE,
    T0_IDS,
    T1_IDS,
    extract_fragments,
    materialize_fragment_set,
    materialize_question_input,
    materialize_question_manifest,
    materialize_revision,
)


INPUTS_PATH = Path("docs/evaluation/W10-AGENT-INPUTS.md")
SPEC_PATH = Path("docs/evaluation/W10-SYNTHETIC-SPEC.md")
KEY_PATH = Path("docs/evaluation/W10-EVALUATOR-KEY.md")

# These pin the three source payloads at the requested baseline.  The helper
# deliberately knows none of these paths and never reads the evaluator key.
SOURCE_SHA256 = {
    INPUTS_PATH: "8844fa9429981847d582282b2b287f29c4e228353510d27d4d5ea555388ca839",
    KEY_PATH: "86137f46eb6b38fde81da83a7682fc8e9a171a0161820d2e1de6f7197dab7213",
    SPEC_PATH: "e4d6d613e2cc54f62cc8ce291de41090b06d4ec725ba9501f80c11b84c6ac881",
}


@pytest.fixture(scope="module")
def authoring():
    return INPUTS_PATH.read_bytes()


@pytest.fixture(scope="module")
def specification():
    return SPEC_PATH.read_bytes()


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def test_existing_w10_payloads_are_byte_identical():
    assert {path: digest(path.read_bytes()) for path in SOURCE_SHA256} == SOURCE_SHA256


def test_fragment_parser_preserves_every_declared_payload(authoring):
    fragments = extract_fragments(authoring)
    assert frozenset(fragments) == ALL_IDS
    for fragment_id, payload in fragments.items():
        assert payload.startswith(("### {} ".format(fragment_id)).encode("ascii"))
        assert payload.endswith(b"\n")
        assert payload in authoring


def test_active_revision_membership_order_and_t1_digest(authoring):
    t0 = materialize_revision(authoring, "T0")
    t1 = materialize_revision(authoring, "T1")
    assert (t0.label, t0.fragment_ids) == ("T0", T0_IDS)
    assert (t1.label, t1.fragment_ids) == ("T1", T1_IDS)
    assert t0.content == materialize_fragment_set(authoring, T0_IDS)
    assert t1.content == materialize_fragment_set(authoring, T1_IDS)
    assert len(t1.content) == ACTIVE_T1_SIZE
    assert digest(t1.content) == ACTIVE_T1_SHA256
    assert not any(fragment_id.encode() in t1.content for fragment_id in HANDOFF_IDS)
    assert b"### PM-S1 " not in t1.content
    assert b"### AR-S1 " not in t1.content
    assert b"### IO-S3 " not in t1.content


def test_question_manifest_exact_bytes_and_digest(specification):
    manifest = materialize_question_manifest(specification)
    assert len(manifest) == QUESTION_MANIFEST_SIZE
    assert digest(manifest) == QUESTION_MANIFEST_SHA256
    assert tuple(line.split(b"\t", 1)[0].decode() for line in manifest.splitlines()) == QUESTION_IDS
    assert b"Required capability" not in manifest
    assert b"Scoring" not in manifest


@pytest.mark.parametrize("question_id", QUESTION_IDS)
def test_question_views_have_exact_declared_membership(authoring, specification, question_id):
    phase = "A" if question_id == "Q9" else None
    result = materialize_question_input(
        authoring, specification, question_id, phase=phase
    )
    expected_ids = (T0_IDS, T1_IDS) if question_id in DUAL_REVISION_QUESTIONS else (T1_IDS,)
    assert tuple(view.fragment_ids for view in result.revision_views) == expected_ids
    assert result.question.startswith(question_id.encode() + b"\t")
    assert result.handoff_views == ()
    assert result.chat_history == ()


def test_q9_phases_prevent_future_handoff_leakage(authoring, specification):
    phase_a = materialize_question_input(authoring, specification, "Q9", phase="A")
    phase_b = materialize_question_input(authoring, specification, "Q9", phase="B")
    assert phase_a.handoff_views == ()
    assert tuple(view.label for view in phase_b.handoff_views) == HANDOFF_IDS
    assert tuple(view.fragment_ids for view in phase_b.handoff_views) == tuple(
        (fragment_id,) for fragment_id in HANDOFF_IDS
    )
    assert phase_b.revision_views == phase_a.revision_views
    assert phase_b.chat_history == ()
    for view in phase_a.revision_views:
        assert b"### X-H1 " not in view.content
        assert b"### X-H2 " not in view.content


def test_evaluator_key_cannot_leak_into_any_generated_view(authoring, specification):
    key = KEY_PATH.read_bytes()
    views = []
    for question_id in QUESTION_IDS:
        phase = "B" if question_id == "Q9" else None
        result = materialize_question_input(authoring, specification, question_id, phase=phase)
        views.extend(view.content for view in result.revision_views)
        views.extend(view.content for view in result.handoff_views)
        views.append(result.question)
    assert key not in views
    assert b"# W10-A evaluator key" not in b"".join(views)
    assert b"Expected answer matrix" not in b"".join(views)


@pytest.mark.parametrize("revision", ("", "t1", "T2", None))
def test_invalid_revisions_are_rejected(authoring, revision):
    with pytest.raises(ValueError, match="revision"):
        materialize_revision(authoring, revision)


@pytest.mark.parametrize("question_id", ("", "Q0", "Q11", "q1", None))
def test_invalid_question_ids_are_rejected(authoring, specification, question_id):
    with pytest.raises(ValueError, match="question ID"):
        materialize_question_input(authoring, specification, question_id)


@pytest.mark.parametrize("question_id,phase", (("Q9", None), ("Q9", "C"), ("Q1", "A")))
def test_invalid_phases_are_rejected(authoring, specification, question_id, phase):
    with pytest.raises(ValueError, match="phase"):
        materialize_question_input(authoring, specification, question_id, phase=phase)


def test_missing_duplicate_and_unknown_fragment_ids_are_rejected(authoring):
    fragments = extract_fragments(authoring)
    missing = authoring.replace(fragments["PM-S1"], b"", 1)
    duplicate = authoring + b"\n" + fragments["PM-S1"]
    unknown = authoring + "\n### ZZ-S9 — unexpected\ncontent\n".encode("utf-8")
    for malformed in (missing, duplicate, unknown):
        with pytest.raises(ValueError, match="fragment ID"):
            extract_fragments(malformed)
    with pytest.raises(ValueError, match="duplicates"):
        materialize_fragment_set(authoring, ("PM-S1", "PM-S1"))
    with pytest.raises(ValueError, match="unknown"):
        materialize_fragment_set(authoring, ("NO-SUCH-ID",))


@pytest.mark.parametrize(
    "mutator",
    (
        lambda data: data.replace(b"| Q1 |", b"| Q2 |", 1),
        lambda data: data.replace(b"| Q1 |", b"| Q0 |", 1),
        lambda data: data.replace(b" | conditional meaning, conflicting recommendation |", b"", 1),
    ),
)
def test_malformed_question_manifests_are_rejected(specification, mutator):
    with pytest.raises(ValueError, match="question manifest"):
        materialize_question_manifest(mutator(specification))


@pytest.mark.parametrize("prefix", (b"\xef\xbb\xbf", b" "))
def test_bom_and_trailing_space_are_not_silently_stripped(specification, prefix):
    malformed = prefix + specification if prefix.startswith(b"\xef") else specification.replace(
        b"# W10-A synthetic evaluation specification\n",
        b"# W10-A synthetic evaluation specification \n",
        1,
    )
    with pytest.raises(ValueError):
        materialize_question_manifest(malformed)


@pytest.mark.parametrize("level", range(1, 7))
@pytest.mark.parametrize("has_title", (False, True))
def test_every_heading_ends_payload_before_unselected_text(authoring, level, has_title):
    marker = b"unselected-synthetic-marker"
    heading = b"#" * level + (b" BOUNDARY" if has_title else b"")
    boundary = heading + b"\n" + marker + b"\n\n"
    altered = authoring.replace(b"### PM-S4 ", boundary + b"### PM-S4 ", 1)
    original_view = materialize_revision(authoring, "T1")
    altered_view = materialize_revision(altered, "T1")
    assert altered_view == original_view
    assert marker not in altered_view.content
