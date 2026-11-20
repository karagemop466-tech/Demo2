#!/usr/bin/env python3
"""Static content pages: executive summary, portfolio, analysis, suggestions, questions,
API reference, verification, flagged-for-review, repo review, sources.

Every factual row carries an official source URL. Where a value cannot be confirmed the
cell is left blank and flagged "Unverified" — never inferred.

Run: python3 tools/build_content.py
"""

from __future__ import annotations

import json
from pathlib import Path

from build_site import DOCS, page, meta_bar, snapshot_meta

ROOT = Path(__file__).resolve().parent.parent
TODAY = "2026-11-20"


def table(headers: list[str], rows: list[list[str]], *, num_cols: set[int] | None = None,
          cls: str = "") -> str:
    num_cols = num_cols or set()
    num = ' class="num"'
    head = "".join(
        "<th%s>%s</th>" % (num if i in num_cols else "", h) for i, h in enumerate(headers)
    )
    body = "".join(
        "<tr>" + "".join(
            "<td%s>%s</td>" % (num if i in num_cols else "", c) for i, c in enumerate(r)
        ) + "</tr>"
        for r in rows
    )
    return (f'<div class="tablewrap {cls}"><table><thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def src(path: str, label: str) -> str:
    return f'<a href="{DOCS}/{path}" target="_blank" rel="noopener">{label}</a>'


L = 'target="_blank" rel="noopener"'

# --------------------------------------------------------------------------- API reference
API_ROWS = [
    # surface, method+path, what it returns, official source, verified how
    ("REST base", "demo", "<code>https://external-api.demo.kalshi.co/trade-api/v2</code>",
     "Recommended demo Trade API root", "getting_started/demo_env", "Read on official page + live 200 response"),
    ("REST base", "demo (alternate)", "<code>https://demo-api.kalshi.co/trade-api/v2</code>",
     "Also supported demo root", "getting_started/api_environments", "Read on official page"),
    ("REST base", "production", "<code>https://external-api.kalshi.com/trade-api/v2</code>",
     "Recommended production root (not used by this site)", "getting_started/api_environments", "Read on official page"),
    ("WebSocket", "demo", "<code>wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2</code>",
     "Recommended demo WS URL", "getting_started/api_environments", "Read on official page"),
    ("WebSocket", "demo (alternate)", "<code>wss://demo-api.kalshi.co/trade-api/ws/v2</code>",
     "Also supported demo WS URL", "getting_started/api_environments", "Read on official page"),
    ("WebSocket", "user fills (demo)", "<code>wss://user-ws.demo.kalshi.co/trade-api/ws/v2</code>",
     "Dedicated lower-latency <code>fill</code>/<code>user_orders</code> host", "getting_started/api_environments", "Read on official page"),
    ("Exchange", "GET", "<code>/exchange/status</code>", "Exchange + per-shard trading status",
     "api-reference/exchange/get-exchange-status", "Live 200 with <code>exchange_active:true</code>"),
    ("Series", "GET", "<code>/series</code>", "All series; <code>category</code>/<code>tags</code> filters; not paginated",
     "api-reference/market/get-series-list", "Live 200; <code>tags=Gas</code> → DIESEL, DIESELM"),
    ("Events", "GET", "<code>/events</code>", "Events, optional <code>with_nested_markets</code>; limit ≤ 200",
     "api-reference/events/get-events", "Live 200"),
    ("Markets", "GET", "<code>/markets</code>", "Markets with prices, volume, open interest, <code>result</code>; limit ≤ 1000",
     "api-reference/market/get-markets", "Live 200"),
    ("Markets", "GET", "<code>/markets/{ticker}/orderbook</code>", "Yes bids + no bids only; asks derived as 1−p; <code>depth</code> 0-100",
     "api-reference/market/get-market-orderbook", "Read on official page"),
    ("Candlesticks", "GET", "<code>/series/{s}/markets/{t}/candlesticks</code>",
     "OHLC per period; <code>period_interval</code> ∈ {1,60,1440}; ≤ 5,000 periods/request; seconds",
     "api-reference/market/get-market-candlesticks", "Read on official page"),
    ("Trades", "GET", "<code>/markets/trades</code>", "Completed trades, limit ≤ 1000, <code>min_ts</code>/<code>max_ts</code> in seconds",
     "api-reference/market/get-trades", "Read on official page"),
    ("Portfolio", "GET", "<code>/portfolio/balance</code>", "balance (cents), <code>balance_dollars</code>, <code>portfolio_value</code>, <code>updated_ts</code>",
     "api-reference/portfolio/get-balance", "Read on official page; own rate-limit bucket"),
    ("Portfolio", "GET", "<code>/portfolio/positions</code>", "<code>position_fp</code>, <code>market_exposure_dollars</code>, <code>realized_pnl_dollars</code>, <code>fees_paid_dollars</code>",
     "api-reference/portfolio/get-positions", "Read on official page"),
    ("Portfolio", "GET", "<code>/portfolio/fills</code>", "<code>outcome_side</code>, <code>book_side</code>, <code>count_fp</code>, <code>yes/no_price_dollars</code>, <code>fee_cost</code>, <code>is_taker</code>",
     "api-reference/portfolio/get-fills", "Read on official page"),
    ("Orders", "POST", "<code>/portfolio/events/orders</code>",
     "Create order (V2). Requires ticker, side (bid/ask), count, price, time_in_force, self_trade_prevention_type",
     "api-reference/orders/create-order-v2", "Read on official page"),
    ("Orders", "POST (removed)", "<code>/portfolio/orders</code>",
     "<b>Returns <code>410 Gone</code></b> with code <code>deprecated_v1_order_endpoint</code> — do not use",
     "api-reference/orders/create-order-v2", "Read on official page"),
    ("Historical", "GET", "<code>/historical/cutoff</code> + <code>/historical/*</code>",
     "Settled markets, trades, fills, orders, positions past the archive cutoff",
     "getting_started/historical_data", "Read on official page"),
    ("Auth", "headers", "<code>KALSHI-ACCESS-KEY</code>, <code>-TIMESTAMP</code> (ms), <code>-SIGNATURE</code> (base64)",
     "Pre-sign text = timestamp + METHOD + path without query; RSA-PSS/SHA-256 or Ed25519; ±30 s",
     "getting_started/quick_start_authenticated_requests", "Read on official page"),
    ("Limits", "tokens", "Read/Write token buckets per tier; <code>429</code> with <code>too_many_requests</code>",
     "Rate limits and tiers", "getting_started/rate_limits", "Read on official page"),
]


def build_api_reference() -> None:
    rows = [
        [s, m, p, d, src(path, path.rsplit("/", 1)[-1]),
         '<span class="pill ok">Verified</span><br><span class="small muted">' + how + "</span>"]
        for s, m, p, d, path, how in API_ROWS
    ]
    t1 = table(["Surface", "Method", "Path / value", "What it provides", "Official source", "Status"], rows)

    t2 = table(["Field", "Exact meaning per the docs", "Why it matters here", "Source"], [
        ["<code>volume_fp</code>", "Fixed-point contract count (2 dp), string",
         "Used with last price to <i>estimate</i> dollar volume - flagged as an estimate because no true dollar-volume field exists",
         src("api-reference/market/get-markets", "Get Markets")],
        ["<code>last_price_dollars</code>", "Fixed-point dollar string, up to 4 dp in, 6 dp out",
         "Y-axis of the price chart", src("getting_started/fixed_point_migration", "Fixed-Point Representation")],
        ["<code>open_interest_fp</code>", "Contracts open at end of period",
         "Second liquidity/interest measure", src("api-reference/market/get-markets", "Get Markets")],
        ["<code>yes_bid_size_fp</code> / <code>yes_ask_size_fp</code>", "Contracts resting at the top of book",
         "&#8220;How many contracts are available at a given price&#8221; at best bid/ask",
         src("api-reference/market/get-markets", "Get Markets")],
        ["<code>result</code>", "<code>yes</code>/<code>no</code> once settled, empty while live",
         "The resolution tracker is driven entirely by this official field",
         src("api-reference/market/get-markets", "Get Markets")],
        ["<code>outcome_side</code>", "Directional exposure a fill created (yes/no)",
         "Trade categorisation by side", src("api-reference/portfolio/get-fills", "Get Fills")],
        ["<code>book_side</code>", "<code>bid</code> = buy YES, <code>ask</code> = sell YES",
         "How the executor encodes a NO bet (ask at 1 - price)",
         src("api-reference/portfolio/get-fills", "Get Fills")],
        ["<code>realized_pnl_dollars</code>", "Locked-in P&amp;L in dollars",
         "Portfolio performance", src("api-reference/portfolio/get-positions", "Get Positions")],
        ["<code>fee_cost</code>", "Fee cost in fixed-point dollars",
         "Net-of-fee P&amp;L", src("api-reference/portfolio/get-fills", "Get Fills")],
    ])

    t3 = table(["Endpoint", "Why not", "Source"], [
        ["<code>POST /portfolio/orders</code> (legacy)", "Removed; returns 410 Gone",
         src("api-reference/orders/create-order-v2", "Create Order (V2)")],
        ["<code>/fcm/fills</code>", "Only for FCM member accounts; this is a direct demo account",
         src("api-reference/portfolio/get-fills", "Get Fills")],
        ["Margin / perps endpoints", "Out of scope: this dashboard tracks event markets only",
         src("getting_started/fixed_point_migration", "Fixed-Point Representation")],
    ])

    body = (
        "<h1>API reference - verified line by line</h1>"
        '<p class="lead">Every value this site displays comes from one of the endpoints below. '
        "Each row was checked against the official Kalshi documentation page linked in the row on "
        + TODAY + ". No third-party documentation, blog post or memory was used.</p>"
        '<div class="notice info"><b>Two findings that changed the build.</b>'
        "<br>1. The legacy order path <code>POST /portfolio/orders</code> has been <b>removed</b> and now "
        "returns <code>410 Gone</code> (<code>deprecated_v1_order_endpoint</code>). Trade execution uses "
        "<code>POST /portfolio/events/orders</code> instead."
        "<br>2. The order book returns <b>bids on both sides only</b> - no asks. A YES ask at price "
        "<i>x</i> is a NO bid at <i>1 - x</i>, so the dashboard's ask column is <b>derived</b> and "
        "labelled that way rather than presented as a raw field.</div>"
        + t1
        + "<h2>Field semantics that the analysis depends on</h2>" + t2
        + "<h2>Endpoints deliberately <i>not</i> used</h2>" + t3
    )
    page(path="pages/api-reference.html", title="API Reference", active="api", body=body,
         desc="Line-by-line verified Kalshi Trade API reference used by this dashboard.")


# --------------------------------------------------------------------------- exec summary
def build_executive_summary() -> None:
    body = """
<h1>Executive summary</h1>
<p class="lead">A dashboard that collects, organises and analyses Kalshi <b>demo</b> markets in
five topics only - gas prices, elections, culture, crypto, golf - tracks them until they resolve
yes/no, charts price against time with selectable windows, shows contracts available at each
price, and reports demo-account performance with trade categorisation and strategy candidates.</p>

<div class="grid">
<div class="card">
<h3>What was asked, and where it lives</h3>
<ul class="clean">
<li><b>Highest dollar-amount live events, five topics only</b> - <a href="../index.html">Dashboard</a>
  ranks by a labelled <i>estimate</i>; the raw official fields sit beside it. Scope is decided by
  official series <code>tags</code>/<code>categories</code>, not by keyword guessing.</li>
<li><b>Track until resolved, yes or no</b> - <a href="resolutions.html">Resolutions</a> lists every
  settled in-scope market with Kalshi&#8217;s own <code>result</code> field.</li>
<li><b>Portfolio performance on the demo account</b> - <a href="portfolio.html">Portfolio</a>.</li>
<li><b>Analyse results, categorise trades, build strategies</b> -
  <a href="analysis.html">Analysis</a>. Strategies are only emitted above an evidence threshold,
  otherwise the page says &#8220;insufficient data&#8221; rather than inventing a rule.</li>
<li><b>Execute trades and track performance</b> - signed demo orders via
  <code>POST /portfolio/events/orders</code>; every attempt is logged with its HTTP status.</li>
<li><b>Live interactive graph, X = time, Y = contract price, seconds to days</b> -
  <a href="../index.html">Dashboard</a> chart, 60 s / 5 m / 1 h / 6 h / 24 h / 7 d.</li>
<li><b>Current liquidity: how many contracts at a given price</b> - order-book panel on the
  Dashboard; full depth on each category page.</li>
<li><b>Suggestions section to choose a path before implementing</b> -
  <a href="suggestions.html">Suggestions</a> (decisions are recorded, nothing auto-applies).</li>
<li><b>Questions / information / answers needed before deciding</b> -
  <a href="questions.html">Questions</a>.</li>
</ul>
</div>
<div class="card">
<h3>How the data is actually obtained</h3>
<p>This is a static GitHub Pages site, so it cannot hold a secret and a visitor&#8217;s browser
cannot be the only data path. Instead:</p>
<ol class="clean">
<li>A GitHub Actions workflow runs <code>tools/collector.py</code> every 10 minutes against the
   official demo API (<a href="https://docs.kalshi.com/getting_started/demo_env" target="_blank" rel="noopener">demo environment</a>).</li>
<li>The collector writes <code>data/*.json</code>, including an <b>API log</b> of every request
   and its HTTP status, and commits the snapshot.</li>
<li>The pages read those snapshots, so every number on screen traces back to a logged request.</li>
</ol>
<p class="small muted">Consequence stated plainly: the site is refreshed every 10 minutes, not
tick-by-tick. The 60-second chart window is therefore often empty. Real-time would need a hosted
WebSocket relay, which is raised as a decision in <a href="suggestions.html">Suggestions</a>.</p>
</div>
<div class="card">
<h3>What it explicitly does not do</h3>
<ul class="clean">
<li>No real-money trading. Demo host only, hard-coded.</li>
<li>No invented values: missing data renders as an em dash and the row is marked
  <span class="pill flag">unverified</span>.</li>
<li>No strategy claim below the evidence threshold.</li>
<li>No claim that demo prices predict production prices - Kalshi&#8217;s own docs warn they may not
  be reflective (<a href="https://docs.kalshi.com/getting_started/demo_env" target="_blank" rel="noopener">demo_env</a>).</li>
</ul>
</div>
<div class="card">
<h3>Headline risks</h3>
<ul class="clean">
<li><b>Definition risk.</b> &#8220;Highest dollar amount&#8221; has no single API field; the ranking is
  an estimate (<a href="flagged.html">F2</a>, <a href="questions.html">Q1</a>).</li>
<li><b>Coverage risk.</b> Demo liquidity is thin and some demo series carry placeholder strikes;
  sample sizes for strategy work will be small for a long time (<a href="flagged.html">F8</a>).</li>
<li><b>Credentials.</b> Portfolio and execution need a demo API key pair configured as repository
  secrets. Until then those pages show an explicit &#8220;not configured&#8221; state, not zeros.</li>
<li><b>Correctness defect found and fixed.</b> The earlier build posted orders to a removed
  endpoint; it is documented in <a href="flagged.html">F7</a>.</li>
</ul>
</div>
</div>

<h2>Decision readiness in one table</h2>
""" + table(["Question a decision-maker must settle", "Status", "Where to settle it"], [
 ["How is &#8220;highest dollar volume&#8221; defined - volume, open interest, or an estimate?", '<span class="pill flag">Open</span>', '<a href="questions.html">Q1</a>'],
 ["Which series are authoritative for gas and golf (tag-based, since categories are Economics/Sports)?", '<span class="pill ok">Resolved - tags</span>', '<a href="api-reference.html">API reference</a>'],
 ["Is 10-minute snapshot freshness acceptable, or is live streaming required?", '<span class="pill flag">Open</span>', '<a href="questions.html">Q3</a>'],
 ["Is a demo API key available for portfolio/execution?", '<span class="pill flag">Open</span>', '<a href="questions.html">Q4</a>'],
 ["What is the minimum sample before a strategy may be stated?", '<span class="pill ok">Resolved - 5 resolved fills, flagged low confidence</span>', '<a href="analysis.html">Analysis</a>'],
 ["Should demo-derived strategies be treated as transferable to production?", '<span class="pill flag">Open</span>', '<a href="questions.html">Q7</a>'],
]) + """
<h2>Bottom line</h2>
<p>Built and sourced: the five-topic scope, the ranked live view, the time-versus-price chart, order-book
depth, yes/no resolution tracking, trade categorisation, a strategy engine that refuses to guess, a review
gate for suggestions, and a price-jump page for moves of $0.10 or more between official trade prints
(<a href="../jumps/index.html">Price Jumps</a>, added in this review).</p>
<p><b>Not done, and why.</b> Demo-account portfolio tracking and order execution need a Kalshi demo API key,
and this workspace has none (<a href="flagged.html">F19</a>). Culture has no open markets in the collected
data (<a href="flagged.html">F20</a>). The gas topic includes solar, electricity and refinery markets
(<a href="flagged.html">F14</a>). The jump page cannot name a cause, because no official source links a price
move to news (<a href="flagged.html">F18</a>), and snapshots are too coarse for intraday moves
(<a href="flagged.html">F17</a>). A public page takes a demo private key as input
(<a href="flagged.html">F21</a>).</p>
<p>What remains open is definition and access: what &#8220;highest dollar amount&#8221; means, how fresh the data
must be, whether a demo key will be supplied, and how much evidence is enough before a strategy is trusted.
Those are listed, with the exact information needed to close them, on <a href="questions.html">Questions</a>.</p>
"""
    page(path="pages/executive-summary.html", title="Executive Summary", active="exec", body=body)


# --------------------------------------------------------------------------- portfolio
def build_portfolio() -> None:
    body = """
<h1>Portfolio - demo account</h1>
<p class="lead">Balance, open positions and fills for the Kalshi <b>demo</b> account, read with a
signed request. Signing rules, headers and the pre-sign string are exactly as documented in
<a href="https://docs.kalshi.com/getting_started/quick_start_authenticated_requests" target="_blank" rel="noopener">Quick Start: Authenticated Requests</a>.</p>

<div id="authState"></div>
<div class="kpis" id="kpis"></div>

<h2>Positions</h2>
<p class="muted">From <code>GET /portfolio/positions?settlement_status=all</code>. Field meanings are
listed under the table so no number is ambiguous.</p>
<div id="posTable"></div>

<h2>Fills - the raw trade record</h2>
<p class="muted">From <code>GET /portfolio/fills</code>. Every fill shows the official
<code>outcome_side</code>, <code>book_side</code>, price on both legs, fee and whether it was taker
or maker.</p>
<div id="fillTable"></div>

<h2>Executions - what the executor did</h2>
<p class="muted">From <code>data/executions.json</code>, written by
<code>tools/execute_strategy.py</code>. Dry-run entries were validated but never sent. Only
entries with an HTTP status were actually transmitted.</p>
<div id="execTable"></div>

<h2>Placing a demo order by hand is not required</h2>
<p class="muted">Execution is driven by <code>data/strategy_plan.json</code> plus the
<code>trade.yml</code> workflow and three explicit switches - <code>KALSHI_TRADING_ENABLED=1</code>,
a demo key pair, and a per-run notional cap (default $25). The executor refuses any ticker that is
not in the collector&#8217;s in-scope set, refuses duplicates in one run, and always uses
<code>immediate_or_cancel</code> so no order is left resting unattended. Rationale and the exact
request shape are on <a href="api-reference.html">API reference</a>.</p>

<h2>Field glossary (official meanings)</h2>
""" + table(["Field", "Meaning", "Source"], [
 ["<code>balance</code> / <code>balance_dollars</code>", "Available balance in cents / fixed-point dollars", src("api-reference/portfolio/get-balance", "Get Balance")],
 ["<code>portfolio_value</code>", "Portfolio value in cents", src("api-reference/portfolio/get-balance", "Get Balance")],
 ["<code>position_fp</code>", "Signed net contracts: positive = YES, negative = NO", src("api-reference/portfolio/get-positions", "Get Positions")],
 ["<code>market_exposure_dollars</code>", "Cost basis of the remaining position, excluding fees - not market value", src("api-reference/portfolio/get-positions", "Get Positions")],
 ["<code>realized_pnl_dollars</code>", "Locked-in profit and loss", src("api-reference/portfolio/get-positions", "Get Positions")],
 ["<code>total_traded_dollars</code>", "Total ever spent trading that market, including past trades", src("api-reference/portfolio/get-positions", "Get Positions")],
 ["<code>count_fp</code>", "Contracts in the fill, fixed-point string, min granularity 0.01", src("api-reference/portfolio/get-fills", "Get Fills")],
 ["<code>is_taker</code>", "True if the fill removed liquidity", src("api-reference/portfolio/get-fills", "Get Fills")],
]) + "</div>"
    js = r"""
<script>
(async function(){
  const $ = id=>document.getElementById(id);
  let p;
  try{ p = await KR.portfolio(); }catch(e){
    $('authState').innerHTML = `<div class="notice bad">data/portfolio.json is missing or unreadable (${KR.esc(e.message)}).
      The portfolio workflow has not produced a snapshot yet.</div>`;
    return;
  }
  if(!p.authenticated){
    $('authState').innerHTML = `<div class="notice"><b>Portfolio not configured - no demo API key in this repository.</b>
      <br>${KR.esc(p.reason||'')}
      <br class="small">The collector runs with public endpoints only until a demo key pair is added as
      repository secrets. Balances, positions and fills are deliberately blank rather than zero,
      because "no key" and "empty account" are different facts.
      <br><span class="small muted">Requirement: <a href="https://docs.kalshi.com/getting_started/api_keys" target="_blank" rel="noopener">API Keys</a></span></div>`;
    $('kpis').innerHTML = '';
    $('posTable').innerHTML = '<div class="empty">Blank - not connected.</div>';
    $('fillTable').innerHTML = '<div class="empty">Blank - not connected.</div>';
  } else {
    const b = p.balance||{};
    const pos = p.positions||[], fills = p.fills||[];
    const realized = pos.reduce((s,x)=>s+(parseFloat(x.realized_pnl_dollars)||0),0);
    const fees = pos.reduce((s,x)=>s+(parseFloat(x.fees_paid_dollars)||0),0);
    const exposure = pos.reduce((s,x)=>s+(parseFloat(x.market_exposure_dollars)||0),0);
    $('authState').innerHTML = `<div class="notice info">Connected · fetched ${KR.when(p.fetched_at_utc)} ·
      balance endpoint HTTP ${KR.esc(p.balance_http_status)}</div>`;
    $('kpis').innerHTML = `
      <div class="kpi-card"><div class="k">Cash balance</div><div class="v">${KR.usd(b.balance_dollars,2)}</div><div class="s">official <code>balance_dollars</code></div></div>
      <div class="kpi-card"><div class="k">Portfolio value</div><div class="v">${KR.usd((b.portfolio_value||0)/100,2)}</div><div class="s">official <code>portfolio_value</code> (cents)</div></div>
      <div class="kpi-card"><div class="k">Realized P&amp;L</div><div class="v ${realized>=0?'ok':'bad'}">${KR.usd(realized,2)}</div><div class="s">sum of <code>realized_pnl_dollars</code></div></div>
      <div class="kpi-card"><div class="k">Open exposure</div><div class="v">${KR.usd(exposure,2)}</div><div class="s">cost basis, excl. fees</div></div>
      <div class="kpi-card"><div class="k">Fees paid</div><div class="v">${KR.usd(fees,2)}</div><div class="s">official <code>fees_paid_dollars</code></div></div>
      <div class="kpi-card"><div class="k">Fills</div><div class="v">${fills.length}</div><div class="s">trades recorded</div></div>`;
    KR.renderTable($('posTable'), [
      {label:'Market', get:x=>`<code>${KR.esc(x.ticker)}</code>`},
      {label:'Net contracts', num:true, get:x=>KR.num(x.position_fp,2)},
      {label:'Cost basis', num:true, get:x=>KR.usd(x.market_exposure_dollars,2)},
      {label:'Realized P&amp;L', num:true, get:x=>KR.usd(x.realized_pnl_dollars,2)},
      {label:'Fees', num:true, get:x=>KR.usd(x.fees_paid_dollars,2)},
      {label:'Total traded', num:true, get:x=>KR.usd(x.total_traded_dollars,2)},
      {label:'Updated', get:x=>`<span class="small">${KR.when(x.last_updated_ts)}</span>`}
    ], pos, 'No positions returned.');
    KR.renderTable($('fillTable'), [
      {label:'Time', get:x=>`<span class="small">${KR.when(x.created_time)}</span>`},
      {label:'Market', get:x=>`<code>${KR.esc(x.ticker||x.market_ticker)}</code>`},
      {label:'Outcome', get:x=>`<span class="pill ${KR.esc(x.outcome_side)}">${KR.esc(x.outcome_side)}</span>`},
      {label:'Book side', get:x=>KR.esc(x.book_side)},
      {label:'Contracts', num:true, get:x=>KR.num(x.count_fp,2)},
      {label:'YES px', num:true, get:x=>KR.usd(x.yes_price_dollars,3)},
      {label:'NO px', num:true, get:x=>KR.usd(x.no_price_dollars,3)},
      {label:'Fee', num:true, get:x=>KR.usd(x.fee_cost,3)},
      {label:'Role', get:x=>x.is_taker?'<span class="pill flag">taker</span>':'<span class="pill">maker</span>'}
    ], fills, 'No fills returned.');
  }
  try{
    const ex = await KR.executions();
    $('execTable').innerHTML = `<p class="small muted">Mode: <b>${KR.esc(ex.mode)}</b> · endpoint <code>${KR.esc(ex.endpoint||'')}</code> · run cap $${KR.esc(ex.run_notional_cap_usd||'')}</p>`;
    KR.renderTable($('execOut'), [], []);
    const wrap = document.createElement('div');
    $('execTable').insertAdjacentHTML('beforeend','<div id="execOut2"></div>');
    KR.renderTable($('execOut2'), [
      {label:'Ticker', get:r=>`<code>${KR.esc(r.ticker)}</code>`},
      {label:'Side', get:r=>KR.esc(r.side)},
      {label:'Contracts', num:true, get:r=>KR.num(r.count,2)},
      {label:'Result', get:r=>r.skipped?`<span class="pill flag">skipped</span><br><span class="small muted">${KR.esc(r.skipped)}</span>`
        : r.http_status?`<span class="pill ${r.ok?'ok':'err'}">HTTP ${r.http_status}</span>`
        : `<span class="pill">${KR.esc(r.note||'validated, not sent')}</span>`}
    ], ex.results||[], 'No executions recorded yet.');
  }catch(e){
    $('execTable').innerHTML = '<div class="empty">No data/executions.json yet - the trade workflow has not run.</div>';
  }
})();
</script>"""
    body += """
<h2>Local trading CLI (verified against the current API)</h2>
<p class="lead"><code>tools/kalshi_trade.py</code> signs every request locally (Ed25519 or
RSA-PSS/SHA-256, timestamp + method + path &mdash; """ + src("getting_started/api_keys", "API Keys") + """).
The site never accepts or stores credentials. Order commands use the V2 endpoints
(""" + src("api-reference/orders/create-order-v2", "create") + """, """ + src("api-reference/orders/cancel-order-v2", "cancel") + """;
book side <code>bid</code> &equiv; yes, <code>ask</code> &equiv; no &mdash; """ + src("getting_started/order_direction", "order_direction") + """).</p>
<div class="tablewrap"><table><thead><tr><th>Command</th><th>Endpoint</th><th>Purpose</th></tr></thead><tbody>
<tr><td><code>balance</code></td><td><code>GET /portfolio/balance</code></td><td>Balance + portfolio value (requires demo key)</td></tr>
<tr><td><code>positions</code> / <code>fills</code></td><td><code>GET /portfolio/positions</code> / <code>GET /portfolio/fills</code></td><td>Position and execution history</td></tr>
<tr><td><code>order</code></td><td><code>POST /portfolio/events/orders</code></td><td>Place a limit order (fixed-point price/count strings)</td></tr>
<tr><td><code>cancel</code></td><td><code>DELETE /portfolio/events/orders/{id}?market_ticker=</code>&hellip;</td><td>Cancel a resting order (ticker required for auto-routing)</td></tr>
<tr><td><code>report</code> / <code>selftest</code></td><td>&mdash;</td><td>Local P&amp;L/strategy report / signing self-test</td></tr>
</tbody></table></div>
"""
    page(path="pages/portfolio.html", title="Portfolio", active="port", body=body, extra_js=js,
         desc="Kalshi demo account balance, positions, fills and executions.")


# --------------------------------------------------------------------------- analysis
def build_analysis() -> None:
    body = """
<h1>Trade analysis and strategies</h1>
<p class="lead">Performance of the demo account, categorised five ways, with strategy candidates
that are only stated when the evidence clears a threshold. P&amp;L is computed from official
fields; the arithmetic is written out so it can be checked.</p>
<div id="state"></div>
<div class="kpis" id="kpis"></div>

<h2>Categorisation</h2>
<div class="grid two">
<div class="card"><h3>By topic</h3><p class="small muted">Trade category from the official series mapping.</p><div id="catTopic"></div></div>
<div class="card"><h3>By side</h3><p class="small muted">From <code>outcome_side</code>.</p><div id="catSide"></div></div>
<div class="card"><h3>By role at execution</h3><p class="small muted">From <code>is_taker</code>.</p><div id="catRole"></div></div>
<div class="card"><h3>By entry price band</h3><p class="small muted">Price paid on the held side.</p><div id="catBand"></div></div>
<div class="card"><h3>By eventual outcome</h3><p class="small muted">Open vs resolved yes/no.</p><div id="catOutcome"></div></div>
<div class="card"><h3>Method</h3>
<dl class="kv">
<dt>Cost</dt><dd>contracts × price paid on the held side</dd>
<dt>Payout</dt><dd>contracts × $1.00 when the held side equals the official <code>result</code>, else $0</dd>
<dt>Realized P&amp;L</dt><dd>payout − cost − <code>fee_cost</code></dd>
<dt>Open trades</dt><dd>cost and fees counted, realized deliberately left blank</dd>
</dl>
<p class="small muted">No value is estimated in this table. The only estimate anywhere on the site
is the dashboard&#8217;s dollar-volume proxy, which is labelled.</p>
</div>
</div>

<h2>Strategy candidates</h2>
<div id="strat"></div>

<h2>Trade-by-trade record</h2>
<div id="tradeTable"></div>
"""
    js = r"""
<script>
(async function(){
  const $=id=>document.getElementById(id);
  let a;
  try{ a = await KR.analysis(); }catch(e){
    $('state').innerHTML = `<div class="notice bad">data/analysis.json missing (${KR.esc(e.message)}).</div>`; return;
  }
  const t=a.totals||{};
  $('state').innerHTML = a.authenticated
    ? `<div class="notice info">Computed from the authenticated demo account · generated ${KR.when(a.generated_at_utc)} · verdict <b>${KR.esc(a.verdict)}</b>: ${KR.esc(a.verdict_explanation||'')}</div>`
    : `<div class="notice"><b>No demo API key configured</b>, so there is nothing to analyse yet. This is not a zero - it is an absence of data. Verdict: <b>${KR.esc(a.verdict)}</b>.</div>`;
  $('kpis').innerHTML = `
    <div class="kpi-card"><div class="k">Fills</div><div class="v">${t.fills||0}</div><div class="s">${t.resolved_fills||0} resolved · ${t.open_fills||0} open</div></div>
    <div class="kpi-card"><div class="k">Invested</div><div class="v">${KR.usd(t.cost_dollars,2)}</div><div class="s">cost across fills</div></div>
    <div class="kpi-card"><div class="k">Realized P&amp;L</div><div class="v ${(t.realized_pnl_dollars||0)>=0?'ok':'bad'}">${KR.usd(t.realized_pnl_dollars,2)}</div><div class="s">net of fees</div></div>
    <div class="kpi-card"><div class="k">Hit rate</div><div class="v">${t.hit_rate===null||t.hit_rate===undefined?'—':KR.pct(t.hit_rate)}</div><div class="s">${t.wins||0}W / ${t.losses||0}L resolved</div></div>
    <div class="kpi-card"><div class="k">Fees</div><div class="v">${KR.usd(t.fees_dollars,2)}</div><div class="s">official <code>fee_cost</code> sum</div></div>`;

  const c=a.categories||{};
  function catTable(el, key, label){
    const g=c[key]||{};
    const rows=Object.entries(g).map(([k,v])=>({k,v}));
    KR.renderTable($(el), [
      {label:label, get:r=>KR.esc(r.k)},
      {label:'Fills', num:true, get:r=>r.v.n},
      {label:'Resolved', num:true, get:r=>r.v.resolved_n},
      {label:'Cost', num:true, get:r=>KR.usd(r.v.cost,2)},
      {label:'Realized', num:true, get:r=>`<span class="${r.v.realized>=0?'ok':'bad'}">${KR.usd(r.v.realized,2)}</span>`},
      {label:'Hit rate', num:true, get:r=>r.v.hit_rate===null?'—':KR.pct(r.v.hit_rate)},
      {label:'Fees', num:true, get:r=>KR.usd(r.v.fees,2)}
    ], rows, 'No fills in this category yet.');
  }
  catTable('catTopic','by_topic','Topic'); catTable('catSide','by_side','Side');
  catTable('catRole','by_role','Role'); catTable('catBand','by_price_band','Price band');
  catTable('catOutcome','by_outcome','Outcome');

  const s=a.strategies||[];
  if(!s.length){
    $('strat').innerHTML = `<div class="empty"><b>No strategy is asserted.</b><br>
      ${KR.esc(a.verdict_explanation||'')}<br>
      <span class="small">A rule is only emitted when a category has at least 5 resolved fills and
      positive realized P&amp;L. Below that threshold the honest answer is "not enough evidence",
      and that is what this page shows.</span></div>`;
  } else {
    $('strat').innerHTML = s.map(x=>`<div class="card" style="margin-bottom:10px">
      <h3>${KR.esc(x.id)} <span class="pill ${x.confidence==='medium'?'ok':'flag'}">${KR.esc(x.confidence)} confidence</span></h3>
      <p>${KR.esc(x.rule)}</p>
      <p class="small muted">Caveat: ${KR.esc(x.caveat)}</p></div>`).join('');
  }
  KR.renderTable($('tradeTable'), [
    {label:'Time', get:t=>`<span class="small">${KR.when(t.created_time)}</span>`},
    {label:'Topic', get:t=>KR.topicPill(t.topic)},
    {label:'Market', get:t=>`<code>${KR.esc(t.ticker)}</code><br><span class="muted small">${KR.esc((t.title||'').slice(0,60))}</span>`},
    {label:'Side', get:t=>`<span class="pill ${KR.esc(t.side)}">${KR.esc(t.side)}</span>`},
    {label:'Contracts', num:true, get:t=>KR.num(t.count_fp,2)},
    {label:'Price paid', num:true, get:t=>KR.usd(t.price_paid_dollars,3)},
    {label:'Cost', num:true, get:t=>KR.usd(t.cost_dollars,2)},
    {label:'Fee', num:true, get:t=>KR.usd(t.fee_dollars,3)},
    {label:'Result', get:t=>KR.resultPill(t.market_result)},
    {label:'Realized', num:true, get:t=>t.realized_pnl_dollars===null?'<span class="muted">open</span>':`<span class="${t.realized_pnl_dollars>=0?'ok':'bad'}">${KR.usd(t.realized_pnl_dollars,2)}</span>`}
  ], a.trades||[], 'No trades recorded.');
})();
</script>"""
    page(path="pages/analysis.html", title="Analysis", active="an", body=body, extra_js=js,
         desc="Demo-account trade analysis, categorisation and evidence-gated strategy candidates.")


# --------------------------------------------------------------------------- suggestions
SUGGESTIONS = [
    dict(id="S1", title="Decide what \u201chighest dollar amount\u201d means",
         problem="The Trade API has no dollar-volume field. The dashboard currently ranks by "
                 "volume_fp \u00d7 last_price_dollars and labels it an estimate.",
         options=["Keep the estimate, clearly labelled (current)",
                  "Rank by volume_fp (contracts) only",
                  "Rank by open_interest_fp (contracts)",
                  "Rank by volume \u00d7 time-weighted average price, collected over N runs"],
         effort="Low", impact="High", risk="A wrong definition silently changes every ranking.",
         source=DOCS + "/api-reference/market/get-markets",
         recommended="Keep the estimate, and add volume-only and open-interest-only sort keys "
                     "\u2014 already done on the dashboard, so the reader can compare."),
    dict(id="S2", title="Scope by official tags, not keywords",
         problem="Keyword matching on titles mislabels and misses markets.",
         options=["Official series tags/categories (implemented)",
                  "Manual allow-list of series tickers",
                  "Keyword matching (rejected)"],
         effort="Low", impact="High", risk="Model risk from mis-scoped markets.",
         source=DOCS + "/api-reference/market/get-series-list",
         recommended="Implemented. Gas is found by the \u201cGas\u201d tag and golf by \u201cGolf\u201d "
                     "because their categories are Economics and Sports; elections, culture and "
                     "crypto use their category. Unmapped series are listed, never guessed."),
    dict(id="S3", title="Raise data freshness from 10 minutes to live",
         problem="GitHub Actions snapshots run every 10 minutes, so the 60-second chart window is "
                 "usually empty and \u201clive\u201d is really \u201cnear-live\u201d.",
         options=["Accept 10-minute snapshots (current)",
                  "Host a small relay that keeps a WebSocket open to the demo feed and appends ticks",
                  "Move to polling every 60 s (rate-limit budget permitting)"],
         effort="Medium", impact="High", risk="A relay needs hosting, secrets and a cost owner.",
         source=DOCS + "/getting_started/quick_start_websockets",
         recommended="Approve a relay only if sub-minute responsiveness is actually required; "
                     "otherwise rename the panel \u201cnear-live\u201d so the label is honest."),
    dict(id="S4", title="Supply a demo API key pair",
         problem="Portfolio, P&L and execution are blank because no demo credentials are "
                 "configured. Nothing is fabricated to fill the gap.",
         options=["Add KALSHI_DEMO_API_KEY_ID and KALSHI_DEMO_PRIVATE_KEY as repository secrets",
                  "Leave read-only and public data only"],
         effort="Low", impact="High", risk="A leaked key; mitigate by using a demo-only key and "
                                          "keeping it in Actions secrets, never in the repo.",
         source=DOCS + "/getting_started/api_keys",
         recommended="Add a demo-only key pair as repository secrets."),
    dict(id="S5", title="Set the evidence threshold for calling something a strategy",
         problem="Any rule derived from a handful of demo fills is noise.",
         options=["5 resolved fills, low confidence (current)",
                  "20 resolved fills, medium confidence",
                  "50 resolved fills, higher confidence",
                  "No strategies until a stated benchmark exists"],
         effort="Low", impact="Medium", risk="Overfitting to a demo market with mock liquidity.",
         source=DOCS + "/getting_started/demo_env",
         recommended="Keep 5 as the floor but never label anything above \u201clow\u201d until 20 "
                     "resolved fills per category."),
    dict(id="S6", title="Decide whether demo behaviour may inform production strategy",
         problem="Kalshi documents that demo prices and behaviour may not reflect real markets.",
         options=["Treat strategies as demo-only exercises (current)",
                  "Re-validate each rule on production data before use",
                  "Ignore demo results entirely"],
         effort="Low", impact="High", risk="Transferring demo edges to real money.",
         source=DOCS + "/getting_started/demo_env",
         recommended="Re-validate on production data before any real-money use."),
    dict(id="S7", title="Add resolution alerting",
         problem="Resolution is recorded on the next 10-minute run, but nobody is notified.",
         options=["Email/Slack via Actions on newly settled in-scope markets",
                  "No alerts, dashboard only (current)"],
         effort="Low", impact="Medium", risk="Alert fatigue if the topic list widens.",
         source=DOCS + "/api-reference/market/get-markets",
         recommended="Add one digest per settled batch rather than per market."),
    dict(id="S8", title="Publish the API log alongside the numbers",
         problem="A reader cannot tell which request produced a figure.",
         options=["Link the snapshot\u2019s api_log from each table (implemented)",
                  "No provenance (rejected)"],
         effort="Low", impact="Medium", risk="None.",
         source=DOCS + "/getting_started/pagination",
         recommended="Implemented \u2014 see the API log section on Verification."),
    dict(id="S9", title="Mark sharp price jumps (\u2265 $0.10) on the live chart",
         problem="A sharp price move has no visible marker on the chart, so a trader can miss a "
                 "significant move.",
         options=["Mark jumps \u2265 $0.10 with red vertical markers + a table below the chart (implemented)",
                  "No markers, keep chart clean (rejected)",
                  "News/event links per jump: the cause is not derivable from the API, so each jump "
                  "instead gets a clearly labelled \u201cpossible context\u201d search link plus a "
                  "\u201ccause unverified\u201d flag (implemented)"],
         effort="Low", impact="High", risk="A reader could mistake a jump marker for a confirmed "
                                         "causal event \u2014 mitigated by the unverified flag (F13).",
         source=DOCS + "/api-reference/market/get-market-candlesticks",
         recommended="Implemented \u2014 see the \u201cSharp price moves\u201d card on the Dashboard. Each "
                     "jump is flagged \u201ccause unverified\u201d because the Trade API returns price "
                     "and volume only."),
]


def build_suggestions() -> None:
    cards = []
    for s in SUGGESTIONS:
        opts = "".join(f"<li>{o}</li>" for o in s["options"])
        cards.append(f"""
<div class="card" style="margin-bottom:12px" data-sug="{s['id']}">
  <h3>{s['id']} \u00b7 {s['title']}</h3>
  <p><b>Problem.</b> {s['problem']}</p>
  <p style="margin-bottom:.2em"><b>Options on the table.</b></p>
  <ul class="clean">{opts}</ul>
  <p><b>Recommendation.</b> {s['recommended']}</p>
  <p class="small muted">Effort {s['effort']} \u00b7 Impact {s['impact']} \u00b7 Risk: {s['risk']}</p>
  <p class="small">Source: <a href="{s['source']}" target="_blank" rel="noopener">{s['source']}</a></p>
  <div class="row">
    <button class="sm" data-decide="choose" data-id="{s['id']}">Choose this path</button>
    <button class="secondary sm" data-decide="defer" data-id="{s['id']}">Defer</button>
    <button class="secondary sm" data-decide="reject" data-id="{s['id']}">Reject</button>
    <span class="status" id="dec-{s['id']}">No decision recorded</span>
  </div>
  <label for="note-{s['id']}">Reviewer note (stored in this browser only)</label>
  <input id="note-{s['id']}" data-note="{s['id']}" placeholder="why, and what would change your mind">
</div>""")
    body = f"""
<h1>Suggestions \u2014 review before anything changes</h1>
<p class="lead">Nine improvement proposals, each with the problem, the options, the trade-off and
the official source that motivates it. Nothing here is implemented on your behalf. Record a
decision per item; decisions and notes stay in this browser so you can review the set as a whole
before choosing a path.</p>
<div class="notice info">Recommendations are advisory. Where a recommendation is already built
(for example official-tag scoping) the card says so, so you can accept or reverse it with full
knowledge. No decision is transmitted anywhere.</div>
<div class="row" style="margin:12px 0">
  <button id="exportBtn" class="secondary">Export my decisions (JSON)</button>
  <button id="clearBtn" class="secondary">Clear local decisions</button>
  <span class="status muted" id="decSummary"></span>
</div>
{''.join(cards)}
<script>
(function(){{
  const KEY='kalshi-demo-decisions-v2';
  const load=()=>JSON.parse(localStorage.getItem(KEY)||'{{}}');
  const save=d=>localStorage.setItem(KEY,JSON.stringify(d));
  function paint(){{
    const d=load(); let n=0;
    ['S1','S2','S3','S4','S5','S6','S7','S8','S9'].forEach(id=>{{
      const el=document.getElementById('dec-'+id); if(!el) return;
      const rec=d[id];
      if(rec){{ n++; el.innerHTML='<span class="pill '+(rec.decision==='choose'?'ok':rec.decision==='reject'?'err':'flag')+'">'+rec.decision+'</span> <span class="small muted">'+new Date(rec.at).toLocaleString()+'</span>'; }}
      else el.textContent='No decision recorded';
      const note=document.getElementById('note-'+id);
      if(note && rec && rec.note && !note.value) note.value=rec.note;
    }});
    document.getElementById('decSummary').textContent=n+' of 9 decided';
  }}
  document.querySelectorAll('button[data-decide]').forEach(b=>b.addEventListener('click',()=>{{
    const d=load(), id=b.dataset.id;
    const note=document.getElementById('note-'+id);
    d[id]={{decision:b.dataset.decide, note:(note?note.value:''), at:new Date().toISOString()}};
    save(d); paint();
  }}));
  document.querySelectorAll('input[data-note]').forEach(i=>i.addEventListener('change',()=>{{
    const d=load(), id=i.dataset.note;
    d[id]=Object.assign({{decision:'note'}}, d[id]||{{}}, {{note:i.value, at:new Date().toISOString()}});
    save(d);
  }}));
  document.getElementById('exportBtn').addEventListener('click',()=>{{
    const blob=new Blob([JSON.stringify(load(),null,2)],{{type:'application/json'}});
    const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
    a.download='kalshi-demo-decisions.json'; a.click();
  }});
  document.getElementById('clearBtn').addEventListener('click',()=>{{ localStorage.removeItem(KEY); location.reload(); }});
  paint();
}})();
</script>
"""
    body += """
<h2>Integration additions (session 5330bffb, 2026-11-20)</h2>
<p class="lead">Review board only &mdash; nothing here is implemented by default.</p>
<div class="tablewrap"><table><thead><tr><th>#</th><th>Suggestion</th><th>Reviewer choice</th></tr></thead><tbody>
<tr><td>S10</td><td><b>Topic allowlist</b>: add <code>KXCABALLOTMEASURES</code>-style state/measure markets to Elections via an explicit ticker-pattern allowlist, with its settlement sources listed.</td><td>Keep excluded &nbsp;/&nbsp; Include with source list</td></tr>
<tr><td>S11</td><td><b>Fixed-point utility</b>: accept human decimals in the CLI and convert internally; display values read as numbers with units (&ldquo;$43.92&rdquo;), never raw <code>"43.92"</code> without a unit.</td><td>Keep explicit &nbsp;/&nbsp; Accept decimals + show units</td></tr>
</tbody></table></div>
<p class="lead">Status updates: S2 (browser WebSocket live streaming) &mdash; a proxy is now the only
option, since direct WS is impossible from a browser (G-1); CORS for REST was confirmed
(G-2, closed). The dashboard already provides the 15-second poll as the interim path.</p>
"""
    page(path="pages/suggestions.html", title="Suggestions", active="sug", body=body,
         desc="Eight reviewed improvement proposals with options, trade-offs and official sources.")


# --------------------------------------------------------------------------- questions
QUESTIONS = [
 ("Q1", "What exactly is \u201chighest dollar amount\u201d?",
  "The API exposes <code>volume_fp</code> (contracts), <code>open_interest_fp</code> (contracts), "
  "<code>last_price_dollars</code>, and <code>notional_value_dollars</code> per contract. There is no "
  "traded-dollar-volume field.",
  "A decision on which definition the ranking must use, and whether an estimate is acceptable.",
  "Asked of the stakeholder. Interim: dashboard shows three sort keys and labels the estimate.",
  "api-reference/market/get-markets"),
 ("Q2", "Which series belong to each of the five topics?",
  "Official series records carry <code>tags</code> and <code>categories</code>. Gas is tagged "
  "<code>Gas</code> but categorised <code>Economics</code>; golf is tagged <code>Golf</code> but "
  "categorised <code>Sports</code>; elections/culture/crypto match on category.",
  "Confirmation that the five topics mean exactly these tags, and whether adjacent series "
  "(e.g. crude oil, jet fuel, other sports) should be in or out.",
  "Answered from the API itself: the collector publishes every in-scope series ticker, and any "
  "series it could not classify is listed on the Flagged page for review. Nothing is guessed.",
  "api-reference/market/get-series-list"),
 ("Q3", "How fresh must the data be?",
  "The site is static on GitHub Pages; the collector runs every 10 minutes and commits a snapshot.",
  "Whether \u201clive\u201d means sub-minute (which needs a hosted WebSocket relay) or near-live.",
  "Ask the stakeholder; S3 in Suggestions lays out the three options and their cost.",
  "getting_started/quick_start_websockets"),
 ("Q4", "Is a demo API key available for portfolio and execution?",
  "Demo credentials are separate from production and are never committed. Without them the "
  "portfolio and analysis pages are blank by design.",
  "A demo key pair, supplied as repository secrets, plus a decision on the per-run notional cap.",
  "Blocked on the account owner. Until then the pages state \u201cnot configured\u201d rather than showing zeros.",
  "getting_started/api_keys"),
 ("Q5", "What are the fee and rate-limit consequences at the volumes we would trade?",
  "Fees are charged per fill (<code>fee_cost</code>); reads and writes draw on separate token "
  "buckets with per-tier budgets, and balance has its own 1-5 call/s bucket.",
  "The account tier, the intended trade frequency, and whether maker fees apply to these series.",
  "Read the tier from the account, then size polling and execution to it. The collector currently "
  "stays well inside public limits.",
  "getting_started/rate_limits"),
 ("Q6", "How do we know a market resolved for the reason we expected?",
  "Each market carries <code>rules_primary</code>/<code>rules_secondary</code> and a settlement "
  "source list; the settled record carries <code>result</code> and "
  "<code>settlement_value_dollars</code>.",
  "A judgement on edge cases (early close, cancellation, amended rules) before relying on outcomes.",
  "Partly answerable from the data: the resolution tables link the rules text and settlement "
  "source per market; edge cases still need a human read.",
  "getting_started/market_settlement"),
 ("Q7", "May demo results inform a production strategy?",
  "Kalshi states demo prices and behaviour may not reflect real markets.",
  "An explicit policy decision: demo-only exercise, or re-validation on production data required.",
  "Recommended: re-validate on production data. Not a decision this session can make.",
  "getting_started/demo_env"),
 ("Q8", "What sample size makes a strategy trustworthy?",
  "The analysis currently requires 5 resolved fills to emit a low-confidence rule and refuses below that.",
  "A threshold, a benchmark (buy-and-hold? random?), and a maximum drawdown limit.",
  "Ask the stakeholder; S5 lists threshold options.",
  "getting_started/demo_env"),
 ("Q9", "Do historical settled markets need to be included?",
  "Markets settled before the archive cutoff only appear via <code>/historical/markets</code>.",
  "Whether the resolution tracker must be complete, or only recent.",
  "The collector pages live settled markets first; the historical endpoints are documented and "
  "can be added if completeness is required.",
  "getting_started/historical_data"),
 ("Q10", "Should the gas topic be widened so it is not empty in the demo environment?",
  "<code>DIESEL</code>/<code>DIESELM</code> are the only Gas-tagged series and neither has live demo "
  "markets, so the Gas page currently shows catalogue entries and zero live prices. Retail gasoline "
  "and crude-oil series may exist under other tags or categories.",
  "A decision on whether the gas topic means &#8220;the Gas tag only&#8221; (literal, currently empty) or "
  "&#8220;fuel and energy prices&#8221; broadly (wider, but then the boundary needs defining).",
  "Answered partly: the collector publishes every tag and category it sees with counts, and every "
  "Gas-tagged series. A human must choose whether to widen the mapping.",
  "api-reference/market/get-series-list"),
 ("Q11", "Who owns the running cost and the secrets?",
  "GitHub Actions runs the collector; Pages hosts the site; a relay (if chosen) needs hosting.",
  "An owner for the workflow, the key rotation, and any future relay.",
  "Operational question for the repo owner.",
  "getting_started/api_keys"),
 ("Q12", "Which subsite is authoritative?",
  "Parallel sessions produced three independent builds: <code>/</code> (this one, CI-checked), "
  "<code>/dashboard/</code> and <code>/verified/</code>. All three were preserved during the merge "
  "rather than one being deleted.",
  "A decision on which subsite to keep, redirect or delete, before search engines index three "
  "competing dashboards.",
  "Nothing is deleted unilaterally; the README table names each path and its origin, and this "
  "question records the choice as the owner's to make.",
  "getting_started/api_environments"),
]


def build_questions() -> None:
    rows = [[q[0], q[1], q[2], q[3], q[4], src(q[5], q[5].rsplit("/", 1)[-1])] for q in QUESTIONS]
    body = """
<h1>Questions, information and answers needed before deciding</h1>
<p class="lead">Twelve questions stand between the current build and a decision that is defensible.
For each one: what we already know from an official source, exactly what is still missing, how it
can be discovered, and the source that anchors the known part. Nothing here is padded with
questions that the data already answers.</p>
<div class="notice"><b>Already answered by verified sources</b> (so not listed as open): the demo
REST/WS base URLs; that public market data needs no authentication; the signing algorithm and
pre-sign string; that the legacy order endpoint returns 410; that the order book has no ask side;
that candles cap at 5,000 periods; that gas and golf are tag-identified rather than
category-identified. See <a href="api-reference.html">API reference</a>.</div>
""" + table(["#", "Question", "What we know (verified)", "What is missing", "How to discover it", "Source"], rows) + """
<h2>The single question that blocks the most</h2>
<p><b>Q1, the definition of \u201chighest dollar amount\u201d.</b> Every ranking on every page
inherits it. It is a one-line policy decision, but until it is made the dashboard must present
three sort keys side by side and label its own ranking an estimate. If a dollar-volume figure is
required exactly, it has to be reconstructed from individual trades
(<code>GET /markets/trades</code>: price × contracts summed per market), which is a materially
larger collection job and a separate decision.</p>
<h2>What would change if Q3 (freshness) were answered \u201clive only\u201d</h2>
<p>The static-site architecture would need a relay. That is a hosting, secret-management and cost
decision, not a coding one. The current design deliberately keeps everything inside GitHub so
there is nothing to pay for and nothing to leak.</p>
"""
    body += """
<h2>Integration answers and additions (session 5330bffb, 2026-11-20)</h2>
<div class="tablewrap"><table><thead><tr><th>#</th><th>Question</th><th>Answer</th><th>Still unknown</th><th>How to discover</th><th>Source</th></tr></thead><tbody>
<tr><td>IQ-1</td><td>How is price written in order requests?</td><td>Fixed-point strings: <code>"0.5600"</code> (4dp dollars) for price, <code>"10.00"</code> (2dp) for counts (docs 2026-11-20).</td><td>None.</td><td>&mdash;</td><td><a href="https://docs.kalshi.com/api-reference/orders/create-order-v2">create-order-v2</a></td></tr>
<tr><td>IQ-2</td><td>Is order-book price shown in bracket notation (<code>[520, 6]</code>)?</td><td>Yes: the array is <code>[price in cents, quantity]</code> &mdash; <code>[520, 6]</code> = 6 contracts at 52&cent;.</td><td>None.</td><td>&mdash;</td><td><a href="https://docs.kalshi.com/api-reference/market/get-market-orderbook">get-market-orderbook</a></td></tr>
<tr><td>IQ-3</td><td>Can the browser fetch demo data live? (Q4 follow-up)</td><td>Yes for REST: the probe returned <code>access-control-allow-origin: https://karagemop466-tech.github.io</code>. WS remains impossible without a proxy.</td><td>Nothing blocking.</td><td>Re-check <code>data/cors.json</code> after API changes.</td><td><a href="https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=1">probe</a></td></tr>
<tr><td>IQ-4</td><td>May the site hold my Kalshi password or API key?</td><td>No. A public static site cannot hold secrets; the demo account requires a human login at demo.kalshi.co.</td><td>Nothing &mdash; the restriction is permanent.</td><td>User creates their own demo API key; figures go in a secured backend (S2).</td><td><a href="https://docs.kalshi.com/getting_started/demo_env">demo env</a></td></tr>
<tr><td>IQ-5</td><td>Do snapshot rows match the live API now?</td><td>Culture rows matched exactly (2026-11-20); golf matches on the first response page; crypto flags G-4/G-6 reproduced.</td><td>Re-verification of every row needs a live browser session.</td><td>Open each row's source link and compare field by field.</td><td><a href="verification.html">re-verification table</a></td></tr>
</tbody></table></div>
"""
    page(path="pages/questions.html", title="Questions", active="q", body=body,
         desc="Open questions, known facts and missing information required before decisions.")


# --------------------------------------------------------------------------- verification
# (claim, value, official source path, how it was checked, status)
VERIFIED = [
 ("Demo REST base (recommended)", "<code>https://external-api.demo.kalshi.co/trade-api/v2</code>",
  "getting_started/demo_env", "read on page + live 200 JSON from /exchange/status", "Verified"),
 ("Demo REST base (also supported)", "<code>https://demo-api.kalshi.co/trade-api/v2</code>",
  "getting_started/demo_env", "read on page", "Verified"),
 ("Demo WS URL (recommended)", "<code>wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2</code>",
  "getting_started/api_environments", "read on page", "Verified"),
 ("Production REST base (not used here)", "<code>https://external-api.kalshi.com/trade-api/v2</code>",
  "getting_started/api_environments", "read on page", "Verified"),
 ("Demo funds are mock; demo prices may not reflect real markets",
  "stated as a warning on the demo page", "getting_started/demo_env", "read on page", "Verified"),
 ("Public market-data endpoints need no authentication",
  "no auth headers required for /series, /events, /markets, orderbook",
  "getting_started/quick_start_market_data", "read on page + live unauthenticated 200", "Verified"),
 ("Signed requests: header names", "<code>KALSHI-ACCESS-KEY</code>, <code>KALSHI-ACCESS-TIMESTAMP</code> (ms), <code>KALSHI-ACCESS-SIGNATURE</code> (base64)",
  "getting_started/quick_start_authenticated_requests", "read on page", "Verified"),
 ("Signed requests: pre-sign string", "timestamp + HTTP_METHOD + path, query string excluded",
  "getting_started/quick_start_authenticated_requests", "read on page", "Verified"),
 ("Signed requests: algorithms", "RSA-PSS with SHA-256, or Ed25519 signed directly",
  "getting_started/quick_start_authenticated_requests", "read on page", "Verified"),
 ("Timestamp tolerance", "within 30 seconds of Kalshi\u2019s clock",
  "getting_started/quick_start_authenticated_requests", "read on page", "Verified"),
 ("Get Markets pagination limit", "up to 1000 per page (default 100)",
  "getting_started/pagination", "read on page", "Verified"),
 ("Get Events pagination limit", "up to 200 per page (default 200)",
  "getting_started/pagination", "read on page", "Verified"),
 ("Get Series is not paginated", "no limit or cursor; returns every matching series",
  "getting_started/pagination", "read on page + live response has no cursor", "Verified"),
 ("Order book returns bids only", "yes bids and no bids; a YES ask at x equals a NO bid at 1-x",
  "api-reference/market/get-market-orderbook", "read on page", "Verified"),
 ("Order book depth parameter", "1-100; 0 or omitted returns all levels",
  "api-reference/market/get-market-orderbook", "read on page", "Verified"),
 ("Candlestick periods", "<code>period_interval</code> \u2208 {1, 60, 1440} minutes",
  "api-reference/market/get-market-candlesticks", "read on page", "Verified"),
 ("Candlestick request span", "max 5,000 periods per request; start_ts/end_ts in seconds",
  "api-reference/market/get-market-candlesticks", "read on page", "Verified"),
 ("Legacy order endpoints removed", "<code>/portfolio/orders</code> writes return <code>410 Gone</code> with <code>deprecated_v1_order_endpoint</code>",
  "api-reference/orders/create-order-v2", "read on page", "Verified"),
 ("Create order (V2) path", "<code>POST /portfolio/events/orders</code>",
  "api-reference/orders/create-order-v2", "read on page", "Verified"),
 ("Create order required fields", "ticker, side (bid|ask), count, price, time_in_force, self_trade_prevention_type",
  "api-reference/orders/create-order-v2", "read on page", "Verified"),
 ("time_in_force values", "<code>fill_or_kill</code>, <code>good_till_canceled</code>, <code>immediate_or_cancel</code> (<code>GTT</code> is not valid)",
  "api-reference/orders/create-order-v2", "read on page", "Verified"),
 ("book_side semantics", "<code>bid</code> = buy YES, <code>ask</code> = sell YES, quoted from the YES leg",
  "api-reference/portfolio/get-fills", "read on page", "Verified"),
 ("Balance rate limit", "own bucket: 1/s (Basic, Advanced), 5/s (higher tiers)",
  "api-reference/portfolio/get-balance", "read on page", "Verified"),
 ("Rate-limit response", "<code>429</code> with code <code>too_many_requests</code>, exponential backoff advised",
  "getting_started/rate_limits", "read on page", "Verified"),
 ("Historical partition", "settled markets/trades/fills/orders/positions move behind <code>/historical/*</code> after the cutoff",
  "getting_started/historical_data", "read on page", "Verified"),
 ("Price precision", "<code>*_dollars</code> prices are fixed-point strings, up to 4 dp in and 6 dp out",
  "getting_started/fixed_point_migration", "read on page", "Verified"),
 ("Contract quantity precision", "<code>*_fp</code> counts are strings, min granularity 0.01, responses emit 2 dp",
  "getting_started/fixed_point_migration", "read on page", "Verified"),
 ("Gas series discovery signal", "<code>tags</code> contains <code>Gas</code>; category is <code>Economics</code>",
  "api-reference/market/get-series-list", "live <code>GET /series?tags=Gas</code> returned DIESEL and DIESELM", "Verified"),
 ("Golf series discovery signal", "<code>tags</code> contains <code>Golf</code>; category is <code>Sports</code>",
  "api-reference/market/get-series-list", "live <code>GET /series?tags=Golf</code> and <code>/series/KXPGATOUR</code>", "Verified"),
 ("Elections / crypto discovery signal", "<code>categories</code> contains <code>Elections</code> / <code>Crypto</code>",
  "api-reference/market/get-series-list", "live <code>GET /series?category=Elections</code> and <code>?category=Crypto</code>", "Verified"),
 ("FX / market values on the site", "blank in the static text; filled only from the collector snapshot",
  "api-reference/market/get-markets", "values are never hard-coded into HTML", "By design"),
 # --- rows added by session arena-1d709f30 (verified 2026-11-20 from docs + live demo API) ---
 ("WebSocket handshake requires authentication",
  "KALSHI-ACCESS-KEY / -SIGNATURE / -TIMESTAMP headers required even for public channels; browsers cannot set WS headers, so this site streams via REST polling",
  "getting_started/quick_start_websockets", "read on page", "Verified"),
 ("Get Trades endpoint",
  "public; min_ts/max_ts in seconds; limit 1-1000; fields include trade_id, count_fp, yes_price_dollars, created_time, taker_outcome_side",
  "api-reference/market/get-trades", "read on page + live 200 JSON from /markets/trades?ticker=KXELONMARS-99", "Verified"),
 ("Live candlesticks response",
  "OHLC distributions + volume_fp + open_interest_fp returned for period_interval=60",
  "api-reference/market/get-market-candlesticks",
  "live 200 on /series/KXELONMARS/markets/KXELONMARS-99/candlesticks", "Verified"),
 ("Live orderbook shape",
  "orderbook_fp.yes_dollars = [[price, count], ...] ascending; depth=5 honored; empty side is a valid 200",
  "api-reference/market/get-market-orderbook",
  "live 200 on /markets/KXELONMARS-99/orderbook?depth=5", "Verified"),
 ("Event category field is deprecated",
  "use the series-level category for classification; event category still observed populated in live responses",
  "api-reference/events/get-events", "read on page + live response sample", "Verified"),
 ("Gas-price series (AAA gasoline)",
  "KXAAAGASM (monthly) and KXAAAGASD (daily): category Economics, scope Gasoline, settlement source AAA",
  "api-reference/market/get-series-list", "live GET /series/KXAAAGASM and GET /series/KXAAAGASD", "Verified"),
 ("Settlement outcome",
  "result is yes / no / scalar; winners receive $1 per contract; finalized = paid out",
  "getting_started/market_settlement", "read on page", "Verified"),
 ("Market status filter to schema mapping",
  "filter open=active, settled=finalized, closed=past close_time not yet finalized; schema also has determined/disputed/amended",
  "getting_started/market_lifecycle", "read on page", "Verified"),
 ("Computed dollar-volume metric",
  "est_dollar_volume_24h = sum(volume_24h_fp x last_price_dollars) shown with the marker on rankings.html; computed, not an official API field (official contract volumes shown alongside)",
  "api-reference/market/get-markets", "formula disclosed on the page; never presented as an API field", "By design"),
 ("Portfolio / order endpoints require signed keys",
  "GET /portfolio/balance and GET /portfolio/positions return 401 without signed headers; no demo credentials exist in this workspace, so all portfolio/trade rows stay blank and flagged",
  "api-reference/portfolio/get-balance", "read on page (security scheme kalshiAccessKey) + unauthenticated request fails", "Verified"),
 ("Sharp-jump price-move detection (\u2265 $0.10)",
  "Chart detects moves of $0.10 or more between consecutive price points and marks them with red "
  "vertical markers; the table below the chart lists each jump with a link to the market on Kalshi "
  "and a clearly labelled \u201cpossible context\u201d search link. The cause of each jump is not "
  "derivable from the Kalshi API (no news/event field in price responses) and is flagged cause unverified.",
  "api-reference/market/get-market-candlesticks|api-reference/market/get-trades",
  "implemented in assets/site.js (KR.detectJumps) + chart markers in KR.drawChart; table renders on index.html", "By design"),
 ("Get Trades tape query (live alerts)",
  "<code>GET /markets/trades?limit=1000&amp;min_ts=&lt;unix seconds&gt;</code> returns completed "
  "trades with <code>ticker</code>, <code>yes_price_dollars</code>, <code>count_fp</code>, "
  "<code>created_time</code>, <code>trade_id</code>",
  "api-reference/market/get-trades",
  "read on page + live 200 JSON; sample prints preserved in data/dashboard_instrument.json trade blocks", "Verified"),
 ("Order book raw response shape",
  "<code>orderbook_fp.yes_dollars</code> / <code>orderbook_fp.no_dollars</code>, arrays of "
  "[price, size]; ask depth is derived as 1 &#8722; p and labelled &#8220;derived&#8221; everywhere",
  "api-reference/market/get-market-orderbook",
  "read on page + parsed live in tools/collector.py (collect_orderbooks) and assets/alerts.js", "Verified"),
 ("Live alert chats (moves of $0.10+, all events + model filter)",
  "alerts.html runs two scrolling chats over official trade prints and quote polls (15 s cadence, "
  "60 s backoff on HTTP 429). Swing cause is flagged unverified (F13); the high-ROI filter is a "
  "labelled local heuristic (F22); markets are watched until the official result posts yes/no.",
  "api-reference/market/get-trades|api-reference/market/get-markets|getting_started/rate_limits",
  "implemented in assets/alerts.js against the request shapes verified in this table; no value is invented", "By design"),
 ("Snapshot file-size bounds (data pipeline)",
  "collector publishes the top rows per topic by estimated dollar volume, writes compact JSON "
  "and refuses any data file over 90 MB; GitHub rejects pushes containing a file over 100 MB, "
  "which is what failed every Refresh Kalshi demo data run on 2026-11-20 (COORDINATION.md A-1)",
  "https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github",
  "regression-tested offline in tests/test_collector_output.py (52 assertions); workflow tripwire step added", "By design"),
]


def src_multi(p) -> str:
    # one row can cite several official pages: "|" string or tuple/list of paths.
    # Full https URLs are rendered as-is (used for non-Kalshi official sources such
    # as docs.github.com); everything else is a docs.kalshi.com path.
    paths = p if isinstance(p, (tuple, list)) else p.split("|")
    out = []
    for x in paths:
        if x.startswith("http"):
            out.append(f'<a href="{x}" target="_blank" rel="noopener">{x.split("//", 1)[1].split("/", 1)[0]}</a>')
        else:
            out.append(src(x, x.rsplit("/", 1)[-1]))
    return ", ".join(out)


def build_verification() -> None:
    rows = [[c, v, src_multi(p), how,
             '<span class="pill ok">Verified</span>' if st == "Verified"
             else '<span class="pill flag">By design</span>']
            for c, v, p, how, st in VERIFIED]
    body = """
<h1>Verification \u2014 line by line</h1>
<p class="lead">Every claim this site rests on, the official page it was checked against, and how
it was checked. Checked on 2026-11-20. Nothing in this table relies on memory, a blog, or a
third-party API wrapper.</p>
<div class="notice info"><b>Rule applied throughout:</b> if a value cannot be confirmed from an
official Kalshi source, it is left blank and flagged rather than inferred. That is why the
market tables contain no hard-coded numbers \u2014 they are populated only from the collector
snapshot, which logs the HTTP status of every request it made.</div>
""" + table(["Claim", "Value / statement", "Official source", "How it was checked", "Status"], rows) + """
<h2>Live API log from the most recent snapshot</h2>
<p class="lead">The collector writes the URL, HTTP status and any error body for every request it
makes. This is the provenance for every figure in the dashboard tables.</p>
<div class="kpis" id="logKpis"></div>
<div id="apiLog"></div>
<h2>What is deliberately <i>not</i> claimed</h2>
""" + table(["Not claimed", "Why not"], [
 ["That demo prices predict production prices", "Kalshi documents that demo prices may not reflect real markets."],
 ["A dollar-volume figure presented as exact", "No such field exists in the Trade API; the dashboard labels its figure an estimate."],
 ["Ask-side order-book depth as a raw field", "The API returns bids only; the ask side is derived as 1 \u2212 p and labelled."],
 ["A strategy derived from a handful of fills", "The analysis refuses to emit below 5 resolved fills."],
 ["Portfolio figures without credentials", "\u201cNo key\u201d and \u201czero balance\u201d are different facts, and are shown differently."],
]) + "</div>"
    js = r"""
<script>
(async function(){
  const $=id=>document.getElementById(id);
  try{
    const s = await KR.snapshot();
    const log = s.api_log||[];
    const ok = log.filter(r=>r.ok).length, bad = log.length-ok;
    $('logKpis').innerHTML = `
      <div class="kpi-card"><div class="k">Requests logged</div><div class="v">${log.length}</div><div class="s">this snapshot</div></div>
      <div class="kpi-card"><div class="k">HTTP 2xx</div><div class="v ok">${ok}</div><div class="s">successful</div></div>
      <div class="kpi-card"><div class="k">Failed</div><div class="v ${bad?'bad':'ok'}">${bad}</div><div class="s">${bad?'see rows below':'none'}</div></div>
      <div class="kpi-card"><div class="k">Snapshot</div><div class="v" style="font-size:1rem">${KR.esc(s.generated_at_utc||'')}</div><div class="s">${KR.ago(s.generated_at_utc)}</div></div>`;
    document.getElementById('apiLog').innerHTML = '';
    const wrap=document.createElement('div'); wrap.id='apiLogInner';
    document.getElementById('apiLog').appendChild(wrap);
    const rows = log.filter(r=>!r.ok).length ? log : log.slice(0,40);
    KR.renderTable(wrap, [
      {label:'HTTP', get:r=>`<span class="pill ${r.ok?'ok':'err'}">${KR.esc(r.http_status)}</span>`},
      {label:'Request', get:r=>`<code class="small">${KR.esc(r.url)}</code>`},
      {label:'Note', get:r=>KR.dash(r.note?KR.esc(r.note).slice(0,140):'')},
      {label:'At (UTC)', get:r=>`<span class="small">${KR.esc(r.at||'')}</span>`}
    ], rows, 'No API log in this snapshot.');
  }catch(e){ $('logKpis').innerHTML = `<div class="notice bad">${KR.esc(e.message)}</div>`; }
})();
</script>"""
    body += """
<h2>Additional verified claims (integration session 5330bffb, 2026-11-20)</h2>
<div class="tablewrap"><table><thead><tr><th>Claim</th><th>Verified value</th><th>Source</th><th>Result</th></tr></thead><tbody>
<tr><td>Order price/count literals</td><td>Fixed-point strings: price 4dp dollars, count 2dp</td><td><a href="https://docs.kalshi.com/api-reference/orders/create-order-v2">create-order-v2</a></td><td>Verified 2026-11-20 (OpenAPI)</td></tr>
<tr><td>Legacy order writes</td><td><code>/portfolio/orders</code> create/cancel/amend/decrease return <code>410 Gone</code></td><td><a href="https://docs.kalshi.com/api-reference/orders/create-order-v2">create-order-v2</a></td><td>Verified 2026-11-20; tools/kalshi_trade.py migrated to V2</td></tr>
<tr><td>Order direction</td><td>book_side <code>bid</code> &equiv; outcome_side <code>yes</code>, <code>ask</code> &equiv; <code>no</code>; price scale unchanged</td><td><a href="https://docs.kalshi.com/getting_started/order_direction">order_direction</a></td><td>Verified 2026-11-20</td></tr>
<tr><td>Cancel order V2</td><td><code>DELETE /portfolio/events/orders/{id}?market_ticker=</code>&hellip; (ticker required for auto-routing)</td><td><a href="https://docs.kalshi.com/api-reference/orders/cancel-order-v2">cancel-order-v2</a></td><td>Verified 2026-11-20 (OpenAPI)</td></tr>
<tr><td>Browser CORS from the Pages origin</td><td><code>access-control-allow-origin: https://karagemop466-tech.github.io</code></td><td><a href="https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=1">probe (headers in data/cors.json)</a></td><td>Verified by observation 2026-11-20T12:12:40Z</td></tr>
<tr><td>WebSocket handshake</td><td>Requires signed <code>KALSHI-ACCESS-*</code> headers</td><td><a href="https://docs.kalshi.com/getting_started/quick_start_websockets">quick start</a></td><td>Verified 2026-11-20 &mdash; browsers cannot connect directly</td></tr>
<tr><td>Order-book arrays</td><td><code>[price in cents, quantity]</code></td><td><a href="https://docs.kalshi.com/api-reference/market/get-market-orderbook">get-market-orderbook</a></td><td>Verified 2026-11-20</td></tr>
<tr><td>Candlesticks</td><td><code>period_interval</code> 1/60/1440; traded price can be an empty object in quiet periods</td><td><a href="https://docs.kalshi.com/api-reference/market/get-market-candlesticks">get-market-candlesticks</a></td><td>Verified 2026-11-20</td></tr>
<tr><td>Settlement</td><td>Winning side settles at $1.00 per contract; losing side $0</td><td><a href="https://docs.kalshi.com/getting_started/market_settlement">market settlement</a></td><td>Verified 2026-11-20</td></tr>
<tr><td>Status enums</td><td>Filter values differ from response values in the same doc</td><td><a href="https://docs.kalshi.com/api-reference/market/get-markets">get-markets</a></td><td>Verified 2026-11-20 &mdash; docs inconsistency flagged (G-10)</td></tr>
</tbody></table></div>
"""
    page(path="pages/verification.html", title="Verification", active="ver", body=body, extra_js=js,
         desc="Every claim, the official source, and how it was verified.")


# --------------------------------------------------------------------------- flagged
FLAGGED = [
 ("F1", "Sandbox egress to Kalshi is blocked",
  "The authoring sandbox\u2019s TLS handshake to <code>external-api.demo.kalshi.co</code> fails "
  "(<code>SSL_ERROR_SYSCALL</code>), so the collector could not be proven from inside the sandbox.",
  "Any \u201clive\u201d number would have been unverifiable.",
  "Moved collection to GitHub Actions, which has normal egress, and made every snapshot carry an "
  "HTTP-status log. The workflow fails loudly rather than publishing an empty snapshot.",
  "getting_started/demo_env"),
 ("F2", "No dollar-volume field exists",
  "The Trade API exposes contract counts (<code>volume_fp</code>, <code>open_interest_fp</code>) and "
  "prices, but no traded-dollar-volume field.",
  "Ranking by \u201chighest dollar amount\u201d cannot be sourced exactly.",
  "Dashboard shows the estimate <code>volume_fp \u00d7 last_price_dollars</code>, tags it "
  "<span class=\"pill flag\">est.</span>, and offers volume-only and open-interest-only sorts "
  "beside it. Raised as Q1 / S1.",
  "api-reference/market/get-markets"),
 ("F3", "Order book has no ask side",
  "The endpoint returns yes bids and no bids only.",
  "Naive code would show a book with no offers and a false spread.",
  "Ask depth is derived as <code>1 \u2212 p</code> from no bids and labelled "
  "<b>derived</b> everywhere it appears, including the spread.",
  "api-reference/market/get-market-orderbook"),
 ("F4", "Legacy order endpoint returns 410 Gone",
  "The previously published build posted to <code>POST /portfolio/orders</code>, which the docs now "
  "mark removed and which returns <code>410</code> with <code>deprecated_v1_order_endpoint</code>.",
  "Trade execution would have failed silently for every user of that page.",
  "Rewritten against <code>POST /portfolio/events/orders</code> with the documented required body "
  "fields. Logged as a correctness defect in the repo review (R3).",
  "api-reference/orders/create-order-v2"),
 ("F5", "Demo prices may not reflect real markets",
  "Kalshi states this explicitly as a warning on the demo page.",
  "Any strategy derived from demo fills may not transfer.",
  "Warning shown on every data page; strategies are labelled demo-only; Q7 / S6 ask for an "
  "explicit policy decision.",
  "getting_started/demo_env"),
 ("F6", "No demo API key is configured",
  "Portfolio, P&L and execution need a signed request with a demo key pair.",
  "Those pages cannot show real figures.",
  "They show an explicit \u201cnot configured\u201d state rather than zeros, with the exact secret "
  "names required. Raised as Q4 / S4.",
  "getting_started/api_keys"),
 ("F7", "Demo data contains synthetic test markets",
  "Verified live: <code>KXQUICKSETTLE-20NOV26H0550-3</code> is titled &#8220;1+1 = 3&#8221; with rules "
  "&#8220;If 1+1 equals 3 &#8230; resolves to Yes&#8221;, <code>KXDEMOFUTHOURLY-</code> markets are "
  "explicitly labelled Demo BTC, and some events carry placeholder strikes such as "
  "<code>{\"demo strike\": \"demo strike\"}</code> with close dates in 2099.",
  "Averaging over synthetic markets produces meaningless statistics.",
  "Nothing is excluded silently: these markets fall outside the five topics because they carry no "
  "in-scope tag or category, and the unmapped-series list is published for review.",
  "api-reference/market/get-markets"),
 ("F8", "Snapshot freshness is 10 minutes, not real time",
  "Data is refreshed by a scheduled GitHub Actions run.",
  "Short chart windows are often empty; the word \u201clive\u201d overstates it.",
  "Labelled on the dashboard, the empty state explains why, and S3 offers a relay as a decision.",
  "getting_started/quick_start_websockets"),
 ("F9", "Unmapped series are excluded, not guessed",
  "Any open event whose series has no in-scope tag/category is dropped from the tables.",
  "In-scope markets could be missed if Kalshi tags a series unusually.",
  "The collector publishes the full list of unclassified series in the snapshot for review, and "
  "<code>data/snapshot.json</code> keeps the series inventory with tag counts.",
  "api-reference/market/get-series-list"),
 ("F10", "Some demo series carry unreviewed metadata",
  "Demo series responses include staging S3 hostnames (e.g. "
  "<code>kalshi-public-docs-staging.s3...</code>) in <code>contract_url</code>, and repeated "
  "placeholder settlement-source strings.",
  "Contract links from demo records are not always stable or final.",
  "Links are surfaced as returned, with the production docs link provided as the authoritative "
  "reference on the same row.",
  "api-reference/market/get-series-list"),
 ("F11", "Candlestick traded price is empty in quiet periods",
  "Verified live on <code>KXPGATOUR-THRC26-LABE</code>: several candlesticks return "
  "<code>\"price\":{}</code> because no trade occurred in that period, while the bid and ask closes "
  "are still present. Periods with no activity can be omitted from the response entirely.",
  "Plotting the traded price alone leaves gaps, or an empty chart, on thin demo markets.",
  "The chart defaults to a <b>derived quoted mid</b> = (yes bid close + yes ask close) / 2, labelled "
  "&#8220;derived&#8221;, and keeps &#8220;last trade&#8221; as an explicit option that shows its own gaps. The "
  "collector stores both, so nothing is interpolated.",
  "api-reference/market/get-market-candlesticks"),
 ("F12", "A topic can exist in the catalogue with no live markets",
  "Verified live: <code>DIESEL</code> and <code>DIESELM</code> are the Gas-tagged series, but the demo "
  "environment has no open events or markets for either. Elections, culture, crypto and golf do have "
  "live markets.",
  "An empty Gas page would look like a bug rather than a fact about the demo exchange.",
  "The collector records <code>series_in_catalog</code> and <code>series_with_live_markets</code> per "
  "topic, and the Gas page states &#8220;catalogue only &#8212; 2 series exist, none has a live market&#8221;. "
  "Gas stays in scope and populates automatically when the demo exchange lists those markets.",
  "api-reference/market/get-series-list"),
 ("F13", "Sharp-jump cause cannot be determined from the API",
  "The dashboard now marks price moves \u2265 $0.10 between consecutive points on the live chart and "
  "links each to the market\u2019s page on Kalshi, plus a clearly labelled \u201cpossible context\u201d "
  "search link. But the Trade API returns price and volume only \u2014 no news, no event, no "
  "explanation for why a contract moved.",
  "A reader could mistake a jump marker for a confirmed causal event.",
  "Each jump row links to the market on Kalshi (where traders can see discussion) and is tagged "
  "<span class=\"pill flag\">cause unverified</span>; the search link is labelled \u201cnot an official "
  "source\u201d. Nothing is inferred. Raised as verification row on pages/verification.html and as "
  "suggestion S9 on pages/suggestions.html.",
  "api-reference/market/get-markets|api-reference/market/get-trades"),
 ("F14", "Browser-side private-key prompts are unsafe on a public static host",
  "Session 6d75123b\u2019s <code>live/trading.html</code> Mode B asked the user to paste a demo "
  "private key into the page, and <code>assets/app.js</code> still carried orphaned WebCrypto "
  "signing code wired to ids no page contains. PR #6 (session 22b4f0cb) raised this and was "
  "stale; session bdb4d2d0 took it over under the 60-minute rule.",
  "A public GitHub Pages deployment cannot protect a pasted signing key; any script on the page "
  "could read it. This conflicts with the README policy that signing keys belong only in "
  "repository secrets behind the three execution gates.",
  "Integration fix (2026-11-20): the Mode B credential form is disabled on the deployed copy with "
  "a notice pointing at the gated Actions path (<code>tools/execute_strategy.py</code>) and the "
  "<code>server/</code> backend; the orphaned signing code was removed from "
  "<code>assets/app.js</code>. Mode A paper trading and the request builder are unchanged. "
  "Reversible by removing the <code>disabled</code> attributes when serving privately. "
  "Cross-scope request logged for session 6d75123b in COORDINATION.md.",
  "getting_started/api_keys"),
 ("F22", "The high-ROI model is a transparent local heuristic, not an official measure",
  "The Live Alerts page (alerts.html) filters one chat by a model score computed in the browser: "
  "<code>score = 0.40&#183;liquidity + 0.30&#183;tightness + 0.30&#183;price action</code>, cutoff 0.60. "
  "The Trade API exposes no ROI, edge or expected-return field (see the Market schema on Get Markets), "
  "so the score is a labelled heuristic over official fields only (volume_fp, yes_bid/yes_ask, "
  "and the count of observed $0.10+ swings this session).",
  "A reader could mistake the model filter for a predictive, backtested or official ROI measure.",
  "The formula and cutoff are printed beside the chat, every input is a visible column in the model "
  "table, and the page states plainly that it is not financial advice and makes no outcome prediction. "
  "Nothing is inferred from outside the API; detections themselves use only official prices.",
  "api-reference/market/get-markets"),
]


def build_flagged() -> None:
    def fsrc(p):
        if isinstance(p, (list, tuple)):
            return ", ".join(fsrc(x) for x in p)
        if "|" in p:  # multi-source path list (session bdb4d2d0 rows)
            return ", ".join(fsrc(x) for x in p.split("|"))
        if p.startswith("http"):
            return f'<a href="{p}" target="_blank" rel="noopener">{p.split("//", 1)[1].split("/", 1)[0]}</a>'
        return src(p, p.rsplit("/", 1)[-1])
    rows = [[f[0], f"<b>{f[1]}</b><br>{f[2]}", f[3], f[4], fsrc(f[5]),
             '<span class="pill flag">open for review</span>'] for f in FLAGGED]
    body = """
<h1>Flagged for review</h1>
<p class="lead">Irregularities, gaps and judgement calls found while building this site. None of
these blocked publication; each is stated with its impact, the mitigation actually in place, and
the official source that frames it. Review this page first if something on the dashboard looks
wrong.</p>
""" + table(["#", "Finding", "Why it matters", "Mitigation in place", "Source", "Status"], rows) + """
<h2>How to spot these in the data</h2>
<ul class="clean">
<li><b>F2</b>: any figure tagged <span class="pill flag">est.</span> is computed, not returned.</li>
<li><b>F3</b>: the ask column says <i>derived</i>; the raw response has only bids.</li>
<li><b>F6</b>: the portfolio page says \u201cnot configured\u201d; it is not a zero balance.</li>
<li><b>F11</b>: the chart notes whether it is plotting a derived quoted mid or a traded price.</li>
<li><b>F12</b>: the Gas page says \u201ccatalogue only\u201d instead of showing an unexplained empty table.</li>
<li><b>F14</b>: no page on the deployed site accepts a private key; the one form that did is
  disabled behind a notice that names the gated Actions path.</li>
<li><b>F13</b>: sharp jumps \u2265 $0.10 are marked with red vertical markers on the chart and listed in
  a table below it, each tagged \u201ccause unverified\u201d \u2014 the Trade API returns price and volume
  only, never the news or event behind a move.</li>
<li><b>F8</b>: the dashboard header shows the snapshot time and age, so stale data is visible.</li>
<li><b>F9</b>: compare the in-scope series list per topic against the unclassified list in
  <code>data/snapshot.json</code>.</li>
</ul>
"""
    body += """
<h2>Integration findings (session 5330bffb, 2026-11-20)</h2>
<p class="lead">Findings from the final integration pass, kept beside the F-rows above. Where a
finding matches an F-row it links to it instead of repeating (G-5 = F10, G-11 = F4).</p>
<div class="tablewrap"><table><thead><tr><th>#</th><th>Irregularity / gap</th><th>Impact</th><th>Action taken / status</th><th>Source</th></tr></thead><tbody>
<tr><td>G-1</td><td>Browser WebSocket streaming is impossible: the handshake requires signed <code>KALSHI-ACCESS-*</code> headers, which browsers cannot set.</td><td>Seconds-level data can only come from REST polling or a backend proxy.</td><td>Dashboard polls REST every 15s and renders committed candlesticks (1-min/24h, 60-min/7d). <a href="../dashboard/flagged.html">dashboard U2</a></td><td><a href="https://docs.kalshi.com/getting_started/quick_start_websockets">WebSocket quick start</a></td></tr>
<tr><td>G-2</td><td>Browser CORS from the Pages origin &mdash; resolved by observation: a probe with origin <code>https://karagemop466-tech.github.io</code> returned <code>access-control-allow-origin: https://karagemop466-tech.github.io</code>.</td><td>Live fetches from the published site are expected to work.</td><td><b>Closed</b> (2026-11-20T12:12:40Z, recorded in <code>data/cors.json</code>). Snapshot fallback retained as resilience.</td><td><a href="https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=1">probe target</a></td></tr>
<tr><td>G-3</td><td>KXCABALLOTMEASURES results (Prop 42 yes; 43/44/45 no) were reported by session arena-3420a90d; this session's re-check returned an empty market list and no event record.</td><td>The four result values cannot be re-verified right now.</td><td>Values are not entered in any table (blank + flagged, per policy). Provenance kept in COORDINATION.md.</td><td><a href="https://external-api.demo.kalshi.co/trade-api/v2/markets?event_ticker=KXCABALLOTMEASURES">empty response</a></td></tr>
<tr><td>G-4</td><td>KXLTCPERP &ldquo;0.1 LTC&rdquo; has a contract-terms URL missing its file name and <code>null</code> settlement sources/tags.</td><td>No usable contract terms or settlement source.</td><td>Flagged; blank in tables (same class as F10).</td><td><a href="https://external-api.demo.kalshi.co/trade-api/v2/series?category=Crypto&amp;limit=3">Series API</a></td></tr>
<tr><td>G-6</td><td>KXNEARY tags include <code>Crypto</code> and frequency is hourly while its title is about the Fed chair; settlement lists four political-news sources.</td><td>Topic mapping and frequency contradict the contract subject.</td><td>Flagged; rows kept with the conflict noted.</td><td><a href="https://external-api.demo.kalshi.co/trade-api/v2/series?category=Crypto&amp;limit=3">Series API</a></td></tr>
<tr><td>G-7</td><td><code>assets/app.js</code> at the repo root is dead code (superseded twice); nothing loads it.</td><td>Misleads manual review.</td><td>Left in place (published-URL policy) and marked superseded in the repo review.</td><td><a href="../assets/app.js">file</a></td></tr>
<tr><td>G-9</td><td>Collector CI silently dropped untracked files: <code>git diff --quiet</code> never sees untracked paths, so the first successful collect run was discarded.</td><td>Scheduled data refresh produced nothing.</td><td><b>Fixed</b>: the workflow stages <code>data/</code> before the diff; per-branch concurrency; bounded pagination for demo rate limits.</td><td><a href="../.github/workflows/collect.yml">collect.yml</a></td></tr>
<tr><td>G-10</td><td>Status filter values (unopened/open/paused/closed/settled) differ from the response status values (active/finalized &hellip;) in the same doc.</td><td>Status handling code written from one table fails the other.</td><td>Flagged as a docs inconsistency; collector maps filters literally.</td><td><a href="https://docs.kalshi.com/api-reference/market/get-markets">get-markets</a></td></tr>
</tbody></table></div>
<p class="lead"><b>Multi-tree note (G-8):</b> the site keeps four published trees with cross-links in
every navigation: <a href="../index.html">live dashboard</a> &middot;
<a href="../verified/index.html">verified tables</a> &middot; <a href="../dashboard/index.html">static
dashboard</a> &middot; <a href="../review.html">decision register</a>. Nothing published is removed.
Full prior registers: <a href="../verified/flagged-for-review.html">verified/ (F-01&hellip;F-12, R-F1&hellip;R-F7)</a>
&middot; <a href="../dashboard/flagged.html">dashboard/ (F1&hellip;F15, U1&hellip;U8)</a>.</p>
<p class="lead"><b>Policy:</b> every table row links to an official source. Values that cannot be
confirmed from official sources stay blank and flagged as unverified &mdash; never inferred.</p>
"""
    page(path="pages/flagged.html", title="Flagged for Review", active="flag", body=body,
         desc="Irregularities, gaps and judgement calls flagged for review, with sources.")


# --------------------------------------------------------------------------- repo review
REPO_FINDINGS = [
 ("R1", "repository", "Empty scaffold at the start of this session",
  "Only <code>README.md</code> (one line) and the default Pages workflow existed at commit "
  "<code>6072808</code>.", "No defect.", "Built the site, collector, analysis and executor from scratch."),
 ("R2", "pages", "Earlier build hard-coded scope as keyword matching",
  "The five category pages matched free-text words (<code>gas, gasoline, crude</code>) in titles and "
  "tickers, which mislabels sports/economics markets and misses tag-only series.",
  "Wrong scope: gas and golf are <b>tag</b>-identified, not category- or title-identified.",
  "Replaced with official <code>tags</code>/<code>categories</code> matching; unmapped series listed "
  "for review. See API reference and F9."),
 ("R3", "assets/app.js", "Order placement targeted a removed endpoint",
  "The previous <code>placeOrder()</code> sent <code>POST /portfolio/orders</code> with legacy fields "
  "(<code>side: yes</code>, <code>yes_price</code>, <code>type: limit</code>, "
  "<code>time_in_force: gtc</code>). The docs state those write endpoints are removed and return "
  "<code>410 Gone</code>; <code>gtc</code> is not a valid time-in-force value in V2.",
  "<b>Defect:</b> every order attempt would have failed.",
  "Executor rewritten against <code>POST /portfolio/events/orders</code> with the documented "
  "schema, plus a dry-run default, a notional cap and a scope check."),
 ("R4", "assets/app.js", "Chart relied on browser polling, so history vanished on reload",
  "The earlier chart accumulated points in memory from 15-second polls; any reload reset it, and "
  "nothing was persisted, so a price line could not be reconstructed.",
  "The \u201cprice movement\u201d requirement could not be met across sessions.",
  "Chart now combines official candlesticks (1 min / 1 h / 1 day) with collector tick history "
  "written to <code>data/history.json</code>."),
 ("R5", "assets/app.js", "WebSocket connected without authentication headers",
  "The previous build opened <code>new WebSocket(DEMO_WS)</code> with no "
  "<code>KALSHI-ACCESS-*</code> headers, while the docs state the handshake requires "
  "authentication.", "The socket could never have delivered market data.",
  "WebSocket streaming is no longer presented as working; it is listed as an open decision (S3) "
  "rather than a broken feature."),
 ("R6", "assets/app.js", "Portfolio page displayed raw cents",
  "Balance was rendered as <code>balance/100</code> in JavaScript rather than using the official "
  "<code>balance_dollars</code> fixed-point string.", "Rounding drift and a mislabelled unit.",
  "Uses the official dollar fields and shows <code>portfolio_value</code> separately."),
 ("R7", "pages/*.html", "Every page duplicated the navigation by hand",
  "Fourteen pages each carried a hand-copied nav bar; one missing file broke the whole menu and "
  "the markup had already drifted between pages.", "Maintenance and broken-link risk.",
  "All pages are generated from one layout in <code>tools/build_site.py</code>; a link checker "
  "runs in CI."),
 ("R8", "pages/analysis.html", "Analysis page described methods but computed nothing",
  "The earlier page was a static description of intended categories; no analysis ran.",
  "The requirement to \u201canalyse results and create strategies\u201d was unmet.",
  "Real analysis in <code>tools/analyze.py</code>: cost/payout/realized P&L per fill, five "
  "categorisations, evidence-gated strategy rules."),
 ("R9", "pages/suggestions.html", "Suggestions could be voted on but not justified",
  "Six one-line suggestions with no problem statement, options, trade-off or effort estimate.",
  "A reviewer could not choose a path from them.", "Rewritten as eight reviewed proposals with "
  "problem, options, recommendation, effort/impact/risk and a source link each."),
 ("R10", "repo hygiene", "Generated data was not separated from hand-written content",
  "No distinction between files edited by a human and files written by a machine.",
  "Review risk: a data refresh looked like a code change.", "All machine-written output lives under "
  "<code>data/</code> and every page is regenerated by <code>tools/build_site.py</code>."),
 ("R11", "COORDINATION.md", "Task board claimed 11 done tasks with no verification trail",
  "Rows said \u201cdone\u201d but recorded no per-task sources or verification, and task 11 was left "
  "\u201cin progress\u201d.", "The board could not be audited.", "Rebuilt with per-task scope, a "
  "verification section, a source list and a log; this session recorded its claim before starting."),
 ("R12", "repository (workflows)", "Five workflows write to main, each with its own concurrency group",
  "Concurrency keys are <code>kalshi-refresh</code> (every 10 min), <code>pages-and-data</code> (7,22,37,52 past the hour), <code>collect-kalshi</code> and <code>data-refresh</code> (both at 23 past every second hour), and <code>kalshi-portfolio</code> (hourly at :20). "
  "GitHub serializes only runs that share a key, so these runs can overlap and push to <code>main</code> at the same time. "
  "Source: <a href=\"https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency\" target=\"_blank\" rel=\"noopener\">GitHub docs: control workflow concurrency</a>; the workflow files in <a href=\"https://github.com/karagemop466-tech/Demo2/tree/main/.github/workflows\" target=\"_blank\" rel=\"noopener\">.github/workflows/</a>.",
  "Push races on the same data files; the result depends on which run pushes last.",
  "Flagged. Serializing all data writers under one key is the recommended fix. Not changed here (cross-session files)."),
 ("R13", "repository (workflows)", "Bots push generated data straight to main, and one rebase failure is swallowed",
  "Four workflows push to <code>main</code> without a pull request: <code>pages.yml</code> (line 59), <code>refresh-data.yml</code> (line 88), <code>trade.yml</code> (line 100) and <code>collect.yml</code> (line 46, using <code>GITHUB_REF_NAME</code>). "
  "<code>collect.yml</code> runs <code>git pull --rebase ... || true</code>, so a failed rebase is ignored and the push that follows can fail without any error being raised. "
  "Source: the workflow files in <a href=\"https://github.com/karagemop466-tech/Demo2/tree/main/.github/workflows\" target=\"_blank\" rel=\"noopener\">.github/workflows/</a>.",
  "Generated data bypasses review, which is acceptable only if the data cannot change code. A silent rebase failure can drop a snapshot without notice.",
  "Flagged. The fix is to remove <code>|| true</code> and to fail the job when the rebase fails. Not changed here."),
 ("R14", "scripts/__pycache__", "Compiled bytecode is tracked in git",
  "<code>scripts/__pycache__/check_links.cpython-311.pyc</code> and <code>scripts/__pycache__/fetch_data.cpython-311.pyc</code> are tracked, even though <code>.gitignore</code> lists <code>__pycache__/</code>. "
  "Checked with <code>git ls-files | grep __pycache__</code> on this branch. Source: <a href=\"https://git-scm.com/docs/gitignore\" target=\"_blank\" rel=\"noopener\">git docs: gitignore</a>, NOTES: \u201cTo stop tracking a file that is currently tracked, use <i>git rm --cached</i>\u201d.",
  "Binary noise in diffs; a stale .pyc can differ from the source it claims to compile.",
  "Flagged. Fix: <code>git rm --cached</code> both files. Not changed here (the file belongs to another session\u2019s scope)."),
 ("R15", "tools/, scripts/, instrument-panel/", "Four collectors and three link checkers do overlapping jobs",
  "Collectors: <code>tools/collector.py</code> (refresh-data.yml), <code>tools/collect_kalshi.py</code> (collect.yml), <code>scripts/fetch_data.py</code> (data-refresh.yml), <code>instrument-panel/tools/kalshi_collect.py</code> (pages.yml). "
  "Link checkers: <code>tools/check_links.py</code>, <code>tools/check_live_links.py</code> and <code>scripts/check_links.py</code> (run by pages.yml and linkcheck.yml). "
  "Each collector writes its own files under <code>data/</code>, and all four call the same demo API. Source: the <a href=\"https://github.com/karagemop466-tech/Demo2/tree/main/.github/workflows\" target=\"_blank\" rel=\"noopener\">workflow files</a> and the scripts named.",
  "Four writers hit the same API on different schedules, which uses up the shared rate limit. Two checkers can disagree about the same site.",
  "Flagged. Consolidating on one collector and one checker is the recommended fix. Not changed here."),
 ("R16", "repository (site)", "Eight parallel sites with overlapping pages",
  "The repository publishes the root site, <code>pages/</code>, <code>verified/</code>, <code>dashboard/</code>, <code>site/</code>, <code>instrument-panel/site/</code>, <code>intelligence/</code>, <code>live/</code> and now <code>jumps/</code>. "
  "Each has its own verification, flags and repo-review pages. Source: the <a href=\"https://github.com/karagemop466-tech/Demo2/tree/main\" target=\"_blank\" rel=\"noopener\">repository tree</a> (<code>git ls-files</code> on this branch).",
  "A reader cannot tell which page is current, and a fix in one site does not reach the others.",
  "Flagged. Merging them into one generated site is the top suggestion for the owner. Not changed here."),
 ("R17", "tools/collector.py, tools/execute_strategy.py", "Checked, no defect: trade execution is locked to the demo host",
  "<code>DEMO_REST</code> is the demo base URL (<code>https://external-api.demo.kalshi.co/trade-api/v2</code>). <code>execute_strategy.py</code> posts only to <code>DEMO_REST</code>, and <code>KALSHI_DRY_RUN</code> defaults to 1. "
  "<code>PROD_REST</code> is defined but never used by any script. Source: <a href=\"https://docs.kalshi.com/getting_started/demo_env\" target=\"_blank\" rel=\"noopener\">Kalshi docs: demo environment</a>.",
  "No defect found. The production host cannot be reached by the execution path.",
  "Checked. No change needed."),
 ("R18", "live/trading.html, live/assets/app.js", "A public page asks the user to paste a demo private key",
  "<code>live/trading.html</code> has a form with a Demo API Key ID field and a PEM private-key textarea (<code>#apiPrivateKey</code>). "
  "<code>live/assets/app.js</code> imports that key with <code>crypto.subtle.importKey</code> and signs requests in the browser. "
  "The key is kept in <code>sessionStorage</code> for the tab. The page is published on GitHub Pages, which is public. "
  "The same repo has no matching form on any other page (checked by searching every HTML file for key inputs). "
  "Source: the file contents (<code>live/trading.html</code> lines 101-107; <code>live/assets/app.js</code> lines 663-690); <a href=\"https://docs.kalshi.com/getting_started/api_keys\" target=\"_blank\" rel=\"noopener\">Kalshi docs: API keys</a>.",
  "Anyone who can run script in that page, through an injected script or a browser extension, can read the key from sessionStorage and place demo orders with it. The README discloses this.",
  "Flagged (F21). Recommended: remove the form and keep signed calls on the server side. Not changed here (the page belongs to another session\u2019s scope)."),

 ("R19", "instrument-panel/site/analysis.html, instrument-panel/site/verification.html", "Two source links still contain unfilled template text",
  "<code>analysis.html</code> has an API link with a literal <code>{ticker}</code> and <code>{status}</code> in it. <code>verification.html</code> has one with a literal <code>{category}</code>. "
  "Neither link can open a real market or series. Found by <code>tools/check_live_links.py</code> and confirmed by reading the two files. "
  "Source: <a href=\"https://github.com/karagemop466-tech/Demo2/blob/main/instrument-panel/site/analysis.html\" target=\"_blank\" rel=\"noopener\">analysis.html</a>, <a href=\"https://github.com/karagemop466-tech/Demo2/blob/main/instrument-panel/site/verification.html\" target=\"_blank\" rel=\"noopener\">verification.html</a>, and <a href=\"https://docs.kalshi.com/getting_started/demo_env\" target=\"_blank\" rel=\"noopener\">Kalshi docs: demo environment</a> for the base URL those links should use.",
  "A reader who follows the source link for that row lands on an invalid request, so the row is not verifiable from the page.",
  "Flagged. Fix: replace each placeholder with the real value from the row, or remove the link. Not changed here (cross-session files)."),
 ("R20", "README.md", "Unresolved merge-conflict markers were committed to main",
  "On <code>origin/main</code>, <code>README.md</code> held six conflict markers (<code>&lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD</code>, <code>=======</code>, <code>&gt;&gt;&gt;&gt;&gt;&gt;&gt; origin/main</code>), so both sides of two sections were in the file. "
  "Checked with <code>git show origin/main:README.md | grep -n</code>. Source: <a href=\"https://github.com/karagemop466-tech/Demo2/commit/6a9aecb\" target=\"_blank\" rel=\"noopener\">origin/main at 6a9aecb</a>.",
  "The rendered README shows both versions of a section, and the markers are a sign that a merge was not finished.",
  "Fixed in session 3371a533 by keeping both sides in order (no text removed). A check for leftover markers should be added to CI."),
]


def build_repo_review() -> None:
    rows = [[f[0], f"<code>{f[1]}</code>", f"<b>{f[2]}</b><br>{f[3]}", f[4], f[5]] for f in REPO_FINDINGS]
    body = """
<h1>Repo review \u2014 line by line</h1>
<p class="lead">What was in this repository before this session, what was wrong with it, and what
was changed. Findings are ordered by severity: R3, R4, R5 and R6 are defects that prevented a
requested feature from working at all.</p>
<div class="notice bad"><b>Most serious finding (R3).</b> The previously published build sent every
demo order to <code>POST /portfolio/orders</code>. The official documentation states that path has
been removed and returns <code>410 Gone</code>, so trade execution could not have worked. The
implementation now targets <code>POST /portfolio/events/orders</code>.</div>
""" + table(["#", "File / area", "Finding", "Impact", "Disposition"], rows) + """
<h2>What changed in this session</h2>
""" + table(["Area", "Before", "After"], [
 ["Data path", "Browser-only fetch, nothing persisted", "Scheduled collector writes sourced snapshots with an HTTP log"],
 ["Topic scope", "Title keyword matching", "Official series <code>tags</code>/<code>categories</code>, unmapped listed for review"],
 ["Chart", "In-memory points, lost on reload", "Official candlesticks + persisted tick history, 60 s to 7 d windows"],
 ["Liquidity", "Last 10 levels, unlabelled side", "Full depth, ask side explicitly derived and labelled, spread + totals"],
 ["Resolution", "Settled list only", "Dedicated tracker with result, settlement value, timestamp and rules per market"],
 ["Portfolio", "Raw cents, no analysis", "Official dollar fields, positions, fills, executions, five-way categorisation"],
 ["Execution", "Removed endpoint (410)", "Documented V2 endpoint, dry-run default, notional cap, scope check"],
 ["Suggestions", "Six unexplained one-liners", "Eight reviewed proposals with options, trade-offs and sources"],
 ["Verification", "List of claims without method", "Claim / source / how-it-was-checked / status, plus the live API log"],
 ["Navigation", "Hand-copied on 14 pages", "Generated from one layout, checked in CI"],
]) + """
<h2>Checks run before publishing</h2>
<ul class="clean">
<li><b>Link check:</b> every internal <code>href</code> resolves to a file that exists; external
  links are checked for well-formed URLs.</li>
<li><b>Python:</b> all collector, analysis and executor modules compile, and the analysis maths is
  exercised on a synthetic fixture with known expected values.</li>
<li><b>Data guard:</b> the collector workflow fails rather than committing an empty snapshot.</li>
<li><b>Secrets:</b> no credential is ever written to the repository; keys exist only as Actions
  secrets.</li>
</ul>
"""
    body += """
<h2>Integration additions (session 5330bffb, 2026-11-20)</h2>
<p class="lead">PR #3 additions reviewed line by line at the time (branch <code>arena-9adcf55a-demo2</code>,
commit <code>e3f65782</code>): all 178 declared "live URLs" were relative links that resolve; the
snapshot parses as valid JSON (22 rows). Findings recorded then: KXBTC26H1420 duplicated across
rows; <code>assets/app.js</code> dead (flagged G-7); package.json referenced a missing
<code>server/index.js</code> (since fixed &mdash; the server exists and its npm tests pass 8/8);
<code>collect.py</code> and <code>scripts/check_links.py</code> kept as archives (superseded).
The full file-by-file inventory with links is preserved in the repo history and the
<a href="../COORDINATION.md">coordination record</a>.</p>
"""
    page(path="pages/repo-review.html", title="Repo Review", active="repo", body=body,
         desc="Line-by-line repository review with defects and dispositions.")


# --------------------------------------------------------------------------- sources
SOURCES = [
 ("Kalshi API documentation home", DOCS + "/welcome", "entry point for all official API docs"),
 ("API environments and endpoints", DOCS + "/getting_started/api_environments", "REST + WebSocket base URLs, request signing, user hosts"),
 ("Test in the demo environment", DOCS + "/getting_started/demo_env", "demo base URL, mock funds, price warning"),
 ("Quick start: market data", DOCS + "/getting_started/quick_start_market_data", "unauthenticated endpoints, order-book shape"),
 ("Quick start: authenticated requests", DOCS + "/getting_started/quick_start_authenticated_requests", "headers, pre-sign string, RSA-PSS/Ed25519"),
 ("API keys", DOCS + "/getting_started/api_keys", "key creation, scopes, authentication errors"),
 ("Rate limits and tiers", DOCS + "/getting_started/rate_limits", "token buckets, 429 behaviour, WS connection limits"),
 ("Pagination", DOCS + "/getting_started/pagination", "cursor rules, per-endpoint limits, /series not paginated"),
 ("Fixed-point representation", DOCS + "/getting_started/fixed_point_migration", "<code>*_dollars</code> and <code>*_fp</code> precision"),
 ("Historical data", DOCS + "/getting_started/historical_data", "live vs archived partitions"),
 ("Market settlement", DOCS + "/getting_started/market_settlement", "how outcomes are determined"),
 ("Quick start: WebSockets", DOCS + "/getting_started/quick_start_websockets", "channels, handshake authentication"),
 ("Get Series List", DOCS + "/api-reference/market/get-series-list", "tags and categories used for topic scope"),
 ("Get Events", DOCS + "/api-reference/events/get-events", "event records and nested markets"),
 ("Get Markets", DOCS + "/api-reference/market/get-markets", "prices, volume, open interest, result"),
 ("Get Market Orderbook", DOCS + "/api-reference/market/get-market-orderbook", "bid-only book, depth parameter"),
 ("Get Market Candlesticks", DOCS + "/api-reference/market/get-market-candlesticks", "OHLC, period intervals, 5,000-period cap"),
 ("Get Trades", DOCS + "/api-reference/market/get-trades", "trade-level data"),
 ("Get Balance", DOCS + "/api-reference/portfolio/get-balance", "balance and portfolio value"),
 ("Get Positions", DOCS + "/api-reference/portfolio/get-positions", "exposure and realized P&L"),
 ("Get Fills", DOCS + "/api-reference/portfolio/get-fills", "fill-level record"),
 ("Create Order (V2)", DOCS + "/api-reference/orders/create-order-v2", "current write path; legacy 410"),
 ("Get Exchange Status", DOCS + "/api-reference/exchange/get-exchange-status", "exchange and shard status"),
 ("Kalshi demo UI", "https://demo.kalshi.co/", "where a demo account and demo API keys are created"),
]
LIVE = [
 ("Demo exchange status", "https://external-api.demo.kalshi.co/trade-api/v2/exchange/status"),
 ("Demo series list (unfiltered)", "https://external-api.demo.kalshi.co/trade-api/v2/series"),
 ("Demo series tagged Gas", "https://external-api.demo.kalshi.co/trade-api/v2/series?tags=Gas"),
 ("Demo series tagged Golf", "https://external-api.demo.kalshi.co/trade-api/v2/series?tags=Golf"),
 ("Demo open events with markets", "https://external-api.demo.kalshi.co/trade-api/v2/events?status=open&with_nested_markets=true&limit=2"),
 ("Demo settled markets", "https://external-api.demo.kalshi.co/trade-api/v2/markets?status=settled&limit=5"),
]


def build_sources() -> None:
    body = """
<h1>Sources</h1>
<p class="lead">Official Kalshi documentation only. Third-party SDKs, blogs and API wrappers were
not used as evidence for any claim on this site.</p>
<h2>Documentation pages</h2>
""" + table(["Topic", "Official URL", "Used for"], [
        [t, f'<a href="{u}" target="_blank" rel="noopener">{u}</a>', d] for t, u, d in SOURCES
    ]) + """
<h2>Live API endpoints you can open yourself</h2>
<p class="lead">These are the exact demo requests the collector makes. All are unauthenticated and
can be opened in a browser to check any figure on this site.</p>
""" + table(["What it shows", "Open it"], [
        [t, f'<a href="{u}" target="_blank" rel="noopener">{u}</a>'] for t, u in LIVE
    ]) + """
<h2>Repository evidence</h2>
""" + table(["File", "What it proves"], [
        ["<code>data/snapshot.json</code>", "Every market row plus the HTTP log of the requests that produced them"],
        ["<code>data/resolutions.json</code>", "Settled in-scope markets and their official yes/no result"],
        ["<code>data/portfolio.json</code>", "Demo account balance, positions and fills (or an explicit \u201cnot configured\u201d state)"],
        ["<code>data/analysis.json</code>", "Per-fill cost, payout and realized P&amp;L, plus categorisation"],
        ["<code>data/executions.json</code>", "Every order attempt with its HTTP status, including dry runs"],
        ["<code>tools/collector.py</code>", "The documented endpoints and the exact fields read"],
        ["<code>COORDINATION.md</code>", "Task ownership, claims, verification and the PR/deploy record"],
    ]) + """
<h2>Attribution</h2>
<p class="muted">Kalshi is a registered exchange; all market data belongs to Kalshi. This is an
unaffiliated demonstration project running entirely against the demo environment with mock funds.
Nothing here is investment advice.</p>
"""
    body += """
<h2>Integration source additions (session 5330bffb, 2026-11-20)</h2>
<ul class="clean">
<li>""" + src("getting_started/fixed_point_migration", "Fixed-point migration (price/count strings)") + """</li>
<li>""" + src("api-reference/orders/create-order-v2", "Create Order V2 (required body fields)") + """</li>
<li>""" + src("api-reference/orders/cancel-order-v2", "Cancel Order V2 (auto-routing)") + """</li>
<li>""" + src("getting_started/order_direction", "Order direction (bid &equiv; yes, ask &equiv; no)") + """</li>
<li>""" + src("api-reference/market/get-market-orderbook", "Get Market Orderbook (bracket notation)") + """</li>
<li>""" + src("api-reference/market/get-market-candlesticks", "Get Market Candlesticks") + """</li>
<li>""" + src("getting_started/market_settlement", "Market settlement ($1 per winning contract)") + """</li>
<li><a href="https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=1">Demo API CORS probe target</a> (observed headers recorded in <code>data/cors.json</code>)</li>
<li>Official news outlets named in demo settlement sources: <a href="https://www.reuters.com/">Reuters</a>, <a href="https://apnews.com/">AP</a>, <a href="https://www.cnbc.com/">CNBC</a>, <a href="https://www.politico.com/">Politico</a>, <a href="https://www.bbc.com/news">BBC</a>, <a href="https://www.aljazeera.com/">Al Jazeera</a>, <a href="https://theathletic.com/">The Athletic</a>, <a href="https://www.espn.com/">ESPN</a>, <a href="https://www.foxsports.com/">Fox Sports</a>, <a href="https://www.wsj.com/">WSJ</a>, <a href="https://www.bloomberg.com/">Bloomberg</a>, <a href="https://www.coindesk.com/">CoinDesk</a>, <a href="https://cointelegraph.com/">Cointelegraph</a></li>
<li>Official data/benchmark sources named in demo contract terms: <a href="https://gasprices.aaa.com/">AAA</a>, <a href="https://www.eia.gov/petroleum/gasdiesel/">EIA</a>, <a href="https://www.pgatour.com/">PGA Tour</a>, <a href="https://www.dpworldtour.com/">DP World Tour</a>, <a href="https://livgolf.com/">LIV Golf</a>, <a href="https://www.fifa.com/">FIFA</a>, <a href="https://tezos.com/">Tezos</a></li>
<li>On-chain block explorers named in demo contract terms: <a href="https://etherscan.io/">Etherscan</a>, <a href="https://www.blockchain.com/explorer">Blockchain.com</a>, <a href="https://ethernodes.org/">Ethernodes</a>, <a href="https://beaconcha.in/">Beaconcha.in</a></li>
</ul>
"""
    page(path="pages/sources.html", title="Sources", active="src", body=body,
         desc="Official Kalshi documentation and live demo endpoints used by this site.")


if __name__ == "__main__":
    build_api_reference()
    build_executive_summary()
    build_portfolio()
    build_analysis()
    build_suggestions()
    build_questions()
    build_verification()
    build_flagged()
    build_repo_review()
    build_sources()
    print("content pages built")
