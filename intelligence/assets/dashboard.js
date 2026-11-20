/* Kalshi Demo Intelligence — Live Dashboard logic
   Modes:
   - LIVE: browser polls public demo REST endpoints (no auth needed for market data)
   - SNAPSHOT: bundled verified captures from 2026-11-20T11:20:09Z
   Derived metric (labelled everywhere): est_24h_dollar_volume = volume_24h_fp × last_price_dollars
   No official dollar-volume field exists in the Market schema (verified in spec) — flagged F-01.
*/
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const API = KDS.API;

  // Series pulled in live mode: known-live (verified during collection) + top-by-volume per topic from watchlist
  const KNOWN_LIVE = ["KXWTIH", "KXBRENTD", "KXWTIW", "KXVPRESNOMR", "KXBTC", "KXBTCD",
    "KXDANCINGWITHTHESTARS", "KXPGAR1LEAD", "KXPGATOUR", "KX10SONG", "KXTOPSONG"];
  const TOPIC_HEADS = ["KXWTI", "KXWTIW", "KXBRENTW", "KXBRENTD", "KXAAAGASDWA", "KXNATGASW",
    "KXETH", "KXDOGE", "KXLINK", "KXAVAX", "KXBTCMINY",
    "KXMETGALA", "KXDWTSELIMINATION", "KXVPRESNOMR", "KXMIDTERMVOTETURN", "KXDPWORLDTOUR", "KXPGAR1LEAD"];

  const S = {
    mode: null,            // "live" | "snapshot"
    topic: "all",
    sort: "est",
    rows: [],              // event rollup rows
    markets: [],           // flattened market rows
    selectedMarket: null,  // {ticker, series_ticker, event_ticker, topic}
    tf: "hr",
    timer: null,
    refreshing: false
  };

  /* ---------- data assembly ---------- */
  function estDollar(m) {
    const v = KDS.num(m.volume_24h_fp), p = KDS.num(m.last_price_dollars);
    if (v == null || p == null) return null;      // blank stays blank
    return v * p;
  }
  function marketTopic(m) {
    if (m.topic) return m.topic;
    return "unclassified";
  }

  function rollup(markets) {
    // group by event_ticker
    const byEv = new Map();
    for (const m of markets) {
      const k = m.event_ticker || "?";
      if (!byEv.has(k)) byEv.set(k, { event_ticker: k, topic: marketTopic(m), series_ticker: m.series_ticker || "", markets: [] });
      byEv.get(k).markets.push(m);
    }
    const rows = [];
    for (const ev of byEv.values()) {
      let est = 0, estAny = false, vol24 = 0, vol24Any = false, volAll = 0, volAllAny = false;
      let top = null, topEst = -1, closeMin = null, oi = 0, oiAny = false;
      for (const m of ev.markets) {
        const e = estDollar(m); if (e != null) { est += e; estAny = true; }
        const v24 = KDS.num(m.volume_24h_fp); if (v24 != null) { vol24 += v24; vol24Any = true; }
        const va = KDS.num(m.volume_fp); if (va != null) { volAll += va; volAllAny = true; }
        const oiM = KDS.num(m.open_interest_fp); if (oiM != null) { oi += oiM; oiAny = true; }
        const e2 = e != null ? e : -1;
        if (e2 > topEst) { topEst = e2; top = m; }
        if (m.close_time) {
          const t = Date.parse(m.close_time);
          if (!Number.isNaN(t)) closeMin = closeMin == null ? t : Math.min(closeMin, t);
        }
      }
      ev.title = (top && top.title) || ev.event_ticker;
      ev.top = top;
      ev.est = estAny ? est : null;
      ev.vol24 = vol24Any ? vol24 : null;
      ev.volAll = volAllAny ? volAll : null;
      ev.oi = oiAny ? oi : null;
      ev.close = closeMin ? new Date(closeMin).toISOString() : "";
      ev.n = ev.markets.length;
      ev.src = top && top.src ? top.src : "";
      rows.push(ev);
    }
    return rows;
  }

  function applyFilters(rows) {
    let r = rows.slice();
    if (S.topic !== "all") r = r.filter(x => x.topic === S.topic);
    const key = S.sort;
    if (key === "close") {
      r.sort((a, b) => {
        const av = a.close ? Date.parse(a.close) : null;
        const bv = b.close ? Date.parse(b.close) : null;
        if (av == null && bv == null) return 0;
        if (av == null) return 1;    // missing close last
        if (bv == null) return -1;
        return av - bv;              // soonest close first
      });
      return r;
    }
    r.sort((a, b) => {
      let av, bv;
      if (key === "est") { av = a.est; bv = b.est; }
      else if (key === "v24") { av = a.vol24; bv = b.vol24; }
      else if (key === "vall") { av = a.volAll; bv = b.volAll; }
      else if (key === "oi") { av = a.oi; bv = b.oi; }
      if (av == null && bv == null) return 0;
      if (av == null) return 1;   // blanks last
      if (bv == null) return -1;
      return bv - av;
    });
    return r;
  }

  function estCell(v) {
    if (v == null) return '<td class="num blank">— blank</td>';
    return '<td class="num">$' + v.toLocaleString("en-US", { maximumFractionDigits: 2 }) + "</td>";
  }

  function renderRank() {
    const rows = applyFilters(S.rows);
    const tb = $("rankBody");
    tb.innerHTML = rows.map((r, i) => {
      const sel = r.top ? ` data-ticker="${KDS.esc(r.top.ticker)}"` : "";
      return `<tr${r.top ? ' class="rankrow" style="cursor:pointer"' : ""}${sel}>
        <td class="num">${i + 1}</td>
        <td>${KDS.topicPill(r.topic)}</td>
        <td><b>${KDS.esc(r.title)}</b><br><span class="note mono">${KDS.esc(r.event_ticker)} · ${r.n} market${r.n > 1 ? "s" : ""}</span></td>
        <td class="num">${r.top ? KDS.fmtPrice(r.top.last_price_dollars) : "—"}${r.top && r.top.yes_sub_title ? '<br><span class="note">' + KDS.esc(r.top.yes_sub_title) + "</span>" : ""}</td>
        <td class="num">${r.top ? KDS.fmtPrice(r.top.yes_bid_dollars) + " / " + KDS.fmtPrice(r.top.yes_ask_dollars) : "—"}</td>
        <td class="num">${r.vol24 == null ? '<span class="blank">— blank</span>' : KDS.fmtInt(r.vol24)}</td>
        ${estCell(r.est)}
        <td class="num">${r.oi == null ? '<span class="blank">— blank</span>' : KDS.fmtInt(r.oi)}</td>
        <td class="num">${r.close ? r.close.replace("T", " ").replace(/\.\d+Z$/, "Z") : "—"}</td>
        ${KDS.srcCell(r.src, "source")}
      </tr>`;
    }).join("");
    // click → select top market
    tb.querySelectorAll("tr.rankrow").forEach(tr => {
      tr.addEventListener("click", () => selectMarket(tr.dataset.ticker));
    });
    $("rankCount").textContent = rows.length;
  }

  function renderTopicCards() {
    const topics = ["gas prices", "elections", "culture", "crypto", "golf"];
    const wrap = $("topicCards");
    wrap.innerHTML = topics.map(t => {
      const rows = applyFilters(S.rows.filter(r => r.topic === t));
      const top = rows[0];
      if (!top) return `<div class="stat"><div class="label">${t}</div><div class="value small">no data</div><div class="note">—</div></div>`;
      return `<div class="stat"><div class="label">${t}</div>
        <div class="value small">${top.est == null ? "est $ — blank" : "$" + top.est.toLocaleString("en-US", { maximumFractionDigits: 2 })}</div>
        <div class="note" title="derived = Σ markets (volume_24h × last price)">${KDS.esc(top.title.slice(0, 60))}${top.title.length > 60 ? "…" : ""}</div>
        <div class="note">vol 24h: ${top.vol24 == null ? "— blank" : KDS.fmtInt(top.vol24) + " ctr"} · derived est.</div></div>`;
    }).join("");
  }

  /* ---------- LIVE mode ---------- */
  async function loadLive() {
    const series = Array.from(new Set([...KNOWN_LIVE, ...TOPIC_HEADS]));
    const markets = [];
    const errors = [];
    // polite batching: 6 concurrent series reads at a time
    const results = [];
    for (let i = 0; i < series.length; i += 6) {
      const batch = series.slice(i, i + 6);
      const part = await Promise.all(batch.map(async s => {
        try {
          const j = await KDS.fetchJSON(`${API}/markets?series_ticker=${encodeURIComponent(s)}&status=open&limit=1000`, 10000);
          return { s, ok: true, markets: (j.markets || []).map(m => ({ ...m, series_ticker: m.series_ticker || s })) };
        } catch (e) { return { s, ok: false, markets: [] }; }
      }));
      results.push(...part);
      if (i + 6 < series.length) await new Promise(r => setTimeout(r, 250));
    }
    results.forEach(r => { if (!r.ok) errors.push(r.s); else markets.push(...r.markets); });
    // attach topic via watchlist mapping (official category-based)
    const wl = await KDS.getWatchlist();
    const topicOf = {};
    for (const t of wl.topics) for (const q of t.queries) for (const se of (q.series || [])) topicOf[se.ticker] = t.topic;
    for (const c of (wl.topics.find(t => t.topic === "culture")?.series_with_volume_not_in_queries || [])) topicOf[c.ticker] = "culture";
    if (wl.topics.find(t => t.topic === "golf")) for (const se of (wl.topics.find(t => t.topic === "golf").queries.find(q => q.url.endsWith("/series/KXPGATOUR"))?.series || [])) topicOf[se.ticker] = "golf";
    for (const m of markets) m.topic = topicOf[m.series_ticker] || "unclassified";
    S.markets = markets;
    S.rows = rollup(markets);
    $("modeNote").innerHTML = `<span class="badge live"><span class="dot"></span> LIVE — ${markets.length} open markets across ${series.length} watchlist series</span>` +
      (errors.length ? ` <span class="badge flag">series errors: ${errors.length}</span>` : "");
    S.lastOk = new Date().toISOString();
  }

  async function enrichEventTitles(rows) {
    // Fetch official event titles/categories for the top rows in one CSV call (best-effort).
    try {
      const top = rows.slice(0, 30).map(r => r.event_ticker).filter(t => t && !t.startsWith("—"));
      if (!top.length) return;
      const j = await KDS.fetchJSON(`${API}/events?tickers=${encodeURIComponent(top.join(","))}&limit=50`, 9000);
      const map = {};
      for (const ev of (j.events || [])) map[ev.event_ticker] = ev;
      for (const r of rows) {
        const ev = map[r.event_ticker];
        if (ev && ev.title) {
          r.title = ev.title;
          if (ev.category) r.topic = r.topic === "unclassified" ? mapTopicFromCategory(ev.category, r.topic) : r.topic;
        }
      }
    } catch (e) { /* keep market-title fallback */ }
  }
  function mapTopicFromCategory(cat, fallback) {
    const c = (cat || "").toLowerCase();
    if (c === "elections") return "elections";
    if (c === "crypto") return "crypto";
    if (c === "entertainment") return "culture";
    if (c === "commodities" || c === "economics") return "gas prices";
    if (c === "sports") return fallback === "unclassified" ? "unclassified" : fallback; // only golf-tagged series are golf
    return fallback;
  }

  /* ---------- SNAPSHOT mode ---------- */
  async function loadSnapshot() {
    const s = await KDS.getSnapshot();
    const markets = (s.markets || []).map(m => ({ ...m }));
    const evRows = (s.events || []).filter(e => e.status_query === "open");
    // rollup from snapshot markets; events without captured markets still appear
    const rolled = rollup(markets);
    const known = new Map(rolled.map(r => [r.event_ticker, r]));
    for (const e of evRows) {
      if (!known.has(e.event_ticker)) {
        known.set(e.event_ticker, {
          event_ticker: e.event_ticker, topic: e.topic, title: e.title, markets: [],
          est: null, vol24: null, volAll: null, oi: null, close: "", n: 0, src: e.src, top: null
        });
      } else {
        const r = known.get(e.event_ticker);
        r.title = e.title || r.title;
        r.topic = e.topic || r.topic;
        r.src = r.src || e.src;
      }
    }
    S.markets = markets;
    S.rows = Array.from(known.values());
    $("modeNote").innerHTML = `<span class="badge snapshot">SNAPSHOT — verified capture 2026-11-20T11:20:09Z (${markets.length} markets, ${S.rows.length} events)</span> <span class="note">Live ranking requires the browser to reach the demo API; press Refresh to retry.</span>`;
  }

  /* ---------- chart ---------- */
  const TF = {
    sec: { label: "Seconds", help: "tick trades (ms timestamps)" },
    min: { label: "Minutes", help: "1-minute candlesticks" },
    hr: { label: "Hours", help: "1-hour candlesticks" },
    day: { label: "Days", help: "1-day candlesticks" }
  };

  function chartXLabels(t0, t1) {
    const span = t1 - t0;
    const fmt = new Intl.DateTimeFormat("en-GB", span <= 6 * 3600
      ? { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, timeZone: "UTC" }
      : span <= 3 * 86400
        ? { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" }
        : { month: "2-digit", day: "2-digit", hour12: false, timeZone: "UTC" });
    return { fmt, n: 6 };
  }

  function drawChart(seriesList, unit) {
    const canvas = $("chartCanvas"), box = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = box.clientWidth * dpr; canvas.height = box.clientHeight * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    const W = box.clientWidth, H = box.clientHeight;
    ctx.clearRect(0, 0, W, H);
    const pts = seriesList.filter(s => s.pts.length > 0);
    if (!pts.length) {
      ctx.fillStyle = "#93a1b3"; ctx.font = "13px sans-serif"; ctx.textAlign = "center";
      ctx.fillText("No data for this view", W / 2, H / 2); return;
    }
    let t0 = Infinity, t1 = -Infinity, v0 = Infinity, v1 = -Infinity;
    for (const s of pts) for (const p of s.pts) {
      t0 = Math.min(t0, p[0]); t1 = Math.max(t1, p[0]);
      v0 = Math.min(v0, p[1]); v1 = Math.max(v1, p[1]);
    }
    if (t0 === t1) { t0 -= 1; t1 += 1; }
    if (v0 === v1) { v0 -= 0.01; v1 += 0.01; }
    const padV = (v1 - v0) * 0.08; v0 -= padV; v1 += padV;
    const L = 56, R = 14, T = 14, B = 34;
    const X = t => L + (t - t0) / (t1 - t0) * (W - L - R);
    const Y = v => T + (1 - (v - v0) / (v1 - v0)) * (H - T - B);
    // grid
    ctx.strokeStyle = "#263142"; ctx.fillStyle = "#93a1b3"; ctx.font = "10.5px sans-serif";
    ctx.lineWidth = 1;
    const xl = chartXLabels(t0, t1);
    for (let i = 0; i <= xl.n; i++) {
      const t = t0 + (t1 - t0) * i / xl.n, x = X(t);
      ctx.beginPath(); ctx.moveTo(x, T); ctx.lineTo(x, H - B); ctx.stroke();
      ctx.textAlign = "center";
      ctx.fillText(xl.fmt.format(new Date(t * 1000)), x, H - B + 16);
    }
    for (let i = 0; i <= 4; i++) {
      const v = v0 + (v1 - v0) * i / 4, y = Y(v);
      ctx.beginPath(); ctx.moveTo(L, y); ctx.lineTo(W - R, y); ctx.stroke();
      ctx.textAlign = "right";
      ctx.fillText("$" + v.toFixed(3), L - 7, y + 3.5);
    }
    // axis titles
    ctx.textAlign = "center"; ctx.fillStyle = "#5c6b80";
    ctx.fillText(unit === "sec" ? "time (UTC, seconds view — each point is a trade)" : "time (UTC)", (W + L - R) / 2, H - 4);
    ctx.save(); ctx.translate(12, H / 2); ctx.rotate(-Math.PI / 2);
    ctx.fillText("YES contract price ($)", 0, 0); ctx.restore();
    // lines
    for (const s of pts) {
      ctx.strokeStyle = s.color; ctx.lineWidth = s.width || 2;
      if (s.dash) ctx.setLineDash(s.dash); else ctx.setLineDash([]);
      ctx.beginPath();
      s.pts.forEach((p, i) => { const x = X(p[0]), y = Y(p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
      ctx.stroke(); ctx.setLineDash([]);
      if (s.dots) { ctx.fillStyle = s.color; for (const p of s.pts) { ctx.beginPath(); ctx.arc(X(p[0]), Y(p[1]), 2.4, 0, 7); ctx.fill(); } }
    }
    // legend
    let lx = L + 4, ly = T + 4;
    ctx.font = "11px sans-serif"; ctx.textAlign = "left";
    for (const s of pts) {
      ctx.fillStyle = s.color; ctx.fillRect(lx, ly, 14, 3);
      ctx.fillStyle = "#93a1b3"; ctx.fillText(s.name, lx + 19, ly + 5);
      lx += 26 + ctx.measureText(s.name).width;
    }
  }

  async function loadChart() {
    const m = S.selectedMarket;
    if (!m) return;
    $("chartMeta").innerHTML = `<span class="spin"></span> loading ${KDS.esc(m.ticker)} (${TF[S.tf].help})…`;
    const now = Math.floor(Date.now() / 1000);
    const series = [];
    try {
      if (S.tf === "sec") {
        let ticks = [];
        if (S.mode === "snapshot") {
          const s = await KDS.getSnapshot();
          ticks = (s.trades_sample || []).filter(t => t.ticker === m.ticker);
          if (!ticks.length) throw new Error("snapshot has no bundled ticks for this market — Seconds view needs the live API (or pick the DWTS Tatyana Ali market)");
        } else {
          const j = await KDS.pullTrades(m.ticker, 1000);
          ticks = (j.trades || []);
        }
        ticks = ticks.slice().sort((a, b) => Date.parse(a.created_time) - Date.parse(b.created_time));
        series.push({ name: "trade price (YES $)", color: "#4ea1ff", dots: true, width: 1.6, pts: ticks.map(t => [Date.parse(t.created_time) / 1000, Number(t.yes_price_dollars)]) });
        $("chartMeta").textContent = `${ticks.length} trades · source: GET /markets/trades?ticker=… (${S.mode})`;
      } else if (S.mode === "snapshot" && (S.tf === "min" || S.tf === "day")) {
        throw new Error("snapshot-bundles-only-60m-bars");
      } else {
        const period = S.tf === "min" ? 1 : S.tf === "hr" ? 60 : 1440;
        const span = S.tf === "min" ? 6 * 3600 : S.tf === "hr" ? 7 * 86400 : 45 * 86400;
        let bars = [];
        if (S.mode === "snapshot") {
          const s = await KDS.getSnapshot();
          if (s.candlesticks && s.candlesticks.ticker === m.ticker) bars = s.candlesticks.bars;
          else bars = [];
        } else {
          const j = await KDS.pullCandles(m.series_ticker, m.ticker, period, now - span, now);
          bars = (j.candlesticks || []).map(b => [
            b.end_period_ts, b.volume_fp, (b.price || {}).previous_dollars || "",
            (b.price || {}).open_dollars || "", (b.price || {}).high_dollars || "", (b.price || {}).low_dollars || "", (b.price || {}).close_dollars || "",
            (b.yes_bid || {}).open_dollars || "", (b.yes_bid || {}).close_dollars || "",
            (b.yes_ask || {}).close_dollars || ""
          ]);
        }
        if (!bars.length) throw new Error("no candlesticks in range");
        const num = v => { const n = Number(v); return Number.isFinite(n) && v !== "" ? n : null; };
        const price = [], bid = [], ask = [];
        for (const b of bars) {
          const t = b[0];
          const pc = num(b[6]) ?? num(b[3]); if (pc != null) price.push([t, pc]);
          const bc = num(b[8]); if (bc != null) bid.push([t, bc]);
          const ac = num(b[9]); if (ac != null) ask.push([t, ac]);
        }
        series.push({ name: "trade price (close)", color: "#4ea1ff", pts: price });
        if (bid.length) series.push({ name: "best YES bid", color: "#2dd4a7", dash: [4, 4], width: 1.3, pts: bid });
        if (ask.length) series.push({ name: "best YES ask", color: "#ff6b6b", dash: [4, 4], width: 1.3, pts: ask });
        $("chartMeta").textContent = `${bars.length} bars · period=${period}m · source: GET /series/{s}/markets/{t}/candlesticks (live)` + (S.mode === "snapshot" ? " [bundled subset]" : "");
      }
      drawChart(series, S.tf);
      $("chartErr").style.display = "none";
    } catch (e) {
      if (S.mode === "snapshot" && (S.tf === "min" || S.tf === "day")) {
        $("chartErr").style.display = "block";
        $("chartErr").innerHTML = `Snapshot bundles only the Seconds (trade ticks) and Hours (60-minute bars) views for the captured market. Switch to <b>Seconds</b> or <b>Hours</b>, or open this page with live API access for 1-minute / 1-day bars.`;
      } else {
        $("chartErr").style.display = "block";
        $("chartErr").textContent = "Chart load failed: " + (e && e.message || e);
      }
      $("chartMeta").textContent = "";
      drawChart([], S.tf);
    }
  }

  /* ---------- depth ---------- */
  function depthRows(levels, cls) {
    if (!levels || !levels.length) return '<tr><td colspan="3" class="note">no resting orders</td></tr>';
    const max = Math.max(...levels.map(l => Number(l[1]) || 0), 1);
    return levels.map(([p, sz]) => {
      const n = Number(sz) || 0;
      const w = Math.round(n / max * 100);
      return `<tr><td class="num">${KDS.fmtPrice(p)}</td>
        <td class="num depth-bar"><div class="fill ${cls}" style="width:${w}%"></div><span>${KDS.fmtInt(sz)}</span></td>
        <td class="num">${(n / max * 100).toFixed(0)}%</td></tr>`;
    }).join("");
  }

  async function loadDepth() {
    const m = S.selectedMarket;
    if (!m) return;
    $("depthMeta").innerHTML = `<span class="spin"></span> loading orderbook…`;
    try {
      let ob;
      if (S.mode === "snapshot") {
        const s = await KDS.getSnapshot();
        ob = (s.orderbooks || []).find(o => o.ticker === m.ticker) || (s.orderbooks || [])[1] || (s.orderbooks || [])[0];
        if (ob && ob.ticker !== m.ticker) {
          $("depthNote").innerHTML = `<span class="badge flag">bundled orderbook is for ${KDS.esc(ob.ticker)} (selected market has no bundled depth)</span>`;
        } else $("depthNote").innerHTML = "";
      } else {
        ob = await KDS.pullOrderbook(m.ticker);
        $("depthNote").innerHTML = "";
      }
      const b = ob.orderbook_fp || {};
      $("depthYes").innerHTML = depthRows(b.yes_dollars, "");
      $("depthNo").innerHTML = depthRows(b.no_dollars, "no");
      const nYes = (b.yes_dollars || []).reduce((a, l) => a + (Number(l[1]) || 0), 0);
      const nNo = (b.no_dollars || []).reduce((a, l) => a + (Number(l[1]) || 0), 0);
      $("depthMeta").innerHTML = `YES bids: <b>${KDS.fmtInt(nYes)}</b> contracts · NO bids: <b>${KDS.fmtInt(nNo)}</b> contracts · ` +
        (ob.src ? `<a href="${KDS.esc(ob.src)}" target="_blank" rel="noopener">source</a>` : `<a href="${API}/markets/${encodeURIComponent(m.ticker)}/orderbook" target="_blank" rel="noopener">source</a>`);
      $("depthTicker").textContent = ob.ticker || m.ticker;
    } catch (e) {
      $("depthMeta").textContent = "Orderbook load failed: " + (e && e.message || e);
    }
  }

  /* ---------- selection & orchestration ---------- */
  function fillMarketSelect() {
    const sel = $("marketSelect");
    const rows = S.rows.filter(r => r.top).sort((a, b) => (b.est ?? -1) - (a.est ?? -1));
    sel.innerHTML = rows.map(r => `<option value="${KDS.esc(r.top.ticker)}">${KDS.esc(r.title).slice(0, 70)} — ${KDS.esc(r.top.ticker)}</option>`).join("");
    if (S.selectedMarket) sel.value = S.selectedMarket.ticker;
  }

  function selectMarket(ticker) {
    const all = S.markets;
    const m = all.find(x => x.ticker === ticker);
    if (!m) return;
    S.selectedMarket = m;
    try { sessionStorage.setItem("kds.lastTicker", ticker); } catch (e) {}
    $("marketSelect").value = ticker;
    $("selTitle").textContent = m.title || m.ticker;
    $("selMeta").innerHTML = `${KDS.topicPill(m.topic)} <span class="pill mono">${KDS.esc(m.ticker)}</span>
      · last ${KDS.fmtPrice(m.last_price_dollars)} · bid ${KDS.fmtPrice(m.yes_bid_dollars)} / ask ${KDS.fmtPrice(m.yes_ask_dollars)}
      · vol24h ${m.volume_24h_fp == null ? "— blank" : KDS.fmtInt(m.volume_24h_fp)} · OI ${m.open_interest_fp == null ? "— blank" : KDS.fmtInt(m.open_interest_fp)}
      · closes ${KDS.fmtTs(m.close_time)}
      ${m.src ? `· <a href="${KDS.esc(m.src)}" target="_blank" rel="noopener">source</a>` : ""}`;
    loadChart(); loadDepth();
  }

  async function refresh(first) {
    if (S.refreshing) return;
    S.refreshing = true;
    $("refreshBtn").disabled = true;
    try {
      await KDS.probeLive();
      const live = KDS.state.live;
      if (live) await loadLive(); else await loadSnapshot();
      S.mode = live ? "live" : "snapshot";
      const rows = applyFilters(S.rows);
      await enrichEventTitles(S.rows);
      renderRank(); renderTopicCards(); fillMarketSelect();
      // keep/replace selected market
      const still = S.selectedMarket && S.markets.some(x => x.ticker === S.selectedMarket.ticker);
      if (!still) {
        const best = (S.rows.filter(r => r.top).sort((a, b) => (b.est ?? -1) - (a.est ?? -1))[0]) ||
          S.rows.find(r => r.top);
        if (best && best.top) selectMarket(best.top.ticker);
      } else selectMarket(S.selectedMarket.ticker);
      $("updatedAt").textContent = "updated " + new Date().toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z") + " UTC";
      $("chartErr").style.display = "none";
    } catch (e) {
      $("modeNote").innerHTML = `<span class="badge err">refresh failed: ${KDS.esc(e && e.message || e)}</span>`;
    } finally {
      S.refreshing = false;
      $("refreshBtn").disabled = false;
    }
  }

  /* ---------- events wiring ---------- */
  window.addEventListener("DOMContentLoaded", () => {
    KDS.setModeBadge(document.getElementById("modeBadge"));
    document.querySelectorAll("#topicSeg button").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll("#topicSeg button").forEach(x => x.classList.remove("active"));
        b.classList.add("active"); S.topic = b.dataset.topic; renderRank(); renderTopicCards();
      });
    });
    $("sortSel").addEventListener("change", e => { S.sort = e.target.value; renderRank(); renderTopicCards(); });
    document.querySelectorAll("#tfSeg button").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll("#tfSeg button").forEach(x => x.classList.remove("active"));
        b.classList.add("active"); S.tf = b.dataset.tf; loadChart();
      });
    });
    $("marketSelect").addEventListener("change", e => selectMarket(e.target.value));
    $("refreshBtn").addEventListener("click", () => refresh());
    window.addEventListener("resize", () => { if (S.selectedMarket) loadChart(); });
    refresh(true);
    S.timer = setInterval(refresh, 60000); // polite polling cadence
  });
})();
