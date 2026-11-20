/* Kalshi Demo Intelligence — browser-side authentication (demo API keys)
   Implements exactly what the official docs specify:
   headers: KALSHI-ACCESS-KEY (key id), KALSHI-ACCESS-TIMESTAMP (ms), KALSHI-ACCESS-SIGNATURE
   message = timestamp + METHOD + path-without-query
   sign: RSA keys → RSA-PSS over SHA-256 (salt = digest length); Ed25519 → raw message
   Signature base64. Timestamp must be within ±30 s of Kalshi's clock.
   Source: https://docs.kalshi.com/getting_started/quick_start_authenticated_requests.md
   Keys live ONLY in sessionStorage of the current tab and are never sent anywhere but the demo API.
*/
(function () {
  "use strict";

  const SS_KEY = "kds.kalshi.demo.key";

  function getSession() {
    try { return JSON.parse(sessionStorage.getItem(SS_KEY) || "null"); }
    catch (e) { return null; }
  }
  function setSession(keyId, pem) {
    sessionStorage.setItem(SS_KEY, JSON.stringify({ keyId: keyId.trim(), pem: pem.trim() }));
  }
  function clearSession() { sessionStorage.removeItem(SS_KEY); }

  const b64 = buf => btoa(String.fromCharCode(...new Uint8Array(buf)));

  // Minimal DER helpers: wrap a PKCS#1 (BEGIN RSA PRIVATE KEY) blob in PKCS#8 so WebCrypto can import it.
  function derLen(n) {
    if (n < 0x80) return [n];
    if (n < 0x100) return [0x81, n];
    return [0x82, n >> 8, n & 0xff];
  }
  function derSeq(bytes) {
    const head = [0x30, ...derLen(bytes.length)];
    return Uint8Array.from([...head, ...bytes]);
  }
  function pemToDer(pem) {
    const b64part = pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
    const bin = atob(b64part);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  function pkcs1ToPkcs8(der) { // RSA only
    const algId = Uint8Array.from([
      0x30, 0x0d, 0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x01, 0x01, 0x05, 0x00
    ]);
    const bitStrBody = Uint8Array.from([0x00, ...der]);
    const bitStr = Uint8Array.from([0x03, ...derLen(bitStrBody.length), ...bitStrBody]);
    const inner = Uint8Array.from([...algId, ...bitStr]);
    return derSeq(inner);
  }

  async function importKey(pem) {
    const isRSA = /BEGIN (RSA )?PRIVATE KEY/.test(pem) && !/ed25519/i.test(pem);
    const der = pemToDer(pem);
    const attempts = [];
    if (isRSA) {
      // try as PKCS#8 first, then wrap PKCS#1 → PKCS#8
      attempts.push({
        alg: { name: "RSA-PSS", hash: "SHA-256" },
        data: /BEGIN RSA PRIVATE KEY/.test(pem) ? pkcs1ToPkcs8(der) : der
      });
      if (!/BEGIN PRIVATE KEY/.test(pem)) attempts.push({ alg: { name: "RSA-PSS", hash: "SHA-256" }, data: der });
    } else {
      attempts.push({ alg: { name: "Ed25519" }, data: der });
      attempts.push({ alg: { name: "RSA-PSS", hash: "SHA-256" }, data: pkcs1ToPkcs8(der) });
      attempts.push({ alg: { name: "RSA-PSS", hash: "SHA-256" }, data: der });
    }
    let lastErr;
    for (const a of attempts) {
      try {
        return await crypto.subtle.importKey("pkcs8", a.data, a.alg, false, ["sign"]);
      } catch (e) { lastErr = e; }
    }
    throw new Error("Could not import private key (expected 'BEGIN PRIVATE KEY' (PKCS#8) or 'BEGIN RSA PRIVATE KEY'): " + (lastErr && lastErr.message));
  }

  async function signMessage(priv, message) {
    const alg = priv.algorithm.name;
    if (alg === "Ed25519") {
      const sig = await crypto.subtle.sign("Ed25519", priv, new TextEncoder().encode(message));
      return b64(sig);
    }
    // RSA-PSS, salt length = SHA-256 digest length (matches official Python example)
    const sig = await crypto.subtle.sign(
      { name: "RSA-PSS", saltLength: 32 },
      priv, new TextEncoder().encode(message)
    );
    return b64(sig);
  }

  /* Authenticated request against the demo API. path like '/portfolio/balance?limit=5' */
  async function apiAuth(path, opts) {
    opts = opts || {};
    const sess = getSession();
    if (!sess) throw new Error("No API keys loaded — add demo keys on the Trading page.");
    const priv = await importKey(sess.pem);
    const method = (opts.method || "GET").toUpperCase();
    const signPath = path.split("?")[0];           // sign without query params (official rule)
    const ts = String(Date.now());                  // milliseconds
    const message = ts + method + signPath;
    const sig = await signMessage(priv, message);
    const headers = {
      "KALSHI-ACCESS-KEY": sess.keyId,
      "KALSHI-ACCESS-TIMESTAMP": ts,
      "KALSHI-ACCESS-SIGNATURE": sig,
      "Accept": "application/json"
    };
    if (opts.body) headers["Content-Type"] = "application/json";
    const res = await fetch(KDS.API + path, {
      method, headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined
    });
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch (e) { /* keep text */ }
    if (!res.ok) {
      const err = new Error("HTTP " + res.status + " — " + (json && (json.message || json.code) || text.slice(0, 200) || res.statusText));
      err.status = res.status; err.json = json;
      throw err;
    }
    return json;
  }

  window.KAuth = { getSession, setSession, clearSession, apiAuth, importKey };
})();
