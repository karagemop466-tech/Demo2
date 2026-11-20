# COORDINATION.md — Shared Task Board

Session ID: `fed802ba` (branch `arena/fed802ba-demo2`, base `35dc3822` on `main`)
Last updated: 2026-11-20

> Single-session execution: all tasks below are claimed by this session.
> No other session is active in this checkout. If another session starts,
> it must claim a non-overlapping scope here first.

## Task board

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| 1 | Repo review + official source verification | done | e3f65782 | `pages/sources.html`, `pages/verification.html` |
| 2 | Executive summary | done | e3f65782 | `pages/executive-summary.html` |
| 3 | Live dashboard (markets, chart, orderbook) | done | e3f65782 | `index.html`, `assets/app.js`, `assets/style.css` |
| 4 | Category subpages (gas/elections/culture/crypto/golf) | done | e3f65782 | `pages/gas.html`, `pages/elections.html`, `pages/culture.html`, `pages/crypto.html`, `pages/golf.html` |
| 5 | Portfolio + trade execution + analysis | done | e3f65782 | `pages/portfolio.html`, `assets/app.js` |
| 6 | Resolution tracking (yes/no) | done | e3f65782 | `index.html`, `pages/portfolio.html` |
| 7 | Suggestions review board | done | e3f65782 | `pages/suggestions.html` |
| 8 | Questions / missing-information register | done | e3f65782 | `pages/questions.html` |
| 9 | Flagged for Review page | done | e3f65782 | `pages/flagged.html` |
| 10 | GitHub Pages deploy config | done | e3f65782 | `.github/workflows/pages.yml` |
| 11 | Final integration + link check + PR | in progress | fed802ba | all |

## Sources used (official only)

- https://docs.kalshi.com/welcome
- https://docs.kalshi.com/getting_started/demo_env
- https://docs.kalshi.com/getting_started/api_environments
- https://docs.kalshi.com/getting_started/making_your_first_request
- https://docs.kalshi.com/getting_started/quick_start_market_data
- https://docs.kalshi.com/getting_started/quick_start_authenticated_requests
- https://docs.kalshi.com/getting_started/api_keys
- https://docs.kalshi.com/api-reference/market/get-markets

## Verification performed

- Demo REST base `https://external-api.demo.kalshi.co/trade-api/v2` and WS
  `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` confirmed on
  demo_env + api_environments pages.
- Public endpoints need no auth; portfolio/trading need signed API keys
  (RSA-PSS/SHA-256 or Ed25519, ms timestamp, 30s tolerance) — confirmed on
  quick_start pages + api_keys page.
- Sandbox egress to Kalshi API fails (TLS `SSL_ERROR_SYSCALL`); live data
  is therefore fetched client-side in the visitor's browser. No market
  values are hard-coded — see Flagged for Review.

## Verification performed — session fed802ba (2026-11-20)

All claims re-checked against official Kalshi docs (docs.kalshi.com) on 2026-11-20:

| Claim checked | Official source | Status |
|---|---|---|
| Demo REST base `https://external-api.demo.kalshi.co/trade-api/v2`; also `https://demo-api.kalshi.co/trade-api/v2` | https://docs.kalshi.com/getting_started/demo_env | Verified |
| Demo WS `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2`; also `wss://demo-api.kalshi.co/trade-api/ws/v2` | https://docs.kalshi.com/getting_started/demo_env + api_environments | Verified |
| Demo = mock funds; prices may not reflect real markets | https://docs.kalshi.com/getting_started/demo_env | Verified |
| Public market-data endpoints need no auth | https://docs.kalshi.com/getting_started/quick_start_market_data | Verified |
| Get Markets fields (ticker, title, subtitle, yes/no bid/ask dollars, last_price_dollars, volume_fp, result, settlement_value_dollars, settlement_ts, close_time, status, cursor pagination) | https://docs.kalshi.com/api-reference/market/get-markets | Verified |
| Orderbook `yes_dollars`/`no_dollars` = [price, count] strings, ascending, no asks (reciprocal), depth param, empty arrays valid | https://docs.kalshi.com/getting_started/orderbook_responses | Verified |
| Auth headers KALSHI-ACCESS-KEY/TIMESTAMP/SIGNATURE; sign timestamp+method+path (no query); RSA-PSS/SHA-256 or Ed25519; 30s tolerance | https://docs.kalshi.com/getting_started/quick_start_authenticated_requests + api_keys | Verified |
| GET /portfolio/balance, /portfolio/positions, /portfolio/fills, POST /portfolio/orders | https://docs.kalshi.com/getting_started/quick_start_authenticated_requests | Verified |

Link check: 17 HTML files, 276 internal links resolved, 0 broken.
JS syntax: `node --check assets/app.js` and `node --check app.js` passed.
No secrets or hard-coded market values in the repo; live values come only from the visitor's browser.

## Irregularities / handoffs

- See `pages/flagged.html`. None block merge per instructions.
- No merge conflicts encountered (single session, clean tree).

## PR / deploy record

- PR: (to be filled after `gh pr create`)
- Merge result: (to be filled)
- Pages deploy: (to be filled)

## Update 2026-11-20 (post-merge)
- PR #1: https://github.com/karagemop466-tech/Demo2/pull/1 — MERGED (merge commit acf8ef38292d7aaff1591a077742798b3a0ddde2)
- Pages: https://karagemop466-tech.github.io/Demo2/ (legacy build from main /)

## Follow-up integration update — branch `arena/407c72e2-demo2`

- This checkout found that `origin/main` had advanced with PR #1 and already contains the complete multi-page dashboard. To avoid overwriting that work, retained the existing `index.html`, `.github/workflows/pages.yml`, and this coordination board from `origin/main`; additional root-level analysis, portfolio-safe-state, and review pages are additive. README now explains both sets of pages and security cautions.
- Added links and analysis references based on official docs: market data quick start, orderbook schema, WebSocket quick start, events endpoint, portfolio balance endpoint, order guide, and changelog.
- Follow-up implementation: `analysis.html`, `portfolio.html`, `review.html`, root `app.js` and `style.css`; does not alter existing `pages/` content or `assets/` implementation. The root portfolio page purposely exposes no account metrics and no trade form.
- Verification: `node --check app.js` passed; checked local links in the newly added root pages before reconciliation. Existing site remains unchanged after resolving rebase conflicts by retaining the main versions.
- Rebase conflict encountered after `origin/main` advanced. Preserved main's shared dashboard, workflow, and coordination content; no main implementation was discarded. Root README was updated to document the additional pages, and any earlier branch-only top-level monitor mockup was omitted because it conflicted with main's dashboard landing page. Follow-up run of the main site's link checker and deployment is still required.
- PR #3: https://github.com/karagemop466-tech/Demo2/pull/3 — MERGED 2026-11-20; merge commit `5224293c8b48b9b7f8a6ed3b8b4f2c5556115c24`.
- GitHub Pages deployment run `44726290846` completed successfully after the merge. Site URL: https://karagemop466-tech.github.io/Demo2/ . No branch status checks were reported; local HTML link checks and JavaScript syntax checks passed.

## Session 6822d767 — branch `arena/6822d767-demo2`

Note: this session's rules name the branch `arena/6822d767-demo2` and allow work only on that branch, so `session-<id>/<task>` branches were not created. Claims below were written after work began (the board was read first, then the work was scoped to avoid overlap). No other session's files were edited.

| Task | Status | Owner | Files touched |
|------|--------|-------|---------------|
| V-1 Row-level verified data tables (gas, elections, culture, crypto, golf); each row links to the Kalshi API response it came from | done | 6822d767 | `verified/gas-prices.html`, `verified/elections.html`, `verified/culture.html`, `verified/crypto.html`, `verified/golf.html`, `data/kalshi_snapshot.json` |
| V-2 Flagged for Review register (data + repo irregularities, with source links) | done | 6822d767 | `verified/flagged-for-review.html`, `verified/repo-review.html` |
| V-3 Questions, suggestions (choice board, nothing implemented), portfolio/trade status | done | 6822d767 | `verified/questions.html`, `verified/suggestions.html`, `verified/portfolio.html`, `verified/index.html` |
| V-4 Live price chart and orderbook depth (browser polls the demo API; CORS not verified) | done, browser test pending | 6822d767 | `verified/live-dashboard.html`, `verified/assets/live.js` |
| V-5 Build and link check tooling | done | 6822d767 | `tools/build_site.py`, `tools/check_links.py`, `verified/assets/style.css`, `verified/assets/suggestions.js` |

### Sources (official Kalshi docs and API responses, read 2026-11-20)
- Demo env: https://docs.kalshi.com/getting_started/demo_env.md
- Fixed-point fields (`_fp` = contracts, `_dollars` = prices): https://docs.kalshi.com/getting_started/fixed_point_migration.md
- Get Market: https://docs.kalshi.com/api-reference/market/get-market.md · Get Markets: https://docs.kalshi.com/api-reference/market/get-markets.md · Orderbook: https://docs.kalshi.com/api-reference/market/get-market-orderbook.md
- API keys: https://docs.kalshi.com/getting_started/api_keys.md · Demo account help: https://help.kalshi.com/en/articles/13823775-creating-and-using-a-demo-account
- Market settlement (Yes/No pays $1 per contract): https://docs.kalshi.com/getting_started/market_settlement.md
- API responses observed (demo root): `/series?category=Economics|Elections|Culture|Crypto`, `/series?tags=Golf`, `/events?status=open&limit=200`, `/search/tags_by_categories`

### Verification performed
- 24 data rows copied from the observed JSON responses. Blank fields are left blank, never inferred.
- Only the first page of each query was read (pagination not followed). Stated on every affected page and in flag F-12.
- `python3 tools/check_links.py`: 12 pages, 24 sourced rows, zero broken internal links or anchors. External links are listed but not fetched by the script. Key external docs were fetched and checked by hand.
- Both JavaScript files pass `node --check`.

### Irregularities (non-blocking, see `verified/flagged-for-review.html`)
- Demo data includes 2099 close dates and "demo strike" fields (F-01). Demo prices may not reflect real markets (Kalshi's own warning).
- Volume fields are contract counts, not dollars (F-02). The "highest dollar amount" ranking is not computed.
- KXRIQUAHOG settlement source is a NY Fed SOFR page (F-03). KXBTCMAX130 ticker and title disagree (F-04). Placeholder and Google-search settlement sources on KXXBANNED* (F-05).
- "Culture" is a series category but not in `tags_by_categories`; Golf is a tag under Sports (F-11).
- Repo: main's Pages workflow and dashboard are live; README says keys are pasted in-browser on the Portfolio page (R-F5, security review requested).

### Requests to the final integration session (shared files, not edited here)
1. Add a link to `verified/index.html` from the root `index.html` navigation.
2. Decide on R-F5 (in-browser API key entry on a public Pages site).
3. Review PR #3 (branch `arena/407c72e2-demo2`, merged into main at 5224293 during this session). It added root `analysis.html`, `portfolio.html`, `review.html`, `app.js`, `style.css`, and edited root `README.md`. This session did not review it.
4. Demo portfolio, trade execution, and per-trade performance are BLOCKED until a Kalshi demo account and API key exist. Creating them needs a human login at Kalshi. This is a manual step and cannot be done from the sandbox.

### PR / deploy record
- PR: https://github.com/karagemop466-tech/Demo2/pull/5 (branch `arena/6822d767-demo2` into `main`), MERGED 2026-11-20 11:18 UTC, merge commit 7fb1eebbd8c42a49d33d91be5a1b5fb8e9409bbe (`gh pr merge 5 --merge`; mergeable and CLEAN before merge).
- Pages deploy: build for 7fb1eeb reported `built` (no error). Verified live at https://karagemop466-tech.github.io/Demo2/verified/index.html and `.../verified/crypto.html` (rows and source links render).
- Integration request still open: link `verified/index.html` from the root navigation (shared file; not edited here).

---

## Session arena-3420a90d — branch `arena/3420a90d-demo2` (added 2026-11-20)

Session owner: `arena-3420a90d`. Work was scoped to the new folder `dashboard/` plus this section. Shared root files (`index.html`, `README.md` top section, `pages/`, `verified/`, `tools/`, `.github/workflows/pages.yml`) were **not** rewritten. The merge from `origin/main` kept their content. Those sessions' claims are untouched.

**Overlap note.** `main` already contains a multi-page site (`pages/`, `verified/`). This session added a separate dashboard at `dashboard/` with different page coverage (Resolutions, Live tape, Portfolio status, Analysis, Suggestions with Approve/Defer/Reject, Questions, Flagged). The integration session should decide whether to consolidate the two sites. Consolidating is not done here, so no working pages are removed.

| Task | Status | Owner | Files touched |
|---|---|---|---|
| T0 Board/claims | done | arena-3420a90d | `COORDINATION.md` |
| T1 Executive summary | done | arena-3420a90d | `dashboard/index.html` |
| T2 Markets tables (Gas, Crypto, Elections, Culture, Golf) | done | arena-3420a90d | `dashboard/markets.html`, `dashboard/data/snapshot.json` |
| T3 Resolutions (YES/NO) | done | arena-3420a90d | `dashboard/resolutions.html` |
| T4 Live dashboard (price chart, live tape, orderbook) | done | arena-3420a90d | `dashboard/live.html`, `dashboard/assets/live.js` |
| T5 Portfolio & trades | **blocked** (needs Kalshi demo API key; no trades placed) | arena-3420a90d | `dashboard/portfolio.html` |
| T6 Analysis | done (hypotheses only) | arena-3420a90d | `dashboard/analysis.html` |
| T7 Suggestions (decision-first) | done | arena-3420a90d | `dashboard/suggestions.html` |
| T8 Questions | done | arena-3420a90d | `dashboard/questions.html` |
| T9 Flagged for Review | done (F1–F15, constraints U1–U8) | arena-3420a90d | `dashboard/flagged.html` |
| T10 Integration (merge `main`, link + script checks, PR, merge, Pages) | in progress | arena-3420a90d | `COORDINATION.md`, `README.md` (appended section), `dashboard/` |

### Sources (official)
- Kalshi docs: `docs.kalshi.com/getting_started/api_environments` · `/api-reference/market/get-markets` · `/api-reference/market/get-series-list` · `/api-reference/market/get-market-candlesticks` · `/getting_started/orderbook_responses` · `/getting_started/market_settlement` · `/getting_started/rate_limits` · `/getting_started/quick_start_websockets` · `/getting_started/api_keys`
- Demo API responses (read via the sandbox fetch tool, which can reach Kalshi; sandbox bash cannot): `https://external-api.demo.kalshi.co/trade-api/v2/series/KXAAAGASM`, `/markets?series_ticker=KXAAAGASM|KXBTCMINY|KXPGATOP40`, `/markets?tickers=…`, `/markets/{ticker}/orderbook?depth=5`, `/series/KXBTCMINY/markets/…/candlesticks`, `/series?category=Crypto|Elections|Culture|Sports`, `/series?tags=Golf`, `/series/KXELONMARS`, `/events?status=open&with_nested_markets=true`
- Production API (read-only comparison): `https://external-api.kalshi.com/trade-api/v2/series/KXAAAGASM`

### Verification performed
- Every snapshot row cites the API URL it was read from. Blanks are marked UNVERIFIED and never filled in.
- Re-fetched after drafting: gas 4.80 and 4.70 quotes (`markets?tickers=`); BTC 50k orderbook top bid $0.23 matches the market `yes_bid`, and implied YES ask $0.24 matches `yes_ask`; KXELONMARS series and event source lists (F13 corrected to the event).
- Link check: all relative links in `dashboard/*.html` resolve. Each page's inline and `assets/*.js` scripts parse with `node --check`. All 9 pages were executed under jsdom against `data/snapshot.json` with no script errors.

### Irregularities (non-blocking; see `dashboard/flagged.html`)
- F1–F2 placeholder and search-engine settlement sources (KXXBANNED*, KXCABALLOTMEASURES, KXTALARICO…, KXELONMARS-99).
- F3 demo vs production metadata differs (KXAAAGASM `fee_type`, contract URL staging S3 vs assets).
- F4 docs status-enum mismatch (filter enum unopened/open/paused/closed/settled vs schema initialized/inactive/active/closed/determined/disputed/amended/finalized; responses use `active`/`finalized`).
- F5 last trade outside current quote (KXBTCMINY-27JAN01-50000.00: last $0.50, quote $0.23/$0.24).
- F6 one-sided quote with large open interest (KXAAAGASM-26NOV30-4.80: OI 55,567.52; bid $0.00 / ask $1.00).
- F7 missing metadata (KXDOGEPERP); F8 demo-only synthetic markets; F9 category mapping ("Gas prices" = Economics/Oil & Gas tag; "Golf" = Sports tag); F10 contracts not dollars; F11 markdown in titles; F12 gas close_time before measurement date; F13 event vs series settlement-source mismatch (KXELONMARS-99 vs KXELONMARS); F14 HTTP 502 on one request; F15 tracking parameter in a settlement URL.

### Handoffs / conflicts
- Merge conflict with `origin/main` (advanced by sessions fed802ba / 6822d767 / 407c72e2): `COORDINATION.md`, `README.md`, `index.html` (add/add). Resolved by keeping `origin/main` versions of these shared root files and appending this session's section. No other session's work was discarded. Recorded here.
- Pages settings: the integration token returned HTTP 403 on `PUT /repos/.../pages`. The workflow `pages.yml` on `main` deploys the repo root, so `dashboard/` is published with it. No Pages setting was changed.

### Not done / blocked (requires user action)
- Portfolio, balances, trade execution and per-trade P&L need a Kalshi **demo API key** created by a human login. Not available in this workspace. No trades were placed and no values were invented.
