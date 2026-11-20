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
  /* Fallback chain: 1) CI collector files (data/*.json, refreshed every 2h);
     2) the verified hand-captured snapshots (dashboard/data/snapshot.json markets,
        data/kalshi_snapshot.json series/events) with values copied verbatim and
     their original source links. Nothing is inferred in either path. */
  var CATMAP = { "Gas prices": "gas-prices", "Elections": "elections", "Culture": "culture", "Crypto": "crypto", "Golf": "golf" };
  function legacyFrom(kind) {
    var loads = [fetch("dashboard/data/snapshot.json", { cache: "no-store" }), fetch("data/kalshi_snapshot.json", { cache: "no-store" })];
    return Promise.all(loads.map(function (p) { return p.then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); }))
      .then(function (pair) {
        var dash = pair[0], old = pair[1];
        if (!dash && !old) throw new Error("no committed snapshots");
        var rows = [], collected = "";
        if (kind === "open" || kind === "settled") {
          if (!dash) throw new Error("no market snapshot");
          collected = (dash.meta && dash.meta.captured_utc_date) || "";
          rows = (dash.markets || []).filter(function (m) {
            return kind === "open" ? (m.status === "active" && !m.result) : (m.result === "yes" || m.result === "no" || m.status === "finalized");
          }).map(function (m) {
            return {
              ticker: m.ticker, title: m.title, topic: CATMAP[m.category] || "",
              status: m.status, result: m.result || "",
              settlement_value_dollars: "", settlement_ts: "",
              volume_fp: m.volume_contracts, open_interest_fp: m.open_interest_contracts,
              last_price_dollars: m.last_price, yes_bid_dollars: m.yes_bid,
              yes_ask_dollars: m.yes_ask, close_time: m.close_time_utc,
              source_url: m.source, dollar_turnover_estimate: "", settlement_sources: []
            };
          });
        } else {
          if (!old) throw new Error("no series snapshot");
          collected = (old.meta && old.meta.collected_on) || "";
          rows = (old.rows || []).map(function (r) {
            return {
              series_ticker: r.ticker, title: r.title + (r.type === "event" ? " (event)" : ""),
              category: r.kalshi_category, tags: String(r.tags || "").split(";").map(function (s) { return s.trim(); }).filter(Boolean),
              frequency: r.frequency, contract_terms_url: r.contract_terms,
              settlement_sources: r.settlement_sources || [], source_url: r.source_api, _type: r.type
            };
          });
        }
        return { collected_at: collected, rows: rows, _fallback: true };
      });
  }
  function load(kind) {
    if (cache[kind]) return Promise.resolve(cache[kind]);
    return fetch(KINDS[kind].file, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(KINDS[kind].file + " HTTP " + r.status);
      return r.json();
    }).catch(function () {
      return legacyFrom(kind);
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
          h.innerHTML = '<p class="muted">' + KINDS[kind].title + ' — ' + rows.length + ' row(s) matching topic <b>' + esc(topic) + '</b>. ' +
            (j._fallback
              ? 'CI collector files not present yet — showing the verified hand-captured snapshot (values copied verbatim with their original source links), captured <b>' + esc(j.collected_at || "?") + '</b>.'
              : 'Snapshot collected <b>' + esc(j.collected_at || "?") + '</b> UTC by tools/collect_kalshi.py from the official Kalshi demo API.') +
            ' Blank cells (—) were blank in the API response and are marked unverified.</p>' +
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
