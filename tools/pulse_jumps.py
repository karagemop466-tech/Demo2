#!/usr/bin/env python3
"""Pulse sharp-jump detector: |price move| >= $0.10 between consecutive prints.

Inputs (all official Kalshi demo API snapshots, already collected):
  data/dashboard_instrument.json  — trades (GET /markets/trades) + markets + series
  data/history_instrument/*.json  — collector tick samples (last price per market)

Output:
  data/pulse_jumps.json — every detected jump with before/after prices, timestamps,
  trade/sample ids, and verified cause-context links (Kalshi event/market/rules/
  settlement-source URLs). External news causation is NEVER invented: the Kalshi
  API does not provide it, so that column stays blank and flagged unverified.

Official endpoint patterns used (verified, see docs/VERIFICATION.md):
  GET /markets/{ticker}                    docs/api-reference/market/get-market
  GET /markets/trades?ticker=              docs/api-reference/market/get-trades
  GET /markets/{ticker}/orderbook          docs/api-reference/market/get-market-orderbook
  GET /series/{s}/markets/{t}/candlesticks docs/api-reference/market/get-market-candlesticks
  GET /events/{event_ticker}               docs/api-reference/events/get-events
  Settlement: docs/getting_started/market_settlement (YES/NO pays $1)

Stdlib only. Offline: reads local snapshots, makes no network calls.
"""
from __future__ import annotations

import glob
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
API = "https://external-api.demo.kalshi.co/trade-api/v2"
THRESHOLD = 0.10


def fnum(v, default=None):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def parse_ts(s):
    """ISO string -> epoch seconds (float) or None."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def main() -> int:
    snap_path = DATA / "dashboard_instrument.json"
    snap = json.loads(snap_path.read_text())
    markets_by_ticker: dict[str, dict] = {}
    for rows in (snap.get("markets") or {}).values():
        for m in rows:
            markets_by_ticker[m["ticker"]] = m
    for m in snap.get("resolved") or []:
        markets_by_ticker.setdefault(m["ticker"], m)
    series_by_ticker = {s["ticker"]: s for s in (snap.get("series") or [])}

    def enrich(ticker: str) -> dict:
        m = markets_by_ticker.get(ticker, {})
        s = series_by_ticker.get(m.get("series_ticker", ""), {})
        settle = (s.get("settlement_sources") or [{}])[0] if s else {}
        event_ticker = m.get("event_ticker") or ""
        series_ticker = m.get("series_ticker") or ""
        return {
            "ticker": ticker,
            "title": m.get("title") or "",
            "topic": m.get("topic") or "",
            "event_ticker": event_ticker,
            "series_ticker": series_ticker,
            "market_url": f"{API}/markets/{ticker}",
            "trades_url": f"{API}/markets/trades?ticker={ticker}&limit=1000",
            "orderbook_url": f"{API}/markets/{ticker}/orderbook?depth=20",
            "candlesticks_url": (
                f"{API}/series/{series_ticker}/markets/{ticker}/candlesticks"
                if series_ticker else ""
            ),
            "event_url": f"{API}/events/{event_ticker}" if event_ticker else "",
            "settlement_source_name": settle.get("name") or "",
            "settlement_source_url": settle.get("url") or "",
            "contract_terms_url": s.get("contract_terms_url") or "",
            "cause_note": (
                "Unverified: the Kalshi API does not provide news causation. "
                "Use the event/market/rules/settlement-source links to investigate; "
                "no external news URL is asserted."
            ),
        }

    jumps: list[dict] = []

    # --- source 1: trade prints (yes_price_dollars sequence, ascending time) ---
    for ticker, block in (snap.get("trades") or {}).items():
        trades = sorted(
            block.get("trades") or [],
            key=lambda t: parse_ts(t.get("created_time")) or 0,
        )
        prev = None
        for t in trades:
            px = fnum(t.get("yes_price_dollars"))
            ts = parse_ts(t.get("created_time"))
            if px is None or ts is None:
                continue
            if prev is not None:
                delta = px - prev["price"]
                if abs(delta) >= THRESHOLD:
                    j = enrich(ticker)
                    j.update({
                        "source": "trade_prints",
                        "ts_before": prev["ts_iso"],
                        "ts_after": t.get("created_time"),
                        "price_before": prev["price"],
                        "price_after": px,
                        "delta": round(delta, 4),
                        "trade_id_before": prev.get("trade_id"),
                        "trade_id_after": t.get("trade_id"),
                        "count_fp_after": t.get("count_fp"),
                    })
                    jumps.append(j)
            prev = {"price": px, "ts_iso": t.get("created_time"),
                    "trade_id": t.get("trade_id")}

    # --- source 2: collector tick samples (last price lp, ascending sample ts) ---
    samples: list[dict] = []
    for path in sorted(glob.glob(str(DATA / "history_instrument" / "20*.json"))):
        try:
            h = json.loads(Path(path).read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for s in h.get("samples") or []:
            if isinstance(s.get("ts"), (int, float)) and isinstance(s.get("markets"), dict):
                samples.append(s)
    samples.sort(key=lambda s: s["ts"])
    tickers: set[str] = set()
    for s in samples:
        tickers.update(s["markets"].keys())
    for ticker in sorted(tickers):
        prev = None
        for s in samples:
            cell = s["markets"].get(ticker)
            if not cell:
                continue
            px = fnum(cell.get("lp"))
            if px is None:
                continue
            if prev is not None:
                delta = px - prev["price"]
                if abs(delta) >= THRESHOLD:
                    j = enrich(ticker)
                    j.update({
                        "source": "collector_ticks",
                        "ts_before": prev["ts_iso"],
                        "ts_after": s["ts_iso"] if "ts_iso" in s else datetime.fromtimestamp(
                            s["ts"], tz=timezone.utc).isoformat(),
                        "price_before": prev["price"],
                        "price_after": px,
                        "delta": round(delta, 4),
                        "trade_id_before": None,
                        "trade_id_after": None,
                        "count_fp_after": None,
                        "tick_gap_seconds": int(s["ts"] - prev["ts"]),
                    })
                    jumps.append(j)
            prev = {"price": px, "ts": s["ts"],
                    "ts_iso": s.get("ts_iso") or datetime.fromtimestamp(
                        s["ts"], tz=timezone.utc).isoformat()}

    # sort newest first
    def jump_ts(j):
        return parse_ts(j.get("ts_after")) or 0
    jumps.sort(key=jump_ts, reverse=True)

    by_topic: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for j in jumps:
        by_topic[j["topic"] or "unknown"] = by_topic.get(j["topic"] or "unknown", 0) + 1
        by_source[j["source"]] = by_source.get(j["source"], 0) + 1

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "threshold_usd": THRESHOLD,
        "definition": (
            "|yes_price_after - yes_price_before| >= 0.10 between consecutive "
            "trade prints (GET /markets/trades) or consecutive collector tick "
            "samples (last_price_dollars). Prices are official API fields; "
            "the jump flag is computed arithmetic."
        ),
        "inputs": [
            "data/dashboard_instrument.json (trades, markets, series)",
            "data/history_instrument/20*.json (tick samples)",
        ],
        "counts": {"total": len(jumps), "by_topic": by_topic, "by_source": by_source},
        "jumps": jumps,
        "docs": {
            "get_trades": "https://docs.kalshi.com/api-reference/market/get-trades",
            "get_market": "https://docs.kalshi.com/api-reference/market/get-market",
            "get_orderbook": "https://docs.kalshi.com/api-reference/market/get-market-orderbook",
            "candlesticks": "https://docs.kalshi.com/api-reference/market/get-market-candlesticks",
            "get_events": "https://docs.kalshi.com/api-reference/events/get-events",
            "settlement": "https://docs.kalshi.com/getting_started/market_settlement",
        },
    }
    (DATA / "pulse_jumps.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"pulse_jumps: {len(jumps)} jumps (by_topic={by_topic}, by_source={by_source})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
