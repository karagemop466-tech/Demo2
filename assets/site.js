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
