// The single source of truth for the UI's data shapes.
//
// For a frontend novice: we declare each "collection" once as a Zod schema, and
// `@zodal/core`'s defineCollection() *infers* the UI affordances from it — which
// fields are searchable, which are visible, which are large "content" that
// belongs in object storage vs. small queryable "metadata". We never hand-list
// columns; we read them off the collection. The same schemas validate every API
// response (see api.ts), so the Python backend and this UI share one contract.
import { z } from 'zod';
import { defineCollection } from '@zodal/core';

// One transcript segment — the row the transcript view renders.
// Time is integer milliseconds (never floats) — mirrors hearing/types.py.
export const SegmentSchema = z.object({
  id: z.string(),
  meetingId: z.string(),
  speaker: z.string(), // diarization label, e.g. "me" / "them" / "spk_0"
  side: z.enum(['me', 'them']), // channel-derived; drives the me/them lanes
  channel: z.string(),
  startMs: z.number().int(),
  endMs: z.number().int(),
  text: z.string(),
  confidence: z.number().nullable().optional(),
  isFinal: z.boolean().default(true), // false = a live partial (future live mode)
});
export type Segment = z.infer<typeof SegmentSchema>;

// A meeting record: small queryable metadata. (The recording blob would be a
// "content" field routed to object storage via zodal bifurcation — omitted here
// since this batch UI only renders the transcript.)
export const MeetingSchema = z.object({
  id: z.string(),
  title: z.string(),
  startedAt: z.string(),
  durationMs: z.number().int(),
  participants: z.array(z.string()),
  segmentCount: z.number().int(),
});
export type Meeting = z.infer<typeof MeetingSchema>;

// The AI copilot's output — another collection, rendered as a feedback list.
export const FeedbackSchema = z.object({
  id: z.string(),
  meetingId: z.string(),
  kind: z.enum(['note', 'suggested_question', 'surfaced_doc', 'fact_check']),
  atMs: z.number().int(),
  title: z.string(),
  body: z.string(),
  sourceUrl: z.string().optional(),
});
export type Feedback = z.infer<typeof FeedbackSchema>;

// The zodal collections. We read inferred field lists off these to drive the UI.
export const segments = defineCollection(SegmentSchema);
export const meetings = defineCollection(MeetingSchema);
export const feedback = defineCollection(FeedbackSchema);
