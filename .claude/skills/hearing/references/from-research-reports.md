# Source extracts for the `hearing` orchestrator skill

Curated slices of the two research reports (dated June 2026) that justify the
project **vision**, the **four-layer architecture**, and the **milestone
roadmap** this orchestrator routes around. `[DIY]` = "Meeting Transcription Apps
& a DIY Real-Time Transcription Pipeline on macOS"; `[GD]` = "Meeting
Transcription and AI Agents — GD Report". Both live in `misc/docs/`. Bracketed
`[n]` markers are the originals' citation numbers; matching URLs are listed at
the bottom. Per-layer depth lives in each sibling skill's own `references/`.

---

## [DIY] The four-concern decomposition (TOPIC 2 intro) — THE architecture spine

> # TOPIC 2: Building Your Own Transcription + Real-Time Agent Pipeline
>
> Architecturally this decomposes into four separable concerns, each swappable
> behind a clear interface:
> 1. **Audio capture** (mic + system audio) → produces audio frames
> 2. **STT engine** (the pluggable facade) → local or cloud, batch or streaming → produces text
> 3. **Diarization / speaker ID** (separate concern) → labels who spoke
> 4. **Agent layer** → consumes the transcript stream and does things

Four facades, dependency-injected. This is what every hearing-* skill implements
against; the orchestrator routes a task to the concern that owns it.

---

## [DIY] The channel-split insight (TL;DR + Concern 1) — the project's cheapest win

> Keep mic and system audio as separate channels — that channel split is itself
> the elegant way to know when *you* are speaking.

> Capture with **BlackHole + Aggregate Device** (mic ch 1-2, system ch 3-4) via
> **sounddevice**. … run **WhisperX** (faster-whisper + pyannote) on the system
> channel for a diarized transcript; tag the mic channel as "me."

"Me vs them" speaker attribution for free, no voice model — diarize only the
system channel. (Owned by [[hearing-audio-capture]] + [[hearing-diarization]].)

---

## [DIY] Recommendations (staged) — THE milestone roadmap (verbatim)

> **Stage 0 — Use an app while you build.** Run **Krisp** (unlimited free
> transcription) or **Granola** (export notes before the history window
> expires) so you have working transcripts today. If privacy/on-device matters,
> buy **MacWhisper Pro** (~$69 once) for diarized local file transcription.
>
> **Stage 1 — Batch DIY (highest value/effort ratio).** Capture with **BlackHole
> + Aggregate Device** (mic ch 1-2, system ch 3-4) via **sounddevice**. After the
> meeting, run **WhisperX** (faster-whisper + pyannote) on the system channel for
> a diarized transcript; tag the mic channel as "me." This gets you diarized,
> speaker-attributed transcripts entirely on-device. Facade the STT call so you
> can swap in a cloud API later.
>
> **Stage 2 — Live streaming.** Add **RealtimeSTT** (faster-whisper or
> Parakeet-MLX backend) + **silero-vad**; emit finalized utterances to an
> `asyncio.Queue`. Use the channel split for instant "me vs them."
>
> **Stage 3 — Agent loop.** Consume the queue in your agent framework; start with
> post-utterance triggers (notes, suggested questions, RAG). Add the **OpenAI
> Realtime API** or **Deepgram streaming** only if local latency/accuracy is
> insufficient.
>
> **Decision thresholds:** Stay local if Apple-Silicon latency is acceptable
> (M2+ handles medium/turbo in real time) and cost-sensitivity is high. Switch a
> stage to cloud STT when WER on your meetings exceeds tolerance or you need more
> than a couple of concurrent streams; at sustained high volume (~100k+
> min/month) self-hosting on a GPU becomes cheaper than per-minute cloud [6].
> Prefer **Deepgram** for low-latency streaming, **AssemblyAI** for cheapest
> batch, **OpenAI gpt-4o-transcribe-diarize** if you want managed diarization.

**Orchestrator mapping of the report's "Stages" to this project's milestones:**
the report's Stage 1 = **Milestone 1 (BATCH)**; the report's Stages 2+3 = the
additive **Milestone 2 (LIVE)**. Build batch first; live reuses the same STT and
agent interfaces, swapping only the source + trigger cadence.

---

## [DIY] Caveats (the project-management risk list)

> - Free-tier limits change frequently; figures reflect early-to-mid 2026
>   reporting … verify current caps before committing.
> - "Bot-free" (Granola, Krisp) ≠ "local": those still process audio in the
>   cloud. Only **MacWhisper / Meetily / Hyprnote** keep audio fully on-device.
> - Recording consent is your responsibility; laws vary and Otter faced a 2025
>   consent-related class action [12].
> - macOS may silently resample virtual-device audio; aggregate devices need
>   matching sample rates [8].
> - WER headline numbers are clean-audio, single-speaker, often vendor-reported;
>   real meeting accuracy is lower.
> - Some OpenAI transcribe model versions are scheduled for retirement around
>   June 2026 — design the facade to swap model names easily [55].

---

## [GD] Strategic Architectural Recommendations (frameworks for the LIVE milestone)

> - **For Building Custom real-time Agentic Applications**: developers building
>   voice-enabled applications … should utilize **Pipecat** or **LiveKit
>   Agents**.3 Pipecat should be selected when building highly customized
>   voice-first pipelines requiring precise control over frame processing,
>   modular service swapping, and linear Python structures.3 LiveKit Agents is
>   the optimal choice when the system requires production-grade WebRTC media
>   routing, multi-participant room architectures … and a battle-tested agent
>   server orchestration layer.3
> - **For Absolute Data Sovereignty and Local Environments**: … deploy
>   **Meetily** or **ownscribe**.4 Operating 100% locally on-device … eliminate
>   cloud API costs … run indefinitely without subscription fees.4

The GD report also models the live latency budget (VAD + STT + LLM TTFT +
tool/RAG retrieval + TTS + transport) and notes that naive VAD over-triggers on
mid-sentence pauses — semantic turn detection fixes it. That detail is owned by
[[hearing-live-pipeline]]; here it only justifies *deferring* the live milestone
until the stationary batch target is solid.

---

## REFERENCES (URLs for the `[n]` markers used above)

- [6] [OpenAI Transcription & Whisper API Pricing Calculator | Costgoat](https://costgoat.com/pricing/openai-transcription)
- [8] [BlackHole | GitHub – ExistentialAudio](https://github.com/ExistentialAudio/BlackHole)
- [12] [Otter.ai Free vs Pro | AFFiNE](https://affine.pro/blog/otter-ai-free-vs-pro)
- [55] [Azure OpenAI Realtime API — transcribe model retirements (June 2026) | Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5864686/azure-openai-realtime-api-gpt-4o-transcribe-diariz)
- [GD-3] Pipecat / LiveKit framework recommendation, GD Report "Strategic Architectural Recommendations".
- [GD-4] Meetily / ownscribe local-first recommendation, GD Report "Strategic Architectural Recommendations".
