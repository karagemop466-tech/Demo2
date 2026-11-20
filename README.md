# Kalshi Demo Dashboard

Live GitHub Pages dashboard for Kalshi **demo** markets in five topics only:
gas prices, elections, culture, crypto, golf.

- **Landing / Dashboard:** `index.html` — live markets ranked by notional, price chart (time vs contract price), orderbook liquidity, resolved (yes/no) tracking.
- **Subpages:** `pages/` — Executive Summary, Gas, Elections, Culture, Crypto, Golf, Portfolio & Trading, Analysis, Suggestions, Questions, Verification, Flagged for Review, Sources.
- **Demo API:** `https://external-api.demo.kalshi.co/trade-api/v2` (REST) and `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` (WS). See `pages/sources.html`.
- **Trading:** paste your own demo API Key ID + private key on the Portfolio page. Keys stay in your browser and are signed in-browser (RSA-PSS/SHA-256 or Ed25519). Never commit keys.

## Run locally
Open `index.html` in a browser (live fetch happens client-side). Or serve: `python3 -m http.server 8000`.

## Deploy
GitHub Pages via `.github/workflows/pages.yml` (deploy from `main`).
