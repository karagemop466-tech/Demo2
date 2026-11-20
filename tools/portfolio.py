#!/usr/bin/env python3
"""Portfolio snapshot (authenticated).  Writes data/portfolio.json.

Endpoints (verified against docs.kalshi.com, see pages/api-reference.html):
  GET /portfolio/balance    -> balance, balance_dollars, portfolio_value, updated_ts
  GET /portfolio/positions  -> market_positions[] with realized_pnl_dollars, fees_paid_dollars
  GET /portfolio/fills      -> fills[] with outcome_side, book_side, count_fp,
                               yes_price_dollars, no_price_dollars, fee_cost, is_taker

If no API key is configured we write authenticated:false and NOTHING else. We never
invent a balance, a position, or a P&L.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collector import DATA, DEMO_REST, get_json, paginate, signer_from_env, write_json, API_LOG  # noqa: E402


def main() -> int:
    signer = signer_from_env()
    if signer is None:
        write_json(
            "portfolio.json",
            {
                "authenticated": False,
                "reason": (
                    "No demo API key configured. Set repository secrets "
                    "KALSHI_DEMO_API_KEY_ID and KALSHI_DEMO_PRIVATE_KEY to enable "
                    "portfolio snapshots and trade execution."
                ),
                "documented_requirement": "https://docs.kalshi.com/getting_started/api_keys",
                "api_log": API_LOG,
            },
        )
        print("portfolio: not authenticated, wrote empty snapshot")
        return 0

    balance, bstatus = get_json(f"{DEMO_REST}/portfolio/balance", signer)
    positions = paginate(f"{DEMO_REST}/portfolio/positions?settlement_status=all",
                         "market_positions", signer, max_pages=10)
    fills = paginate(f"{DEMO_REST}/portfolio/fills", "fills", signer, max_pages=10)

    write_json(
        "portfolio.json",
        {
            "authenticated": True,
            "fetched_at_utc": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
            "balance": balance,
            "balance_http_status": bstatus,
            "positions": positions,
            "fills": fills,
            "api_log": API_LOG,
            "field_notes": {
                "balance.balance": "integer cents, official field",
                "balance.balance_dollars": "fixed-point dollar string, official field",
                "positions[].realized_pnl_dollars": "official field, locked-in P&L",
                "positions[].market_exposure_dollars": "official cost basis of remaining position",
                "fills[].outcome_side": "official: yes|no directional exposure",
                "fills[].book_side": "official: bid=buy YES, ask=sell YES",
            },
        },
    )
    print(f"portfolio: balance_http={bstatus} positions={len(positions)} fills={len(fills)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
