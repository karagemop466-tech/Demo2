# Kalshi Demo — Executive Summary

**Review date:** 2026-11-20 (UTC). This summary distinguishes official API capabilities, checked-in implementation, and items not verified. It does not treat demo data as real-market evidence or claim that any price move was caused by a news story.

## Goal and scope

The repository contains a GitHub Pages site and supporting collectors for Kalshi **demo** market research, limited to five requested topic groupings: gas prices, elections, culture, crypto, and golf. It includes market/resolution snapshots, interactive price and orderbook views, portfolio/trade reporting scaffolding, dry-run execution, source records, and a Flagged for Review register.

The repository currently contains several independently built dashboard sections rather than one consolidated application. The root landing page links into these sections; their ranking metrics and degree of interactivity are not fully uniform. Treat the instrument-panel pages as the most recent data-driven research dashboard, not as proof that every separate subsite has identical behavior.

## Official Kalshi demo API

Kalshi documents these demo endpoints in [Test in the Demo Environment](https://docs.kalshi.com/getting_started/demo_env):

| Surface | Recommended demo endpoint | Also supported | Official source |
| --- | --- | --- | --- |
| REST Trade API | `https://external-api.demo.kalshi.co/trade-api/v2` | `https://demo-api.kalshi.co/trade-api/v2` | [Demo environment](https://docs.kalshi.com/getting_started/demo_env) |
| WebSocket API | `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` | `wss://demo-api.kalshi.co/trade-api/ws/v2` | [Demo environment](https://docs.kalshi.com/getting_started/demo_env) |

The demo uses mock funds, separate credentials from production, and Kalshi cautions that demo prices and behavior may not reflect real markets ([official demo guide](https://docs.kalshi.com/getting_started/demo_env)). The dashboard is research/testing software, not investment advice.

## What the code and site do

| Requirement | Current implementation / limit | Source or verification |
| --- | --- | --- |
| Five requested topics | The instrument-panel collector discovers series by official Kalshi category/tag queries; the category-to-topic mapping is not a guaranteed complete taxonomy. | [Series list](https://docs.kalshi.com/api-reference/market/get-series-list); `instrument-panel/tools/kalshi_collect.py`; [Flagged for Review](../instrument-panel/site/flagged.html) |
| Current market data | GitHub Actions collects demo API data and commits snapshots; the instrument panel workflow is scheduled every 15 minutes (GitHub schedules may be delayed). Its live chart also polls public REST from the visitor's browser. Neither is a guarantee of exchange-tick real time. | [.github/workflows/pages.yml](../.github/workflows/pages.yml); [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) |
| Price chart | The instrument-panel chart displays timestamp on X, contract price on Y, client-polled market points, optional official candlesticks (1-minute or 1-hour intervals), and collector snapshots. Browser polling is not a WebSocket stream. | [Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks); `instrument-panel/site/assets/live.js` |
| Orderbook liquidity | Public orderbook snapshots show bid price levels and contract quantities; this is resting-book depth, not a guarantee of executable liquidity. The API may return no levels. | [Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook) |
| Outcomes | Collected settled markets retain the API's `result` field, whose documented schema allows `yes` / `no`. Settlement timing can vary. | [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets); [Market settlement](https://docs.kalshi.com/getting_started/market_settlement) |
| Portfolio | The checked-in portfolio snapshot says unauthenticated because this repository has no configured demo API key. No balance, positions, fills, or account performance are claimed here. | [Get Balance](https://docs.kalshi.com/api-reference/portfolio/get-balance); [Get Positions](https://docs.kalshi.com/api-reference/portfolio/get-positions); [Get Fills](https://docs.kalshi.com/api-reference/portfolio/get-fills); `data/portfolio.json` |
| Simulated trades / strategy testing | The repository has dry-run order validation and a separate paper-trading UI. The latest recorded execution artifact is dry-run with zero results; this is not an executed Kalshi trade or a validated profitable strategy. | `tools/execute_strategy.py`; `live/trading.html`; `data/executions.json`; [Create Order V2](https://docs.kalshi.com/api-reference/orders/create-order-v2) |
| Actual demo order execution | Guarded by private repository secrets, a separate explicit enable variable, dry-run setting, in-scope ticker checks, and order/notional caps. It was not exercised in this review because credentials are absent. Never paste private keys into a public page or chat. | [API keys](https://docs.kalshi.com/getting_started/api_keys); `.github/workflows/trade.yml`; `tools/execute_strategy.py` |
| Price jumps and related links | A separate `session-8b9a46b4/` subsite detects consecutive recorded trade prints that move at least $0.10 in either direction and links to the official demo trades response. Its checked-in snapshot found 39 such print-to-print changes across 12 markets / 2,479 prints. This is historical captured trade data, not a continuously updating alert stream; cause/news remains blank. | [Trades API](https://docs.kalshi.com/api-reference/market/get-trades); [jump page](../session-8b9a46b4/site/jumps.html); output timestamp `2026-11-20T12:43:59Z` |

## Ranking and price interpretation

“Highest dollar amount” is ambiguous. Kalshi exposes contract volume and open interest; the current instrument-panel landing page ranks its displayed examples by **open interest × last price** (a computed dollar estimate), while other repository sections use different measures. Do not label such a calculation “dollar volume” or an official exchange field. The underlying fields and fixed-point units are documented by [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) and [fixed-point migration](https://docs.kalshi.com/getting_started/fixed_point_migration).

An empty orderbook is materially different from a quoted market. Open interest is not a measure of immediately available depth. A chart of current API snapshots also cannot recover price movement that occurred between polls.

## Security and environment

Kalshi API requests use signed authentication headers. The official signing guide supports Ed25519 and RSA-PSS and requires the timestamp, method, and path (without query parameters) in the pre-sign text; the timestamp must be within 30 seconds ([API keys](https://docs.kalshi.com/getting_started/api_keys)). Kalshi's WebSocket connections require API-key authentication during the handshake ([WebSocket connection](https://docs.kalshi.com/websockets/websocket-connection)).

GitHub Pages is static hosting. It can display public market data but does not itself run the repository's Node backend or safely hold a private key. This repo's static pages do not ask visitors for credentials. Authenticated account features require a separately hosted trusted process and configured demo credentials; until then their values must stay blank/unavailable.

## Open items and irregularities

1. **Account-specific performance and actual orders are unverified.** No demo credentials are present; the current portfolio artifact is explicitly unauthenticated and the execution artifact has no orders.
2. **No news cause attribution.** The separate jump page detects qualifying historic demo trade-print moves and links to the Kalshi trades response. There is no verified news feed or source-to-price causal analysis; any news link shown near a jump must remain a lead for human review. The print detector is not itself a live alert stream.
3. **Multiple dashboard implementations.** Root, `pages/`, `site/`, `live/`, `intelligence/`, `dashboard/`, `verified/`, and `instrument-panel/` coexist. Their data and metrics are not a single consistent product; integration/consolidation remains a product task.
4. **Coverage limits.** Topic inclusion depends on API categories/tags, collector limits, and available demo series. For example, the current instrument-panel snapshot has no open Culture markets; that is not evidence that no culture events exist outside that query/snapshot.
5. **Snapshot time matters.** The checked-in instrument-panel snapshot reviewed here was generated at `2026-11-20T13:11:17Z`. It is a historical capture and not a claim about current prices after that timestamp. The separate jump/backtest artifact is from the earlier `2026-11-20T12:43:59Z` snapshot.

See [Verification Log](./VERIFICATION.md), the instrument-panel [Verification](../instrument-panel/site/verification.html) page, and [Flagged for Review](../instrument-panel/site/flagged.html) for evidence and detailed caveats.
