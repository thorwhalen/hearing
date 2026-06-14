import { describe, expect, it } from 'vitest';
import {
  buildCommands,
  paletteEntries,
  toAITools,
  transcriptToJson,
  transcriptToMarkdown,
  transcriptToSrt,
} from './commands';
import { type Segment } from './schema';

const segs: Segment[] = [
  { id: '1', meetingId: 'm', speaker: 'me', side: 'me', channel: 'mic', startMs: 0, endMs: 1500, text: 'Hello there', isFinal: true },
  { id: '2', meetingId: 'm', speaker: 'them', side: 'them', channel: 'system', startMs: 1500, endMs: 3000, text: 'Hi back', isFinal: true },
];

describe('export formatters', () => {
  it('markdown includes speakers and timestamps', () => {
    const md = transcriptToMarkdown(segs);
    expect(md).toContain('# Transcript');
    expect(md).toContain('**me**');
    expect(md).toContain('Hello there');
  });

  it('srt has sequence numbers and arrow timestamps', () => {
    const srt = transcriptToSrt(segs);
    expect(srt).toContain('1\n00:00:00,000 --> 00:00:01,500');
    expect(srt).toContain('them: Hi back');
  });

  it('json round-trips the segments', () => {
    expect(JSON.parse(transcriptToJson(segs))).toHaveLength(2);
  });
});

describe('command registry (acture pattern)', () => {
  it('export expands into one palette row per format', () => {
    const rows = paletteEntries(buildCommands()).filter((e) => e.command.id === 'transcript.export');
    expect(rows.map((e) => e.args.format).sort()).toEqual(['json', 'markdown', 'srt']);
  });

  it('non-parameterized commands are a single palette row', () => {
    const rows = paletteEntries(buildCommands()).filter((e) => e.command.id === 'transcript.search');
    expect(rows).toHaveLength(1);
  });

  it('projects commands to AI/MCP tools with input schemas', () => {
    const tools = toAITools(buildCommands());
    const exp = tools.find((t) => t.name === 'transcript.export');
    expect(exp).toBeTruthy();
    expect(exp!.description).toMatch(/export/i);
    expect(JSON.stringify(exp!.inputSchema)).toContain('format'); // params -> tool schema
  });
});
