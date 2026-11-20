#!/usr/bin/env python3
"""Offline smoke test: run the collector's pure functions on a fixture, no network.

Catches the class of bug that broke the settled-market block (a block that silently
produces zero rows), which a network test can miss when an API happens to be quiet.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import kalshi_collect as kc  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        FAILS.append(f"{name}: {detail}")
        print(f"  FAIL {name} {detail}")


print("select_series")
series = [
    {"ticker": "B", "frequency": "one_off"},
    {"ticker": "A", "frequency": "daily"},
    {"ticker": "C", "frequency": "weekly"},
]
picked = [s["ticker"] for s in kc.select_series(series, 2)]
check("recurring series win the cap", picked == ["A", "C"], picked)

print("derive")
m = {"volume_fp": "10.00", "volume_24h_fp": "2.00", "open_interest_fp": "4.00",
     "last_price_dollars": "0.5000"}
d = kc.derive(m)
check("notional = volume x price", d["notional_lifetime_usd"] == 5.0, d)
check("open interest $ = oi x price", d["open_interest_usd"] == 2.0, d)
check("missing price stays null", kc.derive({"volume_fp": "10.00"})["notional_lifetime_usd"] is None)
check("previous price is used only when last is absent",
      kc.derive({"volume_fp": "1", "previous_price_dollars": "0.2"})["price_used"] == "previous_price_dollars")

print("series scoping")
gas = {"id": "gas", "match_tags": ["oil and energy"], "match_words": ["gas", "gasoline", "diesel"]}
check("oil-and-energy tag matches gas",
      kc.series_matches(gas, {"tags": ["Oil and energy"], "title": "Texas gas price", "ticker": "X"}))
check("title word matches gas",
      kc.series_matches(gas, {"tags": None, "title": "National gasoline average", "ticker": "X"}))
check("unrelated series does not match gas",
      not kc.series_matches(gas, {"tags": ["Jobs & Economy"], "title": "Unemployment", "ticker": "KXU3MAX"}))
cult = {"id": "culture", "match_tags": [], "match_words": []}
check("culture category matches Culture",
      kc.series_matches(cult, {"categories": ["Culture"], "category": "Culture"}))
check("Entertainment is not Culture",
      not kc.series_matches(cult, {"categories": ["Entertainment"], "category": "Entertainment"}))

print("url building")
check("series query encodes category", "category=Crypto" in kc.ENDPOINTS["series_by_category"].format(category="Crypto"))
check("market query keeps mve_filter",
      "mve_filter=exclude" in kc.ENDPOINTS["markets"].format(ticker="X", status="open"))

print()
if FAILS:
    print(f"FAILED {len(FAILS)}")
    for f in FAILS:
        print(" ", f)
    sys.exit(1)
print("all offline checks passed")
