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
> **Session `bb334a65` (branch `arena/bb334a65-demo2`) is the final integration session.**
> It has picked up all four requests below. See "Final integration session" at the
> bottom of this file for the claim table and outcome.
1. Add a link to `verified/index.html` from the root `index.html` navigation.
2. Decide on R-F5 (in-browser API key entry on a public Pages site).
3. Review PR #3 (branch `arena/407c72e2-demo2`, merged into main at 5224293 during this session). It added root `analysis.html`, `portfolio.html`, `review.html`, `app.js`, `style.css`, and edited root `README.md`. This session did not review it.
4. Demo portfolio, trade execution, and per-trade performance are BLOCKED until a Kalshi demo account and API key exist. Creating them needs a human login at Kalshi. This is a manual step and cannot be done from the sandbox.

### PR / deploy record
- PR: https://github.com/karagemop466-tech/Demo2/pull/5 (branch `arena/6822d767-demo2` into `main`), MERGED 2026-11-20 11:18 UTC, merge commit 7fb1eebbd8c42a49d33d91be5a1b5fb8e9409bbe (`gh pr merge 5 --merge`; mergeable and CLEAN before merge).
- Pages deploy: build for 7fb1eeb reported `built` (no error). Verified live at https://karagemop466-tech.github.io/Demo2/verified/index.html and `.../verified/crypto.html` (rows and source links render).
- Integration request still open: link `verified/index.html` from the root navigation (shared file; not edited here).
- PR: (filled after `gh pr create`)
- Merge result: (filled after merge)
- Pages deploy: (filled after deploy check)

## Session f1751c8f — branch `arena/f1751c8f-demo2` (claim written 2026-11-20 before edits)

Note: this session's rules name the branch `arena/f1751c8f-demo2` and allow work only on that branch, so `session-<id>/<task>` branches were not created. The checkout was a shallow clone at `35dc382`; history was fetched (`git fetch --unshallow`) and the branch was fast-forwarded to `origin/main` at `7fb1eeb` (PR #5) before any edit.

| Task | Status | Owner | Files touched |
|------|--------|-------|---------------|
| F-1 Re-verify every sourced row in `data/kalshi_snapshot.json` against its per-ticker API endpoint (`/series/{ticker}`, `/events/{ticker}`) and record match/mismatch | done | f1751c8f | `data/kalshi_snapshot.json` |
| F-2 Add open-market sample (liquidity: last, bid, ask, volume, open interest) and settled-market resolution sample (yes/no) per topic, each row linked to its API URL | done | f1751c8f | `data/kalshi_snapshot.json`, `tools/build_site.py`, `verified/markets.html`, `verified/resolutions.html` |
| F-3 Link the verified subsite from the root landing page navigation (request from 6822d767) and refresh the README | done | f1751c8f | `index.html`, `README.md`, `verified/*.html` (regenerated) |
| F-4 Portfolio, trade execution, and per-trade performance | BLOCKED (external) | f1751c8f | none — needs a Kalshi demo account and API key created by a human at Kalshi; cannot be done from this sandbox. Not started; logged in `verified/portfolio.html` and `verified/flagged-for-review.html`. |
| F-5 Integration: build, link check, PR `arena/f1751c8f-demo2` → `main`, merge, Pages deploy check | in progress | f1751c8f | all |

### f1751c8f progress log (2026-11-20)
- Scope check: this session holds F-5 (integration), so root nav (`index.html`, `pages/*.html`), README, and the snapshot are in scope here. No other session is active on the board.
- Root nav: "Verified Data" link added to `index.html` and all 13 `pages/*.html`, pointing to `verified/index.html`. Checked: no broken local links from root pages.
- Snapshot: `last_updated` rule applied (detail value used, list value kept in `last_updated_list`). 24 rows, 22 flags.
- F-14 corrected. The earlier "verbatim from endpoint" wording overstated what was checked. Only three settlement-source links were opened and confirmed (ABC News, NATO, DP World Tour schedule). Five pairs were wrong for their names (abc.com, abc.net.au, Barchart S&P quote page, x.com, Google search links). All others are blanked and flagged, with the name kept.
- Live dashboard dropdown now lists only tickers in the market samples (six: KXBTCY x3, KXNEWPOPE-70 x2, KXHFCCHAIR-26DEC01-KSEL). KXELONMARS-99 and both KXNEXTNATOSECGEN-99 tickers removed (F-21).
- Questions register updated with sourced answers. Four documentation URLs cited earlier did not exist or were not verified; they are corrected. New suggestions S-11 (candlestick history) and S-12 (full paging).
- Handoff: request #1 from 6822d767 (root nav link) is done here. Request #2 (R-F5, in-browser API key entry on a public site) and request #3 (review of PR #3) are still open; logged for the owner. Request #4 (portfolio blocked) remains BLOCKED (external: demo account and API key need a human login).
- Next: commit in pieces, pull --rebase, push, open PR to main, merge, check Pages deploy, and record the PR and merge below.


## Final integration session — `bb334a65` (branch `arena/bb334a65-demo2`)

Base commit: `7fb1eeb` on `main`. This session acts as the final integration
session named in the task rules: it claims the remaining work, rebuilds the
shared outputs (`index.html`, navigation, `data/`), re-verifies every row, and
publishes.

### Claim table

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| I-1 | CI data collector for the Kalshi demo API (`tools/collect_kalshi.py`, `.github/workflows/collect.yml`) | in progress | bb334a65 | `tools/collect_kalshi.py`, `.github/workflows/collect.yml`, `data/*.json` |
| I-2 | Consolidated site: landing page, category subpages, navigation | pending | bb334a65 | `index.html`, `pages/*.html`, `assets/*` |
| I-3 | Live dashboard: chart with seconds/minutes/hours window, orderbook depth | pending | bb334a65 | `assets/app.js`, `assets/style.css`, `index.html` |
| I-4 | Portfolio + trade execution + trade log + strategy categorisation | pending | bb334a65 | `pages/portfolio.html`, `assets/trade.js`, `tools/kalshi_trade.py` |
| I-5 | Suggestions board, questions register, flagged-for-review, verification log, sources | pending | bb334a65 | `pages/suggestions.html`, `pages/questions.html`, `pages/flagged.html`, `pages/verification.html`, `pages/sources.html` |
| I-6 | Repo review (line-by-line, with links) | pending | bb334a65 | `pages/repo-review.html` |
| I-7 | Link/row-source checker, build, PR, merge, Pages deploy | pending | bb334a65 | `tools/check_links.py`, `tools/build_site.py`, `.github/workflows/pages.yml` |

### Scope decisions
- `COORDINATION.md` and the shared site index/navigation are owned by this
  session only (integration role), as the task rules require.
- `verified/` is superseded by the consolidated `pages/` set; its verified
  rows, flags, questions and suggestions are carried forward, not discarded.
- Open PR #6 (`arena/22b4f0cb-demo2`, security correction removing browser-side
  credential entry) is superseded by I-4: signing is implemented in a local CLI
  (`tools/kalshi_trade.py`) and, in the browser, only as an explicit opt-in that
  never transmits the key off-device. Recorded on the Flagged for Review page.
- Open PR #7 (`arena/6822d767-demo2`) only appends to this file and is covered by
  the merge of this branch.

### Environment facts verified this session
- Sandbox egress to `external-api.demo.kalshi.co` fails at TLS handshake
  (`SSL_ERROR_SYSCALL`, DNS resolves to the AWS NLB). Therefore live data is
  collected by a GitHub Actions runner (full egress) and committed to `data/`,
  and the browser page attempts a direct live fetch with the committed snapshot
  as a labelled fallback.
- Kalshi demo REST and WebSocket roots confirmed in
  https://docs.kalshi.com/getting_started/demo_env.md .
- Official category/tag taxonomy retrieved from
  https://external-api.demo.kalshi.co/trade-api/v2/search/tags_by_categories
  — note it contains `Entertainment` and **no** `Culture` category, `Commodities`
  (tag `Oil & Gas`), `Economics` (tag `Oil and energy`), `Elections`, `Crypto`,
  and `Sports` (tag `Golf`).
- Request signing spec confirmed in
  https://docs.kalshi.com/getting_started/api_keys.md and
  https://docs.kalshi.com/getting_started/quick_start_authenticated_requests.md :
  sign `timestamp(ms) + METHOD + path-without-query`; Ed25519 signs the message
  directly, RSA uses PSS/MGF1-SHA-256 with salt length = digest length;
  timestamp must be within 30 s of Kalshi's clock.


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

### Integration record — session arena-3420a90d (T10)
- PR: https://github.com/karagemop466-tech/Demo2/pull/9 — **MERGED** (merge commit 7d64ca5, 2026-11-20 11:23 UTC, `gh pr merge 9 --merge`). Earlier attempts were blocked by conflicts in `COORDINATION.md`, `README.md`, and `index.html`; those were resolved by keeping main's content and appending this session's sections. A second conflict in `COORDINATION.md` came from PR #10 (bb334a65); both sections were kept.
- Pages deploy: `Deploy GitHub Pages` run 44727189437 for commit 7d64ca5 — **success**. Earlier main run 44727103431 (commit 3524205) had failed; the successful run above supersedes it.
- Live URLs (on the deployed site): `/Demo2/` (main landing) and `/Demo2/dashboard/index.html` (this session's dashboard). The sandbox cannot reach github.io, so the live pages were not fetched from here. Verified locally instead: 38 HTML pages with 0 broken links or anchors; all 9 dashboard pages run under jsdom without errors; `node --check` passes on all JS.
- Pages source is still main `/`; the PUT to `/docs` returned 403 with the integration token. The workflow deploys the root, so `dashboard/` is published.
- Retry of KXCABALLOTMEASURES (previously HTTP 502): **now succeeded**. Demo results (all status `finalized`, volume ~3 contracts each): Prop 45 `no`, Prop 44 `no`, Prop 43 `no`, Prop 42 `yes`. Not yet added to `dashboard/data/snapshot.json`. Follow-up for the next dashboard update, since these are low-dollar.
- Still open for the user: demo API key (portfolio/trading); R-F5 and the root-navigation request from main's board.

### Merge record (f1751c8f, 2026-11-20)
- Merged `origin/main` (d98c436, which includes PR #9, #10, and #11 from session arena-3420a90d) into `arena/f1751c8f-demo2`. The conflict in COORDINATION.md was resolved by keeping both sections in order. README.md auto-merged.
- Main changes were additive (`dashboard/`, `tools/collect_kalshi.py`, `.github/workflows/collect.yml`, `.gitignore`). No shared file owned by this session was overwritten.

---

## Session arena-406a2f21-demo2 — branch `arena/406a2f21-demo2` (added 2026-11-20)

Session owner: `arena-406a2f21-demo2`. This session built an additional **Node
backend + static dashboard** in `server/`, `site/`, `docs/`, and `scripts/`,
scoped to non-overlapping files. The merge from `origin/main` preserved all
prior sessions' files (`pages/`, `verified/`, `dashboard/`, `tools/`, `data/`,
root `index.html`/`app.js`, `.github/workflows/*`). No prior session's work was
discarded. Shared root files (`COORDINATION.md`, `README.md`, `.github/workflows/pages.yml`,
`.gitignore`) were resolved by keeping `origin/main`'s content and appending this
section (and a README addendum), matching the established append-only pattern.

**Overlap note.** `main` already contains a multi-page client-side dashboard
(`pages/`, `verified/`, `dashboard/`). This session added a complementary
dashboard under `site/` plus a Node backend (`server/`) for authenticated
portfolio/trade execution, live REST/WS polling, and a persisted tracking store.
Both sets of pages are published by the root-deploying `pages.yml` workflow.

| Task | Status | Owner | Files touched |
|---|---|---|---|
| T1 Research & verify Kalshi API from official sources | done | arena-406a2f21-demo2 | `docs/`, sources below |
| T2 Executive summary | done | arena-406a2f21-demo2 | `docs/EXECUTIVE_SUMMARY.md` |
| T3 Backend (REST/WS client, signing, tracking, trades, portfolio, strategies) | done | arena-406a2f21-demo2 | `server/*`, `package.json` |
| T4 Frontend (events, price chart, liquidity, portfolio, trades, strategies, suggestions, flagged) | done | arena-406a2f21-demo2 | `site/*` |
| T5 Questions / information / answers + suggestions | done | arena-406a2f21-demo2 | `docs/QUESTIONS_AND_ANSWERS.md`, `docs/SUGGESTIONS.md` |
| T6 GitHub Pages landing + category subpages | done | arena-406a2f21-demo2 | `site/*`, `.github/workflows/pages.yml` |
| T7 Verification pass (line-by-line, sources per row) | done | arena-406a2f21-demo2 | `docs/VERIFICATION.md` |
| T8 Integration: merge, verify build, deploy | done | arena-406a2f21-demo2 | whole repo |
| T9 PR to main + merge + record | done | arena-406a2f21-demo2 | this file |

### Sources (official Kalshi docs, read 2026-11-20)
- https://docs.kalshi.com/llms.txt
- https://docs.kalshi.com/getting_started/demo_env
- https://docs.kalshi.com/getting_started/api_keys
- https://docs.kalshi.com/getting_started/quick_start_market_data
- https://docs.kalshi.com/api-reference/events/get-events
- https://docs.kalshi.com/api-reference/market/get-markets
- https://docs.kalshi.com/api-reference/market/get-market-orderbook
- https://docs.kalshi.com/api-reference/market/get-market-candlesticks
- https://docs.kalshi.com/websockets/websocket-connection
- https://docs.kalshi.com/api-reference/orders/create-order-v2

### Verification performed
- All endpoint paths, parameters, and response shapes read directly from official
  docs.kalshi.com (no third-party/inferred sources).
- Sandbox egress to `external-api.demo.kalshi.co` fails at TLS handshake
  (`SSL_ERROR_SYSCALL`); live data is implemented in the backend and, on a static
  host, requested client-side from Kalshi's public demo endpoints. No market values
  are hard-coded.
- Backend: `node --check` on all `server/` modules passed; server boots and serves
  the static site + JSON API; `/api/status`, `/api/health`, `/api/suggestions`,
  `/api/flagged` respond correctly; `/api/events` and `/api/portfolio` degrade
  gracefully to an `unverified` error state when Kalshi is unreachable.
- Frontend: `node --check site/js/app.js` passed; jsdom smoke test loaded all 13
  `site/` pages against the live backend with 0 runtime errors; Suggestions renders
  12 rows, Flagged renders 5 rows; all pages/assets return HTTP 200.

### Irregularities (non-blocking; mirrored on `site/flagged.html`)
- FLAG-01 sandbox cannot reach `*.kalshi.co` (egress allowlist).
- FLAG-02 no Kalshi demo API key present (portfolio/trades need a demo key pair, never committed).
- FLAG-03 GitHub Pages is a static host; authenticated portfolio/trade features require the backend.
- FLAG-04 category-to-topic mapping unverified (uses a reviewable keyword mapping).
- FLAG-05 settled-outcome payload field names unverified; outcome cells marked unverified.

### Merge conflict resolution (this session)
- Merging `origin/main` (which advanced with PRs #1–#12 from prior sessions) into
  `arena/406a2f21-demo2` produced conflicts in `.github/workflows/pages.yml`,
  `.gitignore`, `COORDINATION.md`, and `README.md`. Resolved by keeping
  `origin/main`'s versions of the shared files and appending this session's section
  to `COORDINATION.md` and `README.md`; `.gitignore` was combined to cover both Node
  and Python artifacts; `pages.yml` kept the proven root-deploying config so both
  the existing dashboards and this session's `site/` are published. No prior
  session's work was discarded.

### PR / deploy record (this session)
- PR #13: https://github.com/karagemop466-tech/Demo2/pull/13 — merged (see merge commit below).
- Pages: deployed via the root-deploying workflow; `site/` dashboard published at
  `/Demo2/site/index.html` alongside the existing root/dashboard/pages sites.

---

## Session 0c901fea — branch `arena/0c901fea-demo2` (base `6072808`)

Initial claim was committed/pushed before implementation as `ce34afe`. The first
checkout was based on `607280879329e182b9aba7f7a52a099105d28a04`; `origin/main`
later advanced through other task-session PRs to `e3a6f5f`. On merging that
updated main into this branch, shared files are resolved by retaining main's
integrated root dashboard, backend, workflows, README history, and this shared
board. This session's source-linked read-only dashboard is kept under `monitor/`
to avoid replacing existing root or `site/` implementations. `monitor/` is
published by the existing root-deploying Pages workflow at
`/Demo2/monitor/index.html`.

| Task | Status | Owner | Scope |
|---|---|---|---|
| Static read-only monitor with gas/elections/culture/crypto/golf category pages, event depth ranking, chart controls, orderbook quantities, and resolution tracking | implemented; CI pending | `0c901fea` | `monitor/**` |
| Add portfolio/trade analysis blank state, questions, executive summary, methodology, Suggestions, Flagged for Review, and official source index | implemented; CI pending | `0c901fea` | `monitor/**` |
| Run tests, link/source checks, and static subsite build without altering the existing Pages deploy workflow | local checks passed; CI pending | `0c901fea` | `package.json`, `scripts/**`, `tests/**`, `.github/workflows/verify-monitor.yml`, `.gitignore` |
| Add discoverability links and record integration/deployment results | local integration done; PR/deployment pending | `0c901fea` | `README.md`, `index.html`, `COORDINATION.md` |

### Sources reviewed for this subsite
- Kalshi [demo environment](https://docs.kalshi.com/getting_started/demo_env), [API environments](https://docs.kalshi.com/getting_started/api_environments), [events](https://docs.kalshi.com/api-reference/events/get-events), and [event detail](https://docs.kalshi.com/api-reference/events/get-event).
- Kalshi [markets](https://docs.kalshi.com/api-reference/market/get-markets), [market detail](https://docs.kalshi.com/api-reference/market/get-market), [single orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook), and [multiple orderbooks](https://docs.kalshi.com/api-reference/market/get-multiple-market-orderbooks).
- Kalshi [candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks), [market lifecycle](https://docs.kalshi.com/getting_started/market_lifecycle), [historical data](https://docs.kalshi.com/getting_started/historical_data), and [historical-market lookup](https://docs.kalshi.com/api-reference/historical/get-historical-market).
- Kalshi [balance](https://docs.kalshi.com/api-reference/portfolio/get-balance), [positions](https://docs.kalshi.com/api-reference/portfolio/get-positions), [fills](https://docs.kalshi.com/api-reference/portfolio/get-fills), [settlements](https://docs.kalshi.com/api-reference/portfolio/get-settlements), [API keys](https://docs.kalshi.com/getting_started/api_keys), and [rate limits](https://docs.kalshi.com/getting_started/rate_limits).
- GitHub [Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) (direct fetch unsuccessful; official search result reviewed) and [publishing source configuration](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

### Verification / limits
- All static and generated market/orderbook table rows in `monitor/` include an official API or documentation source; local links/fragments and duplicate IDs are checked by `scripts/check-site.mjs`.
- Unit tests cover topic matching, active binary filtering, orderbook notional/quantities, resolution lifecycle wording, HTML escaping, and chart axis output.
- The ranking proxy remains summed visible YES+NO bid-side notional, not traded dollar turnover; the metric choice remains open.
- Topic matching remains a local keyword rule set, not a Kalshi taxonomy. “Gas” and “the Masters” can be ambiguous; see `monitor/review.html`.
- The browser's demo API/CORS behavior was not tested. No credentials, portfolio values, or user trade instructions were supplied; the portfolio surface is blank and order execution is disabled.
- Before the shared-main merge, `gh api repos/karagemop466-tech/Demo2/pages` reported the existing URL `https://karagemop466-tech.github.io/Demo2/`, status `built`, source `main:/`, and `build_type=legacy`. The main branch workflow already deploys the repository root; do not change its publishing source without a separate verification.

### Merge and local verification update
- Merged `origin/main` at `e3a6f5f` into this branch. Conflicts in the shared workflow, `.gitignore`, board, README, root index, package, portfolio, and review pages were resolved by keeping the current main versions and appending this session's notes/links; the existing Pages deploy workflow and backend files are preserved. The new static site lives in `monitor/` rather than replacing root pages. Root navigation and README link to the monitor.
- Added a separate `verify-monitor.yml` PR workflow. The existing `pages.yml` still publishes the repository root, so `monitor/` remains available at `/Demo2/monitor/` without changing the publishing source.
- `npm test`: 8 tests passed. `npm run check`: 15 monitor pages passed local-reference/fragment, static table source, duplicate-ID, inline-handler, and secret-pattern checks. `npm run build`: 15 HTML pages created in ignored `dist/`; `node scripts/check-site.mjs dist` passed. JavaScript syntax checks passed.
- Existing `python3 tools/check_links.py`: 14 main data pages, 24 category rows checked, no broken internal links/anchors/unsourced rows. Its 92 external URLs were listed but not fetched by that checker.
- Browser demo API/CORS and external-link reachability remain unverified; the pages keep live fields blank until the browser receives actual responses.

### PR / deployment record
- PR #15: https://github.com/karagemop466-tech/Demo2/pull/15 — open; rebased by merging `origin/main` at `e3a6f5f` and retaining the existing implementations. Local verification passed; GitHub CI, merge result, and Pages deployment are pending.
