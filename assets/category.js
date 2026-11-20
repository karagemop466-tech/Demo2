/* Category page: full in-scope table + data-derived findings for one topic. */
(function () {
  "use strict";
  var K = window.K, KALSHI = K.KALSHI;
  var $ = function (id) { return document.getElementById(id); };
  var TOPIC = document.body.getAttribute("data-topic");
  var state = { rows: [], meta: null };

  function stats(rows) {
    var turnover = rows.map(function (r) { return Number(r.turnover_dollars) || 0; }).sort(function (a, b) { return b - a; });
    var sum = turnover.reduce(function (a, b) { return a + b; }, 0);
    var top3 = turnover.slice(0, 3).reduce(function (a, b) { return a + b; }, 0);
    var median = turnover.length ? turnover[Math.floor(turnover.length / 2)] : 0;
    var bySeries = {};
    rows.forEach(function (r) {
      var s = r.series_ticker || "unknown";
      bySeries[s] = (bySeries[s] || 0) + 1;
    });
    var seriesRows = Object.keys(bySeries).map(function (k) { return { s: k, n: bySeries[k] }; })
      .sort(function (a, b) { return b.n - a.n; });
    var byCat = {};
    rows.forEach(function (r) {
      var c = r.series_category || "unclassified";
      byCat[c] = (byCat[c] || 0) + 1;
    });
    return {
      count: rows.length, sum: sum, median: median, top3Share: sum ? top3 / sum : 0,
      seriesRows: seriesRows, byCat: byCat,
      priced: rows.filter(function (r) { return r.last_price_dollars !== null; }).length,
      settled: rows.filter(function (r) { return r.result; }).length
    };
  }

  function render() {
    var tb = $("catRows");
    if (!tb) return;
    var st = stats(state.rows);
    $("statCount").textContent = K.fmtNum(st.count);
    $("statTurnover").textContent = K.money(st.sum, 0);
    $("statMedian").textContent = K.money(st.median, 0);
    $("statTop3").textContent = K.pct(st.top3Share, 0);
    $("statSeries").textContent = K.fmtNum(st.seriesRows.length);

    tb.innerHTML = state.rows.map(function (m, i) {
      return "<tr>" +
        '<td class="num">' + (i + 1) + "</td>" +
        "<td><b>" + K.esc(m.title || m.ticker) + "</b>" + (m.subtitle ? "<br><span class='srcline'>" + K.esc(m.subtitle) + "</span>" : "") + "</td>" +
        "<td>" + K.esc(m.ticker) + "<br><span class='srcline'>" + K.esc(m.event_ticker || "") + "</span></td>" +
        "<td>" + K.esc(m.series_ticker || "—") + "<br><span class='srcline'>" + K.esc(m.series_category || "") + "</span></td>" +
        '<td class="num">' + K.money(m.last_price_dollars, 4) + "</td>" +
        '<td class="num">' + K.money(m.turnover_dollars, 0) + "</td>" +
        '<td class="num">' + K.money(m.turnover_24h_dollars, 0) + "</td>" +
        '<td class="num">' + K.money(m.open_interest_value_dollars, 0) + "</td>" +
        '<td class="num">' + (m.resting_liquidity_notional_dollars === null || m.resting_liquidity_notional_dollars === undefined ? "—" : K.money(m.resting_liquidity_notional_dollars, 0)) + "</td>" +
        "<td>" + K.money(m.yes_bid_dollars, 4) + " / " + K.money(m.yes_ask_dollars, 4) + "</td>" +
        "<td>" + K.esc(m.close_time ? m.close_time.slice(0, 16).replace("T", " ") : "—") + "</td>" +
        "<td>" + (m.result ? '<span class="pill res-' + K.esc(m.result) + '">' + K.esc(m.result.toUpperCase()) + "</span>" : '<span class="badge-open">open</span>') + "</td>" +
        "<td>" + K.marketLink(m.ticker, "market") + "<br>" + K.apiLink(m.links && m.links.api_market, "api") + "</td>" +
        '<td><a class="btn secondary" href="../index.html?ticker=' + encodeURIComponent(m.ticker) + '">Chart</a></td>' +
        "</tr>";
    }).join("") || '<tr><td colspan="13" class="muted">No in-scope markets in the current snapshot.</td></tr>';

    var f = $("findingsBody");
    if (f) {
      f.innerHTML =
        "<tr><td>Markets in scope</td><td class='num'>" + K.fmtNum(st.count) + "</td>" +
        "<td>Counted from the snapshot produced by <code>GET /markets?status=open</code> and classified by the rules on the Methodology page.</td>" +
        "<td><a href='" + KALSHI.docs.getMarkets + "' target='_blank' rel='noopener'>Get Markets</a></td></tr>" +
        "<tr><td>Aggregate dollar turnover</td><td class='num'>" + K.money(st.sum, 0) + "</td>" +
        "<td>Sum over in-scope markets of volume_fp × last_price_dollars (computed on this site).</td>" +
        "<td><a href='" + KALSHI.docs.getMarkets + "' target='_blank' rel='noopener'>Get Markets</a></td></tr>" +
        "<tr><td>Median market turnover</td><td class='num'>" + K.money(st.median, 0) + "</td>" +
        "<td>Middle value of the per-market turnover distribution — used instead of the mean because turnover is heavily skewed.</td>" +
        "<td><a href='" + KALSHI.docs.getMarkets + "' target='_blank' rel='noopener'>Get Markets</a></td></tr>" +
        "<tr><td>Share of turnover in the top 3 markets</td><td class='num'>" + K.pct(st.top3Share, 0) + "</td>" +
        "<td>Concentration check: a high share means the topic is driven by a few markets rather than broad participation.</td>" +
        "<td><a href='" + KALSHI.docs.getMarkets + "' target='_blank' rel='noopener'>Get Markets</a></td></tr>" +
        "<tr><td>Distinct series</td><td class='num'>" + K.fmtNum(st.seriesRows.length) + "</td>" +
        "<td>Number of official Kalshi series that feed this topic.</td>" +
        "<td><a href='" + KALSHI.docs.seriesList + "' target='_blank' rel='noopener'>Get Series List</a></td></tr>" +
        "<tr><td>Official categories represented</td><td>" + Object.keys(st.byCat).map(function (c) {
          return "<span class='pill'>" + K.esc(c) + " (" + st.byCat[c] + ")</span>";
        }).join(" ") + "</td><td>Categories come from the official series record, not from keyword guessing.</td>" +
        "<td><a href='" + KALSHI.docs.series + "' target='_blank' rel='noopener'>Get Series</a></td></tr>" +
        "<tr><td>Largest series in this topic</td><td>" + st.seriesRows.slice(0, 6).map(function (s) {
          return "<span class='pill'>" + K.esc(s.s) + " (" + s.n + ")</span>";
        }).join(" ") + "</td><td>Count of in-scope markets per series.</td>" +
        "<td><a href='" + KALSHI.docs.seriesList + "' target='_blank' rel='noopener'>Get Series List</a></td></tr>";
    }
  }

  function init() {
    var status = $("catStatus");
    K.loadJSON("markets.json").then(function (d) {
      state.meta = d.meta;
      state.rows = (d.markets || []).filter(function (m) { return m.topic === TOPIC; })
        .sort(function (a, b) { return (b.turnover_dollars || 0) - (a.turnover_dollars || 0); });
      render();
      if (status) {
        status.innerHTML = '<span class="ok">Snapshot</span> ' + K.esc(K.tsHuman(d.meta.generated_at)) +
          " · " + K.fmtNum(state.rows.length) + " in-scope markets · source: " +
          '<a href="' + KALSHI.docs.getMarkets + '" target="_blank" rel="noopener">Get Markets</a>';
      }
    }).catch(function (e) {
      if (status) status.innerHTML = '<span class="bad">Snapshot unavailable: ' + K.esc(e.message) + "</span>";
      render();
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
