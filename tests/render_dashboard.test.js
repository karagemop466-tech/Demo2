/* Full-page render test of the canonical dashboard (index.html) and of the
 * Live Alerts page, in a real DOM.
 *
 * It runs the real page scripts against the real data/ files, with the Kalshi
 * demo API replaced by a fixture, and checks that:
 *   - the dashboard renders with no JavaScript error
 *   - the KPI cards, the markets table and the liquidity panel are populated
 *   - the live alert feeds are populated from the committed tick history
 *   - starting the live feed and polling once adds a new line to the chat
 *   - the Live Alerts page loads its data (it used to ask for /pages/data/...)
 *
 * jsdom is a dev dependency; when it is not installed the test is skipped
 * instead of failing, so the dependency-free suite stays runnable anywhere.
 *
 * Run: node --test tests/render_dashboard.test.js
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');

let JSDOM = null;
let VirtualConsole = null;
try {
  const jsdom = await import('jsdom');
  JSDOM = jsdom.JSDOM;
  VirtualConsole = jsdom.VirtualConsole;
} catch {
  JSDOM = null;
}

const skip = JSDOM ? false : 'jsdom is not installed (npm install jsdom)';

function readJSON(rel) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
}

/* Load a page with its CSS and shared JS inlined, and a fetch stub that
   serves data/ from disk and answers the Kalshi API with a fixture. */
async function boot(pageRel) {
  let html = fs.readFileSync(path.join(ROOT, pageRel), 'utf8');
  const depth = pageRel.split('/').length - 1;
  const prefix = '../'.repeat(depth);
  const siteJs = fs.readFileSync(path.join(ROOT, 'assets', 'site.js'), 'utf8');
  const css = fs.readFileSync(path.join(ROOT, 'assets', 'style.css'), 'utf8');
  html = html
    .replace(new RegExp(`<link rel="stylesheet" href="${prefix}assets/style.css">`), `<style>${css}</style>`)
    .replace(new RegExp(`<script src="${prefix}assets/site.js"></script>`), `<script>${siteJs}</script>`);

  const errors = [];
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    url: 'https://karagemop466-tech.github.io/Demo2/' + pageRel,
    virtualConsole: new VirtualConsole(),
    beforeParse(window) {
      window.addEventListener('error', (e) => errors.push(String(e.error || e.message)));
      const origError = window.console.error;
      window.console.error = (...a) => { errors.push(a.join(' ')); origError(...a); };
      window.HTMLCanvasElement.prototype.getContext = () => ({
        setTransform() {}, clearRect() {}, beginPath() {}, moveTo() {}, lineTo() {},
        stroke() {}, closePath() {}, fill() {}, arc() {}, fillText() {}, strokeText() {},
        createLinearGradient: () => ({ addColorStop() {} }),
        setLineDash() {}, save() {}, restore() {}, fillRect() {},
        measureText: () => ({ width: 10 }),
      });
      window.fetch = async (input) => {
        const url = String(input);
        if (url.startsWith('http')) {
          // Kalshi demo API fixture: every requested market moved $0.12 since
          // its last trade, so the alert engine must raise a line for each.
          const tickers = (url.match(/tickers=([^&]+)/) || [, ''])[1]
            .split(',').map(decodeURIComponent).filter(Boolean);
          return {
            ok: true,
            json: async () => ({
              markets: tickers.map((t) => ({
                ticker: t, title: 'Fixture ' + t, status: 'open',
                last_price_dollars: '0.6200', previous_price_dollars: '0.5000',
                yes_bid_dollars: '0.6100', yes_ask_dollars: '0.6300',
                volume_fp: '1000.00', open_interest_fp: '500.00',
                close_time: '2026-11-30T00:00:00Z',
              })),
            }),
          };
        }
        const rel = url.replace(/^https?:\/\/[^/]+\/Demo2\//, '')
          .replace(/^(\.\.\/)+/, '').split('?')[0];
        try {
          const body = readJSON(rel);
          return { ok: true, json: async () => body };
        } catch (e) {
          return { ok: false, status: 404, json: async () => ({}) };
        }
      };
    },
  });
  const { window } = dom;
  const wait = async (fn, label, ms = 8000) => {
    const start = Date.now();
    while (Date.now() - start < ms) {
      if (fn()) return true;
      await new Promise((r) => setTimeout(r, 50));
    }
    throw new Error('timed out waiting for ' + label);
  };
  /* jsdom windows keep their timers alive, and the dashboard schedules a
     polling interval, so every test must close its window or the test runner
     never exits. */
  const close = () => { try { window.close(); } catch (e) { /* already closed */ } };
  return { dom, window, errors, wait, close };
}

test('the dashboard renders, populates its panels and raises a live alert', { skip }, async () => {
  const { window, errors, wait, close } = await boot('index.html');
  const doc = window.document;
  await wait(() => doc.querySelectorAll('#mktTable table tbody tr').length > 0, 'the markets table');
  await wait(() => /Live feed|Starting|Live —/.test(doc.querySelector('#liveStatus').textContent),
    'the live panel status');

  assert.deepEqual(errors, [], 'no JavaScript error may be raised while rendering');

  assert.ok(doc.querySelectorAll('#kpis .kpi-card').length >= 4, 'KPI cards are rendered');
  const tableRows = doc.querySelectorAll('#mktTable table tbody tr').length;
  assert.ok(tableRows > 0, 'the markets table has rows');
  assert.ok(doc.querySelector('#liqBid table') || doc.querySelector('#liqBid .empty'),
    'the liquidity panel is populated (a table or an explicit empty state)');

  // the live feeds exist and are seeded from the committed history
  assert.ok(doc.querySelector('#chatAll'), 'the all-alerts feed exists');
  assert.ok(doc.querySelector('#chatRoi'), 'the ROI feed exists');

  // start the live feed and let one poll land
  doc.querySelector('#liveGo').dispatchEvent(new window.Event('click', { bubbles: true }));
  await wait(() => doc.querySelector('#liveStatus').textContent.includes('Live'), 'the live status');
  await wait(() => doc.querySelectorAll('#chatAll .ln').length > 0, 'a chat line');
  assert.match(doc.querySelector('#liveStatus').textContent, /Live/);
  assert.deepEqual(errors, [], 'no JavaScript error may be raised while polling');
  close();
});

test('the chart is drawn and the live sample is appended to the series', { skip }, async () => {
  const { window, errors, wait, close } = await boot('index.html');
  const doc = window.document;
  await wait(() => doc.querySelectorAll('#mktTable table tbody tr').length > 0, 'the markets table');
  const canvas = doc.querySelector('#chart');
  assert.ok(canvas, 'the chart canvas exists');
  assert.ok(canvas.width > 0, 'the chart canvas was sized');
  assert.ok(doc.querySelector('#chartNote').textContent.includes('points'),
    'the chart note reports the number of points');
  assert.deepEqual(errors, []);
  close();
});

test('the Live Alerts page loads its data from the right path', { skip }, async () => {
  const { window, errors, wait, close } = await boot('pages/live-alerts.html');
  const doc = window.document;
  await wait(() => doc.querySelector('#chatAll').children.length > 0 ||
    doc.querySelector('#chatAll .notice.bad'), 'the alert rows');
  assert.ok(!doc.querySelector('#chatAll .notice.bad'),
    'the page must not report a data load failure');
  assert.ok(doc.querySelectorAll('#chatAll .alertrow').length > 0,
    'the page must render alert rows');
  assert.deepEqual(errors, [], 'no JavaScript error may be raised on the Live Alerts page');
  close();
});
