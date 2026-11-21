import test from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, verify as cryptoVerify } from "node:crypto";
import {
  buildChartSvg,
  buildOrderbookRows,
  escapeHtml,
  getTopicsForEvent,
  isActiveBinaryMarket,
  orderbookBidNotional,
  resolutionForMarket,
} from "../monitor/assets/js/app.js";
import { KalshiClient, buildCreateOrderV2Payload } from "../server/kalshiClient.js";

test("topic matching uses requested topic terms and does not confuse Las Vegas with gas", () => {
  assert.deepEqual(getTopicsForEvent({ title: "US gasoline price forecast", category: "Economics" }), ["gas-prices"]);
  assert.deepEqual(getTopicsForEvent({ title: "Who wins the presidential election?", category: "Politics" }), ["elections"]);
  assert.deepEqual(getTopicsForEvent({ title: "Best picture winner", category: "Entertainment" }), ["culture"]);
  assert.deepEqual(getTopicsForEvent({ title: "Bitcoin above threshold", category: "Crypto" }), ["crypto"]);
  assert.deepEqual(getTopicsForEvent({ title: "PGA tournament winner", category: "Sports" }), ["golf"]);
  assert.deepEqual(getTopicsForEvent({ title: "Las Vegas visitor count", category: "Tourism" }), []);
});

test("topic matcher can place an event in more than one explicit requested group", () => {
  assert.deepEqual(
    getTopicsForEvent({ title: "Crypto market during the presidential election", category: "Politics" }),
    ["elections", "crypto"],
  );
});

test("only active, unresolved binary markets enter the live list", () => {
  assert.equal(isActiveBinaryMarket({ market_type: "binary", status: "active", result: "" }), true);
  assert.equal(isActiveBinaryMarket({ market_type: "binary", status: "closed", result: "" }), false);
  assert.equal(isActiveBinaryMarket({ market_type: "binary", status: "active", result: "yes" }), false);
  assert.equal(isActiveBinaryMarket({ market_type: "scalar", status: "active", result: "" }), false);
});

test("orderbook bid-side notional sums price times returned contract quantity", () => {
  const book = {
    yes_dollars: [["0.5000", "10.00"], ["0.2500", "4.00"]],
    no_dollars: [["0.3000", "10.00"]],
  };
  assert.equal(orderbookBidNotional(book), 9);
  assert.equal(orderbookBidNotional({ yes_dollars: [], no_dollars: [] }), 0);
  assert.equal(orderbookBidNotional(null), null);
});

test("orderbook rows preserve contract counts and mark parity-derived asks", () => {
  const rows = buildOrderbookRows({
    orderbook_fp: {
      yes_dollars: [["0.4000", "5.50"]],
      no_dollars: [["0.2000", "3.00"]],
    },
  });
  assert.ok(rows);
  assert.ok(rows.some((row) => row.side === "YES bid" && row.price === 0.4 && row.contracts === 5.5 && row.derived === false));
  assert.ok(rows.some((row) => row.side === "NO ask · implied" && row.price === 0.6 && row.contracts === 5.5 && row.derived === true));
  assert.ok(rows.some((row) => row.side === "YES ask · implied" && row.price === 0.8 && row.contracts === 3 && row.derived === true));
});

test("resolution labels distinguish determined, disputed, and finalized YES/NO results", () => {
  assert.equal(resolutionForMarket({ result: "yes", status: "determined" }), "Determined YES · settlement pending");
  assert.equal(resolutionForMarket({ result: "no", status: "disputed" }), "Disputed · prior result NO");
  assert.equal(resolutionForMarket({ result: "yes", status: "finalized" }), "Settled YES");
  assert.equal(resolutionForMarket({ result: "", status: "finalized" }), "Finalized · result not returned");
  assert.equal(resolutionForMarket({ result: "scalar", status: "finalized" }), "Result: scalar · status finalized");
});

test("HTML escaping protects dynamic market text", () => {
  assert.equal(escapeHtml(`<event & \"title\">`), "&lt;event &amp; &quot;title&quot;&gt;");
});

test("chart output has timestamp axis labels and does not invent a missing point", () => {
  assert.equal(buildChartSvg([]), "");
  const svg = buildChartSvg([{ ts: Date.now() - 60_000, price: 0.3 }, { ts: Date.now(), price: 0.7 }], "1h");
  assert.match(svg, /<svg/);
  assert.match(svg, /horizontal axis is time/);
  assert.match(svg, /class=\"chart-path\"/);
});

test("buildCreateOrderV2Payload maps sides, preserves unified YES price, and formats V2 fields", () => {
  const buyYes = buildCreateOrderV2Payload({
    market_ticker: "KXBTC-100K",
    side: "yes",
    action: "buy",
    price: 0.42,
    count: 5,
    time_in_force: "gtc",
  });
  assert.equal(buyYes.ticker, "KXBTC-100K");
  assert.equal(buyYes.side, "bid");
  assert.equal(buyYes.price, "0.4200");
  assert.equal(buyYes.count, "5.00");
  assert.equal(buyYes.time_in_force, "good_till_canceled");
  assert.equal(buyYes.self_trade_prevention_type, "taker_at_cross");
  assert.ok(buyYes.client_order_id.length > 0);

  assert.equal(buildCreateOrderV2Payload({ ticker: "T", side: "no", action: "buy", price: 0.42, count: 1 }).side, "ask");
  assert.equal(buildCreateOrderV2Payload({ ticker: "T", side: "no", action: "buy", price: 0.42, count: 1 }).price, "0.4200");
  assert.equal(buildCreateOrderV2Payload({ ticker: "T", side: "yes", action: "sell", price: 0.42, count: 1 }).side, "ask");
  assert.equal(buildCreateOrderV2Payload({ ticker: "T", side: "no", action: "sell", price: 0.42, count: 1 }).side, "bid");

  assert.throws(() => buildCreateOrderV2Payload({ ticker: "T", side: "yes", price: 1.2, count: 1 }), /Invalid order price/);
  assert.throws(() => buildCreateOrderV2Payload({ ticker: "T", side: "maybe", price: 0.5, count: 1 }), /Invalid order side/);
});

test("KalshiClient createOrder posts V2 payload to /portfolio/events/orders and signs full /trade-api/v2 path", async () => {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const privatePem = privateKey.export({ type: "pkcs8", format: "pem" });
  const seen = [];
  const client = new KalshiClient({
    baseUrl: "https://external-api.demo.kalshi.co/trade-api/v2",
    keyId: "test-key-id",
    privateKeyPem: privatePem,
    enabled: true,
    fetchImpl: async (url, init) => {
      seen.push({ url: String(url), init });
      return {
        ok: true,
        status: 201,
        text: async () => JSON.stringify({ order_id: "ord-123", fill_count: "0.00", remaining_count: "2.00" }),
      };
    },
  });

  const resp = await client.createOrder({
    market_ticker: "KXBTC-100K",
    side: "yes",
    action: "buy",
    price: 0.55,
    count: 2,
    client_order_id: "cid-1",
  });
  assert.equal(resp.order_id, "ord-123");
  assert.equal(seen.length, 1);
  assert.equal(seen[0].url, "https://external-api.demo.kalshi.co/trade-api/v2/portfolio/events/orders");
  assert.equal(seen[0].init.method, "POST");
  const sentBody = JSON.parse(seen[0].init.body);
  assert.deepEqual(sentBody, {
    ticker: "KXBTC-100K",
    client_order_id: "cid-1",
    side: "bid",
    count: "2.00",
    price: "0.5500",
    time_in_force: "good_till_canceled",
    self_trade_prevention_type: "taker_at_cross",
  });
  const headers = seen[0].init.headers;
  const signedMsg = Buffer.from(headers["KALSHI-ACCESS-TIMESTAMP"] + "POST/trade-api/v2/portfolio/events/orders", "utf8");
  const sigBuf = Buffer.from(headers["KALSHI-ACCESS-SIGNATURE"], "base64");
  assert.equal(cryptoVerify(null, signedMsg, publicKey, sigBuf), true);
});

test("KalshiClient getAllEvents follows cursor pagination and deduplicates events", async () => {
  const calls = [];
  const client = new KalshiClient({
    baseUrl: "https://external-api.demo.kalshi.co/trade-api/v2",
    enabled: false,
    fetchImpl: async (url) => {
      const u = new URL(String(url));
      const cursor = u.searchParams.get("cursor") || "";
      calls.push(cursor);
      const body = cursor === ""
        ? { events: [{ event_ticker: "EV1" }, { event_ticker: "EV2" }], cursor: "c2" }
        : { events: [{ event_ticker: "EV2" }, { event_ticker: "EV3" }], cursor: "" };
      return { ok: true, status: 200, text: async () => JSON.stringify(body) };
    },
  });

  const res = await client.getAllEvents({ status: "open", limit: 200 });
  assert.deepEqual(calls, ["", "c2"]);
  assert.equal(res.pagesFetched, 2);
  assert.equal(res.truncated, false);
  assert.deepEqual(res.events.map((e) => e.event_ticker), ["EV1", "EV2", "EV3"]);
});
