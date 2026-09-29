"""Offline, test-only materialization helpers for the W10 fixture.

The functions in this module transform caller-supplied bytes only.  They do not
open files, contact services, run a model, or inspect the evaluator key.  The
returned objects describe the byte views an agent would receive; they do not
claim to provide hostile-host sandbox isolation.
"""

from dataclasses import dataclass
import re
from typing import Dict, Optional, Tuple


T0_IDS = (
    "PM-S1", "PM-S2", "PM-S3", "AR-S1", "AR-S2", "AR-S3", "AR-S4",
    "IO-S1", "IO-S2", "IO-S3",
)
T1_IDS = (
    "PM-S1R", "PM-S2", "PM-S3", "PM-S4", "AR-S1R", "AR-S2",
    "AR-S3", "AR-S4", "AR-S5", "IO-S1", "IO-S2", "IO-S3R", "IO-S4",
)
HISTORY_IDS = ("PM-S1", "AR-S1", "IO-S3")
HANDOFF_IDS = ("X-H1", "X-H2")
ALL_IDS = frozenset(T0_IDS + T1_IDS + HANDOFF_IDS)
DUAL_REVISION_QUESTIONS = frozenset(("Q3", "Q5", "Q6", "Q8"))
QUESTION_IDS = tuple("Q{}".format(number) for number in range(1, 11))

ACTIVE_T1_SIZE = 3756
ACTIVE_T1_SHA256 = "8d080ddec4ecdfdf42fa5d082c7192cfb8e38bda038b058197bd4c41963f3cb0"
QUESTION_MANIFEST_SIZE = 763
QUESTION_MANIFEST_SHA256 = "9260c853e7a76abc925131b41f35e48f95570c6429e99e71a078fbf9627804b0"

_FRAGMENT_HEADING = re.compile(rb"^### ([A-Z]+-[A-Z0-9]+) [^\r\n]+$", re.MULTILINE)
_ANY_HEADING = re.compile(rb"^#{1,6}(?:[ \t]+[^\r\n]*)?$", re.MULTILINE)
_QUESTION_ROW = re.compile(
    rb"^\| (Q(?:[1-9]|10)) \| ([^|\r\n]+) \| [^|\r\n]+ \|$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class ByteView:
    """A labelled, immutable byte view (label is metadata, not serialized)."""

    label: str
    content: bytes
    fragment_ids: Tuple[str, ...]


@dataclass(frozen=True)
class QuestionInput:
    """All bytes exposed for one question, kept as distinct labelled views."""

    question_id: str
    question: bytes
    revision_views: Tuple[ByteView, ...]
    handoff_views: Tuple[ByteView, ...] = ()
    chat_history: Tuple[bytes, ...] = ()


def _validate_source(data: bytes, name: str) -> None:
    if not isinstance(data, bytes):
        raise TypeError("{} must be bytes".format(name))
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError("{} must not contain a UTF-8 BOM".format(name))
    if b"\r" in data:
        raise ValueError("{} must use LF newlines".format(name))
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("{} must be UTF-8".format(name)) from error
    if not data.endswith(b"\n"):
        raise ValueError("{} must end with LF".format(name))
    if any(line.endswith((b" ", b"\t")) for line in data.splitlines()):
        raise ValueError("{} must not contain trailing whitespace".format(name))


def extract_fragments(authoring: bytes) -> Dict[str, bytes]:
    """Parse and validate all declared W10 fragments from authoring bytes."""

    _validate_source(authoring, "authoring fixture")
    matches = list(_FRAGMENT_HEADING.finditer(authoring))
    fragments: Dict[str, bytes] = {}
    for match in matches:
        fragment_id = match.group(1).decode("ascii")
        if fragment_id in fragments:
            raise ValueError("duplicate fragment ID: {}".format(fragment_id))
        next_heading = _ANY_HEADING.search(authoring, match.end() + 1)
        end = next_heading.start() if next_heading else len(authoring)
        payload = authoring[match.start():end].rstrip(b"\n") + b"\n"
        fragments[fragment_id] = payload

    actual = frozenset(fragments)
    if actual != ALL_IDS:
        missing = sorted(ALL_IDS - actual)
        unexpected = sorted(actual - ALL_IDS)
        raise ValueError("invalid fragment IDs; missing={!r}, unexpected={!r}".format(
            missing, unexpected
        ))
    return fragments


def materialize_fragment_set(authoring: bytes, fragment_ids: Tuple[str, ...]) -> bytes:
    """Materialize an explicit ordered ID set using the specification byte rule."""

    if not isinstance(fragment_ids, tuple) or not fragment_ids:
        raise ValueError("fragment_ids must be a non-empty tuple")
    if len(set(fragment_ids)) != len(fragment_ids):
        raise ValueError("fragment_ids must not contain duplicates")
    fragments = extract_fragments(authoring)
    unknown = [fragment_id for fragment_id in fragment_ids if fragment_id not in fragments]
    if unknown:
        raise ValueError("unknown fragment IDs: {!r}".format(unknown))
    return b"\n".join(fragments[fragment_id] for fragment_id in fragment_ids)


def materialize_revision(authoring: bytes, revision: str) -> ByteView:
    """Return exactly the active T0 or active T1 byte view."""

    if revision == "T0":
        fragment_ids = T0_IDS
    elif revision == "T1":
        fragment_ids = T1_IDS
    else:
        raise ValueError("revision must be T0 or T1")
    return ByteView(revision, materialize_fragment_set(authoring, fragment_ids), fragment_ids)


def materialize_question_manifest(specification: bytes) -> bytes:
    """Extract only the ten ordered question IDs and reader-task texts."""

    _validate_source(specification, "specification")
    matches = list(_QUESTION_ROW.finditer(specification))
    ids = tuple(match.group(1).decode("ascii") for match in matches)
    if ids != QUESTION_IDS:
        raise ValueError("question manifest must contain Q1 through Q10 exactly once in order")
    return b"".join(match.group(1) + b"\t" + match.group(2) + b"\n" for match in matches)


def materialize_question_input(
    authoring: bytes,
    specification: bytes,
    question_id: str,
    *,
    phase: Optional[str] = None,
) -> QuestionInput:
    """Build the declared per-question views without combining them into a new format."""

    if question_id not in QUESTION_IDS:
        raise ValueError("unknown question ID: {!r}".format(question_id))
    if question_id == "Q9":
        if phase not in ("A", "B"):
            raise ValueError("Q9 phase must be A or B")
    elif phase is not None:
        raise ValueError("phase is valid only for Q9")

    manifest = materialize_question_manifest(specification)
    question = next(
        line for line in manifest.splitlines(keepends=True)
        if line.startswith(question_id.encode("ascii") + b"\t")
    )
    active_t1 = materialize_revision(authoring, "T1")

    if question_id in DUAL_REVISION_QUESTIONS:
        revisions = (materialize_revision(authoring, "T0"), active_t1)
    else:
        revisions = (active_t1,)

    handoffs: Tuple[ByteView, ...] = ()
    if question_id == "Q9" and phase == "B":
        fragments = extract_fragments(authoring)
        handoffs = tuple(
            ByteView(fragment_id, fragments[fragment_id], (fragment_id,))
            for fragment_id in HANDOFF_IDS
        )

    return QuestionInput(question_id, question, revisions, handoffs)
