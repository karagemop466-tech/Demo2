#!/usr/bin/env python3
"""Pulse automated simulated-trading engine (no API key, no manual input).

Two outputs, both computed from official snapshots only:

1. data/pulse_backtest.json — five deterministic strategies backtested on
   resolved, *traded* markets (volume_fp > 0). Entry price = the market's
   official last_price_dollars; payout = $1.00 if the held side equals the
   official `result`, else $0 (docs/getting_started/market_settlement).
   One contract per market, gross (fees excluded and stated). Never-traded
   markets (last_price_dollars = 0.0000 default) are excluded — see F-15.

2. data/pulse_simulated.json — live paper portfolio: the top open markets per
   topic by official notional (volume_fp x last_price_dollars, computed and
   labelled), entered at the first collector tick and marked at the latest
   tick. Unrealised P&L only; nothing is booked as realised until Kalshi
   settles the market (result = yes/no).

Strategies (all 1 contract, side from the buyer's point of view):
  always_yes   — buy YES at last price
  always_no    — buy NO at (1 - last price)
  favorite     — buy the side the market favours (YES if price >= 0.50)
  contrarian   — fade the favourite
  longshot_yes — buy YES only when price <= 0.20, else skip

Categorisation: by topic, by side, by entry-price band, by topic x side.
A strategy is only described as supported when n >= 30 resolved trades;
below that the output says "insufficient data" (mirrors the calibration
rule on instrument-panel/site/analysis.html).

Stdlib only. Offline: reads local snapshots, makes no network calls.
"""
from __future__ import annotations

import glob
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
API = "https://external-api.demo.kalshi.co/trade-api/v2"
MIN_N = 30


def fnum(v, default=None):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def band(price: float) -> str:
    for lo, hi, label in [
        (0.00, 0.10, "0.00-0.10"), (0.10, 0.20, "0.10-0.20"),
        (0.20, 0.30, "0.20-0.30"), (0.30, 0.50, "0.30-0.50"),
        (0.50, 0.70, "0.50-0.70"), (0.70, 0.90, "0.70-0.90"),
        (0.90, 1.01, "0.90-1.00"),
    ]:
        if lo <= price < hi or (label == "0.90-1.00" and price == 1.0):
            return label
    return "unknown"


def strategy_side(name: str, price: float):
    """Return 'yes'/'no'/None(skip) for a strategy at a YES price."""
    if name == "always_yes":
        return "yes"
    if name == "always_no":
        return "no"
    if name == "favorite":
        return "yes" if price >= 0.50 else "no"
    if name == "contrarian":
        return "no" if price >= 0.50 else "yes"
    if name == "longshot_yes":
        return "yes" if price <= 0.20 else None
    return None


STRATEGIES = ["always_yes", "always_no", "favorite", "contrarian", "longshot_yes"]


def settle(side: str, price: float, result: str):
    """(cost, payout, pnl) for 1 contract. price is the YES price."""
    cost = price if side == "yes" else (1.0 - price)
    payout = 1.0 if side == result else 0.0
    return round(cost, 4), payout, round(payout - cost, 4)


def main() -> int:
    snap = json.loads((DATA / "dashboard_instrument.json").read_text())
    resolved = snap.get("resolved") or []
    traded = [r for r in resolved
              if (fnum(r.get("volume_fp"), 0) or 0) > 0
              and fnum(r.get("last_price_dollars")) is not None
              and r.get("result") in ("yes", "no")]
    traded.sort(key=lambda r: r.get("close_time") or "")

    # ---- backtest ----
    strat_results: dict[str, dict] = {}
    for name in STRATEGIES:
        trades = []
        for r in traded:
            price = fnum(r["last_price_dollars"])
            side = strategy_side(name, price)
            if side is None:
                continue
            cost, payout, pnl = settle(side, price, r["result"])
            trades.append({
                "ticker": r["ticker"], "topic": r.get("topic") or "unknown",
                "side": side, "entry_yes_price": price, "band": band(price),
                "result": r["result"], "cost": cost, "payout": payout, "pnl": pnl,
                "close_time": r.get("close_time"),
                "source": r.get("source_url") or f"{API}/markets/{r['ticker']}",
            })
        # equity curve in close-time order for max drawdown
        equity, peak, max_dd, run = 0.0, 0.0, 0.0, 0.0
        for t in trades:
            run += t["pnl"]
            equity = run
            peak = max(peak, equity)
            max_dd = min(max_dd, equity - peak)
        wins = sum(1 for t in trades if t["pnl"] > 0)
        losses = sum(1 for t in trades if t["pnl"] < 0)
        strat_results[name] = {
            "n": len(trades), "wins": wins, "losses": losses,
            "win_rate": round(wins / len(trades), 4) if trades else None,
            "total_cost": round(sum(t["cost"] for t in trades), 2),
            "total_payout": round(sum(t["payout"] for t in trades), 2),
            "net_pnl": round(sum(t["pnl"] for t in trades), 2),
            "avg_pnl": round(sum(t["pnl"] for t in trades) / len(trades), 4) if trades else None,
            "max_drawdown": round(max_dd, 2),
            "verdict": (
                "described_n>=30_hindsight_caveat"
                if len(trades) >= MIN_N else "insufficient_data"
            ),
            "trades": trades,
        }

    def categorise(trades, key):
        groups: dict[str, dict] = defaultdict(
            lambda: {"n": 0, "wins": 0, "cost": 0.0, "payout": 0.0, "pnl": 0.0})
        for t in trades:
            g = groups[t[key]]
            g["n"] += 1
            g["wins"] += 1 if t["pnl"] > 0 else 0
            g["cost"] += t["cost"]
            g["payout"] += t["payout"]
            g["pnl"] += t["pnl"]
        return {k: {"n": v["n"], "wins": v["wins"],
                    "win_rate": round(v["wins"] / v["n"], 4) if v["n"] else None,
                    "cost": round(v["cost"], 2), "payout": round(v["payout"], 2),
                    "pnl": round(v["pnl"], 2)} for k, v in sorted(groups.items())}

    # categorise the favorite strategy's trades (the only side-varying one
    # with a full sample); other strategies are single-side by construction.
    fav_trades = strat_results["favorite"]["trades"]
    backtest = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": (
            "Backtest on resolved traded markets only (volume_fp > 0, result yes/no). "
            "Entry = official last_price_dollars; payout $1 if held side == result "
            "(market_settlement). 1 contract per market, gross of fees. "
            "Never-traded markets excluded (last_price 0.0000 is a default, F-15). "
            "CAVEAT (hindsight): last_price is the final traded price, not a price "
            "you could necessarily have bought at. Treat this as a calibration "
            "description (implied vs realised), not a tradable strategy. Fees, "
            "slippage and out-of-sample testing are excluded."
        ),
        "population": {
            "resolved_total": len(resolved), "traded_used": len(traded),
            "never_traded_excluded": len(resolved) - len(traded),
            "by_topic": dict(sorted(
                __import__("collections").Counter(
                    r.get("topic") or "unknown" for r in traded).items())),
        },
        "strategies": {k: {kk: vv for kk, vv in v.items() if kk != "trades"}
                       for k, v in strat_results.items()},
        "categorisation_favorite": {
            "by_topic": categorise(fav_trades, "topic"),
            "by_side": categorise(fav_trades, "side"),
            "by_band": categorise(fav_trades, "band"),
        },
        "trades_by_strategy": {k: v["trades"] for k, v in strat_results.items()},
        "docs": {
            "settlement": "https://docs.kalshi.com/getting_started/market_settlement",
            "get_markets": "https://docs.kalshi.com/api-reference/market/get-markets",
        },
    }
    (DATA / "pulse_backtest.json").write_text(json.dumps(backtest, indent=1) + "\n")

    # ---- live paper portfolio (top open per topic, tick entry/mark) ----
    samples: list[dict] = []
    for path in sorted(glob.glob(str(DATA / "history_instrument" / "20*.json"))):
        try:
            h = json.loads(Path(path).read_text())
        except (OSError, json.JSONDecodeError):
            continue
        samples.extend(s for s in (h.get("samples") or [])
                       if isinstance(s.get("ts"), (int, float)))
    samples.sort(key=lambda s: s["ts"])

    def tick_price(ticker: str, which: str):
        vals = []
        for s in samples:
            cell = (s.get("markets") or {}).get(ticker)
            if cell and fnum(cell.get("lp")) is not None:
                vals.append(fnum(cell["lp"]))
        if not vals:
            return None
        return vals[0] if which == "first" else vals[-1]

    positions = []
    for topic, rows in (snap.get("markets") or {}).items():
        ranked = sorted(rows, key=lambda m: fnum(m.get("notional_lifetime_usd"), 0) or 0,
                        reverse=True)[:3]
        for m in ranked:
            ticker = m["ticker"]
            entry = tick_price(ticker, "first")
            mark = tick_price(ticker, "last")
            if entry is None:
                entry = fnum(m.get("last_price_dollars"))
            if mark is None:
                mark = fnum(m.get("last_price_dollars"))
            if entry is None or mark is None:
                continue
            # paper side: favorite (buy the favoured side at entry)
            side = "yes" if entry >= 0.50 else "no"
            entry_cost = entry if side == "yes" else 1.0 - entry
            mark_value = mark if side == "yes" else 1.0 - mark
            positions.append({
                "ticker": ticker, "topic": topic, "title": m.get("title") or "",
                "side": side, "entry_yes_price": entry, "mark_yes_price": mark,
                "entry_cost": round(entry_cost, 4),
                "unrealised_pnl": round(mark_value - entry_cost, 4),
                "notional_lifetime_usd": m.get("notional_lifetime_usd"),
                "volume_fp": m.get("volume_fp"),
                "open_interest_fp": m.get("open_interest_fp"),
                "close_time": m.get("close_time"),
                "source": m.get("source_market_url") or f"{API}/markets/{ticker}",
            })
    positions.sort(key=lambda p: (p["topic"], -float(p["notional_lifetime_usd"] or 0)))
    simulated = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "paper_simulated_no_key",
        "method": (
            "Top 3 open markets per topic by computed notional "
            "(volume_fp x last_price_dollars, labelled computed). Entry = first "
            "collector tick last price, mark = latest tick. Side = favorite. "
            "Unrealised only; realised stays blank until Kalshi settles (result)."
        ),
        "portfolio": {
            "positions": len(positions),
            "invested": round(sum(p["entry_cost"] for p in positions), 2),
            "unrealised_pnl": round(sum(p["unrealised_pnl"] for p in positions), 2),
            "realised_pnl": None,
            "note": "Realised is blank (not zero) until markets settle.",
        },
        "positions": positions,
        "docs": {
            "settlement": "https://docs.kalshi.com/getting_started/market_settlement",
            "get_markets": "https://docs.kalshi.com/api-reference/market/get-markets",
        },
    }
    (DATA / "pulse_simulated.json").write_text(json.dumps(simulated, indent=1) + "\n")
    print(f"pulse_simulate: backtest n={len(traded)} traded; "
          f"paper positions={len(positions)}")
    for name, r in strat_results.items():
        print(f"  {name}: n={r['n']} pnl={r['net_pnl']} verdict={r['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
