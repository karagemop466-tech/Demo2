# Verification Log

> Line-by-line verification of the Kalshi Demo dashboard. Every claim is checked
> against an official source (docs.kalshi.com). Values that cannot be confirmed from
> an official source are left blank and flagged **unverified** — never inferred.
>
> Status: **verified** = confirmed against the linked official source.
> **unverified** = cannot be confirmed here (see flags).

## 1. API surface & endpoints

| Item | Claim | Status | Source |
| --- | --- | --- | --- |
| Demo REST base (recommended) | `https://external-api.demo.kalshi.co/trade-api/v2` | verified | [demo_env](https://docs.kalshi.com/getting_started/demo_env) |
| Demo REST base (also supported) | `https://demo-api.kalshi.co/trade-api/v2` | verified | [demo_env](https://docs.kalshi.com/getting_started/demo_env) |
| Demo WS base (recommended) | `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` | verified | [demo_env](https://docs.kalshi.com/getting_started/demo_env) |
| Demo WS base (also supported) | `wss://demo-api.kalshi.co/trade-api/ws/v2` | verified | [demo_env](https://docs.kalshi.com/getting_started/demo_env) |
| Demo uses mock funds; creds not shared with prod | Yes | verified | [demo_env](https://docs.kalshi.com/getting_started/demo_env) |
| Auth headers | `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-TIMESTAMP`, `KALSHI-ACCESS-SIGNATURE` | verified | [api_keys](https://docs.kalshi.com/getting_started/api_keys) |
| Signature = base64(sign(timestamp + method + path)) | Yes; path signed without query string | verified | [api_keys](https://docs.kalshi.com/getting_started/api_keys) |
| Key types | Ed25519 (recommended), RSA-PSS/SHA-256 (2048-bit) | verified | [api_keys](https://docs.kalshi.com/getting_started/api_keys) |
| Timestamp tolerance | 30 seconds | verified | [api_keys](https://docs.kalshi.com/getting_started/api_keys) |
| `GET /events` params (status, with_nested_markets, limit, series_ticker, min_updated_ts) | Confirmed | verified | [Get Events](https://docs.kalshi.com/api-reference/events/get-events) |
| `GET /events` excludes multivariate | Yes | verified | [Get Events](https://docs.kalshi.com/api-reference/events/get-events) |
| `GET /markets` status filter (`unopened`, `open`, `closed`, `settled`) | Confirmed | verified | [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) |
| `GET /markets/{ticker}/orderbook` returns `orderbook_fp` yes/no dollars | Confirmed | verified | [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook) |
| Orderbook levels are `[price_dollars, count_fp]`, best bid last | Confirmed | verified | [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook) |
| Binary equivalence: yes bid X = no ask 100−X | Confirmed | verified | [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook) |
| Candlesticks `period_interval` = 1, 60, 1440 minutes | Confirmed | verified | [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks) |
| Candlesticks max 5,000 periods per request | Confirmed | verified | [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks) |
| Candlestick fields (OHLC, volume_fp, open_interest_fp) | Confirmed | verified | [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks) |
| Public market-data reads require no auth | Confirmed | verified | [Quick Start: Market Data](https://docs.kalshi.com/getting_started/quick_start_market_data) |
| WebSocket connection requires auth even for public channels | Confirmed | verified | [WebSocket Connection](https://docs.kalshi.com/websockets/websocket-connection) |
| WS channels include `ticker`, `orderbook_delta`, `trade`, `market_lifecycle_v2` | Confirmed | verified | [WebSocket Connection](https://docs.kalshi.com/websockets/websocket-connection) |
| REST responses are cached; can lag by seconds | Confirmed | verified | [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) |

## 2. Environment / behavior checks performed

| Check | Result | Status | Source |
| --- | --- | --- | --- |
| `curl` to demo `GET /exchange/status` from sandbox | TLS reset / HTTP 000 (egress allowlist excludes kalshi.co) | unverified (FLAG-01) | [demo_env](https://docs.kalshi.com/getting_started/demo_env) |
| Backend `/api/health` reachability check | reports Kalshi unreachable from sandbox | verified (as a negative) | — |
| Backend `/api/status` returns configured base URLs & topics | Returns correct config | verified | — |
| Node syntax check of all server modules | Passed | verified | — |
| Backend serves static `site/` and API routes | Confirmed via live preview | verified | — |

## 3. Items left blank / unverified (no inference)

| Item | Why unverified | Flag |
| --- | --- | --- |
| Live event titles, prices, volumes, notional | Kalshi demo API unreachable from this sandbox | FLAG-01 |
| Portfolio balance / positions | No API key + no egress | FLAG-01, FLAG-02 |
| Executed trades / order fills | No API key + no egress | FLAG-01, FLAG-02 |
| Settled yes/no outcome field names | Not fully enumerated on fetched doc pages | FLAG-05 |
| Exact category→topic mapping | No official enumeration of the five topics | FLAG-04 |
| Sub-minute (seconds) candlesticks | Official candlesticks are ≥1 minute | FLAG (see Suggestions S5) |

## 4. What the dashboard does with unverified data

- Live tables show a connectivity/status indicator; when Kalshi is unreachable, rows are
  not fabricated. The tables show a clear "unavailable / unverified" state with the reason.
- "Est. notional" is explicitly labeled a **computed** metric (price × volume), not an
  official Kalshi field.
- Resolution (yes/no) cells show "unverified" until confirmed from a live settled market.
- Every table row carries a source link to an official Kalshi page.

## 5. Sources (official)

- https://docs.kalshi.com/llms.txt
- https://docs.kalshi.com/getting_started/demo_env
- https://docs.kalshi.com/getting_started/api_keys
- https://docs.kalshi.com/getting_started/quick_start_market_data
- https://docs.kalshi.com/api-reference/events/get-events
- https://docs.kalshi.com/api-reference/market/get-markets
- https://docs.kalshi.com/api-reference/market/get-market-orderbook
- https://docs.kalshi.com/api-reference/market/get-market-candlesticks
- https://docs.kalshi.com/websockets/websocket-connection
- https://docs.kalshi.com/getting_started/market_settlement
- https://docs.kalshi.com/openapi.yaml
