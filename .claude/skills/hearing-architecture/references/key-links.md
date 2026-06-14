# Key external references for hearing-architecture

The most important repos/docs for the *architecture* concern. (Engine/diarization/
capture/agent specifics live in the respective sibling skills' references.)

## Pipelines to study before designing ours (synthesize, don't import)

- **Pipecat** — https://github.com/pipecat-ai/pipecat — modular event-driven Python
  voice pipeline; frames flow through FrameProcessors. Study the FrameProcessor
  intercept + fire-and-forget pattern; the multimodal Frame taxonomy. Docs:
  https://docs.pipecat.ai/pipecat/learn/overview
- **LiveKit Agents** — https://github.com/livekit/agents — WebRTC room model with
  per-participant AgentSessions and per-track STT. Study the multi-participant
  (per-channel) transcription idea; our channel split is the cheap analogue.
  Multi-user transcriber example:
  https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py

## Reference projects with our exact shape (capture + STT + diarization + agent)

- **anarlog / Hyprnote** — https://github.com/fastrepl/anarlog — local-first meeting
  notetaker; system-audio capture, local or cloud STT, speaker ID, MCP server so
  Claude can read/write notes. Closest match to the whole hearing goal.
- **Meetily** — https://github.com/Zackriya-Solutions/meetily — Rust/Tauri, 100%
  local; captures mic + system audio simultaneously with ducking; pluggable AI.
  Channel-split selective capture issue (the channel trick in the wild):
  https://github.com/Zackriya-Solutions/meeting-minutes/issues/337

## Streaming building blocks (for the live source + trigger)

- **RealtimeSTT** — https://github.com/KoljaB/RealtimeSTT — batteries-included
  low-latency: VAD (WebRTC + Silero), selectable engines, realtime-text callbacks,
  `feed_audio` for fed chunks. Best starting point for the live `CaptureSource`/trigger.
- **WhisperLive** — https://github.com/collabora/WhisperLive — near-live Whisper over
  WebSocket; word-level timestamps; optional real-time speaker ID. Reference for the
  streaming-segment-over-a-queue shape.
- **OpenAI Realtime transcription** — https://developers.openai.com/api/docs/guides/realtime-transcription
  — managed streaming session returning incremental deltas; reference for the
  `stream_transcribe` interim/final contract.

## Python composition idioms (the actual implementation primitives)

- `typing.Protocol` — structural facades (no inheritance) — https://docs.python.org/3/library/typing.html#typing.Protocol
- `dataclasses` (frozen, slots, `replace`) — the segment spine + enrich-by-copy —
  https://docs.python.org/3/library/dataclasses.html
- `asyncio.Queue` — decoupled stages / backpressure —
  https://docs.python.org/3/library/asyncio-queue.html
