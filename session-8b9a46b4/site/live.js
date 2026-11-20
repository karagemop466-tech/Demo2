// Live chart: browser -> official Kalshi demo API (public endpoints, no auth).
// Seconds = trade prints; minutes/hours = candlesticks (period 1/60 min).
// Docs: https://docs.kalshi.com/api-reference/market/get-trades
//       https://docs.kalshi.com/api-reference/market/get-market-candlesticks
//       https://docs.kalshi.com/api-reference/market/get-market-orderbook
const BASE = "https://external-api.demo.kalshi.co/trade-api/v2";
const $ = (id) => document.getElementById(id);
async function load() {
  const t = $("ticker").value.trim(), w = $("window").value;
  $("status").textContent = "loading…";
  try {
    let pts = [];
    if (w === "seconds") {
      const r = await fetch(`${BASE}/markets/trades?ticker=${encodeURIComponent(t)}&limit=200`);
      const j = await r.json();
      pts = j.trades.map(x => [Date.parse(x.created_time), parseFloat(x.yes_price_dollars)]).sort((a, b) => a[0] - b[0]);
    } else {
      const period = w === "minutes" ? 1 : 60;
      const now = Math.floor(Date.now() / 1000);
      const r = await fetch(`${BASE}/markets/${encodeURIComponent(t)}/candlesticks?start_ts=${now - 86400}&end_ts=${now}&period_interval=${period}`);
      const j = await r.json();
      pts = (j.candlesticks || []).map(c => [c.end_period_ts * 1000, parseFloat(c.yes_bid?.close_dollars ?? c.yes_ask?.close_dollars ?? NaN)]).filter(p => !isNaN(p[1]));
    }
    draw(pts);
    $("status").textContent = pts.length ? `${pts.length} points` : "no data for this ticker/window";
    const b = await (await fetch(`${BASE}/markets/${encodeURIComponent(t)}/orderbook?depth=10`)).json();
    $("book").innerHTML = "<table><tr><th>YES bid price</th><th>Contracts</th></tr>" +
      (b.orderbook?.yes || []).map(([p, c]) => `<tr><td>$${p}</td><td>${c}</td></tr>`).join("") +
      "</table><p>Source: <a href='" + BASE + "/markets/" + encodeURIComponent(t) + "/orderbook?depth=10'>orderbook API</a></p>";
  } catch (e) { $("status").textContent = "error: " + e.message; }
}
function draw(pts) {
  const c = $("chart"), x = c.getContext("2d");
  x.clearRect(0, 0, c.width, c.height);
  if (!pts.length) return;
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = 0, y1 = 1;
  x.strokeStyle = "#888"; x.beginPath(); x.moveTo(40, 10); x.lineTo(40, 300); x.lineTo(890, 300); x.stroke();
  x.strokeStyle = "#1a73e8"; x.beginPath();
  pts.forEach(([px, py], i) => {
    const X = 40 + (px - x0) / Math.max(1, x1 - x0) * 850;
    const Y = 300 - (py - y0) / (y1 - y0) * 290;
    i ? x.lineTo(X, Y) : x.moveTo(X, Y);
  });
  x.stroke();
  x.fillStyle = "#000"; x.fillText("$1.00", 2, 16); x.fillText("$0", 18, 300);
  x.fillText(new Date(x0).toISOString(), 40, 318); x.fillText(new Date(x1).toISOString(), 760, 318);
}
$("go").addEventListener("click", load);
