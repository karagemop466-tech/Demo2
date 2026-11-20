#!/usr/bin/env python3
"""Offline tests for the Kalshi demo data pipeline.

These run in CI without any network access, so a broken collector is caught before
it can publish an empty snapshot. The fixture values are hand-computed, not copied
from a run, so the expected numbers are checkable by hand.

Run:  python3 tools/test_pipeline.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import collector  # noqa: E402
import roi_model  # noqa: E402

FAILURES: list[str] = []
PASSED = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        PASSED += 1
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} :: {detail}")


def approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


# --------------------------------------------------------------------------- model
def test_model() -> None:
    print("ROI model")
    now = 1_700_000_000.0
    # Hand-computed fixture:
    #   bid 0.40 / ask 0.42  -> mid 0.41, spread 0.02
    #   sizes 300 + 100      -> depth 400
    #   last 0.30            -> dislocation +0.11 -> capped at 1.0
    #   volume 1000          -> turnover log10(1001)/log10(10001)
    #   close +10 days       -> window 1.0
    row = {
        "market_ticker": "T-1",
        "topic": "golf",
        "yes_bid_dollars": "0.40",
        "yes_ask_dollars": "0.42",
        "last_price_dollars": "0.30",
        "yes_bid_size_fp": "300.00",
        "yes_ask_size_fp": "100.00",
        "volume_fp": "1000.00",
        "close_time": "2023-11-15T00:00:00Z",  # 2023-11-14 + 1 day from now
    }
    s = roi_model.score_market(row, now=now)
    d = s["roi_derived"]
    check("derived mid", approx(d["mid"], 0.41, 1e-9), str(d))
    check("derived spread", approx(d["spread"], 0.02, 1e-9), str(d))
    check("derived depth", approx(d["depth"], 400.0, 1e-9), str(d))
    check("derived dislocation", approx(d["dislocation"], 0.11, 1e-9), str(d))
    check("liquidity component capped at 1", approx(s["roi_components"]["liquidity"], 1.0, 1e-9),
          str(s["roi_components"]))
    check("tightness component", approx(s["roi_components"]["tightness"], 0.75, 1e-9),
          str(s["roi_components"]))
    check("dislocation component capped at 1", approx(s["roi_components"]["dislocation"], 1.0, 1e-9),
          str(s["roi_components"]))
    expected = 100.0 * (
        0.28 * 1.0
        + 0.22 * 0.75
        + 0.24 * 1.0
        + 0.10 * (roi_model.math.log10(1001.0) / roi_model.math.log10(10001.0))
        + 0.06 * ((0.30 / 0.70) / 10.0)
        + 0.10 * 1.0
    )
    check("score matches the published formula", approx(s["roi_score"], round(expected, 1), 1e-6),
          f"{s['roi_score']} != {round(expected, 1)}")
    check("gates pass for a liquid tight market", s["roi_gates_passed"] is True, str(s["roi_gate_failures"]))

    # A dead contract must fail the gates and never reach the high-ROI feed.
    dead = {
        "market_ticker": "T-2",
        "yes_bid_dollars": "0.00",
        "yes_ask_dollars": "1.00",
        "last_price_dollars": "0.99",
        "yes_bid_size_fp": "0.00",
        "yes_ask_size_fp": "0.00",
        "volume_fp": "0.00",
        "close_time": "2023-11-15T00:00:00Z",
    }
    sd = roi_model.score_market(dead, now=now)
    check("dead contract fails the gates", sd["roi_gates_passed"] is False, str(sd["roi_gate_failures"]))
    check("dead contract is never high ROI", sd["roi_high"] is False, str(sd))
    check("missing fields never raise", isinstance(sd["roi_score"], float), str(sd))

    # A row with no quote at all must still score (0) rather than crash.
    empty = roi_model.score_market({}, now=now)
    check("empty row scores 0", empty["roi_score"] == 0.0, str(empty["roi_score"]))
    check("empty row is not high ROI", empty["roi_high"] is False, str(empty))


def test_jumps() -> None:
    print("jump detection")
    trades = [
        {"ticker": "A", "topic": "golf", "yes_price_dollars": "0.50", "created_time": "2026-01-01T00:00:00Z",
         "count_fp": "1.00", "trade_id": "1"},
        {"ticker": "A", "topic": "golf", "yes_price_dollars": "0.55", "created_time": "2026-01-01T00:01:00Z",
         "count_fp": "1.00", "trade_id": "2"},
        {"ticker": "A", "topic": "golf", "yes_price_dollars": "0.70", "created_time": "2026-01-01T00:02:00Z",
         "count_fp": "1.00", "trade_id": "3"},
        {"ticker": "B", "topic": "crypto", "yes_price_dollars": "0.10", "created_time": "2026-01-01T00:00:00Z",
         "count_fp": "1.00", "trade_id": "4"},
    ]
    jumps = collector.detect_jumps(trades)
    check("one jump found (0.05 is below the threshold, 0.15 is above)", len(jumps) == 1, str(jumps))
    if jumps:
        j = jumps[0]
        check("jump direction up", j["direction"] == "up", str(j))
        check("jump change value", approx(j["change"], 0.15, 1e-9), str(j))
        check("jump cause is blank", j["cause"] is None, str(j))
        check("jump carries an official source", j["source"].startswith("https://"), str(j))
    check("no jump when nothing moves", collector.detect_jumps(trades[:1]) == [], "expected []")


def test_writers() -> None:
    print("writers")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        collector.DATA = root
        payload = {"a": 1, "b": [1, 2, 3]}
        collector.write_json("x.json", payload)
        raw = (root / "x.json").read_text()
        check("json is written compact (no newlines inside the object)", "\n  " not in raw, repr(raw[:80]))
        check("json round-trips", json.loads(raw) == payload, raw[:80])
        rows = [{"market_ticker": "T", "topic": "golf", "roi_score": 10.0}]
        collector.write_csv(rows, "y.csv", ["market_ticker", "topic", "roi_score"])
        csv_text = (root / "y.csv").read_text().splitlines()
        check("csv header", csv_text[0] == "market_ticker,topic,roi_score", csv_text[0])
        check("csv row", csv_text[1] == "T,golf,10.0", csv_text[1])


def test_index() -> None:
    print("ticker index")
    rows = [{"market_ticker": "T-1", "topic": "golf", "roi_score": 42.0, "last_price_dollars": "0.5"}]
    idx = collector.build_ticker_index(rows)
    check("index keyed by ticker", "T-1" in idx, str(idx))
    check("index carries the topic", idx["T-1"][0] == "golf", str(idx))


def main() -> int:
    test_model()
    test_jumps()
    test_writers()
    test_index()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED, {PASSED} passed")
        for f in FAILURES:
            print("  -", f)
        return 1
    print(f"ALL {PASSED} CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
