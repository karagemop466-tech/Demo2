#!/usr/bin/env python3
"""Automated SIMULATED strategy desk for the Kalshi demo dashboard.

Run by `.github/workflows/refresh-data.yml` right after `tools/collector.py`, so every
data refresh also advances the simulation — no manual input, no credentials, and no
order is ever sent to the exchange from here.

What this is
------------
Paper trading against REAL collected prices. Entry and exit prices are raw official
fields from `GET /markets` (as captured by the collector into `data/snapshot.json`):

  * buy YES at the market's `yes_ask_dollars`      (official field)
  * buy NO  at the market's `no_ask_dollars`       (official field)
  * mark open positions at `last_price_dollars`    (official field; NO marked at 1 - p,
    which is the documented binary equivalence and is labelled "derived")
  * settle at `settlement_value_dollars` from the market's settled record, falling back
    to the official `result` field ("yes" -> $1.00 to the YES side, "no" -> $0.00)

Fees use the series' own `fee_type` / `fee_multiplier` (official fields on the series
record — verified live 2026-11-20: `GET /series/KXBTC` -> `fee_type: "quadratic"`,
`fee_multiplier: 1`) with Kalshi's published quadratic general form
`0.07 x multiplier x contracts x price x (1 - price)`, rounded up per
https://docs.kalshi.com/getting_started/fee_rounding . The 0.07 constant is Kalshi's
general fee schedule and is NOT restated on docs.kalshi.com, so every fee in this ledger
is labelled `fee_basis: "quadratic model, 0.07 constant — not exchange-confirmed"`.

What this is NOT
----------------
It is not the demo account's performance. The real account (`data/portfolio.json`,
`tools/portfolio.py`) stays "not configured" until a demo API key exists in repository
secrets; nothing here reads or writes it. Fills are assumptions of execution at the
posted quote with unlimited size — the order book is NOT consulted, so a real account
could be filled worse or not at all. Every table on `pages/paper-trading.html` says so.

Self-test: `python3 tools/paper_trade.py --selftest` (hand-computed fixture, no network).
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import os
from decimal import ROUND_CEILING, Decimal
import json

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LEDGER = DATA / "paper_ledger.json"

START_CASH = float(os.environ.get("KALSHI_PAPER_START_CASH", "1000"))
POSITION_USD = 25.0            # notional per simulated position
MAX_NEW_PER_RUN = 10           # per strategy, keeps the ledger legible
MIN_TRADES_FOR_VERDICT = 10    # below this, no pattern may be described
SWING = 0.10                   # the brief's threshold: a >= $0.10 move in either direction
FEE_CONST = 0.07               # general quadratic constant (see module docstring)

TOPICS = ["gas", "elections", "culture", "crypto", "golf"]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def f(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


MICRO = Decimal("0.000001")


def fee_for(count: float, price, multiplier=None) -> float:
    """Trade fee: Kalshi's quadratic general form, rounded UP to $0.000001 per
    https://docs.kalshi.com/getting_started/fee_rounding (fees are six-decimal amounts).

    Computed in Decimal, not float: `0.07 * 26 * 0.95 * 0.05` is 0.08645000000000001 in
    binary floating point, and a "round up" of that overcharges by a micro-dollar. The
    multiplier is taken from the series' own `fee_multiplier` field when the collector
    captured one, so it is the exchange's number rather than an assumed one.
    """
    m = Decimal(str(multiplier)) if multiplier not in (None, "", 0, "0") else Decimal(1)
    pr = Decimal(str(price))
    fee = Decimal(str(FEE_CONST)) * m * Decimal(str(count)) * pr * (Decimal(1) - pr)
    return float(fee.quantize(MICRO, rounding=ROUND_CEILING))


# --------------------------------------------------------------------------- rules
# Each strategy is a pure screen over ONE market row plus that market's collected tick
# history. No strategy uses information the collector did not have, and no strategy
# claims an edge: `verdict` text is withheld below MIN_TRADES_FOR_VERDICT closed trades.
def hist_series(history: dict, ticker: str) -> list[float]:
    pts = (history.get("points") or {}).get(ticker) or []
    out = []
    for p in pts:
        v = f(p.get("last"))
        if v is not None:
            out.append(v)
    return out


def last_swing(vals: list[float], lookback: int = 6) -> float:
    """Largest signed move between consecutive collected points in the last `lookback`."""
    tail = vals[-lookback:] if len(vals) > 1 else []
    best = 0.0
    for a, b in zip(tail, tail[1:]):
        d = b - a
        if abs(d) > abs(best):
            best = d
    return best


def days_to(close_time: str | None) -> float | None:
    """Days from now to the market's official `close_time`; None when absent."""
    if not close_time:
        return None
    try:
        d = dt.datetime.fromisoformat(str(close_time).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (d - dt.datetime.now(dt.timezone.utc)).total_seconds() / 86400.0


def strat_fade_down(m: dict, ctx: dict) -> str | None:
    if ctx["swing"] <= -SWING and f(m.get("last_price_dollars")) is not None \
            and f(m["last_price_dollars"]) <= 0.45:
        return f"collected history shows a {ctx['swing']:+.2f} move and yes is still <= $0.45"
    return None


def strat_ride_up(m: dict, ctx: dict) -> str | None:
    if ctx["swing"] >= SWING and f(m.get("volume_24h_fp")) and \
            f(m["volume_24h_fp"]) >= 25 and f(m.get("last_price_dollars")) not in (None,) \
            and f(m["last_price_dollars"]) <= 0.90:
        return f"collected history shows a {ctx['swing']:+.2f} move with 24h volume " \
               f"{f(m['volume_24h_fp']):.0f} contracts"
    return None


def strat_longshot_no(m: dict, ctx: dict) -> str | None:
    ya = f(m.get("yes_ask_dollars"))
    dte = days_to(m.get("close_time"))
    if ya is not None and ya >= 0.90 and dte is not None and 0 < dte <= 7:
        return f"yes ask at ${ya:.2f} with {dte:.1f} days to close"
    return None


def strat_converge_yes(m: dict, ctx: dict) -> str | None:
    mid_yes = f(m.get("yes_bid_dollars"))
    dte = days_to(m.get("close_time"))
    if mid_yes is not None and mid_yes >= 0.95 and dte is not None and 0 < dte <= 3 \
            and (f(m.get("est_dollar_volume")) or 0) >= 1000:
        return f"yes bid at ${mid_yes:.2f}, est. ${f(m.get('est_dollar_volume')):,.0f} " \
               f"volume, {dte:.1f} days to close"
    return None


STRATEGIES: dict[str, dict[str, Any]] = {
    "fade_down_move": {"side": "yes", "rule": strat_fade_down,
                       "describe": "Buy YES at the posted ask after a >= $0.10 drop in the "
                                   "collected tick history, while the price is still <= $0.45."},
    "ride_up_move": {"side": "yes", "rule": strat_ride_up,
                     "describe": "Buy YES at the posted ask after a >= $0.10 rise with "
                                 "meaningful 24h volume, capped at $0.90."},
    "longshot_no_fade": {"side": "no", "rule": strat_longshot_no,
                         "describe": "Buy NO at the posted ask where YES is quoted at "
                                     "$0.90 or better and the market closes within 7 days."},
    "converge_yes": {"side": "yes", "rule": strat_converge_yes,
                     "describe": "Buy YES at the posted ask on a near-certain, high-volume "
                                 "market closing within 3 days (harvest the last cents)."},
}


# --------------------------------------------------------------------------- ledger
def load_ledger() -> dict:
    if LEDGER.exists():
        try:
            d = json.loads(LEDGER.read_text())
            if isinstance(d, dict) and "trades" in d:
                return d
        except (json.JSONDecodeError, OSError):
            pass
    return {"trades": [], "runs": [], "next_id": 1, "cash": START_CASH,
            "realized_pnl_dollars": 0.0, "fees_paid_dollars": 0.0}


def settle_and_mark(ledger: dict, snap: dict) -> tuple[list[dict], list[dict]]:
    """Close settled trades at official settlement values; refresh marks on the rest."""
    by_ticker = {m["market_ticker"]: m for m in snap.get("markets") or []}
    resolved = {r["market_ticker"]: r for r in snap.get("resolutions") or [] if r.get("market_ticker")}
    marks, closes = [], []
    for t in ledger["trades"]:
        if t.get("status") != "open":
            continue
        tk = t["market_ticker"]
        r = resolved.get(tk)
        m = by_ticker.get(tk)
        if r is not None:
            result = (r.get("result") or "").lower()
            if result not in ("yes", "no"):
                t["needs_review"] = ("settled record returned result "
                                     f"{r.get('result')!r}; position left open rather than guessed")
                continue
            won = (result == t["side"])
            sv = f(r.get("settlement_value_dollars"))
            if sv is None or sv not in (0.0, 1.0):
                payout_per = 1.0 if won else 0.0
                t["payout_basis"] = "derived from the official result field (settlement_value_dollars absent)"
            else:
                payout_per = sv if t["side"] == "yes" else round(1.0 - sv, 4)
                t["payout_basis"] = "official settlement_value_dollars"
            proceeds = round(t["contracts"] * payout_per, 6)
            t["status"] = "settled"
            t["settled_at"] = r.get("settlement_ts")
            t["official_result"] = result
            t["proceeds_dollars"] = proceeds
            t["realized_pnl_dollars"] = round(proceeds - t["cost_dollars"], 6)
            t["source_url"] = r.get("market_url") or t.get("source_url")
            ledger["cash"] = round(ledger["cash"] + proceeds, 6)
            ledger["realized_pnl_dollars"] = round(ledger["realized_pnl_dollars"]
                                                   + t["realized_pnl_dollars"], 6)
            closes.append(t)
            continue
        if m is None:
            t["stale_marks"] = (t.get("stale_marks", 0) + 1)
            continue
        lp = f(m.get("last_price_dollars"))
        if lp is None:
            continue
        mark_per = lp if t["side"] == "yes" else round(1.0 - lp, 4)
        t["mark_price_dollars"] = mark_per
        t["mark_value_dollars"] = round(t["contracts"] * mark_per, 6)
        t["marked_at"] = snap.get("generated_at_utc")
        t["unrealized_pnl_dollars"] = round(t["mark_value_dollars"] - t["cost_dollars"], 6)
        marks.append(t)
    return marks, closes


def new_trades(ledger: dict, snap: dict) -> tuple[list[dict], dict, dict]:
    held = {(t["strategy"], t["market_ticker"]) for t in ledger["trades"] if t.get("status") == "open"}
    tried = {(t["strategy"], t["market_ticker"]) for t in ledger["trades"]}
    history = {}
    hp = DATA / "history.json"
    if hp.exists():
        try:
            history = json.loads(hp.read_text())
        except json.JSONDecodeError:
            history = {}
    created: list[dict] = []
    screened_by: dict[str, int] = {}
    # Why a rule fired but produced no order. On the demo exchange most books are empty
    # (yes ask quoted at 1.00 / 0.00), so "0 fills" is usually "no executable quote",
    # not "no opportunity" — the numbers are published so that is visible, not implied.
    skips: dict[str, int] = {"no_usable_ask": 0, "size_below_one_contract": 0,
                             "insufficient_paper_cash": 0}
    for name, spec in STRATEGIES.items():
        made = 0
        screened = 0
        for m in snap.get("markets") or []:
            if made >= MAX_NEW_PER_RUN:
                break
            tk = m.get("market_ticker")
            if not tk or (name, tk) in held or (name, tk) in tried:
                continue
            ctx = {"swing": last_swing(hist_series(history, tk))}
            try:
                reason = spec["rule"](m, ctx)
            except (TypeError, ValueError):
                reason = None
            if not reason:
                continue
            side = spec["side"]
            screened += 1
            price = f(m.get("yes_ask_dollars")) if side == "yes" else f(m.get("no_ask_dollars"))
            if price is None or not (0.0 < price < 1.0):
                # no posted ask for that side -> no simulated fill (never invent a price)
                skips["no_usable_ask"] += 1
                continue
            contracts = int(POSITION_USD / price)
            if contracts < 1:
                skips["size_below_one_contract"] += 1
                continue
            cost = round(contracts * price, 6)
            fee = round(fee_for(contracts, price, f(m.get("series_fee_multiplier"))), 6)
            if cost + fee > ledger["cash"]:
                skips["insufficient_paper_cash"] += 1
                continue
            created.append({
                "id": None,  # assigned below, in order
                "strategy": name,
                "topic": m.get("topic"),
                "market_ticker": tk,
                "market_title": m.get("market_title") or m.get("title"),
                "event_ticker": m.get("event_ticker"),
                "series_ticker": m.get("series_ticker"),
                "side": side,
                "contracts": contracts,
                "entry_price_dollars": price,
                "entry_field": "yes_ask_dollars" if side == "yes" else "no_ask_dollars",
                "cost_dollars": cost,
                "fee_dollars": fee,
                "fee_basis": "quadratic model, 0.07 constant — not exchange-confirmed",
                "series_fee_type": m.get("series_fee_type"),
                "series_fee_multiplier": m.get("series_fee_multiplier"),
                "opened_at": now_iso(),
                "opened_run": snap.get("generated_at_utc"),
                "status": "open",
                "reason": reason,
                "trigger_swing_dollars": round(ctx["swing"], 4),
                "close_time": m.get("close_time"),
                "source_url": m.get("market_url"),
                "mark_price_dollars": price,
                "mark_value_dollars": cost,
                "unrealized_pnl_dollars": 0.0,
                "simulated": True,
            })
            ledger["cash"] = round(ledger["cash"] - cost - fee, 6)
            ledger["fees_paid_dollars"] = round(ledger["fees_paid_dollars"] + fee, 6)
            made += 1
        screened_by[name] = screened
    for t in created:
        t["id"] = ledger["next_id"]
        ledger["next_id"] += 1
        ledger["trades"].append(t)
    return created, screened_by, skips


def summarise(ledger: dict, snap: dict, created: list[dict], closes: list[dict],
              screened_by: dict | None = None, skips: dict | None = None) -> dict:
    trades = ledger["trades"]
    per: dict[str, dict] = {}
    for name in STRATEGIES:
        rows = [t for t in trades if t["strategy"] == name]
        closed = [t for t in rows if t["status"] == "settled"]
        openn = [t for t in rows if t["status"] == "open"]
        wins = [t for t in closed if (t.get("realized_pnl_dollars") or 0) > 0]
        losses = [t for t in closed if (t.get("realized_pnl_dollars") or 0) <= 0]
        realized = round(sum(t.get("realized_pnl_dollars") or 0 for t in closed), 4)
        unreal = round(sum(t.get("unrealized_pnl_dollars") or 0 for t in openn), 4)
        fees = round(sum(t.get("fee_dollars") or 0 for t in rows), 4)
        cost = round(sum(t.get("cost_dollars") or 0 for t in rows), 4)
        payout = round(sum(t.get("proceeds_dollars") or 0 for t in closed), 4)
        entry = round(sum(t.get("mark_value_dollars") or 0 for t in openn), 4)
        net = round(realized + unreal, 4)
        per[name] = {
            "strategy": name,
            "describe": STRATEGIES[name]["describe"],
            "side": STRATEGIES[name]["side"],
            "trades": len(rows),
            "settled": len(closed),
            "open": len(openn),
            "wins": len(wins),
            "losses": len(losses),
            "hit_rate": round(len(wins) / len(closed), 4) if closed else None,
            "cost_dollars": cost,
            "proceeds_dollars": payout,
            "open_mark_value_dollars": entry,
            "fees_dollars": fees,
            "realized_pnl_dollars": realized,
            "unrealized_pnl_dollars": unreal,
            "net_pnl_dollars": net,
            "roi_on_cost": round(net / cost, 4) if cost else None,
            "avg_win_dollars": round(sum(t["realized_pnl_dollars"] for t in wins) / len(wins), 4) if wins else None,
            "avg_loss_dollars": round(sum(t["realized_pnl_dollars"] for t in losses) / len(losses), 4) if losses else None,
            "verdict": (
                f"{len(closed)} settled trades — too few to describe a pattern "
                f"(threshold {MIN_TRADES_FOR_VERDICT}); nothing is claimed"
                if len(closed) < MIN_TRADES_FOR_VERDICT else
                f"{len(wins)}/{len(closed)} settled trades profitable; net ${net:+,.2f} "
                f"after ${fees:,.2f} simulated fees"
            ),
        }
    by_topic: dict[str, dict] = {}
    for topic in TOPICS:
        rows = [t for t in trades if t.get("topic") == topic]
        if not rows:
            continue
        closed = [t for t in rows if t["status"] == "settled"]
        by_topic[topic] = {
            "trades": len(rows),
            "settled": len(closed),
            "realized_pnl_dollars": round(sum(t.get("realized_pnl_dollars") or 0 for t in closed), 4),
            "fees_dollars": round(sum(t.get("fee_dollars") or 0 for t in rows), 4),
        }
    openn = [t for t in trades if t["status"] == "open"]
    equity = round(ledger["cash"] + sum(t.get("mark_value_dollars") or 0 for t in openn), 6)
    return {
        "generated_at_utc": now_iso(),
        "snapshot_generated_at_utc": snap.get("generated_at_utc"),
        "simulated": True,
        "notice": (
            "SIMULATED fills placed by this repository's own code at the posted quote. "
            "No order was sent to Kalshi and this is NOT the demo account's performance; "
            "the account itself is reported separately in data/portfolio.json. Execution "
            "at the full posted size is assumed — the order book is not consulted."
        ),
        "cash_dollars": round(ledger["cash"], 6),
        "start_cash_dollars": START_CASH,
        "equity_dollars": equity,
        "equity_definition": "cash + mark-to-market value of open positions (derived from last_price_dollars)",
        "total_return": round((equity / START_CASH) - 1.0, 6) if START_CASH else None,
        "realized_pnl_dollars": round(ledger["realized_pnl_dollars"], 6),
        "fees_paid_dollars": round(ledger["fees_paid_dollars"], 6),
        "totals": {
            "trades": len(trades),
            "open": len(openn),
            "settled": len([t for t in trades if t["status"] == "settled"]),
            "opened_this_run": len(created),
            "settled_this_run": len(closes),
        },
        "by_strategy": per,
        "by_topic": by_topic,
        "entry_rules_fired_but_no_order_this_run": {
            "screened_and_matched": sum((screened_by or {}).values()),
            "orders_written": len(created),
            "reasons": dict(skips or {}),
            "meaning": "a match with no order means the posted quote could not be taken "
                       "at the simulated size; the desk never invents a fill price",
        },
        "policy": {
            "position_usd": POSITION_USD,
            "max_new_per_strategy_per_run": MAX_NEW_PER_RUN,
            "min_settled_for_verdict": MIN_TRADES_FOR_VERDICT,
            "swing_threshold_dollars": SWING,
            "fee_model": "0.07 x series fee_multiplier x contracts x p x (1-p), rounded up",
            "fee_constant_source": "Kalshi general fee schedule; the 0.07 constant is not restated on docs.kalshi.com — see pages/flagged.html",
        },
    }


def run(snap: dict, ledger: dict, write: bool = True, quiet: bool = False) -> tuple[dict, dict]:
    """Advance the desk one run. Returns (summary, updated_ledger) — the caller's ledger
    is copied, so an unchanged input means a dry run really was side-effect free."""
    ledger = copy.deepcopy(ledger)
    marks, closes = settle_and_mark(ledger, snap)
    created, screened_by, skips = new_trades(ledger, snap)
    summary = summarise(ledger, snap, created, closes, screened_by, skips)
    ledger.setdefault("runs", []).append({
        "at": summary["generated_at_utc"],
        "snapshot": summary["snapshot_generated_at_utc"],
        "opened": len(created),
        "settled": len(closes),
        "marked": len(marks),
        "equity_dollars": summary["equity_dollars"],
        "cash_dollars": summary["cash_dollars"],
    })
    ledger["runs"] = ledger["runs"][-500:]
    ledger["trades"] = ledger["trades"][-4000:]
    ledger["summary"] = summary
    if write:
        DATA.mkdir(exist_ok=True)
        out = {
            "generated_at_utc": summary["generated_at_utc"],
            "schema": "kalshi-paper-ledger/1",
            "summary": summary,
            "runs": ledger["runs"],
            "trades": ledger["trades"],
            "cash": ledger["cash"],
            "next_id": ledger["next_id"],
            "realized_pnl_dollars": ledger["realized_pnl_dollars"],
            "fees_paid_dollars": ledger["fees_paid_dollars"],
        }
        LEDGER.write_text(json.dumps(out, indent=1) + "\n")
        if not quiet:
            # DATA may be relocated by a caller (tests, CI temp dirs): show the real path.
            try:
                shown = LEDGER.relative_to(ROOT)
            except ValueError:
                shown = LEDGER
            print(f"wrote {shown} ({LEDGER.stat().st_size:,} bytes) "
                  f"trades={len(out['trades'])} opened={len(created)} settled={len(closes)}")
    elif not quiet:
        print(f"dry-run: would open {len(created)}, settle {len(closes)}, "
              f"mark {len(marks)}; equity ${summary['equity_dollars']:,.2f}")
    return summary, ledger


# ---------------------------------------------------------------------------- selftest
def selftest() -> int:
    """Hand-computed fixture: the arithmetic the CI gate checks, with no network.

    Close times are generated relative to NOW (+20 h) rather than hard-coded, because the
    entry rules are about time-to-close; the asserted numbers below do not depend on it.
    """
    close = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = {
        "generated_at_utc": "2026-01-01T00:00:00+00:00",
        "markets": [
            {"market_ticker": "A-1", "topic": "crypto", "market_title": "A",
             "yes_ask_dollars": "0.9500", "no_ask_dollars": "0.0500",
             "yes_bid_dollars": "0.9600", "last_price_dollars": "0.9500",
             "close_time": close, "volume_24h_fp": "5000.00",
             "est_dollar_volume": 5000.0, "series_fee_multiplier": "1"},
        ],
        "resolutions": [],
    }
    ledger = {"trades": [], "runs": [], "next_id": 1, "cash": 1000.0,
              "realized_pnl_dollars": 0.0, "fees_paid_dollars": 0.0}
    s, ledger = run(snap, ledger, write=False, quiet=True)
    by_side = {x["side"]: x for x in ledger["trades"]}
    assert len(by_side) == 2, f"expected one YES and one NO fill, got {list(by_side)}"
    tr = by_side["yes"]
    # 0.95 -> 26 contracts for <=$25; cost 24.70; fee = ceil6(0.07*26*0.95*0.05)
    assert tr["contracts"] == 26, tr["contracts"]
    assert tr["cost_dollars"] == 24.70, tr["cost_dollars"]
    assert abs(tr["fee_dollars"] - 0.086450) < 1e-9, tr["fee_dollars"]
    # longshot_no_fade fires on the same market too (buy NO at $0.05): 500 contracts
    no_tr = by_side["no"]
    assert no_tr and no_tr["contracts"] == 500 and no_tr["cost_dollars"] == 25.0, no_tr
    # now settle it YES: the YES strategy gets $26.00 back, the NO strategy $0.00
    snap2 = {"generated_at_utc": "2026-01-02T00:00:00+00:00", "markets": [],
             "resolutions": [{"market_ticker": "A-1", "result": "yes",
                              "settlement_value_dollars": "1.0000",
                              "settlement_ts": "2026-01-02T00:00:00Z",
                              "market_url": "https://external-api.demo.kalshi.co/trade-api/v2/markets/A-1"}]}
    ledger2 = {"trades": [dict(x) for x in ledger["trades"]], "runs": [], "next_id": 99,
               "cash": ledger["cash"], "realized_pnl_dollars": 0.0, "fees_paid_dollars": 0.0}
    marks, closes = settle_and_mark(ledger2, snap2)
    yes = next(t for t in closes if t["side"] == "yes")
    no = next(t for t in closes if t["side"] == "no")
    assert yes["realized_pnl_dollars"] == round(26 * 1.0 - 24.70, 6), yes
    assert no["realized_pnl_dollars"] == round(500 * 0.0 - 25.0, 6) == -25.0, no
    assert yes["official_result"] == "yes" and no["payout_basis"] == "official settlement_value_dollars"
    # no posted ask -> no trade (never invent a price)
    snap3 = {"generated_at_utc": "x", "markets": [{"market_ticker": "B-1", "topic": "golf",
              "yes_ask_dollars": "1.0000", "no_ask_dollars": "0.0000",
              "yes_bid_dollars": "0.0000", "last_price_dollars": "0.0000",
              "close_time": None, "est_dollar_volume": 0}], "resolutions": []}
    empty = {"trades": [], "runs": [], "next_id": 1, "cash": 1000.0,
             "realized_pnl_dollars": 0.0, "fees_paid_dollars": 0.0}
    _, empty = run(snap3, empty, write=False)
    assert empty["trades"] == [], "a market with no usable ask must not produce a fill"
    print("paper_trade selftest OK: sizing, fee rounding, settlement both sides, no-fill guard")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    sp = DATA / "snapshot.json"
    if not sp.exists():
        print("::warning::data/snapshot.json missing — run the collector first; skipping the desk")
        return 0
    snap = json.loads(sp.read_text())
    summary, _ = run(snap, load_ledger(), write=not args.dry_run)
    tot = summary["totals"]
    print(f"paper desk: trades={tot['trades']} open={tot['open']} settled={tot['settled']} "
          f"equity=${summary['equity_dollars']:,.2f} realized=${summary['realized_pnl_dollars']:,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
