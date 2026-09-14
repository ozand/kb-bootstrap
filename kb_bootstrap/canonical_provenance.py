"""Bounded deterministic provenance and freshness validation for canonical concepts."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import unquote, urlsplit

import yaml
from yaml.constructor import ConstructorError

from .canonical_profile import VALID_STATUSES, _concept_files, _traverses_symlink

MAX_TIMESTAMP_LENGTH = 128
TIMESTAMP_PATTERN = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<time_hour>\d{2}):(?P<time_minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d+))?"
    r"(?:Z|(?P<sign>[+-])(?P<offset_hour>\d{2}):(?P<offset_minute>\d{2}))$"
)
DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[/\\]")
INVALID_PERCENT_PATTERN = re.compile(r"%(?![0-9A-Fa-f]{2})")
RELATIVE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]*$")
CREDENTIAL_WORD_PATTERN = re.compile(
    r"(?i)(token|password|secret|api[_-]?key|authorization)\s*[:=]"
)


class _ProvenanceLoader(yaml.SafeLoader):
    """Keep timestamps as strings, retain other native types, reject duplicate keys."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=False)
            try:
                duplicate = key in seen
            except TypeError as exc:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable mapping key",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a duplicate mapping key",
                    key_node.start_mark,
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


_ProvenanceLoader.yaml_implicit_resolvers = {
    key: list(value) for key, value in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
for first_character, resolvers in list(_ProvenanceLoader.yaml_implicit_resolvers.items()):
    _ProvenanceLoader.yaml_implicit_resolvers[first_character] = [
        (tag, expression)
        for tag, expression in resolvers
        if tag != "tag:yaml.org,2002:timestamp"
    ]


def parse_timestamp(value: object) -> Optional[Fraction]:
    """Return exact UTC seconds so arbitrary fractional precision is preserved."""
    if not isinstance(value, str) or len(value) > MAX_TIMESTAMP_LENGTH:
        return None
    match = TIMESTAMP_PATTERN.fullmatch(value)
    if not match:
        return None

    offset_hour = int(match.group("offset_hour") or 0)
    offset_minute = int(match.group("offset_minute") or 0)
    if (
        offset_minute >= 60
        or offset_hour > 14
        or (offset_hour == 14 and offset_minute != 0)
    ):
        return None

    offset = f"{match.group('sign') or '+'}{offset_hour:02d}:{offset_minute:02d}"
    whole_value = (
        f"{match.group('year')}-{match.group('month')}-{match.group('day')}"
        f"T{match.group('time_hour')}:{match.group('time_minute')}:{match.group('second')}"
        f"{offset}"
    )
    try:
        parsed = datetime.fromisoformat(whole_value).astimezone(timezone.utc)
    except (OverflowError, ValueError):
        return None
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = parsed - epoch
    whole_seconds = delta.days * 86400 + delta.seconds
    fraction_text = match.group("fraction")
    fraction = (
        Fraction(int(fraction_text), 10 ** len(fraction_text))
        if fraction_text
        else Fraction(0)
    )
    return Fraction(whole_seconds) + fraction


def _safe_actor(value: object) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        return False
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return False
    if "://" in value or value.startswith(("/", "\\")) or DRIVE_PATTERN.match(value):
        return False
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value) and not value.startswith("human:"):
        return False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", value):
        return False
    return not CREDENTIAL_WORD_PATTERN.search(value)


def _safe_resource(value: object) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        return False
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return False
    if any(character.isspace() for character in value):
        return False
    if value.startswith(("/", "\\")) or DRIVE_PATTERN.match(value):
        return False
    if CREDENTIAL_WORD_PATTERN.search(value) or INVALID_PERCENT_PATTERN.search(value):
        return False

    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if parsed.scheme:
        if parsed.scheme not in {"http", "https"} or "@" in parsed.netloc:
            return False
        try:
            hostname = parsed.hostname
            parsed.port
        except ValueError:
            return False
        if not hostname or "\\" in value:
            return False
        decoded_value = unquote(value)
        if any(ord(character) < 32 or ord(character) == 127 for character in decoded_value):
            return False
        if "%" in decoded_value or "\\" in decoded_value or "%" in parsed.netloc:
            return False
        if re.search(r"(?i)%2f|%5c", parsed.path):
            return False
        decoded_path = unquote(parsed.path)
        path_parts = decoded_path.split("/")
        if any(part in {".", ".."} for part in path_parts):
            return False
        if any("%" in part for part in path_parts):
            return False
        return True

    if "%" in value or "\\" in value or "?" in value or "#" in value:
        return False
    parts = value.split("/")
    if any(
        part in {"", ".", ".."} or not RELATIVE_SEGMENT_PATTERN.fullmatch(part)
        for part in parts
    ):
        return False
    return True


def _frontmatter_native(path: Path) -> Tuple[Dict[str, object], str]:
    if path.is_symlink() or _traverses_symlink(path):
        return {}, "symlinked path is not allowed"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}, "cannot read UTF-8 Markdown"
    if not lines or lines[0] != "---":
        return {}, "missing exact YAML frontmatter"
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, "missing exact YAML frontmatter"
    try:
        parsed = yaml.load("\n".join(lines[1:end]), Loader=_ProvenanceLoader)
    except yaml.YAMLError:
        return {}, "frontmatter is invalid YAML"
    if not isinstance(parsed, dict):
        return {}, "frontmatter must be a mapping"
    return parsed, ""


def _generated_errors(value: object) -> List[str]:
    if not isinstance(value, dict):
        return ["generated must be a mapping"]
    errors: List[str] = []
    if not _safe_actor(value.get("by")):
        errors.append("generated.by is missing or unsafe")
    if "at" in value and parse_timestamp(value.get("at")) is None:
        errors.append("generated.at must be an offset-aware timestamp")
    return errors


def _verified_errors(value: object) -> List[str]:
    events = [value] if isinstance(value, dict) else value
    if not isinstance(events, list):
        return ["verified must be a mapping or list"]
    errors: List[str] = []
    for position, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            errors.append(f"verified event {position} must be a mapping")
            continue
        if not _safe_actor(event.get("by")):
            errors.append(f"verified event {position}.by is missing or unsafe")
        if parse_timestamp(event.get("at")) is None:
            errors.append(f"verified event {position}.at must be an offset-aware timestamp")
    return errors


def _sources_errors(value: object) -> List[str]:
    if not isinstance(value, list):
        return ["sources must be a list"]
    errors: List[str] = []
    for position, source in enumerate(value, start=1):
        if not isinstance(source, dict):
            errors.append(f"source {position} must be a mapping")
            continue
        if not _safe_resource(source.get("resource")):
            errors.append(f"source {position}.resource is missing or unsafe")
    return errors


def validate_canonical_provenance(
    base_dir: Union[str, Path], now: Optional[object] = None
) -> Tuple[str, bool]:
    """Validate bounded optional families and classify freshness deterministically."""
    explicit_now: Optional[Fraction] = None
    if now is not None:
        explicit_now = parse_timestamp(now)
        if explicit_now is None:
            return "RESULT: BLOCKED (--now must be an offset-aware timestamp)", False

    raw_root = Path(base_dir).absolute()
    root = raw_root.resolve()
    if _traverses_symlink(raw_root):
        return "RESULT: BLOCKED (canonical root traverses a symlink)", False
    if not root.is_dir():
        return "RESULT: BLOCKED (canonical root is unavailable)", False

    concept_files, traversal_errors = _concept_files(root)
    errors: List[str] = list(traversal_errors)
    counts = {
        "generated_present": 0,
        "generated_absent": 0,
        "generated_invalid": 0,
        "verified_present": 0,
        "verified_absent": 0,
        "verified_invalid": 0,
        "sources_present": 0,
        "sources_absent": 0,
        "sources_invalid": 0,
        "fresh": 0,
        "stale": 0,
        "unknown": 0,
        "freshness_invalid": 0,
    }

    for concept in concept_files:
        relative = concept.relative_to(root).as_posix()
        metadata, frontmatter_error = _frontmatter_native(concept)
        if frontmatter_error:
            errors.append(f"{relative}: {frontmatter_error}")
            errors.append(f"{relative}: provenance fields are unavailable")
            counts["freshness_invalid"] += 1
            continue

        status = metadata.get("status")
        if "status" in metadata and (
            not isinstance(status, str) or status not in VALID_STATUSES
        ):
            errors.append(f"{relative}: status must be draft, stable, or deprecated")

        for field, validator in (
            ("generated", _generated_errors),
            ("verified", _verified_errors),
            ("sources", _sources_errors),
        ):
            if field not in metadata:
                counts[f"{field}_absent"] += 1
                continue
            field_errors = validator(metadata[field])
            if field_errors:
                counts[f"{field}_invalid"] += 1
                errors.extend(f"{relative}: {error}" for error in field_errors)
            else:
                counts[f"{field}_present"] += 1

        if "stale_after" not in metadata:
            counts["unknown"] += 1
            continue
        stale_after = parse_timestamp(metadata.get("stale_after"))
        if stale_after is None:
            counts["freshness_invalid"] += 1
            errors.append(f"{relative}: stale_after must be an offset-aware timestamp")
        elif explicit_now is None:
            counts["unknown"] += 1
        elif explicit_now < stale_after:
            counts["fresh"] += 1
        else:
            counts["stale"] += 1

    errors.sort()
    lines = [
        "=== Canonical Provenance/Freshness Profile ===",
        f"Concept files: {len(concept_files)}",
        (
            "Generated: "
            f"present={counts['generated_present']} "
            f"absent={counts['generated_absent']} "
            f"invalid={counts['generated_invalid']}"
        ),
        (
            "Verified: "
            f"present={counts['verified_present']} "
            f"absent={counts['verified_absent']} "
            f"invalid={counts['verified_invalid']}"
        ),
        (
            "Sources: "
            f"present={counts['sources_present']} "
            f"absent={counts['sources_absent']} "
            f"invalid={counts['sources_invalid']}"
        ),
        (
            "Freshness: "
            f"fresh={counts['fresh']} stale={counts['stale']} "
            f"unknown={counts['unknown']} invalid={counts['freshness_invalid']}"
        ),
        f"Comparison time: {'explicit' if explicit_now is not None else 'absent'}",
    ]
    if errors:
        lines.append(f"ERRORS ({len(errors)}):")
        lines.extend(f"   - {error}" for error in errors)
    else:
        lines.append("ERRORS: 0")
    lines.append("Source mutation: no")
    return "\n".join(lines), not errors
