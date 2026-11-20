# COORDINATION.md — Shared Task Board

Current session ID: `92996116` (branch `arena/92996116-demo2`, base `35dc382` on `main`)

> This session is the sole active session in this checkout as of 2026-11-20.
> Any other session that starts must claim a non-overlapping scope here first,
> before editing any file.

## Task board

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| 1 | Repo review + line-by-line source verification | done | 92996116 | `pages/sources.html`, `pages/verification.html` |
| 2 | Executive summary | done | 92996116 | `pages/executive-summary.html` |
| 3 | Live dashboard: markets ranked by dollar amount | done | 92996116 | `index.html`, `assets/app.js` |
| 4 | Price chart with time-scale selector (sec/min/hr/day) | done | 92996116 | `assets/app.js` |
| 5 | Orderbook / liquidity depth table | done | 92996116 | `assets/app.js` |
| 6 | Resolution tracking (watchlist, yes/no outcome) | done | 92996116 | `assets/app.js` |
| 7 | Portfolio tracking via signed demo API | done | 92996116 | `pages/portfolio.html`, `assets/portfolio.js` |
| 8 | Trade execution (demo) + fill categorization + strategies | done | 92996116 | `assets/portfolio.js`, `pages/analysis.html` |
| 9 | Category subpages (gas/elections/culture/crypto/golf) | done | 92996116 | `pages/gas.html` … `pages/golf.html` |
| 10 | Suggestions review board | done | 92996116 | `pages/suggestions.html` |
| 11 | Questions / missing-information register | done | 92996116 | `pages/questions.html` |
| 12 | Flagged for Review page | done | 92996116 | `pages/flagged.html` |
| 13 | CI data snapshot (scheduled refresh) | done | 92996116 | `scripts/refresh-data.mjs`, `.github/workflows/refresh-data.yml` |
| 14 | Final integration + link check + PR + merge + Pages deploy | in progress | 92996116 | all |

## Claim record

- 2026-11-20 — session `92996116` claimed tasks 1–14 (whole repo scope, sole active session).
- Claimed scope: `index.html`, `assets/*`, `pages/*`, `scripts/*`, `data/*`,
  `.github/workflows/*`, `README.md`, `COORDINATION.md`.
- No other session holds a claim. No conflicts to resolve.

## Sources used (official only)

- https://docs.kalshi.com/getting_started/api_environments
- https://docs.kalshi.com/getting_started/demo_env
- https://docs.kalshi.com/getting_started/making_your_first_request
- https://docs.kalshi.com/getting_started/quick_start_market_data
- https://docs.kalshi.com/getting_started/quick_start_authenticated_requests
- https://docs.kalshi.com/getting_started/quick_start_create_order
- https://docs.kalshi.com/getting_started/quick_start_websockets
- https://docs.kalshi.com/getting_started/orderbook_responses
- https://docs.kalshi.com/getting_started/market_lifecycle
- https://docs.kalshi.com/getting_started/market_settlement
- https://docs.kalshi.com/getting_started/fixed_point_migration
- https://docs.kalshi.com/api-reference/market/get-markets
- https://docs.kalshi.com/api-reference/market/get-market-candlesticks
- https://docs.kalshi.com/api-reference/market/get-market-orderbook
- https://docs.kalshi.com/api-reference/market/get-series-list
- https://docs.kalshi.com/api-reference/events/get-events
- https://docs.kalshi.com/api-reference/portfolio/*
- https://docs.kalshi.com/api-reference/orders/create-order

## Verification performed

- Demo REST base `https://external-api.demo.kalshi.co/trade-api/v2` and WS
  `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` confirmed live (see
  `pages/sources.html` for the exact requests and timestamps).
- Live checks run 2026-11-20 against the demo API: `GET /markets?limit=2`,
  `GET /markets?status=settled&limit=1`,
  `GET /series/KXDEMOFUTHOURLY/markets/KXDEMOFUTHOURLY-26NOV20H11-UP/candlesticks?...&period_interval=1`,
  `GET /series?limit=200`, `GET /markets/{ticker}/orderbook`.
- Public endpoints need no authentication; portfolio/trading need signed API
  keys (RSA-PSS/SHA-256 or Ed25519, millisecond timestamp, 30 s tolerance).
- Sandbox shell egress to Kalshi is blocked (TLS `SSL_ERROR_SYSCALL`); the
  build environment therefore cannot verify browser CORS behaviour or execute
  authenticated calls. Live data is fetched client-side in the visitor's
  browser, and a CI job produces the committed snapshot.

## Irregularities / handoffs

- See `pages/flagged.html`. None block merge per instructions.
- No merge conflicts encountered.

## PR / deploy record

- PR: (pending)
- Merge result: (pending)
- Pages deploy: (pending)

## History (previous sessions)

- PR #1: https://github.com/karagemop466-tech/Demo2/pull/1 — MERGED
- PR #3: https://github.com/karagemop466-tech/Demo2/pull/3 — MERGED
- Pages: https://karagemop466-tech.github.io/Demo2/
