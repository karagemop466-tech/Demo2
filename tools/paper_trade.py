#!/usr/bin/env python3
"""Automated simulated (paper) trading over the collected Kalshi demo snapshot.

Runs on GitHub Actions with NO credentials (see .github/workflows/paper-trade.yml),
reads data/snapshot.json (+ data/history.json) written by tools/collector.py, and
writes data/paper_portfolio.json. This is the "automate simulated trades to test
different strategies" requirement: nothing is sent to any exchange, no key is used,
and every input is an official field copied by the collector.

Strategies (deterministic; same snapshot -> same decisions):
  momentum     buy YES at the ask when the recorded price history rose >= $0.10
  mean_revert  buy NO  at the derived ask (1 - yes_bid) when it fell >= $0.10
  longshot     buy YES at the ask when 0 < last <= $0.10 and volume_fp >= 100
  favorite     buy YES at the ask when last >= $0.90 and the spread <= $0.05

Every trade is categorised by topic, strategy and price band (longshot / mid /
favorite) so results can be analysed by trade type. Open positions are held until
the market resolves and are settled on the official `result` field: YES pays $1 per
contract on "yes", NO pays $1 on "no" (docs: getting_started/market_settlement).

Disclosed limits (also flagged on the site as F23):
  - fees are NOT modeled (fee schedule not verified here -> left at zero, blank not
    guessed); real results would be lower
  - fills are assumed at the quoted ask with no slippage and no partial fills
  - marks use the quoted bid; when a side is blank in the API response the position
    is marked at cost and labelled "mark blank"
  - this is a simulation over demo-environment prices, which the official demo page
    warns may not reflect real markets (docs: getting_started/demo_env)
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("DATA_DIR") or (ROOT / "data"))

START_CASH = 100.00
MAX_OPEN = 20
NEAR_TERM_RESERVE = 6
NEAR_TERM_DAYS = 7
COUNT_PER_TRADE = 10.0          # contracts
LONGSHOT_MAX = 0.10
FAVORITE_MIN = 0.90
FALL_MAX = 0.05                 # favorite spread cap
HISTORY_RISE = 0.10
HISTORY_FALL = 0.10
EQUITY_HISTORY_CAP = 500

DOCS_SETTLEMENT = "https://docs.kalshi.com/getting_started/market_settlement"
DOCS_DEMO = "https://docs.kalshi.com/getting_started/demo_env"


def f(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def price_band(last: float) -> str:
    if last <= LONGSHOT_MAX:
        return "longshot"
    if last >= FAVORITE_MIN:
        return "favorite"
    return "mid"


def load() -> tuple[dict, dict]:
    snap = json.loads((DATA / "snapshot.json").read_text()) if (DATA / "snapshot.json").exists() else {}
    hist = json.loads((DATA / "history.json").read_text()) if (DATA / "history.json").exists() else {}
    return snap, hist


def history_move(points: list[dict]) -> float | None:
    """Last minus first recorded price over the kept history. None if not computable."""
    vals = [f(p.get("last")) for p in points or []]
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    return round(vals[-1] - vals[0], 4)


def is_near_term(market: dict, ref_dt: dt.datetime, days: int = NEAR_TERM_DAYS) -> bool:
    """True when close_time is within (0, days] of ref_dt."""
    ct = market.get("close_time")
    if not ct:
        return False
    try:
        close_dt = dt.datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
    except ValueError:
        return False
    delta = close_dt - ref_dt
    return dt.timedelta(0) < delta <= dt.timedelta(days=days)


def decide(market: dict, points: list[dict], held: set[str]) -> dict | None:
    """Return a trade intent for one market row, or None. Never guesses a blank."""
    t = market.get("market_ticker")
    if not t or t in held:
        return None
    # never open a position on a market that has already resolved
    if (market.get("result") or "") in ("yes", "no"):
        return None
    last = f(market.get("last_price_dollars"))
    yb = f(market.get("yes_bid_dollars"))
    ya = f(market.get("yes_ask_dollars"))
    vol = f(market.get("volume_fp"))
    if last is None:
        return None
    move = history_move(points)

    def intent(side: str, price: float | None, strategy: str, reason: str) -> dict | None:
        if price is None or price <= 0 or price >= 1:
            return None  # no usable ask -> stay out; blank is never filled in
        return {
            "ticker": t, "title": market.get("market_title") or market.get("title") or "",
            "topic": market.get("topic") or "", "side": side, "price_dollars": round(price, 4),
            "count": COUNT_PER_TRADE, "strategy": strategy,
            "category": {"topic": market.get("topic") or "", "band": price_band(last),
                         "side": side, "strategy": strategy},
            "reason": reason, "source_url": market.get("market_url") or "",
        }

    if move is not None and move >= HISTORY_RISE:
        return intent("yes", ya, "momentum",
                      f"history rose {move:+.4f} (>= +{HISTORY_RISE:.2f}) over recorded ticks; buy YES at ask")
    if move is not None and move <= -HISTORY_FALL:
        # buy NO at the derived ask: a NO ask equals 1 - yes_bid (orderbook docs)
        return intent("no", (1 - yb) if yb is not None else None, "mean_revert",
                      f"history fell {move:+.4f} (<= -{HISTORY_FALL:.2f}); buy NO at derived ask 1 - yes_bid")
    if 0 < last <= LONGSHOT_MAX and (vol or 0) >= 100:
        return intent("yes", ya, "longshot",
                      f"last {last:.4f} <= {LONGSHOT_MAX:.2f} with volume_fp {vol:.0f} >= 100; buy YES at ask")
    if last >= FAVORITE_MIN and yb is not None and ya is not None and (ya - yb) <= FALL_MAX:
        return intent("yes", ya, "favorite",
                      f"last {last:.4f} >= {FAVORITE_MIN:.2f} and spread {ya - yb:.4f} <= {FALL_MAX:.2f}; buy YES at ask")
    return None


def settle(pos: dict, result: str) -> dict:
    won = (pos["side"] == "yes" and result == "yes") or (pos["side"] == "no" and result == "no")
    payout = pos["count"] * (1.0 if won else 0.0)
    pnl = round(payout - pos["cost_dollars"], 4)
    out = dict(pos)
    out.update({"result": result, "payout_dollars": round(payout, 4), "realized_pnl_dollars": pnl,
                "settled_at_utc": now_iso(),
                "settlement_source": DOCS_SETTLEMENT})
    return out


def main() -> int:
    snap, hist = load()
    if not snap:
        print("no data/snapshot.json — run tools/collector.py first", file=sys.stderr)
        return 1

    ledger_path = DATA / "paper_portfolio.json"
    if ledger_path.exists():
        led = json.loads(ledger_path.read_text())
    else:
        led = {
            "starting_cash_dollars": f"{START_CASH:.2f}",
            "cash_dollars": START_CASH,
            "trades": [], "positions": [], "settled": [], "history": [],
            "definitions": {
                "type": "SIMULATED paper trading. No orders are sent anywhere; no API key is used.",
                "fees": "NOT modeled (left at zero — flagged F23, never guessed).",
                "fills": "assumed at the quoted ask, no slippage, no partial fills.",
                "marks": "mark-to-market at the quoted bid; when a side is blank the position "
                         "is marked at cost and labelled 'mark blank'.",
                "settlement": f"official result field: yes -> YES pays $1/contract, no -> NO pays $1/contract ({DOCS_SETTLEMENT})",
                "environment": f"demo prices may not reflect real markets ({DOCS_DEMO})",
                "strategies": {
                    "momentum": f"buy YES at ask when recorded history rose >= +${HISTORY_RISE:.2f}",
                    "mean_revert": f"buy NO at derived ask (1 - yes_bid) when history fell <= -${HISTORY_FALL:.2f}",
                    "longshot": f"buy YES at ask when 0 < last <= ${LONGSHOT_MAX:.2f} and volume_fp >= 100",
                    "favorite": f"buy YES at ask when last >= ${FAVORITE_MIN:.2f} and spread <= ${FALL_MAX:.2f}",
                },
            },
        }

    led.setdefault("trades", [])
    led.setdefault("positions", [])
    led.setdefault("settled", [])
    led.setdefault("history", [])
    led["generated_at_utc"] = now_iso()
    led["source_snapshot_generated_at"] = snap.get("generated_at_utc") or ""

    rows = snap.get("markets") or []
    resolutions = {r.get("market_ticker"): r for r in (snap.get("resolutions") or [])}
    for r in rows:
        if r.get("result") in ("yes", "no"):
            resolutions.setdefault(r.get("market_ticker"), r)

    # 1) settle resolved positions on the official result
    still_open = []
    for p in led["positions"]:
        rec = resolutions.get(p["ticker"])
        if rec and rec.get("result") in ("yes", "no"):
            s = settle(p, rec["result"])
            led["settled"].append(s)
            led["cash_dollars"] = round(led["cash_dollars"] + s["payout_dollars"], 4)
        else:
            still_open.append(p)
    led["positions"] = still_open

    # 2) evaluate strategies on the snapshot (deterministic order: est_dollar_volume desc, ticker)
    #    settled tickers stay in `held` forever so a market is never re-bought after resolution.
    #    Reserve up to NEAR_TERM_RESERVE slots for markets closing within NEAR_TERM_DAYS so the
    #    simulated portfolio exercises real settlements rather than locking every slot until 2028+.
    held = {p["ticker"] for p in led["positions"]} | {s["ticker"] for s in led["settled"]}
    points = (hist.get("points") or {})
    ordered = sorted(rows, key=lambda m: (-(m.get("est_dollar_volume") or 0), m.get("market_ticker") or ""))
    try:
        ref_dt = dt.datetime.fromisoformat(str(snap.get("generated_at_utc") or "").replace("Z", "+00:00"))
    except ValueError:
        ref_dt = dt.datetime.now(dt.timezone.utc)
    near_candidates = [m for m in ordered if is_near_term(m, ref_dt)]
    near_open_count = sum(1 for p in led["positions"] if is_near_term({"close_time": p.get("close_time")}, ref_dt))
    near_budget = max(0, NEAR_TERM_RESERVE - near_open_count)
    new_trades = 0

    def try_open(m: dict) -> bool:
        nonlocal new_trades
        intent = decide(m, points.get(m.get("market_ticker"), []), held)
        if not intent:
            return False
        cost = round(intent["price_dollars"] * intent["count"], 4)
        if cost > led["cash_dollars"]:
            return False
        led["cash_dollars"] = round(led["cash_dollars"] - cost, 4)
        trade = {"ts": now_iso(), "cost_dollars": cost, **intent}
        led["trades"].append(trade)
        led["positions"].append({
            "ticker": intent["ticker"], "title": intent["title"], "topic": intent["topic"],
            "side": intent["side"], "entry_price_dollars": intent["price_dollars"],
            "count": intent["count"], "cost_dollars": cost, "opened_ts": trade["ts"],
            "close_time": m.get("close_time") or "",
            "strategy": intent["strategy"], "source_url": intent["source_url"],
        })
        held.add(intent["ticker"])
        new_trades += 1
        return True

    near_added = 0
    for m in near_candidates:
        if len(led["positions"]) >= MAX_OPEN or near_added >= near_budget:
            break
        if try_open(m):
            near_added += 1

    for m in ordered:
        if len(led["positions"]) >= MAX_OPEN:
            break
        try_open(m)

    # 3) mark to market
    by_ticker = {m.get("market_ticker"): m for m in rows}
    marks = {}
    for p in led["positions"]:
        m = by_ticker.get(p["ticker"]) or {}
        bid = f(m.get("yes_bid_dollars")) if p["side"] == "yes" else f(m.get("no_bid_dollars"))
        if bid is None:
            p["mark_price_dollars"] = p["entry_price_dollars"]
            p["mark_note"] = "mark blank — bid missing in API response; marked at cost"
            p["unrealized_pnl_dollars"] = 0.0
        else:
            p["mark_price_dollars"] = round(bid, 4)
            p["mark_note"] = ""
            p["unrealized_pnl_dollars"] = round((bid - p["entry_price_dollars"]) * p["count"], 4)
        marks[p["ticker"]] = p["unrealized_pnl_dollars"]

    # 4) strategy stats (by trade type)
    stats: dict[str, dict] = {}
    for t in led["trades"]:
        s = stats.setdefault(t["strategy"], {"trades": 0, "open_positions": 0, "settled": 0,
                                             "wins": 0, "losses": 0, "realized_pnl_dollars": 0.0,
                                             "cost_dollars": 0.0})
        s["trades"] += 1
        s["cost_dollars"] = round(s["cost_dollars"] + t["cost_dollars"], 4)
    for p in led["positions"]:
        stats.setdefault(p["strategy"], {"trades": 0, "open_positions": 0, "settled": 0,
                                         "wins": 0, "losses": 0, "realized_pnl_dollars": 0.0,
                                         "cost_dollars": 0.0})["open_positions"] += 1
    for s in led["settled"]:
        st = stats.setdefault(s["strategy"], {"trades": 0, "open_positions": 0, "settled": 0,
                                              "wins": 0, "losses": 0, "realized_pnl_dollars": 0.0,
                                              "cost_dollars": 0.0})
        st["settled"] += 1
        st["wins" if s["payout_dollars"] > 0 else "losses"] += 1
        st["realized_pnl_dollars"] = round(st["realized_pnl_dollars"] + s["realized_pnl_dollars"], 4)
    led["strategy_stats"] = stats

    # 5) equity + bounded history
    unrealized = round(sum(marks.values()), 4)
    settled_pnl = round(sum(s["realized_pnl_dollars"] for s in led["settled"]), 4)
    equity = round(led["cash_dollars"] + sum(p["count"] * p["mark_price_dollars"] for p in led["positions"]), 4)
    led["totals"] = {
        "cash_dollars": round(led["cash_dollars"], 4),
        "equity_dollars": equity,
        "realized_pnl_dollars": settled_pnl,
        "unrealized_pnl_dollars": unrealized,
        "trades_total": len(led["trades"]),
        "open_positions": len(led["positions"]),
        "settled_positions": len(led["settled"]),
        "resolution_counts": {
            "yes": sum(1 for s in led["settled"] if s.get("result") == "yes"),
            "no": sum(1 for s in led["settled"] if s.get("result") == "no"),
        },
    }
    led["history"].append({"ts": now_iso(), "equity_dollars": equity,
                           "cash_dollars": round(led["cash_dollars"], 4),
                           "open_positions": len(led["positions"])})
    led["history"] = led["history"][-EQUITY_HISTORY_CAP:]

    DATA.mkdir(exist_ok=True)
    ledger_path.write_text(json.dumps(led, indent=1) + "\n")
    print(f"paper portfolio: equity={equity:.2f} cash={led['cash_dollars']:.2f} "
          f"open={len(led['positions'])} settled={len(led['settled'])} new_trades={new_trades}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
