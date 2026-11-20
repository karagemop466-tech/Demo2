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

## Session `3371a533` — branch `arena/3371a533-demo2` (claim written 2026-11-20 UTC, before edits)

Base: `main` at `4c13151` (PR #31). Board re-read at claim time: every existing task is `done`, no task
is unclaimed or in progress, so this session claims only the gaps it verified.

**Gap check (verified by grep on the branch, not assumed).** No page on `main` shows a ≥ $0.10 price
move with a time window, and none links candidate causes. Kalshi connector: `list_connector_tools` →
`unsupported`; no demo API key exists in this sandbox, so demo-account portfolio and order execution
cannot be run from here (see flags below).

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| J-1 | Price-jump alerts: sample-to-sample moves ≥ $0.10 from the official demo-API snapshots, with time window, coverage counts, and an explicit blank cause column | claimed | 3371a533 | `tools/build_jumps.py` (new), `jumps/index.html` (new, generated), `data/jumps.json` (new, generated) |
| J-2 | Repo irregularity review: each claim checked against the file, git history, or an official GitHub/Kalshi doc page | claimed | 3371a533 | `jumps/repo-review.html` (new, generated); flag rows appended via `tools/build_jumps.py` |
| J-3 | Integration: nav link to `jumps/` added to the generator, CI gates re-run, PR to `main`, merge, Pages deploy check, record | claimed | 3371a533 | `tools/build_site.py` NAV (one additive row), `pages/flagged.html` via `tools/build_content.py` (additive flag rows), this section |

Scope rules: no edit to another session's page content; shared generated files are regenerated only by
their own generator; every other edit is additive and logged below.

### Results — session 3371a533 (J-1, J-2 done; J-3 integration in progress)

| # | Status | Result | Where |
|---|--------|--------|-------|
| J-1 | done | 39 trade-print moves ≥ $0.10 across 12 markets (newest first, each with both prints' size and the official trades-API source); snapshot moves ≥ $0.10: 0 (733 pairs, gaps 2.2–47.2 min). Cause column is blank and marked unverified on every row. | `jumps/index.html`, `data/jumps.json`, `tools/build_jumps.py`, `pages.yml` step (added) |
| J-2 | done | Repo findings R12–R19 and flags F13–F20 added (each with a source link). Two items are security/scope flags, not just notes: **F20 / R18** — `live/trading.html` takes a pasted demo private key in the browser; **R19** — two instrument-panel source links still contain literal `{ticker}` / `{category}`. | `tools/build_content.py` → `pages/flagged.html`, `pages/repo-review.html` |
| J-3 | in progress | Nav entry added (`jumps/index.html`, "Price Jumps"); executive summary "Bottom line" corrected (it said everything was built and sourced; it is not — see F13, F16, F18, F19, F20). | `tools/build_site.py` (one NAV row), `tools/build_content.py` (executive summary paragraph), regenerated pages |

#### Sources read this session (official; each fetched or queried on 2026-11-20 UTC)

- https://docs.kalshi.com/api-reference/market/get-trades — `limit` max 1000, `cursor` pagination, trade fields (used for J-1 and F15).
- https://external-api.demo.kalshi.co/trade-api/v2/markets/trades?ticker=KXSCOTTIESLAM-28&limit=3 — live check: the three newest prints match the snapshot (trade `0725a27c…` at 0.55 and `0724c91a…` at 0.45, times and counts equal).
- https://external-api.demo.kalshi.co/trade-api/v2/series?category=Culture — live: 2 series (`KXXBANNEDMURRAYHILLGUY1`, `KXXBANNEDGROK`), both one-off (F19).
- https://kalshi.com/markets/kxaaagasd — the series web-page pattern `kalshi.com/markets/<series>` redirects to the full market page (checked for one series only; used for the "Kalshi page" link on J-1).
- https://docs.kalshi.com/api-reference/market/get-series-list — `category` filter (matches `categories` list), `tags`, `frequency` (F13, F14, F19).
- https://docs.kalshi.com/getting_started/quick_start_websockets — the `trade` channel is public data, but the handshake requires API-key headers (F16, F18).
- https://docs.kalshi.com/getting_started/api_keys — key types, signing, storage; the private key is shown once (F18, F20).
- https://docs.kalshi.com/getting_started/demo_env — demo base URL; demo setup tutorial link (F18, R17, R19).
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency — a concurrency group serialises only runs that share its key (R12).
- https://git-scm.com/docs/gitignore — NOTES: "To stop tracking a file that is currently tracked, use git rm --cached" (R14).

#### Verification performed

- Regenerated every page with `tools/build_site.py` and `tools/build_content.py`; the CI diff gate still passes on the committed output.
- `tools/check.py` → all clean; `scripts/check_links.py` → 0 broken internal links (8,217+ references across 86 HTML files).
- `tools/build_jumps.py` run on the committed snapshot; output checked: every table row has a source link (39/39 move rows, 12/12 coverage rows); no `None`/`nan`/`undefined` values.
- `instrument-panel/tests_smoke.py`, `instrument-panel/tools/validate_data.py`, `instrument-panel/tools/check_site.py` → pass. `.github/workflows/pages.yml` parses as YAML (checked in a venv).
- Every claim in F13–F20 and R12–R19 was checked against the file, the API response, or the official doc listed above. Two earlier draft claims were **wrong** and were corrected before commit: R18 said no page takes a key (it does: F20), and the executive summary overstated completeness.

#### Irregularities flagged (open for review; none block merge)

- F13 gas topic includes solar, electricity, refinery and Louisiana oil-and-gas jobs (18 markets).
- F14 elections: 2,409 series dropped by the 300-per-topic cap.
- F15 trade history: one page per market, first 600 prints kept, cursor never followed.
- F16 snapshots too coarse for intraday moves of $0.10 (733 pairs, gaps up to 47 min).
- F17 no official source gives a cause for a price move; cause column left blank.
- F18 demo portfolio and order execution cannot run from this workspace (no key; `gh secret list` → HTTP 403).
- F19 culture has 0 open markets (2 one-off series exist).
- F20 public page `live/trading.html` takes a demo private key in the browser (sessionStorage).
- R12 five workflows, five concurrency keys, all pushing to `main`.
- R13 four bots push straight to `main`; `collect.yml` uses `git pull --rebase ... || true`.
- R14 two `.pyc` files tracked despite `.gitignore`.
- R15 four collectors and three link checkers with overlapping jobs.
- R16 eight-plus parallel sites with overlapping pages.
- R19 two instrument-panel source links contain unfilled `{ticker}` / `{category}`.

#### Shared-file edits made by this session (all additive or regenerated; logged here as required)

- `.github/workflows/pages.yml`: one new step (`python3 tools/build_jumps.py`) and the `jumps/` + `data/jumps.json` paths added to the existing `git add` line. No other lines changed.
- `tools/build_site.py`: one NAV row for `jumps/index.html`.
- `tools/build_content.py`: F13–F20 appended to `FLAGGED`, R12–R19 appended to `REPO_FINDINGS`, the flagged-table source column accepts full URLs, and the executive-summary "Bottom line" paragraph was rewritten to match the verified state.
- Regenerated: `index.html`, `pages/*.html` (nav change and new rows only).

#### Not done (blocked or out of scope for this session)

- Demo-account portfolio tracking and order execution (F18): needs a demo key and secrets from the owner. No key was invented.
- Live (seconds/minutes/hours) price stream: the jump page is a static build of collected data; a WebSocket trade feed needs the same key (F16, F18).
- Consolidating the eight sites (R16) and removing the tracked `.pyc` files (R14): recommended, not done here because the files belong to other sessions.
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
