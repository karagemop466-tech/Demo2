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
 *   GET /markets?tickers=<t1,t2,...>                 — exact watched quotes + result (get-markets docs)
 *   GET /markets/{ticker}/orderbook?depth=10         — liquidity on selection (get-market-orderbook docs)
 *   GET /series/{s}/markets/{t}/candlesticks         — live chart fallback (get-market-candlesticks docs)
 * plus the committed data/snapshot.json + data/history.json as the labelled fallback.
 *
 * Detection rule (user requirement): |change in contract price| >= $0.10 between
 * two consecutive observations (rounded to 4 decimal places so IEEE-754 float drift
 * like 0.60 - 0.50 = 0.09999999999999998 never misses an exact $0.10 move), either direction.
 *
 * The cause of a swing is NOT derivable from the API. Each alert links to the
 * market API row, any official settlement_sources listed on the event, and offers
 * a news SEARCH link labelled "possible context (unverified)" — it asserts nothing (F13).
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
  var SWING_TENTHS_BP = 1000;  // 0.1000 * 10000 to avoid float drift
  var POLL_MS = 15000;         // same cadence as the Live Console; 429 => backoff
  var TRACK_PER_TOPIC = 12;    // highest est. dollar volume, per topic
  var TICKER_BATCH_SIZE = 40;  // safe URL length per GET /markets?tickers=...
  var MAX_FEED = 300;          // entries kept per chat
  var ROI_CUT = 0.60;
  var SESSION_TICK_CAP = 400;

  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>\"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };
  var num = function (v, d) { var n = Number(v); return isFinite(n) ? n.toFixed(d == null ? 2 : d) : "—"; };
  var clamp = function (v, lo, hi) { return Math.max(lo, Math.min(hi, v)); };

  function isSwing(fromVal, toVal, threshold) {
    if (fromVal == null || fromVal === "" || toVal == null || toVal === "") return false;
    var a = Number(fromVal), b = Number(toVal);
    if (!isFinite(a) || !isFinite(b)) return false;
    var thr = threshold == null ? SWING : Number(threshold);
    var diffBp = Math.round(Math.abs(b - a) * 10000);
    var thrBp = Math.round(thr * 10000);
    return diffBp >= (isFinite(thrBp) ? thrBp : SWING_TENTHS_BP);
  }

  function batchTickers(tickers, size) {
    var n = size || TICKER_BATCH_SIZE;
    var out = [];
    for (var i = 0; i < tickers.length; i += n) out.push(tickers.slice(i, i + n));
    return out;
  }

  function parseOrderbookFp(fp) {
    fp = fp || {};
    var yes = (fp.yes_dollars || []).map(function (lv) { return [Number(lv[0]), Number(lv[1])]; });
    var no = (fp.no_dollars || []).map(function (lv) { return [Number(lv[0]), Number(lv[1])]; });
    yes.sort(function (a, b) { return b[0] - a[0]; });
    var asks = no.map(function (lv) { return [Math.round((1 - lv[0]) * 1e4) / 1e4, lv[1]]; }).sort(function (a, b) { return a[0] - b[0]; });
    return {
      yes_bids: yes,
      derived_yes_asks: asks,
      best_yes_bid: yes.length ? yes[0][0] : null,
      best_yes_ask_derived: asks.length ? asks[0][0] : null,
      yes_bid_contracts: yes.reduce(function (s, lv) { return s + lv[1]; }, 0),
      derived_ask_contracts: asks.reduce(function (s, lv) { return s + lv[1]; }, 0),
      spread_derived: (yes.length && asks.length) ? Math.round((asks[0][0] - yes[0][0]) * 1e4) / 1e4 : null,
    };
  }

  var S = {
    idx: new Map(),          // ticker -> meta {topic,title,series_ticker,event_ticker,market_url,close_time,settlement_sources,...}
    quote: new Map(),        // ticker -> last observed {last,yes_bid,yes_ask,volume_fp,open_interest_fp,status,result}
    tapeLast: new Map(),     // ticker -> last print price observed
    swings: new Map(),       // ticker -> session swing count
    ticks: new Map(),        // ticker -> [{t,v}] session samples for the chart
    liveCandles: new Map(),  // ticker:interval -> {fetchedAt, candles:[...]}
    candleInflight: new Set(),
    seenAlerts: new Set(),   // dedup key for seeded / previous_price alerts
    prevChecked: new Set(),  // tickers whose previous_price_dollars was already checked
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

  function settlementLinks(meta) {
    var list = Array.isArray(meta.settlement_sources) ? meta.settlement_sources : [];
    var links = [];
    list.forEach(function (src) {
      if (src && src.url && /^https?:\/\//i.test(src.url) && links.length < 2) {
        links.push('<a href="' + esc(src.url) + '" target="_blank" rel="noopener" ' +
          'title="Official settlement source named on this series record">' +
          esc(src.name || "settlement source") + "</a>");
      }
    });
    return links.length ? " · official source: " + links.join(", ") : "";
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

  function swingEntry(t, fromV, toV, srcLabel, dedupKey) {
    if (dedupKey) {
      if (S.seenAlerts.has(dedupKey)) return;
      S.seenAlerts.add(dedupKey);
    }
    var meta = S.idx.get(t) || { market_ticker: t, title: t };
    var d = toV - fromV;
    var m = modelScore(t);
    var dir = d > 0 ? "▲" : "▼";
    var cls = d > 0 ? "up" : "down";
    var vol = (S.quote.get(t) || meta).volume_fp;
    var html =
      '<div class="chatmsg ' + cls + '">' +
      '<div class="chatmeta"><span class="pill ' + esc(meta.topic || "") + '">' + esc(meta.topic || "?") + "</span>" +
      ' <b>' + dir + " " + esc(meta.market_title || meta.title || t) + "</b>" +
      ' <span class="muted small">' + esc(t) + "</span></div>" +
      '<div class="chatbody">price <b>$' + num(fromV, 4) + " → $" + num(toV, 4) + "</b> (" +
      (d > 0 ? "+" : "") + "$" + num(d, 4) + ")" +
      ' <span class="pill flag">≥ $0.10</span> · ' + esc(srcLabel) +
      (vol != null ? " · volume " + esc(vol) : "") +
      (m.score >= ROI_CUT ? ' · <span class="pill ok">model ' + num(m.score) + "</span>" : "") +
      "</div>" +
      '<div class="chatlinks">' +
      (meta.market_url ? '<a href="' + esc(meta.market_url) + '" target="_blank" rel="noopener">official API row</a> · ' : "") +
      '<a href="#" data-sel="' + esc(t) + '">chart</a> · ' + newsLink(meta) +
      settlementLinks(meta) +
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
      '<a href="pages/resolutions.html">resolutions page</a>' + settlementLinks(meta) + "</div></div>";
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

  function intervalForWindow(winSec) {
    if (winSec <= 3600) return { key: "1m", minutes: 1, span: Math.max(winSec, 6 * 3600) };
    if (winSec <= 86400) return { key: "1h", minutes: 60, span: 20 * 86400 };
    return { key: "1d", minutes: 1440, span: 120 * 86400 };
  }

  function normalizeApiCandles(arr) {
    return (arr || []).map(function (c) {
      var p = c.price || {};
      var yb = (c.yes_bid || {}).close_dollars;
      var ya = (c.yes_ask || {}).close_dollars;
      var mid = (yb != null && yb !== "" && ya != null && ya !== "")
        ? Math.round(((Number(yb) + Number(ya)) / 2) * 10000) / 10000
        : null;
      return {
        ts: c.end_period_ts,
        close_dollars: p.close_dollars,
        yes_bid_close: yb,
        yes_ask_close: ya,
        derived_mid: mid,
      };
    });
  }

  function ensureLiveCandles(t, winSec) {
    var meta = S.idx.get(t);
    if (!meta || !meta.series_ticker) return;
    var iv = intervalForWindow(winSec);
    var cacheKey = t + ":" + iv.key;
    var cached = S.liveCandles.get(cacheKey);
    if (cached && (Date.now() - cached.fetchedAt) < 60000) return;
    if (S.candleInflight.has(cacheKey) || Date.now() < S.backoffUntil) return;
    S.candleInflight.add(cacheKey);
    var nowS = Math.floor(Date.now() / 1000);
    var startS = nowS - iv.span;
    var url = API + "/series/" + encodeURIComponent(meta.series_ticker) +
      "/markets/" + encodeURIComponent(t) +
      "/candlesticks?start_ts=" + startS + "&end_ts=" + nowS + "&period_interval=" + iv.minutes;
    getJSON(url).then(function (j) {
      S.liveCandles.set(cacheKey, { fetchedAt: Date.now(), candles: normalizeApiCandles(j.candlesticks) });
      if (S.selected === t) drawSelected();
    }).catch(function () {
      S.liveCandles.set(cacheKey, { fetchedAt: Date.now(), candles: [] });
    }).finally(function () {
      S.candleInflight.delete(cacheKey);
    });
  }

  function drawSelected() {
    var t = S.selected;
    if (!t) return;
    var snap = S.snapshot || {};
    var iv = intervalForWindow(S.win);
    var per = (snap.candles || {})[t] || {};
    var snapCandles = Array.isArray(per) ? per
      : (((per[iv.key] || per["1m"] || per["1h"] || per["1d"] || {}).candles) || []);
    var liveEntry = S.liveCandles.get(t + ":" + iv.key);
    var candles = (liveEntry && liveEntry.candles && liveEntry.candles.length)
      ? liveEntry.candles
      : snapCandles.map(function (c) {
          return {
            ts: c.ts,
            close_dollars: c.close != null ? c.close : c.close_dollars,
            yes_bid_close: c.yes_bid_close,
            yes_ask_close: c.yes_ask_close,
            derived_mid: c.derived_mid,
          };
        });
    if ((!snapCandles || !snapCandles.length) && (!liveEntry || (Date.now() - liveEntry.fetchedAt) >= 60000)) {
      ensureLiveCandles(t, S.win);
    }
    var hist = ((snap.history || {}).points || {})[t] || [];
    // Use traded close when present; fall back to derived_mid in quiet periods.
    var hasTrades = candles.some(function (c) { return c.close_dollars != null && c.close_dollars !== ""; });
    var field = hasTrades ? "close_dollars" : "derived_mid";
    var series = KR.buildSeries(candles, hist, field);
    var now = Date.now(), cutoff = now - S.win * 1000;
    series = series.filter(function (p) { return p.t >= cutoff; });
    sessionTicks(t).forEach(function (p) { if (p.t >= cutoff) series.push({ t: p.t, v: p.v, src: "tick" }); });
    series.sort(function (a, b) { return a.t - b.t; });
    var jumps = KR.detectJumps(series, SWING);
    KR.drawChart($("chartAlerts"), series, {
      jumps: jumps,
      spanSeconds: S.win,
      emptyMessage: "Loading live candlesticks / waiting for samples in this window. Short windows fill from 15 s polling; longer windows use candlesticks and tick history."
    });
    var note = $("chartNoteAlerts");
    var srcText = (liveEntry && liveEntry.candles && liveEntry.candles.length)
      ? "live candlesticks + tick history + live samples"
      : "candlesticks + tick history + live samples";
    if (note) note.textContent = series.length + " points · " + jumps.length + " moves ≥ $0.10 (red) · window " +
      (S.win >= 3600 ? (S.win / 3600) + " h" : (S.win / 60) + " min") + " · " +
      (hasTrades ? "traded price" : "quoted mid (derived)") + " · " + srcText;
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
      var liqEl = $("liqAlerts");
      if (!liqEl) return;
      if (!book || book.error) {
        liqEl.innerHTML = '<div class="empty">No order book for this market in the snapshot; live depth loads on selection when the API is reachable.</div>';
        return;
      }
      liqEl.innerHTML =
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
        var parsed = parseOrderbookFp(j.orderbook_fp);
        parsed.raw_request = API + "/markets/" + t + "/orderbook?depth=10";
        paint(parsed);
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
    if (prev.last != null && nv != null && isSwing(prev.last, nv)) {
      S.swings.set(t, (S.swings.get(t) || 0) + 1);
      swingEntry(t, Number(prev.last), Number(nv), "quote change (Get Markets)");
    }
    // Check official previous_price_dollars vs last_price_dollars once per ticker on initial live quote
    if (fields.previous_price != null && nv != null && !S.prevChecked.has(t)) {
      S.prevChecked.add(t);
      if (isSwing(fields.previous_price, nv)) {
        S.swings.set(t, (S.swings.get(t) || 0) + 1);
        swingEntry(t, Number(fields.previous_price), Number(nv),
          "previous_price_dollars move (Get Markets)",
          "prev:" + t + ":" + fields.previous_price + "->" + nv);
      }
    }
    S.quote.set(t, Object.assign({}, prev, fields));
    var ticks = S.ticks.get(t) || [];
    if (nv != null) {
      ticks.push({ t: Date.now(), v: Number(nv) });
      if (ticks.length > SESSION_TICK_CAP) ticks.shift();
      S.ticks.set(t, ticks);
    }
  }

  function seedFromSnapshotHistory(snap) {
    var pts = ((snap.history || {}).points) || {};
    var seeded = [];
    S.idx.forEach(function (_, t) {
      var arr = pts[t] || [];
      for (var i = 1; i < arr.length; i++) {
        var a = Number(arr[i - 1].last), b = Number(arr[i].last);
        if (isSwing(a, b)) {
          seeded.push({
            t: t, fromV: a, toV: b, ts: arr[i].t || 0,
            key: "hist:" + t + ":" + (arr[i].t || i) + ":" + a + "->" + b,
          });
        }
      }
      var per = (snap.candles || {})[t] || {};
      var c1m = (per["1m"] || {}).candles || [];
      for (var j = 1; j < c1m.length; j++) {
        var ca = c1m[j - 1].close != null ? c1m[j - 1].close : c1m[j - 1].derived_mid;
        var cb = c1m[j].close != null ? c1m[j].close : c1m[j].derived_mid;
        if (ca != null && cb != null && isSwing(ca, cb)) {
          seeded.push({
            t: t, fromV: Number(ca), toV: Number(cb), ts: c1m[j].ts || 0,
            key: "candle:" + t + ":" + (c1m[j].ts || j) + ":" + ca + "->" + cb,
          });
        }
      }
    });
    seeded.sort(function (a, b) { return a.ts - b.ts; });
    seeded.slice(-20).forEach(function (item) {
      S.swings.set(item.t, (S.swings.get(item.t) || 0) + 1);
      var whenStr = item.ts ? new Date(item.ts * 1000).toISOString().slice(11, 19) + "Z" : "snapshot";
      swingEntry(item.t, item.fromV, item.toV, "snapshot history (" + whenStr + ")", item.key);
    });
  }

  function handleTape(trades) {
    trades.forEach(function (tr) {
      var t = tr.ticker;
      if (!S.idx.has(t)) return;               // in-scope tracked universe only
      var px = Number(tr.yes_price_dollars);
      if (!isFinite(px)) return;
      var prev = S.tapeLast.get(t);
      S.tapeLast.set(t, px);
      if (prev != null && isSwing(prev, px)) {
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
          trades.length + " prints) seeded — live swings ≥ $0.10 and settlements post in real time.");
      } else {
        handleTape(trades.slice().sort(function (a, b) { return String(a.created_time).localeCompare(String(b.created_time)); }));
      }
    }).catch(function (e) { throw { src: "trades", e: e }; }));

    // 2. exact watched markets via GET /markets?tickers=... (official Get Markets docs:
    //    when `tickers` is the only filter, every matching market is returned in one
    //    response regardless of status, so BOTH live quotes AND yes/no settlements arrive).
    var batches = batchTickers(Array.from(S.idx.keys()), TICKER_BATCH_SIZE);
    var seenTickers = new Set();
    var quotesJob = Promise.all(batches.map(function (batch) {
      var qUrl = API + "/markets?tickers=" + encodeURIComponent(batch.join(","));
      return getJSON(qUrl).then(function (j) {
        (j.markets || []).forEach(function (m) {
          if (!S.idx.has(m.ticker)) return;
          seenTickers.add(m.ticker);
          notePrice(m.ticker, {
            last: m.last_price_dollars != null ? Number(m.last_price_dollars) : null,
            previous_price: m.previous_price_dollars != null ? Number(m.previous_price_dollars) : null,
            yes_bid: m.yes_bid_dollars != null ? Number(m.yes_bid_dollars) : null,
            yes_ask: m.yes_ask_dollars != null ? Number(m.yes_ask_dollars) : null,
            volume_fp: m.volume_fp, open_interest_fp: m.open_interest_fp,
            status: m.status, result: m.result || "",
          });
          if (m.result === "yes" || m.result === "no") resolutionEntry(m.ticker, m.result);
        });
      });
    })).then(function () {
      var st = $("fetchStatus");
      if (st) st.textContent = "last poll " + new Date().toLocaleTimeString() + " · " + seenTickers.size + "/" + S.idx.size + " tracked markets updated";
    }).catch(function (e) { throw { src: "markets", e: e }; });
    jobs.push(quotesJob);

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

  /* Expose deterministic helpers for offline tests */
  if (typeof window !== "undefined") {
    window.__ALERTS_INTERNALS = {
      isSwing: isSwing,
      batchTickers: batchTickers,
      parseOrderbookFp: parseOrderbookFp,
      modelScore: modelScore,
      handleTape: handleTape,
      notePrice: notePrice,
      resolutionEntry: resolutionEntry,
      seedFromSnapshotHistory: seedFromSnapshotHistory,
      state: S,
    };
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
            est_dollar_volume: m.est_dollar_volume,
            settlement_sources: m.settlement_sources || [],
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
      seedFromSnapshotHistory(snap);
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
