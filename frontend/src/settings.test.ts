import { beforeEach, describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS, loadSettings, saveSettings } from './settings';

class MemStore {
  m = new Map<string, string>();
  getItem(k: string) {
    return this.m.has(k) ? this.m.get(k)! : null;
  }
  setItem(k: string, v: string) {
    this.m.set(k, v);
  }
  removeItem(k: string) {
    this.m.delete(k);
  }
}

beforeEach(() => {
  (globalThis as unknown as { localStorage: MemStore }).localStorage = new MemStore();
});

describe('settings', () => {
  it('returns the (cheapest) defaults when nothing is stored', () => {
    expect(loadSettings()).toEqual(DEFAULT_SETTINGS);
    expect(DEFAULT_SETTINGS.engine).toBe('whisper');
    expect(DEFAULT_SETTINGS.aiNotes).toBe(false);
  });

  it('round-trips saved settings', () => {
    saveSettings({ ...DEFAULT_SETTINGS, engine: 'openai', aiNotes: true });
    const s = loadSettings();
    expect(s.engine).toBe('openai');
    expect(s.aiNotes).toBe(true);
    expect(s.model).toBe('base'); // untouched default preserved
  });

  it('merges partial stored JSON over defaults', () => {
    globalThis.localStorage.setItem('hearing.settings', JSON.stringify({ live: true }));
    const s = loadSettings();
    expect(s.live).toBe(true);
    expect(s.engine).toBe('whisper'); // default filled in
  });
});
