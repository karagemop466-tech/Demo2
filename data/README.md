# data/

Machine-written JSON. Do not edit by hand.

| File | Written by | Contents |
|------|-----------|----------|
| `snapshot.json` | `tools/collector.py` (Actions, every 10 min) | In-scope markets (top rows per topic by estimated dollar volume — `counts` records the full in-scope count and exactly what was trimmed), order books, candlesticks, resolutions, series catalogue, **and the HTTP log of every request**. `by_topic` lists market tickers only; the rows themselves are published exactly once (in `markets`). Compact JSON, and the collector refuses to write any file over 90 MB (GitHub rejects pushes with a file over 100 MB — the 2026-11-20 incident documented in `tools/collector.py`). |
| `topic-<name>.json` | same run | Per-topic slice so each category page loads a small file (slim rows: null fields omitted; `count_in_scope` / `trimmed_by_volume` record the full count and the trimming) |
| `resolutions.json` | same run | Settled in-scope markets with the official `result` |
| `history.json` | same run | Appended tick history used by the price chart — bounded: kept for the top 600 markets by estimated dollar volume, max 288 points each |
| `portfolio.json` | `tools/portfolio.py` (signed) | Balance, positions, fills - or an explicit "not configured" record |
| `analysis.json` | `tools/analyze.py` | Per-fill cost/payout/realised P&L, five categorisations, gated strategies |
| `executions.json` | `tools/execute_strategy.py` | Every order attempt with its HTTP status, including dry runs |
| `strategy_plan.json` | **human** | Trade intents and run limits. Empty by default: nothing is traded. |

Provenance rule: any figure on the site must be traceable to a request listed in
`snapshot.json -> api_log`. If a field is missing, the site renders an em dash instead of a
guessed value.
