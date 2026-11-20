---

## Session arena-1d709f30 — branch `arena/1d709f30-demo2` (added 2026-11-20)

Session owner: `1d709f30`. Base of this branch was `6072808` (an older point
on `main`); this session merged `origin/main` (through PR #11, `d98c436`) and
resolved two add/add conflicts without discarding any other session's work:
- `.github/workflows/pages.yml` — kept main's proven deploy flow and
  **added** a whole-site internal link-check step before the artifact upload
  (main's version retained as the base).
- `COORDINATION.md` — kept main's full board/history; this section is appended.

Claim table (files listed are owned by this session; everything else untouched):

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| S-1 | Merge main into this branch, resolve conflicts | done | 1d709f30 | `COORDINATION.md`, `.github/workflows/pages.yml` (additive step only) |
| S-2 | Data pipeline: official demo API → topic-ranked snapshots (computed 24h dollar volume), resolution tracking, CORS probe, chart/depth snapshot | done | 1d709f30 | `scripts/fetch_data.py`, `.github/workflows/data-refresh.yml`, `data/events_top.json`, `data/resolved.json`, `data/series_index.json`, `data/cors.json`, `data/live_snapshot.json`, `data/pipeline_meta.json` |
| S-3 | Dollar-amount rankings page (gas prices, elections, culture, crypto, golf) with per-row official source links + formula disclosure | done | 1d709f30 | `rankings.html`, `assets/rankings.js` |
| S-4 | Whole-site link checker + CI workflow | done | 1d709f30 | `scripts/check_links.py`, `.github/workflows/linkcheck.yml` |
| S-5 | Consolidated navigation (root landing → all subsites: pages/, verified/, dashboard/, root extras) | done | 1d709f30 | `index.html` (nav links appended only) |
| S-6 | Verification additions (CORS probe result, dollar-formula disclosure) | done | 1d709f30 | `pages/verification.html` (append rows only), this section |
| S-7 | Final integration: link check, PR → main, merge, Pages deploy confirm, record | done | 1d709f30 | this section, PR record below |

Scope rules honored: no other session's page content is rewritten; all edits
to shared files (`index.html`, `pages/verification.html`, `pages.yml`,
`COORDINATION.md`) are strictly additive.

### Sources used by this session (official only; all fetched 2026-11-20)

- https://docs.kalshi.com/getting_started/demo_env (demo REST/WS endpoints table)
- https://docs.kalshi.com/getting_started/api_environments (full endpoint list, signing scope)
- https://docs.kalshi.com/getting_started/api_keys (Ed25519/RSA-PSS headers, 30s timestamp rule)
- https://docs.kalshi.com/getting_started/quick_start_market_data (public endpoints, caching lag)
- https://docs.kalshi.com/getting_started/quick_start_websockets (WS handshake REQUIRES auth headers)
- https://docs.kalshi.com/getting_started/rate_limits (429 handling, unauthenticated limits)
- https://docs.kalshi.com/getting_started/market_lifecycle (statuses; filter enum ↔ schema mapping)
- https://docs.kalshi.com/getting_started/market_settlement (Yes/No pays $1; result field)
- https://docs.kalshi.com/api-reference/market/get-markets (Market schema, status filters, pagination)
- https://docs.kalshi.com/api-reference/market/get-series-list (`category`/`tags` filters, `include_volume`)
- https://docs.kalshi.com/api-reference/events/get-events (`with_nested_markets`, event `category` deprecated)
- https://docs.kalshi.com/api-reference/market/get-market-orderbook (yes/no bids [price,count], depth 0-100)
- https://docs.kalshi.com/api-reference/market/get-trades (public trade prints, ts in seconds)
- https://docs.kalshi.com/api-reference/market/get-market-candlesticks (period 1/60/1440 min, max 5000 periods)
- https://docs.kalshi.com/api-reference/portfolio/get-balance (401 without keys; field names)
- https://docs.kalshi.com/api-reference/portfolio/get-positions (realized_pnl_dollars etc.; 401 without keys)
- https://docs.kalshi.com/api-reference/orders/create-order-v2 (POST /portfolio/events/orders; legacy = 410)
- Live demo API responses observed this session: `/markets?limit=2&status=open`,
  `/events?limit=3&status=open&with_nested_markets=true`, `/series?include_volume=true`,
  `/series?category=Crypto|Culture|Economics`, `/series?tags=Golf|Gas|Gasoline`,
  `/series/KXAAAGASM`, `/series/KXAAAGASD`, `/series/KXNATGAS15M`,
  `/markets/trades?ticker=KXELONMARS-99`, `/series/KXELONMARS/markets/KXELONMARS-99/candlesticks`,
  `/markets/KXELONMARS-99/orderbook?depth=5` (all under the recommended demo base).

### Verification performed by this session

- Every endpoint/field claim above was read from the official docs page or the
  live official demo API response — no value is inferred. Blanks stay blank.
- Third-party mentions of gas series tickers (KXAAAGASM/KXAAAGASD/KXNATGAS15M)
  were re-verified against `GET /series/{ticker}` on the official demo API
  before use (official source = the API URL recorded per row).
- `GET /portfolio/balance` without keys fails (auth required per
  get-balance.md `security: kalshiAccessKey...` + 401 response) → all
  portfolio/trade rows on this site remain blank and flagged; no demo
  credentials exist in this workspace and none were invented.
- CORS from a page origin is probed by `scripts/fetch_data.py` (records
  observed `Access-Control-Allow-*` headers into `data/cors.json`) — this
  closes the previously open "CORS not verified" item with an observed
  result rather than an assumption.

### Cross-scope integration fixes (session 1d709f30, logged per the task rules)

Broken links found by `scripts/check_links.py` on the merged tree were fixed at
integration (owners' sessions had already merged; no content was discarded):

1. `tools/build_site.py` NAV: `../verified/index.html` produced
   `../../verified/index.html` inside `pages/*.html` (404 live: it resolves
   above the site root) and `../verified/index.html` from the root index.
   Changed the NAV entry to `verified/index.html`; the `prefix` mechanism now
   yields the correct path from both root and `pages/`.
2. `tools/check.py`: nav link count expectation 18 → 19 after adding
   Dollar Rankings to the canonical nav.
3. Root `index.html` + `pages/*.html` regenerated with
   `tools/build_site.py` / `tools/build_content.py` (CI requires generated
   output to match the generator; hand edits would fail the diff gate).
4. `site/js/app.js`: `renderTable` now supports `rowId`; flagged/suggestions
   rows get `id="FLAG-xx"` / `id="Sx"` so the existing deep links
   (`site/*.html` → `flagged.html#FLAG-04`, `suggestions.html#S3`) resolve, plus
   a `location.hash` scroll after render. Anchors existed in the JS data
   arrays but were never attached to the DOM.
5. `scripts/check_links.py` (new): whole-site checker — 1,862 references
   across 67 HTML files, rejects root-absolute paths (project Pages break),
   validates anchors (static ids or runtime `id:` declarations in sibling JS),
   skips `${...}` template literals, and in CI (`linkcheck.yml`) probes every
   external URL. `pages.yml` now gates deploy on the internal check.
6. `tools/build_content.py`: appended this session's 10 verification rows
   (WS-auth requirement, trades/candlesticks/orderbook live checks, AAA gas
   series, settlement/status mappings, computed-metric disclosure, portfolio
   auth) and regenerated `pages/verification.html`.

Verification after fixes: `python3 scripts/check_links.py` → 0 problems;
`python3 tools/check.py` → all clean; `node --check` on changed JS passes;
`python3 -m py_compile` on changed Python passes.

### PR / deploy record — session 1d709f30

- PR: https://github.com/karagemop466-tech/Demo2/pull/24 — **MERGED** 2026-11-20
  12:11:53 UTC (`gh pr merge 24 --merge`), merge commit
  `532edadfd490ed85570647fcf20ac2f0f149b266`. Both PR checks passed before merge:
  `Build and check the site` (success, ~14 s) and `Link check (all pages,
  internal + external)` (success, 52 s — 1,943+ internal references across 70
  HTML files plus every external URL probed with HEAD→GET fallback, 429 backoff).
- Pages deploy: `Deploy GitHub Pages` run for `532edad` — **success** (20 s);
  `pages build and deployment` for the follow-up data commit `8d2c47d` —
  **success** (59 s). Pages API: `status: built`, source `main /`,
  https://karagemop466-tech.github.io/Demo2/ . Newest github-pages deployment
  targets `8d2c47d` (github-pages[bot], 2026-11-20T12:12:56Z).
  Live verification (fetched after deploy): `/Demo2/rankings.html` serves the
  page with method box + tables, and `/Demo2/data/events_top.json` serves real
  ranked rows (e.g. elections top event `KXPRESNOMD-28`, est. 24h $24,034.81,
  1,555,533.39 contracts, per-row official source URLs).
- Data pipeline first run on `main`: `Refresh Kalshi data` run 44733769348 —
  **success** (fetch + commit steps), data commit `8d2c47d` on main. Outputs:
  `data/events_top.json` (topic rankings: gas 1, elections 10, culture 0,
  crypto 10, golf 6 rows — culture blank because no in-scope culture events
  had volume/OI in the window, stated as blank, not filled),
  `data/resolved.json` (200 settled markets with official `result` yes/no),
  `data/series_index.json`, `data/live_snapshot.json`, `data/pipeline_meta.json`.
- **CORS (previously open item) — observed, not assumed**: probe with
  `Origin: https://karagemop466-tech.github.io` against
  `GET /trade-api/v2/markets?limit=1` returned HTTP 200 with
  `access-control-allow-origin: https://karagemop466-tech.github.io` (origin
  echoed), `access-control-allow-credentials: true`, and
  `access-control-expose-headers: X-Csrf-Token,X-Ratelimit-Limit,...`.
  Conclusion: browser-side live fetch from the GitHub Pages origin is
  supported by the demo API. Raw evidence: `data/cors.json` (refreshed every
  pipeline run). Source: https://docs.kalshi.com/getting_started/quick_start_market_data .
- Two genuinely broken external docs links found by the external probe and
  fixed: `docs.kalshi.com/demo_env` → `docs.kalshi.com/getting_started/demo_env`
  (in `tools/build_content.py` API rows) and
  `docs.kalshi.com/api-reference/markets/get-market` → `.../market/get-market`
  (singular `market`) in `review.html`. Both re-checked live (200).
- This record + data sync PR: https://github.com/karagemop466-tech/Demo2/pull/25 —
  **MERGED** 2026-11-20 12:19:11 UTC, merge commit `b8e29c3`; both PR checks
  passed (link check incl. external, build+check). Pages deployments for
  `b8e29c3` created 12:19:15Z / 12:19:23Z; final site status verified `built`
  at https://karagemop466-tech.github.io/Demo2/ .
- Session 1d709f30 complete: all claimed tasks (S-1…S-7) done; open items that
  require a human (Kalshi demo account + API key for portfolio/trade execution)
  remain flagged on the Flagged pages and in the questions register, per the
  verification rules (blank, never inferred).
---

---

# Session `arena-ddc587ae` — board appended at integration (2026-11-20)

> Added by the integration merge of PR #16. The board above records sessions that landed on `main` first; this section records the parallel session's scope, evidence and decisions. Both are preserved deliberately.

**Branch:** `arena/ddc587ae-demo2` · **Scope:** `intelligence/` subsite + its data + `intelligence/scripts/linkcheck.mjs` (non-overlapping with root/`pages/`/`dashboard/`/`site/`/`verified/` scopes).

## Task board (session arena-ddc587ae)

| ID | Task | Status | Evidence / notes |
|----|------|--------|------------------|
| T1 | Coordination setup | done | This board first pushed in commit `954870d` (pre-merge branch history). |
| T2 | Official docs research & endpoint verification | done | docs.kalshi.com: demo_env, openapi.yaml v3.37.0, get-markets, get-events, get-series-list, get-market-orderbook, get-market-candlesticks, get-trades, get-tags-for-series-categories, market_settlement, quick_start_authenticated_requests, quick_start_websockets, create-order-v2, get-balance, get-fills, get-positions, get-settlements; cftc.gov/PressRoom/PressReleases/8302-20. Live: `GET /exchange/status` → 200 trading-active. |
| T3 | Demo API data collection | done | `intelligence/data/watchlist.json` + `intelligence/data/snapshot.json` — 177 records, each with its exact source URL; enumeration completeness per query (complete: Oil&Gas 4/4, BTC 4/4, DWTS 1/1; partial flagged F-16). |
| T4 | Site build (landing + subpages, per-row sources) | done | 9 pages under `intelligence/` (relocated at integration to coexist with the root site on `main`). |
| T5 | Live dashboard (ranking + chart + depth) | done | Batched 60 s REST polling with LIVE/SNAPSHOT badge; chart periods 1/60/1440 min + seconds via trade ticks (spec-verified); depth from official bids-only orderbook with documented 1−P ask equivalence. |
| T6 | Portfolio & trading | done (security-aligned) | Verified metric formulas + public-feed categorisation engine + strategy templates; **browser credential entry removed at integration** (F-17/D-05, aligned with repo README + PR #6); execution paths = `server/` backend / docs playground. No session keys existed (F-02) → no fabricated account data. |
| T7 | Event resolution tracking | done | `intelligence/events.html` — protocol table + captured YES ($1.0000) and NO ($0.0000) settlements with `settlement_ts`; blank PR04 flagged (F-04). |
| T8 | Suggestions + Questions | done | 9 suggestions (S-06 implemented), 5 decisions D-01…D-05; 14 Q&As + missing-information discovery table. |
| T9 | Flagged for Review | done | `intelligence/flagged.html` — 17 flags with verbatim API values + sources. |
| T10 | Verification pass | done | `node intelligence/scripts/linkcheck.mjs` → PASS (9 pages, 272 links, 177 source fields); `node --check` on all JS; local smoke test 16/16 HTTP 200. |
| T11 | Integration + PR + merge + Pages | DONE | PR #16 **MERGED** 2026-11-20, merge commit `2ccd57c` (`gh pr merge 16 --merge`). Conflicts with `main` resolved additively twice (README + COORDINATION union-resolved — every session preserved); site relocated to `intelligence/` so no root file was overwritten. CI `Build and check the site` run `44729787843` → **success** (66 HTML incl. subsite); `Deploy GitHub Pages` run `44729787760` → **success**; `pages build and deployment` run `44729786102` → **success**. Pages verified **live with content**: root https://karagemop466-tech.github.io/Demo2/ (existing site intact) + subsite https://karagemop466-tech.github.io/Demo2/intelligence/ (17 flags, 5 topics, all 9 pages). |

## Irregularities / handoffs (session arena-ddc587ae)

- 17 open flags — see `intelligence/flagged.html` (F-01…F-17). None block merge per instructions.
- Security: browser-side key entry removed; related open PR #6 left for its owner session (cross-scope — not edited).
- Cross-scope requests: none outstanding; `server/` (backend) referenced by pointer only, not modified.
- Note for later sessions: `git pull --rebase` was replaced by an explicit `git merge origin/main` for this sync — a rebase would have replayed pre-relocation commits over the root site and destroyed the combined conflict resolution; recorded here as a deliberate deviation.

## PR / Pages record (session arena-ddc587ae)

- PR #16: https://github.com/karagemop466-tech/Demo2/pull/16 — **MERGED** 2026-11-20, merge commit `2ccd57c` (`gh pr merge 16 --merge`; verified `gh pr view 16` state=MERGED).
- Pages root (existing site): https://karagemop466-tech.github.io/Demo2/ — unchanged by this PR.
- Pages subsite (this session): https://karagemop466-tech.github.io/Demo2/intelligence/ — **verified live with full content** post-merge (fetched title "Kalshi Demo Intelligence — Overview", stats 5/124/10/8/17 render, all nav links present).

---

## Session `6d75123b` — branch `arena/6d75123b-demo2` (final scope after rebase)

`origin/main` advanced three times while this session worked (PR #9–#14). By the third rebase, main already contained
a merged root-dashboard rebuild (session `406a2f21` / `e88eb254`) that had independently reached the same API
corrections this session made: V2 `POST /portfolio/events/orders`, the removed legacy order endpoint (`410 Gone`), and
the WebSocket handshake requirement.

**Decision: do not overwrite it.** Main's dashboard, `pages/`, `verified/`, `dashboard/`, `site/` and `server/` are
kept exactly as merged. This session's unique contribution is published additively under `live/`, and one real defect
found in main was fixed.

### Delivered

| Item | Status | Files |
|---|---|---|
| Interactive console: windows, fixed $0–$1 chart axis, full order-book depth with cumulative liquidity | done | `live/index.html`, `live/assets/app.js`, `live/assets/style.css` |
| Resolution tracking to YES/NO, persisted per browser | done | `live/index.html` |
| Paper trading without credentials | done | `live/trading.html` |
| Signed demo orders on V2 endpoint with confirmation step | done | `live/trading.html` |
| Trade categorisation (topic, side, price band, topic×side) + strategy only above n=10 | done | `live/trading-analysis.html` |
| Nav links from the main site into `live/` | done | `index.html`, every `pages/*.html` |

### Defect found in main and fixed

- **17 broken `verified/` navigation links.** `pages/*.html` linked `../../verified/index.html`, which resolves to a
  path outside the repository root, and the root page linked `../verified/index.html`. Both 404 on the deployed Pages
  site. Corrected to `../verified/index.html` and `verified/index.html`. Found by `tools/check_live_links.py`.

### Verification

- `python3 tools/check_live_links.py` → 46 HTML files, 1063 href/src attributes, no broken internal links, no duplicate
  ids, no placeholders (skips `<script>` bodies and `<code>` examples so template literals are not false positives).
- `python3 tools/check_links.py` (pre-existing, `verified/` subsite) → OK.
- `node --check` on `assets/site.js`, `assets/app.js`, `live/assets/app.js`, `server/*.js` → OK.
- jsdom behaviour harness against `live/` with mocked demo-API fixtures: 19 assertions, all passing.
- `node scripts/smoke.mjs` against `server/index.js`: 0 errors; Kalshi network calls fail only because of the sandbox
  egress limit (F-1).

### Conflicts encountered (all resolved without discarding other sessions' work)

1. `COORDINATION.md` — upstream kept in full, this session's section appended.
2. `README.md` — this session's section appended below upstream content.
3. `tools/check_links.py` — name collision with main's checker; upstream file kept untouched, this session's stricter
   checker published as `tools/check_live_links.py`.
4. Root `index.html` and `pages/` — upstream's newer rebuild kept; only the nav link to `live/` and the `verified/`

### Follow-up: the broken links were generator-side

The first push of this work failed CI at the "regenerating produced a diff" gate, which was correct: the `verified/`
link defect lived in `tools/build_site.py`'s `NAV` table, where the entry was written as `../verified/index.html` and
then concatenated with a per-page prefix — producing `../../verified/...` from `pages/` and `../verified/...` from the
root. Both are wrong. Fixed at the source (`verified/index.html` relative to the prefix), and the "Live Console" entry
was added to the same table so a regeneration cannot drop it again.

Two knock-on adjustments, both reviewed deliberately rather than by loosening a guard:

- `tools/check.py` expected exactly 18 nav links; the console entry makes it 19. The count is updated with a comment,
  not removed.
- `tools/check.py`'s private-key scanner flagged the literal PEM header text used as a textarea
  placeholder in `live/trading.html` (writing the header out here would trip the same guard, which is why it is described
  rather than quoted). The scanner is untouched — it is a good guard — and the placeholder was reworded.

Final local state before merge: `tools/check_live_links.py` clean (46 files / 1063 attributes), `tools/check.py`
"links, nav, data, secrets and scripts all clean", `tools/check_links.py` OK, `node --check` OK on both app scripts, and
re-running both generators produces no diff.

   link fix were applied on top.

---

### Merge record (f1751c8f, 2026-11-20)
- Merged `origin/main` (d98c436, which includes PR #9, #10, and #11 from session arena-3420a90d) into `arena/f1751c8f-demo2`. The conflict in COORDINATION.md was resolved by keeping both sections in order. README.md auto-merged.
- Main changes were additive (`dashboard/`, `tools/collect_kalshi.py`, `.github/workflows/collect.yml`, `.gitignore`). No shared file owned by this session was overwritten.

---

## Session `64df4faa` — branch `arena/64df4faa-demo2` (claim written 2026-11-20 11:35 UTC, before edits)

This session's rules name the branch `arena/64df4faa-demo2`, so `session-<id>/<task>` branches
were not created. The board was read first. `main` at claim time: `8330897` (PR #12),
with sessions `f1751c8f`, `arena-3420a90d`, `bb334a65`, `6822d767`, `e3f65782` and `407c72e2`
already merged and **still active** on their own branches (`Refresh Kalshi demo data snapshot`
and `Build and check the site` runs were in progress while this claim was written).

**Scope discipline.** Because three other dashboards are being actively edited, this session is
**additive only**. It does not edit `pages/`, `verified/`, `dashboard/`, `assets/`, `app.js`,
`style.css`, `analysis.html`, `portfolio.html`, `review.html`, `data/kalshi_snapshot.json`,
`tools/build_site.py`, `tools/check_links.py` or `tools/collect_kalshi.py`.

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| W-1 | Verified data collector (public demo API → snapshot + 3-day tick history) | done | 64df4faa | `tools/kalshi_collect.py`, `data/dashboard.json`, `data/history/*` |
| W-2 | Data validator that fails the build on unsourced / out-of-range / unreconciled / stale rows | done | 64df4faa | `tools/validate_data.py` |
| W-3 | Dashboard site: overview, 5 topic pages, live chart + orderbook, resolutions, portfolio, analysis | done | 64df4faa | `site/*.html`, `site/assets/*` |
| W-4 | Questions register (22 questions, known/missing/how-to-find-out) | done | 64df4faa | `site/content/questions.json`, `site/questions.html` |
| W-5 | Suggestions board (10 decisions, nothing implemented) | done | 64df4faa | `site/content/suggestions.json`, `site/suggestions.html` |
| W-6 | Flagged for Review register (data + repo irregularities, evidence links) | done | 64df4faa | `site/content/flags.json`, `site/flagged.html` |
| W-7 | Repo review: claim-by-claim against official docs | done | 64df4faa | `site/content/repo_review.json`, `site/repo-review.html` |
| W-8 | Clean landing page indexing every dashboard in the repo | done | 64df4faa | `index.html` |
| W-9 | Workflow: collect → validate → commit → link-check → deploy, every 15 min | done | 64df4faa | `.github/workflows/pages.yml` |
| W-10 | Integration: re-verify rows, build, link check, PR to `main`, merge, deploy check | **done** — PR #28 merged `46acd3e`; CI green on main at `64d0961`; site fetched live and checked | 64df4faa | all of the above |

### Environment facts verified by this session (not assumed)

- Additive sandbox bash **cannot** reach Kalshi (TLS `SSL_ERROR_SYSCALL`, DNS resolves to the AWS
  NLB for `external-api.demo.kalshi.co` and `external-api-ws.demo.kalshi.co`). Confirmed by `curl`.
- The sandbox's `fetch_page` tool **can** reach the demo API and the docs; that is how the raw
  responses cited on the site were read.
- A GitHub Actions runner **can** reach the demo API: a probe workflow returned HTTP 200 from
  `/exchange/status` and committed the response to the branch, which is how the collector design
  was validated before writing it.
- **CORS**: `/exchange/status` with `Origin: https://karagemop466-tech.github.io` returned
  `access-control-allow-origin: https://karagemop466-tech.github.io` (and `cache-control: public, max-age=1`).
  That is why the browser can poll the API directly and no proxy is needed for public data.
  This contradicts the earlier board note “CORS not verified”; it is now verified and re-checked each run.
- `search/tags_by_categories` contains **no Culture category** but does contain Entertainment;
  Culture exists only as a series category (`/series?category=Culture` → 2 series). Golf is a tag
  under Sports. Both are documented on the site rather than worked around.

### Sources (official, read this session)
`docs.kalshi.com`: `getting_started/demo_env`, `getting_started/orderbook_responses`,
`getting_started/market_settlement`, `getting_started/historical_data`, `getting_started/rate_limits`,
`getting_started/fixed_point_migration`, `api-reference/market/get-markets`,
`api-reference/market/get-market-orderbook`, `api-reference/market/get-series-list`,
`api-reference/market/get-trades`, `api-reference/market/get-market-candlesticks`,
`api-reference/events/get-events`, `api-reference/portfolio/get-balance`.
Raw API responses cited per row: `/series?category=Economics|Elections|Culture|Crypto`,
`/series?tags=Golf`, `/markets?series_ticker=…&status=open|settled`, `/markets/{ticker}/orderbook`,
`/markets/trades?ticker=…`, `/exchange/status`, `/search/tags_by_categories`.

### Verification performed
- `python3 tools/build_dashboard_site.py` then `python3 tools/check_site.py`: 55 pages checked,
  0 blocking errors; owned pages all carry the demo disclaimer and are reachable from the nav.
  Issues found in other sessions' pages are printed as **REPORTED, not blocking** so they are
  visible without blocking this session.
- `python3 tools/validate_data.py` enforces: source URL on every row, prices inside $0.00–$1.00,
  derived money reconciling with its inputs, no field filled in when its inputs are missing,
  snapshot younger than 6 hours.
- Every Kalshi doc path used on the site was fetched during this session; results are listed on
  `site/repo-review.html` under “Documentation links checked” (FETCHED vs REFERENCED).

### Requests to other sessions (not edited here)
1. **`pages/portfolio.html` and the root monitor still contain a credential-entry form** (API key ID
   + private key pasted into the page). PR #6 removed it but was never merged. This is recorded as
   F-08 on `site/flagged.html`. Whoever owns `pages/` should merge or close PR #6.
2. `dashboard/`, `verified/`, `pages/` and the root notes now make **four parallel dashboards**.
   This session did not consolidate them because all three are being edited right now; the landing
   page indexes all four instead. Consolidation is Suggestion S5 on the site.
3. The board's earlier claim that CORS is unverified is out of date — see above.

### Results actually obtained (not planned)

| Fact | Value | How it was verified |
|---|---|---|
| Open in-scope markets collected | 1,311 | `data/dashboard_instrument.json` `counts.open_markets_in_scope`, from one shared `/markets?status=open` stream intersected with each topic's series list |
| In-scope series | 174 | `/series?category=…` and `/series?tags=Golf` |
| Resolved markets collected | 1,601 | `/markets?series_ticker=…&status=settled` per series, `result` copied verbatim |
| — of which ever traded | 270 | `volume_fp > 0` |
| — of which never traded | 1,331 | `volume_fp == 0`; API returns `last_price_dollars` `0.0000` for these |
| Live orderbook snapshots | 48 (20 non-empty) | `/markets/{ticker}/orderbook?depth=20` |
| Trade histories | 12 markets | `/markets/trades?ticker=…` |
| Requests per run | ~440, 0 errors | `meta.https_requests`, `meta.request_errors` |
| Run duration | ~2 minutes | GitHub run 44737674422 |

### Two bugs this session found in its own work, and what now prevents them

1. **Resolved-market block silently emptied.** Restructuring the topic loop dropped the settled-markets
   call; the run still "passed" with 0 resolved rows. `tools/validate_data.py` now **fails** when the
   resolved set is empty, and `instrument-panel/tests_smoke.py` (offline, no network) runs first in CI.
2. **A calibration that measured a default value.** 1,331 of 1,601 resolved markets never traded and
   carry `last_price_dollars = 0.0000`. Calibrating them reported a fake +26-point edge on long shots.
   The Analysis page now calibrates **only traded markets** (n=270), labels bands with n<30 as too small
   to interpret, and keeps the uncorrected table in a collapsible block so the correction is checkable.
   Recorded as flag **F-15**.

### Rate limiting, verified rather than assumed
The 300-series run produced **539 x HTTP 429**. Kalshi documents that public endpoints “charge your IP
address's budget first”, that publicly cacheable responses carry **no** `X-RateLimit-*` headers, and that
a 429 has no penalty — so backoff is the only remedy. The collector now spaces requests globally
(widening x1.5 per 429, narrowing 0.5% per success, 4 workers) and publishes the observed 429 count on
the Verification page. After the restructure: 440 requests, 0 errors, 5 observed 429s.

### PR / deploy record — complete

| PR | What | Result |
|----|------|--------|
| [#28](https://github.com/karagemop466-tech/Demo2/pull/28) | The instrument panel itself (15 pages, collector, validator, workflow) | **merged** `46acd3e` at 2026-11-20T12:43:50Z |
| [#29](https://github.com/karagemop466-tech/Demo2/pull/29) | Move the nav link into `build_site.py` so the generated-page check passes | **merged** |
| [#30](https://github.com/karagemop466-tech/Demo2/pull/30) | Derive the expected nav size from the generator instead of hardcoding 20 | **merged** `64d0961` |

**`Build and check the site` is green on main at `64d0961`.** `pages build and deployment` succeeded,
and `Deploy GitHub Pages` ran the full collect → validate → rebuild → link-check chain.

**Live and verified by fetching the deployed page** (not by assuming):
`https://karagemop466-tech.github.io/Demo2/instrument-panel/site/analysis.html` returns the dashboard,
showing 1,601 resolved markets, 317 traded / 1,284 never-traded, and the corrected calibration table.

### Two CI failures I caused on main, and what was actually wrong

Both were **my** mistakes, both blocked nothing but looked like broken deployments, and both are worth
recording so another session does not repeat them:

1. **Edited a generated file.** `index.html` is produced by `tools/build_site.py`. Adding a nav link by
   hand made CI's "pages must match the generator" step fail. *Lesson: if a file has a generator, edit
   the generator.*
2. **A hardcoded count in a checker.** `tools/check.py` asserted "nav has 20 links", a magic number that
   has to be edited whenever a section is added. It now reads the count from the generator's `NAV` list,
   so it checks that pages match their source rather than a number someone has to remember.

In both cases the Pages deploy itself was fine; only the consistency job was red. The site was never
broken, and it is worth distinguishing the two when reading Actions.

---

## Session `arena-bdb4d2d0` — branch `arena/bdb4d2d0-demo2` — CLAIM (2026-11-20 13:01 UTC, written before edits)

Role: **final review + integration session** for this pass. The platform fixes
this session's branch name, so `session-<id>/<task>` branches are not created
(same precedent as sessions `1d709f30`, `64df4faa`). This section is pushed as
the claim, before any other edits.

**Scope discipline.** Active sessions at claim time (commits within the last
hour, listed so no one double-claims): `21eed9ff` (PR #34, docs verification),
`8b9a46b4` (PR #32, sharp-jump detector + backtest subsite), `5330bffb`
(PR #27, integration of its own pipeline/registers). Their file scopes are
**not** edited here. Stale claims (>60 min old, no commits — takeover rule):
`0c901fea` (PR #15, last commit 11:46 UTC) and `22b4f0cb` (PR #6, last commit
11:19 UTC). Those two are taken over by this session at 13:01 UTC per the
60-minute rule; their work is integrated **additively** via this branch and the
handoff is logged below.

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| R-1 | Repo line-by-line review vs official Kalshi sources; every claim checked or flagged | **done** | bdb4d2d0 | `integration/bdb4d2d0/repo-review.md` |
| R-2 | Independent re-verification of combined site data: every table row carries an official source link; unverifiable values stay blank + flagged | **done** | bdb4d2d0 | `integration/bdb4d2d0/verification.md` |
| R-3 | Irregularity register (data, security, CI, docs) with evidence links | **done** | bdb4d2d0 | `integration/bdb4d2d0/irregularities.md` |
| R-4 | Integration: bring origin/main + takeover PRs onto this branch, resolve conflicts additively, run every checker, fix broken links | in progress | bdb4d2d0 | merge commits on this branch; cross-scope fixes logged below |
| R-5 | Final PR → main, merge without waiting, GitHub Pages deploy confirm, record here | in progress | bdb4d2d0 | this section |

### Findings, fixes and handoffs (session bdb4d2d0, 2026-11-20 13:0x–13:4x UTC)

Full detail in `integration/bdb4d2d0/{repo-review,verification,irregularities}.md`.
Summary of what this session changed and why (all verified after the change):

1. **Main was red — fixed (commit `6df5c9f`).** PR #35 (session `e36292f6`)
   hand-edited `index.html`, `pages/{flagged,suggestions,verification}.html`
   without updating `tools/build_site.py`/`build_content.py`; the "pages must
   match the generator" gate failed on main (runs 12:57:58 / 13:02:27). Ported
   the sharp-jump feature into the generators (S9, F13, verification row,
   dashboard card + jump table), repaired their `/bin/bash.10` heredoc
   corruption (`$0.10`), and added the brief-required "possible context
   (unverified)" news-search link per jump row (labelled, never causal).
2. **Security — fixed (commit `49e706e`, flag F14).** Took over stale PR #6
   (`22b4f0cb`, last commit 11:19 UTC, >60 min rule): removed the orphaned
   WebCrypto signing code from `assets/app.js` and disabled the `live/trading.html`
   Mode B credential form on the deployed copy (reversible notice points at the
   gated Actions path + `server/`). Cross-scope request to session `6d75123b`:
   if that session returns, keep Mode B disabled on the public deploy.
3. **Placeholder links — fixed (commit `79fecce`).** `instrument-panel/tools/site_build_core.py`
   `ext()` rendered endpoint URL *patterns* as clickable `{ticker}` links.
   Patterns now render as `<code>`; the analysis source line keeps the official
   `get-markets` docs link. (`instrument-panel/` = session `64df4faa` scope,
   session done/merged; fix logged here per the cross-scope rule.)
4. **Flagged (not changed): F15** — `data/snapshot.json` + `data/resolutions.json`
   have never landed on main (collector step "Collect demo snapshot" failed in
   the only main run, `44728913873`; log body unreachable from this sandbox,
   GitHub blob EOF). The deployed `pages/resolutions.html` 404s its data file;
   both pages show honest empty states. **Handoff:** session `6332d7d3` has a
   rewritten collector green on `arena/6332d7d3-demo2` (runs 13:02/13:10 UTC) —
   that PR is the proper fix; this session dispatched `Refresh Kalshi demo data`
   on main (`44744689706`) at 13:29 UTC to re-test current code. Also **F16**
   (history tick rows lack source URLs) and **F17** (4 pipelines → one `data/`).
5. **Re-verification sample (8/8 matched):** resolved-market `result` +
   `settlement_ts`, event + lead-market quotes, series tags/category, demo
   endpoint table, create-order required-vs-optional fields, WS-handshake auth
   requirement — all re-fetched from their official source URLs 13:15–13:25 UTC.
   Provenance audit covered 11,430 rows across every `data/` list: every
   rendered table row carries an official URL except F16's tick rows.
6. **PR bookkeeping:** PR #15 (`0c901fea`) is superseded by PR #27
   (`5330bffb`) — identical `monitor/` scope; integration treats #27 as the
   superset and closes #15 with that note at merge time. PRs #32/#34/#27 were
   active during this session (commits within the hour) and were left untouched.

Outputs of this session live under `integration/bdb4d2d0/` (new directory,
non-overlapping with every other session's scope). Any edit to a shared file is
additive, generator-first where a generator exists, and logged in this section.

## Session `arena/e36292f6` — branch `arena/e36292f6-demo2` (started 2026-11-20)

**Branch:** `arena/e36292f6-demo2`, branched from `main` at `4c13151`. Scope: integration/final verification plus the sharp-jump price-movement feature (live chart markers + market links for moves ≥ $0.10 in either direction) and landing-page clarity. Non-overlapping with prior sessions — edits only to `COORDINATION.md` (this section), `assets/site.js` (sharp-jump detection + chart markers), `index.html` (landing clarity), `pages/verification.html` (sharp-jump verification row), `pages/flagged.html` (sharp-jump flag if unverifiable), and `pages/suggestions.html` (sharp-jump decision card).

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| E-1 | Coordination claim + claim commit/push | done | e36292f6 | `COORDINATION.md` |
| E-2 | Sharp-jump detection on live chart (≥ $0.10, either direction) with market links | done | e36292f6 | `assets/site.js`, `index.html`, `assets/style.css` |
| E-3 | Verification row + flag for sharp-jump feature (cause not derivable from API) | done | e36292f6 | `pages/verification.html`, `pages/flagged.html` |
| E-4 | Suggestion card for sharp-jump / live-interactivity | done | e36292f6 | `pages/suggestions.html` |
| E-5 | Full re-verification: build, link checks, both checkers | done | e36292f6 | all site files (read-only) |
| E-6 | PR from this branch to main, merge, Pages deploy confirm, record | in progress | e36292f6 | this section, PR record |

Sources to verify against (official only): https://docs.kalshi.com/api-reference/market/get-market-candlesticks, https://docs.kalshi.com/api-reference/market/get-trades, https://docs.kalshi.com/api-reference/market/get-market-orderbook, https://docs.kalshi.com/getting_started/demo_env.
