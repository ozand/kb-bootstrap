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
    container_indents: List[int] = []
    paragraph = False
    for line in body.splitlines():
        candidate = line
        if line.strip():
            while container_indents and not line.startswith(" " * container_indents[-1]):
                # Exiting an inner item also ends its unclosed fence. Retain
                # outer items so a sibling's real links remain visible.
                container_indents.pop()
                fence = None
            base_indent = container_indents[-1] if container_indents else 0
            candidate = line[base_indent:]
            if fence is None:
                item_match = LIST_ITEM_PATTERN.match(candidate)
                if item_match:
                    content = item_match.group(3)
                    marker = candidate[len(item_match.group(1)):].split()[0]
                    ordered = marker[0].isdigit()
                    can_interrupt = (not ordered or marker[:-1] == "1") and bool(content)
                    if not paragraph or can_interrupt:
                        container_indents.append(base_indent + len(candidate) - len(content))
                        candidate = content
        else:
            paragraph = False
            if container_indents:
                candidate = ""

        match = FENCE_PATTERN.match(candidate)
        if match:
            marker, tail = match.groups()
            if fence is None:
                # Backtick info strings cannot themselves contain backticks.
                if marker[0] != "`" or "`" not in tail:
                    fence = marker
                    paragraph = False
                    continue
            elif (
                marker[0] == fence[0]
                and len(marker) >= len(fence)
                and not tail.strip(" \t")
            ):
                fence = None
                paragraph = False
                continue
        if fence is None:
            visible.append(line)
            paragraph = bool(candidate.strip())
    return "\n".join(visible)
