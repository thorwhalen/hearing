// User settings, persisted in the browser (localStorage). Defaults are the
// LEAST expensive options — local on-device STT, no AI, no API calls — so the
// app does something useful out of the box with nothing configured. Turn the
// paid/AI features on here when you want them.
export interface Settings {
  engine: 'whisper' | 'openai'; // whisper = local/free; openai = cloud (needs key)
  model: string; // local whisper model size
  aiNotes: boolean; // Claude summary/actions (needs ANTHROPIC_API_KEY)
  live: boolean; // stream finalized segments as they arrive
  apiBase: string; // '' = same origin; e.g. 'http://localhost:8000' for local compute
}

export const DEFAULT_SETTINGS: Settings = {
  engine: 'whisper',
  model: 'base',
  aiNotes: false,
  live: false,
  apiBase: '',
};

const KEY = 'hearing.settings';

export function loadSettings(): Settings {
  try {
    const raw = globalThis.localStorage?.getItem(KEY);
    return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : { ...DEFAULT_SETTINGS };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function saveSettings(settings: Settings): void {
  try {
    globalThis.localStorage?.setItem(KEY, JSON.stringify(settings));
  } catch {
    /* storage unavailable (e.g. private mode) — settings just won't persist */
  }
}
