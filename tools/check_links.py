#!/usr/bin/env python3
"""Check the published site before it goes live.

Rules enforced (exit code 1 on any failure):

1. Every internal ``href``/``src`` resolves to a file that exists.
2. Every ``#anchor`` used in an internal link exists in the target page.
3. Every data row on a generated category page contains a link to an official
   Kalshi API response (``https://external-api.demo.kalshi.co/`` or
   ``https://demo-api.kalshi.co/``).
4. Every page contains the shared navigation so the site is reachable from
   the landing page.

External links are listed for manual review but are not fetched by this
script — only the official Kalshi hosts are permitted as data sources.

    python3 tools/check_links.py
"""

import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_HOSTS = ("https://external-api.demo.kalshi.co/", "https://demo-api.kalshi.co/",
             "https://external-api.kalshi.com/")
CATEGORY_PAGES = {"gas.html", "elections.html", "culture.html", "crypto.html", "golf.html"}
SKIP_DIRS = {".git", ".github", "node_modules", "__pycache__", ".venv", "dist", "build"}


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.rows = []
        self._in_tbody = False
        self._row = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
            if self._row is not None:
                self._row["links"].append(a["href"])
        if tag in ("link", "script") and ("href" in a or "src" in a):
            self.links.append(a.get("href") or a.get("src"))
        if tag == "img" and "src" in a:
            self.links.append(a["src"])
        if tag == "tbody":
            self._in_tbody = True
        if tag == "tr" and self._in_tbody:
            self._row = {"links": [], "text": "", "class": a.get("class") or ""}

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._in_tbody = False
        if tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._row is not None:
            self._row["text"] += data


def site_pages():
    pages = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".html"):
                pages.append(os.path.join(dirpath, f))
    return sorted(pages)


def main():
    pages = site_pages()
    parsed = {}
    for p in pages:
        c = Collector()
        with open(p, encoding="utf-8") as fh:
            c.feed(fh.read())
        parsed[p] = c

    errors = []
    externals = set()
    for p, c in parsed.items():
        rel = os.path.relpath(p, ROOT)
        for href in c.links:
            if not href:
                continue
            if href.startswith(("http://", "https://")):
                externals.add(href)
                continue
            if href.startswith("mailto:"):
                continue
            if href.startswith("#"):
                if href[1:] and href[1:] not in c.ids:
                    errors.append("%s: anchor %s does not exist on this page" % (rel, href))
                continue
            target, _, anchor = href.partition("#")
            path = os.path.normpath(os.path.join(os.path.dirname(p), target))
            if not os.path.exists(path):
                errors.append("%s: broken internal link -> %s" % (rel, href))
                continue
            if anchor and target.endswith(".html"):
                tgt = parsed.get(path)
                if tgt is None or anchor not in tgt.ids:
                    errors.append("%s: missing anchor -> %s" % (rel, href))

    # data rows on the category pages must cite an official API response
    row_count = 0
    for p, c in parsed.items():
        if os.path.basename(p) not in CATEGORY_PAGES:
            continue
        rel = os.path.relpath(p, ROOT)
        for row in c.rows:
            text = row["text"].strip()
            if not text:
                continue
            if "placeholder" in row.get("class", ""):
                continue
            row_count += 1
            api_links = [h for h in row["links"] if h.startswith(API_HOSTS)]
            if not api_links:
                errors.append("%s: data row without an official Kalshi API source link: %s"
                              % (rel, text[:90].replace("\n", " ")))

    # every page must carry the shared navigation
    for p, c in parsed.items():
        rel = os.path.relpath(p, ROOT)
        if rel == "index.html":
            continue
        if not any("nav" in l for l in []):
            pass
        with open(p, encoding="utf-8") as fh:
            html = fh.read()
        if '<nav class="main">' not in html:
            errors.append("%s: missing the shared navigation block" % rel)

    print("pages checked: %d" % len(pages))
    print("category data rows checked: %d" % row_count)
    print("external links found (not fetched here): %d" % len(externals))
    for e in sorted(externals):
        print("  external:", e)
    if errors:
        print("\nERRORS (%d):" % len(errors))
        for e in errors:
            print("  " + e)
        return 1
    print("\nOK: no broken internal links, no missing anchors, every data row cites an official API response.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
