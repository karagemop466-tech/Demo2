/* Kalshi demo dashboard - live price chart and orderbook.
 * Public (unauthenticated) GET requests only. No credentials are ever read or sent.
 *
 * Data sources, in the order they are drawn:
 *   1. Polled ticks        - /markets/{ticker}, taken by THIS browser, every N seconds.
 *   2. Official candles    - /series/{series}/markets/{ticker}/candlesticks?period_interval=1|60
 *   3. Collector snapshots - data/history/*.json, committed every 15 min by GitHub Actions.
 * Nothing is synthesised: a gap in the data is drawn as a gap.
 */
(function () {
  "use strict";
  const API = "https://external-api.demo.kalshi.co/trade-api/v2";
  const $ = (id) => document.getElementById(id);
  const COLORS = { last: "#1f5fbf", bid: "#1f9d55", ask: "#b32d2d", snap: "#b9c3cf", grid: "#e6ecf3", axis: "#6b7a8c" };

  let ticker = null;
  let series = null;          // series ticker for candlestick calls (derived from the market)
  let timer = null;
  let running = true;
  let paused = false;

  const ticks = new Map();    // ticker -> [{t, last, bid, ask, src}]
  let candles = [];           // [{t, close, src:'candle'}]
  let snapshots = [];         // [{t, last}]
  let lastError = "";

  const fnum = (v) => (v === null || v === undefined || v === "" ? null : Number(v));
  const money4 = (v) => (v === null || v === undefined || Number.isNaN(v) ? "—" : "$" + Number(v).toFixed(4));
  const contracts = (v) => (v === null || v === undefined || Number.isNaN(Number(v)) ? "—" : Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }));

  function setStatus(text, cls) {
    const s = $("status"); const d = $("dot");
    if (s) s.textContent = text;
    if (d) d.className = "dot " + (cls || "");
  }

  async function getJSON(url) {
    const r = await fetch(url, { headers: { Accept: "application/json" }, cache: "no-store" });
    if (r.status === 429) throw new Error("rate limited (HTTP 429) — increase the refresh interval");
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  /* ---------- chart ---------- */
  function drawChart() {
    const c = $("chart");
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const cssW = c.parentElement.clientWidth - 12;
    const cssH = 400;
    c.width = Math.floor(cssW * dpr); c.height = Math.floor(cssH * dpr);
    c.style.height = cssH + "px";
    const g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, cssW, cssH);

    const pad = { l: 58, r: 16, t: 16, b: 46 };
    const W = cssW, H = cssH;
    const winSec = Number($("win").value || 300);
    const now = Date.now();
    const t0 = now - winSec * 1000;

    g.fillStyle = "#fff"; g.fillRect(0, 0, W, H);

    // y grid 0..1
    g.font = "11px ui-monospace, Menlo, monospace";
    g.strokeStyle = COLORS.grid; g.fillStyle = COLORS.axis; g.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = pad.t + (H - pad.t - pad.b) * (i / 5);
      g.beginPath(); g.moveTo(pad.l, y); g.lineTo(W - pad.r, y); g.stroke();
      g.fillText("$" + (1 - i / 5).toFixed(2), 8, y + 4);
    }
    // x ticks
    for (let i = 0; i <= 5; i++) {
      const t = t0 + ((now - t0) * i) / 5;
      const x = pad.l + (W - pad.l - pad.r) * (i / 5);
      g.strokeStyle = COLORS.grid;
      g.beginPath(); g.moveTo(x, pad.t); g.lineTo(x, H - pad.b); g.stroke();
      const d = new Date(t);
      const label = winSec <= 900
        ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
        : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      g.fillStyle = COLORS.axis;
      g.fillText(label, Math.min(x - 28, W - 76), H - 26);
    }
    g.fillStyle = COLORS.axis;
    g.fillText("time →", W - pad.r - 42, H - 8);
    g.fillText("price $", 8, pad.t - 4);

    const X = (t) => pad.l + ((W - pad.l - pad.r) * (t - t0)) / Math.max(1, now - t0);
    const Y = (p) => pad.t + (H - pad.t - pad.b) * (1 - Math.max(0, Math.min(1, p)));

    const series_ = ticks.get(ticker) || [];
    const pts = series_.filter((x) => x.t >= t0);

    // collector snapshots (grey dots)
    snapshots.filter((s) => s.t >= t0).forEach((s) => {
      g.fillStyle = COLORS.snap;
      g.beginPath(); g.arc(X(s.t), Y(s.last), 2.5, 0, Math.PI * 2); g.fill();
    });

    // candlesticks (dashed)
    const candlePts = candles.filter((s) => s.t >= t0);
    if (candlePts.length > 1) {
      g.strokeStyle = "#8a94a1"; g.setLineDash([4, 3]); g.lineWidth = 1.4;
      g.beginPath();
      candlePts.forEach((s, i) => { const x = X(s.t), y = Y(s.close); i ? g.lineTo(x, y) : g.moveTo(x, y); });
      g.stroke(); g.setLineDash([]);
    }

    // polled lines
    const draw = (key, colour, width) => {
      g.strokeStyle = colour; g.lineWidth = width; g.beginPath();
      let started = false;
      pts.forEach((p) => {
        const v = p[key];
        if (v === null || v === undefined) { started = false; return; }
        const x = X(p.t), y = Y(v);
        if (!started) { g.moveTo(x, y); started = true; } else g.lineTo(x, y);
      });
      g.stroke();
    };
    draw("ask", COLORS.ask, 1.3);
    draw("bid", COLORS.bid, 1.3);
    draw("last", COLORS.last, 2.2);

    // last point marker
    const lastPt = [...pts].reverse().find((p) => p.last !== null && p.last !== undefined);
    if (lastPt) {
      g.fillStyle = COLORS.last;
      g.beginPath(); g.arc(X(lastPt.t), Y(lastPt.last), 3.4, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#0f1720"; g.font = "12px ui-monospace, Menlo, monospace";
      const label = "$" + Number(lastPt.last).toFixed(4);
      const lx = Math.min(X(lastPt.t) + 8, W - 70);
      g.fillText(label, lx, Math.max(14, Y(lastPt.last) - 8));
    }

    if (!pts.length && !candlePts.length && !snapshots.length) {
      g.fillStyle = "#6b7a8c"; g.font = "13px system-ui";
      g.fillText("Waiting for the first tick… (check the status line; nothing is drawn until real data arrives)", pad.l + 10, pad.t + 30);
    }
  }

  /* ---------- orderbook ---------- */
  function renderBook(el, ob, opts) {
    const d = ob.derived || {};
    const yes = (ob.yes_dollars || []).slice().reverse(); // best first
    const no = (ob.no_dollars || []).slice().reverse();
    if (!yes.length && !no.length) {
      el.innerHTML = '<p class="empty">The API returned an empty book for this market: no resting orders on either side. (An unknown ticker also returns empty rather than 404 — Kalshi docs.)</p>';
      return;
    }
    const maxQ = Math.max(1, ...yes.concat(no).map((r) => Number(r[1]) || 0));
    const row = (p, q, side, cum) => {
      const pct = Math.max(2, Math.round((Number(q) / maxQ) * 100));
      const dollarSide = side === "yes" ? Number(p) : 1 - Number(p);
      const show = opts.usd ? money4(dollarSide) : money4(p);
      return `<tr>
        <td class="num">${show}</td>
        <td class="num">${contracts(q)}</td>
        <td><div class="bar ${side}"><span style="width:${pct}%"></span></div></td>
        <td class="num small">${contracts(cum)}</td></tr>`;
    };
    const tableBlock = (arr, side, title, note) => {
      let cum = 0;
      const rows = arr.slice(0, 25).map(([p, q]) => { cum += Number(q) || 0; return row(p, q, side, cum); }).join("");
      return `<div>
        <h4 style="margin:0 0 2px">${title}</h4>
        <p class="small muted" style="margin:0 0 6px">${note}</p>
        <div class="tablewrap"><table><thead><tr>
          <th class="num">${opts.usd ? (side === "yes" ? "YES price" : "YES price (1−NO bid)") : "Price"}</th>
          <th class="num">Contracts</th><th>Depth</th><th class="num">Cumulative</th>
        </tr></thead><tbody>${rows || '<tr><td colspan="4" class="empty">no levels</td></tr>'}</tbody></table></div>
      </div>`;
    };
    el.innerHTML = `
      <div class="grid c3" style="margin-bottom:12px">
        <div class="kpi"><div class="label">Best YES bid</div><div class="value" style="font-size:20px">${money4(d.best_yes_bid)}</div><div class="sub">highest price someone will pay for YES</div></div>
        <div class="kpi"><div class="label">Implied YES ask</div><div class="value" style="font-size:20px">${money4(d.implied_yes_ask)}</div><div class="sub">= 1 − best NO bid (orderbooks have no asks)</div></div>
        <div class="kpi"><div class="label">Contracts resting</div><div class="value" style="font-size:20px">${contracts(d.yes_contracts_at_levels)} / ${contracts(d.no_contracts_at_levels)}</div><div class="sub">YES side / NO side, summed over returned levels</div></div>
      </div>
      <div class="depth">
        ${tableBlock(yes, "yes", "YES bids", "Price a buyer will pay for YES; best first.")}
        ${tableBlock(no, "no", "NO bids", "Price a buyer will pay for NO. A NO bid at $0.30 is a YES ask at $0.70.")}
      </div>
      <p class="small muted">${ob.source_url ? `<a href="${ob.source_url}" target="_blank" rel="noopener">API response</a> · ` : ""}levels returned: ${d.yes_levels || 0} YES / ${d.no_levels || 0} NO. Depth bars are relative to the largest level shown. Order counts per level are not published by Kalshi.</p>`;
  }

  /* ---------- history + candles ---------- */
  async function loadHistory() {
    try {
      const idx = await getJSON("data/history/index.json");
      const days = (idx.days || []).slice(-3);
      const all = [];
      for (const d of days) {
        try {
          const j = await getJSON("data/history/" + d + ".json");
          (j.samples || []).forEach((s) => {
            const m = (s.markets || {})[ticker];
            if (m && m.lp) all.push({ t: s.ts * 1000, last: Number(m.lp) });
          });
        } catch (e) { /* a missing day file is not an error */ }
      }
      snapshots = all.sort((a, b) => a.t - b.t);
    } catch (e) {
      snapshots = [];
    }
  }

  function guessSeries(t) {
    // Market tickers look like SERIES-EVENT-STRIKE; the event ticker is returned by the API.
    return t;
  }

  async function loadCandles() {
    if (!ticker) return;
    candles = [];
    const winSec = Number($("win").value || 300);
    const interval = winSec <= 3600 ? 1 : 60;
    const end = Math.floor(Date.now() / 1000);
    const start = end - Math.min(winSec, interval === 1 ? 3 * 24 * 3600 : 60 * 24 * 3600);
    const s = series || guessSeries(ticker);
    const url = `${API}/series/${encodeURIComponent(s)}/markets/${encodeURIComponent(ticker)}/candlesticks?start_ts=${start}&end_ts=${end}&period_interval=${interval}`;
    try {
      const j = await getJSON(url);
      candles = (j.candlesticks || [])
        .map((c) => ({ t: c.end_period_ts * 1000, close: Number((c.price || {}).close_dollars) }))
        .filter((c) => !Number.isNaN(c.close));
    } catch (e) {
      // Candlesticks are optional: the chart still draws polled and snapshot points.
      candles = [];
    }
  }

  /* ---------- polling ---------- */
  async function tick() {
    if (!ticker || paused) return;
    try {
      const [mj, ob] = await Promise.all([
        getJSON(`${API}/markets/${encodeURIComponent(ticker)}`),
        getJSON(`${API}/markets/${encodeURIComponent(ticker)}/orderbook?depth=20`).catch(() => null),
      ]);
      const m = mj.market || {};
      if (!series && m.event_ticker) {
        // event_ticker is SERIES-EVENT; series is the first segment before the date code.
        const parts = m.event_ticker.split("-");
        series = parts.length > 1 ? m.event_ticker.slice(0, m.event_ticker.lastIndexOf("-")) : m.event_ticker;
      }
      const obd = (ob && ob.orderbook_fp) || {};
      const bestNo = (obd.no_dollars || []).length ? Number(obd.no_dollars[obd.no_dollars.length - 1][0]) : null;
      const impliedAsk = bestNo === null ? null : Number((1 - bestNo).toFixed(4));
      const point = {
        t: Date.now(),
        last: fnum(m.last_price_dollars),
        bid: fnum(m.yes_bid_dollars),
        ask: fnum(m.yes_ask_dollars) !== null ? fnum(m.yes_ask_dollars) : impliedAsk,
      };
      const arr = ticks.get(ticker) || [];
      arr.push(point);
      const keepMs = 8 * 3600 * 1000;
      while (arr.length && Date.now() - arr[0].t > keepMs) arr.shift();
      ticks.set(ticker, arr);

      setStatus(`live · ${ticker} · last ${money4(point.last)} · bid ${money4(point.bid)} · ask ${money4(point.ask)} · ${arr.length} ticks · updated ${new Date().toLocaleTimeString()}`, "live");

      if (ob && $("obout") && $("obmkt").value === ticker) {
        renderBook($("obout"), {
          yes_dollars: obd.yes_dollars || [], no_dollars: obd.no_dollars || [],
          derived: deriveOb(obd), source_url: `${API}/markets/${encodeURIComponent(ticker)}/orderbook?depth=20`,
        }, { usd: $("obsize").dataset.usd === "1" });
      }
      drawChart();
    } catch (e) {
      lastError = e.message;
      setStatus("error: " + e.message + " — retrying. No value is shown rather than a stale one being presented as live.", "err");
    }
  }

  function deriveOb(obd) {
    const yes = obd.yes_dollars || [], no = obd.no_dollars || [];
    const sum = (a, f) => a.reduce((acc, r) => acc + f(r), 0);
    const bestNo = no.length ? Number(no[no.length - 1][0]) : null;
    return {
      yes_levels: yes.length, no_levels: no.length,
      best_yes_bid: yes.length ? Number(yes[yes.length - 1][0]) : null,
      best_no_bid: bestNo,
      implied_yes_ask: bestNo === null ? null : Number((1 - bestNo).toFixed(4)),
      yes_contracts_at_levels: sum(yes, (r) => Number(r[1]) || 0),
      no_contracts_at_levels: sum(no, (r) => Number(r[1]) || 0),
      yes_resting_usd: sum(yes, (r) => (Number(r[0]) || 0) * (Number(r[1]) || 0)),
      no_resting_usd: sum(no, (r) => (Number(r[0]) || 0) * (Number(r[1]) || 0)),
    };
  }

  function restart() {
    if (timer) clearInterval(timer);
    const ms = Number($("intv").value || 15000);
    timer = setInterval(tick, ms);
  }

  async function changeMarket() {
    ticker = $("mkt").value;
    series = null;
    if (!$("obmkt").value || $("obmkt").value !== ticker) $("obmkt").value = ticker;
    setStatus("loading " + ticker + "…", "wait");
    await Promise.all([loadCandles(), loadHistory()]);
    tick();
    // if the market is not in the stored history, still show its candles
    drawChart();
  }

  function initSnapshots() {
    const el = $("obsnap");
    if (!el) return;
    const data = window.__OB__ || {};
    const keys = Object.keys(data);
    if (!keys.length) { el.innerHTML = '<p class="empty">No orderbook snapshots were collected.</p>'; return; }
    el.innerHTML = keys.slice(0, 12).map((k) => {
      const ob = data[k]; const d = ob.derived || {};
      return `<div class="card" style="padding:12px 14px">
        <div class="tick small"><b>${k}</b></div>
        <div class="small muted" style="margin-bottom:6px">${d.yes_levels || 0} YES levels · ${d.no_levels || 0} NO levels</div>
        <table class="small"><tbody>
          <tr><td>Best YES bid</td><td class="num">${money4(d.best_yes_bid)}</td></tr>
          <tr><td>Implied YES ask</td><td class="num">${money4(d.implied_yes_ask)}</td></tr>
          <tr><td>Contracts resting</td><td class="num">${contracts(d.yes_contracts_at_levels)} / ${contracts(d.no_contracts_at_levels)}</td></tr>
        </tbody></table>
        <button class="ghost sm" data-load="${k}" style="margin-top:8px">Show full book</button>
      </div>`;
    }).join("");
    el.querySelectorAll("button[data-load]").forEach((b) => {
      b.onclick = () => {
        const k = b.dataset.load;
        $("obmkt").value = k;
        renderBook($("obout"), window.__OB__[k], { usd: $("obsize").dataset.usd === "1" });
        $("obout").scrollIntoView({ behavior: "smooth", block: "center" });
      };
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!$("chart")) return;
    ticker = $("mkt").value;
    $("mkt").addEventListener("change", changeMarket);
    $("win").addEventListener("change", async () => { await loadCandles(); drawChart(); });
    $("intv").addEventListener("change", restart);
    $("play").addEventListener("click", () => {
      paused = !paused;
      $("play").textContent = paused ? "Resume" : "Pause";
      setStatus(paused ? "paused — last values stay on screen, nothing is refreshed" : "resuming…", paused ? "wait" : "wait");
      if (!paused) tick();
    });
    $("obload").addEventListener("click", async () => {
      const t = $("obmkt").value;
      if (!t) return;
      $("obout").innerHTML = '<p class="empty">Loading live orderbook…</p>';
      try {
        const ob = await getJSON(`${API}/markets/${encodeURIComponent(t)}/orderbook?depth=20`);
        const obd = ob.orderbook_fp || {};
        renderBook($("obout"), { yes_dollars: obd.yes_dollars || [], no_dollars: obd.no_dollars || [], derived: deriveOb(obd), source_url: `${API}/markets/${encodeURIComponent(t)}/orderbook?depth=20` }, { usd: $("obsize").dataset.usd === "1" });
      } catch (e) {
        $("obout").innerHTML = `<p class="empty">Orderbook request failed: ${e.message}. Nothing is displayed rather than a stale book.</p>`;
      }
    });
    $("obsize").addEventListener("click", () => {
      const b = $("obsize");
      b.dataset.usd = b.dataset.usd === "1" ? "0" : "1";
      b.textContent = b.dataset.usd === "1" ? "Show raw prices" : "Show $ notional per level";
      $("obload").click();
    });
    initSnapshots();
    changeMarket();
    restart();
    window.addEventListener("resize", drawChart);
  });
})();
