# Live console and trading (`live/`)

An additive subsection of the Kalshi demo dashboard. It does not replace or modify the root dashboard, the `pages/`
research set, `verified/`, `dashboard/` or `site/` — it links to them.

**Live:** https://karagemop466-tech.github.io/Demo2/live/

| Page | Purpose |
|---|---|
| [`live/index.html`](index.html) | Interactive console: five-topic market table ranked by notional, price chart with 60 s / 5 m / 15 m / 1 h / 6 h windows, live order book with contracts at each price and cumulative depth, resolved feed, markets tracked until YES/NO |
| [`live/trading.html`](trading.html) | Paper-trade simulator (no key); authenticated account access and order submission intentionally disabled |
| [`live/trading-analysis.html`](trading-analysis.html) | Trades bucketed by topic, side, entry-price band and topic × side; a bucket must reach 10 trades before a pattern is described |

## What is different here

The root dashboard shows the same markets as static snapshots produced by the monthly collector. This subsection adds
what a static table cannot do:

1. **A selectable-time price chart** built from live REST snapshots taken while the page is open, on a fixed $0–$1
   axis so a small move is not exaggerated by a zoomed scale.
2. **Full order-book depth** — price, contracts resting at that level, cumulative contracts, and dollar value per level
   for both YES and NO, with best bid, the implied ask (1 − best NO bid) and the spread.
3. **A resolution tracker** that remembers markets you have viewed and flips them to the YES/NO the exchange reports.
4. **Trade analysis** from a local paper simulator that needs no credentials. Authenticated account access and
   live order submission are intentionally disabled (see Security below).

## Two things to know before trusting a number

- **"Highest dollar amount" is an inference.** Kalshi reports `volume_fp` and `open_interest_fp` as *contract counts*,
  never dollar turnover. This console shows two labelled proxies — notional traded (volume × last price) and notional
  open interest — and lets you sort by either. Recorded as flag **F-2** on
  [`pages/flagged.html`](../pages/flagged.html).
- **Topic scope is a keyword heuristic.** There is no official "gas prices" or "culture" filter in the API. The keyword
  list is printed on each category page so it can be audited. Recorded as flag **F-3**.

## Endpoints used (all from the browser, all demo)

```
GET  /markets?status=open              market table
GET  /markets?status=settled           resolved feed and paper-trade settlement
GET  /markets/{ticker}                 selected market snapshot
GET  /markets/{ticker}/orderbook       depth: [price_dollars, count_fp], ascending, best bid last
GET  /portfolio/balance                signed — needs your demo key
GET  /portfolio/positions              signed
GET  /portfolio/fills                  signed
GET  /portfolio/settlements            signed
POST /portfolio/events/orders          signed — V2 order entry (legacy /portfolio/orders returns 410 Gone)
```

Verified against official documentation; see [`pages/verification.html`](../pages/verification.html) for the quoted
wording and [`pages/sources.html`](../pages/sources.html) for the reference list.

## Security

Authenticated account access and order submission are **intentionally disabled** in this static client. A public
GitHub Pages application has no trusted server to protect a private signing key, so browser-side key entry would
expose the key to site scripts and any compromise of the hosting origin. The credential-entry UI and browser-side
signing have been removed. Portfolio reads and demo order execution require a separately secured backend that stores
credentials in a secret manager, authenticates the account owner, and logs activity. The trade-off is recorded as
question **Q-2** on [`pages/questions.html`](../pages/questions.html) and proposal **S-9** on
[`pages/suggestions.html`](../pages/suggestions.html).

Demo money only. Demo prices are not real market prices
([demo environment docs](https://docs.kalshi.com/getting_started/demo_env)).
