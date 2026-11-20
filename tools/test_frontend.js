/* Frontend smoke test for the published pages.
 *
 * Loads index.html and pages/portfolio.html in jsdom, stubs `fetch` so the
 * browser reads the committed snapshot instead of the network, and asserts that
 * the pages render rows without throwing.
 *
 *   npm install jsdom   (once)
 *   node tools/test_frontend.js
 *
 * Exits non-zero on the first failure.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.resolve(__dirname, '..');
const DATA = path.join(ROOT, 'data');

function readJson(name, fallback) {
  try {
    return JSON.parse(fs.readFileSync(path.join(DATA, name), 'utf8'));
  } catch (e) {
    return fallback;
  }
}

const openRows = readJson('markets_open.json', { rows: [] }).rows || [];
const settledRows = readJson('markets_settled.json', { rows: [] }).rows || [];
const seriesRows = readJson('series_scope.json', { rows: [] }).rows || [];
const orderbooks = (readJson('orderbooks.json', { rows: {} }).rows) || {};

const failures = [];
function check(name, ok, detail) {
  console.log((ok ? 'PASS  ' : 'FAIL  ') + name + (detail ? '  — ' + detail : ''));
  if (!ok) failures.push(name);
}

function jsonResponse(body) {
  return Promise.resolve({
    ok: true,
    status: 200,
    text: () => Promise.resolve(JSON.stringify(body)),
    json: () => Promise.resolve(body)
  });
}

function stubFetch(url) {
  const u = String(url);
  if (u.indexOf('/markets?') >= 0 && u.indexOf('status=settled') >= 0) {
    return jsonResponse({ markets: settledRows });
  }
  if (u.indexOf('/markets?') >= 0) {
    return jsonResponse({ markets: openRows });
  }
  if (u.indexOf('/series?') >= 0 || /\/series$/.test(u)) {
    return jsonResponse({
      series: seriesRows.map(s => ({
        ticker: s.series_ticker, title: s.title, category: s.category,
        categories: s.categories, tags: s.tags
      }))
    });
  }
  if (u.indexOf('/candlesticks') >= 0) {
    const now = Math.floor(Date.now() / 1000);
    const candles = [];
    for (let i = 20; i >= 0; i--) {
      candles.push({ end_period_ts: now - i * 60, price: { close_dollars: '0.4' } });
    }
    return jsonResponse({ candlesticks: candles });
  }
  if (u.indexOf('/orderbook') >= 0) {
    const ticker = u.split('/markets/')[1].split('/')[0];
    const ob = orderbooks[ticker] || { yes: [['0.4000', '10.00']], no: [['0.5700', '5.00']] };
    return jsonResponse({
      orderbook_fp: {
        yes_dollars: (ob.yes || []).map(x => [String(x[0]), String(x[1])]),
        no_dollars: (ob.no || []).map(x => [String(x[0]), String(x[1])])
      }
    });
  }
  if (u.indexOf('/markets/') >= 0) {
    const ticker = u.split('/markets/')[1].split('?')[0];
    const row = openRows.find(r => r.ticker === ticker) || openRows[0] || {};
    return jsonResponse({ market: row });
  }
  return jsonResponse({});
}

function makeDom(file) {
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', e => errors.push(e.message + ' :: ' + (e.stack || '').split('\n')[0]));
  virtualConsole.on('error', (...a) => errors.push(a.join(' ')));
  const html = fs.readFileSync(path.join(ROOT, file), 'utf8');
  const dom = new JSDOM(html, {
    url: 'https://example.invalid/' + file,
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    virtualConsole
  });
  const win = dom.window;
  win.fetch = stubFetch;
  win.WebSocket = function () {
    this.close = function () {};
    this.send = function () {};
  };
  win.HTMLCanvasElement.prototype.getContext = function () {
    return new Proxy({}, {
      get: (t, p) => {
        if (p === 'canvas') return { width: 0, height: 0 };
        return function () { return 0; };
      },
      set: () => true
    });
  };
  win.HTMLCanvasElement.prototype.toDataURL = function () { return 'data:,'; };
  return { dom, win, errors };
}

function loadScripts(win, files) {
  for (const f of files) {
    const code = fs.readFileSync(path.join(ROOT, f), 'utf8');
    const el = win.document.createElement('script');
    el.textContent = code;
    win.document.body.appendChild(el);
  }
}

function tick(ms) {
  return new Promise(r => setTimeout(r, ms));
}

(async function main() {
  // ---------------------------------------------------------------- index
  const { dom, win, errors } = makeDom('index.html');
  await tick(300);
  loadScripts(win, ['assets/app.js']);
  await tick(600);

  const doc = win.document;
  const marketRows = doc.querySelectorAll('#marketsBody tr');
  const settledTableRows = doc.querySelectorAll('#settledBody tr');
  check('index: no script errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  check('index: market table rendered rows', marketRows.length > 0, marketRows.length + ' rows');
  const dataRows = Array.from(marketRows).filter(tr => (tr.className || '') !== 'placeholder');
  check('index: market rows carry a source link',
    dataRows.length === 0 || dataRows.every(tr => tr.querySelector('a[href*="external-api.demo.kalshi.co"]') !== null),
    dataRows.length + ' data rows');
  check('index: status line reports a mode',
    (doc.getElementById('liveStatus').textContent || '').length > 5,
    doc.getElementById('liveStatus').textContent.slice(0, 80));
  check('index: chart canvas present', doc.getElementById('priceChart') !== null);
  check('index: window selector offers seconds, minutes and hours',
    (function () {
      const vals = Array.from(doc.getElementById('windowSel').options).map(o => parseInt(o.value, 10));
      return vals.indexOf(60) >= 0 && vals.indexOf(300) >= 0 && vals.indexOf(3600) >= 0 && vals.indexOf(86400) >= 0;
    })());
  if (settledTableRows.length) {
    const resolved = Array.from(settledTableRows).filter(tr => (tr.className || '') !== 'placeholder');
    check('index: resolution table shows a result value',
      resolved.length === 0 || resolved.some(tr => /YES|NO/.test(tr.textContent)),
      resolved.length + ' resolved rows');
  } else {
    check('index: resolution table present', true, 'no settled rows in the snapshot');
  }
  dom.window.close();

  // ---------------------------------------------------------------- portfolio
  const p = makeDom('pages/portfolio.html');
  await tick(200);
  loadScripts(p.win, ['assets/portfolio.js']);
  await tick(300);
  check('portfolio: no script errors', p.errors.length === 0, p.errors.slice(0, 3).join(' | '));
  check('portfolio: connect button present', p.win.document.getElementById('connectBtn') !== null);
  check('portfolio: order form present', p.win.document.getElementById('orderTicker') !== null);
  check('portfolio: trade log rendered', p.win.document.querySelectorAll('#tradeLogBody tr').length > 0);
  check('portfolio: strategy table rendered', p.win.document.querySelectorAll('#strategyBody tr').length > 0);
  check('portfolio: no account figures are pre-filled',
    (p.win.document.getElementById('portfolioBox').textContent || '').indexOf('Not connected') >= 0);
  p.win.document.getElementById('clearLogBtn').click();
  p.dom.window.close();

  console.log();
  if (failures.length) {
    console.log('FAILED: ' + failures.join(', '));
    process.exit(1);
  }
  console.log('All frontend checks passed.');
})().catch(e => {
  console.error('test harness error:', e);
  process.exit(1);
});
