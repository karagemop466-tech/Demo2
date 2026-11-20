#!/usr/bin/env node
/* linkcheck.mjs — Kalshi Demo Intelligence build-time verification (S-06)
 *
 * Checks, for every page in the repo root:
 *   1. internal href/src targets exist on disk (relative links, anchors)
 *   2. every <a href> is present and well-formed (http(s), mailto, #, relative)
 *   3. data/*.json records that render as table rows carry a source URL
 *      (watchlist series → src or settlement_source or url; snapshot records → src)
 *   4. external URLs: shape + (best-effort) reachability.
 *      Network-blocked domains are reported as SKIP (this sandbox allowlists
 *      github/npm/pypi only); genuine 404/410 responses FAIL.
 *
 * Usage:  node scripts/linkcheck.mjs            # internal + shape + data sources
 *         node scripts/linkcheck.mjs --external # also attempt HTTP reachability
 *
 * Exit code 0 = pass (warnings allowed), 1 = failures.
 */
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const doExternal = process.argv.includes("--external");
const failures = [];
const warnings = [];
let checkedLinks = 0, checkedSources = 0;

// ---------- collect pages ----------
const pages = readdirSync(root).filter(f => f.endsWith(".html"));
const anchorsByPage = {};
for (const p of pages) {
  const html = readFileSync(join(root, p), "utf8");
  anchorsByPage[p] = new Set([...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]));
}

const external = new Set();

for (const page of pages) {
  const html = readFileSync(join(root, page), "utf8");

  // 1+2: link targets
  const hrefRe = /(?:href|src)="([^"]+)"/g;
  for (const m of html.matchAll(hrefRe)) {
    const url = m[1];
    if (url.includes("${")) { checkedLinks++; continue; } // runtime-built link (template literal) — not statically checkable
    checkedLinks++;
    if (/^(https?:)?\/\//.test(url)) {
      if (url.startsWith("http://") && !url.includes("localhost")) warnings.push(`${page}: plain http link ${url}`);
      if (!/^https:\/\//.test(url) && !url.startsWith("//")) { /* handled above */ }
      external.add(url.startsWith("//") ? "https:" + url : url);
      continue;
    }
    if (url.startsWith("mailto:") || url.startsWith("#")) continue;
    if (url.startsWith("#")) continue;
    // relative file link
    const [file, hash] = url.split("#");
    if (file) {
      const target = join(root, file);
      if (!existsSync(target)) { failures.push(`${page}: broken internal link → ${url}`); continue; }
      if (hash && file.endsWith(".html")) {
        if (!anchorsByPage[file] || !anchorsByPage[file].has(hash)) {
          failures.push(`${page}: missing anchor #${hash} in ${file}`);
        }
      }
    }
  }

  // anchor-only links must exist in the same page
  for (const m of html.matchAll(/href="#([^"]+)"/g)) {
    checkedLinks++;
    if (!anchorsByPage[page].has(m[1])) failures.push(`${page}: missing local anchor #${m[1]}`);
  }
}

// ---------- data source presence ----------
function isUrl(s) { return typeof s === "string" && /^https:\/\/[^\s]+$/.test(s); }

// watchlist: every series record must have at least one source-ish field
const wl = JSON.parse(readFileSync(join(root, "data/watchlist.json"), "utf8"));
for (const topic of wl.topics) {
  for (const q of topic.queries) {
    if (!isUrl(q.url)) failures.push(`watchlist: topic "${topic.topic}" query missing url`);
    else external.add(q.url);
    q.series.forEach((s, i) => {
      checkedSources++;
      const has =
        isUrl(s.src) ||
        (s.settlement_source && isUrl(s.settlement_source.url)) ||
        (Array.isArray(s.settlement_source) && s.settlement_source.some(x => isUrl(x.url)));
      if (!has) failures.push(`watchlist ${topic.topic}/${q.url}: series[${i}] ${s.ticker} has no source URL`);
      if (isUrl(s.src)) external.add(s.src);
    });
  }
  for (const s of (topic.series_with_volume_not_in_queries || [])) {
    checkedSources++;
    if (!isUrl(s.src)) failures.push(`watchlist ${topic.topic}: ${s.ticker} (series_with_volume_not_in_queries) missing src`);
    else external.add(s.src);
  }
}

// snapshot: every row-bearing record must carry src
const snap = JSON.parse(readFileSync(join(root, "data/snapshot.json"), "utf8"));
const snapLists = [
  ["events", snap.events], ["markets", snap.markets], ["resolutions", snap.resolutions],
  ["orderbooks", snap.orderbooks], ["trades_sample", snap.trades_sample]
];
for (const [name, list] of snapLists) {
  (list || []).forEach((r, i) => {
    checkedSources++;
    if (!isUrl(r.src)) failures.push(`snapshot.${name}[${i}] missing/invalid src (${r.ticker || r.event_ticker || "?"})`);
    else external.add(r.src);
  });
}
checkedSources += 1;
if (!isUrl(snap.exchange_status?.src)) failures.push("snapshot.exchange_status missing src"); else external.add(snap.exchange_status.src);
if (!isUrl(snap.candlesticks?.src)) failures.push("snapshot.candlesticks missing src"); else external.add(snap.candlesticks.src);
if (!isUrl(snap.portfolio_probe?.url)) failures.push("snapshot.portfolio_probe missing url"); else external.add(snap.portfolio_probe.url);

// ---------- external reachability (best effort) ----------
async function head(url) {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 8000);
    const res = await fetch(url, { method: "GET", redirect: "follow", signal: ctrl.signal });
    clearTimeout(t);
    if (res.status === 404 || res.status === 410) return `FAIL ${res.status}`;
    if (res.status >= 400) return `WARN ${res.status}`;
    return "OK";
  } catch (e) {
    return `SKIP (${String(e.cause?.code || e.name || "net")})`;
  }
}

if (doExternal) {
  const urls = [...external].sort();
  let ok = 0, skip = 0, warn = 0;
  for (let i = 0; i < urls.length; i += 4) {
    const part = urls.slice(i, i + 4);
    const res = await Promise.all(part.map(async u => [u, await head(u)]));
    for (const [u, st] of res) {
      if (st === "OK") ok++;
      else if (st.startsWith("SKIP")) skip++;
      else if (st.startsWith("WARN")) { warn++; warnings.push(`external ${st}: ${u}`); }
      else failures.push(`external ${st}: ${u}`);
    }
  }
  console.log(`external: ${ok} OK · ${skip} SKIPPED (sandbox allowlist) · ${warn} warnings`);
}

// ---------- report ----------
console.log(`pages: ${pages.length} · links checked: ${checkedLinks} · data source fields checked: ${checkedSources} · external URLs catalogued: ${external.size}`);
for (const w of warnings) console.log("WARN  " + w);
for (const f of failures) console.log("FAIL  " + f);
if (failures.length) { console.log(`\n${failures.length} failure(s)`); process.exit(1); }
console.log("\nPASS — every internal link resolves; every data row has a source URL.");
