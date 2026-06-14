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

export interface StreamHandlers {
  onMeeting?: (m: { id: string; title: string }) => void;
  onSegment: (s: Segment) => void;
}

// Live mode: read the NDJSON stream from POST /api/transcribe/stream and invoke
// the handlers as each finalized segment arrives (server→client push). Uses the
// fetch ReadableStream reader (a plain, dependency-free way to consume a stream).
export async function transcribeStream(
  file: File,
  handlers: StreamHandlers,
  opts: { title?: string } = {},
): Promise<void> {
  const form = new FormData();
  form.append('file', file);
  form.append('title', opts.title ?? file.name);

  const res = await fetch('/api/transcribe/stream', { method: 'POST', body: form });
  if (!res.ok || !res.body) {
    throw new Error(`Live transcription failed (HTTP ${res.status})`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      const msg = JSON.parse(line) as { type: string; meeting?: { id: string; title: string }; segment?: unknown };
      if (msg.type === 'meeting' && msg.meeting) handlers.onMeeting?.(msg.meeting);
      else if (msg.type === 'segment') handlers.onSegment(SegmentSchema.parse(msg.segment));
    }
  }
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
