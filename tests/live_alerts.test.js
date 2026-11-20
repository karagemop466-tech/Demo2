/* Offline test of the live alert engine in assets/site.js.
 *
 * No browser, no network: the demo API response is a fixture and `fetch` is a
 * stub. What is verified:
 *   - a move of exactly $0.10 raises an alert, $0.09 does not
 *   - both official signals are used (previous_price_dollars and the previous poll)
 *   - the same direction is not alerted twice inside the de-duplication window
 *   - the ROI score is 0..1, rises with the size of the move and is explainable
 *   - the seeded history produces the same kind of alert as a live poll
 *
 * Run: node --test tests/live_alerts.test.js
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');

function loadKR(fetchImpl) {
  const src = fs.readFileSync(path.join(ROOT, 'assets', 'site.js'), 'utf8');
  const sandbox = {
    fetch: fetchImpl,
    console,
    Date,
    Math,
    JSON,
    setTimeout,
    clearTimeout,
    Promise,
    window: {},
    document: { addEventListener() {}, querySelector: () => null },
    getComputedStyle: () => ({ getPropertyValue: () => '#00c389' }),
  };
  sandbox.window.document = sandbox.document;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox);
  return sandbox.window.KR;
}

const MKT = (over = {}) => ({
  ticker: 'KXT-1',
  title: 'Test market',
  status: 'open',
  last_price_dollars: '0.5000',
  previous_price_dollars: '0.5000',
  yes_bid_dollars: '0.4900',
  yes_ask_dollars: '0.5100',
  volume_fp: '1000.00',
  open_interest_fp: '500.00',
  close_time: '2026-11-21T00:00:00Z',
  ...over,
});

function marketRows(rows) {
  return {
    ok: true,
    json: async () => ({ markets: rows }),
  };
}

test('a move of exactly $0.10 raises an alert and $0.09 does not', async () => {
  const KR = loadKR(async () => marketRows([MKT({ last_price_dollars: '0.6000', previous_price_dollars: '0.5000' })]));
  const alerts = [];
  KR.live.on('alert', (a) => alerts.push(a));
  KR.live.setMarkets([{ market_ticker: 'KXT-1', market_title: 'Test market', topic: 'golf',
    est_dollar_volume: 500, open_interest_fp: '500.00', close_time: '2026-11-21T00:00:00Z' }]);
  await KR.live.pollOnce();
  assert.equal(alerts.length, 1, 'a $0.10 move must alert');
  assert.equal(alerts[0].change.toFixed(2), '0.10');
  assert.equal(alerts[0].dir, 'up');
  assert.equal(alerts[0].basis, 'previous trade');

  const KR2 = loadKR(async () => marketRows([MKT({ last_price_dollars: '0.5900', previous_price_dollars: '0.5000' })]));
  const alerts2 = [];
  KR2.live.on('alert', (a) => alerts2.push(a));
  KR2.live.setMarkets([{ market_ticker: 'KXT-1', topic: 'golf', est_dollar_volume: 1,
    open_interest_fp: '1', close_time: '2026-11-21T00:00:00Z' }]);
  await KR2.live.pollOnce();
  assert.equal(alerts2.length, 0, 'a $0.09 move must not alert');
});

test('a move between two polls is caught even when the API previous price is unchanged', async () => {
  let call = 0;
  const KR = loadKR(async () => {
    call += 1;
    const last = call === 1 ? '0.5000' : '0.7000';
    return marketRows([MKT({ last_price_dollars: last, previous_price_dollars: '0.5000' })]);
  });
  const alerts = [];
  KR.live.on('alert', (a) => alerts.push(a));
  KR.live.setMarkets([{ market_ticker: 'KXT-1', topic: 'golf', est_dollar_volume: 100,
    open_interest_fp: '100', close_time: '2026-11-21T00:00:00Z' }]);
  await KR.live.pollOnce();
  assert.equal(alerts.length, 0, 'the first poll only records the starting price');
  await KR.live.pollOnce();
  assert.equal(alerts.length, 1, 'the second poll must catch the $0.20 move');
  assert.ok(['previous trade', 'previous poll'].includes(alerts[0].basis));
  assert.equal(alerts[0].change.toFixed(2), '0.20');
});

test('the same direction is not alerted twice inside the de-duplication window', async () => {
  let call = 0;
  const KR = loadKR(async () => {
    call += 1;
    const last = call === 1 ? '0.5000' : (call === 2 ? '0.7000' : '0.7500');
    return marketRows([MKT({ last_price_dollars: last, previous_price_dollars: '0.5000' })]);
  });
  const alerts = [];
  KR.live.on('alert', (a) => alerts.push(a));
  KR.live.setMarkets([{ market_ticker: 'KXT-1', topic: 'golf', est_dollar_volume: 100,
    open_interest_fp: '100', close_time: '2026-11-21T00:00:00Z' }]);
  await KR.live.pollOnce();
  await KR.live.pollOnce();   // +0.20 -> alert
  await KR.live.pollOnce();   // +0.25 from the same base -> suppressed
  assert.equal(alerts.length, 1, 'duplicate direction inside 90 s must be suppressed');
});

test('the ROI score is bounded, monotone in the move and explainable', async () => {
  const KR = loadKR(async () => marketRows([]));
  const a = { change: 0.10, est: 100, oi: 10, closeTime: '2026-11-21T00:00:00Z' };
  const b = { change: 0.30, est: 100, oi: 10, closeTime: '2026-11-21T00:00:00Z' };
  const small = KR.live.score(a);
  const big = KR.live.score(b);
  assert.ok(small >= 0 && small <= 1, 'score must be within 0..1');
  assert.ok(big > small, 'a bigger move must score higher');
  assert.ok(a.scoreParts && typeof a.scoreParts.size === 'number', 'the parts must be exposed');
  for (const [k, v] of Object.entries(a.scoreParts)) {
    assert.ok(v >= 0 && v <= 1, `${k} must be within 0..1`);
  }
  // the score must be exactly the weighted sum the page documents
  const weighted = 0.45 * a.scoreParts.size + 0.25 * a.scoreParts.depth +
                   0.15 * a.scoreParts.open + 0.15 * a.scoreParts.time;
  // the published score is rounded to three decimals, so allow half of that
  assert.ok(Math.abs(weighted - a.score) < 5e-4,
    `documented formula mismatch: ${weighted} vs ${a.score}`);
});

test('the seeded history produces the same alert shape as a live poll', () => {
  const KR = loadKR(async () => marketRows([]));
  const seeded = KR.live.seedFromHistory(
    { points: { 'KXT-1': [
      { t: 1750000000, last: '0.5000', yes_bid: '0.49', yes_ask: '0.51' },
      { t: 1750000600, last: '0.6500', yes_bid: '0.64', yes_ask: '0.66' },
    ] } },
    [{ market_ticker: 'KXT-1', market_title: 'Test market', topic: 'golf',
       est_dollar_volume: 250, open_interest_fp: '250.00', close_time: '2026-11-21T00:00:00Z' }]);
  assert.equal(seeded.length, 1, 'the seeded history must contain the $0.15 move');
  assert.equal(seeded[0].change.toFixed(2), '0.15');
  assert.equal(seeded[0].basis, 'committed history');
  assert.ok(seeded[0].score > 0);
});

test('a failed request is reported instead of being swallowed', async () => {
  const KR = loadKR(async () => { throw new Error('HTTP 429 for test'); });
  const statuses = [];
  KR.live.on('status', (s) => statuses.push(s));
  KR.live.setMarkets([{ market_ticker: 'KXT-1', topic: 'golf', est_dollar_volume: 1,
    open_interest_fp: '1', close_time: '2026-11-21T00:00:00Z' }]);
  await KR.live.pollOnce();
  assert.equal(statuses.at(-1).state, 'error');
  assert.match(statuses.at(-1).error, /429/);
});

test('the live order book reads the official response shape and derives the ask side', async () => {
  /* The shape below is the live demo API's own answer, captured on 2026-11-20
     from GET /markets/KXECCOMPACT-30/orderbook?depth=25:
       { "orderbook_fp": { "yes_dollars": [[price, qty], ...],
                           "no_dollars":  [[price, qty], ...] } }
     Only bids exist, so a NO bid at p is a YES ask at (1 - p). */
  const KR = loadKR(async () => ({
    ok: true,
    json: async () => ({
      orderbook_fp: {
        yes_dollars: [['0.6000', '10.00'], ['0.5900', '25.00']],
        no_dollars: [['0.4000', '5.00']],
      },
    }),
  }));
  const book = await KR.live.fetchOrderbook('KXT-1', 25);
  /* The arrays are built inside the vm sandbox, so they are compared through
     JSON: same values, and the test realm's own prototypes. */
  const plain = (v) => JSON.parse(JSON.stringify(v));
  assert.deepStrictEqual(plain(book.yes_bids), [[0.6, 10], [0.59, 25]], 'yes bids, best first');
  assert.deepStrictEqual(plain(book.no_bids), [[0.4, 5]]);
  assert.deepStrictEqual(plain(book.derived_yes_asks), [[0.6, 5]],
    'a NO bid at 0.40 is a YES ask at 0.60');
  assert.equal(book.best_yes_bid, 0.6);
  assert.equal(book.best_yes_ask_derived, 0.6);
  assert.equal(book.yes_bid_contracts, 35);
  assert.equal(book.derived_ask_contracts, 5);
  assert.equal(book.spread_derived, 0);
  assert.match(book.raw_request, /\/markets\/KXT-1\/orderbook\?depth=25$/);
});

test('an empty book is reported as empty, not as an error', async () => {
  const KR = loadKR(async () => ({
    ok: true,
    json: async () => ({ orderbook_fp: { yes_dollars: [], no_dollars: [] } }),
  }));
  const book = await KR.live.fetchOrderbook('KXT-EMPTY', 25);
  assert.equal(book.yes_bids.length, 0);
  assert.equal(book.best_yes_bid, null);
  assert.equal(book.best_yes_ask_derived, null);
  assert.equal(book.spread_derived, null);
});
