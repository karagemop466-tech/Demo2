/* Kalshi Demo Intelligence — shared app helpers */
(function () {
  "use strict";

  const API = "https://external-api.demo.kalshi.co/trade-api/v2";
  const DOCS = "https://docs.kalshi.com";

  const state = {
    live: null,        // null = untested, true/false once probed
    snapshot: null,
    watchlist: null,
    lastProbe: null
  };

  async function fetchJSON(url, ms) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), ms || 9000);
    try {
      const res = await fetch(url, { signal: ctrl.signal, headers: { "Accept": "application/json" } });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const j = await res.json();
      return j;
    } finally { clearTimeout(t); }
  }

  async function probeLive() {
    if (state.live !== null) return state.live;
    try {
      await fetchJSON(API + "/exchange/status", 7000);
      state.live = true;
    } catch (e) {
      state.live = false;
      state.probeError = String(e && e.message || e);
    }
    state.lastProbe = new Date().toISOString();
    return state.live;
  }

  async function getSnapshot() {
    if (!state.snapshot) state.snapshot = await fetchJSON("data/snapshot.json", 8000);
    return state.snapshot;
  }
  async function getWatchlist() {
    if (!state.watchlist) state.watchlist = await fetchJSON("data/watchlist.json", 8000);
    return state.watchlist;
  }

  function setModeBadge(el) {
    if (!el) return;
    probeLive().then(ok => {
      el.className = "badge " + (ok ? "live" : "snapshot");
      el.innerHTML = ok
        ? '<span class="dot"></span> <b>LIVE</b> demo API reachable — runtime polling active'
        : '<b>SNAPSHOT</b> ' + (state.probeError ? "· live API blocked from this browser (" + esc(state.probeError) + ")" : "· bundled verified data");
      el.title = "Probe time: " + state.lastProbe + " — " + API + "/exchange/status";
    });
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function num(v) {
    if (v === "" || v == null) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  function fmtInt(v) { const n = num(v); return n == null ? "" : n.toLocaleString("en-US", { maximumFractionDigits: 2 }); }
  function fmtUsd(v) { const n = num(v); return n == null ? "" : "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function fmtPrice(v) { const n = num(v); return n == null ? "" : "$" + n.toFixed(4).replace(/0+$/, "").replace(/\.$/, ".00"); }
  function fmtTs(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? String(iso) : d.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
  }
  function fmtEpoch(sec) {
    const d = new Date(Number(sec) * 1000);
    return Number.isNaN(d.getTime()) ? String(sec) : d.toISOString().replace("T", " ").replace("Z", "");
  }

  // Source cell: always a link to an official URL
  function srcCell(url, label) {
    if (!url) return '<td class="blank">— unverified (no source)</td>';
    return '<td><a class="src-link" href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(label || shortUrl(url)) + "</a></td>";
  }
  function shortUrl(u) {
    try {
      const x = new URL(u, location.href);
      const p = x.pathname.replace("/trade-api/v2", "") + (x.search || "");
      return (x.hostname.includes("kalshi") ? "" : x.host) + p;
    } catch (e) { return u; }
  }

  // Generic table renderer. columns: [{k, label, cls, fmt(row)->html optional, src: row=>url}]
  function renderTable(tbodyEl, columns, rows) {
    const html = rows.map(row => {
      return "<tr>" + columns.map(c => {
        if (c.src) return srcCell(c.src(row), c.srcLabel);
        const v = c.fmt ? c.fmt(row) : esc(row[c.k]);
        const cls = c.cls ? ' class="' + c.cls + '"' : "";
        const blank = (v === "" || v == null) && c.blankFlag ? ' class="blank"' : "";
        return "<td" + (cls || blank) + ">" + (v === "" || v == null ? (c.blankFlag ? "— blank (unverified)" : "") : v) + "</td>";
      }).join("") + "</tr>";
    }).join("");
    tbodyEl.innerHTML = html;
  }

  function topicPill(t) {
    if (!t) return '<span class="pill">—</span>';
    return '<span class="pill topic">' + esc(t) + "</span>";
  }
  function resultPill(r) {
    if (r === "yes") return '<span class="pill yes">YES</span>';
    if (r === "no") return '<span class="pill no">NO</span>';
    if (r === "scalar") return '<span class="pill">scalar</span>';
    return '<span class="pill">unresolved</span>';
  }

  // ---- Live data pullers (used by dashboard; all public endpoints, no auth) ----
  // Pull open events with nested markets for a set of series tickers (paged per series).
  async function pullSeriesMarkets(seriesTickers, opts) {
    opts = opts || {};
    const out = [];
    for (const s of seriesTickers) {
      try {
        const j = await fetchJSON(API + "/events?series_ticker=" + encodeURIComponent(s) +
          "&status=open&with_nested_markets=true&limit=200" + (opts.cursor ? "&cursor=" + encodeURIComponent(opts.cursor) : ""), 10000);
        for (const ev of (j.events || [])) {
          out.push(ev);
        }
      } catch (e) { /* series error tolerated; caller shows partial */ }
      if (opts.pause) await new Promise(r => setTimeout(r, opts.pause));
    }
    return out;
  }

  async function pullOrderbook(ticker) {
    return fetchJSON(API + "/markets/" + encodeURIComponent(ticker) + "/orderbook", 8000);
  }
  async function pullTrades(ticker, limit) {
    return fetchJSON(API + "/markets/trades?ticker=" + encodeURIComponent(ticker) + "&limit=" + (limit || 200), 8000);
  }
  async function pullCandles(seriesTicker, marketTicker, period, startTs, endTs) {
    return fetchJSON(API + "/series/" + encodeURIComponent(seriesTicker) + "/markets/" + encodeURIComponent(marketTicker) +
      "/candlesticks?period_interval=" + period + "&start_ts=" + startTs + "&end_ts=" + endTs, 9000);
  }
  async function pullMarketsBySeries(seriesTicker) {
    return fetchJSON(API + "/markets?series_ticker=" + encodeURIComponent(seriesTicker) + "&status=open&limit=1000", 10000);
  }

  window.KDS = {
    API, DOCS, state, fetchJSON, probeLive, getSnapshot, getWatchlist, setModeBadge,
    esc, num, fmtInt, fmtUsd, fmtPrice, fmtTs, fmtEpoch, srcCell, shortUrl,
    renderTable, topicPill, resultPill,
    pullSeriesMarkets, pullOrderbook, pullTrades, pullCandles, pullMarketsBySeries
  };
})();
