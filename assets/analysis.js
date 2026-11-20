/* Trade analysis: categorise fills, measure results against real resolutions, derive strategies. */
(function () {
  "use strict";
  var K = window.K, KALSHI = K.KALSHI;
  var $ = function (id) { return document.getElementById(id); };
  var state = { fills: [], resolved: {}, topics: {}, result: null, source: "" };

  function buildMaps() {
    var p1 = K.loadJSON("markets.json").then(function (d) {
      (d.markets || []).forEach(function (m) { if (m.topic) state.topics[m.ticker] = m.topic; });
    }).catch(function () {});
    var p2 = K.loadJSON("resolved.json").then(function (d) {
      (d.resolved || []).forEach(function (m) {
        if (m.topic) state.topics[m.ticker] = m.topic;
        state.resolved[m.ticker] = m;
      });
    }).catch(function () {});
    return Promise.all([p1, p2]);
  }

  function render() {
    var a = K.analysis.analyzeFills(state.fills, state.resolved, state.topics);
    state.result = a;
    $("anSource").innerHTML = state.source;
    $("anEmpty").style.display = a.rows.length ? "none" : "block";

    $("kFills").textContent = K.fmtNum(a.summary.fills);
    $("kResolved").textContent = K.fmtNum(a.summary.resolved);
    $("kWin").textContent = a.summary.winRate === null ? "—" : K.pct(a.summary.winRate, 0);
    $("kPnl").textContent = K.money(a.summary.totalPnl, 4);
    $("kFees").textContent = K.money(a.summary.totalFees, 4);

    function groupTable(rows, dimName) {
      return "<tr><td>" + K.esc(dimName) + "</td>" +
        rows.map(function (g) {
          return "<tr><td>" + K.esc(g.key) + "</td><td class='num'>" + g.count + "</td><td class='num'>" + g.resolved + "</td>" +
            "<td class='num'>" + (g.winRate === null ? "—" : K.pct(g.winRate, 0)) + "</td>" +
            "<td class='num'>" + (g.avgPnl === null ? "—" : K.money(g.avgPnl, 4)) + "</td>" +
            "<td class='num'>" + (g.resolved ? K.money(g.pnl, 4) : "—") + "</td></tr>";
        }).join("") + "</tbody>";
    }
    function wrap(header, rows, dim) {
      if (!rows.length) return "<tr><td colspan='6' class='muted'>No data.</td></tr>";
      return "<tr><th>" + K.esc(dim) + "</th><th class='num'>Fills</th><th class='num'>Resolved</th><th class='num'>Win rate</th>" +
        "<th class='num'>Avg P&amp;L / resolved fill</th><th class='num'>Total P&amp;L</th></tr>" + rows.map(function (g) {
          return "<tr><td>" + K.esc(g.key) + "</td><td class='num'>" + g.count + "</td><td class='num'>" + g.resolved + "</td>" +
            "<td class='num'>" + (g.winRate === null ? "—" : K.pct(g.winRate, 0)) + "</td>" +
            "<td class='num'>" + (g.avgPnl === null ? "—" : K.money(g.avgPnl, 4)) + "</td>" +
            "<td class='num'>" + (g.resolved ? K.money(g.pnl, 4) : "—") + "</td></tr>";
        }).join("");
    }

    $("byTopic").innerHTML = wrap("Topic", a.byTopic, "Topic");
    $("bySide").innerHTML = wrap("Outcome side", a.bySide, "Outcome side");
    $("byBucket").innerHTML = wrap("Price band", a.byBucket, "Price band");
    $("byHour").innerHTML = wrap("Hour of day (UTC)", a.byHour, "Hour (UTC)");
    $("byMaker").innerHTML = wrap("Taker / maker", a.byMaker, "Liquidity role");

    $("tradesBody").innerHTML = a.rows.length ? a.rows.map(function (r) {
      return "<tr><td>" + K.esc(r.time || "—") + "</td><td>" + K.marketLink(r.ticker) + "</td>" +
        "<td>" + K.topicPill(r.topic) + "</td><td>" + K.esc(r.outcome || "—") + "</td>" +
        "<td>" + K.esc(r.bookSide || "—") + "</td><td class='num'>" + K.fmtNum(r.contracts, 2) + "</td>" +
        "<td class='num'>" + K.money(r.price, 4) + "</td><td>" + K.esc(r.bucket) + "</td>" +
        "<td>" + (r.result ? '<span class="pill res-' + K.esc(r.result) + '">' + K.esc(r.result.toUpperCase()) + "</span>" : '<span class="badge-open">not settled</span>') + "</td>" +
        "<td class='num'>" + (r.pnl === null ? "—" : K.money(r.pnl, 4)) + "</td></tr>";
    }).join("") : '<tr><td colspan="10" class="muted">No fills yet.</td></tr>';

    var s = a.strategies;
    $("strategyBody").innerHTML = s.length ? s.map(function (x) {
      return "<tr><td>" + K.esc(x.dimension) + "</td><td>" + K.esc(x.segment) + "</td>" +
        "<td class='num'>" + x.fills + "</td><td class='num'>" + x.resolved + "</td>" +
        "<td class='num'>" + K.pct(x.winRate, 0) + "</td>" +
        "<td class='num'>" + K.money(x.avgPnl, 4) + "</td>" +
        "<td>" + K.esc(x.statement) + "</td></tr>";
    }).join("") : '<tr><td colspan="7" class="muted">No strategy is stated because fewer than three fills in any segment have ' +
      'resolved yet. A pattern is only written down when the evidence supports it — nothing is asserted in advance.</td></tr>';
  }

  function loadFromApi() {
    var out = $("anStatus");
    out.innerHTML = '<span class="muted">Loading fills…</span>';
    K.trading.signedFetch("/portfolio/fills?limit=200", "GET").then(function (j) {
      state.fills = j.fills || [];
      state.source = '<span class="ok">Live fills</span> from <code>GET /portfolio/fills</code> — ' +
        '<a href="' + KALSHI.docs.fills + '" target="_blank" rel="noopener">Get Fills</a>.';
      buildMaps().then(render);
    }).catch(function (e) {
      out.innerHTML = '<span class="bad">' + K.esc(e.message) + "</span>";
    });
  }

  function loadFromLog() {
    var log = K.getTradeLog().filter(function (x) { return x.kind === "fills" && x.fills; });
    if (!log.length) {
      $("anStatus").innerHTML = '<span class="warn">No fills have been cached in this browser yet. Place a demo order and ' +
        "press <b>Load portfolio</b>, or add demo credentials and press <b>Load fills from the API</b>.</span>";
      return;
    }
    var latest = log[0];
    state.fills = latest.fills;
    state.source = '<span class="ok">Cached fills</span> from this browser’s trade log (' + K.esc(latest.ts) + ").";
    buildMaps().then(render);
  }

  function init() {
    var b1 = $("loadFillsApi"), b2 = $("loadFillsLog");
    if (b1) b1.onclick = loadFromApi;
    if (b2) b2.onclick = loadFromLog;
    loadFromLog();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
