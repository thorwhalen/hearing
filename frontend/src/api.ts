// Thin client for the Python HTTP layer (`hearing serve`). In dev, Vite proxies
// /api/* to http://127.0.0.1:8000 (see vite.config.ts).
//
// Note the payoff of the schema-as-contract: we parse the response with the same
// Zod schemas the UI renders from, so a mismatch between the backend and the UI
// is caught immediately instead of silently rendering wrong data.
import { z } from 'zod';
import { MeetingSchema, SegmentSchema, type Meeting, type Segment } from './schema';

const TranscribeResponseSchema = z.object({
  meeting: MeetingSchema,
  segments: z.array(SegmentSchema),
  summary: z.string().optional(),
});

export interface TranscribeResponse {
  meeting: Meeting;
  segments: Segment[];
  summary?: string;
}

export async function transcribeFile(
  file: File,
  opts: { title?: string; summarize?: boolean } = {},
): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('title', opts.title ?? file.name);
  form.append('summarize', String(opts.summarize ?? false));

  const res = await fetch('/api/transcribe', { method: 'POST', body: form });
  if (!res.ok) {
    throw new Error(`Transcription failed (HTTP ${res.status}): ${await res.text()}`);
  }
  return TranscribeResponseSchema.parse(await res.json());
}

export async function getHealth(): Promise<{ status: string; version: string }> {
  const res = await fetch('/api/health');
  if (!res.ok) throw new Error(`Health check failed (HTTP ${res.status})`);
  return res.json();
}

/** Format integer milliseconds as M:SS (for segment timestamps). */
export function clock(ms: number): string {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}
