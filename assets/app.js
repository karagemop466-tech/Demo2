/* ==========================================================================
   Kalshi Demo Monitor - shared client.

   Public market data only: GET /markets, GET /markets/{ticker},
   GET /markets/{ticker}/orderbook, GET /series/.../candlesticks.
   Official references:
     https://docs.kalshi.com/api-reference/market/get-markets
     https://docs.kalshi.com/api-reference/market/get-market-orderbook
     https://docs.kalshi.com/api-reference/market/get-market-candlesticks
     https://docs.kalshi.com/getting_started/quick_start_market_data

   Portfolio / trading (pages/portfolio.html only) uses the documented signed
   request scheme:
     https://docs.kalshi.com/getting_started/quick_start_authenticated_requests
     https://docs.kalshi.com/getting_started/api_keys
   The private key is held in memory for the life of the page only. It is never
   written to localStorage, sessionStorage, a cookie, or the network beyond the
   signature request itself.

   Every number rendered here comes from an API response. Nothing is inferred:
   a missing field is rendered as an explicit "UNVERIFIED" marker.
   ========================================================================== */
(function (global) {
  'use strict';

  var DEMO_REST = 'https://external-api.demo.kalshi.co/trade-api/v2';
  var DOCS = {
    markets: 'https://docs.kalshi.com/api-reference/market/get-markets',
    market: 'https://docs.kalshi.com/api-reference/market/get-market',
    orderbook: 'https://docs.kalshi.com/api-reference/market/get-market-orderbook',
    candles: 'https://docs.kalshi.com/api-reference/market/get-market-candlesticks',
    events: 'https://docs.kalshi.com/api-reference/events/get-events',
    demo: 'https://docs.kalshi.com/getting_started/demo_env',
    auth: 'https://docs.kalshi.com/getting_started/quick_start_authenticated_requests',
    keys: 'https://docs.kalshi.com/getting_started/api_keys',
    order: 'https://docs.kalshi.com/getting_started/quick_start_create_order',
    marketData: 'https://docs.kalshi.com/getting_started/quick_start_market_data',
    fixedPoint: 'https://docs.kalshi.com/getting_started/fixed_point_migration',
    direction: 'https://docs.kalshi.com/getting_started/order_direction',
  };

  var TOPICS = [
    { id: 'gas', label: 'Gas prices' },
    { id: 'elections', label: 'Elections' },
    { id: 'culture', label: 'Culture' },
    { id: 'crypto', label: 'Crypto' },
    { id: 'golf', label: 'Golf' },
  ];

  var METRICS = {
    traded: { label: 'Contract value traded ($)', key: 'contract_value_traded_usd' },
    oi: { label: 'Open interest value ($)', key: 'open_interest_usd' },
    volume: { label: 'Contracts traded (volume_fp)', key: 'volume_fp' },
  };

  /* ------------------------------ helpers ------------------------------ */
  var $ = function (id) { return document.getElementById(id); };

  function esc(s) {
    return String(s === undefined || s === null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function num(v) {
    if (v === undefined || v === null || v === '') return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }

  function money(v, dp) {
    var n = num(v);
    if (n === null) return null;
    return '$' + n.toFixed(dp === undefined ? 2 : dp);
  }

  function count(v) {
    var n = num(v);
    if (n === null) return null;
    return n.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }

  function when(iso) {
    if (!iso) return null;
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return d.toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
  }

  function unv(text) {
    return '<span class="unv">' + esc(text || 'UNVERIFIED') + '</span>';
  }

  /** Cell renderer: value -> html, blank fields become an explicit marker. */
  function cell(v, fmt) {
    if (v === undefined || v === null || v === '') return unv();
    var out = fmt ? fmt(v) : String(v);
    if (out === null || out === '') return unv();
    return esc(out);
  }

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  /* ------------------------------- fetch ------------------------------- */
  var requestLog = [];

  function api(path, opts) {
    opts = opts || {};
    var url = (opts.base || DEMO_REST) + path;
    return fetch(url, { headers: { accept: 'application/json' } }).then(function (res) {
      requestLog.push({ url: url, status: res.status, at: new Date().toISOString() });
      if (res.status === 429) { var e = new Error('Rate limited by the Kalshi API (HTTP 429).'); e.code = 429; throw e; }
      if (!res.ok) throw new Error('HTTP ' + res.status + ' from ' + path);
      return res.json();
    }, function (err) {
      requestLog.push({ url: url, status: 'network_error', at: new Date().toISOString() });
      throw new Error('The browser could not reach the Kalshi demo API (network or CORS restriction).');
    });
  }

  function apiRetry(path, opts) {
    opts = opts || {};
    var tries = opts.tries || 4;
    var attempt = 0;
    function run() {
      return api(path, opts).catch(function (err) {
        attempt += 1;
        if (attempt >= tries) throw err;
        return sleep(400 * Math.pow(2, attempt)).then(run);
      });
    }
    return run();
  }

  /* ------------------------------ state ------------------------------- */
  var state = {
    snapshot: null,
    meta: null,
    markets: [],          // rows for the active topic
    allMarkets: [],
    settled: [],
    events: [],
    live: {},             // ticker -> refreshed market object
    selected: null,
    topic: 'all',
    metric: 'traded',
    windowSec: 3600,
    points: [],
    orderbook: null,
    mode: 'snapshot',     // 'snapshot' | 'live'
    lastError: null,
  };

  var listeners = [];

  function onChange(fn) { listeners.push(fn); }
  function emit() { listeners.forEach(function (fn) { try { fn(state); } catch (e) { /* noop */ } }); }

  /* ---------------------------- snapshot load -------------------------- */
  function loadJSON(rel) {
    return fetch(rel, { headers: { accept: 'application/json' } }).then(function (r) {
      if (!r.ok) throw new Error('Missing ' + rel + ' (HTTP ' + r.status + ')');
      return r.json();
    });
  }

  function loadSnapshot() {
    return Promise.all([
      loadJSON('data/meta.json'),
      loadJSON('data/open-markets.json'),
      loadJSON('data/open-events.json'),
      loadJSON('data/settled-markets.json'),
      loadJSON('data/orderbooks.json'),
    ]).then(function (parts) {
      state.meta = parts[0];
      state.allMarkets = [].concat.apply([], Object.keys(parts[1].topics).map(function (k) { return parts[1].topics[k]; }));
      state.events = [].concat.apply([], Object.keys(parts[2].topics).map(function (k) { return parts[2].topics[k]; }));
      state.settled = [].concat.apply([], Object.keys(parts[3].topics).map(function (k) { return parts[3].topics[k]; }));
      state.orderbookSnapshot = parts[4].books || {};
      applyTopicFilter();
      emit();
    });
  }

  function rowsFor(topic) {
    if (!state.allMarkets.length) return [];
    if (topic === 'all') return state.allMarkets;
    return state.allMarkets.filter(function (m) { return m.topic === topic; });
  }

  function settledFor(topic) {
    if (!state.settled.length) return [];
    if (topic === 'all') return state.settled;
    return state.settled.filter(function (m) { return m.topic === topic; });
  }

  function eventsFor(topic) {
    if (!state.events.length) return [];
    if (topic === 'all') return state.events;
    return state.events.filter(function (e) { return e.topic === topic; });
  }

  function applyTopicFilter() {
    state.markets = rowsFor(state.topic).slice();
    sortMarkets();
  }

  function sortMarkets() {
    var key = (METRICS[state.metric] || METRICS.traded).key;
    state.markets.sort(function (a, b) {
      var av = num(a[key]), bv = num(b[key]);
      return (bv === null ? -1 : bv) - (av === null ? -1 : av);
    });
  }

  /* --------------------------- table rendering ------------------------- */
  function marketRow(m) {
    var live = state.live[m.ticker] || m;
    var value = live.contract_value_traded_usd !== undefined ? live.contract_value_traded_usd : m.contract_value_traded_usd;
    var oiUsd = live.open_interest_usd !== undefined ? live.open_interest_usd : m.open_interest_usd;
    var vol = live.volume_fp !== undefined ? live.volume_fp : m.volume_fp;
    var last = live.last_price_dollars !== undefined ? live.last_price_dollars : m.last_price_dollars;
    var bid = live.yes_bid_dollars !== undefined ? live.yes_bid_dollars : m.yes_bid_dollars;
    var ask = live.yes_ask_dollars !== undefined ? live.yes_ask_dollars : m.yes_ask_dollars;
    return '<tr data-ticker="' + esc(m.ticker) + '"' +
      (state.selected && state.selected.ticker === m.ticker ? ' class="selected"' : '') + '>' +
      '<td><span class="tag ' + esc(m.topic) + '">' + esc(topicLabel(m.topic)) + '</span></td>' +
      '<td class="ticker nowrap"><a href="' + esc(m.source_url) + '" target="_blank" rel="noopener">' + esc(m.ticker) + '</a></td>' +
      '<td class="title-cell"><span class="t">' + esc(m.title || m.event_title || '') + '</span>' +
      '<span class="s">' + esc(m.event_title && m.title ? m.event_title : (m.series_title || '')) + '</span></td>' +
      '<td class="num" data-field="last">' + cell(last, function (v) { return money(v, 4); }) + '</td>' +
      '<td class="num nowrap" data-field="quote">' + cell(bid, function (v) { return money(v, 4); }) + ' / ' + cell(ask, function (v) { return money(v, 4); }) + '</td>' +
      '<td class="num" data-field="volume">' + cell(vol, count) + '</td>' +
      '<td class="num" data-field="traded">' + cell(value, function (v) { return money(v, 2); }) + '</td>' +
      '<td class="num" data-field="oi">' + cell(oiUsd, function (v) { return money(v, 2); }) + '</td>' +
      '<td class="nowrap" data-field="close">' + cell(m.close_time, when) + '</td>' +
      '<td class="nowrap"><a href="' + esc(m.source_url) + '" target="_blank" rel="noopener">API</a> ' +
      '<a href="' + esc(DOCS.markets) + '" target="_blank" rel="noopener">docs</a></td>' +
      '</tr>';
  }

  function topicLabel(id) {
    for (var i = 0; i < TOPICS.length; i += 1) if (TOPICS[i].id === id) return TOPICS[i].label;
    return id;
  }

  function renderMarkets() {
    var tb = document.querySelector('#marketTable tbody');
    if (!tb) return;
    var rows = state.markets.slice(0, 60);
    tb.innerHTML = rows.length
      ? rows.map(marketRow).join('')
      : '<tr><td colspan="10" class="muted">No in-scope markets in the current snapshot.</td></tr>';
    tb.querySelectorAll('tr[data-ticker]').forEach(function (tr) {
      tr.addEventListener('click', function (ev) {
        if (ev.target.tagName === 'A') return;
        selectMarket(tr.getAttribute('data-ticker'));
      });
    });
  }

  function renderEvents() {
    var tb = document.querySelector('#eventTable tbody');
    if (!tb) return;
    var rows = eventsFor(state.topic).slice(0, 40);
    tb.innerHTML = rows.length
      ? rows.map(function (e) {
        return '<tr>' +
          '<td><span class="tag ' + esc(e.topic) + '">' + esc(topicLabel(e.topic)) + '</span></td>' +
          '<td class="title-cell"><span class="t">' + esc(e.title || '') + '</span><span class="s">' + esc(e.event_ticker) + '</span></td>' +
          '<td class="num">' + cell(e.markets, count) + '</td>' +
          '<td class="num">' + cell(e.volume_fp, count) + '</td>' +
          '<td class="num">' + cell(e.contract_value_traded_usd, function (v) { return money(v, 2); }) + '</td>' +
          '<td class="num">' + cell(e.open_interest_usd, function (v) { return money(v, 2); }) + '</td>' +
          '<td class="nowrap">' + cell(e.close_time, when) + '</td>' +
          '<td class="nowrap"><a href="' + esc(e.source_url) + '" target="_blank" rel="noopener">API</a></td>' +
          '</tr>';
      }).join('')
      : '<tr><td colspan="8" class="muted">No in-scope events in the current snapshot.</td></tr>';
  }

  function renderSettled() {
    var tb = document.querySelector('#resolvedTable tbody');
    if (!tb) return;
    var rows = settledFor(state.topic).slice(0, 40);
    tb.innerHTML = rows.length
      ? rows.map(function (m) {
        var res = m.result === 'yes' || m.result === 'no' ? m.result : null;
        return '<tr>' +
          '<td><span class="tag ' + esc(m.topic) + '">' + esc(topicLabel(m.topic)) + '</span></td>' +
          '<td class="ticker nowrap"><a href="' + esc(m.source_url) + '" target="_blank" rel="noopener">' + esc(m.ticker) + '</a></td>' +
          '<td class="title-cell"><span class="t">' + esc(m.title || '') + '</span></td>' +
          '<td>' + (res ? '<span class="badge ' + res + '">' + res.toUpperCase() + '</span>' : unv()) + '</td>' +
          '<td class="num">' + cell(m.settlement_value_dollars, function (v) { return money(v, 4); }) + '</td>' +
          '<td class="nowrap">' + cell(m.settlement_ts, when) + '</td>' +
          '<td class="nowrap"><a href="' + esc(m.source_url) + '" target="_blank" rel="noopener">API</a></td>' +
          '</tr>';
      }).join('')
      : '<tr><td colspan="7" class="muted">No settled in-scope markets in the current snapshot.</td></tr>';
  }

  function renderKpis() {
    var set = function (id, v) { var el = $(id); if (el) el.textContent = v; };
    var markets = rowsFor(state.topic);
    var traded = markets.reduce(function (a, m) { return a + (num(m.contract_value_traded_usd) || 0); }, 0);
    var vol = markets.reduce(function (a, m) { return a + (num(m.volume_fp) || 0); }, 0);
    var evs = eventsFor(state.topic);
    var settledRows = settledFor(state.topic);
    var yes = settledRows.filter(function (m) { return m.result === 'yes'; }).length;
    var no = settledRows.filter(function (m) { return m.result === 'no'; }).length;
    set('kpiMarkets', markets.length.toLocaleString('en-US'));
    set('kpiTraded', money(traded, 0) || '$0');
    set('kpiVolume', count(vol) || '0');
    set('kpiEvents', evs.length.toLocaleString('en-US'));
    set('kpiResolved', settledRows.length ? yes + ' yes / ' + no + ' no' : '—');
    set('kpiUpdated', state.meta && state.meta.generated_at ? when(state.meta.generated_at) : '—');
  }

  /* --------------------------- market selection ------------------------ */
  function findRow(ticker) {
    var found = null;
    state.allMarkets.forEach(function (m) { if (m.ticker === ticker) found = m; });
    return found;
  }

  function selectMarket(ticker) {
    var row = findRow(ticker);
    if (!row) return;
    state.selected = row;
    state.points = [];
    var titleEl = $('selectedTitle');
    var tickerEl = $('selectedTicker');
    if (titleEl) titleEl.textContent = row.title || row.event_title || row.ticker;
    if (tickerEl) tickerEl.textContent = row.ticker + ' · ' + (row.series_title || row.series_ticker || '');
    renderMarkets();
    loadCandles();
    pollMarket();
    loadOrderbook();
    emit();
  }

  /* ------------------------------- chart ------------------------------- */
  var WINDOWS = [
    { sec: 900, label: 'Last 15 minutes', interval: 1 },
    { sec: 3600, label: 'Last 1 hour', interval: 1 },
    { sec: 21600, label: 'Last 6 hours', interval: 60 },
    { sec: 86400, label: 'Last 24 hours', interval: 60 },
    { sec: 259200, label: 'Last 3 days', interval: 1440 },
  ];

  function windowDef(sec) {
    for (var i = 0; i < WINDOWS.length; i += 1) if (WINDOWS[i].sec === sec) return WINDOWS[i];
    return WINDOWS[1];
  }

  function loadCandles() {
    var row = state.selected;
    if (!row) return Promise.resolve();
    if (!row.series_ticker) {
      renderChartNote('No series_ticker recorded for this market, so candlesticks cannot be requested (the Get Markets response has no series_ticker field). Showing live snapshots only.');
      return Promise.resolve();
    }
    var def = windowDef(state.windowSec);
    var end = Math.floor(Date.now() / 1000);
    var start = end - def.sec;
    var url = '/series/' + encodeURIComponent(row.series_ticker) + '/markets/' + encodeURIComponent(row.ticker) +
      '/candlesticks?start_ts=' + start + '&end_ts=' + end + '&period_interval=' + def.interval;
    return apiRetry(url).then(function (json) {
      var candles = (json && json.candlesticks) || [];
      state.points = candles.map(function (c) {
        var price = c.price && (c.price.close_dollars !== undefined ? c.price.close_dollars : c.price.close);
        return { t: Number(c.end_period_ts), p: num(price) };
      }).filter(function (p) { return p.p !== null; });
      renderChartNote('Official candlesticks: ' + candles.length + ' periods of ' + def.interval +
        ' minute(s) from ' + DOCS.candles + '. Newest points are live REST snapshots.');
      renderChart();
    }).catch(function (err) {
      state.points = [];
      renderChartNote('Candlesticks unavailable (' + err.message + '). Live snapshots only.');
      renderChart();
    });
  }

  function renderChartNote(text) {
    var el = $('chartNote');
    if (el) el.textContent = text;
  }

  function renderChart() {
    var canvas = $('priceChart');
    if (!canvas || !global.KalshiChart) return;
    global.KalshiChart.draw(canvas, state.points, {
      xLabel: 'time (' + windowDef(state.windowSec).label.toLowerCase() + ')',
      emptyText: 'Waiting for price data…',
    });
  }

  function appendPoint(p, t, live) {
    var last = state.points[state.points.length - 1];
    if (last && last.t === t) return;
    state.points.push({ t: t, p: p, live: !!live });
    var cut = t - state.windowSec * 1.2;
    state.points = state.points.filter(function (x) { return x.t >= cut; });
  }

  /* ---------------------------- live polling --------------------------- */
  function pollMarket() {
    if (!state.selected) return Promise.resolve();
    var ticker = state.selected.ticker;
    return apiRetry('/markets/' + encodeURIComponent(ticker)).then(function (json) {
      var m = json.market || json;
      if (!m || !m.ticker) return;
      state.live[ticker] = m;
      var price = num(m.last_price_dollars);
      if (price !== null) {
        appendPoint(price, Math.floor(Date.now() / 1000), true);
        renderChart();
      }
      updateSelectedKpis(m);
    }).catch(function (err) {
      setStatus('Live refresh: ' + err.message, 'down');
    });
  }

  function updateSelectedKpis(m) {
    var set = function (id, v) { var el = $(id); if (el) el.textContent = v; };
    set('selLast', m.last_price_dollars ? money(m.last_price_dollars, 4) : '—');
    set('selBid', m.yes_bid_dollars ? money(m.yes_bid_dollars, 4) : '—');
    set('selAsk', m.yes_ask_dollars ? money(m.yes_ask_dollars, 4) : '—');
    set('selVolume', m.volume_fp ? count(m.volume_fp) : '—');
    set('selOi', m.open_interest_fp ? count(m.open_interest_fp) : '—');
    set('selClose', m.close_time ? when(m.close_time) : '—');
    set('selStatus', m.status || '—');
  }

  /* ------------------------------ orderbook ---------------------------- */
  function renderBook(rows, maxQty) {
    if (!rows || !rows.length) return '<p class="muted">No resting bids reported at this level.</p>';
    var max = maxQty || rows.reduce(function (a, r) { return Math.max(a, num(r[1]) || 0); }, 0) || 1;
    return '<table><thead><tr><th class="num">Price</th><th class="num">Contracts</th><th>Depth</th></tr></thead><tbody>' +
      rows.map(function (r, i) {
        var qty = num(r[1]) || 0;
        var pct = Math.max(2, Math.round((qty / max) * 100));
        return '<tr' + (i === 0 ? ' class="best"' : '') + '>' +
          '<td class="num">' + esc(r[0]) + '</td>' +
          '<td class="num">' + esc(r[1]) + '</td>' +
          '<td><div class="bar" style="width:' + pct + '%"></div></td>' +
          '</tr>';
      }).join('') + '</tbody></table>';
  }

  function loadOrderbook() {
    if (!state.selected) return Promise.resolve();
    var ticker = state.selected.ticker;
    return apiRetry('/markets/' + encodeURIComponent(ticker) + '/orderbook?depth=12').then(function (json) {
      var book = (json && json.orderbook_fp) || {};
      var yes = (book.yes_dollars || []).slice().reverse();
      var no = (book.no_dollars || []).slice().reverse();
      state.orderbook = { yes: yes, no: no, at: new Date().toISOString() };
      var yEl = $('bookYes');
      var nEl = $('bookNo');
      if (yEl) yEl.innerHTML = renderBook(yes);
      if (nEl) nEl.innerHTML = renderBook(no);
      var at = $('bookAt');
      if (at) at.textContent = 'Orderbook read at ' + state.orderbook.at.replace('T', ' ').slice(0, 19) + ' UTC';
    }).catch(function (err) {
      var yEl = $('bookYes');
      if (yEl) yEl.innerHTML = '<p class="bad">' + esc(err.message) + '</p>';
    });
  }

  /* ------------------------------- status ------------------------------ */
  function setStatus(text, kind) {
    var el = $('liveStatus');
    if (!el) return;
    el.textContent = text;
    var pill = el.closest ? el.closest('.pill') : null;
    if (pill) pill.className = 'pill ' + (kind || '');
  }

  function refreshVisibleRows() {
    // Re-read the series behind the visible rows so the table stays live.
    var series = {};
    state.markets.slice(0, 60).forEach(function (m) {
      if (m.series_ticker) series[m.series_ticker] = true;
    });
    var keys = Object.keys(series).slice(0, 8);
    if (!keys.length) return Promise.resolve();
    return Promise.all(keys.map(function (s) {
      return apiRetry('/markets?series_ticker=' + encodeURIComponent(s) + '&limit=1000').catch(function () { return null; });
    })).then(function (results) {
      var updated = 0;
      results.forEach(function (json) {
        if (!json || !json.markets) return;
        json.markets.forEach(function (m) {
          state.live[m.ticker] = m;
          updated += 1;
        });
      });
      if (updated) {
        state.markets = state.markets.map(function (m) {
          var l = state.live[m.ticker];
          if (!l) return m;
          var price = num(l.last_price_dollars);
          var vol = num(l.volume_fp);
          var oi = num(l.open_interest_fp);
          return {
            ...m,
            last_price_dollars: l.last_price_dollars !== undefined ? l.last_price_dollars : m.last_price_dollars,
            yes_bid_dollars: l.yes_bid_dollars !== undefined ? l.yes_bid_dollars : m.yes_bid_dollars,
            yes_ask_dollars: l.yes_ask_dollars !== undefined ? l.yes_ask_dollars : m.yes_ask_dollars,
            volume_fp: l.volume_fp !== undefined ? l.volume_fp : m.volume_fp,
            contract_value_traded_usd: (price !== null && vol !== null) ? price * vol : m.contract_value_traded_usd,
            open_interest_usd: (price !== null && oi !== null) ? price * oi : m.open_interest_usd,
          };
        });
        sortMarkets();
        renderMarkets();
      }
      state.mode = 'live';
      setStatus('Live · ' + updated + ' markets refreshed from the demo API', 'live');
    });
  }

  /* --------------------------- signed requests ------------------------- */
  function b64ToBytes(b64) {
    var bin = atob(String(b64).replace(/\s/g, ''));
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i);
    return out;
  }

  function bytesToB64(buf) {
    var bytes = new Uint8Array(buf);
    var s = '';
    for (var i = 0; i < bytes.length; i += 1) s += String.fromCharCode(bytes[i]);
    return btoa(s);
  }

  /** DER length encoder. */
  function derLen(len) {
    if (len < 0x80) return new Uint8Array([len]);
    var bytes = [];
    while (len > 0) { bytes.unshift(len & 0xff); len >>= 8; }
    return new Uint8Array([0x80 | bytes.length].concat(bytes));
  }

  function derSeq(parts) {
    var body = [];
    parts.forEach(function (p) { body = body.concat(Array.from(p)); });
    return new Uint8Array([0x30].concat(Array.from(derLen(body.length))).concat(body));
  }

  function derInt(value) {
    var bytes = [value];
    while (bytes.length > 1 && bytes[0] === 0 && bytes[1] < 0x80) bytes.shift();
    if (bytes[0] >= 0x80) bytes.unshift(0);
    return new Uint8Array([0x02].concat(Array.from(derLen(bytes.length))).concat(bytes));
  }

  /** OID 1.2.840.113549.1.1.1 (rsaEncryption) + NULL. */
  function rsaAlgorithmId() {
    var oid = new Uint8Array([0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x01, 0x01]);
    return new Uint8Array([0x30, 0x0d].concat(Array.from(oid)).concat([0x05, 0x00]));
  }

  /** Wrap a PKCS#1 RSA key (BEGIN RSA PRIVATE KEY) in a PKCS#8 envelope. */
  function pkcs1ToPkcs8(pkcs1) {
    var version = derInt(0);
    var alg = rsaAlgorithmId();
    var octet = new Uint8Array([0x04].concat(Array.from(derLen(pkcs1.length))).concat(Array.from(pkcs1)));
    return derSeq([version, alg, octet]);
  }

  /**
   * Import a Kalshi private key.
   * https://docs.kalshi.com/api-reference/api-keys/generate-api-key
   *  - "rsa" keys are issued as PKCS#1 ("BEGIN RSA PRIVATE KEY"), signed RSA-PSS SHA-256.
   *  - "ed25519" keys are issued as PKCS#8 ("BEGIN PRIVATE KEY"), signed directly.
   */
  function importPrivateKey(pem) {
    var header = (pem.match(/-----BEGIN ([^-]+)-----/) || [])[1] || '';
    var body = pem.replace(/-----BEGIN [^-]+-----/g, '').replace(/-----END [^-]+-----/g, '').replace(/\s/g, '');
    if (!body) return Promise.reject(new Error('The private key PEM could not be read.'));
    var der = b64ToBytes(body);
    if (header.indexOf('RSA PRIVATE KEY') >= 0) der = pkcs1ToPkcs8(der);
    return crypto.subtle.importKey('pkcs8', der, { name: 'RSA-PSS', hash: 'SHA-256' }, false, ['sign'])
      .then(function (key) { return { key: key, alg: 'RSA-PSS' }; })
      .catch(function () {
        return crypto.subtle.importKey('pkcs8', der, { name: 'Ed25519' }, false, ['sign'])
          .then(function (key) { return { key: key, alg: 'Ed25519' }; });
      })
      .catch(function () {
        throw new Error('Unsupported private key. Kalshi issues RSA (PKCS#1 or PKCS#8) and Ed25519 keys.');
      });
  }

  /**
   * Signed request.
   * Message signed = timestamp + method + path (full path from the API root, no query).
   * https://docs.kalshi.com/getting_started/quick_start_authenticated_requests
   */
  function signedFetch(path, method, body, credentials) {
    if (!credentials || !credentials.keyId || !credentials.pem) {
      return Promise.reject(new Error('No demo API credentials loaded.'));
    }
    return importPrivateKey(credentials.pem).then(function (imported) {
      var ts = String(Date.now());
      var signPath = '/trade-api/v2' + path.split('?')[0];
      var msg = new TextEncoder().encode(ts + method + signPath);
      var algo = imported.alg === 'Ed25519'
        ? { name: 'Ed25519' }
        : { name: 'RSA-PSS', saltLength: 32 }; // PSS.DIGEST_LENGTH for SHA-256
      return crypto.subtle.sign(algo, imported.key, msg).then(function (sig) {
        var headers = {
          'KALSHI-ACCESS-KEY': credentials.keyId,
          'KALSHI-ACCESS-TIMESTAMP': ts,
          'KALSHI-ACCESS-SIGNATURE': bytesToB64(sig),
        };
        if (body) headers['Content-Type'] = 'application/json';
        return fetch(DEMO_REST + path, {
          method: method,
          headers: headers,
          body: body ? JSON.stringify(body) : undefined,
        });
      });
    }).then(function (res) {
      return res.text().then(function (text) {
        var json = {};
        try { json = text ? JSON.parse(text) : {}; } catch (e) { json = { raw: text }; }
        if (!res.ok) {
          var msg = (json.error && (json.error.message || json.error.code)) || ('HTTP ' + res.status);
          var details = json.error && json.error.details ? (': ' + json.error.details) : '';
          throw new Error(msg + details);
        }
        return json;
      });
    });
  }

  /* ------------------------------ suggestions --------------------------- */
  function voteStore() {
    try { return JSON.parse(localStorage.getItem('kalshi.suggestion.votes') || '{}'); }
    catch (e) { return {}; }
  }

  function renderVotes() {
    var votes = voteStore();
    document.querySelectorAll('[data-vote]').forEach(function (el) {
      var id = el.getAttribute('data-vote');
      var status = $('vote-' + id);
      if (status) status.textContent = votes[id] ? votes[id].label : 'No decision recorded';
    });
  }

  function initVotes() {
    var votes = voteStore();
    document.querySelectorAll('[data-vote]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-vote');
        var label = btn.getAttribute('data-vote-label') || btn.textContent.trim();
        votes[id] = { label: label, at: new Date().toISOString() };
        try { localStorage.setItem('kalshi.suggestion.votes', JSON.stringify(votes)); } catch (e) { /* noop */ }
        renderVotes();
      });
    });
    renderVotes();
  }

  /* ------------------------------- wiring ------------------------------ */
  function init() {
    var topicSel = $('topicFilter');
    if (topicSel) {
      TOPICS.forEach(function (t) {
        var o = document.createElement('option');
        o.value = t.id; o.textContent = t.label;
        topicSel.appendChild(o);
      });
      topicSel.addEventListener('change', function () {
        state.topic = topicSel.value;
        applyTopicFilter();
        renderMarkets(); renderEvents(); renderSettled(); renderKpis();
      });
    }

    var metricSel = $('metricFilter');
    if (metricSel) {
      Object.keys(METRICS).forEach(function (k) {
        var o = document.createElement('option');
        o.value = k; o.textContent = METRICS[k].label;
        metricSel.appendChild(o);
      });
      metricSel.value = state.metric;
      metricSel.addEventListener('change', function () {
        state.metric = metricSel.value;
        sortMarkets(); renderMarkets();
      });
    }

    var winSel = $('windowFilter');
    if (winSel) {
      WINDOWS.forEach(function (w) {
        var o = document.createElement('option');
        o.value = String(w.sec); o.textContent = w.label;
        winSel.appendChild(o);
      });
      winSel.value = String(state.windowSec);
      winSel.addEventListener('change', function () {
        state.windowSec = parseInt(winSel.value, 10);
        loadCandles();
      });
    }

    var canvas = $('priceChart');
    if (canvas && global.KalshiChart) {
      global.KalshiChart.attachHover(canvas, function () { return state.points; }, $('chartTip'));
      window.addEventListener('resize', renderChart);
    }

    var refreshBtn = $('refreshBtn');
    if (refreshBtn) refreshBtn.addEventListener('click', function () {
      refreshVisibleRows();
      if (state.selected) { pollMarket(); loadOrderbook(); }
    });

    loadSnapshot().then(function () {
      renderMarkets(); renderEvents(); renderSettled(); renderKpis();
      setStatus('Snapshot loaded (' + (state.meta && state.meta.generated_at ? when(state.meta.generated_at) : 'n/a') + ') - refreshing live', 'stale');
      refreshVisibleRows().catch(function () {
        setStatus('Live API unreachable from this browser - showing the verified snapshot', 'down');
      });
      if (state.markets.length) selectMarket(state.markets[0].ticker);
      emit();
    }).catch(function (err) {
      setStatus('Could not load data/ snapshot: ' + err.message, 'down');
      renderMarkets(); renderEvents(); renderSettled();
    });

    initVotes();

    setInterval(function () {
      if (state.selected) pollMarket();
    }, 6000);
    setInterval(function () {
      if (state.selected) loadOrderbook();
    }, 12000);
    setInterval(function () {
      refreshVisibleRows().catch(function () { /* keep the snapshot */ });
    }, 45000);

    onChange(function (s) {
      var gen = $('snapshotStamp');
      if (gen && s.meta) gen.textContent = 'Snapshot generated ' + when(s.meta.generated_at);
    });
  }

  global.KalshiApp = {
    state: state,
    esc: esc,
    num: num,
    money: money,
    count: count,
    when: when,
    unv: unv,
    cell: cell,
    api: api,
    apiRetry: apiRetry,
    signedFetch: signedFetch,
    importPrivateKey: importPrivateKey,
    selectMarket: selectMarket,
    renderMarkets: renderMarkets,
    renderSettled: renderSettled,
    renderEvents: renderEvents,
    loadSnapshot: loadSnapshot,
    DOCS: DOCS,
    DEMO_REST: DEMO_REST,
    TOPICS: TOPICS,
    requestLog: requestLog,
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
}(window));
