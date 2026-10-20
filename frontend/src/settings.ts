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

const KEY = 'hearing.settings';

// Read stored settings, keeping each stored field that is still valid and
// falling back to its default otherwise (a renamed option never breaks the app).
export function loadSettings(): Settings {
  let stored: Record<string, unknown> = {};
  try {
    const raw = globalThis.localStorage?.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : {};
    if (parsed && typeof parsed === 'object') stored = parsed as Record<string, unknown>;
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
  const out: Record<string, unknown> = { ...DEFAULT_SETTINGS };
  for (const [name, field] of Object.entries(SettingsSchema.shape)) {
    const checked = field.safeParse(stored[name]);
    if (checked.success && name in stored) out[name] = checked.data;
  }
  return out as Settings;
}

export function saveSettings(value: Settings): void {
  try {
    globalThis.localStorage?.setItem(KEY, JSON.stringify(value));
  } catch {
    /* storage unavailable (e.g. private mode) — settings just won't persist */
  }
}
