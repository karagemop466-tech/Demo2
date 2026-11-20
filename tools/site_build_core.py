#!/usr/bin/env python3
"""Build the Kalshi demo dashboard site (site/).

Inputs (all committed, all sourced):
  data/dashboard.json     - collected API snapshot (tools/kalshi_collect.py)
  site/content/*.json     - narrative pages: questions, suggestions, repo review, flags

Run: python3 tools/build_dashboard_site.py
"""
import html
import json
import os
import shutil
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data", "dashboard.json")
CONTENT = os.path.join(ROOT, "site", "content")
OUT = os.path.join(ROOT, "site")
REPO = "https://github.com/karagemop466-tech/Demo2"
PAGES_BASE = "https://karagemop466-tech.github.io/Demo2/site/"

E = html.escape

NAV = [
    ("index.html", "Overview"),
    ("gas.html", "Gas"),
    ("elections.html", "Elections"),
    ("culture.html", "Culture"),
    ("crypto.html", "Crypto"),
    ("golf.html", "Golf"),
    ("live.html", "Live &amp; Liquidity"),
    ("resolved.html", "Resolutions"),
    ("portfolio.html", "Portfolio &amp; Trades"),
    ("analysis.html", "Analysis"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("verification.html", "Verification"),
    ("repo-review.html", "Repo Review"),
    ("flagged.html", "Flagged for Review"),
]

TOPIC_META = {
    "gas": {"title": "Gas prices", "cls": "gas",
            "scope": "Series tagged <b>Oil and energy</b> (Kalshi category Economics) plus any Economics series whose title or ticker names gas, gasoline or diesel."},
    "elections": {"title": "Elections", "cls": "elections",
                  "scope": "Series whose Kalshi discovery categories include <b>Elections</b>."},
    "culture": {"title": "Culture", "cls": "culture",
                "scope": "Series whose Kalshi discovery categories include <b>Culture</b>. Kalshi files most entertainment contracts under <b>Entertainment</b>; those are listed on the Culture page as a clearly separated adjacent set."},
    "crypto": {"title": "Crypto", "cls": "crypto",
               "scope": "Series whose Kalshi discovery categories include <b>Crypto</b>."},
    "golf": {"title": "Golf", "cls": "golf",
             "scope": "Series carrying the Kalshi tag <b>Golf</b>. Golf is a tag under the Sports category in Kalshi's own tag list."},
}

D = {}
try:
    with open(DATA, encoding="utf-8") as fh:
        D = json.load(fh)
except Exception:
    D = {}


def load(name):
    p = os.path.join(CONTENT, name)
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def money(v, dash="—"):
    if v is None or v == "":
        return f'<span class="blank">{dash}</span>'
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return f'<span class="blank">{dash}</span>'


def price(v, dash="—"):
    if v is None or v == "":
        return f'<span class="blank">{dash}</span>'
    try:
        return f"${float(v):.4f}"
    except (TypeError, ValueError):
        return f'<span class="blank">{dash}</span>'


def count(v, dash="—"):
    if v is None or v == "":
        return f'<span class="blank">{dash}</span>'
    try:
        f = float(v)
        return f"{f:,.0f}" if f == int(f) else f"{f:,.2f}"
    except (TypeError, ValueError):
        return f'<span class="blank">{dash}</span>'


def ext(url, label=None):
    if not url:
        return ""
    return f'<a href="{E(url, quote=True)}" target="_blank" rel="noopener">{E(label or url)}</a>'


def badge(text, cls="info"):
    return f'<span class="b {cls}">{E(str(text))}</span>'


def top_nav_html(active=None):
    return "".join(f'<a href="{href}"{(" class=active" if href == active else "")}>{label}</a>' for href, label in NAV)


def demo_banner():
    return ('<div class="notice warn"><h4>Demo environment data — not real markets</h4>'
            'Every price, volume and resolution below comes from Kalshi\'s <b>demo</b> exchange '
            '(<a href="https://external-api.demo.kalshi.co/trade-api/v2" target="_blank" rel="noopener">external-api.demo.kalshi.co</a>). '
            'Kalshi states that demo prices and behaviour “may not be reflective of those in real markets”. '
            'See <a href="https://docs.kalshi.com/getting_started/demo_env" target="_blank" rel="noopener">demo environment docs</a>. '
            'No real money is involved anywhere on this site.</div>')


def page(filename, title, body, active=None, extra_head="", extra_script="", lede=""):
    nav = []
    for href, label in NAV:
        cls = ' class="active"' if href == active else ""
        nav.append(f'<a href="{href}"{cls}>{label}</a>')
    gen = (D.get("meta") or {}).get("generated_at", "not collected yet")
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} · Kalshi Demo Dashboard</title>
<meta name="description" content="Live Kalshi demo-market dashboard for gas prices, elections, culture, crypto and golf, with sourced data, verification and a flagged-for-review register.">
<link rel="stylesheet" href="assets/style.css">
{extra_head}
</head>
<body>
<header class="top">
  <div class="bar">
    <div class="brand"><a href="index.html">Kalshi <span>Demo</span> Dashboard</a></div>
    <span class="tagline">gas · elections · culture · crypto · golf — live demo market data</span>
    <span class="pill-demo">DEMO DATA</span>
    <span class="spacer"></span>
    <span class="tagline">snapshot {E(gen)}</span>
  </div>
  <nav class="nav">{"".join(nav)}</nav>
</header>
<main>
{f'<p class="lede">{lede}</p>' if lede else ''}
{body}
</main>
<footer class="site">
  <p><b>Sources.</b> Kalshi demo Trade API snapshot collected by <code>tools/kalshi_collect.py</code>; each table row links to the exact API response it was copied from.
  Definitions: <a href="https://docs.kalshi.com/getting_started/fixed_point_migration" target="_blank" rel="noopener">fixed-point fields</a> ·
  <a href="https://docs.kalshi.com/api-reference/market/get-market-orderbook" target="_blank" rel="noopener">orderbook</a> ·
  <a href="https://docs.kalshi.com/getting_started/market_settlement" target="_blank" rel="noopener">settlement</a>.</p>
  <p><b>Not financial advice.</b> Demo environment only; Kalshi states demo prices may not reflect real markets.
  Anything that could not be confirmed from an official source is left blank and listed on the
  <a href="flagged.html">Flagged for Review</a> page. Repository: {ext(REPO)}</p>
</footer>
{extra_script}
</body>
</html>
"""
    with open(os.path.join(OUT, filename), "w", encoding="utf-8") as fh:
        fh.write(doc)
    return doc


def status_badge(st):
    s = (st or "").lower()
    cls = "open" if s in ("active", "open") else "settled" if s in ("settled", "finalized", "closed", "determined") else "info"
    return badge(st or "—", cls)


def result_badge(res):
    r = (res or "").lower()
    if r == "yes":
        return badge("YES", "yes")
    if r == "no":
        return badge("NO", "no")
    return f'<span class="blank">—</span>'


def market_table(rows, show_topic=False, id_prefix="t"):
    if not rows:
        return '<p class="empty">No in-scope markets were returned by the API at collection time.</p>'
    head = ['<th class="num">Rank</th>', '<th>Market</th>', '<th>Event</th>']
    if show_topic:
        head.append("<th>Topic</th>")
    head += ['<th class="num">Last price</th>', '<th class="num">YES bid</th>', '<th class="num">YES ask</th>',
             '<th class="num">Volume (contracts)</th>', '<th class="num">Open interest</th>',
             '<th class="num">Notional (vol × price)</th>', '<th>Status</th>', '<th class="num">Close time</th>',
             '<th>Source</th>']
    body = []
    for i, m in enumerate(rows, 1):
        src = m.get("source_market_url") or m.get("source_url")
        cells = [
            f'<td class="num">{i}</td>',
            f'<td><div><b>{E(str(m.get("ticker") or ""))}</b></div><div class="small muted">{E(str(m.get("title") or ""))}</div></td>',
            f'<td class="small">{E(str(m.get("event_title") or m.get("event_ticker") or ""))}</td>',
        ]
        if show_topic:
            tid = m.get("topic") or ""
            meta = TOPIC_META.get(tid, {"title": tid, "cls": "info"})
            cells.append(f'<td>{badge(meta["title"], meta["cls"])}</td>')
        cells += [
            f'<td class="num">{price(m.get("last_price_dollars"))}</td>',
            f'<td class="num">{price(m.get("yes_bid_dollars"))}</td>',
            f'<td class="num">{price(m.get("yes_ask_dollars"))}</td>',
            f'<td class="num">{count(m.get("volume_fp"))}</td>',
            f'<td class="num">{count(m.get("open_interest_fp"))}</td>',
            f'<td class="num">{money(m.get("notional_lifetime_usd"))}</td>',
            f'<td>{status_badge(m.get("status"))}</td>',
            f'<td class="num small">{E(str(m.get("close_time") or "")[:16].replace("T", " "))}</td>',
            f'<td class="small">{ext(src, "API")} · {ext(m.get("source_url"), "list")}</td>',
        ]
        body.append("<tr>" + "".join(cells) + "</tr>")
    return ('<div class="tablewrap"><table><thead><tr>' + "".join(head) + "</tr></thead><tbody>"
            + "".join(body) + "</tbody></table></div>")


def series_table(rows, show_topic=False):
    if not rows:
        return '<p class="empty">No series returned.</p>'
    head = "<tr><th>Series</th><th>Title</th><th>Frequency</th><th>Tags</th><th>Fee type</th><th>Settlement source(s)</th><th>Contract terms</th></tr>"
    out = []
    for s in rows:
        ss = s.get("settlement_sources") or []
        ss_html = "<br>".join(ext(x.get("url"), x.get("name") or x.get("url")) for x in ss[:4])
        if len(ss) > 4:
            ss_html += f'<div class="small muted">+{len(ss) - 4} more (see API)</div>'
        out.append(
            "<tr>"
            f'<td class="tick"><b>{E(str(s.get("ticker") or ""))}</b></td>'
            f'<td>{E(str(s.get("title") or ""))}</td>'
            f'<td>{E(str(s.get("frequency") or ""))}</td>'
            f'<td class="small">{E(", ".join(s.get("tags") or []) or "—")}</td>'
            f'<td class="small">{E(str(s.get("fee_type") or ""))} ×{E(str(s.get("fee_multiplier")))}</td>'
            f'<td class="small">{ss_html or "<span class=blank>—</span>"}</td>'
            f'<td class="small">{ext(s.get("contract_terms_url"), "terms")}</td>'
            "</tr>"
        )
    return '<div class="tablewrap"><table><thead>' + head + "</thead><tbody>" + "".join(out) + "</tbody></table></div>"


def resolved_table(rows):
    if not rows:
        return '<p class="empty">No settled in-scope markets were returned at collection time.</p>'
    head = ("<tr><th>Result</th><th>Market</th><th>Series</th><th class=\"num\">Final price</th>"
            "<th class=\"num\">Volume</th><th class=\"num\">Open interest</th><th>Close</th><th>Source</th></tr>")
    out = []
    for r in rows:
        out.append(
            "<tr>"
            f'<td>{result_badge(r.get("result"))}</td>'
            f'<td><div><b>{E(str(r.get("ticker") or ""))}</b></div><div class="small muted">{E(str(r.get("title") or ""))}</div></td>'
            f'<td class="tick small">{E(str(r.get("series_title") or r.get("series_ticker") or ""))}</td>'
            f'<td class="num">{price(r.get("last_price_dollars"))}</td>'
            f'<td class="num">{count(r.get("volume_fp"))}</td>'
            f'<td class="num">{count(r.get("open_interest_fp"))}</td>'
            f'<td class="small num">{E(str(r.get("close_time") or "")[:16].replace("T", " "))}</td>'
            f'<td class="small">{ext(r.get("source_market_url"), "API")}</td>'
            "</tr>"
        )
    return '<div class="tablewrap"><table><thead>' + head + "</thead><tbody>" + "".join(out) + "</tbody></table></div>"


def kpi(label, value, sub="", cls=""):
    return (f'<div class="kpi {cls}"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="sub">{sub}</div></div>')


def all_markets():
    rows = []
    for tid, ms in (D.get("markets") or {}).items():
        for m in ms:
            m2 = dict(m)
            m2.setdefault("topic", tid)
            rows.append(m2)
    rows.sort(key=lambda m: (m.get("open_interest_usd") or -1), reverse=True)
    return rows


def resolved_all():
    rows = list(D.get("resolved") or [])
    rows.sort(key=lambda r: (r.get("last_price_used") or -1), reverse=True)
    return rows
