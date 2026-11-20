(function(){
const API = "https://external-api.demo.kalshi.co/trade-api/v2";
const $ = id => document.getElementById(id);
let timer = null, samples = [], current = null;
const fmt = v => (v===null||v===undefined||v==="") ? "–" : Number(v).toFixed(4);
const num = v => (v===null||v===undefined||v==="") ? null : Number(v);
function tickerNow(){ return ($("tickerTxt").value.trim() || $("tickerSel").value).toUpperCase(); }
function setStatus(msg, cls){ $("statusLine").textContent = msg; $("statusLine").style.color = cls||""; }
async function getJSON(url){
  const r = await fetch(url, {headers:{"Accept":"application/json"}});
  if(!r.ok) throw new Error("HTTP "+r.status);
  return r.json();
}
function drawChart(){
  const c = $("chart"), g = c.getContext("2d");
  const W = c.width, H = c.height, pad = {l:60,r:20,t:20,b:40};
  g.clearRect(0,0,W,H);
  const winSec = Number($("windowSel").value);
  const now = Date.now(), t0 = now - winSec*1000;
  const pts = samples.filter(s => s.t >= t0);
  g.fillStyle="#fff"; g.fillRect(0,0,W,H);
  // y grid 0..1
  g.font="12px system-ui"; g.strokeStyle="#d8dee4"; g.fillStyle="#59636e";
  for(let i=0;i<=5;i++){
    const y = pad.t + (H-pad.t-pad.b)*(1-i/5);
    g.beginPath(); g.moveTo(pad.l,y); g.lineTo(W-pad.r,y); g.stroke();
    g.fillText((i/5).toFixed(2), 8, y+4);
  }
  // x ticks (time)
  for(let i=0;i<=5;i++){
    const t = t0 + (now-t0)*i/5;
    const x = pad.l + (W-pad.l-pad.r)*i/5;
    const d = new Date(t);
    const label = winSec<=300 ? d.toLocaleTimeString() : d.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
    g.fillText(label, x-30, H-14);
  }
  const X = t => pad.l + (W-pad.l-pad.r)*((t-t0)/(now-t0));
  const Y = p => pad.t + (H-pad.t-pad.b)*(1-p);
  const series = [["last","#0969da"],["bid","#1a7f37"],["ask","#cf222e"]];
  series.forEach(([k,col])=>{
    g.strokeStyle=col; g.lineWidth=2; g.beginPath(); let started=false;
    pts.forEach(s=>{ const v=s[k]; if(v===null) return; const x=X(s.t), y=Y(v); if(!started){g.moveTo(x,y);started=true;} else g.lineTo(x,y); });
    g.stroke();
  });
  // legend
  g.fillStyle="#0969da"; g.fillText("last price",pad.l,14);
  g.fillStyle="#1a7f37"; g.fillText("yes bid",pad.l+90,14);
  g.fillStyle="#cf222e"; g.fillText("yes ask",pad.l+160,14);
  g.fillStyle="#59636e"; g.fillText("Y = contract price ($), X = time", W-260, 14);
}
function renderBook(bodyId, levels){
  const body = $(bodyId);
  if(!levels || !levels.length){ body.innerHTML = '<tr><td colspan="3">No resting orders at the requested depth.</td></tr>'; return; }
  let cum = 0; body.innerHTML = levels.map(([p,q])=>{ cum += Number(q); return `<tr><td>${Number(p).toFixed(4)}</td><td>${Number(q).toFixed(2)}</td><td>${cum.toFixed(2)}</td></tr>`; }).join("");
}
async function poll(){
  const t = tickerNow();
  try{
    const m = (await getJSON(`${API}/markets/${encodeURIComponent(t)}`)).market;
    const b = await getJSON(`${API}/markets/${encodeURIComponent(t)}/orderbook?depth=10`);
    const ob = b.orderbook_fp || {yes_dollars:[], no_dollars:[]};
    const now = Date.now();
    samples.push({t:now, last:num(m.last_price_dollars), bid:num(m.yes_bid_dollars), ask:num(m.yes_ask_dollars)});
    if(samples.length>5000) samples = samples.slice(-5000);
    $("kLast").textContent = fmt(m.last_price_dollars);
    $("kBid").textContent = fmt(m.yes_bid_dollars);
    $("kAsk").textContent = fmt(m.yes_ask_dollars);
    $("kVol").textContent = m.volume_fp ?? "–";
    $("kOi").textContent = m.open_interest_fp ?? "–";
    $("kStatus").textContent = m.status ?? "–";
    // yes bids: ascending, best last -> show best first
    renderBook("bidsBody", (ob.yes_dollars||[]).slice().reverse());
    // yes asks derived from no bids: ask price = 1 - no bid price
    const asks = (ob.no_dollars||[]).slice().reverse().map(([p,q])=>[(1-Number(p)).toFixed(4), q]);
    renderBook("asksBody", asks);
    setStatus(`Updated ${new Date(now).toLocaleTimeString()} from ${API} (demo data).`);
    drawChart();
  }catch(err){
    $("kStatus").textContent = "error";
    setStatus(`Could not reach the Kalshi demo API from this browser (${err.message}). Status unverified: the request may be blocked by CORS or the network, or the ticker may be wrong.`, "#cf222e");
  }
}
function start(){
  stop();
  const reset = tickerNow() !== current; if(reset){ samples = []; current = tickerNow(); }
  poll();
  timer = setInterval(poll, Number($("pollSel").value));
  setStatus("Running…");
}
function stop(){ if(timer){ clearInterval(timer); timer=null; setStatus("Stopped."); } }
$("startBtn").addEventListener("click", start);
$("stopBtn").addEventListener("click", stop);
$("windowSel").addEventListener("change", drawChart);
$("tickerSel").addEventListener("change", ()=>{ $("tickerTxt").value=""; });
drawChart();
})();
