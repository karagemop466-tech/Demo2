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

# --- deterministic output-size bounds -----------------------------------------
# Why these exist (verified incident, 2026-11-20): GitHub rejects a push containing
# any file over 100 MB ("pre-receive declined"), and data/snapshot.json reached
# 112 MB (mostly duplicated rows + legal rules text). Every `Refresh Kalshi demo
# data` run then failed at the commit step for hours (runs 44728913873 … 44800417665)
# and the published data went stale. The collector therefore (a) publishes only the
# TOP_N rows per topic by estimated dollar volume — which is exactly the product
# focus ("highest dollar amount live events") — (b) never stores the same market row
# twice, (c) writes compact JSON, and (d) refuses to write any file over
# FILE_LIMIT_BYTES so the failure mode is a loud, immediate collector error instead
# of an opaque push rejection. Nothing is invented when trimming: dropped rows are
# counted in `counts.markets_trimmed_per_topic` and the full in-scope count is kept
# in `counts.markets_in_scope`.
PUBLISH_PER_TOPIC = 1200
HISTORY_TICKERS_MAX = 600      # tick history is kept for the largest markets only
HISTORY_POINTS_MAX = 288       # per ticker (288 x 10-min runs = 48 h)
FILE_LIMIT_BYTES = 90_000_000  # hard tripwire; GitHub's push limit is 100 MB/file

# Fields that tools/check.py requires on every market row, even when null.
ROW_REQUIRED_KEYS = ("topic", "market_ticker", "yes_bid_dollars", "yes_ask_dollars", "volume_fp")

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
# Unauthenticated public requests have their own documented limits and the docs say
# plainly to back off on 429 (https://docs.kalshi.com/getting_started/rate_limits).
# The 2026-11-21T00:53Z snapshot logged 44 429s and 105 404s out of 1,606 requests;
# the 429s hit the per-series enrichment calls, which fire back-to-back. A small
# minimum interval, plus Retry-After support, removes the storm without guessing at a
# private limit that the docs do not publish.
MIN_REQUEST_INTERVAL_S = 0.12
_LAST_REQUEST_AT = 0.0
FETCH_WARNINGS: list[str] = []


def _throttle() -> None:
    global _LAST_REQUEST_AT
    wait = MIN_REQUEST_INTERVAL_S - (time.monotonic() - _LAST_REQUEST_AT)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_AT = time.monotonic()


def get_json(url: str, signer: Signer | None = None, retries: int = 4) -> tuple[Any, int]:
    """GET a URL, return (parsed_json_or_None, http_status). Logs every attempt."""
    last_status: int | str = "no-attempt"
    for attempt in range(retries):
        _throttle()
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
            # Honour Retry-After when the server sends one (documented 429 behaviour).
            retry_after = 0.0
            try:
                retry_after = float((e.headers or {}).get("Retry-After") or 0)
            except (TypeError, ValueError):
                retry_after = 0.0
            time.sleep(retry_after if retry_after > 0 else 1.5 * (attempt + 1))
        except Exception as e:  # network/TLS/timeout
            last_status = type(e).__name__
            log_req(url, last_status, str(e)[:200])
            time.sleep(1.5 * (attempt + 1))
    return None, int(last_status) if isinstance(last_status, int) else 0


def paginate(url: str, key: str, signer: Signer | None = None, max_pages: int = 30,
             page_limit: int = 200) -> list[dict]:
    """Cursor pagination exactly as documented in getting_started/pagination.md.

    `limit` maximum is 1000 (Get Markets). The default stays 200 for the large
    open-event sweep; settled-market sweeps ask for 1000 to cover more history.
    Docs: https://docs.kalshi.com/api-reference/market/get-markets
    """
    out: list[dict] = []
    cursor = ""
    for _ in range(max_pages):
        u = url + ("&" if "?" in url else "?") + f"limit={page_limit}"
        if cursor:
            u += "&cursor=" + urllib.parse.quote(cursor, safe="")
        j, status = get_json(u, signer)
        if not j:
            # A failed page truncates the sweep. Silence would make the published count
            # look complete when it is only a floor, so the reason is recorded and
            # published with the snapshot (`fetch_warnings`).
            FETCH_WARNINGS.append(
                f"pagination stopped after {len(out)} rows on page {_ + 1} of {max_pages}: "
                f"HTTP {status} for {u}")
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
            rows.append(
                {
                    "topic": topic,
                    "event_ticker": ev.get("event_ticker"),
                    "series_ticker": st,
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
                    "close_time": m.get("close_time"),
                    "open_time": m.get("open_time"),
                    "updated_time": m.get("updated_time"),
                    "price_level_structure": m.get("price_level_structure"),
                    # Full rules text omitted for file size (the 2026-11-20 run hit
                    # GitHub's 100 MB file limit: snapshot.json 112 MB, mostly legal
                    # text). The verbatim prefix is kept as `rules_primary_head`
                    # (clearly named) and the FULL rules stay reachable at the row's
                    # official `market_url`. Nothing inferred or rewritten.
                    "rules_primary_head": (m.get("rules_primary") or "")[:160] or None,
                    "exchange_index": m.get("exchange_index"),
                    "settlement_sources": ev.get("settlement_sources"),
                    "series_category": series.get("category"),
                    "series_categories": series.get("categories"),
                    "contract_terms_url": series.get("contract_terms_url"),
                    "contract_url": series.get("contract_url"),
                    # Verifiable official link only: the exact API endpoint that produced
                    # this row. A human web-UI market URL could not be confirmed from an
                    # official source, so it is not invented (blank + flagged on the site).
                    "event_url": f"{DEMO_REST}/events/{ev.get('event_ticker')}",
                    "market_url": f"{DEMO_REST}/markets/{m.get('ticker')}",
                }
            )
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
        "source_requests": ["GET /series", "GET /events?status=open&with_nested_markets=true"],
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


# Evidence for the resolutions page: which request produced the rows. Kept module-level
# so main() can publish it next to the rows (a value with no traceable request is unusable).
RESOLUTION_QUERY: dict = {}


def collect_resolutions(signer: Signer | None, limit_markets: int = 400,
                        window_days: int = 30) -> list[dict]:
    """Settled in-scope markets with the official yes/no `result`.

    Two defects were found in the previous implementation and are fixed here
    (evidence: data/resolutions.json had `count: 0` at 2026-11-21T00:53Z while the same
    API returned 200 settled crypto markets to data/resolved.json at 03:17Z):

    1. No settled-time filter. `GET /markets?status=settled` without a `_ts` filter has
       no guaranteed order, so the first pages were old/unmapped series and every row
       was dropped. `min_settled_ts` is the documented filter and a `_ts`-filtered
       listing is sorted by settlement time, latest first.
       https://docs.kalshi.com/api-reference/market/get-markets
    2. Series ticker = `event_ticker.split("-")[0]`. That is wrong for real series
       tickers containing a dash (e.g. `GOVPARTY-NH`), so those rows never matched the
       series index either. The longest leading segment that IS a known series wins.

    A 365-day window is tried only if the 30-day window returns nothing; which window
    produced the rows is published in RESOLUTION_QUERY. No value is invented — a market
    whose topic cannot be mapped from an official record is skipped and counted nowhere.
    """
    series_idx = load_series_index(signer)
    topic_cache: dict[str, str | None] = {}

    def topic_for(st: str) -> str | None:
        if st in topic_cache:
            return topic_cache[st]
        topic = series_topic(series_idx.get(st))
        if topic is None and st:
            # The bare /series list omits product_metadata (used for the AAA gasoline
            # family); GET /series/{ticker} includes it. Official data only.
            try:
                j2, _ = get_json(f"{DEMO_REST}/series/{st}", signer)
                full = (j2 or {}).get("series") if isinstance(j2, dict) else None
                if isinstance(full, dict) and full.get("ticker"):
                    series_idx[st] = full
                    topic = series_topic(full)
            except Exception as e:
                log_req(f"{DEMO_REST}/series/{st}", "error",
                        f"resolution enrichment skipped: {type(e).__name__}: {e}")
        topic_cache[st] = topic
        return topic

    def series_of(ev: str) -> str:
        parts = [p for p in (ev or "").split("-") if p]
        for i in range(len(parts), 0, -1):
            cand = "-".join(parts[:i])
            if cand in series_idx:
                return cand
        return parts[0] if parts else ""

    for window in (window_days, 365):
        since = int(time.time()) - window * 86400
        url = f"{DEMO_REST}/markets?status=settled&min_settled_ts={since}"
        settled = paginate(url, "markets", signer, max_pages=12, page_limit=1000)
        rows = _resolution_rows(settled, series_of, topic_for, limit_markets)
        RESOLUTION_QUERY.clear()
        RESOLUTION_QUERY.update({
            "request": url,
            "window_days": window,
            "markets_scanned": len(settled),
            "rows_in_scope": len(rows),
            "docs": "https://docs.kalshi.com/api-reference/market/get-markets",
        })
        if rows:
            return rows
    return []


def _resolution_rows(settled: list[dict], series_of, topic_for,
                     limit_markets: int) -> list[dict]:
    """Map settled markets to topics and keep only rows whose official result exists."""
    rows: list[dict] = []
    for m in settled:
        ev = m.get("event_ticker") or ""
        st = series_of(ev)
        topic = topic_for(st)
        if topic not in TOPICS:
            continue
        # The brief asks whether an event resolved yes or no. A settled market without
        # either value is not shown as an outcome — it is skipped, never assumed.
        result = str(m.get("result") or "").lower()
        if result not in ("yes", "no"):
            continue
        rows.append(
            {
                "topic": topic,
                "series_ticker": st,
                "event_ticker": ev,
                "market_ticker": m.get("ticker"),
                "status": m.get("status"),
                "title": m.get("title"),
                "result": result,                          # official yes / no
                "settlement_value_dollars": m.get("settlement_value_dollars"),
                "settlement_ts": m.get("settlement_ts"),
                "close_time": m.get("close_time"),
                "expiration_value": m.get("expiration_value"),
                "volume_fp": m.get("volume_fp"),
                "open_interest_fp": m.get("open_interest_fp"),
                "rules_primary_head": (m.get("rules_primary") or "")[:160] or None,
                "market_url": f"{DEMO_REST}/markets/{m.get('ticker')}" if m.get("ticker") else None,
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


# --------------------------------------------------------------------------- main
def write_json(name: str, payload: Any, compact: bool = False) -> None:
    DATA.mkdir(exist_ok=True)
    p = DATA / name
    if compact:
        text = json.dumps(payload, separators=(",", ":"), sort_keys=False) + "\n"
    else:
        text = json.dumps(payload, indent=1, sort_keys=False) + "\n"
    if len(text.encode("utf-8")) > FILE_LIMIT_BYTES:
        # Fail here, loudly, instead of letting GitHub reject the push later
        # (GitHub's pre-receive hook refuses any file over 100 MB — the incident
        # documented at the FILE_LIMIT_BYTES constant above).
        print(f"::error::data/{name} would be {len(text)} bytes > {FILE_LIMIT_BYTES} "
              f"- refusing to write (tighten PUBLISH_PER_TOPIC bounds, do not push)")
        raise SystemExit(2)
    p.write_text(text)
    try:
        shown = p.relative_to(ROOT)
    except ValueError:  # tests redirect DATA outside the repo; keep the message useful
        shown = p
    print(f"wrote {shown} ({p.stat().st_size} bytes)")


def slim_row(r: dict) -> dict:
    """Drop null fields, keeping the check.py-required keys on every row.

    Applied only at write time: collect_scope still builds full rows, so offline
    tests that inspect its return value are unaffected. Nothing is rewritten or
    inferred — nulls are simply omitted and the site renders an em dash for a
    missing field (the pages already handle absent keys).
    """
    return {k: v for k, v in r.items() if v is not None or k in ROW_REQUIRED_KEYS}


def select_published(rows: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Top PUBLISH_PER_TOPIC rows per topic by estimated dollar volume.

    Returns (published_rows, trimmed_per_topic). The product scope is the
    "highest dollar amount live events"; trimming is recorded in `counts` and
    never silent. Rows with no estimate sort last but are still eligible.
    """
    published: list[dict] = []
    trimmed: dict[str, int] = {}
    for t in TOPICS:
        tr = [r for r in rows if r["topic"] == t]
        tr.sort(key=lambda r: (r.get("est_dollar_volume") is not None,
                               r.get("est_dollar_volume") or -1), reverse=True)
        keep, drop = tr[:PUBLISH_PER_TOPIC], tr[PUBLISH_PER_TOPIC:]
        published.extend(keep)
        trimmed[t] = len(drop)
    return published, trimmed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope-only", action="store_true", help="skip candles/books (fast path)")
    args = ap.parse_args()

    signer = signer_from_env()
    started = dt.datetime.now(dt.timezone.utc)
    status = exchange_status(signer)

    scope = collect_scope(signer)
    rows = scope["markets_in_scope"]

    # enrich with the estimate, clearly named as such
    for r in rows:
        r["est_dollar_volume"] = implied_dollar_volume(r)

    books = {} if args.scope_only else collect_orderbooks(rows, signer)
    candles = {} if args.scope_only else collect_candles(rows, signer)
    resolutions = collect_resolutions(signer)

    # Publish the largest markets per topic (product scope: "highest dollar amount
    # live events"). Full in-scope counts are kept; trimmed counts are recorded.
    by_topic_full = {t: [r for r in rows if r["topic"] == t] for t in TOPICS}
    for t in TOPICS:
        by_topic_full[t].sort(key=lambda r: (r.get("est_dollar_volume") is not None,
                                             r.get("est_dollar_volume") or -1), reverse=True)
    published, trimmed = select_published(rows)
    pub_by_topic = {t: [r for r in published if r["topic"] == t] for t in TOPICS}
    # by_topic holds market tickers only — the full rows are published exactly once
    # (in `markets` and in data/topic-<t>.json). The previous full-row duplication
    # here doubled snapshot.json and fed the 100 MB push failure (see write_json).
    by_topic = {t: [r["market_ticker"] for r in pub_by_topic[t]] for t in TOPICS}

    finished = dt.datetime.now(dt.timezone.utc)
    snapshot = {
        "generated_at_utc": finished.isoformat(timespec="seconds"),
        "started_at_utc": started.isoformat(timespec="seconds"),
        "environment": "demo",
        "rest_base": DEMO_REST,
        "authenticated": signer is not None,
        "exchange_status": status,
        "series_inventory": scope["series_inventory"],
        "topic_catalog": scope["topic_catalog"],
        "unmapped_series": scope["unmapped_series"],
        "counts": {
            "series_index": scope["series_index_size"],
            "events_scanned": scope["events_scanned"],
            "markets_in_scope": len(rows),
            "per_topic": {t: len(by_topic_full[t]) for t in TOPICS},
            "markets_published": len(published),
            "markets_trimmed_per_topic": trimmed,
            "resolved_in_scope": len(resolutions),
            "orderbooks": len(books),
            "candle_sets": len(candles),
        },
        "markets": [slim_row(r) for r in published],
        "by_topic": by_topic,
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
            "published_rows": (
                "markets holds the top rows per topic by est_dollar_volume (see "
                "PUBLISH_PER_TOPIC in tools/collector.py); by_topic holds those rows' "
                "market_ticker values only. counts.markets_in_scope is the full count; "
                "counts.markets_trimmed_per_topic records what was left out and why."
            ),
        },
        "api_log": API_LOG,
        "fetch_warnings": FETCH_WARNINGS,
    }
    write_json("snapshot.json", snapshot, compact=True)

    # per-topic files keep each category page payload small (slim rows, compact JSON)
    for t in TOPICS:
        write_json(
            f"topic-{t}.json",
            {
                "generated_at_utc": snapshot["generated_at_utc"],
                "topic": t,
                "count": len(pub_by_topic[t]),
                "count_in_scope": len(by_topic_full[t]),
                "trimmed_by_volume": trimmed[t],
                "markets": [slim_row(r) for r in pub_by_topic[t]],
                "resolutions": [r for r in resolutions if r["topic"] == t],
            },
            compact=True,
        )

    write_json("resolutions.json", {"generated_at_utc": snapshot["generated_at_utc"],
                                    "count": len(resolutions),
                                    "query": RESOLUTION_QUERY or None,
                                    "resolutions": resolutions})

    # history ledger: append one compact point per market per run (for the price chart).
    # Bounded on purpose: only the HISTORY_TICKERS_MAX largest published markets keep a
    # tick history, capped at HISTORY_POINTS_MAX points each, so history.json can never
    # grow toward GitHub's per-file push limit as runs accumulate (it would otherwise
    # gain points for every market on every run, forever).
    hist_path = DATA / "history.json"
    hist = json.loads(hist_path.read_text()) if hist_path.exists() else {"points": {}}
    pts = hist.setdefault("points", {})
    ranked = sorted(published, key=lambda r: (r.get("est_dollar_volume") is not None,
                                              r.get("est_dollar_volume") or -1), reverse=True)
    hist_keep = {r["market_ticker"] for r in ranked[:HISTORY_TICKERS_MAX]}
    for stale in [k for k in pts if k not in hist_keep]:
        del pts[stale]
    for r in published:
        t = r["market_ticker"]
        if t not in hist_keep:
            continue
        lp = r.get("last_price_dollars")
        yb = r.get("yes_bid_dollars")
        if lp in (None, ""):
            continue
        pts.setdefault(t, []).append(
            {"t": int(finished.timestamp()), "last": lp, "yes_bid": yb,
             "yes_ask": r.get("yes_ask_dollars")}
        )
        pts[t] = pts[t][-HISTORY_POINTS_MAX:]
    hist["updated_at_utc"] = snapshot["generated_at_utc"]
    hist["definitions"] = {
        "points": (
            f"tick samples taken by each collector run (10-min cadence); kept for the "
            f"top {HISTORY_TICKERS_MAX} markets by est_dollar_volume, max "
            f"{HISTORY_POINTS_MAX} points each"
        ),
    }
    write_json("history.json", hist, compact=True)

    print(f"OK  in-scope markets={len(rows)}  published={len(published)}  "
          f"trimmed={trimmed}  resolved={len(resolutions)}  "
          f"books={len(books)}  auth={signer is not None}")
    if not rows:
        print("WARNING: zero in-scope markets returned — scope filter or API issue.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
