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
    ("index.html", "Start here", "landing"),
    ("dashboard.html", "Live dashboard", "dash"),
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
    ("pages/resolutions.html", "Resolutions", "res"),
    ("pages/causes.html", "Cause Channels", "cause"),
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


def nav_html(active: str, prefix: str) -> str:
    items = []
    for href, label, key in NAV:
        cur = ' aria-current="page"' if key == active else ""
        items.append(f'<a href="{prefix}{href}"{cur}>{label}</a>')
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
<p class="lead" style="font-size:.95em">All sections: <a href="rankings.html">Dollar Rankings</a> ·
<a href="verified/index.html">Verified rows</a> · <a href="dashboard/index.html">Dashboard</a> ·
<a href="index.html">Start here</a> · <a href="site/index.html">Site</a> · <a href="intelligence/index.html">Intelligence</a> ·
<a href="analysis.html">Analysis (root)</a> · <a href="portfolio.html">Portfolio status (root)</a> ·
<a href="review.html">Review (root)</a></p>
<div id="metaBar"></div>
<noscript><div class="notice">JavaScript is required for the live panels. The static
tables on the category, resolution and verification pages still work without it.</div></noscript>

<div class="kpis" id="kpis"></div>
<h2>Topics at a glance</h2>
<p class="muted">Five topics, kept separate. Each card is that topic's own page; the counts and the
24-hour dollar figures come from the same snapshot as the tables below.</p>
<div class="kpis" id="topicStrip"></div>

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
    <h3>Sharp price moves <span class="muted">— jumps &ge; $0.10 between consecutive price points</span></h3>
    <p class="muted" style="margin-top:0">Each red marker on the chart is a move of $0.10 or more
      between two consecutive points. The API returns price and volume but not the news or event
      behind a move, so the cause is not inferred — each row links to the market's own page on
      Kalshi and is flagged <span class="pill flag">cause unverified</span>. Proposed news links
      (channels to check, not claims of causation) are on
      <a href="{PREFIX}pages/causes.html">Cause channels</a>.</p>
    <div id="jumpTable"></div>
  </div>

  <div class="card">
    <h3>Liquidity over time <span class="muted">— contracts resting, sampled every ~22 s</span></h3>
    <p class="small muted" style="margin-top:0">Kalshi publishes no order-book history, so the
      collector polls <a href="https://docs.kalshi.com/api-reference/market/get-market-orderbook" target="_blank" rel="noopener">Get
      Market Orderbook</a> while it runs. This chart is those polls: total contracts bid and total
      offered on the selected market. A flat line means the book did not change; a gap means no
      sample was taken then. Nothing is interpolated.</p>
    <div class="chartwrap"><canvas id="liqChart" class="chart" style="height:220px"></canvas></div>
    <div class="legend"><span id="liqChartNote" class="muted"></span></div>
  </div>

  <div class="card">
    <h3>Liquidity now <span class="muted">— contracts available at each price</span></h3>
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

<h2>Markets ranked by dollar amount</h2>
<p class="muted" id="rankNote"></p>
<div class="notice info"><b>What "highest dollar amount" means here.</b> The Trade API has no
  single dollar-volume field. Every row therefore shows the raw official fields
  (<code>volume_fp</code>, <code>open_interest_fp</code>, <code>last_price_dollars</code>) and
  one clearly-labelled <b>estimate</b>: <code>volume_fp × last_price_dollars</code>. See
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

    renderTopicStrip(snap);
    renderTable(rows);
    await drawChart();
    await renderLiquidity();
    await drawLiqHistory();
    renderResolved(snap.resolutions||[]);
  }catch(e){
    $('kpis').innerHTML = `<div class="notice bad">Data snapshot could not be loaded: ${KR.esc(e.message)}.
      The snapshot is produced by <code>.github/workflows/refresh-data.yml</code>; if this is the first
      run, wait for the workflow (Actions → “Refresh Kalshi demo data”). No values are invented.</div>`;
  }

  function renderTopicStrip(snap){
    const c = snap.counts || {}, cat = snap.topic_catalog || {}, pt = c.per_topic || {};
    const usd = {};
    (snap.markets||[]).forEach(m=>{ if(m.usd_volume_24h!=null){ usd[m.topic]=(usd[m.topic]||0)+m.usd_volume_24h; } });
    const order = ['gas','elections','culture','crypto','golf'];
    const el = $('topicStrip'); if(!el) return;
    el.innerHTML = order.map(t=>{
      const n = pt[t]||0, live = c.markets_in_scope||0;
      const share = live ? Math.round(100*n/live) : 0;
      const cat1 = cat[t]||{};
      return `<a class="kpi-card" href="{PREFIX}pages/${t}.html" style="text-decoration:none">
        <div class="k">${KR.esc(t[0].toUpperCase()+t.slice(1))}</div>
        <div class="v">${KR.num(n,0)}</div>
        <div class="s">${KR.esc(String(share))}% of live · ${KR.num(cat1.series_read,0)}/${KR.num(cat1.series_in_catalog,0)} series read${
          usd[t]!==undefined ? ` · ${KR.usd(usd[t],2)} traded in 24 h` : ''}</div></a>`;
    }).join('');
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
    KR.renderTable($('jumpTable'), [
      {label:'When (UTC)', get:j=>`<span class="small">${KR.when(new Date(j.toTime).toISOString())}</span>`},
      {label:'From → To', num:true, get:j=>`${KR.usd(j.fromV,4)} → ${KR.usd(j.toV,4)}`},
      {label:'Change', num:true, get:j=>(j.change>0?'▲ ':'▼ ')+KR.usd(Math.abs(j.change),4)},
      {label:'Direction', get:j=>`<span class="pill ${j.dir==='up'?'up':'down'}">${j.dir}</span>`},
      {label:'Market', get:j=>`<b>${KR.esc(m.market_title||m.market_ticker||'—')}</b><br><span class="muted small">${KR.esc(m.market_ticker||'—')}</span>`},
      {label:'Source', get:j=>KR.link(m.market_url||'','Kalshi market')+' <span class="pill flag">cause unverified</span>'}
    ], jumps, 'No sharp moves (≥ $0.10 between consecutive points) in this window. A blank table means the price moved in smaller steps — nothing is inferred.');
  }

  async function drawLiqHistory(){
    const cv = document.getElementById('liqChart'); if(!cv) return;
    const note = $('liqChartNote');
    let h = null;
    try { h = await KR.getJSON("data/liquidity.json"); } catch(e){
      note.textContent = 'data/liquidity.json could not be loaded: ' + e.message; return;
    }
    const m = (h.markets||{})[state.ticker];
    if(!m || !(m.points||[]).length){
      note.textContent = 'No order-book samples for this market in the current snapshot. '
        + 'The collector samples the top markets by dollar volume, one per topic first.';
      KR.drawChart(cv, [], {spanSeconds: 3600, emptyMessage: 'No liquidity samples for this market.'});
      return;
    }
    const bid = m.points.map(p=>({t:p.ts*1000, v:p.yes_bid_contracts, src:'sample'}));
    const ask = m.points.map(p=>({t:p.ts*1000, v:p.derived_ask_contracts, src:'sample'}));
    // drawChart takes one series; draw the bid series and overlay the ask series.
    KR.drawChart(cv, bid, {spanSeconds: 3600, secondary: ask, priceAxis: false, unit: "",
      emptyMessage: 'No liquidity samples.'});
    const last = m.points[m.points.length-1];
    note.innerHTML = `${m.points.length} samples · latest: <b>${KR.num(last.yes_bid_contracts,2)}</b> contracts bid, `
      + `<b>${KR.num(last.derived_ask_contracts,2)}</b> offered (derived from NO bids) · `
      + `best yes bid ${KR.usd(last.best_yes_bid,2)} · best yes ask ${KR.usd(last.best_yes_ask_derived,2)}`;
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
  $('mktSel').addEventListener('change', async e=>{ state.ticker=e.target.value; await drawChart(); await renderLiquidity(); await drawLiqHistory(); });
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
      const read = cat.series_read, failed = cat.series_failed || 0;
      if(inCat === undefined){
        catBox.innerHTML = '<span class="muted">Series-catalogue counts are not in this snapshot yet.</span>';
      } else if(failed){
        catBox.innerHTML = '<span class="pill flag">partial</span> <b>' + KR.num(read,0) + '</b> of <b>' + KR.num(inCat,0) +
          '</b> series were read; <b>' + KR.num(failed,0) + '</b> request(s) failed (rate limit or timeout). ' +
          'A smaller number below can mean a failed request, not an empty topic — see <a href="verification.html">Verification</a>.';
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
      {label:'Rules', get:m=>m.rules_primary?`<span class="small" title="${KR.esc(m.rules_primary)}">${KR.esc(m.rules_primary.slice(0,90))}${m.rules_primary.length>90?'…':''}</span>`:'—'},
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
<h2>Topics at a glance</h2>
<p class="muted">Five topics, kept separate. Each card is that topic's own page; the counts and the
24-hour dollar figures come from the same snapshot as the tables below.</p>
<div class="kpis" id="topicStrip"></div>
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
<h2>Topics at a glance</h2>
<p class="muted">Five topics, kept separate. Each card is that topic's own page; the counts and the
24-hour dollar figures come from the same snapshot as the tables below.</p>
<div class="kpis" id="topicStrip"></div>
<h2>How the events resolved, by topic</h2>
<p class="muted">Counts of settled in-scope markets by the official <code>result</code> field.
A market that never traded still has a result: it settles at $1.00 (yes) or $0.00 (no) regardless
of whether anyone bought it, so it is counted here and flagged on
<a href="flagged.html">Flagged for Review</a> when its volume is zero — a YES on a market nobody
traded is not evidence about anything.</p>
<div id="byTopic"></div>
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
    // per-topic YES/NO breakdown, so "how did events resolve" is answerable at a glance
    const ORDER = ['gas','elections','culture','crypto','golf'];
    const bt = ORDER.map(tp=>{
      const rs = rows.filter(r=>r.topic===tp);
      const yes = rs.filter(r=>r.result==='yes').length;
      const no  = rs.filter(r=>r.result==='no').length;
      const traded = rs.filter(r=>Number(r.volume_fp||0) > 0).length;
      return {topic:tp, resolved:rs.length, yes, no,
              yesShare: (yes+no) ? (yes/(yes+no)) : null,
              traded, untraded: rs.length - traded};
    });
    KR.renderTable($('byTopic'), [
      {label:'Topic', get:r=>KR.topicPill(r.topic)},
      {label:'Settled markets', num:true, get:r=>KR.num(r.resolved,0)},
      {label:'Resolved YES', num:true, get:r=>KR.num(r.yes,0)},
      {label:'Resolved NO', num:true, get:r=>KR.num(r.no,0)},
      {label:'YES share', num:true, get:r=>r.yesShare===null?KR.dash(''):KR.pct(r.yesShare)},
      {label:'Ever traded', num:true, get:r=>`${KR.num(r.traded,0)} <span class="muted small">of ${KR.num(r.resolved,0)}</span>`},
      {label:'Never traded', num:true, get:r=>r.untraded?`${KR.num(r.untraded,0)} <span class="pill flag">no volume</span>`:KR.num(0,0)},
      {label:'Source', get:r=>`<a href="https://external-api.demo.kalshi.co/trade-api/v2/markets?status=settled&limit=1000" target="_blank" rel="noopener">settled markets</a>`}
    ], bt, 'No resolved markets in the current snapshot.');

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
        {label:'Rules', get:r=>r.rules_primary?`<span class="small" title="${KR.esc(r.rules_primary)}">${KR.esc(r.rules_primary.slice(0,80))}…</span>`:'—'},
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


LANDING_BODY = r"""
<h1>Kalshi demo dashboard — start here</h1>
<p class="lead">One dashboard for the five topics the brief names — <b>gas prices, elections,
culture, crypto and golf</b> — with price charts, order-book liquidity, resolution tracking
(<b>yes</b> or <b>no</b>) and simulated-trade analysis, built from Kalshi's public <b>demo</b>
Trade API. Mock money only; nothing here is investment advice.</p>

<div class="notice info"><b>What every number on this site is.</b> Either (a) a value copied
verbatim from a Kalshi API response, (b) arithmetic over copied values, labelled as computed
(e.g. 24-hour dollar volume from trade prints), or (c) blank. A value that could not be confirmed
is left blank and listed on <a href="pages/flagged.html">Flagged for Review</a> — it is never
filled in from memory or guessed. Each table row links to the request it came from.</div>

<h2>Choose a view</h2>
<div class="kpis" id="landingCards"></div>

<h2>The five topics</h2>
<p class="muted">Kept separate, with the events inside each topic kept together. Counts come from
the latest snapshot; a topic with no live markets says so instead of showing an empty table.</p>
<div id="topicTable"></div>

<h2>Track record of the pipeline</h2>
<div class="kpis" id="pipelineKpis"></div>

<h2>How to use this in a trading workflow</h2>
<div class="tablewrap"><table>
<thead><tr><th>Step</th><th>Page</th><th>What to look at</th><th>Why it is the right page</th></tr></thead>
<tbody>
<tr><td>1</td><td><a href="dashboard.html">Live dashboard</a></td>
<td>Ranked markets, the price chart (X = time, Y = contract price), the order book and the
liquidity-over-time chart.</td>
<td>It is the only page with both the ranking and the two charts on one screen, so a candidate
is judged on price AND on whether it can actually be traded.</td></tr>
<tr><td>2</td><td><a href="pages/gas.html">Topic pages</a></td>
<td>All live events for one topic, then everything already resolved for it.</td>
<td>Keeping topics apart stops a golf long-shot being compared with a gas price market.</td></tr>
<tr><td>3</td><td><a href="pages/resolutions.html">Resolutions</a></td>
<td>How each event resolved, YES or NO, and how much of it ever traded.</td>
<td>A YES on a market with zero volume is not evidence about anything; the page says so.</td></tr>
<tr><td>4</td><td><a href="pages/causes.html">Cause channels</a></td>
<td>The settlement sources Kalshi itself names for each contract, and the steps to line a
$0.10+ move up against the news.</td>
<td>The API never says why a price moved, so the honest answer is a checklist, not a headline.</td></tr>
<tr><td>5</td><td><a href="pages/analysis.html">Analysis</a></td>
<td>Per-trade P&amp;L, five categorisations, and strategies gated behind a minimum sample.</td>
<td>Strategy claims below the sample threshold are refused rather than shown as findings.</td></tr>
</tbody></table></div>
"""

LANDING_JS = r"""
<script>
(async function(){
  const $ = id => document.getElementById(id);
  const views = [
    {href:"dashboard.html", t:"Live dashboard", d:"Ranked live markets, price chart (time vs price), order book depth, liquidity over time, sharp-move table."},
    {href:"pages/executive-summary.html", t:"Executive summary", d:"The brief, what was built, what the data says, and what is still missing."},
    {href:"instrument-panel/site/index.html", t:"Instrument panel", d:"1,500+ open in-scope markets and 1,600+ resolved ones, ranked by open interest, with per-row API links."},
    {href:"verified/index.html", t:"Verified rows", d:"Every row with its official source; anything unconfirmable is blank and flagged."},
    {href:"rankings.html", t:"Dollar rankings", d:"Highest-dollar events per topic by a stated formula."},
    {href:"pages/resolutions.html", t:"Resolutions", d:"Settled events by YES/NO, with the YES share and how much ever traded."},
    {href:"pages/causes.html", t:"Cause channels", d:"Official settlement sources per contract, and how to check a $0.10+ move."},
    {href:"live/index.html", t:"Live console", d:"Paper trading with no credentials, plus signed demo orders if you supply your own key."},
    {href:"pages/analysis.html", t:"Analysis", d:"Trade categorisation and gated strategy results from the demo account."},
    {href:"pages/suggestions.html", t:"Suggestions", d:"What would make the site more live and interactive, each with a decision."},
    {href:"pages/flagged.html", t:"Flagged for review", d:"Every irregularity and unverified item, with its source."},
    {href:"pages/verification.html", t:"Verification", d:"Every claim, the official page it was checked against, and the run's request log."}
  ];
  $('landingCards').innerHTML = views.map(v =>
    `<a class="kpi-card" href="${v.href}" style="text-decoration:none">
       <div class="k">${KR.esc(v.t)}</div>
       <div class="s" style="font-size:.82rem;line-height:1.35">${KR.esc(v.d)}</div>
     </a>`).join('');

  try{
    const m = await KR.getJSON("data/dashboard_meta.json");
    const c = m.counts || {}, cat = m.topic_catalog || {};
    $('pipelineKpis').innerHTML = `
      <div class="kpi-card"><div class="k">Snapshot</div>
        <div class="v" style="font-size:1rem">${KR.esc((m.generated_at_utc||'').replace('T',' ').replace('+00:00',' UTC'))}</div>
        <div class="s">${KR.ago(m.generated_at_utc)} · GitHub Actions</div></div>
      <div class="kpi-card"><div class="k">In-scope live markets</div><div class="v">${KR.num(c.markets_in_scope,0)}</div>
        <div class="s">across the five topics</div></div>
      <div class="kpi-card"><div class="k">Settled markets in log</div><div class="v">${KR.num(c.resolved_in_scope,0)}</div>
        <div class="s">${KR.num(c.resolved_this_run,0)} added by the last run</div></div>
      <div class="kpi-card"><div class="k">API requests</div><div class="v">${KR.num(m.api_request_count,0)}</div>
        <div class="s">${KR.num(m.api_request_failures,0)} failed (rate limit) · <a href="pages/verification.html">log</a></div></div>`;

    const rows = Object.entries(cat).map(([t,v])=>({topic:t, ...v,
      live:(c.per_topic||{})[t], settled:(m.resolutions_by_topic||{})[t]}));
    KR.renderTable($('topicTable'), [
      {label:'Topic', get:r=>KR.topicPill(r.topic)},
      {label:'Live markets', num:true, get:r=>KR.num(r.live,0)},
      {label:'Series read', num:true, get:r=>`${KR.num(r.series_read,0)} <span class="muted small">of ${KR.num(r.series_in_catalog,0)}</span>`},
      {label:'Requests failed', num:true, get:r=>r.series_failed?`<span class="pill err">${r.series_failed}</span>`:KR.num(0,0)},
      {label:'Settled in log', num:true, get:r=>KR.num(r.settled,0)},
      {label:'Page', get:r=>`<a href="pages/${KR.esc(r.topic)}.html">${KR.esc(r.topic)} →</a>`},
      {label:'Source', get:r=>`<a href="https://external-api.demo.kalshi.co/trade-api/v2/series?category=${encodeURIComponent(r.topic)}" target="_blank" rel="noopener">series list</a>`}
    ], rows, 'No snapshot yet — the first workflow run will fill this in.');
  }catch(e){
    $('pipelineKpis').innerHTML = `<div class="notice bad">data/dashboard_meta.json could not be loaded: ${KR.esc(e.message)}.
      The snapshot is written by <code>.github/workflows/refresh-data.yml</code>. No values are invented.</div>`;
  }
})();
</script>
"""


CAUSES_BODY = r"""
<h1>Cause channels — where a sharp price move can be checked</h1>
<p class="lead">The dashboard marks every move of <b>$0.10 or more</b> between two consecutive
contract prices. Kalshi's API returns the price, the volume and the time of that move — it does
<b>not</b> return the news behind it, and this site will not invent one.</p>

<div class="notice"><b>What is and is not claimed here.</b> Nothing on this page says an article
<i>caused</i> a move. Each row is a <b>channel to check</b>, published by Kalshi itself as the
settlement source for that contract, together with the market's own page so the move can be lined
up against its timestamp. Verifying a cause is left to the reader, because the only authoritative
statement of a cause would have to come from the source that settles the contract.</div>

<h2>1. The official settlement sources, per contract</h2>
<p class="muted">Every Kalshi series record carries a <code>settlement_sources</code> array
(<a href="https://docs.kalshi.com/api-reference/market/get-series-list" target="_blank" rel="noopener">Get
Series List</a>). Those are the publications the exchange itself names as authoritative for the
contract, which makes them the right places to look first. They come from
<a href="https://external-api.demo.kalshi.co/trade-api/v2/series?category=Crypto&amp;limit=5" target="_blank" rel="noopener">the
API</a> — not from a keyword search.</p>
<div id="srcTable"></div>

<h2>2. How to line a move up against the news</h2>
<div class="tablewrap"><table>
<thead><tr><th>Step</th><th>What to do</th><th>Why that is the correct order</th><th>Source</th></tr></thead>
<tbody>
<tr><td>1</td><td>Read the move's timestamp on the dashboard (UTC to the second).</td>
<td>The chart's points are timestamped by the exchange; a cause must be at or before the move.</td>
<td><a href="https://docs.kalshi.com/api-reference/market/get-market-candlesticks" target="_blank" rel="noopener">Candlesticks</a> (end_period_ts)</td></tr>
<tr><td>2</td><td>Open the market's own page and check its rules text.</td>
<td>The rules define exactly which event would move the contract, so you know what to look for.</td>
<td><a href="https://docs.kalshi.com/getting_started/market_lifecycle" target="_blank" rel="noopener">Market lifecycle</a></td></tr>
<tr><td>3</td><td>Look at the settlement sources listed for that series.</td>
<td>Kalshi names these as authoritative for the contract; other outlets are commentary.</td>
<td><a href="https://docs.kalshi.com/api-reference/market/get-series-list" target="_blank" rel="noopener">Get Series List</a></td></tr>
<tr><td>4</td><td>Check whether the move coincides with a trade print at that price.</td>
<td>A jump with volume is a traded repricing; a jump with no volume is a quote change.</td>
<td><a href="https://docs.kalshi.com/api-reference/market/get-trades" target="_blank" rel="noopener">Get Trades</a></td></tr>
<tr><td>5</td><td>Record the link, the timestamp and the source. If nothing matches, leave it blank.</td>
<td>An unmatched move stays "cause unverified" — the site never guesses.</td>
<td><a href="flagged.html">Flagged for Review</a></td></tr>
</tbody></table></div>

<h2>3. Suggested reading — channels, not conclusions</h2>
<p class="muted">These are general newsrooms that Kalshi's own <code>settlement_sources</code> lists
for in-scope series. They are <b>suggestions of where to look</b>, not evidence about any specific
move, and no publication is claimed to have reported any specific jump.</p>
<div id="newsTable"></div>

<h2>4. What would make this automatic</h2>
<p class="muted">Two things are missing before a jump could be annotated automatically, and both are
recorded rather than worked around: Kalshi publishes no news or event feed keyed to price moves, and
its public API returns no field describing <i>why</i> a price changed. Until one exists, this page
stays a checklist. See <a href="suggestions.html">Suggestions</a> and
<a href="flagged.html">Flagged for Review</a> (F13).</p>
"""

CAUSES_JS = r"""
<script>
(async function(){
  const $ = id => document.getElementById(id);
  try{
    const meta = await KR.getJSON("data/dashboard_meta.json");
    const cat = meta.topic_catalog || {};
    $('scopeNote') && ($('scopeNote').textContent = Object.keys(cat).length + " topics in scope");
  }catch(e){}

  // 1. settlement sources per in-scope series, read from the collector's snapshot
  try{
    const s = await KR.getJSON("data/series_index.json");
    const topics = ["gas","elections","culture","crypto","golf"];
    const rows = [];
    const seen = new Set();
    for(const [ticker, series] of Object.entries(s.series || {})){
      const topic = series._topic || series.topic;
      if(!topics.includes(topic)) continue;
      for(const src of (series.settlement_sources || [])){
        const key = ticker + "|" + (src.name||"");
        if(seen.has(key)) continue;
        seen.add(key);
        rows.push({ticker, topic, name: src.name, url: src.url, title: series.title});
      }
    }
    rows.sort((a,b)=> (a.topic.localeCompare(b.topic)) || String(a.name).localeCompare(String(b.name)));
    KR.renderTable($('srcTable'), [
      {label:'Topic', get:r=>KR.topicPill(r.topic)},
      {label:'Series', get:r=>`<b>${KR.esc(r.title||r.ticker)}</b><br><span class="muted small">${KR.esc(r.ticker)}</span>`},
      {label:'Settlement source named by Kalshi', get:r=>KR.esc(r.name||'—')},
      {label:'Link', get:r=>r.url?KR.link(r.url,'open'):'— <span class="pill flag">no URL in API</span>'},
      {label:'Source', get:r=>KR.esc(`GET ${KR.DEMO_REST}/series/${r.ticker}`)}
    ], rows.slice(0,400), 'No settlement sources in the snapshot yet.');
  }catch(e){
    $('srcTable').innerHTML = `<div class="notice bad">data/series_index.json could not be loaded: ${KR.esc(e.message)}</div>`;
  }

  // 3. generic news channels named by Kalshi as settlement sources, most frequent first
  try{
    const s = await KR.getJSON("data/series_index.json");
    const counts = new Map();
    for(const series of Object.values(s.series || {})){
      for(const src of (series.settlement_sources || [])){
        if(!src.url || !src.name) continue;
        if(!/^https?:/.test(src.url)) continue;
        const k = src.name + "|" + src.url;
        counts.set(k, (counts.get(k)||0) + 1);
      }
    }
    const rows = [...counts.entries()]
      .map(([k,n])=>{const [name,url]=k.split("|"); return {name,url,n};})
      .sort((a,b)=>b.n-a.n);
    KR.renderTable($('newsTable'), [
      {label:'Channel', get:r=>`<b>${KR.esc(r.name)}</b>`},
      {label:'Link', get:r=>KR.link(r.url,'open')},
      {label:'Named as a settlement source by Kalshi for', num:true, get:r=>r.n + ' series'},
      {label:'Source', get:r=>`<a href="https://docs.kalshi.com/api-reference/market/get-series-list" target="_blank" rel="noopener">settlement_sources</a>`}
    ], rows.slice(0,60), 'No settlement sources in the snapshot yet.');
  }catch(e){
    $('newsTable').innerHTML = `<div class="notice bad">data/series_index.json could not be loaded: ${KR.esc(e.message)}</div>`;
  }
})();
</script>
"""


def build_live_pages() -> None:
    snap = snapshot_meta()
    page(path="dashboard.html", title="Live dashboard", active="dash",
         body=meta_bar(snap) + DASH_BODY.replace("{PREFIX}", ""),
         extra_js=DASH_JS.replace("{PREFIX}", ""),
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

    page(path="index.html", title="Kalshi demo dashboard — start here", active="landing",
         body=LANDING_BODY, extra_js=LANDING_JS,
         desc="Start here: which dashboard to open for what, the five topics, and how each number on the site was produced.")

    page(path="pages/causes.html", title="Cause channels", active="cause",
         body=CAUSES_BODY, extra_js=CAUSES_JS,
         desc="Where a sharp Kalshi price move can be checked: the settlement sources Kalshi itself names, and the steps to line a move up against the news.")


if __name__ == "__main__":
    print("building live pages...")
    build_live_pages()
