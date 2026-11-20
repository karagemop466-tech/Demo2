# Kalshi Demo Intelligence

Source-linked analytics site for the **Kalshi demo exchange** — built on official endpoints only
(`https://external-api.demo.kalshi.co/trade-api/v2`), with a live dashboard, event-to-resolution
tracking, price/liquidity charts, portfolio analysis and an open review queue.

**Live site:** https://karagemop466-tech.github.io/Demo2/ (GitHub Pages, deploys from `main` root)

## What's here

| Path | Purpose |
| --- | --- |
| `index.html` | Landing page — status, verification model, navigation |
| `executive-summary.html` | What/where/how verified: API surfaces, endpoints, headline findings |
| `dashboard.html` + `assets/dashboard.js` | Highest-dollar live events (5 topics), chart (s–min–h–day), order-book depth |
| `events.html` | Open events on watch + YES/NO resolutions with settlement evidence |
| `portfolio.html` | Performance, trade categorisation, strategy templates (personal data gated by demo API keys) |
| `trading.html` + `assets/auth.js` | Create Order (V2) ticket with browser-side RSA-PSS/Ed25519 signing |
| `suggestions.html` | Improvement queue with For review → Decided → Implemented workflow |
| `questions.html` | Answers from official sources + missing-information discovery |
| `flagged.html` | All unverified / derived / irregular items with source links |
| `data/watchlist.json` | Topic → official series queries (completeness recorded) + series rows |
| `data/snapshot.json` | Verified captures: events, markets, resolutions, orderbooks, candlesticks, trades |
| `scripts/linkcheck.mjs` | Build-time verification: internal links + every data row has a source URL |
| `COORDINATION.md` | Multi-session task board / change log |

## Data rules (enforced)

1. **Every table row links to its source** — the JSON records embed the exact official URL they
   were read from; `scripts/linkcheck.mjs` fails the build if one is missing.
2. **Unconfirmable values stay blank** and render as *“— blank (unverified)”* — never inferred.
3. **Derived metrics** (e.g. `volume_24h_fp × last_price_dollars`) are labelled *derived*
   everywhere and listed on the Flagged page (F-01).
4. **Demo ≠ production** — official docs warn demo prices/behaviour may not reflect real markets.

## Running locally

```bash
python3 -m http.server 8080   # any static server works; no build step
node scripts/linkcheck.mjs    # link + source verification
```

The dashboard prefers live API polling in the visitor's browser and falls back to the bundled
verified snapshots (mode is always displayed).

## Documentation & governance

- Official docs: https://docs.kalshi.com (demo environment: `docs/getting_started/demo_env`)
- Regulator record: KalshiEX LLC designated a Contract Market (DCM) — https://www.cftc.gov/PressRoom/PressReleases/8302-20
- Coordination, tasks, PR record: [`COORDINATION.md`](COORDINATION.md)
