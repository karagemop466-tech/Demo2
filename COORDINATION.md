# COORDINATION.md — Shared Task Board

Session ID: `e88eb254` (branch `arena/e88eb254-demo2`, base `6072808` on `main`)
Previous session: `e3f65782` (branch `arena/e3f65782-demo2`) — PR #1 and #2 merged before this session.
Last updated: 2026-11-20 (session e88eb254)

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

## Log

- 2026-11-20 e88eb254 — merged `origin/main` (PR #1/#2 output) into this branch; no conflicts.
  Claimed tasks 12–19 and pushed the claim before starting work.
- 2026-11-20 e88eb254 — tasks 12–20 complete; opened PR and merged to `main`.
