#!/usr/bin/env python3
"""Execute demo trades described by data/strategy_plan.json.  Writes data/executions.json.

Write path (verified): POST /portfolio/events/orders  — "Create Order (V2)".
The legacy POST /portfolio/orders write endpoints were REMOVED and now return
410 Gone with code deprecated_v1_order_endpoint:
  https://docs.kalshi.com/api-reference/orders/create-order-v2.md

Required body fields per the documented schema:
  ticker, side (bid|ask), count (fixed-point string), price (fixed-point dollars),
  time_in_force (fill_or_kill|good_till_canceled|immediate_or_cancel),
  self_trade_prevention_type (taker_at_cross|maker)
  side: bid = buy YES, ask = sell YES (BookSide is quoted from the YES leg only,
  per the Get Fills / BookSide definition).
  i.e. buying NO at (1 - yes_price) is an `ask` at the YES price.

Safety, non-negotiable:
  - demo environment only; the base URL is hard-coded to the demo host
  - refuses to spend more than the configured notional cap per run
  - refuses to trade a ticker that is not in the collector's in-scope set
  - refuses duplicate tickers within one run
  - every attempt (including rejections) is recorded with its HTTP status/body
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collector import DATA, DEMO_REST, signer_from_env  # noqa: E402

# Caps are taken from the plan file when present (data/strategy_plan.json -> run_limits),
# and can only be tightened by the environment, never loosened.
DEFAULT_MAX_NOTIONAL = 25.0
DRY_RUN = os.environ.get("KALSHI_DRY_RUN", "1") not in ("0", "false", "False")


def post_order(signer, body: dict) -> dict:
    url = DEMO_REST + "/portfolio/events/orders"
    ts_headers = signer.headers("POST", "/trade-api/v2/portfolio/events/orders")
    req = urllib.request.Request(url, method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **ts_headers})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return {"http_status": r.status, "ok": True, "body": json.loads(raw or "{}"), "request": body, "url": url}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:800]
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return {"http_status": e.code, "ok": False, "body": parsed, "request": body, "url": url}
    except Exception as e:  # network
        return {"http_status": 0, "ok": False, "body": {"error": str(e)[:300]}, "request": body, "url": url}


def main() -> int:
    plan_path = DATA / "strategy_plan.json"
    if not plan_path.exists():
        print("no strategy_plan.json — nothing to execute")
        (DATA / "executions.json").write_text(
            json.dumps({"at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                        "executed": [], "mode": "dry_run" if DRY_RUN else "live_demo",
                        "reason": "no strategy_plan.json present"}, indent=1) + "\n")
        return 0

    plan = json.loads(plan_path.read_text())
    limits = plan.get("run_limits") or {}
    # A plan or environment may tighten, but must never raise the default cap.
    max_notional = Decimal(str(DEFAULT_MAX_NOTIONAL))
    if limits.get("max_notional_usd") is not None:
        max_notional = min(max_notional, Decimal(str(limits["max_notional_usd"])))
    max_notional = min(max_notional, Decimal(str(os.environ.get("KALSHI_MAX_NOTIONAL_USD", max_notional))))
    if not max_notional.is_finite() or max_notional < 0:
        raise ValueError("max notional must be finite and nonnegative")
    max_orders = min(10, int(limits.get("max_orders_per_run", 10)))
    if max_orders < 0:
        raise ValueError("max orders must be nonnegative")
    snap_path = DATA / "snapshot.json"
    snap = json.loads(snap_path.read_text()) if snap_path.exists() else {}
    in_scope = {m["market_ticker"]: m for m in snap.get("markets") or []}

    signer = signer_from_env()
    results: list[dict] = []
    spent = Decimal("0")
    submitted = 0
    seen: set[str] = set()

    for intent in plan.get("orders") or []:
        ticker = intent.get("ticker", "")
        side = intent.get("side")                   # user-facing: yes | no, never guessed
        price = intent.get("price")                 # YES-denominated price
        try:
            count = Decimal(str(intent.get("count", 0)))
            yes_px = Decimal(str(price))
        except (InvalidOperation, ValueError):
            count, yes_px = Decimal("NaN"), Decimal("NaN")
        note = {}

        # global kill switch: execution is enabled only when the repo owner opts in
        if os.environ.get("KALSHI_TRADING_ENABLED", "0") != "1":
            note = {"skipped": "KALSHI_TRADING_ENABLED is not set to 1"}
        elif signer is None:
            note = {"skipped": "no demo API key configured"}
        elif ticker not in in_scope:
            note = {"skipped": "ticker not in the collector's in-scope market set"}
        elif ticker in seen:
            note = {"skipped": "duplicate ticker in one run"}
        elif side not in ("yes", "no"):
            note = {"skipped": "side must be yes or no"}
        elif not count.is_finite() or count <= 0 or count > Decimal("250000") or count != count.quantize(Decimal("0.01")):
            note = {"skipped": "count must be positive, no greater than 250000, with at most two decimal places"}
        elif not yes_px.is_finite() or not Decimal("0") < yes_px < Decimal("1") or yes_px != yes_px.quantize(Decimal("0.0001")):
            note = {"skipped": "YES price must be between 0 and 1 with at most four decimal places"}
        elif submitted >= max_orders:
            note = {"skipped": f"max_orders_per_run ({max_orders}) reached"}
        else:
            notional = count * (yes_px if side == "yes" else Decimal("1") - yes_px)
            if spent + notional > max_notional:
                note = {"skipped": f"run notional cap ${max_notional} would be exceeded",
                        "notional": float(notional)}

        if note:
            results.append({"ticker": ticker, "side": side, "count": float(count) if count.is_finite() else None, "price": price,
                            "mode": "dry_run" if DRY_RUN else "live_demo", **note})
            continue

        # side: bid = buy YES ; ask = sell YES (economically buy NO at 1-price)
        book_side = "bid" if side == "yes" else "ask"
        order_price = yes_px
        body = {
            "ticker": ticker,
            "side": book_side,
            "count": f"{count:.2f}",
            "price": f"{order_price:.4f}",
            "time_in_force": "immediate_or_cancel",   # never rest a demo order unattended
            "self_trade_prevention_type": "taker_at_cross",
        }
        spent += notional
        submitted += 1
        seen.add(ticker)

        if DRY_RUN:
            results.append({"ticker": ticker, "side": side, "count": float(count) if count.is_finite() else None, "price": price,
                            "mode": "dry_run", "request": body,
                            "note": "validated, not sent (KALSHI_DRY_RUN=1)"})
        else:
            res = post_order(signer, body)
            res.update({"ticker": ticker, "side": side, "count": float(count) if count.is_finite() else None, "price": price,
                        "mode": "live_demo"})
            results.append(res)

    out = {
        "at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "mode": "dry_run" if DRY_RUN else "live_demo",
        "endpoint": DEMO_REST + "/portfolio/events/orders",
        "endpoint_doc": "https://docs.kalshi.com/api-reference/orders/create-order-v2.md",
        "run_notional_cap_usd": float(max_notional),
        "max_orders_per_run": max_orders,
        "planned_notional_usd": float(spent),
        "results": results,
    }
    (DATA / "executions.json").write_text(json.dumps(out, indent=1) + "\n")
    ok = sum(1 for r in results if r.get("ok"))
    skipped = sum(1 for r in results if "skipped" in r)
    print(f"execution: mode={out['mode']} sent_ok={ok} skipped={skipped} cap=${max_notional}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
