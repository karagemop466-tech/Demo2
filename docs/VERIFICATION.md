# Verification Log — Kalshi Demo Dashboard

**Review performed:** 2026-11-20 UTC. This log separates (1) claims read from official Kalshi documentation, (2) repository checks run in this session, and (3) observations copied from checked-in collector artifacts. An official documentation field/schema is not the same as a fresh live API observation. No portfolio values or unobserved market values are inferred.

## 1. Official documentation claims checked

Each row links to the official Kalshi documentation page used for the check.

| Claim | Verification | Status | Official source |
|---|---|---|---|
| Demo REST and WebSocket endpoint pairs shown in the project | Matched the current demo endpoint table | Verified from docs | [Demo environment](https://docs.kalshi.com/getting_started/demo_env) |
| Demo uses mock funds and its price/behavior may not represent real markets | Read on official demo guide | Verified from docs | [Demo environment](https://docs.kalshi.com/getting_started/demo_env) |
| `GET /markets` exposes prices, volume/open-interest fixed-point fields, status, and `result` in the documented response shape | Matched endpoint response schema; a schema example is not evidence of current live values | Verified from docs | [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) |
| Series discovery supports category and tag filters; category matching is exact and case-sensitive; categories can be plural | Matched query parameter documentation | Verified from docs | [Get Series List](https://docs.kalshi.com/api-reference/market/get-series-list) |
| Event results include nested markets when requested; event category is not treated as the authoritative five-topic taxonomy | Checked endpoint description/schema; topic membership remains project query logic | Verified from docs / taxonomy not defined | [Get Events](https://docs.kalshi.com/api-reference/events/get-events) |
| Orderbook contains YES/NO bid levels with fixed-point contract counts; `depth` permits 0 (all levels) or 1–100 | Matched query and response schema | Verified from docs | [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook) |
| Candlestick periods are 1, 60, or 1440 minutes | Matched allowed interval values; seconds are not an official candlestick interval | Verified from docs | [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks) |
| Portfolio balance, positions, and fills require authentication headers | Authorization sections document key, signature, and timestamp headers | Verified from docs | [Get Balance](https://docs.kalshi.com/api-reference/portfolio/get-balance), [Get Positions](https://docs.kalshi.com/api-reference/portfolio/get-positions), [Get Fills](https://docs.kalshi.com/api-reference/portfolio/get-fills) |
| Authenticated signature uses timestamp + HTTP method + path without query; RSA-PSS/SHA-256 and Ed25519 supported; timestamp tolerance 30 seconds | Matched current signing guide | Verified from docs | [API Keys](https://docs.kalshi.com/getting_started/api_keys) |
| WebSocket handshake requires API-key authentication | Matched WebSocket security scheme | Verified from docs | [WebSocket Connection](https://docs.kalshi.com/websockets/websocket-connection) |
| V2 create-order endpoint is `POST /portfolio/events/orders` | Matched endpoint and request shape; no real order sent in this review | Verified from docs | [Create Order (V2)](https://docs.kalshi.com/api-reference/orders/create-order-v2) |
| A YES or NO winning contract pays $1 per contract in simple yes/no settlement; timing can vary | Matched settlement guide | Verified from docs | [Market Settlement](https://docs.kalshi.com/getting_started/market_settlement) |
| Public unauthenticated calls have separate limits and clients should back off on HTTP 429 | Matched rate-limit guidance | Verified from docs | [Rate Limits](https://docs.kalshi.com/getting_started/rate_limits) |

## 2. Repository snapshot observations

These are observations from checked-in files, not a fresh request from this review session. Each dataset row contains or links to its actual Kalshi demo API source URL; inspect the linked raw response to review that particular value.

| Observation | Evidence in repository | Status / caveat | Source |
|---|---|---|---|
| Instrument-panel snapshot timestamp is `2026-11-20T13:11:17Z`; base is the recommended demo REST API | `data/dashboard_instrument.json` metadata | Verified as checked-in artifact metadata; not a current-after-timestamp price | [Demo API base](https://external-api.demo.kalshi.co/trade-api/v2) |
| Snapshot records 336 HTTP requests and zero request errors | `data/dashboard_instrument.json` metadata | Copied from artifact; it does not mean this session made those requests | [Instrument-panel snapshot](../data/dashboard_instrument.json) |
| Collector includes five requested topics; displayed rows link to official demo API responses | `instrument-panel/tools/kalshi_collect.py`; `instrument-panel/tools/validate_data.py` | The validation run confirms row source URLs use the Kalshi demo API prefix; coverage is bounded by collector query/caps | [Series List](https://docs.kalshi.com/api-reference/market/get-series-list) |
| Current collector output has no open culture matches | `python instrument-panel/tools/validate_data.py` warning; snapshot content | Snapshot/query result only; it does not establish that Culture has no events | [Demo series API](https://external-api.demo.kalshi.co/trade-api/v2/series?category=Culture) |
| Two crypto series records have no settlement-source entries in the returned data | `python instrument-panel/tools/validate_data.py` warnings: `KXLINKPERP`, `KXLTCPERP` | Missing source fields are left missing; flagged, not filled by inference | [Series List](https://docs.kalshi.com/api-reference/market/get-series-list) |
| Portfolio snapshot is unauthenticated and gives a reason that no demo key is configured | `data/portfolio.json` | No balance, positions, fills, or account performance can be reported | [Get Balance](https://docs.kalshi.com/api-reference/portfolio/get-balance) |
| Latest execution artifact is `dry_run`, has a $25 run cap, and has zero order results | `data/executions.json` | No simulated order result and no live order can be inferred from an empty list | [Create Order (V2)](https://docs.kalshi.com/api-reference/orders/create-order-v2) |
| Workflow has three execution gates: demo key secrets, `KALSHI_TRADING_ENABLED=1`, and its dry-run/dispatch handling | `.github/workflows/trade.yml`; `tools/execute_strategy.py` | Code/config review only; this session did not execute or authenticate an order | [API Keys](https://docs.kalshi.com/getting_started/api_keys) |
| Current instrument-panel summary displays `open interest × last price` as a computed dollar estimate | `instrument-panel/site/index.html` | Not exchange-reported dollar turnover; other dashboard sections use different ranking concepts | [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) |

## 3. Automated checks run in this session

| Command | Result | What it establishes | What it does not establish |
|---|---|---|---|
| `python3 tools/check.py` | Exit 0; links/nav/secrets/JS checks clean; data warning: `data/snapshot.json` absent | Root `index.html` and generated `pages/` have expected structure; no detected embedded private-key block; syntax checks pass | It does not check every row of every historical subsite; its warning shows the separate top-level `data/snapshot.json` pipeline artifact is currently absent |
| `python3 scripts/check_links.py` | Exit 0; 8,448 references across 105 HTML files | Internal references/anchors pass under this checker | This invocation did not use `--external`; external URLs were not live-probed here |
| `python3 scripts/check_links.py --external` | Exit 0; 3,506 unique external URLs probed; no hard failures; transient TLS, timeout, remote-close, and rate-limit cases emitted warnings | Internal and external target checks pass under the link checker's policy; known temporary/anti-bot blocks remain visible | Remote errors were not silently relabeled as confirmed links; they remain `verify manually` warnings |
| `python3 instrument-panel/tests_smoke.py` | Exit 0; all offline assertions pass | Collector selection, derived fields, URL construction, and scoping against fixtures | No network or live account behavior |
| `python3 instrument-panel/tools/validate_data.py` | Exit 0; 3,104 rows, 336 requests, 0 recorded errors; warnings for two missing settlement-source lists, two malformed terms URLs blanked, and no open Culture matches | Instrument-panel market/resolution/series API source fields, price ranges, derived arithmetic, and freshness passed its current validator | Does not establish completeness of topic enumeration or explain missing settlement sources |
| `python3 instrument-panel/tools/check_site.py` | Exit 0; 105 pages checked; 13 reported runtime-anchor issues in a separate `site/` subsite | Instrument-panel site links/nav/anchors and disclaimers pass according to this checker | The 13 findings remain review items in another subsite; they are not silently treated as fixed |
| `node intelligence/scripts/linkcheck.mjs` | Exit 0; 9 pages, 272 links, 177 data-source fields | `intelligence/` internal references and that subsite's source fields pass | Does not certify all tables across all repository subsites |

## 4. Unverified / flagged requirements

| Item | What can be confirmed now | What remains unverified or incomplete | Official source / evidence |
|---|---|---|---|
| Fresh live event prices | Instrument-panel client polls public REST for selected markets; the separate `session-8b9a46b4/site/live.js` uses trade prints for seconds, and resolves a market's event/series before requesting 1m/1h candles; orderbook parsing uses `orderbook_fp.yes_dollars` | No WebSocket-backed browser feed is deployed; data between browser polls is missed, REST can be delayed, and these separate pages do not form one unified stream. The new routes were syntax-checked and passed a local mocked-fetch test; they were not exercised against the live API from this review | [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets); [Get Event](https://docs.kalshi.com/api-reference/events/get-event); [Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks); [Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook); [WebSocket Connection](https://docs.kalshi.com/websockets/websocket-connection); [live chart source](../session-8b9a46b4/site/live.js) |
| Seconds/minutes/hours charting | Chart client polling creates seconds-scale observation points; official candles support 1m/1h/1d | Seconds are not official candlestick granularity and cannot be reconstructed for times the browser was not polling | [Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks) |
| News links for moves of at least $0.10 | `session-8b9a46b4/tools/jump_backtest.py` detects consecutive trade-print prices changing by at least $0.10 in either direction. Its checked-in output has 39 jumps from 2,479 prints across 12 markets in the 2026-11-20T12:43:59Z snapshot | This is historical captured demo data, not an ongoing live alert. No verified news feed or causal attribution is implemented; the cause field is blank. Any possible news link must be labeled context for review, never “cause” based only on timing | [Get Trades](https://docs.kalshi.com/api-reference/market/get-trades); [jump data](../session-8b9a46b4/data/jumps.json); [jump page](../session-8b9a46b4/site/jumps.html) |
| Portfolio performance | API endpoint schemas and local analysis code exist | No key configured: live account balance, positions, fills, realized/unrealized P&L, and account-level strategy results are blank/unavailable | [Get Balance](https://docs.kalshi.com/api-reference/portfolio/get-balance); [Get Positions](https://docs.kalshi.com/api-reference/portfolio/get-positions); [Get Fills](https://docs.kalshi.com/api-reference/portfolio/get-fills) |
| Real demo order execution | Guarded implementation targets the documented V2 endpoint | No credentials or confirmed execution; the dry-run artifact has no results. Do not report an order as placed | [Create Order (V2)](https://docs.kalshi.com/api-reference/orders/create-order-v2) |
| Exhaustive five-topic scope | Official series categories/tags provide discovery filters | No docs-backed completeness guarantee for a custom union of gas/elections/culture/crypto/golf; collector limits and snapshot timing can omit series | [Get Series List](https://docs.kalshi.com/api-reference/market/get-series-list) |
| One simplified dashboard | Root landing page links to multiple sub-sites | Multiple historical implementations coexist and do not share one ranking metric or data model; consolidation remains open | [Repository](https://github.com/karagemop466-tech/Demo2) |
| Every row across every HTML table has an official source | Instrument-panel validator and `intelligence/` checker validate their own data rows; broad link check validates internal references | No repository-wide validator currently proves that every table row in all 85 HTML pages carries an official row-specific source; do not generalize subsite checks to all pages | [Instrument-panel validator](../instrument-panel/tools/validate_data.py); [intelligence checker](../intelligence/scripts/linkcheck.mjs) |

## 5. Source register (official)

- [Demo environment and endpoints](https://docs.kalshi.com/getting_started/demo_env)
- [API environments](https://docs.kalshi.com/getting_started/api_environments)
- [API keys and request signing](https://docs.kalshi.com/getting_started/api_keys)
- [Get Events](https://docs.kalshi.com/api-reference/events/get-events)
- [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets)
- [Get Series List](https://docs.kalshi.com/api-reference/market/get-series-list)
- [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook)
- [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks)
- [Get Trades](https://docs.kalshi.com/api-reference/market/get-trades)
- [Get Balance](https://docs.kalshi.com/api-reference/portfolio/get-balance)
- [Get Positions](https://docs.kalshi.com/api-reference/portfolio/get-positions)
- [Get Fills](https://docs.kalshi.com/api-reference/portfolio/get-fills)
- [Create Order (V2)](https://docs.kalshi.com/api-reference/orders/create-order-v2)
- [Market Settlement](https://docs.kalshi.com/getting_started/market_settlement)
- [WebSocket Connection](https://docs.kalshi.com/websockets/websocket-connection)
- [Rate Limits](https://docs.kalshi.com/getting_started/rate_limits)
