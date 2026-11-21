// Kalshi REST client with Ed25519/RSA request signing.
// Signing scheme is verified from the official docs:
// https://docs.kalshi.com/getting_started/api_keys
//   - Headers: KALSHI-ACCESS-KEY (Key ID), KALSHI-ACCESS-TIMESTAMP (ms),
//     KALSHI-ACCESS-SIGNATURE (base64 of sign(timestamp + method + path)).
//   - Path is signed WITHOUT the query string.
//   - Ed25519 signs the message directly; RSA uses RSA-PSS with SHA-256,
//     salt length = digest length.
import { createPrivateKey, sign as cryptoSign, constants } from 'crypto';

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
  return cryptoSign('sha256', message, {
    key,
    padding: constants.RSA_PKCS1_PSS_PADDING,
    saltLength: 32,
  });
}

export class KalshiClient {
  constructor({ baseUrl, keyId, privateKeyPem, enabled }) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.keyId = keyId;
    this.privateKeyPem = privateKeyPem;
    this.enabled = enabled && Boolean(keyId) && Boolean(privateKeyPem);
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
    // Authenticated requests must never send demo credentials to an arbitrary host.
    if (auth && this.enabled && (url.protocol !== 'https:' || url.port ||
        !['external-api.demo.kalshi.co', 'demo-api.kalshi.co'].includes(url.hostname))) {
      throw new KalshiError('Authenticated requests are restricted to official demo hosts');
    }
    if (auth && !this.enabled) throw new KalshiError('Demo authentication is not configured');
    // Kalshi signs the full URL path (including /trade-api/v2), not the query.
    const headers = { Accept: 'application/json' };
    const ah = auth ? this._authHeaders(method, url.pathname) : {};
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
      res = await fetch(url, {
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

  getEvents({ status, withNestedMarkets, limit, seriesTicker, minUpdatedTs } = {}) {
    return this.request('GET', '/events', {
      auth: false,
      query: {
        status,
        with_nested_markets: withNestedMarkets ? 'true' : undefined,
        limit,
        series_ticker: seriesTicker,
        min_updated_ts: minUpdatedTs,
      },
    });
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

  getOrders({ status, marketTicker, limit } = {}) {
    return this.request('GET', '/orders', {
      auth: true,
      query: { status, market_ticker: marketTicker, limit },
    });
  }

  // This low-level V2 client is not exposed through the public HTTP server.
  // Callers must provide the documented YES-book bid/ask V2 body explicitly.
  createOrder(order) {
    if (!order || typeof order.ticker !== 'string' || !order.ticker ||
        !['bid', 'ask'].includes(order.side) || typeof order.count !== 'string' ||
        typeof order.price !== 'string' || !order.time_in_force || !order.self_trade_prevention_type) {
      throw new KalshiError('Invalid V2 order body');
    }
    return this.request('POST', '/portfolio/events/orders', { auth: true, body: order });
  }

  cancelOrder({ orderId, marketTicker }) {
    return this.request('POST', '/orders/cancel', {
      auth: true,
      body: { order_id: orderId, market_ticker: marketTicker },
    });
  }
}
