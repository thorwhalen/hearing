// Command-dispatch layer (acture pattern), hand-written — no acture-* dependency.
//
// Each operation is defined ONCE as a Command: it becomes a command-palette
// entry, a keyboard shortcut, and (via toAITools) an AI/MCP tool schema. The
// `params` Zod schema is the single source of truth for both the palette's
// choices and the AI tool's input schema. This mirrors acture's "define once,
// project everywhere" idea (see the hearing-frontend skill).
import { z } from 'zod';
import { clock, type TranscribeResponse } from './api';
import { type Segment } from './schema';

// What a command can touch. Kept tiny and explicit (a frontend novice can read
// exactly what each command may do).
export interface CommandContext {
  result: TranscribeResponse | null;
  focusSearch: () => void;
  clear: () => void;
}

export interface Command {
  id: string;
  title: string;
  hotkey?: string; // e.g. "e" — fired when the palette is open and focused
  aiDescription: string; // projected into the AI/MCP tool description
  params?: z.ZodObject<z.ZodRawShape>;
  run: (args: Record<string, unknown>, ctx: CommandContext) => void;
}

// ---- transcript export formatters (pure — unit-tested) ---------------------
export function transcriptToMarkdown(segments: Segment[]): string {
  const lines = ['# Transcript', ''];
  for (const s of segments) {
    lines.push(`- **${s.speaker}** [${clock(s.startMs)}] ${s.text.trim()}`);
  }
  return lines.join('\n') + '\n';
}

export function transcriptToJson(segments: Segment[]): string {
  return JSON.stringify(segments, null, 2);
}

function srtTime(ms: number): string {
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  const millis = ms % 1000;
  const p = (n: number, w = 2) => n.toString().padStart(w, '0');
  return `${p(h)}:${p(m)}:${p(s)},${p(millis, 3)}`;
}

export function transcriptToSrt(segments: Segment[]): string {
  return (
    segments
      .map((s, i) => `${i + 1}\n${srtTime(s.startMs)} --> ${srtTime(s.endMs)}\n${s.speaker}: ${s.text.trim()}`)
      .join('\n\n') + '\n'
  );
}

const EXPORTERS: Record<string, { ext: string; mime: string; render: (s: Segment[]) => string }> = {
  markdown: { ext: 'md', mime: 'text/markdown', render: transcriptToMarkdown },
  srt: { ext: 'srt', mime: 'application/x-subrip', render: transcriptToSrt },
  json: { ext: 'json', mime: 'application/json', render: transcriptToJson },
};

// Browser-only side effect (guarded so tests can import the formatters safely).
function download(filename: string, content: string, mime: string): void {
  if (typeof document === 'undefined') return;
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ---- the command registry --------------------------------------------------
export function buildCommands(): Command[] {
  return [
    {
      id: 'transcript.export',
      title: 'Export transcript',
      aiDescription: 'Export the current meeting transcript as markdown, SRT subtitles, or JSON.',
      params: z.object({
        format: z.enum(['markdown', 'srt', 'json']).describe('Output format'),
      }),
      run: (args, ctx) => {
        if (!ctx.result) return;
        const fmt = (args.format as string) ?? 'markdown';
        const e = EXPORTERS[fmt] ?? EXPORTERS.markdown;
        download(`transcript.${e.ext}`, e.render(ctx.result.segments), e.mime);
      },
    },
    {
      id: 'transcript.search',
      title: 'Search transcript',
      hotkey: 'f',
      aiDescription: 'Focus the transcript search box.',
      run: (_args, ctx) => ctx.focusSearch(),
    },
    {
      id: 'transcript.clear',
      title: 'Clear transcript',
      aiDescription: 'Clear the current transcript and feedback from the view.',
      run: (_args, ctx) => ctx.clear(),
    },
  ];
}

// A flat list of selectable palette rows. A command whose params have a single
// enum field expands into one row per value (e.g. Export → markdown/srt/json);
// otherwise it's one row. The palette stays dumb; this is where params → rows.
export interface PaletteEntry {
  id: string;
  label: string;
  command: Command;
  args: Record<string, unknown>;
}

function firstEnumField(params: z.ZodObject<z.ZodRawShape>): { name: string; values: string[] } | null {
  for (const [name, field] of Object.entries(params.shape)) {
    if (field instanceof z.ZodEnum) {
      return { name, values: (field as z.ZodEnum).options as string[] };
    }
  }
  return null;
}

export function paletteEntries(commands: Command[]): PaletteEntry[] {
  const out: PaletteEntry[] = [];
  for (const c of commands) {
    const enumField = c.params ? firstEnumField(c.params) : null;
    if (enumField) {
      for (const v of enumField.values) {
        out.push({ id: `${c.id}:${v}`, label: `${c.title} — ${v}`, command: c, args: { [enumField.name]: v } });
      }
    } else {
      out.push({ id: c.id, label: c.title, command: c, args: {} });
    }
  }
  return out;
}

// Project commands to AI/MCP tool definitions — the acture payoff: the same
// command that powers the palette is also the AI tool. The params Zod schema
// becomes the tool's input schema (Zod v4 `toJSONSchema`).
export function toAITools(commands: Command[]) {
  return commands.map((c) => ({
    name: c.id,
    description: c.aiDescription,
    inputSchema: c.params ? z.toJSONSchema(c.params) : { type: 'object', properties: {} },
  }));
}
