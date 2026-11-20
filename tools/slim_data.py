#!/usr/bin/env python3
"""One-shot adapter: apply the K-1 publish caps to already-committed data files.

The collector (tools/collector.py) now bounds what it writes. The data files that
were committed BEFORE the fix (snapshot.json 46 MB, series_index.json 26 MB,
topic-elections.json 22 MB) still carry the old unbounded shapes. This script
brings them to the same shape the collector now produces, using the collector's
own helpers so the rules cannot drift:

  * rows compacted (rules shortened + flagged, settlement_sources bounded);
  * per-topic publish cap with honest count/count_total/capped markers;
  * series records shortened, full-record source URL kept;
  * history bounded (top 300 markets, 288 points each);
  * compact JSON encoding; publish guard enforced.

Safe to re-run. Values are only shortened or dropped by documented caps — never
inferred or rewritten.

Run:  python3 tools/slim_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import collector  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PUBLISH_PER_TOPIC = 500


def rank_key(r: dict):
    uv = r.get("usd_volume_24h")
    if uv is not None:
        return (1, uv)
    est = r.get("est_dollar_volume")
    if est is None:
        try:
            est = float(r.get("volume_fp") or 0) * float(r.get("last_price_dollars") or 0)
        except (TypeError, ValueError):
            est = -1
    return (0, est)


def compact_row(r: dict) -> dict:
    out = dict(r)
    rules = out.get("rules_primary")
    if isinstance(rules, str) and len(rules) > 300:
        out["rules_primary"] = rules[:300]
        out["rules_truncated"] = True
    out["settlement_sources"] = collector._compact_sources(out.get("settlement_sources"))
    total = out.get("settlement_sources_total")
    if total is None:
        srcs = r.get("settlement_sources")
        if isinstance(srcs, list):
            out["settlement_sources_total"] = len(srcs)
    return out


def slim_rows(rows: list) -> tuple[list, int]:
    rows = [compact_row(r) for r in rows]
    rows.sort(key=rank_key, reverse=True)
    full = len(rows)
    return rows[:PUBLISH_PER_TOPIC], full


def main() -> int:
    totals = {}

    snap_path = DATA / "snapshot.json"
    if snap_path.exists():
        snap = json.loads(snap_path.read_text())
        by_topic = snap.get("by_topic") or {}
        markets_all = snap.get("markets") or []
        per_topic_full: dict = {}
        published: dict = {}
        new_by_topic = {}
        for t in list(by_topic.keys()) or sorted({r.get("topic") for r in markets_all}):
            rows = by_topic.get(t) or [r for r in markets_all if r.get("topic") == t]
            capped, full = slim_rows(rows)
            new_by_topic[t] = capped
            per_topic_full[t] = full
            published[t] = len(capped)
        snap["by_topic"] = new_by_topic
        snap["markets"] = [r for t in new_by_topic for r in new_by_topic[t]]
        counts = snap.setdefault("counts", {})
        counts["per_topic"] = per_topic_full
        counts["per_topic_published"] = published
        counts["markets_published"] = sum(published.values())
        counts["markets_in_scope"] = counts.get("markets_in_scope") or sum(per_topic_full.values())
        counts["rows_capped"] = any(per_topic_full[t] > published[t] for t in per_topic_full)
        # derived summary keys (same values the collector now writes into snapshot.json)
        api_log = snap.get("api_log") or []
        cat = snap.get("topic_catalog") or {}
        snap["series_with_live_markets_total"] = sum(
            len(v.get("series_with_live_markets") or []) for v in cat.values())
        snap["series_read_total"] = sum(v.get("series_read", 0) for v in cat.values())
        snap["api_request_count"] = len(api_log)
        snap["api_request_failures"] = len([r for r in api_log if not r.get("ok")])
        res_rows = snap.get("resolutions") or []
        snap["resolutions_by_topic"] = {
            t: len([r for r in res_rows if r.get("topic") == t])
            for t in ("gas", "elections", "culture", "crypto", "golf")}
        collector.write_json("snapshot.json", snap, compact=True)
        totals["snapshot.json"] = (snap_path.stat().st_size, counts["markets_published"])

    for t in ("gas", "elections", "culture", "crypto", "golf"):
        p = DATA / f"topic-{t}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        capped, full = slim_rows(d.get("markets") or [])
        d["markets"] = capped
        d["count"] = len(capped)
        d["count_total"] = max(full, d.get("count_total") or 0)
        d["capped"] = d["count_total"] > len(capped)
        d["cap_note"] = ("Rows are capped at the top of the dollar-volume ranking so "
                         "every published file stays under GitHub's 100 MB limit; "
                         "count_total is the full in-scope count.")
        collector.write_json(f"topic-{t}.json", d, compact=True)
        totals[f"topic-{t}.json"] = (p.stat().st_size, len(capped))

    sidx_path = DATA / "series_index.json"
    if sidx_path.exists():
        sidx = json.loads(sidx_path.read_text())
        sidx["series"] = [
            collector._slim_series(s) if isinstance(s, dict) else s
            for s in (sidx.get("series") or [])
        ]
        collector.write_json("series_index.json", sidx, compact=True)
        totals["series_index.json"] = (sidx_path.stat().st_size, len(sidx["series"]))

    hist_path = DATA / "history.json"
    if hist_path.exists():
        hist = json.loads(hist_path.read_text())
        pts = hist.get("points") or {}
        snap = json.loads((DATA / "snapshot.json").read_text()) if (DATA / "snapshot.json").exists() else {}
        ranked = sorted((snap.get("markets") or []), key=rank_key, reverse=True)
        tracked = {r.get("market_ticker") for r in ranked[:300] if r.get("market_ticker")}
        if not tracked:
            tracked = set(list(pts.keys())[:300])
        kept = {}
        for t in list(pts.keys()):
            if t in tracked:
                kept[t] = pts[t][-288:]
        hist["points"] = kept
        hist["tracked_markets"] = len(kept)
        hist["retention_points"] = 288
        collector.write_json("history.json", hist, compact=True)
        totals["history.json"] = (hist_path.stat().st_size, len(kept))

    rlog_path = DATA / "resolutions_log.json"
    if rlog_path.exists():
        rlog = json.loads(rlog_path.read_text())
        rows = rlog.get("resolutions") or []
        rows.sort(key=lambda r: (r.get("settlement_ts") or ""), reverse=True)
        rlog["resolutions"] = rows[:5000]
        rlog["count"] = len(rlog["resolutions"])
        collector.write_json("resolutions_log.json", rlog, compact=True)
        totals["resolutions_log.json"] = (rlog_path.stat().st_size, rlog["count"])

    for name, (size, n) in totals.items():
        print(f"  {name}: {size:,} bytes, {n} rows")
    print("slim_data: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
