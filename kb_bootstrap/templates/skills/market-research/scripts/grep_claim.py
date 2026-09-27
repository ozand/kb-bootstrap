#!/usr/bin/env python3
"""Check whether a claim is backed by raw captures — prints only matching lines.

Usage:
  grep_claim.py kb/research/<folder> "precision-2" ["voiceprint" ...] [--raw 019,020] [--context 120]

Every term is searched case-insensitively in raw/*.md (or only the listed raw numbers).
For each hit prints "<raw file>:<line>: …<context>…" (max 3 hits per file). No hit for a
term means the claim is NOT supported by what you captured: remove it, mark it as a
hypothesis in «Ограничения», or capture a source that states it. Standard library only.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("research_dir", type=Path)
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--raw", default="", help="comma-separated raw numbers, e.g. 019,020")
    ap.add_argument("--context", type=int, default=120)
    a = ap.parse_args()

    only = {n.strip().zfill(3) for n in a.raw.split(",") if n.strip()}
    files = [f for f in sorted((a.research_dir / "raw").glob("*.md")) if not only or f.name[:3] in only]
    missing = 0
    for term in a.terms:
        low, found = term.lower(), 0
        print(f"== {term!r}")
        for f in files:
            hits = 0
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                pos = line.lower().find(low)
                if pos < 0:
                    continue
                start = max(0, pos - a.context // 2)
                print(f"  {f.name}:{i}: …{line[start:start + a.context].strip()}…")
                hits += 1
                if hits == 3:
                    break
            found += hits
        if not found:
            print("  NOT FOUND in raw — do not state this as a fact")
            missing += 1
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
