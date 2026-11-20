/* rankings.js — Highest dollar-amount live events (focus topics), official demo API only.
   Data path: live browser fetch first, CI snapshot (data/*.json) as labelled fallback.
   Ranking metric is COMPUTED (formula shown on the page); all other fields are official. */
"use strict";
const DEMO = "https://external-api.demo.kalshi.co/trade-api/v2";
const TOPICS = ["gas prices", "elections", "culture", "crypto", "golf"];
const EVENT_PAGES = 6;      // page cap for open events (200/page)
const SETTLED_EVENT_PAGES = 4;

const state = { rows: [], resolved: [], mode: "loading", fetchedAt: "", source: "", topic: "all" };

/* ---------- helpers ---------- */
const $ = (s) => document.querySelector(s);
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = String(text);
  return n;
}
function srcLink(url, label) {
  const a = document.createElement("a");
  a.href = url; a.target = "_blank"; a.rel = "noopener";
  a.textContent = label || "API";
  return a;
}
function usd(v) { const n = Number(v); return isFinite(n) ? "$" + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : ""; }
function contracts(v) { const n = Number(v); return isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : ""; }
function when(s) { return s ? String(s).replace("T", " ").replace("Z", "") : ""; }
async function getJSON(url) {
  const r = await fetch(url, { headers: { "Accept": "application/json" } });
  if (!r.ok) throw new Error("HTTP " + r.status + " for " + url);
  return r.json();
}

/* ---------- classification (identical rules to scripts/fetch_data.py) ---------- */
function classify(ev, series) {
  const title = ((ev.title || "") + " " + (ev.sub_title || "")).toLowerCase();
  const ecat = ev.category || "";
  const out = new Set();
  if (series) {
    const st = (series.ticker || "").toUpperCase();
    const stitle = (series.title || "").toLowerCase();
    const scat = series.category || "";
    const tags = (series.tags || []).map((t) => String(t).toLowerCase());
    const scope = ((series.product_metadata || {}).scope || "").toLowerCase();
    if (st.startsWith("KXAAAGAS") || scope === "gasoline" || stitle.includes("gas price") || title.includes("gas price")) out.add("gas prices");
    if (scat === "Elections" || ecat === "Elections") out.add("elections");
    if (scat === "Culture" || ecat === "Culture") out.add("culture");
    if (scat === "Crypto" || ecat === "Crypto") out.add("crypto");
    if (tags.includes("golf") || stitle.includes("golf") || title.includes("golf")) out.add("golf");
  } else {
    if (ecat === "Elections") out.add("elections");
    if (ecat === "Culture") out.add("culture");
    if (ecat === "Crypto") out.add("crypto");
    if (title.includes("gas price")) out.add("gas prices");
    if (title.includes("golf")) out.add("golf");
  }
  return [...out];
}
const fnum = (s) => { const n = parseFloat(s); return isFinite(n) ? n : 0; };

function computeRows(events, seriesMap) {
  const per = {}; TOPICS.forEach((t) => (per[t] = []));
  for (const ev of events) {
    if ((ev.event_ticker || "").startsWith("KXMVE")) continue;
    const series = seriesMap[ev.series_ticker] || null;
    const topics = classify(ev, series);
    if (!topics.length) continue;
    let vol24 = 0, dollar24 = 0, oi = 0, best = null;
    for (const m of ev.markets || []) {
      if (!["active", "closed", "determined"].includes(m.status)) continue;
      const v = fnum(m.volume_24h_fp);
      vol24 += v; dollar24 += v * fnum(m.last_price_dollars); oi += fnum(m.open_interest_fp);
      if (!best || v > fnum(best.volume_24h_fp)) best = m;
    }
    if (vol24 <= 0 && oi <= 0) continue;
    const row = {
      event_ticker: ev.event_ticker, title: ev.title, series_ticker: ev.series_ticker,
      category: (series && series.category) || ev.category || "",
      volume_24h_contracts: vol24, open_interest_contracts: oi,
      est_dollar_volume_24h: dollar24, computed: true,
      source: DEMO + "/events?tickers=" + encodeURIComponent(ev.event_ticker) + "&with_nested_markets=true",
      lead_market: best ? {
        ticker: best.ticker, status: best.status, last_price_dollars: best.last_price_dollars,
        yes_bid_dollars: best.yes_bid_dollars, yes_ask_dollars: best.yes_ask_dollars,
        close_time: best.close_time, source: DEMO + "/markets/" + encodeURIComponent(best.ticker),
      } : null,
    };
    topics.forEach((t) => per[t].push(row));
  }
  const rows = [];
  TOPICS.forEach((t) => per[t].sort((a, b) => b.est_dollar_volume_24h - a.est_dollar_volume_24h || b.volume_24h_contracts - a.volume_24h_contracts).slice(0, 10).forEach((r, i) => rows.push({ ...r, topic: t, rank: i + 1 })));
  return rows;
}

/* ---------- live fetchers ---------- */
async function fetchSeriesMap() {
  const j = await getJSON(DEMO + "/series?include_volume=true");
  const map = {};
  for (const s of j.series || []) map[s.ticker] = s;
  return map;
}
async function fetchEvents(status, pages) {
  const out = []; let cursor = "";
  for (let i = 0; i < pages; i++) {
    const url = DEMO + "/events?limit=200&status=" + status + "&with_nested_markets=true" + (cursor ? "&cursor=" + encodeURIComponent(cursor) : "");
    const j = await getJSON(url);
    out.push(...(j.events || []));
    cursor = j.cursor || "";
    if (!cursor || !(j.events || []).length) break;
    await new Promise((r) => setTimeout(r, 350)); // stay gentle on unauthenticated limits
  }
  return out;
}
function resolvedFromEvents(events) {
  const rows = [];
  for (const ev of events) {
    for (const m of ev.markets || []) {
      if (!m.result) continue;
      rows.push({
        ticker: m.ticker, event_ticker: ev.event_ticker, event_title: ev.title,
        series_ticker: ev.series_ticker, category: ev.category || "",
        status: m.status, result: m.result, close_time: m.close_time,
        last_price_dollars: m.last_price_dollars,
        source: DEMO + "/markets/" + encodeURIComponent(m.ticker),
        event_source: DEMO + "/events/" + encodeURIComponent(ev.event_ticker),
        _ev: ev,
      });
    }
  }
  return rows;
}
function resolveTopics(rows, seriesMap) {
  rows.forEach((r) => { r.topics = classify(r._ev || { title: r.event_title, category: r.category }, seriesMap[r.series_ticker] || null); });
  return rows.filter((r) => r.topics.length);
}

/* ---------- snapshot fallbacks ---------- */
async function trySnapshot() {
  const out = {};
  try {
    const j = await getJSON("data/events_top.json");
    out.rows = TOPICS.flatMap((t) => (j.topics && j.topics[t] ? j.topics[t].map((r, i) => ({ ...r, topic: t, rank: i + 1 })) : []));
    out.fetchedAt = j.fetched_at; out.source = j.source;
  } catch (_) { /* no snapshot yet */ }
  try {
    const j = await getJSON("data/resolved.json");
    out.resolved = (j.markets || []).map((m) => ({ ...m, _ev: { title: m.event_title, category: "", series_ticker: m.series_ticker } }));
    out.resolvedAt = j.fetched_at;
  } catch (_) { /* no snapshot yet */ }
  try { out.cors = await getJSON("data/cors.json"); } catch (_) { /* optional */ }
  return out;
}

/* ---------- rendering ---------- */
function renderRanks() {
  const tb = $("#rankTable tbody"); tb.textContent = "";
  const rows = state.rows.filter((r) => state.topic === "all" || r.topic === state.topic);
  if (!rows.length) {
    const tr = el("tr"); const td = el("td", "muted", "No rows — " + (state.mode === "live" ? "no in-scope events with volume in the fetched pages." : "live fetch failed and no CI snapshot is present yet (data/events_top.json). No values are invented."));
    td.colSpan = 11; tr.appendChild(td); tb.appendChild(tr); return;
  }
  for (const r of rows) {
    const tr = el("tr");
    tr.appendChild(el("td", "", r.rank));
    const ev = el("td"); ev.appendChild(document.createTextNode(r.title || r.event_ticker || ""));
    ev.appendChild(document.createElement("br")); ev.appendChild(srcLink(r.source, r.event_ticker || "event JSON"));
    tr.appendChild(ev);
    tr.appendChild(el("td", "", r.topic));
    tr.appendChild(el("td", "", usd(r.est_dollar_volume_24h)));
    tr.appendChild(el("td", "", contracts(r.volume_24h_contracts)));
    tr.appendChild(el("td", "", contracts(r.open_interest_contracts)));
    const lm = r.lead_market;
    const lmt = el("td");
    if (lm) { lmt.appendChild(document.createTextNode(lm.ticker || "")); lmt.appendChild(document.createElement("br")); lmt.appendChild(srcLink(lm.source, "market JSON")); }
    tr.appendChild(lmt);
    tr.appendChild(el("td", "", lm ? usd(lm.last_price_dollars) : ""));
    tr.appendChild(el("td", "", lm ? ((lm.yes_bid_dollars || "") + " / " + (lm.yes_ask_dollars || "")) : ""));
    tr.appendChild(el("td", "", lm ? when(lm.close_time) : ""));
    tr.appendChild(el("td")); tr.lastChild.appendChild(srcLink(r.source, "source"));
    tb.appendChild(tr);
  }
}
function renderResolved() {
  const tb = $("#resolvedTable tbody"); tb.textContent = "";
  const rows = state.resolved.filter((r) => state.topic === "all" || (r.topics || []).includes(state.topic));
  if (!rows.length) {
    const tr = el("tr"); const td = el("td", "muted", "No resolved in-scope markets in the current window — " + (state.mode === "live" ? "none found live." : "snapshot pending (data/resolved.json)."));
    td.colSpan = 8; tr.appendChild(td); tb.appendChild(tr); return;
  }
  for (const r of rows.slice(0, 60)) {
    const tr = el("tr");
    const tk = el("td"); tk.appendChild(srcLink(r.source, r.ticker || "market")); tr.appendChild(tk);
    const ev = el("td"); ev.appendChild(document.createTextNode(r.event_title || r.event_ticker || ""));
    if (r.event_source) { ev.appendChild(document.createElement("br")); ev.appendChild(srcLink(r.event_source, "event JSON")); }
    tr.appendChild(ev);
    tr.appendChild(el("td", "", (r.topics || []).join(", ")));
    const res = el("td"); res.appendChild(el("b", r.result === "yes" ? "ok" : "", r.result || "")); tr.appendChild(res);
    tr.appendChild(el("td", "", r.status || ""));
    tr.appendChild(el("td", "", when(r.close_time)));
    tr.appendChild(el("td", "", usd(r.last_price_dollars)));
    const s = el("td"); s.appendChild(srcLink(r.source, "source")); tr.appendChild(s);
    tb.appendChild(tr);
  }
}
function status(kind, html) { const s = $("#rankStatus"); s.className = "status " + (kind || ""); s.innerHTML = html; }

async function loadLive() {
  status("", "Fetching live demo API (series + events)…");
  const seriesMap = await fetchSeriesMap();
  const events = await fetchEvents("open", EVENT_PAGES);
  state.rows = computeRows(events, seriesMap);
  const settledEvents = await fetchEvents("settled", SETTLED_EVENT_PAGES);
  state.resolved = resolveTopics(resolvedFromEvents(settledEvents), seriesMap);
  state.mode = "live"; state.fetchedAt = new Date().toISOString(); state.source = DEMO + "/events?status=open|settled&with_nested_markets=true";
  status("ok", "LIVE — " + state.rows.length + " ranked rows, " + state.resolved.length + " resolved markets. " + new Date().toLocaleTimeString());
}
async function loadSnapshot(snap) {
  state.rows = snap.rows || [];
  state.resolved = snap.resolved || [];
  state.mode = "snapshot"; state.fetchedAt = snap.fetchedAt || ""; state.source = snap.source || "data/*.json";
  status("muted", "Snapshot from CI pipeline" + (snap.fetchedAt ? " (fetched " + snap.fetchedAt + ")" : "") + " — live browser fetch unavailable. Retry with Refresh live.");
  if (snap.cors) {
    const a = (snap.cors.observed_headers || {})["access-control-allow-origin"] || "";
    $("#corsStatus").textContent = a ? "CORS probe: Access-Control-Allow-Origin = " + a + " (" + snap.cors.fetched_at + ")" : "CORS probe: no Access-Control-Allow-Origin header observed (" + snap.cors.fetched_at + ") — see data/cors.json";
  }
}
async function refresh() {
  $("#refreshBtn").disabled = true;
  try {
    await loadLive();
  } catch (e) {
    const snap = await trySnapshot();
    if (snap.rows || snap.resolved) { await loadSnapshot(snap); }
    else status("bad", "Live fetch failed (" + e.message + ") and no snapshot yet. No values are fabricated. See Flagged for Review.");
  }
  renderRanks(); renderResolved();
  $("#provenance").textContent = "Mode: " + state.mode + " · fetched_at: " + (state.fetchedAt || "—") + " · source: " + (state.source || "—") + " · rank metric is computed (formula in Method); contract volumes are official fields.";
  $("#refreshBtn").disabled = false;
}
document.addEventListener("DOMContentLoaded", () => {
  $("#refreshBtn").addEventListener("click", refresh);
  document.querySelectorAll("#topicBtns button").forEach((b) => b.addEventListener("click", () => {
    state.topic = b.dataset.topic;
    document.querySelectorAll("#topicBtns button").forEach((x) => x.classList.toggle("secondary", x !== b));
    renderRanks(); renderResolved();
  }));
  refresh();
});
