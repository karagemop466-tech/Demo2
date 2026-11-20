/* Suggestion review board: decisions are stored in this browser only. */
(function () {
  "use strict";
  var K = window.K;
  var $ = function (id) { return document.getElementById(id); };
  var STATES = ["pending", "accept", "defer", "reject"];

  function state() { return K.getSuggestionState(); }

  function apply() {
    var st = state();
    document.querySelectorAll("#sugTable tr[data-id]").forEach(function (tr) {
      var id = tr.getAttribute("data-id");
      var cur = st[id] || { status: "pending", note: "" };
      var cell = tr.querySelector("td.dec");
      cell.innerHTML =
        '<div class="row" style="gap:6px">' +
        STATES.map(function (s) {
          return '<button class="secondary' + (cur.status === s ? " active" : "") + '" data-set="' + s + '" data-id="' + id + '">' +
            s.charAt(0).toUpperCase() + s.slice(1) + "</button>";
        }).join("") +
        "</div>" +
        '<input type="text" data-note="' + id + '" placeholder="note (optional)" value="' + K.esc(cur.note || "") + '" style="margin-top:6px">';
    });
    document.querySelectorAll("[data-set]").forEach(function (b) {
      b.onclick = function () {
        var st2 = state();
        var id = b.getAttribute("data-id");
        st2[id] = st2[id] || { status: "pending", note: "" };
        st2[id].status = b.getAttribute("data-set");
        K.setSuggestionState(st2);
        apply();
      };
    });
    document.querySelectorAll("[data-note]").forEach(function (i) {
      i.onchange = function () {
        var st2 = state();
        var id = i.getAttribute("data-note");
        st2[id] = st2[id] || { status: "pending", note: "" };
        st2[id].note = i.value;
        K.setSuggestionState(st2);
        summary();
      };
    });
    summary();
  }

  function summary() {
    var st = state();
    var counts = { pending: 0, accept: 0, defer: 0, reject: 0 };
    Object.keys(st).forEach(function (k) {
      var s = st[k].status || "pending";
      if (counts[s] === undefined) s = "pending";
      counts[s]++;
    });
    $("sugSummary").innerHTML = "Decisions recorded in this browser: " +
      counts.accept + " accepted · " + counts.defer + " deferred · " + counts.reject + " rejected · " + counts.pending + " pending.";
    $("sugStatus").innerHTML = '<span class="ok">Review board ready.</span>';
  }

  function init() {
    var r = $("resetBtn"), p = $("printBtn");
    if (r) r.onclick = function () { K.setSuggestionState({}); apply(); };
    if (p) p.onclick = function () { window.print(); };
    apply();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
