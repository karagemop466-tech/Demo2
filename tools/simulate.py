#!/usr/bin/env python3
"""Simulated (paper) trades over resolved Kalshi demo markets -> data/simulations.json.

This is the "automate simulated trades to test different strategies" part of the
brief. It never sends an order. It replays a set of rule-based strategies over
the official resolved outcomes that the collectors captured, prices each trade
with the official fields, and reports the result.

Rules of the exercise:
  * A trade is only ever booked when the official `result` of the market is
    known ("yes" or "no"). Nothing is estimated and no open position is ever
    booked as a win or a loss.
  * The entry price is the official `last_price_dollars` of the market at
    collection time. The simulated fill is at that price with a fixed size.
  * Fees use the fee model published on https://kalshi.com/fee-schedule
    (per-100-contract range $0.07-$1.75). The parabola 0.07 * P * (1 - P)
    reproduces both published endpoints exactly, so it is used as the fee model
    and is labelled as an assumption, not a quoted field.
  * Every strategy is reported with its own trade list so a reader can check
    the arithmetic; nothing is asserted that is not computed here.

The Kalshi demo environment uses mock funds and its prices may not reflect real
markets (https://docs.kalshi.com/getting_started/demo_env), so these results
describe the demo data only. They do not predict live-market performance.

Run:  python3 tools/simulate.py
"""

from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CONTRACTS_PER_TRADE = 10.0
FEE_COEFF = 0.07
MIN_CATEGORY_TRADES = 10   # a category needs this many trades before it is listed

PRICE_BANDS = [
    (0.00, 0.10, "0.00-0.10"),
    (0.10, 0.25, "0.10-0.25"),
    (0.25, 0.40, "0.25-0.40"),
    (0.40, 0.60, "0.40-0.60"),
    (0.60, 0.75, "0.60-0.75"),
    (0.75, 0.90, "0.75-0.90"),
    (0.90, 1.01, "0.90-1.00"),
]


def fnum(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def read_json(name: str) -> Any:
    p = DATA / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def band_of(price: float) -> str:
    for lo, hi, label in PRICE_BANDS:
        if lo <= price < hi:
            return label
    return "outside 0.00-1.00"


# The two collectors label the gasoline topic differently; normalise to one name.
TOPIC_ALIASES = {"gas-prices": "gas", "gas_prices": "gas", "gasoline": "gas"}


def is_synthetic_demo(row: dict) -> bool:
    """Demo-only contracts whose own title starts with "Demo"."""
    return (row.get("title") or "").strip().lower().startswith("demo ")


def taker_fee(count: float, price: float) -> float:
    """Kalshi taker fee, rounded up to the next cent.

    fee = 0.07 * contracts * price * (1 - price), rounded up.
    Source: https://kalshi.com/fee-schedule (published per-100-contract range
    $0.07-$1.75; both endpoints of that range match this formula exactly).
    """
    raw = FEE_COEFF * count * price * (1.0 - price)
    return math.ceil(raw * 100.0 - 1e-9) / 100.0


# --------------------------------------------------------------------- universe
def load_universe() -> tuple[list[dict], list[str]]:
    """Resolved in-scope markets, merged from every collector that has them."""
    rows: dict[str, dict] = {}
    sources: list[str] = []

    def absorb(r: dict, source: str) -> None:
        ticker = r.get("market_ticker") or r.get("ticker")
        result = (r.get("result") or "").lower()
        if not ticker or result not in ("yes", "no"):
            return
        price = fnum(r.get("last_price_dollars"))
        if price is None or price <= 0 or price >= 1:
            return
        prev = fnum(r.get("previous_price_dollars"))
        row = {
            "market_ticker": ticker,
            "event_ticker": r.get("event_ticker"),
            "series_ticker": r.get("series_ticker"),
            "title": r.get("title"),
            "yes_sub_title": r.get("yes_sub_title"),
            "topic": (r.get("topic") or "").lower(),
            "result": result,
            "last_price_dollars": price,
            "previous_price_dollars": prev,
            "settlement_value_dollars": r.get("settlement_value_dollars"),
            "settlement_ts": r.get("settlement_ts"),
            "close_time": r.get("close_time"),
            "volume_fp": r.get("volume_fp"),
            "open_interest_fp": r.get("open_interest_fp"),
            "source": source,
        }
        rows.setdefault(ticker, row)

    res = read_json("resolutions.json") or {}
    if res.get("resolutions"):
        sources.append("data/resolutions.json (tools/collector.py, GET /markets?status=settled)")
        for r in res["resolutions"]:
            absorb(r, "data/resolutions.json")

    inst = read_json("dashboard_instrument.json") or {}
    if inst.get("resolved"):
        sources.append("data/dashboard_instrument.json (instrument collector, GET /markets?status=settled)")
        for r in inst["resolved"]:
            absorb(r, "data/dashboard_instrument.json")

    ms = read_json("markets_settled.json") or {}
    if ms.get("rows"):
        sources.append("data/markets_settled.json (GET /markets?status=settled)")
        for r in ms["rows"]:
            absorb(r, "data/markets_settled.json")

    out = list(rows.values())
    for r in out:
        if not r["topic"]:
            r["topic"] = "unmapped"
        else:
            r["topic"] = TOPIC_ALIASES.get(r["topic"], r["topic"])
    out.sort(key=lambda r: (r.get("settlement_ts") or ""))
    return out, sources


# ------------------------------------------------------------------- strategies
def side_price(side: str, yes_price: float) -> float:
    return yes_price if side == "yes" else 1.0 - yes_price


def strategy_defs() -> list[dict]:
    """Each strategy returns (side or None, reason) for a market."""
    return [
        {
            "id": "always_yes",
            "name": "Always YES",
            "rule": "Buy YES at the market's last traded price on every resolved market.",
            "why": "The control case: what the average market paid out, with no filter.",
            "fn": lambda m: ("yes", "always"),
        },
        {
            "id": "always_no",
            "name": "Always NO",
            "rule": "Buy NO at 1 - last price on every resolved market.",
            "why": "The mirror control. Together the two sides pay out every "
                   "market, so the gap between them is the difference in the price "
                   "paid plus the fee.",
            "fn": lambda m: ("no", "always"),
        },
        {
            "id": "cheap_yes",
            "name": "Cheap YES (<= 0.25)",
            "rule": "Buy YES only when the market trades at or below $0.25.",
            "why": "Long shots: small stake, large payout if the tail happens.",
            "fn": lambda m: ("yes", "price<=0.25") if m["last_price_dollars"] <= 0.25 else (None, ""),
        },
        {
            "id": "dear_no",
            "name": "Dear NO (>= 0.75)",
            "rule": "Buy NO only when the market trades at or above $0.75.",
            "why": "Long shots on the other side: buy the underdog at a high YES price.",
            "fn": lambda m: ("no", "price>=0.75") if m["last_price_dollars"] >= 0.75 else (None, ""),
        },
        {
            "id": "mid_yes",
            "name": "Mid-band YES (0.40-0.60)",
            "rule": "Buy YES only when the market trades between $0.40 and $0.60.",
            "why": "The most expensive place to trade (fees peak at $0.50).",
            "fn": lambda m: ("yes", "0.40<=price<=0.60")
            if 0.40 <= m["last_price_dollars"] <= 0.60 else (None, ""),
        },
        {
            "id": "edge_extremes",
            "name": "Extremes (YES <= 0.05, NO >= 0.95)",
            "rule": "Buy YES at or below $0.05, or NO at or above $0.95.",
            "why": "Nearly resolved markets: cheapest fees, but the payout is "
                   "mostly determined by the price you paid.",
            "fn": lambda m: ("yes", "price<=0.05") if m["last_price_dollars"] <= 0.05
            else (("no", "price>=0.95") if m["last_price_dollars"] >= 0.95 else (None, "")),
        },
        {
            "id": "fade_move",
            "name": "Fade a >= $0.10 move",
            "rule": "When the last price moved $0.10 or more against the previous "
                    "price, take the opposite side of that move.",
            "why": "Mean reversion after a sharp move.",
            "fn": lambda m: _move_side(m, follow=False),
        },
        {
            "id": "follow_move",
            "name": "Follow a >= $0.10 move",
            "rule": "When the last price moved $0.10 or more against the previous "
                    "price, take the same side as the move.",
            "why": "Momentum after a sharp move. The opposite hypothesis to Fade.",
            "fn": lambda m: _move_side(m, follow=True),
        },
        {
            "id": "skip_moves",
            "name": "Skip markets that moved >= $0.10",
            "rule": "Buy YES only when the last price moved less than $0.10 against "
                    "the previous price.",
            "why": "The control for Fade and Follow: the same universe minus the "
                   "markets that moved sharply.",
            "fn": lambda m: ("yes", "move<0.10") if _move_size(m) < 0.10 else (None, ""),
        },
    ]


def _move_size(m: dict) -> float:
    prev = m.get("previous_price_dollars")
    if prev is None:
        return 0.0
    return abs(m["last_price_dollars"] - prev)


def _move_side(m: dict, follow: bool) -> tuple[str | None, str]:
    if _move_size(m) < 0.10:
        return (None, "")
    up = m["last_price_dollars"] > m["previous_price_dollars"]
    side = "yes" if up else "no"
    if not follow:
        side = "no" if side == "yes" else "yes"
    return (side, "move>=0.10")


# ------------------------------------------------------------------- evaluation
def evaluate(strategy: dict, markets: list[dict]) -> dict:
    trades = []
    for m in markets:
        side, reason = strategy["fn"](m)
        if side is None:
            continue
        yes_price = m["last_price_dollars"]
        price_paid = side_price(side, yes_price)
        fee = taker_fee(CONTRACTS_PER_TRADE, price_paid)
        cost = CONTRACTS_PER_TRADE * price_paid
        won = (side == m["result"])
        payout = CONTRACTS_PER_TRADE if won else 0.0
        gross = payout - cost
        net = gross - fee
        trades.append({
            "market_ticker": m["market_ticker"],
            "title": m["title"],
            "yes_sub_title": m.get("yes_sub_title"),
            "topic": m["topic"],
            "side": side,
            "reason": reason,
            "yes_price": yes_price,
            "price_paid": round(price_paid, 4),
            "contracts": CONTRACTS_PER_TRADE,
            "cost": round(cost, 4),
            "fee": round(fee, 4),
            "payout": payout,
            "result": m["result"],
            "won": won,
            "gross_pnl": round(gross, 4),
            "net_pnl": round(net, 4),
            "settlement_ts": m.get("settlement_ts"),
            "price_band": band_of(yes_price),
            "source": m.get("source"),
        })

    wins = sum(1 for t in trades if t["won"])
    losses = len(trades) - wins
    capital = sum(t["cost"] for t in trades)
    fees = sum(t["fee"] for t in trades)
    gross = sum(t["gross_pnl"] for t in trades)
    net = sum(t["net_pnl"] for t in trades)

    # equity curve in settlement order -> maximum drawdown
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for t in sorted(trades, key=lambda x: (x.get("settlement_ts") or "", x["market_ticker"])):
        equity += t["net_pnl"]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)

    by_topic: dict[str, dict] = {}
    for t in trades:
        b = by_topic.setdefault(t["topic"], {"trades": 0, "wins": 0, "net_pnl": 0.0})
        b["trades"] += 1
        b["wins"] += 1 if t["won"] else 0
        b["net_pnl"] = round(b["net_pnl"] + t["net_pnl"], 4)

    by_band: dict[str, dict] = {}
    for t in trades:
        b = by_band.setdefault(t["price_band"], {"trades": 0, "wins": 0, "net_pnl": 0.0})
        b["trades"] += 1
        b["wins"] += 1 if t["won"] else 0
        b["net_pnl"] = round(b["net_pnl"] + t["net_pnl"], 4)

    gross_win = sum(t["net_pnl"] for t in trades if t["net_pnl"] > 0)
    gross_loss = abs(sum(t["net_pnl"] for t in trades if t["net_pnl"] < 0))

    return {
        "id": strategy["id"],
        "name": strategy["name"],
        "rule": strategy["rule"],
        "why": strategy["why"],
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "hit_rate": (wins / len(trades)) if trades else None,
        "capital_deployed": round(capital, 2),
        "fees": round(fees, 2),
        "gross_pnl": round(gross, 2),
        "net_pnl": round(net, 2),
        "roi": (net / capital) if capital else None,
        "avg_net_pnl": (net / len(trades)) if trades else None,
        "max_drawdown": round(drawdown, 2),
        "profit_factor": (gross_win / gross_loss) if gross_loss else None,
        "by_topic": by_topic,
        "by_price_band": by_band,
        "trade_list": trades[:200],
    }


def build_categories(markets: list[dict]) -> list[dict]:
    """Group the resolved markets into trade types and report each type.

    A category is a (topic, price band) pair. It becomes a candidate strategy
    only when it has enough resolved trades to be more than an anecdote.
    """
    buckets: dict[tuple, list[dict]] = {}
    for m in markets:
        key = (m["topic"], band_of(m["last_price_dollars"]))
        buckets.setdefault(key, []).append(m)

    out = []
    for (topic, band), ms in sorted(buckets.items()):
        if len(ms) < MIN_CATEGORY_TRADES:
            continue
        for side in ("yes", "no"):
            trades = []
            for m in ms:
                price_paid = side_price(side, m["last_price_dollars"])
                fee = taker_fee(CONTRACTS_PER_TRADE, price_paid)
                cost = CONTRACTS_PER_TRADE * price_paid
                won = (side == m["result"])
                payout = CONTRACTS_PER_TRADE if won else 0.0
                trades.append({
                    "market_ticker": m["market_ticker"],
                    "topic": topic,
                    "band": band,
                    "side": side,
                    "price_paid": round(price_paid, 4),
                    "cost": cost,
                    "fee": fee,
                    "payout": payout,
                    "won": won,
                    "net_pnl": round(payout - cost - fee, 4),
                    "result": m["result"],
                    "settlement_ts": m.get("settlement_ts"),
                })
            wins = sum(1 for t in trades if t["won"])
            capital = sum(t["cost"] for t in trades)
            net = sum(t["net_pnl"] for t in trades)
            fees = sum(t["fee"] for t in trades)
            out.append({
                "topic": topic,
                "price_band": band,
                "side": side,
                "trades": len(trades),
                "wins": wins,
                "hit_rate": wins / len(trades),
                "capital_deployed": round(capital, 2),
                "fees": round(fees, 2),
                "net_pnl": round(net, 2),
                "roi": (net / capital) if capital else None,
                "market_tickers": [t["market_ticker"] for t in trades][:50],
            })
    out.sort(key=lambda c: (c["roi"] is None, -(c["roi"] or 0)))
    return out


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    all_markets, sources = load_universe()

    synthetic = [m for m in all_markets if is_synthetic_demo(m)]
    markets = [m for m in all_markets if not is_synthetic_demo(m)]

    strategies = [evaluate(s, markets) for s in strategy_defs()]
    categories = build_categories(markets)

    by_topic: dict[str, int] = {}
    for m in markets:
        by_topic[m["topic"]] = by_topic.get(m["topic"], 0) + 1

    payload = {
        "generated_at_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "environment": "demo",
        "api_base": "https://external-api.demo.kalshi.co/trade-api/v2",
        "mode": "simulated (paper) - no order is ever sent",
        "contracts_per_trade": CONTRACTS_PER_TRADE,
        "fee_model": {
            "formula": "fee = ceil(0.07 * contracts * price * (1 - price))  (taker)",
            "source": "https://kalshi.com/fee-schedule",
            "note": ("Kalshi publishes a per-100-contract fee range of $0.07-$1.75. "
                     "This parabola reproduces both published endpoints exactly, so "
                     "it is used as the fee model and labelled as an assumption."),
        },
        "universe": {
            "resolved_markets": len(markets),
            "resolved_markets_before_filter": len(all_markets),
            "by_topic": by_topic,
            "sources": sources,
            "rule": ("only markets with an official result of yes or no and a "
                     "last traded price strictly between 0 and 1 are used"),
            "excluded_synthetic_demo_markets": {
                "count": len(synthetic),
                "rule": ("markets whose own title starts with 'Demo ' are demo-only "
                         "synthetic contracts and are left out of the strategy "
                         "statistics"),
                "tickers": [m["market_ticker"] for m in synthetic][:40],
            },
        },
        "strategies": strategies,
        "categories": categories,
        "method_notes": {
            "entry_price": "the market's official last_price_dollars at collection time",
            "payout": "contracts x $1 when the held side equals the official result, else $0",
            "net_pnl": "payout - cost - fee",
            "drawdown": "largest peak-to-trough decline of the cumulative net P&L "
                        "in settlement order",
            "no_estimates": "no open market is booked; only official results settle a trade",
        },
        "caveats": [
            "The Kalshi demo environment uses mock funds; its prices and behaviour "
            "may not reflect real markets "
            "(https://docs.kalshi.com/getting_started/demo_env).",
            "The entry price is the last traded price at collection time, not the "
            "price a real order would necessarily have received.",
            "One contract set per market; no position sizing, no partial fills, no "
            "slippage beyond the published fee.",
            "A positive ROI on demo data is not evidence of a profitable strategy "
            "on the live exchange.",
            "Most resolved in-scope demo markets are short-dated crypto contracts "
            "that settle every few minutes, so the topic mix is not representative "
            "of a real book.",
        ],
        "sources": {
            "get_markets": "https://docs.kalshi.com/api-reference/market/get-markets",
            "market_settlement": "https://docs.kalshi.com/getting_started/market_settlement",
            "demo_env": "https://docs.kalshi.com/getting_started/demo_env",
            "fee_schedule": "https://kalshi.com/fee-schedule",
        },
    }

    out = DATA / "simulations.json"
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {out.relative_to(ROOT)}  markets={len(markets)}  "
          f"strategies={len(strategies)}  categories={len(categories)}")
    for s in strategies:
        roi = "n/a" if s["roi"] is None else f"{s['roi'] * 100:.1f}%"
        print(f"  {s['id']:<14} trades={s['trades']:<5} hit={(s['hit_rate'] or 0) * 100:5.1f}% "
              f"net=${s['net_pnl']:<9.2f} roi={roi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
