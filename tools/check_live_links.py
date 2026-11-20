#!/usr/bin/env python3
"""Strict static checks for the whole published tree.

Complements tools/check_links.py (which validates the verified/ subsite and its
sourced rows) by checking every HTML file in the repository for broken internal
links, duplicate element ids and stray build placeholders.

    python3 tools/check_live_links.py

Exit code 1 on any problem.
"""
import pathlib
import re
import sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "verified", "data"}

HREF = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"')
# API path templates such as /markets/{ticker} are legitimate, so a brace
# preceded by a slash or underscore is not treated as an unfinished placeholder.
PLACEHOLDER = re.compile(r"(?<![/_])\{[A-Za-z_]+\}|TODO|FIXME|Lorem ipsum|XXXX")
CODE_BLOCK = re.compile(r"<code>.*?</code>|<pre>.*?</pre>|<script\b.*?</script>", re.S)


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.dupes = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == "id" and v:
                if v in self.ids:
                    self.dupes.append(v)
                self.ids.append(v)


def html_files():
    for f in ROOT.rglob("*.html"):
        if any(part in SKIP_DIRS for part in f.relative_to(ROOT).parts):
            continue
        yield f


def main():
    problems = []
    files = sorted(html_files())
    checked = 0
    for path in files:
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        checked += len(HREF.findall(text))

        m = PLACEHOLDER.search(CODE_BLOCK.sub(" ", text))
        if m:
            problems.append(f"{rel}: unfinished placeholder {m.group(0)!r}")

        parser = IdCollector()
        parser.feed(text)
        for d in parser.dupes:
            problems.append(f"{rel}: duplicate id {d!r}")

        for href in HREF.findall(text):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if href.startswith("#"):
                if len(href) > 1 and href[1:] not in parser.ids:
                    problems.append(f"{rel}: dangling in-page anchor {href!r}")
                continue
            base = re.split(r"[?#]", href)[0]
            if not base:
                continue
            if not (path.parent / base).resolve().exists():
                problems.append(f"{rel}: broken link {href!r}")

    print(f"scanned {len(files)} html files, {checked} href/src attributes")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(" -", p)
        return 1
    print("no broken internal links, no duplicate ids, no placeholders")
    return 0


if __name__ == "__main__":
    sys.exit(main())
