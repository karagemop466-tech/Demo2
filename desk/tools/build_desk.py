#!/usr/bin/env python3
"""build_desk.py — generate the consolidated Kalshi demo desk.

Reads the official-API snapshots committed in `data/` (collected by the
repository's GitHub Actions workflows, because the authoring sandbox has no
route to the Kalshi demo API) plus the session's own registers, and writes a
small, clean, table-first site under `desk/`.

Every value written into a table row carries the official URL it came from.
Nothing is inferred: a value that cannot be traced to an official source is
rendered as a dash and flagged, never filled in.

    python3 desk/tools/build_desk.py

Outputs
    desk/index.html
    desk/categories/{gas,elections,culture,crypto,golf}.html
    desk/requirements.html
    desk/verification.html
    desk/irregularities.html
    desk/jumps.html
    desk/trading.html
    desk/data/summary.json
"""

from __future__ import annotations

import html
import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESK = ROOT / "desk"
DATA = DESK / "data"

API = "https://external-api.demo.kalshi.co/trade-api/v2"
DOCS = {
    "demo": "https://docs.kalshi.com/getting_started/demo_env",
    "markets": "https://docs.kalshi.com/api-reference/market/get-markets",
    "market": "https://docs.kalshi.com/api-reference/market/get-market",
    "series": "https://docs.kalshi.com/api-reference/market/get-series-list",
    "events": "https://docs.kalshi.com/api-reference/events/get-events",
    "orderbook": "https://docs.kalshi.com/api-reference/market/get-market-orderbook",
    "candles": "https://docs.kalshi.com/api-reference/market/get-market-candlesticks",
    "trades": "https://docs.kalshi.com/api-reference/market/get-trades",
    "balance": "https://docs.kalshi.com/api-reference/portfolio/get-balance",
    "positions": "https://docs.kalshi.com/api-reference/portfolio/get-positions",
    "fills": "https://docs.kalshi.com/api-reference/portfolio/get-fills",
    "order": "https://docs.kalshi.com/api-reference/orders/create-order-v2",
    "settlement": "https://docs.kalshi.com/getting_started/market_settlement",
    "lifecycle": "https://docs.kalshi.com/getting_started/market_lifecycle",
    "websockets": "https://docs.kalshi.com/getting_started/quick_start_websockets",
    "marketdata": "https://docs.kalshi.com/getting_started/quick_start_market_data",
    "ratelimits": "https://docs.kalshi.com/getting_started/rate_limits",
    "keys": "https://docs.kalshi.com/getting_started/api_keys",
}

TOPICS = [
    ("gas", "Gas prices"),
    ("elections", "Elections"),
    ("culture", "Culture"),
    ("crypto", "Crypto"),
    ("golf", "Golf"),
]

NAV = [
    ("Dashboard", "index.html"),
    ("Gas", "categories/gas.html"),
    ("Elections", "categories/elections.html"),
    ("Culture", "categories/culture.html"),
    ("Crypto", "categories/crypto.html"),
    ("Golf", "categories/golf.html"),
    ("Jumps", "jumps.html"),
    ("Trading", "trading.html"),
    ("Requirements", "requirements.html"),
    ("Verification", "verification.html"),
    ("Irregularities", "irregularities.html"),
]

FOOT = [
    ("Requirements", "requirements.html"),
    ("Verification", "verification.html"),
    ("Irregularities", "irregularities.html"),
]


# ----------------------------------------------------------------- helpers
def load(path: pathlib.Path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def money(value):
    n = num(value)
    if n is None:
        return "—"
    return "$" + format(n, ",.2f")


def contracts(value):
    n = num(value)
    if n is None:
        return "—"
    return format(n, ",.0f")


def price(value):
    n = num(value)
    if n is None:
        return "—"
    return format(n, ".4f")


def source_cell(url, label="source"):
    if not url:
        return '<span class="pill unverified">no source</span>'
    return f'<a href="{e(url)}" target="_blank" rel="noopener">{e(label)}</a>'


def stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def table(headers, rows, classes=None):
    """headers: list[str]; rows: list[list[str]] already HTML."""
    if not rows:
        return ('<p class="muted small">No rows. The official source returned nothing for '
                'this query, so nothing is listed here.</p>')
    cls = f' class="{classes}"' if classes else ""
    head = "".join(f"<th{h_}>{h}</th>" for h, h_ in zip(headers, headers))
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return (f'<div class="tbl-scroll"><table{cls}><thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def page(title: str, active: str, body: str, subtitle: str = "", depth: int = 0) -> str:
    """depth 0 = desk/index.html, depth 1 = desk/<dir>/page.html"""
    prefix = "../" * depth
    nav = "".join(
        '<a href="{}{}"{}>{}</a>'.format(prefix, href, ' aria-current="page"' if href == active else "", e(label))
        for label, href in NAV
    )
    foot_links = " · ".join(f'<a href="{prefix}{href}">{e(label)}</a>' for label, href in FOOT)
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · Kalshi Demo Desk</title>
<meta name="description" content="{e(subtitle or 'Consolidated Kalshi demo dashboard for gas prices, elections, culture, crypto and golf, with an official source link on every row.')}">
<link rel="stylesheet" href="{prefix}assets/desk.css">
</head><body>
<header class="top"><div class="in">
<div class="brand">Kalshi <b>Demo Desk</b><small>demo environment · mock funds · not investment advice</small></div>
<nav>{nav}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="in">
<div>Every row links the official Kalshi source it came from. Values that no official source confirms are shown as a dash and flagged.</div>
<div>{foot_links} · <a href="../index.html">Repository dashboard</a></div>
</div></footer>
<script src="{prefix}assets/desk.js"></script>
</body></html>
"""


# ------------------------------------------------------------------- data
def load_snapshot():
    snap = load(ROOT / "data" / "dashboard_instrument.json", {}) or {}
    return snap


def topic_markets(snap, topic):
    markets = snap.get("markets", {}) or {}
    rows = list(markets.get(topic) or [])
    if topic == "culture":
        rows = list(rows) + list(snap.get("markets_culture_adjacent") or [])
    return rows


def topic_series(snap, topic):
    return [s for s in (snap.get("series") or []) if s.get("topic") == topic]


def est_dollar(row):
    """Official fields only: volume_24h_fp x last_price_dollars."""
    vol = num(row.get("volume_24h_fp")) or 0.0
    px = num(row.get("last_price_dollars")) or 0.0
    return vol * px


def build_summary(snap, top_events):
    """Compact runtime data for desk.js (market picker + live chart)."""
    markets = []
    seen = set()
    for topic, _ in TOPICS:
        for row in topic_markets(snap, topic):
            ticker = row.get("ticker")
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            markets.append({
                "ticker": ticker,
                "series_ticker": row.get("series_ticker") or "",
                "event_ticker": row.get("event_ticker") or "",
                "title": row.get("title") or "",
                "topic": topic,
                "last_price_dollars": row.get("last_price_dollars"),
                "yes_bid_dollars": row.get("yes_bid_dollars"),
                "yes_ask_dollars": row.get("yes_ask_dollars"),
                "volume_24h_fp": row.get("volume_24h_fp"),
                "open_interest_fp": row.get("open_interest_fp"),
                "close_time": row.get("close_time") or "",
                "source_url": row.get("source_url") or (API + "/markets/" + ticker),
            })
    markets.sort(key=lambda m: (-(num(m.get("volume_24h_fp")) or 0.0), m["ticker"]))
    markets = markets[:120]

    summary = {
        "generated_at": stamp(),
        "api_base": API,
        "api_docs": DOCS["demo"],
        "source": "data/dashboard_instrument.json (collected from the official Kalshi demo Trade API)",
        "market_count": len(markets),
        "markets": markets,
        "top_events": top_events,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


# --------------------------------------------------------------- fragments
def kpi(label, value, sub=""):
    sub_html = f'<span>{e(sub)}</span>' if sub else ""
    return f'<div class="kpi"><b>{e(value)}</b><span>{e(label)}</span>{sub_html}</div>'


def topic_kpis(snap, topic, resolved_rows):
    series = topic_series(snap, topic)
    open_markets = [m for m in topic_markets(snap, topic)
                    if m.get("topic") == topic]
    yes = sum(1 for r in resolved_rows if r.get("result") == "yes")
    no = sum(1 for r in resolved_rows if r.get("result") == "no")
    traded = sum(1 for r in resolved_rows if (num(r.get("volume_fp")) or 0) > 0)
    cells = [
        kpi("Series in scope", len(series)),
        kpi("Open markets in snapshot", len(open_markets)),
        kpi("Resolved markets", len(resolved_rows)),
        kpi("Resolved yes", yes),
        kpi("Resolved no", no),
        kpi("Resolved that traded", traded, "volume above zero"),
    ]
    return f'<div class="kpis">{"".join(cells)}</div>'


def events_table(top_events, topic=None, limit=25):
    """Highest-dollar live events, from the official /events endpoint snapshot."""
    rows = []
    if topic:
        groups = [(topic, top_events.get(topic) or [])]
    else:
        groups = sorted(top_events.items())
    for name, items in groups:
        for ev in items:
            rows.append((name, ev))
    rows.sort(key=lambda pair: -(num(pair[1].get("est_dollar_volume_24h")) or 0.0))
    body = []
    for name, ev in rows[:limit]:
        lead = ev.get("lead_market") or {}
        body.append([
            f'<span class="pill">{e(name)}</span>',
            f'<a href="{e(ev.get("source"))}" target="_blank" rel="noopener" class="mono">{e(ev.get("event_ticker"))}</a>',
            e(ev.get("title")),
            f'<span class="num">{contracts(ev.get("volume_24h_contracts"))}</span>',
            f'<span class="num">{money(ev.get("est_dollar_volume_24h"))}</span>',
            f'<span class="num">{price(lead.get("last_price_dollars"))}</span>',
            e(ev.get("series_ticker")),
            source_cell(ev.get("source"), "event"),
        ])
    return table(
        ["Topic", "Event ticker", "Event", "24h volume (contracts)", "Est. 24h $", "Lead price",
         "Series", "Official source"],
        body,
    )


def open_markets_table(snap, topic, limit=40):
    rows = topic_markets(snap, topic)
    rows = sorted(rows, key=lambda r: (-(num(r.get("volume_24h_fp")) or 0.0),
                                       -(num(r.get("open_interest_fp")) or 0.0)))
    body = []
    for r in rows[:limit]:
        body.append([
            f'<span class="mono">{e(r.get("ticker"))}</span>',
            e(r.get("title")),
            f'<span class="num">{price(r.get("last_price_dollars"))}</span>',
            f'<span class="num">{price(r.get("yes_bid_dollars"))} / {price(r.get("yes_ask_dollars"))}</span>',
            f'<span class="num">{contracts(r.get("volume_24h_fp"))}</span>',
            f'<span class="num">{contracts(r.get("open_interest_fp"))}</span>',
            e((r.get("close_time") or "")[:10]),
            source_cell(r.get("source_url") or r.get("source_market_url"), "market"),
        ])
    return table(
        ["Market ticker", "Market", "Last price", "Yes bid / ask", "24h volume", "Open interest",
         "Close (UTC)", "Official source"],
        body,
    )


def resolved_tables(snap, topic, limit=20):
    rows = [r for r in (snap.get("resolved") or []) if r.get("topic") == topic]
    rows.sort(key=lambda r: r.get("close_time") or "", reverse=True)

    def block(result):
        picked = [r for r in rows if r.get("result") == result][:limit]
        body = []
        for r in picked:
            body.append([
                f'<span class="mono">{e(r.get("ticker"))}</span>',
                e(r.get("title")),
                f'<span class="pill {"yes" if result == "yes" else "no"}">{e(result)}</span>',
                e((r.get("close_time") or "")[:16].replace("T", " ")),
                f'<span class="num">{price(r.get("last_price_dollars"))}</span>',
                f'<span class="num">{contracts(r.get("volume_fp"))}</span>',
                source_cell(r.get("source_url"), "market"),
            ])
        return table(
            ["Market ticker", "Market", "Result", "Closed (UTC)", "Last price", "Volume",
             "Official source"],
            body,
        )

    out = [f"<h3>Resolved yes</h3>", block("yes"), f"<h3>Resolved no</h3>", block("no")]
    return "".join(out)


def settlement_sources_table(snap, topic):
    series = topic_series(snap, topic)
    body = []
    for s in series:
        srcs = s.get("settlement_sources") or []
        links = []
        for src in srcs[:3]:
            if src.get("url"):
                links.append(f'<a href="{e(src["url"])}" target="_blank" rel="noopener">{e(src.get("name") or src["url"])}</a>')
        body.append([
            f'<span class="mono">{e(s.get("ticker"))}</span>',
            e(s.get("title")),
            e(s.get("category")),
            ", ".join(e(t) for t in (s.get("tags") or [])) or "—",
            ", ".join(links) or '<span class="pill unverified">none published</span>',
            source_cell(API + "/series/" + s.get("ticker", ""), "series"),
        ])
    return table(
        ["Series ticker", "Series", "Kalshi category", "Kalshi tags", "Settlement source named by Kalshi",
         "Official source"],
        body,
    )


# ------------------------------------------------------------------ pages
def build_index(snap, top_events, summary, jumps):
    resolved = snap.get("resolved") or []
    cells = []
    for topic, label in TOPICS:
        series = topic_series(snap, topic)
        open_n = len([m for m in topic_markets(snap, topic) if m.get("topic") == topic])
        res = [r for r in resolved if r.get("topic") == topic]
        cells.append(kpi(label, f"{len(series)} / {open_n}",
                         "series / open markets"))
    cells.append(kpi("Resolved in snapshot", len(resolved), "official yes / no"))
    cells.append(kpi("Snapshot taken", (snap.get("meta") or {}).get("generated_at", "")[:16].replace("T", " "),
                     "official demo API"))
    body = f"""
<h1>Kalshi demo desk</h1>
<p class="lead">One place for the five topics in scope — <b>gas prices, elections, culture, crypto,
golf</b>. Every table row links the official Kalshi demo endpoint it came from. The browser talks to
the public demo API directly for the live chart and the order book; nothing is ever inferred, and a
value no official source confirms is shown as a dash and flagged.</p>
<div class="note">Demo environment only. Mock funds. No credential is requested, entered or stored by
this page. Source of every live number: the official Kalshi demo Trade API
(<a href="{e(DOCS['demo'])}" target="_blank" rel="noopener">demo environment</a>).</div>

<div class="kpis">{"".join(cells)}</div>

<h2>Live price and liquidity</h2>
<div class="grid two">
  <div class="card">
    <div class="row" style="justify-content:space-between;align-items:center">
      <h3 style="margin:0">Contract price over time</h3>
      <span id="liveBadge" class="badge snap">SNAPSHOT</span>
    </div>
    <p class="small muted" style="margin:4px 0 10px">X axis: time. Y axis: contract price in dollars,
    fixed 0.00 to 1.00. Choose the window length in seconds, minutes, hours or days.</p>
    <div class="row" style="margin-bottom:8px">
      <div style="flex:1 1 260px"><label for="mktSel">Market</label>
        <select id="mktSel" style="width:100%" data-default="{e(summary['markets'][0]['ticker']) if summary['markets'] else ''}"></select></div>
    </div>
    <div class="row" style="margin-bottom:8px">
      <label class="small" style="margin:0">Window</label>
      <div class="seg" id="winSeg" role="group" aria-label="Chart window"></div>
    </div>
    <div class="chartwrap"><canvas id="chart" class="chart"></canvas></div>
    <div class="legend"><span><span class="swatch" style="background:#38bdf8"></span>contract price (USD per $1 contract)</span>
      <span><span class="swatch" style="background:#22c55e"></span>rise of $0.10 or more</span>
      <span><span class="swatch" style="background:#f43f5e"></span>fall of $0.10 or more</span></div>
    <p class="small muted" id="chartNote" style="margin:6px 0 0"></p>
    <div class="row small muted" style="margin-top:8px;gap:16px">
      <span>market <b id="liveTicker">—</b></span><span id="liveTick">last quote —</span>
      <button class="link" type="button" id="refreshBtn">refresh now</button>
    </div>
    <p class="small muted" style="margin:6px 0 0" id="liveTitle"></p>
    <p class="small muted" style="margin:2px 0 0">Official source: <span id="liveSource"></span>
      · <span id="liveSeries"></span></p>
  </div>

  <div class="card">
    <h3>Quote and liquidity</h3>
    <div class="kpis" style="margin:6px 0 10px">
      <div class="kpi"><b id="qPrice">—</b><span>last price</span></div>
      <div class="kpi"><b id="qBid">—</b><span>yes bid</span></div>
      <div class="kpi"><b id="qAsk">—</b><span>yes ask</span></div>
      <div class="kpi"><b id="qSpread">—</b><span>spread</span></div>
      <div class="kpi"><b id="qVolume">—</b><span>24h volume</span></div>
      <div class="kpi"><b id="qOi">—</b><span>open interest</span></div>
    </div>
    <p class="small muted" id="depthMeta" style="margin:0 0 8px"></p>
    <p class="small muted" id="depthTotals" style="margin:0 0 8px;display:flex;gap:14px;flex-wrap:wrap"></p>
    <div class="grid" style="grid-template-columns:1fr 1fr;gap:12px">
      <div><h3 class="small">Yes bids resting</h3><div id="depthYes"></div></div>
      <div><h3 class="small">Yes asks (derived from no bids)</h3><div id="depthAsk"></div></div>
    </div>
    <p class="small muted" style="margin:8px 0 0">Kalshi publishes yes bids and no bids only. A no bid
    at price p is the same as a yes ask at 1 − p, so the ask ladder above is derived and labelled as such.</p>
  </div>
</div>

<h2>Sharp moves of $0.10 or more</h2>
<p class="lead">Moves detected in the window you are looking at, and the full list from the scheduled
detector. A cause is never asserted: Kalshi publishes no news feed, so the column that would carry one
stays empty and is flagged.</p>
<div id="jumpBox"><p class="muted small">Choose a market and a window above to detect moves in that series.</p></div>
<p class="small"><a href="jumps.html">All detected moves with official sources</a> · <span id="jumpCount"></span></p>

<h2>Highest-dollar live events</h2>
<div class="note">The Trade API has no dollar-volume field. Each row shows the official contract
volume and an <b>estimate</b> computed as <code>volume_24h_fp × last_price_dollars</code>. The
estimate is labelled as computed and is not an official field.</div>
{events_table(top_events, None, 30)}

<h2>Recently resolved</h2>
<p class="lead">A market stays tracked until Kalshi settles it. The official <code>result</code> field
is then <code>yes</code> or <code>no</code>, and that is what these rows show.</p>
{recent_resolutions_table(snap, 25)}

<h2>One page per topic</h2>
<div class="grid two">
{"".join(f'<div class="card"><h3><a href="categories/{t}.html">{e(l)}</a></h3><p class="small muted" style="margin:0">{e(topic_blurb(snap, t))}</p></div>' for t, l in TOPICS)}
</div>
"""
    return page("Dashboard", "index.html", body)


def topic_blurb(snap, topic):
    series = topic_series(snap, topic)
    open_n = len([m for m in topic_markets(snap, topic) if m.get("topic") == topic])
    res = [r for r in (snap.get("resolved") or []) if r.get("topic") == topic]
    yes = sum(1 for r in res if r.get("result") == "yes")
    no = sum(1 for r in res if r.get("result") == "no")
    return (f"{len(series)} series in scope, {open_n} open markets in the snapshot, "
            f"{len(res)} resolved ({yes} yes, {no} no).")


def recent_resolutions_table(snap, limit=25):
    rows = sorted((snap.get("resolved") or []),
                  key=lambda r: r.get("close_time") or "", reverse=True)[:limit]
    body = []
    for r in rows:
        result = r.get("result")
        pill = f'<span class="pill {"yes" if result == "yes" else "no"}">{e(result)}</span>' if result in ("yes", "no") \
            else f'<span class="pill unverified">{e(result or "no value published")}</span>'
        body.append([
            e(r.get("topic")),
            f'<span class="mono">{e(r.get("ticker"))}</span>',
            e(r.get("title")),
            pill,
            e((r.get("close_time") or "")[:16].replace("T", " ")),
            f'<span class="num">{price(r.get("last_price_dollars"))}</span>',
            f'<span class="num">{contracts(r.get("volume_fp"))}</span>',
            source_cell(r.get("source_url"), "market"),
        ])
    return table(
        ["Topic", "Market ticker", "Market", "Result", "Closed (UTC)", "Last price", "Volume",
         "Official source"],
        body,
    )


def build_category(snap, top_events, topic, label):
    resolved = [r for r in (snap.get("resolved") or []) if r.get("topic") == topic]
    scope = {t["id"]: t for t in ((snap.get("scope") or {}).get("topics") or [])}
    rule = (scope.get(topic) or {}).get("rule", "")
    queries = (scope.get(topic) or {}).get("queries", [])
    body = f"""
<h1>{e(label)}</h1>
<p class="lead">In-scope <b>{e(label)}</b> markets on the Kalshi demo exchange, ranked by dollar
activity, tracked to their official settlement, with the source of every row.</p>
<div class="note"><b>Scope rule.</b> {e(rule)} Official discovery queries:
{" ".join(f'<code>{e(q)}</code>' for q in queries) or "—"} — see
<a href="{e(DOCS['series'])}" target="_blank" rel="noopener">Get Series List</a>.</div>
{topic_kpis(snap, topic, resolved)}

<h2>Highest-dollar live events</h2>
<p class="lead">Estimated 24-hour dollar volume is computed from official fields
(<code>volume_24h_fp × last_price_dollars</code>); it is not an official API field.</p>
{events_table(top_events, topic, 20)}

<h2>Open markets</h2>
{open_markets_table(snap, topic, 50)}

<h2>Tracked until resolution</h2>
<p class="lead">Settled markets with the official <code>result</code>. A yes contract pays $1 and a no
contract pays $0 — see <a href="{e(DOCS['settlement'])}" target="_blank" rel="noopener">Market Settlement</a>.</p>
{resolved_tables(snap, topic, 20)}

<h2>Series in scope and their settlement sources</h2>
<p class="lead">The references Kalshi itself names for each series. These are the pages a trader would
read to understand what a contract settles against.</p>
{settlement_sources_table(snap, topic)}
"""
    if topic == "culture":
        body += """
<h2>Culture-adjacent markets</h2>
<div class="note">Kalshi files these series under the <b>Entertainment</b> category rather than
<b>Culture</b>. They are kept out of the culture counts above and listed here instead, with their
category stated, so nothing is silently reclassified.</div>
""" + culture_adjacent_table(snap)
    return page(label, f"categories/{topic}.html", body, depth=1)


def culture_adjacent_table(snap):
    rows = snap.get("markets_culture_adjacent") or []
    body = []
    for r in rows:
        body.append([
            f'<span class="mono">{e(r.get("ticker"))}</span>',
            e(r.get("title")),
            e(r.get("category") or "Entertainment"),
            f'<span class="num">{price(r.get("last_price_dollars"))}</span>',
            f'<span class="num">{contracts(r.get("volume_24h_fp"))}</span>',
            source_cell(r.get("source_url"), "market"),
        ])
    return table(
        ["Market ticker", "Market", "Kalshi category", "Last price", "24h volume", "Official source"],
        body,
    )


def build_requirements():
    reg = load(DATA / "requirements.json", {}) or {}
    items = reg.get("requirements") or []
    body = []
    for r in items:
        where = r.get("where")
        where_html = f'<a href="{e(where)}">{e(r.get("where_label") or where)}</a>' if where else \
            '<span class="pill unverified">not implemented</span>'
        ev = r.get("evidence")
        ev_html = source_cell(ev, r.get("evidence_label") or "official source") if ev else \
            '<span class="pill unverified">no official source</span>'
        status = r.get("status", "open")
        body.append([
            f'<span class="mono">{e(r.get("id"))}</span>',
            e(r.get("area")),
            e(r.get("requirement")),
            f'<span class="pill {status_class(status)}">{e(status)}</span>',
            where_html,
            ev_html,
            e(r.get("note") or ""),
        ])
    body_html = table(
        ["ID", "Area", "Requirement", "Status", "Where it lives", "Official evidence", "Note"],
        body,
    )
    counts = {}
    for r in items:
        counts[r.get("status", "open")] = counts.get(r.get("status", "open"), 0) + 1
    kpis = "".join(kpi(k.replace("-", " "), v) for k, v in sorted(counts.items()))
    text = f"""
<h1>Requirements register</h1>
<p class="lead">Every requirement in the brief, mapped to where it is met and to the official source
that supports the claim. A requirement is only marked implemented when the code and the official
evidence both exist; everything else is stated as it stands.</p>
<div class="kpis">{kpis}</div>
{body_html}
<p class="small muted" style="margin-top:14px">Register written {e(reg.get('updated') or stamp())}.
Source of the requirement text: the project brief for this repository.</p>
"""
    return page("Requirements", "requirements.html", text)


def status_class(status):
    return {
        "implemented": "yes",
        "verified": "yes",
        "partial": "flag",
        "not verified": "unverified",
        "open": "open",
        "blocked": "flag",
    }.get(status, "unverified")


def build_verification():
    report = load(DATA / "audit_report.json", None)
    if not report:
        body = """
<h1>Verification</h1>
<p class="lead">The line-by-line audit report is produced by the scheduled verification job. It has
not been generated on this branch yet.</p>
<div class="note warn">No report file is present, so nothing is claimed here. Run
<code>python3 desk/tools/verify.py</code> (the GitHub Actions runner has the outbound access the
authoring sandbox does not) to produce <code>desk/data/audit_report.json</code>.</div>
"""
        return page("Verification", "verification.html", body)

    rows = report.get("row_coverage") or []
    body_rows = []
    for r in rows:
        body_rows.append([
            e(r.get("file")),
            f'<span class="num">{e(r.get("rows"))}</span>',
            f'<span class="num">{e(r.get("with_source"))}</span>',
            f'<span class="num">{e(r.get("missing_source"))}</span>',
            f'<span class="num">{e(r.get("not_official"))}</span>',
            e(r.get("note") or ""),
        ])
    live_rows = []
    for r in (report.get("live_rechecks") or {}).get("details") or []:
        live_rows.append([
            f'<span class="mono">{e(r.get("ticker"))}</span>',
            e(r.get("field")),
            f'<span class="num">{e(r.get("snapshot"))}</span>',
            f'<span class="num">{e(r.get("live"))}</span>',
            f'<span class="pill {"yes" if r.get("match") else "flag"}">{"match" if r.get("match") else "differs"}</span>',
            source_cell(r.get("source"), "live endpoint"),
        ])
    text = f"""
<h1>Verification</h1>
<p class="lead">Every data row in the repository is checked for an official Kalshi source, and a sample
is re-fetched from the live official API and compared with the committed snapshot. Generated
{e(report.get('generated_at'))}.</p>
<div class="kpis">
{kpi("Rows checked", report.get("rows_checked", 0))}
{kpi("Rows with an official source", report.get("rows_with_official_source", 0))}
{kpi("Rows missing a source", report.get("rows_missing_source", 0))}
{kpi("Rows pointing somewhere else", report.get("rows_not_official", 0))}
{kpi("Live re-checks passed", (report.get("live_rechecks") or {}).get("ok", 0))}
{kpi("Live re-checks failed", (report.get("live_rechecks") or {}).get("failed", 0))}
</div>
<div class="note {'warn' if report.get('status') != 'pass' else ''}">
Overall status: <b>{e(report.get('status'))}</b>. {e(report.get('summary') or '')}
</div>

<h2>Source coverage by file</h2>
{table(["Data file", "Rows", "With official source", "Missing source", "Not an official URL", "Note"], body_rows)}

<h2>Live re-checks against the official API</h2>
{table(["Market ticker", "Field", "Committed snapshot", "Live official value", "Result", "Official source"], live_rows)}

<h2>What this verification does not cover</h2>
<ul class="tight">
<li>Portfolio, position, fill and order values: those endpoints need a Kalshi API key
(<a href="{e(DOCS['keys'])}" target="_blank" rel="noopener">API keys</a>). No key exists in this
repository, so every portfolio row stays blank and flagged rather than filled in.</li>
<li>The cause of a price move. Kalshi publishes no news feed in the Trade API, so no official source
can confirm why a price moved; the column stays empty.</li>
<li>WebSocket traffic: the demo WebSocket handshake requires signed headers
(<a href="{e(DOCS['websockets'])}" target="_blank" rel="noopener">Quick Start Websockets</a>), so the
browser pages use the REST endpoints, which need no credential.</li>
</ul>
"""
    return page("Verification", "verification.html", text)


def build_irregularities():
    reg = load(DATA / "irregularities.json", {}) or {}
    items = reg.get("items") or []
    body = []
    for it in items:
        sev = it.get("severity", "low")
        body.append([
            f'<span class="mono">{e(it.get("id"))}</span>',
            f'<span class="pill {"no" if sev == "high" else ("flag" if sev == "medium" else "unverified")}">{e(sev)}</span>',
            e(it.get("area")),
            e(it.get("finding")),
            e(it.get("action") or ""),
            source_cell(it.get("evidence"), "evidence"),
        ])
    text = f"""
<h1>Flagged for review</h1>
<p class="lead">Everything found while reviewing this repository line by line against official
sources. Nothing here is silently fixed or hidden; each item says what was found, what was done
about it, and where the evidence is.</p>
<div class="note">Review written {e(reg.get('updated') or stamp())}. Items do not block the site.</div>
{table(["ID", "Severity", "Area", "Finding", "Action taken", "Evidence"], body)}
"""
    return page("Irregularities", "irregularities.html", text)


def build_jumps():
    data = load(DATA / "jumps.json", None)
    if not data:
        text = """
<h1>Sharp moves</h1>
<p class="lead">The scheduled detector has not produced a report on this branch yet.</p>
<div class="note warn">No <code>desk/data/jumps.json</code> is present, so no move is listed. Run
<code>python3 desk/tools/jump_detect.py</code> from a host that can reach the demo API.</div>
"""
        return page("Sharp moves", "jumps.html", text)

    jumps = data.get("jumps") or []
    body = []
    for j in jumps:
        links = []
        for src in (j.get("settlement_sources") or [])[:2]:
            if src.get("url"):
                links.append(f'<a href="{e(src["url"])}" target="_blank" rel="noopener">{e(src.get("name") or src["url"])}</a>')
        body.append([
            e(j.get("topic")),
            f'<span class="mono">{e(j.get("ticker"))}</span>',
            e(j.get("title")),
            e(j.get("ts")),
            f'<span class="num">{price(j.get("from"))} &rarr; {price(j.get("to"))}</span>',
            f'<span class="num {"up" if j.get("delta", 0) > 0 else "down"}">{"+" if j.get("delta", 0) > 0 else ""}{j.get("delta")}</span>',
            f'<span class="pill unverified">not published</span>',
            ", ".join(links) or '<span class="pill unverified">none published</span>',
            source_cell(j.get("source"), "candles"),
        ])
    text = f"""
<h1>Sharp moves of $0.10 or more</h1>
<p class="lead">Consecutive official price points that differ by $0.10 or more in either direction,
detected from the Kalshi demo candlestick endpoint. Generated {e(data.get('generated_at'))} over
{e(data.get('markets_checked'))} markets using {e(data.get('requests'))} official requests.</p>
<div class="note warn"><b>Cause is not asserted.</b> The Kalshi Trade API publishes no news feed, so no
official source can confirm what caused a move. The column that would hold a cause is left empty and
flagged. The links beside it are the settlement references Kalshi itself names for that series —
the pages that determine the outcome, not a claim about the news.</div>
{table(["Topic", "Market ticker", "Market", "Time (UTC)", "Price", "Change", "Cause",
        "Reference named by Kalshi", "Official source"], body)}
<p class="small muted">Detection rule: two consecutive official candlestick closes whose absolute
difference is at least $0.10. Detector source:
<a href="{e(DOCS['candles'])}" target="_blank" rel="noopener">Get Market Candlesticks</a>.</p>
"""
    return page("Sharp moves", "jumps.html", text)


def build_trading():
    text = f"""
<h1>Trading, strategies and performance</h1>
<p class="lead">What the repository can and cannot do on a Kalshi demo account, and how trades are
categorised so a strategy can be tested against evidence rather than opinion.</p>

<div class="note warn"><b>No account values are shown on this page.</b> Portfolio, positions, fills and
order placement need a Kalshi API key. No key exists in this repository and none was invented, so
every value below is a dash and flagged. The three gates that must all open before a demo order is
sent are listed under <a href="#policy">Execution policy</a>.</div>

<h2>Portfolio and performance</h2>
{table(["Item", "Value", "Official source"], [
    ["Demo account balance", '<span class="pill unverified">unverified — needs an API key</span>', source_cell(DOCS["balance"], "Get Balance")],
    ["Open positions", '<span class="pill unverified">unverified — needs an API key</span>', source_cell(DOCS["positions"], "Get Positions")],
    ["Fills and realised profit and loss", '<span class="pill unverified">unverified — needs an API key</span>', source_cell(DOCS["fills"], "Get Fills")],
    ["Simulated (paper) trades", '<a href="../live/trading.html">interactive simulator</a>', source_cell(DOCS["market"], "Get Market")],
])}

<h2 id="policy">Execution policy</h2>
<p class="lead">Three independent gates must all be open before the repository will send a demo order.</p>
<ol class="tight">
<li>Repository secrets <code>KALSHI_DEMO_API_KEY_ID</code> and <code>KALSHI_DEMO_PRIVATE_KEY</code>
exist — see <a href="{e(DOCS['keys'])}" target="_blank" rel="noopener">API keys</a>.</li>
<li>Repository variable <code>KALSHI_TRADING_ENABLED=1</code> is set.</li>
<li>The order passes the executor's checks: the ticker is in the collector's in-scope set, no
duplicate tickers, and the order is inside the per-run notional cap.</li>
</ol>
<p class="lead">Orders use the documented V2 endpoint <code>POST /portfolio/events/orders</code>
(<a href="{e(DOCS['order'])}" target="_blank" rel="noopener">Create Order (V2)</a>). The legacy
<code>POST /portfolio/orders</code> returns 410 Gone and is not used. No browser page in this
repository asks for a private key.</p>

<h2>How trades are categorised</h2>
<p class="lead">Every trade is labelled on four axes so that a strategy is proposed only when the
evidence supports it. A bucket needs at least 10 trades before a pattern is described.</p>
{table(["Axis", "Values", "Why it matters"], [
    ["Topic", "gas, elections, culture, crypto, golf", "Behaviour differs by topic; the same price level means different things in each."],
    ["Side", "yes, no", "A no contract at price p is economically a yes contract at 1 − p, so the side changes the risk, not just the direction."],
    ["Price band", "0.00–0.10, 0.10–0.40, 0.40–0.70, 0.70–1.00", "Long shots pay differently from favourites; the bands are read from the contract price, not from the outcome."],
    ["Topic × side", "the cross of the two axes above", "Shows where an edge, if any, actually concentrates."],
])}

<h2>Strategies that can be tested today</h2>
{table(["Strategy", "What it does", "Where to run it"], [
    ["Paper round trip", "Buy and hold a simulated contract to settlement and score the result as yes or no.", '<a href="../live/trading.html">paper simulator</a>'],
    ["Liquidity sweep", "Walk the order book and report how many contracts are available at each price before a size is committed.", '<a href="index.html">depth ladder</a>'],
    ["Sharp-move reaction", "Act on a confirmed move of $0.10 or more rather than on a single quote.", '<a href="jumps.html">jump monitor</a>'],
    ["Resolution tracking", "Hold a market until Kalshi settles it and record the official result.", '<a href="categories/gas.html">topic pages</a>'],
])}

<h2>Where the numbers come from</h2>
<ul class="tight">
<li>Trade prints: <a href="{e(DOCS['trades'])}" target="_blank" rel="noopener">Get Trades</a>.</li>
<li>Resting liquidity: <a href="{e(DOCS['orderbook'])}" target="_blank" rel="noopener">Get Market Orderbook</a>.</li>
<li>Price history: <a href="{e(DOCS['candles'])}" target="_blank" rel="noopener">Get Market Candlesticks</a>.</li>
<li>Settlement values: <a href="{e(DOCS['settlement'])}" target="_blank" rel="noopener">Market Settlement</a>.</li>
</ul>
"""
    return page("Trading", "trading.html", text)


# ------------------------------------------------------------------- main
def main() -> int:
    snap = load_snapshot()
    top_events = (load(ROOT / "data" / "events_top.json", {}) or {}).get("topics") or {}
    summary = build_summary(snap, top_events)
    jumps = load(DATA / "jumps.json", None)

    written = []
    index = build_index(snap, top_events, summary, jumps)
    (DESK / "index.html").write_text(index, encoding="utf-8")
    written.append("desk/index.html")

    for topic, label in TOPICS:
        p = DESK / "categories" / f"{topic}.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(build_category(snap, top_events, topic, label), encoding="utf-8")
        written.append(f"desk/categories/{topic}.html")

    for name, builder in (
        ("requirements.html", build_requirements),
        ("verification.html", build_verification),
        ("irregularities.html", build_irregularities),
        ("jumps.html", build_jumps),
        ("trading.html", build_trading),
    ):
        (DESK / name).write_text(builder(), encoding="utf-8")
        written.append(f"desk/{name}")

    print(f"wrote {len(written)} pages")
    for w in written:
        print("  " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
