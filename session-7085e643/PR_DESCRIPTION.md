# Session 7085e643 — data pipeline fix, live alert desk, simulated strategy desk

Integrates the work of session `7085e643` (branch `arena/7085e643-demo2`, base `e7fabd4`) into
`main`. Scope: the data pipeline, the dashboard's live alerting, the simulated trade desk, and the
registers that document all of it.

## Why this exists

The scheduled `Refresh Kalshi demo data` workflow was dead: it had succeeded through 14:10 UTC on
2026-11-20 and failed every run after that, on all six push attempts, with

```
remote: error: File data/snapshot.json is 111.97 MB; this exceeds GitHub's file size limit of 100.00 MB
remote: pre-receive hook declined
```

So no fresh data reached the site for 5+ hours. The cause was unbounded growth in the published
payload, not the API: `by_topic` duplicated the whole row set (20.23 MB of a 47.26 MB file), the
history file grew one point per market per run across ~10k markets, and a fresh collection pushed the
snapshot past GitHub's 100 MB push limit.

## What changed

**K-1 — the pipeline is bounded and guarded.**
- `tools/collector.py`: a publish budget (rows per topic, then a byte budget with a halving loop),
  `history.json` bounded to published markets and 144 points each, `api_log` trimmed, and the
  `by_topic` duplicate removed. The snapshot now carries `publish_policy` and `coverage`
  (`universe_markets` vs `published_markets`, `complete_enumeration: false`) so a bounded file can
  never be read as the whole exchange. The full universe is written to `data/out/` (gitignored) and
  uploaded as the run artifact.
- `tools/guard_sizes.py`: a pre-commit step that fails the job and names the oversized file, instead
  of six rejected pushes.
- Resolutions are now queried per in-scope series with the documented
  `series_ticker=…&status=settled&min_settled_ts=…` filter. The previous global `status=settled` scan
  returned 0 in-scope rows for 5 hours; a returned row is kept only when its own `event_ticker`
  belongs to the queried series.
- A near-term pass unions short-dated open markets in via the documented
  `GET /markets?status=open&max_close_ts=<now + window>` filter. Without it the snapshot contained
  **zero** in-scope markets closing within 90 days, so no time-to-close rule could ever fire. Rows
  are tagged `source_pass: "events" | "near_term"` and the window is published.

**K-2 — the live alert desk.** `assets/alerts.js` renders the two scrolling chats the brief asks for:
*All events* and *Model screen — high ROI*, on official `last_price_dollars` moves ≥ $0.10 between
consecutive observations of the same market, in either direction. Lines come from a 20-second browser
poll of the documented `GET /markets?tickers=` filter (tagged `live poll`, requested in batches of 20)
or from the collector's 10-minute history (tagged `snapshot`). Each line links the market's own page
and keeps tracking it until the official `result` (yes/no) lands. The high-ROI feed is a printed
heuristic over official fields, not a forecast. Swing comparisons use a 1e-9 tolerance because
`1.00 - 0.90` is `0.09999999999999998` in binary floats and real $0.10 moves were being dropped.

**K-3 — the simulated strategy desk.** `tools/paper_trade.py` places simulated orders on every
refresh from official fields only: entry at the posted `yes_ask_dollars`/`no_ask_dollars` (never
invented), marks at `last_price_dollars`, settlement at `settlement_value_dollars` with a `result`
fallback, fees from the published quadratic form in `Decimal` rounded up to six decimals. It writes
`data/paper_ledger.json`, rendered by the new `pages/paper-trading.html` with the SIMULATED notice,
the fee basis label, and a method table. It is not the demo account and the order book is not
consulted.

**K-4/K-5 — organisation and registers.** Grouped navigation (Desk / Topics / Registers / Preserved
subsites) with a build-time assertion that every nav entry is grouped; a "Start here" strip on the
dashboard; a new session-7085e643 verification table with the exact live requests; a refreshed
executive summary; and flagged rows N-1…N-7 disclosing the publish cap, the dropped rows, the modelled
fee basis, the near-term request, the resolution lower bound, the fill-size assumption and the alert
desk's heuristic.

## Verification

- `python3 tools/check.py` — links, nav, data, secrets, inline-script syntax: clean.
- `python3 tools/paper_trade.py --selftest` — hand-computed sizing, fee rounding, settlement.
- `python3 session-7085e643/tests/test_pipeline.py` — 21 offline assertions on the publish budget,
  byte halving, history bounds, resolution filtering and the size guard.
- `python3 session-eeb796d7/tools/test_collector_fix.py` — 13/13 collector row-schema checks.
- `node session-7085e643/tests/test_alerts.cjs` — 24 offline checks of the alert desk.
- Live API checks on 2026-11-20 (all URLs in `pages/verification.html` and `COORDINATION.md`):
  the `tickers=` filter, the `max_close_ts` short-dated filter, settled-row fields, series fee
  fields, and `exchange/status` (active).

## Flagged irregularities (do not block the merge)

Published on `pages/flagged.html` as N-1…N-7: the snapshot is a bounded payload, not the universe;
fees are a model (`fee_basis: "quadratic model, 0.07 constant — not exchange-confirmed"`); near-term
rows come from a different request than event rows; resolutions are a lower bound; simulated fills
assume the full size at the posted quote; and the alert desk's screen is a heuristic, not a forecast.
Also still open: no demo API key in repository secrets, so portfolio/execution stay "not configured"
(row 21 / Q4); gas has no live markets and culture has none in the collected data; the cause of a
price move is not returned by the API.

## Not included

The four pre-existing PRs (#34, #36, #40, #44) remain open and conflicting; they are triaged, not
merged here. Other sessions' subsites are preserved, not deleted.
