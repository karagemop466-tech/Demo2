/* Shared helpers + price chart for the Kalshi demo dashboard.
 *
 * Data path: data/*.json written by tools/collector.py on GitHub Actions from the
 * official Kalshi demo Trade API (see pages/api-reference.html). The browser does NOT
 * fabricate anything: if a field is missing it is rendered as an em dash and the row is
 * tagged "unverified".
 */
(function () {
  "use strict";

  var KR = {
    DEMO_REST: "https://external-api.demo.kalshi.co/trade-api/v2",
    DOCS: "https://docs.kalshi.com",
    cache: {},
  };

  /* ---------------- fetch helpers ---------------- */
  KR.getJSON = function (path) {
    if (KR.cache[path]) return KR.cache[path];
    var url = path + (path.indexOf("?") >= 0 ? "&" : "?") + "t=" + Date.now();
    var p = fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(path + " → HTTP " + r.status);
      return r.json();
    });
    KR.cache[path] = p;
    p.catch(function () { delete KR.cache[path]; });
    return p;
  };

  /* ---------------- formatting ---------------- */
  KR.dash = function (v) {
    return v === null || v === undefined || v === "" ? '<span class="muted" title="not returned by the API">—</span>' : v;
  };
  KR.usd = function (v, dp) {
    if (v === null || v === undefined || v === "") return "—";
    var n = Number(v);
    if (!isFinite(n)) return "—";
    return "$" + n.toFixed(dp === undefined ? 2 : dp);
  };
  KR.num = function (v, dp) {
    if (v === null || v === undefined || v === "") return "—";
    var n = Number(v);
    if (!isFinite(n)) return "—";
    return n.toLocaleString(undefined, { minimumFractionDigits: dp || 0, maximumFractionDigits: dp === undefined ? 2 : dp });
  };
  KR.pct = function (v) {
    if (v === null || v === undefined) return "—";
    return (Number(v) * 100).toFixed(1) + "%";
  };
  KR.esc = function (s) {
    return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  KR.topicPill = function (t) {
    return '<span class="pill ' + KR.esc(t) + '">' + KR.esc(t || "unmapped") + "</span>";
  };
  KR.resultPill = function (r) {
    var v = (r || "").toLowerCase();
    if (v === "yes" || v === "no") return '<span class="pill ' + v + '">' + v.toUpperCase() + "</span>";
    return '<span class="pill open">unresolved</span>';
  };
  KR.when = function (iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return KR.esc(iso);
    return d.toISOString().replace("T", " ").replace("Z", " UTC");
  };
  KR.ago = function (iso) {
    if (!iso) return "—";
    var ms = Date.now() - new Date(iso).getTime();
    if (!isFinite(ms)) return "—";
    var m = Math.round(ms / 60000);
    if (m < 1) return "just now";
    if (m < 60) return m + " min ago";
    var h = Math.round(m / 60);
    if (h < 24) return h + " h ago";
    return Math.round(h / 24) + " d ago";
  };

  /* ---------------- data loaders ---------------- */
  KR.snapshot = function () { return KR.getJSON("data/snapshot.json"); };
  KR.topic = function (t) { return KR.getJSON("data/topic-" + t + ".json"); };
  KR.resolutions = function () { return KR.getJSON("data/resolutions.json"); };
  KR.portfolio = function () { return KR.getJSON("data/portfolio.json"); };
  KR.analysis = function () { return KR.getJSON("data/analysis.json"); };
  KR.history = function () { return KR.getJSON("data/history.json"); };
  KR.executions = function () { return KR.getJSON("data/executions.json"); };

  /* Derive an ISO timestamp for a history point: the collector stores unix seconds. */
  KR.pointTime = function (p) { return (p.t || 0) * 1000; };

  /* Merge collected history points with candlesticks into one series.
   * Candles give the long-range shape (documented OHLC), history points give the
   * fine-grained ticks between collector runs. Both are official API values. */
  /* Field names differ between a candlestick and a collector tick, so map explicitly
     rather than guessing. Without this the tick half of a series silently vanishes. */
  KR.HISTORY_KEY = {
    close_dollars: "last",
    yes_bid_close: "yes_bid",
    yes_ask_close: "yes_ask",
  };

  KR.buildSeries = function (candles, historyPoints, field) {
    var out = [];
    var hkey = KR.HISTORY_KEY[field] || "last";
    (candles || []).forEach(function (c) {
      var v = c[field] !== undefined ? c[field] : c.close;
      if (v === null || v === undefined || v === "") return;
      out.push({ t: (c.ts || 0) * 1000, v: Number(v), src: "candle" });
    });
    (historyPoints || []).forEach(function (p) {
      var raw = p[hkey];
      if (raw === null || raw === undefined || raw === "") return;
      var n = Number(raw);
      if (!isFinite(n)) return;
      out.push({ t: KR.pointTime(p), v: n, src: "tick" });
    });
    out.sort(function (a, b) { return a.t - b.t; });
    return out;
  };

  /* ---------------- sharp-jump detection ---------------- */
  /* Scans a sorted price series for adjacent-point moves of at least `threshold`
     dollars (default 0.10) in either direction. Returns one record per jump.
     The cause of each jump is not derivable from the Kalshi API alone, so each
     record links only to the market's own page on Kalshi and is flagged
     "cause unverified" — see pages/flagged.html. */
  KR.detectJumps = function (series, threshold) {
    if (!series || series.length < 2) return [];
    var thr = threshold === undefined ? 0.10 : Number(threshold);
    if (!isFinite(thr) || thr <= 0) thr = 0.10;
    var jumps = [];
    for (var i = 1; i < series.length; i++) {
      var a = series[i - 1], b = series[i];
      if (a.v === null || a.v === undefined || b.v === null || b.v === undefined) continue;
      var change = b.v - a.v;
      if (Math.abs(change) >= thr) {
        jumps.push({
          t: b.t, fromV: a.v, toV: b.v, change: change,
          dir: change > 0 ? 'up' : 'down',
          fromTime: a.t, toTime: b.t
        });
      }
    }
    return jumps;
  };

  /* ---------------- chart ---------------- */
  /* Pure canvas, no external libs, so the page works offline and cannot break on a CDN. */
  KR.drawChart = function (canvas, series, opts) {
    opts = opts || {};
    if (!canvas) return;
    var dpr = window.devicePixelRatio || 1;
    var W = canvas.clientWidth || 640;
    var H = canvas.clientHeight || 340;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);

    var padL = 62, padR = 16, padT = 16, padB = 34;
    var plotW = Math.max(10, W - padL - padR);
    var plotH = Math.max(10, H - padT - padB);

    var css = getComputedStyle(document.documentElement);
    var cLine = css.getPropertyValue("--accent").trim() || "#00c389";
    var cGrid = css.getPropertyValue("--line").trim() || "#24344d";
    var cText = css.getPropertyValue("--muted").trim() || "#93a4bd";

    if (!series || series.length < 2) {
      ctx.fillStyle = cText;
      ctx.font = "13px system-ui,sans-serif";
      ctx.fillText(opts.emptyMessage || "Not enough price points yet for this window.", padL, padT + 24);
      return;
    }

    var t0 = series[0].t, t1 = series[series.length - 1].t;
    if (t1 === t0) t1 = t0 + 1000;
    var vals = series.map(function (d) { return d.v; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    if (hi === lo) { hi = lo + 0.02; lo = Math.max(0, lo - 0.02); }
    var padY = (hi - lo) * 0.12;
    lo = Math.max(0, lo - padY); hi = Math.min(1, hi + padY);

    function X(t) { return padL + plotW * ((t - t0) / (t1 - t0)); }
    function Y(v) { return padT + plotH * (1 - (v - lo) / (hi - lo)); }

    /* grid + y labels */
    ctx.strokeStyle = cGrid; ctx.lineWidth = 1; ctx.font = "11px system-ui,sans-serif";
    ctx.fillStyle = cText;
    for (var i = 0; i <= 4; i++) {
      var v = lo + ((hi - lo) * i) / 4;
      var y = Y(v);
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + plotW, y); ctx.stroke();
      ctx.fillText("$" + v.toFixed(2), 6, y + 4);
    }
    /* x labels */
    var spans = opts.spanSeconds || ((t1 - t0) / 1000);
    var fmt = spans <= 3600
      ? function (t) { return new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }); }
      : spans <= 86400 * 2
        ? function (t) { return new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
        : function (t) { return new Date(t).toLocaleDateString([], { month: "short", day: "numeric" }); };
    ctx.textAlign = "center";
    for (var j = 0; j <= 4; j++) {
      var tt = t0 + ((t1 - t0) * j) / 4;
      ctx.fillText(fmt(tt), X(tt), H - 12);
    }
    ctx.textAlign = "left";

    /* area + line */
    ctx.beginPath();
    series.forEach(function (d, k) { var x = X(d.t), y = Y(d.v); k ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.strokeStyle = cLine; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.stroke();
    ctx.lineTo(X(t1), padT + plotH); ctx.lineTo(X(t0), padT + plotH); ctx.closePath();
    var g = ctx.createLinearGradient(0, padT, 0, padT + plotH);
    g.addColorStop(0, "rgba(0,195,137,.28)"); g.addColorStop(1, "rgba(0,195,137,0)");
    ctx.fillStyle = g; ctx.fill();

    /* sharp-jump markers: vertical dashed lines at each ≥ $0.10 move */
    var jumps = opts.jumps || [];
    if (jumps.length) {
      ctx.save();
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.fillStyle = '#ef4444';
      jumps.forEach(function (j) {
        var x = X(j.t);
        ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + plotH); ctx.stroke();
        ctx.beginPath(); ctx.arc(x, Y(j.toV), 4, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();
    }

    /* last point marker */
    var last = series[series.length - 1];
    ctx.beginPath(); ctx.arc(X(last.t), Y(last.v), 3.5, 0, Math.PI * 2);
    ctx.fillStyle = cLine; ctx.fill();
  };

  /* Build an external link only from a real https URL; otherwise render an em dash.
     Doing this in one place means no page script ever emits a broken href, and a
     malformed URL from the API can never become a dead link on the site. */
  KR.link = function (url, label, cls) {
    var u = String(url || "");
    if (!/^https?:\/\//i.test(u)) return '<span class="muted" title="URL not returned by the API">—</span>';
    return '<a href="' + KR.esc(u) + '"' + (cls ? ' class="' + cls + '"' : "") +
      ' target="_blank" rel="noopener">' + (label || "open") + "</a>";
  };

  /* ---------------- table helper ---------------- */
  KR.renderTable = function (el, cols, rows, emptyMsg) {
    if (!el) return;
    if (!rows || !rows.length) {
      el.innerHTML = '<div class="empty">' + KR.esc(emptyMsg || "No rows.") + "</div>";
      return;
    }
    var head = "<thead><tr>" + cols.map(function (c) {
      return "<th" + (c.num ? ' class="num"' : "") + ">" + c.label + "</th>";
    }).join("") + "</tr></thead>";
    var body = "<tbody>" + rows.map(function (r) {
      return "<tr" + (r._dim ? ' class="dim"' : "") + ">" + cols.map(function (c) {
        var v = c.get(r);
        return "<td" + (c.num ? ' class="num"' : "") + ">" + (v === undefined || v === null ? KR.dash() : v) + "</td>";
      }).join("") + "</tr>";
    }).join("") + "</tbody>";
    el.innerHTML = '<div class="tablewrap"><table>' + head + body + "</table></div>";
  };

  /* ---------------- live alert engine ---------------- */
  /* Two scrolling chat feeds fed by the PUBLIC Kalshi demo REST API, polled from
     the browser. The demo API allows this site's origin (CORS was observed and
     recorded in data/cors.json), so the feeds are real, not simulated.
     The WebSocket feed cannot be used here: per the official docs a WebSocket
     handshake is authenticated even for the public ticker/trade channels, and
     this site must never ask a visitor for a private key.

     Every line is an official price change. The API returns no news feed, so the
     *cause* of a move is never asserted - each line links to the market's own
     Kalshi endpoint and is labelled "cause unverified" (see pages/flagged.html). */
  KR.live = {
    threshold: 0.10,        /* dollars; a move of at least this size raises an alert */
    roiThreshold: 0.55,     /* 0..1; the model score a move needs to reach the ROI feed */
    intervalMs: 30000,      /* polling cadence; the demo API is public and unauthenticated */
    batchSize: 25,          /* tickers per request (one request per batch) */
    maxMarkets: 60,         /* how many in-scope markets are watched */
    markets: [],            /* monitored markets: {ticker,title,topic,est,oi,close} */
    prices: {},             /* ticker -> last price we saw */
    alerts: [],             /* every alert raised this session, newest last */
    seen: {},               /* ticker -> {t, dir} for de-duplication */
    running: false,
    timer: null,
    lastPoll: null,
    lastError: null,
    polls: 0,
    _handlers: { alert: [], status: [], point: [] },
  };

  KR.live.on = function (evt, fn) {
    if (KR.live._handlers[evt]) KR.live._handlers[evt].push(fn);
    return KR.live;
  };
  KR.live.emit = function (evt, payload) {
    (KR.live._handlers[evt] || []).forEach(function (fn) {
      try { fn(payload); } catch (e) { /* one bad listener must not stop the feed */ }
    });
  };

  /* ROI model. A documented heuristic ranking, not a prediction and not a
     profitability claim. Every input is an official field (or the clearly
     labelled estimate built from two official fields):
       size   0.45 * min(|move| / 0.30, 1)
       depth  0.25 * min(est. dollar volume / 50,000, 1)
       open   0.15 * min(open_interest_fp / 5,000, 1)
       time   0.15 * (1 - min(hours to close / 72, 1))
     The weights sum to 1, so the score is 0..1. */
  KR.live.score = function (a) {
    var parts = { size: 0, depth: 0, open: 0, time: 0 };
    parts.size = Math.min(Math.abs(a.change || 0) / 0.30, 1);
    parts.depth = Math.min((a.est || 0) / 50000, 1);
    parts.open = Math.min((a.oi || 0) / 5000, 1);
    var hours = 72;
    if (a.closeTime) {
      var h = (new Date(a.closeTime).getTime() - Date.now()) / 3600000;
      if (isFinite(h)) hours = Math.max(0, h);
    }
    parts.time = 1 - Math.min(hours / 72, 1);
    var total = 0.45 * parts.size + 0.25 * parts.depth + 0.15 * parts.open + 0.15 * parts.time;
    a.score = Math.round(total * 1000) / 1000;
    a.scoreParts = parts;
    return a.score;
  };

  KR.live.marketUrl = function (ticker) {
    return KR.DEMO_REST + "/markets/" + encodeURIComponent(ticker);
  };

  /* Watch the highest-dollar in-scope markets (the same ranking the dashboard
     shows). The list comes from the committed snapshot, so every watched market
     has a source-linked row on the page. */
  KR.live.setMarkets = function (rows) {
    var list = (rows || []).slice(0, KR.live.maxMarkets).map(function (m) {
      return {
        ticker: m.market_ticker,
        title: m.market_title || m.market_ticker,
        topic: m.topic || "",
        est: m.est_dollar_volume || 0,
        oi: parseFloat(m.open_interest_fp) || 0,
        closeTime: m.close_time || null,
        url: m.market_url || KR.live.marketUrl(m.market_ticker),
        seed: parseFloat(m.last_price_dollars),
      };
    });
    KR.live.markets = list;
    return list;
  };

  KR.live.fetchBatch = function (tickers) {
    /* The documented filter is a comma-separated list of market tickers, so the
       separators stay literal and only the tickers themselves are encoded. */
    var list = tickers.map(function (t) { return encodeURIComponent(t); }).join(",");
    var url = KR.DEMO_REST + "/markets?tickers=" + list + "&status=open&limit=1000";
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status + " for " + url);
      return r.json();
    }).then(function (j) {
      return (j && j.markets) || [];
    });
  };

  /* One polling pass. Two independent official signals are compared:
     - the API's own previous_price_dollars vs last_price_dollars (two trades), and
     - the price we saw on the previous poll vs the price now.
     Whichever is larger is used, so a move is never missed between polls. */
  KR.live.pollOnce = function () {
    if (!KR.live.markets.length) return Promise.resolve();
    var batches = [];
    for (var i = 0; i < KR.live.markets.length; i += KR.live.batchSize) {
      batches.push(KR.live.markets.slice(i, i + KR.live.batchSize));
    }
    return batches.reduce(function (chain, batch) {
      return chain.then(function (acc) {
        return KR.live.fetchBatch(batch.map(function (m) { return m.ticker; })).then(function (ms) {
          return acc.concat(ms);
        });
      });
    }, Promise.resolve([])).then(function (markets) {
      var now = Date.now();
      var byTicker = {};
      KR.live.markets.forEach(function (m) { byTicker[m.ticker] = m; });
      markets.forEach(function (m) {
        var meta = byTicker[m.ticker];
        if (!meta) return;
        var last = parseFloat(m.last_price_dollars);
        if (!isFinite(last)) return;
        var prevTrade = parseFloat(m.previous_price_dollars);
        var prevSeen = KR.live.prices[m.ticker];
        var from = null, change = 0, basis = "";
        /* Prices carry four decimals, so the difference is rounded before the
           comparison. Without this, 0.60 - 0.50 evaluates to 0.09999999999999998
           in binary floating point and a move of exactly $0.10 would be
           silently dropped. */
        var dTrade = isFinite(prevTrade) ? Math.round((last - prevTrade) * 10000) / 10000 : NaN;
        var dPoll = isFinite(prevSeen) ? Math.round((last - prevSeen) * 10000) / 10000 : NaN;
        if (isFinite(dTrade) && Math.abs(dTrade) >= KR.live.threshold) {
          from = prevTrade; change = dTrade; basis = "previous trade";
        }
        if (isFinite(dPoll) && Math.abs(dPoll) >= KR.live.threshold &&
            Math.abs(dPoll) > Math.abs(change)) {
          from = prevSeen; change = dPoll; basis = "previous poll";
        }
        if (from !== null) {
          var dir = change > 0 ? "up" : "down";
          var seen = KR.live.seen[m.ticker];
          if (!(seen && seen.dir === dir && (now - seen.t) < 90000)) {
            var alert = {
              t: now, ticker: m.ticker, title: meta.title, topic: meta.topic,
              from: from, to: last, change: change, dir: dir, basis: basis,
              est: meta.est, oi: meta.oi, closeTime: meta.closeTime,
              url: meta.url || KR.live.marketUrl(m.ticker),
              source: KR.DEMO_REST + "/markets?tickers=" + m.ticker,
            };
            KR.live.score(alert);
            KR.live.seen[m.ticker] = { t: now, dir: dir };
            KR.live.alerts.push(alert);
            if (KR.live.alerts.length > 500) KR.live.alerts.shift();
            KR.live.emit("alert", alert);
          }
        }
        KR.live.prices[m.ticker] = last;
        KR.live.emit("point", {
          ticker: m.ticker, price: last, t: now, market: meta,
          bid: parseFloat(m.yes_bid_dollars), ask: parseFloat(m.yes_ask_dollars),
        });
      });
      KR.live.lastPoll = now;
      KR.live.polls += 1;
      KR.live.lastError = null;
      KR.live.emit("status", { state: "live", at: now });
    }).catch(function (e) {
      KR.live.lastError = String(e && e.message ? e.message : e);
      KR.live.emit("status", { state: "error", at: Date.now(), error: KR.live.lastError });
    });
  };

  KR.live.start = function () {
    if (KR.live.running) return;
    KR.live.running = true;
    KR.live.emit("status", { state: "starting", at: Date.now() });
    var run = function () {
      if (!KR.live.running) return;
      KR.live.pollOnce().then(function () {
        if (!KR.live.running) return;
        KR.live.timer = setTimeout(run, KR.live.intervalMs);
      });
    };
    run();
  };

  KR.live.stop = function () {
    KR.live.running = false;
    if (KR.live.timer) { clearTimeout(KR.live.timer); KR.live.timer = null; }
    KR.live.emit("status", { state: "stopped", at: Date.now() });
  };

  /* Seed the feeds with the moves already visible in the committed tick history,
     so the chats are not empty before the first poll lands. These are the same
     official last/bid/ask prices the collector stored, sampled every few
     minutes - they are labelled as history, never as live ticks. */
  KR.live.seedFromHistory = function (history, markets) {
    var pts = (history && history.points) || {};
    var meta = {};
    (markets || []).forEach(function (m) { meta[m.market_ticker] = m; });
    var out = [];
    Object.keys(pts).forEach(function (ticker) {
      var series = pts[ticker] || [];
      var built = [];
      series.forEach(function (p) {
        var v = parseFloat(p.last);
        if (isFinite(v)) built.push({ t: KR.pointTime(p), v: v });
      });
      KR.detectJumps(built, KR.live.threshold).forEach(function (j) {
        var m = meta[ticker] || {};
        var a = {
          t: j.toTime, ticker: ticker, title: m.market_title || ticker, topic: m.topic || "",
          from: j.fromV, to: j.toV, change: j.change, dir: j.dir, basis: "committed history",
          est: m.est_dollar_volume || 0, oi: parseFloat(m.open_interest_fp) || 0,
          closeTime: m.close_time || null,
          url: m.market_url || KR.live.marketUrl(ticker),
        };
        KR.live.score(a);
        out.push(a);
      });
    });
    out.sort(function (x, y) { return x.t - y.t; });
    return out;
  };

  /* Live order book for one market, straight from the demo API.

     The official response shape (verified against the live demo API on
     2026-11-20, e.g. GET /markets/KXECCOMPACT-30/orderbook?depth=25) is:

       { "orderbook_fp": { "yes_dollars": [[price, quantity], ...],
                           "no_dollars":  [[price, quantity], ...] } }

     The prices are fixed-point strings with four decimals and the quantities
     with two. Only bids are returned, so a NO bid at p is a YES ask at (1 - p);
     the ask side is derived and labelled as derived. The older `orderbook`
     shape (integer cents) is accepted as a fallback. */
  KR.live.fetchOrderbook = function (ticker, depth) {
    var url = KR.DEMO_REST + "/markets/" + encodeURIComponent(ticker) +
      "/orderbook?depth=" + (depth || 25);
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status + " for " + url);
      return r.json();
    }).then(function (j) {
      var fp = (j && j.orderbook_fp) || null;
      var legacy = (j && j.orderbook) || null;
      var yesRaw = fp ? (fp.yes_dollars || []) : (legacy ? (legacy.yes || []) : []);
      var noRaw = fp ? (fp.no_dollars || []) : (legacy ? (legacy.no || []) : []);
      var toLevels = function (arr, legacyCents) {
        return (arr || []).map(function (d) {
          var p = Array.isArray(d) ? d[0] : d.price;
          var q = Array.isArray(d) ? d[1] : d.quantity;
          var price = Number(p);
          if (legacyCents && isFinite(price)) price = price / 100;   /* cents -> dollars */
          return [Math.round(price * 10000) / 10000, Number(q) || 0];
        }).filter(function (d) { return isFinite(d[0]); });
      };
      var yesBids = toLevels(yesRaw, !fp).sort(function (a, b) { return b[0] - a[0]; });
      var noBids = toLevels(noRaw, !fp).sort(function (a, b) { return b[0] - a[0]; });
      var asks = noBids.map(function (d) { return [Math.round((1 - d[0]) * 10000) / 10000, d[1]]; })
        .sort(function (a, b) { return a[0] - b[0]; });
      var bidContracts = yesBids.reduce(function (s, d) { return s + d[1]; }, 0);
      var askContracts = asks.reduce(function (s, d) { return s + d[1]; }, 0);
      var bestBid = yesBids.length ? yesBids[0][0] : null;
      var bestAsk = asks.length ? asks[0][0] : null;
      return {
        ticker: ticker, raw_request: url,
        yes_bids: yesBids, no_bids: noBids, derived_yes_asks: asks,
        best_yes_bid: bestBid, best_yes_ask_derived: bestAsk,
        yes_bid_contracts: bidContracts, derived_ask_contracts: askContracts,
        spread_derived: (bestBid !== null && bestAsk !== null)
          ? Math.round((bestAsk - bestBid) * 10000) / 10000 : null,
      };
    });
  };

  /* ---------------- nav ---------------- */
  KR.mountNav = function () {
    var t = document.querySelector(".navtoggle");
    var n = document.querySelector("nav.main");
    if (t && n) t.addEventListener("click", function () { n.classList.toggle("open"); });
  };

  /* ---------------- staleness banner ---------------- */
  KR.staleness = function (el, generatedAtUtc) {
    if (!el) return;
    if (!generatedAtUtc) {
      el.innerHTML = '<span class="bad">No snapshot yet.</span> Waiting for the data workflow to run.';
      return;
    }
    var age = (Date.now() - new Date(generatedAtUtc).getTime()) / 60000;
    var cls = age > 60 ? "warn" : "ok";
    el.innerHTML = 'Snapshot <span class="' + cls + '">' + KR.when(generatedAtUtc) + "</span>" +
      " (" + KR.ago(generatedAtUtc) + ") · refreshes every 10 min via GitHub Actions";
  };

  window.KR = KR;
  document.addEventListener("DOMContentLoaded", KR.mountNav);
})();
