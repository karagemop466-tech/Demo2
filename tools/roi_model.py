#!/usr/bin/env python3
"""High-ROI shortlist model for Kalshi demo markets.

WHAT THIS IS
    A deterministic, fully published ranking score. It uses ONLY fields that the
    official Kalshi demo Trade API returns (documented at
    https://docs.kalshi.com/api-reference/market/get-markets and
    https://docs.kalshi.com/api-reference/market/get-market-orderbook), plus four
    arithmetic combinations of those fields which are always labelled "derived".

WHAT THIS IS NOT
    It is not a prediction, it does not know the outcome of a market, and it is not
    investment advice. A high score means "this contract is liquid, tight, recently
    moved and priced so that a $0.10 swing is worth capturing" - nothing more.

HOW IT IS VERIFIED
    `tools/roi_model.py` (this file) is the single implementation. `assets/roi.js`
    reproduces the same arithmetic in the browser for live rows; the two are checked
    against one shared fixture by `tools/test_roi_model.py`, which CI runs. The
    weights below are published to `data/roi_model.json` so the site shows the
    numbers it actually used.

SOURCES (official)
    https://docs.kalshi.com/api-reference/market/get-markets
    https://docs.kalshi.com/api-reference/market/get-market-orderbook
    https://docs.kalshi.com/getting_started/demo_env
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# --------------------------------------------------------------------------- model
MODEL: dict[str, Any] = {
    "name": "Kalshi demo high-ROI shortlist score",
    "version": "1.0.0",
    "type": "deterministic heuristic ranking (no outcome prediction)",
    "inputs": [
        "yes_bid_dollars", "yes_ask_dollars", "last_price_dollars",
        "yes_bid_size_fp", "yes_ask_size_fp", "volume_fp", "close_time",
    ],
    "derived": {
        "mid": "(yes_bid_dollars + yes_ask_dollars) / 2",
        "spread": "yes_ask_dollars - yes_bid_dollars",
        "depth": "yes_bid_size_fp + yes_ask_size_fp",
        "dislocation": "mid - last_price_dollars",
        "payoff_multiple": "last_price_dollars / (1 - last_price_dollars)",
        "days_to_close": "(close_time - now) / 86400",
    },
    "weights": {
        "liquidity": 0.28,
        "tightness": 0.22,
        "dislocation": 0.24,
        "turnover": 0.10,
        "payoff": 0.06,
        "window": 0.10,
    },
    "scales": {
        "depth_full": 250.0,
        "spread_max": 0.08,
        "dislocation_full": 0.05,
        "volume_full": 10000.0,
        "payoff_full": 10.0,
        "window_days": 30.0,
    },
    "gates": {
        "min_volume": 0.0,
        "min_price": 0.02,
        "max_price": 0.98,
        "max_spread": 0.10,
        "min_depth": 1.0,
    },
    "roi_min": 55.0,
    "note": (
        "Score = 100 * sum(weight_i * component_i), each component in [0,1]. "
        "A market only reaches the high-ROI feed if it also passes every gate. "
        "Weights and scales are published in data/roi_model.json."
    ),
}


def _f(v: Any) -> float | None:
    """Parse an API decimal string. Returns None when the field is absent/empty."""
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(n):
        return None
    return n


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def score_market(row: dict, now: float | None = None) -> dict:
    """Score one market row. Returns the score plus every intermediate value so the
    site can show why a market was picked instead of asking the reader to trust it."""
    now = time.time() if now is None else now
    w = MODEL["weights"]
    s = MODEL["scales"]
    g = MODEL["gates"]

    bid = _f(row.get("yes_bid_dollars"))
    ask = _f(row.get("yes_ask_dollars"))
    last = _f(row.get("last_price_dollars"))
    bid_sz = _f(row.get("yes_bid_size_fp")) or 0.0
    ask_sz = _f(row.get("yes_ask_size_fp")) or 0.0
    vol = _f(row.get("volume_fp")) or 0.0
    close = row.get("close_time") or ""

    days = None
    if close:
        try:
            import datetime as dt
            t = dt.datetime.fromisoformat(str(close).replace("Z", "+00:00"))
            days = (t.timestamp() - now) / 86400.0
        except Exception:
            days = None

    mid = None if (bid is None or ask is None) else (bid + ask) / 2.0
    spread = None if (bid is None or ask is None) else ask - bid
    depth = bid_sz + ask_sz
    disloc = None if (mid is None or last is None) else mid - last
    payoff = None
    if last is not None and 0.0 < last < 1.0:
        payoff = last / (1.0 - last)

    c_liq = _clamp(depth / s["depth_full"])
    c_tight = 0.0 if spread is None else _clamp(1.0 - spread / s["spread_max"])
    c_disl = 0.0 if disloc is None else _clamp(abs(disloc) / s["dislocation_full"])
    c_turn = _clamp(math.log10(1.0 + vol) / math.log10(1.0 + s["volume_full"]))
    c_pay = 0.0 if payoff is None else _clamp(payoff / s["payoff_full"])
    if days is None:
        c_win = 0.0
    elif days <= 0:
        c_win = 0.0
    elif days <= s["window_days"]:
        c_win = 1.0
    else:
        c_win = _clamp(1.0 - (days - s["window_days"]) / s["window_days"])

    total = (
        w["liquidity"] * c_liq
        + w["tightness"] * c_tight
        + w["dislocation"] * c_disl
        + w["turnover"] * c_turn
        + w["payoff"] * c_pay
        + w["window"] * c_win
    )
    score = round(100.0 * total, 1)

    reasons: list[str] = []
    if c_liq >= 0.25:
        reasons.append(f"depth {depth:,.0f} contracts at the touch")
    if c_tight >= 0.5:
        reasons.append(f"spread {spread:.3f}" if spread is not None else "tight spread")
    if c_disl >= 0.4:
        reasons.append(f"last trade {disloc:+.3f} away from mid" if disloc is not None else "dislocated")
    if c_turn >= 0.5:
        reasons.append(f"{vol:,.0f} contracts traded")
    if c_win >= 0.99 and days is not None:
        reasons.append(f"closes in {days:.1f} d")

    gates_passed = (
        vol > g["min_volume"]
        and last is not None
        and g["min_price"] <= last <= g["max_price"]
        and spread is not None
        and spread <= g["max_spread"]
        and depth >= g["min_depth"]
    )
    gate_fail: list[str] = []
    if vol <= g["min_volume"]:
        gate_fail.append("no volume")
    if last is None:
        gate_fail.append("no last price")
    elif last < g["min_price"] or last > g["max_price"]:
        gate_fail.append(f"price {last:.3f} outside {g['min_price']}-{g['max_price']}")
    if spread is None:
        gate_fail.append("no two-sided quote")
    elif spread > g["max_spread"]:
        gate_fail.append(f"spread {spread:.3f} > {g['max_spread']}")
    if depth < g["min_depth"]:
        gate_fail.append("no size at the touch")

    return {
        "roi_score": score,
        "roi_components": {
            "liquidity": round(c_liq, 3),
            "tightness": round(c_tight, 3),
            "dislocation": round(c_disl, 3),
            "turnover": round(c_turn, 3),
            "payoff": round(c_pay, 3),
            "window": round(c_win, 3),
        },
        "roi_reasons": reasons,
        "roi_gates_passed": bool(gates_passed),
        "roi_gate_failures": gate_fail,
        "roi_derived": {
            "mid": None if mid is None else round(mid, 4),
            "spread": None if spread is None else round(spread, 4),
            "depth": round(depth, 2),
            "dislocation": None if disloc is None else round(disloc, 4),
            "payoff_multiple": None if payoff is None else round(payoff, 3),
            "days_to_close": None if days is None else round(days, 2),
        },
        "roi_high": bool(gates_passed and score >= MODEL["roi_min"]),
    }


def score_rows(rows: list[dict], now: float | None = None) -> list[dict]:
    """Attach the score fields to each row (returns new dicts)."""
    out = []
    for r in rows:
        s = score_market(r, now=now)
        nr = dict(r)
        nr.update(
            {
                "roi_score": s["roi_score"],
                "roi_components": s["roi_components"],
                "roi_reasons": s["roi_reasons"],
                "roi_gates_passed": s["roi_gates_passed"],
                "roi_gate_failures": s["roi_gate_failures"],
                "roi_high": s["roi_high"],
            }
        )
        out.append(nr)
    return out


# --------------------------------------------------------------------------- backtest
def backtest(resolved_rows: list[dict], bands: list[float] = (0, 35, 55, 70, 85)) -> dict:
    """Simulated strategy test on already-settled in-scope markets.

    CAVEAT, and it is a real one: the entry price used is the market's LAST recorded
    price, which is the price the market finished on. That is lookahead - the outcome
    is already visible in the price. So these numbers measure how the demo market
    population is CALIBRATED, not a strategy you could have traded. They are labelled
    as simulated everywhere they appear on the site.
    """
    priced = []
    for r in resolved_rows:
        last = _f(r.get("last_price_dollars"))
        result = (r.get("result") or "").lower()
        if last is None or result not in ("yes", "no"):
            continue
        if not (0.0 < last < 1.0):
            continue
        priced.append((r, last, result))
    if not priced:
        return {"population": 0, "note": "no settled market with a usable last price"}

    out: dict[str, Any] = {
        "population": len(priced),
        "caveat": (
            "Simulated. Entry uses the market's final recorded price, so the outcome is "
            "already visible in the entry price. This measures calibration, not a "
            "tradable edge."
        ),
        "bands": [],
    }
    scored = []
    for r, last, result in priced:
        s = score_market(r)
        scored.append((s["roi_score"], last, result, r.get("topic")))
    edges = list(bands)
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        sel = [x for x in scored if lo <= x[0] < hi]
        if not sel:
            out["bands"].append({"band": f"{lo}-{hi}", "n": 0})
            continue
        entry_yes = sum(1.0 - p for _, p, _, _ in sel) / len(sel)
        entry_no = sum(p for _, p, _, _ in sel) / len(sel)
        yes_wins = sum(1 for _, _, res, _ in sel if res == "yes") / len(sel)
        pnl_yes = sum((1.0 - p) if res == "yes" else -p for _, p, res, _ in sel) / len(sel)
        pnl_no = sum((1.0 - p) if res == "no" else -p for _, p, res, _ in sel) / len(sel)
        out["bands"].append(
            {
                "band": f"{lo}-{hi}",
                "n": len(sel),
                "mean_entry_yes": round(entry_yes, 4),
                "mean_entry_no": round(entry_no, 4),
                "resolved_yes_rate": round(yes_wins, 4),
                "pnl_per_contract_buy_yes": round(pnl_yes, 4),
                "pnl_per_contract_buy_no": round(pnl_no, 4),
            }
        )
    return out


# --------------------------------------------------------------------------- CLI
def main() -> int:
    snap_path = DATA / "snapshot.json"
    resolved_path = DATA / "resolutions.json"
    out_path = DATA / "roi_model.json"

    payload: dict[str, Any] = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": MODEL,
        "sources": [
            "https://docs.kalshi.com/api-reference/market/get-markets",
            "https://docs.kalshi.com/api-reference/market/get-market-orderbook",
            "https://docs.kalshi.com/getting_started/demo_env",
        ],
    }

    if snap_path.exists():
        snap = json.loads(snap_path.read_text())
        markets = snap.get("markets") or []
        if markets:
            scored = score_rows(markets)
            scored.sort(key=lambda r: -(r.get("roi_score") or 0))
            payload["population"] = len(scored)
            payload["high_roi_count"] = sum(1 for r in scored if r.get("roi_high"))
            payload["top"] = [
                {
                    "market_ticker": r.get("market_ticker"),
                    "market_title": r.get("market_title"),
                    "topic": r.get("topic"),
                    "roi_score": r.get("roi_score"),
                    "roi_reasons": r.get("roi_reasons"),
                    "roi_derived": r.get("roi_derived"),
                    "last_price_dollars": r.get("last_price_dollars"),
                    "yes_bid_dollars": r.get("yes_bid_dollars"),
                    "yes_ask_dollars": r.get("yes_ask_dollars"),
                    "volume_fp": r.get("volume_fp"),
                    "close_time": r.get("close_time"),
                }
                for r in scored[:60]
            ]

    if resolved_path.exists():
        pool = json.loads(resolved_path.read_text())
        rows = pool.get("resolutions") or pool.get("resolved") or []
        payload["backtest"] = backtest(rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
