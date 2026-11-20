/* =====================================================================
   Kalshi Demo Dashboard — live client-side dashboard.

   Sources (official):
     REST  https://external-api.demo.kalshi.co/trade-api/v2
     WS    wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2
   Everything on this page is read-only. No credentials are requested,
   stored or transmitted. If the browser cannot reach the Kalshi demo
   API (network or CORS), the page falls back to the committed snapshot
   in /data and says so in the status line.
   ===================================================================== */
'use strict';

var API = 'https://external-api.demo.kalshi.co/trade-api/v2';
var API_WS = 'wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2';

/* Topic scope. Kept in sync with tools/collect_kalshi.py (TOPIC_RULES).
   Official Kalshi categories/tags:
   https://external-api.demo.kalshi.co/trade-api/v2/search/tags_by_categories */
var TOPICS = {
  'gas-prices': {
    label: 'Gas prices',
    categories: ['Commodities', 'Economics'],
    tags: ['Oil & Gas', 'Oil and energy'],
    words: ['gasoline', 'gas price', 'gas prices', 'diesel', 'heating oil', 'crude oil', 'crude', 'wti', 'brent', 'gas tax']
  },
  'elections': {
    label: 'Elections',
    categories: ['Elections'],
    tags: [],
    words: ['election', 'elections', 'primary', 'ballot', 'nominee', 'nominations', 'senate', 'governor', 'house control', 'presidential winner', 'mayor', 'referendum']
  },
  'culture': {
    label: 'Culture',
    categories: ['Entertainment', 'Culture'],
    tags: ['Movies', 'Music', 'Awards', 'Television', 'People', 'Music charts', 'Video games', 'Live Music', 'Reality TV', 'Oscars', 'Grammys', 'Critics Choice Awards', 'Golden Globes', 'The Game Awards', 'Art', 'Food', 'Music Streams', 'Movie Charts', 'TV Charts', 'Achievements', 'Collectibles', 'Music Industry', 'Rotten Tomatoes', 'Views'],
    words: ['oscar', 'oscars', 'grammy', 'grammys', 'emmy', 'emmys', 'box office', 'movie', 'film', 'music', 'album', 'celebrity', 'tv show', 'netflix', 'spotify', 'billboard', 'hollywood', 'met gala', 'golden globe', 'album of the year', 'song of the year']
  },
  'crypto': {
    label: 'Crypto',
    categories: ['Crypto'],
    tags: [],
    words: ['bitcoin', 'btc', 'ethereum', 'ether', 'eth price', 'crypto', 'solana', 'sol price', 'doge', 'dogecoin', 'xrp', 'zec', 'bnb']
  },
  'golf': {
    label: 'Golf',
    categories: [],
    tags: ['Golf'],
    words: ['golf', 'pga', 'masters', 'ryder cup', 'lpga', 'us open golf', 'open championship', 'golfers']
  }
};

var seriesByTicker = {};
var markets = [];
var settled = [];
var selected = null;
var livePoints = [];        /* locally captured polling points for the selected market */
var candlePoints = [];      /* official candlestick history for the selected market */
var pollTimer = null;
var listTimer = null;
var marketTimer = null;
var ws = null;
var dataMode = 'live';      /* 'live' | 'snapshot' */

function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s === undefined || s === null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function num(v) { var n = parseFloat(v); return isFinite(n) ? n : null; }
function money(v) {
  var n = num(v);
  return n === null ? '' : '$' + n.toFixed(2);
}
function fixed(v) {
  if (v === undefined || v === null || v === '') return '';
  var n = parseFloat(v);
  return isFinite(n) ? n.toFixed(2) : String(v);
}
function blank(v) { return (v === undefined || v === null || v === '') ? '<span class="blank" title="Not present in the API response — unverified">—</span>' : esc(v); }

/* ---------------- topic classification ---------------- */
function topicOf(m) {
  var st = m.series_ticker || '';
  var info = seriesByTicker[st] || {};
  var cats = info.categories || (info.category ? [info.category] : []);
  var tags = info.tags || [];
  var text = (' ' + ((m.title || '') + ' ' + (m.subtitle || '') + ' ' + (m.ticker || '') + ' ' + (m.event_ticker || '')).toLowerCase().replace(/[^a-z0-9&+.\- ]+/g, ' ') + ' ');
  var id;
  for (id in TOPICS) {
    if (!TOPICS.hasOwnProperty(id)) continue;
    var r = TOPICS[id];
    var i;
    for (i = 0; i < r.categories.length; i++) { if (cats.indexOf(r.categories[i]) >= 0) return id; }
    for (i = 0; i < r.tags.length; i++) { if (tags.indexOf(r.tags[i]) >= 0) return id; }
  }
  for (id in TOPICS) {
    if (!TOPICS.hasOwnProperty(id)) continue;
    var w = TOPICS[id].words;
    for (var j = 0; j < w.length; j++) {
      if (w[j].indexOf(' ') >= 0) { if (text.indexOf(' ' + w[j] + ' ') >= 0) return id; }
      else if (text.indexOf(' ' + w[j] + ' ') >= 0) return id;
    }
  }
  return null;
}

/* ---------------- data loading ---------------- */
function fetchJSON(url) {
  return fetch(url, { headers: { 'Accept': 'application/json' } }).then(function (r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  });
}

function loadAllMarkets(status, maxPages) {
  var out = [], cursor = '', page = 0;
  function step() {
    var url = API + '/markets?limit=1000&status=' + status + (cursor ? '&cursor=' + encodeURIComponent(cursor) : '');
    return fetchJSON(url).then(function (j) {
      out = out.concat(j.markets || []);
      cursor = j.cursor || '';
      page++;
      if (cursor && page < (maxPages || 10)) return step();
      return out;
    });
  }
  return step();
}

function loadSeries() {
  var out = [];
  function step(cursor) {
    var url = API + '/series' + (cursor ? '?cursor=' + encodeURIComponent(cursor) : '');
    return fetchJSON(url).then(function (j) {
      out = out.concat(j.series || []);
      if (j.cursor && out.length < 4000) return step(j.cursor);
      return out;
    });
  }
  return step('').catch(function () { return []; });
}

function loadSnapshot() {
  return Promise.all([
    fetch('data/markets_open.json').then(function (r) { return r.json(); }),
    fetch('data/markets_settled.json').then(function (r) { return r.json(); }),
    fetch('data/series_scope.json').then(function (r) { return r.json(); })
  ]).then(function (res) {
    var open = res[0].rows || [], set = res[1].rows || [], ser = res[2].rows || [];
    ser.forEach(function (s) {
      seriesByTicker[s.series_ticker] = { categories: s.categories || [], category: s.category || '', tags: s.tags || [] };
    });
    return { open: open, settled: set, collected: res[0].collected_at };
  });
}

function applySnapshot(rows, topicKey) {
  /* Snapshot rows already carry their topic from the Python classifier. */
  return rows.filter(function (r) { return !topicKey || r.topic === topicKey; });
}

/* ---------------- rendering ---------------- */
function turnover(m) {
  var v = num(m.volume_fp), p = num(m.last_price_dollars);
  if (v === null || p === null) return null;
  return v * p;
}

function renderMarketsTable() {
  var topic = $('topicFilter').value;
  var q = ($('searchBox').value || '').toLowerCase();
  var rows = markets.filter(function (m) {
    if (topic && topicOf(m) !== topic) return false;
    if (q && ((m.title || '') + ' ' + (m.ticker || '')).toLowerCase().indexOf(q) < 0) return false;
    return true;
  });
  rows.sort(function (a, b) {
    var ta = turnover(a), tb = turnover(b);
    if (ta === null && tb === null) return String(a.ticker).localeCompare(String(b.ticker));
    if (ta === null) return 1;
    if (tb === null) return -1;
    return tb - ta;
  });
  var tbody = $('marketsBody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="muted">No in-scope markets in the current listing.</td></tr>';
  } else {
    tbody.innerHTML = rows.slice(0, 300).map(function (m) {
      var t = turnover(m);
      return '<tr>' +
        '<td class="mono nowrap"><a href="' + esc(m.source_url || ('https://external-api.demo.kalshi.co/trade-api/v2/markets/' + encodeURIComponent(m.ticker))) + '" target="_blank" rel="noopener">' + esc(m.ticker) + '</a></td>' +
        '<td>' + esc(m.title || '') + '<div class="muted small mono">' + esc(m.series_ticker || m.event_ticker || '') + '</div></td>' +
        '<td><span class="pill">' + esc(topicOf(m) || '—') + '</span></td>' +
        '<td class="num">' + (money(m.last_price_dollars) || '<span class="blank">—</span>') + '</td>' +
        '<td class="num">' + (money(m.yes_bid_dollars) || '<span class="blank">—</span>') + '</td>' +
        '<td class="num">' + (money(m.yes_ask_dollars) || '<span class="blank">—</span>') + '</td>' +
        '<td class="num">' + fixed(m.volume_fp) + '</td>' +
        '<td class="num">' + (t === null ? '<span class="blank">—</span>' : '$' + t.toFixed(2)) + '</td>' +
        '<td class="nowrap small">' + esc(m.close_time || '') + '</td>' +
        '</tr>';
    }).join('');
  }
  $('marketCount').textContent = rows.length + ' in-scope market' + (rows.length === 1 ? '' : 's');
  $('rowNote').textContent = 'Showing up to 300 of ' + rows.length + ' rows. "Est. $ turnover" = volume_fp × last_price_dollars; the API has no dollar-turnover field (flagged).';
}

function renderSettledTable() {
  var tbody = $('settledBody');
  var rows = settled.slice(0, 200);
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="muted">No settled in-scope markets returned by the API.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (m) {
    var res = (m.result || '').toLowerCase();
    var cls = res === 'yes' ? 'yes' : (res === 'no' ? 'no' : 'grey');
    var label = res === 'yes' ? 'YES' : (res === 'no' ? 'NO' : '—');
    return '<tr>' +
      '<td class="mono nowrap"><a href="' + esc(m.source_url || '') + '" target="_blank" rel="noopener">' + esc(m.ticker) + '</a></td>' +
      '<td>' + esc(m.title || '') + '</td>' +
      '<td><span class="pill ' + cls + '">' + label + '</span></td>' +
      '<td class="num">' + (money(m.settlement_value_dollars) || '<span class="blank">—</span>') + '</td>' +
      '<td class="nowrap small">' + esc(m.settlement_ts || '') + '</td>' +
      '<td class="nowrap small">' + esc(m.close_time || '') + '</td>' +
      '</tr>';
  }).join('');
}

function renderTickerSelect() {
  var sel = $('tickerSelect');
  var opts = markets.slice(0, 300).map(function (m) {
    return '<option value="' + esc(m.ticker) + '">' + esc(m.ticker) + ' — ' + esc((m.title || '').slice(0, 70)) + '</option>';
  }).join('');
  sel.innerHTML = opts;
}

/* ---------------- chart ---------------- */
function windowMs() { return parseInt($('windowSel').value, 10) * 1000; }

function fmtTime(ts, spanMs) {
  var d = new Date(ts);
  function p(n) { return (n < 10 ? '0' : '') + n; }
  if (spanMs <= 6 * 3600 * 1000) return p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  if (spanMs <= 3 * 24 * 3600 * 1000) return p(d.getHours()) + ':' + p(d.getMinutes());
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
}

function drawChart() {
  var c = $('priceChart');
  if (!c) return;
  var dpr = window.devicePixelRatio || 1;
  var w = c.clientWidth, h = c.clientHeight;
  c.width = w * dpr; c.height = h * dpr;
  var g = c.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  g.fillStyle = '#0d1628'; g.fillRect(0, 0, w, h);

  var span = windowMs();
  var now = Date.now();
  var from = now - span;
  var pts = [];
  candlePoints.forEach(function (p) { if (p.t >= from && p.t <= now + 60000) pts.push(p); });
  livePoints.forEach(function (p) { if (p.t >= from && p.t <= now + 60000) pts.push(p); });
  pts.sort(function (a, b) { return a.t - b.t; });

  var padL = 52, padR = 14, padT = 16, padB = 30;
  var plotW = Math.max(10, w - padL - padR), plotH = Math.max(10, h - padT - padB);

  g.strokeStyle = '#1d2b44'; g.lineWidth = 1;
  g.fillStyle = '#8fa2c0'; g.font = '11px system-ui, sans-serif';
  for (var i = 0; i <= 4; i++) {
    var y = padT + plotH * i / 4;
    g.beginPath(); g.moveTo(padL, y); g.lineTo(w - padR, y); g.stroke();
  }
  for (var k = 0; k <= 4; k++) {
    var x = padL + plotW * k / 4;
    g.beginPath(); g.moveTo(x, padT); g.lineTo(x, padT + plotH); g.stroke();
  }

  if (pts.length < 2) {
    g.fillStyle = '#9fb0c8';
    g.fillText(pts.length ? 'Collecting points…' : 'No price history in this window yet.', padL + 10, padT + 24);
    $('chartNote').textContent = 'No points in the selected window. Try a longer window, or pick a market with recent trades.';
    return;
  }

  var lo = Infinity, hi = -Infinity;
  pts.forEach(function (p) { if (p.v < lo) lo = p.v; if (p.v > hi) hi = p.v; });
  var pad = Math.max((hi - lo) * 0.15, 0.01);
  lo = Math.max(0, lo - pad); hi = Math.min(1, hi + pad);
  if (hi <= lo) hi = lo + 0.02;

  g.fillStyle = '#8fa2c0';
  for (var j = 0; j <= 4; j++) {
    var val = hi - (hi - lo) * j / 4;
    g.fillText('$' + val.toFixed(2), 6, padT + plotH * j / 4 + 4);
  }

  var t0 = pts[0].t, t1 = pts[pts.length - 1].t;
  if (t1 === t0) t1 = t0 + 1;
  for (var m = 0; m <= 4; m++) {
    var xt = t0 + (t1 - t0) * m / 4;
    g.fillText(fmtTime(xt, span), Math.min(w - 58, padL + plotW * m / 4 - 22), h - 10);
  }

  function X(t) { return padL + plotW * (t - t0) / (t1 - t0); }
  function Y(v) { return padT + plotH * (1 - (v - lo) / (hi - lo)); }

  /* candlestick history in a muted line */
  var cs = candlePoints.filter(function (p) { return p.t >= from && p.t <= now + 60000; });
  if (cs.length > 1) {
    g.strokeStyle = '#3d5a86'; g.lineWidth = 1.5; g.beginPath();
    cs.forEach(function (p, i) { var px = X(p.t), py = Y(p.v); i ? g.lineTo(px, py) : g.moveTo(px, py); });
    g.stroke();
  }
  /* live polled points in the accent colour */
  g.strokeStyle = '#00d68f'; g.lineWidth = 2; g.beginPath();
  var drew = false;
  pts.forEach(function (p, i) {
    var px = X(p.t), py = Y(p.v);
    if (!drew) { g.moveTo(px, py); drew = true; } else g.lineTo(px, py);
  });
  g.stroke();
  g.fillStyle = '#00d68f';
  var last = pts[pts.length - 1];
  g.beginPath(); g.arc(X(last.t), Y(last.v), 3.5, 0, Math.PI * 2); g.fill();

  $('chartNote').textContent = pts.length + ' points · window ' + ($('windowSel').selectedOptions[0] ? $('windowSel').selectedOptions[0].textContent : '') +
    ' · last ' + (money(last.v) || '—') + ' at ' + new Date(last.t).toLocaleString() +
    ' · source: ' + (candlePoints.length ? 'official candlesticks + live polling' : 'live polling only');
}

/* ---------------- candles ---------------- */
function loadCandles() {
  if (!selected) return Promise.resolve();
  var spanSec = Math.round(windowMs() / 1000);
  var period = spanSec <= 60 * 60 * 6 ? 1 : (spanSec <= 60 * 60 * 48 ? 60 : 1440);
  var end = Math.floor(Date.now() / 1000);
  var start = end - spanSec;
  /* 1-minute candles are limited to ~5,000 periods per request */
  if (period === 1 && spanSec / 60 > 4900) { period = 60; }
  var url = API + '/series/' + encodeURIComponent(selected.series_ticker || '') +
    '/markets/' + encodeURIComponent(selected.ticker) +
    '/candlesticks?start_ts=' + start + '&end_ts=' + end + '&period_interval=' + period;
  return fetchJSON(url).then(function (j) {
    candlePoints = (j.candlesticks || []).map(function (c) {
      var px = null;
      if (c.price) px = num(c.price.close_dollars);
      if (px === null && c.price) px = num(c.price.open_dollars);
      if (px === null && c.yes_bid) px = num(c.yes_bid.close_dollars);
      if (px === null) return null;
      return { t: (c.end_period_ts || 0) * 1000, v: px, src: 'candles' };
    }).filter(Boolean);
    drawChart();
  }).catch(function () { candlePoints = []; });
}

/* ---------------- orderbook ---------------- */
function loadOrderbook() {
  var box = $('orderbookBox');
  if (!selected) { box.innerHTML = '<span class="muted">Select a market first.</span>'; return; }
  box.innerHTML = '<span class="muted">Loading orderbook…</span>';
  fetchJSON(API + '/markets/' + encodeURIComponent(selected.ticker) + '/orderbook').then(function (j) {
    var ob = j.orderbook_fp || {};
    var yes = ob.yes_dollars || [], no = ob.no_dollars || [];
    if (!yes.length && !no.length) {
      box.innerHTML = '<span class="muted">The API returned an empty book (no resting orders) for ' + esc(selected.ticker) + '.</span>';
      return;
    }
    var bestYesBid = yes.length ? yes[yes.length - 1] : null;
    var bestNoBid = no.length ? no[no.length - 1] : null;
    var bestYesAsk = bestNoBid ? (1 - parseFloat(bestNoBid[0])).toFixed(4) : null;
    var spread = (bestYesBid && bestYesAsk) ? (parseFloat(bestYesAsk) - parseFloat(bestYesBid[0])).toFixed(4) : null;

    function sideRows(arr, cls) {
      if (!arr.length) return '<tr><td colspan="3" class="muted">No resting bids</td></tr>';
      return arr.slice().reverse().slice(0, 12).map(function (lv) {
        var size = parseFloat(lv[1]);
        var wpc = Math.min(100, size / 500 * 100);
        return '<tr><td class="num">' + money(lv[0]) + '</td>' +
          '<td class="num">' + fixed(lv[1]) + '</td>' +
          '<td class="bar ' + cls + '"><div style="width:' + wpc.toFixed(1) + '%">&nbsp;</div></td></tr>';
      }).join('');
    }
    box.innerHTML =
      '<div class="kv small">' +
      '<dt>Best YES bid</dt><dd>' + (bestYesBid ? money(bestYesBid[0]) + ' (' + fixed(bestYesBid[1]) + ' contracts)' : '<span class="blank">—</span>') + '</dd>' +
      '<dt>Best YES ask</dt><dd>' + (bestYesAsk ? '$' + bestYesAsk + ' <span class="muted">(implied: $1.00 − best NO bid)</span>' : '<span class="blank">—</span>') + '</dd>' +
      '<dt>Spread</dt><dd>' + (spread !== null ? '$' + spread : '<span class="blank">—</span>') + '</dd>' +
      '<dt>Source</dt><dd class="mono small"><a target="_blank" rel="noopener" href="' + esc(API + '/markets/' + encodeURIComponent(selected.ticker) + '/orderbook') + '">orderbook response</a></dd>' +
      '</div>' +
      '<div class="depth" style="margin-top:12px">' +
      '<div><h4 style="margin:0 0 6px;font-size:13.5px">YES bids — contracts available to buy YES</h4>' +
      '<div class="tablewrap"><table><thead><tr><th class="num">Price</th><th class="num">Contracts</th><th>Depth</th></tr></thead><tbody>' + sideRows(yes, '') + '</tbody></table></div></div>' +
      '<div><h4 style="margin:0 0 6px;font-size:13.5px">NO bids — contracts available to buy NO (each is a YES ask at $1.00 − price)</h4>' +
      '<div class="tablewrap"><table><thead><tr><th class="num">Price</th><th class="num">Contracts</th><th>Depth</th></tr></thead><tbody>' + sideRows(no, 'no') + '</tbody></table></div></div>' +
      '</div>' +
      '<p class="muted small" style="margin-top:8px">Bars are scaled to 500 contracts; Kalshi returns bids only, and implied asks are derived from the opposite side (official orderbook guidance).</p>';
  }).catch(function (e) {
    box.innerHTML = '<span class="status bad">Orderbook unavailable: ' + esc(e.message) + '. No values are inferred.</span>';
  });
}

/* ---------------- live polling ---------------- */
function pollMarket() {
  if (!selected) return;
  fetchJSON(API + '/markets/' + encodeURIComponent(selected.ticker)).then(function (j) {
    var m = j.market || {};
    var p = num(m.yes_bid_dollars);
    if (p === null) p = num(m.last_price_dollars);
    if (p !== null) {
      livePoints.push({ t: Date.now(), v: p, src: 'poll' });
      var keep = windowMs() * 2;
      livePoints = livePoints.filter(function (x) { return Date.now() - x.t <= keep; });
    }
    if (m.last_price_dollars) {
      $('selectedLast').textContent = money(m.last_price_dollars);
      $('selectedBid').textContent = money(m.yes_bid_dollars);
      $('selectedAsk').textContent = money(m.yes_ask_dollars);
    }
    drawChart();
  }).catch(function () { /* keep the last good value; never invent one */ });
}

function selectMarket(ticker) {
  var found = null, i;
  for (i = 0; i < markets.length; i++) { if (markets[i].ticker === ticker) { found = markets[i]; break; } }
  if (!found) { $('chartNote').textContent = 'Ticker ' + ticker + ' is not in the in-scope listing. Type any Kalshi demo ticker to chart it.'; }
  selected = found || { ticker: ticker, title: ticker, series_ticker: '' };
  livePoints = []; candlePoints = [];
  $('selectedTicker').textContent = selected.ticker;
  $('selectedTitle').textContent = selected.title || '';
  $('selectedLast').textContent = money(selected.last_price_dollars) || '—';
  $('selectedBid').textContent = money(selected.yes_bid_dollars) || '—';
  $('selectedAsk').textContent = money(selected.yes_ask_dollars) || '—';
  loadCandles();
  loadOrderbook();
  pollMarket();
  drawChart();
}

/* ---------------- boot ---------------- */
function refreshList() {
  var statusEl = $('liveStatus');
  return loadAllMarkets('open', 10).then(function (all) {
    dataMode = 'live';
    markets = all.filter(function (m) { return topicOf(m); });
    settled = [];
    statusEl.innerHTML = '<span class="ok">Live:</span> ' + markets.length + ' in-scope open markets of ' + all.length + ' open · updated ' + new Date().toLocaleTimeString();
    renderMarketsTable();
    renderTickerSelect();
    return loadAllMarkets('settled', 4);
  }).then(function (set) {
    settled = set.filter(function (m) { return topicOf(m); });
    renderSettledTable();
  }).catch(function (e) {
    return loadSnapshot().then(function (snap) {
      dataMode = 'snapshot';
      markets = applySnapshot(snap.open, null);
      settled = applySnapshot(snap.settled, null);
      $('liveStatus').innerHTML = '<span class="status warn">Snapshot mode:</span> the browser could not reach the Kalshi demo API (' + esc(e.message) + '). Showing the snapshot collected ' + esc(snap.collected) + ' by the scheduled collector.';
      renderMarketsTable();
      renderTickerSelect();
      renderSettledTable();
    }).catch(function (e2) {
      statusEl.innerHTML = '<span class="status bad">No data:</span> live API unreachable (' + esc(e.message) + ') and no local snapshot (' + esc(e2.message) + '). No values are shown or inferred.';
    });
  });
}

function init() {
  if (!$('marketsBody')) return;
  loadSeries().then(function (series) {
    series.forEach(function (s) {
      seriesByTicker[s.ticker] = { categories: s.categories || [], category: s.category || '', tags: s.tags || [] };
    });
    return refreshList();
  });

  $('refreshBtn').onclick = function () { refreshList(); };
  $('topicFilter').onchange = renderMarketsTable;
  $('searchBox').oninput = renderMarketsTable;
  $('tickerSelect').onchange = function () { selectMarket(this.value); };
  $('windowSel').onchange = function () { loadCandles(); drawChart(); };
  $('pollSel').onchange = function () {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(pollMarket, parseInt(this.value, 10) * 1000);
  };
  $('orderbookBtn').onclick = loadOrderbook;
  $('tradeBtn').onclick = function () {
    var t = selected ? selected.ticker : '';
    window.location.href = 'pages/portfolio.html' + (t ? '#order-' + encodeURIComponent(t) : '');
  };
  window.addEventListener('resize', drawChart);

  pollTimer = setInterval(pollMarket, parseInt($('pollSel').value, 10) * 1000);
  listTimer = setInterval(refreshList, 60000);

  /* WebSocket is best-effort only. The dashboard never depends on it. */
  try {
    ws = new WebSocket(API_WS);
    ws.onopen = function () { $('wsStatus').innerHTML = '<span class="ok">WS connected</span> (ticker channel not subscribed — no credentials are used)'; };
    ws.onerror = function () { $('wsStatus').innerHTML = '<span class="status warn">WebSocket unavailable — REST polling continues.</span>'; };
    ws.onclose = function () { $('wsStatus').innerHTML = '<span class="status warn">WebSocket closed — REST polling continues.</span>'; };
  } catch (e) {
    $('wsStatus').innerHTML = '<span class="status warn">WebSocket unavailable — REST polling continues.</span>';
  }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
