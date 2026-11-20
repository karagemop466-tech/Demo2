/* Suggestions review board.
   Decisions are stored in this browser only (localStorage). Nothing on the
   site changes because of a decision until a developer implements it. */
'use strict';
var KEY = 'kalshi_demo_suggestion_decisions_v1';
function $(id) { return document.getElementById(id); }
function load() { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } }
function save(d) { localStorage.setItem(KEY, JSON.stringify(d)); }
function esc(s) {
  return String(s === undefined || s === null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function init() {
  var list = document.querySelectorAll('[data-suggestion]');
  if (!list.length) return;
  var dec = load();

  function render() {
    Array.prototype.forEach.call(list, function (el) {
      var id = el.getAttribute('data-suggestion');
      var d = dec[id];
      el.querySelectorAll('.decision button').forEach(function (b) {
        b.classList.toggle('chosen', d === b.getAttribute('data-value'));
      });
      var out = el.querySelector('.decision-state');
      if (out) {
        out.textContent = d ? ('Recorded in this browser: ' + d) : 'No decision recorded yet.';
      }
    });
    var counts = { approve: 0, defer: 0, reject: 0 };
    Object.keys(dec).forEach(function (k) { if (counts[dec[k]] !== undefined) counts[dec[k]]++; });
    var s = $('decisionSummary');
    if (s) s.textContent = counts.approve + ' approved · ' + counts.defer + ' deferred · ' + counts.reject + ' rejected (stored in this browser only)';
  }

  Array.prototype.forEach.call(list, function (el) {
    el.querySelectorAll('.decision button').forEach(function (b) {
      b.onclick = function () {
        var id = el.getAttribute('data-suggestion');
        var d = load();
        d[id] = b.getAttribute('data-value');
        save(d);
        render();
      };
    });
  });

  var reset = $('resetDecisions');
  if (reset) reset.onclick = function () { save({}); render(); };

  var exportBtn = $('exportDecisions');
  if (exportBtn) exportBtn.onclick = function () {
    var blob = new Blob([JSON.stringify(load(), null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'kalshi-suggestion-decisions.json';
    a.click();
  };

  render();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
