# Key external links — streaming STT & live pipelines

Curated, one line each. Verified June 2026.

## Streaming STT engines
- [KoljaB/RealtimeSTT](https://github.com/KoljaB/RealtimeSTT) — most batteries-included; WebRTC+Silero VAD, `feed_audio()`, selectable engines, wake words, realtime callbacks. **Default starting point.**
- [ufal/whisper_streaming](https://github.com/ufal/whisper_streaming) — long-form streaming with the **LocalAgreement** policy; faster-whisper/mlx-whisper/OpenAI backends.
- SimulStreaming — same author's successor to whisper_streaming; **AlignAtt** attention-based emission, lower latency (search the ufal org for the current repo name).
- [collabora/WhisperLive](https://github.com/collabora/WhisperLive) — WebSocket server + browser/iOS clients; faster-whisper / TensorRT-LLM / OpenVINO; word timestamps, custom vocab, optional online pyannote speaker ID.
- [silero-vad](https://github.com/snakers4/silero-vad) — neural VAD, accurate, tiny; recommended default chunker.
- [wiseman/py-webrtcvad](https://github.com/wiseman/py-webrtcvad) — lightweight C VAD; lower accuracy on noisy meeting audio.

## Managed / cloud streaming
- [OpenAI Realtime transcription](https://developers.openai.com/api/docs/guides/realtime-transcription) — `gpt-realtime-whisper`, session `type: "transcription"`, `…input_audio_transcription.delta` / `.completed` events, match by `item_id`.
- [gpt-4o-transcribe-diarize](https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize) — separate model needed for managed diarization in the realtime path.
- Deepgram streaming — lowest-latency cloud streaming option called out in the reports (see the STT skill's pricing table).

## Orchestration frameworks
- [pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat) — frame-based pipeline; intercept `TranscriptionFrame` in a custom `FrameProcessor`, fire-and-forget to the agent. [Docs](https://docs.pipecat.ai/pipecat/learn/overview) · [STT docs](https://docs.pipecat.ai/pipecat/learn/speech-to-text) · [whisper example](https://github.com/pipecat-ai/pipecat/blob/main/examples/transcription/transcription-whisper.py)
- [livekit/agents](https://github.com/livekit/agents) — WebRTC room model; isolated `AgentSession` per participant for multi-channel transcription. [Docs](https://docs.livekit.io/agents/) · [multi-user example](https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py)
- [Voice Agent Architecture (LiveKit blog)](https://livekit.com/blog/voice-agent-architecture-stt-llm-tts-pipelines-explained) — latency budget + semantic turn detection rationale.

## Reference apps to study/fork (local-first meeting notetakers)
- [fastrepl/anarlog](https://github.com/fastrepl/anarlog) (was Hyprnote) — local-first, system-audio capture, speaker ID, MCP server. Closest to `hearing`'s goal.
- [Zackriya-Solutions/meetily](https://github.com/Zackriya-Solutions/meetily) — Rust/Tauri, 100% local, **dual mic+system audio** with ducking, Parakeet/Whisper, Ollama summarization.
- [huggingface/speech-to-speech](https://github.com/huggingface/speech-to-speech) — full cascaded STT→LLM→TTS with MLX Mac optimizations, if a voice-reply loop is ever wanted.
