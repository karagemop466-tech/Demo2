# COORDINATION — shared task board

Repo: `karagemop466-tech/Demo2` · Integration branch: `arena/3420a90d-demo2` (base `main` @ `6072808`)
Live site (GitHub Pages, source `main` `/docs`): https://karagemop466-tech.github.io/Demo2/

Status values: `unclaimed` · `in progress` · `done` · `needs review` · `blocked`
A `needs review` item is published on the **Flagged for Review** page and does not block anything.

## Session log & claims

| Task | Status | Owner (session) | Files in scope | Notes |
|---|---|---|---|---|
| T0 Board setup + repo review | done | arena-3420a90d | `COORDINATION.md`, `README.md` | Repo contained only `README.md`; board created here. |
| T1 Executive summary | done | arena-3420a90d | `docs/index.html`, `docs/executive-summary.md` | Sources: Kalshi API docs + live demo API responses (see Sources). |
| T2 Market data tables (Gas, Crypto, Elections, Culture, Golf) | done | arena-3420a90d | `docs/markets.html`, `docs/data/snapshot.json` | Only values seen in official API responses; blanks flagged. |
| T3 Resolutions tracker (yes/no outcomes) | done | arena-3420a90d | `docs/resolutions.html` | Uses `result` field from `GET /markets`. |
| T4 Live dashboard (price chart, orderbook liquidity) | done | arena-3420a90d | `docs/live.html`, `docs/assets/live.js` | Client-side REST polling; WebSocket needs auth (see Flagged). |
| T5 Portfolio & trade execution | **blocked** | arena-3420a90d | `docs/portfolio.html` | Requires a Kalshi **demo API key** (authenticated endpoints). Not created — see Flagged. |
| T6 Analysis & strategy categories | done | arena-3420a90d | `docs/analysis.html` | Hypotheses only; no trades executed. |
| T7 Suggestions (decision-first) | done | arena-3420a90d | `docs/suggestions.html` | Nothing implemented until the user selects. |
| T8 Questions / information needed | done | arena-3420a90d | `docs/questions.html` | |
| T9 Flagged for Review page | done | arena-3420a90d | `docs/flagged.html`, `docs/data/flags.json` | Irregularities + unverified items with source links. |
| T10 Integration: build/link check, PR, merge, Pages verify | in progress | arena-3420a90d | all | Final integration step. |

No other session has claimed any task. No merge conflicts occurred (single session on this branch).

## Handoff / conflict log

- _None._

## Verification method (applies to every task)

1. Each row is taken from an official Kalshi API response (`https://external-api.demo.kalshi.co/trade-api/v2/...`, or `https://external-api.kalshi.com/trade-api/v2/...` where stated) or from Kalshi's official docs (`https://docs.kalshi.com/...`).
2. A value not present in an official response is left blank and marked **UNVERIFIED**.
3. Values are never inferred or filled in.
4. Third-party sites (e.g., oddsshopper, cryptostruct) were used only to find ticker names; each ticker was then confirmed against the official API before use.
