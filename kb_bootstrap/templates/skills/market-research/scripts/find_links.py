#!/usr/bin/env python3
"""List real article links on a page (help center home, category, search results).

Usage:
  find_links.py <url> [--match search,filter,speaker] [--window-id N] [--limit 40]
  find_links.py "https://help.example.com/search?q=speaker" --window-id N

Prints "<link text> | <url>" for same-site links whose text or URL contains any --match
keyword (all same-site links if omitted). Use it to discover article URLs instead of
guessing them — guessed URLs usually end in "Page not found". Nothing is written to disk.
Requires: surf CLI. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

JS = """
var out = [];
Array.from(document.querySelectorAll('a[href]')).forEach(function (a) {
  var t = (a.innerText || a.getAttribute('aria-label') || '').trim().split(String.fromCharCode(10))[0];
  var href = a.href.split(String.fromCharCode(35))[0];
  if (t && href.indexOf('http') === 0) out.push([t.slice(0, 120), href]);
});
return JSON.stringify(out);
"""


def surf(*args: str, timeout: int = 60) -> str:
    proc = subprocess.run(["surf", *args], capture_output=True, text=True, timeout=timeout,
                          check=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 or out.startswith("Error:"):
        raise RuntimeError(out.strip()[:300])
    return proc.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--match", default="")
    ap.add_argument("--window-id", default=None)
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()

    if a.window_id:
        try:
            surf("--window-id", a.window_id, "go", a.url)
        except RuntimeError as exc:
            if "timed out" not in str(exc):
                raise
        wid = a.window_id
    else:
        found = re.search(r"\b(\d{6,})\b", surf("window.new", a.url))
        if not found:
            raise SystemExit("cannot parse window id from surf window.new")
        wid = found.group(1)
        print(f"window-id: {wid}")
    time.sleep(4)

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(JS)
    value = json.loads(surf("--window-id", wid, "js", "--file", fh.name).strip())
    links = json.loads(value) if isinstance(value, str) else value

    site = urlsplit(a.url).netloc.split(".", 1)[-1] if a.url.count(".") > 1 else urlsplit(a.url).netloc
    keys = [k.strip().lower() for k in a.match.split(",") if k.strip()]
    seen, shown = set(), 0
    for text, href in links:
        if site not in urlsplit(href).netloc or href in seen:
            continue
        if keys and not any(k in (text + " " + href).lower() for k in keys):
            continue
        seen.add(href)
        print(f"{text} | {href}")
        shown += 1
        if shown >= a.limit:
            break
    if not shown:
        print("no matching links — try the site's search page or another keyword")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
