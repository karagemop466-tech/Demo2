# Irregularities register (session `arena-bdb4d2d0`, 2026-11-20)

Every item below is evidence-backed; nothing is inferred. None of these block
publication per the brief. Published-state mirrors: `pages/flagged.html`
(F1–F14, canonical root register) and each subsite's own register.

| # | Irregularity | Evidence | Status / action taken |
|---|---|---|---|
| I-1 | **Main's CI gate was red** — PR #35 hand-edited generated pages; content also contained `/bin/bash.10` for `$0.10` (heredoc `$0` expansion) | `gh run view 44740812355` (failed step "Fail if regenerating produced a diff"); reproduced locally | **Fixed** commit `6df5c9f` — content ported into `tools/build_site.py`/`build_content.py`, corruption repaired, generators regenerated |
| I-2 | **`data/snapshot.json` + `data/resolutions.json` missing on main** → root dashboard and resolutions page show load-error states live | https://karagemop466-tech.github.io/Demo2/pages/resolutions.html ("HTTP 404"); `/data/resolutions.json` 404; only main run of `refresh-data.yml` (`44728913873`) failed at "Collect demo snapshot" | **Flagged F15 + handed off**: session `6332d7d3` has a rewritten collector green on its branch (runs 13:02/13:10 UTC). This session dispatched `Refresh Kalshi demo data` on main (`44744689706`) to re-test current code. Site shows honest empty states ("No values are invented") |
| I-3 | **Browser-side private-key entry on a public static host** (`live/trading.html` Mode B) + orphaned WebCrypto signing code in `assets/app.js` instructing users to paste keys | `assets/app.js` (pre-fix) line 111; `live/trading.html` textarea `apiPrivateKey`; PR #6 (stale) | **Fixed** commit `49e706e` (takeover of stale PR #6 per the 60-minute rule) — form disabled with reversible notice; signing code removed; **flag F14** published. Cross-scope request logged for session `6d75123b` |
| I-4 | **Instrument-panel URL patterns rendered as clickable `{ticker}`/`{category}` links** (404 targets, unfinished placeholders) | `tools/check_live_links.py` 2 problems; generator `ext()` in `instrument-panel/tools/site_build_core.py` | **Fixed** commit `79fecce` — patterns render as `<code>`; source line keeps official `get-markets` link |
| I-5 | **`data/history_instrument/*.json` tick rows have no source URL** | rows = `{t, lp, yb, ya, oi, v}`, file header = `{date, samples}` | **Flagged F16** — suggested fix (file-level `source` field in `kalshi_collect.py`) logged for the owner; not edited here because `pages.yml` rewrites the file every 15 min |
| I-6 | **Four data pipelines commit into one `data/`** (`refresh-data.yml` 10 min, `pages.yml` 15 min, `data-refresh.yml` 2 h, `collect.yml` 2 h); two workflows share near-identical names | `.github/workflows/*.yml` | **Flagged F17** — consolidation proposed on the suggestions register; no workflow edited (owners active) |
| I-7 | **`data/resolved.json`'s 200-row window is all `result=no`** while the larger set is 1,423 no / 178 yes | file audit (verification.md §2 row 1 area) | **Noted** — verbatim per row; window sampling bias documented in the file's own `note`; no values changed |
| I-8 | **Multiple parallel dashboards** (root `pages/`, `dashboard/`, `verified/`, `site/`, `live/`, `intelligence/`, `instrument-panel/`, root extras) with duplicated registers | repo tree | **Noted** — consolidation is Suggestion S5 on `site/` and a decision for the owner; this session did not delete anyone's work |
| I-9 | **Failed-run log bodies unreachable from this sandbox** (GitHub blob storage EOF) | `gh run view --log` / jobs API → EOF for runs `44740812355`, `44728913873` | **Noted** — failure *steps* are known and recorded; message text left blank on purpose |
| I-10 | **`docs/` summaries vs site registers diverge in structure** (3 executive summaries, 3+ suggestion registers) | `docs/EXECUTIVE_SUMMARY.md`, `monitor/executive-summary.html`, `intelligence/` overview | **Noted** — active session `21eed9ff` (PR #34) is verifying `docs/`; not touched here to avoid scope collision |
| I-11 | **PR #15 (`0c901fea`) superseded by PR #27 (`5330bffb`)** — same `monitor/` subsite + `scripts/build-site.mjs` + `package.json` | `gh pr view 15/27 --json files` | **Handoff** — integration handles at merge time (see COORDINATION.md R-4/R-5 record) |
| I-12 | **Open-PR pile-up at session start** (5 open: #6, #15, #27, #32, #34) with overlapping `COORDINATION.md` appends | `gh pr list` 13:00 UTC | **Managed** — claims pushed first; conflicts union-resolved keeping every session's section |

Legend: **Fixed** = changed in this session's PR with verification; **Flagged** =
published on the Flagged-for-Review register with source links and left open for
the owner; **Noted** = recorded for review, no behaviour change; **Handoff** =
resolved at integration per COORDINATION.md.
