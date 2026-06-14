# Research-report extracts — live overlay, transcript streaming, RAG (frontend-relevant)

Curated slices from the two June-2026 reports for the **hearing-frontend** skill.
Citation markers are kept; matching URLs are listed at the bottom of each section.
These are *condensed* extracts, not the full reports.

---

## A. GD Report — "Meeting Transcription and AI Agents"

### A.1 LiveKit's WebRTC room-based orchestration (multi-participant transcription)

LiveKit Agents treats AI agents as stateful, programmable server-side participants
that join virtual rooms alongside human users [3]. For multi-user scenarios where
several speakers must be transcribed on separate channels, a **supervisor agent**
monitors the room; when a participant connects it spawns an isolated `AgentSession`
bound to that participant's identity, each configured with its own VAD + STT plugin
(e.g. Deepgram Nova-3), transcribing that stream without mixing it with other members
[38][48]. The transcript is then **published back to the room on the unified
`lk.transcription` text-stream topic, so client applications or downstream agents can
intercept the data in real time** [47].

> Frontend takeaway: `lk.transcription` is the reference for a *single stream of
> transcript events any client UI subscribes to*. hearing's HTTP+SSE layer is the
> framework-agnostic equivalent.

### A.2 Real-time RAG integration pipeline

The reference open-source design (LiveKit Agents + Qdrant vector DB + LlamaIndex):
the agent's routing logic **intercepts transcription segments**, checks the text for
semantic intent / entity triggers, and — if a query needs contextual documentation —
vectorizes the text and matches it against the vector collection; the retrieved chunks
are appended to the LLM's system prompt dynamically [37][27]. **To prevent retrieval
latency from blocking the audio stream, the vector search is offloaded to a separate
async task and results are cached** to avoid redundant lookups [37].

Pipecat exposes structured turn events (`on_user_turn_stopped`,
`on_assistant_turn_stopped`) that emit a complete turn transcript when a speaker
finishes — ideal for sending compiled segment payloads to external APIs/microservices
asynchronously for real-time note-taking [46].

ASCII of the reference flow (condensed from the report):

```
LiveKit Room
  Human Speaker ──audio──► STT Agent ──live text──► AgentSession (context logic)
                                                        │
   Client UI & Captions ◄──lk.transcription────────────┤
                                                        ▼
                                          Retrieval Layer (LlamaIndex / Qdrant)
                                                        │ context payload
                                                        ▼
                                          Downstream LLM (reasoning)
```

> Frontend takeaway: the *feedback panel* is fed by this retrieval/LLM stage. Each
> "surfaced doc" / "fact-check" card is a retrieved-and-summarized chunk with a source
> URL — model it as the `Feedback` collection (`kind: 'surfaced_doc' | 'fact_check'`,
> `sourceUrl`, `confidence`). The async-offload + cache rule is a *backend* concern;
> the UI just receives finished cards.

### A.3 Latency budget (why act on finalized turns)

A cascaded pipeline (wait for full sentence → transcribe → LLM → synthesize) adds
unnatural latency; production pipelines stream partial STT results, stream LLM tokens,
and begin TTS on the first tokens [27][25]. End-to-end latency is modeled as the sum of
VAD threshold + STT + LLM time-to-first-token + tool/RAG retrieval + TTS + WebRTC
transport; un-optimized RAG can push it past the comfortable conversational window [37].
VAD-only turn detection mis-fires on mid-sentence pauses; semantic turn-detection
classifiers judge whether the utterance is structurally complete before signaling the
LLM [27].

> Frontend takeaway: the UI must visually distinguish *partial* (`isFinal: false`)
> from *finalized* segments, and feedback should only attach to finalized turns.

**URLs (GD report "Works cited", accessed June 14, 2026):**

- [3] Vapi vs Pipecat vs LiveKit: Voice Agent Frameworks Compared (2026), Inworld AI — https://inworld.ai/resources/vapi-vs-pipecat-vs-livekit
- [27] (LiveKit semantic turn detection / streaming pipeline guidance — LiveKit docs, accessed via report)
- [37] Lessons from implementing RAG in a real-time voice agent (LiveKit), Jorge Jarne — https://medium.com/@jorge.jarne/lessons-from-implementing-rag-in-a-real-time-voice-agent-livekit-43f0689bf565
- [38] Introduction | LiveKit Documentation — https://docs.livekit.io/agents/
- [46] Transcriptions | Pipecat — https://docs.pipecat.ai/api-reference/server/utilities/turn-management/transcriptions
- [47] Transcription text streams not generated for more than one participant · Issue #3657 · livekit/agents — https://github.com/livekit/agents/issues/3657
- [48] agents/examples/other/transcription/multi-user-transcriber.py · livekit/agents — https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py

---

## B. DIY Report — "Meeting Transcription Apps & a DIY Real-Time Transcription Pipeline on macOS"

### B.1 Piping the transcript into an agent (the queue the frontend consumes)

The streaming STT emits incremental/final segments onto a queue (`asyncio.Queue` or
similar); an agent consumer reads **finalized utterances** and triggers actions —
running notes, suggested questions, RAG over related docs. Integration points:

- **Granularity** — act on *finalized* segments (after VAD turn-end) to avoid churning
  on partial text; word-level timestamps let you trigger mid-utterance on keywords [54].
- **Latency budget** — streaming STT adds a few hundred ms to ~1–2 s; the LLM adds more.
  Fine for "surface a doc"; for live captions keep chunks small.
- **Backpressure / decoupling** — keep capture, STT, diarization, and agent as separate
  async tasks so a slow LLM call never stalls capture.
- **Speaker context** — feed the channel-derived "me vs them" label plus diarization
  labels into the agent prompt so it knows who asked what.

> Frontend takeaway: this is exactly the `side: 'me' | 'them'` + `speaker` fields on the
> `Segment` schema, and the `triggeredBy` segment id on `Feedback`.

### B.2 Open-source live-overlay apps to study (the overlay shell, not the data layer)

- **Hyprnote / anarlog** (`fastrepl/anarlog`, MIT) — local-first meeting notetaker;
  real-time transcription (local Whisper/Parakeet or cloud), speaker ID, captures
  system audio from any app, ships an MCP server so Claude/ChatGPT can read/write
  notes [56]. Excellent reference for the exact goal.
- **Meetily** (`Zackriya-Solutions/meetily`, MIT) — Rust/Tauri, 100% local,
  Parakeet/Whisper live transcription, captures mic + system audio simultaneously with
  ducking, Ollama summarization, pluggable AI [57].
- **Glass** (open-source Cluely alternative) and **Pluely** (`iamsrikanthnani/pluely`,
  Tauri, ~10 MB) — real-time meeting "copilot" overlays; Pluely separates system audio
  from mic, does live Whisper STT feeding an LLM [58][59]. **Natively**
  (`Natively-AI-assistant`) adds local RAG + dual audio channels + meeting history [60].
  Good references for the **live-agent overlay pattern** (floating always-on-top panel).

> Frontend takeaway: borrow the *overlay window UX* (small floating panel, transcript +
> feedback side by side) from Pluely/Glass/Natively. Borrow the *data flow* (queue →
> finalized utterances → schema-shaped events) from B.1. Keep the data layer zodal/acture.

**URLs (DIY report REFERENCES):**

- [54] Possible to use Whisper for real-time / streaming tasks? (Discussion #2), openai/whisper — https://github.com/openai/whisper/discussions/2
- [56] anarlog (formerly Hyprnote), fastrepl — https://github.com/fastrepl/anarlog
- [57] Meetily, Zackriya-Solutions — https://github.com/Zackriya-Solutions/meetily
- [58] Cluely vs Glass and Open Source Marketing, Hyperlush — https://hyperlush.com/cluely-vs-glass/
- [59] Pluely, iamsrikanthnani — https://github.com/iamsrikanthnani/pluely
- [60] Natively — open-source AI meeting assistant — https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant
- [61] 4 Best Open Source Meetily Alternatives in 2026, OpenAlternative — https://openalternative.co/alternatives/meetily
