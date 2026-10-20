// User settings, persisted in the browser (localStorage). Defaults are the
// LEAST expensive options — local on-device STT, no AI, no API calls — so the
// app does something useful out of the box with nothing configured. Turn the
// paid/AI features on here when you want them.
//
// For a frontend novice: `SettingsSchema` is the single source of truth. The
// `Settings` type, the defaults, the validation of what is stored, and the
// Settings form (rendered field by field by @zodal/ui-shadcn, see
// components/SchemaForm.tsx) are all derived from it. A new setting is one new
// line in the schema plus, if wanted, a label and help text in `settings`.
import { z } from 'zod';
import { defineCollection } from '@zodal/core';
import type { DataProvider } from '@zodal/store';
import { createLocalStorageProvider } from '@zodal/store-localstorage';

export const WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large-v3'] as const;

export const SettingsSchema = z.object({
  engine: z.enum(['whisper', 'openai']).default('whisper'), // whisper = local/free; openai = cloud (needs key)
  model: z.enum(WHISPER_MODELS).default('base'), // local whisper model size
  aiNotes: z.boolean().default(false), // Claude summary/actions (needs ANTHROPIC_API_KEY)
  live: z.boolean().default(false), // stream finalized segments as they arrive
  apiBase: z.string().default(''), // '' = same origin; e.g. 'http://localhost:8000' for local compute
});
export type Settings = z.infer<typeof SettingsSchema>;

export const DEFAULT_SETTINGS: Settings = SettingsSchema.parse({});

// The schema as a zodal collection: the labels and help texts the form shows.
export const settings = defineCollection(SettingsSchema, {
  fields: {
    engine: { title: 'STT engine', description: 'whisper runs locally for free; openai is a cloud service and needs a key.' },
    model: { title: 'Whisper model', description: 'Larger is more accurate and slower. Used by the whisper engine only.' },
    aiNotes: { title: 'AI notes', description: 'A Claude summary and action items (needs an API key).' },
    live: { title: 'Live stream', description: 'Segments appear as they finalize.' },
    apiBase: {
      title: 'API base URL',
      description: 'Leave blank for the same origin. Set to http://localhost:8000 to run compute on your own machine while the UI is hosted elsewhere.',
    },
  },
});

// Where settings live: any zodal DataProvider. The default keeps them in this
// browser (localStorage); moving them to a server is passing another provider
// (e.g. @zodal/store-http) to createSettingsStore, with no other change.
// The settings are one record, with id SETTINGS_ID, in that provider.
export const SETTINGS_ID = 'settings';
export const STORAGE_KEY = 'hearing.settings.store';
const LEGACY_KEY = 'hearing.settings'; // the plain-object format before the store

type SettingsRecord = Settings & { id: string };

export interface SettingsStore {
  load(): Promise<Settings>;
  save(value: Settings): Promise<void>;
}

// Keep each stored field that is still valid and fall back to its default
// otherwise (a renamed option never breaks the app).
export function sanitizeSettings(stored: unknown): Settings {
  const record = stored && typeof stored === 'object' ? (stored as Record<string, unknown>) : {};
  const out: Record<string, unknown> = { ...DEFAULT_SETTINGS };
  for (const [name, field] of Object.entries(SettingsSchema.shape)) {
    const checked = field.safeParse(record[name]);
    if (checked.success && name in record) out[name] = checked.data;
  }
  return out as Settings;
}

// Settings stored by earlier versions (one JSON object under LEGACY_KEY), if any.
function readLegacySettings(): unknown {
  try {
    const raw = globalThis.localStorage?.getItem(LEGACY_KEY);
    return raw ? JSON.parse(raw) : undefined;
  } catch {
    return undefined;
  }
}

export function createSettingsStore(
  provider: DataProvider<SettingsRecord> = createLocalStorageProvider<SettingsRecord>({
    storageKey: STORAGE_KEY,
  }),
): SettingsStore {
  return {
    async load() {
      try {
        return sanitizeSettings(await provider.getOne(SETTINGS_ID));
      } catch {
        // Nothing stored yet (or storage unavailable): start from what an earlier
        // version stored, else the defaults.
        return sanitizeSettings(readLegacySettings());
      }
    },
    async save(value) {
      const record = { ...value, id: SETTINGS_ID };
      try {
        if (provider.upsert) await provider.upsert(record);
        else
          await provider.update(SETTINGS_ID, record).catch(() => provider.create(record));
      } catch {
        /* storage unavailable (e.g. private mode): settings just won't persist */
      }
    },
  };
}

// The app's store. Tests and other hosts make their own with createSettingsStore.
export const settingsStore: SettingsStore = createSettingsStore();
export const loadSettings = (): Promise<Settings> => settingsStore.load();
export const saveSettings = (value: Settings): Promise<void> => settingsStore.save(value);
