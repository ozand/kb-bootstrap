#!/usr/bin/env python3
"""Create a research folder: kb/research/<YYYY-MM-DD>_<slug>/{brief.md, raw/img/}.

Usage: new_research.py <slug> --title "Human title" [--kb kb] [--issue URL]
Prints the created folder. Fails if kb/ or kb/wiki/ is missing (bootstrap first).
Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "brief-template.md"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--title", required=True)
    ap.add_argument("--kb", type=Path, default=Path("kb"))
    ap.add_argument("--issue", default='""')
    a = ap.parse_args()

    slug = re.sub(r"[^a-z0-9]+", "-", a.slug.lower()).strip("-")
    if not slug:
        sys.exit("slug must contain latin letters or digits")
    if not (a.kb / "wiki").is_dir():
        sys.exit(f"{a.kb}/wiki not found — bootstrap the knowledge base first (see SKILL.md, step 0)")

    date = dt.date.today().isoformat()
    folder = a.kb / "research" / f"{date}_{slug}"
    if folder.exists():
        sys.exit(f"{folder} already exists — continue that research instead of creating a new one")
    (folder / "raw" / "img").mkdir(parents=True)
    title_json = '"' + a.title.replace('"', "'") + '"'
    (folder / "brief.md").write_text(
        TEMPLATE.read_text(encoding="utf-8").format(
            title=a.title, title_json=title_json, date=date, slug=slug, issue=a.issue),
        encoding="utf-8",
    )
    print(folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
