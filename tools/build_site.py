#!/usr/bin/env python3
"""Render the category pages from the collected Kalshi demo snapshot.

Reads data/*.json (written by tools/collect_kalshi.py) and writes
pages/<topic>.html.  Every data row carries the exact API response URL it was
read from, so each row on the site can be checked line by line against the
official Kalshi API.

    python3 tools/build_site.py

Nothing is inferred: a value that is missing from the API response is rendered
blank and marked unverified.
"""

import html
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
PAGES = os.path.join(ROOT, "pages")

TOPICS = [
    ("gas-prices", "gas.html", "Gas prices",
     "Gasoline, diesel, crude-oil and national/state fuel-price contracts.",
     "Official Kalshi category <b>Commodities</b> (tag “Oil &amp; Gas”) and <b>Economics</b> "
     "(tag “Oil and energy”), plus title-keyword matches for gas, diesel and crude oil."),
    ("elections", "elections.html", "Elections",
     "Election, primary, ballot, nominee and control contracts.",
     "Official Kalshi category <b>Elections</b>, plus title-keyword matches for election, primary, "
     "ballot and nominee."),
    ("culture", "culture.html", "Culture",
     "Film, music, television, award and celebrity contracts.",
     "Official Kalshi category <b>Entertainment</b> (tags Movies, Music, Awards, Television, People, "
     "Oscars, Grammys, …), plus title-keyword matches. Note: the official category list published at "
     "<code>/search/tags_by_categories</code> contains <b>Entertainment</b> and no “Culture” category — "
     "see the Flagged page."),
    ("crypto", "crypto.html", "Crypto",
     "Bitcoin, Ethereum, Solana, Dogecoin and other crypto contracts.",
     "Official Kalshi category <b>Crypto</b>, plus title-keyword matches for bitcoin, ethereum, solana "
     "and dogecoin."),
    ("golf", "golf.html", "Golf",
     "PGA, LPGA, major-championship and Ryder Cup contracts.",
     "Official Kalshi tag <b>Golf</b> under category <b>Sports</b>, plus title-keyword matches for golf, "
     "PGA and the majors."),
]

FOOTER = """<footer class="site">
  <div class="inner">
    <span>Kalshi Demo Dashboard · demo environment only · no real funds · research, not advice</span>
    <a href="https://docs.kalshi.com/getting_started/demo_env" target="_blank" rel="noopener">Demo environment docs</a>
    <a href="{sources}">All sources</a>
    <a href="{coord}">Coordination log</a>
  </div>
</footer>"""


def e(v):
    """HTML-escape and render an empty value as an explicit unverified blank."""
    if v is None or v == "":
        return '<span class="blank" title="Not present in the API response — unverified">—</span>'
    return html.escape(str(v))


def money(v):
    if v is None or v == "":
        return e("")
    try:
        return "$" + ("%.4f" % float(v)).rstrip("0").rstrip(".") if float(v) != 0 else "$0.00"
    except (TypeError, ValueError):
        return e(v)


def nav_html():
    """Reuse the navigation block from index.html so there is one source of truth."""
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as fh:
        idx = fh.read()
    m = re.search(r'<nav class="main">.*?</nav>', idx, re.S)
    if not m:
        raise SystemExit("could not find the navigation block in index.html")
    nav = m.group(0)
    return nav


def nav_for_subdir(nav):
    """Rewrite the root-relative navigation so it also works from pages/."""
    out = nav.replace('href="index.html"', 'href="../index.html"')
    out = out.replace('href="pages/', 'href="')
    return out


def load(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def source_link(url, label="source"):
    if not url:
        return '<span class="blank" title="Not present in the API response — unverified">—</span>'
    return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (html.escape(url), html.escape(label))


def market_rows(rows):
    out = []
    for r in rows:
        est = r.get("dollar_turnover_estimate")
        out.append(
            "<tr>"
            '<td class="mono nowrap"><a href="%s" target="_blank" rel="noopener">%s</a></td>'
            "<td>%s<div class=\"muted small mono\">%s</div></td>"
            "<td><span class=\"pill\">%s</span><div class=\"muted small\">%s: %s</div></td>"
            '<td class="num">%s</td>'
            '<td class="num">%s</td>'
            '<td class="num">%s</td>'
            '<td class="num">%s</td>'
            '<td class="num">%s</td>'
            '<td class="num">%s</td>'
            '<td class="nowrap small">%s</td>'
            "<td>%s</td>"
            "</tr>" % (
                html.escape(r.get("source_url") or ""), html.escape(r.get("ticker") or ""),
                e(r.get("title")), e(r.get("series_ticker") or r.get("event_ticker") or ""),
                e(r.get("topic_label") or r.get("topic")),
                e(r.get("classification_basis")), e(r.get("classification_detail")),
                money(r.get("last_price_dollars")), money(r.get("yes_bid_dollars")),
                money(r.get("yes_ask_dollars")), e(r.get("volume_fp")),
                ("$" + ("%.2f" % float(est))) if est not in ("", None) else e(""),
                e(r.get("open_interest_fp")), e(r.get("close_time")),
                source_link(r.get("source_url"), "API"),
            ))
    if not out:
        return '<tr class="placeholder"><td colspan="11" class="muted">No rows in the collected snapshot for this topic.</td></tr>'
    return "\n".join(out)


def settled_rows(rows):
    out = []
    for r in rows:
        res = (r.get("result") or "").lower()
        cls = "yes" if res == "yes" else ("no" if res == "no" else "grey")
        label = "YES" if res == "yes" else ("NO" if res == "no" else e(""))
        out.append(
            "<tr>"
            '<td class="mono nowrap"><a href="%s" target="_blank" rel="noopener">%s</a></td>'
            "<td>%s</td>"
            '<td><span class="pill %s">%s</span></td>'
            '<td class="num">%s</td>'
            '<td class="nowrap small">%s</td>'
            '<td class="nowrap small">%s</td>'
            "<td>%s</td>"
            "</tr>" % (
                html.escape(r.get("source_url") or ""), html.escape(r.get("ticker") or ""),
                e(r.get("title")), cls, label,
                money(r.get("settlement_value_dollars")), e(r.get("settlement_ts")),
                e(r.get("close_time")), source_link(r.get("source_url"), "API"),
            ))
    if not out:
        return '<tr class="placeholder"><td colspan="8" class="muted">No settled rows in the collected snapshot for this topic.</td></tr>'
    return "\n".join(out)


def series_rows(rows):
    out = []
    for r in rows:
        srcs = r.get("settlement_sources") or []
        if srcs:
            links = "<br>".join(
                '<a href="%s" target="_blank" rel="noopener">%s</a>' % (html.escape(s.get("url") or ""), e(s.get("name")))
                for s in srcs[:4]
            )
        else:
            links = e("")
        out.append(
            "<tr>"
            '<td class="mono nowrap"><a href="%s" target="_blank" rel="noopener">%s</a></td>'
            "<td>%s</td>"
            "<td>%s</td>"
            '<td class="small">%s</td>'
            "<td>%s</td>"
            '<td class="small">%s</td>'
            "</tr>" % (
                html.escape(r.get("source_url") or ""), html.escape(r.get("series_ticker") or ""),
                e(r.get("title")), e(r.get("category")),
                ", ".join(r.get("tags") or []) or e(""),
                links,
                source_link(r.get("source_url"), "API"),
            ))
    if not out:
        return '<tr class="placeholder"><td colspan="7" class="muted">No series rows in the collected snapshot for this topic.</td></tr>'
    return "\n".join(out)


def depth_rows(orderbooks, topic):
    rows = []
    for t, ob in sorted(orderbooks.items()):
        if ob.get("topic") != topic:
            continue
        yes = ob.get("yes") or []
        no = ob.get("no") or []
        best_yes = yes[-1] if yes else None
        best_no = no[-1] if no else None
        implied_yes_ask = ("%.4f" % (1 - float(best_no[0]))) if best_no else ""
        rows.append(
            "<tr>"
            '<td class="mono nowrap"><a href="%s" target="_blank" rel="noopener">%s</a></td>'
            "<td>%s</td>"
            '<td class="num">%s</td>'
            '<td class="num">%s</td>'
            '<td class="num">%s</td>'
            '<td class="num">%s</td>'
            "<td>%s</td>"
            "</tr>" % (
                html.escape(ob.get("source_url") or ""), html.escape(t),
                e(ob.get("title")),
                money(best_yes[0]) if best_yes else e(""),
                e(best_yes[1]) if best_yes else e(""),
                money(best_no[0]) if best_no else e(""),
                e(best_no[1]) if best_no else e(""),
                source_link(ob.get("source_url"), "API"),
            ))
        rows.append(
            "<tr><td colspan=\"7\" class=\"small muted\">Implied best YES ask from the best NO bid: %s</td></tr>"
            % (("$" + implied_yes_ask) if implied_yes_ask else e("")))
    if not rows:
        return '<tr class="placeholder"><td colspan="7" class="muted">No orderbook snapshots collected for this topic.</td></tr>'
    return "\n".join(rows)


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Kalshi Demo Dashboard</title>
<meta name="description" content="{blurb} Verified Kalshi demo market rows, each linked to the official API response it came from.">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<header class="top">
  <div class="inner">
    <a class="brand" href="../index.html"><span>KALSHI</span> DEMO<small>RESEARCH DASHBOARD</small></a>
    {nav}
    <span class="tag">DEMO · NO REAL FUNDS</span>
  </div>
</header>

<div class="wrap">
  <p class="eyebrow">Category · {title}</p>
  <h1>{title}</h1>
  <p class="lede">{blurb}</p>

  <div class="callout">
    <b>How this topic was selected.</b>
    <span>{scope}</span>
  </div>

  <div class="card">
    <h3>Open markets in scope</h3>
    <p class="muted small">
      Sorted by estimated dollar turnover (<code>volume_fp × last_price_dollars</code>). The Kalshi API reports
      volume in contracts and has no dollar-turnover field, so the dollar column is a labelled estimate.
      Each row links to the exact API response it was read from.
    </p>
    <div class="tablewrap">
      <table>
        <thead><tr>
          <th>Ticker</th><th>Title</th><th>Topic / basis</th>
          <th class="num">Last $</th><th class="num">YES bid</th><th class="num">YES ask</th>
          <th class="num">Volume (contracts)</th><th class="num">Est. $ turnover</th>
          <th class="num">Open interest</th><th>Close (UTC)</th><th>Source</th>
        </tr></thead>
        <tbody>
{market_rows}
        </tbody>
      </table>
    </div>
    <p class="muted small">Blank cells mean the field was not present in the API response — they are unverified, not zero.</p>
  </div>

  <div class="card">
    <h3>Orderbook depth — contracts available at each price</h3>
    <p class="muted small">
      Best bid per side plus the implied YES ask (<code>$1.00 − best NO bid</code>). Kalshi publishes bids only.
      Full live depth is on the <a href="../index.html">dashboard</a>.
    </p>
    <div class="tablewrap">
      <table>
        <thead><tr><th>Ticker</th><th>Title</th><th class="num">Best YES bid</th><th class="num">YES bid contracts</th>
        <th class="num">Best NO bid</th><th class="num">NO bid contracts</th><th>Source</th></tr></thead>
        <tbody>
{depth_rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <h3>Resolved markets — how each one settled</h3>
    <p class="muted small">
      Markets from the same API listing that have already settled, with the official <code>result</code>
      value (YES or NO) and the settlement amount.
    </p>
    <div class="tablewrap">
      <table>
        <thead><tr><th>Ticker</th><th>Title</th><th>Result</th><th class="num">Settlement $</th>
        <th>Settled at (UTC)</th><th>Close (UTC)</th><th>Source</th></tr></thead>
        <tbody>
{settled_rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <h3>Series behind this topic</h3>
    <p class="muted small">
      The official Kalshi series records, including their category, tags and the settlement sources Kalshi
      publishes for them.
    </p>
    <div class="tablewrap">
      <table>
        <thead><tr><th>Series ticker</th><th>Title</th><th>Category</th><th>Tags</th><th>Settlement sources</th><th></th></tr></thead>
        <tbody>
{series_rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <p class="muted small">
      Snapshot collected <b>{collected}</b> by <a href="https://github.com/karagemop466-tech/Demo2/blob/main/tools/collect_kalshi.py">tools/collect_kalshi.py</a>
      and refreshed automatically by the scheduled collector. API base
      <code>{api_base}</code>.
      See <a href="../pages/verification.html">Verification</a> and <a href="../pages/flagged.html">Flagged for Review</a>.
    </p>
  </div>
</div>

{footer}
</body>
</html>
"""


# ---------------------------------------------------------------- fixtures
def fixtures_block(open_data, settled_data, series_data, orderbooks, meta):
    """Key figures shown on the executive summary, computed from the snapshot."""
    rows = open_data.get("rows", [])
    srows = settled_data.get("rows", [])
    serrows = series_data.get("rows", [])
    total_vol = 0.0
    for r in rows:
        try:
            total_vol += float(r.get("volume_fp") or 0)
        except (TypeError, ValueError):
            pass
    per_topic = {}
    for r in rows:
        t = r.get("topic") or "other"
        per_topic[t] = per_topic.get(t, 0) + 1
    per_topic_settled = {}
    for r in srows:
        t = r.get("topic") or "other"
        per_topic_settled[t] = per_topic_settled.get(t, 0) + 1
    yes = len([r for r in srows if (r.get("result") or "").lower() == "yes"])
    no = len([r for r in srows if (r.get("result") or "").lower() == "no"])

    def n(v):
        return "{:,}".format(v)

    items = [
        ("In-scope open markets", n(len(rows)),
         "matched to gas, elections, culture, crypto or golf"),
        ("In-scope settled markets", n(len(srows)),
         "%d resolved YES · %d resolved NO" % (yes, no)),
        ("Distinct in-scope series", n(len(serrows)),
         "with category, tags and settlement sources"),
        ("Contracts traded (lifetime volume, in scope)", n(int(total_vol)),
         "sum of volume_fp — a contract count, not dollars"),
        ("Orderbook snapshots captured", n(len(orderbooks)),
         "one per highest-turnover market"),
        ("Snapshot collected", html.escape(str(open_data.get("collected_at") or meta.get("collected_at") or "not recorded")),
         "refreshed automatically by the scheduled collector"),
    ]
    out = ['<div class="tablewrap"><table>',
           '<thead><tr><th style="width:40%">Figure</th><th class="num" style="width:20%">Value</th><th>Note</th></tr></thead><tbody>']
    for label, value, note in items:
        out.append('<tr><td>%s</td><td class="num">%s</td><td class="muted small">%s</td></tr>'
                   % (html.escape(label), value, note))
    out.append("</tbody></table></div>")
    if per_topic:
        out.append('<p class="muted small">In-scope open markets by topic: %s. Resolved by topic: %s.</p>'
                   % (html.escape(", ".join("%s %d" % (k, v) for k, v in sorted(per_topic.items()))),
                      html.escape(", ".join("%s %d" % (k, v) for k, v in sorted(per_topic_settled.items())))))
    return "\n".join(out)


# ---------------------------------------------------------------- verification page
VERIFICATION = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Verification — line by line · Kalshi Demo Dashboard</title>
<meta name="description" content="Every request the collector made, the values it stored, and the checks that were run.">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<header class="top">
  <div class="inner">
    <a class="brand" href="../index.html"><span>KALSHI</span> DEMO<small>RESEARCH DASHBOARD</small></a>
    {nav}
    <span class="tag">DEMO · NO REAL FUNDS</span>
  </div>
</header>

<div class="wrap">
  <p class="eyebrow">Audit trail</p>
  <h1>Verification — line by line</h1>
  <p class="lede">
    What was checked, against which official source, and what the result was. Every request the collector made is
    listed with its exact URL so it can be opened and compared with the row it produced.
  </p>

  <h2 id="method">1 · What was verified, and how</h2>
  <div class="card">
    <div class="tablewrap"><table>
      <thead><tr><th style="width:28%">Claim</th><th style="width:34%">Method</th><th style="width:22%">Source</th><th>Result</th></tr></thead>
      <tbody>
        <tr><td>The demo REST and WebSocket roots</td><td>Read the demo environment page</td><td><a href="https://docs.kalshi.com/getting_started/demo_env" target="_blank" rel="noopener">demo environment</a></td><td><span class="pill yes">Confirmed</span></td></tr>
        <tr><td>Market, event and series field names</td><td>Read the raw JSON responses of the demo API and copied the field names from them</td><td><a href="https://external-api.demo.kalshi.co/trade-api/v2/markets?status=open&limit=1000" target="_blank" rel="noopener">/markets</a> · <a href="https://external-api.demo.kalshi.co/trade-api/v2/events?status=open&limit=200" target="_blank" rel="noopener">/events</a> · <a href="https://external-api.demo.kalshi.co/trade-api/v2/series" target="_blank" rel="noopener">/series</a></td><td><span class="pill yes">Confirmed</span></td></tr>
        <tr><td>The five topic mappings</td><td>Fetched the published taxonomy and matched each series' <code>category</code> and <code>tags</code> against it</td><td><a href="https://external-api.demo.kalshi.co/trade-api/v2/search/tags_by_categories" target="_blank" rel="noopener">taxonomy</a></td><td><span class="pill yes">Confirmed</span></td></tr>
        <tr><td>Settled markets carry a YES/NO result</td><td>Queried <code>status=settled</code> and read <code>result</code>, <code>settlement_value_dollars</code> and <code>settlement_ts</code> from the responses</td><td><a href="https://external-api.demo.kalshi.co/trade-api/v2/markets?status=settled&limit=1000" target="_blank" rel="noopener">/markets?status=settled</a></td><td><span class="pill yes">Confirmed</span></td></tr>
        <tr><td>Orderbook shape and the implied ask</td><td>Read <code>orderbook_fp.yes_dollars</code> / <code>no_dollars</code> and applied the published reciprocal rule</td><td><a href="https://docs.kalshi.com/getting_started/orderbook_responses" target="_blank" rel="noopener">orderbook responses</a></td><td><span class="pill yes">Confirmed</span></td></tr>
        <tr><td>The request-signing format</td><td>Generated throw-away Ed25519 and RSA keys, signed with the implementation, and verified the signature against the matching public key</td><td><a href="https://docs.kalshi.com/getting_started/api_keys" target="_blank" rel="noopener">API keys</a> · <code>tools/test_signing.py</code></td><td><span class="pill yes">Confirmed offline</span></td></tr>
        <tr><td>That volume is in contracts, not dollars</td><td>Read the field descriptions in the market schema</td><td><a href="https://docs.kalshi.com/api-reference/market/get-markets" target="_blank" rel="noopener">Get Markets</a></td><td><span class="pill yes">Confirmed</span></td></tr>
        <tr><td>That the demo environment is mock</td><td>Read the demo environment page and observed synthetic contracts in the responses</td><td><a href="https://docs.kalshi.com/getting_started/demo_env" target="_blank" rel="noopener">demo environment</a></td><td><span class="pill yes">Confirmed</span></td></tr>
        <tr><td>Portfolio and trade performance</td><td>Requires a demo API key; no account existed in the build environment</td><td><a href="https://docs.kalshi.com/getting_started/api_keys" target="_blank" rel="noopener">API keys</a></td><td><span class="pill flag">Unverified — no account</span></td></tr>
        <tr><td>Browser CORS access to the demo API</td><td>Not testable without a browser; the published page reports its own mode in the status line</td><td><a href="https://docs.kalshi.com/getting_started/quick_start_market_data" target="_blank" rel="noopener">market data quick start</a></td><td><span class="pill flag">Unverified</span></td></tr>
      </tbody>
    </table></div>
  </div>

  <h2 id="requests">2 · Every request the collector made</h2>
  <div class="card">
    <p class="muted small">Opened directly from this table; the response is the source of the rows below it.</p>
    <div class="tablewrap"><table>
      <thead><tr><th>#</th><th>Request</th><th class="num">HTTP</th><th class="num">Bytes</th><th>Requested at (UTC)</th></tr></thead>
      <tbody>
{request_rows}
      </tbody>
    </table></div>
  </div>

  <h2 id="rows">3 · Spot checks — stored value against the response it came from</h2>
  <div class="card">
    <p class="muted small">
      A representative row from each topic, with every field exactly as the API returned it and a link to that
      response. The full set is in <code>data/markets_open.json</code> and on the category pages.
    </p>
    <div class="tablewrap"><table>
      <thead><tr><th>Ticker</th><th>Title</th><th>Topic</th><th class="num">Last $</th><th class="num">Volume (contracts)</th><th class="num">Close (UTC)</th><th>Source</th></tr></thead>
      <tbody>
{spot_rows}
      </tbody>
    </table></div>
  </div>

  <h2 id="checks">4 · Checks run before publication</h2>
  <div class="card">
    <div class="tablewrap"><table>
      <thead><tr><th style="width:34%">Check</th><th style="width:34%">Command</th><th>What it proves</th></tr></thead>
      <tbody>
        <tr><td>Internal links and anchors</td><td class="mono">python3 tools/check_links.py</td><td>No broken link, no missing anchor, and every data row cites an official API response</td></tr>
        <tr><td>Signing implementation</td><td class="mono">python3 tools/test_signing.py</td><td>The signature format still matches the published Kalshi specification</td></tr>
        <tr><td>Script syntax</td><td class="mono">node --check assets/app.js</td><td>Every browser script parses</td></tr>
        <tr><td>Generated pages match the data</td><td class="mono">python3 tools/build_site.py</td><td>The category and verification pages are regenerated from <code>data/</code>, never edited by hand</td></tr>
      </tbody>
    </table></div>
  </div>

  <h2 id="limits">5 · Limits of this verification</h2>
  <div class="card">
    <ul class="tight">
      <li>The values were verified against the <b>demo</b> environment only. Nothing here says anything about production markets.</li>
      <li>The collector reads the public endpoints without credentials, so it cannot see anything an account holder can see: balance, positions, fills, settlements or order state.</li>
      <li>Listings are read at a point in time. Kalshi states that responses are cached briefly, so a value can lag the exchange by several seconds.</li>
      <li>Markets that settled before the historical cutoff are only available through the separate historical endpoint, so the resolution table covers the recent window only. <a href="flagged.html#f17">Flag F17</a></li>
      <li>Every remaining uncertainty is listed on the <a href="flagged.html">Flagged for Review</a> page.</li>
    </ul>
  </div>
</div>

<footer class="site">
  <div class="inner">
    <span>Kalshi Demo Dashboard · demo environment only · no real funds · research, not advice</span>
    <a href="https://docs.kalshi.com/getting_started/demo_env" target="_blank" rel="noopener">Demo environment docs</a>
    <a href="sources.html">All sources</a>
    <a href="../COORDINATION.md">Coordination log</a>
  </div>
</footer>
</body>
</html>
"""


def build_verification(nav, open_data, log, meta):
    req_rows = []
    for i, r in enumerate(log.get("requests", []), 1):
        url = r.get("url") or ""
        status = r.get("status")
        status_html = str(status) if status is not None else '<span class="blank">—</span>'
        req_rows.append(
            "<tr><td>%d</td><td class=\"mono small\"><a href=\"%s\" target=\"_blank\" rel=\"noopener\">%s</a></td>"
            "<td class=\"num\">%s</td><td class=\"num\">%s</td><td class=\"nowrap small\">%s</td></tr>" % (
                i, html.escape(url), html.escape(url[:120]),
                status_html, html.escape(str(r.get("bytes") or "")),
                html.escape(str(r.get("requested_at") or ""))))
    if not req_rows:
        req_rows.append('<tr><td colspan="5" class="muted">No request log was found.</td></tr>')

    seen, spots = set(), []
    for r in open_data.get("rows", []):
        t = r.get("topic")
        if t in seen:
            continue
        seen.add(t)
        spots.append(
            "<tr><td class=\"mono nowrap\"><a href=\"%s\" target=\"_blank\" rel=\"noopener\">%s</a></td>"
            "<td>%s</td><td>%s</td><td class=\"num\">%s</td><td class=\"num\">%s</td>"
            "<td class=\"nowrap small\">%s</td><td>%s</td></tr>" % (
                html.escape(r.get("source_url") or ""), html.escape(r.get("ticker") or ""),
                e(r.get("title")), e(r.get("topic_label")),
                money(r.get("last_price_dollars")), e(r.get("volume_fp")),
                e(r.get("close_time")), source_link(r.get("source_url"), "API")))
    if not spots:
        spots.append('<tr><td colspan="7" class="muted">No rows in the snapshot.</td></tr>')

    return VERIFICATION.format(nav=nav_for_subdir(nav), request_rows="\n".join(req_rows),
                               spot_rows="\n".join(spots))


def main():
    meta = load("meta.json") or {}
    open_data = load("markets_open.json") or {"rows": []}
    settled_data = load("markets_settled.json") or {"rows": []}
    series_data = load("series_scope.json") or {"rows": []}
    orderbooks = (load("orderbooks.json") or {}).get("rows", {})

    nav = nav_html()
    subnav = nav_for_subdir(nav)
    os.makedirs(PAGES, exist_ok=True)
    written = []
    for topic_id, filename, title, blurb, scope in TOPICS:
        mrows = [r for r in open_data.get("rows", []) if r.get("topic") == topic_id]
        srows = [r for r in settled_data.get("rows", []) if r.get("topic") == topic_id]
        serrows = [r for r in series_data.get("rows", []) if r.get("topic") == topic_id]
        page = PAGE.format(
            title=title, blurb=blurb, scope=scope, nav=subnav,
            footer=FOOTER.format(sources="sources.html", coord="../COORDINATION.md"),
            market_rows=market_rows(mrows), settled_rows=settled_rows(srows),
            series_rows=series_rows(serrows), depth_rows=depth_rows(orderbooks, topic_id),
            collected=html.escape(str(open_data.get("collected_at") or meta.get("collected_at") or "not recorded")),
            api_base=html.escape(str(meta.get("api_base") or "https://external-api.demo.kalshi.co/trade-api/v2")),
        )
        path = os.path.join(PAGES, filename)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(page)
        written.append((filename, len(mrows), len(srows), len(serrows)))
    for filename, m, s, se in written:
        print("wrote pages/%-16s open=%-5d settled=%-5d series=%d" % (filename, m, s, se))

    # verification page, generated from the request log and the snapshot
    log = load("collection_log.json") or {"requests": []}
    vpath = os.path.join(PAGES, "verification.html")
    with open(vpath, "w", encoding="utf-8") as fh:
        fh.write(build_verification(nav, open_data, log, meta))
    print("wrote pages/verification.html")

    # key figures on the executive summary
    exec_path = os.path.join(PAGES, "executive-summary.html")
    if os.path.exists(exec_path):
        with open(exec_path, encoding="utf-8") as fh:
            doc = fh.read()
        block = fixtures_block(open_data, settled_data, series_data, orderbooks, meta)
        block = ("<!-- DATA:FIXTURES:START -->\n" + block + "\n<!-- DATA:FIXTURES:END -->")
        import re as _re
        if _re.search(r"<!-- DATA:FIXTURES:START -->.*?<!-- DATA:FIXTURES:END -->", doc, _re.S):
            doc = _re.sub(r"<!-- DATA:FIXTURES:START -->.*?<!-- DATA:FIXTURES:END -->",
                          block, doc, flags=_re.S)
        else:
            doc = doc.replace("<!-- DATA:FIXTURES -->", block)
        with open(exec_path, "w", encoding="utf-8") as fh:
            fh.write(doc)
        print("filled pages/executive-summary.html fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
