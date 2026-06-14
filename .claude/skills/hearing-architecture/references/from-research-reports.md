# Source extracts for hearing-architecture

Curated slices of the two research reports (dated June 2026) that justify the
architecture decisions in this skill. `[DIY]` = "Meeting Transcription Apps & a
DIY Real-Time Transcription Pipeline on macOS"; `[GD]` = "Meeting Transcription
and AI Agents — GD Report". Both live in `misc/docs/`. Bracketed `[n]` markers
are the originals' citation numbers; matching URLs are listed at the bottom.

---

## [DIY] The four-concern decomposition (lines 74–81) — THE core abstraction

> # TOPIC 2: Building Your Own Transcription + Real-Time Agent Pipeline
>
> Architecturally this decomposes into four separable concerns, each swappable
> behind a clear interface:
> 1. **Audio capture** (mic + system audio) → produces audio frames
> 2. **STT engine** (the pluggable facade) → local or cloud, batch or streaming → produces text
> 3. **Diarization / speaker ID** (separate concern) → labels who spoke
> 4. **Agent layer** → consumes the transcript stream and does things

This is the spine of the whole project: four facades, dependency-injected.

---

## [DIY] Concern 1 — channel-split capture (lines 82–105)

> The challenge is capturing **system audio** (other participants coming out of
> your speakers), not just the mic.

> Crucially, **an aggregate device does not mix** — mic and system audio land on
> separate channels [8][30]. So you can build an aggregate where mic = channels
> 1–2 and BlackHole/system = channels 3–4, record all channels, and slice them
> apart.

> **sounddevice** (PortAudio): open an InputStream on the Aggregate Device, read
> all channels as a NumPy frames×channels array, slice columns (`data[:, 0:2]` =
> mic, `data[:, 2:4]` = system). Supports a `mapping` argument to select channels.

Justifies: `Channel` enum as first-class, `CaptureSource` yielding `(channel, frames)`.

---

## [DIY] Concern 2 — the STT facade (lines 110–112)

> Because you'll facade this behind a clear interface (`transcribe(audio) ->
> segments` plus a streaming variant), the rest of the architecture doesn't care
> which engine sits behind it.

Direct justification for the `STTEngine` Protocol (`transcribe` + `stream_transcribe`).
WhisperX adds word-level timestamps + diarization [34]; faster-whisper is the
practical self-hosting default [33]. (Engine choice is owned by hearing-stt.)

---

## [DIY] Concern 3 — diarization vs identification + the channel trick (lines 151–156)

> - **Diarization** = "who spoke when" — partitioning audio into anonymous
>   Speaker 1 / Speaker 2 segments. **Identification** = attaching real identities.
> - **Open-source diarization**: **pyannote.audio 3.1** is the gold standard ... [7][49]
> - **The channel trick (elegant)** — since the BlackHole+Aggregate setup keeps
>   your **mic** on one channel and **system audio** (everyone else) on another,
>   you already know who's local: just measure which channel has energy. The mic
>   channel = you; the system channel = remote participants [8][30]. This is ...
>   far simpler and more reliable than fingerprinting. Run diarization on the
>   *system* channel to separate the remote speakers, and treat the *mic* channel
>   as a known speaker ("me").

Justifies: `speaker=ME` from the MIC channel; diarization only on SYSTEM; the
`Diarizer` Protocol enriching `.speaker`; a `ChannelTrickDiarizer` as the cheap default.

---

## [DIY] Concern 4 — live loop, queue, decoupling (lines 158–172)

> the streaming STT emits incremental/final segments onto a queue
> (`asyncio.Queue` or similar). An agent consumer reads finalized utterances and
> triggers actions — running notes, suggested questions, RAG over related docs.

> - **Granularity**: act on *finalized* segments (after VAD turn-end) to avoid
>   churning on partial text; word-level timestamps ... let you trigger on
>   keywords mid-utterance [54].
> - **Backpressure / decoupling**: keep capture, STT, diarization, and agent as
>   separate async tasks so a slow LLM call never stalls audio capture.
> - **Speaker context**: feed the channel-derived "me vs them" label plus
>   diarization labels into the agent prompt so it knows who asked what.

Justifies: decoupled async tasks + `asyncio.Queue`; act on finalized segments;
fire-and-forget the agent; feed channel + speaker into the agent.

VAD building blocks: silero-vad (neural) / webrtcvad (lightweight); pattern is
VAD → buffer utterance → transcribe → emit [54]. RealtimeSTT [38] is the most
batteries-included streaming starting point.

---

## [GD] Idiomatic pipeline shapes to SYNTHESIZE (not import) — lines 106–219

The GD report describes two frameworks. We **do not adopt either**; we extract
the *shapes* and rebuild them idiomatically in Python (Protocols + dataclasses +
asyncio.Queue).

### Pipecat — frame-based pipeline (lines 110–179)

> Pipecat ... processes streaming multimodal data ... as discrete *Frames*
> flowing through a directed pipeline of *Frame Processors*.

Pipeline shape: `Transport.in → VADProcessor (Silero) → STTService → LiveAgent`.
Key lesson — a custom `FrameProcessor` intercepts `TranscriptionFrame` and does
**non-blocking fire-and-forget** routing to the agent so the media pipeline never
lags:

> ```python
> if isinstance(frame, TranscriptionFrame):
>     asyncio.create_task(self._route_to_agent(frame.text, frame.timestamp))
> ...
> await self.push_frame(frame, direction)  # forward downstream
> ```

> When a user or assistant finishes speaking, events such as `on_user_turn_stopped`
> ... emit a complete turn transcript. These structured turn events are ideal for
> sending compiled segment payloads to external APIs.

→ Our equivalent: `agent.on_segment` fired via `asyncio.create_task`; act on turn/
finalized boundaries; segments flow on through the pipeline.

### LiveKit — room model, per-participant STT (lines 181–184)

> For multi-user scenarios where multiple speakers must be transcribed
> simultaneously on separate channels, LiveKit Agents provides native
> multi-participant tracking ... spawns an isolated AgentSession ... transcribing
> the participant's audio stream in real-time without mixing it with other room
> members.

→ Our equivalent: per-channel transcription (mic vs system), don't mix; the
channel split is our cheap stand-in for LiveKit's per-participant tracks.

### Real-time RAG (lines 186–219)

> the agent checks the transcribed text for semantic intent or specific entity
> triggers ... To prevent retrieval latencies from blocking the audio stream, the
> vector search is offloaded to a separate, asynchronous task thread, and the
> resulting context is cached.

→ Same decoupling principle: retrieval/LLM work is offloaded; never block capture.
(Agent/RAG internals owned by hearing-agents.)

### Cascaded latency caveat (lines 225–228)

> sequential "cascaded" pipelines (waiting for a speaker to complete an entire
> sentence, transcribing it, sending it to the LLM ...) introduce significant,
> unnatural latencies ... streaming pipelines [stream] partial results as the user
> speaks.

→ Why `stream_transcribe` yields interim + final, and why stages are decoupled.

---

## Reference URLs (from the reports' REFERENCES / Works cited sections)

From [DIY]:
- [7] Best Speaker Diarization Tools 2026 | VexaScribe — https://novascribe.ai/compare/best-speaker-diarization-tools
- [8] BlackHole | ExistentialAudio — https://github.com/ExistentialAudio/BlackHole
- [9] Capturing system audio with Core Audio taps | Apple Developer — https://developer.apple.com/documentation/CoreAudio/capturing-system-audio-with-core-audio-taps
- [30] How to Record Mac System Audio Using Python and BlackHole | Medium — https://medium.com/@mehsamadi/how-to-record-mac-system-audio-using-python-and-blackhole-a45d06eaad0f
- [31] AudioTee: capture system audio output on macOS | Strongly Typed — https://stronglytyped.uk/articles/audiotee-capture-system-audio-output-macos
- [33] faster-whisper | SYSTRAN — https://github.com/SYSTRAN/faster-whisper
- [34] Whisper.cpp vs faster-whisper 2026 (WhisperX, distil-whisper) | PromptQuorum — https://www.promptquorum.com/power-local-llm/local-whisper-stt-comparison-2026
- [38] RealtimeSTT | KoljaB — https://github.com/KoljaB/RealtimeSTT
- [43] Realtime transcription | OpenAI API — https://developers.openai.com/api/docs/guides/realtime-transcription
- [49] Pyannote vs Nemo | La Javaness (Medium) — https://lajavaness.medium.com/comparing-state-of-the-art-speaker-diarization-frameworks-pyannote-vs-nemo-31a191c6300
- [54] Whisper for real-time / streaming (Discussion #2) | openai/whisper — https://github.com/openai/whisper/discussions/2
- [56] anarlog (formerly Hyprnote) | fastrepl — https://github.com/fastrepl/anarlog
- [57] Meetily | Zackriya-Solutions — https://github.com/Zackriya-Solutions/meetily

From [GD]:
- [36] Overview of Pipecat — https://docs.pipecat.ai/pipecat/learn/overview
- [40] pipecat-ai/pipecat (GitHub) — https://github.com/pipecat-ai/pipecat
- [42] pipecat transcription-whisper.py example — https://github.com/pipecat-ai/pipecat/blob/main/examples/transcription/transcription-whisper.py
- [46] Transcriptions (turn management) | Pipecat — https://docs.pipecat.ai/api-reference/server/utilities/turn-management/transcriptions
- [38] Introduction | LiveKit Documentation — https://docs.livekit.io/agents/
- [39] livekit/agents (GitHub) — https://github.com/livekit/agents
- [48] multi-user-transcriber.py | livekit/agents — https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py
- [37] Lessons from implementing RAG in a real-time voice agent (LiveKit) | Medium — https://medium.com/@jorge.jarne/lessons-from-implementing-rag-in-a-real-time-voice-agent-livekit-43f0689bf565
- [27] Voice Agent Architecture: STT, LLM, TTS Pipelines Explained | LiveKit — https://livekit.com/blog/voice-agent-architecture-stt-llm-tts-pipelines-explained
