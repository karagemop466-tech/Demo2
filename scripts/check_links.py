#!/usr/bin/env python3
"""
check_links.py — Link verification for the static site.

Modes:
  python3 scripts/check_links.py
      Internal links only: every href/src in every *.html must resolve to an
      existing file in the repo (relative links only — root-absolute paths
      like /foo.html break on GitHub project pages and are rejected), and
      #fragment targets must exist as id= anchors in the target file.
  python3 scripts/check_links.py --external
      Also issues HEAD/GET requests to every unique http(s) link and fails on
      any non-2xx/3xx. Used by the Pages build workflow (runner has network).

Exit code 0 = all links OK, 1 = problems found (printed line by line).
"""
import os
import re
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTERNAL = "--external" in sys.argv

HREF_RE = re.compile(r'''(?:href|src)\s*=\s*["']([^"'#][^"']*)["']''', re.I)
ID_RE = re.compile(r'''\sid\s*=\s*["']([^"']+)["']''', re.I)


def html_files():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".github", "_site", "node_modules")]
        for fn in filenames:
            if fn.endswith(".html"):
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def ids_in(path):
    try:
        with open(path, encoding="utf-8") as f:
            return set(ID_RE.findall(f.read()))
    except OSError:
        return set()


def main():
    problems = []
    external_urls = set()
    files = html_files()
    checked = 0

    for path in files:
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        for url in HREF_RE.findall(content):
            checked += 1
            if url.startswith(("mailto:", "javascript:", "data:", "tel:")):
                continue
            if "${" in url:
                continue  # JS template literal, resolved at runtime
            if url.startswith(("http://", "https://")):
                external_urls.add(url)
                continue
            if url.startswith("/"):
                problems.append(f"{rel}: root-absolute link breaks on project pages: {url}")
                continue
            target, _, frag = url.partition("#")
            target_path = os.path.normpath(os.path.join(os.path.dirname(path), target)) if target else path
            if not os.path.exists(target_path):
                problems.append(f"{rel}: missing internal target: {url} -> {target_path}")
                continue
            if frag and target_path.endswith(".html"):
                if frag not in ids_in(target_path):
                    # Runtime-rendered anchors: some pages build rows from JS data
                    # arrays (id: 'FLAG-04'). Accept if the target directory's JS
                    # declares that id, so the deep link resolves after render.
                    js_dir = os.path.dirname(target_path)
                    runtime = False
                    for jroot, _jdirs, jfiles in os.walk(js_dir):
                        for fn in jfiles:
                            if fn.endswith(".js"):
                                try:
                                    with open(os.path.join(jroot, fn), encoding="utf-8") as jf:
                                        if re.search(r"id\s*:\s*['\"]" + re.escape(frag) + "['\"]", jf.read()):
                                            runtime = True
                                            break
                                except OSError:
                                    pass
                        if runtime:
                            break
                    if not runtime:
                        problems.append(f"{rel}: missing anchor #{frag} in {os.path.relpath(target_path, ROOT)}")

    print(f"internal: checked {checked} references across {len(files)} HTML files")

    if EXTERNAL:
        print(f"external: probing {len(external_urls)} unique URLs")
        for url in sorted(external_urls):
            ok = False
            last = ""
            for method in ("HEAD", "GET"):
                try:
                    req = urllib.request.Request(url, method=method,
                                                 headers={"User-Agent": "Demo2-link-check/1.0"})
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        ok = 200 <= resp.status < 400
                        last = f"HTTP {resp.status}"
                        break
                except urllib.error.HTTPError as e:
                    last = f"HTTP {e.code}"
                    if e.code in (403, 405) and method == "HEAD":
                        continue  # some servers reject HEAD; retry as GET
                    ok = 200 <= e.code < 400
                    break
                except Exception as e:  # noqa: BLE001
                    last = str(e)
                    break
            if not ok:
                problems.append(f"external link failed: {url} ({last})")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  FAIL {p}")
        return 1
    print("\nAll links OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
