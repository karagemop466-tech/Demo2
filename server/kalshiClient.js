// Kalshi REST client with Ed25519/RSA request signing.
// Signing scheme is verified from the official docs:
// https://docs.kalshi.com/getting_started/api_keys
//   - Headers: KALSHI-ACCESS-KEY (Key ID), KALSHI-ACCESS-TIMESTAMP (ms),
//     KALSHI-ACCESS-SIGNATURE (base64 of sign(timestamp + method + path)).
//   - Path is signed WITHOUT the query string.
//   - Ed25519 signs the message directly; RSA uses RSA-PSS with SHA-256,
//     salt length = digest length.
import { createPrivateKey, sign as cryptoSign, constants, randomUUID } from 'crypto';

export class KalshiError extends Error {
  constructor(message, { status, body } = {}) {
    super(message);
    this.name = 'KalshiError';
    this.status = status;
    this.body = body;
  }
}

function signText(privateKeyPem, text) {
  const key = createPrivateKey(privateKeyPem);
  const message = Buffer.from(text, 'utf8');
  if (key.asymmetricKeyType === 'ed25519') {
    return cryptoSign(null, message, key);
  }
  // RSA-PSS with SHA-256, salt length = digest length (32).
  return cryptoSign('rsa-pss', message, {
    key,
    padding: constants.RSA_PSS_PADDING,
    saltLength: 32,
    digest: 'sha256',
  });
}

export function buildCreateOrderV2Payload(input = {}) {
  const ticker = String(input.ticker || input.market_ticker || '').trim();
  if (!ticker) {
    throw new KalshiError('ticker is required for Create Order V2', { status: 400 });
  }
  const rawSide = String(input.side || '').toLowerCase();
  const action = String(input.action || 'buy').toLowerCase();
  let bookSide;
  if (rawSide === 'bid' || rawSide === 'ask') {
    bookSide = rawSide;
  } else if (rawSide === 'yes' || rawSide === 'no') {
    if (action === 'sell') {
      bookSide = rawSide === 'yes' ? 'ask' : 'bid';
    } else {
      bookSide = rawSide === 'yes' ? 'bid' : 'ask';
    }
  } else {
    throw new KalshiError(`Invalid order side: ${input.side}`, { status: 400 });
  }
  const countNum = Number(input.count);
  if (!Number.isFinite(countNum) || countNum <= 0) {
    throw new KalshiError(`Invalid order count: ${input.count}`, { status: 400 });
  }
  const priceNum = Number(input.price ?? input.price_dollars);
  if (!Number.isFinite(priceNum) || priceNum <= 0 || priceNum >= 1) {
    throw new KalshiError(`Invalid order price (must be in (0, 1) dollars): ${input.price ?? input.price_dollars}`, { status: 400 });
  }
  const tifMap = {
    gtc: 'good_till_canceled',
    good_till_canceled: 'good_till_canceled',
    ioc: 'immediate_or_cancel',
    immediate_or_cancel: 'immediate_or_cancel',
    fok: 'fill_or_kill',
    fill_or_kill: 'fill_or_kill',
  };
  const tifKey = String(input.time_in_force || input.type || 'good_till_canceled').toLowerCase();
  const timeInForce = tifMap[tifKey] || 'good_till_canceled';
  const stp = input.self_trade_prevention_type === 'maker' ? 'maker' : 'taker_at_cross';
  return {
    ticker,
    client_order_id: String(input.client_order_id || randomUUID()),
    side: bookSide,
    count: countNum.toFixed(2),
    price: priceNum.toFixed(4),
    time_in_force: timeInForce,
    self_trade_prevention_type: stp,
  };
}

export class KalshiClient {
  constructor({ baseUrl, keyId, privateKeyPem, enabled, fetchImpl } = {}) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.keyId = keyId;
    this.privateKeyPem = privateKeyPem;
    this.enabled = enabled && Boolean(keyId) && Boolean(privateKeyPem);
    this.fetchImpl = fetchImpl || globalThis.fetch;
  }

  _authHeaders(method, pathWithoutQuery) {
    if (!this.enabled) return {};
    const timestamp = String(Date.now());
    const msg = timestamp + method + pathWithoutQuery;
    const signature = signText(this.privateKeyPem, msg).toString('base64');
    return {
      'KALSHI-ACCESS-KEY': this.keyId,
      'KALSHI-ACCESS-TIMESTAMP': timestamp,
      'KALSHI-ACCESS-SIGNATURE': signature,
    };
  }

  async request(method, path, { query, body, auth = true, timeoutMs = 20000 } = {}) {
    const url = new URL(this.baseUrl + path);
    if (query) {
      for (const [k, v] of Object.entries(query)) {
        if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
      }
    }
    // Signing message uses full API pathname without query string (e.g. /trade-api/v2/portfolio/events/orders).
    const pathWithoutQuery = url.pathname;
    const headers = { Accept: 'application/json' };
    const ah = auth ? this._authHeaders(method, pathWithoutQuery) : {};
    Object.assign(headers, ah);
    let payload;
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      payload = JSON.stringify(body);
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let res;
    try {
      res = await this.fetchImpl(url, {
        method,
        headers,
        body: payload,
        signal: controller.signal,
      });
    } catch (err) {
      clearTimeout(timer);
      throw new KalshiError(`Network error calling Kalshi: ${err.message}`, {
        status: 0,
        body: { error: err.message },
      });
    }
    clearTimeout(timer);
    const text = await res.text();
    let json = null;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = { raw: text };
    }
    if (!res.ok) {
      const code = json && json.code;
      throw new KalshiError(
        `Kalshi ${method} ${path} failed: ${res.status} ${code || res.statusText}`,
        { status: res.status, body: json },
      );
    }
    return json;
  }

  // --- Public market data (no authentication required) ---
  getExchangeStatus() {
    return this.request('GET', '/exchange/status', { auth: false });
  }

  getEvents({ status, withNestedMarkets, limit, cursor, seriesTicker, minUpdatedTs } = {}) {
    return this.request('GET', '/events', {
      auth: false,
      query: {
        status,
        with_nested_markets: withNestedMarkets ? 'true' : undefined,
        limit,
        cursor,
        series_ticker: seriesTicker,
        min_updated_ts: minUpdatedTs,
      },
    });
  }

  async getAllEvents({
    status,
    withNestedMarkets = true,
    limit = 200,
    maxPages = 25,
    seriesTicker,
    minUpdatedTs,
  } = {}) {
    const seen = new Set();
    const events = [];
    let cursor;
    let pagesFetched = 0;
    let truncated = false;
    while (pagesFetched < maxPages) {
      const page = await this.getEvents({
        status,
        withNestedMarkets,
        limit,
        cursor,
        seriesTicker,
        minUpdatedTs,
      });
      pagesFetched++;
      for (const ev of page?.events || []) {
        if (!ev?.event_ticker || seen.has(ev.event_ticker)) continue;
        seen.add(ev.event_ticker);
        events.push(ev);
      }
      const nextCursor = page?.cursor;
      if (!nextCursor || nextCursor === cursor) break;
      cursor = nextCursor;
      if (pagesFetched >= maxPages) {
        truncated = true;
      }
    }
    return { events, pagesFetched, truncated };
  }

  getMarkets({ seriesTicker, status, eventTicker, limit, cursor } = {}) {
    return this.request('GET', '/markets', {
      auth: false,
      query: {
        series_ticker: seriesTicker,
        status,
        event_ticker: eventTicker,
        limit,
        cursor,
      },
    });
  }

  getMarket(ticker) {
    return this.request('GET', `/markets/${encodeURIComponent(ticker)}`, { auth: false });
  }

  getOrderbook(ticker, depth) {
    return this.request('GET', `/markets/${encodeURIComponent(ticker)}/orderbook`, {
      auth: false,
      query: { depth },
    });
  }

  getTrades(ticker, limit) {
    return this.request('GET', `/markets/${encodeURIComponent(ticker)}/trades`, {
      auth: false,
      query: { limit },
    });
  }

  getCandlesticks(seriesTicker, ticker, { startTs, endTs, periodInterval } = {}) {
    return this.request(
      'GET',
      `/series/${encodeURIComponent(seriesTicker)}/markets/${encodeURIComponent(ticker)}/candlesticks`,
      {
        auth: false,
        query: { start_ts: startTs, end_ts: endTs, period_interval: periodInterval },
      },
    );
  }

  getSeries(seriesTicker) {
    return this.request('GET', `/series/${encodeURIComponent(seriesTicker)}`, { auth: false });
  }

  // --- Authenticated portfolio / orders ---
  getPortfolioBalance(subaccount) {
    return this.request('GET', '/portfolio/balance', { auth: true, query: { subaccount } });
  }

  getPortfolioPositions(subaccount) {
    return this.request('GET', '/portfolio/positions', { auth: true, query: { subaccount } });
  }

  getOrders({ status, marketTicker, limit, cursor } = {}) {
    return this.request('GET', '/portfolio/orders', {
      auth: true,
      query: { status, ticker: marketTicker, limit, cursor },
    });
  }

  createOrder(order) {
    const body = buildCreateOrderV2Payload(order);
    return this.request('POST', '/portfolio/events/orders', { auth: true, body });
  }

  cancelOrder({ orderId, marketTicker }) {
    if (!orderId || !marketTicker) {
      throw new KalshiError('orderId and marketTicker are required for Cancel Order V2', { status: 400 });
    }
    return this.request('DELETE', `/portfolio/events/orders/${encodeURIComponent(orderId)}`, {
      auth: true,
      query: { market_ticker: marketTicker },
    });
  }
}
