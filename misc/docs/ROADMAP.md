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
| **Live macOS capture source** (BlackHole / Core Audio taps → channels) | 📋 todo | today you bring a recorded multi-channel file |
| Persistence (`record=` dol store for transcripts/recordings) | 📋 todo | hook present in `transcribe(record=...)`; flesh out per `python-storage` |
| Context-connected agents over a knowledge store (RAG) | 📋 todo | `ClaudeAgent.context` hook present; add retrieval per `hearing-agents` |

## Milestone 2 — Live path  ·  *not started (designed)*

> Streaming STT, VAD-based utterance finalization, low-latency in-meeting agent
> feedback. Additive on top of Milestone 1 — same STT/diarizer/agent interfaces.

- `STTEngine.stream_transcribe` (a streaming backend: RealtimeSTT / WhisperLive
  / OpenAI Realtime API).
- VAD (silero / webrtc) → buffer utterance → emit a **finalized** segment
  (`meta['final']`) onto an `asyncio.Queue`.
- Decoupled async stages (capture / STT / diarization / agent) so a slow LLM
  call never stalls capture.
- `live_transcribe(...)` facade (the async generator is stubbed today).
- See the `hearing-live-pipeline` skill.

## Milestone 3 — Frontend  ·  *not started (designed)*

> Schema-driven TypeScript/React UI: a transcript viewer and a live copilot
> overlay (agent feedback panel: notes, suggested questions, surfaced docs,
> fact-checks).

- zodal (Zod-schema-driven collections; content/metadata bifurcation routes
  transcript metadata to a DB and audio to object storage).
- acture (command-dispatch).
- An HTTP layer over the same Python facades (`python-dispatching`).
- See the `hearing-frontend` skill.

## Tracking

Work is tracked in GitHub issues (one epic + one per concern) and design
rationale in Discussions. This file is the human-readable plan of record.
