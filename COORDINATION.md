# COORDINATION.md — Shared Task Board

Repository: `karagemop466-tech/Demo2`
Branch in use by this session: `arena/1d709f30-demo2` (Arena-assigned; session cannot create other branches)

## Session registry

| Session ID | Branch | Status |
|---|---|---|
| `1d709f30` | `arena/1d709f30-demo2` | active |

> Note: The task instructions prescribe per-session branches named `session-<id>/<task>`.
> This session runs inside Arena, which pins it to a single branch
> (`arena/1d709f30-demo2`). All work by this session happens on that branch only;
> file scopes below are kept non-overlapping so any future session can claim
> disjoint files. If another session appears, it should claim its tasks here
> first and work on its own branch, requesting any cross-scope edits via this file.

## Task board

| ID | Task | Status | Owner | Files | Notes |
|---|---|---|---|---|---|
| T1 | Create/claim coordination board | done | 1d709f30 | COORDINATION.md | Claimed 2026-11-20 |
| T2 | Official-source verification pass (Kalshi docs + demo API) | in progress | 1d709f30 | data/sources.json, docs/VERIFICATION.md | See Sources & Verification log below |
| T3 | Repo review & irregularities | in progress | 1d709f30 | docs/REPO-REVIEW.md | Flagged irregularities listed below |
| T4 | Executive summary | in progress | 1d709f30 | index.html, docs/EXECUTIVE-SUMMARY.md | |
| T5 | Live events dashboard (gas, elections, culture, crypto, golf) | in progress | 1d709f30 | events.html, js/app.js, data/events.json | |
| T6 | Event tracking to resolution (yes/no) | in progress | 1d709f30 | events.html, data/resolved.json | |
| T7 | Portfolio performance page (demo account) | in progress | 1d709f30 | portfolio.html | Data gated on API credentials → flagged |
| T8 | Trade analysis & strategies by trade type | in progress | 1d709f30 | strategies.html, data/strategies.json | |
| T9 | Live price chart (time-axis selector) + liquidity/depth | in progress | 1d709f30 | markets.html, js/chart.js, js/depth.js | |
| T10 | Suggestions section (review & choose before implementing) | in progress | 1d709f30 | suggestions.html, data/suggestions.json | |
| T11 | Open questions / missing information | in progress | 1d709f30 | questions.html, data/questions.json | |
| T12 | Flagged-for-review page | in progress | 1d709f30 | flagged.html, data/flagged.json | |
| T13 | Landing page + navigation + subpages | in progress | 1d709f30 | index.html, css/site.css | |
| T14 | Data pipeline (official API → JSON snapshots) | in progress | 1d709f30 | scripts/fetch_data.py, .github/workflows/data-refresh.yml | |
| T15 | Line-by-line verification of every table row | in progress | 1d709f30 | docs/VERIFICATION.md | Every row carries a source URL; blanks flagged |
| T16 | GitHub Pages publish | in progress | 1d709f30 | .github/workflows/pages.yml, site config | |
| T17 | Final integration, link check, PR → main, merge, deploy confirm | in progress | 1d709f30 | PR #1 | PR link recorded below |

Status values: `unclaimed` | `in progress` | `done` | `needs review`

## Sources & Verification log (official sources only)

| # | Fact verified | Official source URL | Verified on |
|---|---|---|---|
| 1 | REST demo base URL `https://external-api.demo.kalshi.co/trade-api/v2` | https://docs.kalshi.com/getting_started/demo_env | 2026-11-20 |
| 2 | Alt REST demo base URL `https://demo-api.kalshi.co/trade-api/v2` | https://docs.kalshi.com/getting_started/demo_env | 2026-11-20 |
| 3 | WS demo URL `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` | https://docs.kalshi.com/getting_started/demo_env | 2026-11-20 |
| 4 | Alt WS demo URL `wss://demo-api.kalshi.co/trade-api/ws/v2` | https://docs.kalshi.com/getting_started/demo_env | 2026-11-20 |
| 5 | `GET /markets` public fields (ticker, volume, prices, result, status) | https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=1 + https://docs.kalshi.com/openapi.yaml | 2026-11-20 |
| 6 | `GET /events` public fields | https://external-api.demo.kalshi.co/trade-api/v2/events?limit=1 | 2026-11-20 |
| 7 | `GET /markets/{ticker}/orderbook` returns bids/asks depth | https://docs.kalshi.com/openapi.yaml | 2026-11-20 |
| 8 | Auth required for portfolio/orders (API key + Ed25519) | https://docs.kalshi.com/getting_started/api_keys | 2026-11-20 |
| 9 | Live demo REST endpoint reachable, returns live JSON | https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=2&status=open | 2026-11-20 |

## Irregularities flagged (details in docs/REPO-REVIEW.md and flagged.html)

1. Repo was empty except a 1-line README (`# Demo2`) at branch point `6072808`.
2. No LICENSE, no .gitignore, no Pages config present initially.
3. User brief lists two demo base URLs (both officially documented — not a conflict).
4. Portfolio / order-execution endpoints require API credentials that do not exist in this environment → all such values left blank and flagged unverified (per verification rules).
5. Sandbox egress blocks direct `curl` to kalshi.co hosts; verification performed via the platform's page-fetch tool against the same official URLs.

## PR / merge / deploy record

| Item | Value |
|---|---|
| PR | pending |
| Merge result | pending |
| GitHub Pages deploy | pending |
