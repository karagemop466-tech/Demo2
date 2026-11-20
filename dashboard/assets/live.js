/* Live dashboard — public Kalshi market-data REST endpoints only.
   Verified endpoints (docs.kalshi.com):
   - GET /markets?series_ticker=&limit=            (Get Markets)
   - GET /markets/{ticker}                          (Get Market)
   - GET /markets/{ticker}/orderbook?depth=N        (Orderbook Responses: orderbook_fp.yes_dollars / no_dollars = [price, count])
   - GET /series/{series}/markets/{ticker}/candlesticks?start_ts&end_ts&period_interval  (1, 60, 1440 minutes)
   No API key is used or stored. Nothing is inferred: missing values are shown as UNVERIFIED. */
(function () {
  var BASE = {
    demo: "https://external-api.demo.kalshi.co/trade-api/v2",
    prod: "https://external-api.kalshi.com/trade-api/v2"
  };
  var SERIES = ["KXBTCMINY", "KXAAAGASM"];
  var WATCH_FALLBACK = {
    KXBTCMINY: ["KXBTCMINY-27JAN01-55000.00", "KXBTCMINY-27JAN01-50000.00", "KXBTCMINY-27JAN01-45000.00"],
    KXAAAGASM: ["KXAAAGASM-26NOV30-5.00", "KXAAAGASM-26NOV30-4.90", "KXAAAGASM-26NOV30-4.80", "KXAAAGASM-26NOV30-4.70"]
  };

  var $ = function (id) { return document.getElementById(id); };
  var state = { series: "KXBTCMINY", ticker: null, markets: [], tape: [], timer: null, interval: 10, backoff: 1, lastErr: "" };

  function env() { return BASE[$("env").value]; }

  function getJSON(url) {
    return fetch(url, { headers: { Accept: "application/json" } }).then(function (r) {
      if (r.status === 429) { var e = new Error("429 rate limited"); e.code = 429; throw e; }
      if (!r.ok) throw new Error("HTTP " + r.status + " from " + url.replace(BASE.demo, "demo").replace(BASE.prod, "prod"));
      return r.json();
    }).catch(function (e) {
      if (e instanceof TypeError) throw new Error("Browser could not reach the Kalshi API (network or CORS). Flagged as UNVERIFIED in flagged.html.");
      throw e;
    });
  }

  function setStatus(msg, bad) {
    var el = $("status");
    el.textContent = msg;
    el.style.color = bad ? "#b42318" : "";
  }

  function fmtP(v) { var n = Number(v); return isNaN(n) ? "" : "$" + n.toFixed(2); }
  function fmtN(v) { var n = Number(v); return isNaN(n) ? "" : n.toLocaleString("en-US", { maximumFractionDigits: 2 }); }
  function cell(v, f) { return v === "" || v == null || f(v) === "" ? '<span class="unv">UNVERIFIED</span>' : f(v); }

  /* ---------- markets ---------- */
  function loadMarkets() {
    var s = state.series;
    return getJSON(env() + "/markets?series_ticker=" + encodeURIComponent(s) + "&limit=100").then(function (d) {
      var all = d.markets || [];
      // Status values in responses are "active"/"finalized" (see Flagged F4 re: docs enum mismatch). Keep active only.
      state.markets = all.filter(function (m) { return m.status === "active"; });
      state.markets.sort(function (a, b) { return (Number(b.volume_fp) || 0) - (Number(a.volume_fp) || 0); });
      var sel = $("market"); sel.innerHTML = "";
      state.markets.forEach(function (m) {
        var o = document.createElement("option"); o.value = m.ticker; o.textContent = m.ticker + " — " + (m.yes_sub_title || m.title || "");
        sel.appendChild(o);
      });
      if (!state.markets.length) {
        var o2 = document.createElement("option"); o2.textContent = "No active markets returned for " + s; sel.appendChild(o2);
        state.ticker = null;
        return;
      }
      if (!state.ticker || !state.markets.some(function (m) { return m.ticker === state.ticker; })) state.ticker = state.markets[0].ticker;
      sel.value = state.ticker;
      renderMarketTable();
    });
  }

  function renderMarketTable() {
    $("mkt-body").innerHTML = state.markets.map(function (m) {
      return "<tr><td><code>" + esc(m.ticker) + "</code></td><td>" + esc(m.title || "") + "</td><td>" + esc(m.status) +
        "</td><td class='num'>" + cell(m.last_price_dollars, fmtP) + "</td><td class='num'>" + cell(m.yes_bid_dollars, fmtP) +
        "</td><td class='num'>" + cell(m.yes_ask_dollars, fmtP) + "</td><td class='num'>" + cell(m.volume_fp, fmtN) +
        "</td><td class='num'>" + cell(m.open_interest_fp, fmtN) + "</td><td><a href='" + env() + "/markets/" + encodeURIComponent(m.ticker) +
        "' target='_blank' rel='noopener'>API ↗</a></td></tr>";
    }).join("");
  }

  /* ---------- market detail (quotes) ---------- */
  function loadQuote() {
    if (!state.ticker) return Promise.resolve();
    return getJSON(env() + "/markets/" + encodeURIComponent(state.ticker)).then(function (d) {
      var m = d.market || d;
      var last = Number(m.last_price_dollars), bid = Number(m.yes_bid_dollars), ask = Number(m.yes_ask_dollars);
      var t = Date.now() / 1000;
      state.tape.push({ t: t, last: last, bid: bid, ask: ask });
      if (state.tape.length > 5000) state.tape.shift();
      state.quote = m;
      renderKpis(m);
    });
  }

  function renderKpis(m) {
    var last = Number(m.last_price_dollars), bid = Number(m.yes_bid_dollars), ask = Number(m.yes_ask_dollars);
    var flag = (!isNaN(last) && !isNaN(bid) && !isNaN(ask) && (last < bid || last > ask))
      ? '<span class="badge b-warn">Last trade outside current quote — see Flagged F5</span>' : "";
    var spread = (!isNaN(bid) && !isNaN(ask)) ? "$" + (ask - bid).toFixed(2) : "";
    $("kpis").innerHTML =
      kpi("Last traded (YES)", cell(m.last_price_dollars, fmtP), "last_price_dollars") +
      kpi("YES bid", cell(m.yes_bid_dollars, fmtP), "best resting buy") +
      kpi("YES ask", cell(m.yes_ask_dollars, fmtP), "best resting sell") +
      kpi("Spread", spread || '<span class="unv">UNVERIFIED</span>', "ask − bid") +
      kpi("Contracts traded", cell(m.volume_fp, fmtN), "volume_fp (contracts)") +
      kpi("Open interest", cell(m.open_interest_fp, fmtN), "open_interest_fp") +
      kpi("Closes (UTC)", cell(m.close_time, function (v) { return esc(v); }), "close_time") +
      '<div class="card" style="grid-column:1/-1"><div class="k">Market</div><div class="s">' + esc(m.title || "") + " " + flag + "</div></div>";
  }
  function kpi(k, v, s) {
    return '<div class="card"><div class="k">' + esc(k) + '</div><div class="v">' + v + '</div><div class="s">' + esc(s) + "</div></div>";
  }

  /* ---------- orderbook (liquidity) ---------- */
  function loadBook() {
    if (!state.ticker) return Promise.resolve();
    return getJSON(env() + "/markets/" + encodeURIComponent(state.ticker) + "/orderbook?depth=10").then(function (d) {
      var ob = d.orderbook_fp || {};
      // Ladder arrays are ascending; show best price first.
      var yes = (ob.yes_dollars || []).slice().reverse();
      var no = (ob.no_dollars || []).slice().reverse();
      var cum = 0;
      $("yes-book").innerHTML = yes.length ? yes.map(function (r) {
        cum += Number(r[1]); return "<tr><td>" + fmtP(r[0]) + "</td><td class='num'>" + fmtN(r[1]) + "</td><td class='num'>" + fmtN(cum) + "</td></tr>";
      }).join("") : "<tr><td colspan='3' class='muted'>No resting YES bids.</td></tr>";
      cum = 0;
      $("no-book").innerHTML = no.length ? no.map(function (r) {
        cum += Number(r[1]); var askP = (1 - Number(r[0])).toFixed(2);
        return "<tr><td>$" + askP + "</td><td class='num'>" + fmtN(r[1]) + "</td><td class='num'>" + fmtN(cum) + "</td></tr>";
      }).join("") : "<tr><td colspan='3' class='muted'>No resting NO bids.</td></tr>";
    });
  }

  /* ---------- chart ---------- */
  function loadCandles() {
    if (!state.ticker) return Promise.resolve([]);
    var win = Number($("window").value);
    var period = win <= 259200 ? 1 : 60;
    var end = Math.floor(Date.now() / 1000), start = end - win;
    var url = env() + "/series/" + encodeURIComponent(state.series) + "/markets/" + encodeURIComponent(state.ticker) +
      "/candlesticks?start_ts=" + start + "&end_ts=" + end + "&period_interval=" + period;
    return getJSON(url).then(function (d) {
      return (d.candlesticks || []).map(function (c) {
        return { t: c.end_period_ts, p: c.price && c.price.close_dollars != null ? Number(c.price.close_dollars) : null,
                 bid: c.yes_bid && c.yes_bid.close_dollars != null ? Number(c.yes_bid.close_dollars) : null,
                 ask: c.yes_ask && c.yes_ask.close_dollars != null ? Number(c.yes_ask.close_dollars) : null,
                 vol: Number(c.volume_fp) };
      });
    });
  }

  function drawChart(points, note, withSec) {
    var svg = $("chart");
    var W = 1000, H = 340, L = 56, R = 16, T = 14, B = 34;
    var pts = points.filter(function (p) { return p.p != null && !isNaN(p.p); });
    if (!pts.length) {
      svg.innerHTML = '<text x="500" y="170" text-anchor="middle" style="font-size:16px;fill:#5b6575">No price points to plot yet.</text>';
      $("chart-note").textContent = note || "";
      return;
    }
    var x0 = pts[0].t, x1 = pts[pts.length - 1].t; if (x1 === x0) x1 = x0 + 1;
    var X = function (t) { return L + (t - x0) / (x1 - x0) * (W - L - R); };
    var Y = function (p) { return T + (1 - Math.min(1, Math.max(0, p))) * (H - T - B); };
    var g = "";
    for (var i = 0; i <= 5; i++) {
      var v = i / 5, y = Y(v);
      g += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y + '" y2="' + y + '" stroke="#e2e7ee"/>';
      g += '<text x="' + (L - 6) + '" y="' + (y + 4) + '" text-anchor="end">$' + v.toFixed(2) + "</text>";
    }
    for (var j = 0; j <= 4; j++) {
      var tt = x0 + (x1 - x0) * j / 4, xx = X(tt);
      g += '<text x="' + xx + '" y="' + (H - 12) + '" text-anchor="middle">' + fmtTime(tt, !!withSec) + "</text>";
    }
    var d = pts.map(function (p, k) { return (k ? "L" : "M") + X(p.t).toFixed(1) + "," + Y(p.p).toFixed(1); }).join(" ");
    var dots = pts.length < 200 ? pts.map(function (p) { return '<circle cx="' + X(p.t).toFixed(1) + '" cy="' + Y(p.p).toFixed(1) + '" r="2.2" fill="#00875a"/>'; }).join("") : "";
    svg.innerHTML = g + '<path d="' + d + '" fill="none" stroke="#00875a" stroke-width="2"/>' + dots +
      '<text x="' + (L + 4) + '" y="' + (T + 12) + '" style="fill:#33405a">YES last price (dollars) · X = time (UTC)</text>';
    var lastP = pts[pts.length - 1].p;
    $("chart-note").textContent = (note || "") + " Points: " + pts.length + ". Last plotted: $" + lastP.toFixed(2) + ".";
  }

  function fmtTime(sec, withSeconds) {
    var d = new Date(sec * 1000);
    var p = function (n) { return (n < 10 ? "0" : "") + n; };
    var s = p(d.getUTCHours()) + ":" + p(d.getUTCMinutes());
    return withSeconds ? s + ":" + p(d.getUTCSeconds()) : s;
  }

  function drawTape() {
    var pts = state.tape.map(function (r) { return { t: r.t, p: isNaN(r.last) ? null : r.last }; });
    drawChart(pts, "Live tape: one point per poll (" + state.interval + "s). X axis shows seconds (UTC).", true);
  }

  function refresh() {
    setStatus("Updating…");
    var mode = $("mode").value;
    $("win-wrap").style.display = mode === "history" ? "" : "none";
    return loadQuote().then(function () {
      return loadBook();
    }).then(function () {
      if (mode === "tape") { drawTape(); }
      else {
        return loadCandles().then(function (c) {
          drawChart(c.map(function (x) { return { t: x.t, p: x.p }; }),
            "History: " + ($("window").value <= 259200 ? "1-minute" : "1-hour") + " candles (YES last trade price per period; gaps = no trades).");
        });
      }
    }).then(function () {
      state.backoff = 1;
      setStatus("Updated " + new Date().toISOString().slice(11, 19) + " UTC · " + env().replace("https://", "").split("/")[0]);
    }).catch(function (e) {
      if (e.code === 429) { state.backoff = Math.min(state.backoff * 2, 8); setStatus("Rate limited (429) — backing off", true); }
      else setStatus(e.message, true);
    }).then(function () { schedule(); });
  }

  function schedule() {
    clearTimeout(state.timer);
    if (!$("auto").checked) return;
    state.interval = Number($("poll").value);
    state.timer = setTimeout(refresh, state.interval * 1000 * state.backoff);
  }

  function setSeries(s) {
    state.series = s; state.ticker = null; state.tape = []; state.quote = null;
    loadMarkets().then(refresh).catch(function (e) { setStatus(e.message, true); });
  }

  function boot() {
    var sel = $("series"); sel.innerHTML = SERIES.map(function (s) { return "<option>" + s + "</option>"; }).join("");
    sel.onchange = function () { setSeries(sel.value); };
    $("market").onchange = function () { state.ticker = $("market").value; state.tape = []; refresh(); };
    $("env").onchange = function () { state.tape = []; setSeries(state.series); };
    $("mode").onchange = refresh;
    $("window").onchange = refresh;
    $("poll").onchange = schedule;
    $("auto").onchange = schedule;
    $("refresh").onclick = refresh;
    $("use-custom").onclick = function () {
      var t = $("custom").value.trim();
      if (!t) return;
      state.ticker = t; state.tape = [];
      var s = t.split("-")[0];
      state.series = s; sel.value = SERIES.indexOf(s) >= 0 ? s : sel.value;
      refresh();
    };
    setSeries(state.series);
    $("mode").value = "history";
  }
  document.addEventListener("DOMContentLoaded", boot);
  // Expose for debugging in browser console only.
  window.__live = state;
})();
