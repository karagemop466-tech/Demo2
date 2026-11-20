/* ==========================================================================
   Kalshi Demo Monitor - price chart.
   X axis = time, Y axis = contract price (US dollars per contract).

   Two verified data sources are combined:
     1. GET /series/{series}/markets/{ticker}/candlesticks
        Official OHLC history. period_interval is 1, 60 or 1440 minutes.
        https://docs.kalshi.com/api-reference/market/get-market-candlesticks
     2. Live REST snapshots of GET /markets/{ticker} taken by this page while it
        is open (the newest point is always the most recent snapshot).

   The WebSocket feed is NOT used: Kalshi requires authentication headers on the
   WebSocket handshake, and a browser page cannot set custom headers on a
   WebSocket. https://docs.kalshi.com/getting_started/quick_start_websockets
   ========================================================================== */
(function (global) {
  'use strict';

  var PALETTE = {
    grid: '#e6ecf3',
    axis: '#8a99ad',
    text: '#4a5768',
    line: '#0d7a5f',
    fill: 'rgba(13,122,95,0.12)',
    live: '#1f6feb',
    cross: '#1f6feb',
    bg: '#ffffff',
  };

  function fmtTime(ts, spanSeconds) {
    var d = new Date(ts * 1000);
    var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
    if (spanSeconds <= 6 * 3600) {
      return pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes()) + ' UTC';
    }
    if (spanSeconds <= 3 * 86400) {
      return pad(d.getUTCMonth() + 1) + '/' + pad(d.getUTCDate()) + ' ' + pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes());
    }
    return pad(d.getUTCDate()) + '/' + pad(d.getUTCMonth() + 1) + '/' + d.getUTCFullYear();
  }

  function niceStep(range, targetTicks) {
    if (!(range > 0)) return 1;
    var raw = range / targetTicks;
    var mag = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10));
    var norm = raw / mag;
    var step = norm >= 5 ? 5 : norm >= 2 ? 2 : 1;
    return step * mag;
  }

  /**
   * Draw the chart.
   * points: [{ t: unix seconds, p: price in dollars, live?: true }]
   */
  function draw(canvas, points, opts) {
    opts = opts || {};
    var dpr = global.devicePixelRatio || 1;
    var cssW = canvas.clientWidth || 600;
    var cssH = canvas.clientHeight || 330;
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    var ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);
    ctx.fillStyle = PALETTE.bg;
    ctx.fillRect(0, 0, cssW, cssH);

    var padL = 52, padR = 14, padT = 16, padB = 30;
    var plotW = Math.max(10, cssW - padL - padR);
    var plotH = Math.max(10, cssH - padT - padB);

    if (!points || points.length === 0) {
      ctx.fillStyle = PALETTE.text;
      ctx.font = '13px system-ui, sans-serif';
      ctx.fillText(opts.emptyText || 'No price history yet.', padL, padT + 20);
      return;
    }

    var tMin = points[0].t;
    var tMax = points[points.length - 1].t;
    if (tMax - tMin < 1) tMax = tMin + 1;

    var pMin = Infinity, pMax = -Infinity;
    points.forEach(function (pt) {
      if (pt.p < pMin) pMin = pt.p;
      if (pt.p > pMax) pMax = pt.p;
    });
    if (opts.minPrice !== undefined && opts.minPrice !== null) pMin = Math.min(pMin, opts.minPrice);
    if (opts.maxPrice !== undefined && opts.maxPrice !== null) pMax = Math.max(pMax, opts.maxPrice);
    var span = pMax - pMin;
    if (span < 0.02) { pMin = Math.max(0, pMin - 0.01); pMax = Math.min(1, pMax + 0.01); span = pMax - pMin; }
    if (span <= 0) { pMin = 0; pMax = 1; span = 1; }
    var padY = span * 0.12;
    pMin = Math.max(0, pMin - padY);
    pMax = Math.min(1, pMax + padY);

    var x = function (t) { return padL + plotW * ((t - tMin) / (tMax - tMin)); };
    var y = function (p) { return padT + plotH * (1 - (p - pMin) / (pMax - pMin)); };

    // grid + y labels
    var yStep = niceStep(pMax - pMin, 5);
    ctx.font = '11px system-ui, sans-serif';
    ctx.textBaseline = 'middle';
    for (var v = Math.ceil(pMin / yStep) * yStep; v <= pMax + 1e-9; v += yStep) {
      var yy = y(v);
      ctx.strokeStyle = PALETTE.grid;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(padL + plotW, yy); ctx.stroke();
      ctx.fillStyle = PALETTE.text;
      ctx.textAlign = 'right';
      ctx.fillText('$' + v.toFixed(yStep < 0.05 ? 3 : 2), padL - 7, yy);
    }

    // x labels
    var xStep = niceStep(tMax - tMin, 6);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    for (var tv = Math.ceil(tMin / xStep) * xStep; tv <= tMax + 1e-9; tv += xStep) {
      var xx = x(tv);
      ctx.strokeStyle = PALETTE.grid;
      ctx.beginPath(); ctx.moveTo(xx, padT); ctx.lineTo(xx, padT + plotH); ctx.stroke();
      ctx.fillStyle = PALETTE.text;
      ctx.fillText(fmtTime(tv, tMax - tMin), xx, padT + plotH + 7);
    }

    // axis lines
    ctx.strokeStyle = PALETTE.axis;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, padT); ctx.lineTo(padL, padT + plotH); ctx.lineTo(padL + plotW, padT + plotH);
    ctx.stroke();

    // area + line
    ctx.beginPath();
    points.forEach(function (pt, i) {
      var px = x(pt.t), py = y(pt.p);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    ctx.lineTo(x(points[points.length - 1].t), padT + plotH);
    ctx.lineTo(x(points[0].t), padT + plotH);
    ctx.closePath();
    ctx.fillStyle = PALETTE.fill;
    ctx.fill();

    ctx.beginPath();
    points.forEach(function (pt, i) {
      var px = x(pt.t), py = y(pt.p);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    ctx.strokeStyle = PALETTE.line;
    ctx.lineWidth = 2;
    ctx.stroke();

    // live marker on the newest point
    var last = points[points.length - 1];
    if (last.live) {
      ctx.fillStyle = PALETTE.live;
      ctx.beginPath();
      ctx.arc(x(last.t), y(last.p), 4, 0, Math.PI * 2);
      ctx.fill();
    }

    // y axis label
    ctx.save();
    ctx.translate(13, padT + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = PALETTE.text;
    ctx.font = '11px system-ui, sans-serif';
    ctx.fillText('contract price (US$)', 0, 0);
    ctx.restore();

    // x axis label
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    ctx.fillStyle = PALETTE.text;
    ctx.fillText(opts.xLabel || 'time', padL + plotW, cssH - 2);
  }

  /** Attach hover crosshair + tooltip to a chart canvas. */
  function attachHover(canvas, getPoints, tooltipEl) {
    function hide() { if (tooltipEl) tooltipEl.style.display = 'none'; }
    canvas.addEventListener('mouseleave', hide);
    canvas.addEventListener('mousemove', function (ev) {
      var pts = getPoints();
      if (!pts || pts.length < 2 || !tooltipEl) { hide(); return; }
      var rect = canvas.getBoundingClientRect();
      var mx = ev.clientX - rect.left;
      var dpr = global.devicePixelRatio || 1;
      var padL = 52, padR = 14;
      var plotW = Math.max(10, rect.width - padL - padR);
      var tMin = pts[0].t, tMax = pts[pts.length - 1].t;
      if (tMax <= tMin) { hide(); return; }
      var frac = Math.min(1, Math.max(0, (mx - padL) / plotW));
      var target = tMin + frac * (tMax - tMin);
      var best = pts[0], bestD = Infinity;
      pts.forEach(function (p) {
        var dd = Math.abs(p.t - target);
        if (dd < bestD) { bestD = dd; best = p; }
      });
      var d = new Date(best.t * 1000);
      tooltipEl.style.display = 'block';
      tooltipEl.style.left = Math.min(rect.width - 150, Math.max(6, mx + 12)) + 'px';
      tooltipEl.style.top = '10px';
      tooltipEl.innerHTML = '<strong>$' + best.p.toFixed(3) + '</strong><br>' +
        d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
      void dpr;
    });
  }

  global.KalshiChart = { draw: draw, attachHover: attachHover, fmtTime: fmtTime };
}(window));
