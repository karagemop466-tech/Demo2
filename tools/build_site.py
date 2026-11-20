#!/usr/bin/env python3
"""Builds every HTML page of the site from one source of truth for layout + nav.

Run:  python3 tools/build_site.py
Output: index.html, pages/*.html

Design constraints taken from the brief:
  - clean landing page, subpages by category, simple dashboard feel
  - all findings in tables with a source link on every row
  - blank + "unverified" when a value cannot be confirmed from an official source
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = "https://docs.kalshi.com"

NAV = [
    ("index.html", "Dashboard", "dash"),
    ("pages/executive-summary.html", "Executive Summary", "exec"),
    ("pages/gas.html", "Gas", "gas"),
    ("pages/elections.html", "Elections", "elections"),
    ("pages/culture.html", "Culture", "culture"),
    ("pages/crypto.html", "Crypto", "crypto"),
    ("pages/golf.html", "Golf", "golf"),
    ("verified/index.html", "Verified Data", "verified"),
    ("dashboard/index.html", "Static Dashboard", "static"),
    ("review.html", "Decision Register", "decide"),
    ("rankings.html", "Dollar Rankings", "rank"),
    ("instrument-panel/site/index.html", "Instrument Panel", "inst"),
    ("live/index.html", "Live Console", "live"),
    ("jumps/index.html", "Price Jumps", "jumps"),
    ("pages/resolutions.html", "Resolutions", "res"),
    ("pages/paper-trading.html", "Paper Trades", "paper"),
    ("pages/portfolio.html", "Portfolio", "port"),
    ("pages/analysis.html", "Analysis", "an"),
    ("pages/suggestions.html", "Suggestions", "sug"),
    ("pages/questions.html", "Questions", "q"),
    ("pages/api-reference.html", "API Reference", "api"),
    ("pages/verification.html", "Verification", "ver"),
    ("pages/flagged.html", "Flagged", "flag"),
    ("pages/repo-review.html", "Repo Review", "repo"),
    ("pages/sources.html", "Sources", "src"),
]

# The navigation is grouped so the landing page stays scannable: the five topics first, the
# trading desk next, the registers after that, and the other sessions' published subsites
# last. The grouping is a presentation of NAV, not a second list of links: every entry must
# appear in exactly one group, which the assertion below enforces at build time (a new page
# that is added to NAV but forgotten here fails the build instead of silently vanishing
# from the navigation).
NAV_GROUPS = [
    ("Desk", ["dash", "paper", "res", "rank"]),
    ("Topics", ["gas", "elections", "culture", "crypto", "golf"]),
    ("Registers", ["exec", "ver", "flag", "repo", "src", "q", "sug", "an", "port", "api"]),
    ("Preserved subsites", ["verified", "static", "inst", "live", "jumps", "decide"]),
]


def nav_html(active: str, prefix: str) -> str:
    by_key = {key: (href, label) for href, label, key in NAV}
    missing = [k for _, keys in NAV_GROUPS for k in keys if k not in by_key]
    ungrouped = [k for _, _, k in NAV
                 if k not in {gk for _, keys in NAV_GROUPS for gk in keys}]
    if missing or ungrouped:
        raise SystemExit(
            f"NAV and NAV_GROUPS disagree: missing={missing} ungrouped={ungrouped}"
        )
    items = []
    for group, keys in NAV_GROUPS:
        links = []
        for k in keys:
            href, label = by_key[k]
            cur = ' aria-current="page"' if k == active else ""
            links.append(f'<a href="{prefix}{href}"{cur}>{label}</a>')
        items.append(f'<span class="navgroup">{group}</span>' + "".join(links))
    return (
        '<header class="top"><div class="hbar"><div class="brand">Kalshi <b>Demo</b> Dashboard'
        "<small>demo environment · not real money</small></div>"
        '<button class="navtoggle secondary sm" aria-label="Toggle navigation">Menu</button>'
        '<nav class="main">' + "".join(items) + "</nav></div></header>"
    )


def footer_html(prefix: str) -> str:
    return (
        '<footer class="site"><div class="in">'
        "<div>Kalshi <b>demo</b> environment only · mock funds · no investment advice.</div>"
        f'<div><a href="{prefix}pages/sources.html">Sources</a> · '
        f'<a href="{prefix}pages/verification.html">Verification</a> · '
        f'<a href="{prefix}pages/flagged.html">Flagged for Review</a> · '
        f'<a href="{prefix}pages/repo-review.html">Repo Review</a> · '
        f'<a href="{prefix}monitor/index.html">Read-only Monitor</a></div>'
        "</div></footer>"
    )


def page(*, path: str, title: str, active: str, body: str, extra_js: str = "",
         desc: str = "", body_attrs: str = "") -> None:
    """Write one page. `path` is relative to the repo root."""
    out = ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    depth = len(Path(path).parts) - 1
    prefix = "../" * depth
    html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · Kalshi Demo Dashboard</title>
<meta name="description" content="{desc or 'Live Kalshi demo-market dashboard for gas, elections, culture, crypto and golf, with sourced data and line-by-line verification.'}">
<link rel="stylesheet" href="{prefix}assets/style.css">
</head><body{body_attrs}>
{nav_html(active, prefix)}
<div class="wrap">
{body}
</div>
{footer_html(prefix)}
<script src="{prefix}assets/site.js"></script>
{extra_js}
</body></html>
"""
    out.write_text(html)
    print(f"  wrote {path} ({len(html):,} bytes)")


# --------------------------------------------------------------------------- shared bits
def snapshot_meta() -> dict:
    p = ROOT / "data" / "snapshot.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def meta_bar(s: dict) -> str:
    gen = s.get("generated_at_utc") or ""
    n = (s.get("counts") or {}).get("markets_in_scope", 0)
    auth = "yes" if s.get("authenticated") else "no"
    return (
        '<div class="card tight"><div class="row" style="justify-content:space-between">'
        f'<div class="status" id="staleness">Snapshot <span class="muted">{gen or "none yet"}</span></div>'
        f'<div class="status muted">{n} in-scope markets · API key configured: {auth} · '
        f'source <a href="{DOCS}/getting_started/demo_env">demo environment</a></div>'
        "</div></div>"
    )


# --------------------------------------------------------------------------- dashboard
DASH_BODY = r"""
<h1>Highest-dollar live markets in scope</h1>
<p class="lead">Live Kalshi <b>demo</b> markets for five topics only — <b>gas prices,
elections, culture, crypto, golf</b>. Ranked by <i>estimated</i> dollar volume, charted by
contract price over time, with order-book liquidity at each price, tracked until the market
resolves <b>yes</b> or <b>no</b>.</p>
<div class="startrow">
  <span class="startlabel">Start here</span>
  <span><b>Alert desk</b> below · <b>Topics:</b>
    <a href="pages/gas.html">Gas</a> · <a href="pages/elections.html">Elections</a> ·
    <a href="pages/culture.html">Culture</a> · <a href="pages/crypto.html">Crypto</a> ·
    <a href="pages/golf.html">Golf</a></span>
  <span><b>Desk:</b> <a href="pages/paper-trading.html">Paper Trades</a> ·
    <a href="pages/resolutions.html">Resolutions</a> · <a href="rankings.html">Dollar Rankings</a></span>
  <span><b>Registers:</b> <a href="pages/verification.html">Verification</a> ·
    <a href="pages/flagged.html">Flagged for Review</a> · <a href="pages/sources.html">Sources</a></span>
</div>
<div id="metaBar"></div>
<noscript><div class="notice">JavaScript is required for the live panels. The static
tables on the category, resolution and verification pages still work without it.</div></noscript>

<div class="kpis" id="kpis"></div>

<h2>Live alert desk <span class="muted">— two scrolling chats of sudden price swings</span></h2>
<p class="lead">Every line is an official <code>last_price_dollars</code> move of
<b>&ge; $0.10</b> between two consecutive observations of the same market, in either
direction. The two chats are: <b>all events</b>, and <b>model screen &mdash; high ROI</b>,
the subset that passes a documented heuristic screen. Lines are newest first and scroll
in real time; each one links to the market's own page on Kalshi and keeps tracking it
until the official <code>result</code> (yes/no) lands.</p>
<div class="notice info"><b>What is live, and what is not.</b> The <span class="pill ok">live poll</span>
lines come from a direct poll of the official demo Trade API
(<a href="https://docs.kalshi.com/api-reference/market/get-markets">Get Markets</a>, the documented
<code>tickers=</code> filter) every 20 seconds. The
<span class="pill">snapshot</span> lines come from the collector's own tick history, which is sampled
every 10 minutes &mdash; coarser, and labelled so it is never mistaken for the live stream. The API
returns price and volume only: <b>it does not say what caused a move</b>, so the
&ldquo;possible context&rdquo; link is a news search tagged
<span class="pill flag">not an official source</span>, and the cause stays unverified
(<a href="pages/flagged.html">F13</a>). Demo prices are not real prices
(<a href="pages/flagged.html">F5</a>).</div>
<p class="lead" style="font-size:.88em">Model screen: move &ge; $0.10, entry price &le; $0.45 on
the side the move favours, <code>volume_24h_fp</code> &ge; 100 contracts, closes within 30 days
&mdash; a heuristic over official fields, <b>not a forecast</b>. Potential ROI shown beside a passing
line is the arithmetic payout if the favoured side resolves, not a prediction of the outcome.</p>
<div id="alertStatus" class="chat-head" style="margin-bottom:8px"></div>
<div class="grid two">
  <div class="card" style="display:flex;flex-direction:column;gap:8px">
    <div class="chat-head"><b>All events</b><span id="alertAllCount" class="muted"></span></div>
    <div class="chat" id="alertAll"></div>
  </div>
  <div class="card" style="display:flex;flex-direction:column;gap:8px">
    <div class="chat-head"><b>Model screen &mdash; high ROI</b><span id="alertModelCount" class="muted"></span></div>
    <div class="chat" id="alertModel"></div>
  </div>
</div>

<div class="grid two" style="margin-top:6px">
  <div class="card">
    <h3>Price movement <span class="muted">— X: time, Y: contract price ($)</span></h3>
    <div class="row" style="margin-bottom:8px">
      <div><label for="mktSel">Market</label>
        <select id="mktSel" style="min-width:280px"></select></div>
    </div>
    <div class="row" style="margin-bottom:8px">
      <label class="small" style="margin:0">Window</label>
      <div class="seg" id="winSeg" role="group" aria-label="Chart window">
        <button data-w="60" aria-pressed="false">60 s</button>
        <button data-w="300" aria-pressed="false">5 min</button>
        <button data-w="3600" aria-pressed="true">1 h</button>
        <button data-w="21600" aria-pressed="false">6 h</button>
        <button data-w="86400" aria-pressed="false">24 h</button>
        <button data-w="604800" aria-pressed="false">7 d</button>
      </div>
    </div>
    <div class="row" style="margin-bottom:8px">
      <label class="small" style="margin:0">Series</label>
      <div class="seg" id="fieldSeg" role="group" aria-label="Series to plot">
        <button data-f="mid" aria-pressed="true">Quoted mid <span class="small">(derived)</span></button>
        <button data-f="close" aria-pressed="false">Last trade</button>
        <button data-f="yes_bid_close" aria-pressed="false">Yes bid</button>
        <button data-f="yes_ask_close" aria-pressed="false">Yes ask</button>
      </div>
    </div>
    <div class="chartwrap"><canvas id="chart" class="chart"></canvas></div>
    <div class="legend">
      <span><span class="swatch" style="background:#00c389"></span>contract price, USD per $1 contract (0.00 - 1.00)</span>
      <span id="chartNote" class="muted"></span>
    </div>
    <p class="small muted" style="margin-top:6px">Long windows use official candlesticks
      (<a href="https://docs.kalshi.com/api-reference/market/get-market-candlesticks">Get Market Candlesticks</a>,
      period 1 min / 1 h / 1 day, max 5,000 periods per request). Short windows use the
      collector's own tick history, which is sampled every 10 minutes — a 60-second window
      will legitimately be empty. Nothing is interpolated.</p>
  </div>

  <div class="card">
    <h3>Sharp price moves <span class="muted">— jumps ≥ $0.10 between consecutive price points</span></h3>
    <p class="muted" style="margin-top:0">Each red marker on the chart is a move of $0.10 or more
      between two consecutive points. The API returns price and volume but not the news or event
      behind a move, so the cause is not inferred — each row links to the market's own page on
      Kalshi and is flagged <span class="pill flag">cause unverified</span>. The
      <span class="pill flag">possible context</span> column is only a news-search link that
      <i>may</i> be related; it is not an official source and asserts nothing.</p>
    <div id="jumpTable"></div>
  </div>

  <div class="card">
    <h3>Liquidity <span class="muted">— contracts available at each price</span></h3>
    <p class="small muted" style="margin-top:0">Raw bids from
      <a href="https://docs.kalshi.com/api-reference/market/get-market-orderbook">Get Market Orderbook</a>.
      Kalshi returns <b>yes bids and no bids only</b>; a NO bid at price <i>p</i> is the same
      as a YES ask at <i>1 − p</i>, so the ask side here is <b>derived</b> and labelled
      as such.</p>
    <div id="liqSummary" class="kpis" style="margin:10px 0 4px"></div>
    <div class="grid" style="grid-template-columns:1fr 1fr;gap:10px">
      <div><h3 class="small">YES bids</h3><div id="liqBid"></div></div>
      <div><h3 class="small">YES asks <span class="muted">(derived)</span></h3><div id="liqAsk"></div></div>
    </div>
    <p class="small muted" id="liqNote"></p>
  </div>
</div>

<h2>Markets ranked by estimated dollar volume</h2>
<div class="notice info"><b>What "highest dollar amount" means here.</b> The Trade API has no
  single dollar-volume field. Every row therefore shows the raw official fields
  (<code>volume_fp</code>, <code>open_interest_fp</code>, <code>last_price_dollars</code>) and
  one clearly-labelled <b>estimate</b>: <code>volume_fp × last_price_dollars</code>.
  Rows missing lifetime <code>volume_fp</code> (top-event lead markets) show a blank there and a
  labelled 24h estimate beside it. Coverage note: the snapshot unions every source-linked market
  set and is <b>not a complete enumeration</b> of the exchange (see the <code>adapter.coverage</code>
  field in <code>data/snapshot.json</code>). See
  <a href="pages/flagged.html">Flagged F2</a> and <a href="pages/questions.html">Q1</a>.</div>
<div class="row" style="margin:10px 0">
  <div><label for="topicFilter">Topic</label>
    <select id="topicFilter"><option value="">All in-scope</option>
      <option value="gas">Gas</option><option value="elections">Elections</option>
      <option value="culture">Culture</option><option value="crypto">Crypto</option>
      <option value="golf">Golf</option></select></div>
  <div><label for="sortSel">Sort</label>
    <select id="sortSel">
      <option value="est">est. dollar volume (desc)</option>
      <option value="volume">volume_fp (desc)</option>
      <option value="oi">open_interest_fp (desc)</option>
      <option value="close">close time (soonest)</option>
    </select></div>
  <div><label for="qBox">Filter text</label><input id="qBox" placeholder="ticker or title"></div>
</div>
<div id="mktTable"></div>

<h2>Tracked until resolution</h2>
<p class="lead">Live rows stay on this page until Kalshi settles the market, at which point the
official <code>result</code> field (<code>yes</code>/<code>no</code>) moves the row to
<a href="pages/resolutions.html">Resolutions</a>. Recently settled in-scope markets:</p>
<div id="resolvedMini"></div>
"""

DASH_JS = r"""
<script src="../assets/alerts.js"></script>
<script>
(async function(){
  const $ = id => document.getElementById(id);
  let state = { window: 3600, field: 'mid', ticker: null, snap:null, filtered:[] };

  try{
    const snap = await KR.snapshot();
    state.snap = snap;
    KR.staleness($('staleness'), snap.generated_at_utc);
    $('metaBar').innerHTML = '';
    const c = snap.counts || {};
    const pt = c.per_topic || {};
    $('kpis').innerHTML = `
      <div class="kpi-card"><div class="k">In-scope live markets</div>
        <div class="v">${KR.num(c.markets_in_scope,0)}</div>
        <div class="s">gas ${pt.gas||0} · elections ${pt.elections||0} · culture ${pt.culture||0} · crypto ${pt.crypto||0} · golf ${pt.golf||0}</div></div>
      <div class="kpi-card"><div class="k">Resolved (tracked) </div>
        <div class="v">${KR.num(c.resolved_in_scope,0)}</div>
        <div class="s">official yes/no outcomes</div></div>
      <div class="kpi-card"><div class="k">Series mapped</div>
        <div class="v">${KR.num(c.series_index,0)}</div>
        <div class="s">via official tags + categories</div></div>
      <div class="kpi-card"><div class="k">Order books pulled</div>
        <div class="v">${KR.num(c.orderbooks,0)}</div>
        <div class="s">top markets by est. volume</div></div>
      <div class="kpi-card"><div class="k">Exchange</div>
        <div class="v ${(snap.exchange_status||{}).response && snap.exchange_status.response.exchange_active ? 'ok':'warn'}">${(snap.exchange_status||{}).response && snap.exchange_status.response.exchange_active ? 'active':'see log'}</div>
        <div class="s">demo /exchange/status</div></div>`;

    // market select: ranked list
    const rows = (snap.markets||[]).slice().sort((a,b)=>(b.est_dollar_volume||0)-(a.est_dollar_volume||0));
    state.filtered = rows;
    $('mktSel').innerHTML = rows.slice(0,80).map(m=>{
      const t = m.market_title || m.market_ticker;
      const short = t.length>70 ? t.slice(0,68)+'…' : t;
      return `<option value="${KR.esc(m.market_ticker)}">[${KR.esc(m.topic)}] ${KR.esc(short)}</option>`;
    }).join('');
    state.ticker = rows.length ? rows[0].market_ticker : null;
    if(state.ticker) $('mktSel').value = state.ticker;

    renderTable(rows);
    await drawChart();
    await renderLiquidity();
    renderResolved(snap.resolutions||[]);
  }catch(e){
    $('kpis').innerHTML = `<div class="notice bad">Data snapshot could not be loaded: ${KR.esc(e.message)}.
      The snapshot is produced by <code>.github/workflows/refresh-data.yml</code>; if this is the first
      run, wait for the workflow (Actions → “Refresh Kalshi demo data”). No values are invented.</div>`;
  }

  function renderTable(rows){
    const topic = $('topicFilter').value, q = $('qBox').value.trim().toLowerCase();
    let r = rows.filter(m=>(!topic||m.topic===topic) &&
      (!q || (m.market_ticker+' '+(m.market_title||'')).toLowerCase().includes(q)));
    const s = $('sortSel').value;
    r.sort((a,b)=>{
      if(s==='volume') return (parseFloat(b.volume_fp)||0)-(parseFloat(a.volume_fp)||0);
      if(s==='oi') return (parseFloat(b.open_interest_fp)||0)-(parseFloat(a.open_interest_fp)||0);
      if(s==='close') return String(a.close_time||'').localeCompare(String(b.close_time||''));
      return (b.est_dollar_volume||0)-(a.est_dollar_volume||0);
    });
    KR.renderTable($('mktTable'), [
      {label:'#', get:(m)=>rows.indexOf(m)+1, num:true},
      {label:'Topic', get:(m)=>KR.topicPill(m.topic)},
      {label:'Market', get:(m)=>`<b>${KR.esc(m.market_title||m.market_ticker)}</b><br><span class="muted small">${KR.esc(m.market_ticker)}</span>`},
      {label:'Last $', num:true, get:(m)=>KR.usd(m.last_price_dollars,2)},
      {label:'Yes bid', num:true, get:(m)=>KR.usd(m.yes_bid_dollars,2)},
      {label:'Yes ask', num:true, get:(m)=>KR.usd(m.yes_ask_dollars,2)},
      {label:'Volume', num:true, get:(m)=>KR.num(m.volume_fp,0)},
      {label:'Open int.', num:true, get:(m)=>KR.num(m.open_interest_fp,0)},
      {label:'Est. $ volume', num:true, get:(m)=>`${KR.usd(m.est_dollar_volume,0)} <span class="pill flag">est.</span>`},
      {label:'Closes', get:(m)=>`<span class="small">${KR.when(m.close_time)}</span>`},
      {label:'Source', get:(m)=>KR.link(m.market_url,'Kalshi')+' · <a href="https://docs.kalshi.com/api-reference/market/get-markets" target="_blank" rel="noopener">API</a>'}
    ], r.slice(0,200), 'No markets match this filter in the current snapshot.');
  }

  async function drawChart(){
    if(!state.ticker) return;
    const snap = state.snap;
    const per = (snap.candles||{})[state.ticker] || {};
    let intervalKey = '1m';
    if(state.window > 3600) intervalKey = '1h';
    if(state.window > 86400) intervalKey = '1d';
    // pick the candle set whose period best matches the window
    if(state.window <= 3600) intervalKey='1m'; else if(state.window<=86400) intervalKey='1h'; else intervalKey='1d';
    const cset = (per[intervalKey]||{}).candles || [];
    let hist = [];
    try{ const h = await KR.history(); hist = ((h.points||{})[state.ticker]||[]); }catch(e){}
    const fieldMap = {mid:'derived_mid', close:'close_dollars', yes_bid_close:'yes_bid_close', yes_ask_close:'yes_ask_close'};
    const candles = cset.map(c=>({ts:c.ts, close_dollars:c.close, yes_bid_close:c.yes_bid_close,
                                  yes_ask_close:c.yes_ask_close, derived_mid:c.derived_mid}));
    const series = KR.buildSeries(candles, hist, fieldMap[state.field])
      .filter(p=>p.t >= Date.now()-state.window*1000 && p.t <= Date.now()+60000);
    const jumps = KR.detectJumps(series, 0.10);
    KR.drawChart(document.getElementById('chart'), series, {
      spanSeconds: state.window,
      jumps: jumps,
      emptyMessage: state.window<=300
        ? 'No ticks inside this window yet. The collector samples every 10 minutes, so a 60-second or 5-minute window only fills when a run has just completed.'
        : 'No price points in this window. Candlestick price objects are empty in periods with no trade - try the quoted-mid series or a longer window.'
    });
    const srcCount = series.filter(p=>p.src==='candle').length, tickCount = series.length-srcCount;
    const label = state.field==='mid' ? 'quoted mid (derived from official bid/ask closes)'
      : state.field==='close' ? 'last traded price - empty in periods with no trade'
      : state.field==='yes_bid_close' ? 'yes bid close' : 'yes ask close';
    $('chartNote').innerHTML = `${series.length} points · ${tickCount} collector ticks + ${srcCount} candlesticks `
      + `(period ${intervalKey==='1m'?'1 min':intervalKey==='1h'?'1 h':'1 day'}) · plotting <b>${label}</b>`
      + (jumps.length ? ` · ${jumps.length} sharp move${jumps.length!==1?'s':''} ≥ $0.10` : '');

    const m = (state.snap.markets||[]).find(x=>x.market_ticker===state.ticker) || {};
    const ctxQ = encodeURIComponent((m.market_title||m.market_ticker||'Kalshi market') + ' Kalshi');
    KR.renderTable($('jumpTable'), [
      {label:'When (UTC)', get:j=>`<span class="small">${KR.when(new Date(j.toTime).toISOString())}</span>`},
      {label:'From → To', num:true, get:j=>`${KR.usd(j.fromV,4)} → ${KR.usd(j.toV,4)}`},
      {label:'Change', num:true, get:j=>(j.change>0?'▲ ':'▼ ')+KR.usd(Math.abs(j.change),4)},
      {label:'Direction', get:j=>`<span class="pill ${j.dir==='up'?'up':'down'}">${j.dir}</span>`},
      {label:'Market', get:j=>`<b>${KR.esc(m.market_title||m.market_ticker||'—')}</b><br><span class="muted small">${KR.esc(m.market_ticker||'—')}</span>`},
      {label:'Source', get:j=>KR.link(m.market_url||'','Kalshi market')+' <span class="pill flag">cause unverified</span>'},
      {label:'Possible context (unverified)', get:j=>`<a href="https://news.google.com/search?q=${ctxQ}" target="_blank" rel="noopener">news search</a> <span class="pill flag">not an official source</span>`}
    ], jumps, 'No sharp moves (≥ $0.10 between consecutive points) in this window. A blank table means the price moved in smaller steps — nothing is inferred.');
  }

  async function renderLiquidity(){
    const snap = state.snap, ob = (snap.orderbooks||{})[state.ticker];
    if(!ob || ob.error){ $('liqSummary').innerHTML=''; $('liqBid').innerHTML='<div class="empty">No order book in this snapshot.</div>'; $('liqAsk').innerHTML=''; $('liqNote').textContent = ob&&ob.error?('Order book request failed: '+ob.error):''; return; }
    $('liqSummary').innerHTML = `
      <div class="kpi-card"><div class="k">Best yes bid</div><div class="v">${KR.usd(ob.best_yes_bid,2)}</div><div class="s">raw field</div></div>
      <div class="kpi-card"><div class="k">Best yes ask</div><div class="v">${KR.usd(ob.best_yes_ask_derived,2)}</div><div class="s">derived from no bids</div></div>
      <div class="kpi-card"><div class="k">Spread</div><div class="v">${KR.usd(ob.spread_derived,3)}</div><div class="s">ask − bid</div></div>`;
    const fmt = a => KR.renderTable(null, [], []) || '';
    KR.renderTable($('liqBid'), [
      {label:'Price', num:true, get:r=>KR.usd(r[0],2)},
      {label:'Contracts', num:true, get:r=>KR.num(r[1],2)}
    ], (ob.yes_bids||[]).slice(0,12).map(r=>({0:r[0],1:r[1],_r:r})).map(x=>({...x, 0:x[0],1:x[1]})), 'No bids.');
    // simple manual render to keep array access obvious
    $('liqBid').innerHTML = tableOf('Yes bid', ob.yes_bids||[], 'No bids resting.');
    $('liqAsk').innerHTML = tableOf('Yes ask (derived)', ob.derived_yes_asks||[], 'No asks (no NO bids resting).');
    $('liqNote').innerHTML = `Total resting: <b>${KR.num(ob.yes_bid_contracts,2)}</b> contracts bid · <b>${KR.num(ob.derived_ask_contracts,2)}</b> offered. Request: <code>${KR.esc(ob.raw_request||'')}</code>`;
  }
  function tableOf(label, arr, empty){
    if(!arr.length) return `<div class="empty">${empty}</div>`;
    return '<div class="tablewrap"><table><thead><tr><th>Price</th><th class="num">Contracts</th></tr></thead><tbody>'+
      arr.slice(0,12).map(r=>`<tr><td>${KR.usd(r[0],2)}</td><td class="num">${KR.num(r[1],2)}</td></tr>`).join('')+
      '</tbody></table></div>';
  }

  function renderResolved(rows){
    const r = rows.slice().sort((a,b)=>String(b.settlement_ts||'').localeCompare(String(a.settlement_ts||''))).slice(0,12);
    KR.renderTable($('resolvedMini'), [
      {label:'Topic', get:m=>KR.topicPill(m.topic)},
      {label:'Market', get:m=>`<b>${KR.esc(m.title||m.market_ticker)}</b><br><span class="muted small">${KR.esc(m.market_ticker)}</span>`},
      {label:'Result', get:m=>KR.resultPill(m.result)},
      {label:'Settlement $', num:true, get:m=>KR.usd(m.settlement_value_dollars,2)},
      {label:'Settled (UTC)', get:m=>`<span class="small">${KR.when(m.settlement_ts)}</span>`},
      {label:'Source', get:m=>`<a href="https://docs.kalshi.com/api-reference/market/get-markets" target="_blank" rel="noopener">Get Markets</a>`}
    ], r, 'No resolved in-scope markets in the current snapshot yet.');
  }

  // events
  $('mktSel').addEventListener('change', async e=>{ state.ticker=e.target.value; await drawChart(); await renderLiquidity(); });
  document.querySelectorAll('#winSeg button').forEach(b=>b.addEventListener('click', async ()=>{
    document.querySelectorAll('#winSeg button').forEach(x=>x.setAttribute('aria-pressed','false'));
    b.setAttribute('aria-pressed','true'); state.window=parseInt(b.dataset.w,10); await drawChart();
  }));
  document.querySelectorAll('#fieldSeg button').forEach(b=>b.addEventListener('click', async ()=>{
    document.querySelectorAll('#fieldSeg button').forEach(x=>x.setAttribute('aria-pressed','false'));
    b.setAttribute('aria-pressed','true'); state.field=b.dataset.f; await drawChart();
  }));
  ['topicFilter','sortSel','qBox'].forEach(id=>$(id).addEventListener('input', ()=>renderTable(state.filtered)));
  window.addEventListener('resize', ()=>{ KR.drawChart(document.getElementById('chart'), [], {}); drawChart(); });

  // Live alert desk: two scrolling chats (all events / model screen). Runs alongside the
  // chart, on official prices only; see assets/alerts.js for the two data streams and the
  // disclosed screen.
  if (window.KR && KR.alerts) KR.alerts.init({ poll: true });
})();
</script>
"""

# --------------------------------------------------------------------------- category
CATEGORY_JS = r"""
<script>
(async function(){
  const TOPIC = document.body.dataset.topic;
  const $ = id => document.getElementById(id);
  try{
    const d = await KR.topic(TOPIC);
    KR.staleness($('staleness'), d.generated_at_utc);
    const ms = d.markets||[];
    // Whether the topic exists in Kalshi's catalogue at all is a different fact from
    // whether it has live markets today. Say both, so "0 live" is never ambiguous.
    let snap = null;
    try { snap = await KR.snapshot(); } catch(e) {}
    const cat = ((snap && snap.topic_catalog) || {})[TOPIC] || {};
    const inCat = cat.series_in_catalog;
    const withLive = (cat.series_with_live_markets || []).length;
    const catBox = $('catNote');
    if(catBox){
      if(inCat === undefined){
        catBox.innerHTML = '<span class="muted">Series-catalogue counts are not in this snapshot yet.</span>';
      } else if(inCat === 0){
        catBox.innerHTML = '<span class="pill flag">no series</span> The API returned no series tagged or categorised for this topic.';
      } else if(withLive === 0){
        catBox.innerHTML = '<span class="pill flag">catalogue only</span> <b>' + inCat + '</b> series exist for this topic in Kalshi&#8217;s catalogue (' +
          (cat.series_tickers||[]).slice(0,6).map(t=>'<code>'+KR.esc(t)+'</code>').join(' ') +
          ') but <b>none has a live market in the demo environment</b> right now. That is an absence of markets, not a data failure.';
      } else {
        catBox.innerHTML = '<span class="pill ok">live</span> <b>' + withLive + '</b> of <b>' + inCat + '</b> catalogued series for this topic have live markets in the demo environment.';
      }
    }
    const highest = ms.slice().sort((a,b)=>(b.est_dollar_volume||0)-(a.est_dollar_volume||0));
    const res = (d.resolutions||[]);
    const live = ms.length, settled = res.length;
    const yesN = res.filter(r=>(r.result||'')==='yes').length;
    const noN = res.filter(r=>(r.result||'')==='no').length;
    $('kpis').innerHTML = `
      <div class="kpi-card"><div class="k">Live markets</div><div class="v">${live}</div><div class="s">status=open</div></div>
      <div class="kpi-card"><div class="k">Resolved</div><div class="v">${settled}</div><div class="s">yes ${yesN} · no ${noN}</div></div>
      <div class="kpi-card"><div class="k">Largest est. $ volume</div>
        <div class="v">${highest.length?KR.usd(highest[0].est_dollar_volume,0):'—'}</div>
        <div class="s">${highest.length?KR.esc((highest[0].market_title||'').slice(0,48)):'no markets'}</div></div>
      <div class="kpi-card"><div class="k">Top 3 est. $ volume</div>
        <div class="v">${KR.usd(highest.slice(0,3).reduce((s,m)=>s+(m.est_dollar_volume||0),0),0)}</div>
        <div class="s">sum of three largest</div></div>`;

    KR.renderTable($('liveTable'), [
      {label:'#', num:true, get:m=>highest.indexOf(m)+1},
      {label:'Market', get:m=>`<b>${KR.esc(m.market_title||m.market_ticker)}</b><br><span class="muted small">${KR.esc(m.market_ticker)} · series ${KR.esc(m.series_ticker)}</span>`},
      {label:'Last $', num:true, get:m=>KR.usd(m.last_price_dollars,2)},
      {label:'Yes bid / ask', num:true, get:m=>`${KR.usd(m.yes_bid_dollars,2)} / ${KR.usd(m.yes_ask_dollars,2)}`},
      {label:'Contracts at best bid', num:true, get:m=>KR.num(m.yes_bid_size_fp,2)},
      {label:'Contracts at best ask', num:true, get:m=>KR.num(m.yes_ask_size_fp,2)},
      {label:'Volume', num:true, get:m=>KR.num(m.volume_fp,0)},
      {label:'Open int.', num:true, get:m=>KR.num(m.open_interest_fp,0)},
      {label:'Est. $ vol', num:true, get:m=>`${KR.usd(m.est_dollar_volume,0)} <span class="pill flag">est.</span>`},
      {label:'Closes', get:m=>`<span class="small">${KR.when(m.close_time)}</span>`},
      {label:'Rules', get:m=>m.rules_primary_head?`<span class="small" title="${KR.esc(m.rules_primary_head)}">${KR.esc(m.rules_primary_head.slice(0,90))}${m.rules_primary_head.length>90?'…':''}</span>`:'—'},
      {label:'Source', get:m=>KR.link(m.market_url,'Kalshi market')}
    ], highest, 'No live markets for this topic in the current snapshot.');

    KR.renderTable($('resTable'), [
      {label:'Result', get:r=>KR.resultPill(r.result)},
      {label:'Market', get:r=>`<b>${KR.esc(r.title||r.market_ticker)}</b><br><span class="muted small">${KR.esc(r.market_ticker)}</span>`},
      {label:'Settlement $', num:true, get:r=>KR.usd(r.settlement_value_dollars,2)},
      {label:'Settled (UTC)', get:r=>`<span class="small">${KR.when(r.settlement_ts)}</span>`},
      {label:'Expiration value', get:r=>KR.dash(r.expiration_value)},
      {label:'Volume', num:true, get:r=>KR.num(r.volume_fp,0)},
      {label:'Source', get:r=>`<a href="https://docs.kalshi.com/api-reference/market/get-markets" target="_blank" rel="noopener">Get Markets (settled)</a>`}
    ], res.slice(0,60), 'No resolved markets for this topic in the current snapshot.');

    const ser = [...new Set(ms.map(m=>m.series_ticker))];
    $('seriesList').innerHTML = ser.length
      ? ser.map(s=>{
          const ex = ms.find(m=>m.series_ticker===s);
          return '<tr><td><code>' + KR.esc(s) + '</code></td><td>' + KR.esc(ex.series_category||'') +
            '</td><td>' + KR.esc((ex.series_categories||[]).join(', ')) +
            '</td><td>' + KR.link(ex.contract_terms_url,'terms') +
            '</td><td>' + KR.link(ex.contract_url,'certification') + '</td></tr>';
        }).join('')
      : '<tr><td colspan="5" class="muted">No series in scope for this topic in the current snapshot.</td></tr>';
  }catch(e){
    $('kpis').innerHTML = `<div class="notice bad">Could not load data/topic-${topicsafe()}.json: ${KR.esc(e.message)}</div>`;
  }
  function topicsafe(){ return TOPIC; }
})();
</script>
"""


def category_page(topic: str, title: str, blurb: str, series_hint: str) -> None:
    body = f"""
<h1>{title}</h1>
<p class="lead">{blurb}</p>
<div id="metaBar"><div class="card tight"><div class="status" id="staleness">Loading snapshot…</div></div></div>
<div class="kpis" id="kpis"></div>
<div class="card tight" style="margin-bottom:14px"><div class="status" id="catNote">Checking the series catalogue…</div></div>

<h2>Live markets — highest estimated dollar volume first</h2>
<p class="muted">Scope rule: a market is in this topic only if its <b>official</b> series record
carries the matching <code>tags</code> or <code>categories</code> value from
<a href="{DOCS}/api-reference/market/get-series-list" target="_blank" rel="noopener">Get Series List</a>
({series_hint}). Nothing is matched on free-text guessing; unmapped series are listed on
<a href="flagged.html">Flagged for Review</a> instead of being silently assigned.</p>
<div id="liveTable"></div>

<h2>Resolved — official yes / no</h2>
<p class="muted">Rows move here when Kalshi sets the official <code>result</code> field. Empty
until a market in this topic settles in the demo environment.</p>
<div id="resTable"></div>

<h2>Series in scope</h2>
<p class="muted">Series tickers actually observed in this topic in the current snapshot, with
their official contract-terms and product-certification links.</p>
<div class="tablewrap"><table>
<thead><tr><th>Series ticker</th><th>Primary category</th><th>Discovery categories</th><th>Contract terms</th><th>Certification</th></tr></thead>
<tbody id="seriesList"><tr><td colspan="5" class="muted">Loading…</td></tr></tbody></table></div>
"""
    page(path=f"pages/{topic}.html", title=title, active=topic, body=body,
         extra_js=CATEGORY_JS, body_attrs=f' data-topic="{topic}"',
         desc=f"{title} markets on Kalshi demo, sourced from the official Trade API.")


# --------------------------------------------------------------------------- resolutions
RES_BODY = r"""
<h1>Resolutions — tracked until the market resolves</h1>
<p class="lead">Every in-scope market Kalshi has settled, with the official outcome
(<b>yes</b> or <b>no</b>), the settlement value, and the settlement timestamp. Rows come
straight from <code>GET /markets?status=settled</code>; the <code>result</code> field is
Kalshi's own, not computed here.</p>
<div id="metaBar"><div class="card tight"><div class="status" id="staleness">Loading…</div></div></div>
<div class="kpis" id="kpis"></div>
<div class="row" style="margin:10px 0">
  <div><label for="topicFilter">Topic</label>
    <select id="topicFilter"><option value="">All</option><option value="gas">Gas</option>
    <option value="elections">Elections</option><option value="culture">Culture</option>
    <option value="crypto">Crypto</option><option value="golf">Golf</option></select></div>
  <div><label for="resFilter">Result</label>
    <select id="resFilter"><option value="">All</option><option value="yes">Yes only</option><option value="no">No only</option></select></div>
</div>
<div id="resTable"></div>
<h2>How resolution is defined</h2>
<div class="tablewrap"><table>
<thead><tr><th>Term</th><th>Meaning</th><th>Source</th></tr></thead><tbody>
<tr><td><code>result</code></td><td>Official market outcome once settled: <code>yes</code> or <code>no</code>; empty while live.</td>
<td><a href="https://docs.kalshi.com/api-reference/market/get-markets" target="_blank" rel="noopener">Get Markets</a></td></tr>
<tr><td><code>settlement_value_dollars</code></td><td>Settlement value of the market in fixed-point dollars.</td>
<td><a href="https://docs.kalshi.com/api-reference/market/get-markets" target="_blank" rel="noopener">Get Markets</a></td></tr>
<tr><td><code>status=settled</code></td><td>The filter used to list resolved markets.</td>
<td><a href="https://docs.kalshi.com/api-reference/market/get-markets" target="_blank" rel="noopener">Get Markets</a></td></tr>
<tr><td>Settlement rules</td><td>How outcomes are determined and positions resolved.</td>
<td><a href="https://docs.kalshi.com/getting_started/market_settlement" target="_blank" rel="noopener">Market Settlement</a></td></tr>
<tr><td>Historical cutoff</td><td>Very old settled markets move to <code>/historical/markets</code>; they are not lost, just partitioned.</td>
<td><a href="https://docs.kalshi.com/getting_started/historical_data" target="_blank" rel="noopener">Historical Data</a></td></tr>
</tbody></table></div>
"""
RES_JS = r"""
<script>
(async function(){
  const $ = id=>document.getElementById(id);
  try{
    const d = await KR.resolutions();
    KR.staleness($('staleness'), d.generated_at_utc);
    const rows = d.resolutions||[];
    const yes = rows.filter(r=>r.result==='yes').length, no = rows.filter(r=>r.result==='no').length;
    const per = {};
    rows.forEach(r=>{ per[r.topic]=per[r.topic]||{yes:0,no:0,total:0}; per[r.topic].total++;
      if(r.result==='yes')per[r.topic].yes++; if(r.result==='no')per[r.topic].no++; });
    $('kpis').innerHTML = `
      <div class="kpi-card"><div class="k">Resolved in scope</div><div class="v">${rows.length}</div><div class="s">all topics</div></div>
      <div class="kpi-card"><div class="k">Resolved YES</div><div class="v ok">${yes}</div><div class="s">result = yes</div></div>
      <div class="kpi-card"><div class="k">Resolved NO</div><div class="v bad">${no}</div><div class="s">result = no</div></div>
      <div class="kpi-card"><div class="k">Topics with data</div><div class="v">${Object.keys(per).length}</div>
        <div class="s">${Object.entries(per).map(([k,v])=>k+': '+v.total).join(' · ')||'none'}</div></div>`;
    function render(){
      const t=$('topicFilter').value, rf=$('resFilter').value;
      const f = rows.filter(r=>(!t||r.topic===t)&&(!rf||r.result===rf));
      KR.renderTable($('resTable'), [
        {label:'Topic', get:r=>KR.topicPill(r.topic)},
        {label:'Result', get:r=>KR.resultPill(r.result)},
        {label:'Market', get:r=>`<b>${KR.esc(r.title||r.market_ticker)}</b><br><span class="muted small">${KR.esc(r.market_ticker)}</span>`},
        {label:'Settlement $', num:true, get:r=>KR.usd(r.settlement_value_dollars,2)},
        {label:'Settled (UTC)', get:r=>`<span class="small">${KR.when(r.settlement_ts)}</span>`},
        {label:'Volume', num:true, get:r=>KR.num(r.volume_fp,0)},
        {label:'Rules', get:r=>r.rules_primary_head?`<span class="small" title="${KR.esc(r.rules_primary_head)}">${KR.esc(r.rules_primary_head.slice(0,80))}…</span>`:'—'},
        {label:'Source', get:r=>`<a href="https://docs.kalshi.com/api-reference/market/get-markets" target="_blank" rel="noopener">settled markets</a>`}
      ], f, 'No resolved markets for this filter in the current snapshot.');
    }
    render();
    ['topicFilter','resFilter'].forEach(id=>$(id).addEventListener('change', render));
  }catch(e){
    $('kpis').innerHTML = `<div class="notice bad">Could not load data/resolutions.json: ${KR.esc(e.message)}</div>`;
  }
})();
</script>
"""


def build_live_pages() -> None:
    snap = snapshot_meta()
    page(path="index.html", title="Live dashboard", active="dash",
         body=meta_bar(snap) + DASH_BODY, extra_js=DASH_JS,
         desc="Live Kalshi demo markets for gas prices, elections, culture, crypto and golf with price charts, liquidity and resolution tracking.")

    category_page(
        "gas", "Gas prices",
        "Fuel-price markets on the Kalshi demo exchange. The in-scope series are the ones tagged "
        "<code>Gas</code>. <b>Verified on 2026-11-20:</b> the demo environment lists "
        "<code>DIESEL</code> (weekly diesel price) and <code>DIESELM</code> (monthly diesel price), "
        "both settled against U.S. Energy Information Administration data, but has <b>no open events "
        "or markets</b> for either series &mdash; so this page shows series, not live prices. That is "
        "a property of the demo exchange, not a gap in the data; the page fills in automatically "
        "when those markets are listed.",
        'tags include <code>Gas</code>; categories are <code>Economics</code> — so category alone '
        'would not find these, which is why the tag is used')
    category_page(
        "elections", "Elections",
        "Election markets: primaries, seat control, party control and international votes. "
        "Official discovery category <code>Elections</code>; each contract lists its own "
        "settlement source (state election boards, AP, county clerks, and so on).",
        'category/categories contain <code>Elections</code>')
    category_page(
        "culture", "Culture",
        "Culture and entertainment markets (awards, music, film, celebrity and similar). "
        "Official discovery category <code>Culture</code>.",
        'category/categories contain <code>Culture</code>')
    category_page(
        "crypto", "Crypto",
        "Crypto price and milestone markets. Official discovery category <code>Crypto</code>; "
        "most series settle against CF Benchmarks indices, which is stated on each series record.",
        'category/categories contain <code>Crypto</code>')
    category_page(
        "golf", "Golf",
        "Golf markets: PGA Tour, DP World Tour, majors, cuts and playoffs. These sit in the "
        "official <code>Sports</code> category, so the <code>Golf</code> tag is what defines "
        "scope here.",
        'tags include <code>Golf</code>; category is <code>Sports</code>, so the tag is the '
        'only reliable signal')

    page(path="pages/resolutions.html", title="Resolutions", active="res",
         body=RES_BODY, extra_js=RES_JS,
         desc="In-scope Kalshi demo markets tracked until resolution, with the official yes/no result.")


if __name__ == "__main__":
    print("building live pages...")
    build_live_pages()
