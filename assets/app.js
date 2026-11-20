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
/* ---- auth (WebCrypto) ---- */
function b64ToBytes(b64){ const bin=atob(b64.replace(/\s/g,"")); const a=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++)a[i]=bin.charCodeAt(i); return a; }
function bytesToB64(buf){ let s=""; const a=new Uint8Array(buf); a.forEach(b=>s+=String.fromCharCode(b)); return btoa(s); }
async function importKey(pem){
  const der = b64ToBytes(pem.replace(/-----BEGIN [^-]+-----/g,"").replace(/-----END [^-]+-----/g,""));
  try{ return {key: await crypto.subtle.importKey("pkcs8",der,{name:"Ed25519"},false,["sign"]), alg:"Ed25519"}; }
  catch(e){ return {key: await crypto.subtle.importKey("pkcs8",der,{name:"RSA-PSS",hash:"SHA-256"},false,["sign"]), alg:"RSA-PSS"}; }
}
async function signedFetch(path, method, body){
  const keyId=document.getElementById("apiKeyId").value.trim();
  const pem=document.getElementById("apiPrivateKey").value;
  if(!keyId||!pem) throw new Error("Enter demo API Key ID + private key (stored only in this browser).");
  const {key,alg}=await importKey(pem);
  const ts=String(Date.now());
  const signPath="/trade-api/v2"+path.split("?")[0];
  const msg=new TextEncoder().encode(ts+method+signPath);
  const sig = alg==="Ed25519" ? await crypto.subtle.sign("Ed25519",key,msg) : await crypto.subtle.sign({name:"RSA-PSS",saltLength:32},key,msg);
  const r=await fetch(DEMO_REST+path,{method,headers:{"KALSHI-ACCESS-KEY":keyId,"KALSHI-ACCESS-TIMESTAMP":ts,"KALSHI-ACCESS-SIGNATURE":bytesToB64(sig),"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
  const j=await r.json().catch(()=>({}));
  if(!r.ok) throw new Error("HTTP "+r.status+": "+JSON.stringify(j));
  return j;
}
async function loadPortfolio(){
  const box=document.getElementById("portfolioBox"); if(!box) return;
  try{
    const bal=await signedFetch("/portfolio/balance","GET");
    const pos=await signedFetch("/portfolio/positions?limit=100","GET");
    const fills=await signedFetch("/portfolio/fills?limit=100","GET");
    box.innerHTML="<p>Balance (cents): "+bal.balance+" → $"+(bal.balance/100).toFixed(2)+"</p><p>Positions: "+(pos.market_positions||[]).length+" · Fills: "+(fills.fills||[]).length+"</p>"+analyzeFills(fills.fills||[]);
    window._fills=fills.fills||[];
  }catch(e){ box.innerHTML="<span class='warn'>Portfolio unavailable:</span> "+e.message; }
}
function analyzeFills(fills){
  if(!fills.length) return "<p class='muted'>No fills yet. Place a demo order to generate data.</p>";
  const byTopic={}, bySide={yes:0,no:0};
  fills.forEach(f=>{ const k=topicOf({title:f.ticker||"",ticker:f.ticker||""})||"other"; byTopic[k]=(byTopic[k]||0)+1; if(f.side) bySide[f.side]=(bySide[f.side]||0)+1; });
  return "<table><tr><th>Category</th><th>Count</th></tr>"+Object.entries(byTopic).map(([k,v])=>"<tr><td>"+k+"</td><td>"+v+"</td></tr>").join("")+"</table><p>Side split: YES "+(bySide.yes||0)+" · NO "+(bySide.no||0)+"</p><p class='muted'>Strategies are derived only from observed fills — see Analysis page. No strategy is recommended without data.</p>";
}
async function placeOrder(){
  const out=document.getElementById("orderResult");
  try{
    const ticker=document.getElementById("orderTicker").value.trim();
    const side=document.getElementById("orderSide").value;
    const count=parseInt(document.getElementById("orderCount").value,10);
    const price=parseFloat(document.getElementById("orderPrice").value);
    if(!ticker||!count||!price) throw new Error("Fill ticker, count, and price.");
    const j=await signedFetch("/portfolio/orders","POST",{ticker,side,count,yes_price:Math.round(price*100),type:"limit",time_in_force:"gtc"});
    out.innerHTML="<span class='ok'>Order accepted:</span> "+JSON.stringify(j).slice(0,500);
    loadPortfolio();
  }catch(e){ out.innerHTML="<span class='bad'>Order failed:</span> "+e.message; }
}
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
