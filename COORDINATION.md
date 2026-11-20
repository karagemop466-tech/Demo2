# COORDINATION.md — Shared Task Board

Session ID: `e3f65782` (branch `arena/e3f65782-demo2`, base `6072808` on `main`)
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
| 11 | Final integration + link check + PR | in progress | e3f65782 | all |

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
- PR: (filled after `gh pr create`)
- Merge result: (filled after merge)
- Pages deploy: (filled after deploy check)
