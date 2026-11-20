/* Pulse shared helpers. Data: ../data/pulse_*.json (CI snapshots) + live demo API.
 * Every number traces to an official API field or labelled computed arithmetic.
 * Missing values render as an em dash — never inferred. */
(function () {
  "use strict";
  var P = {
    DEMO: "https://external-api.demo.kalshi.co/trade-api/v2",
    DOCS: "https://docs.kalshi.com",
  };
  P.esc = function (s) {
    return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  P.dash = function (v) {
    return v === null || v === undefined || v === "" ? '<span class="muted">—</span>' : P.esc(v);
  };
  P.usd = function (v, dp) {
    if (v === null || v === undefined || v === "") return "—";
    var n = Number(v);
    return isFinite(n) ? "$" + n.toFixed(dp === undefined ? 2 : dp) : "—";
  };
  P.num = function (v, dp) {
    if (v === null || v === undefined || v === "") return "—";
    var n = Number(v);
    if (!isFinite(n)) return "—";
    return n.toLocaleString(undefined, { maximumFractionDigits: dp === undefined ? 2 : dp });
  };
  P.when = function (iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    return isNaN(d.getTime()) ? P.esc(iso) : d.toISOString().replace("T", " ").replace("Z", " UTC");
  };
  P.src = function (url, label) {
    if (!url) return "—";
    return '<a href="' + P.esc(url) + '" target="_blank" rel="noopener">' + P.esc(label || "API") + "</a>";
  };
  P.getJSON = function (path) {
    return fetch(path, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(path + " → HTTP " + r.status);
      return r.json();
    });
  };
  P.liveJSON = function (url) {
    return fetch(url, { headers: { Accept: "application/json" }, cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status + " for " + url);
      return r.json();
    });
  };
  window.PULSE = P;
})();
