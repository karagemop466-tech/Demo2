# COORDINATION.md — Shared Task Board

Session ID: `e88eb254` (branch `arena/e88eb254-demo2`, base `6072808` on `main`)
Previous session: `e3f65782` (branch `arena/e3f65782-demo2`) — completed, PR #1 merged, PR #2 merged.
Last updated: 2026-11-20 (session e88eb254)

> Rule: claim a task (write session ID + file scope) and commit/push the claim **before** starting it.
> Never start a task another session has claimed. Keep scopes non-overlapping.
> If you must change a file owned by another session, log a request here instead.

## Claims by session `e88eb254`

| # | Task | Status | Owner | Files touched (exclusive scope) |
|---|------|--------|-------|---------------------------------|
| 12 | API surface re-verification vs official docs (docs.kalshi.com) | in progress | e88eb254 | `data/api_reference.json`, `pages/api-reference.html` |
| 13 | Data collector (GitHub Actions, real demo-API snapshots) | in progress | e88eb254 | `tools/collector.py`, `.github/workflows/refresh-data.yml` |
| 14 | Rebuild live dashboard (chart windows, orderbook liquidity, ranking) | in progress | e88eb254 | `index.html`, `assets/site.js`, `assets/site.css` |
| 15 | Category pages from real data | in progress | e88eb254 | `pages/gas.html`, `pages/elections.html`, `pages/culture.html`, `pages/crypto.html`, `pages/golf.html`, `assets/category.js` |
| 16 | Resolution tracking (live → resolved yes/no) | in progress | e88eb254 | `pages/resolutions.html`, `tools/collector.py` (resolution block) |
| 17 | Portfolio + trade execution + trade analysis/strategies | in progress | e88eb254 | `pages/portfolio.html`, `pages/analysis.html`, `tools/portfolio.py`, `tools/execute_strategy.py`, `.github/workflows/trade.yml` |
| 18 | Executive summary + questions register + suggestions board | in progress | e88eb254 | `pages/executive-summary.html`, `pages/questions.html`, `pages/suggestions.html` |
| 19 | Line-by-line verification, sources, flagged, repo review | in progress | e88eb254 | `pages/verification.html`, `pages/sources.html`, `pages/flagged.html`, `pages/repo-review.html` |
| 20 | Final integration: link check, build, PR, merge, deploy verification | unclaimed | — | all shared outputs (integration only) |

Notes on scope overlap with session e3f65782:
- The rows above intentionally re-own the same filenames produced by e3f65782, because a
  correctness defect was found in their output (see `pages/flagged.html` F7: the order-placement
  call targets an endpoint the official docs state now returns `410 Gone`). e3f65782 is merged and
  inactive; if it resumes it must not edit these files without logging a request here.
- Shared outputs (navigation, site index, data files) are changed only by the final integration
  session (#20), which is this session.

## Handoff / takeover rule

If a claim is >60 minutes old with no commits, any session may take over. Log the handoff in the
"Log" section below. No handoffs so far.

## Log

- 2026-11-20 e88eb254 — merged `origin/main` (PR #1/#2 output from e3f65782) into this branch to
  avoid conflicts; no merge conflicts occurred. Claimed tasks #12–#19 above and pushed this claim
  before starting work.
