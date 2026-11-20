export const API_BASE = "https://external-api.demo.kalshi.co/trade-api/v2";
export const ORDERBOOK_DOCS = "https://docs.kalshi.com/api-reference/market/get-market-orderbook";
export const MULTI_ORDERBOOK_DOCS = "https://docs.kalshi.com/api-reference/market/get-multiple-market-orderbooks";
export const EVENT_DOCS = "https://docs.kalshi.com/api-reference/events/get-events";

export const TOPICS = [
  { slug: "gas-prices", label: "Gas prices", icon: "↗" },
  { slug: "elections", label: "Elections", icon: "◉" },
  { slug: "culture", label: "Culture", icon: "✦" },
  { slug: "crypto", label: "Crypto", icon: "₿" },
  { slug: "golf", label: "Golf", icon: "⛳" },
];

const WATCHLIST_KEY = "kalshi-demo-watchlist-v1";
const REFRESH_MS = 60_000;
const MAX_EVENT_PAGES = 50;
const ORDERBOOK_BATCH_SIZE = 100;
const RANGE_SECONDS = {
  "30s": 30,
  "5m": 5 * 60,
  "15m": 15 * 60,
  "1h": 60 * 60,
  "6h": 6 * 60 * 60,
  "24h": 24 * 60 * 60,
};

const TOPIC_MATCHERS = {
  "gas-prices": /\b(gas|gasoline|natural gas|fuel prices?)\b/i,
  elections: /\b(election|elections|presidential|midterm|primary|runoff|ballot|nominee|gubernatorial|senatorial)\b/i,
  culture: /\b(culture|cultural|entertainment|movie|movies|film|films|music|album|song|artist|box office|streaming|television|tv|oscars?|grammys?|emmys?|tonys?|golden globes?)\b/i,
  crypto: /\b(crypto|cryptocurrency|bitcoin|btc|ethereum|ether|eth|solana|sol|blockchain|token)\b/i,
  golf: /\b(golf|pga|lpga|ryder cup|the masters|open championship)\b/i,
};

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function getTopicsForEvent(event = {}) {
  const category = String(event.category ?? "");
  const text = [
    event.title,
    event.sub_title,
    event.series_ticker,
    event.event_ticker,
    category,
  ].filter(Boolean).join(" ");
  const matched = [];

  for (const topic of TOPICS) {
    if (TOPIC_MATCHERS[topic.slug].test(text)) matched.push(topic.slug);
  }

  return matched;
}

export function isActiveBinaryMarket(market = {}) {
  return market.market_type === "binary" && market.status === "active" && !market.result;
}

function getPriceLevels(bookSide) {
  if (!Array.isArray(bookSide)) return [];
  return bookSide
    .filter((level) => Array.isArray(level) && level.length >= 2)
    .map(([price, contracts]) => ({
      price: numberOrNull(price),
      contracts: numberOrNull(contracts),
    }))
    .filter((level) => level.price !== null && level.contracts !== null && level.contracts >= 0);
}

function getOrderbookSides(orderbook) {
  const fp = orderbook?.orderbook_fp ?? orderbook;
  return {
    yes: getPriceLevels(fp?.yes_dollars ?? fp?.yes),
    no: getPriceLevels(fp?.no_dollars ?? fp?.no),
  };
}

/**
 * Sum bid-side notional across all returned YES and NO price levels.
 * This is a displayed order-book metric (price × contracts), not traded dollar volume.
 */
export function orderbookBidNotional(orderbook) {
  if (!orderbook || typeof orderbook !== "object") return null;
  const { yes, no } = getOrderbookSides(orderbook);
  const sum = [...yes, ...no].reduce((total, level) => total + (level.price * level.contracts), 0);
  return Number.isFinite(sum) ? sum : null;
}

/**
 * Convert Kalshi's YES/NO bid-only book into visible bid rows and parity-derived asks.
 * An ask is explicitly marked derived; the source API does not return an ask ladder.
 */
export function buildOrderbookRows(orderbook) {
  if (!orderbook || typeof orderbook !== "object") return null;
  const { yes, no } = getOrderbookSides(orderbook);
  const rows = [];

  for (const level of yes) {
    rows.push({ side: "YES bid", kind: "bid-yes", price: level.price, contracts: level.contracts, notional: level.price * level.contracts, derived: false });
    rows.push({ side: "NO ask · implied", kind: "ask-no", price: 1 - level.price, contracts: level.contracts, notional: (1 - level.price) * level.contracts, derived: true });
  }
  for (const level of no) {
    rows.push({ side: "NO bid", kind: "bid-no", price: level.price, contracts: level.contracts, notional: level.price * level.contracts, derived: false });
    rows.push({ side: "YES ask · implied", kind: "ask-yes", price: 1 - level.price, contracts: level.contracts, notional: (1 - level.price) * level.contracts, derived: true });
  }

  return rows.sort((a, b) => {
    const aAsk = a.derived;
    const bAsk = b.derived;
    if (aAsk !== bAsk) return aAsk ? 1 : -1;
    if (aAsk) return a.price - b.price;
    return b.price - a.price;
  });
}

function formatCurrency(value, digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatPrice(value) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return formatCurrency(value, 4);
}

function formatQuantity(value) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
}

function formatTimestamp(timestamp, options = {}) {
  if (!timestamp) return "—";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: options.dateStyle ?? "medium",
    timeStyle: options.timeStyle ?? "short",
  }).format(date);
}

function relativeApiPath(path) {
  return `${API_BASE}${path}`;
}

async function fetchJson(url, { timeoutMs = 15_000 } = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Kalshi API returned HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    if (error?.name === "AbortError") throw new Error("Kalshi API request timed out");
    if (error instanceof TypeError) {
      throw new Error("Browser could not reach the demo API. Check network access, API availability, or browser CORS policy.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function loadOpenEvents({ maxPages = MAX_EVENT_PAGES } = {}) {
  const events = [];
  let cursor = "";
  let pageCount = 0;

  do {
    const params = new URLSearchParams({ status: "open", with_nested_markets: "true", limit: "200" });
    if (cursor) params.set("cursor", cursor);
    const payload = await fetchJson(relativeApiPath(`/events?${params.toString()}`));
    events.push(...(Array.isArray(payload.events) ? payload.events : []));
    cursor = typeof payload.cursor === "string" ? payload.cursor : "";
    pageCount += 1;
  } while (cursor && pageCount < maxPages);

  return { events, pageCount, truncated: Boolean(cursor) };
}

async function loadOrderbooks(tickers) {
  const orderbooksByTicker = new Map();
  const errors = [];
  const uniqueTickers = [...new Set(tickers)].filter(Boolean);

  for (let index = 0; index < uniqueTickers.length; index += ORDERBOOK_BATCH_SIZE) {
    const batch = uniqueTickers.slice(index, index + ORDERBOOK_BATCH_SIZE);
    const params = new URLSearchParams();
    batch.forEach((ticker) => params.append("tickers", ticker));
    try {
      const payload = await fetchJson(relativeApiPath(`/markets/orderbooks?${params.toString()}`));
      for (const item of Array.isArray(payload.orderbooks) ? payload.orderbooks : []) {
        if (item?.ticker && item.orderbook_fp) orderbooksByTicker.set(item.ticker, item.orderbook_fp);
      }
    } catch (error) {
      errors.push(error.message);
    }
  }

  return { orderbooksByTicker, errors, requestedCount: uniqueTickers.length };
}

function sumComplete(values) {
  if (!values.length) return 0;
  if (values.some((value) => numberOrNull(value) === null)) return null;
  return values.reduce((sum, value) => sum + Number(value), 0);
}

function eventMarketModels(events) {
  const models = [];
  for (const event of events) {
    const topics = getTopicsForEvent(event);
    if (!topics.length) continue;
    const activeMarkets = (Array.isArray(event.markets) ? event.markets : []).filter(isActiveBinaryMarket);
    if (!activeMarkets.length) continue;
    models.push({ event, topics, markets: activeMarkets });
  }
  return models;
}

function scoreEvent(model, orderbooksByTicker) {
  const values = [];
  for (const market of model.markets) {
    if (!orderbooksByTicker.has(market.ticker)) return null;
    const score = orderbookBidNotional(orderbooksByTicker.get(market.ticker));
    if (score === null) return null;
    values.push(score);
  }
  return values.reduce((sum, value) => sum + value, 0);
}

function getTopic(slug) {
  return TOPICS.find((topic) => topic.slug === slug) ?? null;
}

function topicPills(topicSlugs) {
  return `<span class="topic-pills">${topicSlugs.map((slug) => {
    const topic = getTopic(slug);
    return topic ? `<span class="badge">${escapeHtml(topic.label)}</span>` : "";
  }).join("")}</span>`;
}

function eventSourceLinks(event, firstMarket) {
  const eventHref = relativeApiPath(`/events/${encodeURIComponent(event.event_ticker)}?with_nested_markets=true`);
  const marketHref = firstMarket
    ? relativeApiPath(`/markets/${encodeURIComponent(firstMarket.ticker)}/orderbook`)
    : ORDERBOOK_DOCS;
  return `<a class="source-link" href="${escapeHtml(eventHref)}" target="_blank" rel="noopener noreferrer">Event API ↗</a><a class="source-link" href="${escapeHtml(marketHref)}" target="_blank" rel="noopener noreferrer">Book source ↗</a>`;
}

function getWatchlist() {
  try {
    const parsed = JSON.parse(localStorage.getItem(WATCHLIST_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item) => item && typeof item.event_ticker === "string");
  } catch {
    return [];
  }
}

function setWatchlist(items) {
  try {
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(items));
    return true;
  } catch {
    return false;
  }
}

function isEventTracked(eventTicker) {
  return getWatchlist().some((item) => item.event_ticker === eventTicker);
}

function toggleEventWatch(model) {
  const watchlist = getWatchlist();
  const existingIndex = watchlist.findIndex((item) => item.event_ticker === model.event.event_ticker);
  if (existingIndex >= 0) {
    watchlist.splice(existingIndex, 1);
  } else {
    watchlist.push({
      event_ticker: model.event.event_ticker,
      series_ticker: model.event.series_ticker ?? "",
      title: model.event.title ?? model.event.event_ticker,
      topics: model.topics,
      market_tickers: model.markets.map((market) => market.ticker).filter(Boolean),
      added_at: new Date().toISOString(),
    });
  }
  return setWatchlist(watchlist);
}

function getVisibleModels(models, selectedTopic) {
  if (!selectedTopic || selectedTopic === "all") return models;
  return models.filter((model) => model.topics.includes(selectedTopic));
}

function renderEventRows(models, orderbooksByTicker, selectedTopic) {
  const tbody = document.querySelector("#events-table-body");
  if (!tbody) return;
  const visible = getVisibleModels(models, selectedTopic).map((model) => ({
    ...model,
    depthNotional: scoreEvent(model, orderbooksByTicker),
    volume24h: sumComplete(model.markets.map((market) => market.volume_24h_fp)),
  }));
  visible.sort((a, b) => {
    if (a.depthNotional === null && b.depthNotional !== null) return 1;
    if (a.depthNotional !== null && b.depthNotional === null) return -1;
    if (a.depthNotional !== null && b.depthNotional !== null && b.depthNotional !== a.depthNotional) return b.depthNotional - a.depthNotional;
    return String(a.event.title ?? "").localeCompare(String(b.event.title ?? ""));
  });

  if (!visible.length) {
    const sourceLink = `<a href="${EVENT_DOCS}" target="_blank" rel="noopener noreferrer">Official events API documentation ↗</a>`;
    tbody.innerHTML = `<tr><td class="empty-cell" colspan="7"><strong>No matching open binary markets in the latest API response.</strong>The category rules are intentionally conservative; an API error or a topic not matched by the current title/category keywords will not be replaced with sample values. ${sourceLink}</td></tr>`;
    return;
  }

  tbody.innerHTML = visible.map((model, index) => {
    const firstMarket = model.markets[0];
    const title = model.event.title || model.event.event_ticker || "Untitled event";
    const titleSub = model.event.sub_title || model.event.series_ticker || model.event.event_ticker || "";
    const notional = model.depthNotional === null ? "—" : formatCurrency(model.depthNotional);
    const volume = model.volume24h === null ? "—" : `${formatQuantity(model.volume24h)} contracts`;
    const topics = topicPills(model.topics);
    const tracked = isEventTracked(model.event.event_ticker);
    const marketCount = model.markets.length;
    const eventTicker = escapeHtml(model.event.event_ticker ?? "");
    const marketTicker = escapeHtml(firstMarket?.ticker ?? "");
    const trackLabel = tracked ? "Watching" : "Track";
    const actionLabel = tracked ? "Remove from local watchlist" : "Add to local watchlist";

    return `<tr class="event-row" data-event-ticker="${eventTicker}" data-market-ticker="${marketTicker}" tabindex="0" aria-label="Select ${escapeHtml(title)}">
      <td class="table-number">${index + 1}</td>
      <td><span class="table-title">${escapeHtml(title)}</span><span class="table-subtitle">${escapeHtml(titleSub)}</span></td>
      <td>${topics}</td>
      <td><span class="badge badge-live">${marketCount} open ${marketCount === 1 ? "market" : "markets"}</span></td>
      <td class="table-number" title="Sum of returned YES and NO bid-level price × contract quantities">${notional}<span class="table-subtitle">bid-side depth</span></td>
      <td class="table-number">${volume}<span class="table-subtitle">API volume field is contracts</span></td>
      <td><div class="source-stack">${eventSourceLinks(model.event, firstMarket)}<button class="button button-small button-link" type="button" data-watch="${eventTicker}" aria-label="${actionLabel}">${trackLabel}</button></div></td>
    </tr>`;
  }).join("");
}

function renderTopicTabs(models, selectedTopic) {
  const container = document.querySelector("#topic-tabs");
  if (!container) return;
  const counts = new Map(TOPICS.map((topic) => [topic.slug, 0]));
  for (const model of models) {
    for (const slug of model.topics) counts.set(slug, (counts.get(slug) ?? 0) + 1);
  }
  const isRoot = location.pathname.endsWith("/index.html") || location.pathname.endsWith("/");
  const rootPrefix = document.body.dataset.rootPrefix ?? "./";
  const links = [{ slug: "all", label: "All topics", href: `${rootPrefix}index.html`, count: models.length }];
  for (const topic of TOPICS) {
    links.push({
      slug: topic.slug,
      label: topic.label,
      href: `${rootPrefix}categories/${topic.slug}.html`,
      count: counts.get(topic.slug) ?? 0,
    });
  }
  container.innerHTML = links.map((item) => `<a class="topic-tab ${selectedTopic === item.slug || (isRoot && item.slug === "all" && selectedTopic === "all") ? "is-active" : ""}" href="${escapeHtml(item.href)}" ${selectedTopic === item.slug ? 'aria-current="page"' : ""}>${escapeHtml(item.label)}<span class="topic-tab-count">${item.count}</span></a>`).join("");
}

function fillMarketSelector(models) {
  const select = document.querySelector("#market-select");
  if (!select) return;
  const options = models.flatMap((model) => model.markets.map((market) => ({
    ticker: market.ticker,
    title: market.title || market.yes_sub_title || model.event.title || market.ticker,
    eventTitle: model.event.title || model.event.event_ticker,
    seriesTicker: model.event.series_ticker || "",
    market,
    event: model.event,
  })));
  const current = select.value;
  select.innerHTML = options.length
    ? options.map((option) => `<option value="${escapeHtml(option.ticker)}">${escapeHtml(option.title)} · ${escapeHtml(option.ticker)}</option>`).join("")
    : `<option value="">No open market</option>`;
  const next = options.find((option) => option.ticker === current) ?? options[0];
  select.value = next?.ticker ?? "";
  return options;
}

function setStatus(message, kind = "default") {
  const banner = document.querySelector("#api-status");
  const headerDot = document.querySelector("#header-status-dot");
  const headerText = document.querySelector("#header-status-text");
  if (banner) {
    banner.className = `status-banner${kind === "error" ? " status-banner-error" : kind === "ok" ? " status-banner-ok" : ""}`;
    banner.innerHTML = `<span class="status-dot ${kind === "error" ? "is-error" : kind === "ok" ? "is-live" : ""}" aria-hidden="true"></span><span>${escapeHtml(message)}</span><span class="status-time" id="last-updated-text">${escapeHtml(document.querySelector("#last-updated-text")?.textContent ?? "")}</span>`;
  }
  if (headerDot) headerDot.className = `status-dot ${kind === "error" ? "is-error" : kind === "ok" ? "is-live" : ""}`;
  if (headerText) headerText.textContent = kind === "error" ? "API issue" : kind === "ok" ? "Demo API connected" : "Connecting";
}

function setLastUpdated(date = new Date()) {
  const timeText = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZoneName: "short" }).format(date);
  const lastUpdated = document.querySelector("#last-updated-text");
  if (lastUpdated) lastUpdated.textContent = `Updated ${timeText}`;
  const summary = document.querySelector("#stat-updated");
  if (summary) summary.textContent = timeText;
}

function updateStats(models, books) {
  const eventCount = document.querySelector("#stat-events");
  const marketCount = document.querySelector("#stat-markets");
  const topDepth = document.querySelector("#stat-depth");
  const topLabel = document.querySelector("#stat-depth-label");
  if (eventCount) eventCount.textContent = String(models.length);
  if (marketCount) marketCount.textContent = String(models.reduce((sum, model) => sum + model.markets.length, 0));
  const scores = models.map((model) => scoreEvent(model, books)).filter((value) => value !== null);
  const best = scores.length ? Math.max(...scores) : null;
  if (topDepth) topDepth.textContent = best === null ? "—" : formatCurrency(best, 0);
  if (topLabel) topLabel.textContent = best === null ? "No complete orderbook score" : "Top event displayed bid-side notional";
}

function setEmptyChart(message, detail = "") {
  const chart = document.querySelector("#price-chart");
  if (!chart) return;
  chart.innerHTML = `<div class="chart-empty"><div><strong>${escapeHtml(message)}</strong>${escapeHtml(detail)}</div></div>`;
}

function chartTimeLabel(timestamp, range) {
  const date = new Date(timestamp);
  if (range === "30s" || range === "5m") return date.toLocaleTimeString([], { minute: "2-digit", second: "2-digit" });
  if (range === "15m" || range === "1h" || range === "6h") return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function buildChartSvg(points, range = "1h") {
  const valid = points.filter((point) => Number.isFinite(point?.ts) && Number.isFinite(point?.price));
  if (!valid.length) return "";
  const width = 760;
  const height = 245;
  const left = 62;
  const right = 17;
  const top = 15;
  const bottom = 34;
  const innerWidth = width - left - right;
  const innerHeight = height - top - bottom;
  const oldest = Math.min(...valid.map((point) => point.ts));
  const newest = Math.max(...valid.map((point) => point.ts));
  let minPrice = Math.min(...valid.map((point) => point.price));
  let maxPrice = Math.max(...valid.map((point) => point.price));
  if (minPrice === maxPrice) {
    minPrice = Math.max(0, minPrice - 0.025);
    maxPrice = Math.min(1, maxPrice + 0.025);
    if (minPrice === maxPrice) maxPrice = minPrice + 0.05;
  } else {
    const padding = (maxPrice - minPrice) * 0.12;
    minPrice = Math.max(0, minPrice - padding);
    maxPrice = Math.min(1, maxPrice + padding);
  }
  const xFor = (ts) => left + (newest === oldest ? 0.5 : (ts - oldest) / (newest - oldest)) * innerWidth;
  const yFor = (price) => top + ((maxPrice - price) / (maxPrice - minPrice)) * innerHeight;
  const path = valid.map((point, index) => `${index ? "L" : "M"}${xFor(point.ts).toFixed(1)},${yFor(point.price).toFixed(1)}`).join(" ");
  const yTicks = Array.from({ length: 4 }, (_, index) => maxPrice - ((maxPrice - minPrice) * index / 3));
  const timeTicks = newest === oldest ? [oldest] : [oldest, oldest + (newest - oldest) / 2, newest];
  const grid = yTicks.map((value) => {
    const y = yFor(value);
    return `<line x1="${left}" y1="${y}" x2="${width - right}" y2="${y}" class="chart-gridline"/><text x="${left - 9}" y="${y + 3}" text-anchor="end" class="chart-axis-label">${formatPrice(value)}</text>`;
  }).join("");
  const labels = timeTicks.map((time, index) => {
    const x = xFor(time);
    const anchor = index === 0 ? "start" : index === timeTicks.length - 1 ? "end" : "middle";
    return `<text x="${x}" y="${height - 9}" text-anchor="${anchor}" class="chart-axis-label">${escapeHtml(chartTimeLabel(time, range))}</text>`;
  }).join("");
  const last = valid[valid.length - 1];
  const circles = valid.length === 1 ? `<circle cx="${xFor(last.ts)}" cy="${yFor(last.price)}" r="4" class="chart-point"/>` : "";
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Contract price over time. The horizontal axis is time and the vertical axis is price in dollars.">
    <style>.chart-gridline{stroke:#e6eded;stroke-width:1}.chart-axis-label{fill:#7b898d;font:10px ui-sans-serif,system-ui,sans-serif}.chart-path{fill:none;stroke:#087e75;stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round}.chart-point{fill:#087e75;stroke:#fff;stroke-width:2}</style>
    ${grid}<path d="${path}" class="chart-path"/>${circles}${labels}
  </svg>`;
}

function renderChart(points, range) {
  const chart = document.querySelector("#price-chart");
  if (!chart) return;
  const cutoff = Date.now() - (RANGE_SECONDS[range] ?? RANGE_SECONDS["1h"]) * 1000;
  const filtered = points.filter((point) => point.ts >= cutoff && Number.isFinite(point.price));
  if (!filtered.length) {
    setEmptyChart("No confirmed price observations in this window.", range === "30s" ? "Seconds view starts sampling when this page opens." : "The API has not returned a price point for the selected market and range.");
    return;
  }
  const svg = buildChartSvg(filtered, range);
  chart.innerHTML = svg || `<div class="chart-empty"><div><strong>No chart points available.</strong>Price values are left blank when the API response is missing.</div></div>`;
}

async function fetchCandlesticks(option, range) {
  const end = Math.floor(Date.now() / 1000);
  const start = end - (RANGE_SECONDS[range] ?? RANGE_SECONDS["1h"]);
  const period = ["6h", "24h"].includes(range) ? 60 : 1;
  const params = new URLSearchParams({
    start_ts: String(start),
    end_ts: String(end),
    period_interval: String(period),
    include_latest_before_start: "true",
  });
  const path = `/series/${encodeURIComponent(option.seriesTicker)}/markets/${encodeURIComponent(option.ticker)}/candlesticks?${params.toString()}`;
  const payload = await fetchJson(relativeApiPath(path));
  return (Array.isArray(payload.candlesticks) ? payload.candlesticks : [])
    .map((candle) => ({
      ts: Number(candle.end_period_ts) * 1000,
      price: numberOrNull(candle.price?.close_dollars),
    }))
    .filter((point) => Number.isFinite(point.ts) && point.price !== null);
}

function renderOrderbook(book) {
  const body = document.querySelector("#orderbook-body");
  if (!body) return;
  const sourceHref = dashboardState.currentTicker
    ? relativeApiPath(`/markets/${encodeURIComponent(dashboardState.currentTicker)}/orderbook?depth=10`)
    : ORDERBOOK_DOCS;
  if (!book) {
    body.innerHTML = `<tr><td class="empty-cell" colspan="5"><strong>Orderbook unavailable.</strong>No orderbook value was confirmed for this market. <a class="source-link" href="${escapeHtml(ORDERBOOK_DOCS)}" target="_blank" rel="noopener noreferrer">Official orderbook API documentation ↗</a></td></tr>`;
    return;
  }
  const rows = buildOrderbookRows(book);
  if (!rows?.length) {
    body.innerHTML = `<tr><td class="empty-cell" colspan="5"><strong>No visible price levels returned.</strong>The official book response contained no YES or NO bid levels. <a class="source-link" href="${escapeHtml(sourceHref)}" target="_blank" rel="noopener noreferrer">Official market book response ↗</a></td></tr>`;
    return;
  }
  body.innerHTML = rows.slice(0, 40).map((row) => {
    const sideClass = row.kind === "bid-yes" ? "book-side-yes" : row.kind === "bid-no" ? "book-side-no" : "book-side-ask";
    return `<tr>
      <td class="book-side ${sideClass}">${escapeHtml(row.side)}</td>
      <td class="table-number book-level">${formatPrice(row.price)}</td>
      <td class="table-number book-level">${formatQuantity(row.contracts)}</td>
      <td class="table-number book-level">${formatCurrency(row.notional)}</td>
      <td><a class="source-link" href="${escapeHtml(sourceHref)}" target="_blank" rel="noopener noreferrer">Market book API ↗</a></td>
    </tr>`;
  }).join("");
}

function updateMarketSummary(option, market) {
  const title = document.querySelector("#selected-market-title");
  const ticker = document.querySelector("#selected-market-ticker");
  const price = document.querySelector("#selected-market-price");
  const priceLabel = document.querySelector("#selected-market-price-label");
  const bid = document.querySelector("#selected-market-bid");
  const ask = document.querySelector("#selected-market-ask");
  const status = document.querySelector("#selected-market-status");
  if (!option) {
    if (title) title.textContent = "Select an open market";
    if (ticker) ticker.textContent = "No market selected";
    if (price) price.textContent = "—";
    if (priceLabel) priceLabel.textContent = "No price observation";
    if (bid) bid.textContent = "—";
    if (ask) ask.textContent = "—";
    if (status) status.textContent = "—";
    return;
  }
  const current = market ?? option.market;
  if (title) title.textContent = current.title || current.yes_sub_title || option.title || "Untitled market";
  if (ticker) ticker.textContent = option.ticker;
  if (price) price.textContent = formatPrice(numberOrNull(current.last_price_dollars));
  if (priceLabel) priceLabel.textContent = "Last price · API dollars field";
  if (bid) bid.textContent = formatPrice(numberOrNull(current.yes_bid_dollars));
  if (ask) ask.textContent = formatPrice(numberOrNull(current.yes_ask_dollars));
  if (status) status.textContent = current.status ? String(current.status) : "—";
}

const dashboardState = {
  models: [],
  orderbooksByTicker: new Map(),
  marketOptions: [],
  currentTicker: "",
  selectedMarketData: null,
  selectedBook: null,
  range: "1h",
  pricePoints: [],
  chartLastFetchedAt: 0,
  refreshing: false,
  interval: null,
  selectedInterval: null,
  truncated: false,
};

function selectedOption() {
  return dashboardState.marketOptions.find((option) => option.ticker === dashboardState.currentTicker) ?? null;
}

function updateSelectedTicker(ticker) {
  if (!ticker || ticker === dashboardState.currentTicker) return;
  dashboardState.currentTicker = ticker;
  dashboardState.selectedMarketData = null;
  dashboardState.selectedBook = null;
  dashboardState.pricePoints = [];
  dashboardState.chartLastFetchedAt = 0;
  const option = selectedOption();
  updateMarketSummary(option, option?.market);
  renderOrderbook(null);
  setEmptyChart(dashboardState.range === "30s" ? "Seconds view is collecting observations." : "Loading official price history…");
  void refreshSelectedMarket(true);
  startSelectedTimer();
}

async function refreshSelectedMarket(forceChart = false) {
  const option = selectedOption();
  if (!option) return;
  const marketPath = `/markets/${encodeURIComponent(option.ticker)}`;
  const orderbookPath = `/markets/${encodeURIComponent(option.ticker)}/orderbook?depth=10`;

  const results = await Promise.allSettled([
    fetchJson(relativeApiPath(marketPath)),
    fetchJson(relativeApiPath(orderbookPath)),
  ]);
  if (results[0].status === "fulfilled") {
    const currentMarket = results[0].value.market ?? results[0].value;
    dashboardState.selectedMarketData = currentMarket;
    updateMarketSummary(option, currentMarket);
    const lastPrice = numberOrNull(currentMarket.last_price_dollars);
    if (dashboardState.range === "30s" && lastPrice !== null) {
      const now = Date.now();
      const previous = dashboardState.pricePoints.at(-1);
      if (!previous || now - previous.ts >= 4_000) dashboardState.pricePoints.push({ ts: now, price: lastPrice });
      const cutoff = now - RANGE_SECONDS["30s"] * 1000;
      dashboardState.pricePoints = dashboardState.pricePoints.filter((point) => point.ts >= cutoff).slice(-60);
      renderChart(dashboardState.pricePoints, dashboardState.range);
    }
  } else {
    setStatus(results[0].reason?.message ?? "Could not refresh selected market.", "error");
  }

  if (results[1].status === "fulfilled") {
    dashboardState.selectedBook = results[1].value.orderbook_fp ?? results[1].value;
    renderOrderbook(dashboardState.selectedBook);
  } else {
    renderOrderbook(null);
  }

  if (dashboardState.range !== "30s" && (forceChart || Date.now() - dashboardState.chartLastFetchedAt > 55_000)) {
    try {
      const points = await fetchCandlesticks(option, dashboardState.range);
      dashboardState.pricePoints = points;
      dashboardState.chartLastFetchedAt = Date.now();
      renderChart(points, dashboardState.range);
    } catch (error) {
      setEmptyChart("Price history unavailable.", error.message);
    }
  }
}

function startSelectedTimer() {
  if (dashboardState.selectedInterval) clearInterval(dashboardState.selectedInterval);
  if (!dashboardState.currentTicker) return;
  const intervalMs = dashboardState.range === "30s" ? 5_000 : 30_000;
  dashboardState.selectedInterval = setInterval(() => {
    void refreshSelectedMarket(false);
  }, intervalMs);
}

async function refreshDashboard() {
  if (dashboardState.refreshing) return;
  dashboardState.refreshing = true;
  const refreshButton = document.querySelector("#refresh-button");
  if (refreshButton) refreshButton.disabled = true;
  setStatus("Loading open demo events and public orderbooks…");

  try {
    const { events, truncated } = await loadOpenEvents();
    const models = eventMarketModels(events);
    const allTickers = models.flatMap((model) => model.markets.map((market) => market.ticker));
    const { orderbooksByTicker, errors, requestedCount } = await loadOrderbooks(allTickers);

    dashboardState.models = models;
    dashboardState.orderbooksByTicker = orderbooksByTicker;
    dashboardState.truncated = truncated;

    const selectedTopic = document.body.dataset.topic || "all";
    renderTopicTabs(models, selectedTopic);
    renderEventRows(models, orderbooksByTicker, selectedTopic);
    updateStats(models, orderbooksByTicker);

    const visibleModels = getVisibleModels(models, selectedTopic);
    dashboardState.marketOptions = fillMarketSelector(visibleModels) ?? [];
    const select = document.querySelector("#market-select");
    if (select) {
      dashboardState.currentTicker = select.value;
      select.onchange = () => updateSelectedTicker(select.value);
    }
    if (!dashboardState.currentTicker && dashboardState.marketOptions.length) {
      dashboardState.currentTicker = dashboardState.marketOptions[0].ticker;
    }

    if (dashboardState.currentTicker) {
      if (!dashboardState.marketOptions.some((option) => option.ticker === dashboardState.currentTicker)) {
        dashboardState.currentTicker = dashboardState.marketOptions[0]?.ticker ?? "";
      }
      updateMarketSummary(selectedOption(), selectedOption()?.market);
      void refreshSelectedMarket(true);
      startSelectedTimer();
    } else {
      updateMarketSummary(null, null);
      renderOrderbook(null);
      setEmptyChart("No open binary markets match this view.", "When a market is returned by Kalshi's demo API, the chart will appear here.");
    }

    const statusMessage = errors.length
      ? `Events loaded; orderbooks incomplete for some markets (${requestedCount - orderbooksByTicker.size} missing). Rankings with incomplete books are left blank.`
      : truncated
        ? `API connected; event pagination reached the ${MAX_EVENT_PAGES}-page safety cap. The list may be incomplete.`
        : `Demo API connected · ${events.length} open events checked · public data only · refreshes every ${Math.round(REFRESH_MS / 1000)}s`;
    setStatus(statusMessage, errors.length || truncated ? "error" : "ok");
    setLastUpdated();
  } catch (error) {
    setStatus(`Live demo data unavailable: ${error.message}. No sample values are shown.`, "error");
    const body = document.querySelector("#events-table-body");
    if (body) {
      body.innerHTML = `<tr><td class="empty-cell" colspan="7"><strong>No live values loaded.</strong>${escapeHtml(error.message)} <a href="${EVENT_DOCS}" target="_blank" rel="noopener noreferrer">Official events API docs ↗</a></td></tr>`;
    }
  } finally {
    dashboardState.refreshing = false;
    if (refreshButton) refreshButton.disabled = false;
  }
}

function attachDashboardInteractions() {
  const tableBody = document.querySelector("#events-table-body");
  if (tableBody) {
    tableBody.addEventListener("click", (event) => {
      const watchButton = event.target.closest("[data-watch]");
      if (watchButton) {
        event.stopPropagation();
        const model = dashboardState.models.find((item) => item.event.event_ticker === watchButton.dataset.watch);
        if (!model) return;
        const saved = toggleEventWatch(model);
        if (!saved) {
          setStatus("Browser storage is unavailable; the watchlist was not changed.", "error");
          return;
        }
        renderEventRows(dashboardState.models, dashboardState.orderbooksByTicker, document.body.dataset.topic || "all");
        setStatus(isEventTracked(model.event.event_ticker) ? "Event added to this browser's local watchlist." : "Event removed from this browser's local watchlist.", "ok");
        return;
      }
      if (event.target.closest("a")) return;
      const row = event.target.closest("tr[data-market-ticker]");
      if (row?.dataset.marketTicker) updateSelectedTicker(row.dataset.marketTicker);
    });
    tableBody.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const row = event.target.closest("tr[data-market-ticker]");
      if (!row?.dataset.marketTicker || event.target.closest("button, a")) return;
      event.preventDefault();
      updateSelectedTicker(row.dataset.marketTicker);
    });
  }

  document.querySelectorAll("[data-range]").forEach((button) => {
    button.addEventListener("click", () => {
      dashboardState.range = button.dataset.range;
      document.querySelectorAll("[data-range]").forEach((item) => item.classList.toggle("is-active", item === button));
      dashboardState.pricePoints = [];
      dashboardState.chartLastFetchedAt = 0;
      const caption = document.querySelector("#chart-caption");
      if (caption) caption.textContent = dashboardState.range === "30s"
        ? "Seconds view samples the public last-price field every 5 seconds while this page is open; the browser does not retain a server-side history."
        : `Historical chart uses Kalshi candlesticks. Available documented bars are 1 minute, 1 hour, or 1 day; ${["6h", "24h"].includes(dashboardState.range) ? "this view requests 1-hour bars" : "this view requests 1-minute bars"}.`;
      void refreshSelectedMarket(true);
      startSelectedTimer();
    });
  });

  document.querySelector("#refresh-button")?.addEventListener("click", () => void refreshDashboard());
}

function initDashboard() {
  attachDashboardInteractions();
  void refreshDashboard();
  dashboardState.interval = setInterval(() => void refreshDashboard(), REFRESH_MS);
}

export function resolutionForMarket(market) {
  const result = String(market?.result ?? "").toLowerCase();
  const status = String(market?.status ?? "").toLowerCase();
  if (result === "yes" || result === "no") {
    if (status === "finalized") return `Settled ${result.toUpperCase()}`;
    if (status === "disputed") return `Disputed · prior result ${result.toUpperCase()}`;
    if (status === "determined") return `Determined ${result.toUpperCase()} · settlement pending`;
    return `Result ${result.toUpperCase()} · status ${status || "not returned"}`;
  }
  if (result) return `Result: ${result} · status ${status || "not returned"}`;
  if (status === "finalized") return "Finalized · result not returned";
  return status ? `Pending · ${status}` : "Pending · result not returned";
}

async function fetchTrackedMarket(ticker) {
  const encoded = encodeURIComponent(ticker);
  try {
    const payload = await fetchJson(relativeApiPath(`/markets/${encoded}`));
    return { market: payload.market ?? payload, source: relativeApiPath(`/markets/${encoded}`) };
  } catch {
    const payload = await fetchJson(relativeApiPath(`/historical/markets/${encoded}`));
    return { market: payload.market ?? payload, source: relativeApiPath(`/historical/markets/${encoded}`) };
  }
}

async function refreshWatchlistPage() {
  const tbody = document.querySelector("#watchlist-table-body");
  if (!tbody) return;
  const watchlist = getWatchlist();
  const count = document.querySelector("#watchlist-count");
  if (count) count.textContent = String(watchlist.length);
  if (!watchlist.length) {
    tbody.innerHTML = `<tr><td class="empty-cell" colspan="6"><strong>No events in this browser's watchlist yet.</strong>On a category dashboard, select “Track” beside an event. This list is stored only in this browser. <a href="${EVENT_DOCS}" target="_blank" rel="noopener noreferrer">Official events API docs ↗</a></td></tr>`;
    return;
  }

  const saved = watchlist.map(async (entry) => {
    const tickers = Array.isArray(entry.market_tickers) ? entry.market_tickers : [];
    const marketResults = await Promise.all(tickers.map(async (ticker) => {
      try {
        return await fetchTrackedMarket(ticker);
      } catch (error) {
        return { market: { ticker, status: "unavailable", result: "" }, source: "", error: error.message };
      }
    }));
    return { entry, marketResults };
  });

  const resolvedEvents = await Promise.all(saved);
  tbody.innerHTML = resolvedEvents.map(({ entry, marketResults }) => {
    const outcomes = marketResults.map(({ market, source, error }) => {
      const result = resolutionForMarket(market);
      const status = String(market?.status ?? "").toLowerCase();
      const hasBinaryResult = ["yes", "no"].includes(String(market?.result ?? "").toLowerCase());
      const badgeClass = error || status === "disputed" ? "badge-flag" : status === "finalized" ? "badge-live" : hasBinaryResult ? "badge-wait" : "badge-muted";
      const isProvisionalListing = market?.is_provisional === true;
      const sourceLink = source ? `<a class="source-link" href="${escapeHtml(source)}" target="_blank" rel="noopener noreferrer">Market API ↗</a>` : "";
      return `<li><span class="ticker">${escapeHtml(market?.ticker ?? "—")}</span> <span class="badge ${badgeClass}">${escapeHtml(result)}</span>${isProvisionalListing ? ' <span class="badge badge-wait" title="Kalshi marks this market record as provisional">Provisional listing</span>' : ""}${market?.settlement_ts ? `<span class="table-subtitle">Settlement timestamp ${escapeHtml(formatTimestamp(market.settlement_ts))}</span>` : ""}${error ? `<span class="table-subtitle">${escapeHtml(error)}</span>` : ""} ${sourceLink}</li>`;
    }).join("");
    const sources = marketResults.map((item) => item.source).filter(Boolean);
    const sourceHref = relativeApiPath(`/events/${encodeURIComponent(entry.event_ticker)}?with_nested_markets=true`);
    const topics = topicPills(Array.isArray(entry.topics) ? entry.topics : []);
    const title = entry.title || entry.event_ticker;
    const firstMarket = marketResults[0]?.market;
    const allFinalized = marketResults.length > 0 && marketResults.every((item) => String(item.market?.status ?? "").toLowerCase() === "finalized");
    const allHaveResults = marketResults.length > 0 && marketResults.every((item) => Boolean(item.market?.result));
    const checkedResult = allFinalized ? "All markets finalized" : allHaveResults ? "Results posted · settlement status varies" : "Awaiting result";
    return `<tr>
      <td><span class="table-title">${escapeHtml(title)}</span><span class="table-subtitle">${escapeHtml(entry.event_ticker)}</span></td>
      <td>${topics}</td>
      <td>${marketResults.length ? `<details><summary>${marketResults.length} market${marketResults.length === 1 ? "" : "s"} · ${escapeHtml(checkedResult)}</summary><ul class="outcome-list">${outcomes}</ul></details>` : "—"}</td>
      <td><span class="badge badge-muted">${escapeHtml(firstMarket?.status ?? "unavailable")}</span></td>
      <td>${escapeHtml(formatTimestamp(entry.added_at))}</td>
      <td><a class="source-link" href="${escapeHtml(sourceHref)}" target="_blank" rel="noopener noreferrer">Event API ↗</a>${sources.length ? `<a class="source-link" href="${escapeHtml(sources[0])}" target="_blank" rel="noopener noreferrer">Market data ↗</a>` : ""} <button class="button button-small button-link" type="button" data-unwatch="${escapeHtml(entry.event_ticker)}">Stop tracking</button></td>
    </tr>`;
  }).join("");
  const checked = document.querySelector("#watchlist-last-checked");
  if (checked) checked.textContent = `Checked ${formatTimestamp(new Date().toISOString())}`;
}

function initWatchlist() {
  document.querySelector("#watchlist-refresh")?.addEventListener("click", () => void refreshWatchlistPage());
  document.querySelector("#watchlist-table-body")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-unwatch]");
    if (!button) return;
    const remaining = getWatchlist().filter((item) => item.event_ticker !== button.dataset.unwatch);
    if (setWatchlist(remaining)) void refreshWatchlistPage();
  });
  void refreshWatchlistPage();
  setInterval(() => void refreshWatchlistPage(), REFRESH_MS);
}

function initSuggestions() {
  const selectionLabel = document.querySelector("#suggestion-selection-status");
  const key = "kalshi-demo-selected-suggestions-v1";
  let selected = [];
  try { selected = JSON.parse(localStorage.getItem(key) ?? "[]"); } catch { selected = []; }
  if (!Array.isArray(selected)) selected = [];
  document.querySelectorAll("[data-suggestion-id]").forEach((card) => {
    const checkbox = card.querySelector("input[type=checkbox]");
    if (!checkbox) return;
    checkbox.checked = selected.includes(card.dataset.suggestionId);
    checkbox.addEventListener("change", () => {
      const ids = [...document.querySelectorAll("[data-suggestion-id] input[type=checkbox]:checked")]
        .map((input) => input.closest("[data-suggestion-id]")?.dataset.suggestionId).filter(Boolean);
      try { localStorage.setItem(key, JSON.stringify(ids)); } catch { /* selections remain usable until page refresh */ }
      if (selectionLabel) selectionLabel.textContent = `${ids.length} suggestion${ids.length === 1 ? "" : "s"} selected for review in this browser only. No code changes are applied.`;
    });
  });
  if (selectionLabel) selectionLabel.textContent = `${selected.length} suggestion${selected.length === 1 ? "" : "s"} selected for review in this browser only. No code changes are applied.`;
}

function init() {
  const view = document.body.dataset.view;
  if (view === "dashboard" || view === "category") initDashboard();
  if (view === "watchlist") initWatchlist();
  if (view === "suggestions") initSuggestions();
}

if (typeof document !== "undefined") init();
