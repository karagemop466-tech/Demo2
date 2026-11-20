#!/usr/bin/env python3
"""Build the live alert feed for the Kalshi demo dashboard -> data/alerts.json.

Two products come out of this file:

  1. `alerts` — every observed contract-price move of at least $0.10 in either
     direction, across the five in-scope topics (gas, elections, culture, crypto,
     golf). This is the "all events" chat.

  2. `picks` — the subset the Jump Edge Score model likes. This is the
     "high ROI" chat.

Every number is copied from an official Kalshi demo API response or computed from
those values by a formula printed in the output itself. Nothing is inferred about
*why* a price moved: the Kalshi API returns price and size, never a cause, so each
alert links to the market's own declared settlement sources and is flagged
"cause unverified" (see pages/flagged.html).

Inputs (all produced by the collectors on GitHub Actions):
  data/dashboard_instrument.json  raw trade prints, order books, markets, resolved
  data/jumps.json                 already-computed move list (cross-check only)
  data/snapshot.json              the main in-scope snapshot (market metadata)

Outputs:
  data/alerts.json                the feed + the model definition
  data/alert_summary.json         small file used by the pages for KPI tiles

Run:  python3 tools/alerts.py
"""

from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

API_BASE = "https://external-api.demo.kalshi.co/trade-api/v2"
DOCS = "https://docs.kalshi.com"

THRESHOLD = 0.10          # dollars per $1 contract, either direction
MIN_SAMPLES = 2           # a move needs two prints
MAX_ALERTS = 400

# ---------------------------------------------------------------- model weights
WEIGHTS = {
    "momentum": 0.30,     # size of the move itself
    "conviction": 0.20,   # open interest (contracts outstanding)
    "liquidity": 0.20,    # size resting on the book at the alert price
    "efficiency": 0.15,   # tightness of the quoted spread
    "proximity": 0.15,    # how close the market is to its close time
}
SCORE_CUTOFF = 0.60      # a pick needs at least this percentile score
ROI_CUTOFF = 0.10        # ... and at least this conditional reversion ROI
MIN_ENTRY_DEPTH = 10.0   # ... and at least this many contracts available to take
DEPTH_BAND = 0.02        # price band (dollars) used to match book levels
MIN_TRADEABLE_PRICE = 0.05   # a price below/above this is a micro-print, not a level
MAX_TRADEABLE_PRICE = 0.95

# Kalshi publishes a trading fee whose per-100-contract range is $0.07-$1.75
# (https://kalshi.com/fee-schedule). The parabola 0.07 * P * (1 - P) reproduces
# both published endpoints exactly (0.07 * 100 * 0.01 * 0.99 = 0.0693 -> $0.07
# and 0.07 * 100 * 0.50 * 0.50 = 1.75 -> $1.75), so it is used as the fee model.
# It is an ASSUMPTION reconstructed from the published range, not a quoted field.
FEE_COEFF = 0.07

MODEL = {
    "name": "Jump Edge Score",
    "version": "1.0",
    "kind": "deterministic rule-based ranking (no trained weights, no forecast)",
    "threshold_dollars": THRESHOLD,
    "score_formula": (
        "score = 0.30*momentum + 0.20*conviction + 0.20*liquidity "
        "+ 0.15*efficiency + 0.15*proximity   (each component 0..1)"
    ),
    "components": {
        "momentum": "min(|change| / 0.40, 1)",
        "conviction": "min(open_interest_fp / 1000, 1)",
        "liquidity": "min(contracts resting at the best YES bid / 100, 1)",
        "efficiency": "1 - min(spread / 0.20, 1), spread = yes_ask_dollars - yes_bid_dollars",
        "proximity": "1 - min(days_to_close / 180, 1)",
    },
    "normalisation": (
        "Each raw component is converted to its percentile inside the current alert "
        "set before weighting, so the score ranks the alerts against each other "
        "instead of against a fixed constant. A component the API did not return is "
        "excluded and the remaining weights are renormalised; a missing component "
        "can therefore never make an alert score higher."
    ),
    "weights": WEIGHTS,
    "roi_definition": (
        "Conditional reversion ROI. After a move to price p1 the contrarian side is "
        "bought at p1 (YES after a down move) or 1 - p1 (NO after an up move). If the "
        "price reverted to the pre-move price p0 the gross return would be "
        "|p1 - p0| / price_paid. roi_net subtracts the fee drag 0.07 * (1 - price_paid). "
        "This is a size of the opportunity if reversion happens, NOT a probability "
        "and NOT a return forecast."
    ),
    "depth_definition": (
        "depth_at_entry is the number of contracts the official order book offers "
        "within +/- $0.02 of the price you would have to pay. To buy YES at price p "
        "you lift the YES ask side, which is derived from NO bids at 1 - p; to buy NO "
        "at price q you hit the YES bid side at 1 - q. The book returns bids only, so "
        "the ask side is derived (1 - bid) and labelled as derived everywhere."
    ),
    "fee_model": {
        "formula": "fee_per_contract = 0.07 * P * (1 - P)  (taker, 1 contract)",
        "source": "https://kalshi.com/fee-schedule",
        "note": (
            "Reconstructed from the officially published per-100-contract fee range "
            "$0.07-$1.75; both endpoints match exactly. The published page is the "
            "authority; the parabola is this project's assumption."
        ),
    },
    "pick_rule": (
        f"score >= {SCORE_CUTOFF} and roi_net >= {ROI_CUTOFF} and "
        f"depth_at_entry >= {MIN_ENTRY_DEPTH:.0f} contracts and |change| >= "
        f"{THRESHOLD:.2f} and both prices of the move inside "
        f"{MIN_TRADEABLE_PRICE:.2f}-{MAX_TRADEABLE_PRICE:.2f}"
    ),
    "caveats": [
        "The score ranks where attention is worth spending. It does not predict "
        "direction and it does not forecast a return.",
        "The Kalshi demo environment uses mock funds and its prices and behaviour "
        "may not reflect real markets "
        "(https://docs.kalshi.com/getting_started/demo_env), so no score or ROI "
        "here transfers to the live exchange.",
        "The cause of a price move is not in the API. Each alert links the market's "
        "own declared settlement sources and is flagged 'cause unverified'.",
        "Liquidity and spread are read from the order book at collection time; they "
        "are stale by the time the page renders and are labelled with their source.",
    ],
    "sources": {
        "trades": f"{DOCS}/api-reference/market/get-trades",
        "orderbook": f"{DOCS}/api-reference/market/get-market-orderbook",
        "markets": f"{DOCS}/api-reference/market/get-markets",
        "candlesticks": f"{DOCS}/api-reference/market/get-market-candlesticks",
        "demo_env": f"{DOCS}/getting_started/demo_env",
        "fee_schedule": "https://kalshi.com/fee-schedule",
    },
}


def read_json(name: str) -> Any:
    p = DATA / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def fnum(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(n):
        return None
    return n


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def kalshi_market_page(series_ticker: str) -> str:
    """Public market page pattern used by Kalshi itself (lower-cased series ticker)."""
    if not series_ticker:
        return ""
    return "https://kalshi.com/markets/" + series_ticker.lower()


def parse_ts(v: Any) -> float | None:
    if not v or not isinstance(v, str):
        return None
    try:
        return dt.datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def build_market_index() -> dict[str, dict]:
    """ticker -> market metadata, from every snapshot that carries it."""
    idx: dict[str, dict] = {}

    snap = read_json("snapshot.json") or {}
    for m in snap.get("markets") or []:
        t = m.get("market_ticker") or m.get("ticker")
        if not t:
            continue
        idx[t] = {
            "ticker": t,
            "topic": m.get("topic"),
            "title": m.get("market_title") or m.get("title"),
            "sub_title": m.get("yes_sub_title"),
            "event_ticker": m.get("event_ticker"),
            "series_ticker": m.get("series_ticker"),
            "close_time": m.get("close_time"),
            "volume_fp": m.get("volume_fp"),
            "open_interest_fp": m.get("open_interest_fp"),
            "yes_bid_dollars": m.get("yes_bid_dollars"),
            "yes_ask_dollars": m.get("yes_ask_dollars"),
            "last_price_dollars": m.get("last_price_dollars"),
            "settlement_sources": m.get("settlement_sources") or [],
            "market_url": f"{API_BASE}/markets/{t}",
        }

    inst = read_json("dashboard_instrument.json") or {}
    for topic, rows in (inst.get("markets") or {}).items():
        rows = rows if isinstance(rows, list) else []
        for m in rows:
            t = m.get("ticker")
            if not t:
                continue
            cur = idx.get(t, {})
            cur.update({
                "ticker": t,
                "topic": m.get("topic") or topic,
                "title": m.get("title"),
                "sub_title": m.get("yes_sub_title"),
                "event_ticker": m.get("event_ticker"),
                "series_ticker": m.get("series_ticker"),
                "close_time": m.get("close_time"),
                "volume_fp": m.get("volume_fp"),
                "open_interest_fp": m.get("open_interest_fp"),
                "yes_bid_dollars": m.get("yes_bid_dollars"),
                "yes_ask_dollars": m.get("yes_ask_dollars"),
                "last_price_dollars": m.get("last_price_dollars"),
                "market_url": m.get("source_market_url") or f"{API_BASE}/markets/{t}",
            })
            if m.get("settlement_sources"):
                cur["settlement_sources"] = m["settlement_sources"]
            idx[t] = cur
    return idx


def build_orderbook_index() -> dict[str, dict]:
    """ticker -> order-book summary (levels, best bid, size, derived ask, spread)."""
    out: dict[str, dict] = {}

    def absorb(ticker: str, yes: list, no: list, source: str, force: bool = False) -> None:
        if not ticker:
            return
        if ticker in out and not force:
            return
        yes_rows = [(fnum(p), fnum(c)) for p, c in (yes or [])]
        yes_rows = [(p, c) for p, c in yes_rows if p is not None and c is not None]
        no_rows = [(fnum(p), fnum(c)) for p, c in (no or [])]
        no_rows = [(p, c) for p, c in no_rows if p is not None and c is not None]
        best_bid = max((p for p, _ in yes_rows), default=None)
        size_at_best = 0.0
        if best_bid is not None:
            size_at_best = sum(c for p, c in yes_rows if abs(p - best_bid) < 1e-9)
        # Kalshi returns YES bids and NO bids only. A NO bid at p is a YES ask at 1-p.
        best_no_bid = max((p for p, _ in no_rows), default=None)
        implied_yes_ask = (1.0 - best_no_bid) if best_no_bid is not None else None
        out[ticker] = {
            "ticker": ticker,
            "source_url": source,
            "yes_levels": [[p, c] for p, c in sorted(yes_rows)],
            "no_levels": [[p, c] for p, c in sorted(no_rows)],
            "best_yes_bid": best_bid,
            "contracts_at_best_yes_bid": size_at_best or None,
            "total_yes_bid_contracts": sum(c for _, c in yes_rows) or None,
            "best_no_bid": best_no_bid,
            "implied_yes_ask": implied_yes_ask,
            "derived": True,
            "note": "asks are derived as 1 - no_bid; the API returns bids only",
        }

    inst = read_json("dashboard_instrument.json") or {}
    for ticker, ob in (inst.get("orderbooks") or {}).items():
        if not isinstance(ob, dict):
            continue
        absorb(ticker, ob.get("yes_dollars") or [], ob.get("no_dollars") or [],
               ob.get("source_url") or f"{API_BASE}/markets/{ticker}/orderbook?depth=20")

    snap = read_json("snapshot.json") or {}
    for ticker, ob in (snap.get("orderbooks") or {}).items():
        if not isinstance(ob, dict):
            continue
        # tools/collector.py stores the book as yes_bids / no_bids (floats);
        # the instrument collector stores yes_dollars / no_dollars (strings).
        yes = ob.get("yes_bids") or ob.get("yes_dollars") or []
        no = ob.get("no_bids") or ob.get("no_dollars") or []
        absorb(ticker, yes, no,
               ob.get("raw_request") or f"{API_BASE}/markets/{ticker}/orderbook?depth=25")

    # The book that was collected together with the trade prints is the most
    # recent one for those markets, so it replaces the older entry.
    tj = read_json("trades.json") or {}
    for ticker, blob in (tj.get("markets") or {}).items():
        if not isinstance(blob, dict):
            continue
        ob = blob.get("orderbook")
        if not isinstance(ob, dict):
            continue
        absorb(ticker, ob.get("yes_bids") or [], ob.get("no_bids") or [],
               ob.get("raw_request") or f"{API_BASE}/markets/{ticker}/orderbook?depth=25",
               force=True)
    return out


def depth_at(levels: list, price: float, band: float = DEPTH_BAND) -> float:
    """Contracts offered within +/- `band` of `price` in an official book level list."""
    if not levels or price is None:
        return 0.0
    total = 0.0
    for lvl in levels:
        p = lvl[0] if isinstance(lvl, (list, tuple)) else lvl
        c = lvl[1] if isinstance(lvl, (list, tuple)) else None
        if p is None or c is None:
            continue
        if abs(float(p) - price) <= band + 1e-9:
            total += float(c)
    return total


def entry_depth(book: dict | None, side: str, price: float) -> float:
    """How many contracts you could actually take at `price` for `side`.

    Buying YES at p lifts the YES ask side, which the book exposes as NO bids at
    1 - p. Buying NO at q hits the YES bid side at 1 - q.
    """
    if not book:
        return 0.0
    if side == "yes":
        return depth_at(book.get("no_levels") or [], 1.0 - price)
    return depth_at(book.get("yes_levels") or [], 1.0 - price)


def moves_from_trades(trades: list[dict]) -> list[dict]:
    """Consecutive prints of the SAME market; a move is |p1 - p0| >= threshold."""
    rows = []
    ordered = sorted(
        trades,
        key=lambda t: (t.get("created_time") or "", t.get("trade_id") or ""),
    )
    for i in range(1, len(ordered)):
        a, b = ordered[i - 1], ordered[i]
        p0 = fnum(a.get("yes_price_dollars"))
        p1 = fnum(b.get("yes_price_dollars"))
        if p0 is None or p1 is None:
            continue
        change = p1 - p0
        if abs(change) < THRESHOLD:
            continue
        rows.append({
            "from_price": p0,
            "to_price": p1,
            "change": change,
            "direction": "up" if change > 0 else "down",
            "from_time": a.get("created_time"),
            "to_time": b.get("created_time"),
            "from_size_fp": a.get("count_fp"),
            "to_size_fp": b.get("count_fp"),
            "kind": "trade_print",
        })
    return rows


def moves_from_history(points: list[dict]) -> list[dict]:
    """Collector ticks (last_price_dollars) for one market."""
    rows = []
    ordered = sorted(points, key=lambda p: p.get("t") or 0)
    for i in range(1, len(ordered)):
        a, b = ordered[i - 1], ordered[i]
        p0 = fnum(a.get("last"))
        p1 = fnum(b.get("last"))
        if p0 is None or p1 is None:
            continue
        change = p1 - p0
        if abs(change) < THRESHOLD:
            continue
        rows.append({
            "from_price": p0,
            "to_price": p1,
            "change": change,
            "direction": "up" if change > 0 else "down",
            "from_time": dt.datetime.fromtimestamp(a.get("t"), dt.timezone.utc)
                        .isoformat(timespec="seconds").replace("+00:00", "Z"),
            "to_time": dt.datetime.fromtimestamp(b.get("t"), dt.timezone.utc)
                       .isoformat(timespec="seconds").replace("+00:00", "Z"),
            "from_size_fp": None,
            "to_size_fp": None,
            "kind": "collector_tick",
        })
    return rows


def raw_components(alert: dict, book: dict | None, now: float) -> dict:
    """Raw (un-normalised) model inputs and the conditional reversion ROI."""
    change = alert["change"]
    move = abs(change)
    to_price = alert["to_price"]

    # contrarian (fade) side and its price
    if alert["direction"] == "up":
        fade_side = "no"
        fade_price = 1.0 - to_price
    else:
        fade_side = "yes"
        fade_price = to_price
    fade_price = min(max(fade_price, 0.01), 0.99)

    roi_gross = move / fade_price if fade_price > 0 else None
    fee_per_contract = FEE_COEFF * fade_price * (1.0 - fade_price)
    fee_drag = fee_per_contract / fade_price if fade_price > 0 else None
    roi_net = (roi_gross - fee_drag) if (roi_gross is not None and fee_drag is not None) else None
    tradeable = (MIN_TRADEABLE_PRICE <= to_price <= MAX_TRADEABLE_PRICE
                 and MIN_TRADEABLE_PRICE <= alert["from_price"] <= MAX_TRADEABLE_PRICE)

    oi = fnum(alert.get("open_interest_fp"))
    spread = None
    bid = fnum(alert.get("yes_bid_dollars"))
    ask = fnum(alert.get("yes_ask_dollars"))
    if bid is not None and ask is not None and ask >= bid:
        spread = ask - bid
    depth = None
    if book:
        depth = fnum(book.get("contracts_at_best_yes_bid"))
        if depth is None:
            depth = fnum(book.get("total_yes_bid_contracts"))
    entry = entry_depth(book, fade_side, fade_price)

    close_ts = parse_ts(alert.get("close_time"))
    days_to_close = None
    if close_ts:
        days_to_close = (close_ts - now) / 86400.0

    components = {
        "momentum": clamp01(move / 0.40),
        "conviction": clamp01(oi / 1000.0) if oi is not None else None,
        "liquidity": clamp01(depth / 100.0) if depth is not None else None,
        "efficiency": (1.0 - clamp01(spread / 0.20)) if spread is not None else None,
        "proximity": clamp01(1.0 - days_to_close / 180.0) if days_to_close is not None else None,
    }

    return {
        "score_components": components,
        "fade_side": fade_side,
        "fade_price": round(fade_price, 4),
        "roi_gross": roi_gross,
        "roi_net": roi_net,
        "fee_per_contract": round(fee_per_contract, 6),
        "spread": spread,
        "book_depth": depth,
        "depth_at_entry": entry or None,
        "tradeable_prices": tradeable,
        "days_to_close": days_to_close,
        "open_interest_fp": oi,
    }


def percentile_ranks(alerts: list[dict]) -> None:
    """Convert raw components into percentiles inside this alert set, in place.

    Percentile rank = share of alerts whose raw value is lower or equal. The score
    is then the weighted mean of the percentile ranks. A component the API did not
    return is excluded and the remaining weights are renormalised, so a missing
    component can never make an alert rank higher than a complete one.
    """
    names = list(WEIGHTS)
    values: dict[str, list[float]] = {n: [] for n in names}
    for a in alerts:
        comps = a["score_detail"]["score_components"]
        for n in names:
            v = comps.get(n)
            if v is not None:
                values[n].append(float(v))
    for a in alerts:
        comps = a["score_detail"]["score_components"]
        weighted = 0.0
        used = 0.0
        missing = []
        for n in names:
            v = comps.get(n)
            if v is None:
                missing.append(n)
                continue
            series = values[n]
            if not series:
                continue
            le = sum(1 for x in series if x <= float(v))
            rank = le / len(series)
            weighted += WEIGHTS[n] * rank
            used += WEIGHTS[n]
            comps[n + "_pct"] = round(rank, 4)
        a["score_detail"]["score"] = round(weighted / used, 4) if used > 0 else None
        a["score_detail"]["score_missing_components"] = missing
        a["score_detail"]["score_percentile_components"] = {
            n: comps.get(n + "_pct") for n in names
        }


def build_alerts() -> list[dict]:
    markets = build_market_index()
    books = build_orderbook_index()

    alerts: list[dict] = []
    seen: set[tuple] = set()

    def emit(ticker: str, mv: dict, source_url: str, kind: str) -> None:
        for m in moves:
            key = (ticker, m["from_time"], m["to_time"], kind)
            if key in seen:
                continue
            seen.add(key)
            meta = markets.get(ticker, {})
            row = {
                "ticker": ticker,
                "topic": meta.get("topic") or mv.get("topic"),
                "title": meta.get("title") or mv.get("title"),
                "sub_title": meta.get("sub_title"),
                "event_ticker": meta.get("event_ticker"),
                "series_ticker": meta.get("series_ticker"),
                "close_time": meta.get("close_time"),
                "volume_fp": meta.get("volume_fp"),
                "open_interest_fp": meta.get("open_interest_fp"),
                "yes_bid_dollars": meta.get("yes_bid_dollars"),
                "yes_ask_dollars": meta.get("yes_ask_dollars"),
                "market_url": meta.get("market_url") or f"{API_BASE}/markets/{ticker}",
                "market_page": kalshi_market_page(meta.get("series_ticker") or ""),
                "settlement_sources": (meta.get("settlement_sources") or [])[:3],
                "source_url": source_url,
                "kind": kind,
            }
            row.update(m)
            alerts.append(row)

    # 1) raw trade prints — data/trades.json (tools/collector.py) is preferred,
    #    the instrument-panel collector is the fallback.
    trade_sources: list[tuple[str, dict, str]] = []
    tj = read_json("trades.json") or {}
    for ticker, blob in (tj.get("markets") or {}).items():
        if isinstance(blob, dict):
            trade_sources.append((ticker, blob, blob.get("raw_request") or
                                  f"{API_BASE}/markets/trades?ticker={ticker}&limit=1000"))
    if not trade_sources:
        inst = read_json("dashboard_instrument.json") or {}
        for ticker, blob in (inst.get("trades") or {}).items():
            if isinstance(blob, dict):
                trade_sources.append((ticker, blob, blob.get("source_url") or
                                      f"{API_BASE}/markets/trades?ticker={ticker}&limit=1000"))

    for ticker, blob, source_url in trade_sources:
        trades = blob.get("trades") or []
        moves = moves_from_trades(trades)
        emit(ticker, {"topic": blob.get("topic")}, source_url, "trade_print")

    # 2) collector tick history for the main snapshot's markets
    hist = read_json("history.json") or {}
    for ticker, points in (hist.get("points") or {}).items():
        if not isinstance(points, list) or len(points) < 2:
            continue
        moves = moves_from_history(points)
        if not moves:
            continue
        emit(ticker, {"topic": None},
             f"{API_BASE}/markets/{ticker}", "collector_tick")

    # 3) snapshot-to-snapshot moves already computed by tools/build_jumps.py
    jumps = read_json("jumps.json") or {}
    for mv in jumps.get("snapshot_moves") or []:
        ticker = mv.get("ticker")
        if not ticker:
            continue
        p0 = fnum(mv.get("from_price"))
        p1 = fnum(mv.get("to_price"))
        if p0 is None or p1 is None:
            continue
        change = p1 - p0
        if abs(change) < THRESHOLD:
            continue
        meta = markets.get(ticker, {})
        row = {
            "ticker": ticker,
            "topic": meta.get("topic") or mv.get("topic"),
            "title": meta.get("title") or mv.get("title"),
            "sub_title": meta.get("sub_title"),
            "event_ticker": meta.get("event_ticker"),
            "series_ticker": meta.get("series_ticker"),
            "close_time": meta.get("close_time"),
            "volume_fp": meta.get("volume_fp"),
            "open_interest_fp": meta.get("open_interest_fp"),
            "yes_bid_dollars": meta.get("yes_bid_dollars"),
            "yes_ask_dollars": meta.get("yes_ask_dollars"),
            "market_url": meta.get("market_url") or f"{API_BASE}/markets/{ticker}",
            "market_page": kalshi_market_page(meta.get("series_ticker") or ""),
            "settlement_sources": (meta.get("settlement_sources") or [])[:3],
            "source_url": f"{API_BASE}/markets/{ticker}",
            "kind": "snapshot_pair",
            "from_price": p0,
            "to_price": p1,
            "change": change,
            "direction": "up" if change > 0 else "down",
            "from_time": mv.get("from_time"),
            "to_time": mv.get("to_time"),
            "from_size_fp": None,
            "to_size_fp": None,
        }
        alerts.append(row)

    return alerts


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    now_ts = now.timestamp()

    alerts = build_alerts()
    books = build_orderbook_index()

    for a in alerts:
        a["score_detail"] = raw_components(a, books.get(a["ticker"]), now_ts)
        ts = parse_ts(a.get("to_time"))
        a["to_ts"] = ts
        a["at"] = (dt.datetime.fromtimestamp(ts, dt.timezone.utc)
                   .isoformat(timespec="seconds").replace("+00:00", "Z")) if ts else None

    percentile_ranks(alerts)

    # One bubble per distinct price transition per market. The demo exchange can
    # print the same transition many times in a minute; the chat shows the most
    # recent occurrence and how many times the transition was printed.
    collapsed: dict[tuple, dict] = {}
    out: list[dict] = []
    for a in sorted(alerts, key=lambda x: (x.get("to_ts") or 0), reverse=True):
        key = (a["ticker"], round(a["from_price"], 4), round(a["to_price"], 4), a.get("kind"))
        prev = collapsed.get(key)
        if prev is not None:
            prev["repeats"] = prev.get("repeats", 1) + 1
            continue
        a["repeats"] = 1
        collapsed[key] = a
        out.append(a)
    alerts = out
    percentile_ranks(alerts)

    alerts.sort(key=lambda a: (a.get("to_ts") or 0), reverse=True)
    alerts = alerts[:MAX_ALERTS]

    picks = []
    for a in alerts:
        s = a["score_detail"]
        score = s.get("score")
        roi = s.get("roi_net")
        depth = s.get("depth_at_entry")
        if score is None or roi is None:
            continue
        if (score >= SCORE_CUTOFF and roi >= ROI_CUTOFF
                and (depth or 0) >= MIN_ENTRY_DEPTH and s.get("tradeable_prices")):
            pick = dict(a)
            pick["pick_reason"] = (
                f"score {score:.2f} >= {SCORE_CUTOFF}, conditional reversion ROI "
                f"{roi * 100:.1f}% >= {ROI_CUTOFF * 100:.0f}%, "
                f"{depth:.0f} contracts available at the entry price"
            )
            picks.append(pick)

    by_topic: dict[str, int] = {}
    for a in alerts:
        t = a.get("topic") or "unmapped"
        by_topic[t] = by_topic.get(t, 0) + 1

    payload = {
        "generated_at_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "environment": "demo",
        "api_base": API_BASE,
        "threshold_dollars": THRESHOLD,
        "model": MODEL,
        "stats": {
            "alerts": len(alerts),
            "picks": len(picks),
            "by_topic": by_topic,
            "by_kind": {k: sum(1 for a in alerts if a.get("kind") == k)
                        for k in sorted({a.get("kind") for a in alerts if a.get("kind")})},
            "source": ("raw trade prints (GET /markets/trades), collector ticks "
                       "(GET /markets) and snapshot pairs"),
        },
        "alerts": alerts,
        "picks": picks,
    }

    out = DATA / "alerts.json"
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {out.relative_to(ROOT)}  alerts={len(alerts)} picks={len(picks)}")

    summary = {
        "generated_at_utc": payload["generated_at_utc"],
        "alerts": len(alerts),
        "picks": len(picks),
        "by_topic": by_topic,
        "threshold_dollars": THRESHOLD,
        "model_name": MODEL["name"],
        "model_version": MODEL["version"],
    }
    s_out = DATA / "alert_summary.json"
    s_out.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"wrote {s_out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
