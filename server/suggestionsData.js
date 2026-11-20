// Suggestion catalog served to the site. Mirrors docs/SUGGESTIONS.md.
// Each item is PROPOSED for review; nothing is auto-applied.
export const SUGGESTIONS = [
  {
    id: 'S1',
    title: 'Make the ranking metric explicit and switchable',
    priority: 'High',
    category: 'Metrics',
    detail:
      'Compute notional = price x volume, label it clearly, and toggle ranking by volume, notional, or open interest. Never present a computed number as an official field.',
    source: 'https://docs.kalshi.com/api-reference/market/get-market-candlesticks',
    status: 'proposed',
  },
  {
    id: 'S2',
    title: 'Separate verified vs live/estimated values visually',
    priority: 'High',
    category: 'Data quality',
    detail:
      'Add a per-row badge: verified (official field), computed (derived), or stale (REST cache). Show a data-freshness indicator and last-fetch timestamp.',
    source: 'https://docs.kalshi.com/api-reference/market/get-markets',
    status: 'proposed',
  },
  {
    id: 'S3',
    title: 'Add a reviewed category whitelist for the five topics',
    priority: 'High',
    category: 'Coverage',
    detail:
      'Discover candidate series per topic, store them as reviewable data, and filter strictly by the whitelist. Flag fuzzy title matches.',
    source: 'https://docs.kalshi.com/api-reference/market/get-series',
    status: 'proposed',
  },
  {
    id: 'S4',
    title: 'Add settlement outcome capture with explicit confirmation',
    priority: 'High',
    category: 'Tracking',
    detail:
      'Record event_ticker, status, close_ts, settled_ts, and outcome; mark the outcome unverified until confirmed against a live settled market.',
    source: 'https://docs.kalshi.com/getting_started/market_settlement',
    status: 'proposed',
  },
  {
    id: 'S5',
    title: 'Build the price chart from verified granularity',
    priority: 'High',
    category: 'Chart',
    detail:
      'Ship minutes/hours/days from candlesticks (verified). Provide a seconds view only if the WS trade tick cadence is confirmed; else label seconds unsupported.',
    source: 'https://docs.kalshi.com/api-reference/market/get-market-candlesticks',
    status: 'proposed',
  },
  {
    id: 'S6',
    title: 'Liquidity: add cumulative depth and spread',
    priority: 'Medium',
    category: 'Liquidity',
    detail:
      'Show per-level counts (yes/no), cumulative depth, and best-bid/best-ask spread. Use the binary equivalence (yes bid X = no ask 100-X).',
    source: 'https://docs.kalshi.com/api-reference/market/get-market-orderbook',
    status: 'proposed',
  },
  {
    id: 'S7',
    title: 'Portfolio: add P&L by category and by strategy',
    priority: 'Medium',
    category: 'Portfolio',
    detail:
      'Compute realized/unrealized P&L per trade, then aggregate by topic, direction, and horizon. Present strategy candidates in Suggestions for review.',
    source: 'https://docs.kalshi.com/llms.txt',
    status: 'proposed',
  },
  {
    id: 'S8',
    title: 'Add a decision-log / review workflow',
    priority: 'Medium',
    category: 'Workflow',
    detail:
      'Give each suggestion a status (proposed -> reviewing -> accepted -> implemented) and a decision note. Persist decisions so the site reflects chosen direction.',
    source: 'Project requirement',
    status: 'proposed',
  },
  {
    id: 'S9',
    title: 'Add alerting on thresholds',
    priority: 'Medium',
    category: 'Alerts',
    detail:
      'Allow threshold alerts on price movement, liquidity depth, and volume. Use WS ticker/trade when available; REST polling fallback otherwise.',
    source: 'https://docs.kalshi.com/websockets/websocket-connection',
    status: 'proposed',
  },
  {
    id: 'S10',
    title: 'Robust error handling and connectivity status',
    priority: 'High',
    category: 'Reliability',
    detail:
      'Always show connection status, last error, and retry with exponential backoff. Mark unavailable rows as unverified/unavailable with a reason.',
    source: 'https://docs.kalshi.com/getting_started/rate_limits',
    status: 'proposed',
  },
  {
    id: 'S11',
    title: 'Persist the tracking store',
    priority: 'Medium',
    category: 'Persistence',
    detail:
      'Persist tracking state (watched events, trades, snapshots) to a local store and reload on startup so the dashboard is resumable.',
    source: 'Project requirement',
    status: 'proposed',
  },
  {
    id: 'S12',
    title: 'Accessibility & responsiveness',
    priority: 'Low',
    category: 'UX',
    detail:
      'Ensure keyboard navigation, readable contrast, responsive tables, and per-row source links. Keep tables as the primary read format.',
    source: 'Project requirement',
    status: 'proposed',
  },
];

// Items that are flagged/unverified. Mirrors docs/VERIFICATION.md.
export const FLAGGED = [
  {
    id: 'FLAG-01',
    title: 'Sandbox cannot reach Kalshi demo API',
    detail:
      'Outbound access is allowlisted and excludes kalshi.co. A curl to the demo exchange/status endpoint fails with a TLS reset. Live data is implemented but unverified from this sandbox.',
    status: 'open',
    source: 'https://docs.kalshi.com/getting_started/demo_env',
  },
  {
    id: 'FLAG-02',
    title: 'No Kalshi demo API key present',
    detail:
      'Trade execution and authenticated portfolio reads are implemented but cannot be exercised without a demo account key pair. Keys are never committed.',
    status: 'open',
    source: 'https://docs.kalshi.com/getting_started/api_keys',
  },
  {
    id: 'FLAG-03',
    title: 'GitHub Pages is a static host',
    detail:
      'Pages cannot run a persistent authenticated backend or hold secrets. The static site uses public market-data calls; the backend provides authenticated portfolio/trade features.',
    status: 'open',
    source: 'https://docs.kalshi.com/getting_started/quick_start_market_data',
  },
  {
    id: 'FLAG-04',
    title: 'Category-to-topic mapping is unverified',
    detail:
      'The exact series/category mapping to gas, elections, culture, crypto, and golf is not confirmed from an official enumeration. Filtering uses a reviewable keyword mapping.',
    status: 'open',
    source: 'https://docs.kalshi.com/api-reference/market/get-series',
  },
  {
    id: 'FLAG-05',
    title: 'Settled-outcome payload fields unverified',
    detail:
      'The exact field names for a resolved yes/no outcome were not fully enumerated on the pages fetched. Outcome cells are marked unverified until confirmed from a live settled market.',
    status: 'open',
    source: 'https://docs.kalshi.com/getting_started/market_settlement',
  },
];
