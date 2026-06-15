// Thin client for the Python HTTP layer (`hearing serve`). In dev, Vite proxies
// /api/* to http://127.0.0.1:8000 (see vite.config.ts).
//
// Note the payoff of the schema-as-contract: we parse the response with the same
// Zod schemas the UI renders from, so a mismatch between the backend and the UI
// is caught immediately instead of silently rendering wrong data.
import { z } from 'zod';
import {
  FeedbackSchema,
  MeetingSchema,
  SegmentSchema,
  type Feedback,
  type Meeting,
  type Segment,
} from './schema';

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

// Resolve the API base URL. An explicit setting always wins. Otherwise: served
// from localhost (dev / `hearing serve`) → same origin; served from a remote host
// (e.g. thorwhalen.com/hearing) → your LOCAL backend, since compute runs locally.
export function resolveApiBase(apiBase?: string): string {
  if (apiBase) return apiBase;
  if (typeof location !== 'undefined') {
    const h = location.hostname;
    if (h && h !== 'localhost' && h !== '127.0.0.1' && h !== '[::1]') {
      return 'http://localhost:8000';
    }
  }
  return '';
}

// One fetch wrapper with actionable errors (network failure / 404 = no backend).
async function backendFetch(apiBase: string | undefined, path: string, init?: RequestInit): Promise<Response> {
  const base = resolveApiBase(apiBase);
  const shown = base || (typeof location !== 'undefined' ? location.origin : '');
  let res: Response;
  try {
    res = await fetch(base + path, init);
  } catch {
    throw new Error(
      `Can't reach the backend at ${shown}. Run \`hearing serve\` on your machine, ` +
        `and check the API base URL in Settings (usually http://localhost:8000).`,
    );
  }
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(
        `No hearing backend at ${shown} (HTTP 404). The server only hosts the UI — ` +
          `run \`hearing serve\` locally and set the API base URL to http://localhost:8000 in Settings.`,
      );
    }
    throw new Error(`Backend error (HTTP ${res.status}): ${await res.text().catch(() => '')}`);
  }
  return res;
}

export interface TranscribeOpts {
  title?: string;
  summarize?: boolean;
  engine?: string;
  model?: string;
  apiBase?: string;
}

export async function transcribeFile(file: File, opts: TranscribeOpts = {}): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('title', opts.title ?? file.name);
  form.append('summarize', String(opts.summarize ?? false));
  form.append('engine', opts.engine ?? 'whisper');
  form.append('model', opts.model ?? 'base');

  const res = await backendFetch(opts.apiBase, '/api/transcribe', { method: 'POST', body: form });
  return TranscribeResponseSchema.parse(await res.json());
}

export interface StreamHandlers {
  onMeeting?: (m: { id: string; title: string }) => void;
  onSegment: (s: Segment) => void;
  onFeedback?: (f: Feedback) => void;
}

// Live mode: read the NDJSON stream from POST /api/transcribe/stream and invoke
// the handlers as each finalized segment arrives (server→client push). Uses the
// fetch ReadableStream reader (a plain, dependency-free way to consume a stream).
export async function transcribeStream(
  file: File,
  handlers: StreamHandlers,
  opts: { title?: string; engine?: string; model?: string; apiBase?: string } = {},
): Promise<void> {
  const form = new FormData();
  form.append('file', file);
  form.append('title', opts.title ?? file.name);
  form.append('engine', opts.engine ?? 'whisper');
  form.append('model', opts.model ?? 'base');

  const res = await backendFetch(opts.apiBase, '/api/transcribe/stream', { method: 'POST', body: form });
  if (!res.body) throw new Error('The backend returned no stream body.');
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
      const msg = JSON.parse(line) as {
        type: string;
        meeting?: { id: string; title: string };
        segment?: unknown;
        feedback?: unknown;
      };
      if (msg.type === 'meeting' && msg.meeting) handlers.onMeeting?.(msg.meeting);
      else if (msg.type === 'segment') handlers.onSegment(SegmentSchema.parse(msg.segment));
      else if (msg.type === 'feedback') handlers.onFeedback?.(FeedbackSchema.parse(msg.feedback));
    }
  }
}

export async function getHealth(apiBase = ''): Promise<{ status: string; version: string }> {
  const res = await backendFetch(apiBase, '/api/health');
  return res.json();
}

/** Format integer milliseconds as M:SS (for segment timestamps). */
export function clock(ms: number): string {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}
