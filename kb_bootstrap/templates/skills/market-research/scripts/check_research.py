#!/usr/bin/env python3
"""Check one research folder before opening a PR.

Usage: check_research.py kb/research/<YYYY-MM-DD>_<slug> [--kb kb] [--min-screenshots 8]

Checks: brief.md exists; every raw/*.md has RawCapture frontmatter (url, captured_at,
fidelity); every local image/markdown link in raw/ and wiki/ resolves; no image in raw/img
is orphaned; the report kb/wiki/reports/<folder-name>.md exists, links to the brief and
has at least one concept or entity link; then runs `kb-bootstrap validate` if installed.
Exit code 1 on any problem. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
RAW_KEYS = ("type: RawCapture", "url:", "captured_at:", "fidelity:")


def local_links(md: Path) -> list[str]:
    return [t.split("#")[0] for t in LINK.findall(md.read_text(encoding="utf-8"))
            if not re.match(r"[a-z]+:", t) and not t.startswith("#")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("research_dir", type=Path)
    ap.add_argument("--kb", type=Path, default=Path("kb"))
    ap.add_argument("--min-screenshots", type=int, default=8,
                    help="warn below this many linked screenshots; 0 for non-UX studies")
    ap.add_argument("--skip-validate", action="store_true",
                    help="do not run kb-bootstrap validate (project without kb-bootstrap)")
    a = ap.parse_args()
    rd, problems = a.research_dir, []

    if not (rd / "brief.md").is_file():
        problems.append(f"{rd}/brief.md missing")
    raws = sorted((rd / "raw").glob("*.md"))
    if not raws:
        problems.append("raw/ has no captured pages")
    used_images: set[Path] = set()
    homepages, weak = 0, 0
    for md in raws:
        head = md.read_text(encoding="utf-8").split("\n---", 1)[0]
        url = re.search(r"^url:\s*\"?([^\"\n]+)", head, re.M)
        if url and urlsplit(url.group(1)).path.strip("/") == "":
            homepages += 1
        if re.search(r"^fidelity:\s*(partial|blocked)", head, re.M):
            weak += 1
        missing = [k for k in RAW_KEYS if k not in head]
        if not re.match(r"\d{3}-[a-z0-9-]+\.md$", md.name):
            problems.append(f"{md.name}: name must be NNN-<slug>.md")
        if missing:
            problems.append(f"{md.name}: frontmatter lacks {', '.join(missing)}")

    report = a.kb / "wiki" / "reports" / f"{rd.name}.md"
    wiki_files = sorted((a.kb / "wiki").rglob("*.md"))
    if not report.is_file():
        problems.append(f"report {report} missing")
    else:
        text = report.read_text(encoding="utf-8")
        if "brief.md" not in text:
            problems.append(f"{report.name}: no link to the brief")
        if not re.search(r"\]\([^)]*(concepts|entities)/", text):
            problems.append(f"{report.name}: no links to wiki concepts/entities")

    for md in [*raws, *wiki_files]:
        for target in local_links(md):
            path = (md.parent / target).resolve()
            if not path.exists():
                problems.append(f"{md}: broken link {target}")
            used_images.add(path)
    for img in sorted((rd / "raw" / "img").glob("*")):
        if img.name != ".gitkeep" and img.resolve() not in used_images:
            problems.append(f"orphan image (not linked from raw/wiki): {img}")

    if shutil.which("kb-bootstrap") and not a.skip_validate:
        project_root = a.kb.resolve().parent
        res = subprocess.run(["kb-bootstrap", "validate", "--dir", str(a.kb.resolve()),
                              "--project-root", str(project_root)],
                             capture_output=True, text=True, check=False)
        errors = [ln for ln in res.stdout.splitlines() if re.match(r"\s*ERRORS \(\d+\)", ln)]
        if res.returncode != 0 or errors:
            problems.append("kb-bootstrap validate reported errors — run it and fix them")

    print(f"raw pages: {len(raws)}, images linked: "
          f"{sum(1 for p in used_images if p.parent.name == 'img')}, wiki docs: {len(wiki_files)}")
    images = sum(1 for p in used_images if p.parent.name == "img")
    warnings = []
    if raws and homepages * 2 > len(raws):
        warnings.append(f"{homepages}/{len(raws)} raw pages are site home pages (marketing) — "
                        "look for help-center/docs articles with find_links.py")
    if raws and weak * 3 > len(raws):
        warnings.append(f"{weak}/{len(raws)} captures are partial/blocked")
    if images < a.min_screenshots:
        warnings.append(f"only {images} screenshots linked — UX studies need real UI evidence "
                        "(capture help-center articles with --images)")
    for w in warnings:
        print("WARN:", w)
    for p in problems:
        print("PROBLEM:", p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
