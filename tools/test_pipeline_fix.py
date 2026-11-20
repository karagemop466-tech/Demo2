#!/usr/bin/env python3
"""Offline regression tests for the live-data pipeline fixes.

They cover the two defects that broke the publish step and the resolution table:

1. `select_published` keeps the published file small enough for GitHub
   (the 2026-11-20 run produced a 111.97 MB snapshot.json and the push was
   rejected), while keeping whole events together.
2. `resolve_series_ticker` recovers the series ticker from an event ticker even
   when the series ticker itself contains a dash ("GOVPARTY-NH"), which the old
   `event_ticker.split("-")[0]` rule got wrong - that is why the resolution
   table was empty.

Run: python3 tools/test_pipeline_fix.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import collector as C  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        FAILURES.append(name)


def row(topic: str, event: str, ticker: str, est: float | None) -> dict:
    return {
        "topic": topic,
        "event_ticker": event,
        "market_ticker": ticker,
        "est_dollar_volume": est,
    }


def test_select_published() -> None:
    print("select_published")
    rows: list[dict] = []
    # 5 events in elections, each with 3 markets
    for e in range(5):
        for m in range(3):
            rows.append(row("elections", f"KXE{e}", f"KXE{e}-M{m}", float(1000 - e * 100 + m)))
    # one event with a much bigger market, but it is not the top event by total
    rows.append(row("elections", "KXSMALL", "KXSMALL-M0", 9000.0))
    rows.append(row("golf", "KXPGATOUR", "KXPGATOUR-M0", 500.0))

    kept, meta = C.select_published(rows, events_per_topic=3, top_markets=1)
    kept_tickers = {r["market_ticker"] for r in kept}
    events = {r["event_ticker"] for r in kept}
    check("keeps whole events", "KXSMALL" in events and "KXE0" in events)
    check("drops the lowest event", "KXE4" not in events, f"events={sorted(events)}")
    check("golf row survives", "KXPGATOUR-M0" in kept_tickers)
    check("counts what was seen", meta["markets_seen"] == len(rows))
    check("counts what was published", meta["markets_published"] == len(kept))
    check("per-topic seen counts", meta["per_topic"]["elections"]["events_seen"] == 6)
    check("no duplicate tickers", len(kept_tickers) == len(kept))
    check("published rows are sorted by the estimate",
          all((kept[i]["est_dollar_volume"] or 0) >= (kept[i + 1]["est_dollar_volume"] or 0)
              for i in range(len(kept) - 1)))
    check("the rule is recorded", "estimated dollar volume" in meta["rule"])


def test_resolve_series_ticker() -> None:
    print("resolve_series_ticker")
    known = {"KXNEWPOPE", "GOVPARTY-NH", "KXXRP", "KXPGATOUR", "DIESEL"}
    check("plain event", C.resolve_series_ticker("KXNEWPOPE-70", known) == "KXNEWPOPE")
    check("dashed series ticker", C.resolve_series_ticker("GOVPARTY-NH-26", known) == "GOVPARTY-NH")
    check("crypto event", C.resolve_series_ticker("KXXRP-26NOV2006", known) == "KXXRP")
    check("golf event", C.resolve_series_ticker("KXPGATOUR-THRC26", known) == "KXPGATOUR")
    check("unknown event", C.resolve_series_ticker("KXUNKNOWN-1", known) is None)
    check("empty event", C.resolve_series_ticker("", known) is None)


def test_size_guard() -> None:
    print("size guard")
    check("MAX_FILE_BYTES is below GitHub's 100 MB limit", C.MAX_FILE_BYTES < 100 * 1024 * 1024)
    snap = ROOT / "data" / "snapshot.json"
    if not snap.exists():
        print("  SKIP  no committed snapshot to measure")
        return
    data = json.loads(snap.read_text())
    rows = data.get("markets") or []
    for r in rows:
        r.setdefault("est_dollar_volume", None)
    kept, meta = C.select_published(rows, events_per_topic=C.PUBLISH_EVENTS_PER_TOPIC)
    published_bytes = len(json.dumps(kept, indent=1).encode())
    before = snap.stat().st_size
    check("published rows fit the collector limit",
          published_bytes <= C.MAX_FILE_BYTES,
          f"{published_bytes} bytes")
    print(f"  INFO  committed snapshot {before} bytes -> published rows {published_bytes} bytes "
          f"({meta['markets_published']} of {meta['markets_seen']} markets)")


def test_write_json_refuses_oversized() -> None:
    print("write_json guard")
    original = C.MAX_FILE_BYTES
    try:
        C.MAX_FILE_BYTES = 100
        try:
            C.write_json("__should_not_exist__.json", {"x": "y" * 5000})
            check("oversized payload is refused", False, "no error raised")
        except SystemExit as e:
            check("oversized payload is refused", "exceeds" in str(e))
    finally:
        C.MAX_FILE_BYTES = original
        p = C.DATA / "__should_not_exist__.json"
        if p.exists():
            p.unlink()


def main() -> int:
    test_select_published()
    test_resolve_series_ticker()
    test_size_guard()
    test_write_json_refuses_oversized()
    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) FAILED: {FAILURES}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
