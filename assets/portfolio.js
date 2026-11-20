/* Portfolio, order entry and trade analysis — runs entirely in the visitor's browser.
   Credentials are never sent anywhere except the Kalshi demo API, and are held in
   sessionStorage only (cleared when the tab closes). */
(function () {
  "use strict";
  var K = window.K, KALSHI = K.KALSHI;
  var $ = function (id) { return document.getElementById(id); };

  var CRED_KEY = "kalshi.creds.v1";
  var state = { balance: null, positions: [], fills: [], orders: [], signed: false, lastError: null };

  /* --------------------------- credentials --------------------------- */
  function saveCreds(c) {
    try { sessionStorage.setItem(CRED_KEY, JSON.stringify(c)); } catch (e) {}
  }
  function loadCreds() {
    try { return JSON.parse(sessionStorage.getItem(CRED_KEY) || "null"); } catch (e) { return null; }
  }
  function clearCreds() {
    try { sessionStorage.removeItem(CRED_KEY); } catch (e) {}
  }

  function b64ToBytes(b64) {
    var bin = atob(String(b64).replace(/\s/g, ""));
    var a = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i);
    return a;
  }
  function bytesToB64(buf) {
    var bytes = new Uint8Array(buf), s = "";
    for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return btoa(s);
  }
  function pemToDer(pem) {
    var body = String(pem).replace(/-----BEGIN [^-]+-----/g, "").replace(/-----END [^-]+-----/g, "").replace(/\s/g, "");
    return b64ToBytes(body);
  }

  var cachedKey = null;
  async function importKey(pem) {
    if (cachedKey) return cachedKey;
    var der = pemToDer(pem);
    try {
      cachedKey = { alg: "Ed25519", key: await crypto.subtle.importKey("pkcs8", der, { name: "Ed25519" }, false, ["sign"]) };
    } catch (e) {
      cachedKey = { alg: "RSA-PSS", key: await crypto.subtle.importKey("pkcs8", der, { name: "RSA-PSS", hash: "SHA-256" }, false, ["sign"]) };
    }
    return cachedKey;
  }

  async function signMessage(timestamp, method, path) {
    var creds = loadCreds();
    if (!creds || !creds.keyId || !creds.pem) throw new Error("Add your demo API Key ID and private key first.");
    var k = await importKey(creds.pem);
    var msg = new TextEncoder().encode(timestamp + method + path);
    var sig = k.alg === "Ed25519"
      ? await crypto.subtle.sign("Ed25519", k.key, msg)
      : await crypto.subtle.sign({ name: "RSA-PSS", saltLength: 32 }, k.key, msg);
    return bytesToB64(sig);
  }

  /** Signed request. `path` must start with /trade-api/v2/... (query string excluded from the signature). */
  async function signedFetch(path, method, body, base) {
    var creds = loadCreds();
    var root = (base || (creds && creds.base) || KALSHI.rest).replace(/\/+$/, "");
    var ts = String(Date.now());
    var signPath = path.split("?")[0];
    var signature = await signMessage(ts, method, signPath);
    var res = await fetch(root + path, {
      method: method,
      headers: {
        "KALSHI-ACCESS-KEY": creds.keyId,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "Content-Type": "application/json"
      },
      body: body ? JSON.stringify(body) : undefined
    });
    var text = await res.text();
    var json = {};
    try { json = text ? JSON.parse(text) : {}; } catch (e) { json = { raw: text }; }
    if (!res.ok) {
      var err = new Error("HTTP " + res.status + ": " + (json.message || json.error || json.code || text).toString().slice(0, 300));
      err.body = json;
      throw err;
    }
    return json;
  }

  /* --------------------------- portfolio --------------------------- */
  async function loadPortfolio() {
    var out = $("portfolioOut");
    if (!out) return;
    out.innerHTML = '<span class="muted">Loading portfolio…</span>';
    try {
      var balance = await signedFetch("/portfolio/balance", "GET");
      var positions = await signedFetch("/portfolio/positions?limit=200", "GET");
      var fills = await signedFetch("/portfolio/fills?limit=200", "GET");
      var orders = await signedFetch("/portfolio/orders?limit=200", "GET");
      state.balance = balance;
      state.positions = positions.market_positions || [];
      state.fills = fills.fills || [];
      state.orders = orders.orders || [];
      state.signed = true;
      state.lastError = null;
      renderPortfolio();
      K.addTradeLog({ kind: "snapshot", ts: new Date().toISOString(), fills: state.fills.length });
      K.addTradeLog({ kind: "fills", ts: new Date().toISOString(), fills: state.fills.slice(0, 200) });
    } catch (e) {
      state.lastError = e.message;
      out.innerHTML = '<div class="callout bad"><b>Portfolio request failed.</b> ' + K.esc(e.message) +
        '<br><span class="small">Common causes: the API key is for the wrong environment (demo keys only work on demo hosts), ' +
        "the clock is more than 30 s off, or the key lacks the needed scope. " +
        'See <a href="' + KALSHI.docs.auth + '" target="_blank" rel="noopener">Authenticated Requests</a>.</span></div>';
    }
  }

  function renderPortfolio() {
    var out = $("portfolioOut");
    var b = state.balance || {};
    var balDollars = b.balance_dollars !== undefined && b.balance_dollars !== null ? b.balance_dollars
      : (b.balance !== undefined && b.balance !== null ? Number(b.balance) / 100 : null);
    var pv = b.portfolio_value !== undefined && b.portfolio_value !== null ? Number(b.portfolio_value) / 100 : null;
    out.innerHTML =
      '<div class="grid">' +
      '<div class="card"><div class="kpi-label">Available balance</div><div class="kpi">' + K.money(balDollars) + "</div>" +
      '<div class="muted small">fields: <code>balance</code> (cents), <code>balance_dollars</code>, <code>portfolio_value</code> (cents), <code>updated_ts</code></div></div>' +
      '<div class="card"><div class="kpi-label">Portfolio value</div><div class="kpi">' + K.money(pv) + "</div>" +
      '<div class="muted small">Source: <a href="' + KALSHI.docs.balance + '" target="_blank" rel="noopener">Get Balance</a></div></div>' +
      '<div class="card"><div class="kpi-label">Positions / Fills / Orders</div><div class="kpi">' +
      state.positions.length + " / " + state.fills.length + " / " + state.orders.length + "</div>" +
      '<div class="muted small">Sources: <a href="' + KALSHI.docs.positions + '" target="_blank" rel="noopener">Get Positions</a>, ' +
      '<a href="' + KALSHI.docs.fills + '" target="_blank" rel="noopener">Get Fills</a>, ' +
      '<a href="' + KALSHI.docs.orders + '" target="_blank" rel="noopener">Get Orders</a></div></div>' +
      "</div>" +
      '<h3>Positions</h3><div class="tbl-wrap"><table><thead><tr><th>Ticker</th><th>Contracts</th><th>Market exposure</th>' +
      "<th>Realized P&amp;L</th><th>Last price</th><th>Source</th></tr></thead><tbody>" +
      (state.positions.length ? state.positions.map(function (p) {
        return "<tr><td>" + K.marketLink(p.ticker) + "</td>" +
          "<td>" + (p.position !== undefined ? K.fmtNum(p.position, 2) : "—") + "</td>" +
          "<td>" + (p.market_exposure !== undefined ? K.money(p.market_exposure, 4) : "—") + "</td>" +
          "<td>" + (p.realized_pnl !== undefined ? K.money(p.realized_pnl, 4) : "—") + "</td>" +
          "<td>" + (p.last_price !== undefined ? K.money(p.last_price, 4) : "—") + "</td>" +
          "<td>" + K.apiLink(KALSHI.rest + "/portfolio/positions?limit=200", "api") + "</td></tr>";
      }).join("") : '<tr><td colspan="6" class="muted">No open positions reported.</td></tr>') +
      "</tbody></table></div>" +
      '<h3>Fills</h3><div class="tbl-wrap"><table><thead><tr><th>Time (UTC)</th><th>Ticker</th><th>Outcome</th><th>Book side</th>' +
      "<th class='num'>Contracts</th><th class='num'>YES price</th><th class='num'>Fee</th><th>Source</th></tr></thead><tbody>" +
      (state.fills.length ? state.fills.map(function (f) {
        return "<tr><td>" + K.esc(f.created_time || "—") + "</td><td>" + K.marketLink(f.ticker || f.market_ticker) + "</td>" +
          "<td>" + K.esc(f.outcome_side || f.side || "—") + "</td><td>" + K.esc(f.book_side || "—") + "</td>" +
          "<td class='num'>" + K.fmtNum(f.count_fp, 2) + "</td>" +
          "<td class='num'>" + K.money(f.yes_price_dollars, 4) + "</td>" +
          "<td class='num'>" + K.money(f.fee_cost, 4) + "</td>" +
          "<td>" + K.apiLink(KALSHI.rest + "/portfolio/fills?limit=200", "api") + "</td></tr>";
      }).join("") : '<tr><td colspan="8" class="muted">No fills yet — place a demo order to create some.</td></tr>') +
      "</tbody></table></div>" +
      '<h3>Orders</h3><div class="tbl-wrap"><table><thead><tr><th>Order ID</th><th>Ticker</th><th>Side</th><th>Status</th>' +
      "<th class='num'>Price</th><th class='num'>Filled</th><th class='num'>Remaining</th><th></th></tr></thead><tbody>" +
      (state.orders.length ? state.orders.map(function (o) {
        return "<tr><td><code>" + K.esc(o.order_id) + "</code></td><td>" + K.marketLink(o.ticker) + "</td>" +
          "<td>" + K.esc(o.book_side || o.side || "—") + " / " + K.esc(o.outcome_side || "—") + "</td>" +
          "<td>" + K.esc(o.status || "—") + "</td>" +
          "<td class='num'>" + K.money(o.yes_price_dollars, 4) + "</td>" +
          "<td class='num'>" + K.fmtNum(o.fill_count_fp, 2) + "</td>" +
          "<td class='num'>" + K.fmtNum(o.remaining_count_fp, 2) + "</td>" +
          '<td><button class="danger" data-cancel="' + K.esc(o.order_id) + '" data-ticker="' + K.esc(o.ticker) + '">Cancel</button></td></tr>';
      }).join("") : '<tr><td colspan="8" class="muted">No orders reported.</td></tr>') +
      "</tbody></table></div>";

    out.querySelectorAll("[data-cancel]").forEach(function (b) {
      b.onclick = async function () {
        b.disabled = true;
        try {
          await signedFetch("/portfolio/events/orders/" + encodeURIComponent(b.dataset.cancel) +
            "?market_ticker=" + encodeURIComponent(b.dataset.ticker) + "&exchange_index=-1", "DELETE");
          b.closest("tr").innerHTML = "<td colspan='8' class='ok'>Cancelled.</td>";
          loadPortfolio();
        } catch (e) {
          b.disabled = false;
          b.closest("tr").insertAdjacentHTML("afterend", '<tr><td colspan="8" class="bad">' + K.esc(e.message) + "</td></tr>");
        }
      };
    });
  }

  /* --------------------------- order entry --------------------------- */
  function marketPriceInfo() {
    var ticker = ($("orderTicker") || {}).value || "";
    ticker = ticker.trim();
    if (!ticker) return Promise.resolve(null);
    return fetch(KALSHI.rest + "/markets/" + encodeURIComponent(ticker)).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (j) { return j.market || null; });
  }

  function snapToGrid(price, ranges) {
    if (!ranges || !ranges.length) return price;
    for (var i = 0; i < ranges.length; i++) {
      var r = ranges[i];
      var start = Number(r.start), end = Number(r.end), step = Number(r.step);
      if (price >= start && price <= end) {
        var snapped = start + Math.round((price - start) / step) * step;
        snapped = Math.min(end, Math.max(start, snapped));
        return Math.round(snapped * 10000) / 10000;
      }
    }
    return price;
  }

  async function placeOrder() {
    var out = $("orderOut");
    var ticker = ($("orderTicker").value || "").trim();
    var mode = $("orderSide").value;          // buy_yes | sell_yes | buy_no | sell_no
    var count = String($("orderCount").value || "").trim();
    var priceRaw = $("orderPrice").value;
    var tif = $("orderTif").value;
    var stp = $("orderStp").value;
    var postOnly = $("orderPostOnly").checked;

    if (!ticker || !count || !priceRaw) {
      out.innerHTML = '<span class="bad">Ticker, count and price are required.</span>';
      return;
    }
    var yesPrice = Number(priceRaw);
    if (!isFinite(yesPrice) || yesPrice <= 0 || yesPrice >= 1) {
      out.innerHTML = '<span class="bad">Price must be between 0 and 1 (dollars).</span>';
      return;
    }

    var market = null;
    try { market = await marketPriceInfo(); } catch (e) { market = null; }
    var snapped = market ? snapToGrid(yesPrice, market.price_ranges) : yesPrice;
    if (market && Math.abs(snapped - yesPrice) > 1e-9) {
      out.innerHTML = '<span class="warn">Price snapped to the market price grid: ' + K.money(snapped, 4) + "</span>";
    }

    // V2 single-book model (official Create Order (V2) reference):
    //   side "bid" = buy YES at the quoted YES price
    //   side "ask" = sell YES at the quoted YES price  ( == buy NO at (1 - price) )
    // Buy NO at q  -> sell YES at (1 - q)  -> side "ask", price (1 - q)
    // Sell NO at q -> buy  YES at (1 - q)  -> side "bid", price (1 - q)
    var body = {
      ticker: ticker,
      client_order_id: (crypto.randomUUID ? crypto.randomUUID() : String(Date.now())),
      side: (mode === "buy_yes" || mode === "sell_no") ? "bid" : "ask",
      count: count,
      price: (mode === "buy_no" || mode === "sell_no") ? (1 - snapped).toFixed(4) : snapped.toFixed(4),
      time_in_force: tif,
      self_trade_prevention_type: stp,
      post_only: postOnly
    };

    try {
      var res = await signedFetch("/portfolio/events/orders", "POST", body);
      out.innerHTML = '<div class="callout info"><b>Order accepted (HTTP 201).</b> A 201 means accepted, not resting — check ' +
        "<code>remaining_count</code>.<pre style='white-space:pre-wrap;margin:6px 0 0'>" + K.esc(JSON.stringify(res, null, 2)) + "</pre>" +
        '<span class="small">Request body sent (signed path <code>/trade-api/v2/portfolio/events/orders</code>):</span>' +
        "<pre style='white-space:pre-wrap;margin:6px 0 0'>" + K.esc(JSON.stringify(body, null, 2)) + "</pre></div>";
      K.addTradeLog({
        kind: "order", ts: new Date().toISOString(), ticker: ticker, mode: mode,
        count: Number(count), price_yes: snapped, body: body, response: res
      });
      loadPortfolio();
    } catch (e) {
      out.innerHTML = '<div class="callout bad"><b>Order failed.</b> ' + K.esc(e.message) +
        '<pre style="white-space:pre-wrap;margin:6px 0 0">' + K.esc(JSON.stringify(e.body || {}, null, 2)) + "</pre>" +
        '<span class="small">See <a href="' + KALSHI.docs.createOrder + '" target="_blank" rel="noopener">Create Order (V2)</a> ' +
        'and <a href="https://docs.kalshi.com/getting_started/order_errors" target="_blank" rel="noopener">Order Errors</a>.</span></div>';
    }
  }

  /* --------------------------- analysis engine --------------------------- */
  function priceBucket(p) {
    p = Number(p);
    if (!isFinite(p)) return "unknown";
    if (p < 0.10) return "0–10¢";
    if (p < 0.30) return "10–30¢";
    if (p < 0.50) return "30–50¢";
    if (p < 0.70) return "50–70¢";
    if (p < 0.90) return "70–90¢";
    return "90–100¢";
  }

  /**
   * Categorise fills and derive observed patterns.
   * @param {Array} fills  fills from GET /portfolio/fills
   * @param {Object} resolvedMap ticker -> resolved record (result yes/no)
   * @param {Object} topicMap ticker -> topic
   */
  function analyzeFills(fills, resolvedMap, topicMap) {
    resolvedMap = resolvedMap || {};
    topicMap = topicMap || {};
    var rows = (fills || []).map(function (f) {
      var t = f.ticker || f.market_ticker;
      var price = Number(f.yes_price_dollars);
      var contracts = Number(f.count_fp);
      var outcome = f.outcome_side || f.side || "";
      var res = resolvedMap[t] || null;
      var result = res ? String(res.result || "").toLowerCase() : "";
      var pnl = null, status = "unresolved";
      if (res && result) {
        status = "resolved";
        if (outcome === "yes") pnl = contracts * (result === "yes" ? 1 : 0) - contracts * price;
        else if (outcome === "no") pnl = contracts * (result === "no" ? 1 : 0) - contracts * (1 - price);
      }
      return {
        ticker: t, time: f.created_time || "", outcome: outcome, bookSide: f.book_side || "",
        isTaker: f.is_taker, contracts: contracts, price: price, fee: Number(f.fee_cost) || 0,
        topic: topicMap[t] || "unclassified", bucket: priceBucket(price),
        hour: (f.created_time || "").slice(11, 13), result: result, pnl: pnl, status: status
      };
    });

    function group(keyFn, label) {
      var g = {};
      rows.forEach(function (r) {
        var k = keyFn(r) || "unknown";
        if (!g[k]) g[k] = { key: k, label: label, count: 0, resolved: 0, pnl: 0, wins: 0 };
        g[k].count++;
        if (r.status === "resolved") {
          g[k].resolved++;
          g[k].pnl += r.pnl;
          if (r.pnl > 0) g[k].wins++;
        }
      });
      return Object.keys(g).map(function (k) {
        var o = g[k];
        o.winRate = o.resolved ? o.wins / o.resolved : null;
        o.avgPnl = o.resolved ? o.pnl / o.resolved : null;
        return o;
      }).sort(function (a, b) { return b.count - a.count; });
    }

    var resolvedRows = rows.filter(function (r) { return r.status === "resolved"; });
    var wins = resolvedRows.filter(function (r) { return r.pnl > 0; }).length;
    var totalPnl = resolvedRows.reduce(function (s, r) { return s + (r.pnl || 0); }, 0);
    var totalFees = rows.reduce(function (s, r) { return s + (r.fee || 0); }, 0);

    var strategies = [];
    var buckets = group(function (r) { return r.bucket; }, "price band");
    var topics = group(function (r) { return r.topic; }, "topic");
    var hours = group(function (r) { return r.hour; }, "hour of day (UTC)");
    var sides = group(function (r) { return r.outcome; }, "outcome side");
    var makers = group(function (r) { return r.isTaker === false ? "maker" : "taker"; }, "taker/maker");

    [].concat(
      buckets.map(function (b) { return { dim: "price band", key: b.key, g: b }; }),
      topics.map(function (b) { return { dim: "topic", key: b.key, g: b }; }),
      hours.map(function (b) { return { dim: "hour of day (UTC)", key: b.key, g: b }; }),
      sides.map(function (b) { return { dim: "outcome side", key: b.key, g: b }; }),
      makers.map(function (b) { return { dim: "taker/maker", key: b.key, g: b }; })
    ).forEach(function (d) {
      if (d.g.resolved < 3) return; // no pattern from fewer than three resolved fills
      strategies.push({
        dimension: d.dim, segment: d.key, fills: d.g.count, resolved: d.g.resolved,
        winRate: d.g.winRate, avgPnl: d.g.avgPnl, totalPnl: d.g.pnl,
        statement: "Across " + d.g.resolved + " resolved fills in " + d.dim + " = " + d.key +
          ", " + (d.g.wins) + " were profitable (" + (d.g.winRate * 100).toFixed(0) + "%) and average P&L per resolved fill was " +
          K.money(d.g.avgPnl, 4) + "."
      });
    });

    return {
      rows: rows, resolved: resolvedRows, wins: wins, totalPnl: totalPnl, totalFees: totalFees,
      byBucket: buckets, byTopic: topics, byHour: hours, bySide: sides, byMaker: makers,
      strategies: strategies,
      summary: {
        fills: rows.length, resolved: resolvedRows.length, winRate: resolvedRows.length ? wins / resolvedRows.length : null,
        totalPnl: totalPnl, totalFees: totalFees
      }
    };
  }

  K.analysis = { analyzeFills: analyzeFills, priceBucket: priceBucket };
  K.trading = {
    signedFetch: signedFetch, loadPortfolio: loadPortfolio, placeOrder: placeOrder,
    saveCreds: saveCreds, loadCreds: loadCreds, clearCreds: clearCreds, state: state
  };

  /* --------------------------- page wiring --------------------------- */
  function initPortfolioPage() {
    var keyId = $("apiKeyId"), pem = $("apiPrivateKey"), base = $("apiBase");
    if (!keyId) return;
    var creds = loadCreds();
    if (creds) {
      keyId.value = creds.keyId || "";
      pem.value = creds.pem || "";
      if (base) base.value = creds.base || KALSHI.rest;
      $("credsStatus").innerHTML = '<span class="ok">Credentials loaded from this browser session (sessionStorage).</span>';
    }
    var save = $("saveCredsBtn");
    if (save) save.onclick = function () {
      saveCreds({ keyId: keyId.value.trim(), pem: pem.value, base: base ? base.value : KALSHI.rest });
      $("credsStatus").innerHTML = '<span class="ok">Saved to sessionStorage (cleared when this tab closes).</span>';
    };
    var clr = $("clearCredsBtn");
    if (clr) clr.onclick = function () {
      clearCreds(); keyId.value = ""; pem.value = "";
      $("credsStatus").innerHTML = '<span class="muted">Credentials cleared.</span>';
    };
    var lp = $("loadPortBtn");
    if (lp) lp.onclick = loadPortfolio;
    var po = $("placeOrderBtn");
    if (po) po.onclick = placeOrder;
    var pre = $("prefillBtn");
    if (pre) pre.onclick = function () {
      marketPriceInfo().then(function (m) {
        if (!m) { $("orderOut").innerHTML = '<span class="bad">Market not found.</span>'; return; }
        $("orderPrice").value = m.yes_bid_dollars || "";
        $("orderOut").innerHTML = "Pre-filled with the current YES bid (" + K.money(m.yes_bid_dollars, 4) +
          ") and the market price grid " + K.esc(JSON.stringify(m.price_ranges || [])) + ".";
      }).catch(function (e) { $("orderOut").innerHTML = '<span class="bad">' + K.esc(e.message) + "</span>"; });
    };
    var sideSel = $("orderSide");
    if (sideSel) sideSel.onchange = function () {
      var hint = $("sideHint");
      if (!hint) return;
      var map = {
        buy_yes: "Buys YES at the price you enter (side = bid).",
        sell_yes: "Sells YES at the price you enter (side = ask). Equivalent to buying NO at 1 − price.",
        buy_no: "Buys NO. You enter the NO price; the order is sent as side = ask at price 1 − your price.",
        sell_no: "Sells NO. You enter the NO price; the order is sent as side = bid at price 1 − your price."
      };
      hint.textContent = map[sideSel.value] || "";
    };
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initPortfolioPage);
  else initPortfolioPage();
})();
