/* Portfolio tabulator — runs entirely in the browser on a file you choose.
 * It never calls the Kalshi API, never asks for a key, and never uploads anything.
 *
 * Input: a JSON array (or {"fills":[...]}) of fill records shaped like Kalshi's
 * authenticated /portfolio/fills response. Fields used:
 *   ticker, side | taker_outcome_side, yes_price | yes_price_dollars,
 *   count | count_fp, created_time, action (buy|sell, optional), fee_cost (optional)
 * If a field is absent the row is still counted but the affected statistic is left blank.
 */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const TOPIC_BY_PREFIX = [
    ["KXAAAGAS", "gas"], ["KXPGATOUR", "golf"], ["KXPGAM", "golf"], ["KXGOLF", "golf"],
    ["KXBTC", "crypto"], ["KXETH", "crypto"], ["KXSOL", "crypto"], ["KXXRP", "crypto"], ["KXDOGE", "crypto"],
    ["KXPRESPERSON", "elections"], ["KXSENATE", "elections"], ["KXHOUSE", "elections"],
    ["KXUNDER", "elections"], ["KXNCSEN", "elections"], ["KXHFC", "elections"], ["HOUSENY", "elections"],
    ["KXXBANNED", "culture"], ["KXOSCAR", "culture"], ["KXGRAMMY", "culture"],
  ];

  function num(v) {
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function classify(f) {
    const side = (f.taker_outcome_side || f.side || f.outcome_side || "").toLowerCase() || null;
    const price = num(f.yes_price_dollars) !== null ? num(f.yes_price_dollars)
      : num(f.yes_price) !== null ? num(f.yes_price) / 100 : null;
    const contracts = num(f.count_fp) !== null ? num(f.count_fp) : num(f.count);
    let band = "unknown";
    if (price !== null) {
      if (price < 0.2) band = "0.00–0.19 (long shot)";
      else if (price < 0.4) band = "0.20–0.39";
      else if (price < 0.6) band = "0.40–0.59 (coin flip)";
      else if (price < 0.8) band = "0.60–0.79";
      else band = "0.80–1.00 (heavy favourite)";
    }
    const t = String(f.ticker || "").toUpperCase();
    const topic = (TOPIC_BY_PREFIX.find(([p]) => t.startsWith(p)) || [null, "other"])[1];
    const mode = t.startsWith("KXMVE") ? "multi-leg (MVE)" : "single market";
    const action = (f.action || "").toLowerCase() || (side === "no" ? "buy NO" : "buy YES");
    const fee = num(f.fee_cost) !== null ? num(f.fee_cost) / 100 : num(f.fee_dollars);
    return {
      ticker: f.ticker || "(no ticker)", side, price, contracts, band, topic, mode, action,
      created: f.created_time || null, fee,
      notional: price !== null && contracts !== null ? price * contracts : null,
    };
  }

  function table(title, map, cols) {
    const keys = Object.keys(map).sort();
    if (!keys.length) return "";
    let html = `<h4 style="margin:16px 0 6px">${title}</h4><div class="tablewrap"><table><thead><tr><th>Category</th>${cols.map((c) => `<th class="num">${c[1]}</th>`).join("")}</tr></thead><tbody>`;
    keys.forEach((k) => {
      const rows = map[k];
      html += `<tr><td>${k}</td>${cols.map((c) => `<td class="num">${c[0](rows)}</td>`).join("")}</tr>`;
    });
    html += "</tbody></table></div>";
    return html;
  }

  function group(rows, key) {
    const m = {};
    rows.forEach((r) => { (m[r[key]] = m[r[key]] || []).push(r); });
    return m;
  }

  const n = (rs) => rs.length;
  const avg = (rs, f) => {
    const v = rs.map(f).filter((x) => x !== null && x !== undefined && Number.isFinite(x));
    return v.length ? (v.reduce((a, b) => a + b, 0) / v.length) : "—";
  };
  const money = (v) => (typeof v === "number" ? "$" + v.toFixed(2) : "—");
  const num2 = (v) => (typeof v === "number" ? v.toFixed(2) : "—");

  function render(fills) {
    const out = $("fillsOut");
    if (!Array.isArray(fills) || !fills.length) {
      out.innerHTML = '<p class="empty">No fill records found in that file.</p>';
      return;
    }
    const rows = fills.map(classify);
    const totalNotional = rows.reduce((a, r) => a + (r.notional || 0), 0);
    const totalFees = rows.filter((r) => r.fee !== null).reduce((a, r) => a + r.fee, 0);
    const missing = {
      price: rows.filter((r) => r.price === null).length,
      contracts: rows.filter((r) => r.contracts === null).length,
      side: rows.filter((r) => !r.side).length,
      fee: rows.filter((r) => r.fee === null).length,
    };
    let html = `<div class="grid c3" style="margin:10px 0">
      <div class="kpi"><div class="label">Fills</div><div class="value">${rows.length}</div><div class="sub">${new Set(rows.map((r) => r.ticker)).size} distinct markets</div></div>
      <div class="kpi"><div class="label">Notional traded</div><div class="value">${money(totalNotional)}</div><div class="sub">price × contracts, sum over rows</div></div>
      <div class="kpi"><div class="label">Fees recorded</div><div class="value">${money(totalFees)}</div><div class="sub">${missing.fee} rows had no fee field</div></div>
    </div>`;

    if (missing.price || missing.contracts || missing.side) {
      html += `<div class="notice warn"><h4>Some rows are incomplete</h4>
        price missing in ${missing.price}, contracts missing in ${missing.contracts}, side missing in ${missing.side}.
        Those rows are counted but the affected averages are computed only over rows that carry the field.</div>`;
    }

    html += table("By price band (where the trade sat on the probability curve)", group(rows, "band"),
      [[n, "Fills"], [(rs) => num2(avg(rs, (r) => r.contracts)), "Avg contracts"], [(rs) => money(avg(rs, (r) => r.notional)), "Avg notional"]]);
    html += table("By topic", group(rows, "topic"),
      [[n, "Fills"], [(rs) => money(avg(rs, (r) => r.notional)), "Avg notional"]]);
    html += table("By side (YES / NO)", group(rows, "side"),
      [[n, "Fills"], [(rs) => money(avg(rs, (r) => r.notional)), "Avg notional"]]);
    html += table("By mode", group(rows, "mode"), [[n, "Fills"]]);

    html += `<h4 style="margin:16px 0 6px">Every fill</h4>
      <div class="tablewrap"><table><thead><tr><th>Ticker</th><th>Side</th><th class="num">Price</th><th class="num">Contracts</th><th class="num">Notional</th><th>Band</th><th>Topic</th><th>Mode</th><th class="num">Fee</th><th>Time</th></tr></thead><tbody>`;
    rows.forEach((r) => {
      html += `<tr><td class="tick">${r.ticker}</td><td>${r.side || "—"}</td>
        <td class="num">${r.price === null ? "—" : "$" + r.price.toFixed(4)}</td>
        <td class="num">${r.contracts === null ? "—" : r.contracts}</td>
        <td class="num">${money(r.notional)}</td><td class="small">${r.band}</td>
        <td class="small">${r.topic}</td><td class="small">${r.mode}</td>
        <td class="num">${r.fee === null ? "—" : "$" + r.fee.toFixed(2)}</td>
        <td class="small">${r.created || "—"}</td></tr>`;
    });
    html += "</tbody></table></div>";

    html += `<div class="notice"><h4>What this does not tell you</h4>
      Realised P&amp;L needs the settlement result of each market and the fee actually charged. This tabulator computes
      <b>exposure</b> (price × contracts) and groups it; it does not claim a profit. Fees are shown only where the file
      carries them. The Kalshi fee schedule is at
      <a href="https://kalshi.com/docs/kalshi-fee-schedule.pdf" target="_blank" rel="noopener">kalshi.com/docs/kalshi-fee-schedule.pdf</a>.</div>`;
    out.innerHTML = html;
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!$("fillsFile")) return;
    $("fillsFile").addEventListener("change", (ev) => {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const j = JSON.parse(reader.result);
          render(Array.isArray(j) ? j : (j.fills || []));
        } catch (e) {
          $("fillsOut").innerHTML = `<p class="empty">That file is not valid JSON: ${e.message}. Nothing is guessed from a file that cannot be parsed.</p>`;
        }
      };
      reader.readAsText(f);
    });
    $("demoShape").addEventListener("click", () => {
      $("fillsOut").innerHTML = `<h4>Expected shape</h4>
        <pre class="small" style="background:#f6f8fb;border:1px solid #dde4ec;border-radius:8px;padding:10px;overflow:auto">{
  "fills": [
    {
      "ticker": "KXAAAGASDTN-26NOV20-T280",
      "side": "yes",
      "yes_price": 42,
      "count": 10,
      "created_time": "2026-11-20T14:02:11Z",
      "action": "buy",
      "fee_cost": 12
    }
  ]
}</pre>
        <p class="small muted">Prices may be given in cents (<code>yes_price</code>) or dollars (<code>yes_price_dollars</code>);
        contracts as <code>count</code> or <code>count_fp</code>. Fees as cents (<code>fee_cost</code>) or dollars (<code>fee_dollars</code>).
        Any field you leave out is reported as missing rather than assumed.</p>`;
    });
  });
})();
