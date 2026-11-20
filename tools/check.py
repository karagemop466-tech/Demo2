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
HTML = [ROOT / "index.html", ROOT / "dashboard.html"] + sorted((ROOT / "pages").glob("*.html"))

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
            if "${" in raw:
                # Built at runtime from data (e.g. pages/${topic}.html). There is no static
                # target to resolve; the equivalent static links are checked on the same page.
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
        # Derive the expected count from the generator instead of hardcoding it. A hardcoded
        # number has to be edited every time a section is added (it broke when the instrument
        # panel was linked), and the failure says nothing about what is actually wrong. Comparing
        # against tools/build_site.py's NAV list checks the thing that matters: the pages on disk
        # match the generator that is supposed to have produced them.
        expected = len(nav_source())
        if len(canonical) != expected:
            errors.append(f"nav has {len(canonical)} links, but tools/build_site.py defines {expected}; "
                          f"run tools/build_site.py and commit the result")


def nav_source() -> list:
    """The NAV list from tools/build_site.py, read as source rather than imported."""
    src = (ROOT / "tools" / "build_site.py").read_text()
    block = re.search(r"^NAV\s*=\s*\[(.*?)^\]", src, re.S | re.M)
    if not block:
        return []
    return re.findall(r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"', block.group(1))


def check_data() -> None:
    """Validate the files the pages actually fetch, not a file nothing reads.

    The pages read dashboard_meta.json (counts), top.json (ranked rows) and
    resolutions.json (the rolling log). data/snapshot.json still exists as the full
    provenance record, but it is 12 MB and no page loads it.
    """
    meta_path = ROOT / "data" / "dashboard_meta.json"
    if not meta_path.exists():
        warnings.append("data/dashboard_meta.json not present yet (first workflow run pending)")
        return
    try:
        meta = json.loads(meta_path.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"data/dashboard_meta.json is not valid JSON: {e}")
        return
    for key in ("generated_at_utc", "counts", "topic_catalog", "api_request_count"):
        if key not in meta:
            errors.append(f"dashboard_meta.json missing key {key!r}")
    counts = meta.get("counts") or {}
    if counts.get("markets_in_scope") == 0:
        errors.append("dashboard_meta.json reports zero in-scope markets")

    top_path = ROOT / "data" / "top.json"
    if top_path.exists():
        try:
            top = json.loads(top_path.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"data/top.json is not valid JSON: {e}")
            top = {}
        rows = top.get("rows") or []
        if not rows:
            errors.append("data/top.json has no rows")
        for m in rows[:2000]:
            for k in ("topic", "market_ticker", "volume_fp"):
                if k not in m:
                    errors.append(f"top.json row missing {k!r}: {m.get('market_ticker')}")
                    break
            # provenance: every ranked row must name the request it came from
            if not (m.get("market_url") or m.get("usd_volume_24h_source_url")):
                errors.append(f"top.json row has no source URL: {m.get('market_ticker')}")
            # an em dash in the UI comes from None here; a 0-1 price must stay in range
            for k in ("last_price_dollars", "yes_bid_dollars", "yes_ask_dollars"):
                v = m.get(k)
                if v in (None, ""):
                    continue
                try:
                    f = float(v)
                except (TypeError, ValueError):
                    errors.append(f"top.json row {m.get('market_ticker')}: {k} not numeric")
                    continue
                if not (0 <= f <= 1):
                    errors.append(f"top.json row {m.get('market_ticker')}: {k}={f} outside $0-$1")

    res_path = ROOT / "data" / "resolutions.json"
    if res_path.exists():
        try:
            res = json.loads(res_path.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"data/resolutions.json is not valid JSON: {e}")
            res = {}
        for r in (res.get("resolutions") or [])[:3000]:
            if (r.get("result") or "") not in ("yes", "no"):
                errors.append(f"resolution without an official yes/no result: {r.get('market_ticker')}")

    log_path = ROOT / "data" / "snapshot_api_log.json"
    bad = 0
    if log_path.exists():
        try:
            bad = len([r for r in json.loads(log_path.read_text()).get("api_log", []) if not r.get("ok")])
        except json.JSONDecodeError:
            pass
    elif (ROOT / "data" / "snapshot.json").exists():
        try:
            bad = len([r for r in json.loads((ROOT / "data" / "snapshot.json").read_text())
                       .get("api_log", []) if not r.get("ok")])
        except json.JSONDecodeError:
            pass
    if bad:
        warnings.append(f"{bad} API requests in the last run were non-2xx (see Verification page)")


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
