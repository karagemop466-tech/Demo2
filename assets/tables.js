/* Renders verified per-topic tables from the committed data/ snapshot.
   Snapshot is produced by tools/collect_kalshi.py (GitHub Actions, every 2h),
   which copies each value from the official Kalshi demo API response at the URL
   stored in the row's source_url. Blank API fields stay blank here and are
   marked UNVERIFIED — nothing is ever inferred or filled in. */
(function () {
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function cell(v) {
    return (v === "" || v == null) ? '<span class="unv" title="blank in the official API response — unverified">—</span>' : esc(v);
  }
  function link(url, label) {
    return url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + label + '</a>' : '<span class="unv">no source</span>';
  }
  var KINDS = {
    open: { file: "data/markets_open.json", title: "Open markets" },
    settled: { file: "data/markets_settled.json", title: "Settled markets (resolution: yes/no)" },
    series: { file: "data/series_scope.json", title: "Series" }
  };
  function renderOpen(rows) {
    return '<table><thead><tr><th>Market ticker</th><th>Title</th><th>Status</th><th>Last $</th><th>YES bid</th><th>YES ask</th><th>Volume (contracts)</th><th>Open interest</th><th>Est. $ turnover*</th><th>Close (UTC)</th><th>Source</th></tr></thead><tbody>' +
      rows.map(function (r) {
        return '<tr><td>' + link(r.source_url, esc(r.ticker)) + '</td><td>' + esc(r.title) + '</td><td>' + cell(r.status) + '</td><td>' + cell(r.last_price_dollars) + '</td><td>' + cell(r.yes_bid_dollars) + '</td><td>' + cell(r.yes_ask_dollars) + '</td><td>' + cell(r.volume_fp) + '</td><td>' + cell(r.open_interest_fp) + '</td><td>' + (r.dollar_turnover_estimate === "" ? '<span class="unv">—</span>' : "$" + esc(r.dollar_turnover_estimate)) + '</td><td>' + cell(r.close_time) + '</td><td>' + link(r.source_url, "official API ↗") + '</td></tr>';
      }).join("") + '</tbody></table>';
  }
  function renderSettled(rows) {
    return '<table><thead><tr><th>Market ticker</th><th>Title</th><th>Result</th><th>Settlement $ (YES side)</th><th>Settled at (UTC)</th><th>Settlement source (as listed)</th><th>Source</th></tr></thead><tbody>' +
      rows.map(function (r) {
        var ss = (r.settlement_sources || []).map(function (s) {
          return s && s.url ? esc(s.name || "source") + ' (' + link(s.url, "link") + ')' : esc(s.name || "");
        }).join("; ");
        return '<tr><td>' + link(r.source_url, esc(r.ticker)) + '</td><td>' + esc(r.title) + '</td><td><b>' + cell(r.result) + '</b></td><td>' + cell(r.settlement_value_dollars) + '</td><td>' + cell(r.settlement_ts) + '</td><td>' + (ss ? ss : '<span class="unv">—</span>') + '</td><td>' + link(r.source_url, "official API ↗") + '</td></tr>';
      }).join("") + '</tbody></table>';
  }
  function renderSeries(rows) {
    return '<table><thead><tr><th>Series</th><th>Title</th><th>Category</th><th>Tags</th><th>Frequency</th><th>Contract terms</th><th>Settlement sources</th><th>Source</th></tr></thead><tbody>' +
      rows.map(function (r) {
        var ss = (r.settlement_sources || []).map(function (s) {
          return s && s.url ? esc(s.name || "source") + ' (' + link(s.url, "link") + ')' : esc(s.name || "");
        }).join("; ");
        return '<tr><td>' + link(r.source_url, esc(r.series_ticker)) + '</td><td>' + esc(r.title) + '</td><td>' + cell(r.category) + '</td><td>' + cell((r.tags || []).join("; ")) + '</td><td>' + cell(r.frequency) + '</td><td>' + (r.contract_terms_url ? link(r.contract_terms_url, "terms PDF ↗") : '<span class="unv">—</span>') + '</td><td>' + (ss ? ss : '<span class="unv">—</span>') + '</td><td>' + link(r.source_url, "official API ↗") + '</td></tr>';
      }).join("") + '</tbody></table>';
  }
  var RENDER = { open: renderOpen, settled: renderSettled, series: renderSeries };
  var cache = {};
  function load(kind) {
    if (cache[kind]) return Promise.resolve(cache[kind]);
    return fetch(KINDS[kind].file, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(KINDS[kind].file + " HTTP " + r.status);
      return r.json();
    }).then(function (j) { cache[kind] = j; return j; });
  }
  function mount() {
    var hosts = document.querySelectorAll("[data-topic][data-kind]");
    if (!hosts.length) return;
    var kinds = {};
    hosts.forEach(function (h) { kinds[h.getAttribute("data-kind")] = true; });
    Object.keys(kinds).forEach(function (kind) {
      load(kind).then(function (j) {
        hosts.forEach(function (h) {
          if (h.getAttribute("data-kind") !== kind) return;
          var topic = h.getAttribute("data-topic");
          var rows = (j.rows || []).filter(function (r) { return !topic || r.topic === topic; });
          h.innerHTML = '<p class="muted">' + KINDS[kind].title + ' — ' + rows.length + ' row(s) matching topic <b>' + esc(topic) + '</b>. Snapshot collected <b>' + esc(j.collected_at || "?") + '</b> UTC by tools/collect_kalshi.py from the official Kalshi demo API. Blank cells (—) were blank in the API response and are marked unverified.</p>' +
            (rows.length ? RENDER[kind](rows) : '<p><span class="unv">No rows in the current snapshot for this topic.</span></p>');
        });
      }).catch(function (e) {
        hosts.forEach(function (h) {
          h.innerHTML = '<p><span class="unv">Snapshot unavailable (' + esc(e.message) + '). Run the “Collect Kalshi demo data” GitHub Action to refresh data/.</span></p>';
        });
      });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
