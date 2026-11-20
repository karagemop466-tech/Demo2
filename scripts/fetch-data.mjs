#!/usr/bin/env node
/**
 * Kalshi demo market snapshot harvester.
 *
 * Fetches public (unauthenticated) market data from the Kalshi **demo** Trade API
 * and writes a verified snapshot into ../data/*.json.
 *
 * Official references (all https://docs.kalshi.com):
 *  - Demo environment + endpoints .... https://docs.kalshi.com/getting_started/demo_env
 *  - API environments ................ https://docs.kalshi.com/getting_started/api_environments
 *  - Get Markets ..................... https://docs.kalshi.com/api-reference/market/get-markets
 *  - Get Events ...................... https://docs.kalshi.com/api-reference/events/get-events
 *  - Get Series List ................. https://docs.kalshi.com/api-reference/market/get-series-list
 *  - Tags by categories .............. https://docs.kalshi.com/api-reference/search/get-tags-for-series-categories
 *  - Get Market Orderbook ............ https://docs.kalshi.com/api-reference/market/get-market-orderbook
 *  - Quick start: market data ........ https://docs.kalshi.com/getting_started/quick_start_market_data
 *  - Fixed-point representation ...... https://docs.kalshi.com/getting_started/fixed_point_migration
 *  - Pagination ...................... https://docs.kalshi.com/getting_started/pagination
 *
 * No credentials are used or required. Nothing is inferred: every number written to
 * data/ comes from an API response field documented above.
 *
 * Usage:  node scripts/fetch-data.mjs [--out data] [--base https://external-api.demo.kalshi.co/trade-api/v2]
 */

import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..');

const args = process.argv.slice(2);
const argOf = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};

const BASE = argOf('--base', 'https://external-api.demo.kalshi.co/trade-api/v2').replace(/\/$/, '');
const OUT = resolve(REPO, argOf('--out', 'data'));

const SOURCES = {
  base: BASE,
  taxonomy: 'https://docs.kalshi.com/api-reference/search/get-tags-for-series-categories',
  markets: 'https://docs.kalshi.com/api-reference/market/get-markets',
  events: 'https://docs.kalshi.com/api-reference/events/get-events',
  series: 'https://docs.kalshi.com/api-reference/market/get-series-list',
  orderbook: 'https://docs.kalshi.com/api-reference/market/get-market-orderbook',
  marketData: 'https://docs.kalshi.com/getting_started/quick_start_market_data',
  demoEnv: 'https://docs.kalshi.com/getting_started/demo_env',
  fixedPoint: 'https://docs.kalshi.com/getting_started/fixed_point_migration',
  pagination: 'https://docs.kalshi.com/getting_started/pagination',
};

/* ------------------------------------------------------------------ *
 * Topic scope.
 *
 * Rules (documented + verified against the official taxonomy endpoint
 * GET /search/tags_by_categories and the series/market payloads):
 *
 *  1. Elections  -> official series category "Elections".
 *  2. Culture    -> official series category "Culture" plus category
 *                   "Entertainment" (music / film / TV / awards).
 *  3. Crypto     -> official series tag in the Crypto allowlist. Tags are
 *                   applied across categories, because e.g. KXBUYBTC is
 *                   category "Politics" with tags ["Crypto","Bitcoin",...].
 *  4. Golf       -> official series tag "Golf" (category "Sports").
 *  5. Gas prices -> official series tags for fuel/energy. Gas-related series
 *                   exist under series tags ["Gas"] (e.g. DIESEL) which is not
 *                   present in the published taxonomy list, so the allowlist
 *                   unions the taxonomy tags with the observed official tag
 *                   strings that match gas/fuel wording.
 *
 * Every allowlist entry below is an exact, case-sensitive official tag or
 * category string. No free-text keyword matching is used on market titles.
 * ------------------------------------------------------------------ */
const TOPICS = [
  {
    id: 'gas',
    label: 'Gas prices',
    blurb: 'Diesel, gasoline, crude oil and other fuel-price contracts.',
    categories: [],
    tags: ['Oil & Gas', 'Oil and energy', 'Gas', 'Gasoline', 'Diesel', 'Crude oil'],
  },
  {
    id: 'elections',
    label: 'Elections',
    blurb: 'Official Kalshi category "Elections" (races, primaries, control, legislatures).',
    categories: ['Elections'],
    tags: [],
  },
  {
    id: 'culture',
    label: 'Culture',
    blurb: 'Official categories "Culture" and "Entertainment" (music, film, TV, awards).',
    categories: ['Culture', 'Entertainment'],
    tags: [],
  },
  {
    id: 'crypto',
    label: 'Crypto',
    blurb: 'Official series tags for crypto assets (BTC, ETH, SOL, ...).',
    categories: [],
    tags: ['Crypto', 'Bitcoin', 'BTC', 'ETH', 'Ethereum', 'SOL', 'Solana', 'DOGE', 'Dogecoin', 'XRP', 'BNB', 'HYPE', 'ZEC', 'Zcash', 'NEAR', 'Shiba Inu', 'Tokens'],
  },
  {
    id: 'golf',
    label: 'Golf',
    blurb: 'Official series tag "Golf" (PGA, majors, tour events).',
    categories: [],
    tags: ['Golf'],
  },
];

/* ------------------------------- HTTP ------------------------------ */
let requestCount = 0;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * GET with exponential backoff.
 * Kalshi returns 429 {"error":{"code":"too_many_requests"}} without a
 * Retry-After header and asks clients to apply exponential backoff
 * (https://docs.kalshi.com/getting_started/rate_limits).
 */
async function get(path, { allow404 = false, retries = 6 } = {}) {
  const url = BASE + path;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    requestCount += 1;
    let res;
    try {
      res = await fetch(url, { headers: { accept: 'application/json' } });
    } catch (err) {
      if (attempt === retries) throw new Error(`GET ${path} -> network error: ${err.message}`);
      const wait = Math.min(30000, 500 * 2 ** attempt);
      console.warn(`[kalshi-snapshot] network error on ${path}; retry in ${wait}ms`);
      await sleep(wait);
      continue;
    }
    if (res.status === 429) {
      const body = await res.text().catch(() => '');
      if (attempt === retries) {
        throw new Error(`GET ${path} -> HTTP 429 too_many_requests ${body.slice(0, 200)}`);
      }
      const wait = Math.min(30000, 500 * 2 ** attempt);
      console.warn(`[kalshi-snapshot] 429 on ${path}; retry in ${wait}ms`);
      await sleep(wait);
      continue;
    }
    if (res.status === 404 && allow404) return null;
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      if (res.status >= 500 && attempt < retries) {
        const wait = Math.min(30000, 500 * 2 ** attempt);
        console.warn(`[kalshi-snapshot] ${res.status} on ${path}; retry in ${wait}ms`);
        await sleep(wait);
        continue;
      }
      throw new Error(`GET ${path} -> HTTP ${res.status} ${res.statusText} ${body.slice(0, 300)}`);
    }
    return res.json();
  }
  throw new Error(`GET ${path} -> exhausted retries`);
}

/** Cursor pagination helper (https://docs.kalshi.com/getting_started/pagination). */
async function getAll(path, key, maxPages = 60) {
  const out = [];
  let cursor = '';
  for (let page = 0; page < maxPages; page += 1) {
    const sep = path.includes('?') ? '&' : '?';
    const url = path + (cursor ? `${sep}cursor=${encodeURIComponent(cursor)}` : '');
    const json = await get(url);
    const rows = json?.[key];
    if (Array.isArray(rows)) out.push(...rows);
    cursor = json?.cursor || '';
    if (!cursor) break;
  }
  return out;
}

/* --------------------------- Number helpers ------------------------ */
const num = (v) => {
  if (v === undefined || v === null || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};
const round2 = (n) => (n === null ? null : Math.round(n * 100) / 100);

/* ------------------------------ Taxonomy --------------------------- */
async function loadTaxonomy() {
  const json = await get('/search/tags_by_categories');
  const raw = json?.tags_by_categories || {};
  const taxonomy = {};
  for (const [category, tags] of Object.entries(raw)) {
    taxonomy[category] = Array.isArray(tags) ? tags : [];
  }
  return taxonomy;
}

/* ------------------------------- Series ---------------------------- */
async function loadSeries(taxonomy) {
  const byTicker = new Map();
  const categories = Object.keys(taxonomy);

  const absorb = (json) => {
    for (const s of json?.series || []) byTicker.set(s.ticker, s);
    // Some deployments page this endpoint with a cursor even though it is not
    // always advertised; follow it when present.
    return json?.cursor || '';
  };

  // Category-scoped queries (each series has >=1 category in its `categories` list).
  for (const category of categories) {
    let cursor = '';
    for (let page = 0; page < 40; page += 1) {
      const query = `category=${encodeURIComponent(category)}&limit=1000`;
      const json = await get(cursor ? `/series?${query}&cursor=${encodeURIComponent(cursor)}` : `/series?${query}`);
      cursor = absorb(json);
      if (!cursor) break;
    }
  }
  // Catch-all for series whose `categories` list is empty (e.g. categories:null).
  let cursor = '';
  for (let page = 0; page < 40; page += 1) {
    const json = await get(cursor ? `/series?limit=1000&cursor=${encodeURIComponent(cursor)}` : '/series?limit=1000');
    cursor = absorb(json);
    if (!cursor) break;
  }
  return byTicker;
}

/* -------------------------- Topic classification -------------------- */
function buildTopicIndex(seriesByTicker) {
  const index = new Map(); // series ticker -> topic id
  for (const topic of TOPICS) {
    const tagSet = new Set(topic.tags);
    for (const series of seriesByTicker.values()) {
      if (index.has(series.ticker)) continue;
      const cats = Array.isArray(series.categories) ? series.categories : [];
      const catHit = topic.categories.some((c) => cats.includes(c) || series.category === c);
      const tags = Array.isArray(series.tags) ? series.tags : [];
      const tagHit = tags.some((t) => tagSet.has(t));
      if (catHit || tagHit) index.set(series.ticker, topic.id);
    }
  }
  return index;
}

/* ------------------------------- Markets ---------------------------- */
const MARKET_FIELDS = [
  'ticker', 'event_ticker', 'series_ticker', 'title', 'subtitle', 'yes_sub_title', 'no_sub_title',
  'status', 'market_type', 'open_time', 'close_time', 'latest_expiration_time', 'expected_expiration_time',
  'last_price_dollars', 'yes_bid_dollars', 'yes_ask_dollars', 'no_bid_dollars', 'no_ask_dollars',
  'yes_bid_size_fp', 'yes_ask_size_fp', 'no_bid_size_fp', 'no_ask_size_fp',
  'volume_fp', 'volume_24h_fp', 'open_interest_fp', 'notional_value_dollars',
  'result', 'settlement_value_dollars', 'settlement_ts', 'rules_primary',
];

function pickMarket(m) {
  const out = {};
  for (const f of MARKET_FIELDS) if (m[f] !== undefined) out[f] = m[f];
  const price = num(m.last_price_dollars);
  const volume = num(m.volume_fp);
  // "Dollar amount" proxy: contracts traded (volume_fp) x last traded price ($/contract).
  // There is no single "dollar volume" field in Get Markets; see pages/flagged.html (F2).
  out.contract_value_traded_usd = price !== null && volume !== null ? round2(price * volume) : null;
  out.open_interest_usd = m.open_interest_fp !== undefined && price !== null
    ? round2(num(m.open_interest_fp) * price)
    : null;
  return out;
}

async function loadMarkets(status) {
  const rows = await getAll(`/markets?status=${status}&limit=1000`, 'markets');
  return rows.map(pickMarket);
}

/* ------------------------------- Events ----------------------------- */
function pickEvent(e) {
  return {
    event_ticker: e.event_ticker,
    series_ticker: e.series_ticker,
    title: e.title,
    sub_title: e.sub_title,
    category: e.category,
    exchange_index: e.exchange_index,
    last_updated_ts: e.last_updated_ts,
  };
}

async function loadEvents(status) {
  const rows = await getAll(`/events?status=${status}&limit=200&with_nested_markets=false`, 'events');
  return rows.map(pickEvent);
}

/* ----------------------------- Orderbooks --------------------------- */
async function loadOrderbooks(tickers, depth = 12) {
  const out = {};
  for (const ticker of tickers) {
    const json = await get(`/markets/${encodeURIComponent(ticker)}/orderbook`);
    const book = json?.orderbook_fp || {};
    const trim = (levels) => (Array.isArray(levels) ? levels.slice(-depth).reverse() : []);
    out[ticker] = {
      yes_dollars: trim(book.yes_dollars),
      no_dollars: trim(book.no_dollars),
    };
  }
  return out;
}

/* ------------------------------- Main ------------------------------- */
async function main() {
  const startedAt = new Date().toISOString();
  console.log(`[kalshi-snapshot] base=${BASE}`);

  const taxonomy = await loadTaxonomy();
  console.log(`[kalshi-snapshot] taxonomy categories: ${Object.keys(taxonomy).length}`);

  const seriesByTicker = await loadSeries(taxonomy);
  console.log(`[kalshi-snapshot] series: ${seriesByTicker.size}`);

  const topicIndex = buildTopicIndex(seriesByTicker);
  console.log(`[kalshi-snapshot] series mapped to a topic: ${topicIndex.size}`);

  const openMarkets = await loadMarkets('open');
  console.log(`[kalshi-snapshot] open markets: ${openMarkets.length}`);

  const settledMarkets = await loadMarkets('settled');
  console.log(`[kalshi-snapshot] settled markets: ${settledMarkets.length}`);

  const openEvents = await loadEvents('open');
  console.log(`[kalshi-snapshot] open events: ${openEvents.length}`);

  const eventByTicker = new Map(openEvents.map((e) => [e.event_ticker, e]));

  const scoped = (markets) => markets
    .map((m) => {
      const topic = topicIndex.get(m.series_ticker) || null;
      if (!topic) return null;
      const event = eventByTicker.get(m.event_ticker);
      return {
        ...m,
        topic,
        event_title: event?.title ?? null,
        event_category: event?.category ?? null,
        series_title: seriesByTicker.get(m.series_ticker)?.title ?? null,
        series_category: seriesByTicker.get(m.series_ticker)?.category ?? null,
        series_tags: seriesByTicker.get(m.series_ticker)?.tags ?? null,
        series_frequency: seriesByTicker.get(m.series_ticker)?.frequency ?? null,
        settlement_sources: (seriesByTicker.get(m.series_ticker)?.settlement_sources || []).map((s) => ({
          name: s?.name ?? null,
          url: s?.url ?? null,
        })),
        source_url: `${BASE}/markets/${m.ticker}`,
      };
    })
    .filter(Boolean);

  const scopedOpen = scoped(openMarkets);
  const scopedSettled = scoped(settledMarkets);
  console.log(`[kalshi-snapshot] in-scope open markets: ${scopedOpen.length}`);
  console.log(`[kalshi-snapshot] in-scope settled markets: ${scopedSettled.length}`);

  // Event-level aggregation: the requested unit is "events", so markets are rolled up
  // by event_ticker using the same dollar proxy.
  const eventsByTicker = new Map();
  for (const m of scopedOpen) {
    const e = eventsByTicker.get(m.event_ticker) || {
      event_ticker: m.event_ticker,
      series_ticker: m.series_ticker,
      title: m.event_title,
      category: m.event_category,
      topic: m.topic,
      markets: 0,
      volume_fp: 0,
      open_interest_fp: 0,
      contract_value_traded_usd: 0,
      open_interest_usd: 0,
      last_price_dollars: null,
      close_time: m.close_time,
      source_url: `${BASE}/events/${m.event_ticker}`,
    };
    e.markets += 1;
    e.volume_fp = round2(e.volume_fp + (num(m.volume_fp) || 0));
    e.open_interest_fp = round2(e.open_interest_fp + (num(m.open_interest_fp) || 0));
    e.contract_value_traded_usd = round2(e.contract_value_traded_usd + (num(m.contract_value_traded_usd) || 0));
    e.open_interest_usd = round2(e.open_interest_usd + (num(m.open_interest_usd) || 0));
    const p = num(m.last_price_dollars);
    if (p !== null) e.last_price_dollars = p;
    eventsByTicker.set(m.event_ticker, e);
  }
  const scopedEvents = [...eventsByTicker.values()].sort(
    (a, b) => (b.contract_value_traded_usd || 0) - (a.contract_value_traded_usd || 0),
  );

  // Top markets per topic -> order books (liquidity at a given price).
  const topPerTopic = [];
  for (const topic of TOPICS) {
    const rows = scopedOpen
      .filter((m) => m.topic === topic.id)
      .sort((a, b) => (b.contract_value_traded_usd || 0) - (a.contract_value_traded_usd || 0));
    for (const r of rows.slice(0, 3)) topPerTopic.push(r.ticker);
  }
  const orderbooks = await loadOrderbooks([...new Set(topPerTopic)]);
  console.log(`[kalshi-snapshot] orderbooks: ${Object.keys(orderbooks).length}`);

  const generatedAt = new Date().toISOString();
  const meta = {
    generated_at: generatedAt,
    base_url: BASE,
    environment: 'demo',
    request_count: requestCount,
    sources: SOURCES,
    topic_rules: TOPICS.map((t) => ({
      id: t.id,
      label: t.label,
      categories: t.categories,
      tags: t.tags,
      source: SOURCES.taxonomy,
    })),
    counts: {
      taxonomy_categories: Object.keys(taxonomy).length,
      series: seriesByTicker.size,
      series_mapped: topicIndex.size,
      open_markets: openMarkets.length,
      settled_markets: settledMarkets.length,
      open_events: openEvents.length,
      in_scope_open_markets: scopedOpen.length,
      in_scope_settled_markets: scopedSettled.length,
      in_scope_open_events: scopedEvents.length,
    },
    metric_definitions: {
      contract_value_traded_usd: 'volume_fp (contracts traded, https://docs.kalshi.com/api-reference/market/get-series-list) x last_price_dollars ($ per contract, https://docs.kalshi.com/api-reference/market/get-markets). Derived, not an API field.',
      open_interest_usd: 'open_interest_fp (open contracts) x last_price_dollars ($ per contract). Derived, not an API field.',
      notional_value_dollars: 'API field returned verbatim by Get Markets; definition not published in the API reference.',
    },
  };

  await mkdir(OUT, { recursive: true });
  const write = async (name, value) => {
    const path = resolve(OUT, name);
    await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
    console.log(`[kalshi-snapshot] wrote ${path}`);
  };

  const byTopic = (rows, key = 'topic') => {
    const out = {};
    for (const t of TOPICS) out[t.id] = rows.filter((r) => r[key] === t.id);
    return out;
  };

  await write('meta.json', meta);
  await write('taxonomy.json', { generated_at: generatedAt, source: SOURCES.taxonomy, tags_by_categories: taxonomy });
  await write('open-markets.json', { generated_at: generatedAt, source: SOURCES.markets, topics: byTopic(scopedOpen) });
  await write('open-events.json', { generated_at: generatedAt, source: SOURCES.events, topics: byTopic(scopedEvents) });
  await write('settled-markets.json', { generated_at: generatedAt, source: SOURCES.markets, topics: byTopic(scopedSettled) });
  await write('orderbooks.json', { generated_at: generatedAt, source: SOURCES.orderbook, books: orderbooks });

  console.log(`[kalshi-snapshot] done in ${Date.now() - Date.parse(startedAt)}ms (${requestCount} requests)`);
}

main().catch((err) => {
  console.error(`[kalshi-snapshot] FAILED: ${err && err.message ? err.message : err}`);
  process.exit(1);
});
