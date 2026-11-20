// Renders the static site with jsdom against a locally served copy of the repo and
// reports, per page, whether the data panels filled in or showed an error.
//
// Why: the pages fetch data/*.json and call canvas APIs. A 404 or a JS exception leaves
// the page looking fine in a text diff and broken in a browser. This harness catches
// that, offline, before anything is pushed.
//
// Usage: node scripts/render_check.mjs
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { JSDOM, VirtualConsole } from 'jsdom';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png' };

const server = http.createServer((req, res) => {
  const url = decodeURIComponent((req.url || '/').split('?')[0]);
  let file = path.join(ROOT, url === '/' ? 'index.html' : url);
  if (file.endsWith('/')) file = path.join(file, 'index.html');
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404); res.end('not found'); return;
  }
  res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream' });
  res.end(fs.readFileSync(file));
});

const PAGES = [
  ['index.html', ['#landingCards', '#topicTable', '#pipelineKpis']],
  ['dashboard.html', ['#kpis', '#topicStrip', '#mktTable']],
  ['pages/gas.html', ['#kpis', '#liveTable']],
  ['pages/elections.html', ['#kpis', '#liveTable']],
  ['pages/crypto.html', ['#kpis', '#liveTable']],
  ['pages/golf.html', ['#kpis', '#liveTable']],
  ['pages/culture.html', ['#kpis', '#catNote']],
  ['pages/resolutions.html', ['#kpis', '#byTopic', '#resTable']],
  ['pages/causes.html', ['#srcTable', '#newsTable']],
  ['pages/verification.html', ['#health', '#apiLog']],
  ['pages/analysis.html', ['#kpis', '#tradeTable']],
  ['pages/portfolio.html', ['#kpis']],
  ['pages/executive-summary.html', []],
];

function stubCanvas(dom) {
  // jsdom has no 2D context; give every canvas a no-op one so chart code runs.
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

const results = [];
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;

for (const [page, selectors] of PAGES) {
  const errors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', (e) => { if (!/Not implemented/.test(e.message)) errors.push(e.message); });
  vc.on('error', (...a) => errors.push(a.join(' ')));
  let dom;
  try {
    dom = await JSDOM.fromURL(`${base}/${page}`, {
      runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true,
      virtualConsole: vc,
      beforeParse(win) {
        win.fetch = async (u, o) => fetch(new URL(u, `${base}/${page}`), o);
        stubCanvas(win);
      },
    });
  } catch (e) {
    results.push({ page, ok: false, note: `load failed: ${e.message}` });
    continue;
  }
  await new Promise((r) => setTimeout(r, 1800));
  const doc = dom.window.document;
  const filled = selectors.map((sel) => {
    const el = doc.querySelector(sel);
    if (!el) return `${sel}:MISSING`;
    const txt = (el.textContent || '').trim();
    const tableRows = el.querySelectorAll('tbody tr').length;
    const bad = /could not be loaded|could not load|HTTP 404|missing \(|cann?ot load/i.test(txt);
    if (bad) return `${sel}:ERROR`;
    if (!txt && !tableRows) return `${sel}:EMPTY`;
    return `${sel}:${tableRows ? tableRows + 'rows' : 'ok'}`;
  });
  const errs = filled.filter((f) => /ERROR|MISSING|EMPTY/.test(f));
  results.push({ page, ok: errs.length === 0 && errors.length === 0,
    note: errs.join(' ') + (errors.length ? ` js:${errors.slice(0, 2).join(' | ')}` : ''),
    detail: filled.join(' ') });
  dom.window.close();
}

server.close();
let failed = 0;
for (const r of results) {
  if (!r.ok) failed++;
  console.log(`${r.ok ? 'ok  ' : 'FAIL'} ${r.page.padEnd(30)} ${r.detail || r.note}`);
  if (!r.ok) console.log(`     → ${r.note}`);
}
console.log(`\n${results.length - failed}/${results.length} pages rendered with data, 0 errors`);
process.exit(failed ? 1 : 0);
