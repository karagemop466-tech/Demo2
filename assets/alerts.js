/* Live alert chats for the Kalshi demo dashboard — assets/alerts.js
 *
 * Two scrolling chats side by side:
 *   1. "All events"  — every detected swing of >= $0.10 in contract price, in any
 *      in-scope market (gas, elections, culture, crypto, golf), plus resolution
 *      notices as markets settle yes/no.
 *   2. "High-ROI model picks" — the same feed filtered to markets the model (a
 *      documented heuristic, below) scores at or above the cutoff.
 *
 * Data sources (all official; no value is invented):
 *   GET /markets/trades?min_ts=<unix s>&limit=1000   — trade tape (get-trades docs)
 *   GET /markets?status=open&limit=1000              — current quotes (get-markets docs)
 *   GET /markets/{ticker}/orderbook?depth=10         — liquidity on selection
 * plus the committed data/snapshot.json + data/history.json as the labelled fallback.
 * Verified request shapes: docs.kalshi.com/api-reference/market/get-trades,
 * get-markets, get-market-orderbook (see pages/verification.html rows).
 *
 * Detection rule (user requirement): |change in contract price| >= $0.10 between
 * two consecutive observations (two prints, or two quote samples), either direction.
 *
 * The cause of a swing is NOT derivable from the API. Each alert links to the
 * market and offers only a news SEARCH link labelled "possible context (unverified)"
 * — it asserts nothing (flagged F13 on pages/flagged.html).
 *
 * High-ROI model — transparent heuristic, computed in the browser from official
 * fields only. NOT financial advice, NOT an outcome prediction, NOT backtested:
 *   score = 0.40*liquidity + 0.30*tightness + 0.30*price_action
 *     liquidity    = clamp(log10(1 + volume_fp) / 4, 0, 1)      (observed volume)
 *     tightness    = clamp(1 - 2*(yes_ask - yes_bid), 0, 1)      (narrower = better)
 *     price_action = clamp(sessionSwings / 5, 0, 1)             (>= $0.10 swings seen)
 *   "High ROI" feed = markets with score >= 0.60 at alert time.
 */
(function () {
  "use strict";
  var API = "https://external-api.demo.kalshi.co/trade-api/v2";
  var SWING = 0.10;            // $0.10 threshold, per the requirement
  var POLL_MS = 15000;         // same cadence as the Live Console; 429 => backoff
  var TRACK_PER_TOPIC = 12;    // highest est. dollar volume, per topic
  var MAX_FEED = 300;          // entries kept per chat
  var ROI_CUT = 0.60;
  var SESSION_TICK_CAP = 400;

  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>\"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };
  var num = function (v, d) { var n = Number(v); return isFinite(n) ? n.toFixed(d == null ? 2 : d) : "—"; };
  var clamp = function (v, lo, hi) { return Math.max(lo, Math.min(hi, v)); };

  var S = {
    idx: new Map(),          // ticker -> meta {topic,title,series_ticker,event_ticker,market_url,close_time}
    quote: new Map(),        // ticker -> last observed {last,yes_bid,yes_ask,volume_fp,open_interest_fp,status,result}
    tapeLast: new Map(),     // ticker -> last print price observed
    swings: new Map(),       // ticker -> session swing count
    ticks: new Map(),        // ticker -> [{t,v}] session samples for the chart
    announced: new Map(),    // ticker -> result already announced
    feedAll: [], feedRoi: [],
    minTs: null,             // trades min_ts cursor (unix seconds)
    paused: false,
    backoffUntil: 0,
    fails: 0,
    selected: null,
    win: 3600,
    topicFilter: "",
    snapshot: null,
  };

  /* ------------------------------------------------------------ model */
  function modelScore(t) {
    var q = S.quote.get(t) || {};
    var meta = S.idx.get(t) || {};
    var vol = parseFloat(q.volume_fp != null ? q.volume_fp : meta.volume_fp);
    var liq = clamp((Math.log10(1 + (isFinite(vol) ? vol : 0))) / 4, 0, 1);
    var yb = parseFloat(q.yes_bid != null ? q.yes_bid : meta.yes_bid_dollars);
    var ya = parseFloat(q.yes_ask != null ? q.yes_ask : meta.yes_ask_dollars);
    var spread = (isFinite(yb) && isFinite(ya)) ? (ya - yb) : 1;
    var tight = clamp(1 - 2 * spread, 0, 1);
    var act = clamp((S.swings.get(t) || 0) / 5, 0, 1);
    return { score: 0.40 * liq + 0.30 * tight + 0.30 * act, liq: liq, tight: tight, act: act };
  }

  /* ------------------------------------------------------------ feed */
  function newsLink(meta) {
    var q = encodeURIComponent((meta.title || meta.market_ticker || "").replace(/[()]/g, " "));
    return '<a href="https://news.google.com/search?q=' + q + '" target="_blank" rel="noopener" ' +
      'title="A news search that MAY be related. Not an official source; causation is unverified (F13).">' +
      "possible context (unverified)</a>";
  }

  function pushEntry(kind, ticker, html, model) {
    var e = {
      kind: kind, ticker: ticker, html: html, model: model,
      t: new Date().toISOString(), sort: Date.now(),
    };
    S.feedAll.unshift(e);
    if (S.feedAll.length > MAX_FEED) S.feedAll.pop();
    if (kind === "swing" && model && model.score >= ROI_CUT) {
      S.feedRoi.unshift(e);
      if (S.feedRoi.length > MAX_FEED) S.feedRoi.pop();
    }
    renderFeeds();
  }

  function swingEntry(t, fromV, toV, srcLabel) {
    var meta = S.idx.get(t) || { market_ticker: t, title: t };
    var d = toV - fromV;
    var m = modelScore(t);
    var dir = d > 0 ? "▲" : "▼";
    var cls = d > 0 ? "up" : "down";
    var vol = (S.quote.get(t) || {}).volume_fp;
    var html =
      '<div class="chatmsg ' + cls + '">' +
      '<div class="chatmeta"><span class="pill ' + esc(meta.topic || "") + '">' + esc(meta.topic || "?") + "</span>" +
      ' <b>' + dir + " " + esc(meta.market_title || meta.title || t) + "</b>" +
      ' <span class="muted small">' + esc(t) + "</span></div>" +
      '<div class="chatbody">price <b>$' + num(fromV) + " → $" + num(toV) + "</b> (" +
      (d > 0 ? "+" : "") + "$" + num(d) + ")" +
      ' <span class="pill flag">≥ $0.10</span> · ' + esc(srcLabel) +
      (vol != null ? " · volume " + esc(vol) : "") +
      (m.score >= ROI_CUT ? ' · <span class="pill ok">model ' + num(m.score) + "</span>" : "") +
      "</div>" +
      '<div class="chatlinks">' +
      (meta.market_url ? '<a href="' + esc(meta.market_url) + '" target="_blank" rel="noopener">official API row</a> · ' : "") +
      '<a href="#" data-sel="' + esc(t) + '">chart</a> · ' + newsLink(meta) +
      ' · <span class="muted small" title="The API returns price and volume but never a cause">cause: unverified</span>' +
      "</div></div>";
    pushEntry("swing", t, html, m);
  }

  function resolutionEntry(t, result) {
    if (S.announced.get(t)) return;
    S.announced.set(t, result);
    var meta = S.idx.get(t) || { title: t };
    var html =
      '<div class="chatmsg res"><div class="chatmeta"><span class="pill ' + esc(meta.topic || "") + '">' +
      esc(meta.topic || "?") + "</span> <b>RESOLVED " + esc(String(result).toUpperCase()) + "</b> " +
      '<span class="muted small">' + esc(t) + "</span></div>" +
      '<div class="chatbody">' + esc(meta.market_title || meta.title || t) +
      ' settled <b>' + esc(result) + "</b> (official <code>result</code> field) · tracked until resolution ✓</div>" +
      '<div class="chatlinks">' + (meta.market_url ? '<a href="' + esc(meta.market_url) + '" target="_blank" rel="noopener">official API row</a> · ' : "") +
      '<a href="pages/resolutions.html">resolutions page</a></div></div>';
    pushEntry("resolution", t, html, modelScore(t));
  }

  function systemEntry(text) {
    pushEntry("system", null, '<div class="chatmsg sys"><div class="chatbody muted">' + text + "</div></div>", null);
  }

  /* ------------------------------------------------------------ render */
  function renderFeeds() {
    if (S.paused) return; // keep DOM stable while paused
    var topic = S.topicFilter;
    function paint(el, feed) {
      if (!el) return;
      var rows = feed.filter(function (e) { return !topic || (S.idx.get(e.ticker) || {}).topic === topic || e.kind === "system"; });
      el.innerHTML = rows.length
        ? rows.map(function (e) { return e.html; }).join("")
        : '<div class="empty">No alerts yet. The feed fills as swings ≥ $0.10 are observed (15-second polling).</div>';
    }
    paint($("chatAll"), S.feedAll);
    paint($("chatRoi"), S.feedRoi);
    var rc = $("roiCount"); if (rc) rc.textContent = String(S.feedRoi.length);
    var ac = $("allCount"); if (ac) ac.textContent = String(S.feedAll.length);
  }

  function renderModelTable() {
    var el = $("modelTable");
    if (!el) return;
    var rows = Array.from(S.idx.keys()).map(function (t) {
      var m = modelScore(t);
      return { t: t, m: m, meta: S.idx.get(t) || {} };
    }).sort(function (a, b) { return b.m.score - a.m.score; }).slice(0, 10);
    KR.renderTable(el, [
      { label: "Model score", num: true, get: function (r) { return '<b>' + num(r.m.score) + "</b>" + (r.m.score >= ROI_CUT ? ' <span class="pill ok">pick</span>' : ""); } },
      { label: "Topic", get: function (r) { return KR.topicPill(r.meta.topic); } },
      { label: "Market", get: function (r) { return "<b>" + esc(r.meta.market_title || r.meta.title || r.t) + '</b><br><span class="muted small">' + esc(r.t) + "</span>"; } },
      { label: "Liquidity", num: true, get: function (r) { return num(r.m.liq); } },
      { label: "Tightness", num: true, get: function (r) { return num(r.m.tight); } },
      { label: "Price action", num: true, get: function (r) { return num(r.m.act); } },
      { label: "Last $", num: true, get: function (r) { var q = S.quote.get(r.t) || r.meta; return KR.usd(q.last != null ? q.last : q.last_price_dollars, 2); } },
    ], rows, "Waiting for data…");
  }

  function renderTracked() {
    var el = $("trackTable");
    if (!el) return;
    var topic = S.topicFilter;
    var rows = Array.from(S.idx.values()).filter(function (m) {
      return !topic || m.topic === topic;
    });
    KR.renderTable(el, [
      { label: "Topic", get: function (m) { return KR.topicPill(m.topic); } },
      { label: "Market", get: function (m) { return "<b>" + esc(m.market_title || m.title || m.market_ticker) + '</b><br><span class="muted small">' + esc(m.market_ticker) + "</span>"; } },
      { label: "Last $", num: true, get: function (m) { var q = S.quote.get(m.market_ticker) || {}; return KR.usd(q.last != null ? q.last : m.last_price_dollars, 2); } },
      { label: "Yes bid", num: true, get: function (m) { var q = S.quote.get(m.market_ticker) || {}; return KR.usd(q.yes_bid != null ? q.yes_bid : m.yes_bid_dollars, 2); } },
      { label: "Yes ask", num: true, get: function (m) { var q = S.quote.get(m.market_ticker) || {}; return KR.usd(q.yes_ask != null ? q.yes_ask : m.yes_ask_dollars, 2); } },
      { label: "Status", get: function (m) { var q = S.quote.get(m.market_ticker) || {}; var st = q.status || m.status || ""; var res = q.result || m.result || ""; return res ? KR.resultPill(res) : esc(st || "—"); } },
      { label: "Closes", get: function (m) { return '<span class="small">' + KR.when(m.close_time) + "</span>"; } },
      { label: "Source", get: function (m) { return KR.link(m.market_url, "API row"); } },
    ], rows, "No tracked markets in the snapshot yet.");
  }

  /* ------------------------------------------------------------ chart */
  function sessionTicks(t) { return S.ticks.get(t) || []; }

  function drawSelected() {
    var t = S.selected;
    if (!t) return;
    var snap = S.snapshot || {};
    // candles[t] is { "1m": {candles: [...]}, "1h": ..., "1d": ... } (the collector's
    // shape); older code expected a bare array and crashed on .forEach (fixed here by
    // session b7bc848c's render gate). The arrays carry `ts` + `close`, which
    // KR.buildSeries accepts for the "close_dollars" field via its `c.close` fallback.
    var per = (snap.candles || {})[t] || {};
    var candles = Array.isArray(per) ? per
      : (((per["1m"] || per["1h"] || per["1d"] || {}).candles) || []);
    var hist = ((snap.history || {}).points || {})[t] || [];
    var series = KR.buildSeries(candles, hist, "close_dollars");
    var now = Date.now(), cutoff = now - S.win * 1000;
    series = series.filter(function (p) { return p.t >= cutoff; });
    sessionTicks(t).forEach(function (p) { if (p.t >= cutoff) series.push({ t: p.t, v: p.v, src: "tick" }); });
    series.sort(function (a, b) { return a.t - b.t; });
    var jumps = KR.detectJumps(series, SWING);
    KR.drawChart($("chartAlerts"), series, { jumps: jumps, spanSeconds: S.win, emptyMessage: "No price points in this window yet. Short windows fill from live polling; longer windows use collector candlesticks and tick history." });
    var note = $("chartNoteAlerts");
    if (note) note.textContent = series.length + " points · " + jumps.length + " moves ≥ $0.10 (red) · window " + (S.win >= 3600 ? (S.win / 3600) + " h" : (S.win / 60) + " min") + " · sources: candlesticks + tick history + live samples";
  }

  function renderLiquidity() {
    var t = S.selected;
    if (!t) return;
    var snap = S.snapshot || {};
    var ob = (snap.orderbooks || {})[t];
    function table(side, rows, label) {
      return '<h3 class="small">' + label + '</h3><div class="tablewrap"><table><thead><tr><th>Price</th><th class="num">Contracts</th></tr></thead><tbody>' +
        (rows.length ? rows.slice(0, 8).map(function (lv) {
          return '<tr><td>$' + num(lv[0]) + '</td><td class="num">' + num(lv[1], 0) + "</td></tr>";
        }).join("") : '<tr><td colspan="2" class="muted">—</td></tr>') + "</tbody></table></div>";
    }
    function paint(book) {
      if (!book || book.error) {
        $("liqAlerts").innerHTML = '<div class="empty">No order book for this market in the snapshot; live depth loads on selection when the API is reachable.</div>';
        return;
      }
      $("liqAlerts").innerHTML =
        '<div class="kpis"><div class="kpi-card"><div class="k">Best YES bid</div><div class="v">' +
        (book.best_yes_bid != null ? "$" + num(book.best_yes_bid) : "—") + '</div><div class="s">' + num(book.yes_bid_contracts, 0) + " contracts</div></div>" +
        '<div class="kpi-card"><div class="k">Best YES ask (derived)</div><div class="v">' +
        (book.best_yes_ask_derived != null ? "$" + num(book.best_yes_ask_derived) : "—") + '</div><div class="s">' + num(book.derived_ask_contracts, 0) + " contracts</div></div>" +
        '<div class="kpi-card"><div class="k">Spread (derived)</div><div class="v">' +
        (book.spread_derived != null ? "$" + num(book.spread_derived) : "—") + '</div><div class="s">ask − bid</div></div></div>' +
        '<div class="grid" style="grid-template-columns:1fr 1fr;gap:10px">' +
        "<div>" + table("yes", book.yes_bids || [], "YES bids (raw)") + "</div>" +
        "<div>" + table("ask", book.derived_yes_asks || [], "YES asks (derived: 1 − no bid)") + "</div></div>" +
        '<p class="small muted">Raw request: <code>' + esc(book.raw_request || "") + "</code> · the API returns yes/no bids only; ask depth is derived and labelled (docs: get-market-orderbook).</p>";
    }
    if (ob) paint(ob);
    // live refresh (verified shape: {orderbook_fp:{yes_dollars, no_dollars}})
    fetch(API + "/markets/" + encodeURIComponent(t) + "/orderbook?depth=10", { headers: { Accept: "application/json" }, cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var fp = j.orderbook_fp || {};
        var yes = (fp.yes_dollars || []).map(function (lv) { return [Number(lv[0]), Number(lv[1])]; });
        var no = (fp.no_dollars || []).map(function (lv) { return [Number(lv[0]), Number(lv[1])]; });
        yes.sort(function (a, b) { return b[0] - a[0]; });
        var asks = no.map(function (lv) { return [Math.round((1 - lv[0]) * 1e4) / 1e4, lv[1]]; }).sort(function (a, b) { return a[0] - b[0]; });
        paint({
          yes_bids: yes, derived_yes_asks: asks,
          best_yes_bid: yes.length ? yes[0][0] : null,
          best_yes_ask_derived: asks.length ? asks[0][0] : null,
          yes_bid_contracts: yes.reduce(function (s, lv) { return s + lv[1]; }, 0),
          derived_ask_contracts: asks.reduce(function (s, lv) { return s + lv[1]; }, 0),
          spread_derived: (yes.length && asks.length) ? Math.round((asks[0][0] - yes[0][0]) * 1e4) / 1e4 : null,
          raw_request: API + "/markets/" + t + "/orderbook?depth=10",
        });
      })
      .catch(function () { /* keep the snapshot copy; silently degraded is documented */ });
  }

  function selectMarket(t) {
    S.selected = t;
    var sel = $("mktSelAlerts");
    if (sel && sel.value !== t) sel.value = t;
    drawSelected();
    renderLiquidity();
  }

  /* ------------------------------------------------------------ polling */
  function notePrice(t, fields) {
    // quote-swing detection between consecutive observations
    var prev = S.quote.get(t) || {};
    var nv = fields.last != null ? fields.last : prev.last;
    if (prev.last != null && nv != null && Math.abs(Number(nv) - Number(prev.last)) + 1e-9 >= SWING) {
      S.swings.set(t, (S.swings.get(t) || 0) + 1);
      swingEntry(t, Number(prev.last), Number(nv), "quote change (Get Markets)");
    }
    S.quote.set(t, Object.assign({}, prev, fields));
    var ticks = S.ticks.get(t) || [];
    if (nv != null) {
      ticks.push({ t: Date.now(), v: Number(nv) });
      if (ticks.length > SESSION_TICK_CAP) ticks.shift();
      S.ticks.set(t, ticks);
    }
  }

  function handleTape(trades) {
    trades.forEach(function (tr) {
      var t = tr.ticker;
      if (!S.idx.has(t)) return;               // in-scope tracked universe only
      var px = Number(tr.yes_price_dollars);
      if (!isFinite(px)) return;
      var prev = S.tapeLast.get(t);
      S.tapeLast.set(t, px);
      if (prev != null && Math.abs(px - prev) + 1e-9 >= SWING) {
        S.swings.set(t, (S.swings.get(t) || 0) + 1);
        swingEntry(t, prev, px, "trade print " + esc(tr.count_fp) + " contracts @ " + esc(tr.created_time));
      }
      var ticks = S.ticks.get(t) || [];
      var ts = Date.parse(tr.created_time);
      if (isFinite(ts)) {
        ticks.push({ t: ts, v: px });
        ticks.sort(function (a, b) { return a.t - b.t; });
        if (ticks.length > SESSION_TICK_CAP) ticks.shift();
        S.ticks.set(t, ticks);
      }
      if (S.selected === t) drawSelected();
    });
  }

  function getJSON(url) {
    return fetch(url, { headers: { Accept: "application/json" }, cache: "no-store" }).then(function (r) {
      if (r.status === 429) { var e = new Error("rate limited (HTTP 429)"); e.rate = true; throw e; }
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      return r.json();
    });
  }

  function poll() {
    if (S.paused || Date.now() < S.backoffUntil) return;
    var jobs = [];
    // 1. trade tape since the last cursor (first call: latest batch = replay only)
    var tapeUrl = API + "/markets/trades?limit=1000" + (S.minTs ? "&min_ts=" + S.minTs : "");
    jobs.push(getJSON(tapeUrl).then(function (j) {
      var trades = j.trades || [];
      var first = S.minTs == null;
      trades.forEach(function (tr) {
        var ts = Math.floor(Date.parse(tr.created_time) / 1000);
        if (isFinite(ts) && (S.minTs == null || ts > S.minTs)) S.minTs = ts;
      });
      if (first) {
        // seed last-print prices without alerting; the chat starts from live movement
        trades.forEach(function (tr) {
          if (S.idx.has(tr.ticker)) S.tapeLast.set(tr.ticker, Number(tr.yes_price_dollars));
        });
        systemEntry("Live feed connected. Watching " + S.idx.size + " in-scope markets; initial trade tape (" +
          trades.length + " prints) seeded without alerts — swings ≥ $0.10 from now on are posted live.");
      } else {
        handleTape(trades.slice().sort(function (a, b) { return String(a.created_time).localeCompare(String(b.created_time)); }));
      }
    }).catch(function (e) { throw { src: "trades", e: e }; }));
    // 2. current quotes (one page; tracked markets are the largest, they are on page 1-2)
    jobs.push(getJSON(API + "/markets?status=open&limit=1000").then(function (j) {
      var seen = 0;
      (j.markets || []).forEach(function (m) {
        if (!S.idx.has(m.ticker)) return;
        seen++;
        notePrice(m.ticker, {
          last: m.last_price_dollars != null ? Number(m.last_price_dollars) : null,
          yes_bid: m.yes_bid_dollars != null ? Number(m.yes_bid_dollars) : null,
          yes_ask: m.yes_ask_dollars != null ? Number(m.yes_ask_dollars) : null,
          volume_fp: m.volume_fp, open_interest_fp: m.open_interest_fp,
          status: m.status, result: m.result || "",
        });
        if (m.result === "yes" || m.result === "no") resolutionEntry(m.ticker, m.result);
      });
      var st = $("fetchStatus");
      if (st) st.textContent = "last poll " + new Date().toLocaleTimeString() + " · " + seen + "/" + S.idx.size + " tracked markets on page 1";
    }).catch(function (e) { throw { src: "markets", e: e }; }));

    Promise.all(jobs.map(function (p) { return p.catch(function (err) { return err; }); })).then(function (res) {
      var fails = res.filter(function (r) { return r && r.e; });
      S.fails = fails.length;
      if (fails.length) {
        fails.forEach(function (f) {
          if (f.e && f.e.rate) {
            S.backoffUntil = Date.now() + 60000;
            systemEntry("Rate limited (HTTP 429) on <code>" + esc(f.src) + "</code> — backing off 60 s (docs: getting_started/rate_limits).");
          }
        });
        var st = $("fetchStatus");
        if (st && fails.length) st.textContent = "last poll failed (" + fails.map(function (f) { return f.src + ": " + (f.e && f.e.message); }).join("; ") + ") — retrying every 15 s; snapshot fallback shown";
      }
      renderModelTable();
      renderTracked();
      if (S.selected) drawSelected();
    });
  }

  /* ------------------------------------------------------------ init */
  function initControls() {
    var seg = $("winSegAlerts");
    if (seg) seg.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-w]");
      if (!b) return;
      S.win = Number(b.getAttribute("data-w"));
      Array.prototype.forEach.call(seg.querySelectorAll("button"), function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      drawSelected();
    });
    var tf = $("topicFilterAlerts");
    if (tf) tf.addEventListener("change", function () { S.topicFilter = tf.value; renderFeeds(); renderTracked(); });
    var bp = $("btnPause");
    if (bp) bp.addEventListener("click", function () {
      S.paused = !S.paused;
      bp.textContent = S.paused ? "Resume live feed" : "Pause live feed";
      if (!S.paused) { renderFeeds(); poll(); }
    });
    var bc = $("btnClear");
    if (bc) bc.addEventListener("click", function () {
      S.feedAll = []; S.feedRoi = []; renderFeeds();
      systemEntry("Feeds cleared. Watching continues.");
    });
    var sel = $("mktSelAlerts");
    if (sel) sel.addEventListener("change", function () { selectMarket(sel.value); });
    document.addEventListener("click", function (ev) {
      var a = ev.target.closest("a[data-sel]");
      if (a) { ev.preventDefault(); selectMarket(a.getAttribute("data-sel")); }
    });
  }

  (async function start() {
    initControls();
    try {
      var snap = await KR.snapshot();
      S.snapshot = snap;
      try { S.snapshot.history = await KR.history(); } catch (e) { S.snapshot.history = { points: {} }; }
      KR.staleness($("stalenessAlerts"), snap.generated_at_utc);
      // tracked universe: top TRACK_PER_TOPIC per topic by estimated dollar volume
      var rows = (snap.markets || []).slice();
      var byTopic = {};
      rows.forEach(function (m) {
        var t = m.topic || "unmapped";
        (byTopic[t] = byTopic[t] || []).push(m);
      });
      Object.keys(byTopic).forEach(function (t) {
        byTopic[t].sort(function (a, b) { return (b.est_dollar_volume || -1) - (a.est_dollar_volume || -1); });
        byTopic[t].slice(0, TRACK_PER_TOPIC).forEach(function (m) {
          var tk = m.market_ticker;
          S.idx.set(tk, {
            market_ticker: tk, market_title: m.market_title || m.title || tk,
            title: m.market_title || m.title || tk,
            topic: m.topic, series_ticker: m.series_ticker, event_ticker: m.event_ticker,
            market_url: m.market_url, close_time: m.close_time,
            last_price_dollars: m.last_price_dollars, yes_bid_dollars: m.yes_bid_dollars,
            yes_ask_dollars: m.yes_ask_dollars, volume_fp: m.volume_fp,
          });
          notePrice(tk, {
            last: m.last_price_dollars != null ? Number(m.last_price_dollars) : null,
            yes_bid: m.yes_bid_dollars != null ? Number(m.yes_bid_dollars) : null,
            yes_ask: m.yes_ask_dollars != null ? Number(m.yes_ask_dollars) : null,
            volume_fp: m.volume_fp, open_interest_fp: m.open_interest_fp,
            status: m.status, result: m.result || "",
          });
          if (m.result === "yes" || m.result === "no") S.announced.set(tk, m.result);
        });
      });
      var sel = $("mktSelAlerts");
      if (sel) {
        sel.innerHTML = Array.from(S.idx.values()).map(function (m) {
          return '<option value="' + esc(m.market_ticker) + '">[' + esc(m.topic) + "] " + esc((m.market_title || m.market_ticker).slice(0, 70)) + "</option>";
        }).join("");
      }
      var first = Array.from(S.idx.keys()).sort(function (a, b) {
        return ((S.idx.get(b) || {}).est_dollar_volume || 0) - ((S.idx.get(a) || {}).est_dollar_volume || 0);
      })[0];
      if (first) selectMarket(first);
      var wc = $("watchedCount");
      if (wc) wc.textContent = String(S.idx.size);
      systemEntry("Model: score = 0.40·liquidity + 0.30·tightness + 0.30·price action, cutoff " + ROI_CUT +
        ". A transparent heuristic over official fields — <b>not</b> financial advice and <b>not</b> an outcome prediction.");
      renderModelTable();
      renderTracked();
    } catch (e) {
      var el = $("chatAll");
      if (el) el.innerHTML = '<div class="notice bad">Snapshot could not be loaded: ' + esc(e.message) +
        ". The page falls back to data/snapshot.json committed by .github/workflows/refresh-data.yml. No values are invented.</div>";
    }
    poll();
    setInterval(poll, POLL_MS);
  })();
})();
