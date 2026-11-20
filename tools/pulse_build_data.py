#!/usr/bin/env python3
"""Build trimmed pulse views from data/dashboard_instrument.json.

Outputs (small, browser-friendly; the 10 MB source snapshot is never fetched
by pulse pages directly):
  data/pulse_top.json      — top 10 open markets per topic by computed notional
  data/pulse_resolved.json — resolved traded markets (minimal fields) + counts

Stdlib only. Offline.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
API = "https://external-api.demo.kalshi.co/trade-api/v2"


def fnum(v, default=0.0):
    try:
        return float(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def main() -> int:
    snap = json.loads((DATA / "dashboard_instrument.json").read_text())
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    top = {"generated_at": gen, "topics": {}}
    for topic, rows in (snap.get("markets") or {}).items():
        ranked = sorted(rows, key=lambda m: fnum(m.get("notional_lifetime_usd")),
                        reverse=True)[:10]
        if topic == "gas":
            # Strict gas-price filter (title/ticker names gas/gasoline/diesel).
            # The collector's gas scope is broader (Oil-and-energy tag, which
            # includes solar KXSOLAR). Both views are shown; see flag P-F01.
            strict = [m for m in rows if any(
                w in ((m.get("title") or "") + " " + m["ticker"] + " " +
                      (m.get("series_ticker") or "")).lower()
                for w in ("gas", "gasoline", "diesel", "natgas", "natural gas"))]
            strict = sorted(strict, key=lambda m: fnum(m.get("notional_lifetime_usd")),
                            reverse=True)[:10]
            top["topics"]["gas_strict"] = [{
                "ticker": m["ticker"], "title": m.get("title") or "",
                "event_ticker": m.get("event_ticker") or "",
                "series_ticker": m.get("series_ticker") or "",
                "last_price": m.get("last_price_dollars"),
                "yes_bid": m.get("yes_bid_dollars"), "yes_ask": m.get("yes_ask_dollars"),
                "volume_fp": m.get("volume_fp"), "volume_24h_fp": m.get("volume_24h_fp"),
                "open_interest_fp": m.get("open_interest_fp"),
                "notional_lifetime_usd": m.get("notional_lifetime_usd"),
                "notional_24h_usd": m.get("notional_24h_usd"),
                "close_time": m.get("close_time"), "status": m.get("status"),
                "source": m.get("source_market_url") or f"{API}/markets/{m['ticker']}",
            } for m in strict]
        top["topics"][topic] = [{
            "ticker": m["ticker"], "title": m.get("title") or "",
            "event_ticker": m.get("event_ticker") or "",
            "series_ticker": m.get("series_ticker") or "",
            "last_price": m.get("last_price_dollars"),
            "yes_bid": m.get("yes_bid_dollars"), "yes_ask": m.get("yes_ask_dollars"),
            "volume_fp": m.get("volume_fp"), "volume_24h_fp": m.get("volume_24h_fp"),
            "open_interest_fp": m.get("open_interest_fp"),
            "notional_lifetime_usd": m.get("notional_lifetime_usd"),
            "notional_24h_usd": m.get("notional_24h_usd"),
            "close_time": m.get("close_time"), "status": m.get("status"),
            "source": m.get("source_market_url") or f"{API}/markets/{m['ticker']}",
        } for m in ranked]
    (DATA / "pulse_top.json").write_text(json.dumps(top, indent=1) + "\n")

    resolved = snap.get("resolved") or []
    traded = [r for r in resolved if fnum(r.get("volume_fp")) > 0]
    traded.sort(key=lambda r: r.get("close_time") or "", reverse=True)
    res = {
        "generated_at": gen,
        "counts": {"resolved_total": len(resolved), "traded": len(traded),
                   "never_traded": len(resolved) - len(traded)},
        "markets": [{
            "ticker": r["ticker"], "title": r.get("title") or "",
            "topic": r.get("topic") or "", "result": r.get("result") or "",
            "status": r.get("status") or "",
            "last_price": r.get("last_price_dollars"),
            "volume_fp": r.get("volume_fp"),
            "close_time": r.get("close_time"),
            "source": r.get("source_market_url") or f"{API}/markets/{r['ticker']}",
        } for r in traded],
    }
    (DATA / "pulse_resolved.json").write_text(json.dumps(res, indent=1) + "\n")

    # Orderbook snapshots for the top tickers (so the live page has a labelled
    # snapshot fallback without fetching the 10 MB source file).
    books = snap.get("orderbooks") or {}
    top_tickers = {m["ticker"] for rows in top["topics"].values() for m in rows}
    book_out = {"generated_at": gen, "books": {}}
    for tk in sorted(top_tickers):
        if tk in books:
            book_out["books"][tk] = books[tk]
    (DATA / "pulse_books.json").write_text(json.dumps(book_out, indent=1) + "\n")
    print(f"pulse_build_data: top topics={list(top['topics'])} resolved_traded={len(traded)} books={len(book_out['books'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
