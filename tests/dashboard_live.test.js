// Tests for the dashboard's live layer (session d5905246).
//
// What is asserted, and why each assertion exists:
//   1. ask side is DERIVED from NO bids (Kalshi returns no ask array), and an empty
//      side is null — never 0.00, which would read as a real price.
//   2. the chart opens with points: with a collector that may be hours behind, the
//      initial window is widened to the newest official point instead of showing an
//      empty 1-hour chart (defect observed on the live site 2026-11-21).
//   3. a live poll appends a point from the official order-book response and renders
//      the contract counts at each price.
//   4. a failed poll reports the failure and invents nothing.
//
// Official references:
//   https://docs.kalshi.com/api-reference/market/get-market-orderbook
//   https://docs.kalshi.com/api-reference/market/get-market
//   https://docs.kalshi.com/api-reference/market/get-markets

import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM, VirtualConsole } from "jsdom";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json" };

function stubCanvas(dom) {
  dom.window.HTMLCanvasElement.prototype.getContext = function () {
    const noop = () => {};
    return {
      setTransform: noop, clearRect: noop, fillRect: noop, beginPath: noop,
      moveTo: noop, lineTo: noop, stroke: noop, fill: noop, arc: noop,
      closePath: noop, fillText: noop, save: noop, restore: noop, setLineDash: noop,
      createLinearGradient: () => ({ addColorStop: noop }),
      measureText: () => ({ width: 10 }),
    };
  };
}

function serveRepo() {
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent((req.url || "/").split("?")[0]);
    let file = path.join(ROOT, url === "/" ? "index.html" : url);
    if (file.endsWith("/")) file = path.join(file, "index.html");
    if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404); res.end("not found"); return;
    }
    res.writeHead(200, { "content-type": MIME[path.extname(file)] || "application/octet-stream" });
    res.end(fs.readFileSync(file));
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server)));
}

// Documented order-book shape: orderbook_fp.{yes_dollars,no_dollars} = [[price, count], …];
// no ask array exists, a YES ask at p is a NO bid at 1-p.
const BOOK = {
  orderbook_fp: {
    yes_dollars: [["0.3000", "12.00"], ["0.3500", "40.00"], ["0.2000", "0.00"]],
    no_dollars: [["0.6000", "25.00"], ["0.5500", "8.00"]],
  },
};
const MARKET = { market: { ticker: "TEST-YES", last_price_dollars: "0.3600", status: "active" } };

function jsonResponse(obj, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => obj };
}

async function loadDashboard(mode) {
  const server = await serveRepo();
  const base = `http://127.0.0.1:${server.address().port}`;
  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => { if (!/Not implemented/.test(e.message)) errors.push(e.message); });
  const dom = await JSDOM.fromURL(`${base}/index.html`, {
    runScripts: "dangerously", resources: "usable", pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(win) {
      stubCanvas(win);
      win.fetch = async (url, opts) => {
        const u = String(url);
        if (u.includes("external-api.demo.kalshi.co")) {
          if (mode === "fail") return jsonResponse({ error: "unavailable" }, 503);
          if (u.includes("/orderbook")) return jsonResponse(BOOK);
          if (/\/markets\/[^/?]+(\?|$)/.test(u)) return jsonResponse(MARKET);
          return jsonResponse({ market: MARKET.market });
        }
        return fetch(new URL(u, base), opts);
      };
    },
  });
  await new Promise((r) => setTimeout(r, 2800));
  server.close();
  return { dom, doc: dom.window.document, errors };
}

test("derived ask side, contract counts and empty sides are never zero", () => {
  return loadDashboard("ok").then(({ dom }) => {
    const KR = dom.window.KR;
    const q = KR.bookQuote(BOOK);
    assert.equal(q.best_yes_bid, 0.35, "highest YES bid with contracts");
    assert.equal(q.best_yes_bid_contracts, 40);
    assert.equal(q.best_yes_ask, 0.4, "1 - best NO bid (0.60)");
    assert.equal(q.best_yes_ask_contracts, 25, "asks inherit the NO bid's contract count");
    assert.equal(q.spread, 0.05);
    assert.equal(q.yes_bid_contracts, 52, "zero-count level excluded");
    assert.equal(q.ask_contracts, 33);
    const empty = KR.bookQuote({ orderbook_fp: { yes_dollars: [], no_dollars: [] } });
    assert.equal(empty.best_yes_bid, null);
    assert.equal(empty.best_yes_ask, null);
    assert.equal(KR.liveValue(empty, MARKET.market, "mid"), null, "no mid without both sides");
    assert.equal(KR.liveValue(q, MARKET.market, "mid"), 0.375);
    assert.equal(KR.liveValue(q, MARKET.market, "yes_bid_close"), 0.35);
    assert.equal(KR.liveValue(q, MARKET.market, "yes_ask_close"), 0.4);
    assert.equal(KR.liveValue(q, MARKET.market, "close"), 0.36);
    assert.equal(KR.liveValue(q, null, "close"), null, "market record missing → blank, not 0");
    dom.window.close();
  });
});

test("dashboard opens with chart points, a data-backed market and a live poll", async () => {
  const { dom, doc, errors } = await loadDashboard("ok");
  assert.deepEqual(errors, []);
  const note = doc.querySelector("#chartNote").textContent;
  assert.match(note, /[1-9]\d* points/, `chart should have points, got: ${note}`);
  assert.match(note, /live polls/);
  const selected = doc.querySelector("#mktSel").value;
  const selectedOption = [...doc.querySelectorAll("#mktSel option")].find((o) => o.value === selected);
  assert.ok(selectedOption, "a market is selected by default");
  assert.ok(!/no chart history yet/.test(selectedOption.textContent),
    `default market must have chart data, got: ${selectedOption.textContent}`);
  assert.match(doc.querySelector("#liveBadge").textContent, /live/);
  assert.match(doc.querySelector("#liveBook").textContent, /Best YES bid/);
  assert.match(doc.querySelector("#liveBook").textContent, /contracts at this price/);
  assert.doesNotMatch(doc.querySelector("#liveBook").textContent, /failed/i);
  dom.window.close();
});

test("a failed live poll reports the error and invents no price", async () => {
  const { dom, doc } = await loadDashboard("fail");
  assert.match(doc.querySelector("#liveBadge").textContent, /live poll failed/);
  assert.match(doc.querySelector("#liveBook").textContent, /request failed/i);
  assert.doesNotMatch(doc.querySelector("#liveBook").textContent, /\$0\.00/);
  dom.window.close();
});
