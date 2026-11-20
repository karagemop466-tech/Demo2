/* ==========================================================================
   Kalshi Demo Monitor - portfolio & demo trading.

   Signed requests exactly as Kalshi documents them:
     https://docs.kalshi.com/getting_started/quick_start_authenticated_requests
     https://docs.kalshi.com/getting_started/api_keys
     https://docs.kalshi.com/getting_started/quick_start_create_order
     https://docs.kalshi.com/getting_started/order_direction

   Security posture:
     * The private key is read from the form into a JavaScript variable only.
     * It is never written to localStorage, sessionStorage, a cookie or a log.
     * It is used for nothing except producing the request signature, and the
       signed request goes to the Kalshi demo host only.
   ========================================================================== */
(function (global) {
  'use strict';

  var App = global.KalshiApp;
  var $ = function (id) { return document.getElementById(id); };
  var creds = { keyId: '', pem: '' };

  function esc(s) {
    return String(s === undefined || s === null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function money(v, dp) {
    var n = Number(v);
    if (!isFinite(n)) return '—';
    return '$' + n.toFixed(dp === undefined ? 2 : dp);
  }
  function count(v) {
    var n = Number(v);
    if (!isFinite(n)) return '—';
    return n.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }
  function when(v) {
    if (!v) return '—';
    var d = new Date(v);
    if (isNaN(d.getTime())) return String(v);
    return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  }
  function note(msg, kind) {
    return '<span class="' + (kind || 'muted') + '">' + esc(msg) + '</span>';
  }

  /* --------------------------- credentials --------------------------- */
  function readCreds() {
    var keyId = ($('apiKeyId') || {}).value || '';
    var pem = ($('apiPrivateKey') || {}).value || '';
    creds.keyId = keyId.trim();
    creds.pem = pem.trim();
    var state = $('credState');
    if (state) {
      state.innerHTML = creds.keyId
        ? 'Key ID <code>' + esc(creds.keyId) + '</code> loaded in memory for this page only. It is never stored.'
        : 'No credentials loaded.';
    }
    return creds.keyId && creds.pem;
  }

  function clearCreds() {
    creds = { keyId: '', pem: '' };
    var k = $('apiKeyId'), p = $('apiPrivateKey');
    if (k) k.value = '';
    if (p) p.value = '';
    var state = $('credState');
    if (state) state.textContent = 'No credentials loaded.';
    var box = $('portfolioBox');
    if (box) box.innerHTML = 'Not connected. Credentials were cleared from memory.';
  }

  /* ---------------------------- portfolio ---------------------------- */
  function signed(path, method, body) {
    return App.signedFetch(path, method, body, creds);
  }

  function loadPortfolio() {
    var box = $('portfolioBox');
    if (!box) return Promise.resolve();
    if (!readCreds()) {
      box.innerHTML = note('Enter a demo API Key ID and private key first. Nothing is stored.', 'bad');
      return Promise.resolve();
    }
    box.innerHTML = note('Signing requests to the Kalshi demo API…');
    var balance = null, positions = null, fills = null, orders = null, settlements = null;
    var errors = [];

    function attempt(label, p) {
      return p.then(function (r) { return r; }).catch(function (err) {
        errors.push(label + ': ' + err.message);
        return null;
      });
    }

    return Promise.all([
      attempt('balance', signed('/portfolio/balance', 'GET')),
      attempt('positions', signed('/portfolio/positions?limit=200', 'GET')),
      attempt('fills', signed('/portfolio/fills?limit=200', 'GET')),
      attempt('orders', signed('/portfolio/events/orders?limit=200', 'GET')
        .catch(function () { return signed('/portfolio/orders?limit=200', 'GET'); })),
      attempt('settlements', signed('/portfolio/settlements?limit=200', 'GET')),
    ]).then(function (parts) {
      balance = parts[0]; positions = parts[1]; fills = parts[2]; orders = parts[3]; settlements = parts[4];

      var cash = balance && balance.balance !== undefined ? Number(balance.balance) / 100 : null;
      var payout = balance && balance.payout !== undefined ? Number(balance.payout) / 100 : null;
      var posRows = (positions && positions.market_positions) || [];
      var fillRows = (fills && fills.fills) || [];
      var orderRows = (orders && orders.orders) || [];
      var settleRows = (settlements && settlements.settlements) || [];

      box.innerHTML =
        '<div class="grid grid-4" style="margin-bottom:12px">' +
        kpi('Cash balance', cash === null ? '—' : money(cash), 'GET /portfolio/balance') +
        kpi('Positions', posRows.length, 'GET /portfolio/positions') +
        kpi('Fills', fillRows.length, 'GET /portfolio/fills') +
        kpi('Settlements', settleRows.length, 'GET /portfolio/settlements') +
        '</div>' +
        (errors.length ? '<div class="notice warn"><h3>Partial result</h3><ul class="tight">' +
          errors.map(function (e) { return '<li>' + esc(e) + '</li>'; }).join('') + '</ul></div>' : '') +
        positionsTable(posRows) + fillsTable(fillRows) + ordersTable(orderRows) + settlementsTable(settleRows);

      renderTradeLog(fillRows, posRows, settleRows);
      global.KalshiPortfolio = { balance: balance, positions: posRows, fills: fillRows, orders: orderRows, settlements: settleRows };
    }).catch(function (err) {
      box.innerHTML = note('Could not load the demo account: ' + err.message, 'bad');
    });
  }

  function kpi(k, v, s) {
    return '<div class="kpi"><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div><div class="s">' + esc(s) + '</div></div>';
  }

  function wrap(title, head, body, empty) {
    if (!body || !body.length) return '<h3>' + esc(title) + '</h3><p class="muted">' + esc(empty) + '</p>';
    return '<h3>' + esc(title) + '</h3><div class="table-wrap"><table><thead><tr>' +
      head.map(function (h) { return '<th>' + esc(h) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      body.join('') + '</tbody></table></div>';
  }

  function positionsTable(rows) {
    var body = rows.map(function (p) {
      return '<tr>' +
        '<td class="ticker nowrap">' + esc(p.ticker || '') + '</td>' +
        '<td class="num">' + count(p.position) + '</td>' +
        '<td class="num">' + (p.market_exposure !== undefined ? money(Number(p.market_exposure) / 100) : '—') + '</td>' +
        '<td class="num">' + (p.unrealized_pnl_cents !== undefined ? money(Number(p.unrealized_pnl_cents) / 100) : '—') + '</td>' +
        '<td class="num">' + (p.realized_pnl_cents !== undefined ? money(Number(p.realized_pnl_cents) / 100) : '—') + '</td>' +
        '<td class="num">' + count(p.total_traded) + '</td>' +
        '</tr>';
    });
    return wrap('Positions', ['Ticker', 'Contracts', 'Exposure', 'Unrealised P&L', 'Realised P&L', 'Traded'], body, 'No open positions in the demo account.');
  }

  function fillsTable(rows) {
    var body = rows.map(function (f) {
      var side = f.outcome_side || f.side || f.taker_outcome_side || '—';
      var price = f.yes_price_dollars !== undefined ? f.yes_price_dollars : f.price_dollars;
      return '<tr>' +
        '<td class="ticker nowrap">' + esc(f.ticker || '') + '</td>' +
        '<td>' + esc(side) + '</td>' +
        '<td class="num">' + (price !== undefined ? money(price, 4) : '—') + '</td>' +
        '<td class="num">' + count(f.count_fp !== undefined ? f.count_fp : f.count) + '</td>' +
        '<td class="num">' + (f.is_taker !== undefined ? (f.is_taker ? 'taker' : 'maker') : '—') + '</td>' +
        '<td class="nowrap">' + esc(when(f.created_time)) + '</td>' +
        '</tr>';
    });
    return wrap('Fills', ['Ticker', 'Outcome side', 'Price', 'Contracts', 'Role', 'Created'], body, 'No fills in the demo account yet.');
  }

  function ordersTable(rows) {
    var body = rows.map(function (o) {
      var price = o.price_dollars !== undefined ? o.price_dollars : o.yes_price_dollars;
      return '<tr>' +
        '<td class="mono nowrap">' + esc(o.order_id || '') + '</td>' +
        '<td class="ticker nowrap">' + esc(o.ticker || '') + '</td>' +
        '<td>' + esc(o.outcome_side || o.side || '—') + '</td>' +
        '<td class="num">' + (price !== undefined ? money(price, 4) : '—') + '</td>' +
        '<td class="num">' + count(o.remaining_count !== undefined ? o.remaining_count : o.count) + '</td>' +
        '<td>' + esc(o.status || '—') + '</td>' +
        '</tr>';
    });
    return wrap('Open orders', ['Order ID', 'Ticker', 'Side', 'Price', 'Remaining', 'Status'], body, 'No orders in the demo account.');
  }

  function settlementsTable(rows) {
    var body = rows.map(function (s) {
      return '<tr>' +
        '<td class="ticker nowrap">' + esc(s.ticker || '') + '</td>' +
        '<td>' + (s.market_result ? '<span class="badge ' + esc(s.market_result) + '">' + esc(String(s.market_result).toUpperCase()) + '</span>' : '—') + '</td>' +
        '<td class="num">' + count(s.yes_count_fp) + '</td>' +
        '<td class="num">' + count(s.no_count_fp) + '</td>' +
        '<td class="num">' + (s.revenue !== undefined ? money(Number(s.revenue) / 100) : '—') + '</td>' +
        '<td class="num">' + (s.fee_cost !== undefined ? money(s.fee_cost, 4) : '—') + '</td>' +
        '<td class="nowrap">' + esc(when(s.settled_time)) + '</td>' +
        '</tr>';
    });
    return wrap('Settlements', ['Ticker', 'Result', 'YES contracts', 'NO contracts', 'Revenue', 'Fees', 'Settled'], body, 'No settlements in the demo account.');
  }

  /* ---------------------------- trade log ---------------------------- */
  function renderTradeLog(fills, positions, settlements) {
    var box = $('tradeLog');
    if (!box) return;
    if (!fills || !fills.length) {
      box.innerHTML = '<p class="muted">No fills loaded. Fill-level categorisation (topic, side, strategy tag, outcome) appears here once fills exist.</p>';
      return;
    }
    var byTopic = {};
    var bySide = {};
    fills.forEach(function (f) {
      var side = f.outcome_side || f.side || 'unknown';
      bySide[side] = (bySide[side] || 0) + 1;
    });
    var rows = fills.map(function (f) {
      var price = f.yes_price_dollars !== undefined ? f.yes_price_dollars : f.price_dollars;
      return '<tr>' +
        '<td class="ticker nowrap">' + esc(f.ticker || '') + '</td>' +
        '<td>' + esc(f.outcome_side || f.side || '—') + '</td>' +
        '<td class="num">' + (price !== undefined ? money(price, 4) : '—') + '</td>' +
        '<td class="num">' + count(f.count_fp !== undefined ? f.count_fp : f.count) + '</td>' +
        '<td>' + esc(when(f.created_time)) + '</td>' +
        '</tr>';
    });
    box.innerHTML =
      '<p class="muted">Side split: ' + Object.keys(bySide).map(function (k) { return esc(k) + ' ' + bySide[k]; }).join(' · ') +
      '. Win rate and net P&amp;L are computed on the Analysis page once a fill is joined to a settled market.</p>' +
      '<div class="table-wrap"><table><thead><tr><th>Ticker</th><th>Outcome side</th><th class="num">Price</th>' +
      '<th class="num">Contracts</th><th>Created</th></tr></thead><tbody>' + rows.join('') + '</tbody></table></div>';
  }

  /* ------------------------------ orders ----------------------------- */
  function clientOrderId() {
    if (global.crypto && global.crypto.randomUUID) return global.crypto.randomUUID();
    return 'kalshi-demo-' + Date.now() + '-' + Math.floor(Math.random() * 1e9);
  }

  function placeOrder() {
    var out = $('orderResult');
    if (!out) return;
    if (!readCreds()) { out.innerHTML = note('Enter a demo API Key ID and private key first.', 'bad'); return; }
    var ticker = (($('orderTicker') || {}).value || '').trim();
    var side = (($('orderSide') || {}).value) || 'yes';
    var countRaw = (($('orderCount') || {}).value) || '1';
    var price = (($('orderPrice') || {}).value) || '';
    var type = (($('orderType') || {}).value) || 'limit';
    if (!ticker) { out.innerHTML = note('Enter a market ticker.', 'bad'); return; }
    if (!(Number(price) > 0)) { out.innerHTML = note('Enter a price between 0 and 1.', 'bad'); return; }

    // Create Order (V2): POST /portfolio/events/orders
    // https://docs.kalshi.com/api-reference/orders/create-order-v2
    //   side = "bid" buys YES, side = "ask" sells YES (so buying NO = "ask").
    //   count and price are fixed-point strings; time_in_force and
    //   self_trade_prevention_type are required.
    var body = {
      ticker: ticker,
      client_order_id: clientOrderId(),
      side: side === 'no' ? 'ask' : 'bid',
      count: (Math.round(Number(countRaw) * 100) / 100).toFixed(2),
      price: Number(price).toFixed(4),
      time_in_force: type === 'ioc' ? 'immediate_or_cancel' : 'good_till_canceled',
      self_trade_prevention_type: 'taker_at_cross',
      post_only: false,
      cancel_order_on_pause: true,
    };

    out.innerHTML = note('Submitting demo order…');
    signed('/portfolio/events/orders', 'POST', body).then(function (order) {
      out.innerHTML = note('Order accepted (HTTP 201). Order ID ' + esc(order.order_id || '') +
        ', remaining ' + esc(order.remaining_count !== undefined ? order.remaining_count : '—') +
        '. A 201 means accepted, not necessarily resting — check the order list below.', 'ok');
      loadPortfolio();
    }).catch(function (err) {
      out.innerHTML = note('Order rejected: ' + err.message, 'bad');
    });
  }

  function cancelOrders() {
    var out = $('orderResult');
    if (!out) return;
    if (!readCreds()) { out.innerHTML = note('Enter a demo API Key ID and private key first.', 'bad'); return; }
    out.innerHTML = note('Cancelling open demo orders…');
    signed('/portfolio/events/orders?status=resting', 'DELETE').then(function (r) {
      out.innerHTML = note('Cancel-all request accepted. ' +
        (r && r.canceled_orders !== undefined ? 'Canceled: ' + r.canceled_orders : ''), 'ok');
      loadPortfolio();
    }).catch(function (err) {
      out.innerHTML = note('Cancel failed: ' + err.message, 'bad');
    });
  }

  /* -------------------------- ticker suggestions --------------------- */
  function fillTickerList() {
    var list = $('tickerList');
    if (!list) return;
    fetch('data/open-markets.json').then(function (r) { return r.json(); }).then(function (json) {
      var topics = (json && json.topics) || {};
      var seen = {};
      var out = [];
      Object.keys(topics).forEach(function (k) {
        (topics[k] || []).slice(0, 8).forEach(function (m) {
          if (m && m.ticker && !seen[m.ticker]) {
            seen[m.ticker] = true;
            out.push('<option value="' + esc(m.ticker) + '">' + esc((m.title || '') + ' — ' + m.topic) + '</option>');
          }
        });
      });
      list.innerHTML = out.join('');
    }).catch(function () { /* the datalist is optional */ });
  }

  function init() {
    var load = $('loadPortBtn');
    if (load) load.addEventListener('click', loadPortfolio);
    var clear = $('clearCredsBtn');
    if (clear) clear.addEventListener('click', clearCreds);
    var place = $('placeOrderBtn');
    if (place) place.addEventListener('click', placeOrder);
    var cancel = $('cancelOrderBtn');
    if (cancel) cancel.addEventListener('click', cancelOrders);
    fillTickerList();
  }

  global.KalshiPortfolioApp = {
    loadPortfolio: loadPortfolio,
    placeOrder: placeOrder,
    clearCreds: clearCreds,
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
}(window));
