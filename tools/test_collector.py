#!/usr/bin/env python3
"""Offline test for tools/collector.py — no network, no credentials.

Why this exists: the collector can only be exercised end-to-end inside GitHub Actions
(the authoring sandbox has no TLS route to Kalshi). A bug therefore used to reach `main`
without anyone noticing the topic counts were zero. This test feeds the collector a
stubbed API that speaks the documented response shapes (docs.kalshi.com ->
api-reference/market/get-markets, get-series-list, get-market-orderbook, get-trades,
get-market-candlesticks, events/get-events) and asserts the properties the site depends
on:

  1. series are mapped to the five topics from the OFFICIAL `category`/`tags` fields;
  2. markets are fetched per in-scope series, and unmapped series are never invented;
  3. dollar fields are copied verbatim, so an absent API field stays absent;
  4. `usd_volume_24h` is computed only from trade prints inside the window;
  5. order-book depth is normalised (yes bids descending, asks derived as 1 - no bid);
  6. every emitted market row carries a source URL;
  7. an empty topic is reported as empty rather than dropped.

Run:  python3 tools/test_collector.py         (exits non-zero on any failure)
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
OLD = (NOW - dt.timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
NOW_TS = int(NOW.timestamp())

SERIES = [
    # topic comes from `category` / `tags` only - see collector.series_topic
    {"ticker": "AAA", "category": "Economics", "categories": ["Economics"], "tags": ["Gas"]},
    {"ticker": "ELEC", "category": "Elections", "categories": ["Elections"], "tags": []},
    {"ticker": "CRY", "category": "Crypto", "categories": ["Crypto"], "tags": ["BTC"]},
    {"ticker": "GOLF", "category": "Sports", "categories": ["Sports"], "tags": ["Golf"]},
    {"ticker": "CULT", "category": "Culture", "categories": ["Culture"], "tags": []},
    {"ticker": "OFFSCOPE", "category": "Weather", "categories": ["Climate and Weather"], "tags": []},
]

MARKETS = {
    "AAA": [
        {
            "ticker": "AAA-26DEC31-2.30", "event_ticker": "AAA-26DEC31", "title": "Gas above 2.30?",
            "yes_sub_title": "Above 2.30", "status": "active", "result": "",
            "yes_bid_dollars": "0.1800", "yes_ask_dollars": "1.0000",
            "no_bid_dollars": "0.0000", "no_ask_dollars": "0.8200",
            "last_price_dollars": "0.9800",
            "yes_bid_size_fp": "0.00", "yes_ask_size_fp": "0.00",
            "volume_fp": "41.58", "volume_24h_fp": "0.00", "open_interest_fp": "38.41",
            "close_time": "2026-12-31T15:00:00Z", "open_time": "2026-11-01T00:00:00Z",
            "updated_time": "2026-11-20T12:00:00Z",
        }
    ],
    "ELEC": [
        {
            "ticker": "ELEC-28-GWHI", "event_ticker": "ELEC-28", "title": "Who runs in 2028?",
            "yes_sub_title": "GWHI", "status": "active", "result": "",
            "yes_bid_dollars": "0.2200", "yes_ask_dollars": "0.9800",
            "no_bid_dollars": "0.0200", "no_ask_dollars": "0.7800",
            "last_price_dollars": "0.9700",
            "yes_bid_size_fp": "10.00", "yes_ask_size_fp": "5.00",
            "volume_fp": "16294.17", "volume_24h_fp": "12.00", "open_interest_fp": "5099.02",
            "close_time": "2028-01-01T15:00:00Z", "open_time": "2026-01-01T00:00:00Z",
            "updated_time": "2026-11-20T12:00:00Z",
        }
    ],
    "CRY": [
        {
            "ticker": "CRY-BNB15M", "event_ticker": "CRY-26NOV20", "title": "BNB up in 15m?",
            "yes_sub_title": "Up", "status": "active", "result": "",
            "yes_bid_dollars": "0.0000", "yes_ask_dollars": "0.0000",
            "no_bid_dollars": "1.0000", "no_ask_dollars": "1.0000",
            # deliberately absent: the collector must not invent a price
            "last_price_dollars": None,
            "yes_bid_size_fp": "0.00", "yes_ask_size_fp": "0.00",
            "volume_fp": "0.00", "volume_24h_fp": "0.00", "open_interest_fp": "0.00",
            "close_time": "2026-11-20T13:15:00Z", "open_time": "2026-11-20T13:00:00Z",
            "updated_time": "2026-11-20T13:00:00Z",
        }
    ],
    "GOLF": [
        {
            "ticker": "GOLF-SLAM", "event_ticker": "GOLF-28", "title": "Win the grand slam?",
            "yes_sub_title": "Yes", "status": "active", "result": "",
            "yes_bid_dollars": "0.9900", "yes_ask_dollars": "1.0000",
            "no_bid_dollars": "0.0000", "no_ask_dollars": "0.0100",
            "last_price_dollars": "0.5500",
            "yes_bid_size_fp": "1.00", "yes_ask_size_fp": "0.00",
            "volume_fp": "18853.16", "volume_24h_fp": "0.00", "open_interest_fp": "4939.14",
            "close_time": "2028-01-01T15:00:00Z", "open_time": "2026-01-01T00:00:00Z",
            "updated_time": "2026-11-20T12:00:00Z",
        }
    ],
    # CULT intentionally has no markets: a topic may legitimately be empty today
}

SETTLED = [
    {
        "ticker": "ELEC-24-OLD", "event_ticker": "ELEC-24", "title": "Old election market",
        "status": "finalized", "result": "yes", "settlement_value_dollars": "1.0000",
        "settlement_ts": "2026-11-01T00:00:00Z", "close_time": "2026-11-01T00:00:00Z",
        "expiration_value": "1", "volume_fp": "10.00", "open_interest_fp": "0.00",
        "rules_primary": "Resolves Yes if ...", "yes_bid_dollars": "0.0000",
        "yes_ask_dollars": "0.0000", "no_bid_dollars": "0.0000", "no_ask_dollars": "0.0000",
        "last_price_dollars": "1.0000", "volume_24h_fp": "0.00",
    }
]

TRADES = {
    "ELEC-28-GWHI": [
        {"trade_id": "t1", "count_fp": "10.00", "yes_price_dollars": "0.5000",
         "no_price_dollars": "0.5000", "created_time": RECENT, "taker_side": "yes"},
        {"trade_id": "t2", "count_fp": "5.00", "yes_price_dollars": "0.2000",
         "no_price_dollars": "0.8000", "created_time": OLD, "taker_side": "no"},
    ],
    "AAA-26DEC31-2.30": [
        {"trade_id": "t3", "count_fp": "2.00", "yes_price_dollars": "0.2500",
         "no_price_dollars": "0.7500", "created_time": RECENT, "taker_side": "yes"},
    ],
}

CALLS: list[str] = []


def fake_get_json(url: str, signer=None, retries: int = 3):
    """Spec-shaped stub. Mirrors the documented response envelope of each endpoint."""
    CALLS.append(url)
    p = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(p.query)
    path = p.path

    if path.endswith("/exchange/status"):
        return {"exchange_active": True, "trading_active": True}, 200
    if path.endswith("/series"):
        return {"series": SERIES}, 200
    if path.endswith("/markets"):
        st = (q.get("series_ticker") or [""])[0]
        status = (q.get("status") or [""])[0]
        if status == "settled":
            return {"markets": SETTLED, "cursor": ""}, 200
        return {"markets": MARKETS.get(st, []), "cursor": ""}, 200
    if "/markets/trades" in path:
        t = (q.get("ticker") or [""])[0]
        return {"trades": TRADES.get(t, [])}, 200
    if path.endswith("/orderbook"):
        ticker = path.split("/markets/")[1].split("/")[0]
        if ticker == "ELEC-28-GWHI":
            return {"orderbook_fp": {"yes_dollars": [["0.2000", "10.00"], ["0.2200", "5.00"]],
                                     "no_dollars": [["0.0100", "3.00"]]}}, 200
        return {"orderbook_fp": {"yes_dollars": [], "no_dollars": []}}, 200
    if path.endswith("/candlesticks"):
        return {"ticker": "x", "candlesticks": [
            {"end_period_ts": NOW_TS, "yes_bid": {"close_dollars": "0.2000"},
             "yes_ask": {"close_dollars": "0.3000"},
             "price": {"open_dollars": "0.2400", "high_dollars": "0.2600",
                       "low_dollars": "0.2300", "close_dollars": "0.2500",
                       "previous_dollars": "0.2400", "mean_dollars": "0.2450"},
             "volume_fp": "3.00", "open_interest_fp": "9.00"}]}, 200
    return None, 404


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
    print(f"  ok  {msg}")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="kalshi-collector-test-"))
    collector.DATA = tmp
    collector.get_json = fake_get_json          # type: ignore[assignment]
    collector.time.sleep = lambda *_: None      # type: ignore[assignment]
    collector.API_LOG.clear()

    import io
    import contextlib
    argv = sys.argv
    sys.argv = ["collector", "--max-runtime", "600", "--volume-markets", "5",
                "--book-markets", "3", "--book-samples", "2"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = collector.main()
    finally:
        sys.argv = argv
    check(rc == 0, "collector.main() returns 0")

    snap = json.loads((tmp / "snapshot.json").read_text())
    rows = snap["markets"]
    by_topic = snap["counts"]["per_topic"]

    print("\nscope")
    check(len(rows) == 4, f"4 in-scope markets collected (got {len(rows)})")
    check(by_topic == {"gas": 1, "elections": 1, "culture": 0, "crypto": 1, "golf": 1},
          f"per-topic counts come from official category/tags only: {by_topic}")
    check("OFFSCOPE" not in {r["series_ticker"] for r in rows},
          "an out-of-scope series (Weather) contributes no rows")
    check(snap["unmapped_series"].get("OFFSCOPE") == 1,
          "the out-of-scope series is recorded in unmapped_series, not guessed into a topic")
    check(all(r.get("series_ticker") for r in rows), "every row names the series it came from")

    print("\nverbatim values")
    cry = next(r for r in rows if r["topic"] == "crypto")
    check(cry["last_price_dollars"] is None,
          "an absent API field stays absent (None), never filled in")
    elec = next(r for r in rows if r["topic"] == "elections")
    check(elec["last_price_dollars"] == "0.9700" and elec["volume_fp"] == "16294.17",
          "dollar and volume fields are copied verbatim from the response")

    print("\ncomputed 24h dollar volume")
    check(elec.get("usd_volume_24h") == 5.0,
          f"10 contracts x $0.50 inside the window = $5.00 (got {elec.get('usd_volume_24h')})")
    check(elec.get("contracts_24h_from_trades") == 10.0,
          "the 5 contracts from 5 days ago are excluded from the window")
    src = elec.get("usd_volume_24h_source_url") or ""
    check("ticker=ELEC-28-GWHI" in src,
          f"the computed value carries the request URL it came from ({src})")

    print("\nranking input")
    top = json.loads((tmp / "top.json").read_text())
    first = top["rows"][0]
    check(first["market_ticker"] == "ELEC-28-GWHI",
          "top.json is ranked by computed 24h dollars first")
    check(first["rank_by"] == "usd_volume_24h", "the row states which metric ranked it")
    check(all(r.get("market_url") for r in top["rows"]), "every ranked row has a source URL")

    print("\nliquidity")
    liq = json.loads((tmp / "liquidity.json").read_text())
    pts = liq["markets"]["ELEC-28-GWHI"]["points"]
    check(len(pts) == 2, f"2 spaced order-book samples stored (got {len(pts)})")
    check([p for p, _ in pts[0]["yes_bids"]] == [0.22, 0.2],
          "yes bids are ordered best-first")
    check([round(p, 4) for p, _ in pts[0]["derived_yes_asks"]] == [0.99],
          "a NO bid at 0.01 is shown as a YES ask at 0.99, derived and labelled")
    check(pts[0]["yes_bid_contracts"] == 15.0 and pts[0]["derived_ask_contracts"] == 3.0,
          "contracts available at each price are totalled (15 bid / 3 offered)")

    print("\ncompact payloads")
    meta = json.loads((tmp / "dashboard_meta.json").read_text())
    check(meta["counts"]["markets_in_scope"] == 4, "dashboard_meta.json carries the counts")
    check(meta["api_request_failures"] == 0, "no stray non-2xx requests in the run")
    for name in ("topic-gas.json", "topic-elections.json", "topic-culture.json",
                 "topic-crypto.json", "topic-golf.json", "resolutions.json"):
        check((tmp / name).exists(), f"{name} written")
    cult = json.loads((tmp / "topic-culture.json").read_text())
    check(cult["count"] == 0, "an empty topic is written as an explicit 0, not omitted")

    print("\nresolutions")
    res = json.loads((tmp / "resolutions.json").read_text())["resolutions"]
    check(len(res) == 1 and res[0]["result"] == "yes",
          "the settled in-scope market keeps its official yes/no result")

    print(f"\n{len(CALLS)} stubbed requests, all offline. ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        sys.exit(1)
