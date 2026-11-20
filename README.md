# Kalshi Demo Dashboard

A live, source-linked dashboard for **Kalshi demo** markets in five topics: **gas prices, elections, culture, crypto
and golf**. Every market row links back to the exact official Kalshi API response it was read from. Nothing on the
site is inferred: a field the API does not return is left blank and marked unverified.

> **Demo environment only.** Kalshi states that demo prices and behaviour may not reflect real markets, and the demo
> environment contains synthetic contracts. Nothing here is trading advice.

**Live site:** <https://karagemop466-tech.github.io/Demo2/>

## What the site does

| Page | What it shows |
|------|----------------|
| `index.html` | Live dashboard: highest-turnover in-scope markets, price chart, orderbook depth, resolution tracking |
| `pages/executive-summary.html` | Executive summary with the key figures and the decisions that are still open |
| `pages/gas.html` · `elections.html` · `culture.html` · `crypto.html` · `golf.html` | One verified table per topic; every row cites its API response |
| `pages/portfolio.html` | Connect a demo account, place demo orders, log trades, categorise them by strategy |
| `pages/analysis.html` | How trades are categorised and what each strategy must clear before it may be reported |
| `pages/suggestions.html` | Ten improvement proposals with an approve / defer / reject review board |
| `pages/questions.html` | What is answered, what is still missing, how to discover it and what it blocks |
| `pages/verification.html` | Every request the collector made, the values it stored and the checks that were run |
| `pages/flagged.html` | Irregularities, constraints and repository issues — for review, not blocking |
| `pages/repo-review.html` | Line-by-line review of every file and every pull request |
| `pages/sources.html` | Every official document and API response used |

## Architecture

```
Kalshi demo API (public, no credentials)
        │
        │  tools/collect_kalshi.py   ← GitHub Actions runner (.github/workflows/collect.yml)
        ▼
   data/*.json   ← committed snapshot, every row keeps its source URL
        │
        │  tools/build_site.py
        ▼
   pages/*.html  ← category and verification pages generated from the snapshot
        │
        │  assets/app.js  ← browser tries the live API first, falls back to data/
        ▼
   GitHub Pages  ← .github/workflows/pages.yml
```

The browser dashboard fetches the live API directly when it can. If it cannot (network or CORS), it switches to the
committed snapshot and says so in its status line rather than presenting a stale value as live.

## Running it locally

```bash
python3 -m http.server 8000      # then open http://localhost:8000/
```

No build step is required — the site is static HTML, CSS and JavaScript.

## Tools

```bash
python3 tools/collect_kalshi.py --out data   # refresh the snapshot (needs outbound access)
python3 tools/build_site.py                  # regenerate the data-driven pages
python3 tools/check_links.py                 # link, anchor and row-source check
python3 tools/test_signing.py                # offline verification of the request signing
python3 tools/kalshi_trade.py --help         # signed command-line API client
```

## Trading from the command line (demo)

Signing follows the official Kalshi specification: the signed message is
`timestamp(ms) + METHOD + path-without-query`; Ed25519 keys sign directly, RSA keys use PSS with SHA-256.

```bash
openssl genpkey -algorithm ed25519 -out kalshi.key
openssl pkey -in kalshi.key -pubout -out kalshi.pub     # register kalshi.pub in the Kalshi demo UI
python3 tools/kalshi_trade.py --key kalshi.key --key-id <KEY_ID> balance
python3 tools/kalshi_trade.py --key kalshi.key --key-id <KEY_ID> place \
        --ticker KX... --side yes --count 10 --price 0.42
```

The private key never leaves the machine. The site also offers an **opt-in** in-browser signer on the Portfolio page;
the key is imported into the page's WebCrypto, is never uploaded, and is discarded on disconnect. Prefer the command
line for anything that matters.

## Security notes

- No credential is stored in this repository, and no credential is required to read the public market data.
- The portfolio and trade figures are blank until a demo key is supplied — the site never shows a placeholder value
  in place of a real one.
- See `pages/flagged.html` (item R1) for the history of an earlier version that pasted a private key into a public
  page, and suggestion S7 for the current options.

## Coordination

`COORDINATION.md` is the shared task board for the sessions that worked on this repository: claims, file scopes,
sources used, verification performed and irregularities found.

## Official references

- [Test in the demo environment](https://docs.kalshi.com/getting_started/demo_env)
- [API environments and endpoints](https://docs.kalshi.com/getting_started/api_environments)
- [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets)
- [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks)
- [Orderbook responses](https://docs.kalshi.com/getting_started/orderbook_responses)
- [Market settlement](https://docs.kalshi.com/getting_started/market_settlement)
- [API keys](https://docs.kalshi.com/getting_started/api_keys)
- [Creating and using a demo account](https://help.kalshi.com/en/articles/13823775-creating-and-using-a-demo-account)
- [GitHub Pages documentation](https://docs.github.com/en/pages)
