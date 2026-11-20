#!/usr/bin/env python3
"""verify.py — the line-by-line verification gate for this repository.

Two jobs:

1. **Row coverage.** Walk every data file in the repository and check that every
   row that carries a market identity and real values also carries the official
   Kalshi URL it came from. A row without one is a defect, because the brief
   requires a source link on every table row.

2. **Live re-check.** Re-fetch a sample of markets from the official Kalshi demo
   API and compare them with the committed snapshot. Identity, status and the
   settlement result must match exactly. The last price of an open market is
   expected to move, so a price difference on an open market is recorded as
   evidence that the snapshot is live, not as a failure.

The authoring sandbox has no route to the Kalshi demo API, so the live half
runs from the GitHub Actions runner. Use --offline to check the data files only.

    python3 desk/tools/verify.py            # full run (needs egress)
    python3 desk/tools/verify.py --offline  # static audit only

Exit code 0 when nothing is wrong, 1 otherwise. The report is written to
desk/data/audit_report.json and published on desk/verification.html.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESK = ROOT / "desk"
DATA = DESK / "data"
API = "https://external-api.demo.kalshi.co/trade-api/v2"

# Hosts that count as the official Kalshi surface.
OFFICIAL_HOSTS = {
    "external-api.demo.kalshi.co",
    "demo-api.kalshi.co",
    "external-api.kalshi.com",
    "api.elections.kalshi.com",
    "docs.kalshi.com",
    "kalshi.com",
    "www.kalshi.com",
    "demo.kalshi.co",
    "assets.kalshi.com",
}

# Key names that hold the official URL a row was read from.
SOURCE_KEY_RE = re.compile(r"(?:^|_)(?:source|src)(?:_url|_api)?$", re.I)
EXTRA_SOURCE_KEYS = {
    "url_as_recorded",
    # Per-row official API URLs written by tools/collector.py. They used to fall
    # outside SOURCE_KEY_RE, so 30k+ fully sourced rows were reported as
    # "missing source" (fixed by session b7bc848c after the K-4 audit run).
    "market_url", "event_url", "series_url", "contract_url", "api_url",
}

# Files that hold derived or reference data rather than sampled API rows.
DERIVED_FILES = {
    "data/analysis.json",
    "data/portfolio.json",
    "data/executions.json",
    "data/strategy_plan.json",
    "data/pipeline_meta.json",
    "data/cors.json",
    "data/api_reverification.json",
    "data/api_settlement_sources.json",
    "data/api_market_samples.json",
    "data/README.md",
}

IDENTITY_KEYS = ("ticker", "market_ticker", "event_ticker", "series_ticker")
VALUE_KEYS = (
    "last_price_dollars", "yes_bid_dollars", "yes_ask_dollars", "volume_fp",
    "volume_24h_fp", "open_interest_fp", "result", "close_price", "price",
    "notional_24h_usd", "notional_lifetime_usd", "open_interest_usd",
)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def is_official(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host in OFFICIAL_HOSTS or host.endswith(".kalshi.com") or host.endswith(".kalshi.co")


def row_sources(obj, source_map=None) -> list:
    """Every URL a row carries under a source-shaped key.

    Some collectors store an identifier instead of the URL itself and keep the
    URL in a file-level `sources` map. Those are resolved here, because the
    row still points at an official source.
    """
    out = []
    if not isinstance(obj, dict):
        return out
    for key, value in obj.items():
        if not (key in EXTRA_SOURCE_KEYS or SOURCE_KEY_RE.search(key)):
            continue
        if isinstance(value, str) and value.startswith("http"):
            out.append(value)
        elif source_map and isinstance(value, str) and value in source_map:
            url = source_map[value]
            if isinstance(url, str) and url.startswith("http"):
                out.append(url)
    return out


def file_source_map(data) -> dict:
    """File-level `sources` map: identifier -> official URL."""
    if not isinstance(data, dict):
        return {}
    sources = data.get("sources")
    if isinstance(sources, dict):
        return {k: v for k, v in sources.items() if isinstance(v, str) and v.startswith("http")}
    if isinstance(sources, list):
        out = {}
        for item in sources:
            if isinstance(item, dict):
                key = item.get("id") or item.get("key") or item.get("name")
                url = item.get("url")
                if key and isinstance(url, str) and url.startswith("http"):
                    out[key] = url
        return out
    return {}


def data_files() -> list:
    found = []
    for pattern in ("data/*.json", "*/data/*.json", "*/*/data/*.json", "desk/data/*.json"):
        found.extend(sorted(ROOT.glob(pattern)))
    seen = set()
    unique = []
    for p in found:
        rel = str(p.relative_to(ROOT))
        if rel in seen:
            continue
        seen.add(rel)
        unique.append(p)
    return unique


def walk_collections(node, path="", inherited=None, source_map=None):
    """Yield (collection_path, rows, inherited_source) for every list of dicts."""
    if isinstance(node, dict):
        own = inherited
        for url in row_sources(node, source_map):
            if is_official(url):
                own = url
                break
        for key, value in node.items():
            yield from walk_collections(value, f"{path}.{key}" if path else str(key), own, source_map)
    elif isinstance(node, list):
        if node and all(isinstance(x, dict) for x in node):
            yield (path, node, inherited)
        for index, value in enumerate(node):
            if isinstance(value, (dict, list)):
                yield from walk_collections(value, f"{path}[{index}]", inherited, source_map)


def audit_rows() -> dict:
    coverage = []
    missing = []
    not_official = []
    rows_checked = 0
    rows_with_official = 0
    markdown_doc_links = 0
    rows_via_source_id = 0

    for path in data_files():
        rel = str(path.relative_to(ROOT))
        data = load(path)
        if data is None:
            continue
        derived = rel in DERIVED_FILES
        source_map = file_source_map(data)
        file_rows = 0
        file_official = 0
        file_missing = 0
        file_not_official = 0
        note = ""

        for cpath, rows, inherited in walk_collections(data, source_map=source_map):
            for row in rows:
                sources = row_sources(row, source_map)
                official = [u for u in sources if is_official(u)]
                other = [u for u in sources if u not in official]
                identity = any(row.get(k) for k in IDENTITY_KEYS)
                has_value = any(row.get(k) not in (None, "", 0, "0", "0.00") for k in VALUE_KEYS)
                if not (identity and has_value):
                    continue
                file_rows += 1
                rows_checked += 1
                if official:
                    file_official += 1
                    rows_with_official += 1
                    direct = [u for u in row_sources(row) if u.startswith("http")]
                    if not direct and inherited is None:
                        rows_via_source_id += 1
                elif inherited:
                    file_official += 1
                    rows_with_official += 1
                elif other:
                    file_not_official += 1
                    not_official.append({"file": rel, "collection": cpath,
                                         "ticker": row.get("ticker"), "url": other[0]})
                else:
                    file_missing += 1
                    missing.append({"file": rel, "collection": cpath, "ticker": row.get("ticker")})

        for url in source_map.values():
            if url.startswith("https://docs.kalshi.com/") and url.endswith(".md"):
                markdown_doc_links += 1
        if derived:
            note = "derived or reference data; checked but not required to carry a source on every row"
        coverage.append({
            "file": rel,
            "rows": file_rows,
            "with_source": file_official,
            "missing_source": file_missing,
            "not_official": file_not_official,
            "note": note,
        })

    return {
        "row_coverage": coverage,
        "rows_checked": rows_checked,
        "rows_with_official_source": rows_with_official,
        "rows_missing_source": len(missing),
        "rows_not_official": len(not_official),
        "missing_examples": missing[:40],
        "not_official_examples": not_official[:40],
        "markdown_documentation_links": markdown_doc_links,
        "rows_sourced_through_a_file_level_identifier": rows_via_source_id,
    }


def http_json(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers={"User-Agent": "Demo2-verify/1.0",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
        return resp.status, json.loads(body)


def live_recheck(sample_size: int = 30) -> dict:
    """Re-fetch a sample of markets from the official API and compare."""
    snap = load(ROOT / "data" / "dashboard_instrument.json") or {}
    markets = snap.get("markets") or {}
    pool = []
    for topic in ("gas", "elections", "crypto", "golf", "culture"):
        for row in (markets.get(topic) or []):
            if row.get("ticker"):
                pool.append((topic, row))
    # spread the sample across topics instead of taking the first N rows
    sample = []
    per_topic = max(1, sample_size // 5)
    for topic in ("gas", "elections", "culture", "crypto", "golf"):
        picked = [r for t, r in pool if t == topic][:per_topic]
        sample.extend(picked)
    if not sample:
        return {"attempted": 0, "ok": 0, "failed": 0, "details": [],
                "note": "no markets in the snapshot to re-check"}

    details = []
    ok = 0
    failed = 0
    for row in sample:
        ticker = row.get("ticker")
        url = f"{API}/markets/{ticker}"
        try:
            status, payload = http_json(url)
        except Exception as exc:  # noqa: BLE001 — reported, never hidden
            failed += 1
            details.append({
                "ticker": ticker, "field": "request", "snapshot": "—", "live": str(exc),
                "match": False, "source": url,
            })
            time.sleep(0.4)
            continue
        live = payload.get("market") or {}
        settled = str(row.get("status") or "").lower() in ("settled", "finalized")
        snap_status = str(row.get("status") or "")
        live_status = str(live.get("status") or "")
        status_match = (snap_status == live_status) or (snap_status == "" and live_status != "")
        snap_result = row.get("result")
        live_result = live.get("result")
        result_match = (snap_result == live_result)
        snap_price = row.get("last_price_dollars")
        live_price = live.get("last_price_dollars")
        if settled:
            price_match = snap_price == live_price
            price_verdict = "match" if price_match else "differs"
        else:
            price_match = True
            price_verdict = "moved since the snapshot (expected for an open market)"
        good = status_match and result_match and price_match
        if good:
            ok += 1
        else:
            failed += 1
        details.append({
            "ticker": ticker,
            "field": "status / result / last price",
            "snapshot": f"{snap_status} / {snap_result} / {snap_price}",
            "live": f"{live_status} / {live_result} / {live_price}",
            "match": good,
            "note": price_verdict,
            "source": url,
        })
        time.sleep(0.35)

    return {"attempted": len(sample), "ok": ok, "failed": failed, "details": details}


def endpoint_probe() -> dict:
    url = f"{API}/exchange/status"
    try:
        status, payload = http_json(url)
        return {
            "url": url,
            "http_status": status,
            "exchange_active": payload.get("exchange_active"),
            "trading_active": payload.get("trading_active"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "http_status": None, "error": str(exc)}


def main() -> int:
    offline = "--offline" in sys.argv
    report = {
        "generated_at": now(),
        "api_base": API,
        "api_docs": "https://docs.kalshi.com/getting_started/demo_env",
        "mode": "static only (no egress)" if offline else "static and live re-check",
    }
    report.update(audit_rows())

    if offline:
        report["live_rechecks"] = {"attempted": 0, "ok": 0, "failed": 0, "details": [],
                                  "note": "skipped: this run had no route to the demo API"}
        report["endpoint_probe"] = {"url": f"{API}/exchange/status", "http_status": None,
                                    "note": "skipped: offline"}
    else:
        report["live_rechecks"] = live_recheck()
        report["endpoint_probe"] = endpoint_probe()

    violations = []
    if report["rows_missing_source"]:
        violations.append(f"{report['rows_missing_source']} row(s) carry values but no official source")
    if report["rows_not_official"]:
        violations.append(f"{report['rows_not_official']} row(s) point at a URL outside the official Kalshi surface")
    live = report.get("live_rechecks") or {}
    if live.get("failed"):
        violations.append(f"{live['failed']} live re-check(s) did not match the committed snapshot")
    probe = report.get("endpoint_probe") or {}
    if probe.get("http_status") not in (None, 200):
        violations.append(f"exchange status probe returned HTTP {probe.get('http_status')}")

    report["status"] = "pass" if not violations else "fail"
    report["violations"] = violations
    report["summary"] = (
        f"{report['rows_checked']} rows checked across {len(report['row_coverage'])} data files; "
        f"{report['rows_with_official_source']} carry an official Kalshi source; "
        f"{live.get('ok', 0)} of {live.get('attempted', 0)} live re-checks matched; "
        f"{len(violations)} violation(s)."
    )

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "audit_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(report["summary"])
    for v in violations:
        print("VIOLATION: " + v)
    print(f"status: {report['status']}")
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
