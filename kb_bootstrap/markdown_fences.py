"""Small shared helper for hiding Markdown fenced code from link scanners."""

import re
from typing import List, Optional


FENCE_PATTERN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
LIST_ITEM_PATTERN = re.compile(
    r"^( {0,3})(?:[*+-]|[0-9]{1,9}[.)])( {1,4})(\S.*|)$"
)


def without_fenced_code(body: str) -> str:
    """Return body lines outside bounded backtick or tilde fences."""
    visible: List[str] = []
    fence: Optional[str] = None
    container_indent: Optional[int] = None
    for line in body.splitlines():
        candidate = line
        item_match = LIST_ITEM_PATTERN.match(line)
        if container_indent is not None:
            if not line.strip():
                candidate = ""
            elif line.startswith(" " * container_indent):
                candidate = line[container_indent:]
            else:
                # A list-relative fence ends with its container even when it has
                # no explicit closing marker. Reprocess the outdented line as
                # ordinary Markdown (or as the start of a sibling list item).
                fence = None
                container_indent = None
        if fence is None and container_indent is None and item_match:
            content = item_match.group(3)
            container_indent = len(line) - len(content)
            candidate = content

        match = FENCE_PATTERN.match(candidate)
        if match:
            marker, tail = match.groups()
            if fence is None:
                # Backtick info strings cannot themselves contain backticks.
                if marker[0] != "`" or "`" not in tail:
                    fence = marker
                    continue
            elif (
                marker[0] == fence[0]
                and len(marker) >= len(fence)
                and not tail.strip(" \t")
            ):
                fence = None
                continue
        if fence is None:
            visible.append(line)
    return "\n".join(visible)
