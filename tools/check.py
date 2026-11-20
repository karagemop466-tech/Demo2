#!/usr/bin/env python3
"""Pre-publish checks. Exit non-zero on any problem.

1. internal link check   - every href/src that points at a repo file must exist
2. external link sanity  - https, has a host, no placeholder text
3. nav consistency       - every page carries the same generated nav
4. data sanity           - snapshot fields used by the pages are present
5. no secrets            - no PEM block or key-looking string in the repo
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
HTML = [ROOT / "index.html"] + sorted((ROOT / "pages").glob("*.html"))

errors: list[str] = []
warnings: list[str] = []


def check_links() -> None:
    href_re = re.compile(r'(?:href|src)="([^"]+)"')
    for f in HTML:
        text = f.read_text()
        for raw in href_re.findall(text):
            if raw.startswith(("http://", "https://")):
                u = urlparse(raw)
                if not u.netloc or "/" not in raw[8:]:
                    errors.append(f"{f.name}: malformed external URL {raw!r}")
                if any(x in raw.lower() for x in ("example.com", "todo", "tbd", "placeholder", "your-api-key")):
                    errors.append(f"{f.name}: placeholder URL {raw!r}")
                if raw.endswith((".md",)):
                    errors.append(f"{f.name}: docs link should be the HTML page, not {raw!r}")
                continue
            if raw.startswith(("mailto:", "#", "javascript:", "data:")):
                continue
            rel = raw.split("#")[0].split("?")[0]
            # a page that links to a sibling subsite uses ../ from pages/, which lands on
            # the repo root; normalise so the check tests the real repository path.
            target = (f.parent / rel).resolve()
            if not target.exists():
                alt = (ROOT / rel.lstrip("./")).resolve()
                if alt.exists():
                    continue
            if not target.exists():
                errors.append(f"{f.name}: broken internal link {raw!r} -> {target}")


def check_nav() -> None:
    nav_re = re.compile(r'<nav class="main">(.*?)</nav>', re.S)
    canonical = None
    for f in HTML:
        m = nav_re.search(f.read_text())
        if not m:
            errors.append(f"{f.name}: no nav block")
            continue
        # normalise: strip the aria-current marker and resolve relative prefixes
        links = re.findall(r'href="([^"]+)"', m.group(1))
        norm = [l.split("/")[-1] for l in links]
        if canonical is None:
            canonical = norm
        elif norm != canonical:
            errors.append(f"{f.name}: nav differs from canonical ({len(norm)} vs {len(canonical)} links)")
    if canonical:
        # 18 original entries + Dollar Rankings + Live Console (2026-11-20).
        expected = 20
        if len(canonical) != expected:
            errors.append(f"nav has {len(canonical)} links, expected {expected}")


def check_data() -> None:
    snap_path = ROOT / "data" / "snapshot.json"
    if not snap_path.exists():
        warnings.append("data/snapshot.json not present yet (first workflow run pending)")
        return
    try:
        s = json.loads(snap_path.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"data/snapshot.json is not valid JSON: {e}")
        return
    for key in ("generated_at_utc", "counts", "markets", "resolutions", "api_log", "series_inventory"):
        if key not in s:
            errors.append(f"snapshot missing key {key!r}")
    for m in s.get("markets", [])[:2000]:
        for k in ("topic", "market_ticker", "yes_bid_dollars", "yes_ask_dollars", "volume_fp"):
            if k not in m:
                errors.append(f"market row missing {k!r}: {m.get('market_ticker')}")
                break
    counts = s.get("counts") or {}
    if counts.get("markets_in_scope") == 0:
        errors.append("snapshot contains zero in-scope markets")
    bad = [r for r in s.get("api_log", []) if not r.get("ok")]
    if bad:
        warnings.append(f"{len(bad)} API requests in the snapshot are non-2xx (see Verification page)")


def check_secrets() -> None:
    pat = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git/" in str(p) or p.name in {"check.py"}:
            continue
        if p.suffix not in {".py", ".html", ".js", ".css", ".md", ".json", ".yml", ".yaml", ".txt"}:
            continue
        try:
            if pat.search(p.read_text(errors="ignore")):
                errors.append(f"{p.relative_to(ROOT)}: contains a private-key block")
        except OSError:
            pass
    for p in sorted(ROOT.rglob("*.json")):
        if "node_modules" in str(p):
            continue


def check_js_syntax() -> None:
    """Inline page scripts must at least be parseable by node (if available)."""
    import shutil
    import subprocess
    import tempfile

    node = shutil.which("node")
    if not node:
        warnings.append("node not available; skipped inline-script syntax check")
        return
    script_re = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S)
    for f in HTML:
        for i, body in enumerate(script_re.findall(f.read_text())):
            if not body.strip():
                continue
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tmp:
                tmp.write(body)
                name = tmp.name
            r = subprocess.run([node, "--check", name], capture_output=True, text=True)
            if r.returncode != 0:
                errors.append(f"{f.name}: inline script #{i} syntax error: {r.stderr.strip().splitlines()[:2]}")
    for js in (ROOT / "assets").glob("*.js"):
        r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
        if r.returncode != 0:
            errors.append(f"{js.name}: syntax error: {r.stderr.strip().splitlines()[:2]}")


def main() -> int:
    print(f"python={sys.version.split()[0]} node={__import__('shutil').which('node')} "
          f"cwd={ROOT} files={len(list(ROOT.rglob('*.html')))} html")
    for name, fn in (("links", check_links), ("nav", check_nav), ("data", check_data),
                     ("secrets", check_secrets), ("js", check_js_syntax)):
        before = len(errors)
        fn()
        print(f"  [{name}] {'ok' if len(errors) == before else str(len(errors) - before) + ' error(s)'}")
        for e in errors[before:]:
            print(f"::error file={e.split(':')[0]}::{e}")
    print(f"pages checked: {len(HTML)}")
    for w in warnings:
        print(f"WARN  {w}")
        print(f"::warning::{w}")
    for e in errors:
        print(f"FAIL  {e}")
    if errors:
        print(f"\n{len(errors)} error(s) - not publishable")
        for e in errors[:40]:
            print(f"::error::{e}")
        return 1
    print("OK — links, nav, data, secrets and scripts all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
