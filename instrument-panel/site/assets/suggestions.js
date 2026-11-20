/* Suggestions board — records the reader's lean in localStorage only.
 * Nothing is transmitted; nothing is applied. The export exists so a decision
 * can be attached to an issue with its reasoning. */
(function () {
  "use strict";
  const KEY = "kalshi-demo-picks-v1";
  const $ = (id) => document.getElementById(id);

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; }
  }
  function save(o) {
    try { localStorage.setItem(KEY, JSON.stringify(o)); } catch (e) { /* private mode */ }
  }
  function paint() {
    const picks = load();
    document.querySelectorAll('input[type=radio][id^="pick-"]').forEach((r) => {
      r.checked = picks[r.name.replace("pick-", "")] === r.value;
    });
    document.querySelectorAll("[id^=dec-]").forEach((el) => {
      const id = el.id.replace("dec-", "");
      const v = picks[id];
      el.innerHTML = v
        ? `Your lean: <b>${v}</b> · <span class="small muted">recorded locally, not sent</span>`
        : "Your lean: <b>not recorded</b>";
    });
    const status = $("pickStatus");
    if (status) {
      const n = Object.keys(picks).length;
      status.textContent = n ? `${n} choice${n === 1 ? "" : "s"} saved in this browser.` : "No choices recorded yet.";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!document.querySelector("[id^=dec-]")) return;
    document.querySelectorAll('input[type=radio]').forEach((r) => {
      r.addEventListener("change", () => {
        const picks = load();
        picks[r.name.replace("pick-", "")] = r.value;
        save(picks);
        paint();
      });
    });
    const ex = $("exportPicks");
    if (ex) ex.addEventListener("click", () => {
      const picks = load();
      const blob = new Blob([JSON.stringify({ source: "kalshi-demo-suggestions", recorded_at: new Date().toISOString(), picks }, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "kalshi-demo-suggestion-picks.json";
      a.click();
      URL.revokeObjectURL(a.href);
    });
    paint();
  });
})();
