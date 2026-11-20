#!/usr/bin/env python3
"""Collect verified Kalshi DEMO market data and write it to data/.

Runs on GitHub Actions (the runner has outbound internet access) and can also be
run locally by anyone with network access:

    python3 tools/collect_kalshi.py --out data

Every HTTP request made is recorded in data/collection_log.json with its exact
URL, status code, timestamp and record count.  Each stored record keeps the
`source_url` of the response it came from, so every table row on the site can
link back to the official Kalshi API response it was read from.

Scope is limited to five topics: gas prices, elections, culture, crypto, golf.
Nothing is inferred: if a field is absent from an API response it is stored as
an empty string and the site renders it blank and flags it as unverified.
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API_BASE = "https://external-api.demo.kalshi.co/trade-api/v2"
DOC_BASE = "https://docs.kalshi.com"
UA = "kalshi-demo-dashboard/1.0 (+https://github.com/karagemop466-tech/Demo2)"

# --------------------------------------------------------------------------
# Topic scope rules.
#
# `series_categories` / `series_tags` come from the official Kalshi taxonomy
# (https://external-api.demo.kalshi.co/trade-api/v2/search/tags_by_categories)
# applied to the `category` and `tags` fields of the official /series endpoint.
# `title_keywords` is a clearly-labelled fallback for markets that carry no
# series metadata; rows matched that way are flagged as heuristic.
# --------------------------------------------------------------------------
TOPIC_RULES = {
    "gas-prices": {
        "label": "Gas prices",
        "series_categories": ["Commodities", "Economics"],
        "series_tags_any": ["Oil & Gas", "Oil and energy"],
        "title_keywords": [
            "gasoline", "gas price", "gas prices", "diesel", "heating oil",
            "crude oil", "crude", "wti", "brent", "gas tax", "gasoline price",
        ],
    },
    "elections": {
        "label": "Elections",
        "series_categories": ["Elections"],
        "series_tags_any": [],
        "title_keywords": [
            "election", "elections", "primary", "ballot", "nominee", "nominations",
            "senate", "governor", "house control", "presidential winner",
            "mayor", "referendum", "vote for",
        ],
    },
    "culture": {
        "label": "Culture",
        "series_categories": ["Entertainment", "Culture"],
        "series_tags_any": [
            "Movies", "Music", "Awards", "Television", "People", "Music charts",
            "Video games", "Live Music", "Reality TV", "Oscars", "Grammys",
            "Critics Choice Awards", "Golden Globes", "The Game Awards", "Art",
            "Food", "Music Streams", "Movie Charts", "TV Charts", "Achievements",
            "Collectibles", "Music Industry", "Rotten Tomatoes", "Views",
            "Dancing with the Stars", "The Voice", "Pokémon", "Singles",
            "Streamer Awards", "New Music", "Live Music",
        ],
        "title_keywords": [
            "oscar", "oscars", "grammy", "grammys", "emmy", "emmys", "box office",
            "movie", "film", "music", "album", "celebrity", "tv show", "netflix",
            "spotify", "billboard", "hollywood", "met gala", "golden globe",
            "super bowl halftime", "album of the year", "song of the year",
        ],
    },
    "crypto": {
        "label": "Crypto",
        "series_categories": ["Crypto"],
        "series_tags_any": [],
        "title_keywords": [
            "bitcoin", "btc", "ethereum", "ether", "eth price", "crypto",
            "solana", "sol price", "doge", "dogecoin", "xrp", "zec", "bnb",
        ],
    },
    "golf": {
        "label": "Golf",
        "series_categories": [],
        "series_tags_any": ["Golf"],
        "title_keywords": [
            "golf", "pga", "masters", "ryder cup", "lpga", "us open golf",
            "open championship", "the open", "golfers",
        ],
    },
}

# Markets that are structurally not tradeable in-scope contracts.
SKIP_TICKER_PREFIX = ("KXMVECROSSCATEGORY", "KXMVE")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Collector:
    def __init__(self):
        self.log = []
        self.ctx = ssl.create_default_context()

    def get(self, url, note=""):
        """GET a URL, record the attempt, return parsed JSON or None."""
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        entry = {
            "url": url,
            "note": note,
            "requested_at": now_iso(),
            "status": None,
            "records": None,
            "error": None,
        }
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60, context=self.ctx) as resp:
                    raw = resp.read().decode("utf-8")
                    entry["status"] = resp.status
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        entry["error"] = "response was not JSON"
                        self.log.append(entry)
                        return None
                    entry["bytes"] = len(raw)
                    self.log.append(entry)
                    return data
            except urllib.error.HTTPError as exc:
                entry["status"] = exc.code
                entry["error"] = "HTTP %s %s" % (exc.code, exc.reason)
                self.log.append(entry)
                if exc.code in (400, 401, 403, 404):
                    return None
                time.sleep(2 * (attempt + 1))
            except Exception as exc:  # noqa: BLE001 - network errors are recorded, not raised
                entry["error"] = "%s: %s" % (type(exc).__name__, exc)
                time.sleep(2 * (attempt + 1))
        self.log.append(entry)
        return None

    def get_paged(self, path, params, key, max_pages=60, note=""):
        """Follow the Kalshi cursor pagination and return (records, urls).

        Stops early if the API repeats a cursor (that means the listing is not
        advancing) and de-duplicates records by their ticker so a listing that
        shifts under a page boundary cannot create duplicates."""
        records, urls = [], []
        seen_cursor = set()
        seen_ids = set()
        cursor = ""
        for page in range(max_pages):
            q = dict(params)
            if cursor:
                q["cursor"] = cursor
            url = API_BASE + path + "?" + urllib.parse.urlencode(q)
            data = self.get(url, note=note)
            if not data:
                break
            batch = data.get(key) or []
            for item in batch:
                ident = item.get("ticker") or item.get("event_ticker") or json.dumps(item, sort_keys=True)
                if ident in seen_ids:
                    continue
                seen_ids.add(ident)
                records.append(item)
            urls.append(url)
            next_cursor = data.get("cursor") or ""
            print("  page %d: %s -> %d new records (cursor %s)"
                  % (page + 1, note or path, len(batch), (next_cursor or "none")[:12]), flush=True)
            if not next_cursor or next_cursor in seen_cursor:
                break
            seen_cursor.add(next_cursor)
            cursor = next_cursor
            time.sleep(0.1)
        return records, urls


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------
def keyword_hit(text, keywords):
    """Case-insensitive keyword match; multi-word keywords match as substrings,
    single-word keywords match on word boundaries."""
    low = re_word(text)
    for kw in keywords:
        k = kw.lower()
        if " " in k:
            if k in low:
                return kw
        elif re.search(r"\b" + re.escape(k) + r"\b", low):
            return kw
    return None


def re_word(text):
    return re.sub(r"[^a-z0-9&+.\- ]+", " ", str(text or "").lower())


def classify(series_info, title, ticker):
    """Return (topic_id, basis, detail). topic_id is None when out of scope."""
    for topic_id, rule in TOPIC_RULES.items():
        cats = series_info.get("categories") or []
        tags = series_info.get("tags") or []
        for c in rule["series_categories"]:
            if c in cats:
                return topic_id, "series_category", c
        for t in rule["series_tags_any"]:
            if t in tags:
                return topic_id, "series_tag", t
    for topic_id, rule in TOPIC_RULES.items():
        hit = keyword_hit(title + " " + (ticker or ""), rule["title_keywords"])
        if hit:
            return topic_id, "title_keyword", hit
    return None, None, None


# --------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------
def collect(out_dir):
    c = Collector()
    started = now_iso()

    # 1. Official taxonomy ------------------------------------------------
    taxonomy_url = API_BASE + "/search/tags_by_categories"
    taxonomy_raw = c.get(taxonomy_url, note="official tag taxonomy per category")
    taxonomy = (taxonomy_raw or {}).get("tags_by_categories", {})

    # 2. Official series list (carries category + tags + settlement sources)
    series_records, series_urls = c.get_paged(
        "/series", {}, "series", max_pages=3, note="series catalogue"
    )
    if not series_records:
        # Fall back to per-category queries if an unfiltered /series call fails.
        series_records, series_urls = [], []
        for cat_name in sorted(taxonomy.keys()):
            recs, urls = c.get_paged(
                "/series", {"category": cat_name}, "series", max_pages=10,
                note="series catalogue for category=%s" % cat_name,
            )
            series_records.extend(recs)
            series_urls.extend(urls)
    series_by_ticker = {}
    for s in series_records:
        t = s.get("ticker")
        if t:
            series_by_ticker[t] = s

    # 3. Open markets (paginated)
    open_markets, open_urls = c.get_paged(
        "/markets", {"status": "open", "limit": 1000}, "markets", max_pages=20,
        note="open markets, full pagination",
    )
    # 4. Settled markets (paginated) - used for resolution tracking
    settled_markets, settled_urls = c.get_paged(
        "/markets", {"status": "settled", "limit": 1000}, "markets", max_pages=20,
        note="settled markets, full pagination",
    )

    # 5. Open events (paginated) - event level category, volume, liquidity
    events, event_urls = c.get_paged(
        "/events", {"status": "open", "limit": 200}, "events", max_pages=20,
        note="open events, full pagination",
    )

    # ---------------------------------------------------------------- build
    def rows_from(markets, status):
        out = []
        for m in markets:
            ticker = m.get("ticker") or ""
            if ticker.startswith(SKIP_TICKER_PREFIX):
                continue
            st = m.get("series_ticker") or ""
            info = series_by_ticker.get(st, {})
            topic, basis, detail = classify(info, m.get("title") or "", ticker)
            if not topic:
                continue
            src = "%s/markets/%s" % (API_BASE, urllib.parse.quote(ticker))
            row = {
                "ticker": ticker,
                "event_ticker": m.get("event_ticker") or "",
                "series_ticker": st,
                "title": m.get("title") or "",
                "subtitle": m.get("subtitle") or m.get("yes_sub_title") or "",
                "topic": topic,
                "topic_label": TOPIC_RULES[topic]["label"],
                "classification_basis": basis,
                "classification_detail": detail,
                "series_category": (info.get("category") or
                                    (info.get("categories") or [""])[0]),
                "series_tags": info.get("tags") or [],
                "status": m.get("status") or status,
                "result": m.get("result") or "",
                "settlement_value_dollars": m.get("settlement_value_dollars") or "",
                "settlement_ts": m.get("settlement_ts") or "",
                "close_time": m.get("close_time") or "",
                "open_time": m.get("open_time") or "",
                "volume_fp": m.get("volume_fp") or "",
                "volume_24h_fp": m.get("volume_24h_fp") or "",
                "open_interest_fp": m.get("open_interest_fp") or "",
                "liquidity_dollars": m.get("liquidity_dollars") or "",
                "last_price_dollars": m.get("last_price_dollars") or "",
                "yes_bid_dollars": m.get("yes_bid_dollars") or "",
                "yes_ask_dollars": m.get("yes_ask_dollars") or "",
                "yes_bid_size_fp": m.get("yes_bid_size_fp") or "",
                "yes_ask_size_fp": m.get("yes_ask_size_fp") or "",
                "no_bid_dollars": m.get("no_bid_dollars") or "",
                "no_ask_dollars": m.get("no_ask_dollars") or "",
                "notional_value_dollars": m.get("notional_value_dollars") or "",
                "rules_primary": m.get("rules_primary") or "",
                "source_url": src,
                "settlement_sources": info.get("settlement_sources") or [],
                "series_title": info.get("title") or "",
            }
            try:
                vol = float(row["volume_fp"] or 0)
                price = float(row["last_price_dollars"] or 0)
                row["dollar_turnover_estimate"] = round(vol * price, 2)
            except (TypeError, ValueError):
                row["dollar_turnover_estimate"] = ""
            out.append(row)
        out.sort(key=lambda r: (-(r["dollar_turnover_estimate"] or 0), r["ticker"]))
        return out

    open_rows = rows_from(open_markets, "open")
    settled_rows = rows_from(settled_markets, "settled")
    for r in settled_rows:
        r["dollar_turnover_estimate"] = ""

    # 6. Orderbook depth for the highest-notional in-scope markets
    orderbooks = {}
    picked = []
    seen_topics = {}
    for r in open_rows:
        picked.append(r)
        seen_topics[r["topic"]] = seen_topics.get(r["topic"], 0) + 1
        if len(picked) >= 30 and all(
            seen_topics.get(t, 0) >= 3 for t in TOPIC_RULES
        ):
            break
    for r in picked:
        url = "%s/markets/%s/orderbook" % (API_BASE, urllib.parse.quote(r["ticker"]))
        data = c.get(url, note="orderbook depth")
        if not data:
            continue
        ob = data.get("orderbook_fp") or data.get("orderbook") or {}
        yes = ob.get("yes_dollars") or ob.get("yes") or []
        no = ob.get("no_dollars") or ob.get("no") or []
        orderbooks[r["ticker"]] = {
            "ticker": r["ticker"],
            "title": r["title"],
            "topic": r["topic"],
            "yes": [[str(a), str(b)] for a, b in yes],
            "no": [[str(a), str(b)] for a, b in no],
            "source_url": url,
        }
        time.sleep(0.1)

    # 7. Event level rows
    event_rows = []
    for e in events:
        et = e.get("event_ticker") or e.get("ticker") or ""
        if not et:
            continue
        st = e.get("series_ticker") or ""
        info = series_by_ticker.get(st, {})
        topic, basis, detail = classify(info, e.get("title") or "", et)
        if not topic:
            continue
        event_rows.append({
            "event_ticker": et,
            "series_ticker": st,
            "title": e.get("title") or "",
            "topic": topic,
            "topic_label": TOPIC_RULES[topic]["label"],
            "classification_basis": basis,
            "classification_detail": detail,
            "category": e.get("category") or (info.get("category") or ""),
            "status": e.get("status") or "",
            "close_time": e.get("close_time") or "",
            "volume_fp": e.get("volume_fp") or e.get("volume") or "",
            "volume_24h_fp": e.get("volume_24h_fp") or "",
            "open_interest_fp": e.get("open_interest_fp") or "",
            "liquidity_dollars": e.get("liquidity_dollars") or e.get("liquidity") or "",
            "source_url": "%s/events/%s" % (API_BASE, urllib.parse.quote(et)),
        })

    # 8. Series rows (with official settlement sources)
    series_rows = []
    for s in series_records:
        st = s.get("ticker") or ""
        info = series_by_ticker.get(st, {})
        topic, basis, detail = classify(info, s.get("title") or "", st)
        if not topic:
            continue
        series_rows.append({
            "series_ticker": st,
            "title": s.get("title") or "",
            "category": s.get("category") or "",
            "categories": s.get("categories") or [],
            "tags": s.get("tags") or [],
            "topic": topic,
            "topic_label": TOPIC_RULES[topic]["label"],
            "classification_basis": basis,
            "classification_detail": detail,
            "frequency": s.get("frequency") or "",
            "fee_type": s.get("fee_type") or "",
            "fee_multiplier": s.get("fee_multiplier") or "",
            "contract_terms_url": s.get("contract_terms_url") or "",
            "settlement_sources": s.get("settlement_sources") or [],
            "source_url": API_BASE + "/series/" + urllib.parse.quote(st),
        })

    # ---------------------------------------------------------------- write
    os.makedirs(out_dir, exist_ok=True)
    meta = {
        "collected_at": started,
        "collected_at_utc": started,
        "collector": "tools/collect_kalshi.py",
        "environment": "Kalshi DEMO",
        "api_base": API_BASE,
        "api_base_alternate": "https://demo-api.kalshi.co/trade-api/v2",
        "websocket_base": "wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2",
        "demo_env_doc": DOC_BASE + "/getting_started/demo_env",
        "api_environments_doc": DOC_BASE + "/getting_started/api_environments",
        "fixed_point_doc": DOC_BASE + "/getting_started/fixed_point_migration",
        "get_markets_doc": DOC_BASE + "/api-reference/market/get-markets",
        "get_market_doc": DOC_BASE + "/api-reference/market/get-market",
        "get_orderbook_doc": DOC_BASE + "/api-reference/market/get-market-orderbook",
        "get_events_doc": DOC_BASE + "/api-reference/events/get-events",
        "get_series_doc": DOC_BASE + "/api-reference/series/get-series",
        "taxonomy_url": taxonomy_url,
        "counts": {
            "open_markets_returned": len(open_markets),
            "settled_markets_returned": len(settled_markets),
            "events_returned": len(events),
            "series_returned": len(series_records),
            "in_scope_open": len(open_rows),
            "in_scope_settled": len(settled_rows),
            "in_scope_events": len(event_rows),
            "in_scope_series": len(series_rows),
            "orderbooks": len(orderbooks),
        },
        "scope": {k: v["label"] for k, v in TOPIC_RULES.items()},
        "scope_rules": TOPIC_RULES,
        "notes": [
            "All values are copied from Kalshi demo API responses. Missing fields stay empty.",
            "volume_fp is a contract count, not dollars.",
            "dollar_turnover_estimate = volume_fp x last_price_dollars (a computed proxy, not an official field).",
            "Kalshi states demo prices and behaviour may not reflect real markets.",
        ],
    }

    def dump(name, obj):
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, sort_keys=False)
            fh.write("\n")
        print("wrote %s" % path)

    dump("meta.json", meta)
    dump("taxonomy.json", {"source_url": taxonomy_url, "collected_at": started,
                           "tags_by_categories": taxonomy})
    dump("markets_open.json", {"source_urls": open_urls, "collected_at": started,
                                "rows": open_rows})
    dump("markets_settled.json", {"source_urls": settled_urls, "collected_at": started,
                                  "rows": settled_rows})
    dump("events_open.json", {"source_urls": event_urls, "collected_at": started,
                              "rows": event_rows})
    dump("series_scope.json", {"source_urls": series_urls, "collected_at": started,
                               "rows": series_rows})
    dump("orderbooks.json", {"collected_at": started, "rows": orderbooks})
    dump("collection_log.json", {"started_at": started, "finished_at": now_iso(),
                                 "requests": c.log})
    print("in-scope open=%d settled=%d events=%d series=%d orderbooks=%d" % (
        len(open_rows), len(settled_rows), len(event_rows), len(series_rows),
        len(orderbooks)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    return collect(args.out)


if __name__ == "__main__":
    sys.exit(main())
