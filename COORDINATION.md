# COORDINATION.md — Shared Task Board (Kalshi Demo)

**Repo:** karagemop466-tech/Demo2
**Created:** 2026-11-20 (UTC)

## Sessions

| Session ID | Branch | Status | Notes |
|---|---|---|---|
| `arena-ddc587ae` | `arena/ddc587ae-demo2` (platform session branch; PR target `main`) | active | Platform constraint: this session may only work on its assigned session branch. Acts as build + integration session. |

## Task Board

| ID | Task | Status | Owner | Files / Scope | Notes |
|----|------|--------|-------|---------------|-------|
| T1 | Coordination setup | done | arena-ddc587ae | COORDINATION.md | Board created 2026-11-20. |
| T2 | Official API docs research & endpoint verification (line-by-line, official sources) | in progress | arena-ddc587ae | docs/verification notes → `executive-summary.html`, `api-reference` sections | Sources: docs.kalshi.com (official Mintlify docs), live demo REST calls. |
| T3 | Demo API data collection (snapshots: series, events, markets, orderbook, candlesticks, trades, settlement) | unclaimed | — | `data/*.json` | Requires fetch_page (sandbox bash egress is restricted to GitHub/npm/PyPI). |
| T4 | Site build: landing + categorized subpages (clean dashboard UI, tables with per-row source links) | unclaimed | — | `index.html`, `*.html`, `assets/*` | GitHub Pages served from `main` root (already enabled). |
| T5 | Live dashboard: top-dollar live events (gas, elections, culture, crypto, golf), price chart (sec/min/hr), liquidity depth | unclaimed | — | `dashboard.html`, `assets/dashboard.js` | REST public data; WS requires API-key auth headers (verified in docs) → fallback design. |
| T6 | Portfolio & trading: demo account tracking, trade analysis, categorization, strategies, order execution | unclaimed | — | `portfolio.html`, `trading.html`, `assets/*` | BLOCKED on demo API credentials (none found in env/repo). Verify 401 via official docs; flag. |
| T7 | Event resolution tracking (live → settled, YES/NO result) | unclaimed | — | `events.html`, `data/*` | Market `result` enum: yes/no/scalar/'' (official spec). |
| T8 | Suggestions section + open Questions/Information/Answers (missing-info discovery) | unclaimed | — | `suggestions.html`, `questions.html` | |
| T9 | Flagged for Review page (unverified/irregularities, non-blocking) | unclaimed | — | `flagged.html` | |
| T10 | Verification pass: every table row has an official source link; blanks + flags where unverifiable | unclaimed | — | all pages | |
| T11 | Integration: link check, site build check, PR to `main`, merge, confirm GitHub Pages deploy | unclaimed | — | `.github/workflows/*` (if needed), COORDINATION.md | PR from `arena/ddc587ae-demo2` → `main`. |

## Inter-session requests

_(Log requests here instead of editing files owned by another session.)_

## Change log

- 2026-11-20 `arena-ddc587ae`: created COORDINATION.md, claimed T1; claims for T2–T11 pending push.
