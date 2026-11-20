# Kalshi Demo Dashboard

A live, interactive dashboard for a **Kalshi demo account** that tracks prediction-market
events across **gas prices, elections, culture, crypto, and golf**, with price-movement
charts, liquidity depth, portfolio performance, trade categorization, strategy suggestions,
and a reviewable suggestions board.

All API endpoints and request signing are verified from the official Kalshi API
documentation ([docs.kalshi.com](https://docs.kalshi.com)). Every table row on the site
carries a source link; values that cannot be confirmed from an official source are left
blank and flagged as **unverified**.

## What it does

- **Live Events** board filtered to the five topics, ranked by estimated notional.
- **Event tracking until resolution** — records whether each event resolved YES or NO.
- **Price-movement chart** — X = time (minute/hour/day candles), Y = contract price.
- **Liquidity** — contracts available at each price level from the live orderbook, with
  cumulative depth and spread.
- **Portfolio** performance on the demo account.
- **Trades** execution, recording, and categorization (topic, side, horizon, type).
- **Strategies** derived from categorized trades, proposed for review.
- **Suggestions** board to review improvement paths before implementing changes.
- **Flagged for Review** page for irregularities and unverified items.

## Layout

```
site/                 Static dashboard (landing page + category subpages) for GitHub Pages
server/               Node backend: Kalshi REST/WS client, signing, trades, tracking store
docs/                 Executive summary, questions/answers, suggestions, verification log
.github/workflows/    GitHub Pages deploy workflow
COORDINATION.md       Shared task board (sessions, tasks, sources, flags)
```

## Run the backend (live dashboard)

```bash
npm install
# Optional: supply a Kalshi demo API key (never commit keys)
# export KALSHI_ACCESS_KEY=<key-id>
# export KALSHI_PRIVATE_KEY="$(cat kalshi.key)"
npm start            # serves the dashboard + API on http://0.0.0.0:8080
```

The backend calls the Kalshi demo API, polls for price updates, executes trades (V2
orders), and persists tracking state to `.data/store.json` (gitignored).

## GitHub Pages

The static site in `site/` is deployed to GitHub Pages on push to `main` (see
`.github/workflows/pages.yml`). On a static host, the site calls Kalshi's public
market-data endpoints directly from the browser; authenticated portfolio/trade features
require the backend with a demo API key.

## Verification & flags

See [docs/VERIFICATION.md](docs/VERIFICATION.md) and the site's **Flagged for Review**
page. Known environment flags:

- **FLAG-01**: this build sandbox cannot reach `*.kalshi.co` (egress allowlist); live data
  is implemented but unverified from this environment.
- **FLAG-02**: no Kalshi demo API key is present; trade execution is implemented but cannot
  be exercised without a demo account key pair.
- **FLAG-03**: GitHub Pages is a static host; it cannot run a persistent authenticated
  backend or hold secrets.

## Sources (official)

- Kalshi API docs: https://docs.kalshi.com/llms.txt
- Demo environment: https://docs.kalshi.com/getting_started/demo_env
- API keys & signing: https://docs.kalshi.com/getting_started/api_keys
- Get Events: https://docs.kalshi.com/api-reference/events/get-events
- Get Markets: https://docs.kalshi.com/api-reference/market/get-markets
- Get Market Orderbook: https://docs.kalshi.com/api-reference/market/get-market-orderbook
- Get Market Candlesticks: https://docs.kalshi.com/api-reference/market/get-market-candlesticks
- WebSocket Connection: https://docs.kalshi.com/websockets/websocket-connection
