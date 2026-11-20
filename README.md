# Kalshi Demo Dashboard

A live, sourced dashboard for Kalshi **demo** markets in five topics only — **gas prices,
elections, culture, crypto, golf**. It ranks the highest-dollar live events, charts contract price
against time with selectable windows, shows how many contracts are available at each price, tracks
every event until it resolves **yes** or **no**, reports demo-account performance, categorises
trades and proposes strategies only when the evidence supports them.

**Site:** https://karagemop466-tech.github.io/Demo2/

Demo environment only. Mock funds. Not investment advice.

## Pages

| Page | What it answers |
|------|-----------------|
| `index.html` — Dashboard | Ranked in-scope markets, price-vs-time chart (60 s → 7 d), order-book depth, recent resolutions |
| `pages/executive-summary.html` | The whole build in one screen, plus what is still open |
| `pages/gas.html` … `golf.html` | One page per topic: live markets, resolved outcomes, series in scope |
| `pages/resolutions.html` | Everything settled, with the official yes/no result |
| `pages/portfolio.html` | Demo balance, positions, fills, executions |
| `pages/analysis.html` | Cost/payout/realised P&L per fill, five categorisations, strategy candidates |
| `pages/suggestions.html` | Eight proposals to review and choose between before anything changes |
| `pages/questions.html` | Ten questions, what is known, what is missing, how to find it |
| `pages/api-reference.html` | Every endpoint used, verified line by line against official docs |
| `pages/verification.html` | Claim → official source → how it was checked → status, plus the live API log |
| `pages/flagged.html` | Irregularities and judgement calls, with mitigations |
| `pages/repo-review.html` | What was wrong in the repo before and what changed |
| `pages/sources.html` | All official sources |

## How the data flows

```
GitHub Actions (every 10 min)            static site (GitHub Pages)
tools/collector.py  ──► data/*.json ──►  pages read the snapshot
   │  official demo Trade API            no secrets in the browser
   └─ writes an HTTP log per request      missing values render as "—"
```

The authoring sandbox cannot reach `external-api.demo.kalshi.co` (TLS handshake fails), so
collection runs where egress works and every snapshot carries the status code of every request.
Nothing is hard-coded into the HTML.

## Trade execution

Read-only by default. Three independent gates must all be open before a demo order is sent:

1. repository secrets `KALSHI_DEMO_API_KEY_ID` and `KALSHI_DEMO_PRIVATE_KEY`;
2. repository variable `KALSHI_TRADING_ENABLED=1`;
3. the order passes the executor's checks — ticker in the collector's in-scope set, no duplicate
   tickers, and inside the per-run notional cap (default $25).

Orders use `POST /portfolio/events/orders` with the documented V2 body. The legacy
`POST /portfolio/orders` is **not** used: it returns `410 Gone`
([Create Order (V2)](https://docs.kalshi.com/api-reference/orders/create-order-v2)).

## Publishing

GitHub Pages serves `main` from the repository root (build type: legacy). Every workflow in this
repository commits to `main` and rebases before pushing, so a data refresh and a page change cannot
clobber each other:

- `Refresh Kalshi demo data` — every 10 minutes, commits `data/`
- `Demo portfolio, analysis and (optional) execution` — hourly, commits reporting artefacts
- `Build and check the site` — on every push and PR; fails on a broken link, an out-of-date page,
  a bad snapshot, a leaked key or a JS syntax error
- `Deploy GitHub Pages` — publishes the repository as-is when Pages is set to the GitHub Actions
  source; with the current legacy source GitHub's own build publishes `main` instead

A `.nojekyll` file is present so no asset is filtered out by Jekyll processing.

## Local development

```bash
cd tools && python3 build_site.py && python3 build_content.py && cd ..
python3 tools/check.py          # links, nav, data, secrets, inline JS
python3 -m http.server 8000     # then open http://localhost:8000/
```

Regenerate the pages after editing anything in `tools/`; CI fails if the generated HTML and the
generator disagree.

## Verification policy

Every table row links an official source. If a value cannot be confirmed from an official Kalshi
source it is left blank and flagged rather than inferred. Open items live on
`pages/flagged.html` and `pages/questions.html`.
