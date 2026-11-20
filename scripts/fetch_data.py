#!/usr/bin/env python3
"""
fetch_data.py — Pull official Kalshi demo Trade API data into data/*.json.

Official sources (verified 2026-11-20, see docs/VERIFICATION.md):
  REST demo base (recommended): https://external-api.demo.kalshi.co/trade-api/v2
    source: https://docs.kalshi.com/getting_started/demo_env
  GET /series?include_volume=true
    source: https://docs.kalshi.com/api-reference/market/get-series-list
  GET /events?limit=200&status=...&with_nested_markets=true
    source: https://docs.kalshi.com/api-reference/events/get-events
  GET /markets?status=settled&min_settled_ts=...
    source: https://docs.kalshi.com/api-reference/market/get-markets
  GET /markets/{ticker}/orderbook?depth=N
    source: https://docs.kalshi.com/api-reference/market/get-market-orderbook
  GET /markets/trades?ticker=...&min_ts=...&max_ts=...
    source: https://docs.kalshi.com/api-reference/market/get-trades
  GET /series/{series}/markets/{ticker}/candlesticks?start_ts=&end_ts=&period_interval=1|60|1440
    source: https://docs.kalshi.com/api-reference/market/get-market-candlesticks

Every record written carries the exact official URL it came from ("source").
Computed fields (never presented as API-provided) carry "computed": true and
a "formula" string.

Stdlib only. Respects rate limits (sleep between calls, back off on 429 —
see https://docs.kalshi.com/getting_started/rate_limits).
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE = "https://external-api.demo.kalshi.co/trade-api/v2"
ORIGIN = os.environ.get("PROBE_ORIGIN", "https://karagemop466-tech.github.io")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Focus topics only (per project brief): gas prices, elections, culture, crypto, golf.
TOPICS = ["gas prices", "elections", "culture", "crypto", "golf"]

SLEEP = 0.45          # seconds between API calls (unauthenticated requests are metered)
RECENT_SETTLED_DAYS = 7


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url, headers=None, timeout=30, tries=3):
    """GET url, return (status, body_bytes, response_headers). Backs off on 429."""
    hdrs = {"User-Agent": "Demo2-Kalshi-Dashboard/1.0 (+data pipeline)"}
    if headers:
        hdrs.update(headers)
    last_err = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers=hdrs, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as e:
            body = e.read() if e.fp else b""
            if e.code == 429:
                wait = 5 * (attempt + 1)
                print(f"  429 on {url} — backing off {wait}s", file=sys.stderr)
                time.sleep(wait)
                last_err = e
                continue
            return e.code, body, dict(e.headers or {})
        except Exception as e:  # noqa: BLE001 — network error, retry
            last_err = e
            time.sleep(2 * (attempt + 1))
    if isinstance(last_err, urllib.error.HTTPError):
        return last_err.code, last_err.read() if last_err.fp else b"", dict(last_err.headers or {})
    raise RuntimeError(f"GET failed after {tries} tries: {url}: {last_err}")


def get_json(url, headers=None):
    status, body, resp_headers = http_get(url, headers=headers)
    if status != 200:
        raise RuntimeError(f"{url} -> HTTP {status}: {body[:300]!r}")
    time.sleep(SLEEP)
    return json.loads(body), resp_headers


def write_json(name, payload):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False, ensure_ascii=False)
    print(f"wrote {path} ({os.path.getsize(path)} bytes)")


def fnum(s, default=0.0):
    """Fixed-point string -> float; blank/None -> default (never invent)."""
    if s is None or s == "":
        return default
    try:
        return float(s)
    except ValueError:
        return default


# ---------------------------------------------------------------- topics ----
# Classification rules (transparent, deterministic, documented on the site):
#   gas prices : series ticker starts with "KXAAAGAS"  (AAA gasoline price series,
#                verified: KXAAAGASM, KXAAAGASD via GET /series/{ticker})
#                OR series product_metadata.scope == "Gasoline"
#                OR title matches "gas price" (case-insensitive)
#   elections  : series.category == "Elections" OR event.category == "Elections"
#   culture    : series.category == "Culture"   OR event.category == "Culture"
#   crypto     : series.category == "Crypto"    OR event.category == "Crypto"
#   golf       : "Golf" in series.tags (case-insensitive) OR title contains "golf"
def classify(event, series):
    title = (event.get("title") or "") + " " + (event.get("sub_title") or "")
    etitle = (event.get("category") or "")
    topics = set()
    if series:
        st = (series.get("ticker") or "")
        s_title = series.get("title") or ""
        s_cat = series.get("category") or ""
        tags = [t.lower() for t in (series.get("tags") or [])]
        scope = ((series.get("product_metadata") or {}) or {}).get("scope") or ""
        if st.upper().startswith("KXAAAGAS") or scope.lower() == "gasoline" or "gas price" in s_title.lower() or "gas price" in title.lower():
            topics.add("gas prices")
        if s_cat == "Elections" or etitle == "Elections":
            topics.add("elections")
        if s_cat == "Culture" or etitle == "Culture":
            topics.add("culture")
        if s_cat == "Crypto" or etitle == "Crypto":
            topics.add("crypto")
        if "golf" in tags or "golf" in s_title.lower() or "golf" in title.lower():
            topics.add("golf")
    else:
        # no series record — fall back to event category/title only
        if etitle == "Elections":
            topics.add("elections")
        if etitle == "Culture":
            topics.add("culture")
        if etitle == "Crypto":
            topics.add("crypto")
        if "gas price" in title.lower():
            topics.add("gas prices")
        if "golf" in title.lower():
            topics.add("golf")
    return sorted(topics)


# ------------------------------------------------------------ pipeline ------
def fetch_series_index():
    """GET /series?include_volume=true — full series list (no pagination per spec)."""
    url = f"{BASE}/series?include_volume=true"
    data, _ = get_json(url)
    series_list = data.get("series") or []
    out = []
    for s in series_list:
        topics = classify({"title": s.get("title"), "sub_title": "", "category": s.get("category")}, s)
        if not topics:
            continue
        out.append({
            "ticker": s.get("ticker"),
            "title": s.get("title"),
            "category": s.get("category"),
            "categories": s.get("categories"),
            "tags": s.get("tags"),
            "scope": ((s.get("product_metadata") or {}) or {}).get("scope"),
            "frequency": s.get("frequency"),
            "volume_fp": s.get("volume_fp"),   # official total series volume (contracts)
            "topics": topics,
            "source": f"{BASE}/series/{s.get('ticker')}",
        })
    payload = {
        "fetched_at": now_iso(),
        "source": url,
        "note": "Official GET /series response, filtered to the 5 focus topics by the documented classification rules. volume_fp is the official series total volume in contracts (include_volume=true).",
        "series": sorted(out, key=lambda r: (r["topics"], r["ticker"] or "")),
    }
    write_json("series_index.json", payload)
    return {s["ticker"]: s for s in out}


def fetch_open_events(series_map):
    """GET /events?status=open&with_nested_markets=true — paginate."""
    events, cursor, pages = [], "", 0
    while pages < 40:
        url = f"{BASE}/events?limit=200&status=open&with_nested_markets=true"
        if cursor:
            url += f"&cursor={cursor}"
        data, _ = get_json(url)
        batch = data.get("events") or []
        events.extend(batch)
        cursor = data.get("cursor") or ""
        pages += 1
        if not cursor or not batch:
            break
    return events, pages


def top_events(events, series_map):
    """Rank focus-topic events by estimated 24h dollar volume (computed)."""
    per_topic = {t: [] for t in TOPICS}
    for ev in events:
        if ev.get("event_ticker", "").startswith("KXMVE"):
            continue  # multivariate combos: excluded from /events per spec; skip defensively
        s_ticker = ev.get("series_ticker")
        series = series_map.get(s_ticker)
        topics = classify(ev, series)
        if not topics:
            continue
        markets = ev.get("markets") or []
        vol24 = 0.0        # contracts (official sum)
        dollar24 = 0.0     # computed estimate
        oi = 0.0           # contracts (official sum)
        best = None
        for m in markets:
            if m.get("status") not in ("active", "closed", "determined"):
                continue
            v24 = fnum(m.get("volume_24h_fp"))
            lp = fnum(m.get("last_price_dollars"))
            vol24 += v24
            dollar24 += v24 * lp          # formula documented; computed, not official
            oi += fnum(m.get("open_interest_fp"))
            if best is None or v24 > fnum(best.get("volume_24h_fp")):
                best = m
        if vol24 <= 0 and oi <= 0:
            continue
        row = {
            "event_ticker": ev.get("event_ticker"),
            "title": ev.get("title"),
            "series_ticker": s_ticker,
            "series_title": (series or {}).get("title"),
            "category": (series or {}).get("category") or ev.get("category"),
            "volume_24h_contracts": round(vol24, 2),
            "open_interest_contracts": round(oi, 2),
            "est_dollar_volume_24h": round(dollar24, 2),
            "computed": True,
            "formula": "est_dollar_volume_24h = sum over child markets of volume_24h_fp * last_price_dollars (USD). Computed from official fields; not an official API field.",
            "market_count": len(markets),
            "lead_market": None,
            "source": f"{BASE}/events?tickers={ev.get('event_ticker')}&with_nested_markets=true",
        }
        if best:
            row["lead_market"] = {
                "ticker": best.get("ticker"),
                "title": best.get("title"),
                "status": best.get("status"),
                "last_price_dollars": best.get("last_price_dollars"),
                "yes_bid_dollars": best.get("yes_bid_dollars"),
                "yes_ask_dollars": best.get("yes_ask_dollars"),
                "yes_bid_size_fp": best.get("yes_bid_size_fp"),
                "yes_ask_size_fp": best.get("yes_ask_size_fp"),
                "volume_24h_fp": best.get("volume_24h_fp"),
                "open_interest_fp": best.get("open_interest_fp"),
                "close_time": best.get("close_time"),
                "result": best.get("result"),
                "source": f"{BASE}/markets/{best.get('ticker')}",
            }
        for t in topics:
            per_topic[t].append(row)

    out = {}
    for t in TOPICS:
        ranked = sorted(per_topic[t], key=lambda r: (-r["est_dollar_volume_24h"], -r["volume_24h_contracts"]))
        out[t] = ranked[:10]
    payload = {
        "fetched_at": now_iso(),
        "source": f"{BASE}/events?status=open&with_nested_markets=true",
        "ranking": "est_dollar_volume_24h (computed) descending; tie-break volume_24h_contracts (official) descending",
        "topics": out,
    }
    write_json("events_top.json", payload)
    return out


def fetch_resolved_topics(series_map):
    """Settled markets (last N days) whose series classifies into a focus topic."""
    since = int((datetime.now(timezone.utc) - timedelta(days=RECENT_SETTLED_DAYS)).timestamp())
    results, cursor, pages = [], "", 0
    while pages < 6:
        url = f"{BASE}/markets?status=settled&limit=1000&min_settled_ts={since}&mve_filter=exclude"
        if cursor:
            url += f"&cursor={cursor}"
        data, _ = get_json(url)
        batch = data.get("markets") or []
        for m in batch:
            # market ticker prefix -> series ticker is not guaranteed; use event lookup cache
            results.append(m)
        cursor = data.get("cursor") or ""
        pages += 1
        if not cursor or not batch:
            break

    # Join each settled market to its event (cached) to get series + category.
    event_cache = {}
    out = []
    for m in results:
        ev_t = m.get("event_ticker")
        if ev_t not in event_cache:
            try:
                edata, _ = get_json(f"{BASE}/events/{ev_t}")
                event_cache[ev_t] = edata.get("event") or {}
            except Exception as e:  # noqa: BLE001
                print(f"  event lookup failed {ev_t}: {e}", file=sys.stderr)
                event_cache[ev_t] = {}
        ev = event_cache[ev_t]
        series = series_map.get(ev.get("series_ticker"))
        topics = classify(ev, series)
        if not topics:
            continue
        out.append({
            "ticker": m.get("ticker"),
            "market_title": m.get("title") or m.get("yes_sub_title"),
            "event_ticker": ev_t,
            "event_title": ev.get("title"),
            "series_ticker": ev.get("series_ticker"),
            "topics": topics,
            "status": m.get("status"),
            "result": m.get("result"),            # official: "yes" | "no" | "scalar" | ""
            "close_time": m.get("close_time"),
            "settled_ts": m.get("settlement_ts") or m.get("updated_time"),
            "last_price_dollars": m.get("last_price_dollars"),
            "volume_fp": m.get("volume_fp"),
            "source": f"{BASE}/markets/{m.get('ticker')}",
            "event_source": f"{BASE}/events/{ev_t}",
        })
        if len(out) >= 200:
            break
    payload = {
        "fetched_at": now_iso(),
        "source": f"{BASE}/markets?status=settled&min_settled_ts={since}&mve_filter=exclude",
        "window_days": RECENT_SETTLED_DAYS,
        "note": "Official settled markets filtered to focus topics. result is the official determination: yes / no / scalar.",
        "markets": out,
    }
    write_json("resolved.json", payload)
    return out


def probe_and_snapshot(series_map, top):
    """CORS probe + a live snapshot for chart/depth fallback when browsers cannot reach the API."""
    probe_url = f"{BASE}/markets?limit=1"
    status, body, hdrs = http_get(probe_url, headers={"Origin": ORIGIN})
    hdr_keys = [
        "access-control-allow-origin", "access-control-allow-headers",
        "access-control-allow-methods", "access-control-allow-credentials",
        "access-control-expose-headers", "vary", "x-ratelimit-limit",
        "x-ratelimit-remaining", "x-ratelimit-reset", "x-ratelimit-cost",
    ]
    observed = {k: hdrs.get(k) or hdrs.get(k.title()) or "" for k in hdr_keys}
    cors = {
        "fetched_at": now_iso(),
        "probe_url": probe_url,
        "origin_sent": ORIGIN,
        "http_status": status,
        "observed_headers": observed,
        "source": probe_url,
        "docs": "https://docs.kalshi.com/getting_started/quick_start_market_data",
        "note": "Observed response headers for an Origin-initiated request. If access-control-allow-origin is empty, browsers cannot fetch the API directly from a page origin and the site falls back to these snapshots.",
    }
    write_json("cors.json", cors)

    # Snapshot for the default chart market: highest est. 24h dollar volume lead market.
    default_ticker, default_series = None, None
    best_val = -1.0
    for t in TOPICS:
        for row in top.get(t, []):
            lm = row.get("lead_market") or {}
            if lm.get("ticker") and row["est_dollar_volume_24h"] > best_val:
                best_val = row["est_dollar_volume_24h"]
                default_ticker = lm["ticker"]
                default_series = row.get("series_ticker")
    if not default_ticker:
        return

    now = int(datetime.now(timezone.utc).timestamp())
    snap = {"fetched_at": now_iso(), "ticker": default_ticker, "series_ticker": default_series}

    st, b, _ = http_get(f"{BASE}/markets/{default_ticker}")
    if st == 200:
        snap["market"] = json.loads(b)
        snap["market_source"] = f"{BASE}/markets/{default_ticker}"
    time.sleep(SLEEP)

    st, b, _ = http_get(f"{BASE}/markets/{default_ticker}/orderbook?depth=100")
    if st == 200:
        snap["orderbook"] = json.loads(b)
        snap["orderbook_source"] = f"{BASE}/markets/{default_ticker}/orderbook?depth=100"
    time.sleep(SLEEP)

    st, b, _ = http_get(f"{BASE}/markets/trades?ticker={default_ticker}&limit=500&max_ts={now}&min_ts={now - 86400}")
    if st == 200:
        snap["trades"] = json.loads(b)
        snap["trades_source"] = f"{BASE}/markets/trades?ticker={default_ticker}&limit=500&max_ts={now}&min_ts={now - 86400}"
    time.sleep(SLEEP)

    if default_series:
        st, b, _ = http_get(
            f"{BASE}/series/{default_series}/markets/{default_ticker}/candlesticks"
            f"?start_ts={now - 86400}&end_ts={now}&period_interval=60"
        )
        if st == 200:
            snap["candles_1h"] = json.loads(b)
            snap["candles_source"] = (
                f"{BASE}/series/{default_series}/markets/{default_ticker}/candlesticks"
                f"?start_ts={now - 86400}&end_ts={now}&period_interval=60"
            )
        time.sleep(SLEEP)

        st, b, _ = http_get(
            f"{BASE}/series/{default_series}/markets/{default_ticker}/candlesticks"
            f"?start_ts={now - 3600}&end_ts={now}&period_interval=1"
        )
        if st == 200:
            snap["candles_1m"] = json.loads(b)
        time.sleep(SLEEP)

    write_json("live_snapshot.json", snap)


def main():
    print(f"== Kalshi demo data pipeline ==\nbase: {BASE}\nout : {OUT_DIR}")
    t0 = time.time()
    series_map = fetch_series_index()
    print(f"focus-series: {len(series_map)}")
    events, pages = fetch_open_events(series_map)
    print(f"open events fetched: {len(events)} in {pages} page(s)")
    top = top_events(events, series_map)
    for t in TOPICS:
        print(f"  topic {t!r}: {len(top[t])} event(s) ranked")
    fetch_resolved_topics(series_map)
    probe_and_snapshot(series_map, top)
    write_json("pipeline_meta.json", {
        "fetched_at": now_iso(),
        "base_url": BASE,
        "runtime_seconds": round(time.time() - t0, 1),
        "topics": TOPICS,
        "docs_demo_env": "https://docs.kalshi.com/getting_started/demo_env",
    })
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
