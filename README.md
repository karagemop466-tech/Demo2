# Demo2 — Kalshi demo dashboard

Live site (GitHub Pages, served from `main` → `/docs`):
https://karagemop466-tech.github.io/Demo2/

## What is here

| Path | What it is |
|---|---|
| `docs/index.html` | Landing page + executive summary |
| `docs/markets.html` | Markets and series by category, with source links per row |
| `docs/resolutions.html` | Settled markets with YES/NO results |
| `docs/live.html` | Live price chart, timestamped live tape, orderbook liquidity (public REST, no login) |
| `docs/portfolio.html` | Portfolio / trades — **blocked** until a Kalshi demo API key is provided |
| `docs/analysis.html` | Verified observations, trade categories, strategy hypotheses (untested) |
| `docs/suggestions.html` | Improvement suggestions with Approve / Defer / Reject — nothing is implemented until selected |
| `docs/questions.html` | Questions, known vs missing information, how to find it |
| `docs/flagged.html` | Flagged for review: irregularities, constraints, unverified items, source list |
| `docs/data/snapshot.json` | The verified data snapshot behind the tables (each row carries its API source key) |
| `COORDINATION.md` | Shared task board, claims, verification log, handoffs |

## Data sources

- Kalshi Trade API docs: https://docs.kalshi.com (API environments, Get Markets, Get Series List, Candlesticks, Orderbook, Settlement, Rate Limits, WebSocket, API Keys)
- Demo REST base URL (as supplied): https://external-api.demo.kalshi.co/trade-api/v2
- Production REST base URL (read-only comparison): https://external-api.kalshi.com/trade-api/v2

Every value is taken from an official API response or the official docs. Values that could not be confirmed are left blank and marked **UNVERIFIED**. Nothing is inferred.

## Run locally

No build step. Serve the `docs/` folder with any static server:

```bash
cd docs && python3 -m http.server 8000
```

The live page calls Kalshi’s public endpoints from the browser. It holds no API keys.

## Known limits

See `docs/flagged.html`. In short: the tables are a sample, the API reports contracts (not dollars) for volume, WebSocket streams require authentication, and trading requires a demo API key.
