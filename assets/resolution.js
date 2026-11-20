/* Resolution tracker: keep watching markets until they settle yes or no. */
(function () {
  "use strict";
  var K = window.K, KALSHI = K.KALSHI;
  var $ = function (id) { return document.getElementById(id); };
  var HISTORY_KEY = "kalshi.resolutions.v1";
  var state = { watch: [], history: [], live: {} };

  function getHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch (e) { return []; }
  }
  function setHistory(h) {
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, 500))); } catch (e) {}
  }

  function renderWatch() {
    var tb = $("watchRows");
    if (!tb) return;
    var watch = K.getWatch();
    state.watch = watch;
    $("watchCount").textContent = K.fmtNum(watch.length);
    tb.innerHTML = watch.length ? watch.map(function (w) {
      var live = state.live[w.ticker] || {};
      var settled = live.result || (w.result || "");
      return "<tr><td><b>" + K.esc(w.title || w.ticker) + "</b><br><span class='srcline'>" + K.esc(w.ticker) + "</span></td>" +
        "<td>" + K.topicPill(w.topic) + "</td>" +
        "<td>" + K.esc(live.status || w.status || "—") + "</td>" +
        "<td>" + K.money(live.last_price_dollars, 4) + "</td>" +
        "<td>" + K.esc(live.close_time ? live.close_time.slice(0, 16).replace("T", " ") : "—") + "</td>" +
        "<td>" + (settled ? '<span class="pill res-' + K.esc(settled) + '">' + K.esc(String(settled).toUpperCase()) + "</span>"
          : '<span class="badge-open">still open</span>') + "</td>" +
        "<td>" + (live.settlement_value_dollars !== undefined && live.settlement_value_dollars !== null
          ? K.money(live.settlement_value_dollars, 4) : "—") + "</td>" +
        "<td>" + K.esc(live.settlement_ts ? live.settlement_ts.slice(0, 19).replace("T", " ") : "—") + "</td>" +
        "<td>" + K.marketLink(w.ticker, "market") + " · " + K.apiLink(KALSHI.rest + "/markets/" + encodeURIComponent(w.ticker), "api") + "</td>" +
        '<td><button class="secondary" data-unwatch="' + K.esc(w.ticker) + '">Stop watching</button></td></tr>';
    }).join("") : '<tr><td colspan="9" class="muted">Nothing watched yet. Use <b>Watch</b> on the ' +
      '<a href="../index.html">dashboard</a> to add a market here; this page then polls it until it settles.</td></tr>';

    tb.querySelectorAll("[data-unwatch]").forEach(function (b) {
      b.onclick = function () {
        var list = K.getWatch().filter(function (x) { return x.ticker !== b.dataset.unwatch; });
        K.setWatch(list);
        renderWatch();
      };
    });
  }

  function renderHistory() {
    var tb = $("historyRows");
    if (!tb) return;
    var h = state.history;
    $("historyCount").textContent = K.fmtNum(h.length);
    tb.innerHTML = h.length ? h.map(function (r) {
      return "<tr><td>" + K.esc(r.title || r.ticker) + "</td><td>" + K.topicPill(r.topic) + "</td>" +
        "<td>" + '<span class="pill res-' + K.esc(r.result) + '">' + K.esc(String(r.result).toUpperCase()) + "</span>" + "</td>" +
        "<td class='num'>" + K.money(r.settlement_value_dollars, 4) + "</td>" +
        "<td>" + K.esc(r.settlement_ts || "—") + "</td>" +
        "<td>" + K.esc(r.resolved_at || "—") + "</td>" +
        "<td>" + K.marketLink(r.ticker, "market") + "</td></tr>";
    }).join("") : '<tr><td colspan="7" class="muted">Nothing has resolved yet in this browser.</td></tr>';
  }

  function renderRecent() {
    var tb = $("recentRows");
    if (!tb) return;
    K.loadJSON("resolved.json").then(function (d) {
      var rows = (d.resolved || []).slice(0, 60);
      $("recentCount").textContent = K.fmtNum((d.resolved || []).length);
      tb.innerHTML = rows.length ? rows.map(function (m) {
        return "<tr><td>" + K.esc(m.title || m.ticker) + "</td><td>" + K.topicPill(m.topic) + "</td>" +
          "<td>" + (m.result ? '<span class="pill res-' + K.esc(m.result) + '">' + K.esc(String(m.result).toUpperCase()) + "</span>" : "—") + "</td>" +
          "<td class='num'>" + K.money(m.settlement_value_dollars, 4) + "</td>" +
          "<td>" + K.esc(m.settlement_ts || "—") + "</td>" +
          "<td>" + K.marketLink(m.ticker, "market") + "</td></tr>";
      }).join("") : '<tr><td colspan="6" class="muted">No resolved markets in the snapshot.</td></tr>';
    }).catch(function () {});
  }

  function poll() {
    var watch = K.getWatch();
    if (!watch.length) { renderWatch(); return; }
    watch.forEach(function (w) {
      fetch(KALSHI.rest + "/markets/" + encodeURIComponent(w.ticker)).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      }).then(function (j) {
        var m = j.market || {};
        state.live[w.ticker] = m;
        var result = (m.result || "").toString().toLowerCase();
        if (result) {
          var h = getHistory();
          if (!h.some(function (x) { return x.ticker === w.ticker; })) {
            h.unshift({
              ticker: w.ticker, title: m.title || w.title, topic: w.topic, result: result,
              settlement_value_dollars: m.settlement_value_dollars, settlement_ts: m.settlement_ts,
              resolved_at: new Date().toISOString()
            });
            setHistory(h);
            state.history = h;
            renderHistory();
          }
        }
        renderWatch();
      }).catch(function (e) {
        var row = state.live[w.ticker] || (state.live[w.ticker] = {});
        row.error = e.message;
        renderWatch();
      });
    });
  }

  function init() {
    state.history = getHistory();
    renderWatch();
    renderHistory();
    renderRecent();
    poll();
    setInterval(poll, 30000);
    var clr = $("clearHistoryBtn");
    if (clr) clr.onclick = function () { setHistory([]); state.history = []; renderHistory(); };
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
