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
 *  - Rate limits ..................... https://docs.kalshi.com/getting_started/rate_limits
 *  - Order direction ................. https://docs.kalshi.com/getting_started/order_direction
 *
 * No credentials are used or required. Nothing is inferred: every number written to
 * data/ comes from an API response field documented above.
 *
 * Usage:  node scripts/fetch-data.mjs [--out data] [--base <url>] [--series-per-topic 30]
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
const SERIES_PER_TOPIC = parseInt(argOf('--series-per-topic', '12'), 10);
// Hard budget so a harvest always finishes inside the CI window instead of
// grinding on rate limits. When the budget is hit, collection stops cleanly and
// the partial snapshot is still written and flagged.
const MAX_REQUESTS = parseInt(argOf('--max-requests', '900'), 10);
// Rows kept per topic in each published snapshot file. The collector sees far
// more markets than a reader can use, and a multi-megabyte JSON file would
// bloat both the repository and the Pages artifact. The cap is applied after
// ranking, so the rows that are kept are the highest-value ones, and the cap
// is recorded in data/meta.json.
const MAX_OPEN_MARKETS_PER_TOPIC = parseInt(argOf('--open-markets-per-topic', '250'), 10);
const MAX_SETTLED_PER_TOPIC = parseInt(argOf('--settled-per-topic', '150'), 10);
const MAX_EVENTS_PER_TOPIC = parseInt(argOf('--events-per-topic', '150'), 10);

const DOCS = {
  base: 'https://docs.kalshi.com/getting_started/demo_env',
  apiEnvironments: 'https://docs.kalshi.com/getting_started/api_environments',
  markets: 'https://docs.kalshi.com/api-reference/market/get-markets',
  events: 'https://docs.kalshi.com/api-reference/events/get-events',
  series: 'https://docs.kalshi.com/api-reference/market/get-series-list',
  taxonomy: 'https://docs.kalshi.com/api-reference/search/get-tags-for-series-categories',
  orderbook: 'https://docs.kalshi.com/api-reference/market/get-market-orderbook',
  marketData: 'https://docs.kalshi.com/getting_started/quick_start_market_data',
  fixedPoint: 'https://docs.kalshi.com/getting_started/fixed_point_migration',
  pagination: 'https://docs.kalshi.com/getting_started/pagination',
  rateLimits: 'https://docs.kalshi.com/getting_started/rate_limits',
  orderDirection: 'https://docs.kalshi.com/getting_started/order_direction',
  settlement: 'https://docs.kalshi.com/getting_started/market_settlement',
};

/* ------------------------------------------------------------------ *
 * Topic scope.
 *
 * Rules are built from the OFFICIAL Kalshi taxonomy, not from market-title
 * keywords:
 *
 *  GET /search/tags_by_categories  -> category -> official tag list
 *  GET /series                      -> series.category / series.categories / series.tags
 *  GET /events                      -> event.category (per event)
 *
 * A series is in scope for a topic when its official `category` / `categories`
 * matches the topic's category allowlist, or one of its official `tags` matches
 * the topic's tag allowlist. Markets inherit the topic of their series.
 *
 * The tag allowlists below are the official tag strings published by
 * GET /search/tags_by_categories, plus the officially observed series tag
 * "Gas" (used by the DIESEL / DIESELM fuel-price series, which is not listed
 * in the published taxonomy). Every allowlist entry is an exact,
 * case-sensitive official string.
 * ------------------------------------------------------------------ */
const TOPICS = [
  {
    id: 'gas',
    label: 'Gas prices',
    blurb: 'Diesel, gasoline and crude-oil / fuel-energy price contracts.',
    categories: [],
    tags: ['Oil & Gas', 'Oil and energy', 'Gas', 'Gasoline', 'Diesel', 'Crude oil'],
  },
  {
    id: 'elections',
    label: 'Elections',
    blurb: 'Official Kalshi category "Elections".',
    categories: ['Elections'],
    tags: [],
  },
  {
    id: 'culture',
    label: 'Culture',
    blurb: 'Official Kalshi categories "Culture" and "Entertainment" (film, music, TV, awards).',
    categories: ['Culture', 'Entertainment'],
    tags: [],
  },
  {
    id: 'crypto',
    label: 'Crypto',
    blurb: 'Official Kalshi crypto tags (BTC, ETH, SOL, ...), applied across categories.',
    categories: [],
    tags: ['Crypto', 'Bitcoin', 'BTC', 'ETH', 'Ethereum', 'SOL', 'Solana', 'DOGE', 'Dogecoin', 'XRP', 'BNB', 'HYPE', 'ZEC', 'Zcash', 'NEAR', 'Shiba Inu', 'Tokens'],
  },
  {
    id: 'golf',
    label: 'Golf',
    blurb: 'Official Kalshi tag "Golf" (PGA, majors, tour events).',
    categories: [],
    tags: ['Golf'],
  },
];

/* ------------------------------- HTTP ------------------------------ */
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const requestLog = [];
let requestCount = 0;
let budgetExhausted = false;

/**
 * GET with exponential backoff.
 * Kalshi returns 429 {"error":{"code":"too_many_requests"}} with no Retry-After
 * header and asks clients to apply exponential backoff
 * (https://docs.kalshi.com/getting_started/rate_limits).
 */
async function get(path, { allow404 = false, retries = 6, note = '', soft = false } = {}) {
  if (budgetExhausted) return null;
  const url = BASE + path;
  // Be gentle: the demo API applies separate unauthenticated limits
  // (https://docs.kalshi.com/getting_started/rate_limits).
  await sleep(40);
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    requestCount += 1;
    if (requestCount > MAX_REQUESTS) {
      budgetExhausted = true;
      requestLog.push({ url, status: 'budget_exhausted', note });
      console.warn(`[kalshi-snapshot] request budget (${MAX_REQUESTS}) reached; stopping collection`);
      return null;
    }
    const started = Date.now();
    let res;
    try {
      res = await fetch(url, { headers: { accept: 'application/json' } });
    } catch (err) {
      if (attempt === retries) {
        requestLog.push({ url, status: 'network_error', note, error: String(err && err.message) });
        const msg = `GET ${path} -> network error: ${err.message}`;
        if (soft) { console.warn(`[kalshi-snapshot] soft-fail: ${msg}`); return null; }
        throw new Error(msg);
      }
      const wait = Math.min(30000, 700 * 2 ** attempt);
      console.warn(`[kalshi-snapshot] network error on ${path}; retry in ${wait}ms`);
      await sleep(wait);
      continue;
    }
    if (res.status === 429) {
      if (attempt === retries) {
        requestLog.push({ url, status: 429, note });
        const msg = `GET ${path} -> HTTP 429 too_many_requests`;
        if (soft) { console.warn(`[kalshi-snapshot] soft-fail: ${msg}`); return null; }
        throw new Error(msg);
      }
      const wait = Math.min(30000, 700 * 2 ** attempt);
      console.warn(`[kalshi-snapshot] 429 on ${path}; retry in ${wait}ms`);
      await sleep(wait);
      continue;
    }
    if (res.status === 404 && allow404) {
      requestLog.push({ url, status: 404, note });
      return null;
    }
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      if (res.status >= 500 && attempt < retries) {
        const wait = Math.min(30000, 700 * 2 ** attempt);
        console.warn(`[kalshi-snapshot] ${res.status} on ${path}; retry in ${wait}ms`);
        await sleep(wait);
        continue;
      }
      requestLog.push({ url, status: res.status, note });
      const msg = `GET ${path} -> HTTP ${res.status} ${res.statusText} ${body.slice(0, 300)}`;
      if (soft) { console.warn(`[kalshi-snapshot] soft-fail: ${msg}`); return null; }
      throw new Error(msg);
    }
    const json = await res.json();
    requestLog.push({
      url,
      status: 200,
      note,
      ms: Date.now() - started,
      records: Array.isArray(json?.markets) ? json.markets.length
        : Array.isArray(json?.events) ? json.events.length
          : Array.isArray(json?.series) ? json.series.length : null,
    });
    return json;
  }
  throw new Error(`GET ${path} -> exhausted retries`);
}

/* --------------------------- Number helpers ------------------------ */
const num = (v) => {
  if (v === undefined || v === null || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};
const round2 = (n) => (n === null || n === undefined ? null : Math.round(n * 100) / 100);

/* ------------------------------ Taxonomy --------------------------- */
async function loadTaxonomy() {
  const json = await get('/search/tags_by_categories', { note: 'official series category -> tag taxonomy' });
  const raw = json?.tags_by_categories || {};
  const taxonomy = {};
  for (const [category, tags] of Object.entries(raw)) taxonomy[category] = Array.isArray(tags) ? tags : [];
  return taxonomy;
}

/* ------------------------------- Series ---------------------------- */
async function loadSeries(taxonomy) {
  const byTicker = new Map();
  const absorb = (json) => {
    for (const s of json?.series || []) byTicker.set(s.ticker, s);
    return json?.cursor || '';
  };

  // 0) Full catalogue pagination. GET /series without a category filter returns
  //    every series with its official category/categories/tags, so the whole
  //    in-scope catalogue can be classified locally with a handful of requests.
  {
    let cursor = '';
    for (let page = 0; page < 60; page += 1) {
      const q = 'include_volume=true&limit=1000';
      const json = await get(cursor ? `/series?${q}&cursor=${encodeURIComponent(cursor)}` : `/series?${q}`,
        { note: 'series catalogue', soft: true });
      if (!json) break;
      cursor = absorb(json);
      if (!cursor) break;
    }
  }

  // 1) Per-category queries (every series carries >=1 discovery category).
  //    Soft-fail: a taxonomy category that is not itself a series category
  //    answers 400 and must not abort the harvest.
  for (const category of Object.keys(taxonomy)) {
    const q = `category=${encodeURIComponent(category)}&include_volume=true&limit=1000`;
    let cursor = '';
    for (let page = 0; page < 20; page += 1) {
      const json = await get(cursor ? `/series?${q}&cursor=${encodeURIComponent(cursor)}` : `/series?${q}`,
        { note: `series list for category=${category}`, soft: true });
      if (!json) break;
      cursor = absorb(json);
      if (!cursor) break;
    }
  }

  // 2) Per-tag queries (official tags that live under a different primary category,
  //    e.g. "Golf" under Sports, "Crypto" tags under Politics).
  for (const topic of TOPICS) {
    for (const tag of topic.tags) {
      const q = `tags=${encodeURIComponent(tag)}&include_volume=true&limit=1000`;
      let cursor = '';
      for (let page = 0; page < 4; page += 1) {
        const json = await get(cursor ? `/series?${q}&cursor=${encodeURIComponent(cursor)}` : `/series?${q}`,
          { note: `series list for tag=${tag}`, soft: true });
        if (!json) break;
        cursor = absorb(json);
        if (!cursor) break;
      }
    }
  }
  return byTicker;
}

/* -------------------------- Topic classification -------------------- */
function topicOfSeries(series) {
  if (!series) return null;
  const cats = Array.isArray(series.categories) ? series.categories : [];
  const tags = Array.isArray(series.tags) ? series.tags : [];
  for (const topic of TOPICS) {
    const catHit = topic.categories.some((c) => cats.includes(c) || series.category === c);
    const tagHit = tags.some((t) => topic.tags.includes(t));
    if (catHit || tagHit) return topic.id;
  }
  return null;
}

function pickInScopeSeries(seriesByTicker) {
  const byTopic = {};
  for (const topic of TOPICS) byTopic[topic.id] = [];
  for (const series of seriesByTicker.values()) {
    const topic = topicOfSeries(series);
    if (!topic) continue;
    byTopic[topic].push(series);
  }
  // Rank by the official series volume (contracts traded across all events of the
  // series) so the highest-activity series are collected first.
  for (const topic of TOPICS) {
    byTopic[topic.id].sort((a, b) => (num(b.volume_fp) || 0) - (num(a.volume_fp) || 0));
    byTopic[topic.id] = byTopic[topic.id].slice(0, SERIES_PER_TOPIC);
  }
  return byTopic;
}

/* ------------------------------- Markets ---------------------------- */
const MARKET_FIELDS = [
  'ticker', 'event_ticker', 'title', 'subtitle', 'yes_sub_title', 'no_sub_title',
  'status', 'market_type', 'open_time', 'close_time', 'latest_expiration_time',
  'expected_expiration_time', 'last_price_dollars', 'previous_price_dollars',
  'yes_bid_dollars', 'yes_ask_dollars', 'no_bid_dollars', 'no_ask_dollars',
  'yes_bid_size_fp', 'yes_ask_size_fp', 'no_bid_size_fp', 'no_ask_size_fp',
  'volume_fp', 'volume_24h_fp', 'open_interest_fp', 'notional_value_dollars',
  'result', 'settlement_value_dollars', 'settlement_ts', 'rules_primary',
  'price_level_structure',
];

function pickMarket(m, topic) {
  const out = { topic };
  for (const f of MARKET_FIELDS) if (m[f] !== undefined && m[f] !== null) out[f] = m[f];
  const price = num(m.last_price_dollars);
  const volume = num(m.volume_fp);
  const oi = num(m.open_interest_fp);
  // Derived dollars (NOT API fields) - see pages/verification.html and pages/flagged.html.
  out.contract_value_traded_usd = price !== null && volume !== null ? round2(price * volume) : null;
  out.open_interest_usd = price !== null && oi !== null ? round2(price * oi) : null;
  out.source_url = `${BASE}/markets/${encodeURIComponent(m.ticker)}`;
  return out;
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
    settlement_sources: (e.settlement_sources || []).map((s) => ({ name: s?.name ?? null, url: s?.url ?? null })),
    source_url: `${BASE}/events/${encodeURIComponent(e.event_ticker)}`,
  };
}

/* ----------------------------- Orderbooks --------------------------- */
async function loadOrderbooks(tickers, depth = 12) {
  const out = {};
  for (const ticker of tickers) {
    const json = await get(`/markets/${encodeURIComponent(ticker)}/orderbook?depth=${depth}`,
      { note: `orderbook for ${ticker}`, soft: true, allow404: true });
    if (!json) continue;
    const book = json?.orderbook_fp || {};
    const trim = (levels) => (Array.isArray(levels) ? levels.slice(-depth).reverse() : []);
    out[ticker] = {
      yes_dollars: trim(book.yes_dollars),
      no_dollars: trim(book.no_dollars),
      source_url: `${BASE}/markets/${encodeURIComponent(ticker)}/orderbook`,
    };
  }
  return out;
}

/* ------------------------------- Main ------------------------------- */
async function main() {
  const startedAt = Date.now();
  console.log(`[kalshi-snapshot] base=${BASE}`);

  const taxonomy = await loadTaxonomy();
  console.log(`[kalshi-snapshot] taxonomy categories: ${Object.keys(taxonomy).length}`);

  const seriesByTicker = await loadSeries(taxonomy);
  console.log(`[kalshi-snapshot] series catalogue: ${seriesByTicker.size}`);

  const inScope = pickInScopeSeries(seriesByTicker);
  for (const topic of TOPICS) console.log(`[kalshi-snapshot] in-scope series for ${topic.id}: ${inScope[topic.id].length}`);

  const eventsByTicker = new Map();
  const markets = [];

  for (const topic of TOPICS) {
    for (const series of inScope[topic.id]) {
      const seriesTicker = series.ticker;

      // Markets for the series (no status filter -> open + closed + settled).
      let cursor = '';
      for (let page = 0; page < 3; page += 1) {
        const q = `series_ticker=${encodeURIComponent(seriesTicker)}&limit=1000`;
        const json = await get(cursor ? `/markets?${q}&cursor=${encodeURIComponent(cursor)}` : `/markets?${q}`,
          { note: `markets for series=${seriesTicker}`, soft: true });
        if (!json) break;
        for (const m of json?.markets || []) markets.push(pickMarket(m, topic.id));
        cursor = json?.cursor || '';
        if (!cursor) break;
      }

      // Events for the series (official event titles + official event category).
      cursor = '';
      for (let page = 0; page < 3; page += 1) {
        const q = `series_ticker=${encodeURIComponent(seriesTicker)}&limit=200`;
        const json = await get(cursor ? `/events?${q}&cursor=${encodeURIComponent(cursor)}` : `/events?${q}`,
          { note: `events for series=${seriesTicker}`, soft: true });
        if (!json) break;
        for (const e of json?.events || []) {
          const picked = pickEvent(e);
          eventsByTicker.set(picked.event_ticker, picked);
        }
        cursor = json?.cursor || '';
        if (!cursor) break;
      }
    }
  }
  console.log(`[kalshi-snapshot] markets collected: ${markets.length}`);
  console.log(`[kalshi-snapshot] events collected: ${eventsByTicker.size}`);

  const seriesTitle = (t) => seriesByTicker.get(t)?.title ?? null;

  const enriched = markets.map((m) => {
    const event = eventsByTicker.get(m.event_ticker);
    const series = event?.series_ticker ? seriesByTicker.get(event.series_ticker) : null;
    return {
      ...m,
      series_ticker: event?.series_ticker ?? null,
      series_title: seriesTitle(event?.series_ticker),
      series_category: series?.category ?? null,
      series_categories: series?.categories ?? null,
      series_tags: series?.tags ?? null,
      series_frequency: series?.frequency ?? null,
      series_volume_fp: series?.volume_fp ?? null,
      event_title: event?.title ?? null,
      event_category: event?.category ?? null,
      settlement_sources: event?.settlement_sources ?? null,
    };
  });

  const open = enriched.filter((m) => m.status === 'active');
  const settled = enriched.filter((m) => m.status === 'finalized' || m.result === 'yes' || m.result === 'no');
  console.log(`[kalshi-snapshot] active markets: ${open.length} · settled markets: ${settled.length}`);

  // Event-level roll-up: the requested unit is "events".
  const eventsAgg = new Map();
  for (const m of open) {
    const key = m.event_ticker;
    const agg = eventsAgg.get(key) || {
      event_ticker: key,
      series_ticker: m.series_ticker,
      title: m.event_title,
      sub_title: null,
      category: m.event_category,
      topic: m.topic,
      markets: 0,
      volume_fp: 0,
      open_interest_fp: 0,
      contract_value_traded_usd: 0,
      open_interest_usd: 0,
      last_price_dollars: null,
      close_time: m.close_time,
      settlement_sources: m.settlement_sources,
      source_url: `${BASE}/events/${encodeURIComponent(key)}`,
    };
    agg.markets += 1;
    agg.volume_fp = round2(agg.volume_fp + (num(m.volume_fp) || 0));
    agg.open_interest_fp = round2(agg.open_interest_fp + (num(m.open_interest_fp) || 0));
    agg.contract_value_traded_usd = round2(agg.contract_value_traded_usd + (num(m.contract_value_traded_usd) || 0));
    agg.open_interest_usd = round2(agg.open_interest_usd + (num(m.open_interest_usd) || 0));
    const p = num(m.last_price_dollars);
    if (p !== null) agg.last_price_dollars = p;
    eventsAgg.set(key, agg);
  }
  const events = [...eventsAgg.values()]
    .sort((a, b) => (b.contract_value_traded_usd || 0) - (a.contract_value_traded_usd || 0));

  const topPerTopic = [];
  for (const topic of TOPICS) {
    const rows = open.filter((m) => m.topic === topic.id)
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
    request_budget: MAX_REQUESTS,
    budget_exhausted: budgetExhausted,
    docs: DOCS,
    topic_rules: TOPICS.map((t) => ({
      id: t.id,
      label: t.label,
      blurb: t.blurb,
      categories: t.categories,
      tags: t.tags,
      source: DOCS.taxonomy,
    })),
    counts: {
      taxonomy_categories: Object.keys(taxonomy).length,
      series_catalogue: seriesByTicker.size,
      series_per_topic: Object.fromEntries(TOPICS.map((t) => [t.id, inScope[t.id].length])),
      markets_collected: markets.length,
      events_collected: eventsByTicker.size,
      active_markets: open.length,
      settled_markets: settled.length,
      open_events: events.length,
    },
    caps: {
      series_per_topic: SERIES_PER_TOPIC,
      open_markets_per_topic: MAX_OPEN_MARKETS_PER_TOPIC,
      settled_markets_per_topic: MAX_SETTLED_PER_TOPIC,
      events_per_topic: MAX_EVENTS_PER_TOPIC,
      note: 'Rows are ranked first, then capped per topic. The rows kept are the highest-value ones; rows beyond the cap are not published.',
    },
    metric_definitions: {
      contract_value_traded_usd: 'DERIVED: volume_fp (contracts traded) x last_price_dollars ($ per contract). Not an API field. Sources: ' + DOCS.markets + ' , ' + DOCS.fixedPoint,
      open_interest_usd: 'DERIVED: open_interest_fp (open contracts) x last_price_dollars ($ per contract). Not an API field.',
      notional_value_dollars: 'API field, verbatim. Kalshi defines it as "the total value of a single contract at settlement in dollars" - it is NOT turnover.',
      series_volume_fp: 'API field, verbatim: total number of contracts traded across all events in the series.',
    },
  };

  await mkdir(OUT, { recursive: true });
  const write = async (name, value) => {
    await writeFile(resolve(OUT, name), `${JSON.stringify(value, null, 2)}\n`, 'utf8');
    console.log(`[kalshi-snapshot] wrote ${name}`);
  };

  const byTopic = (rows) => {
    const out = {};
    for (const t of TOPICS) out[t.id] = rows.filter((r) => r.topic === t.id);
    return out;
  };
  const sortByValue = (rows) => [...rows].sort(
    (a, b) => (b.contract_value_traded_usd || 0) - (a.contract_value_traded_usd || 0),
  );

  await write('meta.json', meta);
  await write('taxonomy.json', { generated_at: generatedAt, source: DOCS.taxonomy, tags_by_categories: taxonomy });
  await write('open-markets.json', {
    generated_at: generatedAt,
    source: DOCS.markets,
    metric: 'rows sorted by contract_value_traded_usd (derived)',
    cap_per_topic: MAX_OPEN_MARKETS_PER_TOPIC,
    topics: Object.fromEntries(Object.entries(byTopic(open)).map(([k, v]) => [k, sortByValue(v).slice(0, MAX_OPEN_MARKETS_PER_TOPIC)])),
  });
  await write('open-events.json', {
    generated_at: generatedAt,
    source: DOCS.events,
    metric: 'rows sorted by contract_value_traded_usd (derived)',
    cap_per_topic: MAX_EVENTS_PER_TOPIC,
    topics: Object.fromEntries(Object.entries(byTopic(events)).map(([k, v]) => [k, sortByValue(v).slice(0, MAX_EVENTS_PER_TOPIC)])),
  });
  await write('settled-markets.json', {
    generated_at: generatedAt,
    source: DOCS.markets,
    metric: 'rows sorted by settlement_ts (newest first)',
    cap_per_topic: MAX_SETTLED_PER_TOPIC,
    topics: Object.fromEntries(Object.entries(byTopic(settled)).map(([k, v]) => [
      k, [...v].sort((a, b) => String(b.settlement_ts || '').localeCompare(String(a.settlement_ts || ''))).slice(0, MAX_SETTLED_PER_TOPIC),
    ])),
  });
  await write('orderbooks.json', { generated_at: generatedAt, source: DOCS.orderbook, books: orderbooks });
  await write('collection-log.json', {
    generated_at: generatedAt,
    note: 'Every API request made by scripts/fetch-data.mjs, with its exact URL and HTTP status.',
    requests: requestLog,
  });

  console.log(`[kalshi-snapshot] done in ${Date.now() - startedAt}ms (${requestCount} requests)`);
}

main().catch(async (err) => {
  console.error(`[kalshi-snapshot] FAILED: ${err && err.message ? err.message : err}`);
  // Never lose a harvest: persist whatever was collected plus the failure reason
  // so the site can publish it and flag it for review.
  try {
    const generatedAt = new Date().toISOString();
    const byTopic = (rows) => {
      const out = {};
      for (const t of TOPICS) out[t.id] = rows.filter((r) => r.topic === t.id);
      return out;
    };
    await mkdir(OUT, { recursive: true });
    const write = async (name, value) => {
      await writeFile(resolve(OUT, name), `${JSON.stringify(value, null, 2)}\n`, 'utf8');
      console.log(`[kalshi-snapshot] wrote ${name}`);
    };
    await write('meta.json', {
      generated_at: generatedAt,
      base_url: BASE,
      environment: 'demo',
      request_count: requestCount,
      partial: true,
      error: String(err && err.message ? err.message : err),
      docs: DOCS,
      topic_rules: TOPICS.map((t) => ({ id: t.id, label: t.label, categories: t.categories, tags: t.tags })),
      counts: { taxonomy_categories: null, series_catalogue: null, markets_collected: 0, events_collected: 0 },
    });
    await write('open-markets.json', { generated_at: generatedAt, source: DOCS.markets, partial: true, topics: byTopic([]) });
    await write('open-events.json', { generated_at: generatedAt, source: DOCS.events, partial: true, topics: byTopic([]) });
    await write('settled-markets.json', { generated_at: generatedAt, source: DOCS.markets, partial: true, topics: byTopic([]) });
    await write('orderbooks.json', { generated_at: generatedAt, source: DOCS.orderbook, books: {} });
    await write('collection-log.json', {
      generated_at: generatedAt,
      note: 'Every API request made by scripts/fetch-data.mjs, with its exact URL and HTTP status.',
      error: String(err && err.message ? err.message : err),
      requests: requestLog,
    });
  } catch (writeErr) {
    console.error(`[kalshi-snapshot] could not even persist the partial snapshot: ${writeErr && writeErr.message}`);
  }
  process.exit(1);
});
