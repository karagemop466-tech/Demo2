/* Kalshi Demo Dashboard — frontend logic.
 * Works in two modes:
 *   1) Backend mode  : served by the Node backend -> calls relative /api/* (proxy + WS).
 *   2) Direct mode   : served from GitHub Pages -> calls Kalshi public demo endpoints
 *                      directly from the browser (no auth needed for market data).
 * Authenticated features (portfolio/trades) require backend mode with a key.
 * Verified endpoints: https://docs.kalshi.com (see COORDINATION.md).
 */
(function () {
  'use strict';

  const REST_DEMO = 'https://external-api.demo.kalshi.co/trade-api/v2';
  const TOPICS = ['gas', 'elections', 'culture', 'crypto', 'golf'];

  // Fallback flagged list for static/direct mode (mirrors docs/VERIFICATION.md).
  window.FALLBACK_FLAGS = [
    { id: 'FLAG-01', title: 'Sandbox cannot reach Kalshi demo API', detail: 'Outbound access is allowlisted and excludes kalshi.co. Live data is implemented but unverified from this environment.', status: 'open', source: 'https://docs.kalshi.com/getting_started/demo_env' },
    { id: 'FLAG-02', title: 'No Kalshi demo API key present', detail: 'Trade execution and authenticated portfolio reads are implemented but cannot be exercised without a demo account key pair. Keys are never committed.', status: 'open', source: 'https://docs.kalshi.com/getting_started/api_keys' },
    { id: 'FLAG-03', title: 'GitHub Pages is a static host', detail: 'Pages cannot run a persistent authenticated backend or hold secrets. The static site uses public market-data calls; the backend provides authenticated portfolio/trade features.', status: 'open', source: 'https://docs.kalshi.com/getting_started/quick_start_market_data' },
    { id: 'FLAG-04', title: 'Category-to-topic mapping is unverified', detail: 'The exact series/category mapping to the five topics is not confirmed from an official enumeration. Filtering uses a reviewable keyword mapping.', status: 'open', source: 'https://docs.kalshi.com/api-reference/market/get-series' },
    { id: 'FLAG-05', title: 'Settled-outcome payload fields unverified', detail: 'The exact field names for a resolved yes/no outcome were not fully enumerated on the pages fetched. Outcome cells are marked unverified until confirmed from a live settled market.', status: 'open', source: 'https://docs.kalshi.com/getting_started/market_settlement' },
  ];
  const TOPIC_LABELS = {
    gas: 'Gas Prices', elections: 'Elections', culture: 'Culture', crypto: 'Crypto', golf: 'Golf',
  };

  // ---- API mode detection ----
  let MODE = 'direct'; // 'backend' | 'direct'
  async function detectMode() {
    try {
      const r = await fetch('/api/status', { cache: 'no-store' });
      if (r.ok) {
        MODE = 'backend';
        return true;
      }
    } catch { /* not on backend */ }
    MODE = 'direct';
    return false;
  }

  // ---- Direct Kalshi public calls (browser -> Kalshi) ----
  async function directEvents(status) {
    const r = await fetch(`${REST_DEMO}/events?status=${status}&with_nested_markets=true&limit=200`);
    if (!r.ok) throw new Error(`events ${r.status}`);
    const d = await r.json();
    return { events: d.events || [], cursor: d.cursor || '' };
  }
  async function directMarkets(series, status) {
    let url = `${REST_DEMO}/markets?limit=200`;
    if (series) url += `&series_ticker=${encodeURIComponent(series)}`;
    if (status) url += `&status=${status}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(`markets ${r.status}`);
    const d = await r.json();
    return d.markets || [];
  }
  async function directOrderbook(ticker) {
    const r = await fetch(`${REST_DEMO}/markets/${encodeURIComponent(ticker)}/orderbook`);
    if (!r.ok) throw new Error(`orderbook ${r.status}`);
    return r.json();
  }
  async function directCandlesticks(series, ticker, periodInterval, hours) {
    const now = Math.floor(Date.now() / 1000);
    const span = periodInterval * 60 * (hours || 24);
    const url = `${REST_DEMO}/series/${encodeURIComponent(series)}/markets/${encodeURIComponent(ticker)}/candlesticks?start_ts=${now - span}&end_ts=${now}&period_interval=${periodInterval}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(`candlesticks ${r.status}`);
    const d = await r.json();
    return d.candlesticks || [];
  }

  // ---- Unified data fetchers ----
  async function fetchEvents(status) {
    if (MODE === 'backend') {
      const r = await fetch(`/api/events?status=${status}`, { cache: 'no-store' });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'events failed');
      return d.events || [];
    }
    const d = await directEvents(status);
    return normalizeEvents(d.events);
  }
  async function fetchOrderbook(ticker) {
    if (MODE === 'backend') {
      const r = await fetch(`/api/orderbook?ticker=${encodeURIComponent(ticker)}`, { cache: 'no-store' });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'orderbook failed');
      return d;
    }
    const d = await directOrderbook(ticker);
    return normalizeOrderbook(ticker, d);
  }
  async function fetchCandlesticks(series, ticker, periodInterval, hours) {
    if (MODE === 'backend') {
      const r = await fetch(`/api/candlesticks?series_ticker=${encodeURIComponent(series)}&ticker=${encodeURIComponent(ticker)}&period=${periodInterval}&hours=${hours}`, { cache: 'no-store' });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'candlesticks failed');
      return d.candlesticks || [];
    }
    return directCandlesticks(series, ticker, periodInterval, hours);
  }

  // ---- Normalizers (direct mode -> backend-like shape) ----
  const num = (v) => { const n = typeof v === 'number' ? v : parseFloat(v); return Number.isFinite(n) ? n : null; };
  const TOPIC_KEYWORDS = {
    gas: ['gas', 'gasoline', 'fuel', 'oil', 'energy', 'crude', 'natgas', 'natural gas'],
    elections: ['election', 'vote', 'candidate', 'poll', 'president', 'senate', 'congress'],
    culture: ['culture', 'film', 'movie', 'music', 'award', 'oscar', 'grammy', 'tv', 'show'],
    crypto: ['crypto', 'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'coin', 'cryptocurrency'],
    golf: ['golf', 'pga', 'masters', 'open championship', 'ryder'],
  };
  function categorizeTopic(text) {
    const t = (text || '').toLowerCase();
    for (const [topic, kws] of Object.entries(TOPIC_KEYWORDS)) {
      if (kws.some((k) => t.includes(k))) return topic;
    }
    return 'other';
  }
  function normalizeMarket(m) {
    const price = num(m.yes_bid_dollars ?? m.yes_bid) ?? 0;
    const volume = num(m.volume_fp ?? m.volume) ?? 0;
    return {
      ticker: m.ticker,
      event_ticker: m.event_ticker,
      title: m.title,
      status: m.status,
      yes_bid: num(m.yes_bid_dollars ?? m.yes_bid),
      yes_ask: num(m.yes_ask_dollars ?? m.yes_ask),
      last_price: num(m.last_price_dollars ?? m.last_price ?? price),
      volume: volume,
      notional: Math.round(price * volume * 100) / 100,
      close_ts: m.close_ts,
      settled_ts: m.settled_ts,
      outcome: m.result || m.outcome || null,
      series_ticker: m.series_ticker,
    };
  }
  function normalizeEvents(events) {
    return events.map((ev) => {
      const markets = (ev.markets || []).map(normalizeMarket);
      const text = [ev.title, ev.sub_title, ev.category, ...markets.map((m) => m.title)].filter(Boolean).join(' ');
      const topic = categorizeTopic(text);
      const notional = markets.reduce((a, m) => a + (m.notional || 0), 0);
      const volume = markets.reduce((a, m) => a + (m.volume || 0), 0);
      return {
        event_ticker: ev.event_ticker,
        title: ev.title,
        sub_title: ev.sub_title,
        series_ticker: ev.series_ticker,
        status: ev.status,
        topic,
        in_scope: TOPICS.includes(topic),
        notional: Math.round(notional * 100) / 100,
        volume: Math.round(volume),
        markets,
        close_ts: ev.strike_date || (markets[0] && markets[0].close_ts),
      };
    });
  }
  function normalizeOrderbook(ticker, d) {
    const ob = d.orderbook_fp || { yes_dollars: [], no_dollars: [] };
    const toLevels = (arr) => (arr || []).map((l) => ({ price: num(l[0]), count: num(l[1]) })).filter((l) => l.price !== null && l.count !== null);
    const yes = toLevels(ob.yes_dollars);
    const no = toLevels(ob.no_dollars);
    const bestYes = yes.length ? yes[yes.length - 1] : null;
    const bestNo = no.length ? no[no.length - 1] : null;
    return {
      ticker, yes, no, best_yes_bid: bestYes, best_no_bid: bestNo,
      spread: bestYes && bestNo ? Math.round((100 - (bestNo.price + bestYes.price)) * 100) / 100 : null,
    };
  }

  // ---- Rendering helpers ----
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const money = (v) => (v == null ? '' : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);
  const price = (v) => (v == null ? '' : `${Number(v).toFixed(3)}`);

  function setStatus(state, text) {
    const el = document.getElementById('conn-status');
    if (!el) return;
    el.className = `status-pill ${state}`;
    el.querySelector('.dot') && (el.querySelector('.dot').className = 'dot');
    el.innerHTML = `<span class="dot"></span><span>${esc(text)}</span>`;
  }

  function topicBadge(topic) {
    if (!TOPICS.includes(topic)) return `<span class="badge">${esc(topic || 'other')}</span>`;
    return `<span class="badge topic">${esc(TOPIC_LABELS[topic])}</span>`;
  }
  function statusBadge(status) {
    const cls = status === 'settled' ? 'settled' : status === 'open' ? 'open' : '';
    return `<span class="badge ${cls}">${esc(status || '—')}</span>`;
  }
  function resolutionBadge(res) {
    if (res === 'yes' || res === true) return `<span class="badge yes">YES</span>`;
    if (res === 'no' || res === false) return `<span class="badge no">NO</span>`;
    return `<span class="badge">unverified</span>`;
  }
  function srcLink(url, label) {
    if (!url) return `<span class="src">no source</span>`;
    return `<a class="src" href="${esc(url)}" target="_blank" rel="noopener">${esc(label || url)}</a>`;
  }

  function renderTable(container, columns, rows, opts) {
    const o = opts || {};
    if (!rows.length) {
      container.innerHTML = `<div class="empty">${esc(o.empty || 'No rows.')}</div>`;
      return;
    }
    const head = columns.map((c) => `<th class="${c.num ? 'num' : ''}">${esc(c.label)}</th>`).join('');
    const body = rows.map((r, i) => {
      const tds = columns.map((c) => {
        const val = c.render ? c.render(r, i) : esc(r[c.key]);
        return `<td class="${c.num ? 'num' : ''}">${val}</td>`;
      }).join('');
      return `<tr>${tds}</tr>`;
    }).join('');
    container.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
  }

  // ---- Chart (canvas) ----
  function drawChart(canvas, points, opts) {
    const o = opts || {};
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.clientWidth * (window.devicePixelRatio || 1);
    const H = canvas.height = canvas.clientHeight * (window.devicePixelRatio || 1);
    ctx.clearRect(0, 0, W, H);
    const pad = { l: 44, r: 12, t: 12, b: 26 };
    if (!points || points.length < 2) {
      ctx.fillStyle = '#9aa6bd';
      ctx.font = `${14 * (window.devicePixelRatio || 1)}px sans-serif`;
      ctx.fillText('Not enough data to draw a chart.', pad.l, H / 2);
      return;
    }
    const xs = points.map((p) => p.ts);
    const ys = points.map((p) => p.price);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = 0, yMax = 100;
    const sx = (x) => pad.l + ((x - xMin) / (xMax - xMin || 1)) * (W - pad.l - pad.r);
    const sy = (y) => H - pad.b - ((y - yMin) / (yMax - yMin || 1)) * (H - pad.t - pad.b);

    // grid + y labels
    ctx.strokeStyle = '#2a3447';
    ctx.fillStyle = '#9aa6bd';
    ctx.lineWidth = 1;
    ctx.font = `${10 * (window.devicePixelRatio || 1)}px sans-serif`;
    for (let g = 0; g <= 5; g++) {
      const y = yMin + ((yMax - yMin) * g) / 5;
      const yy = sy(y);
      ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(W - pad.r, yy); ctx.stroke();
      ctx.fillText(`${y.toFixed(0)}¢`, 4, yy + 3 * (window.devicePixelRatio || 1));
    }
    // x labels
    const fmtTime = (ts, unit) => {
      const d = new Date(ts * (unit === 's' ? 1000 : 1000));
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };
    for (let g = 0; g <= 4; g++) {
      const x = xMin + ((xMax - xMin) * g) / 4;
      const xx = sx(x);
      ctx.fillText(fmtTime(x, o.unit), xx - 30 * (window.devicePixelRatio || 1), H - 8 * (window.devicePixelRatio || 1));
    }

    // line
    ctx.strokeStyle = o.color || '#00b67a';
    ctx.lineWidth = 2 * (window.devicePixelRatio || 1);
    ctx.beginPath();
    points.forEach((p, i) => { const X = sx(p.ts), Y = sy(Math.max(0, Math.min(100, p.price))); if (i === 0) ctx.moveTo(X, Y); else ctx.lineTo(X, Y); });
    ctx.stroke();
    // area
    ctx.lineTo(sx(points[points.length - 1].ts), sy(0));
    ctx.lineTo(sx(points[0].ts), sy(0));
    ctx.closePath();
    ctx.fillStyle = (o.color || '#00b67a') + '22';
    ctx.fill();
  }

  // ---- WebSocket hub (backend mode only) ----
  function connectWS(onPrice) {
    if (MODE !== 'backend') return null;
    try {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${proto}://${location.host}/ws`);
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'price' && onPrice) onPrice(msg);
        } catch { /* ignore */ }
      };
      ws.onerror = () => { /* polling fallback remains */ };
      return ws;
    } catch { return null; }
  }

  // =====================================================================
  // Page logic
  // =====================================================================
  const page = document.body.getAttribute('data-page');

  async function init() {
    const onBackend = await detectMode();
    setStatus(onBackend ? 'ok' : 'warn', onBackend ? 'Backend · live data' : 'Static · direct Kalshi');
    try {
      if (page === 'landing') await landing();
      else if (page === 'events') await eventsPage();
      else if (page === 'category') await categoryPage();
      else if (page === 'market') await marketPage();
      else if (page === 'portfolio') await portfolioPage();
      else if (page === 'trades') await tradesPage();
      else if (page === 'strategies') await strategiesPage();
      else if (page === 'suggestions') await suggestionsPage();
      else if (page === 'flagged') await flaggedPage();
    } catch (err) {
      setStatus('err', `Error: ${err.message}`);
      const main = document.querySelector('main');
      if (main && !main.querySelector('.note')) {
        const n = document.createElement('div');
        n.className = 'note danger';
        n.textContent = `Data load error: ${err.message}`;
        main.prepend(n);
      }
    }
  }

  async function landing() {
    // Show quick stats if live data available; else show flagged note.
    const stats = document.getElementById('landing-stats');
    try {
      const events = await fetchEvents('open');
      const inScope = events.filter((e) => e.in_scope);
      const top = inScope.slice(0, 5);
      stats.innerHTML = `
        <div class="card"><h3>Live events (in scope)</h3><div class="metric">${inScope.length}</div><p>Gas · Elections · Culture · Crypto · Golf</p></div>
        <div class="card"><h3>Top notional</h3><div class="metric">${top.length ? money(top[0].notional) : '—'}</div><p>${top.length ? esc(top[0].title) : 'awaiting data'}</p></div>
        <div class="card"><h3>Mode</h3><div class="metric">${MODE === 'backend' ? 'Live' : 'Direct'}</div><p>${MODE === 'backend' ? 'Polling Kalshi demo API' : 'Kalshi public endpoints'}</p></div>
        <div class="card"><h3>Topics</h3><div class="metric">5</div><p>gas, elections, culture, crypto, golf</p></div>`;
      const topEl = document.getElementById('landing-top');
      const cols = [
        { label: 'Event', render: (r) => `<a href="events.html?ticker=${encodeURIComponent(r.event_ticker)}">${esc(r.title)}</a>` },
        { label: 'Topic', render: (r) => topicBadge(r.topic) },
        { label: 'Status', render: (r) => statusBadge(r.status) },
        { label: 'Est. notional', num: true, render: (r) => money(r.notional) },
        { label: 'Volume', num: true, render: (r) => r.volume },
        { label: 'Source', render: (r) => srcLink('https://docs.kalshi.com/api-reference/events/get-events', 'Get Events API') },
      ];
      renderTable(topEl, cols, top, { empty: 'No in-scope live events found.' });
    } catch (err) {
      stats.innerHTML = `<div class="card"><h3>Live data</h3><div class="metric unverified">unavailable</div><p>Kalshi demo API unreachable from this host (FLAG-01).</p></div>`;
      const n = document.createElement('div');
      n.className = 'note danger';
      n.innerHTML = `Live market data could not be loaded: <b>${esc(err.message)}</b>. This is expected on a static host without Kalshi access. The dashboard is fully implemented; see <a href="flagged.html">Flagged for Review</a>.`;
      document.querySelector('main').prepend(n);
    }
  }

  async function eventsPage() {
    const topicFilter = new URLSearchParams(location.search).get('topic') || 'all';
    const container = document.getElementById('events-table');
    const sel = document.getElementById('topic-filter');
    if (sel) {
      const opts = ['all', ...TOPICS].map((t) => `<option value="${t}" ${t === topicFilter ? 'selected' : ''}>${t === 'all' ? 'All topics' : TOPIC_LABELS[t]}</option>`).join('');
      sel.innerHTML = opts;
      sel.onchange = () => { location.search = sel.value === 'all' ? '' : `?topic=${sel.value}`; };
    }
    setStatus('warn', 'Loading events…');
    const events = await fetchEvents('open');
    const filtered = events.filter((e) => e.in_scope && (topicFilter === 'all' || e.topic === topicFilter));
    filtered.sort((a, b) => b.notional - a.notional);
    setStatus(MODE === 'backend' ? 'ok' : 'warn', `${filtered.length} in-scope events`);
    const cols = [
      { label: 'Event', render: (r) => `<a class="row-link" href="market.html?ticker=${encodeURIComponent(r.markets[0] ? r.markets[0].ticker : r.event_ticker)}&series=${encodeURIComponent(r.series_ticker || '')}">${esc(r.title)}</a>` },
      { label: 'Topic', render: (r) => topicBadge(r.topic) },
      { label: 'Status', render: (r) => statusBadge(r.status) },
      { label: 'Est. notional', num: true, render: (r) => money(r.notional) },
      { label: 'Volume (contracts)', num: true, render: (r) => r.volume },
      { label: 'Markets', num: true, render: (r) => (r.markets || []).length },
      { label: 'Resolution', render: (r) => resolutionBadge(r.markets && r.markets.find((m) => m.status === 'settled') ? r.markets.find((m) => m.status === 'settled').outcome : null) },
      { label: 'Source', render: (r) => srcLink('https://docs.kalshi.com/api-reference/events/get-events', 'Get Events') },
    ];
    renderTable(container, cols, filtered, { empty: 'No in-scope live events. Kalshi may be unreachable (see Flagged).' });
  }

  async function categoryPage() {
    const topic = document.body.getAttribute('data-topic');
    const container = document.getElementById('cat-table');
    document.getElementById('cat-title').textContent = TOPIC_LABELS[topic] + ' Markets';
    setStatus('warn', 'Loading…');
    const events = await fetchEvents('open');
    const filtered = events.filter((e) => e.in_scope && e.topic === topic).sort((a, b) => b.notional - a.notional);
    // Flatten to market rows
    const rows = [];
    for (const ev of filtered) for (const m of ev.markets || []) rows.push({ ...m, event: ev.title, topic });
    rows.sort((a, b) => (b.last_price || 0) - (a.last_price || 0));
    setStatus(MODE === 'backend' ? 'ok' : 'warn', `${rows.length} markets`);
    const cols = [
      { label: 'Market', render: (r) => `<a class="row-link" href="market.html?ticker=${encodeURIComponent(r.ticker)}&series=${encodeURIComponent(r.series_ticker || '')}">${esc(r.title)}</a>` },
      { label: 'Event', render: (r) => esc(r.event) },
      { label: 'Yes bid', num: true, render: (r) => price(r.yes_bid) },
      { label: 'Yes ask', num: true, render: (r) => price(r.yes_ask) },
      { label: 'Volume', num: true, render: (r) => r.volume },
      { label: 'Status', render: (r) => statusBadge(r.status) },
      { label: 'Source', render: () => srcLink('https://docs.kalshi.com/api-reference/market/get-markets', 'Get Markets') },
    ];
    renderTable(container, cols, rows, { empty: `No live ${TOPIC_LABELS[topic]} markets found.` });
  }

  async function marketPage() {
    const params = new URLSearchParams(location.search);
    const ticker = params.get('ticker') || '';
    const series = params.get('series') || '';
    const chartCanvas = document.getElementById('price-chart');
    const liquidityEl = document.getElementById('liquidity-table');
    const statEl = document.getElementById('market-stats');
    const periodSel = document.getElementById('period-sel');
    const hoursSel = document.getElementById('hours-sel');
    if (periodSel) periodSel.onchange = loadChart;
    if (hoursSel) hoursSel.onchange = loadChart;

    if (!ticker) {
      setStatus('err', 'No ticker provided');
      return;
    }
    // Orderbook (liquidity)
    try {
      const ob = await fetchOrderbook(ticker);
      let cumYes = 0, cumNo = 0;
      const yesRows = ob.yes.slice().reverse().map((l) => { cumYes += l.count; return { price: l.price, count: l.count, cum: cumYes, side: 'YES' }; });
      const noRows = ob.no.slice().reverse().map((l) => { cumNo += l.count; return { price: l.price, count: l.count, cum: cumNo, side: 'NO' }; });
      const rows = [...yesRows, ...noRows].sort((a, b) => b.price - a.price);
      const cols = [
        { label: 'Side', render: (r) => `<span class="badge ${r.side === 'YES' ? 'yes' : 'no'}">${r.side}</span>` },
        { label: 'Price ($)', num: true, render: (r) => price(r.price) },
        { label: 'Contracts', num: true, render: (r) => r.count },
        { label: 'Cum. depth', num: true, render: (r) => r.cum },
      ];
      renderTable(liquidityEl, cols, rows, { empty: 'No orderbook data (unverified).' });
      statEl.innerHTML = `
        <div class="card"><h3>Best YES bid</h3><div class="metric">${price(ob.best_yes_bid && ob.best_yes_bid.price)}</div><p>${ob.best_yes_bid ? ob.best_yes_bid.count + ' contracts' : '—'}</p></div>
        <div class="card"><h3>Best NO bid</h3><div class="metric">${price(ob.best_no_bid && ob.best_no_bid.price)}</div><p>${ob.best_no_bid ? ob.best_no_bid.count + ' contracts' : '—'}</p></div>
        <div class="card"><h3>Spread</h3><div class="metric">${ob.spread == null ? '—' : ob.spread}</div><p>cents</p></div>
        <div class="card"><h3>Total YES depth</h3><div class="metric">${cumYes}</div><p>contracts</p></div>`;
    } catch (err) {
      liquidityEl.innerHTML = `<div class="empty unverified">Liquidity unavailable: ${esc(err.message)} (unverified)</div>`;
    }
    await loadChart();

    async function loadChart() {
      const period = Number(periodSel.value);
      const hours = Number(hoursSel.value);
      try {
        const candles = await fetchCandlesticks(series, ticker, period, hours);
        const points = candles.map((c) => ({ ts: c.ts, price: c.price }));
        drawChart(chartCanvas, points, { color: '#00b67a' });
        setStatus(MODE === 'backend' ? 'ok' : 'warn', `${points.length} candles · ${period}m window`);
      } catch (err) {
        setStatus('err', `Chart unavailable: ${err.message}`);
      }
    }

    // live price updates over WS (backend mode)
    connectWS((msg) => {
      if (msg.ticker === ticker && chartCanvas) {
        // append point
        const last = chartCanvas.__points && chartCanvas.__points[chartCanvas.__points.length - 1];
        const pts = chartCanvas.__points || [];
        if (!last || msg.ts > last.ts) pts.push({ ts: msg.ts, price: msg.price });
        chartCanvas.__points = pts.slice(-1000);
        drawChart(chartCanvas, chartCanvas.__points, { color: '#00b67a' });
      }
    });
  }

  async function portfolioPage() {
    const el = document.getElementById('portfolio');
    if (MODE !== 'backend') {
      el.innerHTML = `<div class="note">Portfolio requires the authenticated backend (a Kalshi demo API key). Running in static/direct mode, portfolio data is unavailable — flagged as <b>unverified</b>. See <a href="flagged.html">Flagged for Review</a> (FLAG-02).</div>`;
      return;
    }
    try {
      const r = await fetch('/api/portfolio', { cache: 'no-store' });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'portfolio failed');
      const bal = d.balance || {};
      el.innerHTML = `
        <div class="cards">
          <div class="card"><h3>Available balance</h3><div class="metric">${money(bal.available_balance || bal.available)}</div><p>USD</p></div>
          <div class="card"><h3>Total balance</h3><div class="metric">${money(bal.total_balance || bal.total)}</div><p>USD</p></div>
          <div class="card"><h3>Margin</h3><div class="metric">${money(bal.margin || bal.margin_used)}</div><p>USD</p></div>
        </div>
        <p class="src">Source: <a href="https://docs.kalshi.com/llms.txt" target="_blank" rel="noopener">Kalshi portfolio endpoints</a></p>`;
    } catch (err) {
      el.innerHTML = `<div class="note danger">Portfolio unavailable: ${esc(err.message)} (unverified)</div>`;
    }
  }

  async function tradesPage() {
    const el = document.getElementById('trades-table');
    if (MODE !== 'backend') {
      el.innerHTML = `<div class="note">Trade records are stored by the authenticated backend. In static/direct mode there are no executed trades to display. See <a href="flagged.html">Flagged for Review</a> (FLAG-02).</div>`;
      return;
    }
    try {
      const r = await fetch('/api/trades/records', { cache: 'no-store' });
      const d = await r.json();
      const trades = d.trades || [];
      const cols = [
        { label: 'Time', render: (r) => esc(new Date(r.ts).toLocaleString()) },
        { label: 'Market', render: (r) => esc(r.title || r.market_ticker) },
        { label: 'Topic', render: (r) => topicBadge(r.topic) },
        { label: 'Side', render: (r) => r.side === 'yes' ? '<span class="badge yes">YES</span>' : r.side === 'no' ? '<span class="badge no">NO</span>' : esc(r.side) },
        { label: 'Price', num: true, render: (r) => price(r.price) },
        { label: 'Count', num: true, render: (r) => r.count },
        { label: 'Type', render: (r) => esc(r.type) },
        { label: 'Status', render: (r) => esc(r.status) },
      ];
      renderTable(el, cols, trades, { empty: 'No trades executed yet.' });
    } catch (err) {
      el.innerHTML = `<div class="note danger">Trades unavailable: ${esc(err.message)}</div>`;
    }
  }

  async function strategiesPage() {
    const el = document.getElementById('strategies');
    if (MODE !== 'backend') {
      el.innerHTML = `<div class="note">Strategy analysis is computed from executed trades in the backend. No trades yet in static mode — see <a href="flagged.html">Flagged</a> (FLAG-02).</div>`;
      return;
    }
    try {
      const r = await fetch('/api/strategies', { cache: 'no-store' });
      const d = await r.json();
      const perf = d.performance || {};
      const totals = perf.totals || {};
      const rows = (d.strategies || []).map((s) => ({ ...s }));
      const perfHtml = `
        <div class="cards">
          <div class="card"><h3>Trades</h3><div class="metric">${totals.count || 0}</div></div>
          <div class="card"><h3>P&L</h3><div class="metric">${money(totals.pnl)}</div></div>
          <div class="card"><h3>Win rate</h3><div class="metric">${((totals.winRate || 0) * 100).toFixed(0)}%</div></div>
        </div>`;
      const cols = [
        { label: 'Strategy', render: (r) => esc(r.title) },
        { label: 'Rationale', render: (r) => esc(r.rationale) },
        { label: 'Suggested action', render: (r) => esc(r.action) },
        { label: 'Priority', render: (r) => `<span class="badge priority-${esc(r.priority)}">${esc(r.priority)}</span>` },
        { label: 'Status', render: (r) => `<span class="badge decision-${esc(r.status || 'proposed')}">${esc(r.status || 'proposed')}</span>` },
      ];
      renderTable(el, cols, rows, { empty: 'No strategy suggestions yet. Execute trades to generate suggestions.' });
      document.getElementById('strategies-perf').innerHTML = perfHtml;
    } catch (err) {
      el.innerHTML = `<div class="note danger">Strategies unavailable: ${esc(err.message)}</div>`;
    }
  }

  async function suggestionsPage() {
    const el = document.getElementById('suggestions');
    try {
      const r = await fetch('/api/suggestions', { cache: 'no-store' });
      const d = await r.json();
      const items = d.suggestions || [];
      const cols = [
        { label: 'ID', render: (r) => esc(r.id) },
        { label: 'Suggestion', render: (r) => esc(r.title) },
        { label: 'Detail', render: (r) => esc(r.detail) },
        { label: 'Priority', render: (r) => `<span class="badge priority-${esc(r.priority)}">${esc(r.priority)}</span>` },
        { label: 'Category', render: (r) => esc(r.category) },
        { label: 'Decision', render: (r) => `<span class="badge decision-${esc(r.status || 'proposed')}">${esc(r.status || 'proposed')}</span>` },
        { label: 'Source', render: (r) => srcLink(r.source, 'source') },
        { label: 'Action', render: (r, i) => {
          const stat = r.status || 'proposed';
          const btns = ['proposed', 'reviewing', 'accepted', 'implemented'].map((s) => `<button class="btn" data-i="${i}" data-s="${s}" ${s === stat ? 'disabled' : ''}>${s}</button>`).join(' ');
          return btns;
        } },
      ];
      renderTable(el, cols, items, { empty: 'No suggestions.' });
      el.addEventListener('click', async (e) => {
        const b = e.target.closest('button[data-s]');
        if (!b) return;
        const i = Number(b.dataset.i), s = b.dataset.s;
        const item = items[i];
        const row = b.closest('tr');
        const decisionCell = row.querySelector('td:nth-child(6)');
        try {
          await fetch('/api/suggestions/decision', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: item.id, status: s, decidedBy: 'reviewer' }),
          });
          decisionCell.innerHTML = `<span class="badge decision-${s}">${s}</span>`;
          row.querySelectorAll('button').forEach((x) => { x.disabled = (x.dataset.s === s); });
        } catch (err) {
          decisionCell.innerHTML = `<span class="badge decision-reviewing">error</span>`;
        }
      });
    } catch (err) {
      el.innerHTML = `<div class="note danger">Suggestions unavailable: ${esc(err.message)}</div>`;
    }
  }

  async function flaggedPage() {
    const el = document.getElementById('flagged');
    try {
      let flags = window.FALLBACK_FLAGS || [];
      if (MODE === 'backend') {
        const r = await fetch('/api/flagged', { cache: 'no-store' });
        if (r.ok) flags = (await r.json()).flags || flags;
      }
      const cols = [
        { label: 'ID', render: (r) => esc(r.id) },
        { label: 'Item', render: (r) => esc(r.title) },
        { label: 'Detail', render: (r) => esc(r.detail) },
        { label: 'Status', render: (r) => `<span class="badge decision-${esc(r.status)}">${esc(r.status)}</span>` },
        { label: 'Source', render: (r) => srcLink(r.source, 'source') },
      ];
      renderTable(el, cols, flags, { empty: 'No flags.' });
    } catch (err) {
      el.innerHTML = `<div class="note danger">Flagged list unavailable: ${esc(err.message)}</div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', init);
  // expose for inline fallback
  window.__kalshi = { TOPICS, TOPIC_LABELS, REST_DEMO };
})();
