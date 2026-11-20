# data/

Machine-written JSON. Do not edit by hand.

| File | Written by | Contents |
|------|-----------|----------|
| `snapshot.json` | `tools/collector.py` (Actions, every 10 min) | In-scope markets, order books, candlesticks, resolutions, series catalogue, **and the HTTP log of every request**. A **bounded publish payload**: `coverage` states the universe vs published counts, so a capped file never reads as a complete enumeration |
| `paper_ledger.json` | `tools/paper_trade.py` (Actions, every 10 min, after the collector) | The **simulated** strategy desk's ledger: trades, runs, per-strategy performance. Not the demo account; every fee carries `fee_basis: "quadratic model, 0.07 constant — not exchange-confirmed"` |
| `topic-<name>.json` | same run | Per-topic slice so each category page loads a small file |
| `resolutions.json` | same run | Settled in-scope markets with the official `result` |
| `history.json` | same run | Appended tick history used by the price chart |
| `portfolio.json` | `tools/portfolio.py` (signed) | Balance, positions, fills - or an explicit "not configured" record |
| `analysis.json` | `tools/analyze.py` | Per-fill cost/payout/realised P&L, five categorisations, gated strategies |
| `executions.json` | `tools/execute_strategy.py` | Every order attempt with its HTTP status, including dry runs |
| `strategy_plan.json` | **human** | Trade intents and run limits. Empty by default: nothing is traded. |

`data/out/` (gitignored, uploaded as the run artifact) holds the **complete** collected universe of
the same run, so the bounded published payload can always be re-derived and audited.

Provenance rule: any figure on the site must be traceable to a request listed in
`snapshot.json -> api_log`. If a field is missing, the site renders an em dash instead of a
guessed value.
