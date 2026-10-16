#!/usr/bin/env python3
"""Capture one web page into a research raw/ folder as Markdown (+ optional images).

Usage:
  capture_page.py <research_dir> <url> [--entity otter-ai] [--slug otter-search]
                  [--window-id N] [--images 3] [--min-width 500] [--by "pi/p7"]

- Opens the page in your own surf window (creates one if --window-id is omitted and
  prints its id — reuse it for the next pages).
- Converts the main content to Markdown (scripts/extract_markdown.js) and writes
  raw/NNN-<slug>.md with RawCapture frontmatter; NNN is the next free number.
- --images N saves the first N large content images to raw/img/NNN-<k>.<ext> and rewrites
  their links to the local copies. Pick N>0 only for pages with real product UI.
Requires: surf CLI connected to a browser. Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTRACTOR = HERE / "extract_markdown.js"
BLOCK_MARKERS = ("captcha", "verify you are human", "access denied", "sign in to continue",
                 "log in to continue", "enable javascript")
CHALLENGE = re.compile(r"just a moment|checking your browser|attention required|verify you are human|"
                       r"security check|are you a robot|captcha", re.I)
NOT_FOUND = re.compile(r"page not found|can.t be found|404|doesn.t exist|no longer available", re.I)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def surf(*args: str, timeout: int = 60) -> str:
    proc = subprocess.run(["surf", *args], capture_output=True, text=True, timeout=timeout,
                          check=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 or out.startswith("Error:"):
        raise RuntimeError(f"surf {' '.join(args[:3])} failed: {out.strip()[:300]}")
    return proc.stdout


def open_page(url: str, window_id: str | None) -> str:
    if window_id:
        try:
            surf("--window-id", window_id, "go", url)
        except RuntimeError as exc:  # slow pages: surf gives up waiting, the tab keeps loading
            if "timed out" not in str(exc):
                raise
            time.sleep(6)
    else:
        out = surf("window.new", url)
        found = re.search(r"\b(\d{6,})\b", out)
        if not found:
            raise RuntimeError(f"cannot parse window id from: {out.strip()[:200]}")
        window_id = found.group(1)
        print(f"window-id: {window_id}  (pass --window-id {window_id} next time)")
    time.sleep(4)
    return window_id


def extract(window_id: str) -> dict:
    raw = surf("--window-id", window_id, "js", "--file", str(EXTRACTOR), timeout=90).strip()
    value = json.loads(raw)
    return json.loads(value) if isinstance(value, str) else value


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return "-".join(slug.split("-")[:6]) or "page"


def next_number(raw_dir: Path) -> int:
    nums = [int(p.name[:3]) for p in raw_dir.glob("[0-9][0-9][0-9]-*.md")]
    return max(nums, default=0) + 1


def _exclusive_write(path: Path, data: bytes, study_dir: Path) -> None:
    """Create one contained output without replacing an existing path."""
    root = study_dir.absolute()
    target = path.absolute()
    try:
        if os.path.commonpath((str(root), str(target))) != str(root):
            raise ValueError("output path escapes study")
    except ValueError as exc:
        raise ValueError("output path escapes study") from exc
    try:
        relative_root = root.relative_to(Path(root.anchor))
        current = Path(root.anchor)
        for part in relative_root.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("study path is unsafe")
        relative = target.relative_to(root)
        for part in relative.parts[:-1]:
            current = current / part
            if current.is_symlink() or not current.is_dir():
                raise ValueError("output parent is unavailable or unsafe")
        if target.is_symlink():
            raise ValueError("output path is unsafe")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(str(target), flags, 0o666)
    except FileExistsError:
        raise
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


MAX_IMAGE_BYTES = 5_000_000
MAGIC = ((b"\x89PNG", ".png"), (b"GIF8", ".gif"), (b"\xff\xd8", ".jpg"), (b"RIFF", ".webp"))


def save_image(src: str, base: Path, window_id: str,
               study_dir: Path | None = None, created: list[Path] | None = None) -> Path | None:
    """Download an image (browser screenshot as fallback). Returns the saved path."""
    try:
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as resp:  # public http(s) image
            data = resp.read(MAX_IMAGE_BYTES + 1)
        ext = next((e for magic, e in MAGIC if data.startswith(magic)), None)
        if ext and 2000 < len(data) <= MAX_IMAGE_BYTES:
            dest = base.with_suffix(ext)
            if study_dir is None:
                dest.write_bytes(data)
            else:
                _exclusive_write(dest, data, study_dir)
                if created is not None:
                    created.append(dest)
            return dest
    except FileExistsError:
        raise
    except (OSError, ValueError):
        pass
    dest = base.with_suffix(".png")  # too big, unknown type or blocked: screenshot it
    try:
        staged = None
        try:
            surf("--window-id", window_id, "go", src)
            time.sleep(2)
            if study_dir is None:
                surf("--window-id", window_id, "screenshot", "--output", str(dest))
                return dest if dest.is_file() and not dest.is_symlink() else None
            fd, staged_name = tempfile.mkstemp(prefix=".capture-image-", suffix=".png", dir=str(dest.parent))
            os.close(fd)
            staged = Path(staged_name)
            surf("--window-id", window_id, "screenshot", "--output", str(staged))
            if not staged.is_file() or staged.is_symlink():
                return None
            _exclusive_write(dest, staged.read_bytes(), study_dir)
            if created is not None:
                created.append(dest)
            return dest
        finally:
            if staged is not None and staged.is_file() and not staged.is_symlink():
                staged.unlink()
    except FileExistsError:
        raise
    except ValueError:
        if study_dir is not None:
            raise
        return None
    except (RuntimeError, OSError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("research_dir", type=Path)
    ap.add_argument("url")
    ap.add_argument("--entity", default="")
    ap.add_argument("--slug", default="")
    ap.add_argument("--window-id", default=None)
    ap.add_argument("--images", type=int, default=0)
    ap.add_argument("--min-width", type=int, default=500)
    ap.add_argument("--by", default="agent via surf")
    a = ap.parse_args()

    raw_dir = a.research_dir / "raw"
    if not (a.research_dir / "brief.md").is_file() or (a.research_dir / "brief.md").is_symlink():
        sys.exit(f"{a.research_dir} is not a research folder (no safe brief.md); run new_research.py first")
    if raw_dir.is_symlink() or not raw_dir.is_dir():
        sys.exit("capture output is blocked: raw directory is unavailable or unsafe")
    image_dir = raw_dir / "img"
    if image_dir.is_symlink() or not image_dir.is_dir():
        sys.exit("capture output is blocked: image directory is unavailable or unsafe")

    window_id = open_page(a.url, a.window_id)
    page = extract(window_id)
    md, title = page["markdown"], page["title"].strip() or a.url
    if NOT_FOUND.search(title) or (len(md) < 800 and NOT_FOUND.search(md)):
        print(f"NOT SAVED: {a.url} looks like a 404 page ({title!r}). Find the real article "
              "with find_links.py (help center home, category or search page) instead of guessing.")
        return 2
    num = next_number(raw_dir)
    slug = a.slug or slugify(f"{a.entity} {title}" if a.entity else title)
    stem = f"{num:03d}-{slug}"

    low = md.lower()
    challenge = CHALLENGE.search(title) or (len(md) < 1500 and CHALLENGE.search(md))
    fidelity = ("blocked" if challenge or (len(md) < 1500 and any(m in low for m in BLOCK_MARKERS))
                else "partial" if len(md) < 500 else "full")
    if challenge:  # bot-check page: keep a stub, not the checker's text
        md = f"Blocked: the site showed a bot check ({title!r}); content not captured."
        page["images"] = []

    saved = []
    created_images: list[Path] = []
    wanted = [i for i in page["images"] if i["width"] >= a.min_width][: max(a.images, 0)]
    for k, img in enumerate(wanted, 1):
        try:
            dest = save_image(img["src"], raw_dir / "img" / f"{num:03d}-{k}", window_id,
                              a.research_dir, created_images)
        except (FileExistsError, OSError, ValueError):
            created_paths = [path.relative_to(a.research_dir).as_posix() for path in created_images]
            if created_paths:
                print("PARTIAL: image output blocked; created files preserved: " + ", ".join(created_paths))
            else:
                print("BLOCKED: image output already exists or output path is unsafe")
            return 3
        if dest:
            md = md.replace(f"]({img['src']})", f"](img/{dest.name})")
            saved.append(dest.name)
    if saved:  # leave the window on the article, not on the last image
        surf("--window-id", window_id, "go", page["url"])

    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    front = "\n".join([
        "---",
        "type: RawCapture",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"url: {json.dumps(page['url'])}",
        f"captured_at: {now}",
        f"captured_by: {json.dumps(a.by, ensure_ascii=False)}",
        f"entity: {json.dumps(a.entity)}",
        f"fidelity: {fidelity}",
        "---",
    ])
    out = raw_dir / f"{stem}.md"
    try:
        _exclusive_write(out, f"{front}\n\n# {title}\n\n{md}\n".encode("utf-8"), a.research_dir)
    except (FileExistsError, OSError, ValueError):
        created_paths = [path.relative_to(a.research_dir).as_posix() for path in created_images]
        if created_paths:
            print("PARTIAL: markdown output blocked; created files preserved: " + ", ".join(created_paths))
        else:
            print("BLOCKED: markdown output already exists or output path is unsafe")
        return 3

    print(f"saved {out}  chars={len(md)} fidelity={fidelity} images_saved={len(saved)}")
    rest = [i for i in page["images"] if i not in wanted and i["width"] >= a.min_width]
    if rest:
        print(f"{len(rest)} more large images not saved (rerun with a higher --images if they show UI)")
    if fidelity != "full":
        print("check the page: fidelity is not full — edit nothing in raw, note the limitation in the report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
