# Kalshi Demo Monitor

A GitHub Pages research dashboard over the Kalshi **demo** environment, covering five
topics only: **gas prices, elections, culture, crypto and golf**.

**Live site:** https://karagemop466-tech.github.io/Demo2/

The site publishes one snapshot, one design system and one navigation. Earlier
parallel implementations (`pages/`+`verified/` from one session, `dashboard/` from
another, and a root-level monitor) were consolidated into this tree during the final
integration; their findings were folded into the Flagged for Review and Questions
registers rather than discarded.

## Pages

| Page | What it does |
|------|--------------|
| `index.html` | Landing dashboard: ranked in-scope markets, live price chart, liquidity by price, event table, resolved markets |
| `pages/executive-summary.html` | What is verified, what is deliberately not claimed, scope and volume |
| `pages/gas.html`, `pages/elections.html`, `pages/culture.html`, `pages/crypto.html`, `pages/golf.html` | One sub-page per in-scope topic |
| `pages/portfolio.html` | Demo-account balance, positions, fills, settlements, and demo order execution |
| `pages/analysis.html` | Market-structure layer plus the trade-review framework and strategy taxonomy |
| `pages/suggestions.html` | Suggested improvements, reviewable before implementation |
| `pages/questions.html` | Question / information / answer register for missing information |
| `pages/verification.html` | Line-by-line verification of every claim against an official source |
| `pages/flagged.html` | Flagged for review: irregularities and unverified items, each with its source |
| `pages/sources.html` | Every official endpoint and document the site relies on |

## Data pipeline

```
scripts/fetch-data.mjs   ->  data/*.json   ->  tools/build_site.py   ->  index.html + pages/*.html
   (GitHub Actions)            (committed)         (committed)
```

* `scripts/fetch-data.mjs` calls only unauthenticated demo endpoints
  (`/series`, `/markets`, `/events`, `/search/tags_by_categories`,
  `/markets/{ticker}/orderbook`). Every request is logged in
  `data/collection-log.json` with its exact URL and HTTP status.
* Topic scope comes from Kalshi's own series `category` and `tags` — no title
  keyword guessing. The allowlists are listed on each category page.
* `tools/build_site.py` renders every page from the snapshot. `tools/check_links.py`
  then verifies internal links, anchors, that every data row carries an API source
  link, and that no placeholder value was rendered.

Run locally:

```bash
python3 tools/build_site.py
python3 tools/check_links.py
python3 -m http.server 8000     # then open http://localhost:8000/
```

## Verification rules

* Every table row links to the exact API response it was read from.
* A field absent from an API response renders as `UNVERIFIED` — never guessed,
  defaulted or interpolated.
* Dollar rankings are **derived** (contracts × last price) and labelled as such;
  `volume_fp` and `open_interest_fp` are contract counts, not dollars.
* The published tables are a ranked sample: rows are ranked first, then capped per
  topic. The cap is recorded in `data/meta.json` and stated on the pages.
* Demo prices and demo outcomes are mock values. Kalshi states they may not
  reflect real markets.

## Security posture

`pages/portfolio.html` signs Kalshi requests in the browser so a demo account can be
inspected and demo orders can be placed. The private key is read from the form into a
page variable only: it is never written to `localStorage`, `sessionStorage`, a cookie
or a log, and it is used for nothing except producing a request signature.

That is still a public page, so treat it as a demo-only tool with a demo key. Moving
signing behind a private backend with a secret manager is tracked as suggestion S2 and
flag F8. Never use a production key here.

## Repository layout

```
assets/style.css      design system
assets/chart.js       canvas price-chart module
assets/app.js         shared client: filters, live polling, chart, order book
assets/portfolio.js   demo portfolio + signed order execution
data/*.json           committed snapshot, one file per topic view
scripts/fetch-data.mjs  the harvester
tools/build_site.py     the site generator
tools/check_links.py    link / source / placeholder checker
.github/workflows/refresh-data.yml  scheduled harvest, build, link check, Pages deploy
```

## Official references

- [Kalshi market data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data)
- [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) · [Get Events](https://docs.kalshi.com/api-reference/events/get-events) · [Get Series List](https://docs.kalshi.com/api-reference/market/get-series-list)
- [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks) · [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook)
- [Get Tags for Series Categories](https://docs.kalshi.com/api-reference/search/get-tags-for-series-categories)
- [Authenticated requests](https://docs.kalshi.com/getting_started/quick_start_authenticated_requests) · [Create Order (V2)](https://docs.kalshi.com/api-reference/orders/create-order-v2) · [Order direction](https://docs.kalshi.com/getting_started/order_direction)
- [Demo environment](https://docs.kalshi.com/getting_started/demo_env) · [Rate limits](https://docs.kalshi.com/getting_started/rate_limits) · [Fixed-point migration](https://docs.kalshi.com/getting_started/fixed_point_migration)
- [GitHub Pages documentation](https://docs.github.com/en/pages)

See [COORDINATION.md](COORDINATION.md) for the session history, claims and verification notes.
