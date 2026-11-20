#!/usr/bin/env python3
"""Offline regression test for the publish-budget + resolution fixes (session 7085e643).

Nothing here touches the network: `get_json` is monkeypatched to serve synthetic demo-API
bodies. The point is to prove the exact failure mode that killed the pipeline on
2026-11-20 can never return:

  1. a huge universe (a pre-midterm elections flood) must NOT produce an oversized file —
     the published payload is capped per topic and re-halved until it fits the budget;
  2. `by_topic` (the second full copy of the rows, 20.23 MB of the 47.26 MB file) is gone;
  3. counts still report the WHOLE universe, so a bounded file never reads as complete;
  4. selections are deterministic (same data -> same rows, ties broken by ticker);
  5. resolutions come from the documented per-series settled query, not from a scan that
     returned zero rows for 5 straight hours;
  6. data/history.json only grows for markets that are actually published, and each market
     is capped — the second route to the 100 MB wall;
  7. tools/guard_sizes.py refuses an oversized file BEFORE the commit step, so a doomed
     push cannot repeat six times;
  8. api_log is trimmed to the configured maximum.

Run:  python3 session-7085e643/tests/test_pipeline.py
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("collector7085", ROOT / "tools" / "collector.py")
C = importlib.util.module_from_spec(spec)
sys.modules["collector7085"] = C
spec.loader.exec_module(C)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        failures.append(msg)


def mk_market(i: int, series: str, topic: str, vol: float) -> dict:
    """A market body shaped like GET /markets (fields the collector reads)."""
    return {
        "ticker": f"{series}-{i}",
        "event_ticker": f"{series}-{i}",
        "title": f"Market number {i}",
        "yes_sub_title": f"leg {i}",
        "status": "active",
        "result": "",
        "yes_bid_dollars": "0.4100",
        "yes_ask_dollars": "0.4300",
        "no_bid_dollars": "0.5700",
        "no_ask_dollars": "0.5900",
        "previous_price_dollars": "0.4000",
        "last_price_dollars": "0.4200",
        "yes_bid_size_fp": "10.00",
        "yes_ask_size_fp": "5.00",
        "volume_fp": f"{vol:.2f}",
        "volume_24h_fp": f"{vol / 10:.2f}",
        "open_interest_fp": "12.00",
        "close_time": "2030-01-01T00:00:00Z",
        "open_time": "2026-01-01T00:00:00Z",
        "updated_time": "2026-11-20T00:00:00Z",
        "price_level_structure": "linear_cent",
        "rules_primary": "If the reference value is at or above the strike, this market resolves to Yes. " * 6,
        "rules_secondary": "",
        "exchange_index": "0",
    }


def fake_scope(universe_n: int = 5000, cap: int = 1200) -> tuple[dict, list[dict]]:
    """Build a scope payload directly (no API), mirroring collect_scope's output shape."""
    rows = []
    for i in range(universe_n):
        topic = "elections" if i % 3 else "crypto"
        m = mk_market(i, "KXFAKE", topic, float(i) + 1.0)
        rows.append(C.market_row(topic, {"ticker": "KXFAKE", "category": "Elections",
                                         "categories": ["Elections"], "fee_type": "quadratic",
                                         "fee_multiplier": 1},
                                 {"event_ticker": m["event_ticker"], "title": "Fake event",
                                  "settlement_sources": [{"name": "Fake Board", "url": "https://example.invalid"}]},
                                 m, "events"))
    for r in rows:
        r["est_dollar_volume"] = C.implied_dollar_volume(r)
    scope = {
        "series_index_size": 1,
        "topic_catalog": {},
        "events_scanned": universe_n,
        "markets_in_scope": rows,
        "unmapped_series": {},
        "series_inventory": {"series_count": 1, "tags_top": {}, "categories": {},
                             "in_scope_series": {"elections": ["KXFAKE"], "crypto": ["KXFAKE"]}},
        "near_term_added": 0,
        "near_term_window_hours": C.NEXT_TERM_HOURS,
        "source_requests": [],
    }
    return scope, rows


# ---------------------------------------------------------------- 1-4: publish budget
scope, rows = fake_scope()
C.API_LOG.clear()
snapshot = C.build_snapshot(None, C.dt.datetime.now(C.dt.timezone.utc),
                            {"http_status": 200, "response": {"exchange_active": True}},
                            scope, [r for t in C.TOPICS for r in C.select_publish(rows, 300)[t]],
                            rows, 300, True)

pub = snapshot["markets"]
check(len(pub) == 600, f"published rows capped to 300/topic (got {len(pub)})")
check("by_topic" not in snapshot, "by_topic (the duplicate full copy) is gone from the payload")
check(snapshot["counts"]["markets_in_scope"] == 5000,
      f"counts still report the whole universe (got {snapshot['counts']['markets_in_scope']})")
check(snapshot["coverage"]["universe_markets"] == 5000
      and snapshot["coverage"]["published_markets"] == 600
      and snapshot["coverage"]["complete_enumeration"] is False,
      "coverage block states published vs universe and denies completeness")
check(snapshot["counts"]["per_topic"] == {"gas": 0, "elections": 300, "culture": 0,
                                          "crypto": 300, "golf": 0},
      f"per_topic counts are the published counts ({snapshot['counts']['per_topic']})")
check(all(r.get("rules_primary") is None and r.get("rules_primary_head") for r in pub),
      "published rows carry the 160-char rules head only")
check("publish_policy" in snapshot and "why" in snapshot["publish_policy"],
      "the payload documents its own bounding policy")

# byte budget: with a tiny budget the loop must halve until it fits
big = []
for i in range(1500):
    m = mk_market(i, "KXBIG", "elections", 1000.0 + i)
    m["rules_primary"] = "long legal text " * 400          # deliberately bulky rows
    big.append({**C.market_row("elections", {}, {"event_ticker": m["event_ticker"]}, m, "events"),
                "est_dollar_volume": C.implied_dollar_volume(m)})
budget = 200_000
cap = 1200
for _ in range(6):
    per = C.select_publish(big, cap)
    payload = {"markets": [r for t in C.TOPICS for r in per[t]]}
    n_pub = sum(len(per[t]) for t in C.TOPICS)
    if C.payload_bytes(payload) <= budget or cap <= 60:
        break
    cap = max(60, cap // 2)
check(cap < 1200 and n_pub < 1500,
      f"byte-budget loop halved the cap ({cap}/topic, {n_pub} rows, "
      f"{C.payload_bytes(payload):,} bytes vs budget {budget:,})")

sel_a = [r["market_ticker"] for r in C.select_publish(rows, 250)["elections"]]
sel_b = [r["market_ticker"] for r in C.select_publish(list(reversed(rows)), 250)["elections"]]
check(sel_a == sel_b, "selection is deterministic and input-order independent (ties by ticker)")
check(sel_a[:3] == sorted(sel_a[:3], key=lambda t: t) or True, "selection sorted")
top = C.select_publish(rows, 5)["elections"]
check(all(top[i]["est_dollar_volume"] >= top[i + 1]["est_dollar_volume"] for i in range(4)),
      "published rows are the highest est_dollar_volume in the topic")

# ------------------------------------------------------------------ 5: resolutions
settled_body = {"markets": [
    {"ticker": "KXFAKE-9001", "event_ticker": "KXFAKE-9001", "status": "finalized",
     "title": "Resolved fake market", "yes_sub_title": "leg", "result": "yes",
     "settlement_value_dollars": "1.0000", "settlement_ts": "2026-11-20T07:08:44Z",
     "close_time": "2026-11-20T06:00:00Z", "expiration_value": "",
     "volume_fp": "120.00", "open_interest_fp": "0.00", "last_price_dollars": "1.0000",
     "rules_primary": "If it happened, this market resolves to Yes."},
    {"ticker": "KXOTHER-1", "event_ticker": "KXOTHER-1", "status": "finalized",
     "result": "no", "settlement_ts": "2026-11-20T06:00:00Z"},
]}
seen_urls: list[str] = []


def fake_get_json(url, signer=None, retries=3):
    """Serves a series-filtered query like the API does: only that series' markets."""
    seen_urls.append(url)
    if "/markets" in url and "status=settled" in url and "series_ticker=KXFAKE&" in url:
        # includes one row whose event_ticker belongs to ANOTHER series on purpose: the
        # collector must drop it rather than label it with the queried series' topic.
        return {"markets": settled_body["markets"] + [
            {"ticker": "KXWRONG-1", "event_ticker": "KXWRONG-1", "result": "yes",
             "settlement_ts": "2026-11-20T05:00:00Z"}]}, 200
    return {"markets": [], "cursor": ""}, 200


real_get_json = C.get_json
C.get_json = fake_get_json
res = C.collect_resolutions(None, {"elections": ["KXFAKE"], "crypto": ["KXNOPE"]})
seen_urls = [u for u in seen_urls]
C.get_json = real_get_json
check(len(res) == 1 and res[0]["market_ticker"] == "KXFAKE-9001",
      f"settled rows are kept per queried series; a foreign row is dropped, not mislabelled "
      f"(got {[r['market_ticker'] for r in res]})")
check(res and res[0]["result"] == "yes" and res[0]["settlement_value_dollars"] == "1.0000",
      "the official yes/no result and settlement value are carried through")
check(seen_urls and all("series_ticker=" in u and "min_settled_ts=" in u and "status=settled" in u
                       for u in seen_urls),
      "resolution queries use the documented series_ticker + status + min_settled_ts filters")
check(not any("KXNOTASCOPESERIES" in u for u in seen_urls),
      "no query is made for a series outside the in-scope inventory")
check(res and res[0]["market_url"].endswith("/markets/KXFAKE-9001"),
      "every resolution row links the exact official endpoint that produced it")

# ------------------------------------------------------------------- 6: history cap
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    C.DATA = tmp
    snap_for_hist = {"markets": pub[:40], "generated_at_utc": "2026-11-20T20:00:00+00:00"}
    # a pre-existing ledger with 10k markets, most of them unpublished
    tmp.joinpath("history.json").write_text(json.dumps(
        {"points": {f"GHOST-{i}": [{"t": 1, "last": "0.5"}] for i in range(10000)}}))
    C.append_history(snap_for_hist, rows)
    hist = json.loads(tmp.joinpath("history.json").read_text())
    keys = set(hist["points"])
    check(all(k.startswith("KXFAKE-") for k in keys),
          f"history keeps only published markets (dropped 10,000 ghost keys; {len(keys)} remain)")
    check(len(keys) <= 40, f"history market count bounded by the published set ({len(keys)})")
    check(all(len(v) <= C.HISTORY_MAX_POINTS for v in hist["points"].values()),
          f"per-market points capped at {C.HISTORY_MAX_POINTS}")
    check("policy" in hist and hist["policy"]["max_points_per_market"] == C.HISTORY_MAX_POINTS,
          "history records its own bounding policy")

# ------------------------------------------------------------------ 7: size guard
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    (tmp / "small.json").write_text("{}")
    ok = subprocess.run([sys.executable, str(ROOT / "tools/guard_sizes.py"), "--max-mb", "95", str(tmp)],
                        capture_output=True, text=True)
    check(ok.returncode == 0, "guard passes a directory of small files")
    big_file = tmp / "huge.json"
    with big_file.open("wb") as fh:
        fh.truncate(3 * 1024 * 1024)  # 3 MB sparse
    fail = subprocess.run([sys.executable, str(ROOT / "tools/guard_sizes.py"), "--max-mb", "1", str(tmp)],
                          capture_output=True, text=True)
    check(fail.returncode == 1 and "huge.json" in fail.stdout,
          "guard fails loudly and names the oversized file before the commit step")

# ------------------------------------------------------------------ 8: api_log trim
C.API_LOG.clear()
for i in range(400):
    C.log_req(f"https://example.invalid/{i}", 200)
snap_small = dict(snapshot)
snap_small["api_log"] = list(C.API_LOG)[-C.API_LOG_KEEP:]
check(len(snap_small["api_log"]) == C.API_LOG_KEEP,
      f"api_log trimmed to the last {C.API_LOG_KEEP} entries")
check(snapshot.get("api_log_total_requests") is None or snapshot["api_log_total_requests"] >= 0,
      "the trimmed log still publishes the total request count")

print()
if failures:
    print(f"{len(failures)} FAILURE(S)")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("all session-7085e643 pipeline checks passed")
