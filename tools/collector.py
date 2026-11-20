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

# The ROI model lives next to the collector so both write the same numbers.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import roi_model  # noqa: E402

# --- endpoints (verified: docs.kalshi.com/getting_started/api_environments.md) ----
DEMO_REST = "https://external-api.demo.kalshi.co/trade-api/v2"
PROD_REST = "https://external-api.kalshi.com/trade-api/v2"

# In-scope topics only (user requirement). Matching is done on the OFFICIAL Kalshi
# `series.category` / series ticker, not on free-text guesses — see TOPIC_RULES.
TOPICS = ["gas", "elections", "culture", "crypto", "golf"]

# Size caps for the committed tick history. Without them the ledger grows without
# bound (10,241 markets x 288 points) and every scheduled run pushes megabytes.
HISTORY_MARKETS = 400
HISTORY_POINTS = 72

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
def collect_scope(signer: Signer | None) -> dict:
    """Open markets for the in-scope topics, plus their event/series metadata."""
    series_idx = load_series_index(signer)
    topic_cache = {t: series_topic(s) for t, s in series_idx.items()}
    events = paginate(DEMO_REST + "/events?status=open&with_nested_markets=true", "events", signer,
                      max_pages=50)

    rows: list[dict] = []
    unmapped_series: dict[str, int] = {}
    enriched: set[str] = set()
    events_meta: dict[str, dict] = {}
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
        ev_ticker = ev.get("event_ticker")
        if ev_ticker and ev_ticker not in events_meta:
            # Event-level metadata, stored once instead of on every market row.
            # `settlement_sources` is an official field of the EVENT object
            # (https://docs.kalshi.com/api-reference/events/get-events) - verified live
            # on GET /events/{event_ticker} in the demo environment.
            events_meta[ev_ticker] = {
                "event_ticker": ev_ticker,
                "topic": topic,
                "series_ticker": st,
                "title": ev.get("title"),
                "sub_title": ev.get("sub_title"),
                "category": ev.get("category"),
                "mutually_exclusive": ev.get("mutually_exclusive"),
                "settlement_sources": [
                    {"name": s.get("name"), "url": s.get("url")}
                    for s in (ev.get("settlement_sources") or [])
                ],
                "series_category": series.get("category"),
                "series_categories": series.get("categories"),
                "contract_terms_url": series.get("contract_terms_url"),
                "contract_url": series.get("contract_url"),
                "event_url": f"{DEMO_REST}/events/{ev_ticker}",
                "market_count": len(ev.get("markets") or []),
            }
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
                    # `settlement_sources` and the series-level contract URLs are the
                    # same for every market of an event/series, so they are stored once
                    # per event in data/events.json instead of on every market row.
                    # `settlement_source_count` keeps the count visible on the row.
                    "settlement_source_count": len(ev.get("settlement_sources") or []),
                    "series_category": series.get("category"),
                    "series_categories": series.get("categories"),
                    # Verifiable official link only: the exact API endpoint that produced
                    # this row. A human web-UI market URL could not be confirmed from an
                    # official source, so it is not invented (blank + flagged on the site).
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
        "events_meta": events_meta,
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


def collect_resolutions(signer: Signer | None, limit_markets: int = 400) -> list[dict]:
    """Settled in-scope markets with the official yes/no `result`."""
    settled = paginate(DEMO_REST + "/markets?status=settled", "markets", signer, max_pages=10)
    series_idx = load_series_index(signer)
    topic_cache = {t: series_topic(s) for t, s in series_idx.items()}
    rows: list[dict] = []
    for m in settled:
        ev = m.get("event_ticker") or ""
        # The series ticker is the leading segment of the event ticker.
        st = ev.split("-")[0] if ev else ""
        topic = topic_cache.get(st)
        if topic not in TOPICS:
            continue
        rows.append(
            {
                "topic": topic,
                "series_ticker": st,
                "event_ticker": ev,
                "market_ticker": m.get("ticker"),
                "status": m.get("status"),
                "title": m.get("title"),
                "result": m.get("result") or "",          # "yes" / "no" / ""
                "settlement_value_dollars": m.get("settlement_value_dollars"),
                "settlement_ts": m.get("settlement_ts"),
                "close_time": m.get("close_time"),
                "expiration_value": m.get("expiration_value"),
                "volume_fp": m.get("volume_fp"),
                "open_interest_fp": m.get("open_interest_fp"),
                # Kept so the simulated-strategy backtest can price an entry and score
                # the same market with the same model (tools/roi_model.py).
                "last_price_dollars": m.get("last_price_dollars"),
                "yes_bid_dollars": m.get("yes_bid_dollars"),
                "yes_ask_dollars": m.get("yes_ask_dollars"),
                "yes_bid_size_fp": m.get("yes_bid_size_fp"),
                "yes_ask_size_fp": m.get("yes_ask_size_fp"),
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


def collect_trades(rows: list[dict], signer: Signer | None, pages: int = 3) -> list[dict]:
    """GET /markets/trades - every completed transaction on the demo exchange.

    Docs: https://docs.kalshi.com/api-reference/market/get-trades
      limit    0..1000 (default 100)
      cursor   pagination cursor
      min_ts   only items after this unix timestamp
      max_ts   only items before this unix timestamp

    The endpoint returns trades for ALL markets, so the rows are filtered to the
    in-scope topics. The prints are the rawest live signal the API gives us and are
    what the two chat feeds on the site are built from.
    """
    scope_tickers = {r["market_ticker"] for r in rows if r.get("market_ticker")}
    topic_of = {r["market_ticker"]: r.get("topic") for r in rows if r.get("market_ticker")}
    title_of = {r["market_ticker"]: (r.get("market_title") or r.get("event_title")) for r in rows}
    out: list[dict] = []
    cursor = ""
    for _ in range(max(1, pages)):
        url = DEMO_REST + "/markets/trades?limit=1000"
        if cursor:
            url += "&cursor=" + urllib.parse.quote(cursor)
        j, status = get_json(url, signer)
        if not j:
            break
        batch = j.get("trades") or []
        for t in batch:
            tk = t.get("ticker")
            if tk not in scope_tickers:
                continue
            out.append(
                {
                    "trade_id": t.get("trade_id"),
                    "ticker": tk,
                    "topic": topic_of.get(tk),
                    "title": title_of.get(tk),
                    "count_fp": t.get("count_fp"),
                    "yes_price_dollars": t.get("yes_price_dollars"),
                    "no_price_dollars": t.get("no_price_dollars"),
                    "taker_side": t.get("taker_side"),
                    "taker_book_side": t.get("taker_book_side"),
                    "is_block_trade": t.get("is_block_trade"),
                    "created_time": t.get("created_time"),
                }
            )
        cursor = j.get("cursor") or ""
        if not cursor or not batch:
            break
    out.sort(key=lambda t: str(t.get("created_time") or ""), reverse=True)
    return out


def detect_jumps(trades: list[dict], threshold: float = 0.10) -> list[dict]:
    """Price moves of at least `threshold` dollars between consecutive prints.

    Only consecutive prints of the SAME market are compared, and only prints that
    carry a yes price. The cause of a move is not in the API, so no cause is recorded
    here - the site links the market and flags the cause as unverified.
    """
    by_ticker: dict[str, list[dict]] = {}
    for t in trades:
        p = t.get("yes_price_dollars")
        if p in (None, ""):
            continue
        try:
            price = float(p)
        except (TypeError, ValueError):
            continue
        by_ticker.setdefault(t["ticker"], []).append(
            {
                "t": t.get("created_time"),
                "price": price,
                "count_fp": t.get("count_fp"),
                "trade_id": t.get("trade_id"),
            }
        )
    jumps: list[dict] = []
    for ticker, pts in by_ticker.items():
        pts.sort(key=lambda x: str(x["t"] or ""))
        for a, b in zip(pts, pts[1:]):
            change = b["price"] - a["price"]
            if abs(change) >= threshold:
                jumps.append(
                    {
                        "ticker": ticker,
                        "topic": next((t.get("topic") for t in trades if t["ticker"] == ticker), None),
                        "from_time": a["t"],
                        "to_time": b["t"],
                        "from_price": a["price"],
                        "to_price": b["price"],
                        "change": round(change, 4),
                        "direction": "up" if change > 0 else "down",
                        "to_count_fp": b.get("count_fp"),
                        "to_trade_id": b.get("trade_id"),
                        "cause": None,
                        "cause_status": "unverified - not derivable from the Kalshi API",
                        "source": f"{DEMO_REST}/markets/trades?limit=1000",
                    }
                )
    jumps.sort(key=lambda j: str(j.get("to_time") or ""), reverse=True)
    return jumps


def write_csv(rows: list[dict], name: str, columns: list[str]) -> None:
    """Write the complete in-scope market list as a plain CSV table."""
    import csv

    DATA.mkdir(exist_ok=True)
    p = DATA / name
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columns)
        for r in rows:
            w.writerow(["" if r.get(c) is None else r.get(c) for c in columns])
    try:
        shown = p.relative_to(ROOT)
    except ValueError:
        shown = p
    print(f"wrote {shown} ({p.stat().st_size:,} bytes)")


def build_ticker_index(rows: list[dict]) -> dict:
    """Compact ticker -> summary map used by the live feeds in the browser."""
    idx: dict[str, list] = {}
    for r in rows:
        tk = r.get("market_ticker")
        if not tk:
            continue
        idx[tk] = [
            r.get("topic"),
            r.get("roi_score"),
            r.get("last_price_dollars"),
            r.get("yes_bid_dollars"),
            r.get("yes_ask_dollars"),
            r.get("volume_fp"),
            r.get("open_interest_fp"),
            r.get("close_time"),
            (r.get("market_title") or "")[:90],
        ]
    return idx


def exchange_status(signer: Signer | None) -> dict:
    j, status = get_json(DEMO_REST + "/exchange/status", signer)
    return {"http_status": status, "response": j}


# --------------------------------------------------------------------------- main
def write_json(name: str, payload: Any, pretty: bool = False) -> None:
    """Write one data file.

    The large files are written WITHOUT indentation on purpose. The snapshot used to
    be written with indent=1, which inflates the JSON by ~3.4x; the market list was
    then stored twice (as `markets` and again as `by_topic`). Together those two
    things made data/snapshot.json 47 MB, so every scheduled run had to push tens of
    megabytes to `main` and the refresh workflow started failing at the push step.
    Compact JSON plus a single copy of each row is ~10x smaller and is still plain
    JSON that any tool can read.
    """
    DATA.mkdir(exist_ok=True)
    p = DATA / name
    if pretty:
        text = json.dumps(payload, indent=1, sort_keys=False)
    else:
        text = json.dumps(payload, separators=(",", ":"), sort_keys=False)
    p.write_text(text + "\n")
    try:
        shown = p.relative_to(ROOT)
    except ValueError:
        shown = p
    print(f"wrote {shown} ({p.stat().st_size:,} bytes)")


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

    # transparent, published high-ROI score (tools/roi_model.py)
    rows = roi_model.score_rows(rows)

    books = {} if args.scope_only else collect_orderbooks(rows, signer)
    candles = {} if args.scope_only else collect_candles(rows, signer)
    resolutions = collect_resolutions(signer)
    trades = [] if args.scope_only else collect_trades(rows, signer)
    jumps = detect_jumps(trades) if trades else []

    by_topic = {t: [r for r in rows if r["topic"] == t] for t in TOPICS}
    for t in TOPICS:
        by_topic[t].sort(key=lambda r: (r.get("est_dollar_volume") or -1), reverse=True)

    finished = dt.datetime.now(dt.timezone.utc)
    ranked = sorted(rows, key=lambda r: (r.get("est_dollar_volume") or -1), reverse=True)
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
            "per_topic": {t: len(by_topic[t]) for t in TOPICS},
            "resolved_in_scope": len(resolutions),
            "orderbooks": len(books),
            "candle_sets": len(candles),
            "trades_collected": len(trades),
            "jumps_ge_0_10": len(jumps),
            "high_roi_markets": sum(1 for r in rows if r.get("roi_high")),
            "events_in_scope": len(scope["events_meta"]),
        },
        # The full market list lives in the per-topic files and in data/markets.csv.
        # It used to be stored twice here (`markets` AND `by_topic`), which is what
        # made this file 47 MB. `top_markets` is the ranked head the landing page
        # uses; the topic pages read their own file.
        "top_markets": ranked[:400],
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
            "roi_score": (
                "Model score from tools/roi_model.py (published weights in "
                "data/roi_model.json). A ranking heuristic over official fields only; "
                "it is not a prediction of the outcome and not investment advice."
            ),
            "jump": (
                "A price move of at least $0.10 between two consecutive trade prints of "
                "the same market (GET /markets/trades). The cause of a move is not in the "
                "API, so the cause column is left blank and flagged unverified."
            ),
        },
        "api_log": API_LOG,
    }
    write_json("snapshot.json", snapshot)

    # compact per-topic files keep each page payload small
    for t in TOPICS:
        write_json(
            f"topic-{t}.json",
            {
                "generated_at_utc": snapshot["generated_at_utc"],
                "topic": t,
                "count": len(by_topic[t]),
                "markets": by_topic[t],
                "resolutions": [r for r in resolutions if r["topic"] == t],
            },
        )

    # event-level metadata (settlement sources, contract terms) stored once per event
    write_json(
        "events.json",
        {
            "generated_at_utc": snapshot["generated_at_utc"],
            "count": len(scope["events_meta"]),
            "events": scope["events_meta"],
        },
    )

    write_json("resolutions.json", {"generated_at_utc": snapshot["generated_at_utc"],
                                    "count": len(resolutions), "resolutions": resolutions})

    # recent prints + the jumps they imply
    write_json(
        "trades.json",
        {
            "generated_at_utc": snapshot["generated_at_utc"],
            "count": len(trades),
            "source": f"{DEMO_REST}/markets/trades?limit=1000",
            "docs": "https://docs.kalshi.com/api-reference/market/get-trades",
            "trades": trades[:2000],
        },
    )
    write_json(
        "jumps.json",
        {
            "generated_at_utc": snapshot["generated_at_utc"],
            "threshold_dollars": 0.10,
            "count": len(jumps),
            "source": f"{DEMO_REST}/markets/trades?limit=1000",
            "docs": "https://docs.kalshi.com/api-reference/market/get-trades",
            "note": (
                "Cause of a move is not derivable from the Kalshi API. The cause field "
                "is empty on every row and flagged unverified."
            ),
            "jumps": jumps[:500],
        },
    )

    # compact ticker -> summary map used by the live chat feeds
    write_json(
        "ticker_index.json",
        {
            "generated_at_utc": snapshot["generated_at_utc"],
            "rest_base": DEMO_REST,
            "count": len(rows),
            "columns": ["topic", "roi_score", "last_price_dollars", "yes_bid_dollars",
                        "yes_ask_dollars", "volume_fp", "open_interest_fp", "close_time",
                        "title"],
            "index": build_ticker_index(rows),
        },
    )

    # the complete in-scope table as a plain CSV
    write_csv(
        ranked,
        "markets.csv",
        ["market_ticker", "topic", "event_ticker", "series_ticker", "market_title",
         "yes_sub_title", "status", "result", "yes_bid_dollars", "yes_ask_dollars",
         "last_price_dollars", "yes_bid_size_fp", "yes_ask_size_fp", "volume_fp",
         "volume_24h_fp", "open_interest_fp", "est_dollar_volume", "roi_score",
         "roi_gates_passed", "close_time", "market_url"],
    )

    # history ledger: append one compact point per market per run (for the price chart)
    # CAPPED on purpose. The old code appended a point for EVERY in-scope market and
    # kept 288 of them, which grows past 250 MB in under two days at a 10-minute
    # cadence. Only the markets a reader can actually chart are kept.
    hist_path = DATA / "history.json"
    hist = json.loads(hist_path.read_text()) if hist_path.exists() else {"points": {}}
    pts = hist.setdefault("points", {})
    keep = {r["market_ticker"] for r in ranked[:HISTORY_MARKETS]}
    for r in ranked[:HISTORY_MARKETS]:
        t = r["market_ticker"]
        lp = r.get("last_price_dollars")
        yb = r.get("yes_bid_dollars")
        if lp in (None, ""):
            continue
        pts.setdefault(t, []).append(
            {"t": int(finished.timestamp()), "last": lp, "yes_bid": yb,
             "yes_ask": r.get("yes_ask_dollars")}
        )
        pts[t] = pts[t][-HISTORY_POINTS:]
    for stale in [t for t in pts if t not in keep]:
        del pts[stale]
    hist["updated_at_utc"] = snapshot["generated_at_utc"]
    hist["note"] = (
        f"Collector tick history for the top {HISTORY_MARKETS} markets by estimated "
        f"dollar volume, last {HISTORY_POINTS} points each. Capped so the committed "
        "file stays a reasonable size."
    )
    write_json("history.json", hist)

    print(f"OK  in-scope markets={len(rows)}  resolved={len(resolutions)}  "
          f"books={len(books)}  auth={signer is not None}")
    if not rows:
        print("WARNING: zero in-scope markets returned — scope filter or API issue.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
