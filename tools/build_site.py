#!/usr/bin/env python3
"""Build the Kalshi Demo Monitor site from the verified snapshot in data/.

    python3 tools/build_site.py

Inputs  (written by scripts/fetch-data.mjs):
    data/meta.json, data/open-markets.json, data/open-events.json,
    data/settled-markets.json, data/orderbooks.json, data/taxonomy.json

Outputs:
    index.html and pages/*.html

Rules:
  * Every value rendered in a data table comes from a snapshot row, and every
    row carries a link to the exact API response it was read from.
  * A field that is absent from the API response is rendered as an explicit
    "UNVERIFIED" marker. Nothing is inferred, defaulted or interpolated.
  * The same tables are re-rendered in the browser by assets/app.js, so the
    static HTML and the live view show identical numbers.
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
PAGES = os.path.join(ROOT, "pages")

# --------------------------------------------------------------------------
# Official documentation links (https://docs.kalshi.com) used across the site.
# --------------------------------------------------------------------------
DOCS = {
    "welcome": "https://docs.kalshi.com/welcome",
    "demo": "https://docs.kalshi.com/getting_started/demo_env",
    "envs": "https://docs.kalshi.com/getting_started/api_environments",
    "market_data": "https://docs.kalshi.com/getting_started/quick_start_market_data",
    "auth": "https://docs.kalshi.com/getting_started/quick_start_authenticated_requests",
    "keys": "https://docs.kalshi.com/getting_started/api_keys",
    "create_order": "https://docs.kalshi.com/getting_started/quick_start_create_order",
    "order_errors": "https://docs.kalshi.com/getting_started/order_errors",
    "websockets": "https://docs.kalshi.com/getting_started/quick_start_websockets",
    "order_direction": "https://docs.kalshi.com/getting_started/order_direction",
    "orderbook": "https://docs.kalshi.com/getting_started/orderbook_responses",
    "fixed_point": "https://docs.kalshi.com/getting_started/fixed_point_migration",
    "pagination": "https://docs.kalshi.com/getting_started/pagination",
    "rate_limits": "https://docs.kalshi.com/getting_started/rate_limits",
    "settlement": "https://docs.kalshi.com/getting_started/market_settlement",
    "lifecycle": "https://docs.kalshi.com/getting_started/market_lifecycle",
    "fees": "https://docs.kalshi.com/getting_started/fee_rounding",
    "historical": "https://docs.kalshi.com/getting_started/historical_data",
    "mcp": "https://docs.kalshi.com/getting_started/mcp",
    "get_markets": "https://docs.kalshi.com/api-reference/market/get-markets",
    "get_market": "https://docs.kalshi.com/api-reference/market/get-market",
    "get_events": "https://docs.kalshi.com/api-reference/events/get-events",
    "get_series": "https://docs.kalshi.com/api-reference/market/get-series-list",
    "get_series_one": "https://docs.kalshi.com/api-reference/market/get-series",
    "get_orderbook": "https://docs.kalshi.com/api-reference/market/get-market-orderbook",
    "get_candles": "https://docs.kalshi.com/api-reference/market/get-market-candlesticks",
    "get_trades": "https://docs.kalshi.com/api-reference/market/get-trades",
    "tags_by_categories": "https://docs.kalshi.com/api-reference/search/get-tags-for-series-categories",
    "get_balance": "https://docs.kalshi.com/api-reference/portfolio/get-balance",
    "get_positions": "https://docs.kalshi.com/api-reference/portfolio/get-positions",
    "get_fills": "https://docs.kalshi.com/api-reference/portfolio/get-fills",
    "get_orders": "https://docs.kalshi.com/api-reference/portfolio/get-orders",
    "create_order": "https://docs.kalshi.com/api-reference/orders/create-order",
    "api_key_generate": "https://docs.kalshi.com/api-reference/api-keys/generate-api-key",
    "changelog": "https://docs.kalshi.com/changelog",
    "demo_site": "https://demo.kalshi.co/",
    "demo_help": "https://help.kalshi.com/en/articles/13823775-creating-and-using-a-demo-account",
    "github_pages": "https://docs.github.com/en/pages",
}

TOPICS = [
    {
        "id": "gas",
        "label": "Gas prices",
        "file": "gas.html",
        "blurb": "Diesel, gasoline, crude oil and other fuel-price contracts.",
        "rule": "Official series tag allowlist: Oil & Gas, Oil and energy, Gas, Gasoline, Diesel, Crude oil.",
        "categories": [],
        "tags": ["Oil & Gas", "Oil and energy", "Gas", "Gasoline", "Diesel", "Crude oil"],
    },
    {
        "id": "elections",
        "label": "Elections",
        "file": "elections.html",
        "blurb": "Official Kalshi category “Elections”: races, primaries, control, legislatures.",
        "rule": "Official series category allowlist: Elections.",
        "categories": ["Elections"],
        "tags": [],
    },
    {
        "id": "culture",
        "label": "Culture",
        "file": "culture.html",
        "blurb": "Official Kalshi categories “Culture” and “Entertainment”: film, music, TV, awards.",
        "rule": "Official series category allowlist: Culture, Entertainment.",
        "categories": ["Culture", "Entertainment"],
        "tags": [],
    },
    {
        "id": "crypto",
        "label": "Crypto",
        "file": "crypto.html",
        "blurb": "Crypto-asset contracts (BTC, ETH, SOL and the rest of the official crypto tag list).",
        "rule": "Official series tag allowlist: Crypto, Bitcoin, BTC, ETH, Ethereum, SOL, Solana, DOGE, Dogecoin, XRP, BNB, HYPE, ZEC, Zcash, NEAR, Shiba Inu, Tokens.",
        "categories": [],
        "tags": ["Crypto", "Bitcoin", "BTC", "ETH", "Ethereum", "SOL", "Solana", "DOGE",
                 "Dogecoin", "XRP", "BNB", "HYPE", "ZEC", "Zcash", "NEAR", "Shiba Inu", "Tokens"],
    },
    {
        "id": "golf",
        "label": "Golf",
        "file": "golf.html",
        "blurb": "PGA tour events, majors and golf outright markets.",
        "rule": "Official series tag allowlist: Golf.",
        "categories": [],
        "tags": ["Golf"],
    },
]
TOPIC_BY_ID = {t["id"]: t for t in TOPICS}

NAV = [
    ("index.html", "Dashboard"),
    ("pages/executive-summary.html", "Executive summary"),
    ("pages/gas.html", "Gas"),
    ("pages/elections.html", "Elections"),
    ("pages/culture.html", "Culture"),
    ("pages/crypto.html", "Crypto"),
    ("pages/golf.html", "Golf"),
    ("pages/portfolio.html", "Portfolio & trading"),
    ("pages/analysis.html", "Analysis"),
    ("pages/suggestions.html", "Suggestions"),
    ("pages/questions.html", "Questions"),
    ("pages/verification.html", "Verification"),
    ("pages/flagged.html", "Flagged for review"),
    ("pages/sources.html", "Sources"),
]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def money(value, dp=2):
    n = num(value)
    if n is None:
        return None
    return f"${n:,.{dp}f}"


def count(value):
    n = num(value)
    if n is None:
        return None
    return f"{n:,.2f}".rstrip("0").rstrip(".") if n % 1 else f"{int(n):,}"


def when(value):
    if not value:
        return None
    text = str(value)
    if text.endswith("Z") and "T" in text:
        return text.replace("T", " ")[:16] + " UTC"
    return text


def cell(value, formatter=money):
    """Render a value, or an explicit UNVERIFIED marker when it is absent."""
    if value is None or value == "":
        return '<span class="unv">UNVERIFIED</span>'
    out = formatter(value)
    if out is None or out == "":
        return '<span class="unv">UNVERIFIED</span>'
    return esc(out)


def link(url, text=None):
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(text or url)}</a>'


def source_cell(row):
    url = row.get("source_url") or ""
    if not url:
        return '<span class="unv">UNVERIFIED</span>'
    return f'{link(url, "API")} · {link(DOCS["get_markets"], "docs")}'


def load(name, default=None):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------
def layout(title: str, active: str, body: str, depth: int = 0, scripts: str = "",
           description: str = "") -> str:
    prefix = "../" * depth
    nav = "".join(
        f'<a href="{prefix}{href}"'
        + (' aria-current="page"' if href == active else "")
        + f">{esc(label)}</a>"
        for href, label in NAV
    )
    desc = description or "Kalshi demo markets for gas prices, elections, culture, crypto and golf."
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Kalshi Demo Monitor</title>
<meta name="description" content="{esc(desc)}">
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-inner">
    <a class="brand" href="{prefix}index.html">Kalshi <span class="dot">Demo</span> Monitor<small>research dashboard</small></a>
    <nav class="main">{nav}</nav>
    <span class="pill-demo">Demo only · no real funds</span>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="site">
  <div class="wrap">
    <p>Demo environment only. Kalshi states that demo prices and market behaviour
    <a href="{DOCS['demo']}">may not be reflective of those in real markets</a>. Every figure on this site is read from the
    Kalshi demo API and carries a link to the response it came from; nothing is inferred.
    Build snapshot: <span id="snapshotStamp">—</span></p>
    <p><a href="{DOCS['welcome']}">Kalshi API documentation</a> ·
    <a href="{DOCS['demo_site']}">Kalshi demo</a> ·
    <a href="pages/sources.html">Sources</a> ·
    <a href="pages/verification.html">Verification</a> ·
    <a href="pages/flagged.html">Flagged for review</a></p>
  </div>
</footer>
{scripts}
</body>
</html>
"""


def crumb(parts) -> str:
    items = []
    for i, (href, label) in enumerate(parts):
        if href:
            items.append(f'<a href="{esc(href)}">{esc(label)}</a>')
        else:
            items.append(esc(label))
    return '<div class="breadcrumb">' + " › ".join(items) + "</div>"


# --------------------------------------------------------------------------
# table builders
# --------------------------------------------------------------------------
MARKET_HEAD = ("Topic", "Ticker", "Market", "Last $", "YES bid / ask",
               "Contracts traded", "Contract value traded $", "Open interest $",
               "Closes (UTC)", "Source")
MARKET_COLS = 10


def market_rows(rows, limit=40) -> str:
    if not rows:
        return f'<tr><td colspan="{MARKET_COLS}" class="muted">No rows in the current snapshot.</td></tr>'
    out = []
    for m in rows[:limit]:
        title = m.get("title") or m.get("event_title") or ""
        sub = m.get("event_title") if m.get("title") else (m.get("series_title") or m.get("series_ticker") or "")
        topic = TOPIC_BY_ID.get(m.get("topic"), {}).get("label", m.get("topic"))
        out.append(
            "<tr>"
            f'<td><span class="tag {esc(m.get("topic"))}">{esc(topic)}</span></td>'
            f'<td class="ticker nowrap">{link(m.get("source_url"), m.get("ticker"))}</td>'
            f'<td class="title-cell"><span class="t">{esc(title)}</span><span class="s">{esc(sub)}</span></td>'
            f'<td class="num">{cell(m.get("last_price_dollars"), lambda v: money(v, 4))}</td>'
            f'<td class="num nowrap">{cell(m.get("yes_bid_dollars"), lambda v: money(v, 4))} / {cell(m.get("yes_ask_dollars"), lambda v: money(v, 4))}</td>'
            f'<td class="num">{cell(m.get("volume_fp"), count)}</td>'
            f'<td class="num">{cell(m.get("contract_value_traded_usd"), lambda v: money(v, 2))}</td>'
            f'<td class="num">{cell(m.get("open_interest_usd"), lambda v: money(v, 2))}</td>'
            f'<td class="nowrap">{cell(m.get("close_time"), when)}</td>'
            f'<td class="nowrap">{source_cell(m)}</td>'
            "</tr>"
        )
    return "".join(out)


def event_rows(rows, limit=25) -> str:
    if not rows:
        return '<tr><td colspan="8" class="muted">No rows in the current snapshot.</td></tr>'
    out = []
    for e in rows[:limit]:
        topic = TOPIC_BY_ID.get(e.get("topic"), {}).get("label", e.get("topic"))
        out.append(
            "<tr>"
            f'<td><span class="tag {esc(e.get("topic"))}">{esc(topic)}</span></td>'
            f'<td class="title-cell"><span class="t">{esc(e.get("title"))}</span><span class="s">{esc(e.get("event_ticker"))}</span></td>'
            f'<td class="num">{cell(e.get("markets"), count)}</td>'
            f'<td class="num">{cell(e.get("volume_fp"), count)}</td>'
            f'<td class="num">{cell(e.get("contract_value_traded_usd"), lambda v: money(v, 2))}</td>'
            f'<td class="num">{cell(e.get("open_interest_usd"), lambda v: money(v, 2))}</td>'
            f'<td class="nowrap">{cell(e.get("close_time"), when)}</td>'
            f'<td class="nowrap">{source_cell(e)}</td>'
            "</tr>"
        )
    return "".join(out)


def settled_rows(rows, limit=25) -> str:
    if not rows:
        return '<tr><td colspan="7" class="muted">No rows in the current snapshot.</td></tr>'
    out = []
    for m in rows[:limit]:
        result = m.get("result")
        badge = (f'<span class="badge {esc(result)}">{esc(result.upper())}</span>'
                 if result in ("yes", "no") else '<span class="unv">UNVERIFIED</span>')
        topic = TOPIC_BY_ID.get(m.get("topic"), {}).get("label", m.get("topic"))
        out.append(
            "<tr>"
            f'<td><span class="tag {esc(m.get("topic"))}">{esc(topic)}</span></td>'
            f'<td class="ticker nowrap">{link(m.get("source_url"), m.get("ticker"))}</td>'
            f'<td class="title-cell"><span class="t">{esc(m.get("title"))}</span></td>'
            f'<td>{badge}</td>'
            f'<td class="num">{cell(m.get("settlement_value_dollars"), lambda v: money(v, 4))}</td>'
            f'<td class="nowrap">{cell(m.get("settlement_ts"), when)}</td>'
            f'<td class="nowrap">{source_cell(m)}</td>'
            "</tr>"
        )
    return "".join(out)


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------
def build_index(meta, markets, events, settled, books) -> str:
    topic_options = "".join(f'<option value="{t["id"]}">{esc(t["label"])}</option>' for t in TOPICS)
    metric_options = (
        '<option value="traded">Contract value traded ($) — volume_fp × last_price_dollars</option>'
        '<option value="oi">Open interest value ($) — open_interest_fp × last_price_dollars</option>'
        '<option value="volume">Contracts traded (volume_fp)</option>'
    )
    body = f"""
{crumb([("", "Kalshi Demo Monitor")])}
<section class="card" style="border-left:4px solid var(--brand)">
  <p class="eyebrow">Live dashboard · highest dollar amount</p>
  <h1>Kalshi demo events, tracked from open to resolution</h1>
  <p class="lede">Every open demo market in the five requested topics — gas prices, elections,
  culture, crypto and golf — ranked by dollar amount, with a live price chart, the resting
  order book (contracts available at each price), and the settled markets that show whether
  each event resolved <b>yes</b> or <b>no</b>. Scope comes from Kalshi's own series taxonomy,
  not from title keywords.</p>
  <div class="statusbar" style="margin-top:12px">
    <span class="pill" id="liveStatusWrap"><span class="led"></span><span id="liveStatus">Loading snapshot…</span></span>
    <span class="pill">Snapshot: <span id="kpiUpdated">—</span></span>
    <button class="small secondary" id="refreshBtn">Refresh now</button>
  </div>
</section>

<div class="grid grid-4" style="margin-bottom:14px">
  <div class="kpi"><div class="k">Open in-scope markets</div><div class="v" id="kpiMarkets">—</div><div class="s">{link(DOCS["get_markets"], "Get Markets")}</div></div>
  <div class="kpi"><div class="k">Contract value traded</div><div class="v" id="kpiTraded">—</div><div class="s">derived: volume_fp × last_price_dollars</div></div>
  <div class="kpi"><div class="k">Contracts traded</div><div class="v" id="kpiVolume">—</div><div class="s">volume_fp (contract count)</div></div>
  <div class="kpi"><div class="k">In-scope events</div><div class="v" id="kpiEvents">—</div><div class="s">{link(DOCS["get_events"], "Get Events")}</div></div>
</div>

<div class="card">
  <div class="card-head">
    <h2>Open markets, ranked by dollar amount</h2>
    <div class="row">
      <div style="min-width:170px"><label for="topicFilter">Topic</label>
        <select id="topicFilter"><option value="all">All five topics</option>{topic_options}</select></div>
      <div style="min-width:230px"><label for="metricFilter">Ranking metric</label>
        <select id="metricFilter">{metric_options}</select></div>
    </div>
  </div>
  <p class="muted">“Highest dollar amount” has no single API field. Kalshi's
  <code>notional_value_dollars</code> is <em>the value of a single contract at settlement</em>, not turnover, so the ranking
  uses a derived measure, clearly labelled on every row. See
  {link("pages/flagged.html", "Flagged for review")} (F2) and {link("pages/verification.html", "Verification")}.</p>
  <div class="table-wrap">
    <table id="marketTable">
      <caption>Snapshot rows carry the exact API response they were read from. The browser refreshes prices live from the demo API.</caption>
      <thead><tr>{''.join(f'<th>{esc(h)}</th>' for h in MARKET_HEAD)}</tr></thead>
      <tbody>{market_rows(markets, 40)}</tbody>
    </table>
  </div>
</div>

<div class="grid grid-2">
  <div class="card chart-card">
    <div class="card-head">
      <h2>Price movement</h2>
      <div style="min-width:190px"><label for="windowFilter">Graph length</label>
        <select id="windowFilter"></select></div>
    </div>
    <p class="muted">X axis = time · Y axis = contract price in US dollars. History comes from Kalshi
    candlesticks; the newest points are live REST snapshots.</p>
    <div class="chart-shell">
      <canvas id="priceChart" class="chart"></canvas>
      <div id="chartTip" style="display:none;position:absolute;background:#101a2b;color:#fff;padding:6px 9px;border-radius:8px;font-size:12px;pointer-events:none"></div>
    </div>
    <p class="muted" id="chartNote">Select a market row to plot its price history.</p>
    <div class="chart-legend">
      <span><b id="selectedTitle">—</b></span>
      <span class="mono" id="selectedTicker">—</span>
    </div>
  </div>

  <div class="card">
    <h2>Selected market</h2>
    <dl class="kv">
      <dt>Last traded</dt><dd id="selLast">—</dd>
      <dt>YES bid</dt><dd id="selBid">—</dd>
      <dt>YES ask</dt><dd id="selAsk">—</dd>
      <dt>Contracts traded</dt><dd id="selVolume">—</dd>
      <dt>Open interest</dt><dd id="selOi">—</dd>
      <dt>Closes</dt><dd id="selClose">—</dd>
      <dt>Status</dt><dd id="selStatus">—</dd>
    </dl>
    <h3 style="margin-top:16px">Liquidity — contracts available at each price</h3>
    <p class="muted">{link(DOCS["get_orderbook"], "Get Market Orderbook")} returns resting YES and NO bids.
    A bid for YES at price X is an offer to sell NO at 1 − X, so asks are not returned separately.</p>
    <div class="book">
      <div><h4>YES bids</h4><div id="bookYes" class="muted">—</div></div>
      <div><h4>NO bids</h4><div id="bookNo" class="muted">—</div></div>
    </div>
    <p class="muted" id="bookAt">—</p>
  </div>
</div>

<div class="card">
  <div class="card-head"><h2>Events, rolled up by dollar amount</h2>
    <span class="muted">Markets grouped by event_ticker · {link(DOCS["get_events"], "Get Events")}</span></div>
  <div class="table-wrap">
    <table id="eventTable">
      <thead><tr><th>Topic</th><th>Event</th><th class="num">Markets</th><th class="num">Contracts</th>
        <th class="num">Contract value traded $</th><th class="num">Open interest $</th><th>Closes (UTC)</th><th>Source</th></tr></thead>
      <tbody>{event_rows(events, 25)}</tbody>
    </table>
  </div>
</div>

<div class="card">
  <div class="card-head"><h2>Resolved events — how each market settled</h2>
    <span class="muted">status = settled · <code>result</code> = yes / no · {link(DOCS["settlement"], "Market Settlement")}</span></div>
  <div class="table-wrap">
    <table id="resolvedTable">
      <thead><tr><th>Topic</th><th>Ticker</th><th>Market</th><th>Result</th>
        <th class="num">Settlement $</th><th>Settled (UTC)</th><th>Source</th></tr></thead>
      <tbody>{settled_rows(settled, 25)}</tbody>
    </table>
  </div>
</div>
"""
    scripts = ('<script src="assets/chart.js"></script>\n<script src="assets/app.js"></script>')
    return layout("Dashboard", "index.html", body, depth=0, scripts=scripts)


def build_topic_page(topic, meta, markets, events, settled, books) -> str:
    options = "".join(f'<option value="{t["id"]}"{" selected" if t["id"] == topic["id"] else ""}>{esc(t["label"])}</option>'
                       for t in TOPICS)
    tabs = "".join(
        '<a href="pages/%s"%s>%s</a>' % (t["file"], ' class="active"' if t["id"] == topic["id"] else "", esc(t["label"]))
        for t in TOPICS
    )
    top = markets[0] if markets else None
    body = f"""
{crumb([("", "Dashboard"), (f'pages/{topic["file"]}', topic["label"])])}
<p class="eyebrow">Category</p>
<h1>{esc(topic["label"])}</h1>
<p class="lede">{esc(topic["blurb"])}</p>

<div class="card">
  <h3>How this page is scoped</h3>
  <p class="muted">{esc(topic["rule"])} The allowlist contains only official Kalshi tag and category
  strings published by {link(DOCS["tags_by_categories"], "Get Tags for Series Categories")} and returned by
  {link(DOCS["get_series"], "Get Series List")}. Markets inherit the topic of their series.</p>
  <div class="tabs">
    {tabs}
  </div>
</div>

<div class="grid grid-4" style="margin-bottom:14px">
  <div class="kpi"><div class="k">Open markets</div><div class="v" id="kpiMarkets">—</div><div class="s">{link(DOCS["get_markets"], "Get Markets")}</div></div>
  <div class="kpi"><div class="k">Contract value traded</div><div class="v" id="kpiTraded">—</div><div class="s">derived</div></div>
  <div class="kpi"><div class="k">Contracts traded</div><div class="v" id="kpiVolume">—</div><div class="s">volume_fp</div></div>
  <div class="kpi"><div class="k">In-scope events</div><div class="v" id="kpiEvents">—</div><div class="s">{link(DOCS["get_events"], "Get Events")}</div></div>
</div>

<div class="card">
  <div class="card-head"><h2>Open {esc(topic["label"].lower())} markets by dollar amount</h2>
    <span class="muted">click a row to chart it</span></div>
  <div class="table-wrap">
    <table id="marketTable">
      <caption>Every row links to the demo API response it was read from.</caption>
      <thead><tr>{''.join(f'<th>{esc(h)}</th>' for h in MARKET_HEAD)}</tr></thead>
      <tbody>{market_rows(markets, 40)}</tbody>
    </table>
  </div>
</div>

<div class="grid grid-2">
  <div class="card chart-card">
    <div class="card-head"><h2>Price movement</h2>
      <div style="min-width:190px"><label for="windowFilter">Graph length</label><select id="windowFilter"></select></div></div>
    <p class="muted">X axis = time · Y axis = contract price. History from Kalshi candlesticks; newest points are live snapshots.</p>
    <div class="chart-shell">
      <canvas id="priceChart" class="chart"></canvas>
      <div id="chartTip" style="display:none;position:absolute;background:#101a2b;color:#fff;padding:6px 9px;border-radius:8px;font-size:12px;pointer-events:none"></div>
    </div>
    <p class="muted" id="chartNote">—</p>
    <div class="chart-legend"><span><b id="selectedTitle">—</b></span><span class="mono" id="selectedTicker">—</span></div>
  </div>
  <div class="card">
    <h2>Selected market</h2>
    <dl class="kv">
      <dt>Last traded</dt><dd id="selLast">—</dd>
      <dt>YES bid</dt><dd id="selBid">—</dd>
      <dt>YES ask</dt><dd id="selAsk">—</dd>
      <dt>Contracts traded</dt><dd id="selVolume">—</dd>
      <dt>Open interest</dt><dd id="selOi">—</dd>
      <dt>Closes</dt><dd id="selClose">—</dd>
      <dt>Status</dt><dd id="selStatus">—</dd>
    </dl>
    <h3 style="margin-top:16px">Liquidity — contracts available at each price</h3>
    <div class="book">
      <div><h4>YES bids</h4><div id="bookYes" class="muted">—</div></div>
      <div><h4>NO bids</h4><div id="bookNo" class="muted">—</div></div>
    </div>
    <p class="muted" id="bookAt">—</p>
  </div>
</div>

<div class="card">
  <div class="card-head"><h2>{esc(topic["label"])} events</h2></div>
  <div class="table-wrap">
    <table id="eventTable">
      <thead><tr><th>Topic</th><th>Event</th><th class="num">Markets</th><th class="num">Contracts</th>
        <th class="num">Contract value traded $</th><th class="num">Open interest $</th><th>Closes (UTC)</th><th>Source</th></tr></thead>
      <tbody>{event_rows(events, 25)}</tbody>
    </table>
  </div>
</div>

<div class="card">
  <div class="card-head"><h2>Resolved {esc(topic["label"].lower())} markets</h2>
    <span class="muted">status = settled · result = yes / no</span></div>
  <div class="table-wrap">
    <table id="resolvedTable">
      <thead><tr><th>Topic</th><th>Ticker</th><th>Market</th><th>Result</th>
        <th class="num">Settlement $</th><th>Settled (UTC)</th><th>Source</th></tr></thead>
      <tbody>{settled_rows(settled, 25)}</tbody>
    </table>
  </div>
</div>
"""
    scripts = ('<script src="../assets/chart.js"></script>\n<script src="../assets/app.js"></script>')
    return layout(topic["label"], f'pages/{topic["file"]}', body, depth=1, scripts=scripts)


def build_executive_summary(meta, markets, events, settled, books) -> str:
    counts = meta.get("counts", {}) if meta else {}
    generated = when((meta or {}).get("generated_at"))
    total_traded = sum(num(m.get("contract_value_traded_usd")) or 0 for m in markets)
    yes = sum(1 for m in settled if m.get("result") == "yes")
    no = sum(1 for m in settled if m.get("result") == "no")
    topic_rows = []
    for t in TOPICS:
        rows = [m for m in markets if m.get("topic") == t["id"]]
        srows = [m for m in settled if m.get("topic") == t["id"]]
        topic_rows.append(
            "<tr>"
            f'<td><span class="tag {esc(t["id"])}">{esc(t["label"])}</span></td>'
            f'<td class="num">{len(rows)}</td>'
            f'<td class="num">{len(srows)}</td>'
            f'<td class="num">{money(sum(num(m.get("contract_value_traded_usd")) or 0 for m in rows), 0)}</td>'
            f'<td>{esc(t["rule"])}</td>'
            f'<td class="nowrap">{link(DOCS["tags_by_categories"], "taxonomy")}</td>'
            "</tr>"
        )
    body = f"""
{crumb([("", "Kalshi Demo Monitor"), (None, "Executive summary")])}
<p class="eyebrow">Executive summary</p>
<h1>What this system does, what it proves, and what it cannot yet do</h1>
<p class="lede">A single dashboard over the Kalshi <b>demo</b> environment covering five topics
(gas prices, elections, culture, crypto, golf), with live prices, liquidity, resolution
tracking, a verified data snapshot, and an explicit register of everything that is still unverified.</p>

<div class="grid grid-2">
  <div class="card">
    <h3>What is verified and working</h3>
    <ul class="tight">
      <li><b>Scope from the official taxonomy.</b> Markets are assigned to a topic using Kalshi's own
      series <code>category</code> and <code>tags</code>, published by
      {link(DOCS["tags_by_categories"], "Get Tags for Series Categories")}. No title-keyword guessing.</li>
      <li><b>A live snapshot pipeline.</b> {link(DOCS["get_markets"], "Get Markets")},
      {link(DOCS["get_events"], "Get Events")}, {link(DOCS["get_series"], "Get Series List")} and
      {link(DOCS["get_orderbook"], "Get Market Orderbook")} are collected by
      <code>scripts/fetch-data.mjs</code> on a GitHub Actions schedule; every request is logged in
      <code>data/collection-log.json</code>. Snapshot built: <b>{esc(generated or "—")}</b>.</li>
      <li><b>Real price history.</b> The chart uses Kalshi candlesticks
      ({link(DOCS["get_candles"], "Get Market Candlesticks")}) for the x-axis history and live REST
      snapshots for the newest points.</li>
      <li><b>Liquidity at a price.</b> The order book shows contracts resting at each bid price.</li>
      <li><b>Resolution tracking.</b> Settled markets are listed with their official
      <code>result</code> (yes / no) and settlement value.</li>
    </ul>
  </div>
  <div class="card">
    <h3>What is deliberately not claimed</h3>
    <ul class="tight">
      <li><b>No fabricated numbers.</b> Any field absent from an API response is rendered as
      <span class="unv">UNVERIFIED</span>, never guessed.</li>
      <li><b>No real-money trading.</b> Everything runs against the demo environment
      ({link(DOCS["demo"], "demo env")}); Kalshi warns demo prices may not reflect real markets.</li>
      <li><b>No account data without credentials.</b> Portfolio and trade screens stay blank until a
      demo API key is supplied in the browser; see {link("pages/portfolio.html", "Portfolio &amp; trading")}.</li>
      <li><b>No strategy without trades.</b> Strategy suggestions stay empty until real fills exist.</li>
    </ul>
  </div>
</div>

<div class="card">
  <h3>Scope and volume in the current snapshot</h3>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Topic</th><th class="num">Open markets</th><th class="num">Settled markets</th>
        <th class="num">Contract value traded</th><th>Scope rule (official strings)</th><th>Source</th></tr></thead>
      <tbody>{''.join(topic_rows)}</tbody>
    </table>
  </div>
  <p class="muted">Totals across all five topics: <b>{len(markets)}</b> open in-scope markets,
  <b>{len(events)}</b> in-scope events, <b>{len(settled)}</b> settled in-scope markets
  ({yes} resolved yes, {no} resolved no), {money(total_traded, 0)} of derived contract value traded.
  Contract value traded is a derived measure (contracts × last price), not an API field.</p>
</div>

<div class="grid grid-3">
  <div class="card"><h3>Live endpoints used</h3><ul class="tight">
    <li>{link(DOCS["get_markets"], "Get Markets")}</li>
    <li>{link(DOCS["get_market"], "Get Market")}</li>
    <li>{link(DOCS["get_orderbook"], "Get Market Orderbook")}</li>
    <li>{link(DOCS["get_candles"], "Get Market Candlesticks")}</li>
    <li>{link(DOCS["get_events"], "Get Events")}</li>
    <li>{link(DOCS["get_series"], "Get Series List")}</li>
    <li>{link(DOCS["tags_by_categories"], "Get Tags for Series Categories")}</li>
  </ul></div>
  <div class="card"><h3>Authenticated endpoints (portfolio / trading)</h3><ul class="tight">
    <li>{link(DOCS["get_balance"], "Get Balance")}</li>
    <li>{link(DOCS["get_positions"], "Get Positions")}</li>
    <li>{link(DOCS["get_fills"], "Get Fills")}</li>
    <li>{link(DOCS["get_orders"], "Get Orders")}</li>
    <li>{link(DOCS["create_order"], "Create Order")}</li>
    <li>{link(DOCS["auth"], "Quick start: authenticated requests")}</li>
  </ul></div>
  <div class="card"><h3>Read next</h3><ul class="tight">
    <li>{link("pages/questions.html", "Questions, information and answers needed")}</li>
    <li>{link("pages/suggestions.html", "Suggested improvements (review before implementing)")}</li>
    <li>{link("pages/flagged.html", "Flagged for review")}</li>
    <li>{link("pages/verification.html", "Line-by-line verification")}</li>
    <li>{link("pages/analysis.html", "Trade analysis and strategies")}</li>
  </ul></div>
</div>

<div class="card">
  <h3>Pipeline facts</h3>
  <dl class="kv">
    <dt>Snapshot generated</dt><dd>{esc(generated or "—")}</dd>
    <dt>API requests in the last harvest</dt><dd>{esc(counts.get("markets_collected") and meta.get("request_count") or meta.get("request_count"))}</dd>
    <dt>Series catalogue read</dt><dd>{esc(count((meta or {}).get("counts", {}).get("series_catalogue")))}</dd>
    <dt>Markets collected</dt><dd>{esc(count((meta or {}).get("counts", {}).get("markets_collected")))}</dd>
    <dt>Events collected</dt><dd>{esc(count((meta or {}).get("counts", {}).get("events_collected")))}</dd>
    <dt>Collector</dt><dd><code>scripts/fetch-data.mjs</code> (Node 20, public endpoints only)</dd>
  </dl>
</div>
"""
    return layout("Executive summary", "pages/executive-summary.html", body, depth=1)


def build_portfolio(meta, markets, events, settled, books) -> str:
    body = f"""
{crumb([("", "Kalshi Demo Monitor"), (None, "Portfolio & trading")])}
<p class="eyebrow">Demo account</p>
<h1>Portfolio performance and demo trade execution</h1>
<p class="lede">Connect your <b>demo</b> Kalshi account to load balance, positions, fills and
settlements, and to place demo orders. Requests are signed in your browser exactly as Kalshi
documents ({link(DOCS["auth"], "quick start: authenticated requests")}).</p>

<div class="notice warn">
  <h3>Security notice — read before connecting</h3>
  <p>This site is a <b>public static page</b>. Your private key is held in the page's memory only:
  it is never written to localStorage, sessionStorage or a cookie, and it is used for nothing except
  producing the request signature. It is still a public page, so treat it as a demo-only tool and
  use a demo key with the smallest useful scope. For production use, or to hold funds, put the
  signed calls behind a private backend with a secret manager — see
  {link("pages/suggestions.html", "suggestion S2")}. Never reuse a production key here.</p>
</div>

<div class="grid grid-2">
  <div class="card">
    <h2>1 · Connect a demo account</h2>
    <p class="muted">Create a key at <a href="{DOCS["demo_site"]}" target="_blank" rel="noopener">demo.kalshi.co</a>
    → <b>Account &amp; security → API Keys</b>. Kalshi issues RSA (PKCS#1) or Ed25519 keys;
    see {link(DOCS["api_key_generate"], "Generate API Key")}.</p>
    <div class="field">
      <label for="apiKeyId">Demo API Key ID</label>
      <input id="apiKeyId" type="text" autocomplete="off" spellcheck="false" placeholder="a952bcbe-ec3b-4b5b-b8f9-11dae589608c">
    </div>
    <div class="field">
      <label for="apiPrivateKey">Demo private key (PEM)</label>
      <textarea id="apiPrivateKey" rows="7" autocomplete="off" spellcheck="false"
        placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;…&#10;-----END RSA PRIVATE KEY-----"></textarea>
    </div>
    <div class="row">
      <button id="loadPortBtn">Load balance, positions and fills</button>
      <button class="secondary" id="clearCredsBtn" type="button">Clear from memory</button>
    </div>
    <p class="muted" style="margin-top:8px" id="credState">No credentials loaded.</p>
  </div>

  <div class="card">
    <h2>2 · Account snapshot</h2>
    <div id="portfolioBox" class="muted">Not connected. Balance, positions, fills and settlements stay blank until a demo key is loaded — no values are invented.</div>
  </div>
</div>

<div class="card">
  <div class="card-head"><h2>3 · Place a demo order</h2>
    <span class="muted">{link(DOCS["create_order"], "Create Order")} · {link(DOCS["order_direction"], "order direction")}</span></div>
  <p class="muted">Direction uses <code>outcome_side</code> (yes / no). Kalshi states that
  <code>outcome_side</code> and <code>book_side</code> are the canonical fields and that the legacy
  <code>action</code> / <code>side</code> fields are deprecated.</p>
  <div class="row">
    <div class="field" style="flex:2 1 240px"><label for="orderTicker">Market ticker</label>
      <input id="orderTicker" list="tickerList" placeholder="KXDEMOFUTHOURLY-26NOV20H12-UP" autocomplete="off">
      <datalist id="tickerList"></datalist></div>
    <div class="field"><label for="orderSide">Outcome side</label>
      <select id="orderSide"><option value="yes">yes</option><option value="no">no</option></select></div>
    <div class="field"><label for="orderCount">Contracts</label>
      <input id="orderCount" type="number" min="1" step="1" value="1"></div>
    <div class="field"><label for="orderPrice">Price (US$)</label>
      <input id="orderPrice" type="number" min="0.01" max="0.99" step="0.01" value="0.50"></div>
    <div class="field"><label for="orderType">Order type</label>
      <select id="orderType"><option value="limit">limit</option><option value="market">market</option></select></div>
  </div>
  <div class="row" style="margin-top:12px">
    <button id="placeOrderBtn">Place demo order</button>
    <button class="secondary" id="cancelOrderBtn" type="button">Cancel open orders</button>
  </div>
  <p class="muted" style="margin-top:8px">Orders are sent to the Kalshi <b>demo</b> exchange only.
  Demo funds are mock funds and cannot be withdrawn — see {link(DOCS["demo_help"], "Kalshi demo account help")}.</p>
  <div id="orderResult" style="margin-top:10px"></div>
</div>

<div class="card">
  <div class="card-head"><h2>4 · Trade log and categorisation</h2>
    <span class="muted">{link(DOCS["get_fills"], "Get Fills")} · {link(DOCS["get_positions"], "Get Positions")}</span></div>
  <div id="tradeLog"><p class="muted">No fills loaded. Fill-level categorisation (topic, side, strategy tag, outcome)
  appears here once fills exist — see {link("pages/analysis.html", "Analysis")}.</p></div>
</div>
"""
    scripts = '<script src="../assets/portfolio.js"></script>'
    return layout("Portfolio & trading", "pages/portfolio.html", body, depth=1, scripts=scripts)


def build_analysis(meta, markets, events, settled, books) -> str:
    topic_rows = []
    for t in TOPICS:
        rows = [m for m in markets if m.get("topic") == t["id"]]
        srows = [m for m in settled if m.get("topic") == t["id"]]
        yes = sum(1 for m in srows if m.get("result") == "yes")
        no = sum(1 for m in srows if m.get("result") == "no")
        prices = [num(m.get("last_price_dollars")) for m in rows]
        prices = [p for p in prices if p is not None]
        avg = sum(prices) / len(prices) if prices else None
        topic_rows.append(
            "<tr>"
            f'<td><span class="tag {esc(t["id"])}">{esc(t["label"])}</span></td>'
            f'<td class="num">{len(rows)}</td>'
            f'<td class="num">{cell(avg, lambda v: f"${v:.3f}")}</td>'
            f'<td class="num">{len(srows)}</td>'
            f'<td class="num">{yes}</td>'
            f'<td class="num">{no}</td>'
            f'<td class="num">{money(sum(num(m.get("contract_value_traded_usd")) or 0 for m in rows), 0)}</td>'
            "</tr>"
        )
    body = f"""
{crumb([("", "Kalshi Demo Monitor"), (None, "Analysis")])}
<p class="eyebrow">Analysis</p>
<h1>Trade analysis and strategy formation</h1>
<p class="lede">Two layers: what the <b>verified snapshot</b> says about the in-scope markets, and
what your <b>demo fills</b> say about your trading. Strategy rules are only produced once real
fills exist — until then the correct output is “no strategy”.</p>

<div class="card">
  <div class="card-head"><h2>Layer 1 — market structure in the snapshot</h2>
    <span class="muted">source: {link(DOCS["get_markets"], "Get Markets")} + {link(DOCS["get_events"], "Get Events")}</span></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Topic</th><th class="num">Open markets</th><th class="num">Mean last price</th>
        <th class="num">Settled</th><th class="num">Resolved yes</th><th class="num">Resolved no</th>
        <th class="num">Contract value traded</th></tr></thead>
      <tbody>{''.join(topic_rows)}</tbody>
    </table>
  </div>
  <p class="muted">“Mean last price” is the arithmetic mean of the <code>last_price_dollars</code> field
  across the open in-scope markets of that topic. It is a market-structure statistic, not a forecast.</p>
</div>

<div class="card">
  <div class="card-head"><h2>Layer 2 — trade review framework</h2>
    <span class="muted">applies to demo fills from {link(DOCS["get_fills"], "Get Fills")}</span></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Dimension</th><th>Field used</th><th>Official source</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td>Topic</td><td>series / event category of the traded market</td><td>{link(DOCS["tags_by_categories"], "Get Tags for Series Categories")}</td><td>computed from the snapshot series index</td></tr>
        <tr><td>Direction</td><td><code>outcome_side</code> (yes / no)</td><td>{link(DOCS["order_direction"], "Order direction")}</td><td>computed from fills</td></tr>
        <tr><td>Entry price</td><td><code>yes_price_dollars</code> / <code>no_price_dollars</code></td><td>{link(DOCS["get_fills"], "Get Fills")}</td><td>computed from fills</td></tr>
        <tr><td>Size</td><td><code>count_fp</code></td><td>{link(DOCS["get_fills"], "Get Fills")}</td><td>computed from fills</td></tr>
        <tr><td>Outcome</td><td>market <code>result</code> (yes / no) joined on ticker</td><td>{link(DOCS["get_markets"], "Get Markets")} (status=settled)</td><td>computed from fills + settled markets</td></tr>
        <tr><td>Net P&amp;L</td><td>settlement value − entry value − fees</td><td>{link(DOCS["fees"], "Fee Rounding")}</td><td>computed from fills; fees come from the fill response</td></tr>
        <tr><td>Strategy tag</td><td>entered by you at order time</td><td>—</td><td>not available yet — no fills in this account</td></tr>
      </tbody>
    </table>
  </div>
  <p class="muted">No win rate, drawdown or strategy is stated on this page because no demo fills are
  available to this session. The framework above is the exact computation that runs once
  {link("pages/portfolio.html", "fills are loaded")}.</p>
</div>

<div class="card">
  <h2>Strategy taxonomy (applied to real fills)</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Strategy tag</th><th>Entry rule</th><th>Exit rule</th><th>Minimum fills before reporting</th></tr></thead>
      <tbody>
        <tr><td><code>fade-spread</code></td><td>buy at or below the best bid when the YES spread is ≥ 3¢</td><td>hold to settlement</td><td>10</td></tr>
        <tr><td><code>near-miss</code></td><td>buy YES on a market whose last price is ≤ 0.15 and whose close is ≤ 7 days away</td><td>hold to settlement</td><td>10</td></tr>
        <tr><td><code>deep-liquidity</code></td><td>limit order at a price level holding ≥ 100 contracts</td><td>re-quote or cancel</td><td>10</td></tr>
        <tr><td><code>event-fade</code></td><td>buy NO when the event category is Crypto or Golf and the last price is ≥ 0.85</td><td>hold to settlement</td><td>10</td></tr>
      </tbody>
    </table>
  </div>
  <p class="muted">These are <b>hypothesis templates</b> for tagging, not validated strategies. They are
  only reported on with observed fills, and they must be tested out of sample before use. Demo
  prices may not reflect real markets ({link(DOCS["demo"], "demo env")}), so results do not transfer.</p>
</div>
"""
    return layout("Analysis", "pages/analysis.html", body, depth=1)


def build_suggestions(meta, markets, events, settled, books) -> str:
    suggestions = [
        ("S1", "Publish a signed series allowlist per topic",
         "The topic allowlists on the category pages are official Kalshi tag strings, but they were assembled by hand from the taxonomy endpoint. A generated allowlist file (topic → series tickers, refreshed by the collector) would make the scope reproducible and reviewable.",
         "https://docs.kalshi.com/api-reference/search/get-tags-for-series-categories",
         "High", "Medium"),
        ("S2", "Move signed requests to a private backend",
         "Browser-side signing keeps the private key on a public page. A small private service with the key in a secret manager, read-only by default and with an explicit trade-confirmation step, removes the exposure.",
         "https://docs.kalshi.com/getting_started/quick_start_authenticated_requests",
         "High", "High"),
        ("S3", "Add a WebSocket bridge for true tick-level updates",
         "Kalshi's WebSocket requires authentication headers, which a browser page cannot set. A relay (backend or browser extension) would give sub-second prices and order-book deltas instead of REST polling.",
         "https://docs.kalshi.com/getting_started/quick_start_websockets",
         "Medium", "Medium"),
        ("S4", "Rank on event dollar amount instead of market dollar amount",
         "The dashboard currently ranks markets and then rolls them up per event. Ranking the event directly, with its own toggle, matches the wording “highest dollar amount live events” more literally.",
         "https://docs.kalshi.com/api-reference/events/get-events",
         "Medium", "Low"),
        ("S5", "Persist the price history server-side",
         "Chart history is rebuilt from candlesticks on each load. Storing a rolling tape would allow long-window views, cross-market comparison and post-hoc strategy testing.",
         "https://docs.kalshi.com/api-reference/market/get-market-candlesticks",
         "Medium", "Medium"),
        ("S6", "Add settlement reconciliation against positions",
         "Joining settled markets to demo positions would produce realised P&L automatically, instead of asking the reviewer to reconcile manually.",
         "https://docs.kalshi.com/api-reference/portfolio/get-positions",
         "Medium", "Low"),
        ("S7", "Show the contract terms PDF beside every market row",
         "Each series exposes a contract_terms_url. Surfacing it next to the row makes the resolution rule reviewable in one click and reduces the false-positive risk of topic matching.",
         "https://docs.kalshi.com/api-reference/market/get-series-list",
         "Low", "Low"),
        ("S8", "Publish a per-topic settlement histogram",
         "Resolved yes/no counts per topic are the cheapest sanity check that the topic filter is not accidentally biased towards one outcome.",
         "https://docs.kalshi.com/getting_started/market_settlement",
         "Low", "Low"),
    ]
    cards = []
    for sid, title, body, src, impact, effort in suggestions:
        cards.append(f"""
<div class="card">
  <div class="card-head">
    <h3>{esc(sid)} · {esc(title)}</h3>
    <span class="pill">Impact: {esc(impact)}</span>
  </div>
  <p>{esc(body)}</p>
  <p class="muted">Source: {link(src)}</p>
  <div class="row">
    <button class="small" data-vote="{esc(sid)}" data-vote-label="Choose as the best path">Choose as the best path</button>
    <button class="small secondary" data-vote="{esc(sid)}" data-vote-label="Defer">Defer</button>
    <button class="small secondary" data-vote="{esc(sid)}" data-vote-label="Reject">Reject</button>
    <span class="muted" id="vote-{esc(sid)}">No decision recorded</span>
  </div>
</div>""")
    body_html = f"""
{crumb([("", "Kalshi Demo Monitor"), (None, "Suggestions")])}
<p class="eyebrow">Review board</p>
<h1>Suggested improvements</h1>
<p class="lede">Nothing here is implemented. Each suggestion is written so a reviewer can accept,
defer or reject it <b>before</b> any change is made. Your decision is stored in this browser only
(localStorage) and never leaves your device — it is a working aid, not a submission.</p>

<div class="notice">
  <h3>How to review</h3>
  <p>Read the suggestion, open its source link, then record a decision. Use
  {link("pages/questions.html", "Questions")} for anything you still need before deciding, and
  {link("pages/flagged.html", "Flagged for review")} for items that are already known to be irregular.</p>
</div>

{''.join(cards)}
"""
    scripts = '<script src="../assets/app.js"></script>'
    return layout("Suggestions", "pages/suggestions.html", body_html, depth=1, scripts=scripts)


def build_questions(meta, markets, events, settled, books) -> str:
    rows = [
        ("Q1", "What exactly does “highest dollar amount” mean?",
         "Get Markets returns <code>volume_fp</code> (contracts), <code>open_interest_fp</code> (contracts), <code>last_price_dollars</code> ($/contract) and <code>notional_value_dollars</code>, which Kalshi defines as the value of a single contract at settlement.",
         "There is no dollar-turnover field. The dashboard ranks on contracts × last price and labels it as derived; open-interest value is offered as an alternative.",
         "Choose one measure and make it the default; both are already available as options in the dashboard ranking selector.",
         DOCS["get_markets"]),
        ("Q2", "Which markets belong to each of the five topics?",
         "Kalshi publishes a category → tag taxonomy, and every series carries a category and tags.",
         "The allowlists are hand-assembled from official tag strings; a series whose topic is only implied by its title is excluded.",
         "Generate the allowlist from the taxonomy in the collector and publish it as a reviewable file (suggestion S1).",
         DOCS["tags_by_categories"]),
        ("Q3", "Which demo account and API key will be used?",
         "Demo keys are created in the Kalshi demo UI and are signed per request; no demo credentials exist in this repository.",
         "Without a key there is no balance, no positions, no fills and no executed trades, so portfolio performance cannot be reported yet.",
         "Create a demo key at demo.kalshi.co and load it in the browser on the Portfolio page, or provide a private backend (suggestion S2).",
         DOCS["keys"]),
        ("Q4", "How long should a market be tracked after it settles?",
         "Get Markets returns settled markets with <code>result</code>, <code>settlement_value_dollars</code> and <code>settlement_ts</code>.",
         "The snapshot keeps the settled rows collected for each topic; there is no long-term archive.",
         "Decide a retention window and store a settlement ledger per event.",
         DOCS["get_markets"]),
        ("Q5", "What price history should the chart use?",
         "Kalshi publishes candlesticks with 1, 60 and 1440 minute periods, limited to 5,000 periods per request.",
         "The chart therefore shows at most three days at daily resolution; a longer window needs a stored tape.",
         "Choose the maximum look-back and store it (suggestion S5).",
         DOCS["get_candles"]),
        ("Q6", "Is browser polling fast enough for decisions?",
         "REST market data is cached briefly and can lag the exchange by several seconds; Kalshi points to WebSockets for current prices.",
         "The dashboard polls, so it is a few seconds behind and never receives order-book deltas.",
         "Set a latency target and, if it matters, run the WebSocket bridge (suggestion S3).",
         DOCS["market_data"]),
        ("Q7", "Which liquidity measure should be shown?",
         "The order book returns resting YES and NO bids as [price, contracts] arrays; asks are the reciprocal of the other side's bids.",
         "Only bids are available; there is no separate ask ladder and no aggregated depth endpoint.",
         "Decide whether to show the reciprocal ask side, and at what depth.",
         DOCS["get_orderbook"]),
        ("Q8", "How should fees and net P&L be computed?",
         "Kalshi documents fee rounding and per-series fee structures (quadratic, with optional maker rebates).",
         "No fee is charged in the snapshot; net P&L can only be computed from real fills.",
         "Confirm the fee inputs once fills exist and define the P&L formula (suggestion S6).",
         DOCS["fees"]),
        ("Q9", "Is it acceptable to run signed requests from a public page?",
         "The signing scheme is documented and the key never leaves the page in this implementation.",
         "A public page is still the wrong place for a private key. No key is stored, but the exposure is non-zero.",
         "Move signing to a private backend (suggestion S2).",
         DOCS["auth"]),
        ("Q10", "Should demo results be used to judge a strategy?",
         "Kalshi warns that demo prices and behaviour may not reflect real markets.",
         "Demo P&L cannot validate a strategy for live trading.",
         "Agree up front that demo results are a pipeline test only, and require out-of-sample validation before any live use.",
         DOCS["demo"]),
    ]
    body = f"""
{crumb([("", "Kalshi Demo Monitor"), (None, "Questions")])}
<p class="eyebrow">Decision register</p>
<h1>Questions, information and answers needed</h1>
<p class="lede">Everything below is either answered from an official source, or explicitly left
open with the missing information named and a way to obtain it. No answer is invented.</p>
<div class="table-wrap">
  <table>
    <thead><tr><th>#</th><th>Question</th><th>What we know (verified)</th><th>What is missing</th>
      <th>How to obtain it</th><th>Source</th></tr></thead>
    <tbody>
      {''.join(f"<tr><td class='nowrap'>{esc(n)}</td><td>{q}</td><td>{known}</td><td>{missing}</td><td>{how}</td><td class='nowrap'>{link(src)}</td></tr>" for n, q, known, missing, how, src in rows)}
    </tbody>
  </table>
</div>
<div class="card" style="margin-top:14px">
  <h3>Questions that only the account owner can answer</h3>
  <ul class="tight">
    <li>Which demo API key will be connected, and who owns it?</li>
    <li>What is the maximum number of contracts a single demo order may place?</li>
    <li>Should orders be placed automatically, or only after an explicit per-order confirmation?</li>
    <li>Which categories may be traded at all, and which are observation-only?</li>
    <li>What is the stopping rule if the demo account loses a set fraction of its mock funds?</li>
  </ul>
  <p class="muted">These are policy decisions, not technical unknowns; they are not filled in on your behalf.</p>
</div>
"""
    return layout("Questions", "pages/questions.html", body, depth=1)


def build_flagged(meta, markets, events, settled, books) -> str:
    rows = [
        ("F1", "Demo data is not real-market data",
         "Kalshi states demo prices and market behaviour “may not be reflective of those in real markets”. Demo series also carry 2099 close dates and synthetic strikes.",
         "Any result derived from demo prices does not transfer to live trading.",
         "Every page carries the demo warning; no live-trading claim is made anywhere.",
         DOCS["demo"]),
        ("F2", "“Highest dollar amount” has no single API field",
         "Kalshi defines <code>notional_value_dollars</code> as the value of one contract at settlement, so it is not turnover. <code>volume_fp</code> and <code>open_interest_fp</code> are contract counts.",
         "Any dollar ranking is a derived measure and can be argued with.",
         "The derived measure is labelled on every row and the ranking metric is a user choice.",
         DOCS["get_markets"]),
        ("F3", "Topic scope is a hand-assembled allowlist",
         "The allowlists use official tag and category strings from Kalshi's taxonomy endpoint, but the exact set per topic was chosen here.",
         "A market that Kalshi considers in-scope may be excluded, or vice versa.",
         "Publish the generated allowlist and review it (suggestion S1).",
         DOCS["tags_by_categories"]),
        ("F4", "Only the top series per topic are collected",
         "The collector reads the highest-volume series per topic, because Get Series List returns <code>volume_fp</code> per series.",
         "A low-volume but relevant series may be missing from the snapshot.",
         "Raise <code>--series-per-topic</code> in the collector, or collect every in-scope series.",
         DOCS["get_series"]),
        ("F5", "A browser page may not be able to call the demo API",
         "Public demo endpoints need no authentication, but browser CORS behaviour for this origin could not be confirmed from the build environment.",
         "Live prices and the order book may fail to load in some browsers.",
         "The site falls back to the verified snapshot and labels the state; a same-origin proxy is the fix (suggestion S3).",
         DOCS["market_data"]),
        ("F6", "The WebSocket feed is not used",
         "Kalshi requires the three authentication headers on the WebSocket handshake, and browsers cannot set custom headers on a WebSocket.",
         "Prices are a few seconds behind, and there are no order-book deltas.",
         "Use a relay (suggestion S3).",
         DOCS["websockets"]),
        ("F7", "No demo API credentials are held by this project",
         "Demo keys are created by the account owner in the Kalshi demo UI and are signed per request.",
         "Portfolio performance, fills, settlements and executed trades cannot be reported until a key is loaded in the browser.",
         "Load a demo key on the Portfolio page, or provide a private backend (suggestion S2).",
         DOCS["keys"]),
        ("F8", "Signed requests run from a public page",
         "The private key is kept in page memory only; it is never written to storage and is only used to sign.",
         "A public page is not an appropriate place for a long-lived credential.",
         "Move signing to a private backend (suggestion S2).",
         DOCS["auth"]),
        ("F9", "Demo settlement sources contain placeholder text",
         "Several demo series list settlement sources with unfilled template text (for example “account holder of”) and some point at search-engine pages rather than a named source.",
         "The resolution rule for those contracts cannot be verified from the API alone.",
         "Read the contract terms PDF linked on each series before relying on a resolution.",
         DOCS["get_series_one"]),
        ("F10", "Chart history is capped by the candlestick API",
         "One candlestick request may span at most 5,000 periods; 1-minute data therefore reaches about 3.5 days, and the dashboard offers windows up to 3 days.",
         "Longer-horizon analysis needs stored history.",
         "Store a rolling tape (suggestion S5).",
         DOCS["get_candles"]),
        ("F11", "Collection is limited by unauthenticated rate limits",
         "Unauthenticated public requests have their own limits and return HTTP 429 without a Retry-After header.",
         "A harvest can be incomplete if the limit is hit repeatedly.",
         "The collector retries with exponential backoff and logs every request in <code>data/collection-log.json</code>.",
         DOCS["rate_limits"]),
        ("F12", "Strategy and win-rate claims are not made",
         "No demo fills are available to this session, so there is no realised P&L, no win rate and no drawdown.",
         "The strategy table on the Analysis page is a hypothesis taxonomy, not a result.",
         "Load fills on the Portfolio page and the analysis becomes computable.",
         DOCS["get_fills"]),
        ("F13", "Three earlier partial implementations existed in the repository",
         "Earlier parallel sessions had produced <code>pages/</code>, <code>verified/</code> and <code>dashboard/</code> trees, each with its own navigation and data snapshot.",
         "Duplicate navigation and contradictory figures were possible.",
         "This integration keeps one site, one design system and one snapshot pipeline; the previous trees are removed and their content is folded in.",
         "https://github.com/karagemop466-tech/Demo2"),
    ]
    body = f"""
{crumb([("", "Kalshi Demo Monitor"), (None, "Flagged for review")])}
<p class="eyebrow">Open items</p>
<h1>Flagged for review</h1>
<p class="lede">Irregularities and unverified items, each with the source needed to check it by hand.
None of them block the site. Review them after the site is live and ask for changes.</p>
<div class="table-wrap">
  <table>
    <thead><tr><th>#</th><th>Item</th><th>What was observed</th><th>Why it matters</th>
      <th>What was done</th><th>Source</th></tr></thead>
    <tbody>
      {''.join(f"<tr><td class='nowrap'>{esc(n)}</td><td><b>{esc(t)}</b></td><td>{obs}</td><td>{why}</td><td>{done}</td><td class='nowrap'>{link(src)}</td></tr>" for n, t, obs, why, done, src in rows)}
    </tbody>
  </table>
</div>
<div class="card" style="margin-top:14px">
  <h3>Repository flags</h3>
  <ul class="tight">
    <li>No LICENSE file is present in the repository.</li>
    <li>No secrets, API keys or market values are committed; the data files are public demo responses.</li>
    <li>Earlier sessions left three parallel site trees; this integration merged them into one.</li>
  </ul>
</div>
"""
    return layout("Flagged for review", "pages/flagged.html", body, depth=1)


def build_sources(meta, markets, events, settled, books) -> str:
    groups = [
        ("Environment and getting started", ["welcome", "demo", "envs", "market_data", "auth", "keys", "create_order", "order_errors", "websockets", "order_direction", "orderbook", "fixed_point", "pagination", "rate_limits", "settlement", "lifecycle", "fees", "historical", "mcp"]),
        ("Market and event data", ["get_markets", "get_market", "get_events", "get_series", "get_series_one", "get_orderbook", "get_candles", "get_trades", "tags_by_categories"]),
        ("Portfolio and trading", ["get_balance", "get_positions", "get_fills", "get_orders", "create_order", "api_key_generate"]),
        ("Other", ["changelog", "demo_site", "demo_help", "github_pages"]),
    ]
    blocks = []
    for title, keys in groups:
        items = "".join(f"<li>{link(DOCS[k])}</li>" for k in keys)
        blocks.append(f'<div class="card"><h3>{esc(title)}</h3><ul class="tight">{items}</ul></div>')
    base = (meta or {}).get("base_url") or "https://external-api.demo.kalshi.co/trade-api/v2"
    body = f"""
{crumb([("", "Kalshi Demo Monitor"), (None, "Sources")])}
<p class="eyebrow">References</p>
<h1>Sources</h1>
<p class="lede">Only official Kalshi documentation, the official Kalshi demo API and GitHub Pages
documentation are used. Third-party values are not used anywhere on this site.</p>
<div class="grid grid-2">{''.join(blocks)}</div>
<div class="card">
  <h3>API endpoints this site calls</h3>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Endpoint</th><th>Authentication</th><th>Used for</th><th>Documentation</th></tr></thead>
      <tbody>
        <tr><td class="mono">{esc(base)}/markets</td><td>none</td><td>Open and settled markets, prices, volume, results</td><td>{link(DOCS["get_markets"], "Get Markets")}</td></tr>
        <tr><td class="mono">{esc(base)}/markets/&#123;ticker&#125;</td><td>none</td><td>Live price of the selected market</td><td>{link(DOCS["get_market"], "Get Market")}</td></tr>
        <tr><td class="mono">{esc(base)}/markets/&#123;ticker&#125;/orderbook</td><td>none</td><td>Contracts resting at each price</td><td>{link(DOCS["get_orderbook"], "Get Market Orderbook")}</td></tr>
        <tr><td class="mono">{esc(base)}/series/&#123;series&#125;/markets/&#123;ticker&#125;/candlesticks</td><td>none</td><td>Historical price series for the chart</td><td>{link(DOCS["get_candles"], "Get Market Candlesticks")}</td></tr>
        <tr><td class="mono">{esc(base)}/events</td><td>none</td><td>Event titles, categories and settlement sources</td><td>{link(DOCS["get_events"], "Get Events")}</td></tr>
        <tr><td class="mono">{esc(base)}/series</td><td>none</td><td>Series category and tags used for topic scope</td><td>{link(DOCS["get_series"], "Get Series List")}</td></tr>
        <tr><td class="mono">{esc(base)}/search/tags_by_categories</td><td>none</td><td>Official category → tag taxonomy</td><td>{link(DOCS["tags_by_categories"], "Get Tags for Series Categories")}</td></tr>
        <tr><td class="mono">{esc(base)}/portfolio/balance</td><td>signed</td><td>Cash balance</td><td>{link(DOCS["get_balance"], "Get Balance")}</td></tr>
        <tr><td class="mono">{esc(base)}/portfolio/positions</td><td>signed</td><td>Open and settled positions</td><td>{link(DOCS["get_positions"], "Get Positions")}</td></tr>
        <tr><td class="mono">{esc(base)}/portfolio/fills</td><td>signed</td><td>Trade fills for the analysis</td><td>{link(DOCS["get_fills"], "Get Fills")}</td></tr>
        <tr><td class="mono">{esc(base)}/portfolio/orders</td><td>signed</td><td>Place and cancel demo orders</td><td>{link(DOCS["create_order"], "Create Order")}</td></tr>
      </tbody>
    </table>
  </div>
</div>
"""
    return layout("Sources", "pages/sources.html", body, depth=1)


def build_verification(meta, markets, events, settled, books) -> str:
    rows = [
        ("Recommended demo REST base is https://external-api.demo.kalshi.co/trade-api/v2", "https://external-api.demo.kalshi.co/trade-api/v2", DOCS["demo"], "Verified"),
        ("Also supported demo REST base is https://demo-api.kalshi.co/trade-api/v2", "https://demo-api.kalshi.co/trade-api/v2", DOCS["demo"], "Verified"),
        ("Recommended demo WebSocket is wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2", "wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2", DOCS["demo"], "Verified"),
        ("Demo uses mock funds and demo prices may not reflect real markets", "—", DOCS["demo"], "Verified"),
        ("Public market-data endpoints need no authentication", "—", DOCS["market_data"], "Verified"),
        ("Get Markets returns volume_fp, open_interest_fp, last_price_dollars, yes/no bid and ask, result, settlement_value_dollars and settlement_ts", "—", DOCS["get_markets"], "Verified"),
        ("notional_value_dollars is “the total value of a single contract at settlement in dollars”", "—", DOCS["get_markets"], "Verified"),
        ("_dollars fields are fixed-point dollar strings and _fp fields are contract counts", "—", DOCS["fixed_point"], "Verified"),
        ("Orderbook yes_dollars / no_dollars are [price, contracts] arrays, ascending, best bid last, and no asks are returned", "—", DOCS["orderbook"], "Verified"),
        ("Candlesticks accept period_interval 1, 60 or 1440 minutes and at most 5,000 periods per request", "—", DOCS["get_candles"], "Verified"),
        ("Series carry a category, categories and tags; the category → tag taxonomy is published", "—", DOCS["tags_by_categories"], "Verified"),
        ("Events carry an official category and a series_ticker; Get Events excludes multivariate events", "—", DOCS["get_events"], "Verified"),
        ("Authenticated requests need KALSHI-ACCESS-KEY, KALSHI-ACCESS-TIMESTAMP (ms) and KALSHI-ACCESS-SIGNATURE", "—", DOCS["auth"], "Verified"),
        ("The signed message is timestamp + method + path, without the query string; RSA uses PSS/SHA-256, Ed25519 signs directly", "—", DOCS["auth"], "Verified"),
        ("The timestamp must be within 30 seconds of the Kalshi clock", "—", DOCS["keys"], "Verified"),
        ("Order and fill direction is expressed by outcome_side (yes/no) and book_side (bid/ask); legacy action/side are deprecated", "—", DOCS["order_direction"], "Verified"),
        ("Unauthenticated requests have separate limits and return HTTP 429 with no Retry-After header; clients should back off", "—", DOCS["rate_limits"], "Verified"),
        ("Settled markets report result yes or no with a settlement value and settlement timestamp", "—", DOCS["settlement"], "Verified"),
        ("WebSocket connections require authentication headers, which a browser page cannot set", "—", DOCS["websockets"], "Verified"),
        ("Demo keys are issued as PKCS#1 RSA or PKCS#8 Ed25519 PEM keys", "—", DOCS["api_key_generate"], "Verified"),
        ("Live market values (prices, volumes, results) are read from the demo API at request time", "live only — never hard-coded", DOCS["get_markets"], "Verified live"),
        ("Realised P&L, win rate and drawdown for the demo account", "—", DOCS["get_fills"], "Unverified — no demo credentials; see F7"),
        ("Whether Kalshi's own site agrees with this site's topic grouping", "—", DOCS["tags_by_categories"], "Unverified — needs a reviewer with account access"),
        ("Browser CORS behaviour for the demo API from a public GitHub Pages origin", "—", DOCS["market_data"], "Unverified from the build environment — see F5"),
    ]
    body = f"""
{crumb([("", "Kalshi Demo Monitor"), (None, "Verification")])}
<p class="eyebrow">Line by line</p>
<h1>Verification</h1>
<p class="lede">Every factual claim the site relies on, checked against an official Kalshi page.
Anything that could not be confirmed from an official source is listed as unverified rather than filled in.</p>
<div class="table-wrap">
  <table>
    <thead><tr><th>Claim</th><th>Value</th><th>Official source</th><th>Status</th></tr></thead>
    <tbody>
      {''.join(f"<tr><td>{esc(c)}</td><td class='mono nowrap'>{esc(v)}</td><td class='nowrap'>{link(s)}</td><td>{status}</td></tr>" for c, v, s, status in rows)}
    </tbody>
  </table>
</div>
<div class="card" style="margin-top:14px">
  <h3>Snapshot provenance</h3>
  <dl class="kv">
    <dt>Generated</dt><dd>{esc(when((meta or {}).get("generated_at")) or "—")}</dd>
    <dt>Collector</dt><dd><code>scripts/fetch-data.mjs</code></dd>
    <dt>Request log</dt><dd><code>data/collection-log.json</code> (every URL and status code)</dd>
    <dt>API base</dt><dd class="mono">{esc((meta or {}).get("base_url") or "—")}</dd>
  </dl>
</div>
"""
    return layout("Verification", "pages/verification.html", body, depth=1)


# --------------------------------------------------------------------------
def main() -> int:
    os.makedirs(PAGES, exist_ok=True)
    meta = load("meta.json", {}) or {}
    open_markets = load("open-markets.json", {}) or {}
    open_events = load("open-events.json", {}) or {}
    settled = load("settled-markets.json", {}) or {}
    books = load("orderbooks.json", {}) or {}

    markets = [m for rows in (open_markets.get("topics") or {}).values() for m in rows]
    events = [e for rows in (open_events.get("topics") or {}).values() for e in rows]
    settled_rows = [m for rows in (settled.get("topics") or {}).values() for m in rows]

    written = []

    def write(path, content):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append(os.path.relpath(path, ROOT))

    write(os.path.join(ROOT, "index.html"),
          build_index(meta, markets, events, settled_rows, books))

    for topic in TOPICS:
        t_markets = [m for m in markets if m.get("topic") == topic["id"]]
        t_events = [e for e in events if e.get("topic") == topic["id"]]
        t_settled = [m for m in settled_rows if m.get("topic") == topic["id"]]
        write(os.path.join(PAGES, topic["file"]),
              build_topic_page(topic, meta, t_markets, t_events, t_settled, books))

    write(os.path.join(PAGES, "executive-summary.html"),
          build_executive_summary(meta, markets, events, settled_rows, books))
    write(os.path.join(PAGES, "portfolio.html"),
          build_portfolio(meta, markets, events, settled_rows, books))
    write(os.path.join(PAGES, "analysis.html"),
          build_analysis(meta, markets, events, settled_rows, books))
    write(os.path.join(PAGES, "suggestions.html"),
          build_suggestions(meta, markets, events, settled_rows, books))
    write(os.path.join(PAGES, "questions.html"),
          build_questions(meta, markets, events, settled_rows, books))
    write(os.path.join(PAGES, "flagged.html"),
          build_flagged(meta, markets, events, settled_rows, books))
    write(os.path.join(PAGES, "sources.html"),
          build_sources(meta, markets, events, settled_rows, books))
    write(os.path.join(PAGES, "verification.html"),
          build_verification(meta, markets, events, settled_rows, books))

    print("built:")
    for path in written:
        print("  ", path)
    print(f"markets={len(markets)} events={len(events)} settled={len(settled_rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
