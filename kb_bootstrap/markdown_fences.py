"""Small shared helper for hiding Markdown fenced code from link scanners."""

import re
from typing import List, Optional


FENCE_PATTERN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def without_fenced_code(body: str) -> str:
    """Return body lines outside bounded backtick or tilde fences."""
    visible: List[str] = []
    fence: Optional[str] = None
    for line in body.splitlines():
        match = FENCE_PATTERN.match(line)
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
