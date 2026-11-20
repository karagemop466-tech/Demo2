#!/usr/bin/env python3
"""Check the built site in verified/ before publishing.

- Every internal href/src resolves to a file in verified/.
- Every #anchor used in an internal link exists in the target page.
- Every data row on a category page has a source link to the Kalshi API.
- Every external link is listed (external URLs are not fetched by this script).
Exit code 1 if any internal link or row check fails.
"""
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = os.path.join(ROOT, "verified")


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.rows = [], set(), []
        self._in_tbody = False
        self._row = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag in ("a",) and "href" in a:
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


def main():
    pages = sorted(f for f in os.listdir(DOCS) if f.endswith(".html"))
    parsed = {}
    for p in pages:
        c = Collector()
        with open(os.path.join(DOCS, p), encoding="utf-8") as fh:
            c.feed(fh.read())
        parsed[p] = c

    errors, externals = [], set()
    for p, c in parsed.items():
        for href in c.links:
            if href.startswith(("http://", "https://")):
                externals.add(href)
                continue
            if href.startswith(("mailto:", "#")) and href.startswith("#"):
                if href[1:] and href[1:] not in c.ids:
                    errors.append(f"{p}: missing anchor {href}")
                continue
            target, _, anchor = href.partition("#")
            path = os.path.normpath(os.path.join(DOCS, target))
            if not os.path.exists(path):
                errors.append(f"{p}: broken internal link -> {href}")
                continue
            if anchor and target.endswith(".html"):
                tgt = parsed.get(os.path.basename(target))
                if tgt is None or anchor not in tgt.ids:
                    errors.append(f"{p}: missing anchor -> {href}")

    category_pages = ["gas-prices.html", "elections.html", "culture.html", "crypto.html", "golf.html"]
    row_count = 0
    for p in category_pages:
        for row in parsed[p].rows:
            if not row["text"].strip() or "No rows" in row["text"]:
                continue
            row_count += 1
            api_links = [h for h in row["links"] if h.startswith("https://external-api.demo.kalshi.co/")]
            if not api_links:
                errors.append(f"{p}: row without Kalshi API source link: {row['text'][:80].strip()}")

    print(f"pages checked: {len(pages)}")
    print(f"category data rows checked: {row_count}")
    print(f"external links found (not fetched here): {len(externals)}")
    for e in sorted(externals):
        print("  external:", e)
    if errors:
        print("\nERRORS:")
        for e in errors:
            print("  " + e)
        return 1
    print("\nOK: no broken internal links, anchors, or unsourced rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
