# Kalshi Demo — Executive Summary

> Prepared for the Kalshi Demo project. Every technical statement below is traceable
> to the official Kalshi API documentation (docs.kalshi.com) or to the project
> requirements. Links to the verified sources are provided. Items that could not be
> confirmed from an official source are flagged as unverified in
> [docs/VERIFICATION.md](./VERIFICATION.md).

## 1. Objective

Build a **live, interactive Kalshi prediction-market dashboard** for a **Kalshi demo
account** that:

1. Collects, organizes, and analyzes market data against a full list of requirements.
2. Tracks **live events until they resolve**, recording how each event resolved
   (`yes` / `no`).
3. Focuses on five topics only: **gas prices, elections, culture, crypto, and golf**.
4. Tracks **portfolio performance** on the Kalshi demo account, analyzes trade
   results, categorizes trades, and builds **strategies** by trade type.
5. Executes trades on events and tracks performance.
6. Shows **live price-movement charts** (X = time with selectable seconds / minutes /
   hours window; Y = current contract price) and **current liquidity** (contracts
   available at each price).
7. Provides a **Suggestions** section to review and choose improvement paths before
   implementing changes.
8. Ships a clean **GitHub Pages** site with a landing page and category subpages,
   tables of all entries/findings, and analysis.

## 2. The Kalshi API surface (verified)

Source: https://docs.kalshi.com/getting_started/demo_env and
https://docs.kalshi.com/getting_started/api_environments

| Surface | Recommended demo endpoint | Also supported |
| --- | --- | --- |
| REST Trade API | `https://external-api.demo.kalshi.co/trade-api/v2` | `https://demo-api.kalshi.co/trade-api/v2` |
| WebSocket API | `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` | `wss://demo-api.kalshi.co/trade-api/ws/v2` |

The demo environment uses **mock funds**; credentials are **not** shared with
production, and demo market prices/behavior may not reflect real markets
(https://docs.kalshi.com/getting_started/demo_env).

### 2.1 Authentication (verified)

Source: https://docs.kalshi.com/getting_started/api_keys

- Kalshi API keys are **asymmetric key pairs**. You sign each request with the
  private key; Kalshi verifies with the registered public key.
- Two key types: **Ed25519** (recommended) and **RSA** (2048-bit, RSA-PSS + SHA-256).
- Every request carries three headers:
  - `KALSHI-ACCESS-KEY` — the Key ID
  - `KALSHI-ACCESS-TIMESTAMP` — request timestamp in ms
  - `KALSHI-ACCESS-SIGNATURE` — base64 signature over
    `timestamp + HTTP method + path` (path **without** query string)
- Timestamp must be within **30 seconds** of Kalshi's clock, else `401`
  `header_timestamp_expired`.
- **Public market-data endpoints require no authentication** (reads of series,
  events, markets, orderbook) —
  https://docs.kalshi.com/getting_started/quick_start_market_data.
- The **WebSocket connection requires authentication** even for public-data
  channels — https://docs.kalshi.com/websockets/websocket-connection.

### 2.2 Key endpoints used by the dashboard (verified)

| Capability | Endpoint | Source |
| --- | --- | --- |
| List events (filter by status) | `GET /events?status=open&with_nested_markets=true&limit=200` | [Get Events](https://docs.kalshi.com/api-reference/events/get-events) |
| List markets (filter by series/status) | `GET /markets?series_ticker=...&status=open` | [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) |
| Current orderbook / liquidity | `GET /markets/{ticker}/orderbook?depth=N` | [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook) |
| Price-history candlesticks | `GET /series/{series}/markets/{ticker}/candlesticks?start_ts=&end_ts=&period_interval=1|60|1440` | [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks) |
| Portfolio balance | `GET /portfolio/balance` | [portfolio](https://docs.kalshi.com/llms.txt) |
| Recent trades | `GET /markets/{ticker}/trades` | [Get Trades](https://docs.kalshi.com/api-reference/market/get-trades) |
| Place order (V2) | `POST /orders` (V2 shape) | [Create Order V2](https://docs.kalshi.com/api-reference/orders/create-order-v2) |
| Exchange status | `GET /exchange/status` | [Get Exchange Status](https://docs.kalshi.com/api-reference/exchange/get-exchange-status) |

**Orderbook / liquidity mechanics** (verified): the orderbook returns
`yes_dollars` and `no_dollars` arrays of `[price_dollars, count_fp]` pairs sorted
ascending, best (highest) bid last. In binary markets a yes bid at price X equals a
no ask at (100 − X). This is the source of the dashboard's "contracts available at a
given price" liquidity view.
Source: https://docs.kalshi.com/api-reference/market/get-market-orderbook

**Candlesticks** (verified): `period_interval` is in **minutes** — `1` (1 minute),
`60` (1 hour), `1440` (1 day). Each candle has OHLC for yes bid/ask and trade price,
plus `volume_fp` and `open_interest_fp`. Max 5,000 periods per request.
Source: https://docs.kalshi.com/api-reference/market/get-market-candlesticks

**WebSocket channels** (verified): `orderbook_delta`, `ticker`, `trade`, `fill`,
`market_positions`, `market_lifecycle_v2`, `user_orders`, etc.
Source: https://docs.kalshi.com/websockets/websocket-connection

## 3. Data freshness (verified caveat)

REST responses such as `GET /markets` and `GET /markets/{ticker}` are **cached for a
short time**; prices, sizes, and status can lag the exchange by several seconds, and
filtered listings can lag longer. Use the **WebSocket API** for current state.
Source: https://docs.kalshi.com/api-reference/market/get-markets

## 4. Dashboard design (what was built)

A two-part system:

1. **Backend** (`server/`) — a Node.js service that:
   - Signs and calls the Kalshi demo REST API (Ed25519/RSA).
   - Maintains a live tracking store for events until resolution (`yes`/`no`).
   - Executes trades (V2 orders) and records them.
   - Computes portfolio performance, categorizes trades, and proposes strategies.
   - Exposes a JSON API the frontend consumes.
2. **Frontend / GitHub Pages site** (`site/`) — a clean dashboard:
   - **Live Events** board filtered to the five topics, ranked by dollar volume.
   - **Price Chart**: X = time (seconds / minutes / hours window selector),
     Y = contract price.
   - **Liquidity** view: contracts available at each price level.
   - **Portfolio**, **Trades**, **Strategies**, **Suggestions**, and
     **Flagged for Review** pages, all in simple tables with source links.

The static GitHub Pages site also works standalone for public market data by calling
Kalshi's public demo endpoints directly from the browser. Authenticated portfolio
and trade execution require the backend with a demo API key (never committed).

## 5. Constraints and flags (do not block merge)

These are documented in detail in [docs/VERIFICATION.md](./VERIFICATION.md) and on
the site's "Flagged for Review" page:

- **FLAG-01 — Sandbox network allowlist**: this build environment can reach
  `github.com`/`npmjs`/`pypi` but **cannot** reach `*.kalshi.co` (TLS reset). Live
  Kalshi calls are implemented but could not be executed/verified from this sandbox.
- **FLAG-02 — No API key**: no Kalshi demo key pair is present. Trade execution is
  implemented and documented but cannot be exercised without a demo account key.
- **FLAG-03 — Static Pages host**: GitHub Pages cannot run a persistent authenticated
  backend or store secrets. The static site uses public market-data calls; the
  backend provides authenticated portfolio/trade features.

## 6. Verification policy

- Every table row on the site carries a **source link** to an official Kalshi page.
- A value that cannot be confirmed from an official source is **left blank** and
  flagged **unverified** — never inferred or filled in.
- All findings, irregularities, and unverified items are recorded in
  [COORDINATION.md](../COORDINATION.md) and the "Flagged for Review" page.

## 7. Sources (official)

- API documentation index: https://docs.kalshi.com/llms.txt
- Demo environment: https://docs.kalshi.com/getting_started/demo_env
- API keys & signing: https://docs.kalshi.com/getting_started/api_keys
- Get Events: https://docs.kalshi.com/api-reference/events/get-events
- Get Markets: https://docs.kalshi.com/api-reference/market/get-markets
- Get Market Orderbook: https://docs.kalshi.com/api-reference/market/get-market-orderbook
- Get Market Candlesticks: https://docs.kalshi.com/api-reference/market/get-market-candlesticks
- Quick Start: Market Data: https://docs.kalshi.com/getting_started/quick_start_market_data
- WebSocket Connection: https://docs.kalshi.com/websockets/websocket-connection
- REST OpenAPI spec: https://docs.kalshi.com/openapi.yaml

## 8. Pulse trader subsite — snapshot and implementation (2026-11-20)

The additional `pulse/` subsite is a trader-facing view of the existing Kalshi **demo** data. It does
not replace the existing dashboard, execute real-money trades, or claim that sampled prices are a
continuous exchange feed.

### Snapshot facts (source: official demo API collector)

| Finding | Observed value | Source / verification |
| --- | ---: | --- |
| In-scope series | 174 | [`data/dashboard_instrument.json`](../data/dashboard_instrument.json), collected from demo series/markets; [Get Series](https://docs.kalshi.com/api-reference/market/get-series-list), [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) |
| Open markets collected | 1,556 | [`data/dashboard_instrument.json`](../data/dashboard_instrument.json); [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) |
| Resolved markets collected | 1,601 | [`data/dashboard_instrument.json`](../data/dashboard_instrument.json); official market `result` field, [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) |
| Resolved markets with `volume_fp > 0` | 317 | Computed filter over official `volume_fp`; [`data/pulse_backtest.json`](../data/pulse_backtest.json) |
| Resolved markets with `volume_fp = 0` (excluded from backtest) | 1,284 | Computed filter over official `volume_fp`; excluded because the displayed last price is not an observed trade price for these markets |
| Open markets by topic | Gas 189; elections 367; culture 0; crypto 500; golf 500 | [`data/dashboard_instrument.json`](../data/dashboard_instrument.json); collector snapshot, not a claim of current live counts |
| Traded resolved results | Yes 83; no 234 | Computed from official `result` on the 317 traded resolved markets; [`data/pulse_backtest.json`](../data/pulse_backtest.json) |
| Detected trade-print jumps | 39 with absolute consecutive `yes_price_dollars` difference ≥ $0.10 | Computed using official trade prices/timestamps, [Get Trades](https://docs.kalshi.com/api-reference/market/get-trades); [`data/pulse_jumps.json`](../data/pulse_jumps.json) |
| Collector tick jumps | 0 in 7 observed tick samples | Computed from [`data/history_instrument/2026-11-20.json`](../data/history_instrument/2026-11-20.json); sample gaps mean this is not evidence of no intervening movement |
| Culture open-market rows | 0 | Empty in this snapshot; see [Pulse Flagged for Review](../pulse/flagged.html) P-F02 |
| Authenticated account values | Blank / unavailable | The existing portfolio snapshot records unauthenticated; no API key exists in repo. Never shown as zero. |

“Dollar amount” ranking is a **computed proxy**, `volume_fp × last_price_dollars`, not a Kalshi-reported
turnover field. It is explicitly marked computed in the page UI. The strict gas-price display omits
energy-adjacent markets (such as solar) that fall into the broad Oil-and-energy collector taxonomy.

### Live interaction and limitations

- `pulse/live.html` polls public demo REST market and orderbook endpoints in the browser. The chart axis
  is time and contract price, with 60-second, 5-minute, 15-minute, 1-hour and 6-hour windows. It labels
  browser polls as observations, not historical exchange data. Official candles support 1-minute,
  1-hour and 1-day periods only: [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks).
- Liquidity displays official YES/NO bid price/count levels. The displayed YES ask is **derived** as
  `1 − best NO bid`, not mislabeled as a raw ask: [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook).
- The 39 recorded ≥$0.10 changes link to official Kalshi market/event/trade/orderbook and contract
  settlement-source context. External news causation is blank and marked **unverified**; the API does
  not establish that any article caused a particular move.
- Five automated paper strategies run on resolved, traded markets only. Results are gross, one-contract
  arithmetic using the final observed price (hindsight-biased); they are a calibration description,
  not evidence of tradable performance. Payout logic follows the official
  [market settlement docs](https://docs.kalshi.com/getting_started/market_settlement). The 12-position
  paper portfolio is separate from the actual demo account, with realised P&amp;L blank until settlement.
- No API key is configured, so no demo balance/positions/fills can be displayed and no orders were
  submitted. The source data and all limitations are published on [Pulse Verification](../pulse/verification.html)
  and [Pulse Flagged for Review](../pulse/flagged.html).

All counts above are a dated snapshot (`data/dashboard_instrument.json` generated 2026-11-20); they
must be refreshed by the repository collector before being treated as current. Full implementation:
[`pulse/`](../pulse/index.html), engines [`tools/pulse_jumps.py`](../tools/pulse_jumps.py),
[`tools/pulse_simulate.py`](../tools/pulse_simulate.py), and outputs in [`data/`](../data/).
