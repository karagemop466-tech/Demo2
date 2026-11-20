#!/usr/bin/env python3
"""Price-jump alerts: contract-price moves of >= $0.10 in either direction.

Run:    python3 tools/build_jumps.py
Reads:  data/dashboard_instrument.json      (official Trade API snapshot: markets + trade prints)
        data/history_instrument/*.json      (rolling 15-minute snapshots of last price per market)
Writes: data/jumps.json                     (machine-readable result, every value sourced)
        jumps/index.html                    (the page)

Two detectors, reported separately because they have different resolution:

  1. TRADE PRINTS (fine resolution). Consecutive official trade prints for the same market,
     sorted by the API's created_time. A move is |yes_price(t) - yes_price(t-1)| >= 0.10.
     Source: GET /markets/trades?ticker=...  (docs: api-reference/market/get-trades).
     Limit: the collector keeps only the first page (limit=1000, cursor not followed) and at
     most 600 prints per market, and only for the largest markets per topic. Stated on the page.

  2. SNAPSHOTS (coarse resolution). Consecutive collector snapshots of last_price_dollars for the
     same market, both prices > 0. Snapshots are ~10-60 minutes apart, so a move that happens and
     reverts between two snapshots is invisible here. Stated on the page.

Nothing is inferred: a move is not attributed to news or any event. The "cause" column is left
blank and marked unverified; a link is shown only where an official Kalshi page exists for the
series (the page URL pattern kalshi.com/markets/<series> was checked live, see flags).
"""

from __future__ import annotations

import datetime as dt
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_site as bs  # noqa: E402  (shared layout + nav)

THRESHOLD = 0.10
EPS = 1e-9
API = "https://external-api.demo.kalshi.co/trade-api/v2"
DOCS_TRADES = "https://docs.kalshi.com/api-reference/market/get-trades"
DOCS_CANDLES = "https://docs.kalshi.com/api-reference/market/get-market-candlesticks"
WEB = "https://kalshi.com/markets/"

TOPIC_LABEL = {"gas": "Gas prices", "elections": "Elections", "culture": "Culture",
               "crypto": "Crypto", "golf": "Golf"}


def load(path: Path):
    return json.loads(path.read_text())


def fmt_time(iso: str) -> str:
    """'2026-10-22T02:52:15.046534Z' -> '2026-10-22 02:52:15 UTC' (sub-seconds dropped for display)."""
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return t.strftime("%Y-%m-%d %H:%M:%S UTC")


def parse_ts(iso: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))


def market_index(snapshot: dict) -> dict:
    idx = {}
    for topic, rows in snapshot.get("markets", {}).items():
        for r in rows:
            idx[r["ticker"]] = {
                "topic": topic,
                "title": r.get("title", ""),
                "series": r.get("series_ticker", ""),
                "event": r.get("event_ticker", ""),
                "api_url": r.get("source_market_url") or f"{API}/markets/{r['ticker']}",
            }
    return idx


def trade_moves(snapshot: dict, idx: dict):
    """Return (moves, per_market_coverage)."""
    moves, coverage = [], []
    for ticker, block in sorted(snapshot.get("trades", {}).items()):
        prints = sorted(block.get("trades", []), key=lambda p: p["created_time"])
        meta = idx.get(ticker, {})
        cov = {
            "ticker": ticker, "topic": meta.get("topic", ""), "title": meta.get("title", ""),
            "prints": len(prints),
            "first": prints[0]["created_time"] if prints else "",
            "last": prints[-1]["created_time"] if prints else "",
            "source_url": block.get("source_url", ""),
            "moves": 0,
        }
        for a, b in zip(prints, prints[1:]):
            pa, pb = float(a["yes_price_dollars"]), float(b["yes_price_dollars"])
            d = pb - pa
            if abs(d) + EPS >= THRESHOLD:
                cov["moves"] += 1
                moves.append({
                    "ticker": ticker,
                    "topic": meta.get("topic", ""),
                    "title": meta.get("title", ""),
                    "series": meta.get("series", ""),
                    "event": meta.get("event", ""),
                    "from_time": a["created_time"], "from_price": f"{pa:.4f}",
                    "from_size": a.get("count_fp", ""),
                    "to_time": b["created_time"], "to_price": f"{pb:.4f}",
                    "to_size": b.get("count_fp", ""),
                    "delta": f"{d:+.4f}",
                    "direction": "up" if d > 0 else "down",
                    "same_timestamp": a["created_time"] == b["created_time"],
                    "trade_source": block.get("source_url", ""),
                    "market_source": meta.get("api_url", ""),
                })
        coverage.append(cov)
    moves.sort(key=lambda m: m["to_time"], reverse=True)
    return moves, coverage


def snapshot_moves(history_dir: Path, idx: dict):
    index = load(history_dir / "index.json")
    days = index.get("days", [])
    samples = []
    for day in days:
        p = history_dir / f"{day}.json"
        if p.exists():
            samples.extend(load(p).get("samples", []))
    samples.sort(key=lambda s: s["ts"])
    moves, pairs, intervals = [], 0, []
    last = {}  # ticker -> (ts, price)
    for s in samples:
        for ticker, m in s["markets"].items():
            p = float(m["lp"])
            if ticker in last and p > 0:
                t0, p0 = last[ticker]
                if p0 > 0:
                    pairs += 1
                    intervals.append(s["ts"] - t0)
                    d = p - p0
                    if abs(d) + EPS >= THRESHOLD:
                        meta = idx.get(ticker, {})
                        moves.append({
                            "ticker": ticker, "topic": m.get("t", meta.get("topic", "")),
                            "title": meta.get("title", ""), "series": meta.get("series", ""),
                            "from_time": dt.datetime.fromtimestamp(t0, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "from_price": f"{p0:.4f}",
                            "to_time": dt.datetime.fromtimestamp(s["ts"], dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "to_price": f"{p:.4f}", "delta": f"{d:+.4f}",
                            "direction": "up" if d > 0 else "down",
                        })
            if p > 0:
                last[ticker] = (s["ts"], p)
    stats = {
        "samples": len(samples),
        "days": days,
        "first_sample": dt.datetime.fromtimestamp(samples[0]["ts"], dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if samples else "",
        "last_sample": dt.datetime.fromtimestamp(samples[-1]["ts"], dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if samples else "",
        "pairs_compared": pairs,
        "min_gap_min": round(min(intervals) / 60, 1) if intervals else None,
        "max_gap_min": round(max(intervals) / 60, 1) if intervals else None,
        "source": "data/history_instrument/*.json (collector snapshots of last_price_dollars)",
    }
    moves.sort(key=lambda m: m["to_time"], reverse=True)
    return moves, stats


def sparkline(prints: list, moves_at: set) -> str:
    """Inline SVG: x = time of each print, y = YES price 0..1. Jump endpoints drawn as red dots."""
    if len(prints) < 2:
        return '<p class="small muted">Fewer than two prints: no line to draw.</p>'
    W, H, PL, PB, PT, PR = 640, 150, 40, 22, 8, 8
    ts = [parse_ts(p["created_time"]).timestamp() for p in prints]
    t0, t1 = min(ts), max(ts)
    span = (t1 - t0) or 1.0

    def X(t): return PL + (t - t0) / span * (W - PL - PR)
    def Y(p): return PT + (1 - p) * (H - PT - PB)

    pts = [(X(t), Y(float(p["yes_price_dollars"])), i) for i, (t, p) in enumerate(zip(ts, prints))]
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y, _) in enumerate(pts))
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#b32d2d"><title>{html.escape(prints[i]["created_time"])} · {float(prints[i]["yes_price_dollars"]):.2f}</title></circle>'
        for x, y, i in pts if i in moves_at
    )
    grid = "".join(
        f'<line x1="{PL}" x2="{W-PR}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#e5e7eb"/>'
        f'<text x="{PL-6}" y="{Y(v)+4:.1f}" font-size="10" text-anchor="end" fill="#6b7280">{v:.2f}</text>'
        for v in (0.0, 0.25, 0.5, 0.75, 1.0)
    )
    xl = (f'<text x="{PL}" y="{H-6}" font-size="10" fill="#6b7280">{fmt_time(prints[0]["created_time"])}</text>'
          f'<text x="{W-PR}" y="{H-6}" font-size="10" text-anchor="end" fill="#6b7280">{fmt_time(prints[-1]["created_time"])}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="YES trade price over time">'
            f'{grid}<path d="{path}" fill="none" stroke="#1f5fa8" stroke-width="1.6"/>{dots}{xl}</svg>')


def build_html(moves, coverage, snap_moves, snap_stats, snapshot, idx) -> str:
    gen = snapshot.get("meta", {}).get("generated_at", "")
    n_prints = sum(c["prints"] for c in coverage)
    markets_with_moves = len({m["ticker"] for m in moves})
    prints_by = {k: sorted(v.get("trades", []), key=lambda p: p["created_time"]) for k, v in snapshot.get("trades", {}).items()}

    # --- KPI row
    kpis = (
        f'<div class="kpis">'
        f'<div class="card"><div class="muted small">Trade-print moves ≥ $0.10</div><div class="big">{len(moves)}</div>'
        f'<div class="small">across {markets_with_moves} of {len(coverage)} markets with trade data</div></div>'
        f'<div class="card"><div class="muted small">Snapshot moves ≥ $0.10</div><div class="big">{len(snap_moves)}</div>'
        f'<div class="small">{snap_stats["pairs_compared"]} price pairs compared across {snap_stats["samples"]} snapshots</div></div>'
        f'<div class="card"><div class="muted small">Trade prints analysed</div><div class="big">{n_prints:,}</div>'
        f'<div class="small">first page per market, newest 600 kept</div></div>'
        f'<div class="card"><div class="muted small">Data as of</div><div class="big" style="font-size:1.1rem">{html.escape(fmt_time(gen) if gen else "unknown")}</div>'
        f'<div class="small">collector run time (UTC)</div></div>'
        f'</div>'
    )

    cause_cell = '<span class="pill flag">unverified</span> <span class="small muted">no official cause source recorded</span>'

    def link(url, label):
        return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{label}</a>'

    # --- Table 1: trade-print jumps
    rows = []
    for m in moves:
        arrow = "▲" if m["direction"] == "up" else "▼"
        same = ' <span class="pill flag">same timestamp: order unknown</span>' if m["same_timestamp"] else ""
        rows.append([
            f'{html.escape(fmt_time(m["to_time"]))}{same}',
            html.escape(TOPIC_LABEL.get(m["topic"], m["topic"])),
            f'{html.escape(m["title"])}<br><span class="small muted">{html.escape(m["ticker"])}</span>',
            f'${m["from_price"]} → ${m["to_price"]}<br><span class="small">{arrow} {html.escape(m["delta"])}</span>',
            f'{html.escape(m["from_size"] or "—")} / {html.escape(m["to_size"] or "—")}',
            cause_cell,
            f'{link(m["trade_source"], "trades API")}<br>{link(m["market_source"], "market API")}'
            + (f'<br>{link(WEB + m["series"].lower(), "Kalshi page")}' if m["series"] else ""),
        ])
    if rows:
        table1 = _table(["Print time (UTC)", "Topic", "Market", "Price move (YES)", "Contracts before / after", "Cause", "Sources"], rows)
    else:
        table1 = '<p class="notice">No trade-print move of $0.10 or more was found in the collected prints.</p>'

    # --- Table 2: snapshot jumps
    if snap_moves:
        srows = [[html.escape(fmt_time(m["to_time"])),
                  html.escape(TOPIC_LABEL.get(m["topic"], m["topic"])),
                  html.escape(m["title"]), f'${m["from_price"]} → ${m["to_price"]}', m["delta"],
                  f'{link(API + "/markets/" + m["ticker"], "market API")}'] for m in snap_moves]
        table2 = _table(["Snapshot time", "Topic", "Market", "Last price", "Move", "Source"], srows)
    else:
        table2 = (f'<p class="notice">None. {snap_stats["pairs_compared"]:,} consecutive-snapshot price pairs were compared '
                  f'(gap between snapshots: {snap_stats["min_gap_min"]}–{snap_stats["max_gap_min"]} minutes). '
                  f'A move that starts and reverts between two snapshots cannot be seen at this resolution.</p>')

    # --- Charts: one per market that has at least 2 prints, markets with moves first
    charts = []
    order = sorted(coverage, key=lambda c: (-c["moves"], -c["prints"]))
    for c in order:
        if c["prints"] < 2:
            continue
        pr = prints_by.get(c["ticker"], [])
        mv = set()
        for i in range(1, len(pr)):
            if abs(float(pr[i]["yes_price_dollars"]) - float(pr[i - 1]["yes_price_dollars"])) + EPS >= THRESHOLD:
                mv.add(i); mv.add(i - 1)
        charts.append(
            f'<div class="card chart"><div><b>{html.escape(c["title"])}</b> '
            f'<span class="small muted">{html.escape(c["ticker"])} · {c["prints"]} prints · {c["moves"]} move(s) ≥ $0.10</span></div>'
            f'{sparkline(pr, mv)}'
            f'<div class="small">Source: {link(c["source_url"], "trades API")}</div></div>')
    chart_html = "".join(charts) or '<p class="notice">No market has two or more trade prints in the collected data.</p>'

    # --- Table 3: coverage
    crow = [[html.escape(TOPIC_LABEL.get(c["topic"], c["topic"])),
             f'{html.escape(c["title"])}<br><span class="small muted">{html.escape(c["ticker"])}</span>',
             f'{c["prints"]:,}',
             html.escape(fmt_time(c["first"])) if c["first"] else "—",
             html.escape(fmt_time(c["last"])) if c["last"] else "—",
             str(c["moves"]), link(c["source_url"], "trades API")] for c in coverage]
    table3 = _table(["Topic", "Market", "Prints kept", "First print", "Latest print", "Moves ≥ $0.10", "Source"], crow)

    style = ("<style>.big{font-size:1.9rem;font-weight:700;line-height:1.2}"
             ".chartgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}"
             ".chart svg{display:block;margin:6px 0}</style>")
    body = style + f"""
<h1>Price jumps ≥ $0.10</h1>
<p class="lead">Every contract-price move of ten cents or more between consecutive official prints, in
either direction. Each row shows the time, the size of the prints on each side, and the official
source. The page does <b>not</b> say what caused a move: the cause column is blank and marked
<span class="pill flag">unverified</span> until an official source is recorded for it.</p>
<div class="notice bad"><b>Coverage is narrow.</b> Only {len(coverage)} markets have trade prints in the
collected data (the collector pulls the largest markets per topic). Snapshot resolution is
{snap_stats["min_gap_min"]}–{snap_stats["max_gap_min"]} minutes. Read "no moves" here as
"none in this sample", not "no moves on Kalshi".</div>
{kpis}
<h2>1. Trade-print moves ≥ $0.10 (newest first)</h2>
<p class="small muted">Price = YES price of each official trade print (<code>yes_price_dollars</code>).
Contracts = <code>count_fp</code> of the print before and after the move. A print can be very small,
so check the contract count before reading a move as market-wide.</p>
{table1}
<h2>2. Snapshot moves ≥ $0.10</h2>
{table2}
<h2>3. Charts: YES trade price over time</h2>
<p class="small muted">Time runs left to right; price runs from $0.00 (bottom) to $1.00 (top). Red dots
mark the two prints on each side of a move of $0.10 or more.</p>
<div class="chartgrid">{chart_html}</div>
<h2>4. Coverage: what was analysed</h2>
<p class="small muted">Every market the collector fetched trade prints for. Prints are the first page of the
official endpoint (up to 1,000 requested) with at most the newest 600 kept, so very old prints may be missing.</p>
{table3}
<h2>5. Limits you should know before using this page</h2>
<ul class="clean">
<li><b>Cause links are not provided.</b> No official Kalshi source links a price move to news. Adding
news links would be inference, so the column stays blank.</li>
<li><b>Thin prints can look like jumps.</b> A single 0.01-contract print can move the last price. Check
the contract counts in table 1.</li>
<li><b>Same-timestamp prints.</b> When two prints share a timestamp, their order is unknown, so a
move between them is shown with a flag.</li>
<li><b>No intraday resolution for snapshots.</b> The snapshot detector cannot see a move shorter than the gap
between snapshots. A WebSocket trade feed would fix this; see the flags page.</li>
<li><b>Time window selector.</b> This page is a static build of the collected data. Choosing seconds, minutes
or hours at run time needs the live feed, which is listed as a suggestion, not built here.</li>
</ul>
<p class="small muted">Generated by <code>tools/build_jumps.py</code> from
<code>data/dashboard_instrument.json</code> and <code>data/history_instrument/</code>. Machine-readable
output: <a href="../data/jumps.json">data/jumps.json</a>. Trade endpoint docs:
{link(DOCS_TRADES, "get-trades")}.</p>
"""
    return body


def _table(headers, rows):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def main() -> int:
    snapshot = load(ROOT / "data" / "dashboard_instrument.json")
    idx = market_index(snapshot)
    moves, coverage = trade_moves(snapshot, idx)
    snap_moves, snap_stats = snapshot_moves(ROOT / "data" / "history_instrument", idx)

    out = {
        "generated_from": {
            "snapshot": "data/dashboard_instrument.json",
            "snapshot_generated_at": snapshot.get("meta", {}).get("generated_at", ""),
            "history": "data/history_instrument/",
        },
        "threshold_dollars": THRESHOLD,
        "trade_print_moves": moves,
        "trade_coverage": coverage,
        "snapshot_moves": snap_moves,
        "snapshot_stats": snap_stats,
        "sources": {
            "trades_endpoint": DOCS_TRADES,
            "api_base": API,
            "web_pattern": WEB + "<series ticker, lowercase>",
            "candlesticks_endpoint": DOCS_CANDLES,
        },
        "not_inferred": "cause is never inferred; no news or event attribution is made",
    }
    (ROOT / "data" / "jumps.json").write_text(json.dumps(out, indent=1) + "\n")

    body = build_html(moves, coverage, snap_moves, snap_stats, snapshot, idx)
    bs.page(path="jumps/index.html", title="Price Jumps", active="jumps", body=body,
            desc="Contract-price moves of $0.10 or more between consecutive official Kalshi prints, with sources.")
    print(f"trade-print moves >= $0.10: {len(moves)}; snapshot moves: {len(snap_moves)}; "
          f"markets with trade data: {len(coverage)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
