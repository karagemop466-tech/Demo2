# COORDINATION — shared task board

Repo: `karagemop466-tech/Demo2` · Integration branch: `arena/3420a90d-demo2` (base `main` @ `6072808`)
Live site (GitHub Pages, source `main` `/docs`): https://karagemop466-tech.github.io/Demo2/

Status values: `unclaimed` · `in progress` · `done` · `needs review` · `blocked`
A `needs review` item is published on the **Flagged for Review** page and does not block anything.

## Session log & claims

| Task | Status | Owner (session) | Files in scope | Notes |
|---|---|---|---|---|
| T0 Board setup + repo review | done | arena-3420a90d | `COORDINATION.md`, `README.md` | Repo contained only `README.md`; board created here. |
| T1 Executive summary | done | arena-3420a90d | `docs/index.html` | Sources: Kalshi API docs + live demo API responses (see Flagged → Sources). |
| T2 Market data tables (Gas, Crypto, Elections, Culture, Golf) | done | arena-3420a90d | `docs/markets.html`, `docs/data/snapshot.json` | Only values seen in official API responses; blanks flagged. |
| T3 Resolutions tracker (yes/no outcomes) | done | arena-3420a90d | `docs/resolutions.html` | Uses `result` field from `GET /markets`. |
| T4 Live dashboard (price chart, orderbook liquidity) | done | arena-3420a90d | `docs/live.html`, `docs/assets/live.js` | Client-side REST polling; WebSocket needs auth (Flagged U2). CORS from browser unverified (Flagged U3). |
| T5 Portfolio & trade execution | **blocked** | arena-3420a90d | `docs/portfolio.html` | Requires a Kalshi **demo API key** (authenticated endpoints). No key in workspace; no trades placed. Flagged U1. |
| T6 Analysis & strategy categories | done | arena-3420a90d | `docs/analysis.html` | Hypotheses only; no trades executed. |
| T7 Suggestions (decision-first) | done | arena-3420a90d | `docs/suggestions.html` | Nothing implemented until the user selects. |
| T8 Questions / information needed | done | arena-3420a90d | `docs/questions.html` | |
| T9 Flagged for Review page | done | arena-3420a90d | `docs/flagged.html`, `docs/data/flags.json` | Irregularities + unverified items with source links. |
| T10 Integration: build/link check, PR, merge, Pages verify | in progress | arena-3420a90d | all | Final integration step. Link check + jsdom run of all 9 pages: no broken local links, no script errors. |

## Task log (sources, verification, irregularities)

- **T2/T3 data**: Series, markets, events, orderbook, candlesticks and settled markets read from `https://external-api.demo.kalshi.co/trade-api/v2/...` (demo) and `https://external-api.kalshi.com/trade-api/v2/...` (production, KXAAAGASM only). Field names checked against `docs.kalshi.com` (Get Markets, Get Series List, Candlesticks, Orderbook Responses, Market Settlement, Rate Limits, WebSocket Quick Start, API Environments).
- **Verification performed**: each snapshot row was re-read from the API response it cites. Gas 4.80 and 4.70 quotes were re-fetched (`markets?tickers=`). The KXBTCMINY-27JAN01-50000.00 orderbook top bid ($0.23) and implied YES ask ($0.24) matched the market's `yes_bid`/`yes_ask`. Market endpoint returns `{"market": {...}}`; candlesticks return `candlesticks[].price.close_dollars`.
- **Irregularities found**: F1–F15 on `docs/flagged.html` (placeholder and search-engine settlement sources; demo vs production metadata; docs status-enum mismatch; last price outside quote; one-sided quote with open interest; missing metadata; demo-only markets; category mapping; contracts-not-dollars; and others).
- **Sample coverage**: Elections and Sports listings were too large for the fetch tool; the site shows a documented sample (see Flagged U7).
- **Handoffs/conflicts**: none.


No other session has claimed any task. No merge conflicts occurred (single session on this branch).

## Handoff / conflict log

- _None._

## Verification method (applies to every task)

1. Each row is taken from an official Kalshi API response (`https://external-api.demo.kalshi.co/trade-api/v2/...`, or `https://external-api.kalshi.com/trade-api/v2/...` where stated) or from Kalshi's official docs (`https://docs.kalshi.com/...`).
2. A value not present in an official response is left blank and marked **UNVERIFIED**.
3. Values are never inferred or filled in.
4. Third-party sites (e.g., oddsshopper, cryptostruct) were used only to find ticker names; each ticker was then confirmed against the official API before use.
