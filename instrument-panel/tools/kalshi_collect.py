#!/usr/bin/env python3
"""Collect verified market data from the Kalshi DEMO Trade API.

Every value written to data/dashboard.json is copied from an API response, or is
plain arithmetic over copied values. Nothing is estimated or inferred.

Run:  python3 tools/kalshi_collect.py
Writes: data/dashboard.json

Official references for every endpoint used are listed in ENDPOINTS below and are
repeated in the JSON meta block so the site can show a source for each row.
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://external-api.demo.kalshi.co/trade-api/v2"
DOCS = "https://docs.kalshi.com"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "data", "dashboard_instrument.json")

ENDPOINTS = {
    "exchange_status": f"{API}/exchange/status",
    "series_by_category": f"{API}/series?category={{category}}&limit=200",
    "series_by_tags": f"{API}/series?tags={{tags}}&limit=200",
    "events": f"{API}/events?series_ticker={{ticker}}&status={{status}}&limit=200",
    "markets": f"{API}/markets?series_ticker={{ticker}}&status={{status}}&limit=1000&mve_filter=exclude",
    "market": f"{API}/markets/{{ticker}}",
    "orderbook": f"{API}/markets/{{ticker}}/orderbook?depth={{depth}}",
    "trades": f"{API}/markets/trades?ticker={{ticker}}&limit=1000",
    "tags_by_categories": f"{API}/search/tags_by_categories",
}

DOCS = {
    "demo_env": "https://docs.kalshi.com/getting_started/demo_env",
    "get_markets": "https://docs.kalshi.com/api-reference/market/get-markets",
    "get_market": "https://docs.kalshi.com/api-reference/market/get-market",
    "get_orderbook": "https://docs.kalshi.com/api-reference/market/get-market-orderbook",
    "get_events": "https://docs.kalshi.com/api-reference/events/get-events",
    "get_series_list": "https://docs.kalshi.com/api-reference/market/get-series-list",
    "get_trades": "https://docs.kalshi.com/api-reference/market/get-trades",
    "candlesticks": "https://docs.kalshi.com/api-reference/market/get-market-candlesticks",
    "fixed_point": "https://docs.kalshi.com/getting_started/fixed_point_migration",
    "settlement": "https://docs.kalshi.com/getting_started/market_settlement",
    "historical": "https://docs.kalshi.com/getting_started/historical_data",
    "rate_limits": "https://docs.kalshi.com/getting_started/rate_limits",
}

# Scope rules. Each topic lists the exact, documented discovery query that produced
# its series. Anything not matched is out of scope and is not displayed as in-scope.
SCOPE = [
    {
        "id": "gas",
        "title": "Gas prices",
        "rule": "series tagged 'Oil and energy' under Kalshi category Economics, or whose title/ticker names gas/gasoline/diesel",
        "queries": ["category:Economics"],
        "match_tags": ["oil and energy"],
        "match_words": ["gas", "gasoline", "diesel"],
    },
    {
        "id": "elections",
        "title": "Elections",
        "rule": "series whose Kalshi discovery categories include 'Elections'",
        "queries": ["category:Elections"],
        "match_tags": [],
        "match_words": [],
    },
    {
        "id": "culture",
        "title": "Culture",
        "rule": "series whose Kalshi discovery categories include 'Culture'",
        "queries": ["category:Culture"],
        "match_tags": [],
        "match_words": [],
    },
    {
        "id": "crypto",
        "title": "Crypto",
        "rule": "series whose Kalshi discovery categories include 'Crypto'",
        "queries": ["category:Crypto"],
        "match_tags": [],
        "match_words": [],
    },
    {
        "id": "golf",
        "title": "Golf",
        "rule": "series carrying the Kalshi tag 'Golf' (a tag under the Sports category)",
        "queries": ["tags:Golf"],
        "match_tags": [],
        "match_words": [],
    },
]

# Culture-adjacent discovery, reported separately so it is never silently mixed in.
ADJACENT = {
    "id": "culture-adjacent",
    "title": "Culture-adjacent (Entertainment category)",
    "queries": ["category:Entertainment"],
    "note": "Kalshi files these under the Entertainment category, not Culture. Shown in a separate table.",
}

MAX_MARKETS_PER_TOPIC = 400          # metadata copies, per topic
MAX_ORDERBOOKS_PER_TOPIC = 30        # live depth snapshots, per topic
MAX_TRADE_MARKETS_PER_TOPIC = 5      # trade-history pulls, per topic (largest markets)
MAX_RESOLVED_PER_SERIES = 8          # settled markets copied per series
REQUEST_PAUSE = 0.05                 # be polite: unauthenticated limits are unpublished
MAX_SERIES_PER_TOPIC = int(os.environ.get('KALSHI_MAX_SERIES', '120'))  # series breadth per topic
SERIES_WORKERS = int(os.environ.get('KALSHI_WORKERS', '10'))  # concurrent per-series fetches

MARKET_FIELDS = [
    "ticker", "event_ticker", "market_type", "title", "yes_sub_title", "status",
    "created_time", "updated_time", "open_time", "close_time",
    "expected_expiration_time", "latest_expiration_time",
    "yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars", "no_ask_dollars",
    "yes_bid_size_fp", "yes_ask_size_fp", "last_price_dollars",
    "previous_price_dollars", "volume_fp", "volume_24h_fp", "open_interest_fp",
    "result", "expiration_value", "can_close_early", "notional_value_dollars",
    "strike_type", "settlement_timer_seconds", "exchange_index",
]

_requests = 0
_errors = []


def _req(url, expect=200, tries=3):
    """GET with small backoff. Returns (json_or_None, status, headers)."""
    global _requests
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "kalshi-demo-dashboard/1.0 (+https://github.com/karagemop466-tech/Demo2)",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8")
                _requests += 1
                time.sleep(REQUEST_PAUSE)
                return (json.loads(body) if body.strip() else None), r.status, dict(r.headers)
        except urllib.error.HTTPError as e:
            _requests += 1
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            _errors.append({"url": url, "status": e.code, "detail": e.read()[:300].decode("utf-8", "replace")})
            return None, e.code, dict(e.headers or {})
        except Exception as e:  # network / TLS / JSON
            _errors.append({"url": url, "status": None, "detail": f"{type(e).__name__}: {e}"})
            if attempt < tries - 1:
                time.sleep(1.0)
    return None, None, {}


def fnum(v):
    """Parse a fixed-point string field. Returns None when absent/unparseable."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def round4(v):
    return None if v is None else round(v, 4)


def derive(m):
    """Derived money figures. Each is documented arithmetic over copied fields."""
    vol = fnum(m.get("volume_fp"))
    vol24 = fnum(m.get("volume_24h_fp"))
    oi = fnum(m.get("open_interest_fp"))
    last = fnum(m.get("last_price_dollars"))
    if last is None:
        last = fnum(m.get("previous_price_dollars"))
    used = "last_price_dollars" if fnum(m.get("last_price_dollars")) is not None else "previous_price_dollars"
    out = {
        "notional_lifetime_usd": round4(vol * last) if (vol is not None and last is not None) else None,
        "notional_24h_usd": round4(vol24 * last) if (vol24 is not None and last is not None) else None,
        "open_interest_usd": round4(oi * last) if (oi is not None and last is not None) else None,
        "price_used": used if last is not None else None,
        "last_price_used": round4(last),
    }
    return out


def series_matches(topic, s):
    if topic["match_tags"]:
        tags = [str(t).lower() for t in (s.get("tags") or [])]
        if any(t in tags for t in topic["match_tags"]):
            return True
    if topic["match_words"]:
        hay = (str(s.get("title", "")) + " " + str(s.get("ticker", ""))).lower()
        if any(w in hay for w in topic["match_words"]):
            return True
    if not topic["match_tags"] and not topic["match_words"]:
        cats = [str(c).lower() for c in (s.get("categories") or [s.get("category") or ""])]
        if topic["id"] == "culture" and "culture" in cats:
            return True
        if topic["id"] == "elections" and "elections" in cats:
            return True
        if topic["id"] == "crypto" and "crypto" in cats:
            return True
    return False


def discover_series():
    """Return {topic_id: [series...]} plus the culture-adjacent list."""
    cache = {}

    def by_category(cat):
        if cat not in cache:
            url = ENDPOINTS["series_by_category"].format(category=urllib.parse.quote(cat))
            j, st, _ = _req(url)
            cache[cat] = (j or {}).get("series", []) if st == 200 else []
            cache[cat + ":url"] = url
        return cache[cat]

    def by_tags(tags):
        key = "tags:" + tags
        if key not in cache:
            url = ENDPOINTS["series_by_tags"].format(tags=urllib.parse.quote(tags))
            j, st, _ = _req(url)
            cache[key] = (j or {}).get("series", []) if st == 200 else []
            cache[key + ":url"] = url
        return cache[key]

    found = {}
    queries = {}
    for topic in SCOPE:
        rows = []
        for q in topic["queries"]:
            kind, _, val = q.partition(":")
            src = by_category(val) if kind == "category" else by_tags(val)
            queries.setdefault(topic["id"], []).append(cache.get(val + ":url") or cache.get("tags:" + val + ":url"))
            for s in src:
                if topic["id"] == "golf" or series_matches(topic, s):
                    rows.append(s)
        # de-duplicate by ticker
        seen, uniq = set(), []
        for s in rows:
            t = s.get("ticker")
            if t and t not in seen:
                seen.add(t)
                uniq.append(s)
        found[topic["id"]] = uniq

    adj = []
    for s in by_category("Entertainment"):
        adj.append(s)
    return found, adj, queries, cache


def select_series(all_series, limit):
    """Choose which series to query when a topic has more than the cap allows.

    Rule (deterministic, no judgement about which market matters): sort by the
    API's own `frequency` field first - daily before weekly before monthly before
    one_off - then by ticker, and take the first `limit`. That guarantees the
    recurring contracts (daily gas prices, daily/hourly crypto) are always
    included, and the series dropped are the tail of the long one-off lists.
    The number dropped is reported per topic, never hidden.
    """
    order = {"daily": 0, "hourly": 0, "15 min": 0, "weekly": 1, "monthly": 2}
    def key(s):
        return (order.get(str(s.get("frequency") or "").lower(), 3), str(s.get("ticker") or ""))
    return sorted(all_series, key=key)[:limit]


def slim_series(s, topic_id):
    return {
        "topic": topic_id,
        "ticker": s.get("ticker"),
        "title": s.get("title"),
        "frequency": s.get("frequency"),
        "category": s.get("category"),
        "categories": s.get("categories") or [],
        "tags": s.get("tags"),
        "fee_type": s.get("fee_type"),
        "fee_multiplier": s.get("fee_multiplier"),
        "contract_terms_url": s.get("contract_terms_url"),
        "contract_url": s.get("contract_url"),
        "settlement_sources": [
            {"name": x.get("name"), "url": x.get("url")} for x in (s.get("settlement_sources") or [])
        ],
        "last_updated_ts": s.get("last_updated_ts"),
        "exchange_index": s.get("exchange_index"),
    }


def collect_events(series_ticker, status):
    url = ENDPOINTS["events"].format(ticker=urllib.parse.quote(series_ticker), status=status)
    j, st, _ = _req(url)
    if st != 200 or not j:
        return [], url
    return j.get("events", []) or [], url


def collect_markets(series_ticker, status):
    url = ENDPOINTS["markets"].format(ticker=urllib.parse.quote(series_ticker), status=status)
    j, st, _ = _req(url)
    if st != 200 or not j:
        return [], url
    return j.get("markets", []) or [], url


def collect_orderbook(ticker, depth=20):
    url = ENDPOINTS["orderbook"].format(ticker=urllib.parse.quote(ticker), depth=depth)
    j, st, _ = _req(url)
    ob = (j or {}).get("orderbook_fp") or {}
    yes = [[p, q] for p, q in (ob.get("yes_dollars") or [])]
    no = [[p, q] for p, q in (ob.get("no_dollars") or [])]
    # Derived totals: plain sums of the returned [price, count] levels.
    yes_contracts = sum(fnum(q) or 0 for _, q in yes)
    no_contracts = sum(fnum(q) or 0 for _, q in no)
    yes_dollars = sum((fnum(p) or 0) * (fnum(q) or 0) for p, q in yes)
    no_dollars = sum((fnum(p) or 0) * (fnum(q) or 0) for p, q in no)
    return {
        "ticker": ticker,
        "http_status": st,
        "source_url": url,
        "yes_dollars": yes,
        "no_dollars": no,
        "derived": {
            "yes_levels": len(yes),
            "no_levels": len(no),
            "yes_contracts_at_levels": round4(yes_contracts),
            "no_contracts_at_levels": round4(no_contracts),
            "yes_resting_usd": round4(yes_dollars),
            "no_resting_usd": round4(no_dollars),
            "best_yes_bid": fnum(yes[-1][0]) if yes else None,
            "best_no_bid": fnum(no[-1][0]) if no else None,
            "implied_yes_ask": round(1 - fnum(no[-1][0]), 4) if no and fnum(no[-1][0]) is not None else None,
        },
    }


def collect_trades(ticker, limit=1000):
    url = ENDPOINTS["trades"].format(ticker=urllib.parse.quote(ticker))
    url = url.replace("limit=1000", f"limit={limit}")
    j, st, _ = _req(url)
    rows = (j or {}).get("trades", []) if st == 200 else []
    return rows, url


def main():
    started = datetime.now(timezone.utc)
    health = {}
    cors = {}

    # --- exchange status + CORS probe (both public) -------------------------
    j, st, _ = _req(ENDPOINTS["exchange_status"])
    health["exchange_status_http"] = st
    health["exchange_status"] = j

    cors_url = ENDPOINTS["exchange_status"]
    try:
        req = urllib.request.Request(
            cors_url,
            headers={
                "Origin": "https://karagemop466-tech.github.io",
                "Access-Control-Request-Method": "GET",
                "User-Agent": "kalshi-demo-dashboard/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            h = dict(r.headers)
            cors = {
                "probe_url": cors_url,
                "probe_origin": "https://karagemop466-tech.github.io",
                "status": r.status,
                "access_control_allow_origin": h.get("access-control-allow-origin") or h.get("Access-Control-Allow-Origin"),
                "cache_control": h.get("cache-control") or h.get("Cache-Control"),
                "x_ratelimit_limit": h.get("x-ratelimit-limit") or h.get("X-RateLimit-Limit"),
                "x_ratelimit_remaining": h.get("x-ratelimit-remaining") or h.get("X-RateLimit-Remaining"),
                "x_ratelimit_cost": h.get("x-ratelimit-cost") or h.get("X-RateLimit-Cost"),
            }
    except Exception as e:
        cors = {"probe_url": cors_url, "error": f"{type(e).__name__}: {e}"}
    health["cors"] = cors

    tags_j, tags_st, _ = _req(ENDPOINTS["tags_by_categories"])
    health["tags_by_categories_http"] = tags_st
    tags_by_cat = (tags_j or {}).get("tags_by_categories") if tags_st == 200 else None

    found, adjacent, queries, cache = discover_series()

    series_rows = []
    markets_by_topic = {}
    resolved_rows = []
    orderbooks = {}
    trade_history = {}
    event_titles = {}
    truncated = {}

    for topic in SCOPE:
        tid = topic["id"]
        mkts = []
        series_list = select_series(found.get(tid, []), MAX_SERIES_PER_TOPIC)
        truncated[tid] = max(0, len(found.get(tid, [])) - len(series_list))

        def fetch_series(s):
            """(series, open markets, settled markets, events, urls) for one series."""
            st = s.get("ticker")
            evs, ev_url = collect_events(st, "open")
            om, om_url = collect_markets(st, "open")
            sm, sm_url = collect_markets(st, "settled")
            return s, om, sm, evs, om_url, sm_url, ev_url

        results = []
        with ThreadPoolExecutor(max_workers=SERIES_WORKERS) as pool:
            futs = {pool.submit(fetch_series, s): s for s in series_list}
            for f in as_completed(futs):
                try:
                    results.append(f.result())
                except Exception as e:  # a single series failing never sinks the run
                    _errors.append({"url": "series " + str(futs[f].get("ticker")), "status": None,
                                    "detail": f"{type(e).__name__}: {e}"})

        results.sort(key=lambda r: str(r[0].get("ticker")))
        for s, om, sm, evs, om_url, sm_url, ev_url in results:
            st_ticker = s.get("ticker")
            series_rows.append(slim_series(s, tid))
            for e in evs:
                event_titles[e.get("event_ticker")] = {
                    "title": e.get("title"),
                    "sub_title": e.get("sub_title"),
                    "series_ticker": e.get("series_ticker"),
                    "event_ticker": e.get("event_ticker"),
                    "source_url": ev_url,
                }
            for m in om:
                m["_source_markets_url"] = om_url
                m["_series"] = s
                mkts.append(m)
            for m in sm[:MAX_RESOLVED_PER_SERIES]:
                row = {k: m.get(k) for k in MARKET_FIELDS}
                row.update(
                    {
                        "topic": tid,
                        "series_ticker": st_ticker,
                        "series_title": s.get("title"),
                        "event_title": (event_titles.get(m.get("event_ticker")) or {}).get("title"),
                        "source_url": sm_url,
                        "source_market_url": ENDPOINTS["market"].format(ticker=urllib.parse.quote(str(m.get("ticker")))),
                    }
                )
                row.update(derive(m))
                resolved_rows.append(row)

        mkts.sort(key=lambda m: (derive(m)["open_interest_usd"] or -1), reverse=True)
        mkts = mkts[:MAX_MARKETS_PER_TOPIC]
        rows = []
        for m in mkts:
            row = {k: m.get(k) for k in MARKET_FIELDS}
            s = m.get("_series") or {}
            row.update(
                {
                    "topic": tid,
                    "series_ticker": s.get("ticker"),
                    "series_title": s.get("title"),
                    "event_title": (event_titles.get(m.get("event_ticker")) or {}).get("title"),
                    "source_url": m.get("_source_markets_url"),
                    "source_market_url": ENDPOINTS["market"].format(ticker=urllib.parse.quote(str(m.get("ticker")))),
                    "source_series_url": (cache.get(str(s.get("category")) + ":url") or ""),
                }
            )
            row.update(derive(m))
            rows.append(row)
        markets_by_topic[tid] = rows

        # live liquidity: depth snapshot for the largest markets by open-interest dollars
        for row in rows[:MAX_ORDERBOOKS_PER_TOPIC]:
            orderbooks[row["ticker"]] = collect_orderbook(row["ticker"])

        # trade history: price path for the largest markets
        for row in rows[:MAX_TRADE_MARKETS_PER_TOPIC]:
            tr, tr_url = collect_trades(row["ticker"])
            if tr:
                trade_history[row["ticker"]] = {"source_url": tr_url, "trades": tr[:600]}

    # culture-adjacent (reported separately)
    adj_rows = [slim_series(s, "culture-adjacent") for s in adjacent]
    adj_markets = []
    for s in adjacent[:8]:
        om, om_url = collect_markets(s.get("ticker"), "open")
        for m in om:
            row = {k: m.get(k) for k in MARKET_FIELDS}
            row.update(
                {
                    "topic": "culture-adjacent",
                    "series_ticker": s.get("ticker"),
                    "series_title": s.get("title"),
                    "source_url": om_url,
                    "source_market_url": ENDPOINTS["market"].format(ticker=urllib.parse.quote(str(m.get("ticker")))),
                }
            )
            row.update(derive(m))
            adj_markets.append(row)
    adj_markets.sort(key=lambda m: (m.get("open_interest_usd") or -1), reverse=True)

    # ---------------- calibration over resolved in-scope markets -------------
    # Method: bucket resolved markets by their last traded YES price, then compare the
    # mean implied probability with the realised YES frequency. Pure arithmetic over
    # copied fields; no market is predicted.
    buckets = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    calib = {f"{buckets[i]:.1f}-{min(buckets[i+1],1.0):.2f}": {"n": 0, "yes": 0, "sum_p": 0.0}
             for i in range(len(buckets) - 1)}
    by_topic = {}
    for r in resolved_rows:
        res = (r.get("result") or "").lower()
        p = fnum(r.get("last_price_dollars"))
        if p is None:
            p = r.get("last_price_used")
        if p is None:
            continue
        if res not in ("yes", "no"):
            continue
        for i in range(len(buckets) - 1):
            if buckets[i] <= p < buckets[i + 1]:
                k = f"{buckets[i]:.1f}-{min(buckets[i+1],1.0):.2f}"
                calib[k]["n"] += 1
                calib[k]["yes"] += 1 if res == "yes" else 0
                calib[k]["sum_p"] += p
                break
        bt = by_topic.setdefault(r["topic"], {"n": 0, "yes": 0, "no": 0})
        bt["n"] += 1
        bt["yes" if res == "yes" else "no"] += 1

    calibration = {
        "method": ("Group resolved in-scope markets by their last traded YES price band, then compare the "
                   "band's mean last traded price (the market's own implied probability) with the share of "
                   "those markets that actually resolved YES. Arithmetic only; no model is fitted."),
        "price_field": "last_price_dollars as returned in the settled-market response",
        "bands": [
            {"band": k, "n": v["n"], "resolved_yes": v["yes"],
             "implied_prob_mean": round4(v["sum_p"] / v["n"]) if v["n"] else None,
             "realised_yes_rate": round4(v["yes"] / v["n"]) if v["n"] else None}
            for k, v in calib.items()
        ],
        "by_topic": [{"topic": k, "n": v["n"], "resolved_yes": v["yes"], "resolved_no": v["no"]} for k, v in sorted(by_topic.items())],
        "totals": {"resolved_rows": len(resolved_rows), "with_price_and_result": sum(v["n"] for v in calib.values())},
    }

    doc = {
        "meta": {
            "generated_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generated_epoch": int(started.timestamp()),
            "api_base": API,
            "api_docs": f"{DOCS['demo_env']}",
            "collector": "tools/kalshi_collect.py",
            "https_requests": _requests,
            "request_errors": _errors,
            "endpoints": ENDPOINTS,
            "docs": DOCS,
            "limits": {"max_series_per_topic": MAX_SERIES_PER_TOPIC, "max_markets_per_topic": MAX_MARKETS_PER_TOPIC,
                    "max_orderbooks_per_topic": MAX_ORDERBOOKS_PER_TOPIC,
                    "max_trade_markets_per_topic": MAX_TRADE_MARKETS_PER_TOPIC,
                    "max_resolved_per_series": MAX_RESOLVED_PER_SERIES},
            "note": ("All values are copied from Kalshi DEMO Trade API responses or are arithmetic over copied "
                     "values. Kalshi states demo prices may not be reflective of real markets."),
        },
        "health": health,
        "scope": {
            "topics": SCOPE,
            "adjacent": ADJACENT,
            "series_queries": queries,
        },
        "tags_by_categories": tags_by_cat,
        "series": series_rows,
        "series_culture_adjacent": adj_rows,
        "markets": markets_by_topic,
        "markets_culture_adjacent": adj_markets[:80],
        "resolved": resolved_rows,
        "orderbooks": orderbooks,
        "trades": trade_history,
        "events": event_titles,
        "calibration": calibration,
        "series_truncated_per_topic": truncated,
        "counts": {
            "series_in_scope": len(series_rows),
            "open_markets_in_scope": sum(len(v) for v in markets_by_topic.values()),
            "resolved_in_scope_collected": len(resolved_rows),
            "orderbooks": len(orderbooks),
            "trade_histories": len(trade_history),
            "culture_adjacent_series": len(adj_rows),
            "culture_adjacent_markets": len(adj_markets),
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)

    # ---- append to the rolling price history (real observed ticks only) ----
    hist_dir = os.path.join(os.path.dirname(OUT), "history_instrument")
    os.makedirs(hist_dir, exist_ok=True)
    epoch = doc["meta"]["generated_epoch"]
    tick = {}
    for tid, rows in markets_by_topic.items():
        for r in rows:
            tick[r["ticker"]] = {
                "t": tid,
                "lp": r.get("last_price_dollars"),
                "yb": r.get("yes_bid_dollars"),
                "ya": r.get("yes_ask_dollars"),
                "oi": r.get("open_interest_fp"),
                "v": r.get("volume_fp"),
            }
    day_file = os.path.join(hist_dir, started.strftime("%Y-%m-%d") + ".json")
    day = {"date": started.strftime("%Y-%m-%d"), "samples": []}
    if os.path.exists(day_file):
        try:
            with open(day_file, encoding="utf-8") as fh:
                day = json.load(fh)
        except Exception:
            pass
    day.setdefault("samples", []).append({"ts": epoch, "markets": tick})
    day["samples"] = day["samples"][-400:]
    with open(day_file, "w", encoding="utf-8") as fh:
        json.dump(day, fh, separators=(",", ":"), ensure_ascii=False)
    # keep three UTC days of history
    keep = sorted(f[:-5] for f in os.listdir(hist_dir) if f.endswith(".json"))[-3:]
    for f in os.listdir(hist_dir):
        if f.endswith(".json") and f[:-5] not in keep:
            os.remove(os.path.join(hist_dir, f))
    # index of retained days for the client
    with open(os.path.join(hist_dir, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"days": keep, "updated": doc["meta"]["generated_at"]}, fh, indent=1)
    print(json.dumps(doc["counts"], indent=1))
    print("requests:", _requests, "errors:", len(_errors))
    if _errors:
        print("first errors:", json.dumps(_errors[:3], indent=1))
    return 0 if doc["counts"]["open_markets_in_scope"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
