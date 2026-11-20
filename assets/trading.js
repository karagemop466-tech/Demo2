/* Kalshi Demo Intelligence — Trading page logic (Create Order V2 + account views) */
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const fmtP = KDS.fmtPrice, fmtI = KDS.fmtInt, esc = KDS.esc;

  function keyState() {
    const s = KAuth.getSession();
    $("keyStatus").innerHTML = s
      ? '<span class="badge live">🔑 keys loaded — key id <b>' + esc(s.keyId.slice(0, 8)) + "…" + "</b> (session only)</span>"
      : '<span class="badge flag">no API keys — authenticated calls disabled (see Q1)</span>';
    $("keyDelBtn").style.display = s ? "" : "none";
    document.querySelectorAll(".authOnly").forEach(el => el.disabled = !s);
  }

  function renderResponse(obj) {
    $("orderResp").style.display = "";
    $("orderResp").innerHTML = "<b>Server response (verbatim):</b><pre class='mono' style='white-space:pre-wrap'>" + esc(JSON.stringify(obj, null, 2)) + "</pre>";
  }

  async function submitOrder() {
    const body = {
      ticker: $("ordTicker").value.trim(),
      side: $("ordSide").value,                      // V2 single-book: bid | ask
      count: $("ordCount").value.trim(),             // FixedPointCount "10.00"
      price: $("ordPrice").value.trim(),             // FixedPointDollars "0.5600"
      time_in_force: $("ordTif").value,
      self_trade_prevention_type: $("ordStp").value
    };
    if ($("ordPostOnly").checked) body.post_only = true;
    if ($("ordExp").value.trim()) {
      body.expiration_time = Number($("ordExp").value.trim());
      if (body.time_in_force === "immediate_or_cancel") body.time_in_force = "good_till_canceled";
    }
    $("orderErr").style.display = "none";
    $("submitBtn").disabled = true;
    try {
      const j = await KAuth.apiAuth("/portfolio/events/orders", { method: "POST", body });
      renderResponse(j);
      $("orderNote").innerHTML = '<span class="okbox">Order accepted. <b>201 means accepted, not resting</b> — <code>remaining_count</code> shows how much rests: ' +
        "fill_count=" + esc(String(j.fill_count)) + ", remaining_count=" + esc(String(j.remaining_count)) + ".</span>";
    } catch (e) {
      $("orderErr").style.display = "block";
      $("orderErr").innerHTML = "<b>Order not placed:</b> " + esc(e.message) +
        (e.status === 410 ? "<br>Legacy <code>/portfolio/orders</code> is gone — this page already uses V2 (<code>POST /portfolio/events/orders</code>)." : "");
    } finally { $("submitBtn").disabled = false; }
  }

  async function loadAccount() {
    $("acctNote").innerHTML = '<span class="spin"></span> fetching balance / positions / fills…';
    try {
      const [bal, pos, fills] = await Promise.all([
        KAuth.apiAuth("/portfolio/balance"),
        KAuth.apiAuth("/portfolio/positions?count_filter=position&settlement_status=all&limit=200"),
        KAuth.apiAuth("/portfolio/fills?limit=200")
      ]);
      $("balCard").innerHTML =
        '<div class="stat"><div class="label">Available balance</div><div class="value">' + fmtP(bal.balance_dollars) + '</div><div class="note">field balance_dollars · balance=' + esc(String(bal.balance)) + " cents</div></div>" +
        '<div class="stat"><div class="label">Portfolio value</div><div class="value">' + fmtP((bal.portfolio_value / 100).toFixed(4)) + '</div><div class="note">portfolio_value=' + esc(String(bal.portfolio_value)) + " cents · updated " + KDS.fmtEpoch(bal.updated_ts) + 'Z</div></div>' +
        '<div class="stat"><div class="label">Fills loaded</div><div class="value">' + (fills.fills || []).length + '</div><div class="note">GET /portfolio/fills</div></div>' +
        '<div class="stat"><div class="label">Positions</div><div class="value">' + (pos.market_positions || []).length + '</div><div class="note">GET /portfolio/positions</div></div>';

      $("posBody").innerHTML = (pos.market_positions || []).map(p =>
        `<tr><td class="mono">${esc(p.ticker)}</td>
         <td class="num">${fmtI(p.position_fp)}</td>
         <td class="num">${fmtP(p.total_traded_dollars)}</td>
         <td class="num">${fmtP(p.market_exposure_dollars)}</td>
         <td class="num" style="color:${KDS.num(p.realized_pnl_dollars) > 0 ? "#2dd4a7" : KDS.num(p.realized_pnl_dollars) < 0 ? "#ff6b6b" : "inherit"}">${fmtP(p.realized_pnl_dollars)}</td>
         <td class="num">${fmtP(p.fees_paid_dollars)}</td>
         <td class="num">${KDS.fmtTs(p.last_updated_ts)}</td>
         <td><a class="src-link" href="${KDS.API}/markets/${encodeURIComponent(p.ticker)}" target="_blank" rel="noopener">market</a></td></tr>`).join("") ||
        '<tr><td colspan="8" class="note">no positions</td></tr>';

      $("fillsBody").innerHTML = (fills.fills || []).map(f =>
        `<tr><td class="num">${KDS.fmtTs(f.created_time)}</td>
         <td class="mono">${esc(f.ticker)}</td>
         <td><span class="pill ${f.outcome_side === "yes" ? "yes" : "no"}">${esc(f.outcome_side || "—")}</span> <span class="pill">${esc(f.book_side || "—")}</span></td>
         <td class="num">${fmtI(f.count_fp)}</td>
         <td class="num">${fmtP(f.yes_price_dollars)}</td>
         <td class="num">${fmtP(f.no_price_dollars)}</td>
         <td>${f.is_taker ? "taker" : "maker"}</td>
         <td class="num">${fmtP(f.fee_cost)}</td>
         <td><a class="src-link" href="${KDS.API}/portfolio/fills?ticker=${encodeURIComponent(f.ticker)}" target="_blank" rel="noopener">source</a></td></tr>`).join("") ||
        '<tr><td colspan="9" class="note">no fills</td></tr>';
      $("acctNote").innerHTML = '<span class="badge live">account data loaded from live demo API</span>';
    } catch (e) {
      $("acctNote").innerHTML = '<span class="badge err">' + esc(e.message) + "</span>" +
        (e.status === 401 ? ' <span class="note">401 — check that the key was created on <b>demo.kalshi.co</b> (demo keys ≠ production keys) and your clock is within ±30 s.</span>' : "");
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    KDS.setModeBadge(document.getElementById("modeBadge"));
    keyState();
    $("saveKeyBtn").addEventListener("click", () => {
      const id = $("keyId").value, pem = $("pem").value;
      if (!id || !pem) { alert("Enter both API Key ID and private key PEM."); return; }
      KAuth.setSession(id, pem);
      $("keyId").value = ""; $("pem").value = "";
      keyState();
    });
    $("keyDelBtn").addEventListener("click", () => { KAuth.clearSession(); keyState(); });
    $("submitBtn").addEventListener("click", submitOrder);
    $("loadAcctBtn").addEventListener("click", loadAccount);
    // demo fill helpers
    $("fillFromChart")?.addEventListener("click", () => {
      const t = sessionStorage.getItem("kds.lastTicker");
      if (t) $("ordTicker").value = t;
    });
    if (sessionStorage.getItem("kds.lastTicker")) $("ordTicker").value = sessionStorage.getItem("kds.lastTicker");
  });
})();
