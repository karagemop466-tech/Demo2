#!/usr/bin/env python3
"""Build session-8b9a46b4 site pages from jumps.json / backtest.json (data-driven, no hard-coded values)."""
import html, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = HERE / "data"; SITE = HERE / "site"; SITE.mkdir(exist_ok=True)
jumps = json.loads((DATA / "jumps.json").read_text())
bt = json.loads((DATA / "backtest.json").read_text())
def src_link(url, label):
    """Link real URLs; render endpoint *patterns* as code (a '{placeholder}' href
    is not reachable). Integration fix, session bdb4d2d0 - found by
    tools/check_live_links.py."""
    if "{" in url:
        return f"<code>{esc(label)}</code>"
    return f'<a href="{esc(url)}">{esc(label)}</a>'


NAV = [("index.html","Executive summary"),("jumps.html","Sharp jumps & live chart"),
       ("strategies.html","Simulated strategies"),("flagged.html","Flagged for review"),
       ("verification.html","Verification")]
def esc(x): return html.escape(str(x))
def page(title, body):
    nav = " · ".join(f'<a href="{h}">{t}</a>' for h, t in NAV)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{esc(title)} — Kalshi Demo (session 8b9a46b4)</title>
<link rel="stylesheet" href="style.css"></head><body>
<header><h1>Kalshi Demo — sharp jumps & simulated strategies</h1><nav>{nav}</nav>
<p class="disc">Demo environment only · mock funds · not investment advice · session arena-8b9a46b4</p></header>
<main>{body}</main><footer><p>Data: <a href="../../data/dashboard_instrument.json">data/dashboard_instrument.json</a>
(collected from the official demo API). Every row links its source. Blank = unverified.</p></footer>
</body></html>"""

# ---- index: executive summary ----
rows = "".join(
 f"<tr><td>{esc(j['ticker'])}</td><td>{esc(j['to_time'])}</td><td>${j['from_yes_price']:.2f} → ${j['to_yes_price']:.2f}</td>"
 f"<td>{j['delta']:+.2f}</td><td>{esc(j['direction'])}</td>"
 f"<td>{'— (blank, unverified)' if not j['cause_news_url'] else esc(j['cause_news_url'])}</td>"
 f"<td><a href=\"{esc(j['source_url'])}\">source</a></td></tr>" for j in jumps["jumps"][:10])
index_body = f"""
<h2>Executive summary</h2>
<p>Scope: five topics only — <b>gas prices, elections, culture, crypto, golf</b> — on the Kalshi
<b>demo</b> API (<a href="https://docs.kalshi.com/getting_started/demo_env">docs</a>).
This subsite adds two things the main site did not have: a <b>sharp-jump detector</b>
(consecutive trade prints moving ≥ $0.10) and a <b>simulated strategy backtest</b> on
resolved demo markets that actually traded. Everything else (rankings, resolutions,
portfolio gating) is already covered by the main site and is linked, not duplicated.</p>
<table><tr><th>Finding</th><th>Value</th><th>Source</th></tr>
<tr><td>Trade prints scanned for jumps</td><td>{jumps['prints_scanned']:,} across {jumps['markets_scanned']} markets</td><td>{src_link(jumps['source_url'], 'GET /markets/trades')}</td></tr>
<tr><td>Sharp jumps (≥ $0.10)</td><td>{jumps['jump_count']}</td><td><a href="../data/jumps.json">jumps.json</a></td></tr>
<tr><td>Resolved markets collected</td><td>{bt['population']['resolved_collected']:,}</td><td>{src_link(bt['source_url'], 'GET /markets (settled)')}</td></tr>
<tr><td>Of which ever traded (backtest population)</td><td>{bt['population']['traded_and_priced']}</td><td><a href="../data/backtest.json">backtest.json</a></td></tr>
<tr><td>Snapshot generated</td><td>{esc(jumps['generated_at'])}</td><td><a href="../../data/dashboard_instrument.json">snapshot</a></td></tr></table>
<h3>Most recent jumps</h3><table><tr><th>Ticker</th><th>Time (UTC)</th><th>YES price</th><th>Δ</th><th>Dir.</th><th>Cause / news link</th><th>Source</th></tr>{rows}</table>
<p><b>Key caveat:</b> {esc(bt['caveat'])} The large always-NO profit reflects that most traded demo
markets resolved NO at low final prices (documented calibration effect on the main site) — it is
<b>not</b> evidence of a tradable edge. See <a href="strategies.html">Simulated strategies</a>.</p>
<p><b>Suggestions to make the site more live/interactive</b> (proposals only, nothing implemented
beyond this page): (1) auto-refresh jump table from the 10-minute data pipeline; (2) WebSocket
ticker tape — note WS requires auth headers even for public data
(<a href="https://docs.kalshi.com/getting_started/quick_start_websockets">docs</a>), so a small
backend proxy is needed; (3) one-click jump → candlestick chart deep link; (4) alert badge when a
jump ≥ $0.10 prints on a watched ticker; (5) consolidate the four parallel dashboards into one nav.</p>"""

# ---- jumps page ----
jrows = "".join(
 f"<tr><td>{esc(j['ticker'])}</td><td>{esc(j['from_time'])}</td><td>{esc(j['to_time'])}</td>"
 f"<td>${j['from_yes_price']:.2f}</td><td>${j['to_yes_price']:.2f}</td><td>{j['delta']:+.2f}</td>"
 f"<td>{esc(j['direction'])}</td><td>{j['contracts_from'] if j['contracts_from'] is not None else '—'} → {j['contracts_to'] if j['contracts_to'] is not None else '—'}</td>"
 f"<td>— (blank, unverified)</td><td><a href=\"{esc(j['source_url'])}\">source</a></td></tr>" for j in jumps["jumps"])
jumps_body = f"""
<h2>Sharp jumps ≥ $0.10 (consecutive trade prints)</h2>
<p>{jumps['jump_count']} jumps in {jumps['prints_scanned']:,} prints. Cause/news links are
<b>blank</b>: the Kalshi Trade API publishes no news or event-cause field, so any cause would be
inference — flagged on <a href="flagged.html">Flagged for review</a>.</p>
<table><tr><th>Ticker</th><th>From</th><th>To</th><th>YES from</th><th>YES to</th><th>Δ $</th><th>Dir.</th><th>Contracts</th><th>Cause / news</th><th>Source</th></tr>{jrows}</table>
<h2>Live chart (browser → demo API)</h2>
<p>Pick a ticker from the jump table, choose a window, and the chart polls the official demo API
directly from your browser (CORS observed working — see <a href="verification.html">Verification</a>).
X = time, Y = YES contract price. Seconds = trade prints; minutes/hours = candlesticks
(period 1 / 60 min). Orderbook shows contracts available at each price.</p>
<label>Ticker <input id="ticker" size="28" value="{esc(jumps['jumps'][0]['ticker']) if jumps['jumps'] else ''}"></label>
<label>Window <select id="window"><option value="seconds">seconds (prints)</option>
<option value="minutes" selected>minutes (1-min candles)</option><option value="hours">hours (60-min candles)</option></select></label>
<button id="go">Load</button> <span id="status"></span>
<canvas id="chart" width="900" height="320"></canvas>
<h3>Orderbook depth (contracts at each price)</h3><div id="book"></div>
<script src="live.js"></script>"""

# ---- strategies page ----
def srow(name, s):
    return (f"<tr><td>{esc(name)}</td><td>{s['n']}</td><td>{s['total_pnl_per_contract'] if s['total_pnl_per_contract'] is not None else '—'}</td>"
            f"<td>{s['mean_pnl_per_contract'] if s['mean_pnl_per_contract'] is not None else '—'}</td>"
            f"<td>{s['win_rate'] if s['win_rate'] is not None else '—'}</td></tr>")
srows = "".join(srow(k, v) for k, v in bt["overall"].items())
trows = ""
for topic, strat in bt["by_topic"].items():
    for name, s in strat.items():
        trows += f"<tr><td>{esc(topic)}</td>{srow(name, s)}</tr>"
for topic in ("gas", "culture"):
    if topic not in bt["by_topic"]:
        trows += f"<tr><td>{topic}</td><td colspan='4'>— no traded resolved markets in snapshot (blank, unverified)</td></tr>"
strat_body = f"""
<h2>Simulated strategies — SIMULATED, historical demo data</h2>
<p>{esc(bt['caveat'])} Population: {bt['population']['traded_and_priced']} of
{bt['population']['resolved_collected']:,} resolved markets (only those with volume &gt; 0 and a real
final price; never-traded markets return a default 0.0000 and are excluded — see main site flag F-15).
P&L is per 1 contract bought at the final print, settled at $1/$0 by the official <code>result</code>.</p>
<h3>Overall</h3><table><tr><th>Strategy</th><th>n</th><th>Total P&L /contract</th><th>Mean P&L</th><th>Win rate</th></tr>{srows}</table>
<h3>By topic</h3><table><tr><th>Topic</th><th>Strategy</th><th>n</th><th>Total P&L</th><th>Mean P&L</th><th>Win rate</th></tr>{trows}</table>
<p>Reading: always-NO profits because {bt['overall']['always_no']['win_rate']*100:.1f}% of traded markets
resolved NO. This is a calibration observation about demo prices, <b>not</b> a recommendation.
Live demo-account execution requires the user's own API keys and stays behind the existing gated
executor (<code>tools/execute_strategy.py</code>); no keys exist in this workspace.</p>
<p>Source: <a href="../data/backtest.json">backtest.json</a> · {src_link(bt['source_url'], 'GET /markets?status=settled')}</p>"""

flagged_body = """
<h2>Flagged for review</h2>
<table><tr><th>ID</th><th>Item</th><th>Why blank / caveat</th><th>Source</th></tr>
<tr><td>J-F1</td><td>Jump cause / news links</td><td>Kalshi Trade API has no news/event-cause field; left blank, never inferred.</td><td><a href="https://docs.kalshi.com/api-reference/market/get-trades">get-trades docs</a></td></tr>
<tr><td>J-F2</td><td>Backtest entry price</td><td>Final print = lookahead; measures calibration, not tradable entry.</td><td><a href="../data/backtest.json">backtest.json</a></td></tr>
<tr><td>J-F3</td><td>Gas & culture backtest rows</td><td>No traded resolved markets in snapshot for these topics; blank.</td><td><a href="../data/backtest.json">backtest.json</a></td></tr>
<tr><td>J-F4</td><td>Live demo-account portfolio/trades</td><td>Requires user API keys (Ed25519/RSA signing); none in workspace; not fabricated.</td><td><a href="https://docs.kalshi.com/getting_started/api_keys">api_keys docs</a></td></tr>
<tr><td>J-F5</td><td>WebSocket live tape</td><td>WS handshake requires auth headers even for public data; browser-only tape not possible without a backend proxy.</td><td><a href="https://docs.kalshi.com/getting_started/quick_start_websockets">websockets docs</a></td></tr></table>"""

verif_body = f"""
<h2>Verification</h2>
<table><tr><th>Claim</th><th>How checked</th><th>Source</th></tr>
<tr><td>Demo REST base URL</td><td>Read from official docs; snapshot meta records same base</td><td><a href="https://docs.kalshi.com/getting_started/demo_env">demo_env</a></td></tr>
<tr><td>Trade prints endpoint & fields (yes_price_dollars, count_fp, created_time)</td><td>Field names copied verbatim from collected responses</td><td><a href="https://docs.kalshi.com/api-reference/market/get-trades">get-trades</a></td></tr>
<tr><td>Candlestick periods 1/60/1440 min</td><td>Official docs</td><td><a href="https://docs.kalshi.com/api-reference/market/get-market-candlesticks">candlesticks</a></td></tr>
<tr><td>Orderbook [price, count] pairs</td><td>Official docs</td><td><a href="https://docs.kalshi.com/api-reference/market/get-market-orderbook">orderbook</a></td></tr>
<tr><td>Browser CORS from GitHub Pages origin</td><td>Observed by pipeline probe (not assumed)</td><td><a href="../../data/cors.json">data/cors.json</a></td></tr>
<tr><td>Settlement pays $1 / $0 by result</td><td>Official docs</td><td><a href="https://docs.kalshi.com/getting_started/market_settlement">settlement</a></td></tr>
<tr><td>Jump/backtest arithmetic</td><td>Re-run: <code>python3 session-8b9a46b4/tools/jump_backtest.py</code></td><td><a href="../data/jumps.json">jumps.json</a></td></tr></table>"""

(SITE / "index.html").write_text(page("Executive summary", index_body))
(SITE / "jumps.html").write_text(page("Sharp jumps & live chart", jumps_body))
(SITE / "strategies.html").write_text(page("Simulated strategies", strat_body))
(SITE / "flagged.html").write_text(page("Flagged for review", flagged_body))
(SITE / "verification.html").write_text(page("Verification", verif_body))
print("built", len(NAV), "pages")
