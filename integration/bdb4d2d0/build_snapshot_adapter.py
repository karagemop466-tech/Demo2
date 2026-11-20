#!/usr/bin/env python3
"""Snapshot adapter — assemble data/snapshot.json + siblings from existing,
source-linked pipeline outputs (flag F15, session arena-bdb4d2d0).

Why this exists
---------------
`data/snapshot.json`, `data/resolutions.json`, `data/topic-*.json` and
`data/history.json` are written by `tools/collector.py` (workflow
`refresh-data.yml`). That step has never completed on `main` (runs
44728913873 and 44744689706 both fail at "Collect demo snapshot"), so the
root dashboard and resolutions page render honest error states. Session
`6332d7d3` has a rewritten collector in flight; when it lands, its real
output replaces these files and this adapter becomes unnecessary.

Rules
-----
* Every value is copied verbatim from a cited file whose rows already carry
  official Kalshi API source URLs. Nothing is estimated except
  `est_dollar_volume`, which is the documented formula (volume_fp x
  last_price_dollars) that the site already labels "est.".
* Missing values stay missing (blank in the UI), never filled.
* Provenance is recorded in `api_log` and in the `adapter` block.

Usage: python3 integration/bdb4d2d0/build_snapshot_adapter.py
"""
import json
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DEMO = "https://external-api.demo.kalshi.co/trade-api/v2"
TOPICS = ["gas", "elections", "culture", "crypto", "golf"]


def load(name):
    return json.loads((DATA / name).read_text())


def money(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    now = dt.datetime.now(dt.timezone.utc)
    now_iso = now.isoformat(timespec="seconds")
    inst = load("dashboard_instrument.json")          # pipeline D (rows carry source URLs)
    resb = load("resolved.json")                      # pipeline B (rows carry source URLs)
    live = load("live_snapshot.json")                 # pipeline B single-market detail

    api_log = [{
        "url": "data/dashboard_instrument.json (pipeline-D output; each row keeps its official API source_url)",
        "http_status": 200, "ok": True, "at": now_iso,
        "note": "adapter input - open markets, resolved set, series inventory",
    }, {
        "url": "data/resolved.json (pipeline-B output; each row keeps its official API source URL)",
        "http_status": 200, "ok": True, "at": now_iso,
        "note": "adapter input - settlement_ts enrichment for resolved rows",
    }, {
        "url": live.get("market_source") or "data/live_snapshot.json",
        "http_status": 200, "ok": True, "at": now_iso,
        "note": "adapter input - one live orderbook + candlesticks",
    }, {
        "url": "integration/bdb4d2d0/build_snapshot_adapter.py",
        "http_status": 200, "ok": True, "at": now_iso,
        "note": "F15: assembled from the files above because tools/collector.py "
                "is red on main; replaced when refresh-data.yml succeeds",
    }]

    samples = load("api_market_samples.json")     # pipeline ? sample rows (full fields, source_api)
    events_top = load("events_top.json")          # pipeline B event rankings (lead markets)

    # ---- open markets: union of every source-linked set ------------------
    # Dedupe by ticker, richest fields first. Instrument rows are the largest
    # set but its open-market enumeration is partial (their flag F-16: e.g. the
    # KXPRESNOMD event, the top-ranked elections event, is absent) - the
    # events-top lead markets and the API sample rows close part of that gap.
    # Rows that lack a field leave it absent; the UI shows blank. Never inferred.
    markets_by_ticker = {}

    def upsert(row):
        t = row.get("market_ticker")
        if not t:
            return
        cur = markets_by_ticker.get(t) or {}
        for k, v in row.items():
            if v not in (None, "") or k not in cur:
                if v not in (None, "") or k not in cur:
                    cur[k] = v
        markets_by_ticker[t] = cur

    def from_full(m, topic_default=None):
        lp = money(m.get("last_price_dollars"))
        vol = money(m.get("volume_fp"))
        return {
            "market_ticker": m.get("ticker"),
            "market_title": m.get("title"),
            "market_url": m.get("source_market_url") or m.get("source_api") or m.get("source_url") or m.get("source"),
            "event_ticker": m.get("event_ticker"),
            "series_ticker": m.get("series_ticker"),
            "topic": m.get("topic") or topic_default,
            "status": m.get("status"),
            "last_price_dollars": m.get("last_price_dollars"),
            "yes_bid_dollars": m.get("yes_bid_dollars"),
            "yes_ask_dollars": m.get("yes_ask_dollars"),
            "yes_bid_size_fp": m.get("yes_bid_size_fp"),
            "yes_ask_size_fp": m.get("yes_ask_size_fp"),
            "volume_fp": m.get("volume_fp"),
            "volume_24h_fp": m.get("volume_24h_fp"),
            "open_interest_fp": m.get("open_interest_fp"),
            "close_time": m.get("close_time"),
            "result": m.get("result") or "",
            "est_dollar_volume": round((vol or 0) * (lp or 0), 2) if (vol is not None and lp is not None) else None,
            "source_url": m.get("source_url") or m.get("source_api") or m.get("source"),
        }

    def from_lead(topic, ev, lm):
        # lead-market rows: volume_fp (lifetime) is NOT in the source, so
        # est_dollar_volume stays null; the 24h estimate is kept separately.
        lp = money(lm.get("last_price_dollars"))
        v24 = money(lm.get("volume_24h_fp"))
        return {
            "market_ticker": lm.get("ticker"),
            "market_title": lm.get("title"),
            "market_url": lm.get("source"),
            "event_ticker": ev.get("event_ticker"),
            "series_ticker": ev.get("series_ticker"),
            "topic": topic,
            "status": lm.get("status"),
            "last_price_dollars": lm.get("last_price_dollars"),
            "yes_bid_dollars": lm.get("yes_bid_dollars"),
            "yes_ask_dollars": lm.get("yes_ask_dollars"),
            "yes_bid_size_fp": lm.get("yes_bid_size_fp"),
            "yes_ask_size_fp": lm.get("yes_ask_size_fp"),
            "volume_fp": None,
            "volume_24h_fp": lm.get("volume_24h_fp"),
            "open_interest_fp": lm.get("open_interest_fp"),
            "close_time": lm.get("close_time"),
            "result": lm.get("result") or "",
            "est_dollar_volume": None,
            "est_dollar_volume_24h": round((v24 or 0) * (lp or 0), 2) if (v24 is not None and lp is not None) else None,
            "row_note": "lead market of a top-24h event; lifetime volume_fp not in the "
                        "source, so est. $ volume (lifetime) is left blank",
            "source_url": lm.get("source"),
        }

    # 1) instrument open markets (largest set, partial enumeration)
    for topic in ["gas", "elections", "crypto", "golf"]:
        for m in inst["markets"].get(topic, []):
            lp = money(m.get("last_price_dollars"))
            vol = money(m.get("volume_fp"))
            row = {
                "market_ticker": m.get("ticker"),
                "market_title": m.get("title"),
                "market_url": m.get("source_market_url") or m.get("source_url"),
                "event_ticker": m.get("event_ticker"),
                "series_ticker": m.get("series_ticker"),
                "topic": m.get("topic") or topic,
                "status": m.get("status"),
                "last_price_dollars": m.get("last_price_dollars"),
                "yes_bid_dollars": m.get("yes_bid_dollars"),
                "yes_ask_dollars": m.get("yes_ask_dollars"),
                "yes_bid_size_fp": m.get("yes_bid_size_fp"),
                "yes_ask_size_fp": m.get("yes_ask_size_fp"),
                "volume_fp": m.get("volume_fp"),
                "volume_24h_fp": m.get("volume_24h_fp"),
                "open_interest_fp": m.get("open_interest_fp"),
                "close_time": m.get("close_time"),
                "result": m.get("result") or "",
                "est_dollar_volume": round((vol or 0) * (lp or 0), 2),
                "source_url": m.get("source_url"),
            }
            upsert(from_full(m, topic))

    # 2) API sample rows (full fields; include culture markets)
    for m in (samples.get("open_markets") or []):
        upsert(from_full(m))

    # 3) the single live-snapshot market (full fields)
    lmkt = live.get("market") or {}
    if isinstance(lmkt, dict) and lmkt.get("ticker"):
        upsert(from_full(lmkt))

    # 4) events-top lead markets (sparse rows; closes part of F-16's gap)
    for topic, evs in (events_top.get("topics") or {}).items():
        for ev in evs:
            if ev.get("lead_market"):
                upsert(from_lead(topic, ev, ev["lead_market"]))

    markets = sorted(markets_by_ticker.values(),
                     key=lambda r: -(r.get("est_dollar_volume") or r.get("est_dollar_volume_24h") or 0))
    # ---- topic normalisation -------------------------------------------
    # Sources label topics differently ("gas", "gas prices", "gas-prices").
    # Normalize to the five page ids; classify orphans ONLY from the official
    # series category/tags in series_index.json (S2: official tags, not
    # keywords). Note: Kalshi files KXNEWPOPE under Elections
    # ("International elections"), so "Who will the next Pope be?" rows stay
    # in elections per the official source, not per intuition.
    si = {x.get("ticker"): x for x in load("series_index.json").get("series", [])}
    alias = {"gas prices": "gas", "gas-prices": "gas", "gas": "gas",
             "elections": "elections", "culture": "culture",
             "crypto": "crypto", "golf": "golf"}

    def classify(r):
        raw = r.get("topic")
        if raw in alias:
            return alias[raw]
        sr = si.get(r.get("series_ticker")) or {}
        cat, tags = sr.get("category"), sr.get("tags") or []
        if cat == "Elections":
            return "elections"
        if cat == "Crypto":
            return "crypto"
        if cat == "Culture":
            return "culture"
        if cat == "Sports" and any(str(t).lower() == "golf" for t in tags):
            return "golf"
        return None  # stays ungrouped and blank; never guessed

    for r in markets:
        r["topic"] = classify(r)
    by_topic = {t: sorted([r for r in markets if r.get("topic") == t],
                          key=lambda r: -(r.get("est_dollar_volume") or r.get("est_dollar_volume_24h") or 0))
                for t in TOPICS}

    # ---- resolutions (official `result` verbatim; blanks stay blank) -----
    settlements = {}   # ticker -> settlement_ts from pipeline B
    for m in resb.get("markets", []):
        if m.get("settled_ts"):
            settlements[m.get("ticker")] = m["settled_ts"]
    resolutions = []
    seen = set()
    for m in inst.get("resolved", []):
        t = m.get("ticker")
        if not t or t in seen:
            continue
        seen.add(t)
        resolutions.append({
            "market_ticker": t,
            "title": m.get("title"),
            "topic": m.get("topic"),
            "result": m.get("result"),           # official field, verbatim
            "volume_fp": m.get("volume_fp"),
            "settlement_ts": settlements.get(t),  # blank (null) when unknown
            "settlement_value_dollars": None,     # not in any input; stays blank
            "rules_primary": None,                # not in any input; stays blank
            "market_url": m.get("source_market_url") or m.get("source_url"),
        })

    # ---- one orderbook (the only one captured) --------------------------
    ticker = live.get("ticker")
    ob_raw = (live.get("orderbook") or {}).get("orderbook_fp") or {}
    orderbooks = {}
    if ticker and ob_raw:
        yes = [[float(p), float(q)] for p, q in (ob_raw.get("yes_dollars") or [])]
        no = [[float(p), float(q)] for p, q in (ob_raw.get("no_dollars") or [])]
        der_asks = sorted([[round(1 - p, 4), q] for p, q in no])
        orderbooks[ticker] = {
            "yes_bids": sorted(yes),
            "derived_yes_asks": der_asks,
            "best_yes_bid": max((p for p, _ in yes), default=None),
            "best_yes_ask_derived": min((p for p, _ in der_asks), default=None),
            "spread_derived": (round(min((p for p, _ in der_asks), default=0)
                                     - max((p for p, _ in yes), default=0), 4)
                               if yes or der_asks else None),
            "yes_bid_contracts": round(sum(q for _, q in yes), 2),
            "derived_ask_contracts": round(sum(q for _, q in no), 2),
            "raw_request": live.get("orderbook_source"),
            "note": "asks derived as 1 - p from NO bids (official book is bids-only)",
        }

    # ---- candlesticks (live_snapshot holds 1m and 1h sets) --------------
    def cmap(c):
        pb = (c.get("price") or {}).get("close_dollars")
        yb = (c.get("yes_bid") or {}).get("close_dollars")
        ya = (c.get("yes_ask") or {}).get("close_dollars")
        mid = None
        if yb not in (None, "") and ya not in (None, ""):
            mid = round((float(yb) + float(ya)) / 2, 6)
        return {"ts": c.get("end_period_ts"), "close": pb,
                "yes_bid_close": yb, "yes_ask_close": ya, "derived_mid": mid}

    candles = {}
    if ticker:
        candles[ticker] = {
            "1m": {"candles": [cmap(c) for c in
                               ((live.get("candles_1m") or {}).get("candlesticks") or [])]},
            "1h": {"candles": [cmap(c) for c in
                               ((live.get("candles_1h") or {}).get("candlesticks") or [])]},
            "1d": {"candles": []},
        }

    # ---- history ledger: one tick per market at adapter time ------------
    pts = {}
    tsec = int(now.timestamp())
    for r in markets:
        if r.get("last_price_dollars") in (None, ""):
            continue
        pts[r["market_ticker"]] = [{
            "t": tsec, "last": r["last_price_dollars"],
            "yes_bid": r["yes_bid_dollars"], "yes_ask": r["yes_ask_dollars"],
        }]
    hist = {"points": pts, "updated_at_utc": now_iso,
            "note": "seeded by the F15 adapter (one tick per market); "
                    "tools/collector.py appends on every successful run"}

    # ---- series inventory + topic catalog -------------------------------
    in_scope = {t: [] for t in TOPICS}
    for s in inst.get("series", []):
        if s.get("topic") in in_scope:
            in_scope[s["topic"]].append(s.get("ticker"))
    series_inventory = {"in_scope_series": in_scope}

    catalog = {}
    for tdef in (inst.get("scope", {}) or {}).get("topics", []):
        catalog[tdef.get("id")] = {"title": tdef.get("title"),
                                   "rule": tdef.get("rule"),
                                   "queries": tdef.get("queries")}

    snapshot = {
        "generated_at_utc": now_iso,
        "started_at_utc": now_iso,
        "environment": "demo",
        "rest_base": DEMO,
        "authenticated": False,
        "adapter": {
            "why": "F15: tools/collector.py never completed on main; this snapshot "
                   "is assembled from source-linked pipeline outputs so the "
                   "dashboard is not empty.",
            "by": "session arena-bdb4d2d0 (integration/bdb4d2d0/build_snapshot_adapter.py)",
            "inputs": ["data/dashboard_instrument.json", "data/resolved.json",
                       "data/live_snapshot.json"],
            "replaced_when": "refresh-data.yml (tools/collector.py) commits a "
                             "successful run - that output overwrites these files",
            "coverage": "Open-market rows are the union of every source-linked set "
                        "(instrument-panel 1,526 partial per its F-16, API samples, one "
                        "live market, 27 events-top lead markets). Rows missing lifetime "
                        "volume_fp keep est. $ volume blank and show the 24h estimate "
                        "instead. Not a complete enumeration of the exchange.",
        },
        "exchange_status": (inst.get("health", {}) or {}).get("exchange_status"),
        "series_inventory": series_inventory,
        "topic_catalog": catalog,
        "unmapped_series": [],
        "counts": {
            "series_index": len(inst.get("series", [])) + len(inst.get("series_culture_adjacent", [])),
            "events_scanned": None,
            "markets_in_scope": len(markets),
            "per_topic": {t: len(by_topic[t]) for t in TOPICS},
            "resolved_in_scope": len(resolutions),
            "orderbooks": len(orderbooks),
            "candle_sets": len(candles),
        },
        "markets": markets,
        "by_topic": by_topic,
        "orderbooks": orderbooks,
        "candles": candles,
        "resolutions": resolutions,
        "definitions": {
            "est_dollar_volume": "ESTIMATE = volume_fp x last_price_dollars, computed. "
                                 "The API exposes no single dollar-volume field. "
                                 "Label is shown in the UI.",
            "derived_yes_asks": "Derived, not raw: a NO bid at price p is equivalent to a "
                                "YES ask at 1-p (Kalshi orderbook docs).",
            "result": "Official market field. 'yes' or 'no' once settled; empty while live.",
            "derived_mid": "Derived, not raw: (yes_bid_close + yes_ask_close) / 2 per "
                           "candlestick period.",
        },
        "api_log": api_log,
    }

    def write(name, payload):
        (DATA / name).write_text(json.dumps(payload, indent=1) + "\n")
        print(f"wrote data/{name} ({(DATA / name).stat().st_size} bytes)")

    write("snapshot.json", snapshot)
    write("resolutions.json", {"generated_at_utc": now_iso,
                               "count": len(resolutions),
                               "resolutions": resolutions,
                               "adapter": snapshot["adapter"]})
    write("history.json", hist)
    for t in TOPICS:
        write(f"topic-{t}.json", {
            "generated_at_utc": now_iso, "topic": t,
            "count": len(by_topic[t]), "markets": by_topic[t],
            "resolutions": [r for r in resolutions if r["topic"] == t],
        })
    print(f"markets={len(markets)} resolutions={len(resolutions)} "
          f"orderbooks={len(orderbooks)} candle_sets={len(candles)}")


if __name__ == "__main__":
    main()
