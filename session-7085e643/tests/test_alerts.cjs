/* Offline verification of assets/alerts.js — run with node, no network, no browser.
 *
 * Loads assets/site.js and assets/alerts.js into a minimal DOM stub, then checks the
 * behaviour the page relies on:
 *   1. the model screen accepts / rejects the documented cases and says why
 *   2. snapshot-derived alerts are built from the collector's tick history (KR.detectJumps)
 *   3. a live poll turn produces an alert on a >= $0.10 move and none on a smaller one
 *   4. a polled official `result` settles the matching lines (yes/no)
 *   5. render() writes both chats and the status banner, newest first
 *
 * Run: node session-7085e643/tests/test_alerts.js
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
let failures = 0;
let passes = 0;

function check(name, cond, extra) {
  if (cond) { passes++; console.log("PASS  " + name); }
  else { failures++; console.log("FAIL  " + name + (extra ? " :: " + extra : "")); }
}

/* ---------------- minimal DOM stub ---------------- */
function makeEl() {
  return {
    id: null, innerHTML: "", textContent: "", scrollTop: 0,
    style: {}, dataset: {},
    addEventListener() {},
  };
}
const els = {};
function getEl(id) { if (!els[id]) { els[id] = makeEl(); els[id].id = id; } return els[id]; }

const window = { KR: null, location: { search: "" }, setInterval: () => 0, clearInterval: () => {} };
global.window = window;
global.document = {
  getElementById: getEl,
  querySelector: () => null,
  addEventListener: () => {},
  documentElement: { style: {} },
};
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.fetch = async () => { throw new Error("network disabled in this test"); };

/* ---------------- load the two scripts ---------------- */
const siteSrc = fs.readFileSync(path.join(ROOT, "assets", "site.js"), "utf8");
const alertsSrc = fs.readFileSync(path.join(ROOT, "assets", "alerts.js"), "utf8");
/* `fetch` is deliberately NOT a parameter: the scripts must see the live global so the
   test can swap the network stub between phases, exactly as a browser would. */
new Function("window", "document", "getComputedStyle", siteSrc + "\n" + alertsSrc)(
  window, global.document, global.getComputedStyle);

const KR = window.KR;
const A = KR.alerts;
check("KR and KR.alerts are exposed", !!KR && !!A);

/* ---------------- 1. the model screen ---------------- */
function mkAlert(over) {
  const base = {
    id: 1, ts: Date.now(), fromV: 0.20, toV: 0.35, change: 0.15, dir: "up",
    source: "live", topic: "crypto", title: "T", ticker: "T-1", marketUrl: null,
    closeTime: new Date(Date.now() + 20 * 86400000).toISOString(),
    settled: false, result: null, volume24h: 500,
  };
  return Object.assign(base, over || {});
}
// up move to 0.35 -> favoured side NO at 0.65 entry: too rich, must fail
let s = A.screen(mkAlert());
check("screen rejects an entry above $0.45 and says why",
  s.ok === false && /entry above/.test(s.reason), JSON.stringify(s));

// up move to 0.85 -> favoured side NO at 0.15 entry: cheap, passes
s = A.screen(mkAlert({ fromV: 0.75, toV: 0.85, change: 0.10 }));
check("screen accepts a cheap favoured-side entry ($0.15 NO)", s.ok === true, JSON.stringify(s));
check("screen reports the potential ROI as arithmetic, not a claim",
  s.ok === true && s.potentialROI > 500 && s.potentialROI < 700, String(s.potentialROI));

// down move to 0.20 -> favoured side YES at 0.20: cheap, passes
s = A.screen(mkAlert({ fromV: 0.35, toV: 0.20, change: -0.15, dir: "down" }));
check("screen accepts a cheap YES after a down move", s.ok === true && s.side === "YES",
  JSON.stringify(s));

// thin book: 24h volume below the floor must fail
s = A.screen(mkAlert({ toV: 0.85, change: 0.10, volume24h: 5 }));
check("screen rejects a move on a book below the volume floor", s.ok === false, JSON.stringify(s));

// far-dated market must fail
s = A.screen(mkAlert({ toV: 0.85, change: 0.10,
  closeTime: new Date(Date.now() + 400 * 86400000).toISOString() }));
check("screen rejects a market that closes beyond the window", s.ok === false, JSON.stringify(s));

// an up move to exactly 1.00: the favoured NO side is free, so the potential ROI is not
// a number - it must be reported as such rather than rendered as 0%
s = A.screen(mkAlert({ fromV: 0.90, toV: 1.00, change: 0.10 }));
check("screen handles a free entry (price 1.00) without inventing an ROI",
  s.ok === true && s.potentialROI === null, JSON.stringify(s));

// missing price / missing close time must fail, never throw
s = A.screen(mkAlert({ toV: null, change: 0.10 }));
check("screen rejects a missing post-move price", s.ok === false && !!s.reason, JSON.stringify(s));
s = A.screen(mkAlert({ toV: 0.85, change: 0.10, closeTime: null }));
check("screen rejects a missing close time", s.ok === false && !!s.reason, JSON.stringify(s));

/* ---------------- 2. snapshot-derived alerts from history ---------------- */
(async function () {
  const ts = Date.now();
  const sec = Math.floor(ts / 1000);
  const history = {
    updated_at_utc: "2026-11-20T00:00:00+00:00",
    points: {
      // 0.20 -> 0.90 is a >= $0.10 jump; must produce exactly one line
      "H-1": [{ t: sec - 600, last: "0.20" }, { t: sec - 300, last: "0.90" }],
      // small moves -> no alert
      "H-2": [{ t: sec - 600, last: "0.30" }, { t: sec - 300, last: "0.35" }],
    },
  };
  const snap = {
    generated_at_utc: "2026-11-20T00:00:00+00:00",
    counts: { markets_in_scope: 2 },
    markets: [
      { market_ticker: "H-1", topic: "elections", market_title: "Half",
        market_url: "https://external-api.demo.kalshi.co/trade-api/v2/markets/H-1",
        last_price_dollars: "0.90", close_time: "2026-11-30T00:00:00Z", volume_24h_fp: "900",
        est_dollar_volume: 90 },
      { market_ticker: "H-2", topic: "crypto", market_title: "Small",
        market_url: "https://external-api.demo.kalshi.co/trade-api/v2/markets/H-2",
        last_price_dollars: "0.35", close_time: "2026-11-30T00:00:00Z", volume_24h_fp: "900",
        est_dollar_volume: 10 },
    ],
  };
  KR.snapshot = async () => snap;
  KR.history = async () => history;
  KR.resolutions = async () => ({ resolutions: [] });
  await A.init({ poll: false });

  const allLines = getEl("alertAll").innerHTML;
  check("snapshot history produced exactly one alert line",
    (allLines.match(/chatline/g) || []).length === 1, String((allLines.match(/chatline/g) || []).length));
  check("the alert names the market and the magnitude",
    allLines.indexOf("H-1") >= 0 && allLines.indexOf("0.7000") >= 0, allLines.slice(0, 200));
  check("snapshot-derived lines are labelled as snapshot, not live",
    allLines.indexOf("snapshot") >= 0 && allLines.indexOf("live poll") < 0);
  check("the model-screen chat shows the passing line",
    getEl("alertModel").innerHTML.indexOf("H-1") >= 0, getEl("alertModel").innerHTML.slice(0, 200));
  check("a passing line is tagged as a model screen, not a claim",
    getEl("alertModel").innerHTML.indexOf("model screen") >= 0);
  check("status banner reports the offline mode and the poll interval",
    getEl("alertStatus").innerHTML.indexOf("live polling unavailable") >= 0,
    getEl("alertStatus").innerHTML.slice(0, 160));

  /* ---------------- 3. a live poll turn ---------------- */
  let pollRows = [
    { ticker: "H-1", title: "Half", last_price_dollars: "1.00", volume_24h_fp: "1200",
      close_time: "2026-11-30T00:00:00Z", result: "", yes_ask_dollars: "1.00" },
  ];
  global.fetch = async (url) => {
    if (String(url).indexOf("tickers=") >= 0) return { ok: true, json: async () => ({ markets: pollRows }) };
    return { ok: false, json: async () => ({}) };
  };
  await A.pollOnce();
  const afterPoll = getEl("alertAll").innerHTML;
  check("a live poll produced a new alert for the >= $0.10 move",
    afterPoll.indexOf("live poll") >= 0, afterPoll.slice(0, 200));
  check("the live line shows the new price", afterPoll.indexOf("1.0000") >= 0, afterPoll.slice(0, 260));
  check("status banner flips to live polling",
    getEl("alertStatus").innerHTML.indexOf("polling the official demo API") >= 0,
    getEl("alertStatus").innerHTML.slice(0, 160));

  /* a repeated price must not add a line */
  await A.pollOnce();
  const countAfter = (getEl("alertAll").innerHTML.match(/chatline/g) || []).length;
  check("a repeated price does not re-announce the same move", countAfter === 2, String(countAfter));

  /* a move under $0.10 must not alert */
  pollRows[0].last_price_dollars = "0.95";
  await A.pollOnce();
  check("a move under $0.10 does not alert",
    (getEl("alertAll").innerHTML.match(/chatline/g) || []).length === 2);

  /* ---------------- 4. resolution ---------------- */
  pollRows[0] = { ticker: "H-1", title: "Half", last_price_dollars: "0.95",
    volume_24h_fp: "1200", close_time: "2026-11-30T00:00:00Z", result: "yes",
    settlement_value_dollars: "1.0000" };
  await A.pollOnce();
  const settled = getEl("alertAll").innerHTML;
  check("the official result settles the matching lines", settled.indexOf(">YES<") >= 0,
    settled.slice(0, 300));
  check("settled lines are marked resolved", settled.indexOf("chatline resolved") >= 0);
  check("newest first: the live line appears above the snapshot line",
    settled.indexOf("live poll") < settled.lastIndexOf("snapshot"));

  /* ---------------- 5. offline poll keeps the snapshot feed ---------------- */
  global.fetch = async () => { throw new Error("offline"); };
  await A.pollOnce();
  check("an offline poll keeps the existing lines and reports offline",
    (getEl("alertAll").innerHTML.match(/chatline/g) || []).length === 2 &&
    getEl("alertStatus").innerHTML.indexOf("live polling unavailable") >= 0);

  console.log("\n" + (failures ? failures + " failure(s)" : "all session-7085e643 alert-desk checks passed") +
    " (" + passes + " passed)");
  process.exit(failures ? 1 : 0);
})();
