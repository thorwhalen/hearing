# hearing — Roadmap

The deliberate ordering: **build the batch path first** (it is high-value,
achievable, and exercises the whole component stack except live streaming), then
add the **live path** as a purely *additive* layer (swap a batch capture/sink
for a streaming one; attach the same agents to a live queue; the batch machinery
keeps working unchanged).

The architecture (four swappable concerns wired by dependency injection) is the
single source of truth — see the `hearing-architecture` skill. Each concern has
its own development skill under `.claude/skills/`.

## Milestone 1 — Batch path  ·  *in progress (core working)*

> Reliably transcribe a meeting to a speaker-labelled file, optionally keep the
> recording, and run context-connected agents over the result post-meeting.

| Concern | Status | Notes |
|---|---|---|
| Shared data model (`TranscriptSegment` spine, integer-ms `TimeSpan`, `Channel`) | ✅ done | `hearing/types.py`, `hearing/interfaces.py` |
| Channel handling (load multi-channel file, split mic/system, resample) | ✅ done | `hearing/capture.py` |
| STT facade + default local engine (faster-whisper) | ✅ done | `hearing/stt.py` |
| "Me vs them" channel-trick diarizer | ✅ done | `hearing/diarize.py` (`ChannelTrickDiarizer`) |
| Batch agents — Claude (default, pluggable) + offline extractive fallback | ✅ done | `hearing/agents.py` |
| Pipeline facade `transcribe(...)` + `summarize(...)` (composition/DI) | ✅ done | `hearing/pipeline.py` |
| `argh` CLI (`transcribe` / `summarize` / `info`) | ✅ done | `hearing/cli.py` |
| Tests + runnable demo | ✅ done | `tests/`, `examples/demo_meeting.py` |
| **Acoustic diarization** (pyannote) for *individual* remote speakers | 🔬 stubbed | `PyannoteDiarizer` implemented, untested (needs HF token) |
| **Live macOS capture source** (BlackHole / Core Audio taps → channels) | 🔬 partial | `DeviceCapture` (sounddevice) implemented but needs hardware to verify; `StreamingFileCapture` streams a file today |
| Persistence (`record=` dol store for transcripts/recordings) | 📋 todo | hook present in `transcribe(record=...)`; flesh out per `python-storage` |
| Context-connected agents over a knowledge store (RAG) | 📋 todo | `ClaudeAgent.context` hook present; add retrieval per `hearing-agents` |

## Milestone 2 — Live path  ·  *core working*

> Streaming STT, VAD-based utterance finalization, low-latency in-meeting agent
> feedback. Additive on top of Milestone 1 — same STT/diarizer/agent interfaces.

| Piece | Status | Notes |
|---|---|---|
| `STTEngine.stream_transcribe` (VAD → utterance → finalized segment) | ✅ done | `hearing/stt.py`; reuses the batch `transcribe` per utterance |
| VAD + utterance segmentation | ✅ done | `hearing/vad.py`: `EnergyVAD` (default, dep-free) + `SileroVAD` (optional); `segment_utterances` |
| `live_transcribe(...)` orchestrator (decoupled async stages, bounded queues) | ✅ done | `hearing/pipeline.py`; per-channel demux preserves "me vs them"; fire-and-forget agent |
| Streaming source for testing/demo | ✅ done | `StreamingFileCapture` (+ `hearing live FILE` CLI) |
| Tests (VAD, live orchestration, real-whisper live integration) | ✅ done | `tests/test_vad.py`, `tests/test_live_pipeline.py` |
| Cloud / lower-latency streaming engines (Deepgram, OpenAI Realtime, WhisperLive) | 📋 todo | behind the same `STTEngine` facade |
| Semantic turn detection (beats naive VAD on mid-sentence pauses) | 📋 todo | see the skill's latency section |
| Live mic/device capture verified on hardware | 📋 todo | `DeviceCapture` written; needs a BlackHole + Aggregate Device to confirm |

See the `hearing-live-pipeline` skill.

## Milestone 3 — Frontend  ·  *static view working*

> Schema-driven TypeScript/React UI: a transcript viewer and (later) a live
> copilot overlay (agent feedback panel: notes, suggested questions, surfaced
> docs, fact-checks).

| Piece | Status | Notes |
|---|---|---|
| HTTP layer over the facades (FastAPI) | ✅ done | `hearing/http_app.py`; `GET /api/health`, `POST /api/transcribe`; `hearing serve`; tested with TestClient |
| zodal schema-driven collections (Segment/Meeting/Feedback) | ✅ done | `frontend/src/schema.ts` — the SSOT; UI reads searchable/visible fields off the collection |
| Static transcript viewer (me/them lanes, search) + AI-notes panel | ✅ done | `frontend/` (Vite+React+TS); builds clean; verified in-browser end-to-end |
| Schema-as-contract API client (Zod-validated responses) | ✅ done | `frontend/src/api.ts` |
| `zodal-ui-shadcn` renderer registry | 📋 todo | not yet published to npm; current renderer is a thin custom view (swap in when available) |
| acture command layer (palette / hotkeys / AI+MCP tools) | 📋 todo | export transcript, jump-to-speaker, ask-the-agent, pin-doc |
| Live transcript streaming (server→client push) | ✅ done | `POST /api/transcribe/stream` (NDJSON) + a "Live" toggle in the UI that appends finalized segments as they arrive |
| Streamed agent-feedback panel (the live copilot) | ✅ done | the stream also pushes `{"type":"feedback",...}` from the live agent's `on_segment`; the UI's `FeedbackPanel` renders notes/suggested-questions live |
| Always-on-top overlay shell (floating copilot window) | 📋 todo | study Pluely/Glass for the overlay window; current UI is an in-page panel |

See the `hearing-frontend` skill. (The HTTP layer also advances Milestone 1's
"interfaces to the outside".)

## Tracking

Work is tracked in GitHub issues (one epic + one per concern) and design
rationale in Discussions. This file is the human-readable plan of record.
