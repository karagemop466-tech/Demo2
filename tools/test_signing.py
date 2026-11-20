#!/usr/bin/env python3
"""Offline verification of the Kalshi request-signing implementation.

No network access and no Kalshi account are needed: this test generates a
throw-away Ed25519 key and a throw-away RSA key with openssl, signs a message
built exactly the way the official specification describes, and verifies the
signature with the matching public key.

Specification under test:
  https://docs.kalshi.com/getting_started/api_keys
  https://docs.kalshi.com/getting_started/quick_start_authenticated_requests

  message = <timestamp in ms> <HTTP METHOD> <path without query parameters>
  Ed25519 -> sign the message directly
  RSA     -> RSA-PSS, SHA-256, MGF1-SHA-256, salt length = digest length
  signature -> base64

Run:  python3 tools/test_signing.py
"""

import base64
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kalshi_trade as kt  # noqa: E402

FAILURES = []


def check(name, ok, detail=""):
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL", (" — " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)


def make_key(tmp, kind):
    pem = os.path.join(tmp, kind + ".pem")
    if kind == "ed25519":
        subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-out", pem], check=True,
                       capture_output=True)
    else:
        subprocess.run(["openssl", "genpkey", "-algorithm", "RSA",
                        "-pkeyopt", "rsa_keygen_bits:2048", "-out", pem], check=True,
                       capture_output=True)
    return pem


def public_key(pem, tmp):
    pub = os.path.join(tmp, "pub.pem")
    subprocess.run(["openssl", "pkey", "-in", pem, "-pubout", "-out", pub], check=True,
                   capture_output=True)
    return pub


def verify_ed25519(pub, message, sig_b64):
    sig = base64.b64decode(sig_b64)
    tmpdir = tempfile.mkdtemp()
    try:
        mfile = os.path.join(tmpdir, "m.bin")
        sfile = os.path.join(tmpdir, "s.bin")
        with open(mfile, "wb") as fh:
            fh.write(message)
        with open(sfile, "wb") as fh:
            fh.write(sig)
        proc = subprocess.run(["openssl", "pkeyutl", "-verify", "-rawin", "-pubin",
                               "-inkey", pub, "-sigfile", sfile, "-in", mfile],
                              capture_output=True)
        return proc.returncode == 0, proc.stderr.decode("utf-8", "replace").strip()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def verify_rsa(pub, message, sig_b64):
    sig = base64.b64decode(sig_b64)
    proc = subprocess.run(
        ["openssl", "dgst", "-sha256",
         "-sigopt", "rsa_padding_mode:pss",
         "-sigopt", "rsa_pss_saltlen:digest",
         "-verify", pub],
        input=message, capture_output=True)
    # dgst -verify reads the signature from stdin, so pass message then sig is not possible;
    # use a temporary file instead.
    tmpdir = tempfile.mkdtemp()
    try:
        mfile = os.path.join(tmpdir, "m.bin")
        sfile = os.path.join(tmpdir, "s.bin")
        with open(mfile, "wb") as fh:
            fh.write(message)
        with open(sfile, "wb") as fh:
            fh.write(sig)
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256",
             "-sigopt", "rsa_padding_mode:pss",
             "-sigopt", "rsa_pss_saltlen:digest",
             "-verify", pub, "-signature", sfile, mfile],
            capture_output=True)
        return proc.returncode == 0, proc.stderr.decode("utf-8", "replace").strip()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    if shutil.which("openssl") is None:
        print("openssl is required for this test")
        return 1
    tmp = tempfile.mkdtemp(prefix="kalshi-sign-test-")
    try:
        ts = "1763640000000"
        method = "GET"
        path = "/trade-api/v2/portfolio/balance"
        message = (ts + method + path).encode("utf-8")

        # Ed25519 ------------------------------------------------------------
        ed_pem = make_key(tmp, "ed25519")
        ed_pub = public_key(ed_pem, tmp)
        check("key type detection: ed25519", kt.key_kind(ed_pem) == "ed25519")
        sig = kt.sign(ed_pem, message)
        ok, err = verify_ed25519(ed_pub, message, sig)
        check("ed25519 signature verifies against the public key", ok, err)
        check("ed25519 signature is base64 of 64 bytes",
              len(base64.b64decode(sig)) == 64)

        # RSA-PSS ------------------------------------------------------------
        rsa_pem = make_key(tmp, "rsa")
        rsa_pub = public_key(rsa_pem, tmp)
        check("key type detection: rsa", kt.key_kind(rsa_pem) == "rsa")
        sig2 = kt.sign(rsa_pem, message)
        ok2, err2 = verify_rsa(rsa_pub, message, sig2)
        check("rsa-pss signature verifies against the public key", ok2, err2)
        check("rsa-pss signature is 256 bytes", len(base64.b64decode(sig2)) == 256)

        # A signature over a different message must not verify.
        bad = kt.sign(ed_pem, (ts + method + path + "x").encode("utf-8"))
        ok3, _ = verify_ed25519(ed_pub, message, bad)
        check("a signature over a different message does not verify", not ok3)

        # Price conversion ----------------------------------------------------
        check("price 0.42 -> 42 cents", kt.price_to_cents("0.42") == 42)
        check("price 0.07 -> 7 cents", kt.price_to_cents("0.07") == 7)
        check("price 1.00 -> 100 cents", kt.price_to_cents("1.00") == 100)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("FAILED: " + ", ".join(FAILURES))
        return 1
    print("All signing checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
