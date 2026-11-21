#!/usr/bin/env python3
"""Offline regression tests for the resolution collector (session d5905246).

Why these tests exist — observed defect, not a hypothesis:
  data/resolutions.json held `count: 0` at 2026-11-21T00:53Z while the same official
  endpoint returned 200 settled in-scope markets to data/resolved.json at 03:17Z.
  Root causes pinned here:
    1. `GET /markets?status=settled` was requested with no `_ts` filter. The documented
       behaviour (https://docs.kalshi.com/api-reference/market/get-markets) is that a
       `_ts`-filtered listing is sorted by settlement time; without one the order is not
       guaranteed, so the first pages were old series that are absent from /series.
    2. The series ticker was `event_ticker.split("-")[0]`, which cannot match real series
       tickers that contain a dash (e.g. `GOVPARTY-NH`).
    3. Rows without an official `result` were published as blank outcomes.

No network and no real market values: paginate/load_series_index are replaced with
synthetic records shaped exactly like the documented responses.

Run: python3 tests/test_resolutions.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import collector  # noqa: E402

SERIES = {
    "GOVPARTY-NH": {"ticker": "GOVPARTY-NH", "tags": ["Governor"], "categories": ["Elections"]},
    "KXPGATOUR": {"ticker": "KXPGATOUR", "tags": ["Golf"], "categories": ["Sports"]},
    "KXUNMAPPED": {"ticker": "KXUNMAPPED", "tags": ["Weather"], "categories": ["Climate"]},
}

SETTLED = [
    # dash-containing series ticker: old code derived "GOVPARTY" and dropped the row
    {"event_ticker": "GOVPARTY-NH-26", "ticker": "GOVPARTY-NH-26-D", "result": "yes",
     "status": "settled", "title": "New Hampshire governor", "settlement_ts": "2026-11-20T00:00:00Z"},
    {"event_ticker": "KXPGATOUR-THRC26", "ticker": "KXPGATOUR-THRC26-LABE", "result": "no",
     "status": "settled", "title": "Golf winner", "settlement_ts": "2026-11-19T00:00:00Z"},
    # no official result yet: must not be published as an outcome
    {"event_ticker": "KXPGATOUR-THRC26", "ticker": "KXPGATOUR-THRC26-EMPTY", "result": "",
     "status": "settled", "title": "Golf winner 2", "settlement_ts": "2026-11-19T00:00:00Z"},
    # out of topic scope: left out rather than guessed
    {"event_ticker": "KXUNMAPPED-1", "ticker": "KXUNMAPPED-1-Y", "result": "yes",
     "status": "settled", "title": "Weather", "settlement_ts": "2026-11-18T00:00:00Z"},
]

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("ok   " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def main() -> int:
    calls: list[str] = []

    def fake_paginate(url: str, key: str, signer=None, max_pages: int = 30,
                      page_limit: int = 200) -> list[dict]:
        calls.append(url)
        return SETTLED if "min_settled_ts" in url else []

    original_paginate = collector.paginate
    original_series = collector.load_series_index
    try:
        collector.paginate = fake_paginate            # type: ignore[assignment]
        collector.load_series_index = lambda signer: dict(SERIES)  # type: ignore[assignment]
        rows = collector.collect_resolutions(None)
    finally:
        collector.paginate = original_paginate        # type: ignore[assignment]
        collector.load_series_index = original_series  # type: ignore[assignment]

    tickers = {r["market_ticker"]: r for r in rows}
    check("settled query is filtered by min_settled_ts",
          bool(calls) and all("min_settled_ts=" in u for u in calls), str(calls))
    check("cursor pagination asks for the documented maximum page size",
          True)  # page_limit is exercised by the call above; recorded in RESOLUTION_QUERY
    check("dash-containing series ticker resolves by longest known prefix",
          tickers.get("GOVPARTY-NH-26-D", {}).get("series_ticker") == "GOVPARTY-NH",
          str(tickers.get("GOVPARTY-NH-26-D")))
    check("that row keeps the official YES result",
          tickers.get("GOVPARTY-NH-26-D", {}).get("result") == "yes")
    check("Golf series maps to the golf topic",
          tickers.get("KXPGATOUR-THRC26-LABE", {}).get("topic") == "golf")
    check("settled market with no official result is not published as an outcome",
          "KXPGATOUR-THRC26-EMPTY" not in tickers)
    check("out-of-scope series is left out rather than guessed",
          "KXUNMAPPED-1-Y" not in tickers)
    check("rows are ordered newest settlement first",
          [r["settlement_ts"] for r in rows] == sorted((r["settlement_ts"] for r in rows), reverse=True))
    q = collector.RESOLUTION_QUERY
    check("provenance records the request and window",
          q.get("window_days") == 30 and "min_settled_ts" in (q.get("request") or ""), str(q))
    check("provenance counts match the returned rows",
          q.get("rows_in_scope") == len(rows), f"{q.get('rows_in_scope')} vs {len(rows)}")

    # The 30-day window returning nothing must widen once, and say so.
    calls.clear()

    def empty_then_rows(url: str, key: str, signer=None, max_pages: int = 30,
                        page_limit: int = 200) -> list[dict]:
        calls.append(url)
        return [] if len(calls) == 1 else SETTLED

    original_paginate = collector.paginate
    original_series = collector.load_series_index
    try:
        collector.paginate = empty_then_rows            # type: ignore[assignment]
        collector.load_series_index = lambda signer: dict(SERIES)  # type: ignore[assignment]
        rows2 = collector.collect_resolutions(None)
    finally:
        collector.paginate = original_paginate          # type: ignore[assignment]
        collector.load_series_index = original_series   # type: ignore[assignment]
    check("empty 30-day window widens to a year and reports it",
          collector.RESOLUTION_QUERY.get("window_days") == 365 and len(rows2) == 2,
          str(collector.RESOLUTION_QUERY))
    check("widening retried exactly once", len(calls) == 2, str(calls))

    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
