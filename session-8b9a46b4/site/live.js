// Browser-side demo chart. Public REST endpoints only; no credentials are read.
// Seconds = recent trade prints; minutes/hours = official candlesticks (1/60 min).
// Sources: https://docs.kalshi.com/api-reference/market/get-market
//          https://docs.kalshi.com/api-reference/events/get-event
//          https://docs.kalshi.com/api-reference/market/get-trades
//          https://docs.kalshi.com/api-reference/market/get-market-candlesticks
//          https://docs.kalshi.com/api-reference/market/get-market-orderbook
const BASE = "https://external-api.demo.kalshi.co/trade-api/v2";
const $ = (id) => document.getElementById(id);

async function getJSON(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" }, cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status} from Kalshi demo API`);
  return response.json();
}

async function load() {
  const ticker = $("ticker").value.trim();
  const windowChoice = $("window").value;
  $("status").textContent = "loading…";
  try {
    let points = [];
    if (windowChoice === "seconds") {
      const trades = await getJSON(`${BASE}/markets/trades?ticker=${encodeURIComponent(ticker)}&limit=200`);
      points = (trades.trades || [])
        .map((trade) => [Date.parse(trade.created_time), Number(trade.yes_price_dollars)])
        .filter(([time, price]) => Number.isFinite(time) && Number.isFinite(price))
        .sort((a, b) => a[0] - b[0]);
    } else {
      // Resolve the official series ticker from market -> event instead of guessing
      // it by splitting the user-supplied market ticker.
      const marketResponse = await getJSON(`${BASE}/markets/${encodeURIComponent(ticker)}`);
      const eventTicker = marketResponse.market?.event_ticker;
      if (!eventTicker) throw new Error("Market response did not include event_ticker");
      const eventResponse = await getJSON(`${BASE}/events/${encodeURIComponent(eventTicker)}`);
      const seriesTicker = eventResponse.event?.series_ticker;
      if (!seriesTicker) throw new Error("Event response did not include series_ticker");

      const period = windowChoice === "minutes" ? 1 : 60;
      const now = Math.floor(Date.now() / 1000);
      const start = now - (period === 1 ? 24 * 60 * 60 : 7 * 24 * 60 * 60);
      const candleUrl = `${BASE}/series/${encodeURIComponent(seriesTicker)}/markets/${encodeURIComponent(ticker)}/candlesticks?start_ts=${start}&end_ts=${now}&period_interval=${period}`;
      const candleResponse = await getJSON(candleUrl);
      points = (candleResponse.candlesticks || [])
        .map((candle) => [
          Number(candle.end_period_ts) * 1000,
          Number(candle.price?.close_dollars ?? candle.yes_bid?.close_dollars ?? candle.yes_ask?.close_dollars),
        ])
        .filter(([time, price]) => Number.isFinite(time) && Number.isFinite(price));
    }

    draw(points);
    $("status").textContent = points.length ? `${points.length} points` : "no data for this ticker/window";

    const bookResponse = await getJSON(`${BASE}/markets/${encodeURIComponent(ticker)}/orderbook?depth=10`);
    const book = bookResponse.orderbook_fp || {};
    const yesBids = book.yes_dollars || [];
    $("book").innerHTML = "<table><tr><th>YES bid price ($)</th><th>Contracts</th></tr>" +
      yesBids.map(([price, count]) => `<tr><td>${Number(price).toFixed(4)}</td><td>${count}</td></tr>`).join("") +
      "</table><p>Source: <a href='" + BASE + "/markets/" + encodeURIComponent(ticker) + "/orderbook?depth=10'>official orderbook API</a></p>";
  } catch (error) {
    $("status").textContent = "error: " + error.message;
  }
}

function draw(points) {
  const canvas = $("chart");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!points.length) return;

  const times = points.map(([time]) => time);
  const start = Math.min(...times);
  const end = Math.max(...times);
  ctx.strokeStyle = "#888";
  ctx.beginPath();
  ctx.moveTo(40, 10);
  ctx.lineTo(40, 300);
  ctx.lineTo(890, 300);
  ctx.stroke();
  ctx.strokeStyle = "#1a73e8";
  ctx.beginPath();
  points.forEach(([time, price], index) => {
    const x = 40 + ((time - start) / Math.max(1, end - start)) * 850;
    const y = 300 - Math.max(0, Math.min(1, price)) * 290;
    index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  ctx.stroke();
  ctx.fillStyle = "#000";
  ctx.fillText("$1.00", 2, 16);
  ctx.fillText("$0.00", 2, 300);
  ctx.fillText(new Date(start).toISOString(), 40, 318);
  ctx.fillText(new Date(end).toISOString(), 760, 318);
}

$("go").addEventListener("click", load);
