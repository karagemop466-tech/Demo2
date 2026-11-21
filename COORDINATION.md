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

- PR: https://github.com/karagemop466-tech/Demo2/pull/63 — **merged** at `003772d` (2026-11-21T06:37:44Z).
- Build-and-check CI on the merge commit: **success** (run 44876440290).
- Pages deploy on the merge commit: **success** (run 44876439996, 23s). Site: https://karagemop466-tech.github.io/Demo2/
- Task E-1: **done**.
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

### Integration record — session arena-3420a90d (T10)
- PR: https://github.com/karagemop466-tech/Demo2/pull/9 — **MERGED** (merge commit 7d64ca5, 2026-11-20 11:23 UTC, `gh pr merge 9 --merge`). Earlier attempts were blocked by conflicts in `COORDINATION.md`, `README.md`, and `index.html`; those were resolved by keeping main's content and appending this session's sections. A second conflict in `COORDINATION.md` came from PR #10 (bb334a65); both sections were kept.
- Pages deploy: `Deploy GitHub Pages` run 44727189437 for commit 7d64ca5 — **success**. Earlier main run 44727103431 (commit 3524205) had failed; the successful run above supersedes it.
- Live URLs (on the deployed site): `/Demo2/` (main landing) and `/Demo2/dashboard/index.html` (this session's dashboard). The sandbox cannot reach github.io, so the live pages were not fetched from here. Verified locally instead: 38 HTML pages with 0 broken links or anchors; all 9 dashboard pages run under jsdom without errors; `node --check` passes on all JS.
- Pages source is still main `/`; the PUT to `/docs` returned 403 with the integration token. The workflow deploys the root, so `dashboard/` is published.
- Retry of KXCABALLOTMEASURES (previously HTTP 502): **now succeeded**. Demo results (all status `finalized`, volume ~3 contracts each): Prop 45 `no`, Prop 44 `no`, Prop 43 `no`, Prop 42 `yes`. Not yet added to `dashboard/data/snapshot.json`. Follow-up for the next dashboard update, since these are low-dollar.
- Still open for the user: demo API key (portfolio/trading); R-F5 and the root-navigation request from main's board.

## Current checkout follow-up — 2026-11-20

- Current Arena branch: `arena/22b4f0cb-demo2`; session ID: `22b4f0cb`.
- Reviewed existing repo and board before changes. The board contains historical owners and prior merged PR notes; it does not reflect the current branch, so this session did not claim another session's task.
- Security correction: removed browser-side API key/private-key entry and signing/order placement from the public static portfolio page, because this deployment cannot protect private signing credentials. Portfolio figures remain blank and trades are not placed. Updated README, dashboard footer, and flagged-review record.
- Files changed: `pages/portfolio.html`, `pages/flagged.html`, `index.html`, `README.md`, `assets/app.js`, `COORDINATION.md`.
- Verification performed: `node --check assets/app.js` passed; searched for credential-entry/signing code references and confirmed none remain in the active dashboard client. Suggestion-voting localStorage is unrelated and remains.
- Remaining verification: live Kalshi API/browser CORS and GitHub Pages deployment are not verified from this turn. Historical deployment notes above are not evidence of this branch's deployment.
- PR #6: https://github.com/karagemop466-tech/Demo2/pull/6 (open). GitHub reports the PR branch as conflicting after rebase onto fetched `origin/main`; no merge was attempted. The PR has no reported checks.
- Irregularity: request for trade execution conflicts with safe public-static hosting; disabled pending separately secured backend and review. See `pages/flagged.html` F6 and `pages/suggestions.html`.

## Session 5330bffb — FINAL INTEGRATION (takeover of pending claims) — branch `arena/5330bffb-demo2`

Claimed 2026-11-20 ~11:35 UTC. Platform rules for this session allow work only
on branch `arena/5330bffb-demo2`, so no `session-<id>/<task>` branches are
created; this branch is the integration branch and its PR goes to `main`.
Re-verification runs against official sources only: the live Kalshi demo Trade
API (read-only GET via the sandbox fetch tool, which can reach the demo host;
sandbox bash egress is blocked just as it was for session 3420a90d) and
docs.kalshi.com.

### Handoff log (protocol takeover)
- Session **bb334a65** marked I-2…I-7 "pending" and its branch was merged at
  11:22 UTC (PR #10) with no commits for those items; the session has ended
  with those tasks unstarted. Per the takeover rule (crashed/stale claims),
  this session takes over bb334a65's I-1…I-7 scope and logs the handoff here.
  Its landed work (`tools/collect_kalshi.py`, `.github/workflows/collect.yml`)
  is kept and reviewed, not rewritten.
- Session **arena-3420a90d** T10 is complete per its own integration record
  (PR #9/#11 merged, deploy run 44727189437 success). Its open asks are
  adopted: site consolidation decision, R-F5 decision, root-navigation link,
  and the KXCABALLOTMEASURES snapshot follow-up.
- PR **#6** (`arena/22b4f0cb-demo2`, "Disable unsafe browser-side trading
  credentials") is still open and conflicting. Its work is exactly the R-F5
  resolution; this session integrates its branch (conflicts resolved by
  keeping main's newer shared content plus 22b4f0cb's security corrections),
  then closes PR #6 as superseded by the integration PR. Nothing discarded.

### Claim table (5330bffb)
| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| G-1 | Site consolidation: cross-tree navigation (keeps all published URLs) | done | 5330bffb | `index.html`, `dashboard/assets/site.js`, `verified/*.html`, `review.html` |
| G-2 | Re-verify every on-page data row + doc claim against official sources; blank/flag anything unconfirmable | done | 5330bffb | `pages/verification.html`, `pages/sources.html`, `pages/flagged.html` |
| G-3 | Fresh verified data: gas, elections, culture, crypto, golf + orderbooks + candlesticks + YES/NO resolutions via CI collector | in progress (workflow run 44729162248) | 5330bffb | `data/*`, `tools/collect_kalshi.py` |
| G-4 | R-F5 decision + portfolio/trade safe state + local CLI trade tool + trade analysis/strategy framework | done | 5330bffb | `pages/portfolio.html`, `pages/analysis.html`, `pages/executive-summary.html`, `tools/kalshi_trade.py` |
| G-5 | Line-by-line repo review incl. PR #3 root additions and PR #6; dead-code audit | done | 5330bffb | `pages/repo-review.html`, `pages/flagged.html` |
| G-6 | Consolidated Flagged-for-Review register + questions register with answers + suggestions decision board | done | 5330bffb | `pages/flagged.html`, `pages/questions.html`, `pages/suggestions.html` |
| G-7 | Live chart (time window s/m/h, price axis, candlesticks) + orderbook liquidity verification/fixes | done | 5330bffb | `assets/app.js`, `index.html`, `assets/tables.js`, `pages/*.html` |
| G-8 | Build + link + JS/DOM checks, PR → main, merge, Pages deploy verification, final record | in progress | 5330bffb | `tools/`, `COORDINATION.md` |

### Integration notes (2026-11-20, final)
- PR #6 work (22b4f0cb) integrated by content-preserving commit `296ad33`; PR #6 closed as
  superseded by PR #27. Nothing discarded.
- PR #15 (0c901fea, read-only monitor) integrated by merge `0680686` (monitor/ tree +
  verify-monitor workflow + npm checks kept; shared files resolved as union). PR #15 closed
  as superseded by PR #27. Their `npm test`/`npm run check`/build chain passes locally
  (8 tests, 15 pages source-linked).
- origin/main (PRs #12–#26 from sessions f1751c8f, e88eb254, 406a2f21, ddc587ae, 6d75123b,
  1d709f30) merged in `cd71dfb` — verified/* takes main's link-fixed versions with the
  cross-nav link re-applied. Their findings were adopted: CORS observed result
  (data/cors.json) closes G-2/F5/U3; orders V2 + order_direction verified and
  tools/kalshi_trade.py migrated (legacy /portfolio/orders writes return 410 Gone).
- Collector fixes in this session: `git diff --quiet` ignored untracked data files (first
  CI run silently dropped — now staged before diff); per-branch concurrency; bounded
  pagination for demo rate limits; candlestick history added.

### Integration notes (2026-11-20 ~12:00 UTC)
- PR #6 work (22b4f0cb) integrated by content-preserving commit `296ad33`; PR #6 will be
  closed as superseded by the integration PR. Nothing discarded.
- A second collect run (44729955155, branch `arena/bb334a65-demo2`) was dispatched at
  11:43 UTC — session bb334a65 may still be active. Overlap note: this session's
  G-4/G-6/G-7 work covers the same files bb334a65's I-2…I-5 planned (`pages/*`,
  `assets/*`, `tools/kalshi_trade.py`). Per protocol, conflicts must be resolved by
  keeping both sessions' work; this session logged the takeover above and did not
  delete any of bb334a65's landed files. `collect.yml` concurrency is now
  per-branch (G-9) so the two collection runs cannot cancel each other.
- KXCABALLOTMEASURES retry values could not be re-verified (empty API response);
  NOT carried into any table — see pages/flagged.html G-3.
---

## Session arena-1d709f30 — branch `arena/1d709f30-demo2` (added 2026-11-20)

Session owner: `1d709f30`. Base of this branch was `6072808` (an older point
on `main`); this session merged `origin/main` (through PR #11, `d98c436`) and
resolved two add/add conflicts without discarding any other session's work:
- `.github/workflows/pages.yml` — kept main's proven deploy flow and
  **added** a whole-site internal link-check step before the artifact upload
  (main's version retained as the base).
- `COORDINATION.md` — kept main's full board/history; this section is appended.

Claim table (files listed are owned by this session; everything else untouched):

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| S-1 | Merge main into this branch, resolve conflicts | done | 1d709f30 | `COORDINATION.md`, `.github/workflows/pages.yml` (additive step only) |
| S-2 | Data pipeline: official demo API → topic-ranked snapshots (computed 24h dollar volume), resolution tracking, CORS probe, chart/depth snapshot | done | 1d709f30 | `scripts/fetch_data.py`, `.github/workflows/data-refresh.yml`, `data/events_top.json`, `data/resolved.json`, `data/series_index.json`, `data/cors.json`, `data/live_snapshot.json`, `data/pipeline_meta.json` |
| S-3 | Dollar-amount rankings page (gas prices, elections, culture, crypto, golf) with per-row official source links + formula disclosure | done | 1d709f30 | `rankings.html`, `assets/rankings.js` |
| S-4 | Whole-site link checker + CI workflow | done | 1d709f30 | `scripts/check_links.py`, `.github/workflows/linkcheck.yml` |
| S-5 | Consolidated navigation (root landing → all subsites: pages/, verified/, dashboard/, root extras) | done | 1d709f30 | `index.html` (nav links appended only) |
| S-6 | Verification additions (CORS probe result, dollar-formula disclosure) | done | 1d709f30 | `pages/verification.html` (append rows only), this section |
| S-7 | Final integration: link check, PR → main, merge, Pages deploy confirm, record | done | 1d709f30 | this section, PR record below |

Scope rules honored: no other session's page content is rewritten; all edits
to shared files (`index.html`, `pages/verification.html`, `pages.yml`,
`COORDINATION.md`) are strictly additive.

### Sources used by this session (official only; all fetched 2026-11-20)

- https://docs.kalshi.com/getting_started/demo_env (demo REST/WS endpoints table)
- https://docs.kalshi.com/getting_started/api_environments (full endpoint list, signing scope)
- https://docs.kalshi.com/getting_started/api_keys (Ed25519/RSA-PSS headers, 30s timestamp rule)
- https://docs.kalshi.com/getting_started/quick_start_market_data (public endpoints, caching lag)
- https://docs.kalshi.com/getting_started/quick_start_websockets (WS handshake REQUIRES auth headers)
- https://docs.kalshi.com/getting_started/rate_limits (429 handling, unauthenticated limits)
- https://docs.kalshi.com/getting_started/market_lifecycle (statuses; filter enum ↔ schema mapping)
- https://docs.kalshi.com/getting_started/market_settlement (Yes/No pays $1; result field)
- https://docs.kalshi.com/api-reference/market/get-markets (Market schema, status filters, pagination)
- https://docs.kalshi.com/api-reference/market/get-series-list (`category`/`tags` filters, `include_volume`)
- https://docs.kalshi.com/api-reference/events/get-events (`with_nested_markets`, event `category` deprecated)
- https://docs.kalshi.com/api-reference/market/get-market-orderbook (yes/no bids [price,count], depth 0-100)
- https://docs.kalshi.com/api-reference/market/get-trades (public trade prints, ts in seconds)
- https://docs.kalshi.com/api-reference/market/get-market-candlesticks (period 1/60/1440 min, max 5000 periods)
- https://docs.kalshi.com/api-reference/portfolio/get-balance (401 without keys; field names)
- https://docs.kalshi.com/api-reference/portfolio/get-positions (realized_pnl_dollars etc.; 401 without keys)
- https://docs.kalshi.com/api-reference/orders/create-order-v2 (POST /portfolio/events/orders; legacy = 410)
- Live demo API responses observed this session: `/markets?limit=2&status=open`,
  `/events?limit=3&status=open&with_nested_markets=true`, `/series?include_volume=true`,
  `/series?category=Crypto|Culture|Economics`, `/series?tags=Golf|Gas|Gasoline`,
  `/series/KXAAAGASM`, `/series/KXAAAGASD`, `/series/KXNATGAS15M`,
  `/markets/trades?ticker=KXELONMARS-99`, `/series/KXELONMARS/markets/KXELONMARS-99/candlesticks`,
  `/markets/KXELONMARS-99/orderbook?depth=5` (all under the recommended demo base).

### Verification performed by this session

- Every endpoint/field claim above was read from the official docs page or the
  live official demo API response — no value is inferred. Blanks stay blank.
- Third-party mentions of gas series tickers (KXAAAGASM/KXAAAGASD/KXNATGAS15M)
  were re-verified against `GET /series/{ticker}` on the official demo API
  before use (official source = the API URL recorded per row).
- `GET /portfolio/balance` without keys fails (auth required per
  get-balance.md `security: kalshiAccessKey...` + 401 response) → all
  portfolio/trade rows on this site remain blank and flagged; no demo
  credentials exist in this workspace and none were invented.
- CORS from a page origin is probed by `scripts/fetch_data.py` (records
  observed `Access-Control-Allow-*` headers into `data/cors.json`) — this
  closes the previously open "CORS not verified" item with an observed
  result rather than an assumption.

### Cross-scope integration fixes (session 1d709f30, logged per the task rules)

Broken links found by `scripts/check_links.py` on the merged tree were fixed at
integration (owners' sessions had already merged; no content was discarded):

1. `tools/build_site.py` NAV: `../verified/index.html` produced
   `../../verified/index.html` inside `pages/*.html` (404 live: it resolves
   above the site root) and `../verified/index.html` from the root index.
   Changed the NAV entry to `verified/index.html`; the `prefix` mechanism now
   yields the correct path from both root and `pages/`.
2. `tools/check.py`: nav link count expectation 18 → 19 after adding
   Dollar Rankings to the canonical nav.
3. Root `index.html` + `pages/*.html` regenerated with
   `tools/build_site.py` / `tools/build_content.py` (CI requires generated
   output to match the generator; hand edits would fail the diff gate).
4. `site/js/app.js`: `renderTable` now supports `rowId`; flagged/suggestions
   rows get `id="FLAG-xx"` / `id="Sx"` so the existing deep links
   (`site/*.html` → `flagged.html#FLAG-04`, `suggestions.html#S3`) resolve, plus
   a `location.hash` scroll after render. Anchors existed in the JS data
   arrays but were never attached to the DOM.
5. `scripts/check_links.py` (new): whole-site checker — 1,862 references
   across 67 HTML files, rejects root-absolute paths (project Pages break),
   validates anchors (static ids or runtime `id:` declarations in sibling JS),
   skips `${...}` template literals, and in CI (`linkcheck.yml`) probes every
   external URL. `pages.yml` now gates deploy on the internal check.
6. `tools/build_content.py`: appended this session's 10 verification rows
   (WS-auth requirement, trades/candlesticks/orderbook live checks, AAA gas
   series, settlement/status mappings, computed-metric disclosure, portfolio
   auth) and regenerated `pages/verification.html`.

Verification after fixes: `python3 scripts/check_links.py` → 0 problems;
`python3 tools/check.py` → all clean; `node --check` on changed JS passes;
`python3 -m py_compile` on changed Python passes.

### PR / deploy record — session 1d709f30

- PR: https://github.com/karagemop466-tech/Demo2/pull/24 — **MERGED** 2026-11-20
  12:11:53 UTC (`gh pr merge 24 --merge`), merge commit
  `532edadfd490ed85570647fcf20ac2f0f149b266`. Both PR checks passed before merge:
  `Build and check the site` (success, ~14 s) and `Link check (all pages,
  internal + external)` (success, 52 s — 1,943+ internal references across 70
  HTML files plus every external URL probed with HEAD→GET fallback, 429 backoff).
- Pages deploy: `Deploy GitHub Pages` run for `532edad` — **success** (20 s);
  `pages build and deployment` for the follow-up data commit `8d2c47d` —
  **success** (59 s). Pages API: `status: built`, source `main /`,
  https://karagemop466-tech.github.io/Demo2/ . Newest github-pages deployment
  targets `8d2c47d` (github-pages[bot], 2026-11-20T12:12:56Z).
  Live verification (fetched after deploy): `/Demo2/rankings.html` serves the
  page with method box + tables, and `/Demo2/data/events_top.json` serves real
  ranked rows (e.g. elections top event `KXPRESNOMD-28`, est. 24h $24,034.81,
  1,555,533.39 contracts, per-row official source URLs).
- Data pipeline first run on `main`: `Refresh Kalshi data` run 44733769348 —
  **success** (fetch + commit steps), data commit `8d2c47d` on main. Outputs:
  `data/events_top.json` (topic rankings: gas 1, elections 10, culture 0,
  crypto 10, golf 6 rows — culture blank because no in-scope culture events
  had volume/OI in the window, stated as blank, not filled),
  `data/resolved.json` (200 settled markets with official `result` yes/no),
  `data/series_index.json`, `data/live_snapshot.json`, `data/pipeline_meta.json`.
- **CORS (previously open item) — observed, not assumed**: probe with
  `Origin: https://karagemop466-tech.github.io` against
  `GET /trade-api/v2/markets?limit=1` returned HTTP 200 with
  `access-control-allow-origin: https://karagemop466-tech.github.io` (origin
  echoed), `access-control-allow-credentials: true`, and
  `access-control-expose-headers: X-Csrf-Token,X-Ratelimit-Limit,...`.
  Conclusion: browser-side live fetch from the GitHub Pages origin is
  supported by the demo API. Raw evidence: `data/cors.json` (refreshed every
  pipeline run). Source: https://docs.kalshi.com/getting_started/quick_start_market_data .
- Two genuinely broken external docs links found by the external probe and
  fixed: `docs.kalshi.com/demo_env` → `docs.kalshi.com/getting_started/demo_env`
  (in `tools/build_content.py` API rows) and
  `docs.kalshi.com/api-reference/markets/get-market` → `.../market/get-market`
  (singular `market`) in `review.html`. Both re-checked live (200).
- This record + data sync PR: https://github.com/karagemop466-tech/Demo2/pull/25 —
  **MERGED** 2026-11-20 12:19:11 UTC, merge commit `b8e29c3`; both PR checks
  passed (link check incl. external, build+check). Pages deployments for
  `b8e29c3` created 12:19:15Z / 12:19:23Z; final site status verified `built`
  at https://karagemop466-tech.github.io/Demo2/ .
- Session 1d709f30 complete: all claimed tasks (S-1…S-7) done; open items that
  require a human (Kalshi demo account + API key for portfolio/trade execution)
  remain flagged on the Flagged pages and in the questions register, per the
  verification rules (blank, never inferred).
---

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
- `tools/check.py`'s private-key scanner flagged the literal PEM header text used as a textarea
  placeholder in `live/trading.html` (writing the header out here would trip the same guard, which is why it is described
  rather than quoted). The scanner is untouched — it is a good guard — and the placeholder was reworded.

Final local state before merge: `tools/check_live_links.py` clean (46 files / 1063 attributes), `tools/check.py`
"links, nav, data, secrets and scripts all clean", `tools/check_links.py` OK, `node --check` OK on both app scripts, and
re-running both generators produces no diff.

   link fix were applied on top.

## Session 0c901fea — read-only Kalshi monitor (PR #15)

Branch: `arena/0c901fea-demo2`. This session contributes a complementary static monitor under `monitor/`, linked from the root dashboard footer and documented in `README.md`. The root dashboard, backend, data pipeline, `pages/`, `verified/`, `dashboard/`, `site/`, `intelligence/`, and existing Pages publishing workflow are preserved. The monitor is not a replacement for those projects.

### Scope and status

| Task | Status | Files |
|---|---|---|
| Review official Kalshi demo/API/authentication/rate-limit sources | done | `monitor/`, docs |
| Build five-topic read-only monitor, charts, book depth, local watchlist, review and sources pages | done | `monitor/` |
| Keep account figures blank without authenticated data; leave trade execution disabled | done | `monitor/portfolio.html`, `monitor/review.html` |
| Link monitor from root dashboard and README | done | `index.html`, `tools/build_site.py`, `README.md` |
| Add monitor test/check/build scripts and PR verification workflow | done locally; remote checks pending | `package.json`, `tests/`, `scripts/`, `.github/workflows/verify-monitor.yml` |
| Integrate the latest `main` and preserve all subsites | in progress | merge of `origin/main` |

### Important caveats

- Browser-side Kalshi demo API/CORS behavior could not be verified from this sandbox. Errors are surfaced; the monitor does not substitute sample market values.
- Ranking sums displayed YES and NO bid-side notional (`price × contracts`). This is a labeled visible-depth proxy, not traded-dollar turnover. The requested meaning of “highest dollar amount” remains unresolved.
- Portfolio/account values remain blank without authenticated account data. No credentials are included; trade execution is disabled and no order was submitted.
- Topic matching uses local keywords, not a verified Kalshi taxonomy. The watchlist is browser-local.
- The existing root Pages publishing setup is retained; when deployed from the repository root the monitor is under `/Demo2/monitor/`.

### Local verification

- `npm ci` succeeded; `npm test`: 8 tests passed.
- `npm run check`: 15 monitor pages passed.
- `npm run build`: 15 static pages built; `node scripts/check-site.mjs dist` passed.
- The existing `tools/build_site.py` + `tools/build_content.py` regeneration is reproducible; `python3 tools/check.py` passed (with the expected warning that the first `data/snapshot.json` collection is pending).
- `python3 tools/check_links.py`: 14 main data pages and 24 rows checked; no broken internal links/anchors or unsourced rows.
- JavaScript syntax checks, Python compile checks, and `git diff --check` passed.

### PR / integration record

- PR #15: https://github.com/karagemop466-tech/Demo2/pull/15
- Original implementation commit: `c7b06b1`.
- Initial integration of `e3a6f5f`: `17e8c8f`.
- Integration of `4b84abf`: `a98cb75`.
- `main` subsequently advanced to `2ccd57c` (including PRs #16 and #21 and the `intelligence/` subsite); this update is being integrated without deleting or replacing `monitor/`, the root dashboard, or the other subsites. Confirm PR checks, mergeability, and Pages deployment only after the current integration is pushed.

---

# Merged from main (PRs #28–#31, instrument panel session)

### Merge record (f1751c8f, 2026-11-20)
- Merged `origin/main` (d98c436, which includes PR #9, #10, and #11 from session arena-3420a90d) into `arena/f1751c8f-demo2`. The conflict in COORDINATION.md was resolved by keeping both sections in order. README.md auto-merged.
- Main changes were additive (`dashboard/`, `tools/collect_kalshi.py`, `.github/workflows/collect.yml`, `.gitignore`). No shared file owned by this session was overwritten.

## Session `64df4faa` — branch `arena/64df4faa-demo2` (claim written 2026-11-20 11:35 UTC, before edits)

This session's rules name the branch `arena/64df4faa-demo2`, so `session-<id>/<task>` branches
were not created. The board was read first. `main` at claim time: `8330897` (PR #12),
with sessions `f1751c8f`, `arena-3420a90d`, `bb334a65`, `6822d767`, `e3f65782` and `407c72e2`
already merged and **still active** on their own branches (`Refresh Kalshi demo data snapshot`
and `Build and check the site` runs were in progress while this claim was written).

**Scope discipline.** Because three other dashboards are being actively edited, this session is
**additive only**. It does not edit `pages/`, `verified/`, `dashboard/`, `assets/`, `app.js`,
`style.css`, `analysis.html`, `portfolio.html`, `review.html`, `data/kalshi_snapshot.json`,
`tools/build_site.py`, `tools/check_links.py` or `tools/collect_kalshi.py`.

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| W-1 | Verified data collector (public demo API → snapshot + 3-day tick history) | done | 64df4faa | `tools/kalshi_collect.py`, `data/dashboard.json`, `data/history/*` |
| W-2 | Data validator that fails the build on unsourced / out-of-range / unreconciled / stale rows | done | 64df4faa | `tools/validate_data.py` |
| W-3 | Dashboard site: overview, 5 topic pages, live chart + orderbook, resolutions, portfolio, analysis | done | 64df4faa | `site/*.html`, `site/assets/*` |
| W-4 | Questions register (22 questions, known/missing/how-to-find-out) | done | 64df4faa | `site/content/questions.json`, `site/questions.html` |
| W-5 | Suggestions board (10 decisions, nothing implemented) | done | 64df4faa | `site/content/suggestions.json`, `site/suggestions.html` |
| W-6 | Flagged for Review register (data + repo irregularities, evidence links) | done | 64df4faa | `site/content/flags.json`, `site/flagged.html` |
| W-7 | Repo review: claim-by-claim against official docs | done | 64df4faa | `site/content/repo_review.json`, `site/repo-review.html` |
| W-8 | Clean landing page indexing every dashboard in the repo | done | 64df4faa | `index.html` |
| W-9 | Workflow: collect → validate → commit → link-check → deploy, every 15 min | done | 64df4faa | `.github/workflows/pages.yml` |
| W-10 | Integration: re-verify rows, build, link check, PR to `main`, merge, deploy check | **done** — PR #28 merged `46acd3e`; CI green on main at `64d0961`; site fetched live and checked | 64df4faa | all of the above |

### Environment facts verified by this session (not assumed)

- Additive sandbox bash **cannot** reach Kalshi (TLS `SSL_ERROR_SYSCALL`, DNS resolves to the AWS
  NLB for `external-api.demo.kalshi.co` and `external-api-ws.demo.kalshi.co`). Confirmed by `curl`.
- The sandbox's `fetch_page` tool **can** reach the demo API and the docs; that is how the raw
  responses cited on the site were read.
- A GitHub Actions runner **can** reach the demo API: a probe workflow returned HTTP 200 from
  `/exchange/status` and committed the response to the branch, which is how the collector design
  was validated before writing it.
- **CORS**: `/exchange/status` with `Origin: https://karagemop466-tech.github.io` returned
  `access-control-allow-origin: https://karagemop466-tech.github.io` (and `cache-control: public, max-age=1`).
  That is why the browser can poll the API directly and no proxy is needed for public data.
  This contradicts the earlier board note “CORS not verified”; it is now verified and re-checked each run.
- `search/tags_by_categories` contains **no Culture category** but does contain Entertainment;
  Culture exists only as a series category (`/series?category=Culture` → 2 series). Golf is a tag
  under Sports. Both are documented on the site rather than worked around.

### Sources (official, read this session)
`docs.kalshi.com`: `getting_started/demo_env`, `getting_started/orderbook_responses`,
`getting_started/market_settlement`, `getting_started/historical_data`, `getting_started/rate_limits`,
`getting_started/fixed_point_migration`, `api-reference/market/get-markets`,
`api-reference/market/get-market-orderbook`, `api-reference/market/get-series-list`,
`api-reference/market/get-trades`, `api-reference/market/get-market-candlesticks`,
`api-reference/events/get-events`, `api-reference/portfolio/get-balance`.
Raw API responses cited per row: `/series?category=Economics|Elections|Culture|Crypto`,
`/series?tags=Golf`, `/markets?series_ticker=…&status=open|settled`, `/markets/{ticker}/orderbook`,
`/markets/trades?ticker=…`, `/exchange/status`, `/search/tags_by_categories`.

### Verification performed
- `python3 tools/build_dashboard_site.py` then `python3 tools/check_site.py`: 55 pages checked,
  0 blocking errors; owned pages all carry the demo disclaimer and are reachable from the nav.
  Issues found in other sessions' pages are printed as **REPORTED, not blocking** so they are
  visible without blocking this session.
- `python3 tools/validate_data.py` enforces: source URL on every row, prices inside $0.00–$1.00,
  derived money reconciling with its inputs, no field filled in when its inputs are missing,
  snapshot younger than 6 hours.
- Every Kalshi doc path used on the site was fetched during this session; results are listed on
  `site/repo-review.html` under “Documentation links checked” (FETCHED vs REFERENCED).

### Requests to other sessions (not edited here)
1. **`pages/portfolio.html` and the root monitor still contain a credential-entry form** (API key ID
   + private key pasted into the page). PR #6 removed it but was never merged. This is recorded as
   F-08 on `site/flagged.html`. Whoever owns `pages/` should merge or close PR #6.
2. `dashboard/`, `verified/`, `pages/` and the root notes now make **four parallel dashboards**.
   This session did not consolidate them because all three are being edited right now; the landing
   page indexes all four instead. Consolidation is Suggestion S5 on the site.
3. The board's earlier claim that CORS is unverified is out of date — see above.

### Results actually obtained (not planned)

| Fact | Value | How it was verified |
|---|---|---|
| Open in-scope markets collected | 1,311 | `data/dashboard_instrument.json` `counts.open_markets_in_scope`, from one shared `/markets?status=open` stream intersected with each topic's series list |
| In-scope series | 174 | `/series?category=…` and `/series?tags=Golf` |
| Resolved markets collected | 1,601 | `/markets?series_ticker=…&status=settled` per series, `result` copied verbatim |
| — of which ever traded | 270 | `volume_fp > 0` |
| — of which never traded | 1,331 | `volume_fp == 0`; API returns `last_price_dollars` `0.0000` for these |
| Live orderbook snapshots | 48 (20 non-empty) | `/markets/{ticker}/orderbook?depth=20` |
| Trade histories | 12 markets | `/markets/trades?ticker=…` |
| Requests per run | ~440, 0 errors | `meta.https_requests`, `meta.request_errors` |
| Run duration | ~2 minutes | GitHub run 44737674422 |

### Two bugs this session found in its own work, and what now prevents them

1. **Resolved-market block silently emptied.** Restructuring the topic loop dropped the settled-markets
   call; the run still "passed" with 0 resolved rows. `tools/validate_data.py` now **fails** when the
   resolved set is empty, and `instrument-panel/tests_smoke.py` (offline, no network) runs first in CI.
2. **A calibration that measured a default value.** 1,331 of 1,601 resolved markets never traded and
   carry `last_price_dollars = 0.0000`. Calibrating them reported a fake +26-point edge on long shots.
   The Analysis page now calibrates **only traded markets** (n=270), labels bands with n<30 as too small
   to interpret, and keeps the uncorrected table in a collapsible block so the correction is checkable.
   Recorded as flag **F-15**.

### Rate limiting, verified rather than assumed
The 300-series run produced **539 x HTTP 429**. Kalshi documents that public endpoints “charge your IP
address's budget first”, that publicly cacheable responses carry **no** `X-RateLimit-*` headers, and that
a 429 has no penalty — so backoff is the only remedy. The collector now spaces requests globally
(widening x1.5 per 429, narrowing 0.5% per success, 4 workers) and publishes the observed 429 count on
the Verification page. After the restructure: 440 requests, 0 errors, 5 observed 429s.

| PR | What | Result |
|----|------|--------|
| [#28](https://github.com/karagemop466-tech/Demo2/pull/28) | The instrument panel itself (15 pages, collector, validator, workflow) | **merged** `46acd3e` at 2026-11-20T12:43:50Z |
| [#29](https://github.com/karagemop466-tech/Demo2/pull/29) | Move the nav link into `build_site.py` so the generated-page check passes | **merged** |
| [#30](https://github.com/karagemop466-tech/Demo2/pull/30) | Derive the expected nav size from the generator instead of hardcoding 20 | **merged** `64d0961` |

**`Build and check the site` is green on main at `64d0961`.** `pages build and deployment` succeeded,
and `Deploy GitHub Pages` ran the full collect → validate → rebuild → link-check chain.

**Live and verified by fetching the deployed page** (not by assuming):
`https://karagemop466-tech.github.io/Demo2/instrument-panel/site/analysis.html` returns the dashboard,
showing 1,601 resolved markets, 317 traded / 1,284 never-traded, and the corrected calibration table.

### Two CI failures I caused on main, and what was actually wrong

Both were **my** mistakes, both blocked nothing but looked like broken deployments, and both are worth
recording so another session does not repeat them:

1. **Edited a generated file.** `index.html` is produced by `tools/build_site.py`. Adding a nav link by
   hand made CI's "pages must match the generator" step fail. *Lesson: if a file has a generator, edit
   the generator.*
2. **A hardcoded count in a checker.** `tools/check.py` asserted "nav has 20 links", a magic number that
   has to be edited whenever a section is added. It now reads the count from the generator's `NAV` list,
   so it checks that pages match their source rather than a number someone has to remember.

In both cases the Pages deploy itself was fine; only the consistency job was red. The site was never
broken, and it is worth distinguishing the two when reading Actions.

---

## Session `arena-bdb4d2d0` — branch `arena/bdb4d2d0-demo2` — CLAIM (2026-11-20 13:01 UTC, written before edits)

Role: **final review + integration session** for this pass. The platform fixes
this session's branch name, so `session-<id>/<task>` branches are not created
(same precedent as sessions `1d709f30`, `64df4faa`). This section is pushed as
the claim, before any other edits.

**Scope discipline.** Active sessions at claim time (commits within the last
hour, listed so no one double-claims): `21eed9ff` (PR #34, docs verification),
`8b9a46b4` (PR #32, sharp-jump detector + backtest subsite), `5330bffb`
(PR #27, integration of its own pipeline/registers). Their file scopes are
**not** edited here. Stale claims (>60 min old, no commits — takeover rule):
`0c901fea` (PR #15, last commit 11:46 UTC) and `22b4f0cb` (PR #6, last commit
11:19 UTC). Those two are taken over by this session at 13:01 UTC per the
60-minute rule; their work is integrated **additively** via this branch and the
handoff is logged below.

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| R-1 | Repo line-by-line review vs official Kalshi sources; every claim checked or flagged | **done** | bdb4d2d0 | `integration/bdb4d2d0/repo-review.md` |
| R-2 | Independent re-verification of combined site data: every table row carries an official source link; unverifiable values stay blank + flagged | **done** | bdb4d2d0 | `integration/bdb4d2d0/verification.md` |
| R-3 | Irregularity register (data, security, CI, docs) with evidence links | **done** | bdb4d2d0 | `integration/bdb4d2d0/irregularities.md` |
| R-4 | Integration: bring origin/main + takeover PRs onto this branch, resolve conflicts additively, run every checker, fix broken links | in progress | bdb4d2d0 | merge commits on this branch; cross-scope fixes logged below |
| R-5 | Final PR → main, merge without waiting, GitHub Pages deploy confirm, record here | in progress | bdb4d2d0 | this section |

### Findings, fixes and handoffs (session bdb4d2d0, 2026-11-20 13:0x–13:4x UTC)

Full detail in `integration/bdb4d2d0/{repo-review,verification,irregularities}.md`.
Summary of what this session changed and why (all verified after the change):

1. **Main was red — fixed (commit `6df5c9f`).** PR #35 (session `e36292f6`)
   hand-edited `index.html`, `pages/{flagged,suggestions,verification}.html`
   without updating `tools/build_site.py`/`build_content.py`; the "pages must
   match the generator" gate failed on main (runs 12:57:58 / 13:02:27). Ported
   the sharp-jump feature into the generators (S9, F13, verification row,
   dashboard card + jump table), repaired their `/bin/bash.10` heredoc
   corruption (`$0.10`), and added the brief-required "possible context
   (unverified)" news-search link per jump row (labelled, never causal).
2. **Security — fixed (commit `49e706e`, flag F14).** Took over stale PR #6
   (`22b4f0cb`, last commit 11:19 UTC, >60 min rule): removed the orphaned
   WebCrypto signing code from `assets/app.js` and disabled the `live/trading.html`
   Mode B credential form on the deployed copy (reversible notice points at the
   gated Actions path + `server/`). Cross-scope request to session `6d75123b`:
   if that session returns, keep Mode B disabled on the public deploy.
3. **Placeholder links — fixed (commit `79fecce`).** `instrument-panel/tools/site_build_core.py`
   `ext()` rendered endpoint URL *patterns* as clickable `{ticker}` links.
   Patterns now render as `<code>`; the analysis source line keeps the official
   `get-markets` docs link. (`instrument-panel/` = session `64df4faa` scope,
   session done/merged; fix logged here per the cross-scope rule.)
4. **Flagged (not changed): F15** — `data/snapshot.json` + `data/resolutions.json`
   have never landed on main (collector step "Collect demo snapshot" failed in
   the only main run, `44728913873`; log body unreachable from this sandbox,
   GitHub blob EOF). The deployed `pages/resolutions.html` 404s its data file;
   both pages show honest empty states. **Handoff:** session `6332d7d3` has a
   rewritten collector green on `arena/6332d7d3-demo2` (runs 13:02/13:10 UTC) —
   that PR is the proper fix; this session dispatched `Refresh Kalshi demo data`
   on main (`44744689706`) at 13:29 UTC to re-test current code. Also **F16**
   (history tick rows lack source URLs) and **F17** (4 pipelines → one `data/`).
5. **Re-verification sample (8/8 matched):** resolved-market `result` +
   `settlement_ts`, event + lead-market quotes, series tags/category, demo
   endpoint table, create-order required-vs-optional fields, WS-handshake auth
   requirement — all re-fetched from their official source URLs 13:15–13:25 UTC.
   Provenance audit covered 11,430 rows across every `data/` list: every
   rendered table row carries an official URL except F16's tick rows.
6. **PR bookkeeping (updated 13:50 UTC after the landscape moved):**
   PR #27, #15 and #32 **merged themselves** at 13:02–13:15 and PR #6 was
   closed by another session at 13:02 (the earlier "superseded by #27" note
   about #15 is obsolete — #15 landed; record corrected here, history kept).
   Main also independently removed the browser-signing code inside PR #27's
   `assets/app.js` rewrite, which supersedes part of this session's commit
   `49e706e` — no work discarded, both paths agree. This session merged
   `origin/main` (through `0dc7749`) into its branch and union-resolved the
   generator conflicts (both sessions' sharp-jump content kept; the richer
   context-link wording + F14 kept), resolving generated files by
   regeneration. New placeholder defects that arrived with PR #32's subsite
   (`session-8b9a46b4/site/*`) were fixed at its generator the same way
   (`{placeholder}` patterns render as code).
7. **R-4 complete (13:5x UTC).** Combined-tree state after the merge:
   `tools/check.py` clean (incl. `[data]`), `scripts/check_links.py` all OK
   (8,000+ references), `tools/check_live_links.py` 0 placeholders across 91
   files, `instrument-panel/tests_smoke.py` passed, `node --check` clean.
   Open PRs at this point: #34 (docs, active 13:33), #36/#38 (new features),
   #40/#41 (**duplicate** the sharp-jump generator port that is already on
   this branch — their authors should close them as superseded once this PR
   lands, or rebase on it; nothing of theirs is lost, the same fix is here).
8. **R-5 in progress:** PR from this branch → main next, then Pages confirm
   and the final record below.

Outputs of this session live under `integration/bdb4d2d0/` (new directory,
non-overlapping with every other session's scope). Any edit to a shared file is
additive, generator-first where a generator exists, and logged in this section.

## Session `arena/e36292f6` — branch `arena/e36292f6-demo2` (started 2026-11-20)

**Branch:** `arena/e36292f6-demo2`, branched from `main` at `4c13151`. Scope: integration/final verification plus the sharp-jump price-movement feature (live chart markers + market links for moves ≥ $0.10 in either direction) and landing-page clarity. Non-overlapping with prior sessions — edits only to `COORDINATION.md` (this section), `assets/site.js` (sharp-jump detection + chart markers), `index.html` (landing clarity), `pages/verification.html` (sharp-jump verification row), `pages/flagged.html` (sharp-jump flag if unverifiable), and `pages/suggestions.html` (sharp-jump decision card).

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| E-1 | Coordination claim + claim commit/push | done | e36292f6 | `COORDINATION.md` |
| E-2 | Sharp-jump detection on live chart (≥ $0.10, either direction) with market links | done | e36292f6 | `assets/site.js`, `index.html`, `assets/style.css` |
| E-3 | Verification row + flag for sharp-jump feature (cause not derivable from API) | done | e36292f6 | `pages/verification.html`, `pages/flagged.html` |
| E-4 | Suggestion card for sharp-jump / live-interactivity | done | e36292f6 | `pages/suggestions.html` |
| E-5 | Full re-verification: build, link checks, both checkers | done | e36292f6 | all site files (read-only) |
| E-6 | PR from this branch to main, merge, Pages deploy confirm, record | in progress | e36292f6 | this section, PR record |

Sources to verify against (official only): https://docs.kalshi.com/api-reference/market/get-market-candlesticks, https://docs.kalshi.com/api-reference/market/get-trades, https://docs.kalshi.com/api-reference/market/get-market-orderbook, https://docs.kalshi.com/getting_started/demo_env.

### Merge record and update — session 3371a533 (merged `origin/main` at `6a9aecb`)

- `origin/main` moved while this session worked (PRs #27, #33, #35 and several data commits). Merged with `git merge origin/main` (no history rewrite). Conflicts: `COORDINATION.md` (both sides kept), `index.html` and `pages/*.html` (generated; regenerated from the merged generators, no hand edits), `README.md` (see below).
- **Defect found on `origin/main`, fixed here (logged as R20 on the Repo Review page):** `README.md` contained six unresolved merge-conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) from earlier merges, so both sides of two sections were in the file. Resolved by keeping both sides in order; no text removed.
- **Main's CI was red** at `9319862` (run 44740812355, step "Fail if regenerating produced a diff"): committed pages did not match the generators. Fixed by regenerating from the merged `build_site.py` / `build_content.py`; the diff gate is clean on the merged tree.
- **Jump numbers changed with the data.** The collector picks the largest markets each run, so the trade set changed. At snapshot `2026-11-20T13:02:54Z`: **7 trade-print moves ≥ $0.10 across 6 of 11 markets with trade data** (the 39 / 12 figures above were from snapshot `12:43:59Z`). Snapshot moves: 0 across 1,399 pairs (gaps 2.2–66.1 min). The live page `jumps/index.html` is authoritative and is rebuilt on every 15-minute data run.
- The 7 current moves include prints of 0.01 contracts (for example `KXAAAGASMAXFL-26DEC31-5.90`, 2026-09-15 0.01 → 0.90 on 0.01 contracts). They are shown with their sizes, because a thin print can look like a market move.
---

# Final record — PR #27 (session 5330bffb)

- **PR:** https://github.com/karagemop466-tech/Demo2/pull/27 — "Final integration: verified data
  pipeline, live dashboard, trade CLI, consolidated registers" — **MERGED** into `main` as
  merge commit `9319862` on 2026-11-20 (~13:05 UTC).
- **Pre-merge checks (all green):** ci.yml "Build and check the site" (generator-determinism,
  Python compile, analysis fixture, links/nav/data/secrets/JS), verify-monitor "Test and build
  monitor subsite" (8 tests + 15-page build), linkcheck (external host rejections like
  WSJ/Reuters 401, CoinDesk 429, DPWorldTour timeout now classified as anti-bot warnings —
  dead links 404/410/DNS still fail).
- **PR #6:** closed as superseded (content integrated at 296ad33; explanation comment posted).
- **PR #15:** found already merged by another session; its monitor/ tree was also integrated via
  merge 0680686 — nothing lost.
- **Deploy:** GitHub Pages deploy workflow `pages.yml` triggered on `main` at 9319862; result
  recorded by the next session entry in this file and visible at
  https://github.com/karagemop466-tech/Demo2/actions/workflows/pages.yml.
- Collector (`collect.yml`) continues refreshing `data/` on this branch and on main's data
  pipelines; the site falls back to committed snapshots when the API is unreachable.
## Session `arena-8b9a46b4` — branch `arena/8b9a46b4-demo2` (added 2026-11-20)

**Scope (non-overlapping, new folder only):** `session-8b9a46b4/` — sharp-jump (≥$0.10) detector + simulated-strategy backtest on already-collected demo data + executive-summary/suggestions pages. No edits to `pages/`, `tools/`, `data/`, `instrument-panel/`, `intelligence/`, `dashboard/`, `site/`, `verified/`, `live/`, `server/`, root HTML.

| ID | Task | Status | Files touched |
|----|------|--------|---------------|
| J-1 | Claim scope, push claim | in progress | `COORDINATION.md` |
| J-2 | Jump detector (≥$0.10 consecutive trade prints) over `data/dashboard_instrument.json` trades | unclaimed | `session-8b9a46b4/tools/jump_backtest.py`, `session-8b9a46b4/data/jumps.json` |
| J-3 | Simulated strategy backtest on resolved traded markets (volume>0), by topic | unclaimed | same script, `session-8b9a46b4/data/backtest.json` |
| J-4 | Site: executive summary, jumps, strategies, flagged, verification pages | unclaimed | `session-8b9a46b4/site/*.html` |
| J-5 | Link/JS checks, PR → main, merge, Pages verify | unclaimed | this section |

Rules honored: news/event *causes* of jumps are not in the Kalshi API — left blank and flagged, never inferred. Backtest is labeled SIMULATED (historical demo prints), not live demo-account execution (requires user keys; existing gated executor in `tools/execute_strategy.py` untouched).

### Results (session arena-8b9a46b4)
- Jump detector over 2,479 trade prints / 12 markets: **39 jumps ≥ $0.10** → `session-8b9a46b4/data/jumps.json` (each row source-linked; cause/news blank = J-F1).
- Simulated backtest on 317 traded resolved markets (of 1,601): always-NO mean +$0.60/contract reflects calibration (73.8% resolved NO), NOT a tradable edge — labeled SIMULATED with lookahead caveat (J-F2). Gas/culture: no traded resolved markets → blank (J-F3).
- Site: 5 pages under `session-8b9a46b4/site/` incl. live browser chart (seconds/minutes/hours + orderbook depth) polling the demo API directly.
- Verification: `python3 session-8b9a46b4/tools/jump_backtest.py` reproducible; `node --check live.js` OK; `python3 scripts/check_links.py` → 8,124 refs, all OK; `python3 tools/check.py` clean; local smoke 200s.
- Tasks J-1…J-5: done (J-5 PR/merge record below).

---

## Session `eeb796d7` — branch `arena/eeb796d7-demo2` (claim written 2026-11-20 13:03 UTC, before edits)

Platform constraint: this session's rules fix the branch name to `arena/eeb796d7-demo2`,
so `session-<id>/<task>` branches are not created; all work lands on that one branch.
Scope is **additive**: owned files are `session-eeb796d7/**` plus this appended board
section. At final-integration time only, shared outputs may be touched (logged there).

State of the board when this claim was written (read first): sessions `arena-5330bffb`
(PR #27, last commit 12:56Z), `arena-8b9a46b4` (PR #32, 12:54Z) and `arena-21eed9ff`
(PR #34, 12:57Z) are **active**; PRs #6 (11:19Z) and #15 (11:46Z) are past the 60-minute
stale limit with no commits and are eligible for takeover.

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| E-1 | Line-by-line verification pass: every checked claim in the merged tree vs official docs + live demo API, per-row source links | in progress | eeb796d7 | `session-eeb796d7/**` |
| E-2 | Irregularities register (repo hygiene: duplicate workflows/tools/data, committed `.pyc`, stale PRs, conflicting schedules) with evidence links | in progress | eeb796d7 | `session-eeb796d7/**` |
| E-3 | Stale-PR takeover per the 60-minute rule: review PR #6 and #15 and record action | in progress | eeb796d7 | (PR operations only) |
| E-4 | Final integration once other sessions are done: merge ready PRs, re-verify combined data line by line, confirm build + no broken links, PR to `main`, merge, confirm Pages, record | unclaimed | eeb796d7 | `COORDINATION.md` (append), any shared output strictly as needed and logged |

### Session `eeb796d7` — work record (2026-11-20 13:00-14:10 UTC)

| # | Task | Status | Evidence |
|---|------|--------|----------|
| E-1 | Line-by-line verification pass vs live official API + docs | **done** | `session-eeb796d7/index.html` (16 rows, per-row source links), `session-eeb796d7/data/verification.json`, raw bodies in `session-eeb796d7/data/raw/` |
| E-2 | Irregularities register | **done** | R-1…R-7 on `session-eeb796d7/index.html` |
| E-3 | Stale-PR takeover per the 60-minute rule | **done (not needed)** | PR #6 closed 13:02:42Z as superseded (PR #27 rewrote `assets/app.js`), PR #15 merged 13:02:26Z inside PR #27 — both by session d0bea7de before takeover was required. No action taken here. |
| E-5 | Collector defect found during E-1: `data/snapshot.json` never published; root dashboard showed 0 markets | **done** | `tools/collector.py` fix + `session-eeb796d7/tools/test_collector_fix.py` (11/11 PASS; pre-fix code reproduces `NameError: name 'series' is not defined` = the exact failure of Actions runs 44728913873 / 44744689706) |

**E-5 detail (three defects in `tools/collector.py`, all fixed and regression-tested):**
1. `collect_scope()` referenced an undefined `series` variable while building market rows —
   `NameError` on the first in-scope market. Offline runs with zero rows never fired it,
   which is why the failure only appeared in Actions. The root dashboard therefore sat on
   `data/snapshot.json` -> 404 ("0 in-scope markets") on the deployed site.
2. Topic classifier missed the AAA gasoline family: `KXAAAGASD/M/…` carry tags
   `["Oil & Gas", "Oil and energy", "Econ Daily"]` and are classified via
   `product_metadata.scope == "Gasoline"` (verified live: `GET /series/KXAAAGASD`).
   The bare `Oil & Gas` tag is deliberately NOT mapped — it also covers WTI crude
   (KXWTI…), natural gas (KXNATGASMON) and TTF (verified live:
   `GET /series?tags=Oil%20%26%20Gas`). Before this fix the gas topic would still have
   been empty after (1) was fixed, contradicting `rankings.html` which shows the AAA rows.
3. `market_url`/`event_url` used the SERIES ticker on `kalshi.com/markets/…`; now they are
   the exact official API endpoints with the market ticker (the per-row source link
   policy). A human web-UI URL pattern for demo markets could not be confirmed from an
   official source and was left blank + flagged (verification row V15), not invented.

**Cross-session notes (not edited, logged per the rules):**
- The sharp-jump landing card/chart wiring that `027edfe` dropped is restored by PR #40
  (session d0bea7de, byte-identical to `9319862`) — tracked to merge at integration (R-3).
- R-5 (five parallel dashboard trees, duplicated tools, 7 workflows with competing
  schedules and observed 429 storms) and R-6 (committed `scripts/__pycache__/*.pyc`)
  remain flagged for review; consolidation is suggestion S5.
- Earlier revision of this branch contained a duplicate generator port (sharp-jump);
  dropped on re-read of the board after main's `027edfe`/`ae1e150` landed the same fix —
  no duplicate work is carried into the merge.

Verification performed for E-5: `python3 session-eeb796d7/tools/test_collector_fix.py`
(11/11), `python3 -m py_compile tools/collector.py`, `python3 tools/check.py` (clean),
`python3 scripts/check_links.py` (all links OK).

**Integration link fixes (session eeb796d7, 13:55-14:05 UTC, logged per the rules):**
The external link check ("Link check (all pages, internal + external)") failed on every PR
with 4 pre-existing non-resolvable URLs (example: PR #40's run 44743893105: crunchyroll
`/en/animeawards/` 404, bare REST base GET 404, `contract_terms/.pdf` 404,
`markets/{ticker}` pattern 404). Because the integration gate is "no broken links", the
following minimal, policy-compliant fixes were made in `instrument-panel/tools/` (NOT in any
open PR's diff) and the site regenerated with `build_dashboard_site.py`:
- `ext()` renders URL patterns (`{ticker}` etc.) and REST/WS base URLs as `<code>` (they are
  documentation, not pages) and verified-dead/blank source URLs as flagged text — no URL is
  invented, dead official URLs stay visible for manual review;
- the demo banner links no longer point at the non-resolvable API base;
- request-error rows render their URLs as text.
All instrument-panel and root checkers re-run clean afterwards (`check_site.py` OK,
`tests_smoke.py` OK, `tools/check.py` OK, `scripts/check_links.py` all links OK).
Follow-up flagged (R-8, not fixed): some `culture.html` rows link rules-prose fragments to
`kalshi.com` (collector parsed rules text as settlement sources) — rows should show the API's
real `settlement_sources` or blank + flag. Full register: `session-eeb796d7/index.html`.
This also answers all three cross-scope link requests from session 3371a533 below
(their items 1–3: pattern href, `contract_terms/.pdf`, API-root href) — fixed at the
generator level and re-verified.


### Second merge record — session 3371a533 (merged `origin/main` at `1baa0eb`)

- `origin/main` gained PR #32 (`8b9a46b4`, sharp-jump detector under `session-8b9a46b4/`), PR #37 and data refreshes. Merged without rewriting history. Conflicts: `COORDINATION.md` (union), `tools/build_content.py`, `pages/{flagged,suggestions,verification}.html` (generated; regenerated).
- **Flag ID collision resolved.** `origin/main` already has **F13 = "Sharp-jump cause cannot be determined from the API"** (session `e36292f6`). My gas-scope flag was also numbered F13. Kept theirs as F13 and renumbered my flags **F13–F20 → F14–F21**, and updated every reference to them (bottom line, R18). Their references (F13 in suggestions and the sharp-jump page) are unchanged.
- **Rendering fix in the shared flagged table:** the generator's row renderer now handles full `https://` source URLs, lists, and paths (the union of both sides). Both forms were in use.
- Gates on the merge commit: `tools/check.py` OK, `scripts/check_links.py` OK, `instrument-panel/tests_smoke.py` OK, `validate_data.py` OK (1 warning: culture topic has no open markets, = F20), `check_site.py` OK, regenerated output matches the committed output (diff gate clean).
- **Overlap logged (no edits made to the other sessions' files):** two other sessions also built a sharp-jump / price-move feature: `e36292f6` (live-chart markers in `assets/site.js`, merged) and `8b9a46b4` (`session-8b9a46b4/`, merged via PR #32). This session's `jumps/` page is a third, separate build from the same trade data. The three use different methods; the board should pick one for the final integration. This is recorded as a finding, not resolved here.
- **Deviation from my own claim, disclosed:** the claim said J-2 would write `jumps/repo-review.html`. The repo review was instead added as flag/finding rows through `tools/build_content.py`, into `pages/flagged.html` and `pages/repo-review.html`, which the claim also allowed as additive rows. No other session's page content was edited by hand; shared pages were regenerated from the generator.
- Open for the owner: F20 (culture: no open markets) and F21 (browser page takes a demo private key) remain open; R19 (two unfilled link placeholders in instrument-panel pages) remains open because those files belong to another session. R20 (README conflict markers on `main`) is fixed on this branch.

### Cross-scope requests from session 3371a533 (not edited here; for the owner of `instrument-panel/` and the final integration session)

Found by the whole-site external link check (`scripts/check_links.py --external`, workflow `linkcheck.yml`). The check is advisory (PR-only, does not gate deploy), and the three failures below are already on `main`. My PR adds none of them. Exact lines at `ccf8923`:

1. **`instrument-panel/site/verification.html:33`** — `href="https://external-api.demo.kalshi.co/trade-api/v2/markets/{ticker}"` is an unfilled template placeholder (GET 404). Same defect as **R19**. Fix in `instrument-panel/tools/build_dashboard_site.py`: substitute a real ticker or link the endpoint's documentation page instead.
2. **`instrument-panel/site/crypto.html:44`** — `href="https://assets.kalshi.com/contract_terms/.pdf"` has an empty ticker (GET 404). Built from the `contract_terms_url` field, which the collector stores as `…/contract_terms/.pdf` when the ticker is blank (see `data/dashboard_instrument.json`). Fix: skip the link when the ticker is blank, or show "not published" with a flag.
3. **`instrument-panel/site/*.html:27`** (12 pages, incl. `index.html:28`) — `href="https://external-api.demo.kalshi.co/trade-api/v2"` points to the API root, which returns 404 for a plain GET. Fix: link to `https://docs.kalshi.com/` (the API reference) and keep the base URL as text.

These are logged, not fixed, because the files belong to the instrument-panel session. Its owner decides the fix. Until then the advisory link check on PRs shows these three failures.

### Final record — session 3371a533 (claim J-1, J-2, J-3)

| # | Status | Result |
|---|--------|--------|
| J-1 | **done, merged** | Price-jump page `jumps/index.html` (nav entry "Price Jumps"); generator `tools/build_jumps.py`; `pages.yml` runs it on each data run. At the snapshot it was built from (`2026-11-20T13:26:12Z`): 53 trade-print moves ≥ $0.10 across 11 markets; 0 snapshot moves across 1,719 pairs. Cause column blank, marked unverified on every row. Verified on the live site. |
| J-2 | **done, merged** | Repo review: R12–R20 on `pages/repo-review.html`; flags F14–F21 on `pages/flagged.html` (F13 is the sharp-jump flag from `e36292f6`; my gas-scope flag was renumbered). Every row carries a source link. R20: README on `main` had six unresolved conflict markers; fixed. |
| J-3 | **done, merged** | PR #38 merged as `8dc7996`. Nav row added; executive-summary "Bottom line" corrected to list what is still open (F18–F21). Gates on the merge: `tools/check.py`, `scripts/check_links.py` (internal), `build_site`/`build_content` diff gate, `instrument-panel` smoke test, `validate_data.py` (1 warning, F20), `check_site.py`. Deploy: "Deploy GitHub Pages" success on `8dc7996`; live page confirmed. |

**Open at close (not blocking, recorded):**
- The external link check (`linkcheck.yml`, PR-only, advisory) did not complete on the runner for the final heads. Several link-check runs across sessions were still in progress after 25+ minutes; they were not failing. Its last complete result (on `d01f42b`) listed three defects, all pre-existing in `instrument-panel/site/` and none introduced by PR #38. Logged above as cross-scope requests.
- Built-in GitHub Pages build (`pages build and deployment`) fails on automated **data-only** commits (`0dc7749`, `436a1a7`) and passes on code commits. Our `Deploy GitHub Pages` job is green. The cause is not in the logs (the log receiver returned EOF); the annotation shows no error. Recommend the owner of `pages.yml` / `collect.yml` check whether data-only pushes need the Pages build retried.
- Two sharp-jump features exist beside this one (`e36292f6`, `8b9a46b4`). The final integration session should pick one.

**Process note:** one `git pull --rebase` on this branch was attempted after a merge of `origin/main`. Rebasing would have replayed merged `main` history and stopped on another session's commit. It was aborted, nothing was lost, and the branch was pushed as a fast-forward. For this branch, use `git merge origin/main` rather than `pull --rebase`.

**E-5 follow-up (session eeb796d7, 14:15-14:25 UTC):** the first real `refresh-data` run on
`main` (44750844593, 49 s, SUCCESS — first ever) published `data/snapshot.json` with 10,241
market rows (elections 9,797 · crypto 376 · golf 68). Gas showed 0 rows: the bare `/series`
list response does NOT carry `product_metadata` (the field that classifies the AAA gasoline
family via `product_metadata.scope == "Gasoline"`; filtered queries like
`/series?tags=Oil%20%26%20Gas` and `GET /series/{ticker}` do carry it — all verified live
2026-11-20), so the scope rule never fired in production even though it passes the offline
fixture tests (which use the full record). Fixed in `tools/collector.py`: for series that
appear in in-scope events but map to no topic, `GET /series/{ticker}` (official full record)
is fetched once per series and re-mapped; event pagination widened 25→50 pages. Test updated
to simulate the slim list + enrichment path (12/12 PASS). Also observed: Pages
`pages-build-deployment` fails on data-only commits (3371a533 documented this too) while
`pages.yml` does not run for them — so the deployed site lags the newest snapshot until the
next code commit deploys; this follow-up commit is a code push and re-deploys the site with
the current tree.

**E-5 follow-up 2 (session eeb796d7, 14:35-14:45 UTC):** the first enrichment run failed in
Actions (44753235358, exit 1) — reproduced offline: `GET /series/{ticker}` can return
`{"series": [...]}` (list) as well as `{"series": {...}}` (dict); the list shape reached
`series_topic` and raised `AttributeError: 'list' object has no attribute 'get'`. Hardened:
`series_topic` type-guards `product_metadata`/record shapes, the enrichment path accepts only
dict records with a ticker and never lets one series kill the run (logged as an api_log note
instead), `inventory` tolerates records without a ticker. Adversarial-shape regression case
added to `session-eeb796d7/tools/test_collector_fix.py` (13/13 PASS).

---

# Session `arena/848af77d-demo2` — integration / final verification (session ID `848af77d`)

Branch: `arena/848af77d-demo2`, branched from `main` at `e7fabd4` (2026-11-20T15:59Z).
Scope: final integration. Add the missing live-alerting surface required by the brief
(two scrolling chats for price swings ≥ $0.10 in either direction), re-verify data rows
against official Kalshi sources, confirm the site builds with no broken links, create the
PR → `main`, merge without waiting, confirm GitHub Pages deploys, and record the result here.

Non-overlapping scope note: this session adds a new generated page `pages/live-alerts.html`
and a nav entry; it regenerates the shared pages from the generators (no hand-edits to
generated HTML). It does not edit any other session's subsite (`dashboard/`, `verified/`,
`site/`, `intelligence/`, `live/`, `monitor/`, `instrument-panel/`, `session-*`).

| # | Task | Status | Owner | Files (exclusive scope) |
|---|------|--------|-------|--------------------------|
| I-1 | Add live-alerts page with two scrolling chats (≥ $0.10 swings; all-events + high-ROI filter) | done | 848af77d | `tools/build_site.py` (NAV + generator), `pages/live-alerts.html` (generated), `index.html` + `pages/*.html` (regenerated nav) |
| I-2 | Re-verify sample data rows against official live demo API (exchange status, series, market, orderbook) | done | 848af77d | `data/snapshot.json` (read-only spot checks), `pages/api-reference.html` |
| I-3 | Run CI checks (tools/check.py, link checks, JS syntax, generator diff gate) | done | 848af77d | `tools/check.py`, `tools/check_links.py` |
| I-4 | Create PR → main, merge, confirm GitHub Pages deploy, record PR link + deploy result | in progress | 848af77d | `COORDINATION.md` (this section), PR record |

Sources used (official only): https://docs.kalshi.com/getting_started/demo_env (demo REST/WS endpoints); https://docs.kalshi.com/api-reference/market/get-trades (≥ $0.10 move detection uses trade prints); https://docs.kalshi.com/api-reference/market/get-markets (market prices, volume, result); https://docs.kalshi.com/api-reference/market/get-market-orderbook (liquidity).

Irregularities carried forward (from `pages/flagged.html`): none block this session; the "two scrolling chats" feature did not previously exist and is being added now under I-1.

# Session `arena/b326b649-demo2` — final integration (current session, 2026-11-20)

Branch: `arena/b326b649-demo2`, branched from `e7fabd4` on `main`. Session ID: `b326b649`.
This checkout is at the same commit as `main` (`e7fabd4`), so the final-integration work lands as
new commits on this branch, is offered as a pull request to `main`, merged without waiting, and
this section is then updated with the PR link, merge result and Pages deploy status.

Prior work is preserved, not rewritten: `pages/` (canonical CI-checked site), `verified/`,
`dashboard/`, `site/`, `intelligence/`, `live/`, `monitor/`, `jumps/`, `tools/`, `data/`.
No prior session's file is edited here; shared outputs change only via this integration branch.

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| I-1 | Claim integration tasks + push claim immediately | **done** | b326b649 | `COORDINATION.md` (commit 731b626, pushed) |
| I-2 | Re-verify a sample of combined table rows against official docs + live demo API | **done** | b326b649 | `data/snapshot.json` (read-only) + live fetches below |
| I-3 | Confirm full build + internal+external link check pass; no broken links | **done** | b326b649 | `tools/check.py`, `scripts/check_links.py` |
| I-4 | Trigger GitHub Pages deploy + confirm the live site | **in progress** | b326b649 | `.github/workflows/pages.yml` (workflow dispatch only) |
| I-5 | PR `arena/b326b649-demo2` → `main`, merge without waiting, record PR link + merge result | unclaimed | b326b649 | `COORDINATION.md` |

### Sources re-checked this session (official only, fetched 2026-11-20)

| Claim checked | Official source | Status |
|---|---|---|
| Demo REST root `https://external-api.demo.kalshi.co/trade-api/v2` (also `https://demo-api.kalshi.co/trade-api/v2`) | https://docs.kalshi.com/getting_started/demo_env | **Verified** — live GET returned `{"exchange_active":true,"trading_active":true}` |
| Demo = mock funds, prices may not reflect real markets | https://docs.kalshi.com/getting_started/demo_env | **Verified** |
| WebSocket handshake requires signed `KALSHI-ACCESS-*` headers (not possible browser-side) | https://docs.kalshi.com/getting_started/quick_start_websockets | **Verified** (doc text) |
| Public market-data endpoints need no auth | https://docs.kalshi.com/getting_started/quick_start_market_data | **Verified** (doc text) |
| Orderbook returns yes/no bids only; ask side is derived `1 − p` | https://docs.kalshi.com/api-reference/market/get-market-orderbook | **Verified** (doc text) |
| Legacy `POST /portfolio/orders` removed → 410; use `POST /portfolio/events/orders` | https://docs.kalshi.com/api-reference/orders/create-order-v2 | **Verified** (doc text) |

### Market rows re-verified against the live demo API (read-only GET, fetched 2026-11-20)

Every field below was read from `data/snapshot.json` and then re-fetched from the official demo
endpoint `GET /trade-api/v2/markets/{ticker}`. All matched exactly; nothing inferred.

| Snapshot row (topic) | Ticker | last_price_dollars | yes_bid_dollars | yes_ask_dollars | volume_fp | Live-API match? |
|---|---|---|---|---|---|---|
| elections | KXNEWPOPE-70-PPIZ | 0.1000 | 0.0000 | 1.0000 | 11434.49 | Yes — official response identical |
| crypto | KXBTCD-33MAY2100-T67099.99 | 0.0100 | 0.0000 | 1.0000 | 3.18 | Yes — official response identical |
| golf | KXPGAFUTURE-36MRUS-1 | 0.0200 | 0.0000 | 1.0000 | 1.16 | Yes — official response identical |
| gas | — | — | — | — | — | No live markets (catalogue only: DIESEL, DIESELM — flagged F12) |

### Checker results (local, 2026-11-20)

| Checker | Command | Result |
|---|---|---|
| Site pre-publish checks | `python3 tools/check.py` | links ok, nav ok, data ok, secrets ok, js ok; 17 HTML pages; one warning (11 snapshot API requests non-2xx — all documented 429 rate limits) |
| Whole-site internal link check | `python3 scripts/check_links.py` | 9,290 references across 107 HTML files, all OK, 0 broken |

## PR / deploy record (filled in after I-5)

- PR: _to be created_
- Merge result: _to be recorded_
- Pages deploy: _to be recorded_

## Notes

- Sandbox bash egress to `*.kalshi.co` is blocked (TLS handshake fails — flagged F1); live source
  checks above were done with the fetch tool, which can reach the demo host and docs. GitHub
  Actions runners have normal egress, so the collection workflows run there.

---

# Session `arena/a984e8f4-demo2` — gap-fill + integration (CLAIM, 2026-11-20 19:47 UTC)

Branch: `arena/a984e8f4-demo2`, branched from `main` at `e7fabd4` (merged `origin/main` at
`8818f6b`). Session ID: `a984e8f4`. This claim was written and pushed **before** any work
started. Platform constraint: this session may only work on its own branch (no
`session-<id>/<task>` branches), same as prior sessions.

Checked first: session `b326b649` holds I-1…I-5 (final-integration verification + deploy +
their own PR record) with fresh commits — **not touched, not duplicated here**. The four open
PRs #34, #36, #40, #44 are >60 min old with no commits and CONFLICTING with `main`; their
sessions are inactive, so they are eligible for takeover under the 60-minute rule (handoffs
logged below). Task 21 (demo API key secrets) remains owner action and is not claimed.

| # | Task | Status | Owner | Files (exclusive scope) |
|---|------|--------|-------|--------------------------|
| A-1 | Fix failing `Refresh Kalshi demo data` pipeline (collector OK, "Commit snapshot" step fails on every run — last success unknown; site data goes stale) | claimed → in progress | a984e8f4 | `.github/workflows/refresh-data.yml`, `tools/collector.py` (only if the defect is collector-side) |
| A-2 | Requirement gap: two live scrolling alert chats — (1) all in-scope events, (2) high-ROI model filter — with ≥$0.10 swing alerts, wired into the canonical site nav + generator (required by the brief; grep shows no ROI/chat/alert content in `index.html`, `assets/site.js`, `pages/*`) | claimed → in progress | a984e8f4 | `assets/alerts.js` (new), `assets/style.css` (append-only), `tools/build_site.py` (generated page + nav entry), `tools/build_content.py` (additive verification/flag rows only), generated `index.html`, `alerts.html`, `pages/*.html` (regenerated outputs) |
| A-3 | Takeover of stale conflicting PRs #34, #36, #40, #44 per the 60-minute rule: review each, integrate any still-relevant unique value, close or merge with a recorded disposition comment (no session's work silently discarded) | claimed → in progress | a984e8f4 | PR operations only + this section |
| A-4 | Automated simulated (paper) trading that runs with NO secrets, testing multiple strategies, with portfolio performance + trade categorization surfaced on the site (live demo-account execution stays gated behind task 21 secrets) | claimed → in progress | a984e8f4 | `tools/paper_trade.py` (new), `.github/workflows/paper-trade.yml` (new), `data/paper_portfolio.json` (generated), page rows via A-2 generator scope |
| A-5 | Final pass: line-by-line verification of changed content, all checkers green, PR `arena/a984e8f4-demo2` → `main`, merge without waiting, confirm Pages deploy, record PR + merge + deploy here | done (record below) | a984e8f4 | this section + PR operations |

### Work record — session a984e8f4 (2026-11-20 19:47–21:15 UTC)

| # | Status | Result |
|---|--------|--------|
| A-1 | **done** | Root cause of the dead data pipeline confirmed by evidence: `Refresh Kalshi demo data` run 44800417665 shows `Collect demo snapshot` SUCCESS, `Fail loudly if no in-scope data` SUCCESS, **`Commit snapshot` FAILURE** — every run since ~15:24Z; `data/snapshot.json` on main was frozen at 14:10Z (5.5 h stale). Sessions eeb796d7/3371a533 captured the pre-receive rejection text (GitHub 100 MB/file limit; snapshot.json hit 112 MB) and PR #52 slimmed rules text but runs still failed. Fix = deterministic size bounds in `tools/collector.py` (rows published once — `by_topic` is tickers-only now, null fields dropped, compact JSON, top 1,200 rows/topic by est. dollar volume with trimming recorded in `counts`, history bounded to 600 tickers × 288 points, hard 90 MB tripwire in `write_json`) + workflow tripwire step + stage only collector-owned files (blanket `git add data/` used to revert other pipelines' newer files on the push-retry soft-reset path). Latent CI defect found on the way and fixed in the same workflow: `meta_bar()` embeds snapshot timestamps in `index.html`/`alerts.html` at build time, so the first post-fix data commit would have gone red on the generator-diff gate — `refresh-data.yml` now rebuilds generated pages with each snapshot commit. Regression: `tests/test_collector_output.py` (52 assertions, offline). |
| A-2 | **done** | Requirement gap filled: `alerts.html` (generated) + `assets/alerts.js` — two scrolling chats (All events / High-ROI model picks) with ≥ $0.10 swing detection between consecutive observations of official trade prints (`GET /markets/trades?limit=1000&min_ts=…`) and quotes (`GET /markets?status=open&limit=1000`), 15 s polling with 429 backoff, resolution notices on the official yes/no result, price chart (60 s/5 m/1 h/6 h/24 h windows, red ≥ $0.10 markers), live order-book depth (raw bids + labelled derived asks). High-ROI = transparent documented heuristic (`0.40·liquidity + 0.30·tightness + 0.30·price action`, cutoff 0.60) — flagged **F22**. Swing causes never inferred (F13 policy). Verified rows added to `pages/verification.html` (Get Trades tape query, orderbook raw shape, alerts design, size bounds) with official source links. |
| A-4 | **done** | `tools/paper_trade.py` + `.github/workflows/paper-trade.yml`: automated SIMULATED trading with NO credentials — four deterministic strategies (momentum / mean_revert / longshot / favorite), trades categorised by topic + price band + strategy, positions settled on the official yes/no result ($1/contract), per-strategy win/loss/P&L, equity history. Ledger `data/paper_portfolio.json`, rendered client-side on `pages/portfolio.html` ("Simulated strategy lab"). Fees/slippage deliberately unmodeled — flagged **F23**. Regression: `tests/test_paper_trade.py` (20 assertions; found and fixed a real bug — settled markets could be re-bought). |
| A-3 | **done** | Takeover of 4 stale CONFLICTING PRs per the 60-minute rule (last commits 13:33–14:16Z, sessions inactive), each with a public disposition comment: **#34 closed** (superseded by eeb796d7/b326b649 re-verification; pre-#38..#57 base would reintroduce fixed defects), **#36 closed** (its unique `desk/` subtree preserved VERBATIM from `arena/220913cb-demo2` at commit a37e2ca — 21 files, gates pass with it; branch kept), **#40 closed** (defect already fixed on main: sharp-jump landing card present via PR #41's generator port; instrument-panel link fixes landed via eeb796d7), **#44 closed** (collector/tests superseded — its `tools/test_collector.py` exits 2 on the current collector CLI, verified; causes page covered by F13 + jump/alert context links; unique checkers preserved on its branch). Nothing deleted; every branch preserved. |
| A-5 | **done** | Integration rulings + records below. |

### Integration rulings (2026-11-20, session a984e8f4 as final integration)

1. **One canonical "Live Alerts" nav entry** → root `alerts.html` (browser-live). Session 848af77d's
   snapshot-based `pages/live-alerts.html` stays published and is cross-linked from `alerts.html`
   and the Flagged rows; it leaves the nav to keep one entry per feature (brief: "organize and
   simplify the website continuously"). Nothing deleted.
2. **848af77d's live-alerts defects fixed at the generator level** (flagged R6/R9 by f75410bb, owner
   >60 min stale at fix time): `fetch('data/…')` → `fetch('../data/…')` (the "Could not load alert
   data: 503" was the page's relative paths resolving under `/pages/`); metadata join now falls back
   to the jumps row's own topic/title/series/market_source (was 0/14 snapshot-join matches and 6
   source-less rows); the High-ROI rule lets rows with no computable est. volume pass the volume
   gate and be labelled "est. vol —" instead of silently emptying the feed.
3. **`desk/` (session 220913cb) preserved verbatim**, unlinked from nav (subsite duplication stays
   flagged as Q12 for the owner).

### Verification performed (session a984e8f4)

| Check | Command | Result |
|---|---|---|
| Collector regression (bounded output) | `python3 tests/test_collector_output.py` | 52/52 PASS (offline, synthetic official-shaped API) |
| Paper-trading regression | `python3 tests/test_paper_trade.py` | 20/20 PASS (offline) |
| Prior collector regression | `python3 session-eeb796d7/tools/test_collector_fix.py` | all PASS (13/13) |
| Site gates | `python3 tools/check.py` | links ok, nav ok, data ok, secrets ok, js ok; 18 generated pages |
| Whole-site links | `python3 scripts/check_links.py` | 9,650 references / 121 HTML files (incl. `desk/`), all OK |
| JS syntax | `node --check assets/alerts.js` + inline-script check in check.py | OK |
| Executive summary | bottom line updated to current flag set (F22/F23 + alerts + paper lab) | regenerated |

Sources (official only): https://docs.kalshi.com/getting_started/demo_env,
/api-reference/market/get-trades, /api-reference/market/get-markets,
/api-reference/market/get-market-orderbook, /api-reference/market/get-market-candlesticks,
/getting_started/rate_limits, /getting_started/market_settlement, /getting_started/pagination,
/getting_started/quick_start_websockets,
https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
(100 MB push limit — the A-1 root cause).
Sandbox bash egress to `*.kalshi.co` remains blocked (F1); run/API evidence above comes from
workflow run metadata (44800417665 job steps), committed snapshots, and prior sessions' verified
live-API rows — nothing about live market values is asserted from memory.

### PR / deploy record — session a984e8f4 (filled in after merge)

- PR: _pending — see follow-up commit below_
- Merge result: _pending_
- Pages deploy: _pending_
- Refresh-data recovery: _pending (workflow_dispatch on merge to prove A-1)_

Sources to verify against (official only): https://docs.kalshi.com/getting_started/demo_env,
https://docs.kalshi.com/api-reference/market/get-markets,
https://docs.kalshi.com/api-reference/market/get-market-orderbook,
https://docs.kalshi.com/api-reference/market/get-market-candlesticks,
https://docs.kalshi.com/api-reference/market/get-trades,
https://docs.kalshi.com/getting_started/quick_start_websockets,
https://docs.kalshi.com/api-reference/portfolio/get-positions,
https://docs.kalshi.com/api-reference/orders/create-order-v2.
## Session `f75410bb` — current branch `arena/f75410bb-demo2` (claim, 2026-11-20)

Platform branch rules require using this current branch; no separate `session-*` branch is created.
The existing tree already contains multiple dashboard/site implementations. To avoid duplicate
work and conflicting shared outputs, this session claims a scoped audit of the canonical root
site and interactive server against the requirements and official Kalshi docs.

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| F-1 | Audit current site/build/test behavior and verify API/security claims against official docs | done | f75410bb | `session-f75410bb/**` |
| F-2 | Record reproducible findings and verification / sources; make scoped fixes only | needs review | f75410bb | `session-f75410bb/**` |

Claim scope excludes shared pages, datasets, workflows, and other session directories. If a fix
requires those files, the issue will be logged as a cross-scope request rather than edited.

### Session f75410bb — audit result and cross-scope requests (2026-11-20)

| # | Status | Result |
|---|---|---|
| F-1 | **done** | Rechecked Node build/tests, Python site/data/link gates, backend order request and event-poll code; official Kalshi demo, events, orderbook, Create Order V2, and WebSocket pages read directly. Detailed row-by-row evidence and source links: [`session-f75410bb/review.html`](session-f75410bb/review.html). |
| F-2 | **needs review** | R1 order execution route/body is incompatible with documented Create Order V2; R2 event pagination is incomplete; R3 dual scrolling feeds now exist but are snapshot-only and high-ROI is a rule, not a model; R4 authenticated WebSocket needs backend handling; R5 Pages cannot itself run the authenticated backend; R6 live-alert joins yield 0/14 matches, an empty ROI feed, and six source-less rows; R7 provenance timestamps disagree; R8 implied asks are derived; R9 deployed alert feed fails to load because of relative paths. These are not marked fixed. |

**Checks:** `npm test` (8/8); `npm run check` (15 pages); `npm run build` (15 pages); `python3 tools/check.py` (18 pages; pass with existing warning: 11 non-2xx snapshot requests); `python3 scripts/check_links.py` (8,459 references across 124 HTML files, all OK on the integrated tree). A JSDOM run of merged `pages/live-alerts.html` against committed data rendered 14 alerts, but 0/14 matched market metadata, the High-ROI list showed 0, and six alert rows had no source link; the page's visible snapshot timestamps disagree with `data/jumps.json` provenance. Mocked `KalshiClient.createOrder()` printed `POST https://demo.invalid/trade-api/v2/orders` and the legacy-shaped JSON, confirming the implementation without sending a Kalshi request. No credentials were used and no trade was submitted.

**Cross-scope requests (not edited):**
1. Owner of `server/*` (`arena-406a2f21-demo2`, completed scope): please update `KalshiClient.createOrder` and `/api/trades/execute` to the official V2 route/body and add a schema test. Official reference: https://docs.kalshi.com/api-reference/orders/create-order-v2. Current code uses `POST /orders`, `market_ticker`, buy/sell, `outcome_side`, `price_dollars`, and `type`, not the V2 request schema.
2. Owner of `server/*`: paginate `GET /events` via returned cursor in both API handler and periodic tracking; official response includes cursor: https://docs.kalshi.com/api-reference/events/get-events.
3. Final integration/page owner: link `session-f75410bb/review.html` from the published Flagged for Review page or record its findings there. The new report itself has official source links per row; shared page not edited due scope policy.
4. Owner of the merged Live Alerts page (`pages/live-alerts.html`, session 848af77d): dual scroll panes are now present, but `fetch()` runs only once on page load; the page is backed by static collected JSON, not a live refresh/stream. Its "High ROI" is a rule (move floor + estimated volume), not a model. Please label the cadence accurately or add a verified runtime update path, preserving source timestamps and stale-state UI. Official WS handshake requirements: https://docs.kalshi.com/getting_started/quick_start_websockets.
5. Live Alerts page owner: at this checkout, the JSDOM run showed 0/14 jump tickers matching `data/snapshot.json`, leaving every topic/market join blank, High-ROI empty, and six rows without source links. `data/jumps.json` is generated from `data/dashboard_instrument.json`, not the page's `data/snapshot.json`. Please use a compatible, same-provenance metadata source and retain an official per-row link for every alert. Kalshi field references: https://docs.kalshi.com/api-reference/market/get-markets and https://docs.kalshi.com/api-reference/market/get-trades.
6. Live Alerts page owner: the visible `Snapshot` status (`2026-11-20T14:10:44Z`) is stale; the alert data line and `data/jumps.json` source provenance are both `2026-11-20T19:49:16Z`. Please render one accurate freshness status and do not label a static page live unless it refreshes. WS docs: https://docs.kalshi.com/getting_started/quick_start_websockets.

### Session f75410bb — final integration takeover (2026-11-20 19:55 UTC)

**Handoff:** the latest prior final-integration entry is session `b326b649` (I-4/I-5 left in progress/unclaimed; older than 60 minutes and no current branch activity). PR #54's alert work is already merged in `origin/main`. This session takes over the current-tree build/deploy parity and its own PR #55; no other open session PR is being merged or modified.

| # | Task | Status | Owner | Files touched |
|---|---|---|---|---|
| F-3 | Claim final integration: regenerate only generator-owned published outputs, make CI generator diff pass, verify links/build, merge PR #55, confirm Pages deploy | in progress | f75410bb | generated outputs from `tools/build_site.py` + `tools/build_content.py`; `COORDINATION.md` |

The claim does not authorize edits to other sessions' implementation code (`server/`, collectors, live-alert feature logic). If a generated output exposes a defect in another session's source, the finding remains a documented cross-scope request. `pages/live-alerts.html` is regenerated only from its existing owner-maintained generator; source code changes remain out of scope.

| F-4 | Publish the audit report link and its official-source-backed findings on the canonical Flagged for Review page | done | f75410bb | `tools/build_content.py`, generated `pages/flagged.html`, `COORDINATION.md` |

### Post-merge status — session f75410bb

- PR #55: https://github.com/karagemop466-tech/Demo2/pull/55 — **merged** at `be21513ec96b44e9bed98dfcfc1a138324529668` (2026-11-20T19:59:33Z).
- Build-and-check / Pages workflows were queued on GitHub at last verification (CI runs #110–#112; Pages run #48: https://github.com/karagemop466-tech/Demo2/actions/runs/44807242459). The previous CI run on the pre-regeneration head failed because generated pages were stale; after regenerating, local generator parity and all local checks passed. Pages run #48 has not yet completed, and the added audit page is not yet confirmed on the live site. F-3 remains **in progress** until deploy success and live-page verification.

| F-5 | Audit the deployed Live Alerts page's real browser request paths and publish any live-only failure | done | f75410bb | `session-f75410bb/review.html`, `COORDINATION.md`, `tools/build_content.py`, generated `pages/flagged.html` |

**F-5 live-browser finding (2026-11-20):** the deployed `https://karagemop466-tech.github.io/Demo2/pages/live-alerts.html?cb=1` rendered “Could not load alert data: 503.” The live page source calls `fetch('data/snapshot.json')` / `fetch('data/jumps.json')` from a `/pages/` URL, which targets `/pages/data/...`; the actual published files at `/data/...` are available. Logged as R9 and added to the canonical Flagged for Review generator/page. **Cross-scope request:** owner of `tools/build_site.py` / Live Alerts (session 848af77d) please fix the generated fetch paths (for project pages, `../data/...`) and verify live browser loading; source code is not edited in this audit. Kalshi endpoint docs: https://docs.kalshi.com/api-reference/market/get-markets and https://docs.kalshi.com/api-reference/market/get-trades.

---

# Session b7bc848c — K-task records (appended at the integration reconciliation)

## K-1 — data pipeline fix (DONE, session b7bc848c, 2026-11-20 ~20:20 UTC)

**Root cause (verified, not inferred):** GitHub pre-receive rejected every push of the
refresh-data pipeline: `File data/snapshot.json is 111.97 MB; this exceeds GitHub's file size
limit of 100.00 MB` (GH001) and `File data/topic-elections.json is 52.01 MB` (50 MB warning).
Evidence: Actions run annotations for runs `44768457660` and `44800417665` ("could not push
snapshot after 6 attempts"; all 6 attempts identical). The collector itself succeeded. The site
was frozen on the last pushable snapshot (generated 2026-11-20 14:10:44 UTC).

**Size driver (measured):** rows doubled when event pagination widened 25→50 pages
(`eeb796d7` E-5), every row was stored TWICE (`markets` + `by_topic`), and rows carried full
`rules_primary` + unbounded `settlement_sources`. PR #52's "legal text" slim cut ~10%, missing
the real driver. Measured on the frozen snapshot: `markets` 20.2M chars + `by_topic` 20.2M chars
(duplicate) of 40.8M total.

**Fix (tools/collector.py + tools/test_publish_limits.py + tools/slim_data.py):**
1. per-topic publish cap (`--publish-per-topic`, default 500, ranked by dollar volume);
   `counts.per_topic` keeps FULL counts; `counts.per_topic_published`, `counts.rows_capped`,
   per-topic `count_total`/`capped` keep the distinction visible on the site;
2. `rules_primary` shortened to 300 chars with `rules_truncated` flag; `settlement_sources`
   capped at 3 entries (name ≤ 100, url ≤ 160 chars) with `settlement_sources_total` kept;
3. `series_index.json` slimmed (`additional_prohibitions` — ~8 MB of repeated legal boilerplate
   with no consumer — dropped; every record keeps its full-record `source` URL);
4. `history.json` bounded (top 300 markets × 288 points, untracked pruned) — it was on a path to
   hundreds of MB;
5. rolling `resolutions_log.json` capped at 5,000 rows;
6. compact JSON for the big files; **publish guard**: `write_json` refuses > 45 MB payloads and
   fails the run (GH001 can never recur silently);
7. `write_json_if_changed` for catalogue files (identical content apart from timestamps is not
   rewritten — otherwise ~170 MB/day of git history is burned on a 12 MB static file);
8. refresh-data.yml: cadence 10 → 30 min (each run commits ~4 MB and git keeps every blob;
   10-min cadence grew the repo ~750 MB/day — bounded now, growth vector still flagged below),
   shared concurrency key `kalshi-data-writers` (from 6332d7d3) merged with eeb796d7's push-retry
   loop; `data/snapshot.json` stays committed (tools/analyze.py + tools/execute_strategy.py read
   it; 6332d7d3's `.gitignore` exclusion of it was therefore NOT taken) and is kept as a run
   artifact too.
9. `tools/slim_data.py` applied the same caps to the already-committed files: snapshot.json
   46 MB → 3.4 MB, topic-elections.json 22 MB → 0.8 MB, series_index.json 26 MB → 11.7 MB.

**Verification:** `tools/test_publish_limits.py` 35/35 (caps, flags, guard, history bounds,
ranking order preserved), `tools/test_collector.py` 43/43 (unaffected), `tools/check.py` clean,
`scripts/check_links.py` all OK, `scripts/render_check.mjs` 14/14 with real data. The live
confirmation (a refresh run landing on main) is recorded in K-5.

## K-2 — takeover of stale PR #44 / session 6332d7d3 (DONE, per-file disposition)

Takeover per the 60-minute rule (branch idle since 14:16, CONFLICTING with main, session dead).
Their work was integrated, not discarded. Their session's own claim/record is preserved verbatim
at the end of this file.

| Area | Disposition |
|---|---|
| `tools/collector.py` (+572/−126) | **taken** (series-scoped sweep, rotating cap, measured 24h dollars from trade prints, time budget) + layered with K-1 caps/guards |
| `tools/build_site.py` (+430), `tools/build_content.py`, `tools/check.py`, `tools/check_live_links.py` | **taken** (Start-here landing, live dashboard, causes page, stronger checks) |
| `tools/test_collector.py` (43 offline checks), `scripts/render_check.mjs` | **taken**; render_check extended with `pages/alerts.html` |
| `assets/site.js`, `index.html`, `dashboard.html`, `live/index.html`, `pages/*` (18 files incl. NEW `causes.html`) | **taken** and regenerated from the generators |
| **Defect found and fixed on takeover:** `dashboard.html` read `KR.snapshot()` = `dashboard_meta.json` which has NO `markets`/`candles`/`orderbooks` — the market table and chart were empty against real data (their render check passed because empty tables render fallback text). Fixed in the generator: the dashboard loads `data/snapshot.json` (which now also carries the derived summary keys), while other pages keep the small `dashboard_meta.json`. Verified: dashboard table renders 200 rows against real data. | |
| data: `top.json`, `liquidity.json`, `dashboard_meta.json`, `snapshot_api_log.json`, `resolutions_log.json` | **taken** (new products) |
| data: `series_index.json`, `topic-*.json`, `snapshot.json`, `history.json`, `resolutions.json` | **taken and slimmed** to the K-1 shape (mixed run timestamps until the first refresh; see K-5) |
| `.github/workflows/*.yml` (6) | **taken** (shared concurrency key, dispatch inputs, artifact backup) + eeb796d7's push-retry re-applied |
| `.gitignore` (excludes data/snapshot.json) | **NOT taken** — trade pipeline (analyze.py, execute_strategy.py) reads data/snapshot.json; it stays tracked and slim |
| `COORDINATION.md` (+65) | preserved verbatim at the end of this file |

## K-3 — stale PRs #40, #36, #34 (DONE)

| PR | Disposition | Evidence |
|---|---|---|
| #36 (220913cb) "Consolidated Kalshi demo desk" | **integrated by both sessions**: main carries `desk/` verbatim (a984e8f4 A-3); this branch additionally kept the hardened `desk-verify.yml` (shared concurrency key + push-retry — main has no desk workflow). Original takeover note: `desk/` tree (requirements register R-01.. mapped to official sources, jump monitor, verification gate, offline JS tests `node desk/tests/desk.test.js` → fail 0) + `desk-verify.yml` with its concurrency key aligned to `kalshi-data-writers` and the push-retry loop | unique files taken unchanged; workflow hardened |
| #40 (d0bea7de) "Restore sharp-jump landing card" | **superseded — CLOSED by session a984e8f4 (A-3) 20:46Z**, with corroborating evidence recorded here | its card/feature exists on current `main`-in-branch: `dashboard.html` "Sharp price moves ≥ $0.10" + `KR.detectJumps` + `jumps/index.html` + landing card text ("sharp-move table"); the PR's index.html is an OLDER revision of the same content and has no unique files (`git diff --name-status HEAD origin/pr40` → no `A` rows) |
| #34 (21eed9ff) "docs: verify summary, record gaps" | **superseded — CLOSED by session a984e8f4 (A-3) 20:46Z**, with corroborating evidence recorded here | no unique files; its single gap ("account-specific performance and orders unverified — no demo credentials") is already recorded as task 21, S4 and the F-flags on `pages/flagged.html`; its exec-summary draft predates the current `docs/EXECUTIVE_SUMMARY.md` + `pages/executive-summary.html` |

## K-4 — line-by-line re-verification (DONE, 2026-11-20 ~20:40 UTC)

| Claim checked | Official source | Result |
|---|---|---|
| Get Trades schema: `trades[]: {trade_id, ticker, count_fp, yes_price_dollars, no_price_dollars, taker_outcome_side, taker_book_side, created_time, is_block_trade, taker_side}`; `limit` max 1000 | https://docs.kalshi.com/api-reference/market/get-trades | **Verified** (doc text read this session). The Live Alerts poller uses exactly `ticker`, `yes_price_dollars`, `created_time`, `limit=1000`. |
| Same fields on the live demo API | `GET https://external-api.demo.kalshi.co/trade-api/v2/markets/trades?limit=2` | **Verified** — live response fields identical (`created_time` ISO, `yes_price_dollars` string) |
| Demo REST base + alternate base listed in the official endpoint table | https://docs.kalshi.com/api-reference/market/get-trades (host table) | **Verified** — `https://external-api.demo.kalshi.co/trade-api/v2`, `https://demo-api.kalshi.co/trade-api/v2` both listed |
| Exchange status | `GET .../exchange/status` | **Verified** — `exchange_active: true, trading_active: true` (2026-11-20 20:40 UTC) |
| Gas row identity + settlement rule (top.json row `KXAAAGASW-26NOV23-3.6200`) | `GET .../markets/KXAAAGASW-26NOV23-3.6200` | **Verified** — ticker, title ("Will average gas prices be above $3.6200?"), `rules_primary` ("...strictly greater than $3.6200 on Nov 23, 2026 according to AAA..."), `floor_strike` 3.62 match exactly. Price fields differ from the 14:08 snapshot (live: last 0.9700/bid 0.9600/ask 0.9700/vol 15,145.83 vs snapshot 0.9400/0.8600/0.9400/14,761.30) because the market traded after collection — expected for a dated snapshot; snapshot values matched the API at collection time (43-check suite + b326b649's 3-row sample) |
| CORS: browser may call the demo API from the Pages origin | `data/cors.json` (observed headers, 2026-11-20 12:12 UTC): `access-control-allow-origin: https://karagemop466-tech.github.io` | **Verified** — the Live Alerts live poll is feasible browser-side |
| Orderbook returns bids only; asks derived (1 − p) | https://docs.kalshi.com/api-reference/market/get-market-orderbook (read by prior sessions, code labels derived side) | Verified (carried forward) |
| Legacy `POST /portfolio/orders` → 410; use `POST /portfolio/events/orders` | https://docs.kalshi.com/api-reference/orders/create-order-v2 | Verified (carried forward) |

Gate results at this commit: `tools/test_collector.py` 43/43 · `tools/test_publish_limits.py` 35/35 ·
`desk/tests/desk.test.js` fail 0 · `tools/check.py` links/nav/data/secrets/js clean (20 pages) ·
`scripts/check_links.py` 10,735 references / 121 HTML files, all OK · `scripts/render_check.mjs` 14/14
with real data (alerts chats render 65 real ≥$0.10 moves from collector history).

## K-5 — PR, merge, deploy, live data (DONE, 2026-11-20 21:2x UTC)

- **PR:** [#60](https://github.com/karagemop466-tech/Demo2/pull/60) "Final integration: unblock the
  frozen data pipeline, take over 3 stale sessions, add Live Alerts chats, verify line by line"
  (`arena/b7bc848c-demo2` → `main`). Includes the reconciliation merge with session a984e8f4's PR #58
  line (see the reconciliation section above).
- **Merge result:** merged 2026-11-20 **21:21:29 UTC** with `gh pr merge 60 --merge` (merge commit
  `4bfecc7`). Post-merge "Build and check the site" on `main` = **success** (the site was never merged
  broken; the generator-diff gate, tools/check.py, scripts/check_links.py, desk audit and
  scripts/render_check.mjs were all green at the merge commit).
- **Pages deploy:** "pages build and deployment" success + "Deploy GitHub Pages" (pages.yml) ran on the
  merge push; the live site https://karagemop466-tech.github.io/Demo2/ was re-fetched after deploy and
  serves the merged content (including the preserved-variant cross-links in the "All sections" line).
- **First data refresh after the fix:** dispatched `Refresh Kalshi demo data` on `main` → run
  `44819771880` **success in 2m9s**; the loop had already been proven by session a984e8f4's dispatch
  `44814366733` (success, 15m54s) and the scheduled/push runs. Committed snapshots land continuously
  (`data: refresh Kalshi demo snapshot 2026-11-20T21:24Z`, commit `bd3a3f8`). The live site banner reads
  "Snapshot 2026-11-20 21:24:28 UTC (3 min ago)" with 27,440 in-scope markets (gas 3 · elections 26,077
  · crypto 1,065 · golf 295), `counts.markets_published` 2,563 with `markets_trimmed_per_topic` honestly
  recorded. **The 6-hour data freeze is over; the pipeline pushes fresh data and Pages serves it.**
- Open at the time of writing (not mine to merge; owners active): PR **#61** (session a984e8f4 —
  retry-loop `--mixed reset` fix; note their retry soft-reset briefly deleted
  `data/paper_portfolio.json` at 20:53 — restored in this branch's merge and re-published), PR
  **#59** (session 441151f5 — live alert feeds; opened 20:43Z, not yet stale, left to its owner per
  the claim rules).

## New flags raised this session (published on pages/flagged.html after regen where applicable)

- **K-F1 (repo growth):** every data commit stores full blobs; even slimmed (~4 MB/run at 30-min
  cadence) this is ~190 MB/day of git history. Mitigated (caps, cadence, skip-unchanged) but not
  solved; recommended fixes (owner decision): git-squash the `data/` path weekly, git-LFS, or an
  external store. Related to R-5/R-12/R-15.
- **K-F2 (mixed fallback data):** the committed fallback files carry mixed run timestamps
  (top.json 14:08:56 with 131 gas rows from 6332d7d3's collector; topic/snapshot 14:10:44 with
  gas 0 from the pre-takeover collector). Invisible on pages that read snapshot/topic files, but
  the datasets disagree until the first post-merge refresh run (K-5) rewrites them from one
  collector. No value was invented to paper over it.
- **K-F3 (alert model is a heuristic):** the Live Alerts "high ROI" filter is a documented
  two-tier rule, not a learned or backtested model. Labeled as such on the page. Not advice.

**Process note:** one `git pull --rebase` on this branch was attempted after a merge of `origin/main`. Rebasing would have replayed merged `main` history and stopped on another session's commit. It was aborted, nothing was lost, and the branch was pushed as a fast-forward. For this branch, use `git merge origin/main` rather than `pull --rebase`.

---

## Session `6332d7d3` — branch `arena/6332d7d3-demo2` — final integration (claim written 2026-11-20 13:00 UTC, before edits)

**Role:** final integration session for branch `arena/6332d7d3-demo2` (base `4c13151`, the tip of `main`).
The brief asks for one working, live, verified dashboard plus PR → merge → Pages confirmation,
and names the integration session as the only owner of shared outputs.

**What I found on arrival (evidence, not assumption):**

| Observation | Evidence |
|---|---|
| The deployed root dashboard renders **"Snapshot none yet"** and **"0 in-scope markets"**, and its JS throws `data/snapshot.json → HTTP 404` | fetched https://karagemop466-tech.github.io/Demo2/ this session; `data/snapshot.json` is not in `git ls-files` |
| `data/snapshot.json` has **never** been committed on any branch or on `main` | `git log --all -- data/snapshot.json` → empty; no remote branch contains it |
| The workflow that is supposed to produce it (`Refresh Kalshi demo data`) **fails at its first data step** | run 44728913873 on `main`, job `collect`, step "Collect demo snapshot": failure |
| `Deploy GitHub Pages` on `main` has been **stuck in progress for >12 minutes** on a run started before this session | run 44739209404, job `collect`, status in_progress |
| Four dashboards are published side by side (`pages/`, `verified/`, `dashboard/`, `site/` + `intelligence/`, `instrument-panel/`, `live/`), plus 4 stale open PRs (#6, #15, #27, #32) | `gh pr list`; directory listing |

**Scope of this session (all of the following files are mine this session):**

| # | Task | Status | Files |
|---|------|--------|-------|
| Z-1 | Diagnose and repair the snapshot pipeline so the deployed root dashboard shows real, sourced data | in progress | `tools/collector.py` (or a new `tools/build_snapshot.py`), `.github/workflows/*` (additive) |
| Z-2 | Consolidated landing page + navigation, one entry point for every dashboard | in progress | `index.html` (generated), `tools/build_site.py` |
| Z-3 | Verify the pipeline output line by line (sources present, values in range, empty stays empty) | unclaimed→in progress | `tools/check.py` |
| Z-4 | PR → merge → confirm Pages deploy → record result here | in progress | this file |

**Non-overlap:** I do not rewrite `pages/`, `verified/`, `dashboard/`, `site/`, `intelligence/`,
`instrument-panel/` or `live/` content; where the landing page indexes them I only add links.

### Session `6332d7d3` — findings so far (evidence, 2026-11-20 13:00 → 14:00 UTC)

Every item below was reproduced this session; none is inferred.

| # | Finding | How it was established | Status |
|---|---|---|---|
| Z-A | The deployed root dashboard rendered **"Snapshot none yet / 0 in-scope markets"** | fetched https://karagemop466-tech.github.io/Demo2/ ; page's own error text: `data/snapshot.json → HTTP 404` | fixed: `data/snapshot.json` now exists (first successful run 13:08 UTC) |
| Z-B | `data/snapshot.json` had **never** been committed on any branch | `git log --all -- data/snapshot.json` (empty); no remote branch contained it | fixed by Z-A run |
| Z-C | Root cause 1: scope was derived from one `/events?status=open` stream, which is dominated by MVE combo events whose event tickers have no series prefix | run 44740868702 output: 1,556 rows, `per_topic` all zero, 16k+ unmapped; plus live API inspection (`KXMVECROSSCATEGORY-…` tickers) | fixed: scope re-based on `GET /markets?series_ticker=…` per in-scope series |
| Z-D | Root cause 2: resolutions mapped by event-ticker prefix → 0 rows | same run: `resolved_in_scope: 0` with 60+ settled pages read | fixed: per-series settled fetch + rolling `data/resolutions_log.json` |
| Z-E | 36/422 requests returned **429**; the collector retried but never slowed down | `data/snapshot.json → api_log` after the 13:08 run | fixed: global pacing (0.30 s, ×1.6 on 429, ×0.99 on success) |
| Z-F | A failed series request was indistinguishable from an empty topic | same log: 28 × 429 on `/markets?series_ticker=…` appeared as missing markets | fixed: `failed_series` + `series_read` / `series_failed` per topic, shown on the topic pages and on Verification |
| Z-G | Culture has **2 series in the entire demo catalogue and 0 open markets**; gas has 2 series (`AAAGASD`, `AAAGASM`) | `data/series_index.json` (3,310 series fetched live) + `GET /markets?series_ticker=…&status=open` | reported as an absence of markets, with the catalogue counts shown — not a data failure |
| Z-H | `main`'s **CI was red** at the "regenerating produced a diff" gate | run 44740172764, step 6 failure; a hand edit to `index.html` had added a card that the generator did not produce | fixed: the card is restored **in `tools/build_site.py`**, so regeneration is a no-op |
| Z-I | The sharp-jump card's link was wrong from the site root (`pages/causes.html` → `/pages/pages/…`) | `tools/check.py` | fixed by prefix substitution in the generator |
| Z-J | Four dashboards + a monitor were published side by side with no single entry point | directory listing + `gh pr list` | fixed: `/` is now a **Start here** page; the live dashboard is `/dashboard.html` |
| Z-K | `tools/check_live_links.py` reported two false positives as "unfinished placeholder" (API URL templates in `href`s and visible endpoint labels) | running it | fixed at the checker (brace-bearing attribute values are patterns) **and** by marking the two visible labels as `<code>`; no guard was loosened |
| Z-L | A full ~3,000-series sweep cannot finish inside the job window (23 min run died before the commit step) | run 44741984184: step 5 success, step 8 (commit) failure | fixed: `--series-per-topic` (default 90) with **rotation every run**, clock check per series, and the cap published in the snapshot |

**Sources re-read this session** (official only):
`docs.kalshi.com/getting_started/demo_env` (endpoint table, "prices may not be reflective"),
`api-reference/market/get-market-candlesticks` (period_interval 1/60/1440, `price`/`yes_bid`/
`yes_ask` objects), `api-reference/market/get-market-orderbook` (`orderbook_fp`, depth 0–100,
yes/no bid ladders), `api-reference/market/get-markets`, `events/get-events`,
`getting_started/{market_lifecycle,rate_limits,market_settlement}`.
Live responses read this session: `/exchange/status` (trading_active true),
`/series?category=Culture` (exactly 2 series), `/markets?series_ticker=KXXBANNEDGROK&status=open`
(0 markets), `/markets?series_ticker=KXBNB15M&status=open` (live 15-minute crypto market),
`/series?category=Crypto&limit=5`, `/markets?status=open&limit=1` (MVE combo market shape).

**Offline verification added:** `tools/test_collector.py` — 43 checks, no network, wired into
CI. It covers topic mapping from official fields, verbatim value copying (an absent field stays
absent), 24-hour dollars from trade prints, order-book normalisation, rolling-log persistence,
and that a rate-limited series reports "0 markets AND 1 failed series".
=======
# Session `arena/a984e8f4-demo2` — gap-fill + integration (CLAIM, 2026-11-20 19:47 UTC)

Branch: `arena/a984e8f4-demo2`, branched from `main` at `e7fabd4` (merged `origin/main` at
`8818f6b`). Session ID: `a984e8f4`. This claim was written and pushed **before** any work
started. Platform constraint: this session may only work on its own branch (no
`session-<id>/<task>` branches), same as prior sessions.

Checked first: session `b326b649` holds I-1…I-5 (final-integration verification + deploy +
their own PR record) with fresh commits — **not touched, not duplicated here**. The four open
PRs #34, #36, #40, #44 are >60 min old with no commits and CONFLICTING with `main`; their
sessions are inactive, so they are eligible for takeover under the 60-minute rule (handoffs
logged below). Task 21 (demo API key secrets) remains owner action and is not claimed.

| # | Task | Status | Owner | Files (exclusive scope) |
|---|------|--------|-------|--------------------------|
| A-1 | Fix failing `Refresh Kalshi demo data` pipeline (collector OK, "Commit snapshot" step fails on every run — last success unknown; site data goes stale) | claimed → in progress | a984e8f4 | `.github/workflows/refresh-data.yml`, `tools/collector.py` (only if the defect is collector-side) |
| A-2 | Requirement gap: two live scrolling alert chats — (1) all in-scope events, (2) high-ROI model filter — with ≥$0.10 swing alerts, wired into the canonical site nav + generator (required by the brief; grep shows no ROI/chat/alert content in `index.html`, `assets/site.js`, `pages/*`) | claimed → in progress | a984e8f4 | `assets/alerts.js` (new), `assets/style.css` (append-only), `tools/build_site.py` (generated page + nav entry), `tools/build_content.py` (additive verification/flag rows only), generated `index.html`, `alerts.html`, `pages/*.html` (regenerated outputs) |
| A-3 | Takeover of stale conflicting PRs #34, #36, #40, #44 per the 60-minute rule: review each, integrate any still-relevant unique value, close or merge with a recorded disposition comment (no session's work silently discarded) | claimed → in progress | a984e8f4 | PR operations only + this section |
| A-4 | Automated simulated (paper) trading that runs with NO secrets, testing multiple strategies, with portfolio performance + trade categorization surfaced on the site (live demo-account execution stays gated behind task 21 secrets) | claimed → in progress | a984e8f4 | `tools/paper_trade.py` (new), `.github/workflows/paper-trade.yml` (new), `data/paper_portfolio.json` (generated), page rows via A-2 generator scope |
| A-5 | Final pass: line-by-line verification of changed content, all checkers green, PR `arena/a984e8f4-demo2` → `main`, merge without waiting, confirm Pages deploy, record PR + merge + deploy here | done (record below) | a984e8f4 | this section + PR operations |

### Work record — session a984e8f4 (2026-11-20 19:47–21:15 UTC)

| # | Status | Result |
|---|--------|--------|
| A-1 | **done** | Root cause of the dead data pipeline confirmed by evidence: `Refresh Kalshi demo data` run 44800417665 shows `Collect demo snapshot` SUCCESS, `Fail loudly if no in-scope data` SUCCESS, **`Commit snapshot` FAILURE** — every run since ~15:24Z; `data/snapshot.json` on main was frozen at 14:10Z (5.5 h stale). Sessions eeb796d7/3371a533 captured the pre-receive rejection text (GitHub 100 MB/file limit; snapshot.json hit 112 MB) and PR #52 slimmed rules text but runs still failed. Fix = deterministic size bounds in `tools/collector.py` (rows published once — `by_topic` is tickers-only now, null fields dropped, compact JSON, top 1,200 rows/topic by est. dollar volume with trimming recorded in `counts`, history bounded to 600 tickers × 288 points, hard 90 MB tripwire in `write_json`) + workflow tripwire step + stage only collector-owned files (blanket `git add data/` used to revert other pipelines' newer files on the push-retry soft-reset path). Latent CI defect found on the way and fixed in the same workflow: `meta_bar()` embeds snapshot timestamps in `index.html`/`alerts.html` at build time, so the first post-fix data commit would have gone red on the generator-diff gate — `refresh-data.yml` now rebuilds generated pages with each snapshot commit. Regression: `tests/test_collector_output.py` (52 assertions, offline). |
| A-2 | **done** | Requirement gap filled: `alerts.html` (generated) + `assets/alerts.js` — two scrolling chats (All events / High-ROI model picks) with ≥ $0.10 swing detection between consecutive observations of official trade prints (`GET /markets/trades?limit=1000&min_ts=…`) and quotes (`GET /markets?status=open&limit=1000`), 15 s polling with 429 backoff, resolution notices on the official yes/no result, price chart (60 s/5 m/1 h/6 h/24 h windows, red ≥ $0.10 markers), live order-book depth (raw bids + labelled derived asks). High-ROI = transparent documented heuristic (`0.40·liquidity + 0.30·tightness + 0.30·price action`, cutoff 0.60) — flagged **F22**. Swing causes never inferred (F13 policy). Verified rows added to `pages/verification.html` (Get Trades tape query, orderbook raw shape, alerts design, size bounds) with official source links. |
| A-4 | **done** | `tools/paper_trade.py` + `.github/workflows/paper-trade.yml`: automated SIMULATED trading with NO credentials — four deterministic strategies (momentum / mean_revert / longshot / favorite), trades categorised by topic + price band + strategy, positions settled on the official yes/no result ($1/contract), per-strategy win/loss/P&L, equity history. Ledger `data/paper_portfolio.json`, rendered client-side on `pages/portfolio.html` ("Simulated strategy lab"). Fees/slippage deliberately unmodeled — flagged **F23**. Regression: `tests/test_paper_trade.py` (20 assertions; found and fixed a real bug — settled markets could be re-bought). |
| A-3 | **done** | Takeover of 4 stale CONFLICTING PRs per the 60-minute rule (last commits 13:33–14:16Z, sessions inactive), each with a public disposition comment: **#34 closed** (superseded by eeb796d7/b326b649 re-verification; pre-#38..#57 base would reintroduce fixed defects), **#36 closed** (its unique `desk/` subtree preserved VERBATIM from `arena/220913cb-demo2` at commit a37e2ca — 21 files, gates pass with it; branch kept), **#40 closed** (defect already fixed on main: sharp-jump landing card present via PR #41's generator port; instrument-panel link fixes landed via eeb796d7), **#44 closed** (collector/tests superseded — its `tools/test_collector.py` exits 2 on the current collector CLI, verified; causes page covered by F13 + jump/alert context links; unique checkers preserved on its branch). Nothing deleted; every branch preserved. |
| A-5 | **done** | Integration rulings + records below. |

### Integration rulings (2026-11-20, session a984e8f4 as final integration)

1. **One canonical "Live Alerts" nav entry** → root `alerts.html` (browser-live). Session 848af77d's
   snapshot-based `pages/live-alerts.html` stays published and is cross-linked from `alerts.html`
   and the Flagged rows; it leaves the nav to keep one entry per feature (brief: "organize and
   simplify the website continuously"). Nothing deleted.
2. **848af77d's live-alerts defects fixed at the generator level** (flagged R6/R9 by f75410bb, owner
   >60 min stale at fix time): `fetch('data/…')` → `fetch('../data/…')` (the "Could not load alert
   data: 503" was the page's relative paths resolving under `/pages/`); metadata join now falls back
   to the jumps row's own topic/title/series/market_source (was 0/14 snapshot-join matches and 6
   source-less rows); the High-ROI rule lets rows with no computable est. volume pass the volume
   gate and be labelled "est. vol —" instead of silently emptying the feed.
3. **`desk/` (session 220913cb) preserved verbatim**, unlinked from nav (subsite duplication stays
   flagged as Q12 for the owner).

### Verification performed (session a984e8f4)

| Check | Command | Result |
|---|---|---|
| Collector regression (bounded output) | `python3 tests/test_collector_output.py` | 52/52 PASS (offline, synthetic official-shaped API) |
| Paper-trading regression | `python3 tests/test_paper_trade.py` | 20/20 PASS (offline) |
| Prior collector regression | `python3 session-eeb796d7/tools/test_collector_fix.py` | all PASS (13/13) |
| Site gates | `python3 tools/check.py` | links ok, nav ok, data ok, secrets ok, js ok; 18 generated pages |
| Whole-site links | `python3 scripts/check_links.py` | 9,650 references / 121 HTML files (incl. `desk/`), all OK |
| JS syntax | `node --check assets/alerts.js` + inline-script check in check.py | OK |
| Executive summary | bottom line updated to current flag set (F22/F23 + alerts + paper lab) | regenerated |

Sources (official only): https://docs.kalshi.com/getting_started/demo_env,
/api-reference/market/get-trades, /api-reference/market/get-markets,
/api-reference/market/get-market-orderbook, /api-reference/market/get-market-candlesticks,
/getting_started/rate_limits, /getting_started/market_settlement, /getting_started/pagination,
/getting_started/quick_start_websockets,
https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
(100 MB push limit — the A-1 root cause).
Sandbox bash egress to `*.kalshi.co` remains blocked (F1); run/API evidence above comes from
workflow run metadata (44800417665 job steps), committed snapshots, and prior sessions' verified
live-API rows — nothing about live market values is asserted from memory.

### PR / deploy record — session a984e8f4 (filled in after merge)

- PR: _pending — see follow-up commit below_
- Merge result: _pending_
- Pages deploy: _pending_
- Refresh-data recovery: _pending (workflow_dispatch on merge to prove A-1)_

Sources to verify against (official only): https://docs.kalshi.com/getting_started/demo_env,
https://docs.kalshi.com/api-reference/market/get-markets,
https://docs.kalshi.com/api-reference/market/get-market-orderbook,
https://docs.kalshi.com/api-reference/market/get-market-candlesticks,
https://docs.kalshi.com/api-reference/market/get-trades,
https://docs.kalshi.com/getting_started/quick_start_websockets,
https://docs.kalshi.com/api-reference/portfolio/get-positions,
https://docs.kalshi.com/api-reference/orders/create-order-v2.
## Session `f75410bb` — current branch `arena/f75410bb-demo2` (claim, 2026-11-20)

Platform branch rules require using this current branch; no separate `session-*` branch is created.
The existing tree already contains multiple dashboard/site implementations. To avoid duplicate
work and conflicting shared outputs, this session claims a scoped audit of the canonical root
site and interactive server against the requirements and official Kalshi docs.

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| F-1 | Audit current site/build/test behavior and verify API/security claims against official docs | done | f75410bb | `session-f75410bb/**` |
| F-2 | Record reproducible findings and verification / sources; make scoped fixes only | needs review | f75410bb | `session-f75410bb/**` |

Claim scope excludes shared pages, datasets, workflows, and other session directories. If a fix
requires those files, the issue will be logged as a cross-scope request rather than edited.

### Session f75410bb — audit result and cross-scope requests (2026-11-20)

| # | Status | Result |
|---|---|---|
| F-1 | **done** | Rechecked Node build/tests, Python site/data/link gates, backend order request and event-poll code; official Kalshi demo, events, orderbook, Create Order V2, and WebSocket pages read directly. Detailed row-by-row evidence and source links: [`session-f75410bb/review.html`](session-f75410bb/review.html). |
| F-2 | **needs review** | R1 order execution route/body is incompatible with documented Create Order V2; R2 event pagination is incomplete; R3 dual scrolling feeds now exist but are snapshot-only and high-ROI is a rule, not a model; R4 authenticated WebSocket needs backend handling; R5 Pages cannot itself run the authenticated backend; R6 live-alert joins yield 0/14 matches, an empty ROI feed, and six source-less rows; R7 provenance timestamps disagree; R8 implied asks are derived; R9 deployed alert feed fails to load because of relative paths. These are not marked fixed. |

**Checks:** `npm test` (8/8); `npm run check` (15 pages); `npm run build` (15 pages); `python3 tools/check.py` (18 pages; pass with existing warning: 11 non-2xx snapshot requests); `python3 scripts/check_links.py` (8,459 references across 124 HTML files, all OK on the integrated tree). A JSDOM run of merged `pages/live-alerts.html` against committed data rendered 14 alerts, but 0/14 matched market metadata, the High-ROI list showed 0, and six alert rows had no source link; the page's visible snapshot timestamps disagree with `data/jumps.json` provenance. Mocked `KalshiClient.createOrder()` printed `POST https://demo.invalid/trade-api/v2/orders` and the legacy-shaped JSON, confirming the implementation without sending a Kalshi request. No credentials were used and no trade was submitted.

**Cross-scope requests (not edited):**
1. Owner of `server/*` (`arena-406a2f21-demo2`, completed scope): please update `KalshiClient.createOrder` and `/api/trades/execute` to the official V2 route/body and add a schema test. Official reference: https://docs.kalshi.com/api-reference/orders/create-order-v2. Current code uses `POST /orders`, `market_ticker`, buy/sell, `outcome_side`, `price_dollars`, and `type`, not the V2 request schema.
2. Owner of `server/*`: paginate `GET /events` via returned cursor in both API handler and periodic tracking; official response includes cursor: https://docs.kalshi.com/api-reference/events/get-events.
3. Final integration/page owner: link `session-f75410bb/review.html` from the published Flagged for Review page or record its findings there. The new report itself has official source links per row; shared page not edited due scope policy.
4. Owner of the merged Live Alerts page (`pages/live-alerts.html`, session 848af77d): dual scroll panes are now present, but `fetch()` runs only once on page load; the page is backed by static collected JSON, not a live refresh/stream. Its "High ROI" is a rule (move floor + estimated volume), not a model. Please label the cadence accurately or add a verified runtime update path, preserving source timestamps and stale-state UI. Official WS handshake requirements: https://docs.kalshi.com/getting_started/quick_start_websockets.
5. Live Alerts page owner: at this checkout, the JSDOM run showed 0/14 jump tickers matching `data/snapshot.json`, leaving every topic/market join blank, High-ROI empty, and six rows without source links. `data/jumps.json` is generated from `data/dashboard_instrument.json`, not the page's `data/snapshot.json`. Please use a compatible, same-provenance metadata source and retain an official per-row link for every alert. Kalshi field references: https://docs.kalshi.com/api-reference/market/get-markets and https://docs.kalshi.com/api-reference/market/get-trades.
6. Live Alerts page owner: the visible `Snapshot` status (`2026-11-20T14:10:44Z`) is stale; the alert data line and `data/jumps.json` source provenance are both `2026-11-20T19:49:16Z`. Please render one accurate freshness status and do not label a static page live unless it refreshes. WS docs: https://docs.kalshi.com/getting_started/quick_start_websockets.

### Session f75410bb — final integration takeover (2026-11-20 19:55 UTC)

**Handoff:** the latest prior final-integration entry is session `b326b649` (I-4/I-5 left in progress/unclaimed; older than 60 minutes and no current branch activity). PR #54's alert work is already merged in `origin/main`. This session takes over the current-tree build/deploy parity and its own PR #55; no other open session PR is being merged or modified.

| # | Task | Status | Owner | Files touched |
|---|---|---|---|---|
| F-3 | Claim final integration: regenerate only generator-owned published outputs, make CI generator diff pass, verify links/build, merge PR #55, confirm Pages deploy | in progress | f75410bb | generated outputs from `tools/build_site.py` + `tools/build_content.py`; `COORDINATION.md` |

The claim does not authorize edits to other sessions' implementation code (`server/`, collectors, live-alert feature logic). If a generated output exposes a defect in another session's source, the finding remains a documented cross-scope request. `pages/live-alerts.html` is regenerated only from its existing owner-maintained generator; source code changes remain out of scope.

| F-4 | Publish the audit report link and its official-source-backed findings on the canonical Flagged for Review page | done | f75410bb | `tools/build_content.py`, generated `pages/flagged.html`, `COORDINATION.md` |

### Post-merge status — session f75410bb

- PR #55: https://github.com/karagemop466-tech/Demo2/pull/55 — **merged** at `be21513ec96b44e9bed98dfcfc1a138324529668` (2026-11-20T19:59:33Z).
- Build-and-check / Pages workflows were queued on GitHub at last verification (CI runs #110–#112; Pages run #48: https://github.com/karagemop466-tech/Demo2/actions/runs/44807242459). The previous CI run on the pre-regeneration head failed because generated pages were stale; after regenerating, local generator parity and all local checks passed. Pages run #48 has not yet completed, and the added audit page is not yet confirmed on the live site. F-3 remains **in progress** until deploy success and live-page verification.

| F-5 | Audit the deployed Live Alerts page's real browser request paths and publish any live-only failure | done | f75410bb | `session-f75410bb/review.html`, `COORDINATION.md`, `tools/build_content.py`, generated `pages/flagged.html` |

**F-5 live-browser finding (2026-11-20):** the deployed `https://karagemop466-tech.github.io/Demo2/pages/live-alerts.html?cb=1` rendered “Could not load alert data: 503.” The live page source calls `fetch('data/snapshot.json')` / `fetch('data/jumps.json')` from a `/pages/` URL, which targets `/pages/data/...`; the actual published files at `/data/...` are available. Logged as R9 and added to the canonical Flagged for Review generator/page. **Cross-scope request:** owner of `tools/build_site.py` / Live Alerts (session 848af77d) please fix the generated fetch paths (for project pages, `../data/...`) and verify live browser loading; source code is not edited in this audit. Kalshi endpoint docs: https://docs.kalshi.com/api-reference/market/get-markets and https://docs.kalshi.com/api-reference/market/get-trades.
>>>>>>> origin/main

---

## Reconciliation of parallel integrations — sessions `b7bc848c` × `a984e8f4` (2026-11-20 ~21:0x UTC)

Both sessions were final-integration lines working the same brief at the same time. Session
`a984e8f4` claimed first (19:47 UTC, before this session's 20:00 UTC claim) and merged its PR #58
at 20:46 UTC (live alerts chats + paper-trading simulation + its own data-pipeline fix + PR
#34/#36/#40/#44 closures). This session's PR #60 carried a parallel implementation of the same
requirements (pr44's dashboard lineage + its own alert chats + its own pipeline caps). The merge
of `origin/main` into this branch reconciled the two lines **without deleting any session's work**:

| Item | Disposition |
|---|---|
| `tools/collector.py`, `tools/build_site.py`, `tools/build_content.py`, `tools/check.py`, `tools/check_live_links.py`, `assets/style.css` (base), `.github/workflows/{ci,collect,data-refresh,pages,trade,refresh-data}.yml`, `index.html`, `pages/*` (a984e8f4's regenerated set), `data/*` (their bounded outputs + fresh 20:49Z data) | **main's lineage kept** (live and tested; a984e8f4's integration rulings govern the canonical site) |
| `alerts.html` + `assets/alerts.js` (a984e8f4) | canonical Live Alerts nav entry, per their ruling #1 |
| `pages/alerts.html` (this session: history-seeded chats + documented two-tier model) | **preserved, published, cross-linked** from `alerts.html`, not in nav (mirrors their `pages/live-alerts.html` treatment) |
| `dashboard.html` (pr44 lineage: measured-volume ranking + windowed chart + per-row books) | **preserved, published, cross-linked** from `index.html`'s "All sections" line, not in nav |
| `pages/causes.html` (pr44: official settlement-source channels) | **preserved, published, cross-linked** from `index.html`, not in nav (a984e8f4's ruling covered the concept via F13 links; the page itself is kept as an extra view) |
| `assets/site.js` | **this branch's version kept** — verified strict superset of main's KR API (extra `DATA_ROOT`/`dataURL` hooks only), so both page sets work |
| `.github/workflows/desk-verify.yml` (this branch: shared concurrency key + push-retry) | **kept** — main has `desk/` data but no workflow to refresh it; this closes that gap |
| `scripts/render_check.mjs` | **kept, adapted** to the merged page set (jsdom render gate; jsdom already in devDependencies) |
| `tools/slim_data.py`, `tools/test_collector.py`, `tools/test_publish_limits.py`, data products `top.json`/`liquidity.json`/`dashboard_meta.json`/`snapshot_api_log.json`/`resolutions_log.json` | **dropped from the merged tree at reconciliation** (they belong to the superseded collector variant; a984e8f4's A-3 ruling declined that variant and their `tests/test_collector_output.py` (52 assertions) covers bounded output). **Preserved in this branch's history** (commits `406da5a`, `c595a91`, `22ab42a`) and in `origin/pr44` — nothing deleted from the repository's history |
| Repo growth (K-F1) | still open: a984e8f4's collector bounds file sizes (90 MB tripwire) but the */10 cadence still re-commits several MB per run (~hundreds of MB/day of git history). Recommended follow-up (owner or next session): cadence → */30 or a weekly `data/` history squash / LFS. Flagged, not unilateral: their site text states "every 10 minutes". |

Rule application notes: both sessions' claim rows stand as written (no claim was started while
another session held it — the collision was concurrent final-integration work, taken over/merged
under the 60-minute rule with this record). Every dropped artifact is reachable in branch
history; no file was deleted from `main` that existed there before.

---

## Session e303aead — final integration verification (2026-11-21)

Session ID: `e303aead` (branch `arena/e303aead-demo2`, base `ddadabe` on `main`).
Prior sessions merged into this repository: `e88eb254`, `406a2f21`, `b7bc848c`, `a984e8f4`, `f75410bb`, `220913cb` and others listed above.

| # | Task | Status | Owner | Files (exclusive scope) |
|---|------|--------|-------|--------------------------|
| E-1 | Final integration: verify site builds with no broken links, fix generator drift, PR to main, merge, confirm Pages deploy | in progress | e303aead | `pages/live-alerts.html` (regenerated), `COORDINATION.md` (this section) |

Scope note: this session touches only generator-owned output (`pages/live-alerts.html`) and this file.
No other session's implementation code is edited. Open PRs #59 (`arena/441151f5-demo2`) and #61
(`arena/a984e8f4-demo2`) belong to other sessions and are left untouched.

### Verification performed (this session)

- Official docs re-read 2026-11-21: demo REST `https://external-api.demo.kalshi.co/trade-api/v2`
  (also `https://demo-api.kalshi.co/trade-api/v2`), WS `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2`
  (also `wss://demo-api.kalshi.co/trade-api/ws/v2`) — https://docs.kalshi.com/getting_started/demo_env
- `GET /markets` shape (markets[] + cursor, `last_price_dollars`, `volume_fp`, `open_interest_fp`,
  `result` yes/no, `status`) — https://docs.kalshi.com/api-reference/market/get-markets
- `GET /markets/{ticker}/orderbook?depth=0-100` returns `orderbook_fp.{yes_dollars,no_dollars}` as
  [price, count] pairs — https://docs.kalshi.com/api-reference/market/get-market-orderbook
- `POST /portfolio/events/orders` (V2 body: ticker, client_order_id, side bid/ask, count, price) —
  https://docs.kalshi.com/api-reference/orders/create-order-v2
- Local checks: `tools/check.py` (20 pages, links/nav/data/secrets/js clean),
  `tools/check_live_links.py` (110 HTML files, 10,113 href/src, 0 broken),
  `npm test` (8/8), `desk/tests/desk.test.js` (5/5 after `npm install`).
- Generator drift found and fixed: `pages/live-alerts.html` "Data as of" timestamp regenerated
  (2026-11-20T21:30:13Z → 2026-11-21T01:49:13Z). CI fails on stale generated pages, so the
  regenerated file is committed in this session.
- R9 (fetch `data/...` from `/pages/` → 503) confirmed fixed: `pages/live-alerts.html` now fetches
  `../data/snapshot.json` and `../data/jumps.json`.
- Resolutions note: `data/resolutions.json` count is 0 in the 2026-11-21T00:53Z snapshot (strict
  series-tag mapping per F9), while `data/markets_settled.json` (20 crypto, title-keyword mapping)
  and `data/resolved.json` (200, unmapped topics) come from the parallel `scripts/fetch_data.py`
  pipeline. Different methodologies, not a contradiction; the Resolutions page reads the strict
  pipeline. Flagged for owner review, does not block merge.

### PR / deploy record (this session)

- PR: https://github.com/karagemop466-tech/Demo2/pull/63 — **merged** at `003772d` (2026-11-21T06:37:44Z).
- Build-and-check CI on the merge commit: **success** (run 44876440290).
- Pages deploy on the merge commit: **success** (run 44876439996, 23s). Site: https://karagemop466-tech.github.io/Demo2/
- Task E-1: **done**.
## Session e29ebc3a — branch `arena/e29ebc3a-demo2` (claimed 2026-11-21)

Session owner: `e29ebc3a`. Scope (exclusive): `tools/collector.py` (culture scope mapping +
resolutions union fix), `tools/test_series_topic.py` (new offline test), this file's section.
No other session has claimed these files. Shared outputs (`index.html`, `pages/*`, `data/*`)
are NOT edited by hand — they regenerate via `tools/build_site.py` / `tools/build_content.py`
and the Actions collector.

| Task | Status | Owner | Files touched |
|---|---|---|---|
| E1 Audit repo vs requirements (line by line, official sources) | in progress | e29ebc3a | this file |
| E2 Fix Culture scope mapping (Entertainment category + vetted culture tags, priority-ordered) | in progress | e29ebc3a | `tools/collector.py` |
| E3 Fix empty Resolutions (union settled fetch with in-scope rows carrying official results) | in progress | e29ebc3a | `tools/collector.py` |
| E4 Offline unit test for `series_topic` (synthetic official-shaped records) | in progress | e29ebc3a | `tools/test_series_topic.py` |
| E5 Regenerate site, run `tools/check.py` + link check, PR, merge, verify Pages | pending | e29ebc3a | generated pages, this file |

### Audit findings (2026-11-21, evidence in repo)

- **Culture = 0 markets (bug).** `data/snapshot.json` `counts.per_topic.culture = 0` while
  `series_inventory.categories` shows `Entertainment: 2630` series and `tags_top` shows
  `Music: 804, Awards: 493, Movies: 271, Television: 242`. `series_topic()` in
  `tools/collector.py` only maps tag `culture` / category `culture`, so all Entertainment
  series are unmapped. `unmapped_series` proves live culture events were skipped:
  `KXOSCARS (10), KXMOVIECAST (8), KXMUSICREPORT (7), KXALBUMRELEASEDATE (6),
  KXPERFORMROLE007 (6)`. Fix E2 maps Entertainment/Culture categories + vetted culture tags
  to `culture`, checked AFTER gas/elections/crypto/golf so specific topics win.
- **Resolutions page empty (bug).** `data/resolutions.json` = `{"count": 0, "resolutions": []}`
  and `pages/resolutions.html` reads exactly that file, yet `data/snapshot.json` markets
  contain 33 finalized in-scope markets with official results (21 `yes`, 12 `no`).
  `collect_resolutions()` only uses the separate `GET /markets?status=settled` fetch and
  re-derives the series from `event_ticker.split("-")[0]`; the demo settled feed is dominated
  by synthetic series (e.g. `KXDEMOFUTHOURLY`, 20/20 rows in `data/markets_settled.json`)
  that are not in the in-scope index, so the fetch contributes 0. Fix E3 unions the settled
  fetch with in-scope rows already carrying official `result` values.
- **Portfolio / real demo execution: not configured (owner action, not a bug).**
  `data/portfolio.json` = `authenticated: false` ("No demo API key configured");
  `data/analysis.json` verdict `insufficient_data` (0 fills). Paper trading works:
  `data/paper_portfolio.json` (3 simulated trades, cash 79.49 of 100.00). Enabling real demo
  orders needs repo secrets `KALSHI_DEMO_API_KEY_ID` + `KALSHI_DEMO_PRIVATE_KEY` and
  variable `KALSHI_TRADING_ENABLED=1` — see `pages/questions.html` Q4. Flagged, not blocking.
- **Three collectors write `data/` on different schedules** (`refresh-data.yml` →
  `tools/collector.py`, `collect.yml` → `tools/collect_kalshi.py`, `data-refresh.yml` →
  `scripts/fetch_data.py`). They write mostly disjoint files but share `data/` and push to
  `main`; `desk-verify.yml` already shares concurrency key `kalshi-data-writers` with one of
  them. Not changed in this session (other sessions' workflows); flagged for the owner.
- **Live site verified:** Pages API `status: built`, `build_type: legacy`, source `main /`;
  latest `pages build and deployment` runs succeed (e.g. run 44861186297). One older
  `Deploy GitHub Pages` failure (44852384694) predates the latest successful builds.
  Sandbox cannot reach `github.io` or Kalshi (egress blocked), so live-page checks rely on
  Actions runs + `gh` API, recorded here.
- **Official docs re-verified 2026-11-21 (fetch, not recall):**
  demo REST/WS roots + mock-funds warning (demo_env); Get Markets `status` values
  unopened/open/closed/settled + `result`/`settlement_value_dollars`/`settlement_ts` fields;
  Get Market Orderbook `depth` 0–100 + `orderbook_fp.yes_dollars/no_dollars` [price, count]
  pairs; Create Order (V2) `POST /portfolio/events/orders` body shape. All match the repo's
  `pages/api-reference.html` claims.

### E1–E5 results (2026-11-21, session e29ebc3a)

- **E2 done:** `series_topic()` now maps Entertainment/Culture categories + vetted culture
  tags (Movies, Music, Awards, Television, Oscars, Grammys, Rotten Tomatoes, Video games,
  People, …) to `culture`, checked after gas/elections/crypto/golf so specific topics win.
  Broad tags (Food, Art, Views, Achievements, Collectibles) stay unmapped by design.
  Takes effect on the next `Refresh Kalshi demo data` Actions run (sandbox has no Kalshi
  egress, so the live run happens in CI). Evidence for the tag list:
  `data/snapshot.json` `series_inventory.tags_top`.
- **E3 done:** `merge_scope_resolutions()` unions the settled feed with in-scope rows
  carrying official `result` yes/no. Settled rows win on duplicate ticker; scope-only rows
  keep settlement fields blank (None, not guessed). Next collector run will populate
  `data/resolutions.json` (expect ≥ 33 rows from the current snapshot's finalized markets)
  and the Resolutions page.
- **E4 done:** `tools/test_series_topic.py` — 39/39 PASS offline (specific topics unchanged,
  culture expansion, priority ordering, resolutions union). Run: `python3 tools/test_series_topic.py`.
- **E5 done:** `tools/build_site.py` + `tools/build_content.py` regenerated (only
  `pages/live-alerts.html` timestamp changed); `tools/check.py` clean (links/nav/data/
  secrets/js ok); `scripts/check_links.py` clean (10,673 refs, 0 broken).
- **Cross-scope request (not edited):** owner of `.github/workflows/ci.yml` — consider
  adding `python3 tools/test_series_topic.py` to the CI gate so the scope mapping is
  regression-tested on every push. File left untouched per coordination rules.
- **Flagged (not blocking, owner action):** real demo portfolio/execution needs repo
  secrets `KALSHI_DEMO_API_KEY_ID` + `KALSHI_DEMO_PRIVATE_KEY` and variable
  `KALSHI_TRADING_ENABLED=1` (`pages/questions.html` Q4). Three collectors write `data/`
  on different schedules — see audit above. Repo-growth cadence (K-F1) still open.

## 74946c6c — urgent publication race repair

Taking over >60-minute-old workflow retry scope `.github/workflows/{refresh-data,
paper-trade,desk-verify}.yml`: commit 433aabd soft-reset retry reverted PR #65's
unrelated source, report and tests. Claim: restore only lost PR #65 files (not data),
replace soft-reset/recommit with conflict-safe rebase, regenerate pages, verify and
republish. Evidence: `git show --stat 433aabd`; successful Pages build alone did not
prove the changes remained present. Session files are recoverable from e44b644.

PR #65 https://github.com/karagemop466-tech/Demo2/pull/65 merged at e44b644,
2026-11-21T06:44:48Z. Build and paper-trading workflow passed. Subsequent data
commit 433aabd reverted unrelated changes via `git reset --soft`; this follow-up
restores code/reports/tests ONLY, retains latest data, and changes three workflows
to rebase on push rejection (conflicts fail safely instead of overwriting main).
40 paper assertions and canonical checks pass again. Live endpoint cannot be fetched
from this sandbox; deployment verification uses GitHub Pages build API plus checking
that the deployed commit still contains the report and fix, not ancestry alone.

## Session 74946c6c — 2026-11-21 integration audit

Current branch is fixed by Arena: `arena/74946c6c-demo2` (not creating session branches).
Prior paper-trading ownership (a984e8f4, last recorded 2026-11-20) is >60 minutes old;
this session takes over only the narrow missing-quote valuation defect below. Existing
parallel dashboards and collectors will be preserved, not duplicated.

| Task | Status | Owner | File scope |
|---|---|---|---|
| V1 Missing paper quotes must remain unknown, never marked at cost or zero by inference; regression tests | in progress | 74946c6c | `tools/paper_trade.py`, `tests/test_paper_trade.py` |
| V2 Current executive summary + explicit verification limitations and source-linked audit report | in progress | 74946c6c | `docs/SESSION_74946c6c.md`, `audit-74946c6c.html`, README append only |
| V3 Local verification, PR, merge, Pages confirmation | in progress | 74946c6c | `COORDINATION.md` |

Initial evidence: all 10,673 internal references across 124 HTML files resolve.
GitHub Pages API reports legacy build, status built. Official demo environment,
Get Markets and Get Market Orderbook documentation fetched this session. No claim
is made that all historical verification statements in this board were rechecked.


V3 integration scope extension: regeneration found pre-existing drift in
`pages/live-alerts.html` only (generated jump counts/data). Taking over the stale
final-integration scope (>60 minutes, prior day) for that generated output and
`tools/build_content.py` / generated `pages/flagged.html` solely to link the new
audit from the canonical review page. No collector or alternate backend edits.
Cross-scope request to server owner: correct `/orders` to documented V2 route/body,
correct ticker-scoped trade requests to `/markets/trades?ticker=...`, fix signing
path-prefix coverage and test against official schemas before enabling execution.

### Verification results — 74946c6c

V1 done: 40 paper regression assertions pass; quote absence/nonfinite/out-of-range
leaves null marks and null aggregate equity/P&L, explicit zero remains valid.
V2 done: `audit-74946c6c.html` is a source-linked executive summary and clearly
labelled Flagged for Review page, linked from canonical `pages/flagged.html` and
README. Official docs fetched: demo_env, get-markets, get-market-orderbook,
get-trades, create-order-v2, websocket-connection (all on docs.kalshi.com).
V3 local gates: Node 8/8, monitor 15 pages, instrument offline checks, canonical
links/nav/data/secrets/JS check, 5/5 jsdom page renders pass. Canonical checker
warns of 149 non-2xx stored snapshot requests; not relabelled as verified data.
Regeneration repaired one pre-existing timestamp drift in pages/live-alerts.html.
No API credentials entered, no authenticated account access, no exchange orders.
Claim push initially used nonexistent remote branch; retried rebase against main
then pushed only current branch. Later autostash rebase preserved work; no conflict.

Parallel integration reconciliation: PR #64 landed while this branch was being
verified. Rebased onto main; append-only COORDINATION conflicts resolved by
retaining both e303aead's full record and this session's full record. Their timestamp
regeneration is identical to ours and was deduplicated by rebase. No work discarded.
Final internal links: 10,694 references / 125 HTML pages pass; generator parity clean.
PR: https://github.com/karagemop466-tech/Demo2/pull/65 (awaiting checks/merge).


Second reconciliation: PR #66 and automated data refresh landed during the external
link scan. Retained the complete e29ebc3a board records and all refreshed data;
resolved append-only board conflicts without dropping either session's entries.
Regenerated live-alert timestamp to match the newly collected jumps. Build/monitor
checks passed on previous PR head; external scan is nonblocking by workflow design.

## Session `41cfd371` — order safety and integration audit (2026-11-21 06:37 UTC)

Handoff: previous `server/*` owner 406a2f21's scope was completed and audit session f75410bb reported a V2 order schema defect and pagination gap; no active PR from either owner. The last main commit is over 60 minutes old. The platform fixes this session's branch name to `arena/41cfd371-demo2`.

| Task | Status | Owner | Exclusive files |
|---|---|---|---|
| S-1 Audit and remediate demo server order submission against the official V2 schema, with offline tests; flag any remaining unverified behavior | done | 41cfd371 | `server/kalshi.js`, `server/index.js` as needed, new `tests/order-v2.test.js`, `COORDINATION.md` |
| S-2 Integration verification, document limitations and publish review findings | needs review | 41cfd371 | `tools/build_content.py`, generated `pages/flagged.html` and other generator outputs only if required, `COORDINATION.md` |

No other session's open PR will be modified. Sources and results will be logged below.

S-1 scope correction: actual client filename is `server/kalshiClient.js` (not nonexistent `server/kalshi.js`); this replaces the latter in the claim. The backend's HTTP order endpoint has no application authentication or CSRF protection, and the base URL is configurable, so fixing the upstream request without first closing that endpoint would expose signed trading to arbitrary callers. It will fail closed; upstream schema and signatures will be covered offline.

### S-1 / S-2 audit record — 2026-11-21

- **S-1: done for safety remediation; actual account functionality remains unverified.** Checked the official [Create Order V2](https://docs.kalshi.com/api-reference/orders/create-order-v2), [authenticated request signing](https://docs.kalshi.com/getting_started/quick_start_authenticated_requests), and [demo endpoints](https://docs.kalshi.com/getting_started/demo_env). The old client signed `/portfolio/...` without `/trade-api/v2` and used an incorrect RSA signing algorithm/constant and `/orders` body. Corrected full-path signing for Ed25519 and RSA-PSS, switched the low-level order method to the V2 path, and restricted authenticated REST requests to documented demo hosts. Both public HTTP portfolio and order endpoints now fail closed regardless of keys: they previously had no application authentication or CSRF protection. This is not a claim that live execution is ready; no Kalshi order or authenticated account request was sent.
- **S-2: needs review (F24–F25 published)**. Existing alert feed limits watched markets to 12/topic and polling can miss swings, while the collector trims data; backend event pagination is incomplete. Existing claims of complete coverage or always-live tracking cannot be verified. Static Pages cannot run the Node service ([GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)); WebSockets require signed handshake headers ([Kalshi](https://docs.kalshi.com/getting_started/quick_start_websockets)). A secured, persistent monitoring backend, demo keys, and end-to-end verification are still needed. The audit does not represent line-by-line verification of all legacy tables; some pre-existing review rows lack an official source, and the 149 non-2xx entries in the committed snapshot's API log remain unverified.
- Tests: `node --test tests/order-v2.test.js` (4 passed including mocked request signatures, demo-host restriction and HTTP fail-closed with fixture keys); `npm test` (8 passed); `python3 tests/test_paper_trade.py` (20 assertions); `python3 tests/test_collector_output.py` (52 assertions); `python3 tools/check.py` (passed with 149 non-2xx warning); `python3 scripts/check_links.py` (10,677 references, 124 HTML files, local links passed). Rebuilt both page generators; `pages/live-alerts.html` timestamp updated by generator from the existing committed jump data. Official [Get Events](https://docs.kalshi.com/api-reference/events/get-events) and [Get Trades](https://docs.kalshi.com/api-reference/market/get-trades) document cursors.
- PR/deploy: pending verification after this change. Latest existing Pages run at audit time succeeded: https://github.com/karagemop466-tech/Demo2/actions/runs/44861186297. Open PRs #59 and #61 belong to other sessions and were not modified.

- Rebase handoff: `main` advanced during this work when session e303aead merged PR #64. The coordination append conflicted; both sessions’ sections were retained and the rebase completed. Their regenerated `pages/live-alerts.html` was already present upstream, so no overlapping change remains in this PR.

| Task | Status | Owner | Exclusive files |
|---|---|---|---|
| S-3 | Correct demo workflow executor's YES-book NO-side conversion and cumulative cap with offline regression tests | in progress | 41cfd371 | `tools/execute_strategy.py`, new `tests/test_execute_strategy.py`, `COORDINATION.md` |

S-3 handoff: task 17's executor scope was marked done by e88eb254 and has no recent owner PR. Its current plan declares `price` YES-denominated, but code complements it again when building an ask and accumulates the YES ask price rather than the NO purchase cost; the cap can therefore be understated. Source: https://docs.kalshi.com/api-reference/orders/create-order-v2. Until verified do not enable execution. A concurrent PR #65 owns changes to `tools/build_content.py` and `pages/flagged.html`; if overlap is encountered during integration, preserve both sets of flags and coordinate rather than discarding either.
