#!/usr/bin/env python3
"""kalshi_trade.py — local CLI for the Kalshi DEMO account (safe credential path).

The public GitHub Pages site intentionally never accepts API credentials
(see pages/flagged.html F6). This tool runs on YOUR machine, where the private
key stays in a local file or environment variable, and signs requests exactly
as the official docs describe:

  Headers:  KALSHI-ACCESS-KEY (key id)
            KALSHI-ACCESS-TIMESTAMP (Unix ms, must be within 30s of Kalshi)
            KALSHI-ACCESS-SIGNATURE (base64 of the signature)
  Message:  timestamp_ms + HTTP_METHOD + path-without-query
  Ed25519:  sign the message bytes directly (RFC 8032)
  RSA:      RSA-PSS, SHA-256, MGF1-SHA-256, salt length = digest length
Sources (verified 2026-11-20):
  https://docs.kalshi.com/getting_started/api_keys.md
  https://docs.kalshi.com/getting_started/quick_start_authenticated_requests.md
  https://docs.kalshi.com/getting_started/demo_env.md

Usage:
  export KALSHI_KEY_ID=<your demo key id>
  export KALSHI_PRIVATE_KEY_FILE=/path/to/key.pem

  python3 tools/kalshi_trade.py selftest              # offline signing self-test
  python3 tools/kalshi_trade.py balance
  python3 tools/kalshi_trade.py positions
  python3 tools/kalshi_trade.py fills --limit 100
  python3 tools/kalshi_trade.py order --ticker KX... --side yes --count 1 --price 0.50
  python3 tools/kalshi_trade.py cancel --order-id <id>
  python3 tools/kalshi_trade.py report                # categorise fills + P&L + strategy view

The `report` command categorises every fill by topic (gas prices, elections,
culture, crypto, golf, other), side (yes/no) and settled outcome (win/loss),
and computes P&L from the official settlement value. Nothing is inferred:
missing data is printed as BLANK. Strategy lines are emitted only when a
category has >= 5 fills (the policy documented on pages/analysis.html).
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEMO_BASE = "https://external-api.demo.kalshi.co"
API_PREFIX = "/trade-api/v2"

# Topic classifier — same keyword policy as assets/app.js (word-boundary for
# single words; substring for multi-word), so site and CLI agree.
TOPICS = {
    "gas prices": ["gas", "gasoline", "diesel", "gas price", "oil price", "crude"],
    "elections": ["election", "president", "senate", "house", "vote", "ballot",
                  "governor", "mayor", "congress", "republican", "democrat", "primary"],
    "culture": ["oscar", "grammy", "emmy", "celebrity", "movie", "film", "music",
                "album", "tv show", "super bowl halftime", "met gala"],
    "crypto": ["bitcoin", "btc", "ethereum", "eth", "crypto", "doge", "solana", "xrp"],
    "golf": ["golf", "pga", "masters", "us open golf", "ryder", "open championship"],
}


def classify(text):
    t = (text or "").lower()
    import re
    for topic, keys in TOPICS.items():
        for k in keys:
            if " " in k:
                if k in t:
                    return topic
            elif re.search(r"\b" + re.escape(k) + r"\b", t):
                return topic
    return "other"


# ---------------------------------------------------------------- signing
def load_private_key(path):
    from cryptography.hazmat.primitives import serialization
    with open(path, "rb") as fh:
        return serialization.load_pem_private_key(fh.read(), password=None)


def sign_text(private_key, text):
    """Return base64 signature of text per api_keys.md."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    message = text.encode("utf-8")
    if isinstance(private_key, Ed25519PrivateKey):
        signature = private_key.sign(message)  # RFC 8032 over the message
    else:
        signature = private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
    return base64.b64encode(signature).decode("ascii")


def auth_headers(private_key, key_id, method, path_without_query):
    ts = str(int(time.time() * 1000))
    msg = ts + method + path_without_query
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": sign_text(private_key, msg),
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------- REST
CFG = {"base": DEMO_BASE}


def request(method, path, body=None, key_id=None, private_key=None,
            base_url=None, public=False):
    """Signed (or public) request. `path` must include API_PREFIX and may
    include a query string; signing always strips the query (api_keys.md)."""
    url = (base_url or CFG["base"]) + path
    headers = {"User-Agent": "kalshi-trade-cli/1.0", "Accept": "application/json"}
    if not public:
        if not key_id or private_key is None:
            sys.exit("Set KALSHI_KEY_ID and KALSHI_PRIVATE_KEY_FILE for this command.")
        headers.update(auth_headers(private_key, key_id, method, path.split("?")[0]))
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        sys.exit("HTTP %s %s for %s %s\n%s" % (exc.code, exc.reason, method, path, detail))


def get_env():
    key_id = os.environ.get("KALSHI_KEY_ID", "").strip()
    key_file = os.environ.get("KALSHI_PRIVATE_KEY_FILE", "").strip()
    private_key = None
    if key_file:
        private_key = load_private_key(key_file)
    return key_id, private_key


# ---------------------------------------------------------------- commands
def cmd_selftest(_args):
    """Offline verification that the signer matches the documented scheme."""
    from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
    from cryptography.hazmat.primitives import serialization
    ok = True
    # Ed25519 round trip (RFC 8032 over the message bytes)
    ed = ed25519.Ed25519PrivateKey.generate()
    msg = "1700000000000GET/trade-api/v2/portfolio/balance"
    sig_b64 = sign_text(ed, msg)
    pub = ed.public_key()
    try:
        from cryptography.hazmat.primitives.asymmetric import padding as p
        from cryptography.hazmat.primitives import hashes
        pub.verify(base64.b64decode(sig_b64), msg.encode(), )
        print("Ed25519 signing: OK (signature verifies against public key)")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print("Ed25519 signing: FAILED (%s)" % exc)
    # RSA-PSS round trip (SHA-256, MGF1-SHA-256, salt = digest length)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    sig_b64 = sign_text(key, msg)
    try:
        from cryptography.hazmat.primitives.asymmetric import padding as p
        from cryptography.hazmat.primitives import hashes
        key.public_key().verify(
            base64.b64decode(sig_b64), msg.encode(),
            p.PSS(mgf=p.MGF1(hashes.SHA256()), salt_length=p.PSS.DIGEST_LENGTH),
            hashes.SHA256())
        print("RSA-PSS signing: OK (signature verifies against public key)")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print("RSA-PSS signing: FAILED (%s)" % exc)
    # PEM loading path
    pem = ed.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption())
    import tempfile
    with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False) as fh:
        fh.write(pem)
        tmp = fh.name
    try:
        load_private_key(tmp)
        print("PEM load: OK")
    finally:
        os.unlink(tmp)
    print("Pre-sign text format: timestamp_ms + METHOD + path-without-query "
          "(api_keys.md). No network calls were made.")
    return 0 if ok else 1


def cmd_balance(_args):
    key_id, pk = get_env()
    print(json.dumps(request("GET", API_PREFIX + "/portfolio/balance",
                             key_id=key_id, private_key=pk), indent=2))
    return 0


def cmd_positions(_args):
    key_id, pk = get_env()
    q = "?limit=%d" % max(1, min(_args.limit, 1000))
    print(json.dumps(request("GET", API_PREFIX + "/portfolio/positions" + q,
                             key_id=key_id, private_key=pk), indent=2))
    return 0


def cmd_fills(_args):
    key_id, pk = get_env()
    q = "?limit=%d" % max(1, min(_args.limit, 1000))
    print(json.dumps(request("GET", API_PREFIX + "/portfolio/fills" + q,
                             key_id=key_id, private_key=pk), indent=2))
    return 0


def cmd_order(_args):
    key_id, pk = get_env()
    price_cents = int(round(_args.price * 100))
    side = _args.side.lower()
    body = {
        "ticker": _args.ticker,
        "action": "buy",
        "side": side,
        "count": _args.count,
        "type": "limit",
        "yes_price" if side == "yes" else "no_price": price_cents,
        "time_in_force": _args.tif,
    }
    print(json.dumps(request("POST", API_PREFIX + "/portfolio/orders",
                             body=body, key_id=key_id, private_key=pk), indent=2))
    return 0


def cmd_cancel(_args):
    key_id, pk = get_env()
    path = API_PREFIX + "/portfolio/orders/" + urllib.parse.quote(_args.order_id)
    print(json.dumps(request("DELETE", path, key_id=key_id, private_key=pk), indent=2))
    return 0


def cmd_report(_args):
    """Categorise fills, join settled results, compute P&L and strategy view."""
    key_id, pk = get_env()
    fills_resp = request("GET", API_PREFIX + "/portfolio/fills?limit=1000",
                         key_id=key_id, private_key=pk)
    fills = fills_resp.get("fills") or []
    print("Fills retrieved: %d" % len(fills))
    if not fills:
        print("No fills yet — nothing to analyse. (Policy: no strategy without data.)")
        return 0
    # Join each fill's market to its settled result (public endpoint, no auth).
    settled_cache = {}
    rows = []
    for f in fills:
        ticker = f.get("ticker") or f.get("market_ticker") or ""
        if ticker not in settled_cache:
            settled_cache[ticker] = request(
                "GET", API_PREFIX + "/markets/" + urllib.parse.quote(ticker),
                public=True).get("market") or {}
        m = settled_cache[ticker]
        title = m.get("title") or ticker
        topic = classify(title + " " + ticker)
        side = (f.get("side") or "").lower()
        count = float(f.get("count") or f.get("count_fp") or 0)
        price = float(f.get("price") or f.get("price_dollars") or 0) \
            if (f.get("price") or f.get("price_dollars")) else None
        result = m.get("result") or ""
        sv = m.get("settlement_value_dollars")
        pnl = None
        outcome = ""
        if price is not None and sv not in ("", None) and side in ("yes", "no"):
            settle_side = float(sv) if side == "yes" else 1.0 - float(sv)
            pnl = (settle_side - price) * count
            outcome = "win" if pnl > 0 else ("loss" if pnl < 0 else "flat")
        rows.append({
            "ticker": ticker, "title": title, "topic": topic, "side": side,
            "count": count, "price": price, "result": result,
            "settlement_value_dollars": sv, "pnl": pnl, "outcome": outcome,
            "fill_ts": f.get("ts") or f.get("created_ts") or "",
        })
    # Table
    hdr = ["ticker", "topic", "side", "count", "price", "result", "pnl", "outcome"]
    print("\t".join(hdr))
    for r in rows:
        print("\t".join(
            str(r[k]) if r[k] is not None else "BLANK" for k in hdr))
    # Summary by topic and side
    def summary(keyfn, label):
        groups = {}
        for r in rows:
            k = keyfn(r)
            g = groups.setdefault(k, {"n": 0, "wins": 0, "pnl": 0.0, "pnl_known": 0})
            g["n"] += 1
            if r["outcome"] == "win":
                g["wins"] += 1
            if r["pnl"] is not None:
                g["pnl"] += r["pnl"]
                g["pnl_known"] += 1
        print("\n%s:" % label)
        for k in sorted(groups):
            g = groups[k]
            wr = ("%.1f%%" % (100.0 * g["wins"] / g["n"])) if g["n"] else "BLANK"
            pnl = ("$%.2f" % g["pnl"]) if g["pnl_known"] else "BLANK"
            print("  %-12s fills=%-4d win-rate=%-8s pnl=%s" % (k, g["n"], wr, pnl))
    summary(lambda r: r["topic"], "By topic")
    summary(lambda r: r["side"] or "BLANK", "By side")
    # Strategy view — only where the documented data threshold is met
    print("\nStrategy view (policy: >=5 fills per category, otherwise 'insufficient data'):")
    by_topic = {}
    for r in rows:
        by_topic.setdefault(r["topic"], []).append(r)
    for topic in sorted(by_topic):
        rs = by_topic[topic]
        if len(rs) < 5:
            print("  %-12s insufficient data (%d fills)" % (topic, len(rs)))
            continue
        wins = sum(1 for r in rs if r["outcome"] == "win")
        known = [r for r in rs if r["pnl"] is not None]
        pnl = sum(r["pnl"] for r in known) if known else None
        print("  %-12s %d fills, %d wins, net P&L %s — candidate for review; "
              "test out-of-sample before use" % (
                  topic, len(rs), wins,
                  ("$%.2f" % pnl) if pnl is not None else "BLANK"))
    print("\nNotes: settlement value is the YES-side payout "
          "(market_settlement.md: winning side pays $1/contract). Trading fees "
          "are not included (fill fee fields, when present, are printed raw in "
          "`fills`). BLANK = absent from the API response; never inferred.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEMO_BASE,
                    help="API base (default: Kalshi demo)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    sub.add_parser("balance")
    p = sub.add_parser("positions"); p.add_argument("--limit", type=int, default=100)
    p = sub.add_parser("fills"); p.add_argument("--limit", type=int, default=100)
    p = sub.add_parser("order")
    p.add_argument("--ticker", required=True)
    p.add_argument("--side", choices=["yes", "no"], required=True)
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--price", type=float, required=True,
                   help="limit price in dollars (0..1)")
    p.add_argument("--tif", default="gtc", choices=["gtc", "ioc", "fok"])
    p = sub.add_parser("cancel"); p.add_argument("--order-id", required=True)
    sub.add_parser("report")
    args = ap.parse_args()
    if args.base_url != DEMO_BASE:
        CFG["base"] = args.base_url.rstrip("/")
    return {"selftest": cmd_selftest, "balance": cmd_balance,
            "positions": cmd_positions, "fills": cmd_fills, "order": cmd_order,
            "cancel": cmd_cancel, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
