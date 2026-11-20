# Coordination board

Last updated: 2026-11-20 (UTC)

This repository was inspected before implementation. At the start it contained only the seven-byte `README.md`; `COORDINATION.md` did not exist and no other task claims were visible. The session claim was committed and pushed as `ce34afe` to the Arena-assigned branch `arena/0c901fea-demo2` before implementation. That branch is based on `607280879329e182b9aba7f7a52a099105d28a04` (`main`). Do not switch branches. The session identifier available in task context is `0c901fea`; no separate session ID or other active agent is visible.

## Task board

| Task | Status | Owner | File scope |
|---|---|---|---|
| Document verified API facts, methodology, requirements, decision questions, and review flags | in progress | `0c901fea` (`arena/0c901fea-demo2`) | `COORDINATION.md`, `README.md`, `executive-summary.html`, `requirements.html`, `methodology.html`, `review.html`, `sources.html` |
| Build the public, read-only dashboard and requested topic pages; display price history, orderbook depth, and browser-local resolution tracking | in progress | `0c901fea` (`arena/0c901fea-demo2`) | `index.html`, `categories/**`, `assets/**`, `watchlist.html`, `portfolio.html`, `suggestions.html`, `404.html`, `tests/**` |
| Integrate build/check tooling and GitHub Pages workflow; verify, publish, and record final results | in progress (integration reserved to this owner) | `0c901fea` (`arena/0c901fea-demo2`) | `package.json`, `.gitignore`, `.nojekyll`, `.github/workflows/**`, `scripts/**`, plus final integration in the pages above |

No tasks were previously claimed by another session. No concurrent session or coordination channel is visible from this checkout. Do not edit files outside these scopes for unrelated work; if another owner appears, record a file-scope request here rather than editing their files.

## Official sources reviewed

Documentation was fetched from official Kalshi or GitHub pages on 2026-11-20. These sources substantiate implementation choices; they do not constitute a runtime test of the demo API.

- [Kalshi demo environment](https://docs.kalshi.com/getting_started/demo_env) and [API environments](https://docs.kalshi.com/getting_started/api_environments): demo uses mock funds and may differ from production; demo/prod credentials are separate; recommended demo REST base is `https://external-api.demo.kalshi.co/trade-api/v2`.
- [Get Events](https://docs.kalshi.com/api-reference/events/get-events) and [Get Event](https://docs.kalshi.com/api-reference/events/get-event): event metadata, nested markets, open/status filters, cursor pagination, and a documented `limit=200` request shape.
- [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets) and [Get Market](https://docs.kalshi.com/api-reference/market/get-market): status/result/price and volume fields, including fixed-point contract counts.
- [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook) and [Get Multiple Market Orderbooks](https://docs.kalshi.com/api-reference/market/get-multiple-market-orderbooks): binary book is aggregated YES/NO bids, the individual endpoint supports a `depth` query, the batch endpoint accepts 1–100 tickers, and quantities are contract counts. There is no official ask ladder or order-count field in these responses; opposite-side asks are labeled as parity-derived.
- [Get Market Candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks): valid intervals are 1, 60, and 1,440 minutes; the seconds view must use local browser observations rather than claim official second candles.
- [Market lifecycle](https://docs.kalshi.com/getting_started/market_lifecycle), [Historical data](https://docs.kalshi.com/getting_started/historical_data), and [Get Historical Market](https://docs.kalshi.com/api-reference/historical/get-historical-market): determined, disputed, and finalized are distinct; live and historical records have separate cutoffs.
- [Get Balance](https://docs.kalshi.com/api-reference/portfolio/get-balance), [Get Positions](https://docs.kalshi.com/api-reference/portfolio/get-positions), [Get Fills](https://docs.kalshi.com/api-reference/portfolio/get-fills), and [Get Settlements](https://docs.kalshi.com/api-reference/portfolio/get-settlements): account analytics require authenticated account data; fills/settlements and historical handoffs are distinct sources.
- [API keys](https://docs.kalshi.com/getting_started/api_keys), [authenticated requests](https://docs.kalshi.com/getting_started/quick_start_authenticated_requests), [Create Order V2](https://docs.kalshi.com/api-reference/orders/create-order-v2), and [WebSocket quick start](https://docs.kalshi.com/getting_started/quick_start_websockets): requests/orders require signed credentials, private keys must not be embedded in a static site, and even public WebSocket channels use an authenticated handshake.
- [Rate limits](https://docs.kalshi.com/getting_started/rate_limits): endpoint cost/rate limits and historical/request limits inform conservative polling.
- [GitHub Pages custom workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) and [publishing-source configuration](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site): artifact deployment uses Pages permissions and repository publishing-source settings. The custom-workflow page fetch was unsuccessful; its official search result and the successfully fetched publishing-source guide were used, and the result must still be verified in Actions.

## Verification log

| Date | Task | Verification performed | Outcome / irregularities |
|---|---|---|---|
| 2026-11-20 | Initial repository review and claim | Inspected Git status, branch/base, remote, tracked files, and starter README; created and pushed the coordination claim before implementation. | Claim commit `ce34afe` is on `arena/0c901fea-demo2`; no prior task claim was present. |
| 2026-11-20 | Source/API review | Fetched the official pages linked above, including the exact event, orderbook, candle, lifecycle, historical-market, portfolio, authentication, and rate-limit references. | Code uses documented response field shapes and labels derived quantities. No live demo API call or browser CORS check has been made. |
| 2026-11-20 | Implementation review | Reviewed topic matching, displayed-depth ranking formula, chart intervals, orderbook levels, watchlist lifecycle labels, and portfolio/trading boundaries against source docs and code. | “Highest dollar amount” is still ambiguous; current explicitly labeled proxy is summed displayed YES+NO bid-side notional. Topic matching is a local keyword rule set, not an official taxonomy. Portfolio and order submission are not connected or enabled. |
| 2026-11-20 | Code checks | `node --check` passed for the application and build/check scripts. `npm test` passed (8 tests). `npm run check` passed for 15 HTML pages; local references, in-page fragments, source links on static table rows, duplicate IDs, and inline handlers are checked. | Dynamic API/CORS behavior remains unverified; no sample prices or portfolio numbers are bundled. |
| 2026-11-20 | Static build | `npm run build` generated 15 HTML pages in ignored `dist/`; `node scripts/check-site.mjs dist` passed. | GitHub Actions has not run yet. Build artifact is not intended to be committed. |
| 2026-11-20 | GitHub Pages preflight | `gh api repos/karagemop466-tech/Demo2/pages` returned the existing public URL `https://karagemop466-tech.github.io/Demo2/`, with status `built`, `build_type=legacy`, and source `main:/`. | The workflow needs GitHub Actions as the publishing source. Change the Pages source before merge/deploy; do not claim deployment until the workflow run succeeds and the resulting page is checked. |

## Publishing and handoff log

Pending. Create the pull request from `arena/0c901fea-demo2` to `main`, wait for required verification to pass, configure Pages to publish from the custom GitHub Actions workflow, merge without waiting for user review, then verify the Actions deployment and published URL. Record the PR number/URL, merge result, workflow result, and remaining flagged runtime/API limitations here. Do not claim live market values, portfolio connection, trading, or successful publication before each is actually verified.
