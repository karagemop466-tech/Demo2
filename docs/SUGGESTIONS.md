# Suggestions — Improving Decision-Making

> Suggestions to improve the Kalshi demo dashboard's decision-making, plus suggestions
> to **discover missing information** before any change is implemented. Each item is
> labeled so a reviewer can choose the best path. Nothing is auto-applied.

Priority: **High** (core decision quality), **Medium** (usability), **Discovery**
(gathers missing information), **Low** (polish).

---

## S1. Make the ranking metric explicit and switchable
**Priority:** High
**Problem:** "Highest dollar amount" is ambiguous — Kalshi exposes `volume_fp`
(contracts) and dollar prices, but no single "dollar amount" field.
**Suggestion:** Compute **notional = price × volume**, label it clearly, and add a
toggle to rank by volume, notional, or open interest. Never present a computed
number as an official field.
**Source:** https://docs.kalshi.com/api-reference/market/get-market-candlesticks ,
https://docs.kalshi.com/api-reference/market/get-markets
**Discovery needed:** Confirm which metric best matches "dollar amount" for the
user's intent.

## S2. Separate "verified" vs "live/estimated" values visually
**Priority:** High
**Problem:** Cached REST data lags; some values are computed, not official.
**Suggestion:** Add a per-row badge: `verified` (from an official field) vs
`computed` (derived) vs `stale` (REST cache). Show a "data freshness" indicator and
the timestamp of the last successful fetch.
**Source:** https://docs.kalshi.com/api-reference/market/get-markets (cache lag note)
**Discovery needed:** Confirm acceptable staleness thresholds with the user.

## S3. Add a reviewed category whitelist for the five topics
**Priority:** High
**Problem:** The exact event/series mapping to gas, elections, culture, crypto,
golf is unverified.
**Suggestion:** Discover candidate series per topic, store them as reviewable data
(a table the user can edit), and filter strictly by that whitelist. Flag any event
that matches a topic only by fuzzy title matching.
**Source:** https://docs.kalshi.com/api-reference/market/get-series ,
https://docs.kalshi.com/api-reference/events/get-events
**Discovery needed:** Q6 — confirm the category→topic mapping.

## S4. Add settlement outcome capture with explicit confirmation
**Priority:** High
**Problem:** We record how each event resolved (yes/no), but the settled-outcome
field name is unverified.
**Suggestion:** Record `event_ticker`, `status`, `close_ts`, `settled_ts`, and
outcome; mark the outcome cell **unverified** until confirmed against a live settled
market. Add a "confirm resolution" action.
**Source:** https://docs.kalshi.com/api-reference/market/get-markets ,
https://docs.kalshi.com/getting_started/market_settlement
**Discovery needed:** Q8 — confirm the settled-outcome payload.

## S5. Build the price chart from verified granularity
**Priority:** High
**Problem:** The user asked for seconds/minutes/hours. Candlesticks only offer
1-minute, 60-minute, 1440-minute.
**Suggestion:** Ship minutes / hours / days from candlesticks (verified). Provide a
seconds view **only** if the WS `trade` tick cadence is confirmed; otherwise label
seconds as unsupported and offer "recent trades" as a proxy.
**Source:** https://docs.kalshi.com/api-reference/market/get-market-candlesticks
**Discovery needed:** Q10 — confirm sub-minute data availability.

## S6. Liquidity: add cumulative depth and spread
**Priority:** Medium
**Problem:** "Contracts available at a given price" is per-level; decision-making
also benefits from depth and spread.
**Suggestion:** Show per-level counts (yes/no), cumulative depth, and the
best-bid/best-ask spread. Use the binary equivalence (yes bid X = no ask 100−X)
correctly.
**Source:** https://docs.kalshi.com/api-reference/market/get-market-orderbook
**Discovery needed:** None — directly derivable from the verified orderbook shape.

## S7. Portfolio: add P&L by category and by strategy
**Priority:** Medium
**Problem:** Tracking performance is required; categorization is a product decision.
**Suggestion:** Compute realized/unrealized P&L per trade, then aggregate by topic,
direction, and horizon. Present strategy candidates in Suggestions for review before
any strategy is applied automatically.
**Source:** https://docs.kalshi.com/llms.txt (portfolio/orders endpoints)
**Discovery needed:** Q12 — agree on the strategy taxonomy.

## S8. Add a decision-log / review workflow
**Priority:** Medium
**Problem:** The user wants a section to review suggestions and choose the best path
before implementing.
**Suggestion:** Give each suggestion a status (proposed → reviewing → accepted →
implemented) and a decision note. Persist decisions so the site reflects chosen
direction.
**Source:** Project requirement (no external source).
**Discovery needed:** Confirm who reviews and the approval criteria.

## S9. Add alerting on thresholds
**Priority:** Medium
**Problem:** Live tracking benefits from proactive signals.
**Suggestion:** Allow threshold alerts on price movement, liquidity depth, and
volume; surface them in a feed. Use WS `ticker`/`trade` when available, REST polling
fallback otherwise.
**Source:** https://docs.kalshi.com/websockets/websocket-connection
**Discovery needed:** Q1/Q9 — requires egress + optional key.

## S10. Robust error handling and connectivity status
**Priority:** High
**Problem:** Live data can be unavailable (as in this sandbox).
**Suggestion:** Always show a connection status, the last error, and retry with
exponential backoff. Never leave a table blank without a status indicator — mark
unavailable rows as `unverified/unavailable` with a reason.
**Source:** https://docs.kalshi.com/getting_started/rate_limits (429 backoff)
**Discovery needed:** None.

## S11. Persist the tracking store
**Priority:** Medium
**Problem:** Restarting loses watched events/trades/snapshots.
**Suggestion:** Persist tracking state to a local store and reload on startup.
**Discovery needed:** Q14 — confirm durability requirements.

## S12. Accessibility & responsiveness
**Priority:** Low
**Problem:** "Clean, user friendly, simple."
**Suggestion:** Ensure keyboard navigation, readable contrast, responsive tables, and
per-row source links. Keep tables as the primary read format per requirements.
**Source:** Project requirement.

---

## Suggestions to discover missing information (consolidated)

These map to the gaps in [QUESTIONS_AND_ANSWERS.md](./QUESTIONS_AND_ANSWERS.md) and
should be resolved before implementing the corresponding feature:

1. **Kalshi egress** (Q1): run the backend where `*.kalshi.co` is reachable; verify
   with `GET /exchange/status`.
2. **Demo API key** (Q3): generate a key pair; confirm with `GET /portfolio/balance`.
3. **Tier & rate limits** (Q5): read the tier; size polling/batches; backoff on 429.
4. **Category→topic mapping** (Q6): discover series; build a reviewed whitelist.
5. **Settled-outcome fields** (Q8): confirm from a live settled market.
6. **Sub-minute data** (Q10): confirm WS `trade` cadence; else drop the seconds view.
7. **Strategy taxonomy** (Q12): agree categories; review in Suggestions.
8. **Persistence needs** (Q14): confirm durability; add a store.

> No suggestion is implemented without review. The Suggestions page on the site
> mirrors this list with status controls so a reviewer can choose the best path.
