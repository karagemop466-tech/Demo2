#!/usr/bin/env python3
"""Regression test for the publish-size caps (K-1, session b7bc848c).

Why this exists: on 2026-11-20 the data pipeline froze because every push was
rejected by GitHub ("File data/snapshot.json is 111.97 MB; this exceeds GitHub's
file size limit of 100.00 MB", run 44800417665). The collector itself worked; the
FILES it wrote were too big. This test drives tools/collector.py against a stubbed
API with deliberately huge rows and asserts every bound the fix relies on:

  1. per-topic publish caps with honest full counts (count/count_total/capped);
  2. rules text shortened and flagged, never silently presented as complete;
  3. settlement_sources compacted with the original total recorded;
  4. history.json bounded in tickers AND in retained points;
  5. series_index.json records shortened, keeping the full-record source URL;
  6. write_json refuses anything near GitHub's hard limit (publish guard);
  7. ranking order is preserved: published rows are the TOP of each topic.

Run:  python3 tools/test_publish_limits.py         (exits non-zero on any failure)
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import collector  # noqa: E402

NOW = dt.datetime.now(dt.timezone.utc)
RECENT = (NOW - dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

LONG_RULES = "Resolves Yes if the following happens. " * 40        # 1,520 chars
LONG_SOURCES = [{"name": f"Source {i} with a fairly long display name " * 2,
                 "url": f"https://example.org/source-{i}"} for i in range(8)]

N_ELEC = 700


def _mk_market(i: int, base_vol: float) -> dict:
    return {
        "ticker": f"ELEC-M{i:04d}", "event_ticker": f"ELEC-{i // 10:03d}",
        "title": f"Election market {i}?", "yes_sub_title": f"Candidate {i}",
        "status": "active", "result": "",
        "yes_bid_dollars": "0.2500", "yes_ask_dollars": "0.3500",
        "no_bid_dollars": "0.6500", "no_ask_dollars": "0.7500",
        "last_price_dollars": "0.3000",
        "yes_bid_size_fp": "1.00", "yes_ask_size_fp": "1.00",
        "volume_fp": f"{base_vol:.2f}", "volume_24h_fp": "0.00",
        "open_interest_fp": "1.00",
        "close_time": "2028-01-01T00:00:00Z", "open_time": "2026-01-01T00:00:00Z",
        "updated_time": RECENT,
        "rules_primary": LONG_RULES if i % 3 == 0 else f"Short rule {i}.",
    }


SERIES = [
    {"ticker": "ELEC", "category": "Elections", "categories": ["Elections"], "tags": [],
     "title": "Elections", "settlement_sources": LONG_SOURCES,
     "description": "D" * 900, "contract_terms_url": "https://assets.kalshi.com/contract_terms/ELEC.pdf",
     "contract_url": "https://example.org/cert.pdf"},
]

MARKETS = [_mk_market(i, base_vol=100.0 * (i + 1)) for i in range(N_ELEC)]


def fake_get_json(url: str, signer=None, retries: int = 3):
    p = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(p.query)
    path = p.path
    if path.endswith("/exchange/status"):
        return {"exchange_active": True, "trading_active": True}, 200
    if path.endswith("/series"):
        return {"series": SERIES}, 200
    if path.endswith("/markets"):
        status = (q.get("status") or [""])[0]
        if status == "settled":
            return {"markets": [], "cursor": ""}, 200
        return {"markets": MARKETS, "cursor": ""}, 200
    if "/markets/trades" in path:
        return {"trades": []}, 200
    if path.endswith("/orderbook"):
        return {"orderbook_fp": {"yes_dollars": [], "no_dollars": []}}, 200
    if path.endswith("/candlesticks"):
        return {"ticker": "x", "candlesticks": []}, 200
    return None, 404


checks = 0


def check(cond: bool, label: str) -> None:
    global checks
    checks += 1
    print(("  ok  " if cond else "  FAIL ") + label)
    if not cond:
        raise SystemExit(f"FAILED: {label}")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="publish-limits-")
    data_dir = Path(tmp) / "data"
    old_data = collector.DATA
    old_get = collector.get_json
    collector.DATA = data_dir
    collector.get_json = fake_get_json  # type: ignore[assignment]
    argv = sys.argv
    try:
        sys.argv = ["collector", "--max-runtime", "600", "--volume-markets", "0",
                    "--book-markets", "0", "--book-samples", "1",
                    "--series-per-topic", "0", "--publish-per-topic", "50"]
        rc = collector.main()
    finally:
        sys.argv = argv
        collector.DATA = old_data
        collector.get_json = old_get  # type: ignore[assignment]

    print("publish caps")
    check(rc == 0, "collector.main() returns 0")

    snap = json.loads((data_dir / "snapshot.json").read_text())
    counts = snap["counts"]

    check(counts["markets_in_scope"] == N_ELEC, "full in-scope count is kept")
    check(counts["per_topic"]["elections"] == N_ELEC, "per_topic reports the full count")
    check(counts["per_topic_published"]["elections"] == 50, "per_topic_published reports the cap")
    check(counts["rows_capped"] is True, "rows_capped flag is set")
    check(counts["markets_published"] == 50, "markets_published counts published rows")
    check(len(snap["markets"]) == 50, "snapshot carries only published rows")
    check(len(snap["by_topic"]["elections"]) == 50, "by_topic carries only published rows")

    top = json.loads((data_dir / "topic-elections.json").read_text())
    check(top["count"] == 50 and top["count_total"] == N_ELEC,
          "topic file keeps count (published) and count_total (full)")
    check(top["capped"] is True, "topic file is marked capped")
    vols = [float(r["volume_fp"]) for r in top["markets"]]
    check(vols == sorted(vols, reverse=True), "published rows are the top of the ranking")

    print("row compaction")
    row = next(r for r in top["markets"] if r["rules_truncated"])
    check(len(row["rules_primary"]) <= 300, "rules_primary shortened to <= 300 chars")
    check(row["rules_primary"].startswith("Resolves Yes"), "rules prefix is verbatim")
    check(row["rules_truncated"] is True, "truncation is flagged, not silent")
    short = next(r for r in top["markets"] if not r["rules_truncated"])
    check(short["rules_primary"] == f"Short rule {int(short['market_ticker'][6:])}.",
          "short rules stay verbatim")
    srcs = row["settlement_sources"]
    check(isinstance(srcs, list) and len(srcs) <= 3, "settlement_sources capped to 3 entries")
    check(row["settlement_sources_total"] == len(LONG_SOURCES),
          "settlement_sources_total records the original count")
    check(all(len(s.get("name", "")) <= 100 and len(s.get("url", "")) <= 160 for s in srcs),
          "settlement_sources entries are bounded")

    print("history bounds")
    hist = json.loads((data_dir / "history.json").read_text())
    pts = hist["points"]
    check(len(pts) <= 300, "history tracks at most 300 markets")
    check(all(len(v) <= 288 for v in pts.values()), "history retains at most 288 points per market")
    check("ELEC-M0699" not in pts or len(pts) <= 300, "untracked markets are pruned")
    check(hist.get("retention_points") == 288, "retention is published")

    print("series index")
    sidx = json.loads((data_dir / "series_index.json").read_text())
    s = sidx["series"][0]
    check(len(s.get("description", "")) <= 300, "series long text fields shortened")
    check(len(s.get("settlement_sources", [])) <= 5, "series settlement_sources capped")
    check(s["source"].endswith("/series/ELEC"), "series keeps the full-record source URL")

    print("file sizes")
    for name in ("snapshot.json", "topic-elections.json", "history.json",
                 "series_index.json", "resolutions_log.json", "top.json",
                 "dashboard_meta.json", "liquidity.json"):
        size = (data_dir / name).stat().st_size
        check(size < collector.WRITE_LIMIT_BYTES, f"{name} is {size:,} bytes, under the publish guard")

    print("publish guard")
    try:
        collector.write_json("bomb.json", {"x": "y" * 50_000_000})
        check(False, "write_json refuses an over-limit payload")
    except SystemExit as e:
        check(e.code == 2, "write_json refuses an over-limit payload with exit code 2")
    check(not (data_dir / "bomb.json").exists(), "the over-limit payload was not written")

    print(f"\n{checks} checks, ALL PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
