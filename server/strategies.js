// Trade categorization and strategy suggestion engine.
// Categorization uses only fields available from Kalshi (ticker, side, price,
// count, status, timestamps). Strategy ideas are PROPOSED for review in the
// Suggestions section and are NOT auto-applied (per requirements).

// Map a market/event title or ticker to one of the five allowed topics.
// This is a best-effort, reviewable mapping; the exact category->topic mapping is
// flagged as unverified in docs/QUESTIONS_AND_ANSWERS.md (Q6).
const TOPIC_KEYWORDS = {
  gas: ['gas', 'gasoline', 'fuel', 'oil', 'energy', 'crude', 'natgas', 'natural gas'],
  elections: ['election', 'vote', 'candidate', 'poll', 'president', 'senate', 'congress'],
  culture: ['culture', 'film', 'movie', 'music', 'award', 'oscar', 'grammy', 'tv', 'show'],
  crypto: ['crypto', 'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'coin', 'cryptocurrency'],
  golf: ['golf', 'pga', 'masters', 'open championship', 'ryder'],
};

export function categorizeTopic(text = '') {
  const t = text.toLowerCase();
  const hits = Object.entries(TOPIC_KEYWORDS)
    .map(([topic, kws]) => [topic, kws.some((k) => t.includes(k))])
    .filter(([, hit]) => hit)
    .map(([topic]) => topic);
  return hits[0] || 'other';
}

// Classify a single trade into a strategy-type bucket based on verified fields.
export function classifyTrade(trade) {
  const topic = trade.topic || categorizeTopic(`${trade.title || ''} ${trade.ticker || ''}`);
  const side = trade.side || trade.outcome_side || 'unknown'; // yes / no
  const horizon = trade.horizon || inferHorizon(trade);
  const entryPrice = num(trade.price);
  const type = trade.type || inferType(side, horizon, trade);
  return { ...trade, topic, side, horizon, type, entryPrice };
}

function num(v) {
  const n = typeof v === 'number' ? v : parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

function inferHorizon(trade) {
  if (!trade.ts || !trade.resolved_ts) return 'open';
  const days = (new Date(trade.resolved_ts) - new Date(trade.ts)) / 86400000;
  if (days < 1) return 'intraday';
  if (days < 7) return 'short';
  return 'long';
}

function inferType(side, horizon, trade) {
  if (!side || side === 'unknown') return 'directional';
  if (horizon === 'intraday') return `${side}-momentum`;
  return `${side}-hold`;
}

// Aggregate trades by category to compute simple performance stats.
export function aggregatePerformance(trades) {
  const by = (key) => {
    const groups = {};
    for (const t of trades) {
      const k = t[key] || 'unknown';
      if (!groups[k]) groups[k] = { count: 0, invested: 0, returned: 0, wins: 0 };
      const inv = num(t.cost) ?? num(t.price) ?? 0;
      const ret = num(t.payout) ?? num(t.settle_value) ?? 0;
      groups[k].count += 1;
      groups[k].invested += inv;
      groups[k].returned += ret;
      if (ret > inv) groups[k].wins += 1;
    }
    return groups;
  };
  const totals = { count: trades.length, invested: 0, returned: 0, wins: 0 };
  for (const t of trades) {
    const inv = num(t.cost) ?? 0;
    const ret = num(t.payout) ?? num(t.settle_value) ?? 0;
    totals.invested += inv;
    totals.returned += ret;
    if (ret > inv) totals.wins += 1;
  }
  totals.pnl = totals.returned - totals.invested;
  totals.winRate = totals.count ? totals.wins / totals.count : 0;
  return { totals, byTopic: by('topic'), byType: by('type'), bySide: by('side'), byHorizon: by('horizon') };
}

// Produce strategy SUGGESTIONS (not applied) from the categorized trades.
export function suggestStrategies(trades) {
  const perf = aggregatePerformance(trades);
  const suggestions = [];
  for (const [topic, g] of Object.entries(perf.byTopic)) {
    const winRate = g.count ? g.wins / g.count : 0;
    if (g.count >= 2) {
      suggestions.push({
        id: `strat-${topic}`,
        title: `Focus on ${topic} markets`,
        rationale: `${g.count} trades in ${topic}, win rate ${(winRate * 100).toFixed(0)}%, P&L $${(g.returned - g.invested).toFixed(2)}.`,
        action: winRate >= 0.5 ? 'Consider increasing allocation to this topic.' : 'Review entries; consider tightening entry price.',
        status: 'proposed',
        priority: winRate >= 0.5 ? 'High' : 'Medium',
      });
    }
  }
  // Best-performing type
  let best = null;
  for (const [type, g] of Object.entries(perf.byType)) {
    if (!best || (g.count ? g.wins / g.count : 0) > best.winRate) {
      best = { type, ...g, winRate: g.count ? g.wins / g.count : 0 };
    }
  }
  if (best && best.count >= 2) {
    suggestions.push({
      id: `strat-besttype`,
      title: `Replicate the "${best.type}" pattern`,
      rationale: `Best win rate (${(best.winRate * 100).toFixed(0)}%) across ${best.count} trades.`,
      action: 'Document the entry rules for this trade type and review before scaling.',
      status: 'proposed',
      priority: 'High',
    });
  }
  return suggestions;
}
