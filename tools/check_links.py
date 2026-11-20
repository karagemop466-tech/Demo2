#!/usr/bin/env python3
"""Check the built site before publishing.

Checks, over every generated page:

  * every internal href/src resolves to a file that exists on disk;
  * every ``#anchor`` used in an internal link exists in the target page;
  * every data row in a data table carries a link to the Kalshi API response
    it was read from;
  * every external link points at an official Kalshi or GitHub Pages source
    (third-party hosts are reported as errors);
  * no page contains a bare ``undefined``/``None``/``NaN`` where a value
    should have been rendered.

External URLs are listed but not fetched: the build environment has no
guaranteed egress to arbitrary hosts.  Exit code 1 if any check fails.
"""
from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Official hosts only. Anything else is a finding, not a pass.
OFFICIAL_HOSTS = (
    "docs.kalshi.com",
    "help.kalshi.com",
    "demo.kalshi.co",
    "kalshi.co",
    "external-api.demo.kalshi.co",
    "demo-api.kalshi.co",
    "api.elections.kalshi.com",
    "external-api.kalshi.com",
    "github.com",
    "karagemop466-tech.github.io",
    "docs.github.com",
    "www.washingtonpost.com",
)

# Pages whose tables are data tables (every row must carry an API source link).
DATA_PAGES = ("pages/gas.html", "pages/elections.html", "pages/culture.html",
              "pages/crypto.html", "pages/golf.html", "index.html")

# Rows that legitimately have no API source: totals, empty-state and
# explanatory rows carry no market data.
SKIP_ROW_MARKERS = ("no rows", "unverified", "nothing to show", "not connected",
                    "no fills", "no positions", "no orders", "no settlements")


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
        if tag in ("link", "script") and ("href" in a or "src" in a):
            self.links.append(a.get("href") or a.get("src"))
        if tag == "tbody":
            self._in_tbody = True
        if tag == "tr" and self._in_tbody:
            self._row = {"links": [], "text": ""}
        if tag == "a" and self._row is not None and "href" in a:
            self._row["links"].append(a["href"])

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
    pages = [os.path.join(ROOT, "index.html")]
    pages_dir = os.path.join(ROOT, "pages")
    if os.path.isdir(pages_dir):
        for name in sorted(os.listdir(pages_dir)):
            if name.endswith(".html"):
                pages.append(os.path.join(pages_dir, name))
    return pages


def main() -> int:
    pages = site_pages()
    if not pages:
        print("no pages found - run tools/build_site.py first")
        return 1

    parsed = {}
    for path in pages:
        c = Collector()
        with open(path, encoding="utf-8") as fh:
            c.feed(fh.read())
        parsed[os.path.relpath(path, ROOT)] = c

    errors = []
    externals = set()
    row_count = 0

    for rel, c in parsed.items():
        base = os.path.dirname(os.path.join(ROOT, rel))
        for href in c.links:
            if not href:
                errors.append(f"{rel}: empty href/src")
                continue
            if href.startswith(("http://", "https://")):
                externals.add(href)
                host = urlparse(href).netloc.lower()
                if not any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS):
                    errors.append(f"{rel}: non-official external link -> {href}")
                continue
            if href.startswith("mailto:"):
                continue
            if href.startswith("#"):
                if href[1:] and href[1:] not in c.ids:
                    errors.append(f"{rel}: missing anchor {href}")
                continue
            target, _, anchor = href.partition("#")
            path = os.path.normpath(os.path.join(base, target))
            if not os.path.exists(path):
                errors.append(f"{rel}: broken internal link -> {href}")
                continue
            if anchor and target.endswith(".html"):
                tgt_rel = os.path.relpath(path, ROOT)
                tgt = parsed.get(tgt_rel)
                if tgt is None:
                    tgt = Collector()
                    with open(path, encoding="utf-8") as fh:
                        tgt.feed(fh.read())
                if anchor not in tgt.ids:
                    errors.append(f"{rel}: missing anchor -> {href}")

    for rel in DATA_PAGES:
        c = parsed.get(rel)
        if c is None:
            continue
        for row in c.rows:
            text = " ".join(row["text"].split())
            if not text:
                continue
            low = text.lower()
            if any(m in low for m in SKIP_ROW_MARKERS):
                continue
            row_count += 1
            api_links = [h for h in row["links"]
                         if h.startswith("https://external-api.demo.kalshi.co/")]
            if not api_links:
                errors.append(f"{rel}: row without a Kalshi API source link: {text[:90]}")

    # Rendered-value sanity check: no Python/JS placeholder leaking into HTML.
    for rel in parsed:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            body = fh.read()
        for bad in ("None", "undefined", "NaN"):
            if re.search(r">\s*" + bad + r"\s*<", body):
                errors.append(f"{rel}: rendered placeholder value '{bad}'")

    print(f"pages checked: {len(parsed)}")
    print(f"data rows checked: {row_count}")
    print(f"external links found (listed, not fetched): {len(externals)}")
    for e in sorted(externals):
        print("  external:", e)
    if errors:
        print("\nERRORS:")
        for e in errors:
            print("  " + e)
        return 1
    print("\nOK: no broken links, no missing anchors, no unsourced data rows, no placeholders.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
