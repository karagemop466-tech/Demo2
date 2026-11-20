#!/usr/bin/env python3
"""Command-line access to the Kalshi demo (or production) Trade API.

Signing follows the official Kalshi specification:
  https://docs.kalshi.com/getting_started/api_keys
  https://docs.kalshi.com/getting_started/quick_start_authenticated_requests

  * the signed message is  <timestamp-ms><HTTP-METHOD><path-without-query>
  * Ed25519 keys sign the message directly
  * RSA keys use RSA-PSS with SHA-256, MGF1-SHA-256, salt length = digest length
  * the signature is base64 encoded and sent in KALSHI-ACCESS-SIGNATURE
  * the timestamp must be within 30 seconds of Kalshi's clock

The private key never leaves the machine: it is read from a local PEM file and
used only through the `openssl` command line tool, so no third-party Python
package is required.

The credentials are supplied by the operator, not by this repository:

    python3 tools/kalshi_trade.py --key ~/.kalshi/demo.key --key-id <KEY_ID> balance

Commands:
    balance            GET  /portfolio/balance
    positions          GET  /portfolio/positions
    fills              GET  /portfolio/fills
    orders             GET  /portfolio/orders
    settlements        GET  /portfolio/settlements
    market TICKER      GET  /markets/TICKER
    orderbook TICKER   GET  /markets/TICKER/orderbook
    place  --ticker T --side yes|no --count N [--price P] [--type limit|market]
                        POST /portfolio/orders
    cancel  ORDER_ID   DELETE /portfolio/orders/ORDER_ID
    log                read the local trade log written by `place`

Every command prints the raw JSON response so nothing is hidden or reinterpreted.
"""

import argparse
import base64
import json
import os
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DEMO_BASE = "https://external-api.demo.kalshi.co/trade-api/v2"
PROD_BASE = "https://external-api.kalshi.com/trade-api/v2"
LOG_PATH = os.path.join(os.path.expanduser("~"), ".kalshi_demo_trade_log.jsonl")


# ---------------------------------------------------------------- signing
# DER object identifiers for the two supported key types
OID_ED25519 = bytes([0x06, 0x03, 0x2B, 0x65, 0x70])                  # 1.3.101.112
OID_RSA = bytes([0x06, 0x09, 0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D,
                 0x01, 0x01, 0x01])                                    # 1.2.840.113549.1.1.1


def key_kind(pem_path):
    """Detect Ed25519 vs RSA from the parsed key.

    The PEM header does not identify the key type (PKCS#8 RSA keys also start
    with "-----BEGIN PRIVATE KEY-----"), so the SubjectPublicKeyInfo DER is
    inspected for the algorithm identifier instead."""
    proc = subprocess.run(["openssl", "pkey", "-in", pem_path, "-pubout", "-outform", "DER"],
                          capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("could not read the private key with openssl:\n"
                         + proc.stderr.decode("utf-8", "replace").strip())
    der = proc.stdout
    if OID_ED25519 in der[:64]:
        return "ed25519"
    if OID_RSA in der[:64]:
        return "rsa"
    raise SystemExit("unrecognised key type; expected Ed25519 or RSA")


def sign(pem_path, message):
    """Sign `message` and return the base64 signature.

    OpenSSL's one-shot pkeyutl cannot size a pipe, so the message is written
    to a temporary file first."""
    kind = key_kind(pem_path)
    tmp = tempfile.NamedTemporaryFile(prefix="kalshi-msg-", delete=False)
    try:
        tmp.write(message)
        tmp.close()
        if kind == "ed25519":
            cmd = ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", pem_path, "-in", tmp.name]
        else:
            cmd = ["openssl", "dgst", "-sha256",
                   "-sigopt", "rsa_padding_mode:pss",
                   "-sigopt", "rsa_pss_saltlen:digest",
                   "-sign", pem_path, tmp.name]
        proc = subprocess.run(cmd, capture_output=True)
    finally:
        os.unlink(tmp.name)
    if proc.returncode != 0:
        raise SystemExit("signing failed:\n" + proc.stderr.decode("utf-8", "replace").strip())
    return base64.b64encode(proc.stdout).decode("ascii")


def signed_request(base, key_id, pem_path, method, path, body=None, query=None):
    """Perform a signed Kalshi request. `path` is relative to the API base."""
    url = base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    sign_path = "/trade-api/v2" + path.split("?")[0]
    ts = str(int(time.time() * 1000))
    message = (ts + method + sign_path).encode("utf-8")
    signature = sign(pem_path, message)
    headers = {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45, context=ssl.create_default_context()) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"error": raw[:500]}


# ---------------------------------------------------------------- trade log
def append_log(entry):
    path = os.environ.get("KALSHI_TRADE_LOG", LOG_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return path


def read_log():
    path = os.environ.get("KALSHI_TRADE_LOG", LOG_PATH)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# ---------------------------------------------------------------- commands
def price_to_cents(p):
    """Kalshi prices are dollars with up to 4 decimals; the order API uses
    integer cents (no_sub_title / yes_price are in cents)."""
    return int(round(float(p) * 100))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", help="path to the private key PEM file")
    ap.add_argument("--key-id", help="Kalshi API key id")
    ap.add_argument("--base", default=DEMO_BASE, help="API base (default: demo)")
    ap.add_argument("--prod", action="store_true", help="use the production API instead of demo")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("balance")
    sub.add_parser("positions")
    sub.add_parser("fills")
    sub.add_parser("orders")
    sub.add_parser("settlements")
    sub.add_parser("log")

    p_market = sub.add_parser("market")
    p_market.add_argument("ticker")
    p_ob = sub.add_parser("orderbook")
    p_ob.add_argument("ticker")

    p_place = sub.add_parser("place")
    p_place.add_argument("--ticker", required=True)
    p_place.add_argument("--side", required=True, choices=["yes", "no"])
    p_place.add_argument("--count", type=int, required=True)
    p_place.add_argument("--price", type=float, help="limit price in dollars (0-1)")
    p_place.add_argument("--type", default="limit", choices=["limit", "market"])
    p_place.add_argument("--client-order-id", default=None)

    p_cancel = sub.add_parser("cancel")
    p_cancel.add_argument("order_id")

    args = ap.parse_args()
    base = PROD_BASE if args.prod else args.base

    if args.cmd == "log":
        rows = read_log()
        print(json.dumps(rows, indent=2))
        return 0

    if not args.key or not args.key_id:
        raise SystemExit("--key (private key PEM) and --key-id are required for this command. "
                         "See https://docs.kalshi.com/getting_started/api_keys")

    if args.cmd == "balance":
        status, data = signed_request(base, args.key_id, args.key, "GET", "/portfolio/balance")
    elif args.cmd == "positions":
        status, data = signed_request(base, args.key_id, args.key, "GET", "/portfolio/positions")
    elif args.cmd == "fills":
        status, data = signed_request(base, args.key_id, args.key, "GET", "/portfolio/fills")
    elif args.cmd == "orders":
        status, data = signed_request(base, args.key_id, args.key, "GET", "/portfolio/orders")
    elif args.cmd == "settlements":
        status, data = signed_request(base, args.key_id, args.key, "GET", "/portfolio/settlements")
    elif args.cmd == "market":
        status, data = signed_request(base, args.key_id, args.key, "GET",
                                      "/markets/" + urllib.parse.quote(args.ticker))
    elif args.cmd == "orderbook":
        status, data = signed_request(base, args.key_id, args.key, "GET",
                                      "/markets/" + urllib.parse.quote(args.ticker) + "/orderbook")
    elif args.cmd == "cancel":
        status, data = signed_request(base, args.key_id, args.key, "DELETE",
                                      "/portfolio/orders/" + urllib.parse.quote(args.order_id))
    elif args.cmd == "place":
        body = {
            "ticker": args.ticker,
            "side": args.side,
            "count": args.count,
            "type": args.type,
            "time_in_force": "gtc",
        }
        if args.client_order_id:
            body["client_order_id"] = args.client_order_id
        if args.type == "limit":
            if args.price is None:
                raise SystemExit("--price is required for a limit order")
            body["yes_price"] = price_to_cents(args.price)
        status, data = signed_request(base, args.key_id, args.key, "POST",
                                      "/portfolio/orders", body=body)
        append_log({
            "placed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "base": base, "request": body, "http_status": status, "response": data,
        })
    else:
        raise SystemExit("unknown command")

    print(json.dumps(data, indent=2, sort_keys=True))
    if status >= 400:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
