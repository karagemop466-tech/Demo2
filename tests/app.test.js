import test from "node:test";
import assert from "node:assert/strict";
import {
  buildChartSvg,
  buildOrderbookRows,
  escapeHtml,
  getTopicsForEvent,
  isActiveBinaryMarket,
  orderbookBidNotional,
  resolutionForMarket,
} from "../assets/js/app.js";

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
