// Smoke test: load each dashboard page in jsdom, execute app.js against the live
// backend, and report any runtime errors. Canvas is stubbed (jsdom lacks 2D context).
import { JSDOM, VirtualConsole } from 'jsdom';

const BASE = 'http://127.0.0.1:8080';
const pages = [
  'index.html', 'events.html', 'gas.html', 'elections.html', 'culture.html',
  'crypto.html', 'golf.html', 'market.html?ticker=KXBTCD-25AUG0517-T114999.99&series=KXBTCD',
  'portfolio.html', 'trades.html', 'strategies.html', 'suggestions.html', 'flagged.html',
];

const errors = [];
for (const page of pages) {
  const url = BASE + '/' + page;
  const vc = new VirtualConsole();
  vc.on('jsdomError', (e) => errors.push(`[${page}] jsdomError: ${e.message}`));
  vc.on('error', (...a) => errors.push(`[${page}] console.error: ${a.join(' ')}`));

  const dom = await JSDOM.fromURL(url, {
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      // resolve relative fetch URLs against the page base
      window.fetch = (input, init) => {
        const u = typeof input === 'string' && input.startsWith('/') ? BASE + input : input;
        return globalThis.fetch(u, init);
      };
      // stub canvas 2d context (jsdom does not implement it)
      window.HTMLCanvasElement.prototype.getContext = function () {
        return new Proxy({}, {
          get: (_t, prop) => {
            if (prop === 'canvas') return this;
            if (prop === 'measureText') return () => ({ width: 10 });
            if (prop === 'getImageData') return () => ({ data: [] });
            return () => {};
          },
        });
      };
    },
  });
  // wait for async init + fetches
  await new Promise((r) => setTimeout(r, 2500));
  const w = dom.window;
  const hasKalshi = !!(w.__kalshi);
  const statusText = w.document.getElementById('conn-status')?.textContent || '(no status)';
  const tableText = (w.document.querySelector('main')?.textContent || '').slice(0, 60).replace(/\s+/g, ' ');
  console.log(`${page.padEnd(55)} __kalshi=${hasKalshi} status="${statusText}" body="${tableText}..."`);
  dom.window.close();
}

console.log('\n--- ERRORS (' + errors.length + ') ---');
errors.forEach((e) => console.log(e));
process.exit(errors.length ? 1 : 0);
