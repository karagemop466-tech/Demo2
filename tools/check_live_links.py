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
PLACEHOLDER = re.compile(r"(?<![/_?=&])\{[A-Za-z_]+\}|TODO|FIXME|Lorem ipsum|XXXX")
# A brace only survives in visible text (URL-pattern attributes are handled by
# ATTR_VALUE below), so any remaining one is an unfinished placeholder.
PLACEHOLDER_TEXT = re.compile(r"\{[A-Za-z_]+\}")
# Bodies of <script>, <code> and <pre> are not markup: template literals and code
# samples there would otherwise look like broken links or unfinished placeholders.
# The opening <script src="..."> tag is kept so asset references are still checked.
CODE_BLOCK = re.compile(r"<code>.*?</code>|<pre>.*?</pre>", re.S)
SCRIPT_BODY = re.compile(r"(<script\b[^>]*>).*?</script>", re.S)


# An attribute value that contains a brace is an illustrative API URL pattern
# (href=".../markets/{ticker}"), which is documentation, not stray build output.
ATTR_VALUE = re.compile(r'(\b(?:href|src)\s*=\s*")([^"]*)(")')


def strip_code(text: str) -> str:
    text = CODE_BLOCK.sub(" ", SCRIPT_BODY.sub(r"\1", text))
    # Blank the brace-bearing attribute VALUE only, keeping the quotes so the href
    # scanner still sees (and then ignores) the attribute instead of a broken token.
    return ATTR_VALUE.sub(lambda m: m.group(1) + ("https://api-pattern.invalid" if "{" in m.group(2) else m.group(2)) + m.group(3), text)


# A sentence that ends on a preposition ("listed on .") or an empty "()" is the
# signature of a link that was stripped out and never replaced. Cheap to detect,
# and it is exactly the defect this checker missed on its first run.
# Require whitespace *before* the full stop: "listed on ." is broken, while
# "each value is filled in." is ordinary English.
# "the files in .github/workflows." is a directory path ending a sentence, not a stripped
# link. Require the full stop to stand alone (not part of a path or number).
DANGLING = re.compile(r"\b(?:on|in|at|from|per|as|see|below|above)\s+\.(?!\w)|<\s*\.|>\s*\(\s*\)")


def check_dangling(rel, scan, problems):
    # Replace code bodies with a token rather than nothing, otherwise
    # "sees the market's <code>result</code> in <code>GET ...</code>." collapses to
    # "sees the market's in ." and looks like a stripped link.
    text = re.sub(r"<code>.*?</code>|<pre>.*?</pre>", " CODE ", scan, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    m = DANGLING.search(text)
    if m:
        problems.append(f"{rel}: dangling reference near {text[max(0, m.start()-45):m.end()+10]!r}")


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
        checked += len(HREF.findall(strip_code(text)))

        scan = strip_code(text)

        check_dangling(rel, text, problems)

        m = PLACEHOLDER.search(scan)
        if m:
            problems.append(f"{rel}: unfinished placeholder {m.group(0)!r}")
        else:
            m2 = PLACEHOLDER_TEXT.search(scan)
            if m2:
                problems.append(f"{rel}: unfinished placeholder {m2.group(0)!r}")

        parser = IdCollector()
        parser.feed(text)
        for d in parser.dupes:
            problems.append(f"{rel}: duplicate id {d!r}")

        for href in HREF.findall(scan):
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
