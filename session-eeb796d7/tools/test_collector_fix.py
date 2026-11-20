#!/usr/bin/env python3
"""Offline regression test for the tools/collector.py E-5 fixes (session eeb796d7).

Why this exists: the collector crashed in GitHub Actions (runs 44728913873 and
44744689706: "Collect demo snapshot" -> exit 1 within ~23 s) on the FIRST in-scope
market row, because collect_scope() referenced a `series` variable that does not
exist in that scope (NameError). With no network (zero rows) the crash never fired,
which is why an offline run looked healthy while every real run failed and the root
dashboard sat on data/snapshot.json -> 404.

A second defect surfaced while writing this test: the topic classifier mapped only
the exact tags Gas/Gasoline/Diesel, but the AAA gasoline series (KXAAAGASD etc.)
carry tags ["Oil & Gas", "Oil and energy", "Econ Daily"] and are classified via
product_metadata.scope == "Gasoline" (verified live on GET /series/KXAAAGASD).
The bare "Oil & Gas" tag must NOT map: it also covers crude oil (KXWTI), natural
gas and TTF.

This test feeds the collector VERBATIM demo-API response bodies
(session-eeb796d7/data/raw/, fetched 2026-11-20 from
https://external-api.demo.kalshi.co/trade-api/v2) through a monkeypatched
get_json, then asserts:
  1. collect_scope() completes without raising (the NameError is gone),
  2. one row per in-scope market, copied verbatim from the API,
  3. the series_* fields are filled from the event's own series record,
  4. market_url/event_url point at the exact official API endpoints
     (the market TICKER, not the series ticker),
  5. scope=Gasoline classifies as the gas topic; Oil-&-Gas-tagged crude does not,
  6. the zero-row path still exits cleanly.

Run:  python3 session-eeb796d7/tools/test_collector_fix.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

spec = importlib.util.spec_from_file_location("collector", ROOT / "tools" / "collector.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

events_body = json.loads((RAW / "events_KXAAAGASD-28SEP16.json").read_text())["body"]
series_gas = json.loads((RAW / "series_KXAAAGASD.json").read_text())["body"]["series"]
series_wti = json.loads((RAW / "series_KXWTI.json").read_text())["body"]["series"]

# The bare /series LIST response does not carry product_metadata (verified in the
# 2026-11-20 14:10 live run: gas topic mapped only DIESEL/DIESELM). Simulate that:
# the list serves SLIM records; GET /series/{ticker} serves the full record.
series_gas_slim = {k: v for k, v in series_gas.items() if k != "product_metadata"}

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        failures.append(msg)


def fake_get_json(url, signer=None, retries=3):
    if url.rstrip("/").endswith("/series/KXAAAGASD"):
        return {"series": series_gas}, 200  # full record (with product_metadata)
    if "/series" in url and "candlesticks" not in url and "/markets" not in url:
        return {"series": [series_gas_slim, series_wti]}, 200  # slim list
    if "/events" in url:
        return events_body, 200
    return None, 404


collector.get_json = fake_get_json  # type: ignore[assignment]

# --- 1+2: the crash is gone and the rows are produced -------------------------
scope = collector.collect_scope(None)
rows = scope["markets_in_scope"]
check(len(rows) == 3, f"collect_scope returns 3 in-scope rows (got {len(rows)})")

tickers = sorted(r["market_ticker"] for r in rows)
check(tickers == ["KXAAAGASD-28SEP16-2.5", "KXAAAGASD-28SEP16-3", "KXAAAGASD-28SEP16-3.5"],
      f"market tickers copied verbatim: {tickers}")

# --- 3: series fields come from the event's own series record -----------------
ok_series = all(
    r.get("series_category") == series_gas.get("category")
    and r.get("series_categories") == series_gas.get("categories")
    and r.get("contract_terms_url") == series_gas.get("contract_terms_url")
    and r.get("contract_url") == series_gas.get("contract_url")
    for r in rows
)
check(ok_series, "series_category/series_categories/contract_terms_url/contract_url "
                 "are taken from the KXAAAGASD series record")

# --- 4: links point at the official API, with the MARKET ticker --------------
base = collector.DEMO_REST
ok_links = all(
    r["market_url"] == f"{base}/markets/{r['market_ticker']}"
    and r["event_url"] == f"{base}/events/{r['event_ticker']}"
    for r in rows
)
check(ok_links, "market_url/event_url use the exact official API endpoint + market ticker")

# verbatim dollar fields (spot-check the lead market against the fixture)
lead = next(r for r in rows if r["market_ticker"] == "KXAAAGASD-28SEP16-2.5")
check(lead["yes_bid_dollars"] == "0.3500" and lead["volume_fp"] == "12.98"
      and lead["open_interest_fp"] == "9.84",
      "dollar/count fields copied verbatim (yes_bid 0.3500, volume_fp 12.98, OI 9.84)")

# --- 5: classification uses the official scope; Oil & Gas tag is not enough ---
check(collector.series_topic(series_gas) == "gas",
      "KXAAAGASD (product_metadata.scope=Gasoline) classifies as gas")
check(collector.series_topic(series_wti) is None,
      "KXWTI (Oil & Gas tag, no scope) does NOT classify as gas")
check(all(r["topic"] == "gas" for r in rows), "all fixture rows carry topic=gas")

# --- 5b: the golf path (mapped under the OLD rules too — this is the exact path
#        that crashed CI) now builds rows instead of raising NameError -----------
golf_ev = json.loads((RAW / "events_KXPGAFUTURE-36MRUS_extract.json").read_text())["body"]
sidx = json.load(open(ROOT / "data" / "series_index.json"))
golf_series = next(s for s in sidx["series"] if s["ticker"] == "KXPGAFUTURE")


def golf_get_json(url, signer=None, retries=3):
    if "/series" in url and "candlesticks" not in url and "/markets" not in url:
        return {"series": [golf_series]}, 200
    if "/events" in url:
        return golf_ev, 200
    return None, 404


collector.get_json = golf_get_json  # type: ignore[assignment]
gscope = collector.collect_scope(None)
grows = gscope["markets_in_scope"]
check(len(grows) == 3 and all(r["topic"] == "golf" for r in grows),
      "golf event (tag Golf — mapped by the old rules too) builds 3 rows without NameError")
check(all(r["series_category"] == "Sports" for r in grows),
      "golf rows carry series_category from the KXPGAFUTURE series record")

# --- 6: the zero-row path is still clean -------------------------------------
def empty_get_json(url, signer=None, retries=3):
    return None, 0


collector.get_json = empty_get_json  # type: ignore[assignment]
scope0 = collector.collect_scope(None)
check(scope0["markets_in_scope"] == [], "zero-row path returns no rows without raising")

print()
if failures:
    print(f"{len(failures)} FAILURE(S)")
    sys.exit(1)
print("all checks passed")
