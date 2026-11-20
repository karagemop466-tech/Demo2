// Central configuration for the Kalshi demo dashboard backend.
// All Kalshi values here are sourced from the official Kalshi API documentation:
//  - Demo environment & endpoints: https://docs.kalshi.com/getting_started/demo_env
//  - API keys & signing: https://docs.kalshi.com/getting_started/api_keys

export const KALSHI = {
  // Recommended demo REST base (also supported: https://demo-api.kalshi.co/trade-api/v2)
  restBaseUrl: process.env.KALSHI_REST_BASE_URL || 'https://external-api.demo.kalshi.co/trade-api/v2',
  // Recommended demo WebSocket host (also supported: wss://demo-api.kalshi.co/trade-api/ws/v2)
  wsBaseUrl:
    process.env.KALSHI_WS_BASE_URL || 'wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2',
  // Timestamp tolerance per official docs (ms is what we send; 30s window).
  timestampToleranceMs: 30 * 1000,
  // REST polling interval for near-real-time market data (REST is cached a few seconds).
  pollIntervalMs: Number(process.env.KALSHI_POLL_MS || 15000),
};

// Authentication. Keys MUST be supplied via environment variables and NEVER committed.
export const AUTH = {
  keyId: process.env.KALSHI_ACCESS_KEY || '',
  privateKeyPem: (process.env.KALSHI_PRIVATE_KEY || '').replace(/\\n/g, '\n'),
  // If no key is configured, only public (unauthenticated) endpoints are used.
  enabled: Boolean(process.env.KALSHI_ACCESS_KEY && process.env.KALSHI_PRIVATE_KEY),
};

// The five topics the dashboard focuses on (project requirement).
export const TOPICS = ['gas', 'elections', 'culture', 'crypto', 'golf'];

// Directory for persisted tracking state (gitignored).
export const DATA_DIR = process.env.DATA_DIR || '.data';
export const PORT = Number(process.env.PORT || 8080);
