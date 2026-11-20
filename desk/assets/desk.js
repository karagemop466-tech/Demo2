/* desk.js — live interactivity for the consolidated Kalshi demo desk.
 *
 * Everything here talks to the PUBLIC, unauthenticated Kalshi demo Trade API
 * from the visitor's browser. No credential is ever requested, entered or stored.
 * Endpoints used (all documented on docs.kalshi.com):
 *   GET /markets/{ticker}                                      -> current quote
 *   GET /markets/{ticker}/orderbook                            -> depth ladder
 *   GET /markets/trades?ticker={ticker}&limit=N                -> trade prints
 *   GET /series/{series}/markets/{ticker}/candlesticks?period_interval=..&start_ts=..&end_ts=..
 *
 * If the browser cannot reach the API (offline, blocked, CORS failure) the
 * panel shows the error and the bundled snapshot values. It never invents a price.
 */
(function () {
  "use strict";

  var API = "https://external-api.demo.kalshi.co/trade-api/v2";
  var DOCS = {
    markets: "https://docs.kalshi.com/api-reference/market/get-markets",
    market: "https://docs.kalshi.com/api-reference/market/get-market",
    orderbook: "https://docs.kalshi.com/api-reference/market/get-market-orderbook",
    trades: "https://docs.kalshi.com/api-reference/market/get-trades",
    candles: "https://docs.kalshi.com/api-reference/market/get-market-candlesticks",
    settlement: "https://docs.kalshi.com/getting_started/market_settlement",
    demo: "https://docs.kalshi.com/getting_started/demo_env"
  };

  var script = document.currentScript;
  var ASSET_BASE = script ? new URL(".", script.src).href : "./";
  var DATA_BASE = new URL("../data/", ASSET_BASE).href;

  /* ------------------------------------------------------------- helpers */
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s === undefined || s === null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function num(v) {
    if (v === undefined || v === null || v === "") return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }
  function price(v) {
    var n = num(v);
    return n === null ? "—" : n.toFixed(4);
  }
  function money(v) {
    var n = num(v);
    if (n === null) return "—";
    return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function int(v) {
    var n = num(v);
    if (n === null) return "—";
    return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
  }
  function ts(epoch, withDate) {
    if (!epoch) return "—";
    var d = new Date(epoch * 1000);
    if (isNaN(d.getTime())) return "—";
    var t = d.toISOString().replace("T", " ").slice(0, 19) + "Z";
    if (withDate === false) return t.slice(11);
    return t;
  }
  function srcLink(url, label) {
    if (!url) return '<span class="pill unverified">no source</span>';
    return '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(label || "source") + "</a>";
  }

  function getJSON(url, timeoutMs) {
    var ctl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, timeoutMs || 9000);
    return fetch(url, { headers: { Accept: "application/json" }, signal: ctl ? ctl.signal : undefined })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status + " from " + url.replace(API, ""));
        return r.json();
      })
      .finally(function () { clearTimeout(timer); });
  }

  /* ---------------------------------------------------------------- state */
  var S = {
    markets: [],
    market: null,
    window: 3600,
    points: [],
    jumps: [],
    live: false,
    timer: null
  };

  var WINDOWS = [
    { id: 60, label: "60 s", span: 60, src: "trades" },
    { id: 300, label: "5 min", span: 300, src: "candles", period: 1 },
    { id: 900, label: "15 min", span: 900, src: "candles", period: 1 },
    { id: 3600, label: "1 h", span: 3600, src: "candles", period: 1 },
    { id: 21600, label: "6 h", span: 21600, src: "candles", period: 60 },
    { id: 86400, label: "24 h", span: 86400, src: "candles", period: 60 },
    { id: 604800, label: "7 d", span: 604800, src: "candles", period: 1440 },
    { id: 2592000, label: "30 d", span: 2592000, src: "candles", period: 1440 }
  ];

  /* ------------------------------------------------------------- loading */
  function loadMarkets() {
    return getJSON(DATA_BASE + "summary.json", 12000).then(function (j) {
      S.markets = (j && j.markets) || [];
      var sel = $("mktSel");
      if (!sel) return;
      if (!S.markets.length) {
        sel.innerHTML = '<option value="">no markets in the bundled snapshot</option>';
        return;
      }
      var groups = {};
      S.markets.forEach(function (m) {
        (groups[m.topic || "other"] = groups[m.topic || "other"] || []).push(m);
      });
      var html = "";
      Object.keys(groups).sort().forEach(function (topic) {
        html += '<optgroup label="' + esc(topic) + '">';
        groups[topic].forEach(function (m) {
          html += '<option value="' + esc(m.ticker) + '">' +
            esc(m.ticker) + " — " + esc((m.title || "").slice(0, 78)) + "</option>";
        });
        html += "</optgroup>";
      });
      sel.innerHTML = html;
      var want = sel.getAttribute("data-default") || (S.markets[0] && S.markets[0].ticker);
      if (want) sel.value = want;
      selectMarket(sel.value);
    });
  }

  function currentMarket() {
    var ticker = ($("mktSel") && $("mktSel").value) || "";
    for (var i = 0; i < S.markets.length; i++) {
      if (S.markets[i].ticker === ticker) return S.markets[i];
    }
    return null;
  }

  function selectMarket(ticker) {
    S.market = null;
    for (var i = 0; i < S.markets.length; i++) {
      if (S.markets[i].ticker === ticker) { S.market = S.markets[i]; break; }
    }
    if (!S.market) return;
    var m = S.market;
    if ($("liveTicker")) $("liveTicker").textContent = m.ticker;
    if ($("liveTitle")) $("liveTitle").textContent = m.title || "";
    if ($("liveSource")) {
      $("liveSource").innerHTML = srcLink(m.source_url, "official market endpoint");
    }
    if ($("liveSeries")) {
      $("liveSeries").innerHTML = m.series_ticker
        ? srcLink(API + "/series/" + encodeURIComponent(m.series_ticker), "official series endpoint")
        : '<span class="pill unverified">no series</span>';
    }
    renderQuote(m);
    loadSeries();
    loadDepth();
  }

  /* ------------------------------------------------------- live quote */
  function renderQuote(m) {
    var px = num(m.last_price_dollars);
    var bid = num(m.yes_bid_dollars);
    var ask = num(m.yes_ask_dollars);
    if ($("qPrice")) $("qPrice").textContent = price(px);
    if ($("qBid")) $("qBid").textContent = price(bid);
    if ($("qAsk")) $("qAsk").textContent = price(ask);
    if ($("qSpread")) {
      if (bid !== null && ask !== null) $("qSpread").textContent = price(ask - bid);
      else $("qSpread").textContent = "—";
    }
    if ($("qVolume")) $("qVolume").textContent = int(m.volume_24h_fp);
    if ($("qOi")) $("qOi").textContent = int(m.open_interest_fp);
    if ($("qClose")) $("qClose").textContent = m.close_time || "—";
  }

  function pollQuote() {
    if (!S.market) return;
    getJSON(API + "/markets/" + encodeURIComponent(S.market.ticker), 8000).then(function (j) {
      var mk = (j && j.market) || j || {};
      var px = num(mk.last_price_dollars);
      S.live = true;
      setBadge("live", "LIVE");
      if (px !== null) {
        S.market.last_price_dollars = mk.last_price_dollars;
        renderQuote(S.market);
      }
      if ($("liveTick")) {
        $("liveTick").textContent = "last quote " + new Date().toISOString().slice(11, 19) + "Z";
      }
    }).catch(function () {
      setBadge("err", "OFFLINE");
      if ($("liveTick")) $("liveTick").textContent = "last quote unavailable — bundled snapshot shown";
    });
  }

  function setBadge(kind, text) {
    var el = $("liveBadge");
    if (!el) return;
    el.className = "badge " + kind;
    el.textContent = text;
  }

  /* ------------------------------------------------------------- series */
  function loadSeries() {
    if (!S.market) return;
    var m = S.market;
    var w = WINDOWS.filter(function (x) { return x.id === S.window; })[0] || WINDOWS[3];
    var now = Math.floor(Date.now() / 1000);
    var start = now - w.span;
    var note = $("chartNote");
    if (note) note.innerHTML = '<span class="spin"></span> loading ' + esc(w.label) + " of price history";

    if (w.src === "trades") {
      getJSON(API + "/markets/trades?ticker=" + encodeURIComponent(m.ticker) + "&limit=500", 9000)
        .then(function (j) {
          var rows = (j && j.trades) || [];
          var pts = rows.map(function (t) {
            var p = num(t.yes_price_dollars);
            var when = Date.parse(t.created_time) / 1000;
            return { ts: when, p: p };
          }).filter(function (p) { return p.p !== null && isFinite(p.ts); })
            .filter(function (p) { return p.ts >= start; })
            .sort(function (a, b) { return a.ts - b.ts; });
          setSeries(pts, "GET /markets/trades?ticker=" + encodeURIComponent(m.ticker) + " (trade prints, " + pts.length + " points in window)");
        })
        .catch(function (e) { seriesError(e); });
      return;
    }

    var url = API + "/series/" + encodeURIComponent(m.series_ticker || "") +
      "/markets/" + encodeURIComponent(m.ticker) + "/candlesticks" +
      "?period_interval=" + w.period + "&start_ts=" + start + "&end_ts=" + now;
    getJSON(url, 9000).then(function (j) {
      var bars = (j && j.candlesticks) || [];
      var pts = bars.map(function (b) {
        var p = num((b.price || {}).close_dollars);
        return { ts: b.end_period_ts, p: p };
      }).filter(function (p) { return p.p !== null; });
      setSeries(pts, "GET /series/" + encodeURIComponent(m.series_ticker || "") + "/markets/" +
        encodeURIComponent(m.ticker) + "/candlesticks?period_interval=" + w.period +
        " (" + pts.length + " candles)");
    }).catch(function (e) { seriesError(e); });
  }

  function seriesError(e) {
    S.points = [];
    drawChart();
    var note = $("chartNote");
    if (note) note.innerHTML = "price history unavailable: " + esc((e && e.message) || e);
  }

  function setSeries(pts, srcLabel) {
    S.points = pts;
    S.jumps = detectJumps(pts);
    drawChart();
    var note = $("chartNote");
    if (note) {
      note.innerHTML = esc(srcLabel) +
        " · source: <a href=\"" + esc(DOCS.candles) + "\" target=\"_blank\" rel=\"noopener\">Get Market Candlesticks</a>";
    }
    var jt = $("jumpCount");
    if (jt) {
      jt.textContent = S.jumps.length
        ? S.jumps.length + " move(s) of $0.10 or more in this window"
        : "no move of $0.10 or more in this window";
    }
    var jb = $("jumpBox");
    if (jb) {
      if (!S.jumps.length) {
        jb.innerHTML = '<p class="muted small">No consecutive price points in this window differ by $0.10 or more.</p>';
      } else {
        var rows = S.jumps.map(function (j) {
          return "<tr><td class=\"mono small\">" + ts(j.ts) + "</td>" +
            "<td class=\"num\">" + price(j.from) + " &rarr; " + price(j.to) + "</td>" +
            "<td class=\"num " + (j.delta > 0 ? "up" : "down") + "\">" + (j.delta > 0 ? "+" : "") + j.delta.toFixed(4) + "</td>" +
            "<td>" + srcLink(j.source, "candles") + "</td></tr>";
        }).join("");
        jb.innerHTML = '<div class="tbl-scroll"><table><thead><tr><th>Time (UTC)</th><th class="num">Price</th>' +
          '<th class="num">Change</th><th>Official source</th></tr></thead><tbody>' + rows + "</tbody></table></div>" +
          '<p class="small muted">A jump is a change of $0.10 or more between two consecutive official price points. ' +
          "Kalshi publishes no news feed, so the cause of a move is not verifiable from an official source and is left unstated.</p>";
      }
    }
  }

  function detectJumps(pts) {
    var out = [];
    for (var i = 1; i < pts.length; i++) {
      var d = pts[i].p - pts[i - 1].p;
      if (Math.abs(d) >= 0.1) {
        out.push({
          ts: pts[i].ts,
          from: pts[i - 1].p,
          to: pts[i].p,
          delta: d,
          source: S.market ? (API + "/markets/" + encodeURIComponent(S.market.ticker)) : ""
        });
      }
    }
    return out;
  }

  /* --------------------------------------------------------------- depth */
  function loadDepth() {
    if (!S.market) return;
    var m = S.market;
    if ($("depthMeta")) $("depthMeta").innerHTML = '<span class="spin"></span> loading order book';
    getJSON(API + "/markets/" + encodeURIComponent(m.ticker) + "/orderbook", 9000).then(function (j) {
      var fp = (j && j.orderbook_fp) || {};
      var yes = fp.yes_dollars || [];
      var no = fp.no_dollars || [];
      if ($("depthMeta")) {
        $("depthMeta").innerHTML = "source: " +
          srcLink(API + "/markets/" + encodeURIComponent(m.ticker) + "/orderbook", "official order book") +
          " · <a href=\"" + esc(DOCS.orderbook) + "\" target=\"_blank\" rel=\"noopener\">Get Market Orderbook</a>";
      }
      renderDepth($("depthYes"), yes, "bid");
      // Kalshi returns YES bids and NO bids only. A NO bid at price p is a YES
      // ask at 1 - p, so the ask ladder is derived and labelled as derived.
      var asks = no.map(function (l) { return [1 - Number(l[0]), l[1]]; })
        .sort(function (a, b) { return a[0] - b[0]; });
      renderDepth($("depthAsk"), asks, "ask");
      var ny = yes.reduce(function (a, l) { return a + Number(l[1]); }, 0);
      var nn = no.reduce(function (a, l) { return a + Number(l[1]); }, 0);
      if ($("depthTotals")) {
        $("depthTotals").innerHTML =
          "<span>YES bids resting: <b>" + int(ny) + "</b> contracts</span>" +
          "<span>NO bids resting: <b>" + int(nn) + "</b> contracts</span>" +
          "<span>best YES bid: <b>" + (yes.length ? price(yes[0][0]) : "—") + "</b></span>" +
          "<span>best NO bid: <b>" + (no.length ? price(no[0][0]) : "—") + "</b></span>";
      }
    }).catch(function (e) {
      if ($("depthMeta")) $("depthMeta").innerHTML = "order book unavailable: " + esc((e && e.message) || e);
      if ($("depthYes")) $("depthYes").innerHTML = '<p class="muted small">no order book</p>';
      if ($("depthAsk")) $("depthAsk").innerHTML = '<p class="muted small">no order book</p>';
    });
  }

  function renderDepth(el, levels, side) {
    if (!el) return;
    if (!levels.length) {
      el.innerHTML = '<p class="muted small">no resting ' + (side === "bid" ? "YES bids" : "YES asks") + "</p>";
      return;
    }
    var max = 0;
    levels.forEach(function (l) { max = Math.max(max, Number(l[1])); });
    var html = '<table class="depth"><thead><tr><th class="num">Price</th><th class="num">Contracts</th><th class="num">Cumulative</th></tr></thead><tbody>';
    var cum = 0;
    levels.forEach(function (l) {
      cum += Number(l[1]);
      var w = max > 0 ? (Number(l[1]) / max) * 100 : 0;
      html += '<tr><td class="num">' + price(l[0]) + "</td>" +
        '<td class="num"><div class="depth-wrap"><div class="fill ' + (side === "ask" ? "ask" : "bar") +
        '" style="width:' + w.toFixed(1) + '%"></div><span>' + int(l[1]) + "</span></div></td>" +
        '<td class="num muted">' + int(cum) + "</td></tr>";
    });
    el.innerHTML = html + "</tbody></table>";
  }

  /* --------------------------------------------------------------- chart */
  function drawChart() {
    var c = $("chart");
    if (!c) return;
    var dpr = window.devicePixelRatio || 1;
    var cssW = c.clientWidth || 600;
    var cssH = c.clientHeight || 300;
    c.width = Math.round(cssW * dpr);
    c.height = Math.round(cssH * dpr);
    var g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, cssW, cssH);

    var padL = 46, padR = 12, padT = 12, padB = 26;
    var w = cssW - padL - padR, h = cssH - padT - padB;

    // grid + Y axis (contract price 0.00 - 1.00, fixed)
    g.strokeStyle = "#2a3542"; g.fillStyle = "#8b98a5"; g.lineWidth = 1;
    g.font = "11px system-ui, sans-serif"; g.textAlign = "right"; g.textBaseline = "middle";
    for (var p = 0; p <= 10; p++) {
      var y = padT + (1 - p / 10) * h;
      g.beginPath(); g.moveTo(padL, y); g.lineTo(padL + w, y); g.stroke();
      g.fillText((p / 10).toFixed(2), padL - 6, y);
    }
    // X axis baseline
    g.strokeStyle = "#2a3542";
    g.beginPath(); g.moveTo(padL, padT); g.lineTo(padL, padT + h); g.stroke();

    var pts = S.points;
    if (!pts.length) {
      g.fillStyle = "#8b98a5"; g.textAlign = "center"; g.textBaseline = "middle";
      g.fillText("no price points in this window", padL + w / 2, padT + h / 2);
      return;
    }

    var t0 = pts[0].ts, t1 = pts[pts.length - 1].ts;
    if (t1 === t0) t1 = t0 + 1;

    function X(t) { return padL + ((t - t0) / (t1 - t0)) * w; }
    function Y(v) { return padT + (1 - Math.max(0, Math.min(1, v))) * h; }

    // jump markers behind the line
    S.jumps.forEach(function (j) {
      var x = X(j.ts);
      g.strokeStyle = j.delta > 0 ? "rgba(34,197,94,.55)" : "rgba(244,63,94,.55)";
      g.setLineDash([4, 3]); g.lineWidth = 1.5;
      g.beginPath(); g.moveTo(x, padT); g.lineTo(x, padT + h); g.stroke();
      g.setLineDash([]);
      g.fillStyle = j.delta > 0 ? "#22c55e" : "#f43f5e";
      g.beginPath(); g.arc(x, Y(j.to), 3.5, 0, Math.PI * 2); g.fill();
    });

    // price line
    g.strokeStyle = "#38bdf8"; g.lineWidth = 2; g.beginPath();
    for (var i = 0; i < pts.length; i++) {
      var px = X(pts[i].ts), py = Y(pts[i].p);
      if (i === 0) g.moveTo(px, py); else g.lineTo(px, py);
    }
    g.stroke();

    // X labels
    g.fillStyle = "#8b98a5"; g.textAlign = "center"; g.textBaseline = "top";
    var span = t1 - t0;
    var fmt = span <= 3600 ? "time" : (span <= 172800 ? "date+time" : "date");
    for (var k = 0; k <= 4; k++) {
      var t = t0 + (t1 - t0) * (k / 4);
      var label = fmt === "time" ? ts(t, false) : (fmt === "date" ? ts(t).slice(0, 10) : ts(t).slice(5, 16));
      g.fillText(label, X(t), padT + h + 6);
    }
  }

  /* ---------------------------------------------------------------- init */
  function init() {
    var seg = $("winSeg");
    if (seg) {
      seg.innerHTML = WINDOWS.map(function (w) {
        return '<button type="button" data-w="' + w.id + '" aria-pressed="' + (w.id === S.window) + '">' + w.label + "</button>";
      }).join("");
      seg.addEventListener("click", function (ev) {
        var b = ev.target.closest ? ev.target.closest("button[data-w]") : null;
        if (!b) return;
        S.window = Number(b.getAttribute("data-w"));
        Array.prototype.forEach.call(seg.querySelectorAll("button"), function (x) {
          x.setAttribute("aria-pressed", x === b ? "true" : "false");
        });
        loadSeries();
      });
    }
    var sel = $("mktSel");
    if (sel) sel.addEventListener("change", function () { selectMarket(sel.value); });
    var refresh = $("refreshBtn");
    if (refresh) refresh.addEventListener("click", function () { pollQuote(); loadSeries(); loadDepth(); });
    window.addEventListener("resize", drawChart);
    setBadge("snap", "SNAPSHOT");
    loadMarkets().catch(function (e) {
      var n = $("chartNote");
      if (n) n.innerHTML = "bundled snapshot unavailable: " + esc((e && e.message) || e);
    });
    pollQuote();
    S.timer = setInterval(pollQuote, 15000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.DESK = { state: S, esc: esc, price: price, money: money, int: int, ts: ts, srcLink: srcLink, docs: DOCS, api: API };
})();
