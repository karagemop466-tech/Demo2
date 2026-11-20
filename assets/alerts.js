/* Live alert desk — two scrolling chats of sharp contract-price swings.
 *
 * WHY THIS FILE EXISTS
 *   The brief asks for a live alerting system on sudden swings of >= $0.10 in either
 *   direction, as two scrolling chats: one with all events, one filtered to the events
 *   the desk's model screen rates as high ROI. This file implements exactly that on the
 *   canonical dashboard, on top of the helpers in assets/site.js.
 *
 * WHERE THE NUMBERS COME FROM (official fields, nothing invented)
 *   - Swings are computed from the official `last_price_dollars` of the same market,
 *     compared between two consecutive observations.
 *   - Two observation streams, clearly labelled on every line:
 *       "live"    -> a REST poll of the official demo Trade API,
 *                    GET /markets?tickers=<top in-scope markets>&limit=100
 *                    (the documented `tickers` filter; verified live 2026-11-20)
 *       "snapshot"-> the collector's own tick history in data/history.json, which is
 *                    sampled every 10 minutes, so these are coarser.
 *   - A line never appears without a price on both sides of the move. If the API
 *     returns no usable price, no alert is emitted — the desk does not infer a move.
 *   - Resolution: an alert line carries the market's official `result` (yes/no) once the
 *     market settles, and a settlement line is appended when that happens.
 *
 * WHAT IS A MODEL, NOT A FACT
 *   The "high ROI" feed is a HEURISTIC SCREEN over official fields. It is not a forecast,
 *   and demo prices are not real prices (Kalshi's own demo-environment warning). The
 *   thresholds are printed on the page and in the chat header so they can be audited.
 */
(function () {
  "use strict";

  var KR = window.KR;
  if (!KR) return;

  var A = (KR.alerts = {});

  /* ---------------- tunables (all disclosed on the page) ---------------- */
  A.SWING = 0.10;             // the brief's threshold: >= $0.10 in either direction
  A.EPS = 1e-9;               // binary floats: 1.00 - 0.90 is 0.09999999999999998, and a
                              // real $0.10 move must not be silently missed because of it
  A.POLL_MS = 20000;          // live poll interval
  A.TOP_N = 40;               // how many in-scope markets the desk polls: the highest
                              // estimated-dollar-volume ones, so the poll stays small
  A.MAX_LINES = 200;          // lines kept per chat, oldest dropped
  A.MIN_VOLUME_24H = 100;     // screen: contracts traded in 24 h
  A.MAX_DAYS_TO_CLOSE = 30;   // screen: only near-dated events
  A.ROI_ENTRY_MAX = 0.45;     // screen: entry price at or below this -> >= 122% potential
  A.DEMO_REST = "https://external-api.demo.kalshi.co/trade-api/v2";

  A.SCREEN_TEXT =
    "screen: move >= $0.10, entry price <= $0.45 on the side the move favours, " +
    "volume_24h_fp >= " + A.MIN_VOLUME_24H + ", closes within " + A.MAX_DAYS_TO_CLOSE + " days";

  var state = {
    snap: null,
    history: null,
    watch: [],            // tickers in the polled set
    info: {},            // ticker -> {topic, title, marketUrl, closeTime, series}
    lastPrice: {},       // ticker -> last observed official price
    lines: [],           // all alerts, newest first
    seen: {},           // key -> true, so one move is not announced twice
    seq: 0,
    mode: "starting",    // live | fallback | offline | starting
    lastPoll: null,
    timer: null,
    running: false,
  };

  /* ---------------- helpers ---------------- */
  function fnum(v) {
    var n = Number(v);
    return v === null || v === undefined || v === "" || !isFinite(n) ? null : n;
  }

  function daysToClose(iso) {
    if (!iso) return null;
    var t = new Date(iso).getTime();
    if (!isFinite(t)) return null;
    return (t - Date.now()) / 86400000;
  }

  /* The side the move favours, and its entry price.
     A UP move means the YES price rose -> a cheap NO is the high-ROI side, entered at
     1 - p. A DOWN move means the YES price fell -> a cheap YES is the high-ROI side,
     entered at p. Binary-market equivalence, labelled as derived wherever it is shown. */
  function favouredSide(dir, yesPrice) {
    if (dir === "up") return { side: "NO", entry: 1 - yesPrice, yesPrice: yesPrice };
    return { side: "YES", entry: yesPrice, yesPrice: yesPrice };
  }

  /* ---------------- the model screen ---------------- */
  /* Deterministic, auditable, and stated on the page. Returns null when the alert does
     not pass, with the reason so the chat header can explain a small feed. */
  A.screen = function (alert) {
    var p = fnum(alert.toV);
    if (p === null) return { ok: false, reason: "no price after the move" };
    var vol = fnum(alert.volume24h);
    if (vol === null || vol < A.MIN_VOLUME_24H)
      return { ok: false, reason: "24h volume below " + A.MIN_VOLUME_24H + " contracts" };
    /* Compute it here rather than trusting a caller-supplied derived field, so the
       screen is self-contained and a missing close time can never pass by omission. */
    var dtc = alert.daysToClose;
    if (dtc === null || dtc === undefined || !isFinite(dtc)) dtc = daysToClose(alert.closeTime);
    if (dtc === null || dtc === undefined || !isFinite(dtc))
      return { ok: false, reason: "no close time returned" };
    if (dtc > A.MAX_DAYS_TO_CLOSE)
      return { ok: false, reason: "closes further than " + A.MAX_DAYS_TO_CLOSE + " days out" };
    var side = favouredSide(alert.dir, p);
    if (side.entry > A.ROI_ENTRY_MAX)
      return { ok: false, reason: "entry above $" + A.ROI_ENTRY_MAX.toFixed(2) };
    /* potential ROI if that side resolves: payout 1.00 against an entry of q.
       Potential, not a forecast — the market may resolve the other way. */
    var potential = side.entry > 0 ? (1 / side.entry - 1) * 100 : null;
    return { ok: true, reason: "passes", side: side.side, potentialROI: potential };
  };

  /* ---------------- alert construction ---------------- */
  function makeAlert(ticker, fromV, toV, ts, source) {
    var info = state.info[ticker] || {};
    var change = toV - fromV;
    var alert = {
      id: ++state.seq,
      ticker: ticker,
      ts: ts,
      fromV: fromV,
      toV: toV,
      change: change,
      dir: change > 0 ? "up" : "down",
      source: source,
      topic: info.topic || "unmapped",
      title: info.title || ticker,
      marketUrl: info.marketUrl,
      series: info.series || null,
      closeTime: info.closeTime || null,
      result: null,
      settled: false,
      volume24h: fnum(info.volume24h),
    };
    alert.daysToClose = daysToClose(alert.closeTime);
    alert.screen = A.screen(alert);
    return alert;
  }

  /* ---------------- snapshot-derived alerts ---------------- */
  function seedFromHistory(hist) {
    var pts = (hist && hist.points) || {};
    var out = [];
    Object.keys(pts).forEach(function (ticker) {
      if (state.watch.indexOf(ticker) < 0) return;
      var series = (pts[ticker] || []).map(function (p) {
        return { t: KR.pointTime(p), v: fnum(p.last) };
      }).filter(function (p) { return p.v !== null; });
      var jumps = KR.detectJumps(series, A.SWING);
      jumps.forEach(function (j) {
        var key = ticker + "|" + j.fromTime + "|" + j.toV;
        if (state.seen[key]) return;
        state.seen[key] = true;
        out.push(makeAlert(ticker, j.fromV, j.toV, j.toTime, "snapshot"));
      });
    });
    out.sort(function (a, b) { return b.ts - a.ts; });
    out.forEach(function (a) { state.lines.push(a); });
    state.lines.sort(function (a, b) { return b.ts - a.ts; });
  }

  /* ---------------- live poll ---------------- */
  function fallbackUrl() {
    return A.DEMO_REST + "/markets?status=open&limit=100";
  }

  function applyRow(row) {
    var ticker = row.ticker || row.market_ticker;
    if (!ticker) return null;
    var price = fnum(row.last_price_dollars);
    if (price === null) return null;
    state.info[ticker] = {
      topic: (state.info[ticker] || {}).topic,
      title: row.title || (state.info[ticker] || {}).title || ticker,
      marketUrl: row.market_url || (state.info[ticker] || {}).marketUrl ||
        (ticker ? A.DEMO_REST + "/markets/" + encodeURIComponent(ticker) : null),
      closeTime: row.close_time || (state.info[ticker] || {}).closeTime || null,
      series: (state.info[ticker] || {}).series || null,
      volume24h: row.volume_24h_fp !== undefined ? row.volume_24h_fp :
        (state.info[ticker] || {}).volume24h,
    };
    var prev = state.lastPrice[ticker];
    state.lastPrice[ticker] = price;
    var alert = null;
    if (prev !== undefined && Math.abs(price - prev) >= A.SWING - A.EPS) {
      var key = ticker + "|" + prev + "|" + price;
      if (!state.seen[key]) {
        state.seen[key] = true;
        alert = makeAlert(ticker, prev, price, Date.now(), "live");
        state.lines.push(alert);
      }
    }
    /* resolution: official `result` on the live row itself */
    var res = (row.result || "").toLowerCase();
    if (res === "yes" || res === "no") settle(ticker, res, row.settlement_value_dollars);
    return alert;
  }

  function settle(ticker, result, settlementValue) {
    state.lines.forEach(function (a) {
      if (a.ticker !== ticker || a.settled) return;
      a.result = result;
      a.settled = true;
      a.settlementValue = settlementValue;
    });
  }

  A.pollOnce = async function () {
    /* Chunk the ticker list: one unrecognised ticker must not be able to fail the whole
       poll. Batches are requested sequentially (not in parallel) so a 20-second cycle
       cannot turn into a burst of requests against a rate-limited public endpoint. */
    var BATCH = 20;
    var batches = [];
    for (var i = 0; i < state.watch.length; i += BATCH) {
      batches.push(state.watch.slice(i, i + BATCH));
    }
    var rows = [];
    var anyOk = false;
    for (var b = 0; b < batches.length; b++) {
      var url = A.DEMO_REST + "/markets?tickers=" +
        encodeURIComponent(batches[b].join(",")) + "&limit=100";
      try {
        var r = await fetch(url, { cache: "no-store" });
        if (r.ok) {
          var j = await r.json();
          rows = rows.concat(j.markets || []);
          anyOk = true;
        }
      } catch (e) { /* this batch failed; try the rest */ }
    }
    if (!anyOk) {
      /* documented fallback: the open feed, filtered to the watched tickers */
      try {
        var r2 = await fetch(fallbackUrl(), { cache: "no-store" });
        if (r2.ok) {
          var j2 = await r2.json();
          var all = j2.markets || [];
          var wanted = {};
          state.watch.forEach(function (t) { wanted[t] = 1; });
          rows = all.filter(function (m) { return wanted[m.ticker || m.market_ticker]; });
          anyOk = rows.length > 0;
          if (anyOk) state.mode = "fallback";
        }
      } catch (e) { /* offline */ }
    }
    if (!anyOk) {
      // Transitioning to offline must be VISIBLE: repaint so the banner stops claiming
      // live polling rather than leaving the last successful state on screen.
      state.mode = "offline";
      render();
      return;
    }
    state.mode = state.mode === "fallback" ? "fallback" : "live";
    state.lastPoll = Date.now();
    rows.forEach(applyRow);
    render();
  };

  /* ---------------- rendering ---------------- */
  function chatLineHtml(a) {
    var res = a.settled
      ? '<span class="pill ' + KR.esc(a.result) + '">' + KR.esc(a.result.toUpperCase()) + "</span>"
      : '<span class="pill open">open</span>';
    var dirPill = '<span class="pill ' + a.dir + '">' +
      (a.dir === "up" ? "▲ up" : "▼ down") + "</span>";
    var mag = KR.usd(Math.abs(a.change), 4);
    var fromTo = KR.usd(a.fromV, 4) + " → " + KR.usd(a.toV, 4);
    var srcTag = a.source === "live"
      ? '<span class="pill ok">live poll</span>'
      : '<span class="pill">snapshot (10-min samples)</span>';
    var screenTag = a.screen && a.screen.ok
      ? '<span class="pill up">model screen · potential ROI ' +
        (a.screen.potentialROI === null || a.screen.potentialROI === undefined
          ? "n/a (entry at $0.00)"
          : KR.num(Math.round(a.screen.potentialROI), 0) + "%") + "</span>"
      : (a.screen ? '<span class="pill muted" title="' + KR.esc(a.screen.reason) +
        '">screen: ' + KR.esc(a.screen.reason) + "</span>" : "");
    var link = KR.link(a.marketUrl, "market", "chat-link");
    var title = KR.esc(a.title && a.title.length > 60 ? a.title.slice(0, 58) + "…" : a.title);
    return '<div class="chatline' + (a.settled ? " resolved" : "") + '">' +
      '<span class="chat-time">' + KR.when(new Date(a.ts).toISOString()) + "</span>" +
      KR.topicPill(a.topic) + dirPill +
      '<span class="chat-mag">' + mag + "</span>" +
      '<span class="chat-mkt">' + link + " · " + KR.esc(a.ticker) + "</span>" +
      '<span class="chat-title muted">' + title + "</span>" +
      '<span class="chat-px">' + fromTo + "</span>" +
      res + srcTag + screenTag +
      '<a class="chat-ctx" href="https://news.google.com/search?q=' +
      encodeURIComponent((a.title || a.ticker) + " Kalshi") +
      '" target="_blank" rel="noopener">possible context <span class="pill flag">not an official source</span></a>' +
      "</div>";
  }

  function render() {
    var all = state.lines.slice().sort(function (a, b) { return b.ts - a.ts; });
    if (all.length > A.MAX_LINES) all = all.slice(0, A.MAX_LINES);
    var screened = all.filter(function (a) { return a.screen && a.screen.ok; });
    paint("alertAll", all, "No alert yet — no in-scope market has moved >= $0.10 between two " +
      "consecutive official price points.");
    paint("alertModel", screened, "Nothing passed the model screen yet. Thresholds are printed in " +
      "the chat header; a pass is not a forecast.");
    var c1 = document.getElementById("alertAllCount");
    if (c1) {
      c1.textContent = all.length
        ? "· " + all.length + " line" + (all.length !== 1 ? "s" : "")
          + " · " + all.filter(function (a) { return a.settled; }).length + " settled"
          + " · " + all.filter(function (a) { return a.source === "live"; }).length + " live"
        : "";
    }
    var c2 = document.getElementById("alertModelCount");
    if (c2) {
      c2.textContent = screened.length
        ? "· " + screened.length + " pass the screen of " + all.length
        : "";
    }
    var st = document.getElementById("alertStatus");
    if (st) {
      var last = state.lastPoll ? KR.ago(new Date(state.lastPoll).toISOString()) : "never";
      var mode = {
        live: "polling the official demo API",
        fallback: "using the documented open-feed fallback",
        offline: "live polling unavailable — snapshot-derived alerts only",
        starting: "starting",
      }[state.mode] || state.mode;
      st.innerHTML = "<b>" + mode + "</b> · polled " + state.watch.length + " in-scope markets · " +
        "every " + Math.round(A.POLL_MS / 1000) + "s · last poll " + last +
        ' · <button class="btn sm secondary" id="alertPollNow">poll now</button>' +
        ' <span class="muted">(data: official <code>last_price_dollars</code>; the cause of a move ' +
        "is not returned by the API, so links point at the market itself — <a href=\"pages/flagged.html\">F13</a>)</span>";
      var btn = document.getElementById("alertPollNow");
      if (btn) btn.addEventListener("click", function () { A.pollOnce(); });
    }
  }

  function paint(id, rows, empty) {
    var el = document.getElementById(id);
    if (!el) return;
    if (!rows.length) {
      el.innerHTML = '<div class="empty">' + KR.esc(empty) + "</div>";
      return;
    }
    el.innerHTML = rows.map(chatLineHtml).join("");
    el.scrollTop = 0;   // newest first: keep the newest line visible
  }

  /* ---------------- init ---------------- */
  A.init = async function (opts) {
    opts = opts || {};
    if (state.running) return;
    state.running = true;
    var status = document.getElementById("alertStatus");
    try {
      var snap = await KR.snapshot();
      state.snap = snap;
      var markets = (snap.markets || []).slice().sort(function (a, b) {
        return (b.est_dollar_volume || 0) - (a.est_dollar_volume || 0);
      });
      var byTicker = {};
      markets.forEach(function (m) {
        if (!m.market_ticker) return;
        byTicker[m.market_ticker] = m;
        state.info[m.market_ticker] = {
          topic: m.topic,
          title: m.market_title || m.market_ticker,
          marketUrl: m.market_url,
          closeTime: m.close_time || null,
          series: m.series_ticker || null,
          volume24h: m.volume_24h_fp,
        };
      });
      // Bound the polled set to the highest-estimated-dollar-volume in-scope markets.
      state.watch = Object.keys(byTicker).slice(0, A.TOP_N);
      /* start from the collector's own tick history so the chat is not empty before the
         first poll; those lines are labelled "snapshot" so nobody reads them as live. */
      try {
        state.history = await KR.history();
        markets.forEach(function (m) {
          if (m.last_price_dollars !== undefined && m.last_price_dollars !== "") {
            var n = fnum(m.last_price_dollars);
            if (n !== null) state.lastPrice[m.market_ticker] = n;
          }
        });
        seedFromHistory(state.history);
      } catch (e) { /* history is optional; live polling still works */ }

      /* apply any known resolutions to lines already in the chat */
      var resolutions = [];
      try {
        var r = await KR.resolutions();
        resolutions = (r && r.resolutions) || [];
      } catch (e) { /* optional */ }
      resolutions.forEach(function (res) {
        if (res && res.market_ticker) {
          settle(res.market_ticker, String(res.result || "").toLowerCase(), res.settlement_value_dollars);
        }
      });

      render();
      if (opts.poll !== false && !/alerts=off/.test(window.location.search)) {
        await A.pollOnce();
        state.timer = window.setInterval(function () { A.pollOnce(); }, A.POLL_MS);
      } else if (opts.poll === false) {
        state.mode = "offline";
        render();
      }
    } catch (e) {
      if (status) {
        status.innerHTML = '<span class="bad">Alert desk could not start: ' + KR.esc(e.message) + "</span>";
      }
    }
  };
})();
