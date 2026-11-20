/* =====================================================================
   Portfolio, order entry and trade analysis — Kalshi DEMO only.

   Two ways to reach an account:
     1. Local CLI (recommended, no key ever touches a browser):
        python3 tools/kalshi_trade.py --key <key.pem> --key-id <KEY_ID> balance
     2. In-browser signer (opt-in): the PEM is imported into WebCrypto on
        this device and every signed request goes straight from this browser
        to Kalshi. The key is never stored by the server, never transmitted,
        and is held in memory only.

   Signing follows https://docs.kalshi.com/getting_started/api_keys :
     message = <timestamp ms><METHOD><path without query>
     Ed25519 -> sign directly; RSA -> PSS/SHA-256, salt length = digest length.
   ===================================================================== */
'use strict';

var BASE = 'https://external-api.demo.kalshi.co/trade-api/v2';
var TRADES_KEY = 'kalshi_demo_trades_v1';
var state = { keyId: '', key: null, alg: '', connected: false, fills: [], positions: [], settlements: [] };

function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s === undefined || s === null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function n(v) { var x = parseFloat(v); return isFinite(x) ? x : null; }
function money(v) { var x = n(v); return x === null ? '' : '$' + x.toFixed(2); }
function cents(v) { var x = n(v); return x === null ? '' : '$' + (x / 100).toFixed(2); }
function num(v) { return v === undefined || v === null || v === '' ? '<span class="blank" title="Not available — unverified">—</span>' : esc(v); }

/* ------------------------------------------------ key handling */
function pemToDer(pem) {
  var b64 = pem.replace(/-----BEGIN [^-]+-----/g, '').replace(/-----END [^-]+-----/g, '').replace(/\s+/g, '');
  var bin = atob(b64), arr = new Uint8Array(bin.length);
  for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}
function b64(bytes) {
  var s = '', a = new Uint8Array(bytes);
  for (var i = 0; i < a.length; i++) s += String.fromCharCode(a[i]);
  return btoa(s);
}
function importKey(pem) {
  var der = pemToDer(pem);
  return crypto.subtle.importKey('pkcs8', der, { name: 'Ed25519' }, false, ['sign'])
    .then(function (k) { return { key: k, alg: 'Ed25519' }; })
    .catch(function () {
      return crypto.subtle.importKey('pkcs8', der, { name: 'RSA-PSS', hash: 'SHA-256' }, false, ['sign'])
        .then(function (k) { return { key: k, alg: 'RSA-PSS' }; });
    });
}
function signedFetch(path, method, body) {
  var ts = String(Date.now());
  var signPath = '/trade-api/v2' + path.split('?')[0];
  var msg = new TextEncoder().encode(ts + method + signPath);
  var sig;
  if (state.alg === 'Ed25519') {
    sig = crypto.subtle.sign('Ed25519', state.key, msg);
  } else {
    sig = crypto.subtle.sign({ name: 'RSA-PSS', saltLength: 32 }, state.key, msg);
  }
  return sig.then(function (s) {
    return fetch(BASE + path, {
      method: method,
      headers: {
        'KALSHI-ACCESS-KEY': state.keyId,
        'KALSHI-ACCESS-TIMESTAMP': ts,
        'KALSHI-ACCESS-SIGNATURE': b64(s),
        'Content-Type': 'application/json'
      },
      body: body ? JSON.stringify(body) : undefined
    });
  }).then(function (r) {
    return r.text().then(function (t) {
      var j = {};
      try { j = JSON.parse(t); } catch (e) { j = { raw: t }; }
      if (!r.ok) {
        var err = new Error('HTTP ' + r.status + ' — ' + (j && j.message ? j.message : (j && j.error ? j.error : t.slice(0, 200))));
        err.payload = j;
        throw err;
      }
      return j;
    });
  });
}

/* ------------------------------------------------ trade log (local) */
function loadTrades() {
  try { return JSON.parse(localStorage.getItem(TRADES_KEY) || '[]'); } catch (e) { return []; }
}
function saveTrades(t) { localStorage.setItem(TRADES_KEY, JSON.stringify(t)); }

/* ------------------------------------------------ strategy taxonomy
   Every tag is derived from official fields only: topic, side, entry price,
   time to close, and the book at entry. No tag is invented from the outcome. */
function strategyFor(t) {
  var p = n(t.price);
  var band = p === null ? 'unknown' : (p < 0.25 ? 'longshot (<25c)' : (p < 0.6 ? 'mid (25-60c)' : 'favourite (>60c)'));
  var d = t.time_to_close_days;
  var ttc = d === null || d === undefined ? 'unknown horizon' :
    (d < 2 ? 'short-dated (<2d)' : (d < 30 ? 'medium (2-30d)' : 'long (>30d)'));
  var entry = t.entry_side || 'unknown';
  return {
    topic: t.topic || 'other',
    side: t.side,
    band: band,
    horizon: ttc,
    entry: entry,
    label: (t.topic || 'other') + ' · ' + (t.side || '?').toUpperCase() + ' · ' + band + ' · ' + ttc + ' · ' + entry
  };
}
function categorise(trades) {
  var groups = {};
  trades.forEach(function (t) {
    var s = strategyFor(t);
    t.strategy = s.label;
    t.strategy_parts = s;
    if (!groups[s.label]) groups[s.label] = { label: s.label, parts: s, trades: [], wins: 0, losses: 0, pending: 0, pnl: 0, contracts: 0 };
    var g = groups[s.label];
    g.trades.push(t);
    g.contracts += t.count || 0;
    if (t.outcome === 'yes' || t.result === 'yes') { g.wins++; g.pnl += (t.pnl !== undefined && t.pnl !== null) ? t.pnl : 0; }
    else if (t.outcome === 'no' || t.result === 'no') { g.losses++; g.pnl += (t.pnl !== undefined && t.pnl !== null) ? t.pnl : 0; }
    else { g.pending++; }
  });
  return groups;
}

/* ------------------------------------------------ connect */
function connect() {
  var out = $('connectStatus');
  var keyId = $('keyId').value.trim();
  var pem = $('keyPem').value.trim();
  if (!keyId || !pem) { out.innerHTML = '<span class="status warn">Enter both the API key id and the private key PEM.</span>'; return; }
  if (!$('ackBox').checked) { out.innerHTML = '<span class="status warn">Tick the acknowledgement first.</span>'; return; }
  out.innerHTML = '<span class="status">Importing key…</span>';
  importKey(pem).then(function (k) {
    state.key = k.key; state.alg = k.alg; state.keyId = keyId;
    return signedFetch('/portfolio/balance', 'GET');
  }).then(function (bal) {
    state.connected = true;
    out.innerHTML = '<span class="status ok">Connected to the demo API (' + esc(state.alg) + '). Balance: ' + cents(bal.balance) + '</span>';
    $('keyPem').value = '';
    return refreshPortfolio();
  }).catch(function (e) {
    state.connected = false;
    out.innerHTML = '<span class="status bad">Could not connect: ' + esc(e.message) + '</span>';
  });
}

function refreshPortfolio() {
  if (!state.connected) return Promise.resolve();
  var out = $('portfolioBox');
  out.innerHTML = '<span class="muted">Loading portfolio…</span>';
  return Promise.all([
    signedFetch('/portfolio/balance', 'GET'),
    signedFetch('/portfolio/positions?limit=200', 'GET'),
    signedFetch('/portfolio/fills?limit=200', 'GET'),
    signedFetch('/portfolio/settlements?limit=200', 'GET')
  ]).then(function (res) {
    var bal = res[0], pos = res[1], fills = res[2], sett = res[3];
    state.fills = fills.fills || [];
    state.positions = pos.market_positions || pos.positions || [];
    state.settlements = sett.settlements || [];
    renderPortfolio(bal, pos, fills, sett);
  }).catch(function (e) {
    out.innerHTML = '<span class="status bad">Portfolio unavailable: ' + esc(e.message) + '</span>';
  });
}

function renderPortfolio(bal, pos, fills, sett) {
  var positions = pos.market_positions || pos.positions || [];
  var fillRows = (fills.fills || []).map(function (f) {
    return '<tr><td class="mono nowrap">' + esc(f.ticker || '') + '</td><td>' + esc(f.side || '') + '</td>' +
      '<td class="num">' + num(f.count) + '</td><td class="num">' + money(f.price / 100) + '</td>' +
      '<td class="num">' + num(f.created_time) + '</td><td class="mono small">' + esc(f.trade_id || f.order_id || '') + '</td></tr>';
  }).join('');
  var posRows = positions.map(function (p) {
    return '<tr><td class="mono nowrap">' + esc(p.ticker || '') + '</td><td class="num">' + num(p.position) + '</td>' +
      '<td class="num">' + num(p.traded) + '</td><td class="num">' + money(p.realized_pnl / 100) + '</td></tr>';
  }).join('');
  var setRows = (sett.settlements || []).map(function (s) {
    return '<tr><td class="mono nowrap">' + esc(s.ticker || '') + '</td><td>' + esc(s.revenue || '') + '</td>' +
      '<td class="num">' + num(s.settled_time) + '</td></tr>';
  }).join('');

  $('portfolioBox').innerHTML =
    '<div class="kv small">' +
    '<dt>Balance</dt><dd>' + cents(bal.balance) + ' <span class="muted">(source: /portfolio/balance)</span></dd>' +
    '<dt>Open positions</dt><dd>' + positions.length + '</dd>' +
    '<dt>Fills</dt><dd>' + (fills.fills || []).length + '</dd>' +
    '<dt>Settlements</dt><dd>' + (sett.settlements || []).length + '</dd>' +
    '</div>' +
    '<h4 style="margin:14px 0 6px;font-size:14px">Positions</h4>' +
    '<div class="tablewrap"><table><thead><tr><th>Ticker</th><th class="num">Position</th><th class="num">Traded</th><th class="num">Realized P&amp;L</th></tr></thead><tbody>' +
    (posRows || '<tr><td colspan="4" class="muted">No open positions.</td></tr>') + '</tbody></table></div>' +
    '<h4 style="margin:14px 0 6px;font-size:14px">Fills</h4>' +
    '<div class="tablewrap"><table><thead><tr><th>Ticker</th><th>Side</th><th class="num">Count</th><th class="num">Price</th><th>Created</th><th>Trade id</th></tr></thead><tbody>' +
    (fillRows || '<tr><td colspan="6" class="muted">No fills yet.</td></tr>') + '</tbody></table></div>' +
    '<h4 style="margin:14px 0 6px;font-size:14px">Settlements</h4>' +
    '<div class="tablewrap"><table><thead><tr><th>Ticker</th><th>Revenue</th><th class="num">Settled</th></tr></thead><tbody>' +
    (setRows || '<tr><td colspan="3" class="muted">No settlements yet.</td></tr>') + '</tbody></table></div>';
}

/* ------------------------------------------------ order entry */
function placeOrder() {
  var out = $('orderResult');
  if (!state.connected) { out.innerHTML = '<span class="status warn">Connect a demo account first.</span>'; return; }
  var ticker = $('orderTicker').value.trim();
  var side = $('orderSide').value;
  var count = parseInt($('orderCount').value, 10);
  var price = parseFloat($('orderPrice').value);
  var type = $('orderType').value;
  if (!ticker || !count) { out.innerHTML = '<span class="status warn">Ticker and count are required.</span>'; return; }
  if (type === 'limit' && !isFinite(price)) { out.innerHTML = '<span class="status warn">A limit order needs a price in dollars (0–1).</span>'; return; }
  var body = { ticker: ticker, side: side, count: count, type: type, time_in_force: 'gtc' };
  if (type === 'limit') body.yes_price = Math.round(price * 100);
  out.innerHTML = '<span class="status">Submitting…</span>';
  signedFetch('/portfolio/orders', 'POST', body).then(function (j) {
    out.innerHTML = '<span class="status ok">Order accepted by the demo API.</span><pre class="mono" style="white-space:pre-wrap">' + esc(JSON.stringify(j, null, 2)) + '</pre>';
    var trades = loadTrades();
    trades.push({
      placed_at: new Date().toISOString(),
      ticker: ticker, side: side, count: count,
      price: type === 'limit' ? price : null,
      order_type: type, response: j,
      topic: window.__topicOfTicker ? window.__topicOfTicker(ticker) : null
    });
    saveTrades(trades);
    renderTradeLog();
    refreshPortfolio();
  }).catch(function (e) {
    out.innerHTML = '<span class="status bad">Order rejected: ' + esc(e.message) + '</span>';
    if (e.payload) out.innerHTML += '<pre class="mono" style="white-space:pre-wrap">' + esc(JSON.stringify(e.payload, null, 2)) + '</pre>';
  });
}

/* ------------------------------------------------ trade log + categories */
function renderTradeLog() {
  var trades = loadTrades();
  var rows = trades.map(function (t, i) {
    var s = strategyFor(t);
    return '<tr><td>' + esc((t.placed_at || '').slice(0, 19).replace('T', ' ')) + '</td>' +
      '<td class="mono nowrap">' + esc(t.ticker) + '</td>' +
      '<td>' + esc(t.side) + '</td>' +
      '<td class="num">' + num(t.count) + '</td>' +
      '<td class="num">' + (t.price === null || t.price === undefined ? '' : money(t.price)) + '</td>' +
      '<td class="small">' + esc(s.label) + '</td>' +
      '<td class="small">' + esc((t.response && t.response.order && t.response.order.status) || (t.response && t.response.status) || '') + '</td>' +
      '<td><button class="secondary" data-del="' + i + '">Remove</button></td></tr>';
  }).join('');
  $('tradeLogBody').innerHTML = rows || '<tr><td colspan="8" class="muted">No orders have been placed from this browser yet.</td></tr>';
  Array.prototype.forEach.call(document.querySelectorAll('#tradeLogBody button[data-del]'), function (b) {
    b.onclick = function () {
      var arr = loadTrades();
      arr.splice(parseInt(b.getAttribute('data-del'), 10), 1);
      saveTrades(arr);
      renderTradeLog();
    };
  });

  var groups = categorise(trades);
  var gRows = Object.keys(groups).map(function (k) {
    var g = groups[k];
    var winRate = (g.wins + g.losses) ? (100 * g.wins / (g.wins + g.losses)).toFixed(1) + '%' : '—';
    return '<tr><td class="small">' + esc(g.label) + '</td><td class="num">' + g.trades.length + '</td>' +
      '<td class="num">' + g.contracts + '</td><td class="num">' + g.wins + '</td><td class="num">' + g.losses + '</td>' +
      '<td class="num">' + g.pending + '</td><td class="num">' + winRate + '</td>' +
      '<td class="num">' + (g.trades.some(function (t) { return t.pnl !== undefined && t.pnl !== null; }) ? '$' + g.pnl.toFixed(2) : '—') + '</td></tr>';
  }).join('');
  $('strategyBody').innerHTML = gRows || '<tr><td colspan="8" class="muted">No trades to categorise yet. Every trade is tagged from official fields only (topic, side, price band, time to close, entry side).</td></tr>';
}

/* ------------------------------------------------ boot */
function init() {
  if (!$('portfolioBox')) return;
  $('connectBtn').onclick = connect;
  $('disconnectBtn').onclick = function () {
    state.connected = false; state.key = null; state.keyId = '';
    $('connectStatus').innerHTML = '<span class="status">Disconnected. The key was removed from memory.</span>';
    $('portfolioBox').innerHTML = '<span class="muted">Not connected.</span>';
  };
  $('placeOrderBtn').onclick = placeOrder;
  $('refreshPortfolioBtn').onclick = refreshPortfolio;
  $('clearLogBtn').onclick = function () { saveTrades([]); renderTradeLog(); };
  renderTradeLog();

  var hash = (location.hash || '').replace(/^#order-/, '');
  if (hash) { $('orderTicker').value = decodeURIComponent(hash); }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
