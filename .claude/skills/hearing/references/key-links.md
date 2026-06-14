# Key external references for the `hearing` orchestrator

The most important whole-project references — reference apps that match the
*entire* hearing goal, and the frameworks to study before scaffolding. (Per-layer
specifics — engines, diarizers, capture drivers, agent frameworks — live in each
sibling skill's own `references/`.)

## Reference projects with our exact shape (capture + STT + diarization + agent) — study, don't fork

- **anarlog / Hyprnote** — https://github.com/fastrepl/anarlog — local-first
  meeting notetaker: system-audio capture, local or cloud STT, speaker ID, MCP
  server so an LLM can read/write notes. Closest single match to the whole
  hearing goal; study its layer seams.
- **Meetily** — https://github.com/Zackriya-Solutions/meetily — Rust/Tauri, 100%
  local; captures mic + system audio simultaneously with ducking; pluggable AI.
  The channel-split selective-capture issue (the channel trick in the wild):
  https://github.com/Zackriya-Solutions/meeting-minutes/issues/337

## Frameworks for the LIVE milestone (Milestone 2)

- **Pipecat** — https://github.com/pipecat-ai/pipecat — modular event-driven
  Python voice pipeline; frames flow through swappable FrameProcessors. Best fit
  for a custom, linear, Python-first live pipeline. Docs:
  https://docs.pipecat.ai/pipecat/learn/overview
- **LiveKit Agents** — https://github.com/livekit/agents — production-grade WebRTC
  rooms, per-participant sessions, per-track STT. Heavier; reach for it only if
  you need multi-participant WebRTC + telephony.
- **RealtimeSTT** — https://github.com/KoljaB/RealtimeSTT — batteries-included
  streaming STT (faster-whisper / Parakeet-MLX) + VAD; the report's Stage-2 pick.

## The two source reports (primary material — cite these, don't re-research)

- `misc/docs/Meeting Transcription Apps & a DIY Real-Time Transcription Pipeline on macOS.md`
  — the DIY pipeline report: four concerns, the channel trick, the staged roadmap.
- `misc/docs/Meeting Transcription and AI Agents - GD Report.md`
  — the GD report: commercial taxonomy, local-first paradigm, live latency model,
  Pipecat vs LiveKit, strategic recommendations.
