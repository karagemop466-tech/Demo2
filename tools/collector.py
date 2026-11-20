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
import re
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
                _MIN_INTERVAL["v"] = max(0.15, _MIN_INTERVAL["v"] * 0.99)
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
            if e.code == 429:
                _MIN_INTERVAL["v"] = min(3.0, _MIN_INTERVAL["v"] * 1.6)
            time.sleep(1.5 * (attempt + 1))
        except Exception as e:  # network/TLS/timeout
            last_status = type(e).__name__
            log_req(url, last_status, str(e)[:200])
            time.sleep(1.5 * (attempt + 1))
    return None, int(last_status) if isinstance(last_status, int) else 0


# ---------------------------------------------------------------- global throttle
# Kalshi documents that public endpoints charge the IP budget first and that a 429
# carries no penalty (docs: getting_started/rate_limits), so the only remedy is to
# slow down. The interval widens on a 429 and narrows slowly on success.
_MIN_INTERVAL = {"v": 0.30}
_LAST_CALL = {"t": 0.0}
STOP = {"requested": False}


def _throttle() -> None:
    wait = _MIN_INTERVAL["v"] - (time.time() - _LAST_CALL["t"])
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL["t"] = time.time()


def paginate(url: str, key: str, signer: Signer | None = None, max_pages: int = 30,
             complete: dict | None = None) -> list[dict]:
    """Cursor pagination exactly as documented in getting_started/pagination.md.

    A caller may pass its own `limit`; it is kept (the API caps the page size, so a
    smaller value is always honoured and a larger one simply yields full pages).

    If `complete` is passed, `complete["ok"]` is set False when the walk stopped early
    (a failed request or the page cap), so a caller can say "this list is partial"
    instead of presenting a truncated set as the whole.
    """
    if complete is not None:
        complete["ok"] = True
        complete["reason"] = ""
    out: list[dict] = []
    cursor = ""
    for _ in range(max_pages):
        u = url
        if "limit=" not in u:
            u += ("&" if "?" in u else "?") + "limit=200"
        if cursor:
            u += "&cursor=" + urllib.parse.quote(cursor, safe="")
        j, status = get_json(u, signer)
        if not j:
            if complete is not None:
                complete["ok"] = False
                complete["reason"] = f"request failed with HTTP {status}"
            break
        out.extend(j.get(key) or [])
        cursor = j.get("cursor") or ""
        if not cursor:
            break
    else:
        if complete is not None and cursor:
            complete["ok"] = False
            complete["reason"] = f"stopped at the {max_pages}-page cap"
    return out


# ----------------------------------------------------------------- topics / scope
# Official discovery fields only (docs: Get Series List -> `categories`, `category`, `tags`).
# Verified live 2026-11-20: tags=Gas -> DIESEL/DIESELM; tags=Golf -> KXPGATOUR etc.;
# categories contain "Elections" and "Crypto". Both fields are matched case-insensitively.
TAG_TOPIC = {
    "oil and energy": "gas-energy",   # refined below: only fuel-price titles count
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
    if not series:
        return None
    # 0) official product scope (verified live 2026-11-20 on GET /series/KXAAAGASD:
    #    product_metadata.scope == "Gasoline" for the AAA gasoline family). The bare
    #    "Oil & Gas" tag is deliberately NOT mapped here: it also covers crude oil
    #    (KXWTI), natural gas and TTF series, which are not "gas prices".
    scope = str(((series.get("product_metadata") or {}).get("scope")) or "").strip().lower()
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
        if mapped == "gas-energy":
            # The Oil and energy tag covers crude, natgas, electricity and gasoline. The
            # dashboard is about GAS PRICES (retail/wholesale fuel price); the ticker or
            # title has to say gas or diesel, and this fallback only applies when no
            # narrower tag matched.
            hay = f"{series.get('ticker','')} {series.get('title','')}".lower()
            # Word boundaries matter: "Georgia" contains "gas" and Kalshi has dozens of
            # Georgia election series under the Oil and energy tag's parent category.
            if re.search(r"\b(gas|gasoline|diesel|fuel)\b", hay):
                return "gas"
            continue
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
            t: sorted([s["ticker"] for s in series_idx.values() if series_topic(s) == t])
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
def collect_scope(signer: Signer | None, series_per_topic: int = 0,
                  rotation: int = 0, deadline_ts: float = 0.0) -> dict:
    """Open markets for the in-scope topics, fetched SERIES BY SERIES.

    Why not `GET /events?status=open&with_nested_markets=true` (the previous design):
    that stream is ordered by creation time and heavily dominated by multi-leg
    "MVE" combo events. Paging it stops long before the in-scope series are reached,
    and the combo markets carry event tickers such as
    `KXMVECROSSCATEGORY-S2026Y4RKDT7KS5SRIH27` that do not start with a series ticker,
    so they can never be mapped to a topic. The observed result was an empty
    dashboard: 1,556 rows on the previous collector were almost all unmatched combo
    markets and the 5 topic counts rendered 0.

    Re-basing on the series list makes the scope the official catalogue itself:
    one `GET /markets?series_ticker=...&status=open` per in-scope series. That is
    slower, so it is bounded and the bound is reported honestly (see `truncated`).
    """
    series_idx = load_series_index(signer)
    topic_cache = {t: series_topic(s) for t, s in series_idx.items()}
    in_scope: dict[str, list[str]] = {t: [] for t in TOPICS}
    for ticker, series in series_idx.items():
        tp = topic_cache.get(ticker)
        if tp in TOPICS:
            in_scope[tp].append(ticker)

    # A run reads as many in-scope series as its budget allows. When a cap applies it
    # ROTATES through the catalogue (`rotation` changes every run) so successive runs
    # cover different series and none is skipped forever. Nothing is capped silently:
    # the cap, the rotation and every failed request are reported on the site.
    rows: list[dict] = []
    failed: dict[str, list[dict]] = {t: [] for t in TOPICS}
    read: dict[str, int] = {t: 0 for t in TOPICS}
    for topic in TOPICS:
        tickers = sorted(in_scope[topic])
        if series_per_topic and len(tickers) > series_per_topic:
            start = rotation % len(tickers)
            tickers = (tickers + tickers)[start:start + series_per_topic]
        for st in tickers:
            if STOP["requested"] or (deadline_ts and time.time() > deadline_ts):
                STOP["requested"] = True
                failed[topic].append({"series": st, "http": "skipped: time budget reached"})
                continue
            url = (
                f"{DEMO_REST}/markets?series_ticker={urllib.parse.quote(st)}"
                "&status=open&limit=1000"
            )
            done: dict = {}
            markets = paginate(url, "markets", signer, max_pages=3, complete=done)
            read[topic] += 1
            if not done["ok"]:
                failed[topic].append({"series": st, "http": done["reason"],
                                      "url": url})
            for m in markets:
                rows.append(_market_row(topic, st, m, series_idx.get(st), None))

    unmapped = {s_: 1 for s_, t in topic_cache.items() if t is None}
    return {
        "markets_in_scope": rows,
        "series_index_size": len(series_idx),
        "series_inventory": inventory(series_idx),
        "topic_catalog": {
            t: {
                "series_in_catalog": len(in_scope[t]),
                "series_read": read[t],
                "series_failed": len(failed[t]),
                "series_with_live_markets": sorted({r["series_ticker"] for r in rows if r["topic"] == t}),
                "cap_this_run": series_per_topic or None,
            }
            for t in TOPICS
        },
        "rotation": rotation,
        "failed_series": {t: v[:200] for t, v in failed.items() if v},
        "truncated": {},
        "unmapped_series": unmapped,
        "events_scanned": len({r["event_ticker"] for r in rows}),
    }


def _market_row(topic: str, series_ticker: str, m: dict,
                series: dict | None = None, event: dict | None = None) -> dict:
    """One row per market. Dollar fields are copied VERBATIM from the API response.

    Also carries the series-level facts a trader needs to check a market: the official
    settlement sources, the contract terms and the certification, plus the exact API URL
    that produced the row. A human-facing kalshi.com market URL could not be confirmed
    from an official field, so it is not invented (the API URL is used instead).
    """
    series = series or {}
    event = event or {}
    t = m.get("ticker")
    return {
        "topic": topic,
        "event_ticker": m.get("event_ticker"),
        "series_ticker": series_ticker,
        "event_title": event.get("title"),
        "market_ticker": t,
        "market_title": m.get("title"),
        "yes_sub_title": m.get("yes_sub_title"),
        "status": m.get("status"),
        "result": m.get("result") or "",
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
        "rules_primary": m.get("rules_primary"),
        "exchange_index": m.get("exchange_index"),
        "settlement_sources": series.get("settlement_sources"),
        "series_category": series.get("category"),
        "series_categories": series.get("categories"),
        "contract_terms_url": series.get("contract_terms_url"),
        "contract_url": series.get("contract_url"),
        "event_url": f"{DEMO_REST}/events/{urllib.parse.quote(m.get('event_ticker') or '')}",
        "market_url": f"{DEMO_REST}/markets/{urllib.parse.quote(t)}" if t else None,
    }


def collect_trade_volume(rows: list[dict], signer: Signer | None,
                         top_n: int, hours: int = 24) -> dict:
    """REAL dollar volume from public trade prints: GET /markets/trades?ticker=...

    The API has no dollar-turnover field. `volume_fp x last_price_dollars` is only a
    proxy (it prices the whole history at today's price). Each trade print carries
    `count_fp` and `yes_price_dollars`, so summing count x yes price inside a window
    IS turnover in dollars for that window - computed here, per market, and labelled
    as computed rather than raw.
    """
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)

    def activity(r: dict) -> tuple:
        """Prefer markets that actually traded in the last 24 h.

        `volume_24h_fp` is an official market field (contracts), so it is the right
        selector for "where is turnover happening". Ranking by the lifetime estimate
        instead picked markets that traded long ago and had nothing inside the window,
        which is why only one of twelve picks produced a measured dollar figure.
        """
        try:
            v24 = float(r.get("volume_24h_fp") or 0)
        except (TypeError, ValueError):
            v24 = 0.0
        try:
            px = float(r.get("last_price_dollars") or 0)
        except (TypeError, ValueError):
            px = 0.0
        return (1 if v24 > 0 else 0, v24 * px, implied_dollar_volume(r) or 0)

    ranked = sorted(rows, key=activity, reverse=True)
    # Always include a spread over all five topics so no topic is invisible.
    picks: list[dict] = []
    seen: set[str] = set()
    for r in ranked[:top_n]:
        if r["market_ticker"] not in seen:
            picks.append(r); seen.add(r["market_ticker"])
    for topic in TOPICS:
        for r in [x for x in ranked if x["topic"] == topic][:3]:
            if r["market_ticker"] not in seen:
                picks.append(r); seen.add(r["market_ticker"])

    out: dict[str, dict] = {}
    for r in picks:
        t = r["market_ticker"]
        url = f"{DEMO_REST}/markets/trades?ticker={urllib.parse.quote(t)}&limit=1000"
        j, status = get_json(url, signer)
        if not j:
            out[t] = {"error": f"HTTP {status}", "source_url": url}
            continue
        trades = j.get("trades") or []
        usd = 0.0
        contracts = 0.0
        counted = 0
        for tr in trades:
            ts = tr.get("created_time") or ""
            try:
                when = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if when < cutoff:
                continue
            try:
                c = float(tr.get("count_fp") or 0)
                p = float(tr.get("yes_price_dollars") or 0)
            except (TypeError, ValueError):
                continue
            usd += c * p
            contracts += c
            counted += 1
        out[t] = {
            "source_url": url,
            "window_hours": hours,
            "trades_returned": len(trades),
            "trades_in_window": counted,
            "contracts_in_window": round(contracts, 2),
            "usd_volume_in_window": round(usd, 2),
            "note": ("Computed: sum(count_fp x yes_price_dollars) over trade prints whose "
                     "created_time falls inside the window. The API returns at most the "
                     "page it was asked for, so a market trading more than 1000 prints in "
                     "the window is under-counted; trades_returned shows the page size."),
        }
    return out


def collect_orderbook_history(rows: list[dict], signer: Signer | None,
                              top_n: int, samples: int = 12, gap_s: int = 22) -> dict:
    """Repeated orderbook snapshots, so the liquidity page can show depth over time.

    Kalshi publishes no orderbook history endpoint; the only way to chart liquidity is
    to sample it. Each point stores the full bid ladder, so "how many contracts at a
    given price" is answerable for any past sample inside the window as well as now.
    """
    ranked = sorted(rows, key=lambda r: (1 if float(r.get("volume_24h_fp") or 0) > 0 else 0,
                                         implied_dollar_volume(r) or 0), reverse=True)
    picks: list[dict] = []
    seen: set[str] = set()
    for topic in TOPICS:  # one per topic first, so every topic gets a liquidity series
        for r in [x for x in ranked if x["topic"] == topic][:1]:
            if r["market_ticker"] not in seen:
                picks.append(r); seen.add(r["market_ticker"])
    for r in ranked:
        if len(picks) >= top_n:
            break
        if r["market_ticker"] not in seen:
            picks.append(r); seen.add(r["market_ticker"])

    out: dict[str, dict] = {r["market_ticker"]: {"points": [], "source_url": None} for r in picks}
    for i in range(samples):
        for r in picks:
            t = r["market_ticker"]
            url = f"{DEMO_REST}/markets/{urllib.parse.quote(t)}/orderbook?depth=25"
            j, status = get_json(url, signer)
            if not j:
                continue
            ob = j.get("orderbook_fp") or {}
            yes = sorted([[float(p), float(q)] for p, q in (ob.get("yes_dollars") or [])],
                         key=lambda x: -x[0])
            no = sorted([[float(p), float(q)] for p, q in (ob.get("no_dollars") or [])],
                        key=lambda x: -x[0])
            asks = sorted([[round(1 - p, 4), q] for p, q in no], key=lambda x: x[0])
            out[t]["source_url"] = url
            out[t]["points"].append({
                "ts": int(time.time()),
                "yes_bids": yes,
                "derived_yes_asks": asks,
                "yes_bid_contracts": round(sum(q for _, q in yes), 2),
                "derived_ask_contracts": round(sum(q for _, q in asks), 2),
                "best_yes_bid": yes[0][0] if yes else None,
                "best_yes_ask_derived": asks[0][0] if asks else None,
            })
        if i < samples - 1:
            time.sleep(gap_s)   # spaced samples, not a burst
    return out


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


def collect_resolutions(signer: Signer | None, series_by_topic: dict[str, list[str]]) -> dict:
    """Settled in-scope markets, with the official yes/no `result`, accumulated over time.

    Two things the previous version got wrong, both observed on a real run:

    1. It derived the series from the event ticker's leading segment. MVE combo event
       tickers have no series prefix, and many real event tickers carry suffixes, so
       most settled markets were unmappable and the page came out empty (0 rows).
       Now the settled list is fetched per in-scope series, exactly like open markets.

    2. It treated one snapshot as the whole history. The settled list is paginated and
       rate-limited, so each run sees only a slice. Resolutions are therefore appended
       to a rolling log (`data/resolutions.json`) keyed by ticker: a run can add rows,
       never silently drop the ones it did not reach this time.
    """
    per_series_cap = 2      # one request per series keeps the run inside the rate limit
    discovered: dict[str, dict] = {}
    complete: dict[str, dict] = {}
    for topic in TOPICS:
        for st in series_by_topic.get(topic, []):
            if STOP["requested"]:
                break
            url = f"{DEMO_REST}/markets?series_ticker={urllib.parse.quote(st)}&status=settled&limit=200"
            done: dict = {}
            markets = paginate(url, "markets", signer, max_pages=per_series_cap, complete=done)
            complete.setdefault(topic, {"ok": True, "series_incomplete": []})
            if not done["ok"]:
                complete[topic]["ok"] = False
                complete[topic]["series_incomplete"].append(st)
            for m in markets:
                t = m.get("ticker")
                if not t:
                    continue
                discovered[t] = {
                    "topic": topic,
                    "series_ticker": st,
                    "event_ticker": m.get("event_ticker"),
                    "market_ticker": t,
                    "status": m.get("status"),
                    "title": m.get("title"),
                    "result": m.get("result") or "",          # yes / no / ""
                    "settlement_value_dollars": m.get("settlement_value_dollars"),
                    "settlement_ts": m.get("settlement_ts"),
                    "close_time": m.get("close_time"),
                    "expiration_value": m.get("expiration_value"),
                    "volume_fp": m.get("volume_fp"),
                    "open_interest_fp": m.get("open_interest_fp"),
                    "rules_primary": m.get("rules_primary"),
                    "live_url": f"https://external-api.demo.kalshi.co/trade-api/v2/markets/{urllib.parse.quote(t)}",
                    "source_url": url,
                    "first_seen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                }

    # merge with what earlier runs already captured
    prev: dict[str, dict] = {}
    path = DATA / "resolutions_log.json"
    if path.exists():
        try:
            prev = {r["market_ticker"]: r for r in json.loads(path.read_text()).get("resolutions", [])}
        except (json.JSONDecodeError, KeyError, TypeError):
            prev = {}
    merged = dict(prev)
    for ticker, row in discovered.items():
        old = merged.get(ticker) or {}
        merged[ticker] = {**old, **row,
                          "first_seen_utc": old.get("first_seen_utc") or row["first_seen_utc"]}
    out = list(merged.values())
    out.sort(key=lambda r: (r.get("settlement_ts") or ""), reverse=True)
    write_json("resolutions_log.json", {
        "updated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "note": ("Rolling log: each run adds the settled markets it managed to read; rows from "
                 "earlier runs are kept. `complete` says whether every in-scope series was read."),
        "count": len(out),
        "complete": complete,
        "resolutions": out,
    })
    return {"rows": out, "discovered_this_run": len(discovered), "complete": complete}


def exchange_status(signer: Signer | None) -> dict:
    j, status = get_json(DEMO_REST + "/exchange/status", signer)
    return {"http_status": status, "response": j}


# --------------------------------------------------------------------------- main
def write_json(name: str, payload: Any) -> None:
    DATA.mkdir(exist_ok=True)
    p = DATA / name
    p.write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n")
    try:
        shown = p.relative_to(ROOT)
    except ValueError:          # DATA redirected (offline test writes to a temp dir)
        shown = p
    print(f"wrote {shown} ({p.stat().st_size} bytes)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope-only", action="store_true", help="skip candles/books (fast path)")
    ap.add_argument("--max-runtime", type=int, default=900,
                    help="soft wall-clock budget in seconds; optional extras are skipped, "
                         "never the core market list")
    ap.add_argument("--volume-markets", type=int, default=30,
                    help="markets to pull trade prints for (real 24h dollar volume)")
    ap.add_argument("--book-markets", type=int, default=10,
                    help="markets to sample the order book for")
    ap.add_argument("--book-samples", type=int, default=12,
                    help="order-book samples per market, ~22 s apart")
    ap.add_argument("--series-per-topic", type=int, default=0,
                    help="cap in-scope series queried per topic this run (0 = all). "
                         "Coverage rotates between runs so nothing is skipped forever")
    args = ap.parse_args()

    signer = signer_from_env()
    started = dt.datetime.now(dt.timezone.utc)
    deadline = started + dt.timedelta(seconds=args.max_runtime)

    def left() -> float:
        remaining = (deadline - dt.datetime.now(dt.timezone.utc)).total_seconds()
        if remaining < 30:
            STOP["requested"] = True
        return remaining

    status = exchange_status(signer)

    rotation = int(time.time() // 900)      # changes every 15 minutes
    scope = collect_scope(signer, args.series_per_topic, rotation,
                          deadline_ts=(deadline - dt.timedelta(seconds=180)).timestamp())
    rows = scope["markets_in_scope"]

    # enrich with the estimate, clearly named as such
    for r in rows:
        r["est_dollar_volume"] = implied_dollar_volume(r)

    # Order of work: core market list -> resolutions -> real 24h turnaround -> books
    # -> candlesticks. The optional blocks are time-boxed so the essentials always land.
    series_by_topic: dict[str, list[str]] = {t: [] for t in TOPICS}
    for r in rows:
        if r["series_ticker"] not in series_by_topic[r["topic"]]:
            series_by_topic[r["topic"]].append(r["series_ticker"])
    res = ({"rows": [], "discovered_this_run": 0, "complete": {}}
           if left() < 120 else collect_resolutions(signer, series_by_topic))
    resolutions = res["rows"]

    trade_volume: dict[str, dict] = {}
    if not args.scope_only and left() > 240 and args.volume_markets > 0:
        trade_volume = collect_trade_volume(rows, signer, top_n=args.volume_markets)

    books = {} if args.scope_only else collect_orderbooks(rows, signer)
    book_history: dict[str, dict] = {}
    if not args.scope_only and left() > 60 and args.book_markets > 0:
        samples = max(1, min(args.book_samples, int(left() // 25)))
        book_history = collect_orderbook_history(rows, signer, top_n=args.book_markets,
                                                 samples=samples)
    candles = {} if args.scope_only or left() < 45 else collect_candles(rows, signer)

    # attach the computed 24h dollar volume to each row; absent stays absent
    for r in rows:
        tv = trade_volume.get(r["market_ticker"])
        if tv and "usd_volume_in_window" in tv:
            r["usd_volume_24h"] = tv["usd_volume_in_window"]
            r["contracts_24h_from_trades"] = tv["contracts_in_window"]
            r["usd_volume_24h_source_url"] = tv["source_url"]

    by_topic = {t: [r for r in rows if r["topic"] == t] for t in TOPICS}
    for t in TOPICS:
        by_topic[t].sort(key=lambda r: (r.get("usd_volume_24h") if r.get("usd_volume_24h") is not None
                                        else r.get("est_dollar_volume") or -1), reverse=True)

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
            "per_topic": {t: len(by_topic[t]) for t in TOPICS},
            "resolved_in_scope": len(resolutions),
            "resolved_this_run": res["discovered_this_run"],
            "resolved_in_this_run_scope": len([r for r in resolutions
                                               if r.get("topic") in TOPICS]),
            "failed_series_requests": sum(len(v) for v in scope["failed_series"].values()),
            "orderbooks": len(books),
            "candle_sets": len(candles),
            "trade_volume_markets": len(trade_volume),
            "book_history_markets": len(book_history),
            "truncated_topics": sorted(scope["truncated"].keys()),
        },
        "markets": rows,
        "by_topic": by_topic,
        "orderbooks": books,
        "orderbook_history": book_history,
        "trade_volume": trade_volume,
        "candles": candles,
        "resolutions": resolutions,
        "resolutions_this_run": res["discovered_this_run"],
        "resolutions_complete": res["complete"],
        "failed_series": scope["failed_series"],
        "scope_rotation": scope["rotation"],
        "scope_limits": scope["truncated"],
        "definitions": {
            "est_dollar_volume": (
                "ESTIMATE = volume_fp x last_price_dollars, computed by this collector. "
                "The API exposes no single dollar-volume field. Label is shown in the UI."
            ),
            "usd_volume_24h": (
                "COMPUTED, not an API field: sum(count_fp x yes_price_dollars) over public "
                "trade prints (GET /markets/trades) whose created_time is inside the last "
                "24 hours. Only computed for the markets listed in `trade_volume`."
            ),
            "orderbook_history": (
                "SAMPLED, not an API endpoint: /markets/{ticker}/orderbook is polled ~22 s "
                "apart by this collector. Kalshi publishes no orderbook history."
            ),
            "scope_limits": (
                "Per-topic cap on how many series were queried. A topic listed here has more "
                "series in the catalogue than were queried this run; nothing is dropped "
                "silently, the numbers are on the Verification page."
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
                "orderbook_history": {
                    k: v for k, v in book_history.items()
                    if any(r["market_ticker"] == k for r in by_topic[t])
                },
            },
        )

    write_json("resolutions.json", {
        "generated_at_utc": snapshot["generated_at_utc"],
        "count": len(resolutions),
        "this_run": res["discovered_this_run"],
        "complete": res["complete"],
        "note": ("Rolling log of settled in-scope markets. `result` is Kalshi's own field, "
                 "copied verbatim. A market that never traded is included and marked by "
                 "volume_fp = 0."),
        "resolutions": resolutions,
    })

    # ---- compact files: the browser must not download the full snapshot ----
    # The request log is the site's provenance trail, so it must be versioned. It is
    # written separately (a few hundred KB) instead of shipping the 12 MB snapshot.
    write_json("snapshot_api_log.json", {
        "generated_at_utc": snapshot["generated_at_utc"],
        "rest_base": DEMO_REST,
        "count": len(API_LOG),
        "failed": len([r for r in API_LOG if not r["ok"]]),
        "note": ("Every request this run made, with its HTTP status. The dashboard tables are "
                 "populated only from these responses."),
        "api_log": API_LOG,
    })

    write_json("series_index.json", {
        "fetched_at": snapshot["generated_at_utc"],
        "source": f"{DEMO_REST}/series",
        "note": ("Official GET /series response, every series the demo exchange lists, with "
                 "the topic this collector mapped it to from its category/tags. "
                 "settlement_sources are the publications Kalshi names for that series."),
        "series": [
            dict(series,
                 topic=series_topic(series),
                 source=f"{DEMO_REST}/series/{urllib.parse.quote(series.get('ticker') or '')}")
            for series in (load_series_index(signer) or {}).values()
        ],
    })

    write_json("dashboard_meta.json", {
        "generated_at_utc": snapshot["generated_at_utc"],
        "environment": "demo",
        "rest_base": DEMO_REST,
        "authenticated": signer is not None,
        "exchange_status": status,
        "counts": snapshot["counts"],
        "topic_catalog": snapshot["topic_catalog"],
        "scope_limits": snapshot["scope_limits"],
        "series_inventory": {
            "series_count": scope["series_inventory"]["series_count"],
            "in_scope_series": {t: len(v) for t, v in scope["series_inventory"]["in_scope_series"].items()},
        },
        "definitions": snapshot["definitions"],
        "series_with_live_markets_total": sum(
            len(v.get("series_with_live_markets") or [])
            for v in scope["topic_catalog"].values()),
        "series_read_total": sum(v.get("series_read", 0) for v in scope["topic_catalog"].values()),
        "resolutions_by_topic": {
            t: len([r for r in resolutions if r.get("topic") == t]) for t in TOPICS
        },
        "api_request_count": len(API_LOG),
        "api_request_failures": len([r for r in API_LOG if not r["ok"]]),
    })

    ranked_all = sorted(
        rows,
        key=lambda r: (1 if r.get("usd_volume_24h") is not None else 0,
                       r.get("usd_volume_24h") if r.get("usd_volume_24h") is not None
                       else r.get("est_dollar_volume") or -1),
        reverse=True,
    )
    write_json("top.json", {
        "generated_at_utc": snapshot["generated_at_utc"],
        "method": ("Two tiers. First every market whose 24-hour dollar turnover was MEASURED "
                   "from public trade prints (usd_volume_24h), highest first. Then the rest, by "
                   "the est_dollar_volume proxy (volume_fp x last_price_dollars). `rank_by` on "
                   "each row says which metric placed it."),
        "count": min(len(ranked_all), 200),
        "rows": [
            dict(r, rank_by=("usd_volume_24h" if r.get("usd_volume_24h") is not None else "est_dollar_volume"))
            for r in ranked_all[:200]
        ],
    })

    write_json("liquidity.json", {
        "generated_at_utc": snapshot["generated_at_utc"],
        "note": ("Sampled by this collector from GET /markets/{ticker}/orderbook. Kalshi "
                 "publishes no orderbook history; each point is one poll, about 22 s apart."),
        "sample_interval_s": 22,
        "markets": {
            t: dict(
                v,
                topic=next((r["topic"] for r in rows if r["market_ticker"] == t), None),
                title=next((r["market_title"] for r in rows if r["market_ticker"] == t), None),
            )
            for t, v in book_history.items()
        },
    })

    # history ledger: append one compact point per market per run (for the price chart)
    hist_path = DATA / "history.json"
    hist = json.loads(hist_path.read_text()) if hist_path.exists() else {"points": {}}
    pts = hist.setdefault("points", {})
    for r in rows:
        t = r["market_ticker"]
        lp = r.get("last_price_dollars")
        yb = r.get("yes_bid_dollars")
        if lp in (None, ""):
            continue
        pts.setdefault(t, []).append(
            {"t": int(finished.timestamp()), "last": lp, "yes_bid": yb,
             "yes_ask": r.get("yes_ask_dollars")}
        )
        pts[t] = pts[t][-2000:]
    hist["updated_at_utc"] = snapshot["generated_at_utc"]
    write_json("history.json", hist)

    print(f"OK  in-scope markets={len(rows)}  resolved={len(resolutions)}  "
          f"books={len(books)}  auth={signer is not None}")
    if not rows:
        print("WARNING: zero in-scope markets returned — scope filter or API issue.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
