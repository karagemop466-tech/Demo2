#!/usr/bin/env python3
"""jump_detect.py — find sharp moves of $0.10 or more in the in-scope markets.

A "jump" is two consecutive official price points that differ by $0.10 or more in
either direction. Points come from the official Kalshi demo candlestick endpoint
and, for the busiest markets, from the official trade prints so that a move
inside a single minute is not smoothed away.

Every jump keeps the exact official URL it was read from, plus the market, event
and series endpoints and the settlement references Kalshi itself publishes for
that series. The cause of a move is never asserted: the Trade API has no news
feed, so there is no official source that could confirm one.

    python3 desk/tools/jump_detect.py                  # top 40 markets
    python3 desk/tools/jump_detect.py --markets 80
    python3 desk/tools/jump_detect.py --offline        # keep the existing report

Exit code 0 on success. Writes desk/data/jumps.json.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESK = ROOT / "desk"
DATA = DESK / "data"
API = "https://external-api.demo.kalshi.co/trade-api/v2"
THRESHOLD = 0.10


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso(epoch) -> str:
    if not epoch:
        return ""
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def load(path: pathlib.Path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def http_json(url: str, timeout: int = 20, retries: int = 4):
    """GET with backoff. Kalshi documents that public endpoints charge the IP
    address's budget first, so a 429 is expected and only needs a pause."""
    delay = 1.5
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": "Demo2-jump/1.0",
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return exc.code, None
        except Exception:  # noqa: BLE001 — a failed request is reported, not hidden
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return None, None
    return None, None


def in_scope_markets(limit: int):
    """In-scope markets ordered by how much they trade."""
    snap = load(ROOT / "data" / "dashboard_instrument.json") or {}
    series_sources = {}
    for s in (snap.get("series") or []):
        if s.get("ticker"):
            series_sources[s["ticker"]] = s.get("settlement_sources") or []

    markets = []
    seen = set()
    for topic in ("gas", "elections", "culture", "crypto", "golf"):
        for row in (snap.get("markets", {}) or {}).get(topic) or []:
            ticker = row.get("ticker")
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            markets.append({
                "ticker": ticker,
                "series_ticker": row.get("series_ticker") or "",
                "event_ticker": row.get("event_ticker") or "",
                "title": row.get("title") or "",
                "topic": topic,
                "volume_24h_fp": row.get("volume_24h_fp"),
                "open_interest_fp": row.get("open_interest_fp"),
                "close_time": row.get("close_time") or "",
                "settlement_sources": series_sources.get(row.get("series_ticker") or "", []),
            })
    markets.sort(key=lambda m: (-(float(m["volume_24h_fp"] or 0)), -(float(m["open_interest_fp"] or 0))))
    return markets[:limit], len(markets)


def detect_from_candles(market, period: int, span_seconds: int, window_label: str):
    """Consecutive official closes that differ by the threshold."""
    series = market["series_ticker"]
    if not series:
        return []
    now = int(time.time())
    start = now - span_seconds
    url = (f"{API}/series/{series}/markets/{market['ticker']}/candlesticks"
           f"?period_interval={period}&start_ts={start}&end_ts={now}")
    status, payload = http_json(url)
    if status != 200 or not payload:
        return []
    candles = payload.get("candlesticks") or []
    points = []
    for c in candles:
        close = (c.get("price") or {}).get("close_dollars")
        try:
            value = float(close)
        except (TypeError, ValueError):
            continue
        points.append((c.get("end_period_ts"), value, c))
    points.sort(key=lambda p: p[0] or 0)

    out = []
    for index in range(1, len(points)):
        ts0, p0, _ = points[index - 1]
        ts1, p1, candle = points[index]
        delta = p1 - p0
        if abs(delta) >= THRESHOLD:
            out.append({
                "kind": "close to close",
                "window": window_label,
                "ts": iso(ts1),
                "epoch": ts1,
                "from": round(p0, 4),
                "to": round(p1, 4),
                "delta": round(delta, 4),
                "direction": "up" if delta > 0 else "down",
                "source": url,
            })
    # an intra-candle swing of the same size is a different thing and is
    # labelled as such rather than folded into the close-to-close list
    for ts1, p1, candle in points:
        high = (candle.get("price") or {}).get("high_dollars")
        low = (candle.get("price") or {}).get("low_dollars")
        try:
            hi = float(high)
            lo = float(low)
        except (TypeError, ValueError):
            continue
        if hi - lo >= THRESHOLD:
            out.append({
                "kind": "high to low inside one candle",
                "window": window_label,
                "ts": iso(ts1),
                "epoch": ts1,
                "from": round(lo, 4),
                "to": round(hi, 4),
                "delta": round(hi - lo, 4),
                "direction": "up" if hi >= lo else "down",
                "source": url,
            })
    return out


def detect_from_trades(market):
    """Sub-minute moves taken from the official trade prints."""
    url = f"{API}/markets/trades?ticker={market['ticker']}&limit=500"
    status, payload = http_json(url)
    if status != 200 or not payload:
        return []
    trades = payload.get("trades") or []
    points = []
    for t in trades:
        price = t.get("yes_price_dollars")
        try:
            value = float(price)
        except (TypeError, ValueError):
            continue
        created = t.get("created_time")
        epoch = 0
        if created:
            try:
                epoch = int(datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp())
            except ValueError:
                epoch = 0
        points.append((epoch, value))
    points.sort(key=lambda p: p[0])
    out = []
    for index in range(1, len(points)):
        ts0, p0 = points[index - 1]
        ts1, p1 = points[index]
        delta = p1 - p0
        if abs(delta) >= THRESHOLD:
            out.append({
                "kind": "trade to trade",
                "window": "trade prints",
                "ts": iso(ts1),
                "epoch": ts1,
                "from": round(p0, 4),
                "to": round(p1, 4),
                "delta": round(delta, 4),
                "direction": "up" if delta > 0 else "down",
                "source": url,
            })
    return out


def main() -> int:
    offline = "--offline" in sys.argv
    limit = 40
    if "--markets" in sys.argv:
        try:
            limit = int(sys.argv[sys.argv.index("--markets") + 1])
        except (IndexError, ValueError):
            limit = 40

    if offline:
        print("offline: keeping the existing desk/data/jumps.json")
        return 0

    markets, universe = in_scope_markets(limit)
    jumps = []
    requests = 0
    errors = []

    for index, market in enumerate(markets):
        url_market = f"{API}/markets/{market['ticker']}"
        try:
            found = detect_from_candles(market, 1, 24 * 3600, "last 24 hours, 1 minute candles")
            requests += 1
            found += detect_from_candles(market, 60, 7 * 24 * 3600, "last 7 days, 60 minute candles")
            requests += 1
            if index < 10:
                found += detect_from_trades(market)
                requests += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"ticker": market["ticker"], "error": str(exc)})
            found = []
        for jump in found:
            jump.update({
                "ticker": market["ticker"],
                "series_ticker": market["series_ticker"],
                "event_ticker": market["event_ticker"],
                "title": market["title"],
                "topic": market["topic"],
                "market_source": url_market,
                "event_source": f"{API}/events/{market['event_ticker']}" if market["event_ticker"] else "",
                "series_source": f"{API}/series/{market['series_ticker']}" if market["series_ticker"] else "",
                "settlement_sources": market["settlement_sources"],
                "cause": "",
                "cause_note": "Kalshi publishes no news feed in the Trade API, so no official source can confirm what caused this move.",
            })
            jumps.append(jump)
        time.sleep(0.2)

    jumps.sort(key=lambda j: (-abs(j["delta"]), j.get("epoch") or 0))
    report = {
        "generated_at": now_iso(),
        "threshold_dollars": THRESHOLD,
        "rule": "two consecutive official price points whose absolute difference is at least $0.10",
        "markets_in_universe": universe,
        "markets_checked": len(markets),
        "requests": requests,
        "errors": errors,
        "jump_count": len(jumps),
        "source_api": API,
        "docs": {
            "candlesticks": "https://docs.kalshi.com/api-reference/market/get-market-candlesticks",
            "trades": "https://docs.kalshi.com/api-reference/market/get-trades",
        },
        "jumps": jumps,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "jumps.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"checked {len(markets)} of {universe} in-scope markets with {requests} official requests")
    print(f"found {len(jumps)} move(s) of {THRESHOLD:.2f} or more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
