/* Kalshi Demo Intelligence — Trading page logic (V2 request builder + signed curl export)
   Security: this file never handles private keys. Signing happens wherever the
   user runs the exported command (their machine / official docs playground).
*/
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const esc = KDS.esc;

  function buildBody() {
    const body = {
      ticker: $("ordTicker").value.trim(),
      side: $("ordSide").value,
      count: $("ordCount").value.trim(),
      price: $("ordPrice").value.trim(),
      time_in_force: $("ordTif").value,
      self_trade_prevention_type: $("ordStp").value
    };
    if ($("ordPostOnly").checked) body.post_only = true;
    if ($("ordExp").value.trim()) {
      body.expiration_time = Number($("ordExp").value.trim());
      if (body.time_in_force === "immediate_or_cancel") body.time_in_force = "good_till_canceled";
    }
    return body;
  }

  function curlFor(body) {
    const path = "/trade-api/v2/portfolio/events/orders";
    return [
      "# Requires: openssl + curl; export KALSHI_ACCESS_KEY and KALSHI_PRIVATE_KEY (file path) locally.",
      "# Signing per official spec: message = ms_timestamp + \"POST\" + path (no query), RSA-PSS SHA-256, salt = 32, base64.",
      "TS=$(date +%s%3N)",
      `MSG="${'"'}${'$'}{TS}POST${path}${'"'}`,
      `SIG=$(printf '%s' "${'$'}{MSG}" | openssl dgst -sha256 -sigopt rsa_padding_mode:pss -sigopt rsa_pss_saltlen:32 -sign "${'$'}{KALSHI_PRIVATE_KEY}" | openssl base64 -A)`,
      "curl -sS -X POST 'https://external-api.demo.kalshi.co/trade-api/v2/portfolio/events/orders' \\",
      "  -H 'Content-Type: application/json' \\",
      "  -H \"KALSHI-ACCESS-KEY: ${KALSHI_ACCESS_KEY}\" \\",
      "  -H \"KALSHI-ACCESS-TIMESTAMP: ${TS}\" \\",
      "  -H \"KALSHI-ACCESS-SIGNATURE: ${SIG}\" \\",
      "  -d '" + JSON.stringify(body) + "'",
      "",
      "# Expected on success: 201 { order_id, client_order_id?, fill_count, remaining_count, ts_ms }",
      "# (201 = accepted; check remaining_count for what rests. Source: docs create-order-v2)"
    ].join("\n");
  }

  window.addEventListener("DOMContentLoaded", () => {
    KDS.setModeBadge(document.getElementById("modeBadge"));
    $("buildBtn").addEventListener("click", () => {
      const body = buildBody();
      if (!body.ticker) { alert("Market ticker is required."); return; }
      $("bodyOut").textContent = JSON.stringify(body, null, 2);
      $("curlOut").textContent = curlFor(body);
    });
    $("fillFromChart")?.addEventListener("click", () => {
      try {
        const t = sessionStorage.getItem("kds.lastTicker");
        if (t) { $("ordTicker").value = t; return; }
      } catch (e) {}
      alert("Open the dashboard and select a market first.");
    });
    try {
      const t = sessionStorage.getItem("kds.lastTicker");
      if (t) $("ordTicker").value = t;
    } catch (e) {}
  });
})();
