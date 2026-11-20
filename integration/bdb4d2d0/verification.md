# Verification — combined data re-checked line by line (session `arena-bdb4d2d0`, 2026-11-20)

Rule applied: every table row must carry a source link to an official site; a
value that cannot be confirmed from an official source stays blank and is
flagged — never inferred. This file records (1) the automated provenance audit
of every data file, (2) the live re-verification of sample rows against their
exact source URLs, (3) the checker runs over the combined tree, and (4) what is
explicitly **not** verified. Method and scope: [repo-review.md](repo-review.md);
flags: [irregularities.md](irregularities.md).

## 1. Automated provenance audit (every row list in every data file)

Walked every `list-of-dicts` in `data/*.json` and `data/**/*.json`. Result
(rows = 11,430 checked across all files):

| File · list | Rows | Rows with an official kalshi URL | Verdict |
|---|---|---|---|
| `events_top.json` · topics.{gas,elections,crypto,golf} | 1+10+10+6 | 27 / 27 | OK — each row's `source` is its exact event query; `est_dollar_volume_24h` rows also carry `computed:true` + the formula string |
| `resolved.json` · markets | 200 | 200 | OK — per-market `source` URL; `result` copied from official field |
| `series_index.json` · series | 3,310 | 3,310 | OK |
| `dashboard_instrument.json` · series / series_culture_adjacent / markets.{gas,elections,crypto,golf} / resolved | 174 / 2,630 / 1,526 / 1,601 | 5,931 / 5,931 | OK — every row carries its source URL |
| `dashboard_instrument.json` · trades.*.trades | 4,448 | parent `source_url` per ticker | OK — raw trade prints inherit the per-ticker request URL recorded on the parent object |
| `dashboard_instrument.json` · calibration.bands* | 8+8+5 | computed aggregates | OK-by-design — labelled computed on the Analysis page (F-15 discipline: traded markets only, n<30 marked) |
| `api_market_samples.json` · open_markets / settled_markets | 14 / 10 | 24 / 24 | OK |
| `api_reverification.json` · entries | 24 | 24 | OK |
| `api_settlement_sources.json` · sources.* | 141 | URLs **blanked unless opened and confirmed** (F-14 rule; `url_as_recorded` preserved) | OK — exemplary: unconfirmed URLs are blank, not guessed |
| `kalshi_snapshot.json` · rows / flags | 24 / 23 | 24 / 23 | OK — rows carry `source_api`; flags carry `sources` |
| `live_snapshot.json` · market/orderbook/trades/candles | 1+1+500+84 | section-level `*_source` keys on all four | OK |
| `history_instrument/2026-11-20.json` · samples | 8 (→ compact tick rows) | **0** | **FLAGGED (F16)** — no source URL on file or rows |
| `portfolio.json`, `executions.json`, `analysis.json`, `strategy_plan.json`, `pipeline_meta.json`, `cors.json` | 0 rows / meta only | meta carries endpoint + docs URLs | OK — all account values null with reasons, nothing invented |

Conclusion: every rendered table row on the site traces to an official URL;
the single gap is the instrument-panel tick history (F16).

## 2. Live re-verification of sample rows (fetched 2026-11-20 ~13:15–13:25 UTC)

Each row below was re-fetched from its own recorded source URL and compared
field by field. All matched; differences only in fields that move live.

| # | Row (file) | Source URL (from the row) | Checked fields | Result |
|---|---|---|---|---|
| 1 | `resolved.json` → KXXRP-26NOV2006-T1.6399 | https://external-api.demo.kalshi.co/trade-api/v2/markets/KXXRP-26NOV2006-T1.6399 | `result`, `status`, `settlement_ts`, `volume_fp`, `title`, `close_time` | **Match** — live `result:"no"`, `status:"finalized"`, `settlement_ts 2026-11-20T12:10:34.610192Z`, `volume_fp "0.00"`, title identical |
| 2 | `events_top.json` → KXPRESNOMD-28 (top elections event) | https://external-api.demo.kalshi.co/trade-api/v2/events?tickers=KXPRESNOMD-28&with_nested_markets=true | `event_ticker`, `category`, nested `markets[]`, lead-market fields | **Match** — event resolves with child markets (KH/GN/GW/JS/TW… all `event_ticker: KXPRESNOMD-28`); lead market AYAN's snapshot quotes (bid 0.0020 / ask 0.0030) still live-identical; `volume_24h_fp` moved 174,412.23 → 174,506.94 (live drift, row is timestamped 12:12Z) |
| 3 | `live_snapshot.json` → KXPRESNOMD-28-AYAN | https://external-api.demo.kalshi.co/trade-api/v2/markets/KXPRESNOMD-28-AYAN | quotes, sizes, OI, status | **Match** — `yes_bid_size_fp 499999.98`, `yes_ask_size_fp 55555.55` (snapshot 55554.08, live drift), `open_interest_fp 47102372.37`, `status "active"` |
| 4 | `series_index.json` → KXPGATOUR | https://external-api.demo.kalshi.co/trade-api/v2/series/KXPGATOUR | `ticker`, `title`, `category`, `tags` | **Match** — "PGA Tour", `category "Sports"`, `tags ["Golf"]` (re-confirms the Golf-by-tag scoping claim) |
| 5 | Site claim: demo endpoint table | https://docs.kalshi.com/getting_started/demo_env | REST/WS recommended + also-supported URLs, mock-funds warning | **Match verbatim** — `https://external-api.demo.kalshi.co/trade-api/v2`, `https://demo-api.kalshi.co/trade-api/v2`, `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2`, `wss://demo-api.kalshi.co/trade-api/ws/v2`; "price and behavior … may not be reflective of real markets" (F5 claim) |
| 6 | Site claim: create-order required fields | https://docs.kalshi.com/api-reference/orders/create-order-v2 | body schema | **Match** — `price`, `time_in_force`, `self_trade_prevention_type` required; `client_order_id` documented **Optional** (the site row lists exactly the required set); `GTT` "is not a valid API value"; V2 path `POST /portfolio/events/orders` |
| 7 | Site claim: WS handshake requires auth | https://docs.kalshi.com/getting_started/quick_start_websockets | handshake/auth section | **Match** — "WebSocket connections require authentication during the connection handshake"; required headers `KALSHI-ACCESS-KEY/-SIGNATURE/-TIMESTAMP`; public channels still ride the authenticated session (→ browser REST-polling design is correct) |
| 8 | Flag F7 (synthetic demo markets) | live market/event responses (rows 2–3) | `custom_strike` | **Re-confirmed** — `{"demo strike": "demo strike"}` present on KXPRESNOMD-28-AYAN |

## 3. Checker runs over the combined tree (after integration fixes)

| Check | Command | Result |
|---|---|---|
| Generator gate (the step that was red on main) | `cd tools && python build_site.py && python build_content.py` then `git diff` | Only intentional improvements remain (port + corruption fix + context links) |
| Links / nav / data / secrets / scripts | `python3 tools/check.py` | **OK** — "links, nav, data, secrets and scripts all clean" (warning: `data/snapshot.json` not present yet — see F15) |
| Whole-site internal links | `python3 scripts/check_links.py` | **All links OK** — 8,015 references across 85 HTML files |
| Stricter link/placeholder scan | `python3 tools/check_live_links.py` | **Clean** — "no broken internal links, no duplicate ids, no placeholders" (71 files, 7,357 attributes) |
| Instrument-panel smoke (offline) | `python3 instrument-panel/tests_smoke.py` | **All offline checks passed** |
| Instrument-panel build + check | `build_dashboard_site.py` + `check_site.py` | **OK** — owned pages clean (its `site/portfolio.html → flagged.html#FLAG-02` warning is a known false positive: the id is created at runtime by `site/js/app.js` rowId rendering, which `scripts/check_links.py` validates) |
| Python compile | `python3 -m py_compile` on changed generators/helpers | **OK** |
| JS syntax | `node --check` on `assets/site.js`, `assets/app.js`, `app.js` | **OK** |

## 4. Deployed-site spot checks (2026-11-20 13:2x UTC)

| Page | State |
|---|---|
| https://karagemop466-tech.github.io/Demo2/index.html | Renders; dashboard correctly reports *"Data snapshot could not be loaded: data/snapshot.json"* — honest empty state (F15) |
| https://karagemop466-tech.github.io/Demo2/pages/resolutions.html | Renders; data table shows *"Could not load data/resolutions.json … HTTP 404"* (F15). Static definition table intact |
| https://karagemop466-tech.github.io/Demo2/data/pipeline_meta.json | Serves real pipeline metadata (fetch pipeline B healthy) |
| https://karagemop466-tech.github.io/Demo2/data/resolutions.json | **404** — confirms F15 |

## 5. Not verified (kept blank / flagged, never inferred)

- **Demo-account portfolio values** (balance, positions, fills, P&L): no demo
  API key exists in this workspace and the brief forbids manual input → all
  rows blank with the documented reason (F6). Requires the account owner to
  add repository secrets.
- **Any causal claim for sharp price jumps**: the Trade API returns price and
  volume only (verified against `get-markets` / `get-trades` schemas). Jump
  rows link to the market and to a clearly labelled news-search link
  ("not an official source"); causes are never asserted (F13).
- **`data/history_instrument` tick values**: present as captured, but their
  provenance is script-level only (F16).
- **Log body of failed collector run 44728913873**: GitHub blob storage egress
  is denied from this sandbox (EOF) — failure step is known
  ("Collect demo snapshot"), the message is not. Left blank on purpose.
