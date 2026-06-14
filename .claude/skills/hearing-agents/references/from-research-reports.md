# Source extracts — Agent layer

Condensed from the two research reports (dated June 2026). Bracketed `[n]` markers preserved; matching URLs at the bottom of each section.

---

## A. DIY pipeline report — "Piping the transcript into an agent" and OSS to fork

> **Piping the transcript into an agent.** At the architecture level: the streaming STT emits incremental/final segments onto a queue (`asyncio.Queue` or similar). An agent consumer reads finalized utterances and triggers actions — running notes, suggested questions, RAG over related docs. Integration points / considerations:
>
> - **Granularity**: act on *finalized* segments (after VAD turn-end) to avoid churning on partial text; word-level timestamps (WhisperX / Whisper `word_timestamps=True`) let you trigger on keywords mid-utterance [54].
> - **Latency budget**: streaming STT adds a few hundred ms to ~1–2 s; the LLM call adds more. For "surface a doc" tasks that's fine; for live captions keep the STT chunk small.
> - **Backpressure / decoupling**: keep capture, STT, diarization, and agent as separate async tasks so a slow LLM call never stalls audio capture.
> - **Speaker context**: feed the channel-derived "me vs them" label plus diarization labels into the agent prompt so it knows who asked what.

> **Existing open-source projects to study or fork**
> - **Hyprnote** (now also **anarlog**, `fastrepl/anarlog`, MIT) — local-first meeting notetaker; real-time transcription with local (Whisper/Parakeet) or cloud STT, speaker ID, captures system audio from any app, MCP server so Claude/ChatGPT can read/write notes [56]. Excellent reference for your exact goal.
> - **Meetily** (`Zackriya-Solutions/meetily`, MIT) — Rust/Tauri, 100% local, Parakeet/Whisper live transcription, captures microphone + system audio simultaneously with intelligent ducking, Ollama summarization, pluggable AI (local/BYOK/hosted) [57].
> - **Glass** (open-source Cluely alternative) and **Pluely** (`iamsrikanthnani/pluely`, Tauri, ~10 MB) — real-time meeting "copilot" overlays; Pluely separates system audio from mic and does live STT (Whisper) feeding an LLM [58][59]. **Natively** (`Natively-AI-assistant`) adds local RAG + dual audio channels + meeting history [60]. Good references for the live-agent overlay pattern.
> - **huggingface/speech-to-speech** — full cascaded STT→LLM→TTS pipeline with MLX optimizations for Mac [62], if you ever want the voice-response loop.

> **Staged recommendation (Stage 3 — Agent loop):** Consume the queue in your agent framework; start with post-utterance triggers (notes, suggested questions, RAG). Add the OpenAI Realtime API or Deepgram streaming only if local latency/accuracy is insufficient.

**Channel trick for me/them (from Concern 3):** the BlackHole+Aggregate setup keeps your mic on one channel and system audio (everyone else) on another, so you already know who's local — just measure which channel has energy. Mic channel = you; system channel = remote participants [8][30]. Far simpler and more reliable than fingerprinting. Run diarization on the *system* channel; treat the *mic* channel as a known speaker ("me").

### URLs
- [8] BlackHole — https://github.com/ExistentialAudio/BlackHole
- [30] How to Record Mac System Audio Using Python and BlackHole — https://medium.com/@mehsamadi/how-to-record-mac-system-audio-using-python-and-blackhole-a45d06eaad0f
- [54] Possible to use Whisper for real-time / streaming tasks? (openai/whisper discussion) — https://github.com/openai/whisper/discussions/2
- [56] anarlog (formerly Hyprnote) — https://github.com/fastrepl/anarlog
- [57] Meetily — https://github.com/Zackriya-Solutions/meetily
- [58] Cluely vs Glass and Open Source Marketing — https://hyperlush.com/cluely-vs-glass/
- [59] Pluely — https://github.com/iamsrikanthnani/pluely
- [60] Natively — https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant
- [62] Mac OS and MLX Optimizations (huggingface/speech-to-speech) — https://deepwiki.com/huggingface/speech-to-speech/7.3-mac-os-and-mlx-optimizations

---

## B. GD report — Pipecat frame pipeline + the non-blocking intercept snippet

> **Pipecat** is a modular, event-driven, open-source Python framework created by Daily [3]. It processes streaming multimodal data (audio, text, images, video) as discrete *Frames* flowing through a directed pipeline of *Frame Processors* [3]. Raw audio → `Transport.in` → `VADProcessor` (Silero VAD) → `STTService` (Whisper/Deepgram) → custom `LiveAgent` FrameProcessor.

> To pipeline the transcription stream in real-time to an analytical agent without interrupting the core conversational loop, implement a custom `FrameProcessor` to intercept the text frames [42]. The following demonstrates a non-blocking transcription logger that intercepts `TranscriptionFrame` objects to run real-time logging, leaving the primary pipeline to process downstream functions [42]:

```python
import asyncio
from pipecat.frames.frames import Frame, InterimTranscriptionFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

class RealTimeAgentPipeline(FrameProcessor):
    """Intercepts completed transcription frames and pipelines them asynchronously
    to a background analysis agent without blocking the real-time audio pipeline."""
    def __init__(self, agent_client):
        super().__init__()
        self.agent = agent_client

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Always call the parent to maintain frame lifecycle
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            # Non-blocking fire-and-forget to prevent pipeline lag
            asyncio.create_task(self._route_to_agent(frame.text, frame.timestamp))
        elif isinstance(frame, InterimTranscriptionFrame):
            # Optional: handle partial tokens for keyword spotting
            pass
        # Forward downstream to maintain conversational continuity
        await self.push_frame(frame, direction)

    async def _route_to_agent(self, text: str, timestamp: float):
        try:
            await self.agent.analyze_segment_async(text, timestamp)
        except Exception as e:
            # Log errors from external RAG/API without crashing the media stream
            print(f"Agent pipeline routing failed: {e}")
```

> Pipecat manages conversation context through structured aggregators (`LLMContextAggregatorPair`) [46]. When a user or assistant finishes speaking, `on_user_turn_stopped` / `on_assistant_turn_stopped` emit a complete turn transcript [46]. These structured turn events are ideal for sending compiled segment payloads to external APIs/microservices via async HTTP, ensuring real-time note-taking proceeds concurrently [46].

> **LiveKit Agents** operates on a WebRTC-native room model, treating AI agents as stateful, programmable server-side participants that join virtual rooms alongside human users [3]. For multi-user scenarios, a supervisor agent server monitors the WebRTC room [38]; when a participant connects it spawns an isolated `AgentSession` bound to that participant's identity [48], configured with a VAD + dedicated STT plugin (e.g., Deepgram Nova-3), transcribing without mixing streams [48]. The transcript is published back on the unified `lk.transcription` text stream topic [47].

---

## C. GD report — Real-time RAG integration

> To perform real-time RAG or call external tools (document repositories, web search, contextual notes) during a meeting, the agent uses semantic search or tool-calling hooks [37].
>
> Flow (LiveKit Room → STT Agent → AgentSession context logic → Retrieval Layer (LlamaIndex / Qdrant) → Downstream LLM):
>
> When designing an open-source real-time RAG voice agent (LiveKit Agents + Qdrant vector DB + LlamaIndex data framework), configure the agent's core routing logic to intercept transcription segments [37]. The agent checks the transcribed text for semantic intent or specific entity triggers [27]. If a query requires contextual documentation, the text is vectorized and matched against Qdrant's vector collection [37]. Retrieved chunks are appended to the LLM's system prompt dynamically [37].
>
> **To prevent retrieval latencies from blocking the audio stream, the vector search is offloaded to a separate, asynchronous task thread, and the resulting context is cached to prevent redundant, expensive lookups [37].**

---

## D. GD report — Latency model and turn detection

> Sequential "cascaded" pipelines (wait for full sentence → transcribe → LLM → synthesize) introduce significant, unnatural latencies [27]. Production-grade agents use streaming pipelines where STT streams partial results, the LLM streams tokens, and TTS begins on the first few tokens [25].
>
> Cumulative real-time latency ≈ VAD threshold + STT processing + LLM time-to-first-token (streaming) + tool/vector-DB/document-search execution + TTS time-to-first-chunk + WebRTC transport delay. Under optimal conditions a standard streaming pipeline achieves natural conversation flow, but **incorporating extensive, un-optimized RAG queries or heavy on-device embeddings pushes latency past comfortable bounds, causing conversational overlap and sluggish turn-taking [37].**
>
> Standard VAD-based turn detection struggles with mid-sentence pauses, triggering premature interruptions when a user stops to think [27]. Modern implementations solve this with **semantic turn-detection classifiers** that analyze the linguistic meaning of the partial transcript to decide if the utterance is structurally complete before signaling the LLM [27].

> **Pluggable-AI recommendation:** Meetily / ownscribe run 100% locally with pluggable AI (local / BYOK / hosted) [4][5]. For building custom real-time agentic apps, use Pipecat (precise control over frame processing, modular service swapping, linear Python) or LiveKit Agents (production WebRTC, multi-participant rooms, telephony) [3].

### URLs
- [3] Vapi vs Pipecat vs LiveKit: Voice Agent Frameworks Compared (2026) — https://inworld.ai/resources/vapi-vs-pipecat-vs-livekit
- [4] Meetily (GitHub) — https://github.com/Zackriya-Solutions/meetily
- [5] ownscribe (GitHub) — https://github.com/paberr/ownscribe
- [25] Voice agents | LiveKit — https://livekit.com/voice-agents
- [27] Voice Agent Architecture: STT, LLM, and TTS Pipelines Explained | LiveKit — https://livekit.com/blog/voice-agent-architecture-stt-llm-tts-pipelines-explained
- [36] Overview of Pipecat — https://docs.pipecat.ai/pipecat/learn/overview
- [37] Lessons from implementing RAG in a real-time voice agent (LiveKit) — https://medium.com/@jorge.jarne/lessons-from-implementing-rag-in-a-real-time-voice-agent-livekit-43f0689bf565
- [38] Introduction | LiveKit Documentation — https://docs.livekit.io/agents/
- [42] pipecat transcription-whisper example — https://github.com/pipecat-ai/pipecat/blob/main/examples/transcription/transcription-whisper.py
- [46] Transcriptions | Pipecat (turn management) — https://docs.pipecat.ai/api-reference/server/utilities/turn-management/transcriptions
- [47] Transcription text streams for >1 participant (livekit/agents issue #3657) — https://github.com/livekit/agents/issues/3657
- [48] livekit multi-user-transcriber example — https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py
