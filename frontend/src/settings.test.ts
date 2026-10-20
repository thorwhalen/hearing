import { beforeEach, describe, expect, it } from 'vitest';
import type { DataProvider } from '@zodal/store';
import {
  DEFAULT_SETTINGS,
  SETTINGS_ID,
  STORAGE_KEY,
  createSettingsStore,
  loadSettings,
  saveSettings,
} from './settings';

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
  it('returns the (cheapest) defaults when nothing is stored', async () => {
    expect(await loadSettings()).toEqual(DEFAULT_SETTINGS);
    expect(DEFAULT_SETTINGS.engine).toBe('whisper');
    expect(DEFAULT_SETTINGS.aiNotes).toBe(false);
  });

  it('round-trips saved settings through the zodal localStorage provider', async () => {
    await saveSettings({ ...DEFAULT_SETTINGS, engine: 'openai', aiNotes: true });
    expect(globalThis.localStorage.getItem(STORAGE_KEY)).toContain(SETTINGS_ID);
    const s = await loadSettings();
    expect(s.engine).toBe('openai');
    expect(s.aiNotes).toBe(true);
    expect(s.model).toBe('base'); // untouched default preserved
    await saveSettings({ ...s, live: true }); // a second save updates the one record
    expect((await loadSettings()).live).toBe(true);
  });

  it('starts from settings an earlier version stored, merged over defaults', async () => {
    globalThis.localStorage.setItem('hearing.settings', JSON.stringify({ live: true }));
    const s = await loadSettings();
    expect(s.live).toBe(true);
    expect(s.engine).toBe('whisper'); // default filled in
  });

  it('works with any DataProvider (swap the backend by swapping the provider)', async () => {
    const records = new Map<string, Record<string, unknown>>();
    const provider = {
      async getOne(id: string) {
        if (!records.has(id)) throw new Error('not found');
        return records.get(id);
      },
      async upsert(data: Record<string, unknown>) {
        records.set(data.id as string, data);
        return data;
      },
    } as unknown as DataProvider<never>;
    const store = createSettingsStore(provider);
    expect(await store.load()).toEqual(DEFAULT_SETTINGS);
    await store.save({ ...DEFAULT_SETTINGS, model: 'small' });
    expect(records.get(SETTINGS_ID)?.model).toBe('small');
    expect((await store.load()).model).toBe('small');
    expect(globalThis.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

describe('settings schema', () => {
  it('drops stored values the schema no longer accepts', async () => {
    globalThis.localStorage.setItem('hearing.settings', JSON.stringify({ engine: 'gone', model: 'small', live: 'yes' }));
    const s = await loadSettings();
    expect(s.engine).toBe('whisper');
    expect(s.model).toBe('small');
    expect(s.live).toBe(false);
  });
});
