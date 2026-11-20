#!/usr/bin/env python3
"""Build the static verified-data subsite in verified/ from data/kalshi_snapshot.json.

Run from the repository root:  python3 tools/build_site.py
Only values present in data/kalshi_snapshot.json are rendered. Blank fields stay blank.
"""
import html
import json
import os
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data", "kalshi_snapshot.json")
OUT = os.path.join(ROOT, "verified")
ASSETS = os.path.join(OUT, "assets")
API = "https://external-api.demo.kalshi.co/trade-api/v2"
REPO = "https://github.com/karagemop466-tech/Demo2"

with open(DATA, encoding="utf-8") as fh:
    D = json.load(fh)
MS_PATH = os.path.join(ROOT, "data", "api_market_samples.json")
with open(MS_PATH, encoding="utf-8") as fh:
    MS = json.load(fh)

E = html.escape
BUILT = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

NAV = [
    ("index.html", "Home"),
    ("gas-prices.html", "Gas Prices"),
    ("elections.html", "Elections"),
    ("culture.html", "Culture"),
    ("crypto.html", "Crypto"),
    ("golf.html", "Golf"),
    ("live-dashboard.html", "Live Dashboard"),
    ("portfolio.html", "Portfolio &amp; Trades"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("markets.html", "Market Samples"),
    ("resolutions.html", "Resolutions"),
    ("flagged-for-review.html", "Flagged for Review"),
    ("repo-review.html", "Repo Review"),
    ("../index.html", "Main dashboard ↗"),
]


def link(url, label=None):
    if not url:
        return ""
    return f'<a href="{E(url, quote=True)}" target="_blank" rel="noopener">{E(label or url)}</a>'


def page(filename, title, body, active=None, extra_head="", extra_script=""):
    parts = []
    for href, label in NAV:
        cls = ' class="active"' if href == active else ""
        parts.append(f'<a href="{href}"{cls}>{label}</a>')
    nav = "".join(parts)
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} · Kalshi Demo Dashboard</title>
<link rel="stylesheet" href="assets/style.css">
{extra_head}
</head>
<body>
<header class="top">
  <div class="brand"><a href="index.html">Kalshi Demo Dashboard</a><span class="tag">DEMO DATA · read-only</span></div>
  <nav>{nav}</nav>
</header>
<main>
{body}
</main>
<footer>
  <p>Data source: Kalshi <strong>demo</strong> Trade API, <a href="{API}/series" target="_blank" rel="noopener">{E(API)}</a>.
  Kalshi says demo prices and behavior may not reflect real markets. Not financial advice.
  Repository: <a href="{REPO}" target="_blank" rel="noopener">{REPO}</a>.</p>
  <p>Site built {BUILT} from data/kalshi_snapshot.json (collected 2026-11-20).</p>
</footer>
{extra_script}
</body>
</html>
"""
    with open(os.path.join(OUT, filename), "w", encoding="utf-8") as fh:
        fh.write(doc)


def flag_links(ids):
    return " ".join(
        f'<a class="flagchip" href="flagged-for-review.html#{E(i)}">{E(i)}</a>' for i in ids
    )


def source_cell(row):
    out = link(row["source_api"], "List API response")
    if row.get("detail_endpoint"):
        out += "<br>" + link(row["detail_endpoint"], "Detail API response")
    return out


def sources_cell(row):
    items = [link(s["url"], s["name"]) if s.get("url") else E(s["name"]) + ' <span class="flag">(link not verified, F-14)</span>' for s in row["settlement_sources"]]
    return "<br>".join(items)


def category_page(cat):
    rows = [r for r in D["rows"] if r["category"] == cat["id"]]
    flags = {f["id"]: f for f in D["flags"]}
    tr = []
    for r in rows:
        tr.append(f"""<tr>
<td><code>{E(r['ticker'])}</code></td>
<td>{E(r['title'])}{('<br><small>' + E(r['sub_title']) + '</small>') if r.get('sub_title') else ''}</td>
<td>{E(r['type'])}</td>
<td>{E(r['kalshi_category'])}{('<br><small>' + E(r['tags']) + '</small>') if r.get('tags') else ''}</td>
<td>{E(r['frequency'])}</td>
<td>{E(r['last_updated'])}</td>
<td>{sources_cell(r)}</td>
<td>{link(r['contract_terms'], 'Contract terms')}</td>
<td>{source_cell(r)}</td>
<td><span class="ok">Verified: detail API</span>{('<br>' + flag_links(r['flags'])) if r['flags'] else ''}</td>
</tr>""")
    table = "\n".join(tr) if tr else '<tr><td colspan="10">No rows collected yet.</td></tr>'
    notes = ""
    if cat["id"] == "gas-prices":
        notes = "<p class=\"note\">Only two daily AAA gas-price series appeared on the first page of the Economics results. Current prices are not in this table. See flag F-06.</p>"
    if cat["id"] == "golf":
        notes = "<p class=\"note\">Golf is a tag under Sports. Only the first page of the Golf tag query was read. See flags F-11 and F-12.</p>"
    if cat["id"] == "culture":
        notes = "<p class=\"note\">The demo API returned two Culture series in total. Kalshi's tag list has no 'Culture' key. See flag F-11.</p>"
    if cat["id"] == "elections":
        notes = "<p class=\"note\">First page of results only. The NATO and Pope rows are events, not series, and the NATO row is dated to 2099 in demo data (F-01).</p>"
    if cat["id"] == "crypto":
        notes = "<p class=\"note\">First page of results only (9 series). See flags F-04, F-08, and F-09 before using these rows.</p>"
    body = f"""
<section class="hero small">
  <h1>{E(cat['title'])}</h1>
  <p>{E(cat['blurb'])}</p>
  <p class="meta">Rows: <strong>{len(rows)}</strong> · Every row links to the Kalshi API response it came from, and to the contract terms.
  Blank cells are values the source did not provide. They are never inferred.</p>
  {notes}
</section>
<section>
<div class="tablewrap">
<table>
<thead><tr>
<th>Ticker</th><th>Title</th><th>Type</th><th>Kalshi category / tags</th><th>Frequency</th>
<th>Last updated (API)</th><th>Settlement sources</th><th>Contract terms</th><th>Source</th><th>Status</th>
</tr></thead>
<tbody>
{table}
</tbody>
</table>
</div>
</section>
"""
    page(f"{cat['id']}.html", cat["title"], body, active=f"{cat['id']}.html")


def index_page():
    counts = {c["id"]: sum(1 for r in D["rows"] if r["category"] == c["id"]) for c in D["categories"]}
    cards = "".join(
        f'<a class="card" href="{c["id"]}.html"><h3>{E(c["title"])}</h3><p>{E(c["blurb"])}</p>'
        f'<span class="pill">{counts[c["id"]]} rows</span></a>'
        for c in D["categories"]
    )
    body = f"""
<section class="hero">
  <h1>Kalshi Demo Dashboard</h1>
  <p class="lead">A read-only dashboard built from the Kalshi <strong>demo</strong> API. It collects contracts for five topics (gas prices, elections, culture, crypto, golf), records their sources, and lists what is still missing before any trading decision.</p>
  <div class="banner warn">Demo environment only. Kalshi says demo prices "may not be reflective of those in real markets." Nothing here is a trading recommendation.</div>
</section>

<section>
<h2>Executive summary</h2>
<ul class="summary">
  <li><strong>What works:</strong> Public, unauthenticated market-data reads from the demo Trade API return verified data. Every row on the category pages links to the API response it came from.</li>
  <li><strong>What is in the data:</strong> {sum(counts.values())} rows: 2 AAA gas-price series, 6 elections rows (4 series, 2 events), 2 culture series, 9 crypto series, 5 golf series. Each category is the first page of results only, not a full list. Market Samples and Resolutions add open and settled markets from the same API (samples, first page only).</li>
  <li><strong>Biggest limits:</strong> demo data includes 2099 close dates and placeholder-looking settlement sources (see <a href="flagged-for-review.html">Flagged for Review</a>). Volume fields are contract counts, not dollars, so the "highest dollar amount" ranking cannot be read directly.</li>
  <li><strong>Blocked without your action:</strong> Portfolio tracking, trade execution, and per-trade performance need a Kalshi demo account and API key. Creating those requires logging in to Kalshi, so they are not done. See the <a href="portfolio.html">Portfolio &amp; Trades</a> page.</li>
  <li><strong>Next decisions:</strong> review the <a href="suggestions.html">Suggestions</a> and answer the open <a href="questions.html">Questions</a>. No implementation changes are made until you choose.</li>
</ul>
</section>

<section>
<h2>Category pages</h2>
<div class="cards">{cards}</div>
</section>

<section>
<h2>Tools</h2>
<div class="cards">
  <a class="card" href="live-dashboard.html"><h3>Live Dashboard</h3><p>Price chart (x = time, y = contract price) and orderbook depth for a demo market. Polls the public API from your browser.</p></a>
  <a class="card" href="portfolio.html"><h3>Portfolio &amp; Trades</h3><p>Status of the demo account, trade log layout, and the strategy categories proposed for analysis.</p></a>
  <a class="card" href="questions.html"><h3>Questions</h3><p>What is answered, what is not, and how each missing item could be found.</p></a>
  <a class="card" href="suggestions.html"><h3>Suggestions</h3><p>Options to improve the site and decisions. Each one waits for your choice.</p></a>
  <a class="card" href="markets.html"><h3>Market Samples</h3><p>Open demo markets from the API with last price, bid, ask, volume, and open interest. Sample only, not a full list.</p></a>
  <a class="card" href="resolutions.html"><h3>Resolutions</h3><p>Settled demo markets with the result (YES or NO), the settlement value, and the rule that decided it.</p></a>
  <a class="card" href="flagged-for-review.html"><h3>Flagged for Review</h3><p>Irregularities and unverified items, with the source links for manual review.</p></a>
  <a class="card" href="repo-review.html"><h3>Repo Review</h3><p>What the repository contains, checked against GitHub.</p></a>
</div>
</section>
"""
    page("index.html", "Home", body, active="index.html")


def live_page():
    body = f"""
<section class="hero small">
  <h1>Live Dashboard</h1>
  <p>Reads a demo market from <code>{E(API)}</code> every few seconds. X axis is time (seconds to hours); Y axis is the contract price in dollars (0.00 to 1.00).
  The chart fills in as the page runs, so it starts empty. Only data from this browser session is shown.</p>
  <div class="banner warn">Demo prices. Browser access to the API is not verified (CORS). If the status line says "could not reach", the chart cannot update from this browser.</div>
</section>

<section class="controls">
  <label>Market ticker
    <select id="tickerSel">
      <option value="KXBTCY-27JAN0100-B97500">KXBTCY-27JAN0100-B97500 (BTC on Jan 1 2027: 95,000 to 99,999.99)</option>
      <option value="KXBTCY-27JAN0100-T20000.00">KXBTCY-27JAN0100-T20000.00 (BTC on Jan 1 2027: 19,999.99 or below)</option>
      <option value="KXBTCY-27JAN0100-T149999.99">KXBTCY-27JAN0100-T149999.99 (BTC on Jan 1 2027: 150,000 or above)</option>
      <option value="KXNEWPOPE-70-LANT">KXNEWPOPE-70-LANT (Next Pope: Luis Antonio Tagle)</option>
      <option value="KXNEWPOPE-70-PPIZ">KXNEWPOPE-70-PPIZ (Next Pope: Pierbattista Pizzaballa)</option>
      <option value="KXHFCCHAIR-26DEC01-KSEL">KXHFCCHAIR-26DEC01-KSEL (HFC Chair: Keith Self)</option>
    </select>
  </label>
  <label>Or type any ticker
    <input id="tickerTxt" placeholder="e.g. KXBTCY-27JAN0100-T20000.00">
  </label>
  <label>Chart length
    <select id="windowSel">
      <option value="60">Last 60 seconds</option>
      <option value="300" selected>Last 5 minutes</option>
      <option value="3600">Last 1 hour</option>
      <option value="21600">Last 6 hours</option>
    </select>
  </label>
  <label>Poll every
    <select id="pollSel">
      <option value="2000">2 seconds</option>
      <option value="5000" selected>5 seconds</option>
      <option value="15000">15 seconds</option>
    </select>
  </label>
  <button id="startBtn">Start</button>
  <button id="stopBtn" class="secondary">Stop</button>
</section>

<section class="kpis">
  <div class="kpi"><span>Last price</span><strong id="kLast">–</strong></div>
  <div class="kpi"><span>Yes bid</span><strong id="kBid">–</strong></div>
  <div class="kpi"><span>Yes ask</span><strong id="kAsk">–</strong></div>
  <div class="kpi"><span>Volume (contracts)</span><strong id="kVol">–</strong></div>
  <div class="kpi"><span>Open interest (contracts)</span><strong id="kOi">–</strong></div>
  <div class="kpi"><span>Status</span><strong id="kStatus">–</strong></div>
</section>

<section>
<div class="chartbox"><canvas id="chart" width="1000" height="360"></canvas></div>
<p class="note" id="statusLine">Not started.</p>
</section>

<section class="twocol">
<div>
  <h2>Yes bids (contracts available to sell YES into)</h2>
  <div class="tablewrap"><table><thead><tr><th>Price ($)</th><th>Contracts</th><th>Cumulative</th></tr></thead><tbody id="bidsBody"><tr><td colspan="3">No data yet.</td></tr></tbody></table></div>
</div>
<div>
  <h2>Yes asks (from No bids: ask = 1 − no bid price)</h2>
  <div class="tablewrap"><table><thead><tr><th>Price ($)</th><th>Contracts</th><th>Cumulative</th></tr></thead><tbody id="asksBody"><tr><td colspan="3">No data yet.</td></tr></tbody></table></div>
</div>
</section>

<section>
<p class="note">Sources: market fields <code>yes_bid_dollars</code>, <code>yes_ask_dollars</code>, <code>last_price_dollars</code>, <code>volume_fp</code>, <code>open_interest_fp</code> from
<a href="https://docs.kalshi.com/api-reference/market/get-market.md" target="_blank" rel="noopener">Get Market</a>;
orderbook from <a href="https://docs.kalshi.com/api-reference/market/get-market-orderbook.md" target="_blank" rel="noopener">Get Market Orderbook</a> (returns yes bids and no bids only; each level is [price, contract count]).
</p>
</section>
"""
    script = '<script src="assets/live.js"></script>'
    page("live-dashboard.html", "Live Dashboard", body, active="live-dashboard.html", extra_script=script)


def portfolio_page():
    body = """
<section class="hero small">
  <h1>Portfolio &amp; Trades</h1>
  <div class="banner bad"><strong>Status: blocked, needs your action.</strong> Reading your demo portfolio, placing trades, and tracking trade performance require a Kalshi demo account and an API key. This session cannot create either one without logging in to Kalshi.</div>
</section>

<section>
<h2>What is needed (one-time setup)</h2>
<ol>
  <li>Create a Kalshi demo account. Kalshi's guide: <a href="https://help.kalshi.com/en/articles/13823775-creating-and-using-a-demo-account" target="_blank" rel="noopener">help.kalshi.com, creating and using a demo account</a>. Demo site: <a href="https://demo.kalshi.co/" target="_blank" rel="noopener">demo.kalshi.co</a>.</li>
  <li>Generate an API key for that demo account. Kalshi's docs: <a href="https://docs.kalshi.com/getting_started/api_keys" target="_blank" rel="noopener">API Keys</a>. The docs say the key process is the same for demo and production, and demo credentials are separate from production.</li>
  <li>Add the key to a secret store (not to this repository). The repository must never contain credentials.</li>
</ol>
<p class="note">Authenticated endpoints and their signing rules are in the <a href="https://docs.kalshi.com/getting_started/quick_start_authenticated_requests" target="_blank" rel="noopener">Quick Start: Authenticated Requests</a> guide. Trading endpoints are described in <a href="https://docs.kalshi.com/getting_started/quick_start_create_order" target="_blank" rel="noopener">Quick Start: Create your first order</a>. These were not read in full during this session.</p>
</section>

<section>
<h2>Trade log (empty; no trades have been placed)</h2>
<p>Each row will record one order and its result. Fields come from the API response when trading is enabled. No values are filled in here.</p>
<div class="tablewrap"><table>
<thead><tr><th>Order ID</th><th>Placed (UTC)</th><th>Ticker</th><th>Category</th><th>Side</th><th>Contracts</th><th>Price ($)</th><th>Fee ($)</th><th>Result (yes/no)</th><th>P&amp;L ($)</th><th>Source link</th><th>Strategy tag</th></tr></thead>
<tbody><tr><td colspan="12">No trades recorded yet.</td></tr></tbody>
</table></div>
</section>

<section>
<h2>Strategy categories proposed for analysis (not yet tested)</h2>
<p>These are candidate groupings for classifying trades once data exists. They are a plan, not a result. Each one needs a pre-set hypothesis before testing.</p>
<ul>
  <li><strong>By topic:</strong> gas prices, elections, culture, crypto, golf (matches the category pages).</li>
  <li><strong>By entry price band:</strong> low (under $0.20), middle ($0.20 to $0.80), high (over $0.80). Band edges are a proposal.</li>
  <li><strong>By time to close:</strong> under 1 day, 1 to 7 days, over 7 days.</li>
  <li><strong>By liquidity at entry:</strong> contracts available at the entry price, from the orderbook.</li>
  <li><strong>By settlement-source quality:</strong> single official source vs. multiple or unclear sources (see flags F-03, F-05, F-09).</li>
</ul>
</section>
"""
    page("portfolio.html", "Portfolio & Trades", body, active="portfolio.html")


def questions_page():
    answered = [
        ("What is the base URL for the demo REST API?", f"{API}", "Kalshi demo env doc recommends this root.", "https://docs.kalshi.com/getting_started/demo_env.md"),
        ("Is market data available without authentication?", "Yes. The GET market endpoints returned data with no credentials.", "Kalshi's quick-start list describes market data 'without authentication'; observed responses confirm it.", "https://docs.kalshi.com/llms.txt"),
        ("Are demo prices real-market prices?", "Not guaranteed. Kalshi says demo prices may not reflect real markets.", "Demo env doc warning.", "https://docs.kalshi.com/getting_started/demo_env.md"),
        ("Is volume_fp in dollars?", "No. '_fp' fields are contract quantities; '_dollars' fields are prices.", "Fixed-point doc. Market responses show volume_fp as contract counts.", "https://docs.kalshi.com/getting_started/fixed_point_migration.md"),
        ("How does the orderbook show asks?", "It returns yes bids and no bids only. A yes bid at X is the same as a no ask at 1 − X.", "Get Market Orderbook doc.", "https://docs.kalshi.com/api-reference/market/get-market-orderbook.md"),
        ("How are resolved markets settled?", "Yes outcome: YES holders receive $1 per contract. No outcome: NO holders receive $1 per contract. Settled sample results are on the Resolutions page.", "Market Settlement doc. Sample only, see F-18.", "https://docs.kalshi.com/getting_started/market_settlement.md"),
        ("How is dollar volume computed from the API?", "Not directly. Each trade has count_fp and yes_price_dollars, so dollar volume = sum of price × contracts over trades. The market objects give contract counts only.", "Get Trades doc lists these trade fields. Computation not yet run (Q-07).", "https://docs.kalshi.com/api-reference/market/get-trades.md"),
        ("Is there historical price data for charts?", "Yes. Get Market Candlesticks returns 1-minute, 1-hour, or 1-day candles (open, high, low, close, volume, open interest), up to 5,000 periods per request. The site does not use it yet (Suggestion S-11).", "Get Market Candlesticks doc.", "https://docs.kalshi.com/api-reference/market/get-market-candlesticks.md"),
        ("What does the fee rounding rule do?", "A trade fee is rounded up to $0.000001; a rounding fee brings the balance to the user's precision; a rebate returns accumulated overpayment. The per-contract fee schedule was not read (Q-10).", "Fee Rounding doc.", "https://docs.kalshi.com/getting_started/fee_rounding.md"),
        ("What is the 'Culture' and 'Golf' category naming?", "The series endpoint uses 'Culture' as a category and 'Golf' as a tag under 'Sports'. Labels on the site follow what the API returns.", "Series detail responses for KXXBANNEDGROK and KXLIVH2H (see F-11).", "https://docs.kalshi.com/api-reference/market/get-series.md"),
    ]
    unknown = [
        ("Q-06", "Which open markets exist in each of the five topics, and how many?", "Partly answered: the Market Samples page lists the first 3 to 5 open markets per query. Full counts need cursor paging on /markets and /series until the cursor is empty (Get Markets doc).", "Get Markets doc", "https://docs.kalshi.com/api-reference/market/get-markets.md"),
        ("Q-07", "Which markets have the most dollar volume?", "Compute per market: sum of count_fp × yes_price_dollars over trades, paging with the cursor. Not run. Volume fields alone do not give dollars (F-02).", "Get Trades doc", "https://docs.kalshi.com/api-reference/market/get-trades.md"),
        ("Q-08", "What are current prices for the AAA gas-price series?", "Open daily markets exist for KXAAAGASCDOK (Market Samples: zero volume, zero bid/ask). KXAAAGASDTN was not re-queried for open markets in this session (F-06).", "Get Markets doc", "https://docs.kalshi.com/api-reference/market/get-markets.md"),
        ("Q-09", "What did each resolved event settle to (yes or no)?", "Partly answered: 10 sampled settled markets are on the Resolutions page. The full list needs paging. The daily gas YES bucket is not recorded (F-18).", "Market Settlement doc", "https://docs.kalshi.com/getting_started/market_settlement.md"),
        ("Q-10", "What are the trading fees per contract?", "Fee rounding is documented. The fee schedule (linked from the Get Series doc as a PDF) was not read. Series rows carry fee_type 'quadratic' and fee_multiplier 1.", "Get Series doc", "https://docs.kalshi.com/api-reference/market/get-series.md"),
        ("Q-11", "Does the browser (GitHub Pages) get CORS access to the demo API?", "Test from a real browser on the live site. Not verified from the sandbox.", "Live Dashboard status line", "live-dashboard.html"),
        ("Q-12", "Which data is production vs. demo, and which should drive the analysis?", "Decision needed. See Suggestion S-01.", "Demo env doc", "https://docs.kalshi.com/getting_started/demo_env.md"),
        ("Q-13", "How much demo funding is available, and what position sizes are allowed?", "Visible only after the demo account exists. Needs your action. The Kalshi help article says demo accounts start with no funds.", "Kalshi demo account help", "https://help.kalshi.com/en/articles/13823775-creating-and-using-a-demo-account"),
        ("Q-14", "What risk limits and entry rules should apply to demo trades?", "Decision needed from you before any trade. See Suggestions S-05 and S-06.", "Your decision", "suggestions.html"),
        ("Q-15", "Are there markets whose settlement sources are unclear?", "Yes, see flags F-03, F-04, F-05, F-07, F-09, F-14, F-17. Each needs a contract-terms read.", "Flagged for Review", "flagged-for-review.html"),
        ("Q-16", "Why do list and detail endpoints show different last-updated times?", "The Get Series doc defines last_updated_ts as when the series metadata was last updated. The meaning of the list field was not checked. See F-13.", "Get Series doc", "https://docs.kalshi.com/api-reference/market/get-series.md"),
        ("Q-17", "How many contracts are available at each price, for each sampled market?", "Live Dashboard reads the orderbook. The static snapshot does not record depth. Needs a per-market orderbook snapshot at a fixed time.", "Get Market Orderbook doc", "https://docs.kalshi.com/api-reference/market/get-market-orderbook.md"),
        ("Q-18", "Does each shared contract-terms PDF cover its series?", "Open each PDF listed in F-17 and confirm the series name, threshold, date, and source.", "Flag F-17", "flagged-for-review.html#F-17"),
    ]
    rows_a = "".join(
        f"<tr><td>{E(q)}</td><td>{E(a)}</td><td>{E(n)}</td><td>{link(s, s if s.startswith('http') else None) if s.startswith('http') else '<a href=' + chr(34) + E(s) + chr(34) + '>' + E(s) + '</a>'}</td></tr>"
        for q, a, n, s in answered
    )
    rows_u = "".join(
        f"<tr><td>{E(i)}</td><td>{E(q)}</td><td>{E(how)}</td><td>{link(s, lbl) if s.startswith('http') else '<a href=' + chr(34) + E(s) + chr(34) + '>' + E(lbl) + '</a>'}</td></tr>"
        for i, q, how, lbl, s in unknown
    )
    body = f"""
<section class="hero small">
  <h1>Questions</h1>
  <p>What must be answered before a trading decision can reasonably be made. Part A lists what the collected data already answers. Part B lists what is still missing, and how to find it.</p>
</section>
<section>
<h2>Part A. Answered from verified sources</h2>
<div class="tablewrap"><table>
<thead><tr><th>Question</th><th>Answer</th><th>Note</th><th>Source</th></tr></thead>
<tbody>{rows_a}</tbody>
</table></div>
</section>
<section>
<h2>Part B. Still missing (with how to discover each one)</h2>
<div class="tablewrap"><table>
<thead><tr><th>ID</th><th>Question / missing information</th><th>How to discover it</th><th>Reference</th></tr></thead>
<tbody>{rows_u}</tbody>
</table></div>
</section>
"""
    page("questions.html", "Questions", body, active="questions.html")


SUGGESTIONS = [
    ("S-01", "Choose the data source for prices", "Demo prices may not reflect real markets (F-01). Decide whether analysis uses demo data only, production read-only data, or both.",
     ["Demo only: matches the trading account; prices may be unrealistic.", "Production read-only: real prices, no trading; needs a production read path.", "Both, side by side: shows the gap between demo and production prices."]),
    ("S-02", "Rank by dollar volume correctly", "Volume fields are contract counts (F-02). Compute dollar volume from trades, or use a different ranking.",
     ["Trades-based dollar volume (price × contracts) over the last 24 hours.", "Open interest × price as a proxy (labeled as a proxy).", "Rank by contract count and label it as such."]),
    ("S-03", "Refresh the data on a schedule", "The static site only changes when someone rebuilds it. A scheduled job would keep the tables current.",
     ["Manual rebuild on request only (no automation).", "Scheduled GitHub Action that writes a new snapshot (needs a workflow file and your approval).", "Client-side refresh only (live dashboard already does this for one market)."]),
    ("S-04", "Connect the demo account (needs your action)", "Portfolio, trades, and performance tracking need a demo account and API key (Q-13). Creating them requires logging in to Kalshi.",
     ["You create the demo account and key, then share them through a secret store (never in the repo).", "Read-only portfolio first, trading later.", "Skip trading; analyze public market data only."]),
    ("S-05", "Set entry rules before any trade", "Without pre-set rules, results could be fit after the fact. Define rules first (topic, price band, time to close, liquidity, max size).",
     ["Write a rule set now and test it on the snapshot history only.", "Start with very small demo sizes while data is collected.", "Defer trading until more data exists."]),
    ("S-06", "Use liquidity to gate trades", "Orderbook depth shows contracts available at each price (Live Dashboard). Gate entries on enough depth at the target price.",
     ["Minimum depth at the target price (e.g., a set number of contracts).", "Maximum allowed slippage from the best price.", "No gate: accept any depth (higher risk)."]),
    ("S-07", "Hold back markets with unclear settlement", "Some series have placeholder or mismatched settlement sources (F-03, F-05, F-07, F-09).",
     ["Exclude flagged series from trading until reviewed.", "Include them but tag results separately.", "Review each series' contract terms first (recommended)."]),
    ("S-08", "Use streaming prices for the chart", "Polling gives a sample every few seconds. The WebSocket API streams updates and gives finer time resolution.",
     ["Keep polling (simple, works in a browser, limited resolution).", "Add a WebSocket feed (more accurate; needs a small server or a browser test of CORS/WebSocket support).", "Use candlestick data for longer windows."]),
    ("S-09", "Exclude 2099 demo markets from analysis", "Demo events close in 2099 (F-01). They produce no useful short-term signal.",
     ["Exclude markets whose close time is more than one year away.", "Keep them, but label them as demo-only.", "Keep as is."]),
    ("S-11", "Historical price chart from candlesticks", "The live chart only holds what this browser has seen since the page opened. Get Market Candlesticks gives 1-minute, 1-hour, and 1-day history (Q-06 and the Get Market Candlesticks doc).",
     ["Keep the live chart only (simple; no history before the page opened).", "Backfill the chart with 1-minute candles for the last few hours, then add live points (CORS must be tested from a browser first).", "Use hourly or daily candles for longer windows (one request covers up to 5,000 periods)."]),
    ("S-12", "Show full lists, not samples", "The tables show the first page of each query (F-12, F-19). Full coverage needs cursor paging on the Get Markets and Get Series endpoints.",
     ["Page through every series in the five topics and rebuild the snapshot (more requests; cursor per the Get Markets doc).", "Keep samples and label them clearly (current state).", "Limit the scope to the markets the analysis needs (for example one topic first)."]),
    ("S-10", "Add fee-aware profit and loss", "Series carry fee_type 'quadratic' and fee_multiplier 1, but the fee formula has not been verified (Q-10).",
     ["Read the official fee doc, then compute fees per trade.", "Ignore fees for now and label P&L as before fees.", "Defer until a trade exists."]),
]


def suggestions_page():
    items = []
    for sid, title, why, options in SUGGESTIONS:
        opts = "".join(
            f'<label class="opt"><input type="radio" name="{sid}" value="{chr(65+i)}" class="pick" data-id="{sid}"> <strong>Option {chr(65+i)}.</strong> {E(o)}</label>'
            for i, o in enumerate(options)
        )
        items.append(f"""<article class="sugg" id="{sid}">
<header><span class="pill">{sid}</span> <h3>{E(title)}</h3> <span class="pill warn-pill">Awaiting your decision</span></header>
<p><strong>Why:</strong> {E(why)}</p>
<div class="opts">{opts}</div>
<p class="note">Choosing an option here does not change the site. It only records your choice in this browser. Tell the agent which option to implement.</p>
</article>""")
    body = f"""
<section class="hero small">
  <h1>Suggestions</h1>
  <p>Proposed improvements to decision-making and to this site. Each suggestion waits for your choice. No suggestion has been implemented.</p>
  <p class="meta"><button id="copyBtn" class="secondary">Copy my choices</button> <span id="copyMsg"></span></p>
</section>
<section>
{''.join(items)}
</section>
"""
    script = '<script src="assets/suggestions.js"></script>'
    page("suggestions.html", "Suggestions", body, active="suggestions.html", extra_script=script)


def flagged_page():
    cards = []
    for f in D["flags"]:
        src = "".join(f'<li>{link(s["url"], s["name"])}</li>' for s in f["sources"])
        cards.append(f"""<article class="flag sev-{E(f['severity'])}" id="{E(f['id'])}">
<header><span class="pill">{E(f['id'])}</span> <h3>{E(f['topic'])}</h3> <span class="pill">Severity: {E(f['severity'])}</span></header>
<p>{E(f['detail'])}</p>
<p><strong>Sources for manual review:</strong></p><ul>{src}</ul>
<p class="meta">Status: <strong>needs review</strong>. Does not block the site.</p>
</article>""")
    repo_flags = [
        ("R-F1", "At this session's base commit (6072808) the repository had no code, only a one-line README (\"# Demo2\"). Confirm the current main content matches the review.", "https://github.com/karagemop466-tech/Demo2"),
        ("R-F2", "At the base there was no LICENSE, no CI workflow, and no .gitignore. main now has a Pages workflow (.github/workflows/pages.yml) but still no LICENSE in the files listed at review time.", "https://github.com/karagemop466-tech/Demo2"),
        ("R-F3", "COORDINATION.md did not exist at the base. The session that built the main dashboard created it, and this session appended its entry.", "https://github.com/karagemop466-tech/Demo2/blob/main/COORDINATION.md"),
        ("R-F4", "The coordination instructions describe session-<id>/<task> branches, but the session rules here allow only the assigned branch. This session worked only on arena/6822d767-demo2. Reviewer should confirm which convention to use.", "https://github.com/karagemop466-tech/Demo2"),
        ("R-F5", "Security review: the main dashboard's README says users paste a demo API Key ID and private key into the Portfolio page and that keys are signed in-browser. A GitHub Pages site is public static hosting. Confirm this design is acceptable, or move signing out of the browser. This session did not read or store any key.", "https://github.com/karagemop466-tech/Demo2/blob/main/README.md"),
        ("R-F6", "Overlap: main's category pages (pages/gas.html and others) show no data rows; values are live-only in the browser. The verified/ subsite adds static rows with a source link per row. Integration needed to link the two sites from the main navigation (a shared file, not edited here).", "https://github.com/karagemop466-tech/Demo2/blob/main/pages/gas.html"),
        ("R-F7", "PR #3 (branch arena/407c72e2-demo2) merged into main during this session (merge commit 5224293). It adds root-level analysis, portfolio, and review pages. Not reviewed by this session.", "https://github.com/karagemop466-tech/Demo2/pull/3"),
    ]
    rf = "".join(f'<article class="flag sev-medium" id="{i}"><header><span class="pill">{i}</span> <h3>Repo irregularity</h3></header><p>{E(t)}</p><ul><li>{link(u, u)}</li></ul></article>' for i, t, u in repo_flags)
    body = f"""
<section class="hero small">
  <h1>Flagged for Review</h1>
  <p>Irregularities, unverified items, and open issues. Each one has the source links for manual review. Flagged items do not block the site or the merge. They are listed here so you can review them after the site is live and request changes.</p>
</section>
<section><h2>Data flags</h2>{''.join(cards)}</section>
<section><h2>Repository flags</h2>{rf}</section>
"""
    page("flagged-for-review.html", "Flagged for Review", body, active="flagged-for-review.html")


def repo_page():
    body = f"""
<section class="hero small">
  <h1>Repo Review</h1>
  <p>What the repository <a href="{REPO}" target="_blank" rel="noopener">karagemop466-tech/Demo2</a> contained at the start of this session, and what changed.</p>
</section>
<section>
<div class="tablewrap"><table>
<thead><tr><th>Item</th><th>Finding</th><th>Source</th></tr></thead>
<tbody>
<tr><td>README.md</td><td>At this session's base (6072808) it contained only "# Demo2". Current main README is a different file, updated by other sessions.</td><td>{link(REPO + '/blob/main/README.md', 'README.md on main')}</td></tr>
<tr><td>Default branch</td><td>main. This session's branch was based on 6072808 ("Initial commit"). main has since advanced: PR #1, PR #2, and PR #3 (from another session) are merged.</td><td>{link(REPO, 'Repository')}</td></tr>
<tr><td>GitHub Pages</td><td>Legacy build from main, root folder (confirmed via the GitHub Pages API). Live site: https://karagemop466-tech.github.io/Demo2/ . This subsite: https://karagemop466-tech.github.io/Demo2/verified/ .</td><td>{link('https://docs.github.com/en/pages', 'GitHub Pages docs')}</td></tr>
<tr><td>Kalshi API reference</td><td>Demo REST root, WebSocket root, and endpoint docs used for this build.</td><td>{link('https://docs.kalshi.com/getting_started/demo_env.md', 'Demo environment doc')}</td></tr>
<tr><td>Code and tests</td><td>At the base there was no code. This session adds tools/build_site.py (generator) and tools/check_links.py (checker) for the verified/ subsite.</td><td>{link(REPO + '/tree/main/tools', 'tools/ folder')}</td></tr>
</tbody></table></div>
</section>
<section>
<h2>Coordination</h2>
<p>Task board, claims, and log: <a href="{REPO}/blob/main/COORDINATION.md" target="_blank" rel="noopener">COORDINATION.md</a>. Irregularities about the repo are listed in <a href="flagged-for-review.html#R-F1">Flagged for Review</a>.</p>
</section>
"""
    page("repo-review.html", "Repo Review", body, active="repo-review.html")


STYLE = """
:root{--bg:#f6f8fa;--card:#fff;--ink:#1f2328;--muted:#59636e;--line:#d8dee4;--brand:#00b67a;--warn:#9a6700;--bad:#cf222e;--ok:#1a7f37}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
a{color:#0969da}
header.top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;padding:10px 20px;background:#0d1117;color:#fff}
header.top a{color:#c9d1d9;text-decoration:none;margin-right:12px;font-size:14px}
header.top a.active,header.top a:hover{color:#fff;text-decoration:underline}
.brand a{color:#fff;font-weight:700;font-size:16px;margin-right:8px}
.brand .tag{font-size:11px;background:var(--brand);color:#04110c;padding:2px 6px;border-radius:4px;margin-left:6px}
main{max-width:1200px;margin:0 auto;padding:20px}
footer{max-width:1200px;margin:0 auto;padding:16px 20px 40px;color:var(--muted);font-size:13px}
h1{font-size:26px;margin:4px 0 8px}h2{font-size:19px;margin:24px 0 10px}h3{font-size:16px;margin:0}
section{margin-bottom:12px}
.hero{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:16px}
.hero.small p{margin:6px 0}
.lead{font-size:16px}
.meta,.note{color:var(--muted);font-size:13px}
.banner{border-radius:8px;padding:10px 14px;margin:10px 0;border:1px solid}
.banner.warn,.warn-pill{background:#fff8c5;border-color:#d4a72c;color:#633c01}
.banner.bad{background:#ffebe9;border-color:#ff8182;color:#82071e}
.pill{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:999px;padding:1px 8px;background:#f6f8fa;color:var(--muted);margin-right:6px}
.warn-pill{color:#633c01}
.ok{color:var(--ok);font-weight:600;font-size:13px}
.flagchip{display:inline-block;font-size:12px;background:#ffebe9;color:#82071e;border-radius:4px;padding:0 5px;margin:2px 2px 0 0;text-decoration:none}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.card{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;text-decoration:none;color:var(--ink)}
.card:hover{border-color:var(--brand)}
.card p{color:var(--muted);font-size:13px;margin:6px 0}
ul.summary li{margin-bottom:8px}
.tablewrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#f6f8fa;position:sticky;top:0;font-weight:600}
code{font-size:12px;background:#f0f3f6;padding:1px 4px;border-radius:4px}
.sugg,.flag{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:12px}
.sugg header,.flag header{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
.opt{display:block;padding:6px 8px;border-radius:6px;margin:4px 0;cursor:pointer}
.opt:hover{background:#f6f8fa}
.opt.chosen{background:#dafbe1}
.sev-high{border-left:5px solid var(--bad)}.sev-medium{border-left:5px solid var(--warn)}.sev-low{border-left:5px solid var(--muted)}
.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.controls label{display:flex;flex-direction:column;font-size:12px;color:var(--muted);gap:4px}
select,input,button{font:inherit;padding:6px 8px;border-radius:6px;border:1px solid var(--line);background:#fff}
button{background:var(--brand);border-color:var(--brand);color:#fff;cursor:pointer;font-weight:600}
button.secondary{background:#fff;color:var(--ink);border-color:var(--line)}
.kpis{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:14px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.kpi span{display:block;font-size:12px;color:var(--muted)}
.kpi strong{font-size:20px}
.chartbox{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}
canvas{width:100%;height:auto;display:block}
.twocol{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:800px){.twocol{grid-template-columns:1fr}}
"""

LIVE_JS = """
(function(){
const API = "https://external-api.demo.kalshi.co/trade-api/v2";
const $ = id => document.getElementById(id);
let timer = null, samples = [], current = null;
const fmt = v => (v===null||v===undefined||v==="") ? "–" : Number(v).toFixed(4);
const num = v => (v===null||v===undefined||v==="") ? null : Number(v);
function tickerNow(){ return ($("tickerTxt").value.trim() || $("tickerSel").value).toUpperCase(); }
function setStatus(msg, cls){ $("statusLine").textContent = msg; $("statusLine").style.color = cls||""; }
async function getJSON(url){
  const r = await fetch(url, {headers:{"Accept":"application/json"}});
  if(!r.ok) throw new Error("HTTP "+r.status);
  return r.json();
}
function drawChart(){
  const c = $("chart"), g = c.getContext("2d");
  const W = c.width, H = c.height, pad = {l:60,r:20,t:20,b:40};
  g.clearRect(0,0,W,H);
  const winSec = Number($("windowSel").value);
  const now = Date.now(), t0 = now - winSec*1000;
  const pts = samples.filter(s => s.t >= t0);
  g.fillStyle="#fff"; g.fillRect(0,0,W,H);
  // y grid 0..1
  g.font="12px system-ui"; g.strokeStyle="#d8dee4"; g.fillStyle="#59636e";
  for(let i=0;i<=5;i++){
    const y = pad.t + (H-pad.t-pad.b)*(1-i/5);
    g.beginPath(); g.moveTo(pad.l,y); g.lineTo(W-pad.r,y); g.stroke();
    g.fillText((i/5).toFixed(2), 8, y+4);
  }
  // x ticks (time)
  for(let i=0;i<=5;i++){
    const t = t0 + (now-t0)*i/5;
    const x = pad.l + (W-pad.l-pad.r)*i/5;
    const d = new Date(t);
    const label = winSec<=300 ? d.toLocaleTimeString() : d.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
    g.fillText(label, x-30, H-14);
  }
  const X = t => pad.l + (W-pad.l-pad.r)*((t-t0)/(now-t0));
  const Y = p => pad.t + (H-pad.t-pad.b)*(1-p);
  const series = [["last","#0969da"],["bid","#1a7f37"],["ask","#cf222e"]];
  series.forEach(([k,col])=>{
    g.strokeStyle=col; g.lineWidth=2; g.beginPath(); let started=false;
    pts.forEach(s=>{ const v=s[k]; if(v===null) return; const x=X(s.t), y=Y(v); if(!started){g.moveTo(x,y);started=true;} else g.lineTo(x,y); });
    g.stroke();
  });
  // legend
  g.fillStyle="#0969da"; g.fillText("last price",pad.l,14);
  g.fillStyle="#1a7f37"; g.fillText("yes bid",pad.l+90,14);
  g.fillStyle="#cf222e"; g.fillText("yes ask",pad.l+160,14);
  g.fillStyle="#59636e"; g.fillText("Y = contract price ($), X = time", W-260, 14);
}
function renderBook(bodyId, levels){
  const body = $(bodyId);
  if(!levels || !levels.length){ body.innerHTML = '<tr><td colspan="3">No resting orders at the requested depth.</td></tr>'; return; }
  let cum = 0; body.innerHTML = levels.map(([p,q])=>{ cum += Number(q); return `<tr><td>${Number(p).toFixed(4)}</td><td>${Number(q).toFixed(2)}</td><td>${cum.toFixed(2)}</td></tr>`; }).join("");
}
async function poll(){
  const t = tickerNow();
  try{
    const m = (await getJSON(`${API}/markets/${encodeURIComponent(t)}`)).market;
    const b = await getJSON(`${API}/markets/${encodeURIComponent(t)}/orderbook?depth=10`);
    const ob = b.orderbook_fp || {yes_dollars:[], no_dollars:[]};
    const now = Date.now();
    samples.push({t:now, last:num(m.last_price_dollars), bid:num(m.yes_bid_dollars), ask:num(m.yes_ask_dollars)});
    if(samples.length>5000) samples = samples.slice(-5000);
    $("kLast").textContent = fmt(m.last_price_dollars);
    $("kBid").textContent = fmt(m.yes_bid_dollars);
    $("kAsk").textContent = fmt(m.yes_ask_dollars);
    $("kVol").textContent = m.volume_fp ?? "–";
    $("kOi").textContent = m.open_interest_fp ?? "–";
    $("kStatus").textContent = m.status ?? "–";
    // yes bids: ascending, best last -> show best first
    renderBook("bidsBody", (ob.yes_dollars||[]).slice().reverse());
    // yes asks derived from no bids: ask price = 1 - no bid price
    const asks = (ob.no_dollars||[]).slice().reverse().map(([p,q])=>[(1-Number(p)).toFixed(4), q]);
    renderBook("asksBody", asks);
    setStatus(`Updated ${new Date(now).toLocaleTimeString()} from ${API} (demo data).`);
    drawChart();
  }catch(err){
    $("kStatus").textContent = "error";
    setStatus(`Could not reach the Kalshi demo API from this browser (${err.message}). Status unverified: the request may be blocked by CORS or the network, or the ticker may be wrong.`, "#cf222e");
  }
}
function start(){
  stop();
  const reset = tickerNow() !== current; if(reset){ samples = []; current = tickerNow(); }
  poll();
  timer = setInterval(poll, Number($("pollSel").value));
  setStatus("Running…");
}
function stop(){ if(timer){ clearInterval(timer); timer=null; setStatus("Stopped."); } }
$("startBtn").addEventListener("click", start);
$("stopBtn").addEventListener("click", stop);
$("windowSel").addEventListener("change", drawChart);
$("tickerSel").addEventListener("change", ()=>{ $("tickerTxt").value=""; });
drawChart();
})();
"""

SUGG_JS = """
(function(){
const KEY = "kalshi-dashboard-suggestion-choices";
let saved = {};
try { saved = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch(e) { saved = {}; }
function paint(){
  document.querySelectorAll("input.pick").forEach(inp => {
    inp.checked = saved[inp.dataset.id] === inp.value;
    inp.parentElement.classList.toggle("chosen", inp.checked);
  });
}
document.querySelectorAll("input.pick").forEach(inp => {
  inp.addEventListener("change", () => {
    saved[inp.dataset.id] = inp.value;
    localStorage.setItem(KEY, JSON.stringify(saved));
    paint();
  });
});
document.getElementById("copyBtn").addEventListener("click", () => {
  const lines = Object.keys(saved).sort().map(k => k + ": Option " + saved[k]);
  const text = lines.length ? lines.join("\\n") : "No choices selected yet.";
  navigator.clipboard.writeText(text).then(
    () => document.getElementById("copyMsg").textContent = "Copied. Paste it into your message to the agent.",
    () => document.getElementById("copyMsg").textContent = text
  );
});
paint();
})();
"""


def market_page():
    rows = sorted(MS["open_markets"], key=lambda m: float(m["volume_fp"]), reverse=True)
    extra_flags = {"elections": ["F-01"], "gas-prices": ["F-06", "F-18"], "crypto": [], "golf": ["F-19"]}
    trs = []
    for m in rows:
        fl = ["F-02"] + extra_flags.get(m["topic"], [])
        trs.append(f"""<tr>
<td><code>{E(m['ticker'])}</code></td>
<td>{E(m['title'])}<br><small>{E(m['yes_sub_title'])}</small></td>
<td>{E(m['topic'])}</td>
<td>{E(m['status'])}</td>
<td>{E(m['last_price_dollars'])}</td>
<td>{E(m['yes_bid_dollars'])}</td>
<td>{E(m['yes_ask_dollars'])}</td>
<td>{E(m['volume_fp'])}</td>
<td>{E(m['volume_24h_fp'])}</td>
<td>{E(m['open_interest_fp'])}</td>
<td>{E(m['close_time'])}</td>
<td>{link(m['source_api'], 'API response')}</td>
<td><span class="ok">Verified: API</span><br>{flag_links(fl)}</td>
</tr>""")
    body = f"""
<section class="hero small">
  <h1>Market Samples (open demo markets)</h1>
  <p>Open markets returned by the Kalshi <strong>demo</strong> API. Prices are in dollars per contract (a YES contract pays $1.00 if it resolves YES). Volume and open interest are <strong>contract counts</strong>, not dollars (flag F-02).</p>
  <p class="meta">Rows: <strong>{len(rows)}</strong> · Sorted by volume (contracts) <em>within this sample only</em>. This is not a ranking of the exchange and not a dollar ranking.</p>
  <div class="banner warn">Sample, not a list. Each query returned only the first 3 to 5 markets. Golf returned no open markets in this sample (F-19). Liquidity at each price (contracts available) is on the Live Dashboard, which reads the order book.</div>
</section>
<section>
<div class="tablewrap">
<table>
<thead><tr>
<th>Ticker</th><th>Market</th><th>Topic</th><th>Status</th>
<th>Last price ($)</th><th>Yes bid ($)</th><th>Yes ask ($)</th>
<th>Volume (contracts)</th><th>24h volume (contracts)</th><th>Open interest (contracts)</th>
<th>Close time (API)</th><th>Source</th><th>Status</th>
</tr></thead>
<tbody>
{chr(10).join(trs)}
</tbody>
</table>
</div>
</section>
"""
    page("markets.html", "Market Samples", body, active="markets.html")


def resolution_page():
    rows = MS["settled_markets"]
    tally = {}
    for m in rows:
        t = tally.setdefault(m["topic"], {"yes": 0, "no": 0})
        t[m["result"]] += 1
    summary = "".join(f"<li><strong>{E(k)}</strong>: {v['yes']} resolved YES, {v['no']} resolved NO (sample)</li>" for k, v in tally.items())
    trs = []
    for m in rows:
        res = m["result"].upper()
        cls = "yes" if m["result"] == "yes" else "no"
        fl = {"gas-prices": ["F-18"], "golf": ["F-02"], "culture": [], "elections": []}.get(m["topic"], [])
        trs.append(f"""<tr>
<td><code>{E(m['ticker'])}</code></td>
<td>{E(m['title'])}<br><small>{E(m['yes_sub_title'])}</small></td>
<td>{E(m['topic'])}</td>
<td><strong class="{cls}">{res}</strong></td>
<td>{E(m['settlement_value_dollars'])}</td>
<td>{E(m['settlement_ts'])}</td>
<td>{E(m['close_time'])}</td>
<td>{E(m['volume_fp'])}</td>
<td>{E(m['rules_primary'])}</td>
<td>{link(m['source_api'], 'API response')}</td>
<td><span class="ok">Verified: API</span><br>{flag_links(fl)}</td>
</tr>""")
    body = f"""
<section class="hero small">
  <h1>Resolutions (settled demo markets)</h1>
  <p>Settled markets returned by the Kalshi <strong>demo</strong> API, with the <code>result</code> field (YES or NO), the <code>settlement_value_dollars</code> (1.0000 for YES, 0.0000 for NO), and the resolution rule as written by the API.</p>
  <p class="meta">Rows: <strong>{len(rows)}</strong> · Status in the API: <code>finalized</code>. Open events are followed on the <a href="live-dashboard.html">Live Dashboard</a> until they settle.</p>
  <ul class="summary">{summary}</ul>
  <div class="banner warn">Sample only. A market shows here only if it was in the first page of a settled-market query. Demo data, not real markets. See <a href="flagged-for-review.html">Flagged for Review</a>.</div>
</section>
<section>
<div class="tablewrap">
<table>
<thead><tr>
<th>Ticker</th><th>Market</th><th>Topic</th><th>Result</th>
<th>Settlement value ($)</th><th>Settled at (API)</th><th>Close time (API)</th><th>Volume (contracts)</th>
<th>Resolution rule (API)</th><th>Source</th><th>Status</th>
</tr></thead>
<tbody>
{chr(10).join(trs)}
</tbody>
</table>
</div>
</section>
"""
    page("resolutions.html", "Resolutions", body, active="resolutions.html")


def write_assets():
    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, "style.css"), "w", encoding="utf-8") as fh:
        fh.write(STYLE.strip() + "\n")
    with open(os.path.join(ASSETS, "live.js"), "w", encoding="utf-8") as fh:
        fh.write(LIVE_JS.strip() + "\n")
    with open(os.path.join(ASSETS, "suggestions.js"), "w", encoding="utf-8") as fh:
        fh.write(SUGG_JS.strip() + "\n")
    with open(os.path.join(OUT, ".nojekyll"), "w", encoding="utf-8") as fh:
        fh.write("")


def main():
    os.makedirs(OUT, exist_ok=True)
    write_assets()
    index_page()
    for c in D["categories"]:
        category_page(c)
    live_page()
    market_page()
    resolution_page()
    portfolio_page()
    questions_page()
    suggestions_page()
    flagged_page()
    repo_page()
    print("built", OUT)


if __name__ == "__main__":
    main()
