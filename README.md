# Kalshi Demo Monitor

A source-linked static dashboard for selected **Kalshi demo** markets. The browser-side app is wired to request public market data from Kalshi's recommended demo REST API, filter five requested topic groups, show visible orderbook levels, and chart market prices. Live API responses and browser CORS behavior have not been verified from this workspace. The site does **not** connect to an account or place trades.

## Start here

- [Executive summary](./executive-summary.html)
- [Dashboard](./index.html)
- [Requirements and decision questions](./requirements.html)
- [Methodology and definitions](./methodology.html)
- [Portfolio and trading limitations](./portfolio.html)
- [Resolution watchlist](./watchlist.html)
- [Suggestions for review](./suggestions.html)
- [Flagged for Review](./review.html)
- [Official source index](./sources.html)
- [Coordination board](./COORDINATION.md)

## Documented implementation scope

The API facts and field interpretations below were checked against the linked official documentation. Runtime connectivity to the demo API and live market values have **not** been verified from this workspace.

- Demo REST base URL: `https://external-api.demo.kalshi.co/trade-api/v2`.
- Open events in the requested topic groups: gas prices, elections, culture, crypto, and golf.
- Event rank: summed displayed YES/NO bid-side orderbook notional, computed as `price × contracts` from API-returned levels. This is **not** traded dollar volume. The official 24-hour volume field is shown in contracts.
- Visible orderbook: contract count at each returned bid price; asks are shown only as parity-derived values and labeled as derived.
- Charts: 30-second local snapshots every five seconds while the page is open; minute/hour charts use Kalshi's documented candle intervals.
- Resolution tracking: selected event tickers are saved in browser local storage and checked against live market data with a historical-market fallback.

Kalshi's own demo documentation says that its demo environment uses mock funds and demo prices/behavior may not reflect real markets. See [Kalshi's demo environment](https://docs.kalshi.com/getting_started/demo_env).

## Explicitly unavailable

No account credentials or account data were available in this repository/session. Therefore balances, positions, fills, P&L, strategy results, and trade execution are blank or disabled. No order was sent. The public static site does not collect or embed a private signing key. Account features require an authorized, secure server-side integration and agreed risk controls; no secrets should be pasted into the site or chat.

The event matcher is a local keyword rule set, not an official Kalshi topic taxonomy. Browser CORS/live demo API access could not be exercised from this workspace; the UI surfaces errors without filling them with mock data. See [Flagged for Review](./review.html).

## Run and verify locally

No third-party runtime dependencies are required. Use Node.js 20 or newer for tests/build checks.

```sh
npm test
npm run check
npm run build
python3 -m http.server 4173 --directory dist --bind 0.0.0.0
```

Then open `http://localhost:4173`. To test live demo data, the browser needs to reach Kalshi's demo API; if the browser/API blocks the request, the dashboard shows an error and leaves the live table blank.

## Publishing

The GitHub Actions workflow in `.github/workflows/pages.yml` verifies tests and links on pull requests and publishes the `dist/` artifact to GitHub Pages after a push to `main`. The repository must have GitHub Pages configured to use GitHub Actions. The actual deployment must be checked in Actions after merge.

## Official references

- [Kalshi demo environment](https://docs.kalshi.com/getting_started/demo_env)
- [Kalshi API environments](https://docs.kalshi.com/getting_started/api_environments)
- [Kalshi Get Events API](https://docs.kalshi.com/api-reference/events/get-events)
- [Kalshi orderbook API](https://docs.kalshi.com/api-reference/market/get-market-orderbook)
- [Kalshi candlestick API](https://docs.kalshi.com/api-reference/market/get-market-candlesticks)
- [Kalshi market lifecycle](https://docs.kalshi.com/getting_started/market_lifecycle)
- [Kalshi API keys and request signing](https://docs.kalshi.com/getting_started/api_keys)
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
