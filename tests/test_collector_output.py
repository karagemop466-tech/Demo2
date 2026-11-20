#!/usr/bin/env python3
"""Offline regression tests for tools/collector.py's bounded output layer.

Motivation (verified incident, 2026-11-20): data/snapshot.json reached 112 MB and
GitHub's pre-receive hook rejected every push, so the Refresh Kalshi demo data
workflow failed at the commit step for hours and the published data went stale.
These tests pin the fixes: no duplicated rows, no null fields, compact JSON,
recorded trimming, bounded history, and a hard per-file tripwire. No network:
get_json/paginate are replaced with synthetic OFFICIAL-SHAPED records; nothing
here asserts anything about real market values.

Run:  python3 tests/test_collector_output.py
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import collector  # noqa: E402

PASS = 0


def ok(cond: bool, label: str) -> None:
    global PASS
    assert cond, f"FAIL: {label}"
    PASS += 1
    print(f"  ok: {label}")


def fake_get_json(url: str, signer=None, retries: int = 3):
    if url.endswith("/series"):
        return {"series": SERIES}, 200
    if "/series/" in url:
        t = url.rsplit("/", 1)[-1]
        for s in SERIES:
            if s["ticker"] == t:
                return {"series": s}, 200
        return {"series": []}, 200
    if url.endswith("/exchange/status"):
        return {"exchange_active": True, "trading_active": True}, 200
    return {}, 200


def fake_paginate(url: str, key: str, signer=None, max_pages: int = 30):
    if "events" in url:
        return EVENTS
    if "status=settled" in url:
        return SETTLED
    return []


SERIES = [
    {"ticker": "TSTELEC", "tags": ["Elections"], "category": "Elections"},
    {"ticker": "TSTCRYPTO", "tags": ["Crypto"], "category": "Crypto"},
    {"ticker": "TSTGOLF", "tags": ["Golf"], "category": "Golf"},
    {"ticker": "TSTCULT", "tags": ["Culture"], "category": "Culture"},
    {"ticker": "TSTGAS", "tags": ["Oil & Gas"], "category": "Other",
     "product_metadata": {"scope": "Gasoline"}},
]


def make_market(i: int, topic: str) -> dict:
    # Long rules text: must be dropped (only a 160-char head may survive).
    return {
        "ticker": f"TST{topic.upper()}-26DEC31-{i}",
        "title": f"Test market {i} ({topic})",
        "yes_sub_title": None if i % 3 else f"choice {i}",
        "status": "active",
        "result": "",
        "yes_bid_dollars": "0.4000",
        "yes_ask_dollars": "0.5000",
        "no_bid_dollars": "0.5000",
        "no_ask_dollars": "0.6000",
        "last_price_dollars": "0.4500",
        "yes_bid_size_fp": "100.00",
        "yes_ask_size_fp": "120.00",
        "volume_fp": str(1000 + i),
        "volume_24h_fp": None,
        "open_interest_fp": "50.00",
        "close_time": "2026-12-31T23:59:59Z",
        "open_time": "2026-11-01T00:00:00Z",
        "updated_time": "2026-11-20T12:00:00Z",
        "price_level_structure": None,
        "rules_primary": "RULES " + ("legal text " * 500),
        "rules_secondary": "MORE RULES " + ("text " * 500),
        "exchange_index": None,
    }


def make_event(i: int, series_ticker: str, topic: str, n_markets: int) -> dict:
    return {
        "event_ticker": f"{series_ticker}-E{i}",
        "series_ticker": series_ticker,
        "title": f"Test event {i} ({topic})",
        "settlement_sources": [{"title": "Official source", "url": "https://example.org/"}],
        "markets": [make_market(i * 100 + k, topic) for k in range(n_markets)],
    }


EVENTS = (
    [make_event(i, "TSTELEC", "elections", 2) for i in range(650)] +   # 1300 -> trimmed to 1200
    [make_event(i, "TSTCRYPTO", "crypto", 1) for i in range(20)] +
    [make_event(i, "TSTGOLF", "golf", 1) for i in range(5)] +
    [make_event(i, "TSTCULT", "culture", 1) for i in range(3)] +
    [make_event(i, "TSTGAS", "gas", 1) for i in range(4)]
)

SETTLED = [
    {"ticker": "TSTELEC-26DEC31-0", "event_ticker": "TSTELEC-E0", "status": "settled",
     "title": "Test market 0 (elections)", "result": "yes",
     "settlement_value_dollars": "1.0000", "settlement_ts": "2026-11-20T00:00:00Z",
     "close_time": "2026-11-19T23:59:59Z", "expiration_value": "yes"},
    {"ticker": "TSTGOLF-26DEC31-0", "event_ticker": "TSTGOLF-E0", "status": "settled",
     "title": "Test market 0 (golf)", "result": "no",
     "settlement_value_dollars": "0.0000", "settlement_ts": "2026-11-20T00:00:00Z",
     "close_time": "2026-11-19T23:59:59Z", "expiration_value": "no"},
]


def run_main(data_dir: Path) -> None:
    collector.DATA = data_dir
    collector.get_json = fake_get_json
    collector.paginate = fake_paginate
    sys.argv = ["collector.py", "--scope-only"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = collector.main()
    assert rc == 0, buf.getvalue()


def test_helpers() -> None:
    print("test_helpers")
    r = make_market(3, "golf")
    r["topic"] = "golf"
    r["market_ticker"] = r.pop("ticker")  # API shape -> collector row shape
    slim = collector.slim_row(r)
    for k in collector.ROW_REQUIRED_KEYS:
        ok(k in slim, f"slim_row keeps required key {k}")
    ok("volume_24h_fp" not in slim, "slim_row drops null optional fields")
    ok("price_level_structure" not in slim, "slim_row drops null optional fields (2)")
    ok(slim.get("yes_sub_title") == "choice 3", "slim_row keeps non-null optional fields")

    rows = [make_market(i, "golf") for i in range(50)]
    for r in rows:
        r["topic"] = "golf"
        r["est_dollar_volume"] = collector.implied_dollar_volume(r)
    pub, trimmed = collector.select_published(rows + [dict(rows[0], topic="crypto",
                                                           market_ticker="X-1")])
    ok(len(pub) == 51, "select_published keeps rows under the per-topic cap")
    ok(trimmed["golf"] == 0 and trimmed["crypto"] == 0, "no trimming under the cap")

    # tripwire: a payload over FILE_LIMIT_BYTES must refuse to write
    collector.DATA = Path(tempfile.mkdtemp())
    old = collector.FILE_LIMIT_BYTES
    collector.FILE_LIMIT_BYTES = 100
    raised = False
    try:
        collector.write_json("big.json", {"x": "y" * 500})
    except SystemExit:
        raised = True
    finally:
        collector.FILE_LIMIT_BYTES = old
    ok(raised, "write_json refuses an over-limit file (loud failure, no push rejection)")


def test_end_to_end() -> None:
    print("test_end_to_end (synthetic official-shaped API, two runs)")
    tmp = Path(tempfile.mkdtemp(prefix="kalshi-collector-test-"))
    run_main(tmp)
    snap = json.loads((tmp / "snapshot.json").read_text())

    for key in ("generated_at_utc", "counts", "markets", "resolutions", "api_log",
                "series_inventory", "by_topic", "definitions"):
        ok(key in snap, f"snapshot has {key}")

    c = snap["counts"]
    ok(c["markets_in_scope"] == 1300 + 20 + 5 + 3 + 4, "full in-scope count preserved")
    ok(c["markets_published"] == 1200 + 20 + 5 + 3 + 4, "elections trimmed to PUBLISH_PER_TOPIC")
    ok(c["markets_trimmed_per_topic"]["elections"] == 100, "trimmed count recorded, not silent")
    ok(c["resolved_in_scope"] == 2, "resolutions counted")

    ok(all(isinstance(v, list) and all(isinstance(t, str) for t in v)
           for v in snap["by_topic"].values()), "by_topic holds tickers only (no duplicated rows)")
    ok(len(snap["by_topic"]["elections"]) == 1200, "by_topic matches published rows")

    missing = [(m.get("market_ticker"), k) for m in snap["markets"]
               for k in collector.ROW_REQUIRED_KEYS if k not in m]
    ok(not missing, "every published row keeps the check.py-required keys")
    bad_nulls = [(m.get("market_ticker"), k) for m in snap["markets"]
                 for k, v in m.items() if v is None and k not in collector.ROW_REQUIRED_KEYS]
    ok(not bad_nulls, "no null values outside the required keys")
    fat = [m.get("market_ticker") for m in snap["markets"]
           if "rules_primary" in m or "rules_secondary" in m
           or any(isinstance(v, str) and len(v) > 400 for v in m.values())]
    ok(not fat, "no full rules text or oversized strings in published rows")

    head = (tmp / "snapshot.json").read_text()
    ok(not head.lstrip().startswith("{\n"), "snapshot.json written compact (no indent)")
    ok(snap["definitions"].get("published_rows"), "trimming documented in definitions")

    for t in collector.TOPICS:
        tp = json.loads((tmp / f"topic-{t}.json").read_text())
        ok(tp["count"] == len(tp["markets"]), f"topic-{t}: count matches rows")
        ok("count_in_scope" in tp and "trimmed_by_volume" in tp,
           f"topic-{t}: in-scope count and trimming recorded")

    ok(len(snap["resolutions"]) == 2 and {r["result"] for r in snap["resolutions"]} == {"yes", "no"},
       "resolutions keep official yes/no results")

    # second run exercises the history append + bound
    run_main(tmp)
    hist = json.loads((tmp / "history.json").read_text())
    ok(len(hist["points"]) <= collector.HISTORY_TICKERS_MAX, "history tickers bounded")
    ok(all(len(v) <= collector.HISTORY_POINTS_MAX for v in hist["points"].values()),
       "history points per ticker bounded")
    ok(hist["points"], "history recorded for markets with a last price")

    # every file written is well under the tripwire
    for p in tmp.glob("*.json"):
        ok(p.stat().st_size < collector.FILE_LIMIT_BYTES, f"{p.name} under the file limit")


if __name__ == "__main__":
    test_helpers()
    test_end_to_end()
    print(f"\nALL PASS ({PASS} assertions)")
