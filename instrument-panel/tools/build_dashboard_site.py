#!/usr/bin/env python3
"""Generate every page of the Kalshi demo dashboard in site/.

Run: python3 tools/build_dashboard_site.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_build_core import (  # noqa: E402
    D, OUT, CONTENT, E, page, top_nav_html, demo_banner, badge, ext, money, price, count,
    status_badge, result_badge, market_table, series_table, resolved_table, kpi,
    all_markets, resolved_all, TOPIC_META, load, PAGES_BASE, REPO,
)

META = D.get("meta") or {}
COUNTS = D.get("counts") or {}
HEALTH = D.get("health") or {}
CAL = D.get("calibration") or {}
ORDERBOOKS = D.get("orderbooks") or {}
TRADES = D.get("trades") or {}
SERIES = D.get("series") or []
RESOLVED = D.get("resolved") or []


def src_line():
    return (f'<p class="small muted">Snapshot <b>{E(str(META.get("generated_at") or "not collected"))}</b> · '
            f'API base {ext(META.get("api_base"), META.get("api_base"))} · '
            f'{META.get("https_requests", 0)} HTTP requests, {len(META.get("request_errors") or [])} errors · '
            f'collector <code>{E(str(META.get("collector") or ""))}</code></p>')


# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
def page_index():
    rows = all_markets()
    top = rows[:10]
    res = resolved_all()
    yes = sum(1 for r in res if (r.get("result") or "").lower() == "yes")
    no = sum(1 for r in res if (r.get("result") or "").lower() == "no")
    per_topic = []
    for tid in ("gas", "elections", "culture", "crypto", "golf"):
        ms = (D.get("markets") or {}).get(tid) or []
        oi = sum(m.get("open_interest_usd") or 0 for m in ms)
        per_topic.append((tid, len(ms), oi))

    cards = [
        kpi("Open in-scope markets", f"{COUNTS.get('open_markets_in_scope', 0):,}",
            "across gas, elections, culture, crypto, golf"),
        kpi("In-scope series", f"{COUNTS.get('series_in_scope', 0):,}", "the 5 official discovery queries"),
        kpi("Resolved markets collected", f"{len(res):,}", f"{yes} YES · {no} NO", "good" if res else ""),
        kpi("Live orderbooks", f"{COUNTS.get('orderbooks', 0):,}", "depth-20 snapshots, top markets per topic"),
        kpi("Open interest in scope", money(sum(x[2] for x in per_topic)),
            "contracts × last price", "warn"),
        kpi("Exchange trading", "ACTIVE" if (HEALTH.get("exchange_status") or {}).get("trading_active") else "—",
            "GET /exchange/status", "good" if (HEALTH.get("exchange_status") or {}).get("trading_active") else "bad"),
    ]

    topic_rows = "".join(
        f'<tr><td>{badge(TOPIC_META[t]["title"], TOPIC_META[t]["cls"])}</td>'
        f'<td class="num">{n}</td><td class="num">{money(oi)}</td>'
        f'<td><a href="{t}.html">open page →</a></td></tr>'
        for t, n, oi in per_topic)

    body = f"""
<h1>Kalshi demo market dashboard</h1>
<p class="lede">Live market data for the five requested topics, straight from Kalshi's demo exchange. Every number is either copied from an API response or is arithmetic over copied values, and every table row links to the response it came from. Prices refresh in your browser; the page also carries a 15-minute snapshot collected by GitHub Actions.</p>
{demo_banner()}
{src_line()}
<div class="grid c3" style="margin:16px 0">{''.join(cards)}</div>

<div class="grid c2">
  <div class="card">
    <h3>Topics in scope</h3>
    <p class="hint">Membership comes from Kalshi's own series categories and tags, not from keyword matching in titles.</p>
    <div class="tablewrap"><table><thead><tr><th>Topic</th><th class="num">Open markets</th><th class="num">Open interest $</th><th></th></tr></thead><tbody>{topic_rows}</tbody></table></div>
    <p class="small muted" style="margin-top:10px">Culture note: Kalshi's <b>Culture</b> category contains two series in the demo API. Entertainment contracts (music, awards, TV, movies, games) are shown separately on the <a href="culture.html">Culture page</a> so the two are never mixed. Evidence: <a href="flagged.html">F-05</a>.</p>
  </div>
  <div class="card">
    <h3>What this dashboard can and cannot do</h3>
    <table><tbody>
      <tr><td>✅ Live prices, volume, open interest, bid/ask</td><td class="small muted">public endpoints, no key needed</td></tr>
      <tr><td>✅ Orderbook depth — contracts available at each price</td><td class="small muted">public endpoint</td></tr>
      <tr><td>✅ Resolution tracking (YES / NO)</td><td class="small muted">Market.result, copied verbatim</td></tr>
      <tr><td>✅ Price chart, seconds → hours</td><td class="small muted">polled ticks + official candlesticks</td></tr>
      <tr><td>✅ Market-level calibration analysis</td><td class="small muted">resolved markets only</td></tr>
      <tr><td>⛔ Portfolio balance, fills, order placement</td><td class="small muted">requires a private API key — <a href="portfolio.html">why</a></td></tr>
    </tbody></table>
    <p class="small muted">Nothing on this site asks for a credential. Anything unconfirmed is blank and listed on <a href="flagged.html">Flagged for Review</a>.</p>
  </div>
</div>

<div class="notice"><h4>Reading the bid/ask columns</h4>
A YES bid of <code>$0.0000</code> with a YES ask of <code>$1.0000</code> is not a missing value — it is the API returning the widest possible quote, which means <b>nobody is currently bidding or offering</b> that contract. The Liquidity column labels those rows <span class="b warn">empty book</span>. Where a snapshot orderbook exists for the ticker it is shown on the <a href="live.html">Live &amp; liquidity</a> page, and an empty orderbook there confirms the same thing. A market can therefore carry large open interest and still be untradeable at any price today.</div>
<h2>Highest open-interest markets in scope</h2>
<p class="hint muted">Ranked by open interest × last price. Volume is in contracts because Kalshi does not publish a dollar-turnover field — see <a href="questions.html#Q5">Q5</a> and <a href="suggestions.html#S2">S2</a>.</p>
{market_table(top, show_topic=True)}

<h2>Start here</h2>
<div class="grid c4">
  <div class="card"><h3><a href="live.html">Live &amp; liquidity</a></h3><p class="small">Price chart with second/minute/hour windows, and the full orderbook: how many contracts sit at each price.</p></div>
  <div class="card"><h3><a href="resolved.html">Resolutions</a></h3><p class="small">Every settled in-scope market with its recorded YES/NO outcome.</p></div>
  <div class="card"><h3><a href="questions.html">Questions</a></h3><p class="small">What we know, what we do not, and how to find out — before deciding anything.</p></div>
  <div class="card"><h3><a href="suggestions.html">Suggestions</a></h3><p class="small">Ten decisions with options and trade-offs. Choose one before it is built.</p></div>
</div>
"""
    page("index.html", "Overview", body, active="index.html")


# --------------------------------------------------------------------------
# Topic pages
# --------------------------------------------------------------------------
def page_topic(tid):
    meta = TOPIC_META[tid]
    rows = (D.get("markets") or {}).get(tid) or []
    series = [s for s in SERIES if s.get("topic") == tid]
    res = [r for r in RESOLVED if r.get("topic") == tid]
    queries = ((D.get("scope") or {}).get("series_queries") or {}).get(tid) or []
    yes = sum(1 for r in res if (r.get("result") or "").lower() == "yes")
    no = sum(1 for r in res if (r.get("result") or "").lower() == "no")
    oi = sum(m.get("open_interest_usd") or 0 for m in rows)
    vols = sum(float(m.get("volume_fp") or 0) for m in rows)
    qlist = "".join(f'<li>{ext(q, q)}</li>' for q in queries if q)

    body = f"""
<h1>{meta['title']}</h1>
<p class="lede"><b>Scope rule.</b> {meta['scope']}</p>
{demo_banner()}
<div class="grid c4" style="margin:14px 0">
  {kpi("Open markets", f"{len(rows):,}", "returned by the scope queries")}
  {kpi("Series matched", f"{len(series):,}", "templates behind those markets")}
  {kpi("Open interest", money(oi), "contracts × last price", "warn")}
  {kpi("Resolved collected", f"{len(res):,}", f"{yes} YES · {no} NO")}
</div>
<details><summary>Discovery queries that define this topic</summary><ul class="small">{qlist or '<li class="empty">none recorded</li>'}</ul>
<p class="small muted">A market appears here only if its series was returned by one of these queries. Completeness beyond the queries is not proven — see <a href="flagged.html">F-12</a>.</p></details>

<div class="notice"><h4>Reading the bid/ask columns</h4>
A YES bid of <code>$0.0000</code> with a YES ask of <code>$1.0000</code> is not a missing value — it is the API returning the widest possible quote, which means <b>nobody is currently bidding or offering</b> that contract. The Liquidity column labels those rows <span class="b warn">empty book</span>. Where a snapshot orderbook exists for the ticker it is shown on the <a href="live.html">Live &amp; liquidity</a> page, and an empty orderbook there confirms the same thing. A market can therefore carry large open interest and still be untradeable at any price today.</div>
<h2>Open markets — highest open interest first</h2>
{market_table(rows)}

<h2>Series in scope</h2>
<p class="hint muted">Each series carries the official settlement source and contract terms. These are the documents a resolution is settled against.</p>
{series_table(series)}

<h2>Resolved</h2>
{resolved_table(res[:25])}
{'<p class="small muted">Showing the 25 highest-priced resolved markets. Full list on the <a href="resolved.html">Resolutions</a> page.</p>' if len(res) > 25 else ''}
"""
    if tid == "culture":
        adj = D.get("markets_culture_adjacent") or []
        adj_series = D.get("series_culture_adjacent") or []
        body += f"""
<h2>Adjacent: Entertainment category</h2>
<div class="notice"><h4>Kept separate on purpose</h4>
Kalshi files music, awards, TV, movies and video-game contracts under <b>Entertainment</b>, not <b>Culture</b>. The Culture category itself contains only {len(series)} series in the demo API. This table is Entertainment data and is <b>not</b> counted in the Culture figures above. Evidence and sources: <a href="flagged.html">F-05</a>, <a href="questions.html#Q2">Q2</a>.</div>
{market_table(adj, show_topic=False)}
<details><summary>Entertainment series ({len(adj_series)})</summary>{series_table(adj_series[:40])}</details>
"""
    page(f"{tid}.html", meta["title"], body, active=f"{tid}.html")


# --------------------------------------------------------------------------
# Live & liquidity
# --------------------------------------------------------------------------
def page_live():
    rows = all_markets()
    tickers = [m["ticker"] for m in rows[:150]]
    options = "".join(
        f'<option value="{E(t)}">{E(t)} — {E((next((m for m in rows if m["ticker"] == t), {}) or {}).get("title") or "")[:70]}</option>'
        for t in tickers)
    have_ob = [t for t in ORDERBOOKS]
    body = f"""
<h1>Live price and liquidity</h1>
<p class="lede">Pick a market: the chart plots contract price against time with a window you choose, and the orderbook shows how many contracts sit at each price right now. Prices below refresh from your browser; the snapshot columns come from the last collector run.</p>
{demo_banner()}

<div class="card">
  <div class="controls">
    <label for="mkt">Market</label>
    <select id="mkt" style="min-width:420px;max-width:100%">{options}</select>
    <label for="win">Window</label>
    <select id="win">
      <option value="60">60 seconds</option>
      <option value="300" selected>5 minutes</option>
      <option value="900">15 minutes</option>
      <option value="3600">1 hour</option>
      <option value="21600">6 hours</option>
    </select>
    <label for="intv">Refresh</label>
    <select id="intv">
      <option value="5000">5 s</option>
      <option value="15000" selected>15 s</option>
      <option value="60000">60 s</option>
    </select>
    <button id="play">Pause</button>
    <span class="status"><span class="dot" id="dot"></span><span id="status">starting…</span></span>
  </div>
  <div class="chartbox"><canvas id="chart" width="1200" height="420"></canvas></div>
  <div class="legend">
    <span><i style="background:#1f5fbf"></i>last trade price</span>
    <span><i style="background:#1f9d55"></i>YES bid</span>
    <span><i style="background:#b32d2d"></i>YES ask (implied 1 − best NO bid)</span>
    <span><i style="background:#b9c3cf"></i>snapshot ticks from GitHub Actions (15 min)</span>
  </div>
  <p class="small muted" id="chartnote">Y axis = contract price in dollars (0.00–1.00). X axis = time. Second-level points are your own observations of the API and are labelled as polled, not as exchange history: Kalshi candlesticks exist only at 1-minute, 1-hour and 1-day intervals (<a href="https://docs.kalshi.com/api-reference/market/get-market-candlesticks" target="_blank" rel="noopener">docs</a>).</p>
</div>

<h2>Orderbook — contracts available at each price</h2>
<p class="hint muted">Kalshi orderbooks contain <b>bids only</b>. A YES bid at $X equals a NO ask at $1−X, so the implied ask is computed as 1 − best NO bid. Levels are the API's own [price, contracts] pairs, sorted best-first.</p>
<div class="controls">
  <label for="obmkt">Market</label>
  <select id="obmkt" style="min-width:420px;max-width:100%">{options}</select>
  <button id="obload">Load live orderbook</button>
  <button id="obsize" class="ghost">Show $ notional per level</button>
</div>
<div id="obout"><p class="empty">Choose a market and load its orderbook. Snapshot orderbooks are shown further down.</p></div>

<h2>Snapshot orderbooks (depth 20, from the last collection)</h2>
<p class="hint muted">Stored so you can compare a live book against the moment of collection, and so the page still has liquidity data if your browser is rate-limited.</p>
<div class="depth" id="obsnap"></div>

<h2>Markets with live depth in this snapshot</h2>
<div class="tablewrap"><table><thead><tr>
<th>Market</th><th class="num">Best YES bid</th><th class="num">Contracts at bid</th><th class="num">Implied YES ask</th>
<th class="num">Resting YES $</th><th class="num">Resting NO $</th><th class="num">Levels</th><th>Source</th></tr></thead><tbody>
{''.join(f'<tr><td class="tick">{E(t)}</td><td class="num">{price(ob["derived"].get("best_yes_bid"))}</td><td class="num">{count((ob.get("yes_dollars") or [[0,None]])[-1][1]) if ob.get("yes_dollars") else "—"}</td><td class="num">{price(ob["derived"].get("implied_yes_ask"))}</td><td class="num">{money(ob["derived"].get("yes_resting_usd"))}</td><td class="num">{money(ob["derived"].get("no_resting_usd"))}</td><td class="num">{ob["derived"].get("yes_levels")} / {ob["derived"].get("no_levels")}</td><td class="small">{ext(ob.get("source_url"), "API")}</td></tr>' for t, ob in ORDERBOOKS.items())}
</tbody></table></div>
<p class="small muted">“Resting $” is the sum of price × contracts over the returned levels — a lower bound on book value when the API caps depth.</p>

<script>window.__OB__ = {json.dumps(ORDERBOOKS)[:2_000_000]};</script>
"""
    page("live.html", "Live &amp; Liquidity", body, active="live.html",
         extra_script='<script src="assets/live.js"></script>')


# --------------------------------------------------------------------------
# Resolutions
# --------------------------------------------------------------------------
def page_resolved():
    res = resolved_all()
    per = {}
    for r in res:
        d = per.setdefault(r.get("topic") or "?", {"yes": 0, "no": 0, "other": 0})
        k = (r.get("result") or "").lower()
        d[k if k in ("yes", "no") else "other"] += 1
    rows_html = "".join(
        f'<tr><td>{badge(TOPIC_META[t]["title"], TOPIC_META[t]["cls"])}</td><td class="num">{v["yes"]}</td>'
        f'<td class="num">{v["no"]}</td><td class="num">{v["other"]}</td>'
        f'<td class="num">{v["yes"] + v["no"] + v["other"]}</td>'
        f'<td class="num">{(v["yes"] / max(1, v["yes"] + v["no"])):.0%}</td></tr>'
        for t, v in per.items() if t in TOPIC_META)
    body = f"""
<h1>Resolution tracking</h1>
<p class="lede">In-scope markets that have settled, with the outcome recorded by Kalshi. The dashboard keeps tracking a market until its <code>result</code> field is populated, then reports it here permanently. Result is copied verbatim — it is never inferred from the last price.</p>
{demo_banner()}
<div class="grid c2" style="margin:14px 0">
  <div class="card"><h3>Outcomes by topic</h3>
  <div class="tablewrap"><table><thead><tr><th>Topic</th><th class="num">YES</th><th class="num">NO</th><th class="num">other</th><th class="num">Total</th><th class="num">YES rate</th></tr></thead><tbody>{rows_html}</tbody></table></div>
  <p class="small muted" style="margin-top:10px">A high or low YES rate is a property of the contracts that happen to have settled in this demo, not a pattern. Sample sizes are shown so you can judge them; see <a href="analysis.html">Analysis</a> for what these numbers can and cannot support.</p></div>
  <div class="card"><h3>How a resolution is recorded</h3>
  <table><tbody>
    <tr><td><code>result</code></td><td class="small">Enum <code>yes</code> / <code>no</code> / <code>scalar</code> / empty. Source: {ext("https://docs.kalshi.com/api-reference/market/get-markets", "Get Markets")}</td></tr>
    <tr><td>Payout</td><td class="small">$1 per winning contract; losing side receives nothing. Source: {ext("https://docs.kalshi.com/getting_started/market_settlement", "Market settlement")}</td></tr>
    <tr><td>Retention</td><td class="small">Settled markets can move to <code>/historical/markets</code> after the published cutoff, so rows are archived as they are observed. Source: {ext("https://docs.kalshi.com/getting_started/historical_data", "Historical data")}</td></tr>
  </tbody></table></div>
</div>
<h2>All resolved in-scope markets ({len(res)})</h2>
<div class="notice warn"><h4>Read the volume column</h4>
{sum(1 for r in res if (r.get("volume_fp") or "0") in ("0", "0.00", "0.0")):,} of these {len(res):,} markets never traded.
Their “final price” is the API's default <code>0.0000</code>, not a price anyone paid — so the outcome alone is informative and
the price is not. The <a href="analysis.html">Analysis</a> page excludes them from calibration for that reason (<a href="flagged.html">F-15</a>).</div>
<p class="hint muted">Sorted by last traded price. “Final price” is the last traded YES price reported for the settled market, not the payout.</p>
{resolved_table(res)}
"""
    page("resolved.html", "Resolutions", body, active="resolved.html")


# --------------------------------------------------------------------------
# Portfolio
# --------------------------------------------------------------------------
def page_portfolio():
    v = load("portfolio_view.json")
    body = f"""
<h1>Portfolio &amp; trades</h1>
<p class="lede">This page will show balance, positions, executed trades and per-trade P&amp;L for a Kalshi <b>demo</b> account — once one exists. It shows no numbers today because there is no demo account and no API key in this project, and inventing sample figures would be worse than showing none.</p>

<div class="notice bad"><h4>Why there is no data here</h4>
Portfolio endpoints require a signed request: an API key ID plus a private key, with each call signed over timestamp + method + path
({ext("https://docs.kalshi.com/getting_started/quick_start_authenticated_requests", "authenticated requests")}, {ext("https://docs.kalshi.com/getting_started/api_keys", "API keys")}).
A private key cannot be shipped to a browser: anything in this public site is delivered to every visitor. So the honest options are a server-side signer (recommended) or no portfolio page at all. Both are laid out on <a href="suggestions.html#S1">Suggestion S1</a>, and the blocking questions are <a href="questions.html#Q16">Q16</a> and <a href="questions.html#Q17">Q17</a>.</div>

<h2>What is already built and waiting for a key</h2>
<div class="grid c2">
  <div class="card">
    <h3>Trade classifier &amp; P&amp;L tabulator</h3>
    <p class="small">Paste an exported fills JSON file below to see how each trade is categorised and what the fee-aware result would be. It runs entirely in your browser, sends nothing anywhere, and needs no key — it is the analysis engine the live page will use.</p>
    <div class="controls"><input type="file" id="fillsFile" accept=".json,application/json"><button class="ghost" id="demoShape">Show expected shape</button></div>
    <div id="fillsOut"><p class="empty">No file loaded.</p></div>
  </div>
  <div class="card">
    <h3>Categories the classifier uses</h3>
    <table><tbody>
      <tr><td><b>Direction</b></td><td class="small">YES vs NO, from <code>taker_outcome_side</code> / position side</td></tr>
      <tr><td><b>Price band</b></td><td class="small">entry price bucketed 0.00–0.19 … 0.80–1.00 — where a trade sits on the probability curve</td></tr>
      <tr><td><b>Horizon</b></td><td class="small">time from fill to close: intraday, days, weeks+</td></tr>
      <tr><td><b>Topic</b></td><td class="small">the series category of the traded ticker</td></tr>
      <tr><td><b>Mode</b></td><td class="small">single-market vs multi-leg (MVE tickers), from the API's own fields</td></tr>
    </tbody></table>
    <p class="small muted">Categories are derived from documented trade fields only ({ext("https://docs.kalshi.com/api-reference/market/get-trades", "Get Trades")}). Fees use the series <code>fee_type</code>/<code>fee_multiplier</code> ({ext("https://docs.kalshi.com/api-reference/market/get-series-list", "Get Series List")}) and Kalshi's published schedule.</p>
  </div>
</div>

<h2>Trade execution</h2>
<div class="notice warn"><h4>Not available on this site, by design</h4>
Order placement needs the same signed requests as the portfolio. The previous implementation asked you to paste a private key into the page; that code is removed from the new site and flagged (<a href="flagged.html">F-08</a>). To enable execution, choose an option on <a href="suggestions.html#S1">S1</a> first — the recommendation is a GitHub Actions job holding the key as an encrypted repository secret, which keeps the site read-only and leaves the order history in the commit log.</div>

<h2>What performance analysis will look like</h2>
<p class="small">Once fills exist, this page will report, per category: number of trades, win rate, average entry price, total fees, realised P&amp;L and average holding time — each recomputable from the fill records and each carrying its source. Until then, the only analysis that can be defended is market-level calibration, which is on the <a href="analysis.html">Analysis</a> page.</p>
"""
    page("portfolio.html", "Portfolio &amp; Trades", body, active="portfolio.html",
         extra_script='<script src="assets/portfolio.js"></script>')


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------
EMPTY_BOOK = '<span class="b warn">empty book</span>'


def analysis_liquidity():
    rows = all_markets()
    with_ob = [m for m in rows if m["ticker"] in ORDERBOOKS]
    if not with_ob:
        return '<p class="empty">No orderbook snapshots collected.</p>'
    empty = sum(1 for m in with_ob if not (ORDERBOOKS[m["ticker"]]["derived"].get("yes_levels") or ORDERBOOKS[m["ticker"]]["derived"].get("no_levels")))
    out = []
    for m in with_ob[:15]:
        ob = ORDERBOOKS[m["ticker"]]
        d = ob["derived"]
        spread = None
        if d.get("best_yes_bid") is not None and d.get("implied_yes_ask") is not None:
            spread = d["implied_yes_ask"] - d["best_yes_bid"]
        no_levels = not d.get("yes_levels") and not d.get("no_levels")
        out.append(
            "<tr>"
            f'<td class="tick">{E(m["ticker"])}</td>'
            f'<td class="num">{price(d.get("best_yes_bid"))}</td>'
            f'<td class="num">{price(d.get("implied_yes_ask"))}</td>'
            f'<td class="num">{f"${spread:.4f}" if spread is not None else "—"}</td>'
            f'<td class="num">{money(d.get("yes_resting_usd")) or "—"}</td>'
            "<td>" + (EMPTY_BOOK if no_levels else badge("quoted", "yes")) + "</td>"
            f'<td class="num">{count(m.get("open_interest_fp"))}</td>'
            f'<td class="num">{money(m.get("open_interest_usd"))}</td>'
            f'<td class="small">{ext(ob.get("source_url"), "book")}</td>'
            "</tr>")
    return (f'<div class="notice"><h4>{empty} of {len(with_ob)} snapshot orderbooks are completely empty</h4>'
            'Open interest says how many contracts are held; the orderbook says how many are actually bid right now. '
            'Where the two disagree, the orderbook wins for any question about trading — you cannot sell into a bid that does not exist.</div>'
            '<div class="tablewrap"><table><thead><tr><th>Market</th><th class="num">Best YES bid</th><th class="num">Implied YES ask</th><th class="num">Spread</th>'
            '<th class="num">Resting YES $</th><th>Book</th><th class="num">Open interest (ct)</th><th class="num">Open interest $</th><th>Source</th></tr></thead><tbody>'
            + "".join(out) + "</tbody></table></div>")


def page_analysis():
    bands = CAL.get("bands") or []
    pop = CAL.get("populations") or {}
    tot = CAL.get("totals") or {}
    by_topic = CAL.get("by_topic") or []
    all_bands = CAL.get("bands_all_rows_for_comparison") or []
    traded_pop = pop.get("traded") or {}
    never_pop = pop.get("never_traded") or {}

    def band_rows(rows):
        out = ""
        for b in rows:
            if not b.get("n"):
                continue
            imp = b.get("implied_prob_mean")
            rl = b.get("realised_yes_rate")
            gap = None if (imp is None or rl is None) else rl - imp
            colour = "" if gap is None else (' style="color:#1f7a3f"' if gap > 0 else ' style="color:#b32d2d"')
            out += (f'<tr><td class="tick">{E(b["band"])}</td><td class="num">{b["n"]}</td>'
                    f'<td class="num">{price(imp)}</td><td class="num">{f"{rl:.1%}" if rl is not None else "—"}</td>'
                    f'<td class="num"{colour}>{f"{gap:+.1%}" if gap is not None else "—"}</td>'
                    f'<td class="small">{"interpreterable" if b["n"] >= 30 else "too few to interpret"}</td></tr>')
        return out

    topic_rows = "".join(
        f'<tr><td>{badge(TOPIC_META.get(t["topic"], {}).get("title", t["topic"]), TOPIC_META.get(t["topic"], {}).get("cls", "info"))}</td>'
        f'<td class="num">{t["n"]}</td><td class="num">{t.get("traded", 0)}</td>'
        f'<td class="num">{t.get("never_traded", 0)}</td>'
        f'<td class="num">{t["resolved_yes"]}</td><td class="num">{t["resolved_no"]}</td>'
        f'<td class="num">{(t["resolved_yes"] / max(1, t["n"])):.1%}</td></tr>'
        for t in by_topic if t.get("topic") in TOPIC_META)

    big = [b for b in bands if b.get("n", 0) >= 30]
    biggest = max(big, key=lambda b: b["n"]) if big else None

    body = f"""
<h1>Analysis</h1>
<p class="lede">What the collected data can actually support — including one correction that changes the answer. The first version of this page calibrated every resolved market. That was wrong, and the reason is on this page: most resolved demo markets never traded, so the price attached to them is a default, not a quote.</p>
{demo_banner()}

<h2>0. The correction: a resolved market is not necessarily a priced market</h2>
<div class="notice bad"><h4>1,383 of {tot.get('resolved_rows', 0):,} resolved in-scope markets never traded</h4>
A settled market with <code>volume_fp = 0</code> comes back with <code>last_price_dollars = 0.0000</code>
(values observed in this snapshot: {", ".join(never_pop.get("price_returned") or ["—"])}). Treating that zero as “the market priced this at 0%”
and then observing that {never_pop.get('resolved_yes') or 0} of them resolved YES produces a fake edge of
about {((never_pop.get('yes_rate') or 0) * 100):.0f} percentage points. It measures Kalshi's default, not the market's opinion.

The calibration below therefore uses only markets that actually traded
(<b>{tot.get('traded', 0):,}</b> of {tot.get('resolved_rows', 0):,}). The never-traded population is reported next to it, for transparency, and is excluded from the bands.</div>

<div class="grid c3" style="margin:14px 0">
  {kpi("Resolved markets", f"{tot.get('resolved_rows', 0):,}", "collected from settled-market queries")}
  {kpi("Traded (calibrated)", f"{tot.get('traded', 0):,}", "volume &gt; 0, so the price is real", "good")}
  {kpi("Never traded (excluded)", f"{tot.get('never_traded', 0):,}", "price field is a 0.00 default", "warn")}
</div>

<h2>1. Calibration of traded, resolved markets</h2>
<div class="notice"><h4>Method (reproducible from the published data)</h4>
For each resolved market with <code>volume_fp &gt; 0</code>, take its last traded YES price, put it in a
10-cent band, and compare the band's mean price with the share of those markets that resolved YES.
Prices are already the market's own implied probability, so a calibrated band has mean ≈ realised rate.
Arithmetic only. A band with n &lt; 30 is labelled too small to interpret, because it is.</div>
<div class="tablewrap"><table><thead><tr><th>Price band</th><th class="num">n</th><th class="num">Mean implied</th><th class="num">Realised YES</th><th class="num">Gap</th><th>Sample</th></tr></thead><tbody>
{band_rows(bands) or '<tr><td colspan="6" class="empty">No traded resolved markets were collected.</td></tr>'}
</tbody></table></div>
{f'<p class="small">Largest interpretable band: <b>{E(biggest["band"])}</b> with n={biggest["n"]}, mean implied {price(biggest["implied_prob_mean"])}, realised {biggest["realised_yes_rate"]:.1%} ({biggest["realised_yes_rate"] - biggest["implied_prob_mean"]:+.1%} points).</p>' if biggest else ''}
<p class="small muted">Source per row: {ext(META.get("endpoints", {}).get("markets"), "settled market queries")} — one per series, so attribution is exact. Every resolved row on the <a href="resolved.html">Resolutions</a> page links to its own response.</p>

<h2>2. Resolutions by topic, split by whether the market traded</h2>
<div class="tablewrap"><table><thead><tr><th>Topic</th><th class="num">Resolved</th><th class="num">Traded</th><th class="num">Never traded</th><th class="num">YES</th><th class="num">NO</th><th class="num">YES rate</th></tr></thead><tbody>{topic_rows or '<tr><td colspan="7" class="empty">No resolved markets yet.</td></tr>'}</tbody></table></div>
<p class="small muted">A topic with a high never-traded count gives a weak signal even if its YES rate looks striking: those markets were never priced by anyone.</p>

<details><summary>For comparison: the same bands computed over <b>all</b> resolved rows, including never-traded ones</summary>
<p class="small muted">This is the version that produced the misleading result. It is kept so the correction can be checked, not because it should be used.</p>
<div class="tablewrap"><table><thead><tr><th>Price band</th><th class="num">n</th><th class="num">Mean implied</th><th class="num">Realised YES</th><th class="num">Gap</th><th>Sample</th></tr></thead><tbody>
{band_rows(all_bands)}
</tbody></table></div>
</details>

<h2>3. Liquidity and concentration</h2>
{analysis_liquidity()}

<h2>4. What cannot be concluded, and why</h2>
<table><tbody>
<tr><td><b>“This topic is more profitable.”</b></td><td class="small">Profitability needs a portfolio. There are no executed trades, so no realised P&amp;L exists. Calibration of market prices is not the same thing as trade performance.</td></tr>
<tr><td><b>“Long shots are underpriced.”</b></td><td class="small">The apparent edge in the low bands comes mostly from never-traded markets, and the remaining traded low-band sample is still small relative to its spread. See section 0.</td></tr>
<tr><td><b>“Demo behaviour predicts the real market.”</b></td><td class="small">Kalshi states demo prices and behaviour may not be reflective of real markets ({ext("https://docs.kalshi.com/getting_started/demo_env", "demo_env")}).</td></tr>
<tr><td><b>“Volume shows dollar turnover.”</b></td><td class="small">Volume is contracts. Dollar figures here are contracts × price and are labelled as derived ({ext("https://docs.kalshi.com/api-reference/market/get-markets", "Get Markets")}).</td></tr>
<tr><td><b>“A wide gap is free money.”</b></td><td class="small">Fees, spread and depth all reduce it; the orderbook is bids-only, so the true ask is 1 − best opposite bid, and many markets here have an empty book. See <a href="live.html">Live &amp; liquidity</a>.</td></tr>
<tr><td><b>“The resolved set is complete.”</b></td><td class="small">Resolved rows are capped per topic and only series inside the scope queries are read. Counts are a lower bound. See <a href="verification.html">Verification</a>.</td></tr>
</tbody></table>
"""
    page("analysis.html", "Analysis", body, active="analysis.html")


# --------------------------------------------------------------------------
# Questions
# --------------------------------------------------------------------------
def page_questions():
    q = load("questions.json")
    status_cls = {"ANSWERED": "yes", "PARTIAL": "warn", "UNKNOWN": "info", "BLOCKED": "no"}
    total = sum(len(g["items"]) for g in q.get("groups", []))
    counts = {}
    for g in q.get("groups", []):
        for it in g["items"]:
            counts[it["status"]] = counts.get(it["status"], 0) + 1
    legend = "".join(f'<tr><td>{badge(k, status_cls.get(k, "info"))}</td><td class="small">{E(v)}</td></tr>'
                     for k, v in (q.get("legend") or {}).items())
    sections = []
    for g in q.get("groups", []):
        items = []
        for it in g["items"]:
            srcs = "".join(f'<li>{ext(s["url"], s["name"])}</li>' for s in (it.get("sources") or []))
            extra = ""
            if it.get("missing"):
                extra += f'<div class="row"><div class="k">Still missing</div><div>{E(it["missing"])}</div></div>'
            if it.get("implication"):
                extra += f'<div class="row"><div class="k">Why it matters</div><div>{E(it["implication"])}</div></div>'
            if it.get("discover"):
                extra += f'<div class="row"><div class="k">How to find out</div><div>{E(it["discover"])}</div></div>'
            items.append(f"""<div class="qa" id="{E(it['id'])}">
<div class="q">{E(it['id'])} · {it['q']} {badge(it['status'], status_cls.get(it['status'], 'info'))}</div>
<div class="a">{it['answer']}</div>
{extra}
<div class="row"><div class="k">Sources</div><div><ul class="small" style="margin:0;padding-left:18px">{srcs or '<li class="empty">none — unanswered</li>'}</ul></div></div>
</div>""")
        sections.append(f'<h2 id="{E(g["id"])}">{E(g["title"])}</h2>' + "".join(items))

    body = f"""
<h1>Questions that must be answered before deciding</h1>
<p class="lede">{E(q.get("intro", ""))}</p>
<div class="grid c2" style="margin:14px 0">
  <div class="card"><h3>{total} questions · status at a glance</h3>
  <div class="rowwrap">{''.join(f'<div class="kpi" style="flex:1;min-width:120px"><div class="label">{k}</div><div class="value">{v}</div></div>' for k, v in counts.items())}</div>
  <p class="small muted" style="margin-top:12px">A question is never marked answered without a link to the official page or the API response that answers it. Where an answer could only come from a human with a Kalshi login, it is marked BLOCKED rather than guessed.</p></div>
  <div class="card"><h3>Status meanings</h3><table><tbody>{legend}</tbody></table></div>
</div>
{''.join(sections)}
"""
    page("questions.html", "Questions", body, active="questions.html")


# --------------------------------------------------------------------------
# Suggestions
# --------------------------------------------------------------------------
def page_suggestions():
    s = load("suggestions.json")
    gate = "".join(f"<li>{E(g)}</li>" for g in s.get("decision_gate") or [])
    cards = []
    for it in s.get("items") or []:
        opts = "".join(
            f'<div style="margin:8px 0"><label style="display:flex;gap:8px;align-items:flex-start;cursor:pointer">'
            f'<input type="radio" name="pick-{E(it["id"])}" value="{E(o["id"])}">'
            f'<span><b>{E(o["label"])}</b>{badge("recommended", "yes") if o["label"] == it.get("recommendation") or o["id"] == it.get("recommendation") else ""}'
            f'<div class="small">{E(o["detail"])}</div>'
            f'<div class="small muted">Trade-off: {E(o["risk"])}</div></span></label></div>'
            for o in it.get("options") or [])
        unlocks = "".join(f'<li>{E(u)}</li>' for u in it.get("unlocks") or [])
        cards.append(f"""<div class="sug" id="{E(it['id'])}">
<h4>{E(it['id'])} · {E(it['title'])}</h4>
<div class="meta">{badge("needs your decision", "warn")}{badge("nothing implemented yet", "info")}</div>
<p class="small"><b>Problem.</b> {E(it['problem'])}</p>
{opts}
<p class="small" style="margin-top:10px"><b>Recommendation.</b> {E(it.get('recommendation') or '—')}<br><span class="muted">{E(it.get('why') or '')}</span></p>
{f'<p class="small"><b>Unlocks.</b></p><ul class="small">{unlocks}</ul>' if unlocks else ''}
<div class="decision" id="dec-{E(it['id'])}">Your lean: <b>not recorded</b></div>
</div>""")
    body = f"""
<h1>Suggestions — review, then choose</h1>
<p class="lede">{E(s.get('intro', ''))}</p>
<div class="notice"><h4>Decision gate — apply to every card</h4><ol class="small" style="margin:6px 0 0;padding-left:20px">{gate}</ol></div>
<div class="notice warn"><h4>Nothing here has been implemented</h4>These are proposals. Your selections are saved in this browser only (localStorage) so you can come back to them; nothing is transmitted, and no suggestion changes the live pages until someone implements it deliberately.</div>
<div class="controls"><button id="exportPicks" class="ghost">Download my choices as JSON</button><span class="small muted" id="pickStatus"></span></div>
<div class="grid c2">{''.join(cards)}</div>
<h2>How a chosen suggestion becomes a change</h2>
<table><tbody>
<tr><td>1</td><td class="small">Record the choice here (it is stored in your browser, under this site's origin).</td></tr>
<tr><td>2</td><td class="small">Download the JSON and attach it to an issue so the decision is on the record with the reasoning.</td></tr>
<tr><td>3</td><td class="small">Implement behind a small commit; the build validates data and links, so a broken choice fails the deploy.</td></tr>
<tr><td>4</td><td class="small">Anything still unconfirmed goes on <a href="flagged.html">Flagged for Review</a> rather than being asserted.</td></tr>
</tbody></table>
"""
    page("suggestions.html", "Suggestions", body, active="suggestions.html",
         extra_script='<script src="assets/suggestions.js"></script>')


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
def page_verification():
    ep = META.get("endpoints") or {}
    docs = META.get("docs") or {}
    cors = HEALTH.get("cors") or {}
    ep_rows = "".join(f'<tr><td class="tick">{E(k)}</td><td class="small">{ext(v, v)}</td></tr>' for k, v in ep.items())
    doc_rows = "".join(f'<tr><td class="tick">{E(k)}</td><td class="small">{ext(v, v)}</td></tr>' for k, v in docs.items())
    scope_rows = "".join(
        f'<tr><td>{badge(TOPIC_META[t["id"]]["title"], TOPIC_META[t["id"]]["cls"])}</td><td class="small">{E(t["rule"])}</td>'
        f'<td class="small">{"<br>".join(ext(q, q) for q in ((D.get("scope") or {}).get("series_queries") or {}).get(t["id"], []) if q) or "—"}</td></tr>'
        for t in (D.get("scope") or {}).get("topics") or [])
    errs = META.get("request_errors") or []
    err_html = "".join(f'<tr><td class="small">{ext(e.get("url"), e.get("url"))}</td><td class="num">{e.get("status")}</td><td class="small">{E(str(e.get("detail"))[:200])}</td></tr>' for e in errs)

    checks = [
        ("Every table row links to the Kalshi API response it came from", "Enforced by tools/validate_data.py on every deploy; a row without a source_url fails the build."),
        ("No number is inferred", "Prices, volumes and results are copied as strings from the JSON. Dollar figures are contracts × last price and are labelled."),
        ("Blank means the API returned nothing", "Missing fields stay null and render as an em dash. Nothing is imputed or carried over from another field."),
        ("Demo data is labelled as demo", "The demo banner appears on every page; Kalshi's caveat is quoted verbatim."),
        ("Snapshot freshness", "The validator refuses to publish a snapshot older than 6 hours; the collection time is printed in the header of every page."),
        ("Price range sanity", "Every price field must be within $0.00–$1.00 or the build fails."),
        ("Internal links and anchors", "tools/check_site.py resolves every internal link and #anchor before deploy."),
    ]
    check_rows = "".join(f"<tr><td>{E(a)}</td><td class=\"small\">{E(b)}</td></tr>" for a, b in checks)

    body = f"""
<h1>Verification</h1>
<p class="lede">How each claim on this site is checked, what the collector actually calls, and what the checks do not cover. If you only read one section, read <b>What is not verified</b> at the bottom.</p>
{src_line()}

<h2>Automated checks run on every build</h2>
<div class="tablewrap"><table><thead><tr><th>Check</th><th>What it does</th></tr></thead><tbody>{check_rows}</tbody></table></div>

<h2>Endpoints called by the collector</h2>
<div class="tablewrap"><table><thead><tr><th>Name</th><th>URL pattern</th></tr></thead><tbody>{ep_rows}</tbody></table></div>
<p class="small muted">All are public GET requests; no authentication, no credentials. Official documentation for each:</p>
<div class="tablewrap"><table><thead><tr><th>Topic</th><th>Official page</th></tr></thead><tbody>{doc_rows}</tbody></table></div>

<h2>Scope queries — exactly what was asked</h2>
<div class="tablewrap"><table><thead><tr><th>Topic</th><th>Rule</th><th>Query</th></tr></thead><tbody>{scope_rows}</tbody></table></div>

<h2>Browser access (CORS) check</h2>
<table><tbody>
<tr><td>Probe URL</td><td class="small">{ext(cors.get("probe_url"), cors.get("probe_url"))}</td></tr>
<tr><td>Origin sent</td><td class="small"><code>{E(str(cors.get("probe_origin") or ""))}</code></td></tr>
<tr><td>HTTP status</td><td class="num">{cors.get("status") or "—"}</td></tr>
<tr><td>access-control-allow-origin</td><td class="small"><code>{E(str(cors.get("access_control_allow_origin") or "—"))}</code></td></tr>
<tr><td>Cache-Control</td><td class="small"><code>{E(str(cors.get("cache_control") or "—"))}</code></td></tr>
</tbody></table>
<p class="small muted">A reflective allow-origin means a browser on the Pages origin may call the public API directly. This is why the live tables and chart work without a proxy.</p>

<h2>Exchange status at collection</h2>
<pre class="small" style="background:#f6f8fb;border:1px solid #dde4ec;border-radius:8px;padding:10px;overflow:auto">{E(json.dumps(HEALTH.get("exchange_status"), indent=1))}</pre>

<h2>Collection errors</h2>
{('<div class="tablewrap"><table><thead><tr><th>Request</th><th>Status</th><th>Detail</th></tr></thead><tbody>' + err_html + '</tbody></table></div>') if errs else '<p class="small">No request errors in this run.</p>'}
<p class="small muted">{META.get("https_requests", 0)} requests issued · throttle events (HTTP 429) observed: <b>{META.get("throttle_events_429", 0)}</b> · final spacing between request starts: {META.get("final_request_interval_s", "—")} s.</p>
<p class="small muted">Kalshi does not publish the size of the unauthenticated budget. It documents that public endpoints “charge your IP address’s budget first”, that a 429 carries <b>no</b> X-RateLimit headers when the response is publicly cacheable (which market data is), and that a 429 has no penalty or cooldown. The collector therefore spaces requests adaptively: it widens the gap on every 429 and narrows it slowly as calls succeed. The number above is the observed consequence, not a setting.</p>

<h2>How a settled market is attributed to a topic</h2>
<div class="notice"><h4>One documented approximation, stated plainly</h4>
Open markets are queried per series (<code>/markets?series_ticker=…</code>), so their series is exact.
Settled markets are queried once per run with <code>/markets?status=settled</code>, which returns no
series field; each settled market is attributed to the series whose ticker matches its
<code>event_ticker</code> prefix (the event ticker is <code>SERIES-EVENT</code> by Kalshi's own naming).
A settled market whose prefix matches no collected series is <b>dropped rather than guessed</b>, so the
resolved count is a lower bound. Row-level source links still point at the exact market and the query
that returned it.</div>

<h2>Series breadth actually collected</h2>
<p class="small muted">Each topic is capped at {META.get("limits", {}).get("max_series_per_topic", 40)} series per run so the job finishes inside a scheduled slot. Where a topic has more series than that, the number skipped is listed here — it is never silently dropped.</p>
<div class="tablewrap"><table><thead><tr><th>Topic</th><th class="num">Series skipped</th></tr></thead><tbody>
{''.join(f'<tr><td>{badge(TOPIC_META[t]["title"], TOPIC_META[t]["cls"])}</td><td class="num">{n}</td></tr>' for t, n in (D.get("series_truncated_per_topic") or {}).items() if t in TOPIC_META)}
</tbody></table></div>

<h2>What is not verified</h2>
<table><tbody>
<tr><td class="small">Authentication, portfolio endpoints, order placement</td><td class="small">No key exists, so none of these were exercised. Anything they return is unknown here. <a href="questions.html#Q16">Q16</a></td></tr>
<tr><td class="small">WebSocket streaming from a browser</td><td class="small">Not tested. The chart uses REST polling. <a href="questions.html#Q12">Q12</a>, <a href="suggestions.html#S4">S4</a></td></tr>
<tr><td class="small">Unauthenticated rate limits</td><td class="small">Kalshi does not publish numbers; the header values observed are shown above where present. <a href="flagged.html">F-11</a></td></tr>
<tr><td class="small">Historical cutoffs</td><td class="small">Not read in this run, so archival proximity per market is unknown. <a href="questions.html#Q8">Q8</a></td></tr>
<tr><td class="small">Older snapshots in the repo</td><td class="small"><code>data/kalshi_snapshot.json</code> is from an earlier session and is not used by this site. Its provenance is recorded, not re-verified. <a href="flagged.html">F-13</a></td></tr>
</tbody></table>
"""
    page("verification.html", "Verification", body, active="verification.html")


# --------------------------------------------------------------------------
# Repo review
# --------------------------------------------------------------------------
def page_repo_review():
    r = load("repo_review.json")
    rows = "".join(
        f'<tr><td><b>{E(f["area"])}</b><div class="small muted tick">{E(f["file"])}</div></td>'
        f'<td class="small">{E(f["claim"])}</td><td class="small">{E(f["official"])}</td>'
        f'<td>{badge(f["verdict"].split("—")[0].strip(), "yes" if f["verdict"].startswith("MATCH") else "warn")}'
        f'<div class="small muted">{E(f["verdict"])}</div></td>'
        f'<td class="small">{"<br>".join(ext(s["url"], s["name"]) for s in f.get("sources") or [])}</td></tr>'
        for f in r.get("repo_findings") or [])
    links = "".join(f'<tr><td class="small">{ext(l["url"], l["url"])}</td><td class="small">{E(l["result"])}</td></tr>'
                    for l in r.get("link_checks") or [])
    irr = "".join(f"<li>{E(i)}</li>" for i in r.get("irregularities_summary") or [])
    body = f"""
<h1>Repository review</h1>
<p class="lede">{E(r.get('intro', ''))}</p>
<div class="notice"><h4>Summary of irregularities</h4><ul class="small" style="margin:6px 0 0;padding-left:20px">{irr}</ul></div>

<h2>Claim-by-claim check against official documentation</h2>
<div class="tablewrap"><table><thead><tr><th>Area / file</th><th>What the file claims</th><th>What the official source says</th><th>Verdict</th><th>Sources</th></tr></thead><tbody>{rows}</tbody></table></div>

<h2>Documentation links checked</h2>
<div class="tablewrap"><table><thead><tr><th>URL</th><th>Result of this session's check</th></tr></thead><tbody>{links}</tbody></table></div>
<p class="small muted">“FETCHED” means the page was retrieved and read during this session. “REFERENCED” means the page is cited but was not the subject of a full read here — treat its details as unverified until checked.</p>

<h2>Repository history reviewed</h2>
<table><tbody>
<tr><td>Branches</td><td class="small">main plus one Arena session branch per session; every session published through a pull request.</td></tr>
<tr><td>Pull requests</td><td class="small">#1–#5 and #7 merged; #6 open (credential-removal) — see <a href="flagged.html">F-08</a>. {ext("https://github.com/karagemop466-tech/Demo2/pulls", "Pull requests")}</td></tr>
<tr><td>Deployment</td><td class="small">GitHub Pages, legacy build from main / then a custom Actions workflow. {ext("https://github.com/karagemop466-tech/Demo2/actions", "Action runs")}</td></tr>
<tr><td>Data files</td><td class="small"><code>data/kalshi_snapshot.json</code> (earlier session, 24 rows) and <code>data/dashboard.json</code> (this site, rebuilt every 15 minutes). Only the latter is used here.</td></tr>
</tbody></table>
"""
    page("repo-review.html", "Repo Review", body, active="repo-review.html")


# --------------------------------------------------------------------------
# Flagged for review
# --------------------------------------------------------------------------
def page_flagged():
    f = load("flags.json")
    cols = f.get("columns") or ["#", "Kind", "What was found", "Impact", "Status", "Evidence"]
    head = "".join(f"<th>{E(c)}</th>" for c in cols)
    rows = ""
    for it in f.get("items") or []:
        ev = "<br>".join(ext(e["url"], e["name"]) for e in it.get("evidence") or [])
        rows += (f'<tr><td class="tick"><b>{E(it["id"])}</b></td>'
                 f'<td>{badge(it["kind"], "warn" if it["kind"] == "DATA" else "info")}</td>'
                 f'<td class="small">{E(it["found"])}</td><td class="small">{E(it["impact"])}</td>'
                 f'<td class="small">{E(it["status"])}</td><td class="small">{ev}</td></tr>')
    body = f"""
<h1>Flagged for Review</h1>
<p class="lede">{E(f.get('intro', ''))}</p>
<div class="notice warn"><h4>These do not block publication — they block certainty</h4>Everything here is either a property of Kalshi's demo data or a real problem in this repository's history. Each row links to the evidence so you can check it yourself and decide what to change.</div>
<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>
<h2>What to do with this page</h2>
<table><tbody>
<tr><td>1</td><td class="small">Pick the items you care about; DATA items mostly need a decision recorded on <a href="suggestions.html">Suggestions</a>.</td></tr>
<tr><td>2</td><td class="small">REPO items need a change in files owned by earlier sessions — deliberately not edited here, so nothing another session relies on disappears.</td></tr>
<tr><td>3</td><td class="small">If a value looks wrong, open the linked API response; if it matches, the API is the source of truth and the flag is a note about the data, not an error in the site.</td></tr>
</tbody></table>
"""
    page("flagged.html", "Flagged for Review", body, active="flagged.html")


def main():
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    page_index()
    for tid in TOPIC_META:
        page_topic(tid)
    page_live()
    page_resolved()
    page_portfolio()
    page_analysis()
    page_questions()
    page_suggestions()
    page_verification()
    page_repo_review()
    page_flagged()
    print("built pages in", OUT)


if __name__ == "__main__":
    main()
