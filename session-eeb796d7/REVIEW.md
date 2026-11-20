# Session eeb796d7 — review record (2026-11-20)

Deliverable page: [index.html](index.html) · machine record: [data/verification.json](data/verification.json)

## What was done (E-1…E-5)

- **E-1 line-by-line verification** — 16 claims checked against live official demo-API
  responses and official docs pages (13 verified, 2 blank+flagged, 1 defect record). Raw
  verbatim bodies in `data/raw/`. Settled/static fields matched exactly (V4, V5);
  live-field drift recorded as expected behaviour (V6).
- **E-2 irregularities register** — R-1…R-7 on the deliverable page (broken data feed,
  gas classifier gap, sharp-jump feature regression, `$0` shell artifact, tree/tool/workflow
  duplication, committed `.pyc`, URL-pattern placeholders).
- **E-3 stale-PR takeover** — not needed: PR #6 closed as superseded and PR #15 merged via
  PR #27 by session d0bea7de before takeover conditions had to be applied. Recorded on the board.
- **E-4 final integration** — performed at end of session (see COORDINATION.md record).
- **E-5 collector fix (found during E-1)** — `tools/collector.py` crashed on the first
  in-scope market row (`NameError: name 'series' is not defined`), which is why
  `data/snapshot.json` never existed and the deployed root dashboard showed
  "0 in-scope markets". Also fixed: gas topic classification via the verified
  `product_metadata.scope=Gasoline` rule (tag "Oil & Gas" deliberately excluded — it
  covers crude/natgas too), and market/event links now point at the exact official API
  endpoint (the market ticker, not the series ticker; the human web-UI URL pattern could
  not be verified so it is not invented).
  Regression suite `tools/test_collector_fix.py`: 11/11 PASS on verbatim fixtures; the
  pre-fix code reproduces the exact CI crash signature.

## Reproduce

```
python3 session-eeb796d7/tools/test_collector_fix.py   # offline, no network needed
```
