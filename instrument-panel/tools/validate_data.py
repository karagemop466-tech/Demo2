#!/usr/bin/env python3
"""Validate data/dashboard.json before it is published.

Rules enforced (build fails on any violation):
  1. Every market row has a Kalshi API source URL and a ticker.
  2. Every series row has a Kalshi API source URL (via its series query).
  3. Every numeric price copied from the API is within $0.00-$1.00.
  4. Derived money fields are consistent with their stated inputs.
  5. Rows with a price but no volume, or the reverse, keep the missing side null
     (nothing is filled in).
  6. The snapshot is recent (fails if older than 6 hours) so stale data is never
     presented as live.
"""
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data", "dashboard_instrument.json")
API_PREFIX = "https://external-api.demo.kalshi.co/trade-api/v2"
PRICE_FIELDS = ["yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars", "no_ask_dollars",
                "last_price_dollars", "previous_price_dollars"]


def num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return "unparseable"


def main():
    if not os.path.exists(DATA):
        print("FAIL: data/dashboard.json missing")
        return 1
    with open(DATA, encoding="utf-8") as fh:
        d = json.load(fh)

    errors, warnings = [], []
    checked = 0

    for tid, rows in (d.get("markets") or {}).items():
        for r in rows:
            checked += 1
            if not r.get("ticker"):
                errors.append(f"{tid}: row without ticker")
            if not str(r.get("source_url") or "").startswith(API_PREFIX):
                errors.append(f"{tid}/{r.get('ticker')}: missing Kalshi API source_url")
            for f in PRICE_FIELDS:
                v = num(r.get(f))
                if v == "unparseable":
                    errors.append(f"{tid}/{r.get('ticker')}: {f} not numeric: {r.get(f)!r}")
                elif v is not None and not (-0.0001 <= v <= 1.0001):
                    errors.append(f"{tid}/{r.get('ticker')}: {f}={v} outside 0..1")
            # derived money must equal volume * price when both inputs exist
            vol = num(r.get("volume_fp"))
            px = num(r.get("last_price_used"))
            der = r.get("notional_lifetime_usd")
            if vol is not None and px is not None and der is not None:
                if abs(vol * px - der) > 0.01:
                    errors.append(f"{tid}/{r.get('ticker')}: notional mismatch {vol}*{px}!={der}")
            if (vol is None) != (px is None):
                if der is not None:
                    errors.append(f"{tid}/{r.get('ticker')}: derived value present without both inputs")

    for r in d.get("resolved") or []:
        checked += 1
        if not str(r.get("source_url") or "").startswith(API_PREFIX):
            errors.append(f"resolved/{r.get('ticker')}: missing Kalshi API source_url")
        if (r.get("result") or "") not in ("yes", "no", "scalar", ""):
            errors.append(f"resolved/{r.get('ticker')}: unexpected result {r.get('result')!r}")

    for s in d.get("series") or []:
        checked += 1
        if not s.get("ticker"):
            errors.append("series row without ticker")
        if not str(s.get("source_url") or "").startswith(API_PREFIX):
            errors.append(f"series/{s.get('ticker')}: missing Kalshi API source_url")
        if not (s.get("settlement_sources") or []):
            warnings.append(f"series {s.get('ticker')}: no settlement source returned by API")
        invalid_terms = s.get("contract_terms_url_unverified")
        if invalid_terms:
            warnings.append(f"series {s.get('ticker')}: invalid contract-terms URL left blank: {invalid_terms}")

    for t, ob in (d.get("orderbooks") or {}).items():
        for side in ("yes_dollars", "no_dollars"):
            for lvl in ob.get(side) or []:
                if len(lvl) != 2:
                    errors.append(f"orderbook {t}/{side}: level not [price,count]")
                    continue
                p = num(lvl[0])
                if p == "unparseable" or (p is not None and not (0 <= p <= 1)):
                    errors.append(f"orderbook {t}/{side}: bad price {lvl[0]!r}")

    gen = d.get("meta", {}).get("generated_epoch")
    if gen:
        age_h = (time.time() - gen) / 3600
        if age_h > 6:
            errors.append(f"snapshot is {age_h:.1f}h old (limit 6h); refusing to publish stale data")
    else:
        errors.append("meta.generated_epoch missing")

    # A resolved-market block that returns nothing is a bug, not a quiet day: Kalshi's demo
    # exchange always lists settled markets. Fail loudly instead of publishing a zero.
    if not (d.get("resolved") or []):
        errors.append("no resolved markets collected - the settled-market query is broken, "
                      "do not publish a dashboard with an empty resolutions page")
    for tid, n in (d.get("markets") or {}).items():
        if not n:
            warnings.append(f"topic {tid}: no open markets matched its scope queries")

    if d.get("health", {}).get("exchange_status_http") != 200:
        warnings.append("exchange/status was not 200 during collection")

    print(f"rows checked: {checked}")
    print(f"requests: {d.get('meta', {}).get('https_requests')}  errors: {len(d.get('meta', {}).get('request_errors') or [])}")
    for w in warnings[:10]:
        print("WARN:", w)
    if errors:
        print("ERRORS:")
        for e in errors[:40]:
            print(" ", e)
        return 1
    print("OK: data is sourced, price fields are in range, derived values reconcile, snapshot is fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
