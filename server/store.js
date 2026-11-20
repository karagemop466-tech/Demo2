// Persisted tracking store: watched events, their resolution, executed trades,
// and price snapshots. Survives restarts via a JSON file in DATA_DIR.
import fs from 'fs';
import path from 'path';
import { DATA_DIR } from './config.js';

const STORE_PATH = path.join(DATA_DIR, 'store.json');

function nowIso() {
  return new Date().toISOString();
}

const DEFAULT_STATE = {
  trackedEvents: {}, // event_ticker -> { event_ticker, title, topic, status, resolution, close_ts, settled_ts, added_at, updated_at, last_seen }
  trades: [], // executed trade records
  snapshots: [], // { ts, ticker, price, topic }
  suggestions: [], // user decisions on suggestions
};

class Store {
  constructor() {
    this.state = structuredClone(DEFAULT_STATE);
    this._saveTimer = null;
    this._load();
  }

  _load() {
    try {
      if (fs.existsSync(STORE_PATH)) {
        const raw = fs.readFileSync(STORE_PATH, 'utf8');
        const parsed = JSON.parse(raw);
        this.state = { ...structuredClone(DEFAULT_STATE), ...parsed };
      }
    } catch (err) {
      console.warn(`[store] failed to load store: ${err.message}`);
    }
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }

  _scheduleSave() {
    if (this._saveTimer) return;
    this._saveTimer = setTimeout(() => {
      this._saveTimer = null;
      try {
        fs.writeFileSync(STORE_PATH, JSON.stringify(this.state, null, 2));
      } catch (err) {
        console.warn(`[store] failed to save store: ${err.message}`);
      }
    }, 250);
  }

  // --- Events ---
  trackEvent({ event_ticker, title, topic, status, close_ts, settled_ts }) {
    const existing = this.state.trackedEvents[event_ticker] || {};
    const next = {
      ...existing,
      event_ticker,
      title,
      topic,
      status,
      close_ts: close_ts ?? existing.close_ts,
      settled_ts: settled_ts ?? existing.settled_ts,
      added_at: existing.added_at || nowIso(),
      updated_at: nowIso(),
      last_seen: nowIso(),
    };
    this.state.trackedEvents[event_ticker] = next;
    this._scheduleSave();
    return next;
  }

  updateEvent(event_ticker, patch) {
    const existing = this.state.trackedEvents[event_ticker];
    if (!existing) return null;
    const next = { ...existing, ...patch, updated_at: nowIso(), last_seen: nowIso() };
    // If now settled, record resolution.
    if (patch.status === 'settled' && !existing.resolution) {
      next.resolution = patch.resolution || this._inferResolution(patch);
      next.resolution_ts = nowIso();
    }
    this.state.trackedEvents[event_ticker] = next;
    this._scheduleSave();
    return next;
  }

  _inferResolution(market) {
    // Best-effort only; marked unverified unless confirmed from a live settled market.
    if (!market) return null;
    return null;
  }

  listTrackedEvents() {
    return Object.values(this.state.trackedEvents).sort((a, b) =>
      (a.settled_ts || a.close_ts || 0) < (b.settled_ts || b.close_ts || 0) ? 1 : -1,
    );
  }

  // --- Trades ---
  recordTrade(trade) {
    const record = { id: `T${Date.now()}-${Math.floor(Math.random() * 1000)}`, ts: nowIso(), ...trade };
    this.state.trades.push(record);
    this._scheduleSave();
    return record;
  }

  listTrades() {
    return [...this.state.trades].sort((a, b) => (a.ts < b.ts ? 1 : -1));
  }

  // --- Snapshots (price history ring buffer) ---
  pushSnapshot(snap) {
    this.state.snapshots.push({ ts: Date.now(), ...snap });
    // Keep a bounded history (e.g., 10k points).
    if (this.state.snapshots.length > 10000) {
      this.state.snapshots = this.state.snapshots.slice(-10000);
    }
    this._scheduleSave();
  }

  snapshotsFor(ticker, limit = 500) {
    return this.state.snapshots
      .filter((s) => s.ticker === ticker)
      .slice(-limit);
  }

  // --- Suggestion decisions ---
  upsertSuggestionDecision({ id, status, note, decidedBy, decidedAt }) {
    const existing = this.state.suggestions.find((s) => s.id === id) || { id };
    const next = {
      ...existing,
      status,
      note,
      decidedBy,
      decidedAt: decidedAt || nowIso(),
    };
    const idx = this.state.suggestions.findIndex((s) => s.id === id);
    if (idx >= 0) this.state.suggestions[idx] = next;
    else this.state.suggestions.push(next);
    this._scheduleSave();
    return next;
  }

  getSuggestionDecisions() {
    return this.state.suggestions;
  }
}

export const store = new Store();
