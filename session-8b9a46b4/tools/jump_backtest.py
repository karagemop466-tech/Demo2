#!/usr/bin/env python3
"""Session arena-8b9a46b4: sharp-jump detector + simulated strategy backtest.

Reads ONLY already-collected official demo data (data/dashboard_instrument.json,
collected by instrument-panel/tools/kalshi_collect.py from
https://external-api.demo.kalshi.co/trade-api/v2). No network, no inference:
every output row carries its source URL; fields the API does not provide
(e.g. news/event *causes* of a jump) are left blank and flagged.

Jump rule (per user requirement): consecutive trade prints on the same ticker
whose YES price moves by >= $0.10 in either direction.

Backtest rule (SIMULATED, historical): on resolved markets that actually traded
(volume_fp > 0 and last_price_dollars > 0), buy 1 contract at the final print
price and settle at $1/$0 per the official `result`. Caveat (flagged on site):
the final print is not a price knowable at a decision time, so this measures
calibration-style edge, not a tradable entry strategy.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "dashboard_instrument.json"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data"
JUMP_THRESHOLD = 0.10

def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def main():
    d = json.loads(SRC.read_text())
    gen_at = d["meta"]["generated_at"]
    api_base = d["meta"]["api_base"]

    # ---- 1. Sharp jumps from trade prints ----
    jumps = []
    for ticker, block in d["trades"].items():
        prints = sorted(block["trades"], key=lambda t: t["created_time"])
        for a, b in zip(prints, prints[1:]):
            pa, pb = f(a["yes_price_dollars"]), f(b["yes_price_dollars"])
            if pa is None or pb is None: continue
            delta = pb - pa
            if abs(delta) >= JUMP_THRESHOLD - 1e-12:
                jumps.append({
                    "ticker": ticker,
                    "from_time": a["created_time"], "to_time": b["created_time"],
                    "from_yes_price": pa, "to_yes_price": pb,
                    "delta": round(delta, 4),
                    "direction": "up" if delta > 0 else "down",
                    "contracts_from": f(a["count_fp"]), "contracts_to": f(b["count_fp"]),
                    "cause_news_url": "",   # not provided by Kalshi API -> blank, flagged
                    "cause_note": "Kalshi Trade API does not publish news/event causes; left blank (unverified).",
                    "source_url": block["source_url"],
                })
    jumps.sort(key=lambda j: j["to_time"], reverse=True)

    # ---- 2. Simulated strategies on resolved traded markets ----
    traded = [m for m in d["resolved"]
              if (f(m.get("volume_fp")) or 0) > 0 and (f(m.get("last_price_dollars")) or 0) > 0
              and m.get("result") in ("yes", "no")]
    def settle(side, price, result):
        cost = price if side == "yes" else 1 - price
        payout = 1.0 if side == result else 0.0
        return payout - cost
    strategies = {
        "always_yes": lambda p: ("yes", p),
        "always_no": lambda p: ("no", 1 - p),
        "favorite": lambda p: ("yes", p) if p >= 0.5 else ("no", 1 - p),
        "underdog": lambda p: ("no", 1 - p) if p >= 0.5 else ("yes", p),
    }
    def run(rows):
        out = {}
        for name, fn in strategies.items():
            pnls = []
            for m in rows:
                side, price = fn(f(m["last_price_dollars"]))
                pnls.append(settle(side, price, m["result"]))
            out[name] = {
                "n": len(pnls),
                "total_pnl_per_contract": round(sum(pnls), 4) if pnls else None,
                "mean_pnl_per_contract": round(sum(pnls) / len(pnls), 4) if pnls else None,
                "win_rate": round(sum(1 for x in pnls if x > 0) / len(pnls), 4) if pnls else None,
            }
        return out
    by_topic = {}
    for topic in sorted({m["topic"] for m in traded}):
        by_topic[topic] = run([m for m in traded if m["topic"] == topic])

    jumps_out = {"generated_at": gen_at, "api_base": api_base,
                 "threshold_dollars": JUMP_THRESHOLD,
                 "markets_scanned": len(d["trades"]),
                 "prints_scanned": sum(len(b["trades"]) for b in d["trades"].values()),
                 "jump_count": len(jumps), "jumps": jumps,
                 "source_file": "data/dashboard_instrument.json",
                 "source_url": f"{api_base}/markets/trades?ticker={{ticker}}&limit=1000"}
    bt_out = {"generated_at": gen_at, "api_base": api_base,
              "simulated": True,
              "caveat": "Entry at final print price (lookahead); measures calibration edge, not a tradable strategy. Historical demo data only.",
              "population": {"resolved_collected": len(d["resolved"]), "traded_and_priced": len(traded)},
              "overall": run(traded), "by_topic": by_topic,
              "source_file": "data/dashboard_instrument.json",
              "source_url": f"{api_base}/markets?series_ticker={{series}}&status=settled"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "jumps.json").write_text(json.dumps(jumps_out, indent=1))
    (OUT / "backtest.json").write_text(json.dumps(bt_out, indent=1))
    print(f"jumps: {len(jumps)} across {len(d['trades'])} markets; "
          f"backtest population: {len(traded)} traded resolved markets")
    print("overall:", json.dumps(bt_out["overall"]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
