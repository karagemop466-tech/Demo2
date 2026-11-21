#!/usr/bin/env python3
"""Offline regression tests for tools/paper_trade.py (no network, no keys).

Run:  python3 tests/test_paper_trade.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = 0


def ok(cond: bool, label: str) -> None:
    global PASS
    assert cond, f"FAIL: {label}"
    PASS += 1
    print(f"  ok: {label}")


def row(ticker: str, topic: str, last: str, yb: str, ya: str, vol: str = "500.00",
        result: str = "", market_ticker: str | None = None) -> dict:
    return {
        "topic": topic, "market_ticker": market_ticker or ticker,
        "market_title": f"Test {ticker}", "status": "active", "result": result,
        "yes_bid_dollars": yb, "yes_ask_dollars": ya, "last_price_dollars": last,
        "volume_fp": vol, "market_url": f"https://external-api.demo.kalshi.co/trade-api/v2/markets/{ticker}",
    }


def main_test() -> None:
    data = Path(tempfile.mkdtemp(prefix="kalshi-paper-"))
    snap = {
        "generated_at_utc": "2026-11-20T20:00:00+00:00",
        "markets": [
            # momentum: history rises 0.40 -> 0.55
            row("MOM-1", "golf", "0.5500", "0.5000", "0.5600"),
            # mean_revert: history falls 0.60 -> 0.45
            row("MR-1", "elections", "0.4500", "0.4400", "0.5000"),
            # longshot: last 0.08 with volume
            row("LS-1", "crypto", "0.0800", "0.0700", "0.0900", vol="200.00"),
            # favorite: last 0.92, tight spread
            row("FAV-1", "elections", "0.9200", "0.9100", "0.9300"),
            # blank ask -> must be skipped, never guessed
            row("BLANK-1", "crypto", "0.3000", "0.2800", ""),
            # no history -> no momentum, mid price -> no other strategy
            row("FLAT-1", "golf", "0.5000", "0.4800", "0.5200"),
            # already settled winner for the second run (position opened run 1)
            row("MOM-2", "culture", "0.5500", "0.5000", "0.5600"),
        ],
        "resolutions": [],
    }
    hist = {"points": {
        "MOM-1": [{"t": 1, "last": "0.4000"}, {"t": 2, "last": "0.5500"}],
        "MR-1": [{"t": 1, "last": "0.6000"}, {"t": 2, "last": "0.4500"}],
        "MOM-2": [{"t": 1, "last": "0.4000"}, {"t": 2, "last": "0.5500"}],
    }}
    (data / "snapshot.json").write_text(json.dumps(snap))
    (data / "history.json").write_text(json.dumps(hist))
    env = dict(os.environ, DATA_DIR=str(data))

    r = subprocess.run([sys.executable, str(ROOT / "tools" / "paper_trade.py")],
                       capture_output=True, text=True, env=env)
    ok(r.returncode == 0, f"first run exits 0 ({r.stdout.strip()})")
    led = json.loads((data / "paper_portfolio.json").read_text())

    by = {t["ticker"]: t for t in led["trades"]}
    ok("MOM-1" in by and by["MOM-1"]["strategy"] == "momentum" and by["MOM-1"]["side"] == "yes",
       "momentum buys YES at the ask after a >= $0.10 rise")
    ok("MR-1" in by and by["MR-1"]["strategy"] == "mean_revert" and by["MR-1"]["side"] == "no",
       "mean_revert buys NO after a >= $0.10 fall")
    ok("BLANK-1" not in by, "blank ask is skipped, never filled in")
    ok("FLAT-1" not in by, "no-signal market is not traded")
    ok(by["LS-1"]["category"]["band"] == "longshot", "trades are categorised by price band")
    ok(by["FAV-1"]["category"]["band"] == "favorite", "favorite band tagged")
    ok(led["totals"]["cash_dollars"] < 100.0 and led["totals"]["trades_total"] >= 4,
       "cash reduced by simulated costs")
    ok(set(led["totals"]) >= {"cash_dollars", "equity_dollars", "realized_pnl_dollars",
                              "unrealized_pnl_dollars", "resolution_counts"},
       "totals expose performance fields")
    ok(all("source_url" in t and t["source_url"] for t in led["trades"]),
       "every trade carries an official source link")
    ok(led["definitions"]["type"].startswith("SIMULATED"), "output labelled SIMULATED")

    # second run: MOM-2 resolves yes -> payout $10, no duplicate trades
    snap["markets"] = [dict(m, result="yes", status="settled") if m["market_ticker"] == "MOM-2" else m
                       for m in snap["markets"]]
    snap["resolutions"] = [{"market_ticker": "MOM-2", "topic": "culture", "result": "yes"}]
    (data / "snapshot.json").write_text(json.dumps(snap))
    r2 = subprocess.run([sys.executable, str(ROOT / "tools" / "paper_trade.py")],
                        capture_output=True, text=True, env=env)
    ok(r2.returncode == 0, "second run exits 0")
    led2 = json.loads((data / "paper_portfolio.json").read_text())
    ok(led2["totals"]["trades_total"] == led["totals"]["trades_total"],
       "held markets are not re-bought")
    ok(led2["totals"]["settled_positions"] == 1, "resolved position moved to settled")
    s = led2["settled"][0]
    ok(s["result"] == "yes" and s["payout_dollars"] == 10.0,
       "YES win pays $1/contract on the official result")
    ok(abs(s["realized_pnl_dollars"] - (10.0 - s["cost_dollars"])) < 1e-6,
       "realized P&L = payout - cost")
    ok(led2["totals"]["resolution_counts"]["yes"] == 1, "resolution counted as yes")
    ok(led2["strategy_stats"]["momentum"]["wins"] == 1, "strategy stats record the win")

    # Missing and invalid marks must never turn into invented cost/zero valuations.
    for value in (None, "", "NaN", "Infinity", "1.1", "-0.1"):
        snap["markets"] = [dict(m, yes_bid_dollars=value) if m["market_ticker"] == "MOM-1" else m
                           for m in snap["markets"]]
        (data / "snapshot.json").write_text(json.dumps(snap))
        subprocess.run([sys.executable, str(ROOT / "tools" / "paper_trade.py")],
                       check=True, capture_output=True, text=True, env=env)
        marked = json.loads((data / "paper_portfolio.json").read_text())
        pos = next(p for p in marked["positions"] if p["ticker"] == "MOM-1")
        ok(pos["mark_price_dollars"] is None and pos["unrealized_pnl_dollars"] is None,
           f"missing/invalid bid {value!r} stays unknown")
        ok(marked["totals"]["equity_dollars"] is None and
           marked["totals"]["unrealized_pnl_dollars"] is None,
           "incomplete marks invalidate aggregate equity and unrealized P&L")
        ok(marked["history"][-1]["equity_dollars"] is None, "history retains unknown equity")
    snap["markets"] = [dict(m, yes_bid_dollars="0.0000", no_bid_dollars="0.0000")
                       for m in snap["markets"]]
    (data / "snapshot.json").write_text(json.dumps(snap))
    subprocess.run([sys.executable, str(ROOT / "tools" / "paper_trade.py")],
                   check=True, capture_output=True, text=True, env=env)
    zero = json.loads((data / "paper_portfolio.json").read_text())
    ok(zero["totals"]["unpriced_positions"] == 0, "explicit zero bid is not treated as missing")
    ok(zero["totals"]["equity_dollars"] == zero["cash_dollars"], "zero bid arithmetic preserved")

    # cap test: 25 fresh signals -> at most MAX_OPEN (20) new positions
    data2 = Path(tempfile.mkdtemp(prefix="kalshi-paper-cap-"))
    snap2 = {"generated_at_utc": "2026-11-20T20:00:00+00:00",
             "markets": [row(f"LS-{i}", "crypto", "0.0500", "0.0400", "0.0600", vol="300.00")
                         for i in range(25)], "resolutions": []}
    (data2 / "snapshot.json").write_text(json.dumps(snap2))
    (data2 / "history.json").write_text(json.dumps({"points": {}}))
    env2 = dict(os.environ, DATA_DIR=str(data2))
    subprocess.run([sys.executable, str(ROOT / "tools" / "paper_trade.py")],
                   check=True, capture_output=True, text=True, env=env2)
    led3 = json.loads((data2 / "paper_portfolio.json").read_text())
    ok(led3["totals"]["open_positions"] <= 20, "open-position cap enforced (20)")
    ok(led3["totals"]["open_positions"] == 20 and led3["totals"]["trades_total"] == 20,
       "caps fill deterministically in ranked order")

    # float precision + near-term horizon reservation test:
    # 0.60 - 0.50 = 0.09999999999999998 in float; rounded move must trigger momentum
    data3 = Path(tempfile.mkdtemp(prefix="kalshi-paper-near-"))
    far_rows = [dict(row(f"FAR-{i}", "elections", "0.0500", "0.0400", "0.0600", vol="500.00"),
                     est_dollar_volume=1000.0, close_time="2028-11-01T00:00:00Z")
                for i in range(25)]
    near_row = dict(row("NEAR-1", "crypto", "0.6000", "0.5800", "0.6200", vol="150.00"),
                    est_dollar_volume=10.0, close_time="2026-11-22T20:00:00Z")
    snap3 = {"generated_at_utc": "2026-11-20T20:00:00+00:00",
             "markets": far_rows + [near_row], "resolutions": []}
    hist3 = {"points": {"NEAR-1": [{"t": 1, "last": "0.5000"}, {"t": 2, "last": "0.6000"}]}}
    (data3 / "snapshot.json").write_text(json.dumps(snap3))
    (data3 / "history.json").write_text(json.dumps(hist3))
    env3 = dict(os.environ, DATA_DIR=str(data3))
    subprocess.run([sys.executable, str(ROOT / "tools" / "paper_trade.py")],
                   check=True, capture_output=True, text=True, env=env3)
    led4 = json.loads((data3 / "paper_portfolio.json").read_text())
    by4 = {t["ticker"]: t for t in led4["trades"]}
    ok("NEAR-1" in by4 and by4["NEAR-1"]["strategy"] == "momentum",
       "near-term market reserved ahead of 2028 backlog and exact $0.10 float rise (0.50->0.60) fires")


if __name__ == "__main__":
    main_test()
    print(f"\nALL PASS ({PASS} assertions)")
