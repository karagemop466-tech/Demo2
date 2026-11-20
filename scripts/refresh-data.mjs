#!/usr/bin/env node
/**
 * refresh-data.mjs — pull the Kalshi *demo* market data this site publishes.
 *
 * Every field written here comes from the official Kalshi Trade API.
 * Endpoints used (all documented at https://docs.kalshi.com):
 *   GET /series?limit&cursor                       -> series metadata (category, tags)
 *   GET /events?limit&cursor&status                -> event metadata (series_ticker, category, title)
 *   GET /markets?limit&cursor&status               -> markets + prices/volume/open interest
 *   GET /markets/{ticker}/orderbook?depth         -> resting bids (liquidity)
 *   GET /exchange/status                           -> exchange state
 *
 * Nothing is invented: fields that the API does not return are written as null
 * and are rendered as "unverified" on the site.
 *
 * Usage: node scripts/refresh-data.mjs [--out data] [--base https://external-api.demo.kalshi.co/trade-api/v2]
 */
import { writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const argv = process.argv.slice(2);
const argOf = (flag, dflt) => {
  const i = argv.indexOf(flag);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
};
const BASE = argOf("--base", "https://external-api.demo.kalshi.co/trade-api/v2").replace(/\/+$/, "");
const OUT = resolve(argOf("--out", "data"));

const LIMITS = {
  series: { limit: 200, maxPages: 30 },
  events: { limit: 200, maxPages: 60 },
  markets: { limit: 1000, maxPages: 30 },
  settled: { limit: 1000, maxPages: 10 },
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getJSON(path) {
  const url = BASE + path;
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`GET ${path} -> HTTP ${res.status} ${body.slice(0, 200)}`);
  }
  return res.json();
}

/** Paginate a cursor-based endpoint. Returns { rows, pages, truncated }. */
async function paginate(path, { limit, maxPages }, query = {}) {
  const rows = [];
  let cursor = "";
  let pages = 0;
  for (; pages < maxPages; pages++) {
    const q = new URLSearchParams({ ...query, limit: String(limit) });
    if (cursor) q.set("cursor", cursor);
    const sep = path.includes("?") ? "&" : "?";
    const json = await getJSON(path + sep + q.toString());
    const batch = json.markets || json.events || json.series || [];
    rows.push(...batch);
    cursor = json.cursor || "";
    if (!cursor || batch.length === 0) break;
    await sleep(60);
  }
  return { rows, pages: pages + 1, truncated: pages >= maxPages && !!cursor };
}

/* ------------------------------------------------------------------ *
 * Topic scope. Only these five topics are published by this project.
 * Classification uses official series metadata first (category/tags),
 * then the event title, then the market title. Every assigned market
 * records which rule fired so a reviewer can audit it.
 * ------------------------------------------------------------------ */
const TOPICS = ["Gas prices", "Elections", "Culture", "Crypto", "Golf"];

const TOPIC_RULES = {
  "Gas prices": {
    category: [],
    tags: ["gas", "gasoline", "diesel", "crude", "oil", "petroleum", "fuel", "heating oil", "jet fuel", "energy"],
    titleWords: ["gas price", "gasoline", "diesel", "crude oil", "oil price", "petrol", "heating oil", "jet fuel", "refinery"],
  },
  Elections: {
    category: ["Elections"],
    tags: ["elections", "election", "primary", "polling", "republican", "democrat", "ballot"],
    titleWords: ["election", "president", "presidential", "senate", "house", "governor", "mayor", "primary", "ballot", "vote", "congress", "parliament", "referendum"],
  },
  Culture: {
    category: ["Entertainment", "Culture", "Media", "Mentions", "Awards", "Pop Culture"],
    tags: ["movies", "film", "music", "album", "tv", "television", "box office", "awards", "oscar", "grammy", "emmy", "celebrity", "entertainment", "books", "celebrity"],
    titleWords: ["movie", "film", "music", "album", "grammy", "oscar", "emmy", "box office", "celebrity", "actor", "actress", "singer", "tv show", "netflix", "spotify", "billboard", "met gala", "super bowl halftime"],
  },
  Crypto: {
    category: ["Crypto"],
    tags: ["crypto", "bitcoin", "btc", "ethereum", "eth", "solana", "doge", "dogecoin", "xrp", "ripple", "coin"],
    titleWords: ["bitcoin", "btc", "ethereum", "eth ", "solana", "dogecoin", "doge", "xrp", "crypto"],
  },
  Golf: {
    category: [],
    tags: ["golf", "pga", "lpga", "masters", "ryder cup", "open championship", "golf tour", "us open golf", "wmph"],
    titleWords: ["golf", "pga", "lpga", "masters", "ryder cup", "open championship", "bogey", "birdie", "eagle"],
  },
};

function norm(v) {
  return String(v ?? "").toLowerCase();
}

/**
 * Decide the topic of one market.
 * @returns {{topic:string|null, rule:string}} rule explains why.
 */
function classify(series, event, market) {
  const sCat = norm(series?.category);
  const sTags = (series?.tags || []).map(norm);
  const sTitle = norm(series?.title);
  const eTitle = norm(event?.title);
  const eCat = norm(event?.category);
  const mTitle = norm(market?.title);

  for (const topic of TOPICS) {
    const rule = TOPIC_RULES[topic];
    if (rule.category.some((c) => c === sCat || c === eCat)) {
      return { topic, rule: `official category "${series?.category || event?.category}"` };
    }
    const tagHit = sTags.find((t) => rule.tags.some((w) => t === w || t.includes(w)));
    if (tagHit) return { topic, rule: `official series tag "${tagHit}"` };
    const tHit = rule.titleWords.find((w) => sTitle.includes(w));
    if (tHit) return { topic, rule: `series title contains "${tHit}"` };
    const eHit = rule.titleWords.find((w) => eTitle.includes(w));
    if (eHit) return { topic, rule: `event title contains "${eHit}"` };
    const mHit = rule.titleWords.find((w) => mTitle.includes(w));
    if (mHit) return { topic, rule: `market title contains "${mHit}"` };
  }
  return { topic: null, rule: "" };
}

/* ----------------------------- helpers ----------------------------- */
const num = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};
const fp = (v) => (v === undefined || v === null || v === "" ? null : Number(v));

/** Dollar turnover = contracts traded x last traded price (computed, labelled as computed). */
function metrics(m) {
  const last = fp(m.last_price_dollars);
  const vol = fp(m.volume_fp);
  const vol24 = fp(m.volume_24h_fp);
  const oi = fp(m.open_interest_fp);
  return {
    last_price_dollars: last,
    turnover_dollars: vol !== null && last !== null ? vol * last : null,
    turnover_24h_dollars: vol24 !== null && last !== null ? vol24 * last : null,
    open_interest_value_dollars: oi !== null && last !== null ? oi * last : null,
    open_interest_fp: oi,
    volume_fp: vol,
    volume_24h_fp: vol24,
  };
}

/* ------------------------------- run ------------------------------- */
async function main() {
  const startedAt = new Date().toISOString();
  console.log(`[refresh] base=${BASE}`);

  const exchange = await getJSON("/exchange/status").catch((e) => ({ error: String(e) }));
  console.log(`[refresh] exchange=${JSON.stringify(exchange).slice(0, 160)}`);

  const seriesRes = await paginate("/series", LIMITS.series);
  const seriesMap = new Map();
  for (const s of seriesRes.rows) {
    seriesMap.set(s.ticker, {
      ticker: s.ticker,
      title: s.title ?? null,
      category: s.category ?? null,
      categories: s.categories ?? null,
      tags: s.tags ?? null,
      settlement_sources: (s.settlement_sources || []).map((x) => ({ name: x.name ?? null, url: x.url ?? null })),
      contract_terms_url: s.contract_terms_url ?? null,
    });
  }
  console.log(`[refresh] series=${seriesMap.size} pages=${seriesRes.pages}`);

  const eventsRes = await paginate("/events", LIMITS.events, { status: "open" });
  const eventMap = new Map();
  for (const e of eventsRes.rows) {
    eventMap.set(e.event_ticker, {
      event_ticker: e.event_ticker,
      series_ticker: e.series_ticker ?? null,
      title: e.title ?? null,
      sub_title: e.sub_title ?? null,
      category: e.category ?? null,
      mutually_exclusive: e.mutually_exclusive ?? null,
      strike_date: e.strike_date ?? null,
      settlement_sources: (e.settlement_sources || []).map((x) => ({ name: x.name ?? null, url: x.url ?? null })),
    });
  }
  console.log(`[refresh] events(open)=${eventMap.size} pages=${eventsRes.pages}`);

  const marketsRes = await paginate("/markets", LIMITS.markets, { status: "open" });
  console.log(`[refresh] markets(open)=${marketsRes.rows.length} pages=${marketsRes.pages}`);

  const settledRes = await paginate("/markets", LIMITS.settled, { status: "settled" });
  console.log(`[refresh] markets(settled)=${settledRes.rows.length} pages=${settledRes.pages}`);

  /* ---------------- build the in-scope universe ---------------- */
  const scoped = [];
  for (const m of marketsRes.rows) {
    const ev = eventMap.get(m.event_ticker);
    const se = ev?.series_ticker ? seriesMap.get(ev.series_ticker) : null;
    const cls = classify(se, ev, m);
    if (!cls.topic) continue;
    scoped.push({ m, ev, se, cls });
  }
  console.log(`[refresh] in-scope open markets=${scoped.length}`);

  // Orderbooks for the strongest markets per topic (liquidity depth + notional depth).
  const perTopic = new Map();
  for (const row of scoped) {
    const arr = perTopic.get(row.cls.topic) || [];
    arr.push(row);
    perTopic.set(row.cls.topic, arr);
  }
  const books = {};
  let bookRequests = 0;
  for (const [topic, rows] of perTopic) {
    rows.sort((a, b) => (metrics(b.m).turnover_dollars ?? -1) - (metrics(a.m).turnover_dollars ?? -1));
    for (const row of rows.slice(0, 15)) {
      const t = row.m.ticker;
      try {
        const ob = await getJSON(`/markets/${encodeURIComponent(t)}/orderbook?depth=20`);
        const yes = ob?.orderbook_fp?.yes_dollars || [];
        const no = ob?.orderbook_fp?.no_dollars || [];
        const depthNotional = (levels) =>
          levels.reduce((sum, lv) => sum + (fp(lv[0]) ?? 0) * (fp(lv[1]) ?? 0), 0);
        books[t] = {
          yes_bids: yes.map((lv) => [fp(lv[0]), fp(lv[1])]),
          no_bids: no.map((lv) => [fp(lv[0]), fp(lv[1])]),
          yes_depth_notional_dollars: depthNotional(yes),
          no_depth_notional_dollars: depthNotional(no),
        };
        bookRequests++;
      } catch (e) {
        books[t] = { error: String(e).slice(0, 200) };
      }
      await sleep(40);
    }
  }
  console.log(`[refresh] orderbooks fetched=${bookRequests}`);

  const marketRow = (row) => {
    const { m, ev, se, cls } = row;
    const mm = metrics(m);
    const book = books[m.ticker] || null;
    return {
      ticker: m.ticker,
      event_ticker: m.event_ticker ?? null,
      series_ticker: ev?.series_ticker ?? null,
      title: m.title ?? ev?.title ?? null,
      subtitle: m.subtitle ?? ev?.sub_title ?? null,
      yes_sub_title: m.yes_sub_title ?? null,
      no_sub_title: m.no_sub_title ?? null,
      topic: cls.topic,
      topic_rule: cls.rule,
      series_category: se?.category ?? ev?.category ?? null,
      series_tags: se?.tags ?? null,
      status: m.status ?? null,
      open_time: m.open_time ?? null,
      close_time: m.close_time ?? null,
      expected_expiration_time: m.expected_expiration_time ?? null,
      yes_bid_dollars: fp(m.yes_bid_dollars),
      yes_ask_dollars: fp(m.yes_ask_dollars),
      no_bid_dollars: fp(m.no_bid_dollars),
      no_ask_dollars: fp(m.no_ask_dollars),
      last_price_dollars: mm.last_price_dollars,
      volume_fp: mm.volume_fp,
      volume_24h_fp: mm.volume_24h_fp,
      open_interest_fp: mm.open_interest_fp,
      turnover_dollars: mm.turnover_dollars,
      turnover_24h_dollars: mm.turnover_24h_dollars,
      open_interest_value_dollars: mm.open_interest_value_dollars,
      resting_liquidity_notional_dollars: book && typeof book.yes_depth_notional_dollars === "number"
        ? book.yes_depth_notional_dollars + (book.no_depth_notional_dollars || 0)
        : null,
      notional_value_dollars: fp(m.notional_value_dollars),
      settlement_value_dollars: fp(m.settlement_value_dollars),
      result: m.result ?? null,
      settlement_ts: m.settlement_ts ?? null,
      price_ranges: m.price_ranges ?? null,
      price_level_structure: m.price_level_structure ?? null,
      rules_primary: m.rules_primary ?? null,
      settlement_sources: se?.settlement_sources?.length ? se.settlement_sources : ev?.settlement_sources ?? null,
      links: {
        api_market: `${BASE}/markets/${encodeURIComponent(m.ticker)}`,
        api_orderbook: `${BASE}/markets/${encodeURIComponent(m.ticker)}/orderbook`,
        api_docs_market: "https://docs.kalshi.com/api-reference/market/get-market",
        api_docs_markets: "https://docs.kalshi.com/api-reference/market/get-markets",
        api_docs_orderbook: "https://docs.kalshi.com/getting_started/orderbook_responses",
        kalshi_site: `https://demo.kalshi.co/markets/${encodeURIComponent(m.ticker)}`,
      },
    };
  };

  const allRows = scoped.map(marketRow);
  for (const t of TOPICS) {
    const rows = allRows.filter((r) => r.topic === t);
    rows.sort((a, b) => (b.turnover_dollars ?? -1) - (a.turnover_dollars ?? -1));
    console.log(`[refresh] topic ${t}: ${rows.length} markets, top turnover $${(rows[0]?.turnover_dollars ?? 0).toFixed(2)}`);
  }

  // Keep the published set bounded but complete per topic.
  const MAX_PER_TOPIC = 120;
  const markets = [];
  for (const t of TOPICS) {
    const rows = allRows.filter((r) => r.topic === t).sort((a, b) => (b.turnover_dollars ?? -1) - (a.turnover_dollars ?? -1));
    markets.push(...rows.slice(0, MAX_PER_TOPIC));
  }

  /* ---------------- resolved markets (yes / no) ---------------- */
  const resolved = [];
  for (const m of settledRes.rows) {
    const ev = eventMap.get(m.event_ticker);
    const se = ev?.series_ticker ? seriesMap.get(ev.series_ticker) : null;
    const cls = classify(se, ev, m);
    if (!cls.topic) continue;
    resolved.push({
      ticker: m.ticker,
      event_ticker: m.event_ticker ?? null,
      series_ticker: ev?.series_ticker ?? null,
      title: m.title ?? ev?.title ?? null,
      topic: cls.topic,
      topic_rule: cls.rule,
      series_category: se?.category ?? ev?.category ?? null,
      result: m.result ?? null,
      settlement_value_dollars: fp(m.settlement_value_dollars),
      settlement_ts: m.settlement_ts ?? null,
      close_time: m.close_time ?? null,
      last_price_dollars: fp(m.last_price_dollars),
      volume_fp: fp(m.volume_fp),
      turnover_dollars: fp(m.volume_fp) !== null && fp(m.last_price_dollars) !== null ? fp(m.volume_fp) * fp(m.last_price_dollars) : null,
      links: {
        api_market: `${BASE}/markets/${encodeURIComponent(m.ticker)}`,
        api_docs_market: "https://docs.kalshi.com/api-reference/market/get-market",
        kalshi_site: `https://demo.kalshi.co/markets/${encodeURIComponent(m.ticker)}`,
      },
    });
  }
  resolved.sort((a, b) => String(b.settlement_ts ?? "").localeCompare(String(a.settlement_ts ?? "")));
  console.log(`[refresh] in-scope resolved markets=${resolved.length}`);

  /* ---------------- series catalog ---------------- */
  const seriesOut = [];
  for (const [, s] of seriesMap) {
    const cls = classify(s, null, null);
    if (!cls.topic) continue;
    seriesOut.push({ ...s, topic: cls.topic, topic_rule: cls.rule, api_docs: "https://docs.kalshi.com/api-reference/market/get-series" });
  }
  seriesOut.sort((a, b) => String(a.ticker).localeCompare(String(b.ticker)));

  const meta = {
    generated_at: startedAt,
    completed_at: new Date().toISOString(),
    base_url: BASE,
    endpoints: {
      series: `${BASE}/series`,
      events: `${BASE}/events?status=open`,
      markets_open: `${BASE}/markets?status=open`,
      markets_settled: `${BASE}/markets?status=settled`,
      orderbook: `${BASE}/markets/{ticker}/orderbook`,
      exchange_status: `${BASE}/exchange/status`,
    },
    counts: {
      series_total: seriesMap.size,
      events_open: eventMap.size,
      markets_open: marketsRes.rows.length,
      markets_settled: settledRes.rows.length,
      in_scope_open: allRows.length,
      published_markets: markets.length,
      in_scope_resolved: resolved.length,
      published_series: seriesOut.length,
      orderbooks_fetched: bookRequests,
    },
    pagination: {
      series_pages: seriesRes.pages,
      events_pages: eventsRes.pages,
      markets_pages: marketsRes.pages,
      settled_pages: settledRes.pages,
      series_truncated: seriesRes.truncated,
      events_truncated: eventsRes.truncated,
      markets_truncated: marketsRes.truncated,
      settled_truncated: settledRes.truncated,
    },
    exchange_status: exchange,
    topics: TOPICS,
    topic_rules: TOPIC_RULES,
    metric_definitions: {
      turnover_dollars: "volume_fp x last_price_dollars (computed on this site from two API fields)",
      turnover_24h_dollars: "volume_24h_fp x last_price_dollars (computed on this site from two API fields)",
      open_interest_value_dollars: "open_interest_fp x last_price_dollars (computed on this site from two API fields)",
      resting_liquidity_notional_dollars: "sum over orderbook levels of price x contracts, YES bids + NO bids (computed on this site)",
      notional_value_dollars: "verbatim API field notional_value_dollars (Get Markets response)",
    },
  };

  await mkdir(OUT, { recursive: true });
  await writeFile(resolve(OUT, "markets.json"), JSON.stringify({ meta, markets }, null, 1));
  await writeFile(resolve(OUT, "resolved.json"), JSON.stringify({ meta, resolved }, null, 1));
  await writeFile(resolve(OUT, "series.json"), JSON.stringify({ meta, series: seriesOut }, null, 1));
  await writeFile(resolve(OUT, "meta.json"), JSON.stringify(meta, null, 2));
  console.log(`[refresh] wrote ${resolve(OUT, "markets.json")} (${markets.length} markets)`);
  console.log(`[refresh] wrote ${resolve(OUT, "resolved.json")} (${resolved.length} resolved)`);
  console.log(`[refresh] wrote ${resolve(OUT, "series.json")} (${seriesOut.length} series)`);
}

main().catch((e) => {
  console.error("[refresh] FAILED:", e);
  process.exit(1);
});
