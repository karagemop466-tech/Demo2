/* desk/tests/desk.test.js — behaviour tests for the desk's live JavaScript.
 *
 * The browser code talks to the public Kalshi demo API. These tests replace
 * `fetch` with fixtures shaped like the documented responses, so the tests are
 * offline and deterministic. They check the things a trader would notice:
 * that the chart loads the right endpoint for the chosen window, that a move of
 * $0.10 or more is detected and shown with its official source, that the depth
 * ladder counts contracts at each price, and that a failed request produces an
 * error rather than a made-up price.
 *
 *   node --test desk/tests/desk.test.js
 */
import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SOURCE = fs.readFileSync(path.join(HERE, "..", "assets", "desk.js"), "utf8");

const activeDoms = new Set();
afterEach(() => {
  for (const dom of activeDoms) dom.window.close();
  activeDoms.clear();
});

const MARKETS = [
  { ticker: "KXDEMO-1", series_ticker: "KXDEMO", event_ticker: "KXDEMO-1", topic: "gas",
    title: "Demo gas market", last_price_dollars: "0.4000", yes_bid_dollars: "0.3900",
    yes_ask_dollars: "0.4100", volume_24h_fp: "100.00", open_interest_fp: "500.00",
    close_time: "2027-01-01T00:00:00Z", source_url: "https://external-api.demo.kalshi.co/trade-api/v2/markets/KXDEMO-1" },
  { ticker: "KXDEMO-2", series_ticker: "KXDEMO", event_ticker: "KXDEMO-2", topic: "golf",
    title: "Demo golf market", last_price_dollars: "0.2000", yes_bid_dollars: "0.1900",
    yes_ask_dollars: "0.2100", volume_24h_fp: "50.00", open_interest_fp: "200.00",
    close_time: "2027-02-01T00:00:00Z", source_url: "https://external-api.demo.kalshi.co/trade-api/v2/markets/KXDEMO-2" }
];

const CANDLES = {
  candlesticks: [
    { end_period_ts: 1000, price: { close_dollars: "0.3000", high_dollars: "0.3100", low_dollars: "0.2900" },
      yes_bid: {}, yes_ask: {} },
    { end_period_ts: 1060, price: { close_dollars: "0.3200", high_dollars: "0.3300", low_dollars: "0.3100" },
      yes_bid: {}, yes_ask: {} },
    { end_period_ts: 1120, price: { close_dollars: "0.6000", high_dollars: "0.6100", low_dollars: "0.5900" },
      yes_bid: {}, yes_ask: {} }
  ]
};

const ORDERBOOK = {
  orderbook_fp: {
    yes_dollars: [["0.3900", "120.00"], ["0.3800", "80.00"]],
    no_dollars: [["0.5800", "40.00"]]
  }
};

function makeDom() {
  const html = `<!doctype html><html><body>
    <select id="mktSel"></select>
    <div id="winSeg"></div>
    <canvas id="chart"></canvas>
    <div id="chartNote"></div>
    <div id="jumpBox"></div>
    <div id="jumpCount"></div>
    <span id="liveBadge"></span><span id="liveTick"></span><div id="liveTitle"></div>
    <div id="liveSource"></div><div id="liveSeries"></div>
    <div id="qPrice"></div><div id="qBid"></div><div id="qAsk"></div>
    <div id="qSpread"></div><div id="qVolume"></div><div id="qOi"></div><div id="qClose"></div>
    <div id="depthMeta"></div><div id="depthTotals"></div>
    <div id="depthYes"></div><div id="depthAsk"></div>
    <button id="refreshBtn"></button>
  </body></html>`;
  const dom = new JSDOM(html, { url: "https://example.test/desk/index.html", pretendToBeVisual: true, runScripts: "dangerously" });
  const calls = [];
  const noop = () => {};
  const ctx = new Proxy({}, { get(target, key) { return key in target ? target[key] : noop; }, set(target, key, value) { target[key] = value; return true; } });
  dom.window.HTMLCanvasElement.prototype.getContext = () => ctx;
  dom.window.fetch = (url) => {
    calls.push(String(url));
    const u = String(url);
    let payload;
    if (u.includes("summary.json")) payload = { markets: MARKETS, generated_at: "2026-11-20T00:00:00Z" };
    else if (u.includes("/markets/trades")) payload = { trades: [] };
    else if (u.includes("/candlesticks")) payload = CANDLES;
    else if (u.includes("/orderbook")) payload = ORDERBOOK;
    else if (/\/markets\/[^/]+$/.test(u)) payload = { market: { ...MARKETS[0], status: "active", last_price_dollars: "0.4050" } };
    else payload = {};
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(payload) });
  };
  // jsdom's currentScript is read-only in some versions; shadow it with the
  // same URL a normal external <script src> would expose to desk.js.
  Object.defineProperty(dom.window.document, "currentScript", {
    configurable: true,
    get() { return { src: "https://example.test/desk/assets/desk.js" }; }
  });
  return { dom, calls };
}

async function boot({ failFetch = false } = {}) {
  const { dom, calls } = makeDom();
  activeDoms.add(dom);
  if (failFetch) {
    dom.window.fetch = (url) => {
      // Keep the bundled snapshot available; simulate only the live API outage.
      if (String(url).includes("summary.json")) {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ markets: MARKETS }) });
      }
      return Promise.reject(new Error("network down"));
    };
  }
  // Append as a real script so `document.currentScript` behaves like it does
  // in a browser. The src also anchors the desk's relative data/API URLs.
  const script = dom.window.document.createElement("script");
  script.textContent = SOURCE;
  dom.window.document.body.appendChild(script);
  await new Promise((r) => setTimeout(r, 30));
  return { dom, calls, doc: dom.window.document };
}

test("the market picker is filled from the bundled snapshot and the quote is shown", async () => {
  const { doc } = await boot();
  const select = doc.getElementById("mktSel");
  assert.equal(select.options.length, MARKETS.length);
  assert.match(select.options[0].textContent, /KXDEMO-1/);
  assert.equal(doc.getElementById("qPrice").textContent, "0.4000");
  assert.equal(doc.getElementById("qBid").textContent, "0.3900");
  assert.equal(doc.getElementById("qAsk").textContent, "0.4100");
  assert.equal(doc.getElementById("qSpread").textContent, "0.0200");
});

test("the chart window chooses the endpoint that carries that resolution", async () => {
  const { calls } = await boot();
  const windows = calls.filter((c) => c.includes("candlesticks") || c.includes("trades"));
  assert.ok(windows.length > 0);
  // the default window is one hour, which is served by one-minute candlesticks
  assert.match(windows[0], /period_interval=1/);

  const { dom } = await boot();
  const button = dom.window.document.querySelector('#winSeg button[data-w="604800"]');
  assert.ok(button, "the window selector must offer a seven day window");
  button.dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 30));
  const seven = dom.window.document.getElementById("chartNote").textContent;
  assert.match(seven, /period_interval=1440/);
});

test("a move of $0.10 or more is detected and shown with its official source", async () => {
  const { doc } = await boot();
  const jumpBox = doc.getElementById("jumpBox");
  const text = jumpBox.textContent;
  assert.match(text, /0\.3200/);
  assert.match(text, /0\.6000/);
  assert.match(text, /\+0\.28/);
  const link = jumpBox.querySelector("a");
  assert.ok(link, "the jump row must link its official source");
  assert.match(link.getAttribute("href"), /external-api\.demo\.kalshi\.co/);
  assert.match(jumpBox.textContent, /no news feed/i);
});

test("the depth ladder counts contracts at each price and derives the ask side", async () => {
  const { doc } = await boot();
  const yes = doc.getElementById("depthYes").textContent;
  const ask = doc.getElementById("depthAsk").textContent;
  assert.match(yes, /0\.3900/);
  assert.match(yes, /120/);
  assert.match(yes, /200/, "cumulative contracts must be shown");
  // a no bid at 0.58 is the same as a yes ask at 0.42
  assert.match(ask, /0\.4200/);
  assert.match(doc.getElementById("depthMeta").textContent, /official order book/);
});

test("a failed request shows an error instead of a fabricated value", async () => {
  const { dom, doc } = await boot({ failFetch: true });
  doc.getElementById("refreshBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 30));
  const note = doc.getElementById("chartNote").textContent;
  assert.match(note, /unavailable|error/i);
  // The bundled official snapshot remains visible, but it is explicitly marked
  // offline; the failed live call must not overwrite it with an invented value.
  assert.equal(doc.getElementById("qPrice").textContent, "0.4000");
  assert.match(doc.getElementById("liveBadge").textContent, /OFFLINE/);
});
