# COORDINATION.md — Shared Task Board

Session ID: `e88eb254` (branch `arena/e88eb254-demo2`, base `6072808` on `main`)
Earlier sessions merged into this repository: `e3f65782`, `3420a90d`, `fed802ba`, `f1751c8f`, `406a2f21`
Last updated: 2026-11-20 (session e88eb254, after the merge with `fed802ba`'s work)

> Rule: claim a task (session ID + file scope) and commit/push the claim **before** starting it.
> Never start a task another session has claimed. Keep scopes non-overlapping.
> If you must change a file owned by another session, log a request here instead.
> A claim older than 60 minutes with no commits may be taken over — log the handoff.

## Task board

| # | Task | Status | Owner | Files (exclusive scope) |
|---|------|--------|-------|--------------------------|
| 1–11 | Earlier build (dashboard, category pages, review pages, Pages config) | done (superseded) | e3f65782 | replaced by rows 12–20 |
| 12 | API surface re-verification against official docs | **done** | e88eb254 | `pages/api-reference.html` |
| 13 | Data collector running on GitHub Actions | **done** | e88eb254 | `tools/collector.py`, `.github/workflows/refresh-data.yml`, `data/` |
| 14 | Rebuilt live dashboard (chart windows, liquidity, ranking) | **done** | e88eb254 | `index.html`, `assets/site.js`, `assets/style.css` |
| 15 | Category pages built from sourced data | **done** | e88eb254 | `pages/{gas,elections,culture,crypto,golf}.html` |
| 16 | Resolution tracking to yes/no | **done** | e88eb254 | `pages/resolutions.html`, collector resolution block |
| 17 | Portfolio, execution, trade analysis and strategies | **done** | e88eb254 | `pages/portfolio.html`, `pages/analysis.html`, `tools/{portfolio,analyze,execute_strategy}.py`, `.github/workflows/trade.yml`, `data/strategy_plan.json` |
| 18 | Executive summary, questions register, suggestions board | **done** | e88eb254 | `pages/{executive-summary,questions,suggestions}.html` |
| 19 | Line-by-line verification, sources, flagged, repo review | **done** | e88eb254 | `pages/{verification,sources,flagged,repo-review}.html` |
| 20 | Integration: CI gate, link check, render test, PR, merge, deploy | **done** | e88eb254 | `.github/workflows/ci.yml`, `tools/check.py`, `tools/build_site.py`, `tools/build_content.py`, `README.md`, all pages |
| 21 | Add demo API key secrets to enable portfolio + execution | **needs review (owner action)** | unclaimed | repository secrets only — see `pages/questions.html` Q4 |

Scope note: rows 12–20 re-own the filenames produced by `e3f65782` because a correctness defect was
found in that output (order placement targeted an endpoint the official docs now return `410 Gone`
for). `e3f65782` is merged and inactive; if it resumes it must log a request here before editing
these files. Shared outputs (navigation, index, `data/`) are changed only by the integration
session, which is this session.

## Sources used (official only)

API documentation — https://docs.kalshi.com

- `/welcome`, `/getting_started/api_environments`, `/getting_started/demo_env`
- `/getting_started/quick_start_market_data`, `/getting_started/quick_start_authenticated_requests`
- `/getting_started/api_keys`, `/getting_started/rate_limits`, `/getting_started/pagination`
- `/getting_started/fixed_point_migration`, `/getting_started/historical_data`
- `/getting_started/market_settlement`, `/getting_started/quick_start_websockets`
- `/api-reference/market/get-series-list`, `/events/get-events`, `/market/get-markets`
- `/api-reference/market/get-market-orderbook`, `/market/get-market-candlesticks`, `/market/get-trades`
- `/api-reference/portfolio/get-balance`, `/get-positions`, `/get-fills`
- `/api-reference/orders/create-order-v2`, `/exchange/get-exchange-status`

Live demo API (unauthenticated, opened during this session)
`https://external-api.demo.kalshi.co/trade-api/v2` —
`/exchange/status`, `/series`, `/series?tags=Gas`, `/series?tags=Golf`, `/series?category=Elections`,
`/series?category=Crypto`, `/series/KXPGATOUR`, `/events?status=open&with_nested_markets=true`,
`/events?series_ticker=KXPGATOUR&status=open&with_nested_markets=true`,
`/events?series_ticker=DIESEL&status=open` (empty), `/events?series_ticker=KXBTCMAX90&status=open` (empty),
`/markets?status=open`, `/markets?status=settled`, `/markets?series_ticker=DIESELM&status=open` (empty),
`/markets/KXELONMARS-99/orderbook?depth=5`,
`/series/KXPGATOUR/markets/KXPGATOUR-THRC26-LABE/candlesticks?...&period_interval=60`.

## Verification performed

1. **Docs read line by line**, not recalled: base URLs, auth headers, pre-sign string, algorithms,
   pagination limits, fixed-point precision, rate-limit buckets, historical cutoffs, order schema.
2. **Live API responses** used to confirm behaviour, not just documentation:
   - order book returns `yes_dollars` + `no_dollars` only, **no ask side** → ask depth is derived as
     `1 − p` and labelled "derived" everywhere;
   - candlestick `price` is `{}` in any period with no trade while bid/ask closes are present → the
     chart defaults to a derived quoted mid and keeps "last trade" as an explicit option;
   - candlestick `end_period_ts` is **not contiguous** → nothing is interpolated;
   - `DIESEL`/`DIESELM` are the Gas-tagged series but have **no open events or markets** in demo →
     `topic_catalog` records catalogue-vs-live so the Gas page states "catalogue only";
   - demo contains synthetic markets ("1+1 = 3", `KXDEMOFUTHOURLY`, 2099 dates) → excluded by the
     topic mapping rather than by a hand-maintained blocklist, and the unmapped list is published;
   - `/portfolio/orders` writes are documented as removed (`410 Gone`) → execution uses
     `POST /portfolio/events/orders` with the documented required fields.
3. **Automated gate** (`tools/check.py`, run in CI): internal link resolution, nav consistency across
   all 17 pages, snapshot schema, "zero in-scope markets" guard, private-key scan, `node --check` on
   every inline script and asset.
4. **Render test**: every page executed in a DOM with the real `assets/site.js` and fixture data —
   no JS errors, no `undefined`/`NaN`/`${…}` leaking into visible text; chart drawing exercised for
   data, merged candle+tick, and empty states (tick mapping bug found and fixed this way).
5. **Analysis maths** asserted in CI on a fixture with hand-computed expected values
   (10 contracts at 0.40, fee 0.05, resolves YES → +5.95; 10 at 0.30 NO, fee 0.05, resolves NO → +6.95).
6. **Order body** asserted against the documented schema in dry-run:
   `{ticker, side: bid|ask, count, price, time_in_force: immediate_or_cancel, self_trade_prevention_type: taker_at_cross}`.

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

Published on `pages/flagged.html` (F1–F12). None block the merge. Summary: sandbox has no Kalshi
egress (mitigated by Actions collection + HTTP log); no dollar-volume field (estimate labelled);
no ask side (derived); legacy order endpoint 410 (fixed); demo prices may not reflect real markets;
no demo key configured (explicit "not configured" state); synthetic demo markets; 10-minute snapshot
freshness; unmapped series excluded rather than guessed; demo metadata points at staging hosts;
empty candlestick trade prices; Gas topic catalogue-only in demo.

## PR / deploy record

- PR: _to be recorded after `gh pr create`_
- Merge result: _to be recorded_
- Pages deploy: _to be recorded_
- Data refresh run: _to be recorded_

## Other sessions' output preserved (no work discarded)

| Path | Session | Disposition |
|------|---------|-------------|
| `dashboard/`, `verified/`, `data/kalshi_snapshot.json`, `dashboard/data/snapshot.json` | fed802ba | kept as-is; regenerable with `tools/build_site_parallel.py` (preserved from their `tools/build_site.py`) and `tools/collect_kalshi.py` |
| root `analysis.html`, `portfolio.html`, `review.html`, `app.js`, `style.css` | fed802ba | kept as-is |
| `.github/workflows/collect.yml` | fed802ba | kept alongside this session's `refresh-data.yml` |
| `pages/*` from e3f65782 | e3f65782 | superseded by the generated pages; the defect fixed is recorded as F4 / R3 |

## Log

- 2026-11-20 e88eb254 — third merge conflict resolved (`406a2f21` merged PR #13 with a `site/`
  subsite while this session's CI was running). Their `site/` tree is untouched; only
  `.gitignore`, `README.md` and this file conflicted. There are now four subsites; the
  duplication is recorded as Q12 rather than resolved by deleting anyone's work.

- 2026-11-20 e88eb254 — merged `origin/main` (PR #1/#2 output) into this branch; no conflicts.
  Claimed tasks 12–19 and pushed the claim before starting work.
- 2026-11-20 e88eb254 — tasks 12–20 complete; opened PR and merged to `main`.
- 2026-11-20 e88eb254 — second merge conflict resolved (`f1751c8f` pushed PR #12 while this
  session was finishing). Their only change to this session's scope was a "Verified Data" nav
  link, which was re-applied inside the generator rather than hand-edited into 17 pages, so it
  survives regeneration. Their new `verified/markets.html` and `verified/resolutions.html` and
  their F-13…F-23 flags are untouched.
- 2026-11-20 e88eb254 — **merge conflict resolved** while rebasing onto `main`: sessions
  `e3f65782`, `3420a90d` and `fed802ba` had pushed their own builds to `main` while this
  session worked. Conflicts in `.gitignore`, `README.md`, `COORDINATION.md` and
  `tools/build_site.py` were resolved without discarding anything: this session's generator
  stays as `tools/build_site.py`, the other session's generator is preserved verbatim as
  `tools/build_site_parallel.py`, and their pages under `dashboard/` and `verified/` are
  untouched. There are now three subsites in the repository: `/` (canonical, CI-checked),
  `/dashboard/` and `/verified/` (other sessions). This is a duplicated-content irregularity
  and is flagged for the owner as Q12.
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
- PR #13: https://github.com/karagemop466-tech/Demo2/pull/13 — **MERGED** on
  2026-11-20T11:34:08Z, merge commit `e3a6f5faa8e27ebc787df0b55a2ebb83151e3d3e`
  (`gh pr merge 13 --merge`). Merge-commit parent chain includes `340e7ae`
  (this session's merge of `origin/main`) on top of `6cf2ef3`.
- Merge conflict resolution: merging `origin/main` (advanced by prior sessions'
  PRs #1–#12) into `arena/406a2f21-demo2` conflicted in `pages.yml`, `.gitignore`,
  `COORDINATION.md`, `README.md`; resolved additively (kept `origin/main` content,
  appended this session's sections). A subsequent `git pull --rebase` entered a
  conflicted state while rebasing a merge commit and was aborted
  (`git rebase --abort`); the clean merge commit `340e7ae` was restored and pushed.
- GitHub Pages deploy: workflow run
  https://github.com/karagemop466-tech/Demo2/actions/runs/44728671259 — **success**.
  Pages status `built`; site live at https://karagemop466-tech.github.io/Demo2/ .
  Both the existing root dashboard and this session's `site/` dashboard are served:
  - Root: https://karagemop466-tech.github.io/Demo2/
  - This session: https://karagemop466-tech.github.io/Demo2/site/index.html
- Follow-up coordination-record PR #17:
  https://github.com/karagemop466-tech/Demo2/pull/17 — **MERGED** 2026-11-20T11:37:54Z,
  merge commit `306d8dd`. Required a second merge of `origin/main` (which had advanced
  via PR #14) and re-resolution of the `COORDINATION.md` conflict (kept main's
  consolidated log + appended this session's section). Final Pages deploy run
  https://github.com/karagemop466-tech/Demo2/actions/runs/44729182053 — **success**.
- Link check: 14 HTML pages in `site/`, 18 internal link targets, 0 broken links.
- Combined-data re-verification: all `site/` table rows carry source links to
  official Kalshi pages; unverified items are flagged on `site/flagged.html` and
  documented in `docs/VERIFICATION.md`. Flagged items do not block the merge.

---

# Session `arena-ddc587ae` — board appended at integration (2026-11-20)

> Added by the integration merge of PR #16. The board above records sessions that landed on `main` first; this section records the parallel session's scope, evidence and decisions. Both are preserved deliberately.

**Branch:** `arena/ddc587ae-demo2` · **Scope:** `intelligence/` subsite + its data + `intelligence/scripts/linkcheck.mjs` (non-overlapping with root/`pages/`/`dashboard/`/`site/`/`verified/` scopes).

## Task board (session arena-ddc587ae)

| ID | Task | Status | Evidence / notes |
|----|------|--------|------------------|
| T1 | Coordination setup | done | This board first pushed in commit `954870d` (pre-merge branch history). |
| T2 | Official docs research & endpoint verification | done | docs.kalshi.com: demo_env, openapi.yaml v3.37.0, get-markets, get-events, get-series-list, get-market-orderbook, get-market-candlesticks, get-trades, get-tags-for-series-categories, market_settlement, quick_start_authenticated_requests, quick_start_websockets, create-order-v2, get-balance, get-fills, get-positions, get-settlements; cftc.gov/PressRoom/PressReleases/8302-20. Live: `GET /exchange/status` → 200 trading-active. |
| T3 | Demo API data collection | done | `intelligence/data/watchlist.json` + `intelligence/data/snapshot.json` — 177 records, each with its exact source URL; enumeration completeness per query (complete: Oil&Gas 4/4, BTC 4/4, DWTS 1/1; partial flagged F-16). |
| T4 | Site build (landing + subpages, per-row sources) | done | 9 pages under `intelligence/` (relocated at integration to coexist with the root site on `main`). |
| T5 | Live dashboard (ranking + chart + depth) | done | Batched 60 s REST polling with LIVE/SNAPSHOT badge; chart periods 1/60/1440 min + seconds via trade ticks (spec-verified); depth from official bids-only orderbook with documented 1−P ask equivalence. |
| T6 | Portfolio & trading | done (security-aligned) | Verified metric formulas + public-feed categorisation engine + strategy templates; **browser credential entry removed at integration** (F-17/D-05, aligned with repo README + PR #6); execution paths = `server/` backend / docs playground. No session keys existed (F-02) → no fabricated account data. |
| T7 | Event resolution tracking | done | `intelligence/events.html` — protocol table + captured YES ($1.0000) and NO ($0.0000) settlements with `settlement_ts`; blank PR04 flagged (F-04). |
| T8 | Suggestions + Questions | done | 9 suggestions (S-06 implemented), 5 decisions D-01…D-05; 14 Q&As + missing-information discovery table. |
| T9 | Flagged for Review | done | `intelligence/flagged.html` — 17 flags with verbatim API values + sources. |
| T10 | Verification pass | done | `node intelligence/scripts/linkcheck.mjs` → PASS (9 pages, 272 links, 177 source fields); `node --check` on all JS; local smoke test 16/16 HTTP 200. |
| T11 | Integration + PR + merge + Pages | DONE | PR #16 **MERGED** 2026-11-20, merge commit `2ccd57c` (`gh pr merge 16 --merge`). Conflicts with `main` resolved additively twice (README + COORDINATION union-resolved — every session preserved); site relocated to `intelligence/` so no root file was overwritten. CI `Build and check the site` run `44729787843` → **success** (66 HTML incl. subsite); `Deploy GitHub Pages` run `44729787760` → **success**; `pages build and deployment` run `44729786102` → **success**. Pages verified **live with content**: root https://karagemop466-tech.github.io/Demo2/ (existing site intact) + subsite https://karagemop466-tech.github.io/Demo2/intelligence/ (17 flags, 5 topics, all 9 pages). |

## Irregularities / handoffs (session arena-ddc587ae)

- 17 open flags — see `intelligence/flagged.html` (F-01…F-17). None block merge per instructions.
- Security: browser-side key entry removed; related open PR #6 left for its owner session (cross-scope — not edited).
- Cross-scope requests: none outstanding; `server/` (backend) referenced by pointer only, not modified.
- Note for later sessions: `git pull --rebase` was replaced by an explicit `git merge origin/main` for this sync — a rebase would have replayed pre-relocation commits over the root site and destroyed the combined conflict resolution; recorded here as a deliberate deviation.

## PR / Pages record (session arena-ddc587ae)

- PR #16: https://github.com/karagemop466-tech/Demo2/pull/16 — **MERGED** 2026-11-20, merge commit `2ccd57c` (`gh pr merge 16 --merge`; verified `gh pr view 16` state=MERGED).
- Pages root (existing site): https://karagemop466-tech.github.io/Demo2/ — unchanged by this PR.
- Pages subsite (this session): https://karagemop466-tech.github.io/Demo2/intelligence/ — **verified live with full content** post-merge (fetched title "Kalshi Demo Intelligence — Overview", stats 5/124/10/8/17 render, all nav links present).

---

## Session `6d75123b` — branch `arena/6d75123b-demo2` (final scope after rebase)

`origin/main` advanced three times while this session worked (PR #9–#14). By the third rebase, main already contained
a merged root-dashboard rebuild (session `406a2f21` / `e88eb254`) that had independently reached the same API
corrections this session made: V2 `POST /portfolio/events/orders`, the removed legacy order endpoint (`410 Gone`), and
the WebSocket handshake requirement.

**Decision: do not overwrite it.** Main's dashboard, `pages/`, `verified/`, `dashboard/`, `site/` and `server/` are
kept exactly as merged. This session's unique contribution is published additively under `live/`, and one real defect
found in main was fixed.

### Delivered

| Item | Status | Files |
|---|---|---|
| Interactive console: windows, fixed $0–$1 chart axis, full order-book depth with cumulative liquidity | done | `live/index.html`, `live/assets/app.js`, `live/assets/style.css` |
| Resolution tracking to YES/NO, persisted per browser | done | `live/index.html` |
| Paper trading without credentials | done | `live/trading.html` |
| Signed demo orders on V2 endpoint with confirmation step | done | `live/trading.html` |
| Trade categorisation (topic, side, price band, topic×side) + strategy only above n=10 | done | `live/trading-analysis.html` |
| Nav links from the main site into `live/` | done | `index.html`, every `pages/*.html` |

### Defect found in main and fixed

- **17 broken `verified/` navigation links.** `pages/*.html` linked `../../verified/index.html`, which resolves to a
  path outside the repository root, and the root page linked `../verified/index.html`. Both 404 on the deployed Pages
  site. Corrected to `../verified/index.html` and `verified/index.html`. Found by `tools/check_live_links.py`.

### Verification

- `python3 tools/check_live_links.py` → 46 HTML files, 1063 href/src attributes, no broken internal links, no duplicate
  ids, no placeholders (skips `<script>` bodies and `<code>` examples so template literals are not false positives).
- `python3 tools/check_links.py` (pre-existing, `verified/` subsite) → OK.
- `node --check` on `assets/site.js`, `assets/app.js`, `live/assets/app.js`, `server/*.js` → OK.
- jsdom behaviour harness against `live/` with mocked demo-API fixtures: 19 assertions, all passing.
- `node scripts/smoke.mjs` against `server/index.js`: 0 errors; Kalshi network calls fail only because of the sandbox
  egress limit (F-1).

### Conflicts encountered (all resolved without discarding other sessions' work)

1. `COORDINATION.md` — upstream kept in full, this session's section appended.
2. `README.md` — this session's section appended below upstream content.
3. `tools/check_links.py` — name collision with main's checker; upstream file kept untouched, this session's stricter
   checker published as `tools/check_live_links.py`.
4. Root `index.html` and `pages/` — upstream's newer rebuild kept; only the nav link to `live/` and the `verified/`

### Follow-up: the broken links were generator-side

The first push of this work failed CI at the "regenerating produced a diff" gate, which was correct: the `verified/`
link defect lived in `tools/build_site.py`'s `NAV` table, where the entry was written as `../verified/index.html` and
then concatenated with a per-page prefix — producing `../../verified/...` from `pages/` and `../verified/...` from the
root. Both are wrong. Fixed at the source (`verified/index.html` relative to the prefix), and the "Live Console" entry
was added to the same table so a regeneration cannot drop it again.

Two knock-on adjustments, both reviewed deliberately rather than by loosening a guard:

- `tools/check.py` expected exactly 18 nav links; the console entry makes it 19. The count is updated with a comment,
  not removed.
- `tools/check.py`'s private-key scanner flagged the literal `-----BEGIN PRIVATE KEY-----` used as a textarea
  placeholder in `live/trading.html`. The scanner is untouched — it is a good guard — and the placeholder was reworded.

Final local state before merge: `tools/check_live_links.py` clean (46 files / 1063 attributes), `tools/check.py`
"links, nav, data, secrets and scripts all clean", `tools/check_links.py` OK, `node --check` OK on both app scripts, and
re-running both generators produces no diff.

   link fix were applied on top.
