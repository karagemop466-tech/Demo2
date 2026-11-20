/* Shared navigation + footer so every page stays in sync. */
(function () {
  var PAGES = [
    ["index.html", "Dashboard", "index.html"],
    ["pages/executive-summary.html", "Executive Summary", "pages/executive-summary.html"],
    ["pages/gas.html", "Gas", "pages/gas.html"],
    ["pages/elections.html", "Elections", "pages/elections.html"],
    ["pages/culture.html", "Culture", "pages/culture.html"],
    ["pages/crypto.html", "Crypto", "pages/crypto.html"],
    ["pages/golf.html", "Golf", "pages/golf.html"],
    ["pages/portfolio.html", "Portfolio & Trading", "pages/portfolio.html"],
    ["pages/analysis.html", "Trade Analysis", "pages/analysis.html"],
    ["pages/resolution.html", "Resolution Tracker", "pages/resolution.html"],
    ["pages/methodology.html", "Methodology", "pages/methodology.html"],
    ["pages/suggestions.html", "Suggestions", "pages/suggestions.html"],
    ["pages/questions.html", "Questions", "pages/questions.html"],
    ["pages/verification.html", "Verification", "pages/verification.html"],
    ["pages/flagged.html", "Flagged for Review", "pages/flagged.html"],
    ["pages/sources.html", "Sources", "pages/sources.html"]
  ];
  var HERE = (function () {
    var p = window.location.pathname.split("/");
    return p.pop() || "index.html";
  })();

  function esc(s) { return String(s == null ? "" : s); }

  var nav = document.getElementById("site-nav");
  if (nav) {
    var links = PAGES.map(function (p) {
      var cur = p[2].split("/").pop() === HERE ? ' aria-current="page"' : "";
      return '<a href="' + p[2] + '"' + cur + ">" + esc(p[1]) + "</a>";
    }).join("");
    nav.innerHTML =
      '<header class="top"><div class="brand">Kalshi <span>Demo</span> Dashboard</div>' +
      '<nav class="main">' + links + "</nav></header>";
  }

  var foot = document.getElementById("site-foot");
  if (foot) {
    foot.innerHTML =
      '<footer class="site">Demo environment only — no real money. Every market figure on this site comes from the ' +
      'Kalshi demo API (<a href="https://docs.kalshi.com/getting_started/api_environments">environment list</a>) or is left blank and flagged as unverified. ' +
      'See <a href="pages/sources.html">Sources</a>, <a href="pages/verification.html">Verification</a> and <a href="pages/flagged.html">Flagged for Review</a>.</footer>';
  }
})();
