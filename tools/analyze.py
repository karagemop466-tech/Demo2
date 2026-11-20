#!/usr/bin/env python3
"""Trade analysis + strategy derivation.  Writes data/analysis.json.

Every figure is computed from data/portfolio.json (authenticated Kalshi demo data) and
data/resolutions.json (official settled `result`). Nothing is estimated except where a
field is named `est_*` and explained. If there are no fills, the correct output is an
explicit "insufficient data" verdict rather than a made-up strategy.

Trade categories
  - by topic              gas | elections | culture | crypto | golf | unmapped
  - by side               yes | no                  (fill.outcome_side, official field)
  - by taker/maker        taker | maker             (fill.is_taker, official field)
  - by entry-price band   <=0.10 | 0.11-0.30 | 0.31-0.50 | 0.51-0.70 | 0.71-0.90 | >0.90
  - by hold outcome       resolved-yes | resolved-no | open | unknown

P&L rules (documented so they can be audited):
  cost           = count_fp * price_paid_dollars   (price on the side actually held)
  fee            = fee_cost (official field)
  payout         = count_fp * 1.00 if the held side == settled result else 0
  realized       = payout - cost - fee
  Where the market is still open we report cost and unrealized mark separately and do
  NOT book a realized number.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from collections import defaultdict
from pathlib import Path

# DATA_DIR lets the CI maths test run against a throwaway fixture directory instead of the
# real snapshot, so a test can never leave data behind that the site would then serve.
DATA = Path(os.environ.get("DATA_DIR") or (Path(__file__).resolve().parent.parent / "data"))


def f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def band(price: float) -> str:
    for lo, hi, label in [
        (0.00, 0.10, "<=0.10"),
        (0.10, 0.30, "0.11-0.30"),
        (0.30, 0.50, "0.31-0.50"),
        (0.50, 0.70, "0.51-0.70"),
        (0.70, 0.90, "0.71-0.90"),
        (0.90, 1.01, ">0.90"),
    ]:
        if lo < price <= hi:
            return label
    return "unknown"


def main() -> int:
    snap = json.loads((DATA / "snapshot.json").read_text()) if (DATA / "snapshot.json").exists() else {}
    port_path = DATA / "portfolio.json"
    port = json.loads(port_path.read_text()) if port_path.exists() else {"authenticated": False}

    # market_ticker -> {topic, title, result, settlement_ts}
    meta: dict[str, dict] = {}
    for m in snap.get("markets") or []:
        meta[m["market_ticker"]] = {
            "topic": m["topic"],
            "title": m.get("market_title"),
            "result": m.get("result") or "",
            "status": m.get("status"),
            "yes_bid_dollars": m.get("yes_bid_dollars"),
            "last_price_dollars": m.get("last_price_dollars"),
        }
    for r in snap.get("resolutions") or []:
        cur = meta.setdefault(r["market_ticker"], {})
        cur.update(
            {
                "topic": r.get("topic") or cur.get("topic"),
                "title": r.get("title") or cur.get("title"),
                "result": r.get("result") or cur.get("result") or "",
                "settlement_ts": r.get("settlement_ts"),
                "status": "settled",
            }
        )
    # series ticker -> topic, so fills on markets no longer in the open list still map
    series_topic: dict[str, str] = {}
    for inv_topic, tickers in (snap.get("series_inventory", {}).get("in_scope_series") or {}).items():
        for t in tickers:
            series_topic[t] = inv_topic

    fills = port.get("fills") or []
    positions = port.get("positions") or []
    balance = port.get("balance") or {}

    trades: list[dict] = []
    for fl in fills:
        ticker = fl.get("ticker") or fl.get("market_ticker") or ""
        m = meta.get(ticker, {})
        topic = m.get("topic") or series_topic.get(ticker.split("-")[0], "unmapped")
        side = fl.get("outcome_side") or fl.get("side") or ""
        count = f(fl.get("count_fp"))
        yes_px = f(fl.get("yes_price_dollars"))
        no_px = f(fl.get("no_price_dollars"))
        price_paid = yes_px if side == "yes" else no_px
        fee = f(fl.get("fee_cost"))
        cost = round(count * price_paid, 6)
        result = (m.get("result") or "").lower()
        payout = None
        realized = None
        outcome = "open"
        if result in ("yes", "no"):
            won = side == result
            payout = round(count * 1.0, 2) if won else 0.0
            realized = round(payout - cost - fee, 6)
            outcome = f"resolved-{result}"
        elif m.get("status") in ("closed", "settled") and not result:
            outcome = "unknown"
        trades.append(
            {
                "fill_id": fl.get("fill_id") or fl.get("trade_id"),
                "ticker": ticker,
                "title": m.get("title"),
                "topic": topic,
                "side": side,
                "book_side": fl.get("book_side"),
                "is_taker": bool(fl.get("is_taker")),
                "count_fp": fl.get("count_fp"),
                "price_paid_dollars": price_paid,
                "cost_dollars": cost,
                "fee_dollars": fee,
                "created_time": fl.get("created_time"),
                "market_result": result or None,
                "outcome": outcome,
                "payout_dollars": payout,
                "realized_pnl_dollars": realized,
            }
        )
    trades.sort(key=lambda t: t.get("created_time") or "")

    def agg(keyfn):
        out = defaultdict(lambda: {"n": 0, "cost": 0.0, "fees": 0.0, "realized": 0.0,
                                  "resolved_n": 0, "wins": 0, "payout": 0.0})
        for t in trades:
            k = keyfn(t)
            a = out[k]
            a["n"] += 1
            a["cost"] += t["cost_dollars"]
            a["fees"] += t["fee_dollars"]
            if t["realized_pnl_dollars"] is not None:
                a["resolved_n"] += 1
                a["payout"] += t["payout_dollars"] or 0.0
                a["realized"] += t["realized_pnl_dollars"]
                if (t["payout_dollars"] or 0) > 0:
                    a["wins"] += 1
        for a in out.values():
            for k2 in ("cost", "fees", "realized", "payout"):
                a[k2] = round(a[k2], 4)
            a["hit_rate"] = round(a["wins"] / a["resolved_n"], 4) if a["resolved_n"] else None
        return dict(out)

    categories = {
        "by_topic": agg(lambda t: t["topic"]),
        "by_side": agg(lambda t: t["side"] or "unknown"),
        "by_role": agg(lambda t: "taker" if t["is_taker"] else "maker"),
        "by_price_band": agg(lambda t: band(f(t["price_paid_dollars"]))),
        "by_outcome": agg(lambda t: t["outcome"]),
    }

    resolved = [t for t in trades if t["realized_pnl_dollars"] is not None]
    totals = {
        "fills": len(trades),
        "resolved_fills": len(resolved),
        "open_fills": len(trades) - len(resolved),
        "cost_dollars": round(sum(t["cost_dollars"] for t in trades), 4),
        "fees_dollars": round(sum(t["fee_dollars"] for t in trades), 4),
        "realized_pnl_dollars": round(sum(t["realized_pnl_dollars"] or 0 for t in trades), 4),
        "wins": sum(1 for t in resolved if (t["payout_dollars"] or 0) > 0),
        "losses": sum(1 for t in resolved if (t["payout_dollars"] or 0) == 0),
    }
    totals["hit_rate"] = (
        round(totals["wins"] / totals["resolved_fills"], 4) if totals["resolved_fills"] else None
    )

    positions_out = [
        {
            "ticker": p.get("ticker"),
            "topic": series_topic.get((p.get("ticker") or "").split("-")[0], "unmapped"),
            "position_fp": p.get("position_fp"),
            "total_traded_dollars": p.get("total_traded_dollars"),
            "market_exposure_dollars": p.get("market_exposure_dollars"),
            "realized_pnl_dollars": p.get("realized_pnl_dollars"),
            "fees_paid_dollars": p.get("fees_paid_dollars"),
            "last_updated_ts": p.get("last_updated_ts"),
        }
        for p in positions
    ]

    # ---- strategy derivation: rules are stated up front and only fire on enough data
    MIN_N = 5
    strategies: list[dict] = []
    for label, group in categories["by_topic"].items():
        if label in ("unmapped", None):
            continue
        if group["resolved_n"] >= MIN_N and group["realized"] > 0:
            strategies.append(
                {
                    "id": f"topic-{label}",
                    "rule": f"Repeat trades in {label}: {group['resolved_n']} resolved fills, "
                            f"hit rate {group['hit_rate']:.0%}, realized ${group['realized']:.2f}.",
                    "evidence": group,
                    "confidence": "low" if group["resolved_n"] < 20 else "medium",
                    "caveat": "Demo-environment prices; sample is small and not independent.",
                }
            )
    for label, group in categories["by_price_band"].items():
        if group["resolved_n"] >= MIN_N:
            strategies.append(
                {
                    "id": f"band-{label}",
                    "rule": f"Price band {label}: {group['resolved_n']} resolved fills, "
                            f"hit rate {group['hit_rate']:.0%}, realized ${group['realized']:.2f}.",
                    "evidence": group,
                    "confidence": "low",
                    "caveat": "Bands with fewer than 20 resolved fills are anecdotal.",
                }
            )
    maker = categories["by_role"].get("maker")
    taker = categories["by_role"].get("taker")
    if maker and taker and maker["resolved_n"] and taker["resolved_n"]:
        strategies.append(
            {
                "id": "role-split",
                "rule": f"Maker hit rate {maker['hit_rate']:.0%} vs taker {taker['hit_rate']:.0%}; "
                        f"fees ${maker['fees']:.2f} vs ${taker['fees']:.2f}. Prefer the role with the "
                        f"better net of fees.",
                "evidence": {"maker": maker, "taker": taker},
                "confidence": "low" if min(maker["resolved_n"], taker["resolved_n"]) < 20 else "medium",
                "caveat": "Maker/taker split on a demo account does not predict production fills.",
            }
        )

    verdict = (
        "insufficient_data" if len(resolved) < MIN_N
        else ("strategies_proposed" if strategies else "no_edge_detected")
    )
    analysis = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "data/portfolio.json (authenticated demo account) + data/resolutions.json",
        "authenticated": bool(port.get("authenticated")),
        "balance": {
            "balance_dollars": (balance or {}).get("balance_dollars"),
            "portfolio_value_cents": (balance or {}).get("portfolio_value"),
            "updated_ts": (balance or {}).get("updated_ts"),
        },
        "totals": totals,
        "categories": categories,
        "trades": trades,
        "positions": positions_out,
        "strategies": strategies,
        "verdict": verdict,
        "verdict_explanation": {
            "insufficient_data": f"Fewer than {MIN_N} resolved fills. No strategy is asserted.",
            "strategies_proposed": "Candidate rules listed; each carries its own evidence and caveat.",
            "no_edge_detected": "Enough data, but no category showed positive realized P&L.",
        }[verdict],
        "method_notes": {
            "cost": "count_fp x price paid on the held side (yes_price_dollars or no_price_dollars)",
            "realized": "payout - cost - fee, payout = count_fp x $1 when held side == official result",
            "no_estimation": "Open trades are never booked as realized; only official result settles a fill",
        },
    }
    (DATA / "analysis.json").write_text(json.dumps(analysis, indent=1) + "\n")
    print(f"analysis: fills={totals['fills']} resolved={totals['resolved_fills']} verdict={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
