---
name: hearing-frontend
description: Use when building or designing the TypeScript/React frontend for the "hearing" meeting-transcription project — the transcript viewer, the live AI-copilot overlay, the agent-feedback panel (notes, suggested questions, surfaced docs, fact-checks), or the meeting/project-context UI. Covers schema-driven UI with zodal (defineCollection, Zod v4, content-metadata bifurcation routing transcript metadata to a DB and audio/recording content to object storage), command-dispatch with acture (one command → palette + hotkeys + AI tool + MCP + tests), how the Python backend (argh CLI + HTTP layer) feeds the UI, and how live finalized utterances stream to the client. Triggers on transcript view, copilot overlay, agent panel, feedback panel, suggested questions, surfaced docs, fact-check, meeting collection, segment schema, speaker/me-vs-them labels, zodal collection, acture command, bifurcation, lk.transcription, SSE/WebSocket transcript stream, novice-friendly frontend, declarative/schema UI for hearing. Explain JS/TS decisions for a frontend novice.
---

# hearing-frontend

The TypeScript/React frontend for **hearing** (a pluggable macOS meeting-transcription + context-connected AI-agent library; batch-first, then live). The reader is a **frontend novice** — explain every JS/TS decision in plain terms, and prefer **declarative, schema-driven UI** over hand-wired components.

For the backend that feeds this UI see [[hearing-architecture]] (the orchestrator + HTTP layer) and [[hearing-live-pipeline]] (how finalized utterances are produced). Transcript/segment/diarization *data modeling* is owned by the global **annotation-systems** skill — do not re-derive it here. CLI/HTTP/UI dispatch on the Python side is **python-dispatching**; the agent layer's model choices are **claude-api**.

## The core abstraction: declare the shape once, infer the surface

The whole frontend rests on two SSOT (single-source-of-truth) declarations, both schema-first:

1. **zodal** — declare each UI *collection* once as a [Zod v4](https://zod.dev) schema. zodal infers the table columns, form fields, filters, state store, and data-access layer from that one declaration. You don't write column defs or filter widgets by hand. *(Read the local README at `/Users/thorwhalen/Dropbox/py/proj/i/_zodals/zodal/README.md` and the global **zodal-ecosystem** skill before writing zodal code.)*
2. **acture** — declare each *operation* once as a command. It becomes a command-palette entry, a keyboard shortcut, an AI tool call, an MCP tool, an e2e test action, and (via the `acture` PyPI client) a Python call — all from one definition. *(Read `/Users/thorwhalen/Dropbox/py/proj/i/acture/README.md`.)*

> **Novice note — what "headless" and "declarative" mean here.** zodal is *headless*: it produces plain configuration **objects** (which columns, which filters), never JSX/DOM. A renderer package (`zodal-ui-shadcn`) turns those objects into actual on-screen components. So "declarative" = you describe *what* the data is, and the library decides *how* to draw it. You change behavior by editing the schema, not by editing JSX.

**Non-negotiable principle:** UI structure is *derived* from schemas and command definitions, not authored imperatively. If you find yourself hand-coding a `<table>` of transcript rows or a hard-wired `onClick` handler for "ask the agent", stop — that belongs in a zodal collection or an acture command. (This mirrors the Python side's progressive-disclosure rule: simple things one-liner-simple, complex things possible behind optional config.)

## Build order (progressive disclosure — match the backend milestones)

| Stage | Backend milestone | Frontend deliverable | Stack |
|-------|-------------------|----------------------|-------|
| 1 | Batch transcript exists in a store | **Static transcript view** — read-only diarized segments, me/them lanes, search/filter | zodal collection + `zodal-ui-shadcn` |
| 2 | Live pipeline emits finalized utterances | **Live copilot overlay** — append-only transcript that grows in real time | + transcript stream (SSE/WS) appending to the same collection |
| 3 | Agent loop produces feedback | **Agent-feedback panel** — notes / suggested questions / surfaced docs / fact-checks | second zodal collection, streamed like the transcript |
| — | any | **Command layer** — palette, hotkeys, AI/MCP tools (export transcript, jump to speaker, pin a doc, ask the agent) | acture commands |

Do **not** build the overlay before the static view works. The overlay is the static view + a stream that appends rows. Reusing one collection for both is the payoff of the schema-driven approach.

## The three UI surfaces, as zodal collections

Map each surface to one `defineCollection(schema)`. Keep schemas as the SSOT; the backend's Python dataclasses/Pydantic models should mirror these field-for-field (and the HTTP layer serializes to exactly this shape — see [[hearing-architecture]]).

### Surface 1 — Meeting / transcript collection

A meeting is **metadata** (small, queryable: title, participants, time) plus **content** (large, opaque: the recording/audio). This is the textbook case for zodal's **content-metadata bifurcation** — route metadata to a DB and the recording to object storage, composed behind one provider.

```typescript
import { z } from 'zod';
import { defineCollection } from '@zodal/core';
import { createBifurcatedProvider } from '@zodal/store';

// A single transcript segment (the row the UI actually renders).
// Time as integer milliseconds (rational time) — never floats. See annotation-systems.
const Segment = z.object({
  id: z.string().uuid(),
  meetingId: z.string().uuid(),
  speaker: z.string(),                       // diarization label, e.g. "Speaker 2"
  side: z.enum(['me', 'them']),              // channel-derived; drives the me/them lanes
  startMs: z.number().int(),
  endMs: z.number().int(),
  text: z.string(),
  isFinal: z.boolean().default(true),        // false = live partial (Stage 2)
});

// The meeting record: metadata + the opaque recording (content).
const Meeting = z.object({
  id: z.string().uuid(),
  title: z.string(),
  startedAt: z.date(),
  participants: z.array(z.string()),
  recording: z.any(),                        // auto-classified as CONTENT by name heuristic
});

export const segments = defineCollection(Segment);
export const meetings = defineCollection(Meeting);

meetings.getContentFields();   // ['recording']  — large/opaque → object storage
meetings.hasBifurcation();     // true
segments.getSearchableFields(); // ['text', 'speaker'] — drives the search box for free

// Two backends, one provider: metadata in a DB, audio in object storage.
const meetingProvider = createBifurcatedProvider({
  metadataProvider: dbProvider,    // e.g. @zodal/store-supabase (queryable rows)
  contentProvider: blobProvider,   // e.g. @zodal/store-s3      (the recording blob)
  contentFields: meetings.getContentFields(),
});
```

> **Why bifurcation matters here.** You want to *search and filter* thousands of transcript segments cheaply (DB), but the recording is a multi-megabyte blob you only fetch on demand (object storage). The schema decides which is which — `recording` is classified as content by zodal's name heuristic; everything else is queryable metadata. On the Python side this is the same split: transcript JSON in a small store, audio in a blob store (**python-storage** / `dol`).

### Surface 2 — Agent-feedback panel

The live copilot's output is just another collection: each item is a typed piece of feedback. Render it as a streamed, append-only list beside the transcript.

```typescript
const Feedback = z.object({
  id: z.string().uuid(),
  meetingId: z.string().uuid(),
  kind: z.enum(['note', 'suggested_question', 'surfaced_doc', 'fact_check']),
  atMs: z.number().int(),                    // transcript time this responds to
  triggeredBy: z.string().optional(),        // segment id that fired this
  title: z.string(),
  body: z.string(),
  sourceUrl: z.string().url().optional(),    // for surfaced_doc / fact_check citations
  confidence: z.number().min(0).max(1).optional(),
});

export const feedback = defineCollection(Feedback);
feedback.getVisibleFields();  // inferred — group/badge by `kind` in the renderer
```

The `kind` enum becomes a `BadgeCell` automatically (`zodal-ui-shadcn` maps `z.enum` → badge). Filtering by kind ("show only suggested questions") is inferred too — no filter widget written by hand.

### Surface 3 — Meeting / project context

Background docs, prior meetings, and project notes the agent draws on for RAG. Same pattern: small metadata in a DB, document bodies as content.

```typescript
const ContextDoc = z.object({
  id: z.string().uuid(),
  projectId: z.string().uuid(),
  title: z.string(),
  tags: z.array(z.string()),
  source: z.enum(['note', 'prior_meeting', 'upload', 'web']),
  document: z.any(),                         // content → object storage
});
export const contextDocs = defineCollection(ContextDoc);
```

## Rendering: turn the config objects into shadcn components

`zodal-ui-shadcn` is the renderer registry — it resolves a component for each field by Zod type. You feed it zodal's inferred config; it returns React components.

```typescript
import { createShadcnRegistry } from 'zodal-ui-shadcn';
const registry = createShadcnRegistry();
const Cell = registry.resolve(field, { mode: 'cell' });   // table display
const Form = registry.resolve(field, { mode: 'form' });   // data entry
const Filter = registry.resolve(field, { mode: 'filter' }); // filter widget
```

Type → component mapping you get for free: `enum`→Badge, `date`→localized date, `boolean`→check/cross, `array`→comma list, `string`→text + search filter. Override only when needed (e.g. a custom me/them lane renderer) via `registry.register({ tester, renderer, name })` at a higher `PRIORITY.USER`. The transcript "lanes" (me on one side, them on the other) is a layout choice on top of the resolved cells — a thin custom view, not a rewrite of the data layer. See the global **zodal-ecosystem** skill before adding a new renderer.

## The command layer: acture (one definition → every surface)

Every user/agent action is a command, defined once. Don't scatter `onClick` handlers. Candidate commands for hearing:

| Command | Palette | Hotkey | AI/MCP tool | Notes |
|---------|---------|--------|-------------|-------|
| `transcript.export` | ✓ | ✓ | ✓ | export current meeting (md/srt/json) |
| `transcript.jumpToSpeaker` | ✓ | — | ✓ | scroll to next utterance by speaker |
| `agent.ask` | ✓ | ✓ | ✓ | ask the copilot about the meeting so far |
| `context.pinDoc` | ✓ | — | ✓ | add a doc to RAG context for this meeting |
| `feedback.dismiss` | — | ✓ | — | hide a feedback card |

```typescript
// Parameterized command: the Zod params schema drives the palette form AND the AI/MCP tool schema.
const exportTranscript = {
  id: 'transcript.export',
  title: 'Export transcript',
  params: z.object({
    format: z.enum(['markdown', 'srt', 'json']).describe('Output format'),
  }),
  run: async ({ format }, ctx) => ctx.api.exportTranscript(ctx.meetingId, format),
};
```

The `.describe()` on each param is **load-bearing**: acture projects it into the AI tool description and MCP tool schema. acture's own lint rule (`acture/require-param-describe`) flags missing ones. Because the same command is the AI tool *and* the MCP tool, the copilot can invoke "export transcript" or "pin doc" itself, and so can an external MCP client (Claude Desktop, etc.) — one definition, every consumer.

> **Novice note — why this is worth it.** Without acture you'd write the button, the keyboard shortcut, the API call, and a separate AI-tool JSON definition, and keep them in sync by hand. With acture you write the operation once and the four surfaces are projections of it. acture is "agent-written by default" — you do not have to add an `acture-*` npm dependency; the agent can write the small registry/dispatcher into the project. Reach for `acture-palette-react` / `acture-hotkeys` / `acture-ai-vercel` / `acture-mcp-server` only when you decide a tested package beats hand-written glue.

## Backend → frontend wiring

The Python backend ([[hearing-architecture]]) exposes the same operations three ways via **python-dispatching**: an `argh` CLI, an HTTP layer, and (optionally) a UI. The frontend talks to the **HTTP layer**.

- **Batch (Stage 1):** plain REST. zodal store adapters (`@zodal/store-supabase`, `@zodal/store-s3`, or a thin custom `DataProvider` hitting the Python HTTP routes) read the meeting/segment collections. The DataProvider contract is in the **zodal-ecosystem** skill.
- **Live (Stage 2–3):** the backend's finalized-utterance queue ([[hearing-live-pipeline]]) is exposed as a **server-push stream** — Server-Sent Events (SSE) for one-way transcript/feedback push (simplest; a plain `EventSource` in the browser), or WebSocket if you later need bidirectional control. Each pushed event is one `Segment` or `Feedback` object (exactly the zodal schema shape). The client appends it to the in-memory collection store, and the table re-renders. Partial (`isFinal: false`) segments update in place; finalized ones replace them.

> **Novice note — SSE vs WebSocket.** SSE is a one-directional "the server keeps sending me lines" channel over plain HTTP — trivial to consume (`new EventSource(url).onmessage = ...`) and the right default because transcript/feedback flow *server → client only*. Use a WebSocket only when the *client* must push messages mid-stream (e.g. live "barge-in" controls). Start with SSE.

The streaming pattern itself (decoupled async tasks, act on *finalized* segments, backpressure) is the backend's job — see [[hearing-live-pipeline]]. The frontend just consumes one JSON object per event and trusts the schema.

### Reference pattern: LiveKit's `lk.transcription`

The GD report's reference architecture (LiveKit Agents) publishes transcripts on a unified `lk.transcription` text-stream topic that any client UI subscribes to, while an `AgentSession` runs RAG (vectorize the segment → match a vector store → append retrieved chunks to the LLM prompt) on a *separate async task* so retrieval never stalls the audio [1][2][3]. hearing's HTTP+SSE layer is the lightweight, framework-agnostic equivalent of that topic: one stream of transcript events, one stream of agent feedback. If you ever need true multi-participant WebRTC rooms with per-speaker STT, LiveKit Agents is the model to adopt — but it is heavier than a batch-first local app needs. The overlay-window UX (a floating always-on-top copilot panel) is demonstrated by the Pluely / Glass / Natively open-source apps [4][5][6]; study them for the overlay shell, not the data layer.

## Pitfalls (call these out in review)

1. **Hand-authored columns/filters/handlers** — anything derivable from a Zod schema or an acture command must not be hand-written. That is the whole point.
2. **Float timestamps** — segment times are integer milliseconds. Floats break equality and seek. (annotation-systems, non-negotiable.)
3. **Schema drift between Python and TS** — the Zod schemas and the backend models are *one* contract. When one changes, change both; the HTTP layer must serialize to exactly the zodal shape. Consider generating one from the other.
4. **Storing the recording in the DB** — recordings are content → object storage via bifurcation. Only metadata goes in the queryable store.
5. **Building the overlay before the static view** — the overlay is the static view plus a stream. Stage 1 first.
6. **Churning the agent on partial text** — feedback should trigger on *finalized* utterances (backend concern), but the UI must also visibly distinguish `isFinal: false` partials so the user isn't misled.
7. **Scattered `onClick` logic** — route through acture so the action is also an AI/MCP tool and is testable as a sequence.

## References

- `references/from-research-reports.md` — the live-overlay / `lk.transcription` / RAG passages from both reports, with citation markers and URLs.
- `references/key-links.md` — the key external repos and docs (zodal/acture local READMEs, LiveKit, Pluely/Glass/Natively, SSE/EventSource).
- Local READMEs (read before coding): zodal `/Users/thorwhalen/Dropbox/py/proj/i/_zodals/zodal/README.md`, acture `/Users/thorwhalen/Dropbox/py/proj/i/acture/README.md`.
- Global skills: **zodal-ecosystem** (where zodal code lives, DataProvider contract, adding renderers/adapters), **annotation-systems** (segment/diarization/interval modeling), **python-dispatching** (backend CLI/HTTP/UI), **python-storage** (`dol` stores for transcripts/recordings), **claude-api** (agent model choices).
