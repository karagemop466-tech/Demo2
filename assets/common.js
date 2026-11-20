/* Shared helpers for every page: endpoints, formatting, snapshot loading, source links. */
(function (global) {
  "use strict";

  var KALSHI = {
    rest: "https://external-api.demo.kalshi.co/trade-api/v2",
    restAlt: "https://demo-api.kalshi.co/trade-api/v2",
    ws: "wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2",
    wsAlt: "wss://demo-api.kalshi.co/trade-api/ws/v2",
    site: "https://demo.kalshi.co",
    docs: {
      environments: "https://docs.kalshi.com/getting_started/api_environments",
      demo: "https://docs.kalshi.com/getting_started/demo_env",
      marketData: "https://docs.kalshi.com/getting_started/quick_start_market_data",
      auth: "https://docs.kalshi.com/getting_started/quick_start_authenticated_requests",
      createOrder: "https://docs.kalshi.com/getting_started/quick_start_create_order",
      websockets: "https://docs.kalshi.com/getting_started/quick_start_websockets",
      orderbook: "https://docs.kalshi.com/getting_started/orderbook_responses",
      lifecycle: "https://docs.kalshi.com/getting_started/market_lifecycle",
      settlement: "https://docs.kalshi.com/getting_started/market_settlement",
      fixedPoint: "https://docs.kalshi.com/getting_started/fixed_point_migration",
      orderDirection: "https://docs.kalshi.com/getting_started/order_direction",
      getMarkets: "https://docs.kalshi.com/api-reference/market/get-markets",
      getMarket: "https://docs.kalshi.com/api-reference/market/get-market",
      candlesticks: "https://docs.kalshi.com/api-reference/market/get-market-candlesticks",
      orderbookRef: "https://docs.kalshi.com/api-reference/market/get-market-orderbook",
      series: "https://docs.kalshi.com/api-reference/market/get-series",
      seriesList: "https://docs.kalshi.com/api-reference/market/get-series-list",
      events: "https://docs.kalshi.com/api-reference/events/get-events",
      balance: "https://docs.kalshi.com/api-reference/portfolio/get-balance",
      positions: "https://docs.kalshi.com/api-reference/portfolio/get-positions",
      fills: "https://docs.kalshi.com/api-reference/portfolio/get-fills",
      orders: "https://docs.kalshi.com/api-reference/orders/get-orders",
      exchangeStatus: "https://docs.kalshi.com/api-reference/exchange/get-exchange-status"
    }
  };

  var TOPICS = ["Gas prices", "Elections", "Culture", "Crypto", "Golf"];
  var TOPIC_SLUG = {
    "Gas prices": "gas",
    Elections: "elections",
    Culture: "culture",
    Crypto: "crypto",
    Golf: "golf"
  };

  function dataPrefix() {
    return /\/pages\//.test(window.location.pathname) ? "../" : "";
  }

  function fmtNum(v, dp) {
    if (v === null || v === undefined || v === "" || !isFinite(Number(v))) return "—";
    return Number(v).toLocaleString("en-US", {
      minimumFractionDigits: dp === undefined ? 0 : dp,
      maximumFractionDigits: dp === undefined ? 0 : dp
    });
  }
  function money(v, dp) {
    if (v === null || v === undefined || v === "" || !isFinite(Number(v))) return "—";
    return "$" + fmtNum(Number(v), dp === undefined ? 2 : dp);
  }
  function money0(v) { return money(v, 0); }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function pct(v, dp) {
    if (v === null || v === undefined || !isFinite(Number(v))) return "—";
    return (Number(v) * 100).toFixed(dp === undefined ? 1 : dp) + "%";
  }
  function tsHuman(ts) {
    if (!ts) return "—";
    var d = new Date(ts);
    if (isNaN(d.getTime())) return String(ts);
    return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
  }
  function topicPill(topic) {
    if (!topic) return '<span class="pill">unclassified</span>';
    return '<span class="pill ' + (TOPIC_SLUG[topic] || "") + '">' + esc(topic) + "</span>";
  }
  function marketLink(ticker, label) {
    if (!ticker) return "—";
    return '<a href="' + KALSHI.site + "/markets/" + encodeURIComponent(ticker) + '" target="_blank" rel="noopener">' +
      esc(label || ticker) + "</a>";
  }
  function apiLink(url, label) {
    return '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(label || "API") + "</a>";
  }

  /* ---- snapshot loading (files committed by .github/workflows/refresh-data.yml) ---- */
  var cache = {};
  function loadJSON(name) {
    if (cache[name]) return cache[name];
    var p = dataPrefix() + "data/" + name;
    cache[name] = fetch(p, { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status + " for " + p);
        return r.json();
      })
      .catch(function (e) {
        cache[name] = Promise.reject(e);
        return Promise.reject(e);
      });
    return cache[name];
  }

  /* ---- watchlist (localStorage) ---- */
  var WATCH_KEY = "kalshi.watchlist.v1";
  function getWatch() {
    try { return JSON.parse(localStorage.getItem(WATCH_KEY) || "[]"); } catch (e) { return []; }
  }
  function setWatch(list) {
    try { localStorage.setItem(WATCH_KEY, JSON.stringify(list)); } catch (e) {}
  }
  function toggleWatch(entry) {
    var list = getWatch();
    var i = list.findIndex(function (x) { return x.ticker === entry.ticker; });
    if (i >= 0) list.splice(i, 1); else list.push(entry);
    setWatch(list);
    return list;
  }
  function inWatch(ticker) {
    return getWatch().some(function (x) { return x.ticker === ticker; });
  }

  /* ---- local trade log (keeps fills even when the signed API is not available) ---- */
  var LOG_KEY = "kalshi.tradelog.v1";
  function getTradeLog() {
    try { return JSON.parse(localStorage.getItem(LOG_KEY) || "[]"); } catch (e) { return []; }
  }
  function addTradeLog(entry) {
    var list = getTradeLog();
    list.unshift(entry);
    try { localStorage.setItem(LOG_KEY, JSON.stringify(list.slice(0, 500))); } catch (e) {}
    return list;
  }

  /* ---- suggestion review state (localStorage) ---- */
  var SUG_KEY = "kalshi.suggestions.v1";
  function getSuggestionState() {
    try { return JSON.parse(localStorage.getItem(SUG_KEY) || "{}"); } catch (e) { return {}; }
  }
  function setSuggestionState(state) {
    try { localStorage.setItem(SUG_KEY, JSON.stringify(state)); } catch (e) {}
  }

  /* ---- topic classification (mirrors scripts/refresh-data.mjs exactly) ---- */
  var TOPIC_RULES = {
    "Gas prices": {
      category: [],
      tags: ["gas", "gasoline", "diesel", "crude", "oil", "petroleum", "fuel", "heating oil", "jet fuel", "energy"],
      titleWords: ["gas price", "gasoline", "diesel", "crude oil", "oil price", "petrol", "heating oil", "jet fuel", "refinery"]
    },
    Elections: {
      category: ["Elections"],
      tags: ["elections", "election", "primary", "polling", "republican", "democrat", "ballot"],
      titleWords: ["election", "president", "presidential", "senate", "house", "governor", "mayor", "primary", "ballot", "vote", "congress", "parliament", "referendum"]
    },
    Culture: {
      category: ["Entertainment", "Culture", "Media", "Mentions", "Awards", "Pop Culture"],
      tags: ["movies", "film", "music", "album", "tv", "television", "box office", "awards", "oscar", "grammy", "emmy", "celebrity", "entertainment", "books"],
      titleWords: ["movie", "film", "music", "album", "grammy", "oscar", "emmy", "box office", "celebrity", "actor", "actress", "singer", "tv show", "netflix", "spotify", "billboard", "met gala", "super bowl halftime"]
    },
    Crypto: {
      category: ["Crypto"],
      tags: ["crypto", "bitcoin", "btc", "ethereum", "eth", "solana", "doge", "dogecoin", "xrp", "ripple", "coin"],
      titleWords: ["bitcoin", "btc", "ethereum", "eth ", "solana", "dogecoin", "doge", "xrp", "crypto"]
    },
    Golf: {
      category: [],
      tags: ["golf", "pga", "lpga", "masters", "ryder cup", "open championship", "golf tour", "us open golf"],
      titleWords: ["golf", "pga", "lpga", "masters", "ryder cup", "open championship", "bogey", "birdie", "eagle"]
    }
  };
  function norm(v) { return String(v === null || v === undefined ? "" : v).toLowerCase(); }
  function classify(series, event, market) {
    var sCat = norm(series && series.category), eCat = norm(event && event.category);
    var sTags = ((series && series.tags) || []).map(norm);
    var sTitle = norm(series && series.title), eTitle = norm(event && event.title), mTitle = norm(market && market.title);
    for (var i = 0; i < TOPICS.length; i++) {
      var topic = TOPICS[i], rule = TOPIC_RULES[topic];
      if (rule.category.some(function (c) { return c === sCat || c === eCat; })) {
        return { topic: topic, rule: 'official category "' + ((series && series.category) || (event && event.category) || "") + '"' };
      }
      var tagHit = sTags.find(function (t) { return rule.tags.some(function (w) { return t === w || t.indexOf(w) >= 0; }); });
      if (tagHit) return { topic: topic, rule: 'official series tag "' + tagHit + '"' };
      var tHit = rule.titleWords.find(function (w) { return sTitle.indexOf(w) >= 0; });
      if (tHit) return { topic: topic, rule: 'series title contains "' + tHit + '"' };
      var eHit = rule.titleWords.find(function (w) { return eTitle.indexOf(w) >= 0; });
      if (eHit) return { topic: topic, rule: 'event title contains "' + eHit + '"' };
      var mHit = rule.titleWords.find(function (w) { return mTitle.indexOf(w) >= 0; });
      if (mHit) return { topic: topic, rule: 'market title contains "' + mHit + '"' };
    }
    return { topic: null, rule: "" };
  }

  global.K = {
    KALSHI: KALSHI, TOPICS: TOPICS, TOPIC_SLUG: TOPIC_SLUG, TOPIC_RULES: TOPIC_RULES, classify: classify,
    dataPrefix: dataPrefix, fmtNum: fmtNum, money: money, money0: money0, esc: esc, pct: pct,
    tsHuman: tsHuman, topicPill: topicPill, marketLink: marketLink, apiLink: apiLink,
    loadJSON: loadJSON, getWatch: getWatch, setWatch: setWatch, toggleWatch: toggleWatch, inWatch: inWatch,
    getTradeLog: getTradeLog, addTradeLog: addTradeLog,
    getSuggestionState: getSuggestionState, setSuggestionState: setSuggestionState
  };
})(window);
