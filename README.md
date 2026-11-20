# Kalshi Demo Dashboard

Live client-side dashboard and supporting research pages for Kalshi **demo** markets in gas prices, elections, culture, crypto, and golf. The original category-specific site lives at `index.html` and `pages/`. Additional verification, limitations, and decision-register materials are at `analysis.html`, `portfolio.html`, and `review.html`.

## Run locally

Open `index.html` in a browser or serve this repository with `python3 -m http.server 8000`. Public market data is requested client-side from Kalshi's demo API; availability and browser CORS/network restrictions can affect live results.

## Important safety and verification notes

The root-level monitor sorts only documented contract volume, not dollar turnover; its chart is local YES-bid REST snapshots rather than a historical series; topic matching is heuristic. `portfolio.html` deliberately leaves private account values blank and does not execute trades. Do not place private signing keys in a public static site. Review `review.html` for open questions and `pages/flagged.html` for the main site's existing review list.

Portfolio access and order submission are deliberately disabled in the static site. Browser-side private-key signing is not suitable for a public GitHub Pages application. Do not enter API credentials into this site. Enabling authenticated portfolio analysis or demo order execution requires a separately secured backend; see `pages/suggestions.html` and `pages/flagged.html`.

## Official references

- [Kalshi market data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data)
- [Kalshi orderbook schema](https://docs.kalshi.com/getting_started/orderbook_responses)
- [Kalshi authenticated order guide](https://docs.kalshi.com/getting_started/quick_start_create_order)
- [Kalshi WebSocket guide](https://docs.kalshi.com/getting_started/quick_start_websockets)
- [Kalshi events endpoint](https://docs.kalshi.com/api-reference/events/get-events)
- [Kalshi API changelog](https://docs.kalshi.com/changelog)
- [GitHub Pages documentation](https://docs.github.com/en/pages)

See [COORDINATION.md](COORDINATION.md) for history and verification notes.


---

## Dashboard added by session arena-3420a90d (`dashboard/`)

A separate dashboard lives in `dashboard/` (published by the same Pages workflow): https://karagemop466-tech.github.io/Demo2/dashboard/index.html

- `dashboard/markets.html`: markets and series by category, each row linked to its Kalshi API response
- `dashboard/resolutions.html`: settled markets with YES/NO results
- `dashboard/live.html`: candlestick chart, live tape (timestamped polling) and orderbook liquidity, public endpoints only
- `dashboard/portfolio.html`: BLOCKED until a Kalshi demo API key is supplied; no trades placed
- `dashboard/analysis.html`, `suggestions.html` (decision-first), `questions.html`, `flagged.html`

Data: `dashboard/data/snapshot.json`. Verified values only; blanks are marked UNVERIFIED. See `COORDINATION.md` for sources and irregularities.

---

## Final integration — session 5330bffb (`pages/`, `assets/`, `tools/`, `data/`)

The landing page is [`index.html`](index.html) (live dashboard). Everything is cross-linked; entry points:

- `pages/executive-summary.html` — executive summary; `pages/gas|elections|culture|crypto|golf.html` — per-topic verified tables (every row links to its official API response, rendered from `data/` by `assets/tables.js`)
- `pages/portfolio.html` — portfolio & trading: **this site never accepts credentials** (PR #6 security fix); run `tools/kalshi_trade.py` locally with your own Kalshi demo key to track the portfolio, execute demo orders, and generate the categorized trade/strategy report (`python3 tools/kalshi_trade.py selftest` verifies the signing offline)
- `pages/flagged.html` — the consolidated Flagged for Review register (all archives linked); `pages/questions.html`, `pages/suggestions.html` (decision board), `pages/verification.html`, `pages/sources.html`, `pages/repo-review.html`
- `data/` — verified snapshots refreshed by the GitHub Action `Collect Kalshi demo data` (`tools/collect_kalshi.py`, every 2h + on demand): markets (open/settled), events, series, orderbooks, candlesticks (1-min/24h + 60-min/7d), taxonomy, and `collection_log.json` (every request URL/status logged). Each row carries its `source_url`.
- Live browser fetch to the demo API is attempted first and falls back to the labelled snapshot; WebSocket streaming is impossible in a browser (signed handshake headers) — see Flagged G-1/G-2.
