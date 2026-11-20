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
| `intelligence/` | session `arena-ddc587ae` | Source-linked subsite (dashboard, resolutions, portfolio analysis, trading request-builder, review queue, 17 flags) with per-row source data |
| `pages/executive-summary.html` | The whole build in one screen, plus what is still open |
| `pages/gas.html` … `golf.html` | One page per topic: live markets, resolved outcomes, series in scope |
| `pages/resolutions.html` | Everything settled, with the official yes/no result |
| `pages/portfolio.html` | Demo balance, positions, fills, executions |
| `pages/analysis.html` | Cost/payout/realised P&L per fill, five categorisations, strategy candidates |
| `pages/suggestions.html` | Eight proposals to review and choose between before anything changes |
| `pages/questions.html` | Eleven questions, what is known, what is missing, how to find it |
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

## Other material in this repository

Two earlier/parallel sessions produced their own separate subsites. They are preserved
rather than deleted, because they contain independently verified research:

| Path | Origin | Why it is still here |
|------|--------|----------------------|
| `dashboard/`, `verified/`, `dashboard/data/snapshot.json`, `data/kalshi_snapshot.json` | session `fed802ba` | Independently collected demo data and a per-topic research write-up; regenerable with `tools/build_site_parallel.py`, `tools/collect_kalshi.py` |
| `analysis.html`, `portfolio.html`, `review.html`, `app.js`, `style.css` (root) | session `fed802ba` | Earlier standalone pages |
| `site/` | session `406a2f21` | Its own live dashboard, market, portfolio, trades and strategies pages |
| `pages/executive-summary.html` … `pages/sources.html` | session `e3f65782` | Superseded by the pages generated from `tools/build_site.py` + `tools/build_content.py` |

The canonical, CI-checked site is `index.html` plus `pages/`, generated from `tools/`.

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

---

## Kalshi Demo Intelligence (`intelligence/` — session arena-ddc587ae)

A self-contained, source-linked subsite added by session `arena-ddc587ae` (PR #16), living entirely under `intelligence/` so the sites above are untouched:

- **Pages:** landing, executive summary (API surfaces + verified endpoints), live dashboard (top-dollar event ranking for gas/elections/culture/crypto/golf, price chart with Seconds/Minutes/Hours/Days, order-book depth ladder), events & resolutions (YES/NO settlement evidence), portfolio analysis + strategy templates, trading, suggestions (review -> decide -> implement workflow), Q&A, and Flagged for Review (17 flags).
- **Data:** `intelligence/data/watchlist.json` (official series queries with enumeration-completeness flags) and `intelligence/data/snapshot.json` (events, markets, resolutions, orderbooks, candlesticks, trade ticks) — every record embeds the exact official source URL.
- **Verification:** `node intelligence/scripts/linkcheck.mjs` -> internal links + per-row source fields must pass (it does).
- **Trading is security-aligned (F-17/D-05):** the page builds the official Create Order (V2) body and a signed curl export with environment placeholders — it accepts **no credentials**, consistent with the safety notice above and PR #6. Execution happens through the `server/` backend, the Actions-based executor, or the official docs playground.
- **Live data:** dashboard polls the public demo REST API from the visitor browser (60 s, batched) with an explicit LIVE/SNAPSHOT mode badge and bundled verified snapshots as fallback.

Serve locally with `python3 -m http.server 8000` and open `/intelligence/`.

---

## `live/` — interactive console, trading and trade analysis

Additive subsection (does not modify the dashboard, `pages/`, `verified/`, `dashboard/` or `site/`):

- **`live/index.html`** — interactive console: five-topic market table, price chart with 60 s / 5 m / 15 m / 1 h / 6 h
  windows on a fixed $0–$1 axis, full order-book depth (contracts resting at each price, cumulative depth, dollar value
  per level, best bid, implied ask and spread), resolved feed and a markets-tracked-until-YES/NO list.
- **`live/trading.html`** — paper-trade simulator needing no key, plus real demo-account reads and signed V2 demo
  orders (`POST /portfolio/events/orders`) for anyone who supplies their own demo key.
- **`live/trading-analysis.html`** — trades bucketed by topic, side, entry-price band and topic × side; a bucket needs
  10 trades before a pattern is described.

Verified in a jsdom harness with fixtures modelled on the documented response shapes: market filtering (including
exclusion of an out-of-scope market), order-book best bid / implied ask / spread / cumulative-depth arithmetic, chart
windows, offline error state with no fabricated values, paper-trade validation, and analysis withholding below
threshold.

### Fixed here: broken `verified/` links

Navigation links to the `verified/` subsite were pointing one directory too high
(`pages/*.html` → `../../verified/index.html`, which resolves outside the repository root, and the root page →
`../verified/index.html`). On the deployed Pages site every one of those links 404s. All 17 were corrected to
`../verified/index.html` (pages) and `verified/index.html` (root). `tools/check_live_links.py` is the checker that
found it and will catch any recurrence.

### Checkers

```bash
python3 tools/check_links.py        # verified/ subsite + sourced data rows (pre-existing)
python3 tools/check_live_links.py   # every HTML file: internal links, duplicate ids, stray placeholders
```
