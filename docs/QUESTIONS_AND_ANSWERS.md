# Questions, Information & Answers

> A clear log of the questions that must be answered before any decision can be
> reasonably made, what we already know (with verified sources), what we do **not**
> know, and concrete suggestions to discover the missing information. Nothing here is
> inferred — gaps are stated as gaps.

Status legend: **Have** = confirmed from an official source.
**Don't have** = not available / not verifiable in this environment.
**Suggestion** = a concrete action to discover the missing information.

---

## A. Environment & connectivity

### Q1. Can this environment reach the Kalshi demo API?
- **Question:** Is the Kalshi demo REST/WS endpoint reachable for live data?
- **Have:** The documented endpoints
  (https://docs.kalshi.com/getting_started/demo_env). The sandbox reaches
  `github.com`, `registry.npmjs.org`, `pypi.org` fine.
- **Don't have:** Direct connectivity to `*.kalshi.co`. A `curl` to
  `https://external-api.demo.kalshi.co/trade-api/v2/exchange/status` fails with a
  TLS reset / HTTP 000 because outbound access is allowlisted and excludes kalshi.co.
- **Answer:** Not from this sandbox. The backend is written to call Kalshi, but live
  data cannot be fetched or verified here.
- **Suggestion:** Deploy/run the backend in an environment with kalshi.co egress
  allowed; add a health check (`GET /exchange/status`) and surface the result in the
  UI so connectivity is always visible.

### Q2. Which demo base URL should the app use?
- **Have:** Recommended `https://external-api.demo.kalshi.co/trade-api/v2`; also
  supported `https://demo-api.kalshi.co/trade-api/v2` (REST), and the matching WS
  hosts (https://docs.kalshi.com/getting_started/demo_env).
- **Don't have:** Any internal reason one is preferred over the other for this use.
- **Answer:** Default to the **recommended** demo endpoint; keep the alternate as a
  configurable fallback.
- **Suggestion:** Make `baseUrl` configurable and auto-probe both hosts at startup;
  pick the one that answers `/exchange/status` first.

## B. Authentication & trading authority

### Q3. Do we have a Kalshi demo API key pair?
- **Question:** Are `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-TIMESTAMP`, and
  `KALSHI-ACCESS-SIGNATURE` (Ed25519/RSA) available?
- **Have:** The exact signing scheme and header names
  (https://docs.kalshi.com/getting_started/api_keys).
- **Don't have:** A key ID or private key in the environment.
- **Answer:** No. Trade execution and authenticated portfolio reads cannot be
  exercised without a demo account key pair.
- **Suggestion:** Generate a demo key pair from the demo account
  (https://kalshi.com/account/profile → API Keys, or
  `POST /trade-api/v2/api_keys/generate`), supply it to the backend via environment
  variables (never committed), and confirm with `GET /portfolio/balance`.

### Q4. Which key type — Ed25519 or RSA?
- **Have:** Ed25519 is recommended (lower signing cost, 64-byte signatures); RSA
  (2048-bit, RSA-PSS + SHA-256) is the fallback; both share identical headers/errors
  (https://docs.kalshi.com/getting_started/api_keys).
- **Don't have:** A key, so the type is unset.
- **Answer:** Use **Ed25519** by default; support RSA transparently in the signer.
- **Suggestion:** Implement key-type auto-detection from the parsed PEM (as the docs'
  samples do) so either type works without configuration.

### Q5. What tier/rate limits apply to trading?
- **Question:** What are our token budgets, write budgets, and concurrent WS limits?
- **Have:** Rate limits are tier-based (token budgets, burst capacity, WS connection
  limits) — https://docs.kalshi.com/getting_started/rate_limits. Batch order size
  scales with the tier's write budget —
  https://docs.kalshi.com/api-reference/orders/batch-create-orders-v2.
- **Don't have:** Our specific tier, so exact budgets are unknown.
- **Answer:** Not determinable without the account tier.
- **Suggestion:** Read the account tier from the demo account and size polling and
  order batches conservatively; implement exponential backoff on `429`
  `too_many_requests` (WS) and on REST rate errors.

## C. Data & coverage

### Q6. Which event categories map to the five topics?
- **Question:** How do we filter Kalshi events to gas prices, elections, culture,
  crypto, and golf only?
- **Have:** `GET /events` supports `series_ticker`, `tickers`, `status`, timestamps;
  `GET /series` returns a series `category` field
  (https://docs.kalshi.com/api-reference/market/get-series, get-events).
- **Don't have:** An official, enumerated list of which series/categories correspond
  exactly to each of the five topics, and whether "culture" is a single category or
  a set of categories.
- **Answer:** Filtering by a known category string is possible, but the exact
  mapping is **unverified**.
- **Suggestion:** Discover candidate series per topic via `GET /series` /
  `GET /events` and build a reviewed ticker/category whitelist (store it as
  data, not code), then verify each series' `category` and title against the live
  series endpoint.

### Q7. How do we rank events by "highest dollar amount"?
- **Question:** What is "dollar amount" — volume, notional, or open interest?
- **Have:** Markets expose `volume_fp` (contracts traded) and candlesticks expose
  `volume_fp` and `open_interest_fp`; orderbook exposes price/count
  (https://docs.kalshi.com/api-reference/market/get-market-candlesticks,
  get-market-orderbook). Contract price is in dollars
  (`yes_bid_dollars`, `yes_ask_dollars`).
- **Don't have:** A single official "dollar amount" field; notional
  (price × volume) must be computed.
- **Answer:** "Dollar amount" is not a single official field. The dashboard computes
  **notional ≈ price × volume** and labels the metric clearly.
- **Suggestion:** Define the metric explicitly in the UI ("Est. notional = last price
  × volume") and offer toggles for volume vs notional vs open interest so the
  ranking basis is never ambiguous.

### Q8. How is an event's resolution determined and recorded?
- **Question:** How do we know an event resolved yes vs no, and capture it?
- **Have:** Markets have a `status` (`unopened`, `open`, `closed`, `settled`) and
  settlement rules (https://docs.kalshi.com/api-reference/market/get-markets,
  https://docs.kalshi.com/getting_started/market_settlement). WS channels include
  `market_lifecycle_v2`.
- **Don't have:** Live settlement feeds (no network). The exact settlement payload
  fields for a resolved outcome were not fully enumerated on the pages fetched.
- **Answer:** Resolution is detectable by market/event `status=settled` plus the
  settled outcome; exact payload fields need confirmation against the live API.
- **Suggestion:** Poll `GET /events?status=settled` and `GET /markets?status=settled`,
  and subscribe to `market_lifecycle_v2` over WS; record `event_ticker`, `status`,
  `close_ts`, `settled_ts`, and outcome; confirm the settled-outcome field name from a
  live settled market before relying on it.

### Q9. How fresh is REST data, and do we need WebSocket?
- **Have:** REST responses are cached for a few seconds and can lag; WS is required
  for current state (https://docs.kalshi.com/api-reference/market/get-markets). WS
  requires authentication even for public channels
  (https://docs.kalshi.com/websockets/websocket-connection).
- **Don't have:** A WS connection (no key + no network).
- **Answer:** REST polling gives near-real-time data with seconds of lag; true live
  movement requires the authenticated WS feed.
- **Suggestion:** Use REST polling as the baseline, upgrade to WS
  (`orderbook_delta`, `ticker`, `trade`, `market_lifecycle_v2`) when a key and egress
  are available, and keep a polling fallback on WS disconnect.

## D. The dashboard & UI

### Q10. What time windows does the price chart support?
- **Question:** X-axis time range: seconds, minutes, hours.
- **Have:** Candlesticks support `period_interval` = 1 min, 60 min, 1440 min
  (https://docs.kalshi.com/api-reference/market/get-market-candlesticks). Y is
  contract price in dollars.
- **Don't have:** Sub-minute (true per-second) candlesticks from the official API.
- **Answer:** The official candlestick granularity is **1 minute minimum**. A
  "seconds" view is not available from candlesticks; it can only be approximated with
  the `trade` WS channel or recent trades, which is **unverified** here.
- **Suggestion:** Offer minutes / hours / days from candlesticks (verified). For a
  seconds view, either (a) drop it, or (b) build it from WS `trade` ticks — verify
  tick cadence first; do not imply sub-minute candles exist if they don't.

### Q11. What does "liquidity — contracts available at a given price" show?
- **Have:** Orderbook returns `yes_dollars`/`no_dollars` as
  `[price_dollars, count_fp]` pairs, best bid last; a yes bid at X = no ask at
  (100−X) (https://docs.kalshi.com/api-reference/market/get-market-orderbook).
- **Don't have:** Live orderbook (no network).
- **Answer:** Liquidity at a price = the orderbook contract count at that price
  level. This is directly available from `GET /markets/{ticker}/orderbook`.
- **Suggestion:** Render the orderbook depth as a table + cumulative depth curve;
  show both yes and no sides, and a depth toggle (top-N levels).

### Q12. How do we categorize trades and build strategies?
- **Question:** What taxonomy for trade categories/strategies?
- **Have:** Orders/trades expose market ticker, side/direction, price, count, status
  (https://docs.kalshi.com/llms.txt, order_direction, get-trades).
- **Don't have:** A prescribed strategy taxonomy; none is defined by Kalshi.
- **Answer:** The taxonomy is a **product decision**, not an official field. The
  dashboard proposes a category set (e.g., by topic, by direction, by horizon, by
  entry price vs implied probability) and lets the user review suggestions before
  implementing.
- **Suggestion:** Derive categories from verified fields (topic, side, hold time,
  entry→settlement outcome) and present strategy ideas in the Suggestions section for
  review rather than auto-applying them.

## E. Operations & deployment

### Q13. Where does the live dashboard run vs the static GitHub Pages site?
- **Have:** GitHub Pages is a static host; it cannot run a persistent authenticated
  backend or store secrets. Kalshi public market-data endpoints need no auth
  (https://docs.kalshi.com/getting_started/quick_start_market_data).
- **Don't have:** A host with kalshi.co egress and a persistent process for the
  backend.
- **Answer:** The static site can show public market data directly; authenticated
  portfolio/trade features need the backend in an environment with Kalshi access.
- **Suggestion:** Run the backend wherever kalshi.co is reachable; the static site
  detects whether it is served by the backend (relative `/api`) or standalone and
  adapts, clearly labeling authenticated vs public data.

### Q14. What happens to tracking state (events watched, trades, portfolio) if the
process restarts?
- **Have:** Nothing official — persistence is our concern.
- **Don't have:** A persistence layer decision yet.
- **Answer:** Unverified/undecided.
- **Suggestion:** Persist the tracking store (events watched, trade records,
  snapshots) to a local JSON/SQLite file and/or append-only log; reload on restart so
  the dashboard is resumable. Confirm the desired durability before finalizing.

---

## Summary of "don't have / must discover"

| # | Missing information | Suggestion to discover |
| --- | --- | --- |
| Q1 | Kalshi egress from sandbox | Run backend where kalshi.co is reachable; surface `/exchange/status` |
| Q3 | Demo API key pair | Generate from demo account; supply via env, never commit |
| Q5 | Account tier / rate limits | Read tier from account; size polling/batches; backoff on 429 |
| Q6 | Exact category→topic mapping | Discover series per topic; build reviewed whitelist |
| Q8 | Settled-outcome payload field names | Confirm from a live settled market |
| Q10 | Sub-minute (seconds) candles | Confirm WS `trade` tick cadence; else drop seconds view |
| Q12 | Strategy taxonomy | Derive from verified fields; review in Suggestions |
| Q14 | Persistence decision | Add local persistence; confirm durability needs |
