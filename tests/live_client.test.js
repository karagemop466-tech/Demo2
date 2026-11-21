import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const ROOT = path.resolve(import.meta.dirname, "..");

function makeFakeElement(id) {
  return {
    id,
    innerHTML: "",
    textContent: "",
    value: "",
    style: {},
    listeners: {},
    addEventListener(type, fn) {
      (this.listeners[type] = this.listeners[type] || []).push(fn);
    },
    querySelectorAll() {
      return [];
    },
    setAttribute() {},
    getAttribute() {
      return null;
    },
  };
}

function loadAlertsHarness({ snap, history, fetchHandler }) {
  const elements = new Map();
  const getEl = (id) => {
    if (!elements.has(id)) elements.set(id, makeFakeElement(id));
    return elements.get(id);
  };
  const fetchCalls = [];
  const doc = {
    getElementById: getEl,
    addEventListener() {},
  };
  const win = {
    location: { href: "https://example.test/alerts.html" },
  };
  const KR = {
    snapshot: async () => snap,
    history: async () => history || { points: {} },
    staleness() {},
    drawChart() {},
    renderTable(el, cols, rows, empty) {
      if (!el) return;
      el.innerHTML = rows && rows.length
        ? rows.map((r) => cols.map((c) => c.get(r)).join("|")).join("\n")
        : (empty || "");
    },
    when: (iso) => String(iso || "—"),
    buildSeries(candles, hist, field) {
      return (candles || [])
        .map((c) => ({
          t: (c.ts || 0) * 1000,
          v: c[field] != null ? Number(c[field]) : null,
          src: "candle",
        }))
        .filter((p) => p.v != null && Number.isFinite(p.v));
    },
    detectJumps(series, thr) {
      const out = [];
      for (let i = 1; i < series.length; i++) {
        const diff = Math.round(Math.abs(series[i].v - series[i - 1].v) * 10000);
        if (diff >= Math.round((thr || 0.1) * 10000)) out.push(series[i]);
      }
      return out;
    },
    esc: (s) => String(s ?? ""),
    usd: (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? "—" : "$" + Number(v).toFixed(d)),
    num: (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(d)),
    topicPill: (t) => `[${t}]`,
    resultPill: (r) => `[${r}]`,
    link: (u, l) => `<a href="${u}">${l}</a>`,
  };

  const sandbox = {
    window: win,
    document: doc,
    KR,
    fetch: async (url, opts) => {
      fetchCalls.push(String(url));
      return fetchHandler(String(url), opts);
    },
    setInterval: () => 1,
    clearInterval() {},
    console,
    Date,
    Math,
    Number,
    String,
    Array,
    Object,
    Map,
    Set,
    Promise,
    Error,
    encodeURIComponent,
  };
  sandbox.globalThis = sandbox;
  win.window = win;

  const code = fs.readFileSync(path.join(ROOT, "assets/alerts.js"), "utf8");
  vm.runInNewContext(code, sandbox, { filename: "assets/alerts.js" });

  return {
    internals: win.__ALERTS_INTERNALS,
    elements,
    fetchCalls,
    getEl,
  };
}

async function flushMicrotasks(rounds = 8) {
  for (let i = 0; i < rounds; i++) {
    await new Promise((r) => setImmediate(r));
  }
}

test("isSwing handles exact IEEE-754 $0.10 moves without float drift", async () => {
  const snap = {
    generated_at_utc: "2026-11-21T00:00:00Z",
    markets: [],
    candles: {},
    orderbooks: {},
  };
  const h = loadAlertsHarness({
    snap,
    fetchHandler: async () => ({ ok: true, status: 200, json: async () => ({ trades: [], markets: [] }) }),
  });
  await flushMicrotasks();

  assert.equal(h.internals.isSwing(0.50, 0.60), true);
  assert.equal(h.internals.isSwing(0.60, 0.50), true);
  assert.equal(h.internals.isSwing("0.5000", "0.6000"), true);
  assert.equal(h.internals.isSwing(0.50, 0.5999), false);
  assert.equal(h.internals.isSwing(null, 0.60), false);
});

test("batchTickers splits watched tickers into chunks of 40", async () => {
  const h = loadAlertsHarness({
    snap: { generated_at_utc: "2026-11-21T00:00:00Z", markets: [], candles: {}, orderbooks: {} },
    fetchHandler: async () => ({ ok: true, status: 200, json: async () => ({ trades: [], markets: [] }) }),
  });
  await flushMicrotasks();

  const list = Array.from({ length: 95 }, (_, i) => `T-${i}`);
  const batches = h.internals.batchTickers(list);
  assert.deepEqual(Array.from(batches, (b) => b.length), [40, 40, 15]);
});

test("alerts.js polls GET /markets?tickers=..., detects previous_price swing, resolution, and live candles", async () => {
  const nowS = Math.floor(Date.now() / 1000);
  const snap = {
    generated_at_utc: "2026-11-21T00:00:00Z",
    markets: [
      {
        market_ticker: "KXBTC-LIVE",
        market_title: "Bitcoin above $100k",
        topic: "crypto",
        series_ticker: "KXBTC",
        event_ticker: "KXBTC-EV",
        market_url: "https://external-api.demo.kalshi.co/trade-api/v2/markets/KXBTC-LIVE",
        est_dollar_volume: 50000,
        last_price_dollars: "0.5000",
        yes_bid_dollars: "0.4900",
        yes_ask_dollars: "0.5100",
        volume_fp: "10000.00",
        status: "active",
        result: "",
        settlement_sources: [{ name: "CF Benchmarks", url: "https://www.cfbenchmarks.com/" }],
      },
      {
        market_ticker: "KXGOLF-SETTLED",
        market_title: "PGA Winner Test",
        topic: "golf",
        series_ticker: "KXGOLF",
        event_ticker: "KXGOLF-EV",
        market_url: "https://external-api.demo.kalshi.co/trade-api/v2/markets/KXGOLF-SETTLED",
        est_dollar_volume: 10000,
        last_price_dollars: "0.9900",
        yes_bid_dollars: "0.9800",
        yes_ask_dollars: "1.0000",
        volume_fp: "5000.00",
        status: "active",
        result: "",
        settlement_sources: [{ name: "PGA TOUR", url: "https://www.pgatour.com/" }],
      },
    ],
    candles: {},
    orderbooks: {},
  };

  const h = loadAlertsHarness({
    snap,
    fetchHandler: async (url) => {
      if (url.includes("/markets/trades")) {
        return { ok: true, status: 200, json: async () => ({ trades: [] }) };
      }
      if (url.includes("/markets?tickers=")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            markets: [
              {
                ticker: "KXBTC-LIVE",
                last_price_dollars: "0.6000",
                previous_price_dollars: "0.5000",
                yes_bid_dollars: "0.5900",
                yes_ask_dollars: "0.6100",
                volume_fp: "10500.00",
                open_interest_fp: "2000.00",
                status: "active",
                result: "",
              },
              {
                ticker: "KXGOLF-SETTLED",
                last_price_dollars: "1.0000",
                previous_price_dollars: "0.9900",
                yes_bid_dollars: "0.9900",
                yes_ask_dollars: "1.0000",
                volume_fp: "5000.00",
                open_interest_fp: "0.00",
                status: "finalized",
                result: "yes",
              },
            ],
          }),
        };
      }
      if (url.includes("/candlesticks?")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            candlesticks: [
              {
                end_period_ts: nowS - 120,
                price: { close_dollars: "0.5000" },
                yes_bid: { close_dollars: "0.4900" },
                yes_ask: { close_dollars: "0.5100" },
              },
              {
                end_period_ts: nowS - 60,
                price: { close_dollars: "0.6000" },
                yes_bid: { close_dollars: "0.5900" },
                yes_ask: { close_dollars: "0.6100" },
              },
            ],
          }),
        };
      }
      if (url.includes("/orderbook?")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            orderbook_fp: {
              yes_dollars: [["0.5900", "25.00"]],
              no_dollars: [["0.3900", "15.00"]],
            },
          }),
        };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    },
  });

  await flushMicrotasks(12);

  assert.ok(h.fetchCalls.some((u) => u.includes("/markets?tickers=")));
  assert.ok(!h.fetchCalls.some((u) => u.includes("status=open&limit=1000")));
  assert.ok(h.fetchCalls.some((u) => u.includes("/series/KXBTC/markets/KXBTC-LIVE/candlesticks?")));

  const feedHtml = h.getEl("chatAll").innerHTML;
  assert.match(feedHtml, /KXBTC-LIVE/);
  assert.match(feedHtml, /CF Benchmarks/);
  assert.match(feedHtml, /RESOLVED YES/);
  assert.match(feedHtml, /KXGOLF-SETTLED/);
  assert.match(h.getEl("fetchStatus").textContent, /2\/2 tracked markets updated/);
  assert.match(h.getEl("chartNoteAlerts").textContent, /live candlesticks/);
});

test("parseOrderbookFp derives YES asks and spread accurately", async () => {
  const h = loadAlertsHarness({
    snap: { generated_at_utc: "2026-11-21T00:00:00Z", markets: [], candles: {}, orderbooks: {} },
    fetchHandler: async () => ({ ok: true, status: 200, json: async () => ({ trades: [], markets: [] }) }),
  });
  await flushMicrotasks();

  const book = h.internals.parseOrderbookFp({
    yes_dollars: [["0.4200", "10.00"], ["0.4000", "5.00"]],
    no_dollars: [["0.5500", "8.00"]],
  });
  assert.equal(book.best_yes_bid, 0.42);
  assert.equal(book.best_yes_ask_derived, 0.45);
  assert.equal(book.spread_derived, 0.03);
  assert.equal(book.yes_bid_contracts, 15);
  assert.equal(book.derived_ask_contracts, 8);
});

test("generated HTML pages and causes.html align with snapshot data and official endpoints", () => {
  const indexHtml = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
  assert.match(indexHtml, /id="topicStrip"/);
  assert.match(indexHtml, /id="viewMode"/);
  assert.match(indexHtml, /fetchLiveCandles/);
  assert.match(indexHtml, /fetchLiveOrderbook/);
  assert.match(indexHtml, /settlement_sources/);

  const alertsHtml = fs.readFileSync(path.join(ROOT, "alerts.html"), "utf8");
  assert.match(alertsHtml, /GET \/markets\?tickers=/);
  assert.doesNotMatch(alertsHtml, /GET \/markets\?status=open&amp;limit=1000/);

  const causesHtml = fs.readFileSync(path.join(ROOT, "pages/causes.html"), "utf8");
  assert.match(causesHtml, /KR\.snapshot\(\)/);
  assert.doesNotMatch(causesHtml, /dashboard_meta\.json/);
  assert.doesNotMatch(causesHtml, /series_index\.json/);

  const snap = JSON.parse(fs.readFileSync(path.join(ROOT, "data/snapshot.json"), "utf8"));
  const withSources = (snap.markets || []).filter((m) => Array.isArray(m.settlement_sources) && m.settlement_sources.length > 0);
  assert.ok(withSources.length > 0, "snapshot.json markets should carry settlement_sources for causes.html");
});
