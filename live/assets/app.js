/* ============================================================================
   Kalshi Demo Dashboard — client-side logic
   All endpoints, fields and signing rules are taken from docs.kalshi.com
   (see pages/sources.html and pages/verification.html for the exact pages).
   Nothing is hard-coded: every market value below is read live from the
   Kalshi DEMO API in the visitor's browser. If a request fails, the UI shows
   an error and leaves values blank rather than inventing data.
   ========================================================================== */
(function () {
  "use strict";

  var API = "https://external-api.demo.kalshi.co/trade-api/v2";
  var SIGN_PREFIX = "/trade-api/v2";
  var DEMO_SITE = "https://demo.kalshi.co/";

  /* ------------------------------------------------------------------ topic
     The API has no "gas prices / culture" filter. We therefore classify by
     keywords found in title / yes_sub_title / ticker / event_ticker.
     This is a documented heuristic (see Flagged for Review F-3).            */
  var TOPICS = {
    gas: ["gas", "gasoline", "diesel", "crude", "oil", "petrol", "opec", "refinery", "heating oil", "barrel"],
    elections: ["election", "elect", "president", "senate", "house", "congress", "governor", "mayor", "vote", "ballot", "primary", "democrat", "republican", "parliament", "poll"],
    culture: ["oscar", "grammy", "emmy", "tony award", "celebrity", "movie", "film", "box office", "album", "music", "song", "tv", "series", "met gala", "time person", "nobel", "concert", "taylor swift", "billboard"],
    crypto: ["bitcoin", "btc", "ethereum", "eth", "crypto", "dogecoin", "doge", "solana", "sol", "xrp", "ripple", "cardano", "stablecoin", "binance", "coinbase"],
    golf: ["golf", "pga", "masters", "ryder cup", "open championship", "lpga", "liv golf", "birdie", "tour championship"]
  };
  var TOPIC_LABEL = { gas: "Gas prices", elections: "Elections", culture: "Culture", crypto: "Crypto", golf: "Golf" };
  var TOPIC_ORDER = ["gas", "elections", "culture", "crypto", "golf"];

  function textOf(m) {
    return [m.title, m.yes_sub_title, m.ticker, m.event_ticker, m.subtitle]
      .filter(Boolean).join(" ").toLowerCase();
  }
  function classify(m) {
    var t = textOf(m);
    for (var i = 0; i < TOPIC_ORDER.length; i++) {
      var k = TOPIC_ORDER[i], words = TOPICS[k];
      for (var j = 0; j < words.length; j++) {
        if (t.indexOf(words[j]) !== -1) return k;
      }
    }
    return null;
  }
  function classifyText(s) {
    var t = String(s || "").toLowerCase();
    for (var i = 0; i < TOPIC_ORDER.length; i++) {
      var words = TOPICS[TOPIC_ORDER[i]];
      for (var j = 0; j < words.length; j++) if (t.indexOf(words[j]) !== -1) return TOPIC_ORDER[i];
    }
    return null;
  }

  /* ------------------------------------------------------------------ utils */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function num(v) { var n = parseFloat(v); return isFinite(n) ? n : NaN; }
  function money(v, dp) {
    var n = num(v); if (!isFinite(n)) return "—";
    return "$" + n.toFixed(dp == null ? 2 : dp);
  }
  function cents(v) { var n = num(v); return isFinite(n) ? (n * 100).toFixed(1) + "¢" : "—"; }
  function int(v) { var n = num(v); return isFinite(n) ? n.toLocaleString() : "—"; }
  function qty(v) { var n = num(v); if (!isFinite(n)) return "—"; return n.toLocaleString(undefined, { maximumFractionDigits: 2 }); }
  function dt(v) {
    if (!v) return "—";
    var d = new Date(v);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  }
  function hms(ms) {
    var d = new Date(ms);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
  function clockShort(ms) {
    var d = new Date(ms);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  }
  function ago(ms) {
    var s = Math.max(0, (Date.now() - ms) / 1000);
    if (s < 60) return Math.round(s) + "s ago";
    if (s < 3600) return Math.round(s / 60) + "m ago";
    if (s < 86400) return Math.round(s / 3600) + "h ago";
    return Math.round(s / 86400) + "d ago";
  }
  function store(key, fallback) {
    try { var raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; }
    catch (e) { return fallback; }
  }
  function save(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); return true; } catch (e) { return false; }
  }
  function uid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "id-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  }

  /* --------------------------------------------------------------- fetching */
  function apiError(status, body) {
    var code = body && (body.code || (body.error && body.error.code));
    var msg = body && (body.message || (body.error && body.error.message));
    var e = new Error("HTTP " + status + (code ? " · " + code : "") + (msg ? " · " + msg : ""));
    e.status = status; e.code = code; return e;
  }

  function publicGet(path) {
    return fetch(API + path, { headers: { Accept: "application/json" } }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) throw apiError(r.status, j);
        return j;
      });
    });
  }

  /* Cursor pagination as documented in /getting_started/pagination */
  async function paged(path, maxPages) {
    var out = [], cursor = "", pages = 0;
    maxPages = maxPages || 6;
    while (pages < maxPages) {
      var sep = path.indexOf("?") === -1 ? "?" : "&";
      var j = await publicGet(path + sep + "limit=1000" + (cursor ? "&cursor=" + encodeURIComponent(cursor) : ""));
      var rows = j.markets || j.events || j.series || [];
      out = out.concat(rows);
      cursor = j.cursor || "";
      pages++;
      if (!cursor) break;
    }
    return out;
  }

  /* ------------------------------------------------------------- market data
     GET /markets — fields verified on api-reference/market/get-markets:
     volume_fp, volume_24h_fp, last_price_dollars, yes_bid_dollars,
     yes_ask_dollars, no_bid_dollars, no_ask_dollars, open_interest_fp,
     result, settlement_value_dollars, settlement_ts, close_time.          */
  var State = {
    markets: [], allOpenCount: 0, topic: "all", term: "", sort: "notional",
    selected: null, windowSec: 300, points: [], lastRefresh: 0, loading: false
  };

  /* "Highest dollar amount" has no single API field. We show two documented
     proxies side by side and label them: volume × last price (notional traded)
     and open interest × last price (notional at risk). Neither is reported
     turnover — see Flagged for Review F-2. */
  function notionalTraded(m) { return num(m.volume_fp) * num(m.last_price_dollars); }
  function notionalOpen(m) { return num(m.open_interest_fp) * num(m.last_price_dollars); }

  function inScope(list) {
    return list.filter(function (m) { return classify(m) !== null; });
  }

  async function loadMarkets() {
    var markets = await paged("/markets?status=open", 6);
    State.allOpenCount = markets.length;
    State.markets = inScope(markets);
    State.lastRefresh = Date.now();
    return markets.length;
  }

  /* ------------------------------------------------ chart history storage */
  var HIST_KEY = "kd.hist.v1";
  var HIST = store(HIST_KEY, {});
  function pushPoint(ticker, ts, price) {
    if (!ticker || !isFinite(price)) return;
    var arr = HIST[ticker] || (HIST[ticker] = []);
    var last = arr[arr.length - 1];
    if (!last || ts - last[0] >= 1000) arr.push([ts, price]);
    var cut = Date.now() - 24 * 3600 * 1000;
    while (arr.length && arr[0][0] < cut) arr.shift();
    if (arr.length > 4000) arr.splice(0, arr.length - 4000);
    HIST[ticker] = arr;
  }
  function flushHist() { save(HIST_KEY, HIST); }

  /* ------------------------------------------------------------ price chart */
  function chartEls() {
    return { canvas: $("#priceChart"), note: $("#chartNote"), legend: $("#chartLegend") };
  }

  function drawChart() {
    var c = $("#priceChart"); if (!c) return;
    var dpr = window.devicePixelRatio || 1;
    var cssW = c.clientWidth || 640, cssH = c.clientHeight || 300;
    c.width = Math.round(cssW * dpr); c.height = Math.round(cssH * dpr);
    var ctx = c.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    var padL = 46, padR = 12, padT = 12, padB = 26;
    var w = cssW - padL - padR, h = cssH - padT - padB;

    var now = Date.now(), from = now - State.windowSec * 1000;
    var pts = (State.points || []).filter(function (p) { return p[0] >= from; });

    /* axes frame */
    ctx.strokeStyle = "#e5eaf1"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(padL, padT); ctx.lineTo(padL, padT + h); ctx.lineTo(padL + w, padT + h); ctx.stroke();

    /* y axis: contract price in dollars, 0..1 fixed domain labels */
    ctx.fillStyle = "#93a1b3";
    ctx.font = "10px ui-monospace, Menlo, monospace";
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    var lo = 0, hi = 1;
    if (pts.length) {
      var vals = pts.map(function (p) { return p[1]; });
      var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
      var pad = Math.max(0.02, (mx - mn) * 0.25);
      lo = Math.max(0, mn - pad); hi = Math.min(1, mx + pad);
      if (hi - lo < 0.02) { hi = Math.min(1, lo + 0.02); }
    }
    for (var i = 0; i <= 4; i++) {
      var v = hi - (hi - lo) * (i / 4);
      var y = padT + (h * i) / 4;
      ctx.strokeStyle = "#f0f3f8";
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + w, y); ctx.stroke();
      ctx.fillStyle = "#93a1b3";
      ctx.fillText("$" + v.toFixed(2), padL - 7, y);
    }

    /* x axis: time labels */
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    for (var k = 0; k <= 4; k++) {
      var tx = padL + (w * k) / 4;
      var tval = from + (State.windowSec * 1000 * k) / 4;
      ctx.strokeStyle = "#f0f3f8";
      ctx.beginPath(); ctx.moveTo(tx, padT); ctx.lineTo(tx, padT + h); ctx.stroke();
      ctx.fillStyle = "#93a1b3";
      ctx.fillText(State.windowSec >= 3600 ? clockShort(tval) : hms(tval), tx, padT + h + 7);
    }

    if (!pts.length) {
      ctx.fillStyle = "#93a1b3"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.font = "12px system-ui, sans-serif";
      ctx.fillText(State.selected ? "Collecting live snapshots…" : "Select a market to start the price series", padL + w / 2, padT + h / 2);
      return;
    }

    function px(ts) { return padL + w * ((ts - from) / (State.windowSec * 1000)); }
    function py(p) { return padT + h * (1 - (p - lo) / Math.max(1e-6, hi - lo)); }

    /* area + line */
    ctx.beginPath();
    pts.forEach(function (p, idx) { idx ? ctx.lineTo(px(p[0]), py(p[1])) : ctx.moveTo(px(p[0]), py(p[1])); });
    var linePath = ctx.getLineDash(), lastX = px(pts[pts.length - 1][0]);
    ctx.lineTo(lastX, padT + h); ctx.lineTo(px(pts[0][0]), padT + h); ctx.closePath();
    var grad = ctx.createLinearGradient(0, padT, 0, padT + h);
    grad.addColorStop(0, "rgba(15,140,104,.18)"); grad.addColorStop(1, "rgba(15,140,104,0)");
    ctx.fillStyle = grad; ctx.fill();

    ctx.beginPath();
    pts.forEach(function (p, idx) { idx ? ctx.lineTo(px(p[0]), py(p[1])) : ctx.moveTo(px(p[0]), py(p[1])); });
    ctx.strokeStyle = "#0f8c68"; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.stroke();

    /* last point marker + value */
    var lp = pts[pts.length - 1];
    ctx.fillStyle = "#0f8c68";
    ctx.beginPath(); ctx.arc(px(lp[0]), py(lp[1]), 3, 0, Math.PI * 2); ctx.fill();
    ctx.font = "600 10px ui-monospace, Menlo, monospace";
    ctx.textAlign = "right"; ctx.textBaseline = "bottom";
    ctx.fillStyle = "#0a6f53";
    ctx.fillText("$" + lp[1].toFixed(2), Math.min(padL + w - 2, px(lp[0]) + 34), Math.max(padT + 10, py(lp[1]) - 6));
    ctx.textAlign = "left";

    c._pts = pts; c._geom = { padL: padL, padT: padT, w: w, h: h, lo: lo, hi: hi, from: from };
  }

  function attachChartHover() {
    var c = $("#priceChart"); if (!c) return;
    var tip = $("#chartTip");
    c.addEventListener("mousemove", function (ev) {
      if (!c._pts || !c._geom) return;
      var r = c.getBoundingClientRect();
      var g = c._geom;
      var x = ev.clientX - r.left;
      if (x < g.padL || x > g.padL + g.w) { if (tip) tip.textContent = ""; return; }
      var ts = g.from + ((x - g.padL) / g.w) * State.windowSec * 1000;
      var best = c._pts[0], bestD = Infinity;
      c._pts.forEach(function (p) { var d = Math.abs(p[0] - ts); if (d < bestD) { bestD = d; best = p; } });
      if (tip) tip.textContent = new Date(best[0]).toLocaleTimeString() + " · $" + best[1].toFixed(2);
    });
    c.addEventListener("mouseleave", function () { if (tip) tip.textContent = ""; });
  }

  /* -------------------------------------------------------------- orderbook
     GET /markets/{ticker}/orderbook → orderbook_fp.yes_dollars / no_dollars,
     each [price_dollars, count_fp], ascending, best bid last. Only bids are
     returned; a YES bid at X equals a NO ask at 1-X (documented).          */
  async function loadOrderbook(ticker) {
    var box = $("#bookBox"); if (!box) return;
    box.innerHTML = '<p class="muted small">Loading order book…</p>';
    try {
      var j = await publicGet("/markets/" + encodeURIComponent(ticker) + "/orderbook");
      var fp = j.orderbook_fp || {};
      var yes = (fp.yes_dollars || []).map(function (r) { return { p: num(r[0]), q: num(r[1]) }; }).filter(function (r) { return isFinite(r.p) && isFinite(r.q); });
      var no = (fp.no_dollars || []).map(function (r) { return { p: num(r[0]), q: num(r[1]) }; }).filter(function (r) { return isFinite(r.p) && isFinite(r.q); });
      renderBook(yes, no);
    } catch (e) {
      box.innerHTML = '<div class="notice bad"><b>Order book unavailable.</b> ' + esc(e.message) + '. No values are inferred.</div>';
    }
  }

  function depthRows(levels, limit) {
    var sorted = levels.slice().sort(function (a, b) { return b.p - a.p; }).slice(0, limit || 12);
    var cum = 0, rows = [];
    sorted.forEach(function (l) { cum += l.q; rows.push({ p: l.p, q: l.q, cum: cum, dollars: l.p * l.q }); });
    return rows;
  }

  function renderBook(yes, no) {
    var box = $("#bookBox"); if (!box) return;
    if (!yes.length && !no.length) {
      box.innerHTML = '<div class="notice">No resting bids reported for this market (documented: an empty book returns empty arrays, not 404).</div>';
      return;
    }
    var yRows = depthRows(yes), nRows = depthRows(no);
    var bestYes = yes.length ? Math.max.apply(null, yes.map(function (l) { return l.p; })) : NaN;
    var bestNo = no.length ? Math.max.apply(null, no.map(function (l) { return l.p; })) : NaN;
    var impliedAsk = isFinite(bestNo) ? 1 - bestNo : NaN;
    var spread = (isFinite(bestYes) && isFinite(impliedAsk)) ? impliedAsk - bestYes : NaN;
    var maxQ = 1;
    yRows.concat(nRows).forEach(function (r) { if (r.q > maxQ) maxQ = r.q; });

    function sideTable(rows, cls, lastLabel) {
      var html = '<table><thead><tr><th class="num">Price</th><th class="num">Contracts here</th><th class="num">Cumulative</th><th class="num">Value at level</th></tr></thead><tbody>';
      if (!rows.length) html += '<tr><td colspan="4" class="empty">No resting bids.</td></tr>';
      rows.forEach(function (r, i) {
        var wPct = Math.max(3, Math.round((r.q / maxQ) * 100));
        html += '<tr><td class="num"><b>' + cents(r.p) + '</b>' + (i === 0 ? ' <span class="pill ok">best</span>' : '') + '</td>' +
          '<td class="num bar-cell"><span class="bar ' + cls + '" style="width:' + wPct + '%"></span><span>' + qty(r.q) + '</span></td>' +
          '<td class="num">' + qty(r.cum) + '</td><td class="num">' + money(r.dollars, 2) + '</td></tr>';
      });
      html += "</tbody></table>";
      return html;
    }

    var totalYes = yes.reduce(function (a, l) { return a + l.q; }, 0);
    var totalNo = no.reduce(function (a, l) { return a + l.q; }, 0);
    var depthDollars = yes.reduce(function (a, l) { return a + l.p * l.q; }, 0) + no.reduce(function (a, l) { return a + l.p * l.q; }, 0);

    box.innerHTML =
      '<div class="liquidity"><dl>' +
      '<dt>Best YES bid</dt><dd>' + (isFinite(bestYes) ? cents(bestYes) : "—") + '</dd>' +
      '<dt>Implied YES ask <span class="faint">(1 − best NO bid)</span></dt><dd>' + (isFinite(impliedAsk) ? cents(impliedAsk) : "—") + '</dd>' +
      '<dt>Spread</dt><dd>' + (isFinite(spread) ? (spread * 100).toFixed(1) + "¢" : "—") + '</dd>' +
      '<dt>Resting contracts (YES / NO)</dt><dd>' + qty(totalYes) + " / " + qty(totalNo) + '</dd>' +
      '<dt>Resting value both sides</dt><dd>' + money(depthDollars, 2) + '</dd>' +
      '</dl></div>' +
      '<div class="book" style="margin-top:12px">' +
      '<div><h4>YES bids — buy YES here</h4>' + sideTable(yRows, "", "") + '</div>' +
      '<div><h4>NO bids — sell YES / buy NO here</h4>' + sideTable(nRows, "no", "") + '</div>' +
      '</div>' +
      '<p class="xs faint" style="margin:9px 0 0">Contracts available at a given price is the “Contracts here” column; “Cumulative” adds every better-priced level. Values use price × contracts from the API, not an estimate. Kalshi returns bids only — asks are the mirrored NO bids.</p>';
  }

  /* ---------------------------------------------------------- market render */
  function maxNotional() {
    var mx = 0;
    State.markets.forEach(function (m) { var v = notionalTraded(m); if (v > mx) mx = v; });
    return mx || 1;
  }

  function filteredMarkets() {
    var term = State.term.trim().toLowerCase();
    var rows = State.markets.filter(function (m) {
      if (State.topic !== "all" && classify(m) !== State.topic) return false;
      if (!term) return true;
      return textOf(m).indexOf(term) !== -1;
    });
    var sort = State.sort;
    rows.sort(function (a, b) {
      if (sort === "volume") return num(b.volume_fp) - num(a.volume_fp);
      if (sort === "close") return new Date(a.close_time) - new Date(b.close_time);
      if (sort === "price") return num(b.last_price_dollars) - num(a.last_price_dollars);
      if (sort === "oi") return notionalOpen(b) - notionalOpen(a);
      return notionalTraded(b) - notionalTraded(a);
    });
    return rows;
  }

  function renderMarkets() {
    var tb = $("#marketsBody"); if (!tb) return;
    var rows = filteredMarkets();
    var mx = maxNotional();
    if (!rows.length) {
      tb.innerHTML = '<tr><td colspan="9" class="empty">No in-scope open markets match this filter right now. Nothing is filled in or estimated.</td></tr>';
      return;
    }
    tb.innerHTML = rows.slice(0, 60).map(function (m) {
      var t = classify(m), nt = notionalTraded(m), sh = Math.max(2, Math.round((nt / mx) * 100));
      var sel = State.selected && State.selected.ticker === m.ticker;
      return '<tr data-ticker="' + esc(m.ticker) + '"' + (sel ? ' class="sel"' : '') + ' style="cursor:pointer">' +
        '<td class="num">' + (isFinite(nt) ? money(nt, 0) : "—") +
        '<span class="bar" style="display:block;height:3px;margin-top:3px;background:#0f8c68;opacity:.25;width:' + sh + '%"></span></td>' +
        '<td><b>' + esc(m.ticker) + '</b><div class="xs faint">' + esc(m.event_ticker || "") + '</div></td>' +
        '<td class="wrap-cell">' + esc(m.title || m.yes_sub_title || "") + '</td>' +
        '<td><span class="pill ' + t + '">' + TOPIC_LABEL[t] + '</span></td>' +
        '<td class="num">' + cents(m.last_price_dollars) + '</td>' +
        '<td class="num">' + (isFinite(num(m.yes_bid_dollars)) ? cents(m.yes_bid_dollars) + " / " + cents(m.yes_ask_dollars) : "—") + '</td>' +
        '<td class="num">' + int(m.volume_fp) + '</td>' +
        '<td class="num">' + int(m.open_interest_fp) + '</td>' +
        '<td class="num nowrap">' + dt(m.close_time) + '</td>' +
        '</tr>';
    }).join("");

    $$("#marketsBody tr[data-ticker]").forEach(function (tr) {
      tr.addEventListener("click", function () { selectMarket(tr.getAttribute("data-ticker")); });
    });
  }

  function renderKpis() {
    var m = State.markets;
    var top = m.slice().sort(function (a, b) { return notionalTraded(b) - notionalTraded(a); })[0];
    setText("#kpiCount", int(m.length));
    setText("#kpiOpen", int(State.allOpenCount) + " open demo markets scanned");
    setText("#kpiTop", top ? money(notionalTraded(top), 0) : "—");
    setText("#kpiTopName", top ? (top.title || top.ticker) : "no in-scope market");
    var vol = m.reduce(function (a, x) { return a + (isFinite(num(x.volume_fp)) ? num(x.volume_fp) : 0); }, 0);
    setText("#kpiVolume", int(vol));
    var oi = m.reduce(function (a, x) { return a + (isFinite(num(x.open_interest_fp)) ? num(x.open_interest_fp) : 0); }, 0);
    setText("#kpiOI", int(oi));
    setText("#kpiTopics", TOPIC_ORDER.map(function (k) {
      return k + " " + m.filter(function (x) { return classify(x) === k; }).length;
    }).join(" · "));
  }

  function setText(sel, text) { var el = $(sel); if (el) el.textContent = text; }

  /* --------------------------------------------------------------- selection */
  async function selectMarket(ticker, opts) {
    opts = opts || {};
    var base = State.markets.filter(function (m) { return m.ticker === ticker; })[0];
    if (!base && !opts.allowOutside) return;
    State.selected = base || { ticker: ticker };
    if ($("#selTitle")) {
      $("#selTitle").textContent = State.selected.title || State.selected.yes_sub_title || ticker;
      $("#selTicker").textContent = ticker + (State.selected.event_ticker ? " · " + State.selected.event_ticker : "");
    }
    var t = classify(State.selected);
    if ($("#selTopic")) $("#selTopic").innerHTML = t ? '<span class="pill ' + t + '">' + TOPIC_LABEL[t] + '</span>' : '<span class="pill warn">unclassified</span>';
    renderMarkets();
    try {
      var j = await publicGet("/markets/" + encodeURIComponent(ticker));
      var fresh = j.market || j;
      State.selected = Object.assign({}, State.selected, fresh);
      renderSelectedStats();
      pushPoint(ticker, Date.now(), num(fresh.last_price_dollars));
      State.points = (HIST[ticker] || []).slice();
      flushHist(); drawChart();
    } catch (e) {
      if ($("#selStats")) $("#selStats").innerHTML = '<div class="notice bad"><b>Snapshot failed.</b> ' + esc(e.message) + "</div>";
    }
    loadOrderbook(ticker);
    if ($("#tradeTicker")) $("#tradeTicker").value = ticker;
  }

  function renderSelectedStats() {
    var m = State.selected; if (!m || !$("#selStats")) return;
    var spreadTxt = "—";
    if (isFinite(num(m.yes_bid_dollars)) && isFinite(num(m.yes_ask_dollars))) {
      spreadTxt = ((num(m.yes_ask_dollars) - num(m.yes_bid_dollars)) * 100).toFixed(1) + "¢";
    }
    $("#selStats").innerHTML =
      '<dl class="liquidity"><dt>Last price</dt><dd>' + cents(m.last_price_dollars) + '</dd>' +
      '<dt>YES bid / ask</dt><dd>' + cents(m.yes_bid_dollars) + " / " + cents(m.yes_ask_dollars) + '</dd>' +
      '<dt>YES size at bid / ask</dt><dd>' + qty(m.yes_bid_size_fp) + " / " + qty(m.yes_ask_size_fp) + '</dd>' +
      '<dt>Quoted spread</dt><dd>' + spreadTxt + '</dd>' +
      '<dt>Volume</dt><dd>' + int(m.volume_fp) + '</dd>' +
      '<dt>24h volume</dt><dd>' + int(m.volume_24h_fp) + '</dd>' +
      '<dt>Open interest</dt><dd>' + int(m.open_interest_fp) + '</dd>' +
      '<dt>Closes</dt><dd>' + dt(m.close_time) + '</dd>' +
      '<dt>Status</dt><dd>' + esc(m.status || "—") + '</dd>' +
      '</dl>' +
      (m.rules_primary ? '<details><summary>Market rules (from API)</summary><p class="xs muted" style="margin:0">' + esc(m.rules_primary) + '</p></details>' : "");
  }

  /* ------------------------------------------------------- resolution table */
  var RES_KEY = "kd.resolved.v1";

  async function loadResolved(opts) {
    var tb = $("#resolvedBody"); if (!tb) return;
    tb.innerHTML = '<tr><td colspan="6" class="empty">Loading settled demo markets…</td></tr>';
    try {
      var settled = await paged("/markets?status=settled", 4);
      var rows = inScope(settled).sort(function (a, b) {
        return new Date(b.settlement_ts || b.close_time) - new Date(a.settlement_ts || a.close_time);
      });
      save(RES_KEY, { ts: Date.now(), rows: rows.slice(0, 200) });
      renderResolved(rows);
      reconcileWatch(rows);
    } catch (e) {
      tb.innerHTML = '<tr><td colspan="6" class="empty"><b>Could not load settled markets:</b> ' + esc(e.message) + ". No outcome is assumed.</div></td></tr>";
    }
  }

  function renderResolved(rows) {
    var tb = $("#resolvedBody"); if (!tb) return;
    if (!rows.length) { tb.innerHTML = '<tr><td colspan="6" class="empty">No settled in-scope markets returned on the pages scanned.</td></tr>'; return; }
    tb.innerHTML = rows.slice(0, 40).map(function (m) {
      var t = classify(m);
      var r = String(m.result || "").toLowerCase();
      var pill = r === "yes" ? '<span class="pill yes">YES</span>' : r === "no" ? '<span class="pill no">NO</span>' : r === "scalar" ? '<span class="pill warn">scalar</span>' : '<span class="pill">unresolved</span>';
      return '<tr><td><b>' + esc(m.ticker) + '</b></td><td class="wrap-cell">' + esc(m.title || m.yes_sub_title || "") + '</td>' +
        '<td><span class="pill ' + t + '">' + TOPIC_LABEL[t] + '</span></td><td>' + pill + '</td>' +
        '<td class="num">' + cents(m.settlement_value_dollars) + '</td><td class="num nowrap">' + dt(m.settlement_ts || m.close_time) + '</td></tr>';
    }).join("");
  }

  function renderResolvedFromCache() {
    var c = store(RES_KEY, null);
    if (c && c.rows && c.rows.length) renderResolved(c.rows);
  }

  /* Watchlist: markets seen open are remembered; when they show up settled we
     record the yes/no outcome locally so the tracker keeps a stable history. */
  var WATCH_KEY = "kd.watch.v1";
  function reconcileWatch(settledRows) {
    var watch = store(WATCH_KEY, {});
    var seen = {};
    settledRows.forEach(function (m) {
      var w = watch[m.ticker];
      if (w && !w.result && m.result) {
        w.result = m.result; w.settledAt = m.settlement_ts || m.close_time; w.settledValue = m.settlement_value_dollars;
      }
      if (w) seen[m.ticker] = true;
    });
    State.markets.forEach(function (m) {
      if (!watch[m.ticker]) {
        watch[m.ticker] = {
          ticker: m.ticker, title: m.title || m.yes_sub_title, topic: classify(m),
          firstSeen: Date.now(), closeTime: m.close_time, result: null
        };
      }
    });
    save(WATCH_KEY, watch);
    renderWatch();
  }

  function renderWatch() {
    var tb = $("#watchBody"); if (!tb) return;
    var watch = store(WATCH_KEY, {});
    var rows = Object.keys(watch).map(function (k) { return watch[k]; })
      .sort(function (a, b) { return (b.firstSeen || 0) - (a.firstSeen || 0); });
    if (!rows.length) { tb.innerHTML = '<tr><td colspan="5" class="empty">No markets tracked yet. Tracked markets appear here after the first live load.</td></tr>'; return; }
    tb.innerHTML = rows.slice(0, 40).map(function (w) {
      var r = String(w.result || "").toLowerCase();
      var pill = r === "yes" ? '<span class="pill yes">YES</span>' : r === "no" ? '<span class="pill no">NO</span>' : '<span class="pill">pending</span>';
      return '<tr><td><b>' + esc(w.ticker) + '</b></td><td class="wrap-cell">' + esc(w.title || "") + '</td>' +
        '<td><span class="pill ' + (w.topic || "") + '">' + (TOPIC_LABEL[w.topic] || "—") + '</span></td>' +
        '<td>' + pill + '</td><td class="num nowrap">' + (w.settledAt ? dt(w.settledAt) : w.closeTime ? "closes " + dt(w.closeTime) : "—") + '</td></tr>';
    }).join("");
  }

  /* ================================================================ PAPER
     Paper trades are a local simulator. They are clearly labelled as not real
     Kalshi fills. They exist so performance tracking is usable without keys. */
  var PAPER_KEY = "kd.paper.v1";
  function paperTrades() { return store(PAPER_KEY, []); }
  function savePaper(list) { save(PAPER_KEY, list); }

  function paperPrice(m, side) {
    if (side === "yes") return num(m.yes_bid_dollars);
    var nb = num(m.no_bid_dollars);
    if (isFinite(nb)) return nb;
    var ya = num(m.yes_ask_dollars);
    return isFinite(ya) ? 1 - ya : NaN;
  }

  function placePaper(trade) {
    var list = paperTrades();
    list.push(trade);
    savePaper(list);
    renderPaper();
    return trade;
  }

  function settlePaperAgainst(markets, settledMap) {
    var list = paperTrades(), changed = false;
    list.forEach(function (t) {
      if (t.status !== "open") return;
      var res = settledMap[t.ticker];
      if (res) {
        t.status = "settled"; t.result = res.result; t.settledAt = res.settledAt || Date.now();
        var payout = res.result === t.side ? t.count * 1 : 0;
        t.pnl = payout - t.count * t.price;
        changed = true;
      } else {
        var m = markets.filter(function (x) { return x.ticker === t.ticker; })[0];
        if (m) { var p = paperPrice(m, t.side); if (isFinite(p)) t.mark = p; }
      }
    });
    if (changed) savePaper(list);
    return changed;
  }

  function paperSummary() {
    var list = paperTrades();
    var settled = list.filter(function (t) { return t.status === "settled"; });
    var wins = settled.filter(function (t) { return t.pnl > 0; }).length;
    var pnl = settled.reduce(function (a, t) { return a + (t.pnl || 0); }, 0);
    var open = list.filter(function (t) { return t.status === "open"; });
    var openUnreal = open.reduce(function (a, t) {
      if (!isFinite(t.mark)) return a;
      return a + (t.mark - t.price) * t.count;
    }, 0);
    return {
      total: list.length, settled: settled.length, open: open.length,
      wins: wins, winRate: settled.length ? wins / settled.length : NaN,
      realized: pnl, unrealized: openUnreal,
      staked: list.reduce(function (a, t) { return a + t.price * t.count; }, 0)
    };
  }

  function renderPaper() {
    var s = paperSummary();
    setText("#paperTotal", int(s.total));
    setText("#paperOpen", int(s.open));
    setText("#paperWinRate", isFinite(s.winRate) ? (s.winRate * 100).toFixed(0) + "%" : "—");
    setText("#paperRealized", isFinite(s.realized) ? money(s.realized, 2) : "—");
    setText("#paperUnrealized", isFinite(s.unrealized) ? money(s.unrealized, 2) : "—");

    var tb = $("#paperBody"); if (!tb) return;
    var list = paperTrades().slice().sort(function (a, b) { return b.ts - a.ts; });
    if (!list.length) {
      tb.innerHTML = '<tr><td colspan="9" class="empty">No paper trades yet. Use “Paper trade” on the dashboard, or the form above. Nothing is pre-filled.</td></tr>';
      return;
    }
    tb.innerHTML = list.slice(0, 60).map(function (t) {
      var pnl = t.status === "settled" ? t.pnl : (isFinite(t.mark) ? (t.mark - t.price) * t.count : NaN);
      var cls = !isFinite(pnl) ? "" : pnl >= 0 ? "yes" : "no";
      var st = t.status === "settled"
        ? '<span class="pill ' + (t.result === "yes" ? "yes" : "no") + '">' + esc(t.result).toUpperCase() + '</span>'
        : '<span class="pill">open</span>';
      return '<tr><td class="num nowrap">' + dt(t.ts) + '</td><td><b>' + esc(t.ticker) + '</b></td>' +
        '<td><span class="pill ' + (t.topic || "") + '">' + (TOPIC_LABEL[t.topic] || "—") + '</span></td>' +
        '<td><span class="pill ' + (t.side === "yes" ? "yes" : "no") + '">' + (t.side || "").toUpperCase() + '</span></td>' +
        '<td class="num">' + qty(t.count) + '</td><td class="num">' + cents(t.price) + '</td>' +
        '<td class="num">' + (isFinite(t.mark) && t.status === "open" ? cents(t.mark) : "—") + '</td>' +
        '<td>' + st + '</td><td class="num ' + cls + '">' + (isFinite(pnl) ? money(pnl, 2) : "—") + '</td></tr>';
    }).join("");
  }

  /* ============================================================ LIVE (signed)
     Signing per /getting_started/quick_start_authenticated_requests:
     message = timestamp_ms + METHOD + path (path from API root, no query),
     RSA-PSS/SHA-256 (salt = digest length) or Ed25519, base64 signature.    */
  function b64ToBytes(b64) {
    var bin = atob(b64.replace(/-----BEGIN [^-]+-----|-----END [^-]+-----|\s/g, ""));
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  function bufToB64(buf) {
    var bytes = new Uint8Array(buf), s = "";
    for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return btoa(s);
  }

  var keyCache = { pem: null, key: null, alg: null };
  async function importKey(pem) {
    if (keyCache.pem === pem) return keyCache;
    var der = b64ToBytes(pem);
    var alg = null, key = null;
    try { key = await crypto.subtle.importKey("pkcs8", der, { name: "Ed25519" }, false, ["sign"]); alg = "Ed25519"; }
    catch (e) {
      key = await crypto.subtle.importKey("pkcs8", der, { name: "RSA-PSS", hash: "SHA-256" }, false, ["sign"]);
      alg = "RSA-PSS";
    }
    keyCache = { pem: pem, key: key, alg: alg };
    return keyCache;
  }

  function creds() {
    var id = ($("#apiKeyId") && $("#apiKeyId").value.trim()) || sessionStorage.getItem("kd.keyId") || "";
    var pem = ($("#apiPrivateKey") && $("#apiPrivateKey").value.trim()) || sessionStorage.getItem("kd.pem") || "";
    return { id: id, pem: pem };
  }

  async function signedFetch(path, method, body) {
    var c = creds();
    if (!c.id || !c.pem) throw new Error("Add your demo API Key ID and private key first (Account & security → API Keys at demo.kalshi.co).");
    var k = await importKey(c.pem);
    var ts = String(Date.now());
    var msg = new TextEncoder().encode(ts + method + SIGN_PREFIX + path.split("?")[0]);
    var sig = k.alg === "Ed25519"
      ? await crypto.subtle.sign("Ed25519", k.key, msg)
      : await crypto.subtle.sign({ name: "RSA-PSS", saltLength: 32 }, k.key, msg);
    var res = await fetch(API + path, {
      method: method,
      headers: {
        "KALSHI-ACCESS-KEY": c.id,
        "KALSHI-ACCESS-SIGNATURE": bufToB64(sig),
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "Content-Type": "application/json",
        Accept: "application/json"
      },
      body: body ? JSON.stringify(body) : undefined
    });
    var j = await res.json().catch(function () { return {}; });
    if (!res.ok) throw apiError(res.status, j);
    return j;
  }

  var PORT = { balance: null, positions: [], fills: [], settlements: [] };

  async function loadPortfolio() {
    var box = $("#portfolioResult");
    if (box) box.innerHTML = '<p class="muted small">Requesting balance, positions, fills and settlements…</p>';
    try {
      var bal = await signedFetch("/portfolio/balance", "GET");
      var pos = await signedFetch("/portfolio/positions?limit=200&settlement_status=all&count_filter=position", "GET");
      var fills = await signedFetch("/portfolio/fills?limit=200", "GET");
      var sets = null;
      try { sets = await signedFetch("/portfolio/settlements?limit=200", "GET"); }
      catch (e) { sets = { settlements: [], _err: e.message }; }
      PORT.balance = bal;
      PORT.positions = pos.market_positions || [];
      PORT.fills = fills.fills || [];
      PORT.settlements = (sets && sets.settlements) || [];
      renderPortfolio(sets && sets._err);
      if (box) box.innerHTML = '<div class="notice ok"><b>Connected to the demo account.</b> Values below come straight from the API at ' + new Date().toLocaleTimeString() + ".</div>";
    } catch (e) {
      if (box) box.innerHTML = '<div class="notice bad"><b>Could not load the portfolio.</b> ' + esc(e.message) + "<br>Check the key pair, that the key is a <i>demo</i> key, and that its scopes allow portfolio reads. Nothing is shown rather than showing guessed numbers.</div>";
      clearPortfolio();
    }
  }

  function clearPortfolio() {
    ["#pfBalance", "#pfPortfolioValue", "#pfPositions", "#pfFills", "#pfRealized", "#pfFees"].forEach(function (s) { setText(s, "—"); });
    var tb = $("#positionsBody"); if (tb) tb.innerHTML = '<tr><td colspan="7" class="empty">Not connected. Values stay blank by design.</td></tr>';
    var fb = $("#fillsBody"); if (fb) fb.innerHTML = '<tr><td colspan="7" class="empty">Not connected.</td></tr>';
  }

  function renderPortfolio(settlementsErr) {
    var b = PORT.balance || {};
    setText("#pfBalance", isFinite(num(b.balance_dollars)) ? money(b.balance_dollars, 2) : (isFinite(num(b.balance)) ? money(num(b.balance) / 100, 2) : "—"));
    setText("#pfPortfolioValue", isFinite(num(b.portfolio_value)) ? money(num(b.portfolio_value) / 100, 2) : "—");
    setText("#pfPositions", int(PORT.positions.length));
    setText("#pfFills", int(PORT.fills.length));
    var realized = PORT.positions.reduce(function (a, p) { return a + (num(p.realized_pnl_dollars) || 0); }, 0);
    setText("#pfRealized", money(realized, 2));
    var fees = PORT.positions.reduce(function (a, p) { return a + (num(p.fees_paid_dollars) || 0); }, 0);
    setText("#pfFees", money(fees, 2));

    var tb = $("#positionsBody");
    if (tb) {
      if (!PORT.positions.length) tb.innerHTML = '<tr><td colspan="7" class="empty">No open positions returned for this account.</td></tr>';
      else tb.innerHTML = PORT.positions.map(function (p) {
        var t = classifyText(p.ticker);
        var pos = num(p.position_fp);
        return '<tr><td><b>' + esc(p.ticker) + '</b></td>' +
          '<td><span class="pill ' + (t || "") + '">' + (TOPIC_LABEL[t] || "other") + '</span></td>' +
          '<td class="num">' + (isFinite(pos) ? qty(Math.abs(pos)) + (pos < 0 ? " NO" : " YES") : "—") + '</td>' +
          '<td class="num">' + money(p.total_traded_dollars, 2) + '</td>' +
          '<td class="num">' + money(p.market_exposure_dollars, 2) + '</td>' +
          '<td class="num ' + (num(p.realized_pnl_dollars) >= 0 ? "yes" : "no") + '">' + money(p.realized_pnl_dollars, 2) + '</td>' +
          '<td class="num">' + money(p.fees_paid_dollars, 2) + '</td></tr>';
      }).join("");
    }

    var fb = $("#fillsBody");
    if (fb) {
      if (!PORT.fills.length) fb.innerHTML = '<tr><td colspan="7" class="empty">No fills returned.</td></tr>';
      else fb.innerHTML = PORT.fills.slice(0, 80).map(function (f) {
        var t = classifyText(f.ticker || f.market_ticker);
        var side = String(f.outcome_side || f.side || "").toLowerCase();
        return '<tr><td class="num nowrap">' + dt(f.created_time || (f.ts ? f.ts * 1000 : null)) + '</td>' +
          '<td><b>' + esc(f.ticker || f.market_ticker) + '</b></td>' +
          '<td><span class="pill ' + (t || "") + '">' + (TOPIC_LABEL[t] || "other") + '</span></td>' +
          '<td><span class="pill ' + (side === "yes" ? "yes" : "no") + '">' + esc(side.toUpperCase() || "—") + '</span></td>' +
          '<td class="num">' + qty(f.count_fp) + '</td>' +
          '<td class="num">' + cents(f.yes_price_dollars) + '</td>' +
          '<td class="num">' + money(f.fee_cost, 4) + '</td></tr>';
      }).join("");
    }

    var sb = $("#settlementsBody");
    if (sb) {
      if (settlementsErr) sb.innerHTML = '<tr><td colspan="4" class="empty">Settlements unavailable: ' + esc(settlementsErr) + '</td></tr>';
      else if (!PORT.settlements.length) sb.innerHTML = '<tr><td colspan="4" class="empty">No settlements returned for this account.</td></tr>';
      else sb.innerHTML = PORT.settlements.map(function (s) {
        var r = String(s.market_result || "").toLowerCase();
        return '<tr><td><b>' + esc(s.ticker) + '</b></td>' +
          '<td><span class="pill ' + (r === "yes" ? "yes" : r === "no" ? "no" : "warn") + '">' + esc(r.toUpperCase() || "—") + '</span></td>' +
          '<td class="num">' + money(num(s.revenue) / 100, 2) + '</td>' +
          '<td class="num nowrap">' + dt(s.settled_time) + '</td></tr>';
      }).join("");
    }
    renderAnalysis();
  }

  /* ------------------------------------------------------- trade categories */
  function priceBand(p) {
    if (!isFinite(p)) return "unknown";
    if (p < 0.2) return "<20¢";
    if (p < 0.5) return "20-50¢";
    if (p < 0.8) return "50-80¢";
    return "80¢+";
  }

  function groupBy(rows, keyFn) {
    var out = {};
    rows.forEach(function (r) {
      var k = keyFn(r); var g = out[k] || (out[k] = []);
      g.push(r);
    });
    return out;
  }

  /* Analysis uses REAL demo fills when connected; otherwise it analyses the
     local paper-trade log and says so explicitly.                            */
  function analysisRows() {
    var real = PORT.fills.map(function (f) {
      return {
        source: "live", ticker: f.ticker || f.market_ticker, topic: classifyText(f.ticker || f.market_ticker) || "other",
        side: String(f.outcome_side || f.side || "").toLowerCase() || "unknown",
        price: num(f.yes_price_dollars), count: num(f.count_fp), fee: num(f.fee_cost) || 0,
        ts: f.created_time ? new Date(f.created_time).getTime() : (f.ts ? f.ts * 1000 : null)
      };
    });
    if (real.length) return { source: "live", rows: real };
    var paper = paperTrades().map(function (t) {
      return {
        source: "paper", ticker: t.ticker, topic: t.topic || "other", side: t.side,
        price: t.price, count: t.count, fee: 0, ts: t.ts,
        pnl: t.status === "settled" ? t.pnl : (isFinite(t.mark) ? (t.mark - t.price) * t.count : null),
        settled: t.status === "settled"
      };
    });
    return { source: paper.length ? "paper" : "none", rows: paper };
  }

  var MIN_N = 10; /* explicit threshold: below this we refuse to call it a pattern */

  function renderAnalysis() {
    var host = $("#analysisBody"); if (!host) return;
    var a = analysisRows();
    if (!a.rows.length) {
      host.innerHTML = '<div class="notice"><b>No trade data yet.</b> Analysis stays empty until there are real demo fills or local paper trades. No strategy is invented from nothing.</div>';
      var tbl = $("#strategyBody");
      if (tbl) tbl.innerHTML = '<tr><td colspan="5" class="empty">Insufficient data — no strategy can be supported.</td></tr>';
      return;
    }

    var rows = a.rows;
    var sourceNote = a.source === "live"
      ? "Computed from <b>real demo fills</b> loaded from <code>GET /portfolio/fills</code>."
      : "Computed from the <b>local paper-trade log</b> in this browser (simulated, not Kalshi fills).";

    function table(title, groups, note) {
      var keys = Object.keys(groups).sort();
      var html = '<h4>' + title + '</h4><div class="table-wrap"><table><thead><tr><th>Bucket</th><th class="num">Trades</th><th class="num">Contracts</th><th class="num">Avg price</th><th class="num">Cost</th><th class="num">Fees</th><th class="num">P&amp;L</th><th>Signal</th></tr></thead><tbody>';
      keys.forEach(function (k) {
        var g = groups[k];
        var n = g.length;
        var contracts = g.reduce(function (s, r) { return s + (isFinite(r.count) ? r.count : 0); }, 0);
        var cost = g.reduce(function (s, r) { return s + (isFinite(r.price) && isFinite(r.count) ? r.price * r.count : 0); }, 0);
        var fees = g.reduce(function (s, r) { return s + (r.fee || 0); }, 0);
        var avg = contracts ? cost / contracts : NaN;
        var pnls = g.map(function (r) { return r.pnl; }).filter(function (v) { return isFinite(v); });
        var pnl = pnls.length ? pnls.reduce(function (x, y) { return x + y; }, 0) : NaN;
        var signal = n < MIN_N ? '<span class="pill warn">insufficient (n&lt;' + MIN_N + ')</span>' : '<span class="pill ok">n=' + n + '</span>';
        html += '<tr><td>' + esc(k) + '</td><td class="num">' + n + '</td><td class="num">' + qty(contracts) + '</td>' +
          '<td class="num">' + (isFinite(avg) ? cents(avg) : "—") + '</td><td class="num">' + money(cost, 2) + '</td>' +
          '<td class="num">' + money(fees, 2) + '</td><td class="num ' + (isFinite(pnl) ? (pnl >= 0 ? "yes" : "no") : "") + '">' + (isFinite(pnl) ? money(pnl, 2) : "—") + '</td>' +
          '<td>' + signal + '</td></tr>';
      });
      html += '</tbody></table></div>' + (note ? '<p class="xs faint" style="margin:6px 0 0">' + note + '</p>' : "");
      return html;
    }

    host.innerHTML = '<p class="small muted" style="margin:0 0 6px">' + sourceNote + '</p>' +
      '<p class="xs faint" style="margin:0 0 12px">A bucket is only called a pattern when it holds at least ' + MIN_N + ' trades. Below that the honest answer is “insufficient data”.</p>' +
      table("By topic", groupBy(rows, function (r) { return r.topic; })) +
      table("By side", groupBy(rows, function (r) { return r.side; })) +
      table("By entry-price band", groupBy(rows, function (r) { return priceBand(r.price); }),
        "Price bands show where the fills actually sat. Cheap contracts need a higher hit rate to break even; that is arithmetic, not advice.") +
      table("By topic × side", groupBy(rows, function (r) { return r.topic + " / " + r.side; }));

    /* Strategy candidates: only from buckets that clear the threshold. */
    var byCat = groupBy(rows, function (r) { return r.topic + " / " + r.side; });
    var cands = Object.keys(byCat).map(function (k) {
      var g = byCat[k];
      var contracts = g.reduce(function (s, r) { return s + r.count; }, 0);
      var cost = g.reduce(function (s, r) { return s + r.price * r.count; }, 0);
      var avg = contracts ? cost / contracts : NaN;
      var pnls = g.map(function (r) { return r.pnl; }).filter(isFinite);
      var pnl = pnls.length ? pnls.reduce(function (x, y) { return x + y; }, 0) : NaN;
      return { k: k, n: g.length, avg: avg, pnl: pnl };
    }).sort(function (x, y) { return y.n - x.n; });

    var sb = $("#strategyBody");
    if (sb) {
      var ok = cands.filter(function (c) { return c.n >= MIN_N; });
      if (!ok.length) {
        sb.innerHTML = '<tr><td colspan="5" class="empty">No category has reached ' + MIN_N + ' trades yet. Largest so far: ' +
          (cands.length ? esc(cands[0].k) + " with n=" + cands[0].n : "none") + ". Strategy generation is withheld rather than guessed.</td></tr>";
      } else {
        sb.innerHTML = ok.map(function (c) {
          var label = c.pnl > 0 ? "positive so far" : c.pnl < 0 ? "negative so far" : "flat";
          var rule = c.pnl > 0
            ? "Keep sizing this bucket only while the edge survives fees; cap size per market and re-check at n=" + (c.n + 10) + "."
            : "This bucket is losing. Reduce size to the minimum and re-test the thesis before adding contracts.";
          return '<tr><td><b>' + esc(c.k) + '</b></td><td class="num">' + c.n + '</td><td class="num">' + cents(c.avg) + '</td>' +
            '<td class="num ' + (c.pnl >= 0 ? "yes" : "no") + '">' + money(c.pnl, 2) + '</td><td>' + esc(label) + " — " + esc(rule) + '</td></tr>';
        }).join("");
      }
    }

    setText("#analysisSource", a.source === "live" ? "real demo fills" : a.source === "paper" ? "paper-trade log" : "no data");
    setText("#analysisCount", int(rows.length));
  }

  /* ------------------------------------------------------------- paper form */
  function wirePaperForm() {
    var form = $("#paperForm"); if (!form) return;
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var ticker = $("#tradeTicker").value.trim().toUpperCase();
      var side = $("#tradeSide").value;
      var count = num($("#tradeCount").value);
      var price = num($("#tradePrice").value);
      var out = $("#tradeResult");
      if (!ticker) { out.innerHTML = '<div class="notice bad">Enter a market ticker.</div>'; return; }
      if (!isFinite(count) || count <= 0) { out.innerHTML = '<div class="notice bad">Contract count must be a positive number of contracts.</div>'; return; }
      if (Math.round(count) !== count) { out.innerHTML = '<div class="notice bad">Contract count must be a whole number; the simulator does not model fractional fills.</div>'; return; }
      if (!isFinite(price) || price <= 0 || price >= 1) { out.innerHTML = '<div class="notice bad">Price must be between $0.01 and $0.99, because a contract pays at most $1.00.</div>'; return; }
      var byText = classifyText(ticker);
      var topic = byText || (State.topic && State.topic !== "all" ? State.topic : "other");
      var t = {
        id: uid(), ts: Date.now(), ticker: ticker, topic: topic,
        side: side, count: count, price: price, status: "open", mark: price, note: "paper"
      };
      placePaper(t);
      out.innerHTML = '<div class="notice ok"><b>Paper trade logged.</b> ' + esc(ticker) + " · " + esc(side.toUpperCase()) + " · " + qty(count) + " @ " + cents(price) +
        ". It is simulated, appears in the analysis below, and settles when the API reports a yes/no result.</div>";
      form.reset();
    });
  }

  /* -------------------------------------------------------- live order form */
  function wireLiveOrder() {
    var btn = $("#liveOrderBtn"); if (!btn) return;
    btn.addEventListener("click", async function () {
      var out = $("#liveOrderResult");
      var ticker = ($("#liveTicker") && $("#liveTicker").value.trim().toUpperCase()) || "";
      var side = $("#liveSide") ? $("#liveSide").value : "bid";
      var count = num($("#liveCount") && $("#liveCount").value);
      var price = num($("#livePrice") && $("#livePrice").value);
      var ack = $("#liveAck") && $("#liveAck").checked;
      if (!ticker) { out.innerHTML = '<div class="notice bad">Enter a market ticker.</div>'; return; }
      if (!isFinite(count) || count <= 0) { out.innerHTML = '<div class="notice bad">Count must be a positive number of contracts.</div>'; return; }
      if (!isFinite(price) || price <= 0 || price >= 1) { out.innerHTML = '<div class="notice bad">Price must be between $0.01 and $0.99.</div>'; return; }
      if (!ack) { out.innerHTML = '<div class="notice warn">Tick the confirmation box first. Orders are real demo-environment writes.</div>'; return; }
      btn.disabled = true;
      out.innerHTML = '<p class="muted small">Signing and sending order…</p>';
      try {
        /* POST /portfolio/events/orders (V2). The legacy POST /portfolio/orders
           is removed and returns 410 Gone — see verification page V-9. */
        var j = await signedFetch("/portfolio/events/orders", "POST", {
          ticker: ticker,
          client_order_id: uid(),
          side: side,                    /* bid = buy YES, ask = sell YES */
          count: String(count),
          price: price.toFixed(4),
          time_in_force: "good_till_canceled",
          self_trade_prevention_type: "taker_at_cross"
        });
        out.innerHTML = '<div class="notice ok"><b>Order accepted by the demo exchange.</b> ' +
          "order_id <code>" + esc(j.order_id || "—") + "</code> · filled " + esc(j.fill_count || "0") +
          " · remaining " + esc(j.remaining_count || "—") + ". A 201 means accepted, not necessarily resting — check remaining_count.</div>";
        loadPortfolio();
      } catch (e) {
        out.innerHTML = '<div class="notice bad"><b>Order rejected.</b> ' + esc(e.message) +
          "<br>Common causes: wrong key type, insufficient demo balance, price off the market's price grid, or market not open.</div>";
      } finally {
        btn.disabled = false;
      }
    });
  }

  /* ================================================================ dashboard */
  var pollTimer = null;

  async function refreshAll(manual) {
    if (State.loading) return;
    State.loading = true;
    var chip = $("#liveChip");
    if (chip) chip.innerHTML = '<span class="dot stale"></span> Refreshing…';
    try {
      var total = await loadMarkets();
      renderKpis(); renderMarkets();
      setText("#lastUpdate", new Date().toLocaleTimeString());
      if (chip) chip.innerHTML = '<span class="dot"></span> Live · ' + int(State.markets.length) + " in scope";
      if (!State.selected && State.markets.length) {
        var top = State.markets.slice().sort(function (a, b) { return notionalTraded(b) - notionalTraded(a); })[0];
        await selectMarket(top.ticker);
      }
      if (State.selected) {
        try {
          var j = await publicGet("/markets/" + encodeURIComponent(State.selected.ticker));
          var fresh = j.market || j;
          if (fresh && fresh.ticker) {
            State.selected = Object.assign({}, State.selected, fresh);
            pushPoint(fresh.ticker, Date.now(), num(fresh.last_price_dollars));
            State.points = (HIST[fresh.ticker] || []).slice();
            flushHist(); drawChart(); renderSelectedStats();
          }
        } catch (e) { /* transient — keep the last good snapshot, note stays */ }
      }
      refreshResolutionQuietly();
      return total;
    } catch (e) {
      if (chip) chip.innerHTML = '<span class="dot err"></span> API unreachable';
      var status = $("#dataStatus");
      if (status) status.innerHTML = '<div class="notice bad"><b>Live demo data could not be loaded.</b> ' + esc(e.message) +
        "<br>The dashboard deliberately shows no numbers instead of placeholder values. This is usually the browser blocking the cross-origin request, or the demo API being unavailable. Retry with “Refresh”.</div>";
      renderPaper(); renderWatch();
      return 0;
    } finally {
      State.loading = false;
    }
  }

  var resTimer = null;
  async function refreshResolutionQuietly() {
    try {
      var settled = await paged("/markets?status=settled", 3);
      var rows = inScope(settled);
      var map = {};
      rows.forEach(function (m) {
        if (m.result) map[m.ticker] = { result: m.result, settledAt: m.settlement_ts || m.close_time };
      });
      if (settlePaperAgainst(State.markets, map)) renderPaper();
      else renderPaper();
      lastSettled = rows;
      reconcileWatch(rows);
    } catch (e) { /* silent: resolution refresh is best-effort */ }
  }

  var lastSettled = [];

  function wireDashboard() {
    $$("#topicTabs button").forEach(function (b) {
      b.addEventListener("click", function () {
        State.topic = b.getAttribute("data-topic");
        $$("#topicTabs button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
        renderMarkets();
      });
    });
    var search = $("#marketSearch");
    if (search) search.addEventListener("input", function () { State.term = search.value; renderMarkets(); });
    var sort = $("#sortSelect");
    if (sort) sort.addEventListener("change", function () { State.sort = sort.value; renderMarkets(); });
    var refresh = $("#refreshBtn");
    if (refresh) refresh.addEventListener("click", function () { refreshAll(true); });
    var ob = $("#reloadBook");
    if (ob) ob.addEventListener("click", function () { if (State.selected) loadOrderbook(State.selected.ticker); });
    $$("#windowTabs button").forEach(function (b) {
      b.addEventListener("click", function () {
        State.windowSec = parseInt(b.getAttribute("data-window"), 10);
        $$("#windowTabs button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
        setText("#windowLabel", b.textContent.trim());
        drawChart();
      });
    });
    var clearHist = $("#clearHist");
    if (clearHist) clearHist.addEventListener("click", function () {
      if (State.selected) { HIST[State.selected.ticker] = []; State.points = []; flushHist(); drawChart(); }
    });
    attachChartHover();
    wirePaperForm(); wireLiveOrder();
    renderPaper(); renderWatch();
    if ($("#resolvedBody")) loadResolved();
    if ($("#marketsBody")) {
      refreshAll(true);
      pollTimer = setInterval(function () { refreshAll(false); }, 15000);
      window.addEventListener("resize", function () { drawChart(); });
    }
    renderAnalysis();
  }

  /* ------------------------------------------------------------ category page */
  async function initCategory(topic) {
    var tb = $("#catBody"); if (!tb) return;
    tb.innerHTML = '<tr><td colspan="7" class="empty">Loading live demo markets…</td></tr>';
    try {
      var all = await paged("/markets?status=open", 6);
      var rows = all.filter(function (m) { return classify(m) === topic; })
        .sort(function (a, b) { return notionalTraded(b) - notionalTraded(a); });
      setText("#catCount", int(rows.length));
      setText("#catScanned", int(all.length));
      var tot = rows.reduce(function (a, m) { return a + (isFinite(notionalTraded(m)) ? notionalTraded(m) : 0); }, 0);
      setText("#catNotional", rows.length ? money(tot, 0) : "—");
      setText("#catTop", rows.length ? (rows[0].title || rows[0].ticker) : "—");
      setText("#catUpdated", new Date().toLocaleTimeString());

      if (!rows.length) {
        tb.innerHTML = '<tr><td colspan="7" class="empty">The demo API returned no open markets matching this topic’s keywords in the pages scanned. That is a real result, not a placeholder.</td></tr>';
      } else {
        tb.innerHTML = rows.slice(0, 80).map(function (m) {
          return '<tr><td><b>' + esc(m.ticker) + '</b></td><td class="wrap-cell">' + esc(m.title || m.yes_sub_title || "") + '</td>' +
            '<td class="num">' + cents(m.last_price_dollars) + '</td>' +
            '<td class="num">' + cents(m.yes_bid_dollars) + " / " + cents(m.yes_ask_dollars) + '</td>' +
            '<td class="num">' + int(m.volume_fp) + '</td>' +
            '<td class="num">' + money(notionalTraded(m), 0) + '</td>' +
            '<td class="num nowrap">' + dt(m.close_time) + '</td></tr>';
        }).join("");
      }

      var settled = (await paged("/markets?status=settled", 4)).filter(function (m) { return classify(m) === topic; })
        .sort(function (a, b) { return new Date(b.settlement_ts || b.close_time) - new Date(a.settlement_ts || a.close_time); });
      var rb = $("#catResolvedBody");
      if (rb) {
        rb.innerHTML = settled.length ? settled.slice(0, 40).map(function (m) {
          var r = String(m.result || "").toLowerCase();
          return '<tr><td><b>' + esc(m.ticker) + '</b></td><td class="wrap-cell">' + esc(m.title || m.yes_sub_title || "") + '</td>' +
            '<td><span class="pill ' + (r === "yes" ? "yes" : r === "no" ? "no" : "") + '">' + esc(r.toUpperCase() || "—") + '</span></td>' +
            '<td class="num">' + cents(m.settlement_value_dollars) + '</td><td class="num nowrap">' + dt(m.settlement_ts || m.close_time) + '</td></tr>';
        }).join("") : '<tr><td colspan="5" class="empty">No settled markets for this topic in the pages scanned.</td></tr>';
      }
    } catch (e) {
      tb.innerHTML = '<tr><td colspan="7" class="empty"><b>Demo API unavailable:</b> ' + esc(e.message) + ". No values are shown rather than guessed.</td></tr>";
      var st = $("#catStatus");
      if (st) st.innerHTML = '<div class="notice bad">Live fetch failed: ' + esc(e.message) + "</div>";
    }
  }

  /* ------------------------------------------------------------ table filters
     Used by the verification and questions tables. Button labels carry the real
     row count so a stated number can never drift from the table beneath it.   */
  function initFilters() {
    $$("[data-filter]").forEach(function (b) {
      var group = b.parentNode;
      if (group && group.getAttribute("data-filter-ready")) return;
      if (group) group.setAttribute("data-filter-ready", "1");
    });
    var groups = $$("[data-filter]").map(function (b) { return b.parentNode; })
      .filter(function (g, i, all) { return g && all.indexOf(g) === i; });

    groups.forEach(function (group) {
      var buttons = $$("[data-filter]", group);
      var tableId = group.getAttribute("data-table") || (group.closest(".toolbar") && group.closest(".toolbar").getAttribute("data-table"));
      var table = tableId ? $("#" + tableId) : $("table[id]");
      if (!table) return;
      var rows = $$("tbody tr", table);
      var tally = {};
      rows.forEach(function (r) {
        var st = r.getAttribute("data-state");
        if (st) tally[st] = (tally[st] || 0) + 1;
        if (r.getAttribute("data-blocking") === "yes") tally.blocking = (tally.blocking || 0) + 1;
      });
      var status = group.parentNode ? $(".status", group.parentNode) : null;

      function label(b) {
        var f = b.getAttribute("data-filter");
        var n = f === "all" ? rows.length : (tally[f] || 0);
        b.textContent = b.textContent.replace(/\s*[(\u2014-]?\s*\d+\s*\)?$/, "") + " (" + n + ")";
      }
      buttons.forEach(function (b) {
        label(b);
        if (b._wired) return;
        b._wired = true;
        b.addEventListener("click", function () {
          buttons.forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
          var f = b.getAttribute("data-filter"), shown = 0;
          rows.forEach(function (r) {
            var st = r.getAttribute("data-state");
            var ok = f === "all" || st === f || (f === "blocking" && r.getAttribute("data-blocking") === "yes");
            r.style.display = ok ? "" : "none";
            if (ok) shown++;
          });
          if (status) status.textContent = "Showing " + shown + " of " + rows.length;
        });
      });
      if (status) status.textContent = "Showing all " + rows.length;
    });
  }

  /* ------------------------------------------------------------------- boot */
  function boot() {
    var page = document.body.getAttribute("data-page");
    if (page === "dashboard") wireDashboard();
    else if (page === "category") {
      var topic = document.body.getAttribute("data-topic");
      initCategory(topic);
      var btn = $("#catRefresh");
      if (btn) btn.addEventListener("click", function () { initCategory(topic); });
      renderPaper();
    } else if (page === "portfolio") {
      wirePaperForm(); wireLiveOrder(); renderPaper(); renderAnalysis();
      renderResolvedFromCache(); renderWatch();
      loadResolved().catch(function () {});
    } else if (page === "analysis") {  /* live/trading-analysis.html */
      renderAnalysis();
      var b = $("#analysisRefresh");
      if (b) b.addEventListener("click", renderAnalysis);
    } else if (page === "resolution") {
      loadResolved(); renderWatch(); renderPaper();
      var rb = $("#resRefresh");
      if (rb) rb.addEventListener("click", function () { loadResolved(); });
    }
    initFilters();
    var year = $("#year"); if (year) year.textContent = new Date().getFullYear();
    if (page === "dashboard" || page === "category") {
      window.addEventListener("beforeunload", flushHist);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  /* expose a tiny surface for debugging in the console */
  window.KD = {
    API: API,
    state: State,
    refresh: refreshAll,
    select: selectMarket,
    loadPortfolio: loadPortfolio,
    loadOrderbook: loadOrderbook,
    paper: paperTrades,
    analyze: analysisRows,
    clearPaper: function () { savePaper([]); renderPaper(); renderAnalysis(); },
    clearWatch: function () { save(WATCH_KEY, {}); renderWatch(); }
  };
})();
