/* Kalshi Demo Dashboard — client-side only. No keys are ever requested or stored.
   Field names verified against the official OpenAPI (Get Markets) and docs:
   - prices are *_dollars fixed-point strings; quantities are *_fp contract-count strings
     (https://docs.kalshi.com/getting_started/fixed_point_migration)
   - orderbook_fp.yes_dollars/no_dollars are ascending [price_dollars, count_fp] string
     pairs, best bid LAST; the book contains bids only, asks are implied
     (https://docs.kalshi.com/getting_started/orderbook_responses)
   - the WebSocket API requires signed KALSHI-ACCESS-* handshake headers
     (https://docs.kalshi.com/getting_started/quick_start_websockets), which a browser
     cannot set — so this page streams via REST polling + committed candlesticks only. */
const DEMO_REST = "https://external-api.demo.kalshi.co/trade-api/v2";
const TOPICS = {
  gas: ["gas", "gasoline", "diesel", "gas price", "oil price", "crude"],
  elections: ["election", "president", "senate", "house", "vote", "ballot", "governor", "mayor", "congress", "republican", "democrat", "primary"],
  culture: ["oscar", "grammy", "emmy", "celebrity", "movie", "film", "music", "album", "tv show", "super bowl halftime", "met gala"],
  crypto: ["bitcoin", "btc", "ethereum", "eth", "crypto", "doge", "solana", "xrp"],
  golf: ["golf", "pga", "masters", "us open golf", "ryder", "open championship"]
};
/* Multi-word keywords match as substrings; single words match on word boundaries
   (same rule as tools/collect_kalshi.py, so the dashboard and the tables agree). */
function topicOf(m) {
  const t = ((m.title || "") + " " + (m.subtitle || "") + " " + (m.ticker || "") + " " + (m.event_ticker || "")).toLowerCase();
  for (const [k, keys] of Object.entries(TOPICS)) {
    if (keys.some(x => x.includes(" ") ? t.includes(x) : new RegExp("\\b" + x + "\\b").test(t))) return k;
  }
  return null;
}
function notional(m) {
  const v = parseFloat(m.volume_fp || "0") || 0;
  const p = parseFloat(m.last_price_dollars || "0") || 0;
  return v * p;
}
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function apiLinkFor(m) {
  const u = m.source_url || (DEMO_REST + "/markets/" + encodeURIComponent(m.ticker));
  return '<a href="' + esc(u) + '" target="_blank" rel="noopener">API ↗</a>';
}
async function fetchMarkets() {
  let cursor = "", all = [];
  for (let i = 0; i < 5; i++) {
    const url = DEMO_REST + "/markets?status=open&limit=1000" + (cursor ? ("&cursor=" + encodeURIComponent(cursor)) : "");
    const r = await fetch(url); if (!r.ok) throw new Error("Markets HTTP " + r.status);
    const j = await r.json(); all = all.concat(j.markets || []);
    cursor = j.cursor || ""; if (!cursor) break;
  }
  return all;
}
async function fetchOrderbook(ticker) {
  const r = await fetch(DEMO_REST + "/markets/" + encodeURIComponent(ticker) + "/orderbook");
  if (!r.ok) throw new Error("Orderbook HTTP " + r.status);
  return r.json();
}
async function fetchSettled() {
  let cursor = "", all = [];
  for (let i = 0; i < 3; i++) {
    const url = DEMO_REST + "/markets?status=settled&limit=1000" + (cursor ? ("&cursor=" + encodeURIComponent(cursor)) : "");
    const r = await fetch(url); if (!r.ok) throw new Error("Settled HTTP " + r.status);
    const j = await r.json(); all = all.concat(j.markets || []);
    cursor = j.cursor || ""; if (!cursor) break;
  }
  return all.filter(m => topicOf(m));
}
/* ---- committed snapshot fallback (data/ refreshed by GitHub Actions every 2h) ---- */
async function fetchSnapshot(name) {
  const r = await fetch("data/" + name, { cache: "no-store" });
  if (!r.ok) throw new Error("snapshot " + name + " HTTP " + r.status);
  return r.json();
}
/* ---- chart: live ticks + committed candlesticks (1-min 24h, 60-min 7d) ---- */
const history = {}; // ticker -> [{t, p}]
let candleCache = {}; // ticker -> [{t, p}]
let selectedTicker = null, windowSec = 300, snapshotNote = "";
async function loadCandles(ticker) {
  if (candleCache[ticker]) return candleCache[ticker];
  try {
    const j = await fetchSnapshot("candlesticks.json");
    const rec = (j.rows || {})[ticker];
    const out = [];
    if (rec && rec.periods) {
      for (const key of ["1", "60"]) {
        const per = rec.periods[key]; if (!per) continue;
        for (const c of (per.candlesticks || [])) {
          /* price.close_dollars = last traded YES price in the period (may be null) */
          const cd = c.price && c.price.close_dollars;
          if (cd == null) continue;
          const p = parseFloat(cd), t = (c.end_period_ts || 0) * 1000;
          if (Number.isFinite(p) && t > 0) out.push({ t: t, p: p });
        }
      }
    }
    out.sort((a, b) => a.t - b.t);
    candleCache[ticker] = out;
    return out;
  } catch (e) { candleCache[ticker] = []; return []; }
}
function chartPoints() {
  if (!selectedTicker) return [];
  const now = Date.now(), cut = now - windowSec * 1000;
  const live = (history[selectedTicker] || []).filter(x => x.t >= cut);
  const candles = (candleCache[selectedTicker] || []).filter(x => x.t >= cut && x.t <= now);
  const merged = live.concat(candles);
  merged.sort((a, b) => a.t - b.t);
  return merged;
}
function pushHistory(m) {
  const p = parseFloat(m.last_price_dollars || m.yes_bid_dollars || "0");
  if (!selectedTicker || m.ticker !== selectedTicker || !Number.isFinite(p)) return;
  const now = Date.now();
  (history[m.ticker] = history[m.ticker] || []).push({ t: now, p: p });
  history[m.ticker] = history[m.ticker].filter(x => now - x.t <= Math.max(windowSec, 604800) * 1000);
}
function fmtTick(ts, windowSec) {
  const d = new Date(ts);
  const hh = String(d.getHours()).padStart(2, "0"), mm = String(d.getMinutes()).padStart(2, "0"), ss = String(d.getSeconds()).padStart(2, "0");
  return windowSec <= 3600 ? hh + ":" + mm + ":" + ss : (d.getMonth() + 1) + "/" + d.getDate() + " " + hh + ":" + mm;
}
function drawChart() {
  const c = document.getElementById("priceChart"); if (!c) return;
  const ctx = c.getContext("2d"); const W = c.width = c.clientWidth * 2, H = c.height = 640;
  ctx.clearRect(0, 0, W, H); ctx.fillStyle = "#0d1628"; ctx.fillRect(0, 0, W, H);
  const pts = chartPoints();
  ctx.fillStyle = "#9fb0c8"; ctx.font = "24px system-ui";
  if (pts.length < 2) {
    ctx.fillText("Collecting points… live ticks + candlesticks (select a market; snapshot fallback fills history).", 30, 60);
    return;
  }
  const minP = Math.min(...pts.map(x => x.p)), maxP = Math.max(...pts.map(x => x.p));
  const pad = 0.02, lo = Math.max(0, minP - pad), hi = Math.min(1, maxP + pad);
  const t0 = pts[0].t, t1 = Math.max(pts[pts.length - 1].t, t0 + 1000);
  /* Y axis: price labels */
  ctx.fillStyle = "#9fb0c8"; ctx.font = "22px system-ui";
  for (let i = 0; i <= 4; i++) {
    const y = 40 + (H - 120) * i / 4, val = hi - (hi - lo) * i / 4;
    ctx.fillText("$" + val.toFixed(3), 2, y);
    ctx.strokeStyle = "#22304a"; ctx.beginPath(); ctx.moveTo(60, y); ctx.lineTo(W - 20, y); ctx.stroke();
  }
  /* X axis: time labels */
  for (let i = 0; i <= 4; i++) {
    const x = 60 + (W - 120) * i / 4, ts = t0 + (t1 - t0) * i / 4;
    ctx.fillText(fmtTick(ts, windowSec), x - 40, H - 24);
  }
  ctx.strokeStyle = "#00b67a"; ctx.lineWidth = 3; ctx.beginPath();
  pts.forEach((x, i) => {
    const px = 60 + (W - 120) * (x.t - t0) / (t1 - t0);
    const py = 40 + (H - 120) * (1 - (x.p - lo) / Math.max(0.001, hi - lo));
    i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  });
  ctx.stroke();
  ctx.fillStyle = "#e8eef7"; ctx.font = "24px system-ui";
  ctx.fillText("Y: contract price ($) · X: time · window " + (windowSec >= 3600 ? (windowSec / 3600) + "h" : (windowSec / 60) + "m") + " · last $" + pts[pts.length - 1].p.toFixed(3), 60, 30);
}
/* ---- render ---- */
let liveMarkets = [];
async function refresh() {
  const el = document.getElementById("liveStatus"); if (el) el.textContent = "Fetching demo markets…";
  try {
    const all = await fetchMarkets();
    liveMarkets = all.filter(m => topicOf(m)).sort((a, b) => notional(b) - notional(a));
    snapshotNote = "";
    if (el) el.innerHTML = "<span class='ok'>Live:</span> " + liveMarkets.length + " in-scope open markets (of " + all.length + " open). Updated " + new Date().toLocaleTimeString();
    renderTable(liveMarkets.slice(0, 50));
    if (liveMarkets.length && !selectedTicker) { selectedTicker = liveMarkets[0].ticker; const ti = document.getElementById("tickerInput"); if (ti) ti.value = selectedTicker; }
    liveMarkets.forEach(pushHistory);
  } catch (e) {
    /* Live fetch failed (network/CORS) — fall back to the committed verified snapshot. */
    try {
      const snap = await fetchSnapshot("markets_open.json");
      const rows = (snap.rows || []).map(r => ({
        ticker: r.ticker, title: r.title, subtitle: r.topic_label || "", event_ticker: r.series_ticker || "",
        volume_fp: r.volume_fp, last_price_dollars: r.last_price_dollars, yes_bid_dollars: r.yes_bid_dollars,
        yes_ask_dollars: r.yes_ask_dollars, close_time: r.close_time, source_url: r.source_url,
        _topic: (r.topic || "").replace("gas-prices", "gas")
      }));
      liveMarkets = rows.filter(m => topicOf(m) || m._topic).sort((a, b) => notional(b) - notional(a));
      snapshotNote = "Snapshot collected " + (snap.collected_at || "unknown") + " UTC by tools/collect_kalshi.py (GitHub Actions).";
      if (el) el.innerHTML = "<span class='warn'>Live API unavailable (" + esc(e.message) + ") — showing committed snapshot.</span> " + esc(snapshotNote);
      renderTable(liveMarkets.slice(0, 50));
      if (liveMarkets.length && !selectedTicker) { selectedTicker = liveMarkets[0].ticker; const ti = document.getElementById("tickerInput"); if (ti) ti.value = selectedTicker; }
    } catch (e2) {
      if (el) el.innerHTML = "<span class='bad'>Live fetch failed:</span> " + esc(e.message) + " — and no committed snapshot is present. No values are fabricated; tables stay empty.";
    }
  }
  if (selectedTicker) await loadCandles(selectedTicker);
  drawChart();
  const note = document.getElementById("chartNote");
  if (note) note.textContent = snapshotNote
    ? "Chart history: committed candlesticks + this session's ticks. " + snapshotNote
    : "Chart history: committed candlesticks (1-min/24h, 60-min/7d) + live ticks from this session. Live quotes are cached by Kalshi and can lag several seconds (Get Markets docs).";
}
function renderTable(rows) {
  const tb = document.querySelector("#marketsTable tbody"); if (!tb) return;
  tb.innerHTML = rows.map(m => {
    const topic = m._topic || topicOf(m);
    return "<tr><td><button class='secondary' data-t='" + esc(m.ticker) + "'>Chart</button></td><td>" + esc(m.ticker) + " " + apiLinkFor(m) + "</td><td>" + esc(m.title || "") + "</td><td><span class='pill'>" + esc(topic) + "</span></td><td>$" + esc(m.last_price_dollars || "—") + "</td><td>" + esc(m.volume_fp || "—") + "</td><td>$" + notional(m).toFixed(2) + "</td><td>" + esc(m.yes_bid_dollars || "—") + " / " + esc(m.yes_ask_dollars || "—") + "</td><td>" + esc(m.close_time || "—") + "</td></tr>";
  }).join("") || "<tr><td colspan='9'>No in-scope markets in the current data.</td></tr>";
  tb.querySelectorAll("button[data-t]").forEach(b => b.onclick = () => {
    selectedTicker = b.dataset.t; const ti = document.getElementById("tickerInput"); if (ti) ti.value = selectedTicker;
    loadOrderbook(); loadCandles(selectedTicker).then(drawChart);
  });
}
async function loadOrderbook() {
  const ti = document.getElementById("tickerInput"); if (!ti) return;
  const t = ti.value.trim(); if (!t) return;
  const box = document.getElementById("orderbookBox"); if (!box) return;
  box.textContent = "Loading orderbook…";
  /* Bids-only book: implied YES ask = $1.00 - best NO bid (orderbook_responses docs). */
  try {
    const j = await fetchOrderbook(t);
    const yes = (j.orderbook_fp && j.orderbook_fp.yes_dollars) || [], no = (j.orderbook_fp && j.orderbook_fp.no_dollars) || [];
    const bestYes = yes.length ? yes[yes.length - 1] : null, bestNo = no.length ? no[no.length - 1] : null;
    const implied = bestNo ? (1 - parseFloat(bestNo[0])).toFixed(4) : null;
    box.innerHTML =
      (bestYes ? "<p>Best YES bid <b>$" + esc(bestYes[0]) + "</b> · implied YES ask <b>" + (implied ? "$" + implied : "—") + "</b> (= $1.00 − best NO bid)</p>" : "<p>No resting bids.</p>") +
      "<h4>YES bids (price → contracts)</h4><table><tr><th>Price</th><th>Contracts available</th></tr>" + yes.slice(-10).reverse().map(r => "<tr><td>$" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td></tr>").join("") + "</table>" +
      "<h4>NO bids (price → contracts)</h4><table><tr><th>Price</th><th>Contracts available</th></tr>" + no.slice(-10).reverse().map(r => "<tr><td>$" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td></tr>").join("") + "</table>" +
      "<p class='muted'>Book contains bids only; asks are implied (official orderbook docs). <a href='https://docs.kalshi.com/getting_started/orderbook_responses' target='_blank' rel='noopener'>Schema ↗</a></p>";
  } catch (e) {
    /* Snapshot fallback for the orderbook */
    try {
      const j = await fetchSnapshot("orderbooks.json");
      const rec = (j.rows || {})[t];
      if (!rec) throw e;
      const yes = rec.yes || [], no = rec.no || [];
      box.innerHTML = "<p class='warn'>Live orderbook unavailable — committed snapshot (collected " + esc(j.collected_at || "?") + " UTC). <a href='" + esc(rec.source_url || "#") + "' target='_blank' rel='noopener'>API ↗</a></p>" +
        "<h4>YES bids</h4><table><tr><th>Price</th><th>Contracts available</th></tr>" + yes.slice(-10).reverse().map(r => "<tr><td>$" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td></tr>").join("") + "</table>" +
        "<h4>NO bids</h4><table><tr><th>Price</th><th>Contracts available</th></tr>" + no.slice(-10).reverse().map(r => "<tr><td>$" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td></tr>").join("") + "</table>";
    } catch (e2) {
      box.innerHTML = "<span class='bad'>Orderbook failed:</span> " + esc(e.message);
    }
  }
}
/* Authenticated account access and order submission are intentionally omitted from
   this public static client (see pages/portfolio.html and pages/flagged.html F6).
   Use tools/kalshi_trade.py locally with your own demo key instead. */
async function loadResolved() {
  const tb = document.querySelector("#resolvedTable tbody"); if (!tb) return;
  const rowHtml = m => "<tr><td>" + esc(m.ticker) + " " + (m.source_url ? apiLinkFor(m) : "") + "</td><td>" + esc(m.title || "") + "</td><td><span class='pill'>" + esc(m._topic || topicOf(m)) + "</span></td><td>" + esc(m.result || "—") + "</td><td>" + esc(m.settlement_value_dollars || "—") + "</td><td>" + esc(m.settlement_ts || "—") + "</td></tr>";
  try {
    const rows = (await fetchSettled()).slice(0, 50);
    tb.innerHTML = rows.map(rowHtml).join("") || "<tr><td colspan='6'>No settled in-scope markets in latest page.</td></tr>";
  } catch (e) {
    try {
      const snap = await fetchSnapshot("markets_settled.json");
      const rows = (snap.rows || []).slice(0, 50).map(r => ({
        ticker: r.ticker, title: r.title, result: r.result, settlement_value_dollars: r.settlement_value_dollars,
        settlement_ts: r.settlement_ts, source_url: r.source_url,
        _topic: (r.topic || "").replace("gas-prices", "gas")
      }));
      tb.innerHTML = rows.map(rowHtml).join("") || "<tr><td colspan='6'>Snapshot has no settled in-scope rows.</td></tr>";
    } catch (e2) {
      tb.innerHTML = "<tr><td colspan='6'><span class='bad'>Failed:</span> " + esc(e.message) + " (no committed snapshot either)</td></tr>";
    }
  }
}
function wsNotAvailable() {
  const el = document.getElementById("wsStatus");
  if (el) el.innerHTML = "<span class='muted'>WebSocket streaming is not possible in a browser client: the WS handshake requires signed KALSHI-ACCESS-* headers (<a href='https://docs.kalshi.com/getting_started/quick_start_websockets' target='_blank' rel='noopener'>WebSocket quick start ↗</a>). REST polling + candlesticks are used instead.</span>";
}
document.addEventListener("DOMContentLoaded", () => {
  const r = document.getElementById("refreshBtn"); if (r) r.onclick = refresh;
  const o = document.getElementById("loadObBtn"); if (o) o.onclick = loadOrderbook;
  const w = document.getElementById("windowSel"); if (w) w.onchange = () => { windowSec = parseInt(w.value, 10); drawChart(); };
  const t = document.getElementById("tickerInput"); if (t) t.onchange = () => { selectedTicker = t.value.trim(); loadOrderbook(); loadCandles(selectedTicker).then(drawChart); };
  wsNotAvailable();
  refresh(); loadResolved();
  setInterval(refresh, 15000);
});
