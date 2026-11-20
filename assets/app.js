/* Kalshi Demo Dashboard — live market dashboard (public data only, no credentials needed). */
(function () {
  "use strict";
  var K = window.K, KALSHI = K.KALSHI;
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    markets: [],
    resolved: [],
    seriesTickers: [],
    meta: null,
    topic: "All",
    rank: "turnover_dollars",
    query: "",
    selected: null,
    points: [],
    pointSource: "",
    book: null,
    live: false
  };

  /* ------------------------- data loading ------------------------- */
  function loadSnapshot() {
    var p = K.loadJSON("markets.json");
    p.then(function (d) {
      state.meta = d.meta;
      state.markets = d.markets || [];
      state.live = false;
      K.loadJSON("series.json").then(function (s) {
        state.seriesTickers = (s.series || []).map(function (x) { return x.ticker; }).sort(function (a, b) { return b.length - a.length; });
      }).catch(function () {});
      render();
      setStatus();
      if (state.pendingTicker) {
        var want = state.pendingTicker;
        state.pendingTicker = null;
        var m = state.markets.filter(function (x) { return x.ticker === want; })[0];
        if (m) selectMarket(m);
      }
    }).catch(function (e) {
      setStatus("Snapshot unavailable (" + e.message + "). Use “Go live” to pull straight from the Kalshi demo API.", true);
    });
    K.loadJSON("resolved.json").then(function (d) { state.resolved = d.resolved || []; renderResolved(); })
      .catch(function () { renderResolved(); });
  }

  function setStatus(msg, isErr) {
    var el = $("dataStatus");
    if (!el) return;
    if (msg) { el.innerHTML = isErr ? '<span class="bad">' + K.esc(msg) + "</span>" : K.esc(msg); return; }
    if (state.meta && state.meta.generated_at) {
      el.innerHTML = '<span class="ok">Snapshot</span> ' + K.esc(K.tsHuman(state.meta.generated_at)) +
        " · " + K.fmtNum(state.meta.counts && state.meta.counts.in_scope_open) + " in-scope open markets, " +
        K.fmtNum(state.meta.counts && state.meta.counts.in_scope_resolved) + " resolved" +
        " · <a href='" + KALSHI.docs.getMarkets + "' target='_blank' rel='noopener'>source: Get Markets</a>";
    } else {
      el.innerHTML = '<span class="muted">No snapshot loaded.</span>';
    }
  }

  function goLive() {
    var btn = $("liveBtn");
    if (btn) { btn.disabled = true; btn.textContent = "Fetching…"; }
    var all = [], cursor = "", pages = 0;
    function page() {
      var q = "/markets?status=open&limit=1000" + (cursor ? "&cursor=" + encodeURIComponent(cursor) : "");
      return fetch(KALSHI.rest + q).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      }).then(function (j) {
        all = all.concat(j.markets || []);
        cursor = j.cursor || "";
        pages++;
        if (cursor && pages < 6) return page();
        return all;
      });
    }
    page().then(function (raw) {
      return loadLiveMeta().then(function () {
        var seriesMap = state.seriesByTicker || {};
        state.markets = raw.map(function (m) {
          var ev = state.eventByTicker ? state.eventByTicker[m.event_ticker] : null;
          var se = ev && ev.series_ticker ? seriesMap[ev.series_ticker] : null;
          var c = K.classify(se, ev, m);
          var mm = Number(m.volume_fp) * Number(m.last_price_dollars);
          var m24 = Number(m.volume_24h_fp) * Number(m.last_price_dollars);
          var moi = Number(m.open_interest_fp) * Number(m.last_price_dollars);
          return Object.assign({}, m, {
            topic: c.topic, topic_rule: c.rule,
            turnover_dollars: isFinite(mm) ? mm : null,
            turnover_24h_dollars: isFinite(m24) ? m24 : null,
            open_interest_value_dollars: isFinite(moi) ? moi : null,
            links: {
              api_market: KALSHI.rest + "/markets/" + encodeURIComponent(m.ticker),
              kalshi_site: KALSHI.site + "/markets/" + encodeURIComponent(m.ticker)
            }
          });
        }).filter(function (m) { return m.topic; });
        state.live = true;
        setStatus('<span class="ok">Live</span> — pulled ' + K.fmtNum(state.markets.length) + " open markets from " +
          '<a href="' + KALSHI.docs.getMarkets + '" target="_blank" rel="noopener">Get Markets</a> (demo)');
        render();
        if (btn) { btn.disabled = false; btn.textContent = "Go live"; }
      });
    }).catch(function (e) {
      setStatus("Live fetch failed: " + e.message + ". The snapshot above is still shown. " +
        "Browser CORS or network rules may block direct calls from this page.", true);
      if (btn) { btn.disabled = false; btn.textContent = "Go live"; }
    });
  }

  function loadLiveMeta() {
    if (state.metaLoaded) return Promise.resolve();
    var a = K.loadJSON("series.json").then(function (d) {
      state.seriesByTicker = {};
      (d.series || []).forEach(function (s) { state.seriesByTicker[s.ticker] = s; });
      state.seriesTickers = (d.series || []).map(function (s) { return s.ticker; }).sort(function (x, y) { return y.length - x.length; });
    }).catch(function () { state.seriesByTicker = {}; });
    var b = fetch(KALSHI.rest + "/events?status=open&limit=200").then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (j) {
      state.eventByTicker = {};
      (j.events || []).forEach(function (e) { state.eventByTicker[e.event_ticker] = e; });
    }).catch(function () { state.eventByTicker = {}; });
    return Promise.all([a, b]).then(function () { state.metaLoaded = true; });
  }

  /* ------------------------- filtering / ranking ------------------------- */
  function filtered() {
    var q = state.query.trim().toLowerCase();
    return state.markets.filter(function (m) {
      if (state.topic !== "All" && m.topic !== state.topic) return false;
      if (!q) return true;
      return ((m.title || "") + " " + (m.ticker || "") + " " + (m.subtitle || "")).toLowerCase().indexOf(q) >= 0;
    }).sort(function (a, b) {
      return (Number(b[state.rank]) || -1) - (Number(a[state.rank]) || -1);
    });
  }

  function rankLabel() {
    return {
      turnover_dollars: "Dollar turnover (volume × last price)",
      turnover_24h_dollars: "24-hour dollar turnover",
      open_interest_value_dollars: "Open interest value (OI × last price)",
      resting_liquidity_notional_dollars: "Resting liquidity notional (orderbook)"
    }[state.rank] || state.rank;
  }

  /* ------------------------- rendering ------------------------- */
  function render() {
    var rows = filtered();
    var tb = $("marketRows");
    if (!tb) return;
    $("rowCount").textContent = K.fmtNum(rows.length);
    $("rankLabel").textContent = rankLabel();
    tb.innerHTML = rows.slice(0, 250).map(function (m, i) {
      var watched = K.inWatch(m.ticker);
      return "<tr>" +
        '<td class="num">' + (i + 1) + "</td>" +
        "<td><b>" + K.esc(m.title || m.ticker) + "</b><br><span class='srcline'>" + K.esc(m.ticker) +
        " · " + K.esc(m.series_ticker || "—") + "</span></td>" +
        "<td>" + K.topicPill(m.topic) + "<br><span class='srcline'>" + K.esc(m.topic_rule || "") + "</span></td>" +
        '<td class="num">' + K.money(m.last_price_dollars, 4) + "</td>" +
        '<td class="num">' + K.money(m.turnover_dollars, 0) + "</td>" +
        '<td class="num">' + K.money(m.turnover_24h_dollars, 0) + "</td>" +
        '<td class="num">' + K.money(m.open_interest_value_dollars, 0) + "</td>" +
        '<td class="num">' + (m.resting_liquidity_notional_dollars === null || m.resting_liquidity_notional_dollars === undefined ? "—" : K.money(m.resting_liquidity_notional_dollars, 0)) + "</td>" +
        "<td>" + K.money(m.yes_bid_dollars, 4) + " / " + K.money(m.yes_ask_dollars, 4) + "</td>" +
        "<td>" + K.esc(m.close_time ? m.close_time.slice(0, 16).replace("T", " ") : "—") + "</td>" +
        "<td>" + K.marketLink(m.ticker, "market") + "<br>" + K.apiLink(m.links && m.links.api_market, "api") + "</td>" +
        '<td><button class="secondary" data-watch="' + K.esc(m.ticker) + '">' + (watched ? "Watching" : "Watch") + "</button></td>" +
        "<td><button class='secondary' data-sel='" + K.esc(m.ticker) + "'>Chart</button></td>" +
        "</tr>";
    }).join("") || '<tr><td colspan="12" class="muted">No markets match the current filter.</td></tr>';

    tb.querySelectorAll("[data-sel]").forEach(function (b) {
      b.onclick = function () {
        var m = state.markets.filter(function (x) { return x.ticker === b.dataset.sel; })[0];
        if (m) selectMarket(m);
        document.getElementById("chartCard").scrollIntoView({ behavior: "smooth", block: "start" });
      };
    });
    tb.querySelectorAll("[data-watch]").forEach(function (b) {
      b.onclick = function () {
        var m = state.markets.filter(function (x) { return x.ticker === b.dataset.watch; })[0];
        if (!m) return;
        K.toggleWatch({ ticker: m.ticker, title: m.title, topic: m.topic, added_at: new Date().toISOString() });
        render();
      };
    });

    var sel = $("marketSelect");
    if (sel) {
      var cur = sel.value;
      sel.innerHTML = rows.slice(0, 400).map(function (m) {
        return '<option value="' + K.esc(m.ticker) + '">' + K.esc((m.title || m.ticker).slice(0, 90)) + "</option>";
      }).join("");
      if (cur && rows.some(function (m) { return m.ticker === cur; })) sel.value = cur;
    }
  }

  function renderResolved() {
    var tb = $("resolvedRows");
    if (!tb) return;
    var q = (state.query || "").trim().toLowerCase();
    var rows = state.resolved.filter(function (m) {
      if (state.topic !== "All" && m.topic !== state.topic) return false;
      if (!q) return true;
      return ((m.title || "") + " " + (m.ticker || "")).toLowerCase().indexOf(q) >= 0;
    });
    $("resolvedCount").textContent = K.fmtNum(rows.length);
    tb.innerHTML = rows.slice(0, 200).map(function (m) {
      var res = m.result ? '<span class="pill res-' + K.esc(m.result) + '">' + K.esc(m.result.toUpperCase()) + "</span>" : '<span class="badge-open">no result field</span>';
      return "<tr><td>" + K.esc(m.title || m.ticker) + "<br><span class='srcline'>" + K.esc(m.ticker) + "</span></td>" +
        "<td>" + K.topicPill(m.topic) + "</td>" +
        "<td>" + res + "</td>" +
        '<td class="num">' + K.money(m.settlement_value_dollars, 4) + "</td>" +
        "<td>" + K.esc(m.settlement_ts ? m.settlement_ts.slice(0, 19).replace("T", " ") : "—") + "</td>" +
        "<td>" + K.marketLink(m.ticker, "market") + " · " + K.apiLink(m.links && m.links.api_market, "api") + "</td></tr>";
    }).join("") || '<tr><td colspan="6" class="muted">No resolved in-scope markets in the current snapshot.</td></tr>';
  }

  /* ------------------------- chart ------------------------- */
  var pollTimer = null;

  function seriesFor(ticker, eventTicker) {
    var found = null;
    state.seriesTickers.some(function (s) {
      if (eventTicker && eventTicker.indexOf(s) === 0) { found = s; return true; }
      return false;
    });
    return found;
  }

  function selectMarket(m) {
    state.selected = m;
    state.points = [];
    var sel = $("marketSelect");
    if (sel) sel.value = m.ticker;
    $("chartTitle").textContent = (m.title || m.ticker) + "  [" + m.ticker + "]";
    $("chartMeta").innerHTML = "Topic " + K.topicPill(m.topic) +
      " · series " + K.esc(m.series_ticker || "unknown") +
      ' · <a href="' + KALSHI.docs.getMarket + '" target="_blank" rel="noopener">Get Market</a>';
    loadChart();
    loadOrderbook(m.ticker);
    if (pollTimer) clearInterval(pollTimer);
  }

  function windowSpec() {
    var scale = $("scaleSel").value;
    var win = Number($("windowSel").value);
    return { scale: scale, seconds: win };
  }

  function loadChart() {
    var m = state.selected;
    if (!m) return;
    var spec = windowSpec();
    var now = Math.floor(Date.now() / 1000);
    var endTs = now;
    var startTs = now - spec.seconds;
    $("chartNote").innerHTML = "Loading…";
    if (spec.scale === "sec") {
      loadLiveTicks(m);
      return;
    }
    var period = spec.scale === "min" ? 1 : spec.scale === "hr" ? 60 : 1440;
    var series = m.series_ticker || seriesFor(m.ticker, m.event_ticker);
    if (!series) {
      $("chartNote").innerHTML = '<span class="bad">No series ticker known for this market, so the candlestick endpoint ' +
        '<code>/series/{series_ticker}/markets/{ticker}/candlesticks</code> cannot be called. ' +
        "Use the seconds view, which reads the market directly.</span>";
      return;
    }
    var url = KALSHI.rest + "/series/" + encodeURIComponent(series) + "/markets/" + encodeURIComponent(m.ticker) +
      "/candlesticks?start_ts=" + startTs + "&end_ts=" + endTs + "&period_interval=" + period;
    fetch(url).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (j) {
      var pts = (j.candlesticks || []).map(function (c) {
        return { t: (c.end_period_ts || 0) * 1000, p: Number(c.price && c.price.close_dollars) };
      }).filter(function (p) { return isFinite(p.p); });
      state.points = pts;
      state.pointSource = "candlesticks (" + period + "-minute period) · " + pts.length + " points";
      drawChart();
      $("chartNote").innerHTML = "Official candlesticks: <code>GET /series/" + K.esc(series) + "/markets/" + K.esc(m.ticker) +
        "/candlesticks</code> with <code>period_interval=" + period + "</code>. " +
        '<a href="' + KALSHI.docs.candlesticks + '" target="_blank" rel="noopener">Get Market Candlesticks</a>';
    }).catch(function (e) {
      $("chartNote").innerHTML = '<span class="bad">Candlesticks unavailable: ' + K.esc(e.message) + "</span>";
    });
  }

  function loadLiveTicks(m) {
    if (pollTimer) clearInterval(pollTimer);
    $("chartNote").innerHTML = "Live REST polling every 3 s (browser-side).";
    function tick() {
      fetch(KALSHI.rest + "/markets/" + encodeURIComponent(m.ticker)).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      }).then(function (j) {
        var mk = j.market || {};
        var p = Number(mk.last_price_dollars);
        if (isFinite(p)) {
          state.points.push({ t: Date.now(), p: p });
          var max = Math.max(20, Number($("windowSel").value));
          while (state.points.length && Date.now() - state.points[0].t > max * 1000) state.points.shift();
          state.pointSource = "live REST snapshots";
          drawChart();
        }
        $("chartNote").innerHTML = "Live REST polling every 3 s from <code>GET /markets/{ticker}</code> — " +
          '<a href="' + KALSHI.docs.getMarket + '" target="_blank" rel="noopener">Get Market</a>. ' +
          "History is this browser session only; it is not an official historical series.";
      }).catch(function (e) {
        $("chartNote").innerHTML = '<span class="bad">Live poll failed: ' + K.esc(e.message) + "</span>";
      });
    }
    tick();
    pollTimer = setInterval(tick, 3000);
  }

  function fmtTime(t, scale) {
    var d = new Date(t);
    function p(n) { return (n < 10 ? "0" : "") + n; }
    if (scale === "day") return (d.getUTCMonth() + 1) + "/" + d.getUTCDate();
    return p(d.getUTCHours()) + ":" + p(d.getUTCMinutes()) + (scale === "sec" ? ":" + p(d.getUTCSeconds()) : "");
  }

  function drawChart() {
    var c = $("priceChart");
    if (!c) return;
    var dpr = window.devicePixelRatio || 1;
    var W = c.clientWidth, H = c.clientHeight;
    c.width = W * dpr; c.height = H * dpr;
    var ctx = c.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    var pts = state.points;
    var padL = 58, padR = 12, padT = 18, padB = 26;
    if (pts.length < 2) {
      ctx.fillStyle = "#9fb0c8"; ctx.font = "13px system-ui";
      ctx.fillText("Waiting for data points… select a market above.", padL, H / 2);
      return;
    }
    var lo = Math.min.apply(null, pts.map(function (p) { return p.p; }));
    var hi = Math.max.apply(null, pts.map(function (p) { return p.p; }));
    if (hi - lo < 0.02) { lo = Math.max(0, lo - 0.02); hi = Math.min(1, hi + 0.02); }
    var t0 = pts[0].t, t1 = pts[pts.length - 1].t;
    if (t1 === t0) t1 = t0 + 1000;
    var scale = $("scaleSel").value;

    ctx.strokeStyle = "#24344f"; ctx.fillStyle = "#9fb0c8"; ctx.font = "11px system-ui";
    for (var i = 0; i <= 4; i++) {
      var y = padT + (H - padT - padB) * i / 4;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
      var pv = hi - (hi - lo) * i / 4;
      ctx.fillText("$" + pv.toFixed(3), 6, y + 4);
    }
    for (var j = 0; j <= 4; j++) {
      var tt = t0 + (t1 - t0) * j / 4;
      var x = padL + (W - padL - padR) * j / 4;
      ctx.fillText(fmtTime(tt, scale), x - 18, H - 8);
      ctx.strokeStyle = "#1b2942";
      ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, H - padB); ctx.stroke();
    }
    ctx.strokeStyle = "#00b67a"; ctx.lineWidth = 2; ctx.beginPath();
    pts.forEach(function (p, k) {
      var x = padL + (W - padL - padR) * (p.t - t0) / (t1 - t0);
      var y = padT + (H - padT - padB) * (1 - (p.p - lo) / (hi - lo));
      if (k) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    });
    ctx.stroke();
    var last = pts[pts.length - 1];
    var lx = padL + (W - padL - padR), ly = padT + (H - padT - padB) * (1 - (last.p - lo) / (hi - lo));
    ctx.fillStyle = "#00b67a"; ctx.beginPath(); ctx.arc(lx, ly, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#e8eef7";
    ctx.fillText("last $" + last.p.toFixed(4), padL + 4, padT - 4);
    $("chartStats").textContent = pts.length + " points · " + (state.pointSource || "");
  }

  /* ------------------------- orderbook ------------------------- */
  function loadOrderbook(ticker) {
    var box = $("orderbookBox");
    if (!box) return;
    box.innerHTML = '<span class="muted">Loading orderbook…</span>';
    fetch(KALSHI.rest + "/markets/" + encodeURIComponent(ticker) + "/orderbook?depth=20").then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (j) {
      state.book = j.orderbook_fp || {};
      renderBook();
    }).catch(function (e) {
      box.innerHTML = '<span class="bad">Orderbook failed: ' + K.esc(e.message) + "</span>";
    });
  }

  function bookRows(levels, label) {
    if (!levels || !levels.length) return "<tr><td colspan='4' class='muted'>No resting bids reported for " + K.esc(label) + "</td></tr>";
    var rows = levels.slice().reverse();
    var cum = 0, notional = 0;
    return rows.map(function (lv) {
      cum += Number(lv[1]); notional += Number(lv[0]) * Number(lv[1]);
      return "<tr><td class='num'>" + K.money(lv[0], 4) + "</td><td class='num'>" + K.fmtNum(lv[1], 2) +
        "</td><td class='num'>" + K.fmtNum(cum, 2) + "</td><td class='num'>" + K.money(notional, 2) + "</td></tr>";
    }).join("");
  }

  function renderBook() {
    var box = $("orderbookBox");
    var b = state.book || {};
    var yes = b.yes_dollars || [], no = b.no_dollars || [];
    var bestYes = yes.length ? Number(yes[yes.length - 1][0]) : null;
    var bestNo = no.length ? Number(no[no.length - 1][0]) : null;
    var impliedYesAsk = bestNo === null ? null : 1 - bestNo;
    var spread = (bestYes !== null && impliedYesAsk !== null) ? impliedYesAsk - bestYes : null;
    var yesDepth = yes.reduce(function (s, lv) { return s + Number(lv[0]) * Number(lv[1]); }, 0);
    var noDepth = no.reduce(function (s, lv) { return s + Number(lv[0]) * Number(lv[1]); }, 0);
    box.innerHTML =
      '<div class="kv"><span>Best YES bid</span><b>' + K.money(bestYes, 4) + "</b></div>" +
      '<div class="kv"><span>Implied YES ask (1 − best NO bid)</span><b>' + K.money(impliedYesAsk, 4) + "</b></div>" +
      '<div class="kv"><span>Spread</span><b>' + (spread === null ? "—" : K.money(spread, 4)) + "</b></div>" +
      '<div class="kv"><span>Resting depth notional — YES bids</span><b>' + K.money(yesDepth, 2) + "</b></div>" +
      '<div class="kv"><span>Resting depth notional — NO bids</span><b>' + K.money(noDepth, 2) + "</b></div>" +
      '<div class="tbl-wrap" style="margin-top:10px"><table><thead><tr><th>YES bid</th><th class="num">Contracts</th>' +
      "<th class='num'>Cumulative contracts</th><th class='num'>Cumulative $</th></tr></thead><tbody>" +
      bookRows(yes, "YES") + "</tbody></table></div>" +
      '<div class="tbl-wrap" style="margin-top:10px"><table><thead><tr><th>NO bid</th><th class="num">Contracts</th>' +
      "<th class='num'>Cumulative contracts</th><th class='num'>Cumulative $</th></tr></thead><tbody>" +
      bookRows(no, "NO") + "</tbody></table></div>" +
      '<p class="muted small">Bids only — a YES bid at $X is a NO ask at $(1 − X). ' +
      '<a href="' + KALSHI.docs.orderbook + '" target="_blank" rel="noopener">Orderbook Responses</a>.</p>';
  }

  /* ------------------------- wiring ------------------------- */
  function init() {
    var topicSel = $("topicSel");
    if (topicSel) {
      topicSel.innerHTML = '<option value="All">All topics</option>' +
        K.TOPICS.map(function (t) { return '<option value="' + t + '">' + t + "</option>"; }).join("");
      topicSel.onchange = function () { state.topic = topicSel.value; render(); renderResolved(); };
    }
    var rankSel = $("rankSel");
    if (rankSel) {
      rankSel.onchange = function () { state.rank = rankSel.value; render(); };
    }
    var q = $("searchBox");
    if (q) q.oninput = function () { state.query = q.value; render(); renderResolved(); };
    var lb = $("liveBtn");
    if (lb) lb.onclick = goLive;
    var ms = $("marketSelect");
    if (ms) ms.onchange = function () {
      var m = state.markets.filter(function (x) { return x.ticker === ms.value; })[0];
      if (m) selectMarket(m);
    };
    var scaleSel = $("scaleSel"), windowSel = $("windowSel");
    function syncWindows() {
      var s = scaleSel.value;
      var opts = s === "sec" ? [[60, "Last 60 seconds"], [300, "Last 5 minutes"], [900, "Last 15 minutes"], [3600, "Last 60 minutes"]]
        : s === "min" ? [[1800, "Last 30 minutes"], [7200, "Last 2 hours"], [21600, "Last 6 hours"], [86400, "Last 24 hours"]]
          : s === "hr" ? [[86400, "Last 24 hours"], [604800, "Last 7 days"], [2592000, "Last 30 days"], [7776000, "Last 90 days"]]
            : [[2592000, "Last 30 days"], [7776000, "Last 90 days"], [31536000, "Last 365 days"]];
      var cur = windowSel.value;
      windowSel.innerHTML = opts.map(function (o) { return '<option value="' + o[0] + '">' + o[1] + "</option>"; }).join("");
      if (opts.some(function (o) { return String(o[0]) === cur; })) windowSel.value = cur;
    }
    if (scaleSel && windowSel) {
      scaleSel.onchange = function () { syncWindows(); loadChart(); };
      windowSel.onchange = loadChart;
      syncWindows();
    }
    var ob = $("bookBtn");
    if (ob) ob.onclick = function () { if (state.selected) loadOrderbook(state.selected.ticker); };
    window.addEventListener("resize", drawChart);

    loadSnapshot();
    var params = new URLSearchParams(window.location.search);
    if (params.get("ticker")) state.pendingTicker = params.get("ticker");
    setInterval(function () { if (state.live) goLive(); }, 60000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
