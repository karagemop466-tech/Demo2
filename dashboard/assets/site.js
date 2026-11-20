/* Shared helpers: navigation, escaping, formatting, verified-table rendering.
   No values are inferred here: blank input => "UNVERIFIED" marker. */
(function () {
  var PAGES = [
    ["index.html", "Home"],
    ["markets.html", "Markets"],
    ["resolutions.html", "Resolutions"],
    ["live.html", "Live dashboard"],
    ["portfolio.html", "Portfolio & trades"],
    ["analysis.html", "Analysis"],
    ["suggestions.html", "Suggestions"],
    ["questions.html", "Questions"],
    ["flagged.html", "Flagged for review"],
    ["../index.html", "Main site ↗"],
    ["../verified/index.html", "Verified tables ↗"]
  ];

  window.esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  window.money = function (v) {
    if (v === "" || v == null) return '<span class="unv">UNVERIFIED</span>';
    var n = Number(v);
    return isNaN(n) ? esc(v) : "$" + n.toFixed(2);
  };

  window.contracts = function (v) {
    if (v === "" || v == null) return '<span class="unv">UNVERIFIED</span>';
    var n = Number(v);
    return isNaN(n) ? esc(v) : n.toLocaleString("en-US", { maximumFractionDigits: 2 });
  };

  window.textOrUnv = function (v) {
    return v === "" || v == null ? '<span class="unv">UNVERIFIED — blank</span>' : esc(v);
  };

  window.apiLink = function (snap, key) {
    var u = snap && snap.sources && snap.sources[key];
    if (!u) return '<span class="unv">no source</span>';
    return '<a href="' + esc(u) + '" target="_blank" rel="noopener">official API ↗</a>';
  };

  var _dataPrefix = null;
  function resolveData(path) {
    if (/^(https?:|\/|\.\.\/)/.test(path)) return Promise.resolve(path);
    if (_dataPrefix !== null) return Promise.resolve(_dataPrefix + path);
    var candidates = ["", "../", "../../", "../../../"];
    var i = 0;
    function tryNext() {
      if (i >= candidates.length) { _dataPrefix = ""; return path; }
      var url = candidates[i] + path + (path.indexOf("?") >= 0 ? "&" : "?") + "probe=" + Date.now();
      return fetch(url, { cache: "no-store" }).then(function (r) {
        if (r.ok) { _dataPrefix = candidates[i]; return _dataPrefix + path; }
        i += 1; return tryNext();
      }, function () { i += 1; return tryNext(); });
    }
    return tryNext();
  }

  window.loadSnapshot = function () {
    return resolveData("data/snapshot.json").then(function (u) {
    return fetch(u, { cache: "no-store" });
    }).then(function (r) {
      if (!r.ok) throw new Error("snapshot HTTP " + r.status);
      return r.json();
    });
  };

  function renderNav() {
    var host = document.getElementById("nav");
    if (!host) return;
    var here = (location.pathname.split("/").pop() || "index.html");
    if (here.indexOf(".html") === -1) here = "index.html";
    host.innerHTML =
      '<header class="top"><div class="wrap"><span class="brand">Kalshi Demo Dashboard</span><nav class="menu">' +
      PAGES.map(function (p) {
        return '<a href="' + p[0] + '" class="' + (p[0] === here ? "active" : "") + '">' + p[1] + "</a>";
      }).join("") +
      "</nav></div></header>";
  }
  document.addEventListener("DOMContentLoaded", renderNav);
})();
