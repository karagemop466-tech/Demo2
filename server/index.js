// Kalshi demo dashboard backend.
// Serves the static dashboard (site/) and a JSON API + WebSocket hub.
// Kalshi endpoints/signing are verified from docs.kalshi.com (see COORDINATION.md).
import express from 'express';
import http from 'http';
import path from 'path';
import { fileURLToPath } from 'url';
import { WebSocketServer, WebSocket } from 'ws';
import { KALSHI, AUTH, TOPICS, PORT } from './config.js';
import { KalshiClient, KalshiError } from './kalshiClient.js';
import { store } from './store.js';
import { categorizeTopic, classifyTrade, aggregatePerformance, suggestStrategies } from './strategies.js';
import { SUGGESTIONS, FLAGGED } from './suggestionsData.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');

const client = new KalshiClient({
  baseUrl: KALSHI.restBaseUrl,
  keyId: AUTH.keyId,
  privateKeyPem: AUTH.privateKeyPem,
  enabled: AUTH.enabled,
});

const app = express();
app.use(express.json({ limit: '1mb' }));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function num(v) {
  const n = typeof v === 'number' ? v : parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

function normalizeMarket(m) {
  const price = num(m.yes_bid_dollars ?? m.yes_bid) ?? 0;
  const volume = num(m.volume_fp ?? m.volume) ?? 0;
  const notional = price * volume;
  return {
    ticker: m.ticker,
    event_ticker: m.event_ticker,
    title: m.title,
    status: m.status,
    yes_bid: num(m.yes_bid_dollars ?? m.yes_bid),
    yes_ask: num(m.yes_ask_dollars ?? m.yes_ask),
    last_price: num(m.last_price_dollars ?? m.last_price ?? price),
    volume: volume,
    notional: Math.round(notional * 100) / 100,
    close_ts: m.close_ts,
    settled_ts: m.settled_ts,
    outcome: m.result || m.outcome || null,
    series_ticker: m.series_ticker,
  };
}

// Discover the best-known topic for an event by scanning its title/markets.
function topicForEvent(event) {
  const text = [event.title, event.sub_title, event.category,
    ...(event.markets || []).map((m) => m.title || ''),
  ].filter(Boolean).join(' ');
  return categorizeTopic(text);
}

// ---------------------------------------------------------------------------
// Status / connectivity
// ---------------------------------------------------------------------------
app.get('/api/status', async (_req, res) => {
  res.json({
    baseUrl: KALSHI.restBaseUrl,
    wsBaseUrl: KALSHI.wsBaseUrl,
    topics: TOPICS,
    authEnabled: client.enabled,
    connectivity: 'unchecked',
    pollIntervalMs: KALSHI.pollIntervalMs,
  });
});

app.get('/api/health', async (_req, res) => {
  let ok = false;
  let detail = 'unchecked';
  try {
    const r = await client.getExchangeStatus();
    ok = true;
    detail = r?.status || (r?.exchange && r.exchange.status) || 'ok';
  } catch (err) {
    detail = err instanceof KalshiError ? `unreachable: ${err.message}` : String(err.message || err);
  }
  res.json({ reachable: ok, detail, ts: new Date().toISOString() });
});

// ---------------------------------------------------------------------------
// Events (public, filtered to the five topics, ranked by estimated notional)
// ---------------------------------------------------------------------------
app.get('/api/events', async (req, res) => {
  try {
    const status = req.query.status === 'settled' ? 'settled' : 'open';
    const data = await client.getEvents({
      status,
      withNestedMarkets: true,
      limit: 200,
      minUpdatedTs: req.query.min_updated_ts ? Number(req.query.min_updated_ts) : undefined,
    });
    const events = (data?.events || [])
      .map((ev) => {
        const markets = (ev.markets || []).map(normalizeMarket);
        const topic = topicForEvent(ev);
        const notional = markets.reduce((a, m) => a + (m.notional || 0), 0);
        const volume = markets.reduce((a, m) => a + (m.volume || 0), 0);
        return {
          event_ticker: ev.event_ticker,
          title: ev.title,
          sub_title: ev.sub_title,
          series_ticker: ev.series_ticker,
          status: ev.status,
          topic,
          in_scope: TOPICS.includes(topic),
          notional: Math.round(notional * 100) / 100,
          volume: Math.round(volume),
          markets,
          close_ts: ev.strike_date || (markets[0] && markets[0].close_ts),
        };
      })
      .filter((ev) => ev.in_scope)
      .sort((a, b) => b.notional - a.notional);

    // Auto-track in-scope events so resolution is recorded until settled.
    for (const ev of events) {
      store.trackEvent({
        event_ticker: ev.event_ticker,
        title: ev.title,
        topic: ev.topic,
        status: ev.status,
        close_ts: ev.close_ts,
      });
    }
    res.json({ count: events.length, events });
  } catch (err) {
    res.status(502).json({ error: err.message, unverified: true });
  }
});

// ---------------------------------------------------------------------------
// Markets / orderbook / candlesticks (public)
// ---------------------------------------------------------------------------
app.get('/api/markets', async (req, res) => {
  try {
    const data = await client.getMarkets({
      seriesTicker: req.query.series_ticker,
      status: req.query.status,
      eventTicker: req.query.event_ticker,
      limit: Number(req.query.limit) || 200,
      cursor: req.query.cursor,
    });
    const markets = (data?.markets || []).map(normalizeMarket);
    res.json({ count: markets.length, cursor: data?.cursor || '', markets });
  } catch (err) {
    res.status(502).json({ error: err.message, unverified: true });
  }
});

app.get('/api/orderbook', async (req, res) => {
  try {
    const ticker = req.query.ticker;
    if (!ticker) return res.status(400).json({ error: 'ticker required' });
    const data = await client.getOrderbook(ticker, req.query.depth ? Number(req.query.depth) : undefined);
    const ob = data?.orderbook_fp || { yes_dollars: [], no_dollars: [] };
    const toLevels = (arr) =>
      (arr || [])
        .map((lvl) => ({
          price: num(lvl[0]),
          count: num(lvl[1]),
        }))
        .filter((l) => l.price !== null && l.count !== null);
    const yes = toLevels(ob.yes_dollars);
    const no = toLevels(ob.no_dollars);
    const bestYes = yes.length ? yes[yes.length - 1] : null; // best bid is last (ascending)
    const bestNo = no.length ? no[no.length - 1] : null;
    res.json({
      ticker,
      yes,
      no,
      best_yes_bid: bestYes,
      best_no_bid: bestNo,
      spread:
        bestYes && bestNo ? Math.round((100 - (bestNo.price + bestYes.price)) * 100) / 100 : null,
    });
  } catch (err) {
    res.status(502).json({ error: err.message, unverified: true });
  }
});

app.get('/api/candlesticks', async (req, res) => {
  try {
    const { series_ticker, ticker, period, hours } = req.query;
    if (!series_ticker || !ticker) return res.status(400).json({ error: 'series_ticker and ticker required' });
    // period is in minutes per official docs: 1, 60, 1440.
    const periodInterval = Number(period) || 60;
    const now = Math.floor(Date.now() / 1000);
    const span = periodInterval * 60 * Number(hours || 24);
    const data = await client.getCandlesticks(series_ticker, ticker, {
      startTs: now - span,
      endTs: now,
      periodInterval,
    });
    const candles = (data?.candlesticks || []).map((c) => ({
      ts: c.end_period_ts,
      price: num(c.price && (c.price.close_dollars ?? c.price.close)),
      yes_bid: num(c.yes_bid && c.yes_bid.close_dollars),
      yes_ask: num(c.yes_ask && c.yes_ask.close_dollars),
      volume: num(c.volume_fp),
      open_interest: num(c.open_interest_fp),
    }));
    res.json({ ticker, period_interval: periodInterval, candles });
  } catch (err) {
    res.status(502).json({ error: err.message, unverified: true });
  }
});

// ---------------------------------------------------------------------------
// Tracked events (resolution tracking)
// ---------------------------------------------------------------------------
app.get('/api/track/events', (_req, res) => {
  res.json({ events: store.listTrackedEvents() });
});

app.post('/api/track/events', (req, res) => {
  const { event_ticker, title, topic, status, close_ts, settled_ts, resolution } = req.body || {};
  if (!event_ticker) return res.status(400).json({ error: 'event_ticker required' });
  const updated = store.updateEvent(event_ticker, {
    title,
    topic,
    status,
    close_ts,
    settled_ts,
    resolution,
  }) || store.trackEvent({ event_ticker, title, topic, status, close_ts, settled_ts });
  res.json(updated);
});

// ---------------------------------------------------------------------------
// Portfolio & trades (authenticated)
// ---------------------------------------------------------------------------
app.get('/api/portfolio', async (_req, res) => {
  try {
    const balance = await client.getPortfolioBalance();
    const positions = await client.getPortfolioPositions();
    res.json({ balance, positions, source: KALSHI.restBaseUrl + '/portfolio/balance' });
  } catch (err) {
    res.status(client.enabled ? 502 : 401).json({
      error: err.message,
      unverified: true,
      authRequired: !client.enabled,
      note: client.enabled
        ? 'Kalshi call failed.'
        : 'No Kalshi API key configured; portfolio requires authentication.',
    });
  }
});

app.get('/api/trades/records', (_req, res) => {
  const trades = store.listTrades().map(classifyTrade);
  res.json({
    trades,
    performance: aggregatePerformance(trades),
    strategies: suggestStrategies(trades),
  });
});

app.post('/api/trades/execute', async (req, res) => {
  const { market_ticker, side, price, count, action } = req.body || {};
  if (!market_ticker || !side || !price || !count) {
    return res.status(400).json({ error: 'market_ticker, side, price, count required' });
  }
  if (!client.enabled) {
    return res.status(401).json({
      error: 'No Kalshi API key configured; trade execution requires authentication.',
      unverified: true,
    });
  }
  try {
    // V2 order shape: side is 'buy'/'sell', outcome_side 'yes'/'no', price in dollars.
    const order = {
      market_ticker,
      side: action === 'sell' ? 'sell' : 'buy',
      outcome_side: side === 'no' ? 'no' : 'yes',
      price_dollars: String(price),
      count: String(count),
      type: 'gtc',
    };
    const result = await client.createOrder(order);
    const trade = store.recordTrade({
      market_ticker,
      side,
      price,
      count,
      action,
      title: req.body.title || '',
      topic: categorizeTopic(`${req.body.title || ''} ${market_ticker}`),
      order_id: result?.order?.order_id || result?.order_id,
      status: result?.order?.status || 'submitted',
    });
    res.json({ ok: true, kalshi: result, trade });
  } catch (err) {
    res.status(502).json({ error: err.message, unverified: true });
  }
});

// ---------------------------------------------------------------------------
// Strategies & suggestions
// ---------------------------------------------------------------------------
app.get('/api/strategies', (_req, res) => {
  const trades = store.listTrades().map(classifyTrade);
  res.json({
    performance: aggregatePerformance(trades),
    strategies: suggestStrategies(trades),
    decisions: store.getSuggestionDecisions(),
  });
});

app.get('/api/suggestions', (_req, res) => {
  const decisions = store.getSuggestionDecisions();
  const items = SUGGESTIONS.map((s) => ({ ...s, ...(decisions.find((d) => d.id === s.id) || {}) }));
  res.json({ suggestions: items });
});

app.post('/api/suggestions/decision', (req, res) => {
  const { id, status, note, decidedBy } = req.body || {};
  if (!id || !status) return res.status(400).json({ error: 'id and status required' });
  const decision = store.upsertSuggestionDecision({ id, status, note, decidedBy });
  res.json(decision);
});

app.get('/api/flagged', (_req, res) => {
  res.json({ flags: FLAGGED });
});

// ---------------------------------------------------------------------------
// Serve the static dashboard
// ---------------------------------------------------------------------------
const siteDir = path.join(ROOT, 'site');
app.use(express.static(siteDir, { extensions: ['html'] }));

// ---------------------------------------------------------------------------
// WebSocket hub (browser <-> server) and optional Kalshi WS subscriber
// ---------------------------------------------------------------------------
const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);
  ws.send(JSON.stringify({ type: 'hello', ts: Date.now() }));
  ws.on('close', () => clients.delete(ws));
  ws.on('error', () => clients.delete(ws));
});

function broadcast(msg) {
  const data = JSON.stringify(msg);
  for (const ws of clients) {
    if (ws.readyState === WebSocket.OPEN) ws.send(data);
  }
}

// Poll Kalshi REST and broadcast price updates for tracked in-scope markets.
let pollTimer = null;
async function pollAndBroadcast() {
  try {
    const data = await client.getEvents({ status: 'open', withNestedMarkets: true, limit: 200 });
    const events = (data?.events || []).filter((ev) => TOPICS.includes(topicForEvent(ev)));
    for (const ev of events) {
      for (const m of ev.markets || []) {
        if (!m.ticker) continue;
        const price = num(m.yes_bid_dollars ?? m.yes_bid);
        if (price === null) continue;
        store.pushSnapshot({ ticker: m.ticker, price, topic: topicForEvent(ev) });
        broadcast({ type: 'price', ticker: m.ticker, price, event_ticker: ev.event_ticker, ts: Date.now() });
      }
    }
  } catch (err) {
    broadcast({ type: 'status', level: 'warn', message: `Kalshi poll failed: ${err.message}` });
  }
}

// Optional authenticated Kalshi WS subscriber. Requires a key AND egress.
async function startKalshiWs() {
  if (!client.enabled) return;
  try {
    const ws = new WebSocket(KALSHI.wsBaseUrl, {
      headers: client._authHeaders('GET', '/trade-api/ws/v2'),
    });
    let subId = 1;
    ws.on('open', () => {
      ws.send(JSON.stringify({ id: subId++, cmd: 'subscribe', params: { channels: ['ticker', 'orderbook_delta', 'market_lifecycle_v2'] } }));
    });
    ws.on('message', (raw) => {
      try {
        const msg = JSON.parse(raw.toString());
        broadcast({ type: 'kalshi', channel: msg.channel, data: msg });
      } catch {
        /* ignore */
      }
    });
    ws.on('error', (err) => broadcast({ type: 'status', level: 'warn', message: `Kalshi WS error: ${err.message}` }));
    ws.on('close', () => setTimeout(startKalshiWs, 10000));
  } catch (err) {
    broadcast({ type: 'status', level: 'warn', message: `Kalshi WS unavailable: ${err.message}` });
  }
}

function startPolling() {
  pollAndBroadcast();
  pollTimer = setInterval(pollAndBroadcast, KALSHI.pollIntervalMs);
}

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Kalshi demo dashboard backend on http://0.0.0.0:${PORT}`);
  console.log(`  Kalshi REST: ${KALSHI.restBaseUrl}`);
  console.log(`  Auth enabled: ${client.enabled}`);
  startPolling();
  startKalshiWs();
});

process.on('SIGTERM', () => {
  if (pollTimer) clearInterval(pollTimer);
  server.close();
});
