(function(){
const KEY = "kalshi-dashboard-suggestion-choices";
let saved = {};
try { saved = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch(e) { saved = {}; }
function paint(){
  document.querySelectorAll("input.pick").forEach(inp => {
    inp.checked = saved[inp.dataset.id] === inp.value;
    inp.parentElement.classList.toggle("chosen", inp.checked);
  });
}
document.querySelectorAll("input.pick").forEach(inp => {
  inp.addEventListener("change", () => {
    saved[inp.dataset.id] = inp.value;
    localStorage.setItem(KEY, JSON.stringify(saved));
    paint();
  });
});
document.getElementById("copyBtn").addEventListener("click", () => {
  const lines = Object.keys(saved).sort().map(k => k + ": Option " + saved[k]);
  const text = lines.length ? lines.join("\n") : "No choices selected yet.";
  navigator.clipboard.writeText(text).then(
    () => document.getElementById("copyMsg").textContent = "Copied. Paste it into your message to the agent.",
    () => document.getElementById("copyMsg").textContent = text
  );
});
paint();
})();
