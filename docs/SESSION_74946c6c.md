# Executive summary and scoped audit — 21 November 2026

## Executive summary

The repository already implements a static Kalshi demo dashboard, five category
pages (gas prices, elections, culture, crypto, golf), selectable time-window price
charts, orderbook depth, two scrolling alert feeds for movements of at least $0.10,
resolution reports and an hourly credential-free paper-trading workflow.
Use the [dashboard](https://karagemop466-tech.github.io/Demo2/),
[alerts](https://karagemop466-tech.github.io/Demo2/alerts.html) and
[portfolio](https://karagemop466-tech.github.io/Demo2/pages/portfolio.html).
These are existing features, not all newly built or independently live-tested this session.

**Not complete:** authenticated demo-account balances, positions and actual order
execution have not been verified. The committed portfolio explicitly says
`authenticated: false`; no exchange order was submitted this session. A public
static site must not collect private keys. “High ROI” is a disclosed heuristic,
not a validated expected-return model. No news item has been verified as the
cause of a specific jump. Dollar turnover estimates are not observed turnover.

## Official-source checks performed this session

| Item | Confirmed fact | Official source |
|---|---|---|
| Environment | Demo uses mock funds, separate credentials; behavior may differ from real markets. Recommended and alternate endpoints match the supplied URLs. | https://docs.kalshi.com/getting_started/demo_env |
| Prices and results | Market schema includes dollar quotes, contract volume, open interest and result. These are different quantities. | https://docs.kalshi.com/api-reference/market/get-markets |
| Depth | Orderbook response contains `orderbook_fp.yes_dollars` and `no_dollars` price/count pairs; depth can be 0 (all) or 1–100. | https://docs.kalshi.com/api-reference/market/get-market-orderbook |
| Trades | Trade history route is `GET /markets/trades?ticker=…`, with cursor pagination. | https://docs.kalshi.com/api-reference/market/get-trades |
| Orders | Documented V2 creation route is `POST /portfolio/events/orders` with bid/ask side and fixed-point price/count. | https://docs.kalshi.com/api-reference/orders/create-order-v2 |
| Streaming | WebSocket handshake requires API-key authentication. | https://docs.kalshi.com/websockets/websocket-connection |

Verification above means documentation was fetched and relevant schema/examples
read; it does not mean a full authenticated integration test or re-verification
of every line of every legacy dashboard. Historical stored API snapshots have not
been recollected from this restricted sandbox. Their timestamps remain unchanged.

## Fixed in this session

`tools/paper_trade.py` formerly substituted entry cost and zero unrealized P&L
when a bid was absent. It now emits JSON null for missing, nonfinite or invalid
marks, and null aggregate equity/unrealized P&L if any position cannot be priced.
Cash, recorded costs and settled gross P&L remain available. A genuinely reported
zero bid is retained. The definitions migrate on every run, including old ledgers.
Tests cover missing, blank, NaN, infinity, out-of-range and explicit zero quotes.
This is a project valuation policy, not a Kalshi-calculated account balance.

## Flagged for Review

| ID | Finding / remaining limitation | Action | Official reference |
|---|---|---|---|
| A1 | `server/kalshiClient.js` uses `/orders` and ticker-scoped trades, inconsistent with the current documented routes. Existing legacy summary overstates backend readiness. | Do not enable this alternative backend until independently repaired and schema-tested. Owner request recorded in COORDINATION.md. Canonical Python executor is separate. | https://docs.kalshi.com/api-reference/orders/create-order-v2 ; https://docs.kalshi.com/api-reference/market/get-trades |
| A2 | Stored portfolio says authentication is not configured. | Leave account performance unverified; never confuse paper results with account results. | https://docs.kalshi.com/websockets/websocket-connection |
| A3 | Alert watchlist is sampled (top 12 per topic), polling can miss reverted swings; heuristic score is not ROI. | Show watch coverage and sampling age; validate models out of sample before labeling expected returns. | https://docs.kalshi.com/api-reference/market/get-markets |
| A4 | Missing bids formerly produced invented paper valuations. | Fixed prospectively; historical stored equity points are not retrospectively verified or rewritten. | https://docs.kalshi.com/api-reference/market/get-market-orderbook |
| A5 | Simulation assumes quoted fills; does not model fees, depth constraints, slippage or partial fills. | Treat P&L as gross illustrative simulation, not executable performance. | https://docs.kalshi.com/api-reference/market/get-market-orderbook |
| A6 | No independently verified causal news attribution. | Keep cause blank. Settlement-source links do not establish causation. | https://docs.kalshi.com/api-reference/market/get-trades |

## Prioritized improvements (proposals, not verified capabilities)

1. Run one secured server-side WebSocket collector with durable sequence-aware
   storage; expose only public sanitized ticks to Pages through a hosted relay.
2. Consolidate the many preserved dashboard variants into one navigation and one
   timestamped dataset after coordination with their owners.
3. Simulate fills against observed depth and track conservative execution costs;
   evaluate momentum, mean reversion, longshot and favorite strategies separately.
4. Show source/observation age and watchlist coverage beside every alert; distinguish
   quote changes from trade prints and finalized settlement from provisional result.
5. Add timestamped official-source news annotations as context, never automatic
   claims of cause, and retain blank values where evidence is absent.

## Checks

- Paper-trading regression: 40 assertions passed (offline synthetic fixtures).
- Node app suite: 8 tests passed.
- Initial repository internal-link check: 10,673 references, 124 HTML files passed.
- PR, final verification and deployment record: see COORDINATION.md session 74946c6c.
