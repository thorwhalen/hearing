# Source passages — streaming / live pipeline

Condensed from the two `hearing` research reports (dated June 2026). Bracketed
markers below use **this file's** local numbering `[1]…[8]`; the matching URLs
are in the REFERENCES section at the bottom. Original report citation numbers
are noted inline in parentheses for traceability.

---

## From the DIY pipeline report — "Concern 4: Live / streaming + the real-time agent loop" (lines 158–179)

### Streaming STT building blocks (Python)

- **RealtimeSTT** (`KoljaB/RealtimeSTT`) — robust low-latency library: VAD (WebRTC + Silero), wake words, selectable engines via extras (faster-whisper default, plus whisper.cpp, Parakeet, Moonshine, etc.), callbacks for realtime text. Can take mic input or fed audio chunks (`feed_audio`). *The most batteries-included starting point.* (report ref 38 → `[1]`)
- **whisper_streaming** (`ufal/whisper_streaming`) — long-form streaming with a **LocalAgreement** policy; multiple backends (faster-whisper, mlx-whisper, OpenAI API). Being superseded by **SimulStreaming** (faster, **AlignAtt** policy) by the same author. (report ref 52 → `[2]`)
- **WhisperLive** (`collabora/WhisperLive`) — near-live Whisper over WebSocket; faster-whisper/TensorRT/OpenVINO backends; optional real-time speaker ID via pyannote embeddings (online cosine-similarity clustering); browser + iOS clients. (report ref 53 → `[3]`)
- **VAD for chunking** — **silero-vad** (neural, accurate) and **webrtcvad** (lightweight). VAD detects speech boundaries so you only send meaningful chunks to STT; pattern is **VAD -> buffer utterance -> transcribe -> emit**. (report ref 54 → `[5]`)
- **OpenAI Realtime API** — managed streaming transcription session (`type: "transcription"`, model `gpt-realtime-whisper`) over WebSocket/WebRTC, returning incremental deltas. Caveats: deltas may lag until end of turn; for diarization you need `gpt-4o-transcribe-diarize`; some older transcribe model versions are slated for retirement around June 2026. (report refs 43/44/55 → `[4]`)

### Piping the transcript into an agent

The streaming STT emits incremental/final segments onto a queue (`asyncio.Queue`).
An agent consumer reads finalized utterances and triggers actions — running notes,
suggested questions, RAG over related docs. Key considerations:

- **Granularity**: act on *finalized* segments (after VAD turn-end) to avoid churning on partial text; **word-level timestamps** (WhisperX / Whisper `word_timestamps=True`) let you trigger on keywords mid-utterance.
- **Latency budget**: streaming STT adds a few hundred ms to ~1–2 s; the LLM call adds more. For "surface a doc" tasks that's fine; for live captions keep the STT chunk small.
- **Backpressure / decoupling**: keep capture, STT, diarization, and agent as **separate async tasks** so a slow LLM call never stalls audio capture.
- **Speaker context**: feed the channel-derived "me vs them" label plus diarization labels into the agent prompt so it knows who asked what.

### Staged plan (lines 187–189)

- **Stage 2 — Live streaming.** Add **RealtimeSTT** (faster-whisper or Parakeet-MLX backend) + **silero-vad**; emit finalized utterances to an `asyncio.Queue`. Use the channel split for instant "me vs them."
- **Stage 3 — Agent loop.** Consume the queue in your agent framework; start with post-utterance triggers (notes, suggested questions, RAG). Add the **OpenAI Realtime API** or **Deepgram streaming** only if local latency/accuracy is insufficient.

---

## From the GD report — "Real-Time Open-Source STT Engines" + "Engineering Real-Time Agentic Pipelines" (lines 90–179)

### WhisperLive (lines 102–104)

WhisperLive provides a production-grade, real-time streaming implementation of
Whisper. Running as a local or Dockerized server, it establishes persistent
**WebSocket** connections, accepting raw PCM audio streams and returning real-time
transcription segments with **word-level timestamps, custom vocabulary support,
and active speaker diarization**. Backends: Faster-Whisper, NVIDIA TensorRT-LLM,
Intel OpenVINO. (report ref 32; surfaces in DIY report too → `[3]`)

### Pipecat frame-based pipeline (lines 110–179)

Pipecat (by Daily) is a modular, event-driven Python framework. It processes
streaming multimodal data as discrete **Frames** flowing through a directed
pipeline of **Frame Processors**:

```
[ User Audio Input ]
        │
        ▼
   Transport.in ──(Audio Frames)──▶ VADProcessor (Silero) ──(VAD-chunked audio)──▶
        STTService (Whisper / Deepgram) ──(Transcription Frames)──▶ LiveAgent (custom FrameProcessor)
```

To pipeline the transcript to an analytical agent **without interrupting the core
loop**, implement a custom `FrameProcessor` that intercepts text frames and
fires them at the agent non-blocking:

```python
class RealTimeAgentPipeline(FrameProcessor):
    """Intercepts completed transcription frames and pipelines them
    asynchronously to a background agent without blocking the audio pipeline."""
    def __init__(self, agent_client):
        super().__init__()
        self.agent = agent_client

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            asyncio.create_task(self._route_to_agent(frame.text, frame.timestamp))  # fire-and-forget
        elif isinstance(frame, InterimTranscriptionFrame):
            pass  # optional: partial tokens for keyword spotting
        await self.push_frame(frame, direction)  # forward downstream

    async def _route_to_agent(self, text, timestamp):
        try:
            await self.agent.analyze_segment_async(text, timestamp)
        except Exception as e:
            print(f"Agent pipeline routing failed: {e}")  # don't crash the media stream
```

Pipecat manages context via `LLMContextAggregatorPair`; turn events
`on_user_turn_stopped` / `on_assistant_turn_stopped` emit a **complete turn
transcript** — ideal for sending compiled segment payloads to external APIs.
(report refs 3, 36, 40, 42, 43, 46 → `[6][7]`)

### LiveKit Agents (lines 181–219)

WebRTC-native room model; agents are stateful server-side participants. For
multi-speaker scenarios, a supervisor spawns an **isolated `AgentSession` per
participant**, each with its own VAD + STT plugin (e.g. Deepgram Nova-3),
transcribing without mixing streams. Transcripts are published to the room over
the `lk.transcription` text stream. RAG: vectorize transcript -> match against
Qdrant -> append chunks to the LLM system prompt; **offload vector search to a
separate async task and cache** to keep retrieval latency off the audio stream.
(report refs 3, 25, 37, 38, 47, 48, 49 → `[6][8]`)

### Latency modeling and turn detection (lines 225–240)

Sequential "cascaded" pipelines (wait for full sentence -> transcribe -> LLM ->
synthesize) introduce unnatural latency. Streaming pipelines stream partial STT,
stream LLM tokens, and start TTS on the first tokens. Cumulative latency:

```
L_total ≈ L_vad + L_stt + L_llm_ttft + L_tool/rag + L_tts + L_transport
```

- `L_vad` — VAD threshold/turn-end (~100–500 ms)
- `L_stt` — STT processing (~100 ms–2 s)
- `L_llm_ttft` — LLM time-to-first-token, streaming (~few hundred ms)
- `L_tool/rag` — tool call / vector retrieval (tens of ms – seconds)
- `L_tts` — TTS time-to-first-chunk (~hundreds of ms)
- `L_transport` — WebRTC routing (~tens of ms)

Optimal streaming pipelines hit **~hundreds of ms to ~1–2 s** end-to-end;
un-optimized RAG / heavy on-device embeddings push past ~2 s, causing
conversational overlap and sluggish turn-taking.

**Semantic turn detection:** naive VAD-based turn detection struggles with
mid-sentence pauses, triggering premature interruptions when a user stops to
think. Modern implementations deploy **semantic turn-detection classifiers**
(e.g. LiveKit's transformer models) that analyze the linguistic meaning of the
partial transcript to decide whether the utterance is structurally complete
before signaling the LLM. (report refs 3, 25, 27, 37 → `[6]`)

---

## REFERENCES

1. [RealtimeSTT — GitHub (KoljaB)](https://github.com/KoljaB/RealtimeSTT)
2. [whisper_streaming — GitHub (ufal)](https://github.com/ufal/whisper_streaming) (SimulStreaming is the same author's successor)
3. [WhisperLive — GitHub (collabora)](https://github.com/collabora/WhisperLive)
4. [Realtime transcription | OpenAI API](https://developers.openai.com/api/docs/guides/realtime-transcription) · [gpt-4o-transcribe-diarize model](https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize) · [transcribe-model retirements (~June 2026), Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5864686/azure-openai-realtime-api-gpt-4o-transcribe-diariz)
5. [Whisper for real-time/streaming — openai/whisper Discussion #2](https://github.com/openai/whisper/discussions/2) (VAD chunking pattern)
6. [Voice Agent Architecture: STT, LLM, TTS Pipelines Explained — LiveKit](https://livekit.com/blog/voice-agent-architecture-stt-llm-tts-pipelines-explained) · [Voice agents — LiveKit](https://livekit.com/voice-agents) · [Vapi vs Pipecat vs LiveKit (2026) — Inworld AI](https://inworld.ai/resources/vapi-vs-pipecat-vs-livekit)
7. [Pipecat overview](https://docs.pipecat.ai/pipecat/learn/overview) · [Pipecat Speech-to-Text](https://docs.pipecat.ai/pipecat/learn/speech-to-text) · [pipecat-ai/pipecat — GitHub](https://github.com/pipecat-ai/pipecat) · [transcription-whisper.py example](https://github.com/pipecat-ai/pipecat/blob/main/examples/transcription/transcription-whisper.py) · [Pipecat Transcriptions / turn-management](https://docs.pipecat.ai/api-reference/server/utilities/turn-management/transcriptions)
8. [LiveKit Agents docs](https://docs.livekit.io/agents/) · [livekit/agents — GitHub](https://github.com/livekit/agents) · [multi-user-transcriber example](https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py) · [Lessons from RAG in a real-time voice agent (LiveKit) — Jorge Jarne](https://medium.com/@jorge.jarne/lessons-from-implementing-rag-in-a-real-time-voice-agent-livekit-43f0689bf565)
