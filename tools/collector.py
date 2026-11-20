#!/usr/bin/env python3
"""
Kalshi demo dashboard — data collector.

Runs on GitHub Actions (full internet egress) and writes plain JSON snapshots into
data/, which GitHub Pages serves. Nothing in this file invents a value: every number
written comes from an HTTP response from the Kalshi demo (or production) Trade API,
and every snapshot records the exact request URL and HTTP status that produced it.

Documented endpoints used (all verified against docs.kalshi.com — see
pages/api-reference.html for the line-by-line mapping):

  GET /exchange/status                    docs/api-reference/exchange/get-exchange-status
  GET /series?category=...                docs/api-reference/market/get-series-list
  GET /markets?status=open|settled        docs/api-reference/market/get-markets
  GET /markets/{ticker}/orderbook         docs/api-reference/market/get-market-orderbook
  GET /series/{s}/markets/{t}/candlesticks docs/api-reference/market/get-market-candlesticks
  GET /markets/trades                     docs/api-reference/market/get-trades

Auth (optional): demo API key (RSA-PSS/SHA-256 or Ed25519), per
docs.kalshi.com/getting_started/quick_start_authenticated_requests.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# --- endpoints (verified: docs.kalshi.com/getting_started/api_environments.md) ----
DEMO_REST = "https://external-api.demo.kalshi.co/trade-api/v2"
PROD_REST = "https://external-api.kalshi.com/trade-api/v2"

# In-scope topics only (user requirement). Matching is done on the OFFICIAL Kalshi
# `series.category` / series ticker, not on free-text guesses — see TOPIC_RULES.
TOPICS = ["gas", "elections", "culture", "crypto", "golf"]

# --- publish budget (session 7085e643, 2026-11-20) ------------------------------
# Why this exists: GitHub's pre-receive hook declines any pushed file over 100 MB,
# and the collector used to write the same rows THREE times (snapshot.markets,
# snapshot.by_topic and data/topic-<t>.json). When the demo elections universe grew
# past ~24k markets the published file reached 111.97 MB and every data push failed —
# refresh-data run 44800417665 (19:15 UTC) reports on all six attempts:
#   remote: error: File data/snapshot.json is 111.97 MB; this exceeds GitHub's file
#           size limit of 100.00 MB
#   remote: pre-receive hook declined
# so the deployed site sat on a 5-hour-old snapshot. The published payload is now
# bounded by rows-per-topic AND total bytes; the FULL universe is still collected and
# written to data/out/ (gitignored, uploaded as the run artifact), and every page shows
# published-vs-universe counts so nothing reads as a complete enumeration.
# Rows are never edited by this step — only selected.
PUB_MAX_ROWS_PER_TOPIC = int(os.environ.get("KALSHI_PUB_MAX_ROWS_PER_TOPIC", "1200"))
PUB_MAX_BYTES = int(os.environ.get("KALSHI_PUB_MAX_BYTES", "60000000"))
HISTORY_MAX_POINTS = int(os.environ.get("KALSHI_HISTORY_MAX_POINTS", "144"))
API_LOG_KEEP = int(os.environ.get("KALSHI_API_LOG_KEEP", "150"))
OUT_DIR = DATA / "out"

# How far back to look for settled in-scope markets when collecting resolutions
# (documented filter `min_settled_ts` on Get Markets).
RESOLUTION_WINDOW_DAYS = int(os.environ.get("KALSHI_RESOLUTION_WINDOW_DAYS", "30"))
# How far ahead the near-term pass looks for open markets that close soon (hours).
NEXT_TERM_HOURS = int(os.environ.get("KALSHI_NEAR_TERM_HOURS", "48"))
RESOLUTION_MAX_SERIES = int(os.environ.get("KALSHI_RESOLUTION_MAX_SERIES", "8"))

# API request log: (url, http_status, ok, note). Written to data/api_log.json so the
# site can prove which request produced which rows.
API_LOG: list[dict[str, Any]] = []


def log_req(url: str, status: int | str, note: str = "") -> None:
    API_LOG.append(
        {
            "url": url,
            "http_status": status,
            "ok": isinstance(status, int) and 200 <= status < 300,
            "note": note,
            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        }
    )


# --------------------------------------------------------------------------- auth
def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class Signer:
    """Signs requests exactly as documented in Quick Start: Authenticated Requests.

    Pre-sign text = timestamp_ms + METHOD + path-without-query.
    RSA keys -> RSA-PSS(SHA-256, salt=DIGEST_LENGTH); Ed25519 -> sign message directly.
    """

    def __init__(self, key_id: str, pem: str):
        self.key_id = key_id
        self.pem = pem
        self._key = None
        self._alg = None
        self._load()

    def _load(self) -> None:
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
        except Exception:  # pragma: no cover
            return
        try:
            self._key = load_pem_private_key(self.pem.encode(), password=None)
        except Exception:
            self._key = None
            return
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

            self._alg = "Ed25519" if isinstance(self._key, Ed25519PrivateKey) else "RSA-PSS"
        except Exception:
            self._alg = "RSA-PSS"

    @property
    def available(self) -> bool:
        return self._key is not None

    def headers(self, method: str, path_with_query: str) -> dict[str, str]:
        if not self.available:
            raise RuntimeError("signing key not loaded")
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        ts = str(int(time.time() * 1000))
        sign_path = path_with_query.split("?")[0]
        msg = f"{ts}{method}{sign_path}".encode()
        if self._alg == "Ed25519":
            sig = self._key.sign(msg)
        else:
            sig = self._key.sign(
                msg,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.DIGEST_LENGTH),
                hashes.SHA256(),
            )
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
            "KALSHI-ACCESS-TIMESTAMP": ts,
        }


def signer_from_env() -> Signer | None:
    key_id = os.environ.get("KALSHI_DEMO_API_KEY_ID", "").strip()
    pem = os.environ.get("KALSHI_DEMO_PRIVATE_KEY", "")
    pem_path = os.environ.get("KALSHI_DEMO_PRIVATE_KEY_PATH", "").strip()
    if pem_path and Path(pem_path).exists():
        pem = Path(pem_path).read_text()
    if not key_id or not pem.strip():
        return None
    s = Signer(key_id, pem)
    return s if s.available else None


# --------------------------------------------------------------------------- http
def get_json(url: str, signer: Signer | None = None, retries: int = 3) -> tuple[Any, int]:
    """GET a URL, return (parsed_json_or_None, http_status). Logs every attempt."""
    last_status: int | str = "no-attempt"
    for attempt in range(retries):
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")
        if signer is not None:
            path = "/trade-api/v2" + url.split("/trade-api/v2", 1)[-1]
            for k, v in signer.headers("GET", path).items():
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8", "replace")
                last_status = r.status
                log_req(url, r.status)
                try:
                    return json.loads(body), r.status
                except json.JSONDecodeError:
                    log_req(url, r.status, "non-JSON body")
                    return None, r.status
        except urllib.error.HTTPError as e:
            last_status = e.code
            body = e.read().decode("utf-8", "replace")[:300]
            log_req(url, e.code, body)
            if e.code in (401, 403, 404, 400, 410):
                return None, e.code  # not retryable
            time.sleep(1.5 * (attempt + 1))
        except Exception as e:  # network/TLS/timeout
            last_status = type(e).__name__
            log_req(url, last_status, str(e)[:200])
            time.sleep(1.5 * (attempt + 1))
    return None, int(last_status) if isinstance(last_status, int) else 0


def paginate(url: str, key: str, signer: Signer | None = None, max_pages: int = 30) -> list[dict]:
    """Cursor pagination exactly as documented in getting_started/pagination.md."""
    out: list[dict] = []
    cursor = ""
    for _ in range(max_pages):
        u = url + ("&" if "?" in url else "?") + "limit=200"
        if cursor:
            u += "&cursor=" + urllib.parse.quote(cursor, safe="")
        j, status = get_json(u, signer)
        if not j:
            break
        out.extend(j.get(key) or [])
        cursor = j.get("cursor") or ""
        if not cursor:
            break
    return out


# ----------------------------------------------------------------- topics / scope
# Official discovery fields only (docs: Get Series List -> `categories`, `category`, `tags`).
# Verified live 2026-11-20: tags=Gas -> DIESEL/DIESELM; tags=Golf -> KXPGATOUR etc.;
# categories contain "Elections" and "Crypto". Both fields are matched case-insensitively.
TAG_TOPIC = {
    "gas": "gas",
    "gasoline": "gas",
    "diesel": "gas",          # only when the series is a fuel-price series (see below)
    "golf": "golf",
    "elections": "elections",
    "election": "elections",
    "culture": "culture",
    "crypto": "crypto",
    "bitcoin": "crypto",
}
CATEGORY_TOPIC = {
    "elections": "elections",
    "crypto": "crypto",
    "culture": "culture",
}


def series_topic(series: dict) -> str | None:
    """Map an official Kalshi series record to one in-scope topic, or None.

    Uses ONLY official fields returned by GET /series: `tags` (subject tags) and
    `categories`/`category` (discovery/primary category). `diesel` is not treated as
    gas on its own unless the tag "Gas" is also present, because a diesel series is a
    fuel-price series but the tag is the authoritative signal.
    """
    if not series or not isinstance(series, dict):
        return None
    # 0) official product scope (verified live 2026-11-20 on GET /series/KXAAAGASD:
    #    product_metadata.scope == "Gasoline" for the AAA gasoline family). The bare
    #    "Oil & Gas" tag is deliberately NOT mapped here: it also covers crude oil
    #    (KXWTI), natural gas and TTF series, which are not "gas prices".
    pm = series.get("product_metadata")
    scope = str((pm.get("scope") if isinstance(pm, dict) else None) or "").strip().lower()
    if scope == "gasoline":
        return "gas"
    tags = [str(t).strip().lower() for t in (series.get("tags") or []) if t]
    cats = [str(c).strip().lower() for c in (series.get("categories") or []) if c]
    primary = str(series.get("category") or "").strip().lower()

    # 1) explicit tag matches (strongest signal)
    for tag in tags:
        mapped = TAG_TOPIC.get(tag)
        if mapped == "gas" and tag == "diesel":
            continue  # require the "Gas" tag itself
        if mapped:
            return mapped
    # 2) discovery/primary category matches
    for c in cats + [primary]:
        if c in CATEGORY_TOPIC:
            return CATEGORY_TOPIC[c]
    return None


def inventory(series_idx: dict[str, dict]) -> dict:
    """Evidence of what the API actually exposes, so the site can prove the mapping."""
    tags: dict[str, int] = {}
    cats: dict[str, int] = {}
    for s in series_idx.values():
        for t in s.get("tags") or []:
            tags[str(t)] = tags.get(str(t), 0) + 1
        for c in s.get("categories") or []:
            cats[str(c)] = cats.get(str(c), 0) + 1
    return {
        "series_count": len(series_idx),
        "tags_top": dict(sorted(tags.items(), key=lambda kv: -kv[1])[:60]),
        "categories": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
        "in_scope_series": {
            t: sorted([s["ticker"] for s in series_idx.values() if series_topic(s) == t and s.get("ticker")])
            for t in TOPICS
        },
    }


def load_series_index(signer: Signer | None) -> dict[str, dict]:
    """GET /series (unpaginated, verified in pagination.md) -> ticker -> series."""
    idx: dict[str, dict] = {}
    j, status = get_json(DEMO_REST + "/series", signer)
    if not j:
        return idx
    for s in j.get("series") or []:
        t = s.get("ticker")
        if t:
            idx[t] = s
    return idx


# ----------------------------------------------------------------- collector core
def market_row(topic: str, series: dict, ev: dict | None, m: dict, source_pass: str) -> dict:
    """One published market row, built ONLY from fields the API returned.

    `ev` is the nested event record when the row came from GET /events (it carries the
    event title and settlement sources); it is None for the near-term pass, where those
    fields are left blank rather than guessed. `source_pass` records which request
    produced the row, so the site can say so.
    """
    series = series or {}
    ev = ev or {}
    event_ticker = ev.get("event_ticker") or m.get("event_ticker")
    return {
        "topic": topic,
        "event_ticker": event_ticker,
        "series_ticker": ev.get("series_ticker") or m.get("series_ticker")
        or (str(event_ticker).split("-")[0] if event_ticker else None),
        "event_title": ev.get("title"),
        "market_ticker": m.get("ticker"),
        "market_title": m.get("title"),
        "yes_sub_title": m.get("yes_sub_title"),
        "status": m.get("status"),
        "result": m.get("result") or "",
        # ---- dollar fields are VERBATIM strings from the API ----
        "yes_bid_dollars": m.get("yes_bid_dollars"),
        "yes_ask_dollars": m.get("yes_ask_dollars"),
        "no_bid_dollars": m.get("no_bid_dollars"),
        "no_ask_dollars": m.get("no_ask_dollars"),
        "last_price_dollars": m.get("last_price_dollars"),
        "yes_bid_size_fp": m.get("yes_bid_size_fp"),
        "yes_ask_size_fp": m.get("yes_ask_size_fp"),
        "volume_fp": m.get("volume_fp"),
        "volume_24h_fp": m.get("volume_24h_fp"),
        "open_interest_fp": m.get("open_interest_fp"),
        # the API's own previous-session quotes: a documented field, used for the
        # "since yesterday" column instead of a locally stored baseline where absent
        "previous_price_dollars": m.get("previous_price_dollars"),
        "previous_yes_bid_dollars": m.get("previous_yes_bid_dollars"),
        "previous_yes_ask_dollars": m.get("previous_yes_ask_dollars"),
        "close_time": m.get("close_time"),
        "open_time": m.get("open_time"),
        "updated_time": m.get("updated_time"),
        "price_level_structure": m.get("price_level_structure"),
        # Full rules text omitted for file size (the 2026-11-20 run hit GitHub's 100 MB
        # file limit: snapshot.json 112 MB, mostly legal text). The verbatim prefix is
        # kept as `rules_primary_head` (clearly named) and the FULL rules stay reachable
        # at the row's official `market_url`. Nothing inferred or rewritten.
        "rules_primary_head": (m.get("rules_primary") or "")[:160] or None,
        "exchange_index": m.get("exchange_index"),
        "settlement_sources": ev.get("settlement_sources"),
        "series_category": series.get("category"),
        "series_categories": series.get("categories"),
        # Official per-series fee parameters (verified live 2026-11-20 on
        # GET /series/KXBTC -> fee_type "quadratic", fee_multiplier 1), so the simulated
        # desk charges the exchange's own numbers where the collector captured them.
        "series_fee_type": series.get("fee_type"),
        "series_fee_multiplier": series.get("fee_multiplier"),
        "contract_terms_url": series.get("contract_terms_url"),
        "contract_url": series.get("contract_url"),
        # Verifiable official link only: the exact API endpoint that produced this row.
        # A human web-UI market URL could not be confirmed from an official source, so
        # it is not invented (blank + flagged on the site).
        "event_url": f"{DEMO_REST}/events/{event_ticker}" if event_ticker else None,
        "market_url": f"{DEMO_REST}/markets/{m.get('ticker')}" if m.get("ticker") else None,
        "source_pass": source_pass,
    }


def collect_near_term(signer: Signer | None, series_idx: dict, topic_cache: dict,
                      have: set[str], max_pages: int = 12) -> list[dict]:
    """Short-dated open markets the events enumeration misses (added 2026-11-20).

    `GET /events?status=open` is paginated, and on 2026-11-20 the first 5,000 events were
    all long-dated election markets: `data/snapshot.json` contained ZERO in-scope markets
    closing within 90 days, while `GET /markets?status=open&max_close_ts=<now+3h>` returned
    crypto markets closing the same hour (verified live 2026-11-20T19:47Z, first page
    ticker KXCRYPTOLEAD15M-26NOV201745-XRP, close_time 2026-11-20T22:45:00Z). A dashboard
    about swings and resolutions is useless without the markets that actually move and
    settle today, so this pass unions them in through the documented `max_close_ts`
    filter on Get Markets instead of hoping pagination reaches them.
    """
    window = int(NEXT_TERM_HOURS) * 3600
    now = int(time.time())
    url = f"{DEMO_REST}/markets?status=open&max_close_ts={now + window}"
    out: list[dict] = []
    for m in paginate(url, "markets", signer, max_pages=max_pages):
        tk = m.get("ticker")
        if not tk or tk in have:
            continue
        ev_ticker = m.get("event_ticker") or ""
        st = m.get("series_ticker") or (ev_ticker.split("-")[0] if ev_ticker else "")
        topic = topic_cache.get(st)
        if topic is None and st and st not in series_idx:
            # same enrichment rule as the event pass: the full series record is the only
            # thing that can classify the AAA gasoline family (product_metadata.scope)
            j2, _ = get_json(f"{DEMO_REST}/series/{st}", signer)
            full = (j2 or {}).get("series") if isinstance(j2, dict) else None
            if isinstance(full, dict) and full.get("ticker"):
                series_idx[st] = full
                topic_cache[st] = series_topic(full)
                topic = topic_cache.get(st)
        if topic not in TOPICS:
            continue
        row = market_row(topic, series_idx.get(st) or {}, None, m, "near_term")
        have.add(tk)
        out.append(row)
    return out


# ----------------------------------------------------------------- collector core
def collect_scope(signer: Signer | None) -> dict:
    """Open markets for the in-scope topics, plus their event/series metadata."""
    series_idx = load_series_index(signer)
    topic_cache = {t: series_topic(s) for t, s in series_idx.items()}
    events = paginate(DEMO_REST + "/events?status=open&with_nested_markets=true", "events", signer,
                      max_pages=50)

    rows: list[dict] = []
    unmapped_series: dict[str, int] = {}
    enriched: set[str] = set()
    for ev in events:
        st = ev.get("series_ticker") or ""
        topic = topic_cache.get(st)
        if topic is None and st and st not in enriched:
            # The bare /series list response does not carry product_metadata (the
            # field that classifies e.g. the AAA gasoline family via
            # product_metadata.scope == "Gasoline"); GET /series/{ticker} does
            # (verified live 2026-11-20). Enrich only the unmapped series that
            # actually appear in in-scope events, then re-map. Official data only.
            enriched.add(st)
            try:
                j2, _ = get_json(f"{DEMO_REST}/series/{st}", signer)
                full = (j2 or {}).get("series") if isinstance(j2, dict) else None
                # the endpoint can return {"series": {...}} or {"series": [...]} —
                # only a dict record is usable; anything else stays unmapped+flagged
                if isinstance(full, dict) and full.get("ticker"):
                    series_idx[st] = full
                    topic = series_topic(full)
                    topic_cache[st] = topic
            except Exception as e:  # never let one series kill the whole collection
                log_req(f"{DEMO_REST}/series/{st}", "error", f"enrichment skipped: {type(e).__name__}: {e}")
        if topic is None:
            # No official record => no topic. Record it instead of guessing, so the
            # Flagged page can show exactly which series could not be classified.
            unmapped_series[st] = unmapped_series.get(st, 0) + 1
            continue
        if topic not in TOPICS:
            continue
        # series metadata for the row below (was missing: NameError `series` crashed the
        # collector on the first in-scope market — see session eeb796d7 E-5 in COORDINATION.md)
        series = series_idx.get(st) or {}
        for m in ev.get("markets") or []:
            rows.append(market_row(topic, series, ev, m, "events"))

    # Near-term pass: union short-dated open markets the event pagination cannot reach.
    near = collect_near_term(signer, series_idx, topic_cache,
                             {r["market_ticker"] for r in rows if r.get("market_ticker")})
    rows.extend(near)

    # A series can exist in the catalogue with no live events at all (verified live for
    # DIESEL/DIESELM gas series in the demo environment). Record that explicitly so the
    # site can say "series exist, no live markets" instead of implying the topic is empty.
    catalog = {}
    for t in TOPICS:
        tickers = sorted([k for k, v in topic_cache.items() if v == t])
        catalog[t] = {
            "series_in_catalog": len(tickers),
            "series_tickers": tickers[:40],
            "series_with_live_markets": sorted({r["series_ticker"] for r in rows if r["topic"] == t}),
        }

    return {
        "series_index_size": len(series_idx),
        "topic_catalog": catalog,
        "events_scanned": len(events),
        "markets_in_scope": rows,
        "unmapped_series": dict(sorted(unmapped_series.items(), key=lambda kv: -kv[1])[:50]),
        "series_inventory": inventory(series_idx),
        "source_requests": ["GET /series", "GET /events?status=open&with_nested_markets=true",
                            "GET /markets?status=open&max_close_ts=<now+NEXT_TERM_HOURS>"],
        "near_term_added": len(near),
        "near_term_window_hours": NEXT_TERM_HOURS,
    }


def implied_dollar_volume(m: dict) -> float | None:
    """volume_fp x last_price_dollars. DOCUMENTED AS AN ESTIMATE, not an API field."""
    try:
        v = float(m.get("volume_fp") or "")
        p = float(m.get("last_price_dollars") or "")
    except (TypeError, ValueError):
        return None
    return round(v * p, 2)


def collect_orderbooks(rows: list[dict], signer: Signer | None, top_n: int = 12) -> dict:
    """GET /markets/{ticker}/orderbook for the largest markets.

    Per docs, the book returns yes bids and no bids only. A yes ask at price X is
    equivalent to a no bid at (1 - X), so we derive ask depth from the opposite side
    and label it 'derived' so nobody confuses it with a raw field.
    """
    ranked = sorted(rows, key=lambda r: (implied_dollar_volume(r) or 0), reverse=True)[:top_n]
    books: dict[str, dict] = {}
    for r in ranked:
        t = r["market_ticker"]
        j, status = get_json(f"{DEMO_REST}/markets/{urllib.parse.quote(t)}/orderbook?depth=25", signer)
        if not j:
            books[t] = {"error": f"HTTP {status}", "yes_bids": [], "no_bids": []}
            continue
        ob = j.get("orderbook_fp") or {}
        yes = [[float(p), float(q)] for p, q in (ob.get("yes_dollars") or [])]
        no = [[float(p), float(q)] for p, q in (ob.get("no_dollars") or [])]
        # best bid last in the raw arrays per docs; normalise to best-first here
        yes.sort(key=lambda x: x[0], reverse=True)
        no.sort(key=lambda x: x[0], reverse=True)
        # derived yes asks: a no bid at p is a yes ask at 1-p
        asks = sorted([[round(1 - p, 4), q] for p, q in no], key=lambda x: x[0])
        books[t] = {
            "yes_bids": yes,
            "no_bids": no,
            "derived_yes_asks": asks,
            "best_yes_bid": yes[0][0] if yes else None,
            "best_yes_ask_derived": asks[0][0] if asks else None,
            "yes_bid_contracts": round(sum(q for _, q in yes), 2),
            "derived_ask_contracts": round(sum(q for _, q in asks), 2),
            "spread_derived": (
                round(asks[0][0] - yes[0][0], 4) if asks and yes else None
            ),
            "raw_request": f"{DEMO_REST}/markets/{t}/orderbook?depth=25",
        }
    return books


def collect_candles(rows: list[dict], signer: Signer | None, top_n: int = 8) -> dict:
    """GET /series/{s}/markets/{t}/candlesticks with period_interval 1, 60, 1440.

    Docs: max 5000 periods/request, start_ts/end_ts in SECONDS.
    """
    ranked = sorted(rows, key=lambda r: (implied_dollar_volume(r) or 0), reverse=True)[:top_n]
    now = int(time.time())
    out: dict[str, dict] = {}
    for r in ranked:
        t, s = r["market_ticker"], r["series_ticker"]
        windows = {"1m": (1, 60 * 60 * 6), "1h": (60, 60 * 60 * 24 * 20), "1d": (1440, 60 * 60 * 24 * 120)}
        per: dict[str, Any] = {}
        for label, (interval, span) in windows.items():
            start = now - span
            url = (
                f"{DEMO_REST}/series/{urllib.parse.quote(s)}/markets/{urllib.parse.quote(t)}"
                f"/candlesticks?start_ts={start}&end_ts={now}&period_interval={interval}"
            )
            j, status = get_json(url, signer)
            if not j:
                per[label] = {"error": f"HTTP {status}", "candles": []}
                continue
            candles = []
            for c in j.get("candlesticks") or []:
                price = c.get("price") or {}
                bid = (c.get("yes_bid") or {}).get("close_dollars")
                ask = (c.get("yes_ask") or {}).get("close_dollars")
                # `price` is the TRADED price and is empty in any period with no trade
                # (verified live). The quoted mid is therefore derived so the chart has a
                # continuous line; it is labelled "derived" wherever it is shown.
                mid = None
                try:
                    if bid not in (None, "") and ask not in (None, ""):
                        mid = round((float(bid) + float(ask)) / 2, 4)
                except (TypeError, ValueError):
                    mid = None
                candles.append(
                    {
                        "ts": c.get("end_period_ts"),
                        "open": price.get("open_dollars"),
                        "high": price.get("high_dollars"),
                        "low": price.get("low_dollars"),
                        "close": price.get("close_dollars"),
                        "previous": price.get("previous_dollars"),
                        "mean": price.get("mean_dollars"),
                        "yes_ask_close": ask,
                        "yes_bid_close": bid,
                        "derived_mid": mid,
                        "volume_fp": c.get("volume_fp"),
                        "open_interest_fp": c.get("open_interest_fp"),
                    }
                )
            per[label] = {"period_interval": interval, "candles": candles, "raw_request": url}
        out[t] = per
    return out


def collect_resolutions(
    signer: Signer | None,
    series_by_topic: dict[str, list[str]] | None = None,
    limit_markets: int = 400,
) -> list[dict]:
    """Settled in-scope markets with the official yes/no `result` field.

    Rewritten by session 7085e643 (2026-11-20). The previous version paged
    `GET /markets?status=settled` from the beginning and filtered by topic afterwards,
    which produced `resolved_in_scope: 0` in every published snapshot: the demo exchange
    settles a continuous stream of out-of-scope hourly markets, so 10 pages x 200 rows
    never reached an in-scope one. Verified live 2026-11-20 while fixing this:
    `GET /markets?series_ticker=KXBTC&status=settled&limit=2` returns rows carrying
    `result: "no"`, `settlement_ts: "2026-11-20T07:08:44.987173Z"`,
    `settlement_value_dollars: "0.0000"`, while the unfiltered settled list at the same
    moment returns other series. `series_ticker`, `status` and `min_settled_ts` are all
    documented filters on Get Markets, so the fix queries per in-scope series inside a
    recent settlement window instead of scanning and hoping.
    """
    series_by_topic = series_by_topic or {}
    targets: list[tuple[str, str]] = []
    for topic in TOPICS:
        for st in (series_by_topic.get(topic) or [])[:RESOLUTION_MAX_SERIES]:
            targets.append((topic, st))

    window_start = int(time.time()) - RESOLUTION_WINDOW_DAYS * 86400
    rows: list[dict] = []
    for topic, st in targets:
        if len(rows) >= limit_markets:
            break
        url = (
            f"{DEMO_REST}/markets?series_ticker={urllib.parse.quote(st)}&status=settled"
            f"&min_settled_ts={window_start}&limit=200"
        )
        found: list[dict] = []
        cursor = ""
        for _ in range(2):  # bounded: 400 settled markets per series, newest window
            u = url + (f"&cursor={urllib.parse.quote(cursor, safe='')}" if cursor else "")
            j, status = get_json(u, signer)
            if not j:
                break
            found.extend(j.get("markets") or [])
            cursor = j.get("cursor") or ""
            if not cursor:
                break
        for m in found:
            ev = m.get("event_ticker") or ""
            # A `series_ticker` filter is a request, not a promise: keep the row only if
            # the returned record really belongs to the queried series, so a topic label
            # can never be attached to the wrong market.
            if not st or not str(ev).startswith(st + "-"):
                if m.get("ticker"):
                    log_req(url, 200, f"dropped {m['ticker']}: event_ticker {ev!r} is not under series {st!r}")
                continue
            rows.append(
                {
                    "topic": topic,
                    "series_ticker": st,
                    "event_ticker": ev,
                    "market_ticker": m.get("ticker"),
                    "status": m.get("status"),
                    "title": m.get("title"),
                    "yes_sub_title": m.get("yes_sub_title"),
                    # the official answer: "yes" / "no" ("" while the market is live)
                    "result": m.get("result") or "",
                    "settlement_value_dollars": m.get("settlement_value_dollars"),
                    "settlement_ts": m.get("settlement_ts"),
                    "close_time": m.get("close_time"),
                    "expiration_value": m.get("expiration_value"),
                    "volume_fp": m.get("volume_fp"),
                    "open_interest_fp": m.get("open_interest_fp"),
                    "last_price_dollars": m.get("last_price_dollars"),
                    "rules_primary_head": (m.get("rules_primary") or "")[:160] or None,
                    # every row links the exact official request that produced it
                    "market_url": f"{DEMO_REST}/markets/{m.get('ticker')}" if m.get("ticker") else None,
                    "event_url": f"{DEMO_REST}/events/{ev}" if ev else None,
                    "resolution_query_url": url,
                }
            )
            if len(rows) >= limit_markets:
                break

    dedup: dict[str, dict] = {}
    for r in rows:
        if r["market_ticker"]:
            dedup[r["market_ticker"]] = r
    out = list(dedup.values())
    out.sort(key=lambda r: (r.get("settlement_ts") or ""), reverse=True)
    return out


def exchange_status(signer: Signer | None) -> dict:
    j, status = get_json(DEMO_REST + "/exchange/status", signer)
    return {"http_status": status, "response": j}


# ------------------------------------------------------------ publish selection
def pub_rank_key(r: dict):
    """Descending by the labelled est. dollar volume, ties broken by ticker, so two
    runs over the same data select exactly the same rows (deterministic, auditable)."""
    v = r.get("est_dollar_volume")
    return (-(v if isinstance(v, (int, float)) else -1.0), str(r.get("market_ticker") or ""))


def select_publish(rows: list[dict], cap_per_topic: int) -> dict[str, list[dict]]:
    """Top `cap_per_topic` rows per in-scope topic. Nothing is invented or merged: a
    published row is the same object the collector built from the API response."""
    per: dict[str, list[dict]] = {}
    for t in TOPICS:
        per[t] = sorted([r for r in rows if r.get("topic") == t], key=pub_rank_key)[:cap_per_topic]
    return per


def payload_bytes(obj: Any) -> int:
    return len(json.dumps(obj, indent=1).encode())


# --------------------------------------------------------------------------- main
def write_json(name: str, payload: Any, where: Path | None = None) -> None:
    out_dir = where or DATA
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / name
    p.write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n")
    try:
        shown = p.relative_to(ROOT)
    except ValueError:  # DATA relocated (tests, --out elsewhere) — print the real path
        shown = p
    print(f"wrote {shown} ({p.stat().st_size:,} bytes)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope-only", action="store_true", help="skip candles/books (fast path)")
    ap.add_argument("--dry-run", action="store_true",
                    help="collect and size the payload, write nothing (pipeline check)")
    args = ap.parse_args()

    signer = signer_from_env()
    started = dt.datetime.now(dt.timezone.utc)
    status = exchange_status(signer)

    scope = collect_scope(signer)
    universe = scope["markets_in_scope"]

    # enrich with the estimate, clearly named as such (computed here, not an API field)
    for r in universe:
        r["est_dollar_volume"] = implied_dollar_volume(r)

    # ---- bound the PUBLISHED payload; the universe stays complete in data/out/ ----
    cap = PUB_MAX_ROWS_PER_TOPIC
    per_topic: dict[str, list[dict]] = {}
    snapshot: dict[str, Any] = {}
    for _attempt in range(6):
        per_topic = select_publish(universe, cap)
        pub_rows = [r for t in TOPICS for r in per_topic[t]]
        snapshot = build_snapshot(signer, started, status, scope, pub_rows, universe, cap, args.scope_only)
        if payload_bytes(snapshot) <= PUB_MAX_BYTES or cap <= 60:
            break
        cap = max(60, cap // 2)
        print(f"publish budget exceeded ({PUB_MAX_BYTES:,} bytes) - halving rows/topic to {cap}",
              file=sys.stderr)

    if not args.dry_run:
        write_json("snapshot.json", snapshot)
        for topic in TOPICS:
            write_json(
                f"topic-{topic}.json",
                {
                    "generated_at_utc": snapshot["generated_at_utc"],
                    "topic": topic,
                    "count": len(per_topic[topic]),
                    "universe_count": sum(1 for r in universe if r["topic"] == topic),
                    "publish_cap_per_topic": cap,
                    "markets": per_topic[topic],
                    "resolutions": [r for r in snapshot["resolutions"] if r["topic"] == topic],
                },
            )
        write_json("resolutions.json", {
            "generated_at_utc": snapshot["generated_at_utc"],
            "count": len(snapshot["resolutions"]),
            "window_days": RESOLUTION_WINDOW_DAYS,
            "resolutions": snapshot["resolutions"],
        })
        append_history(snapshot, universe)

        # Full universe, unbounded: written for the run artifact, never committed
        # (data/out/ is gitignored). It is the evidence trail behind the counts.
        write_json("full_snapshot.json", {
            "generated_at_utc": snapshot["generated_at_utc"],
            "note": "Complete collected universe; data/snapshot.json is the bounded "
                    "publish payload of this same collection run.",
            "counts": snapshot["counts"],
            "markets": universe,
            "resolutions": snapshot["resolutions"],
            "api_log": snapshot["api_log"],
        }, where=OUT_DIR)

    c = snapshot["counts"]
    print(f"OK  universe={c['markets_in_scope']}  published={c['published_markets']}  "
          f"cap/topic={c['publish_cap_per_topic']}  resolved={c['resolved_in_scope']}  "
          f"books={c['orderbooks']}  candles={c['candle_sets']}  "
          f"snapshot={payload_bytes(snapshot):,} bytes  auth={signer is not None}")
    if not universe:
        print("WARNING: zero in-scope markets returned — scope filter or API issue.", file=sys.stderr)
    return 0


def build_snapshot(signer, started, status, scope, pub_rows, universe, cap, skip_books: bool) -> dict:
    """Assemble the published snapshot payload.

    Differences from the pre-2026-11-20 version, both forced by the file-size outage:
      * `by_topic` is GONE. It was a second full copy of `markets` (20.23 MB of the
        47.26 MB file); pages already read the per-topic files, and anything that needs
        the grouping can derive it from `markets` in one line.
      * `markets` holds the bounded published selection; the universe size is published
        next to it in `coverage` and `counts` so the page can never imply completeness.
      * `api_log` is trimmed to the last API_LOG_KEEP entries (full log stays in the
        run artifact).
    """
    per_topic_count = {t: sum(1 for r in universe if r["topic"] == t) for t in TOPICS}
    books = {} if skip_books else collect_orderbooks(pub_rows, signer)
    candles = {} if skip_books else collect_candles(pub_rows, signer)
    resolutions = collect_resolutions(signer, (scope.get("series_inventory") or {}).get("in_scope_series"))
    finished = dt.datetime.now(dt.timezone.utc)
    return {
        "generated_at_utc": finished.isoformat(timespec="seconds"),
        "started_at_utc": started.isoformat(timespec="seconds"),
        "environment": "demo",
        "rest_base": DEMO_REST,
        "authenticated": signer is not None,
        "exchange_status": status,
        "series_inventory": scope["series_inventory"],
        "topic_catalog": scope["topic_catalog"],
        "unmapped_series": scope["unmapped_series"],
        "publish_policy": {
            "why": "GitHub declines a push containing any file over 100 MB (111.97 MB "
                   "snapshot.json on 2026-11-20 killed every data refresh), and a browser "
                   "should not have to download a 47 MB file to render a dashboard.",
            "selection": "top rows per topic by the labelled est_dollar_volume estimate, "
                         "ties broken by ticker; rows are unmodified API fields",
            "cap_per_topic": cap,
            "max_bytes": PUB_MAX_BYTES,
            "full_universe": "data/out/full_snapshot.json (run artifact, not committed)",
        },
        "coverage": {
            "universe_markets": len(universe),
            "published_markets": len(pub_rows),
            "near_term_markets_added": scope.get("near_term_added"),
            "near_term_window_hours": scope.get("near_term_window_hours"),
            "per_topic_universe": per_topic_count,
            "per_topic_published": {t: sum(1 for r in pub_rows if r["topic"] == t) for t in TOPICS},
            "complete_enumeration": False,
            "statement": "This snapshot is a bounded publish payload of the in-scope "
                         "universe collected in the same run, not a complete enumeration "
                         "of the exchange.",
        },
        "counts": {
            "series_index": scope["series_index_size"],
            "events_scanned": scope["events_scanned"],
            "markets_in_scope": len(universe),
            "published_markets": len(pub_rows),
            "publish_cap_per_topic": cap,
            "per_topic": {t: sum(1 for r in pub_rows if r["topic"] == t) for t in TOPICS},
            "resolved_in_scope": len(resolutions),
            "orderbooks": len(books),
            "candle_sets": len(candles),
        },
        "markets": pub_rows,
        "orderbooks": books,
        "candles": candles,
        "resolutions": resolutions,
        "definitions": {
            "est_dollar_volume": (
                "ESTIMATE = volume_fp x last_price_dollars, computed by this collector. "
                "The API exposes no single dollar-volume field. Label is shown in the UI."
            ),
            "derived_yes_asks": (
                "Derived, not raw: a NO bid at price p is equivalent to a YES ask at 1-p "
                "(Kalshi orderbook docs). Shown so ask-side depth and spread are visible."
            ),
            "result": "Official market field. 'yes' or 'no' once settled; empty while live.",
            "derived_mid": (
                "Derived, not raw: (yes_bid_close + yes_ask_close) / 2 per candlestick. The "
                "candlestick `price` object is the TRADED price and is empty in any period with "
                "no trade, so this keeps the chart continuous without inventing a traded price."
            ),
        },
        "api_log": API_LOG[-API_LOG_KEEP:],
        "api_log_total_requests": len(API_LOG),
    }


def append_history(snapshot: dict, universe: list[dict]) -> None:
    """One compact point per PUBLISHED market per run, for the price chart.

    Bounded twice over (session 7085e643): only markets in the published selection get
    a point, and each market keeps the last HISTORY_MAX_POINTS points. Previously every
    in-scope market appended every run, so the ledger grew toward
    (markets x 288 x ~60 bytes) and became a second route to the 100 MB wall.
    """
    watch = {r["market_ticker"] for r in snapshot["markets"] if r.get("market_ticker")}
    hist_path = DATA / "history.json"
    hist = json.loads(hist_path.read_text()) if hist_path.exists() else {"points": {}}
    pts = hist.setdefault("points", {})
    pts = {k: v for k, v in pts.items() if k in watch}   # drop unpublished history
    hist["points"] = pts
    finished = dt.datetime.now(dt.timezone.utc)
    for r in snapshot["markets"]:
        t = r["market_ticker"]
        lp = r.get("last_price_dollars")
        if lp in (None, ""):
            continue
        pts.setdefault(t, []).append(
            {"t": int(finished.timestamp()), "last": lp, "yes_bid": r.get("yes_bid_dollars"),
             "yes_ask": r.get("yes_ask_dollars")}
        )
        pts[t] = pts[t][-HISTORY_MAX_POINTS:]
    hist["updated_at_utc"] = snapshot["generated_at_utc"]
    hist["policy"] = {
        "markets": len(pts),
        "max_points_per_market": HISTORY_MAX_POINTS,
        "note": "history is kept only for markets in the published selection",
    }
    write_json("history.json", hist)


if __name__ == "__main__":
    sys.exit(main())
