/* Kalshi Demo Dashboard — client-side only. No keys are ever sent anywhere except Kalshi demo API. */
const DEMO_REST = "https://external-api.demo.kalshi.co/trade-api/v2";
const DEMO_WS = "wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2";
const TOPICS = {
  gas: ["gas", "gasoline", "diesel", "oil price", "crude"],
  elections: ["election", "president", "senate", "house", "vote", "ballot", "governor", "mayor", "congress", "republican", "democrat", "primary"],
  culture: ["oscar", "grammy", "emmy", "celebrity", "movie", "film", "music", "album", "tv show", "super bowl halftime", "met gala"],
  crypto: ["bitcoin", "btc", "ethereum", "eth", "crypto", "doge", "solana", "xrp"],
  golf: ["golf", "pga", "masters", "us open golf", "ryder", "open championship"]
};
function topicOf(m){
  const t = ((m.title||"")+" "+(m.subtitle||"")+" "+(m.ticker||"")+" "+(m.event_ticker||"")).toLowerCase();
  for(const [k,keys] of Object.entries(TOPICS)){ if(keys.some(x=>t.includes(x))) return k; }
  return null;
}
function notional(m){ const v=parseFloat(m.volume_fp||"0"); const p=parseFloat(m.last_price_dollars||"0"); return v*p; }
async function fetchMarkets(){
  let cursor="", all=[];
  for(let i=0;i<5;i++){
    const url = DEMO_REST+"/markets?status=open&limit=1000"+(cursor?("&cursor="+encodeURIComponent(cursor)):"");
    const r = await fetch(url); if(!r.ok) throw new Error("Markets HTTP "+r.status);
    const j = await r.json(); all = all.concat(j.markets||[]);
    cursor = j.cursor||""; if(!cursor) break;
  }
  return all;
}
async function fetchOrderbook(ticker){
  const r = await fetch(DEMO_REST+"/markets/"+encodeURIComponent(ticker)+"/orderbook");
  if(!r.ok) throw new Error("Orderbook HTTP "+r.status);
  return r.json();
}
async function fetchSettled(){
  let cursor="", all=[];
  for(let i=0;i<3;i++){
    const url = DEMO_REST+"/markets?status=settled&limit=1000"+(cursor?("&cursor="+encodeURIComponent(cursor)):"");
    const r = await fetch(url); if(!r.ok) throw new Error("Settled HTTP "+r.status);
    const j = await r.json(); all = all.concat(j.markets||[]);
    cursor = j.cursor||""; if(!cursor) break;
  }
  return all.filter(m=>topicOf(m));
}
/* ---- chart ---- */
const history = {}; // ticker -> [{t, p}]
let selectedTicker = null, windowSec = 300;
function pushHistory(m){
  const p = parseFloat(m.last_price_dollars||m.yes_bid_dollars||"0");
  if(!selectedTicker || m.ticker!==selectedTicker) return;
  const now = Date.now();
  (history[m.ticker] ||= []).push({t:now,p});
  history[m.ticker] = history[m.ticker].filter(x=>now-x.t<=windowSec*1000);
}
function drawChart(){
  const c = document.getElementById("priceChart"); if(!c) return;
  const ctx = c.getContext("2d"); const W=c.width=c.clientWidth*2, H=c.height=640;
  ctx.clearRect(0,0,W,H); ctx.fillStyle="#0d1628"; ctx.fillRect(0,0,W,H);
  const pts = selectedTicker ? (history[selectedTicker]||[]) : [];
  ctx.fillStyle="#9fb0c8"; ctx.font="24px system-ui";
  if(pts.length<2){ ctx.fillText("Waiting for live ticks… select a market, then wait for polling.", 30, 60); return; }
  const minP=Math.min(...pts.map(x=>x.p)), maxP=Math.max(...pts.map(x=>x.p));
  const pad=0.02, lo=Math.max(0,minP-pad), hi=Math.min(1,maxP+pad);
  const t0=pts[0].t, t1=pts[pts.length-1].t;
  ctx.strokeStyle="#00b67a"; ctx.lineWidth=3; ctx.beginPath();
  pts.forEach((x,i)=>{ const px=60+(W-120)*(x.t-t0)/Math.max(1,(t1-t0)); const py=40+(H-120)*(1-(x.p-lo)/Math.max(0.001,(hi-lo))); i?ctx.lineTo(px,py):ctx.moveTo(px,py); });
  ctx.stroke();
  ctx.fillStyle="#e8eef7"; ctx.fillText("Y: contract price $"+lo.toFixed(3)+" – $"+hi.toFixed(3), 60, 30);
  ctx.fillText("X: time (window "+windowSec+"s)  last $"+pts[pts.length-1].p.toFixed(3), 60, H-30);
}
/* ---- render ---- */
let liveMarkets=[];
async function refresh(){
  const el=document.getElementById("liveStatus"); if(el) el.textContent="Fetching demo markets…";
  try{
    const all = await fetchMarkets();
    liveMarkets = all.filter(m=>topicOf(m)).sort((a,b)=>notional(b)-notional(a));
    if(el) el.innerHTML="<span class='ok'>Live:</span> "+liveMarkets.length+" in-scope open markets (of "+all.length+" open). Updated "+new Date().toLocaleTimeString();
    renderTable(liveMarkets.slice(0,50));
    if(liveMarkets.length && !selectedTicker){ selectedTicker=liveMarkets[0].ticker; document.getElementById("tickerInput").value=selectedTicker; }
    liveMarkets.forEach(pushHistory); drawChart();
  }catch(e){
    if(el) el.innerHTML="<span class='bad'>Live fetch failed:</span> "+e.message+" — check network/CORS. No values are fabricated; tables stay empty until the API responds. See Flagged for Review.";
  }
}
function renderTable(rows){
  const tb=document.querySelector("#marketsTable tbody"); if(!tb) return;
  tb.innerHTML = rows.map(m=>{
    const topic=topicOf(m);
    return "<tr><td><button class='secondary' data-t='"+m.ticker+"'>Chart</button></td><td>"+m.ticker+"</td><td>"+(m.title||"")+"</td><td><span class='pill'>"+topic+"</span></td><td>$"+(m.last_price_dollars||"—")+"</td><td>"+(m.volume_fp||"—")+"</td><td>$"+notional(m).toFixed(2)+"</td><td>"+(m.yes_bid_dollars||"—")+" / "+(m.yes_ask_dollars||"—")+"</td><td>"+(m.close_time||"—")+"</td></tr>";
  }).join("");
  tb.querySelectorAll("button[data-t]").forEach(b=>b.onclick=()=>{ selectedTicker=b.dataset.t; document.getElementById("tickerInput").value=selectedTicker; loadOrderbook(); drawChart(); });
}
async function loadOrderbook(){
  const t = document.getElementById("tickerInput").value.trim(); if(!t) return;
  const box=document.getElementById("orderbookBox"); box.textContent="Loading orderbook…";
  try{
    const j = await fetchOrderbook(t);
    const yes=(j.orderbook_fp&&j.orderbook_fp.yes_dollars)||[], no=(j.orderbook_fp&&j.orderbook_fp.no_dollars)||[];
    box.innerHTML="<h4>YES bids (price → contracts)</h4><table><tr><th>Price</th><th>Contracts</th></tr>"+yes.slice(-10).reverse().map(r=>"<tr><td>$"+r[0]+"</td><td>"+r[1]+"</td></tr>").join("")+"</table><h4>NO bids</h4><table><tr><th>Price</th><th>Contracts</th></tr>"+no.slice(-10).reverse().map(r=>"<tr><td>$"+r[0]+"</td><td>"+r[1]+"</td></tr>").join("")+"</table>";
  }catch(e){ box.innerHTML="<span class='bad'>Orderbook failed:</span> "+e.message; }
}
/* Authenticated account access and order submission are intentionally omitted from this public static client. */
async function loadResolved(){
  const tb=document.querySelector("#resolvedTable tbody"); if(!tb) return;
  try{
    const rows=(await fetchSettled()).slice(0,50);
    tb.innerHTML=rows.map(m=>"<tr><td>"+m.ticker+"</td><td>"+(m.title||"")+"</td><td><span class='pill'>"+topicOf(m)+"</span></td><td>"+(m.result||"—")+"</td><td>"+(m.settlement_value_dollars||"—")+"</td><td>"+(m.settlement_ts||"—")+"</td></tr>").join("")||"<tr><td colspan='6'>No settled in-scope markets in latest page.</td></tr>";
  }catch(e){ tb.innerHTML="<tr><td colspan='6'><span class='bad'>Failed:</span> "+e.message+"</td></tr>"; }
}
/* WS ticker (best-effort) */
function connectWS(){
  try{
    const ws=new WebSocket(DEMO_WS);
    ws.onopen=()=>{ const el=document.getElementById("wsStatus"); if(el) el.innerHTML="<span class='ok'>WS connected</span>"; };
    ws.onmessage=(ev)=>{ try{ const m=JSON.parse(ev.data); if(m.type==="ticker"&&m.payload&&selectedTicker&&m.payload.market_ticker===selectedTicker){ const p=parseFloat(m.payload.yes_bid_dollars||"0"); (history[selectedTicker]||=[]).push({t:Date.now(),p}); drawChart(); } }catch(e){} };
    ws.onerror=()=>{ const el=document.getElementById("wsStatus"); if(el) el.innerHTML="<span class='warn'>WS unavailable — REST polling continues.</span>"; };
  }catch(e){}
}
document.addEventListener("DOMContentLoaded",()=>{
  const r=document.getElementById("refreshBtn"); if(r) r.onclick=refresh;
  const o=document.getElementById("loadObBtn"); if(o) o.onclick=loadOrderbook;
  const p=document.getElementById("loadPortBtn"); if(p) p.onclick=loadPortfolio;
  const po=document.getElementById("placeOrderBtn"); if(po) po.onclick=placeOrder;
  const w=document.getElementById("windowSel"); if(w) w.onchange=()=>{ windowSec=parseInt(w.value,10); drawChart(); };
  const t=document.getElementById("tickerInput"); if(t) t.onchange=()=>{ selectedTicker=t.value.trim(); loadOrderbook(); drawChart(); };
  refresh(); connectWS(); loadResolved();
  setInterval(refresh,15000);
});
