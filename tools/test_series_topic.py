#!/usr/bin/env python3
"""Offline unit tests for tools/collector.py scope mapping + resolutions union.

Runs with no network and no credentials:

    python3 tools/test_series_topic.py

All series records are synthetic but shaped exactly like official GET /series
responses (docs: api-reference/market/get-series-list — fields `ticker`, `category`,
`categories`, `tags`, `product_metadata`). No live API is called; the collector's
main() is never invoked (it only runs under __main__).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from collector import merge_scope_resolutions, series_topic  # noqa: E402

PASS = 0
FAIL = 0


def check(name, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
        print(f"  ok   {name} -> {got!r}")
    else:
        FAIL += 1
        print(f"  FAIL {name}: got {got!r}, want {want!r}")


def S(ticker, category="", categories=None, tags=None, scope=None):
    """Build a synthetic official-shaped series record."""
    rec = {"ticker": ticker, "category": category,
           "categories": categories or [], "tags": tags or []}
    if scope is not None:
        rec["product_metadata"] = {"scope": scope}
    return rec


print("series_topic — specific topics (unchanged behaviour)")
check("gasoline scope", series_topic(S("KXAAAGASD", scope="Gasoline")), "gas")
check("tag Gas", series_topic(S("DIESEL", tags=["Gas"])), "gas")
check("tag Golf", series_topic(S("KXPGATOUR", tags=["Golf"])), "golf")
check("tag Elections", series_topic(S("KXPRESNOMD", tags=["Elections"])), "elections")
check("tag Crypto", series_topic(S("KXBTC", tags=["Crypto"])), "crypto")
check("tag Bitcoin", series_topic(S("KXBTC", tags=["Bitcoin"])), "crypto")
check("category Elections", series_topic(S("X", category="Elections")), "elections")
check("category Crypto", series_topic(S("X", categories=["Crypto"])), "crypto")
check("diesel alone stays unmapped", series_topic(S("DIESEL", tags=["Diesel"])), None)
check("soccer unmapped", series_topic(S("X", category="Sports", tags=["Soccer"])), None)
check("empty record", series_topic({}), None)
check("None record", series_topic(None), None)

print("series_topic — culture expansion (E2)")
check("category Entertainment", series_topic(S("X", category="Entertainment")), "culture")
check("categories Entertainment", series_topic(S("X", categories=["Entertainment"])), "culture")
check("category Culture", series_topic(S("X", category="Culture")), "culture")
check("tag Music", series_topic(S("KXMUSICREPORT", tags=["Music"])), "culture")
check("tag Movies", series_topic(S("KXMOVIECAST", tags=["Movies"])), "culture")
check("tag Oscars", series_topic(S("KXOSCARS", tags=["Oscars"])), "culture")
check("tag Awards", series_topic(S("X", tags=["Awards"])), "culture")
check("tag Television", series_topic(S("X", tags=["Television"])), "culture")
check("tag Grammys", series_topic(S("X", tags=["Grammys"])), "culture")
check("tag Rotten Tomatoes", series_topic(S("X", tags=["Rotten Tomatoes"])), "culture")
check("tag Video games", series_topic(S("X", tags=["Video games"])), "culture")
check("tag People", series_topic(S("X", tags=["People"])), "culture")
check("case-insensitive", series_topic(S("X", tags=["MUSIC"], category="entertainment")), "culture")
check("broad Food stays unmapped", series_topic(S("X", tags=["Food"])), None)
check("broad Art stays unmapped", series_topic(S("X", tags=["Art"])), None)

print("series_topic — priority: specific topics win over culture")
check("Golf tag + Entertainment cat", series_topic(S("X", category="Entertainment", tags=["Golf"])), "golf")
check("Music tag + Crypto cat", series_topic(S("X", categories=["Crypto"], tags=["Music"])), "culture")
check("Crypto tag + Music tag", series_topic(S("X", tags=["Music", "Crypto"])), "crypto")
check("Elections cat + Entertainment cat", series_topic(S("X", categories=["Entertainment", "Elections"])), "elections")
check("Gasoline scope + Music tag", series_topic(S("X", tags=["Music"], scope="Gasoline")), "gas")

print("merge_scope_resolutions — union (E3)")
settled = [{
    "topic": "crypto", "series_ticker": "KXBTC", "event_ticker": "KXBTC-E1",
    "market_ticker": "KXBTC-E1-YES", "status": "finalized", "title": "Settled BTC",
    "result": "yes", "settlement_value_dollars": "1.0000",
    "settlement_ts": "2026-11-20T00:00:00Z", "close_time": "2026-11-20T00:00:00Z",
    "expiration_value": "1", "volume_fp": "10.00", "open_interest_fp": "5.00",
    "rules_primary_head": None, "market_url": "https://example.invalid/m",
}]
scope_rows = [
    {"topic": "golf", "series_ticker": "KXPGATOUR", "event_ticker": "KXPGATOUR-E2",
     "market_ticker": "KXPGATOUR-E2-YES", "status": "finalized",
     "market_title": "Scope golf", "result": "no", "close_time": "2026-11-21T00:00:00Z",
     "volume_fp": "3.00", "open_interest_fp": "1.00", "rules_primary_head": None,
     "market_url": "https://example.invalid/g"},
    {"topic": "crypto", "series_ticker": "KXBTC", "event_ticker": "KXBTC-E1",
     "market_ticker": "KXBTC-E1-YES", "status": "finalized",
     "market_title": "Scope copy (must lose)", "result": "yes",
     "close_time": "2026-11-20T00:00:00Z", "volume_fp": "10.00",
     "open_interest_fp": "5.00", "rules_primary_head": None,
     "market_url": "https://example.invalid/m"},
    {"topic": "elections", "series_ticker": "KXPRESNOMD", "event_ticker": "KXPRESNOMD-E3",
     "market_ticker": "KXPRESNOMD-E3-YES", "status": "active",
     "market_title": "Still live", "result": "", "close_time": "2027-01-01T00:00:00Z",
     "volume_fp": "1.00", "open_interest_fp": "1.00", "rules_primary_head": None,
     "market_url": "https://example.invalid/e"},
]
merged = merge_scope_resolutions(settled, scope_rows)
check("union length (settled + scope-only)", len(merged), 2)
by_t = {r["market_ticker"]: r for r in merged}
check("settled row wins on duplicate", by_t["KXBTC-E1-YES"]["title"], "Settled BTC")
check("scope-only row added", by_t["KXPGATOUR-E2-YES"]["result"], "no")
check("scope-only settlement blank (not guessed)", by_t["KXPGATOUR-E2-YES"]["settlement_ts"], None)
check("live row excluded", "KXPRESNOMD-E3-YES" in by_t, False)
check("newest first", merged[0]["market_ticker"], "KXPGATOUR-E2-YES")
check("empty inputs", merge_scope_resolutions([], []), [])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
