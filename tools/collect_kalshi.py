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
import concurrent.futures
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

    def get_many(self, jobs, workers=8):
        """Run a list of (url, note) requests concurrently.

        Used for the per-series market lookups: the demo environment has a few
        hundred in-scope series and each individual request is small, so a
        thread pool turns a serial hour into a couple of minutes."""
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.get, url, note): (url, note) for url, note in jobs}
            done = 0
            for fut in concurrent.futures.as_completed(futures):
                url, note = futures[fut]
                done += 1
                try:
                    results.append((url, note, fut.result()))
                except Exception as exc:  # noqa: BLE001 - recorded, not raised
                    results.append((url, note, None))
                if done % 25 == 0:
                    print("  %d/%d requests done" % (done, len(jobs)), flush=True)
        return results

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

    # 2. Official series catalogue (carries category + tags + settlement sources)
    #    Read one category at a time, in parallel: a single unfiltered call is
    #    very large, while the per-category calls are small and quick.
    cat_names = sorted(taxonomy.keys())
    jobs = [("%s/series?category=%s" % (API_BASE, urllib.parse.quote(c)), "category=%s" % c)
            for c in cat_names]
    # also ask for the whole catalogue, in case a series is not listed under
    # any published category
    jobs.append(("%s/series" % API_BASE, "all categories"))
    series_records, series_urls = [], []
    for url, note, data in c.get_many(jobs):
        if not data:
            continue
        series_urls.append(url)
        series_records.extend(data.get("series") or [])
    if not series_records:
        recs, urls = c.get_paged("/series", {}, "series", max_pages=3, note="series catalogue")
        series_records.extend(recs)
        series_urls.extend(urls)
    series_by_ticker = {}
    for s in series_records:
        t = s.get("ticker")
        if t:
            series_by_ticker[t] = s
    print("series catalogue: %d series across %d categories" % (len(series_by_ticker), len(cat_names)),
          flush=True)

    # 3. In-scope series -> every market of those series.
    #
    # The global "open markets" listing is ordered by creation time and the
    # demo environment creates markets continuously, so it has no natural end.
    # Walking it would give a truncated sample. Instead the catalogue of series
    # is read first and every in-scope series is then fetched in full, which
    # gives complete coverage of the five topics.
    in_scope_series = []
    for st, info in series_by_ticker.items():
        topic, basis, detail = classify(info, info.get("title") or "", st)
        if topic:
            in_scope_series.append((st, topic, basis, detail))
    in_scope_series.sort()
    print("in-scope series: %d of %d" % (len(in_scope_series), len(series_by_ticker)), flush=True)

    max_series = int(os.environ.get("KALSHI_MAX_SERIES", "4000"))
    series_capped = len(in_scope_series) > max_series
    if series_capped:
        in_scope_series = in_scope_series[:max_series]
        print("WARNING: series list truncated to %d (KALSHI_MAX_SERIES)" % max_series, flush=True)

    jobs = []
    for st, topic, basis, detail in in_scope_series:
        for status in ("open", "settled"):
            url = ("%s/markets?series_ticker=%s&status=%s&limit=1000"
                   % (API_BASE, urllib.parse.quote(st), status))
            jobs.append((url, "%s %s" % (status, st)))

    open_markets, settled_markets = [], []
    series_market_urls = []
    cursors = []

    def absorb(url, note, data):
        if not data:
            return
        series_market_urls.append(url)
        batch = data.get("markets") or []
        if note.startswith("open"):
            open_markets.extend(batch)
        else:
            settled_markets.extend(batch)
        cur = data.get("cursor") or ""
        if cur:
            cursors.append((url, note, cur))

    for url, note, data in c.get_many(jobs):
        absorb(url, note, data)

    # a series with more than 1,000 markets is continued with its cursor
    round_no = 0
    while cursors and round_no < 4:
        round_no += 1
        more = []
        for url, note, cur in cursors:
            sep = "&" if "?" in url else "?"
            more.append((url + sep + "cursor=" + urllib.parse.quote(cur), note))
        cursors = []
        print("  follow-up round %d for %d series" % (round_no, len(more)), flush=True)
        for url, note, data in c.get_many(more):
            absorb(url, note, data)

    def dedupe(rows):
        seen = set()
        out = []
        for m in rows:
            t = m.get("ticker")
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(m)
        return out

    open_markets = dedupe(open_markets)
    settled_markets = dedupe(settled_markets)
    print("markets: open=%d settled=%d" % (len(open_markets), len(settled_markets)), flush=True)

    # 5. Open events (paginated) - event level category, volume, liquidity
    events, event_urls = c.get_paged(
        "/events", {"status": "open", "limit": 200}, "events", max_pages=6,
        note="open events, first pages",
    )
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
            "in_scope_series": len(in_scope_series),
            "series_list_capped": series_capped,
            "coverage": "every market of every in-scope series (category/tag match against the official taxonomy)",
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
    dump("markets_open.json", {"source_urls": series_market_urls, "collected_at": started,
                                "rows": open_rows})
    dump("markets_settled.json", {"source_urls": series_market_urls, "collected_at": started,
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
