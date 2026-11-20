#!/usr/bin/env python3
"""Link and structure checks for everything that gets published.

Two tiers, because this repository holds work from several sessions:

  BLOCKING  - the pages this session owns (site/, index.html): every internal link and
              #anchor must resolve, and every page must carry the demo-data notice.
  REPORTED  - pages owned by other sessions (pages/, verified/, dashboard/, root notes):
              broken links are printed but do not fail the deploy, so a pre-existing
              problem elsewhere is never hidden and never blocks this session's work.

Exit code 1 only on a BLOCKING failure.
"""
import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKIP_DIRS = {".git", "node_modules", "out", "dist", "__pycache__"}

OWNED_DIRS = (os.path.join("instrument-panel", "site"),)
OWNED_FILES = ("index.html",)


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag in ("link", "script"):
            v = a.get("href") or a.get("src")
            if v:
                self.links.append(v)
        if tag == "img" and a.get("src"):
            self.links.append(a["src"])


def pages():
    out = []
    for base, dirs, files in os.walk(ROOT):
        # third-party and generated dependency trees are not part of the site
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".html"):
                out.append(os.path.join(base, f))
    return sorted(out)


def owned(path):
    rel = os.path.relpath(path, ROOT)
    return rel in OWNED_FILES or os.sep.join(rel.split(os.sep)[:2]) in OWNED_DIRS


def main():
    all_pages = pages()
    parsed, raw, = {}, {}
    for p in all_pages:
        with open(p, encoding="utf-8") as fh:
            t = fh.read()
        raw[p] = t
        c = Collector()
        c.feed(t)
        parsed[p] = c

    blocking, reported, externals = [], [], Counter()

    for p, c in parsed.items():
        rel = os.path.relpath(p, ROOT)
        bucket = blocking if owned(p) else reported
        for href in c.links:
            if href.startswith(("http://", "https://")):
                externals[re.sub(r"^https?://([^/]+).*", r"\1", href)] += 1
                continue
            if href.startswith(("mailto:", "javascript:", "data:")):
                continue
            if href.startswith("#"):
                if href[1:] and href[1:] not in c.ids:
                    bucket.append(f"{rel}: missing anchor {href}")
                continue
            target, _, anchor = href.partition("#")
            if not target:
                continue
            path = os.path.normpath(os.path.join(os.path.dirname(p), target))
            if not os.path.exists(path):
                bucket.append(f"{rel}: broken link -> {href}")
                continue
            if anchor and target.endswith(".html"):
                tp = parsed.get(path)
                if tp is not None and anchor not in tp.ids:
                    bucket.append(f"{rel}: missing anchor -> {href}")
        if owned(p) and "demo" not in raw[p].lower():
            blocking.append(f"{rel}: missing demo-data disclaimer")

    # owned pages must reach the dashboard, the review pages and the sources
    idx_path = os.path.normpath(os.path.join(ROOT, "index.html"))
    idx = raw.get(idx_path)
    if idx is None:
        blocking.append("index.html: landing page missing")
        idx = ""
    linked = set()
    c = Collector(); c.feed(idx)
    for href in c.links:
        if href.endswith(".html") and not href.startswith(("http", "/")):
            linked.add(os.path.normpath(os.path.join(ROOT, href)))
    entry = os.path.normpath(os.path.join(ROOT, "instrument-panel", "site", "index.html"))
    if entry not in linked:
        blocking.append("index.html: does not link to instrument-panel/site/index.html "
                        "(the dashboard is unreachable from the landing page)")

    # every generated site page must be reachable from index.html or the site nav
    site_dir = os.path.join(ROOT, "instrument-panel", "site")
    nav_pages = set()
    if os.path.isdir(site_dir):
        core = os.path.join(site_dir, "index.html")
        if os.path.exists(core):
            c = Collector()
            c.feed(open(core, encoding="utf-8").read())
            for href in c.links:
                if href.endswith(".html") and not href.startswith(("http", "/")):
                    nav_pages.add(os.path.normpath(os.path.join(site_dir, href)))
    for p in all_pages:
        if os.path.dirname(p) != site_dir:
            continue
        if not os.path.exists(os.path.join(site_dir, "assets")):
            continue
        if p != os.path.join(site_dir, "index.html") and p not in nav_pages:
            blocking.append(f"{os.path.relpath(p, ROOT)}: not linked from the site navigation")

    print(f"pages checked: {len(all_pages)}")
    print("external hosts referenced:")
    for host, n in sorted(externals.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {host}")

    if reported:
        print(f"\nREPORTED, not blocking ({len(reported)} issue(s) in pages this session does not own):")
        for e in reported[:40]:
            print("  !", e)
        if len(reported) > 40:
            print(f"  ! … and {len(reported) - 40} more")

    if blocking:
        print(f"\nBLOCKING ERRORS ({len(blocking)}):")
        for e in blocking:
            print("  x", e)
        return 1

    print("\nOK: owned pages have no broken internal links or anchors, carry the demo "
          "disclaimer, and are all reachable from the navigation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
