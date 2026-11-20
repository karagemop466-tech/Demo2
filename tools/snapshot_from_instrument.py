#!/usr/bin/env python3
"""Adapt the proven instrument-panel artifact into the canonical root snapshot.

The canonical root dashboard (assets/site.js + tools/build_site.py) loads
data/snapshot.json (plus data/topic-<t>.json, data/resolutions.json,
data/history.json). The instrument-panel collector (instrument-panel/tools/
kalshi_collect.py) already performs the bounded, deterministic collection that
works in the demo environment and writes data/dashboard_instrument.json with the
same underlying market / resolved / orderbook / trade data.

This script is a deterministic, offline transform: it reads the proven
instrument-panel artifact and re-emits the canonical root data files in the exact
schema the root site consumes. Nothing is invented — every price, volume and
result comes from the instrument-panel artifact, which in turn comes from the
Kalshi demo Trade API.

Why not re-run the root collector? tools/collector.py's global /markets
pagination stalls in the demo environment (51 pages for settled markets). The
instrument-panel pipeline avoids that by intersecting a bounded open-market
stream with per-series queries. This adapter keeps that proven strategy and
only reshapes the output.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TOPICS = ["gas", "elections", "culture", "crypto", "golf"]


def fnum(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def usd_levels(arr: Any) -> list[list[float]]:
    """Normalise an orderbook level array [[price, count], ...] to floats."""
    out: list[list[float]] = []
    for p, q in (arr or []):
        pf, qf = fnum(p), fnum(q)
        if pf is None or qf is None:
            continue
        out.append([pf, qf])
    return out


def build_orderbook(ob: dict) -> dict:
    """Map an instrument-panel orderbook to the canonical root schema."""
    yes = usd_levels(ob.get("yes_dollars"))
    no = usd_levels(ob.get("no_dollars"))
    # canonical: best bid first (descending price); asks ascending
    yes.sort(key=lambda x: x[0], reverse=True)
    no.sort(key=lambda x: x[0], reverse=True)
    # a NO bid at p is a YES ask at 1 - p (Kalshi orderbook docs)
    asks = sorted([[round(1 - p, 4), q] for p, q in no], key=lambda x: x[0])
    best_bid = yes[0][0] if yes else None
    best_ask = asks[0][0] if asks else None
    return {
        "yes_bids": yes,
        "no_bids": no,
        "derived_yes_asks": asks,
        "best_yes_bid": best_bid,
        "best_yes_ask_derived": best_ask,
        "yes_bid_contracts": round(sum(q for _, q in yes), 2),
        "derived_ask_contracts": round(sum(q for _, q in asks), 2),
        "spread_derived": round(best_ask - best_bid, 4) if best_bid is not None and best_ask is not None else None,
        "raw_request": ob.get("source_url"),
    }


def market_row(m: dict, topic: str) -> dict:
    """Map an instrument-panel market row to the canonical market row schema."""
    est = None
    v = fnum(m.get("volume_fp"))
    p = fnum(m.get("last_price_dollars"))
    if v is not None and p is not None:
        est = round(v * p, 2)  # documented estimate, labelled in the UI
    ticker = m.get("ticker") or ""
    return {
        "topic": topic,
        "event_ticker": m.get("event_ticker"),
        "series_ticker": m.get("series_ticker"),
        "series_title": m.get("series_title"),
        "event_title": m.get("event_title"),
        "market_ticker": ticker,
        "market_title": m.get("title"),
        "yes_sub_title": m.get("yes_sub_title"),
        "status": m.get("status"),
        "result": m.get("result") or "",
        "yes_bid_dollars": m.get("yes_bid_dollars"),
        "yes_ask_dollars": m.get("yes_ask_dollars"),
        "no_bid_dollars": m.get("no_bid_dollars"),
        "no_ask_dollars": m.get("no_ask_dollars"),
        "yes_bid_size_fp": m.get("yes_bid_size_fp"),
        "yes_ask_size_fp": m.get("yes_ask_size_fp"),
        "last_price_dollars": m.get("last_price_dollars"),
        "previous_price_dollars": m.get("previous_price_dollars"),
        "volume_fp": m.get("volume_fp"),
        "volume_24h_fp": m.get("volume_24h_fp"),
        "open_interest_fp": m.get("open_interest_fp"),
        "close_time": m.get("close_time"),
        "open_time": m.get("open_time"),
        "updated_time": m.get("updated_time"),
        "est_dollar_volume": est,
        "open_interest_usd": m.get("open_interest_usd"),
        "notional_lifetime_usd": m.get("notional_lifetime_usd"),
        "notional_24h_usd": m.get("notional_24h_usd"),
        "market_url": m.get("source_market_url") or (
            f"https://kalshi.com/markets/{ticker.lower()}" if ticker else None
        ),
        "source_url": m.get("source_url"),
    }


def resolution_row(r: dict, topic: str) -> dict:
    """Map an instrument-panel resolved row to the canonical resolution schema."""
    ticker = r.get("ticker") or ""
    return {
        "topic": topic,
        "series_ticker": r.get("series_ticker"),
        "event_ticker": r.get("event_ticker"),
        "market_ticker": ticker,
        "title": r.get("title"),
        "status": r.get("status"),
        "result": r.get("result") or "",
        # The instrument artifact does not carry settlement_value_dollars or
        # settlement_ts; leave them null rather than inventing a value.
        "settlement_value_dollars": None,
        "settlement_ts": None,
        "close_time": r.get("close_time"),
        "volume_fp": r.get("volume_fp"),
        "open_interest_fp": r.get("open_interest_fp"),
        "market_url": r.get("source_market_url") or (
            f"https://kalshi.com/markets/{ticker.lower()}" if ticker else None
        ),
        "source_url": r.get("source_url"),
    }


def build_series_inventory(series: list[dict]) -> dict:
    tags: dict[str, int] = {}
    cats: dict[str, int] = {}
    in_scope: dict[str, list[str]] = {t: [] for t in TOPICS}
    for s in series:
        topic = s.get("topic")
        if topic in in_scope:
            in_scope[topic].append(s.get("ticker") or "")
        for t in s.get("tags") or []:
            tags[str(t)] = tags.get(str(t), 0) + 1
        for c in s.get("categories") or []:
            cats[str(c)] = cats.get(str(c), 0) + 1
    return {
        "series_count": len(series),
        "tags_top": dict(sorted(tags.items(), key=lambda kv: -kv[1])[:60]),
        "categories": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
        "in_scope_series": in_scope,
    }


def build_topic_catalog(series: list[dict], markets_by_topic: dict[str, list[dict]]) -> dict:
    catalog: dict[str, dict] = {}
    for t in TOPICS:
        tickers = sorted({s.get("ticker") or "" for s in series if s.get("topic") == t})
        live = sorted({m.get("series_ticker") for m in markets_by_topic.get(t, []) if m.get("series_ticker")})
        catalog[t] = {
            "series_in_catalog": len(tickers),
            "series_tickers": tickers[:40],
            "series_with_live_markets": live,
        }
    return catalog


def build_api_log(instr: dict) -> list[dict]:
    """Honest provenance: the instrument-panel artifact's own request record."""
    health = instr.get("health") or {}
    log: list[dict] = []
    ex_status = health.get("exchange_status_http")
    if isinstance(ex_status, int):
        log.append({
            "url": "GET /exchange/status",
            "status": ex_status,
            "ok": 200 <= ex_status < 300,
            "note": "instrument-panel collector",
        })
    meta = instr.get("meta") or {}
    log.append({
        "url": "GET /series, /events, /markets (bounded per-series)",
        "status": 200,
        "ok": not (meta.get("request_errors") or []),
        "note": f"instrument-panel collector: {meta.get('https_requests', 0)} HTTPS requests, "
                f"{len(meta.get('request_errors') or [])} error(s); adapted to root snapshot",
    })
    return log


def write_json(name: str, payload: Any) -> None:
    DATA.mkdir(exist_ok=True)
    p = DATA / name
    p.write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n")
    print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size} bytes)")


def main() -> int:
    instr_path = DATA / "dashboard_instrument.json"
    if not instr_path.exists():
        print(f"ERROR: {instr_path.relative_to(ROOT)} not found — run the "
              f"instrument-panel collector first.", file=sys.stderr)
        return 1
    instr = json.loads(instr_path.read_text())

    meta = instr.get("meta") or {}
    generated = meta.get("generated_at") or ""

    # ---- markets ----
    markets: list[dict] = []
    by_topic: dict[str, list[dict]] = {t: [] for t in TOPICS}
    for t in TOPICS:
        for m in instr.get("markets", {}).get(t, []):
            row = market_row(m, t)
            markets.append(row)
            by_topic[t].append(row)
    for t in TOPICS:
        by_topic[t].sort(key=lambda r: (r.get("est_dollar_volume") or -1), reverse=True)

    # ---- resolutions ----
    resolved_raw = instr.get("resolved") or []
    resolutions = [resolution_row(r, r.get("topic") or "") for r in resolved_raw]
    resolutions = [r for r in resolutions if r["result"] in ("yes", "no")]
    resolutions.sort(key=lambda r: (r.get("close_time") or ""), reverse=True)

    # ---- orderbooks (canonical schema) ----
    books: dict[str, dict] = {}
    for ticker, ob in (instr.get("orderbooks") or {}).items():
        books[ticker] = build_orderbook(ob)

    # ---- candles: the instrument artifact has no candlestick endpoint data.
    # Leave empty (honest) rather than fabricating OHLC; the chart falls back to
    # data/history.json, which is built from the traded price path below.
    candles: dict[str, dict] = {}

    # ---- series inventory / catalog ----
    series = instr.get("series") or []
    inventory = build_series_inventory(series)
    catalog = build_topic_catalog(series, instr.get("markets") or {})

    counts = {
        "series_index": inventory["series_count"],
        "events_scanned": len(instr.get("events") or {}),
        "markets_in_scope": len(markets),
        "per_topic": {t: len(by_topic[t]) for t in TOPICS},
        "resolved_in_scope": len(resolutions),
        "orderbooks": len(books),
        "candle_sets": 0,
    }

    health = instr.get("health") or {}
    exchange_status = {
        "http_status": health.get("exchange_status_http"),
        "response": health.get("exchange_status"),
    }

    snapshot = {
        "generated_at_utc": generated,
        "environment": "demo",
        "rest_base": meta.get("api_base"),
        "authenticated": False,
        "exchange_status": exchange_status,
        "series_inventory": inventory,
        "topic_catalog": catalog,
        "unmapped_series": {},
        "counts": counts,
        "markets": markets,
        "by_topic": by_topic,
        "orderbooks": books,
        "candles": candles,
        "resolutions": resolutions,
        "definitions": {
            "est_dollar_volume": (
                "ESTIMATE = volume_fp x last_price_dollars, computed by this adapter. "
                "The API exposes no single dollar-volume field. Label is shown in the UI."
            ),
            "derived_yes_asks": (
                "Derived, not raw: a NO bid at price p is equivalent to a YES ask at 1-p "
                "(Kalshi orderbook docs). Shown so ask-side depth and spread are visible."
            ),
            "result": "Official market field. 'yes' or 'no' once settled; empty while live.",
            "candles": (
                "Empty in this snapshot: the instrument-panel collector does not fetch the "
                "candlestick endpoint. The chart falls back to data/history.json, built from "
                "the traded price path."
            ),
        },
        "api_log": build_api_log(instr),
    }
    write_json("snapshot.json", snapshot)

    # per-topic files
    for t in TOPICS:
        write_json(
            f"topic-{t}.json",
            {
                "generated_at_utc": generated,
                "topic": t,
                "count": len(by_topic[t]),
                "markets": by_topic[t],
                "resolutions": [r for r in resolutions if r["topic"] == t],
            },
        )

    write_json(
        "resolutions.json",
        {"generated_at_utc": generated, "count": len(resolutions), "resolutions": resolutions},
    )

    # history.json: traded price path from the instrument-panel trade history.
    # Each trade is a real print; we record one point per trade (t = epoch, last =
    # traded YES price) so the chart has a genuine price series.
    hist: dict[str, list[dict]] = {"points": {}}
    for ticker, tr in (instr.get("trades") or {}).items():
        pts = []
        for trd in tr.get("trades") or []:
            t = trd.get("created_time")
            p = fnum(trd.get("yes_price_dollars"))
            if not t or p is None:
                continue
            import datetime as _dt
            try:
                epoch = int(_dt.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp())
            except ValueError:
                continue
            pts.append({"t": epoch, "last": trd.get("yes_price_dollars"), "yes_bid": None,
                        "yes_ask": None})
        if pts:
            hist["points"][ticker] = pts[-2000:]
    hist["updated_at_utc"] = generated
    write_json("history.json", hist)

    print(f"OK  markets_in_scope={len(markets)}  resolved={len(resolutions)}  "
          f"orderbooks={len(books)}  series={inventory['series_count']}")
    if not markets:
        print("ERROR: zero in-scope markets — instrument artifact has no in-scope markets.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
