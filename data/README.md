# data/

Machine-written JSON. Do not edit by hand.

| File | Written by | Contents |
|------|-----------|----------|
| `snapshot.json` | `tools/snapshot_from_instrument.py` (Actions, every 15 min) | Canonical root snapshot: in-scope markets, order books, resolutions, series catalogue, **and the HTTP log of every request**. Adapted from `data/dashboard_instrument.json`, which the instrument-panel collector (`instrument-panel/tools/kalshi_collect.py`) produces via bounded per-series collection. |
| `topic-<name>.json` | same run | Per-topic slice so each category page loads a small file |
| `resolutions.json` | same run | Settled in-scope markets with the official `result` |
| `history.json` | same run | Traded price history used by the price chart |
| `portfolio.json` | `tools/portfolio.py` (signed) | Balance, positions, fills - or an explicit "not configured" record |
| `analysis.json` | `tools/analyze.py` | Per-fill cost/payout/realised P&L, five categorisations, gated strategies |
| `executions.json` | `tools/execute_strategy.py` | Every order attempt with its HTTP status, including dry runs |
| `strategy_plan.json` | **human** | Trade intents and run limits. Empty by default: nothing is traded. |

Provenance rule: any figure on the site must be traceable to a request listed in
`snapshot.json -> api_log`. If a field is missing, the site renders an em dash instead of a
guessed value.
