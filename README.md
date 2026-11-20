# Kalshi Demo Dashboard

Live client-side dashboard and supporting research pages for Kalshi **demo** markets in gas prices, elections, culture, crypto, and golf. The original category-specific site lives at `index.html` and `pages/`. Additional verification, limitations, and decision-register materials are at `analysis.html`, `portfolio.html`, and `review.html`.

## Run locally

Open `index.html` in a browser or serve this repository with `python3 -m http.server 8000`. Public market data is requested client-side from Kalshi's demo API; availability and browser CORS/network restrictions can affect live results.

## Important safety and verification notes

The root-level monitor sorts only documented contract volume, not dollar turnover; its chart is local YES-bid REST snapshots rather than a historical series; topic matching is heuristic. `portfolio.html` deliberately leaves private account values blank and does not execute trades. Do not place private signing keys in a public static site. Review `review.html` for open questions and `pages/flagged.html` for the main site's existing review list.

The other branch's original implementation and research materials are retained. Its original README described browser-side private-key signing and trade execution; that approach requires a security review before use. Do not enter credentials in a public GitHub Pages application.

## Official references

- [Kalshi market data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data)
- [Kalshi orderbook schema](https://docs.kalshi.com/getting_started/orderbook_responses)
- [Kalshi authenticated order guide](https://docs.kalshi.com/getting_started/quick_start_create_order)
- [Kalshi WebSocket guide](https://docs.kalshi.com/getting_started/quick_start_websockets)
- [Kalshi events endpoint](https://docs.kalshi.com/api-reference/events/get-events)
- [Kalshi API changelog](https://docs.kalshi.com/changelog)
- [GitHub Pages documentation](https://docs.github.com/en/pages)

See [COORDINATION.md](COORDINATION.md) for history and verification notes.
