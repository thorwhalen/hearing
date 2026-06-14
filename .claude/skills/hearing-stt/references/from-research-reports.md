# STT engine — extracts from the June-2026 research reports

Condensed from the two reports in `hearing/misc/docs/`. Bracketed markers map to the URLs at the
bottom. The two reports number their references independently, so where a number would collide
the marker is tagged with its report: **`[DIY n]`** = the DIY report's reference *n*, **`[GD n]`**
= the GD report's reference *n*. A bare `[n]` inside a DIY-section block means `[DIY n]`.
Quotes/condensations only — see the full reports for surrounding context.

Source files:
- DIY report: `Meeting Transcription Apps & a DIY Real-Time Transcription Pipeline on macOS.md`
- GD report: `Meeting Transcription and AI Agents - GD Report.md`

---

## Concern 2 — The STT engine (pluggable facade) — DIY report, lines 110-135

> Because you'll facade this behind a clear interface (`transcribe(audio) -> segments` plus a
> streaming variant), the rest of the architecture doesn't care which engine sits behind it.

### Local / open-source (free, cost compute)
- **OpenAI Whisper** — reference model, 99 languages, batch-oriented (no native streaming, no
  native diarization, 25 MB API file limit). Large-v3 is the accuracy anchor.
- **whisper.cpp** — C/C++ port, runs well on CPU and Apple Metal; good for embedding. (DIY whisper.cpp prose is uncited; engine comparison: [DIY 34])
- **faster-whisper** (CTranslate2) — the practical default for self-hosting; much faster +
  lower memory than reference Whisper; int8 quantization; the base for many tools. [33]
- **WhisperX** — built on faster-whisper, adds **word-level timestamps + speaker diarization**
  (via pyannote) and better long-audio handling. The right pick for multi-speaker meeting
  transcription. [34]
- **distil-whisper** (distil-large-v3) — ~6x faster, ~49% smaller, within ~1% WER of Whisper. [35]
- **NVIDIA Parakeet** (TDT 0.6B v2/v3) — exceptionally fast and accurate. Parakeet-TDT-0.6B-v2
  reached **6.05% WER** on the HF Open ASR Leaderboard at RTFx 3386 (batch 128) [36]; v3 reports
  ~6.32% WER covering 25 European languages [37]. (A late-2025 paper ranks v2 ~10th across all
  decoder types, so "leaderboard-topping" claims are version- and date-sensitive [37].) Runs on
  Apple Silicon via MLX; now supported in MacWhisper.
- **NVIDIA Canary** — accuracy-focused; Canary-1B-v2 "outperforms Whisper-large-v3" at RTFx
  ~749 [37]. Slower than Parakeet but very accurate.
- **Moonshine** — small streaming-oriented model for edge/real-time; a RealtimeSTT backend. [38]
- **Apple Silicon / MLX paths**: **lightning-whisper-mlx** ("10x faster than Whisper CPP, 4x
  faster than current MLX Whisper implementation") [39]; **mlx-audio** (Whisper, Parakeet,
  VibeVoice-ASR with speaker labels, streaming) [40]; **Lightning-SimulWhisper** (MLX + CoreML,
  ~15x decoder / ~18x encoder speedup, runs medium/large-v3-turbo in real time on M2) [41]. One
  benchmark found plain MLX Whisper streaming disappointing on an M1 Air [42] — Apple-Silicon
  real-time streaming is comfortable from ~M2 up.

### Cloud STT APIs
- **OpenAI** — Whisper API and gpt-4o-transcribe at **$0.006/min**; gpt-4o-mini-transcribe at
  **$0.003/min**; new streaming model **gpt-realtime-whisper at $0.017/min** over the Realtime
  API (WebSocket/WebRTC) [DIY 6][DIY 43]. **gpt-4o-transcribe-diarize** adds built-in diarization; the
  plain transcribe models do *not* diarize [DIY 44]. ~$5 free credit.
- **Deepgram Nova-3** — streaming-first; **$0.0043/min batch, $0.0077/min streaming**; ~5.26%
  median WER (vendor) / ~18.3% on a hard third-party set; ~300 ms P50 latency; **$200 free credit
  (~45,000 min)** [DIY 4]. Diarization priced separately.
- **AssemblyAI Universal** — cheapest per-minute batch (**Universal-2 $0.0025/min / $0.15/hr**;
  Universal-3 Pro $0.0035/min); streaming via Universal-3; LeMUR for AI over audio; **$50 free
  credit (~185 hours)** [DIY 5].
- **Google Cloud Speech-to-Text** (Chirp) — ~$0.024/min streaming; 100+ languages; first 60
  min/month free [45].
- **Azure Speech** — ~$0.017/min real-time, ~$0.006/min batch; 140+ languages; 5 free hours [46].
- **Speechmatics** (Ursa) — ~$0.004–0.012/min depending on commit; strong multilingual/accents;
  8 free hours/month [47].
- **Rev.ai** — ~$0.02/min (some Standard tiers cheaper); good developer SDKs [48].

### How good is STT today? — DIY report, line 135
SOTA WER on clean English ~**5–6%** (Nova-3 ~5.26% [DIY 4], Parakeet v2 ~6.05% [DIY 36]). On hard,
noisy, accented audio real-world WER rises to mid-teens or higher (Nova-3 ~18.3% on a tough
third-party set [DIY 4]). For meetings (overlap, crosstalk, jargon) expect noticeably worse than the
clean-audio headline. Diarization and custom vocabulary matter as much as the base model.

---

## PRICING TABLE — Cloud STT (per-minute / per-hour) — DIY report, lines 137-149

| Provider / model | Batch $/min | Streaming $/min | ~$/hour | Free tier | Diarization | Notes |
|---|---|---|---|---|---|---|
| **AssemblyAI Universal-2** | $0.0025 | (Universal-3 Pro $0.0035) | $0.15 batch | $50 credit (~185 hrs) | Add-on | Cheapest batch; LeMUR |
| **Deepgram Nova-3** | $0.0043 | $0.0077 | $0.258 batch / $0.462 stream | $200 credit (~45k min) | Add-on | Streaming-first, low latency |
| **OpenAI gpt-4o-mini-transcribe** | $0.003 | — | $0.18 | ~$5 credit | No | Token-billed |
| **OpenAI gpt-4o-transcribe** | $0.006 | $0.017 (gpt-realtime-whisper) | $0.36 | ~$5 credit | Diarize variant | gpt-4o-transcribe-diarize for speakers |
| **Azure Speech** | ~$0.006 | ~$0.017 | ~$1.00 RT | 5 hrs | Yes | 140+ langs |
| **Speechmatics Ursa** | ~$0.004–0.012 | similar | ~$0.24+ | 8 hrs/mo | Yes | Strong accents |
| **Google STT (Chirp)** | ~$0.016–0.024 | ~$0.024 | ~$1.44 | 60 min/mo | Yes | 100+ langs |
| **Rev.ai** | ~$0.02 | available | ~$1.20 | trial | Yes | Simple SDKs |
| **Local (Whisper/Parakeet/etc.)** | $0 (compute) | $0 (compute) | electricity | unlimited | via pyannote/WhisperX | Apple Silicon capable |

---

## Recommendations (staged) — DIY report, lines 181-191

- **Stage 0 — Use an app while you build.** Krisp (unlimited free transcription) or Granola
  (export before history window expires) for working transcripts today. If privacy/on-device
  matters, MacWhisper Pro (~$69 once) for diarized local file transcription.
- **Stage 1 — Batch DIY (highest value/effort ratio).** Capture with BlackHole + Aggregate
  Device (mic ch 1-2, system ch 3-4) via sounddevice. After the meeting, run **WhisperX**
  (faster-whisper + pyannote) on the system channel for a diarized transcript; tag the mic
  channel as "me." Diarized, speaker-attributed transcripts entirely on-device. Facade the STT
  call so you can swap in a cloud API later.
- **Stage 2 — Live streaming.** Add RealtimeSTT (faster-whisper or Parakeet-MLX backend) +
  silero-vad; emit finalized utterances to an `asyncio.Queue`. Use the channel split for instant
  "me vs them."
- **Stage 3 — Agent loop.** Consume the queue; start with post-utterance triggers (notes,
  suggested questions, RAG). Add OpenAI Realtime API or Deepgram streaming only if local
  latency/accuracy is insufficient.

> **Decision thresholds:** Stay local if Apple-Silicon latency is acceptable (M2+ handles
> medium/turbo in real time) and cost-sensitivity is high. Switch a stage to cloud STT when WER
> on your meetings exceeds tolerance or you need more than a couple of concurrent streams; at
> sustained high volume (~100k+ min/month) self-hosting on a GPU becomes cheaper than per-minute
> cloud [DIY 6]. Prefer **Deepgram** for low-latency streaming, **AssemblyAI** for cheapest batch,
> **OpenAI gpt-4o-transcribe-diarize** if you want managed diarization.

---

## Caveats — DIY report, lines 193-199

- Free-tier limits change frequently; figures reflect early-to-mid 2026 reporting and several
  come from vendor/SEO blogs — verify current caps before committing.
- "Bot-free" (Granola, Krisp) ≠ "local": those still process audio in the cloud. Only MacWhisper
  / Meetily / Hyprnote keep audio fully on-device.
- macOS may silently resample virtual-device audio; aggregate devices need matching sample rates.
- WER headline numbers are clean-audio, single-speaker, often vendor-reported; real meeting
  accuracy is lower.
- **Some OpenAI transcribe model versions are scheduled for retirement around June 2026 — design
  the facade to swap model names easily** [55].

---

## Engines & hardware — GD report, lines 90-104, 242-245

- **Whisper.cpp** — highly optimized C/C++ port; minimal memory, rapid inference; HW accel via
  Vulkan + Apple Metal + NVIDIA CUDA; runs medium / large-v3-turbo at low VRAM. Ideal for
  resource-constrained / edge / local dev workstations. [GD 28]
- **Faster-Whisper** — replaces vanilla PyTorch with CTranslate2 (weight quantization + speed
  optimizations); up to **4x** the speed of original Whisper while dramatically reducing VRAM;
  preferred backend for modern Python OSS projects. (definition: [GD 5]; "4x" claim: [GD 4])
- **WhisperLive** — production-grade real-time streaming Whisper; local/Dockerized WebSocket
  server, raw PCM in, real-time segments with word-level timestamps, custom vocabulary, active
  speaker diarization; backends faster-whisper / NVIDIA TensorRT-LLM / Intel OpenVINO. [GD 32]

> **Hardware and VRAM Management.** A local Whisper large-v3 / large-v3-turbo for high-accuracy
> STT requires approximately **6–10 GB of VRAM**, with additional VRAM for local LLM inference
> (Ollama). For constrained infrastructure, use INT8-quantized Whisper via Faster-Whisper, or C++
> runtimes like Whisper.cpp. Alternatively a local WhisperLive server on a dedicated NVIDIA-GPU
> workstation provides an enterprise-wide real-time endpoint, offloading end-user laptops. [GD 5][GD 32]

(Note: the GD report renders the exact VRAM figures as images, so the "~6–10 GB" range is read
from the surrounding GD prose and cross-checked against the companion DIY report. Verify against
your target model before sizing.)

---

## REFERENCES (URLs)

URLs grouped by source report. Numbers are each report's own reference numbers (the two reports
number independently — `[DIY 4]` and `[GD 4]` are different sources).

### DIY report (`Meeting Transcription Apps & a DIY Real-Time Transcription Pipeline on macOS.md`)

- [DIY 4] Deepgram Pricing 2026: Nova-3 Breakdown | BrassTranscripts — https://brasstranscripts.com/blog/deepgram-pricing-per-minute-2025-real-time-vs-batch
- [DIY 5] Speech-to-Text API Pricing (June 2026) | BuildMVPFast — https://www.buildmvpfast.com/api-costs/transcription
- [DIY 6] OpenAI Transcription & Whisper API Pricing Calculator | Costgoat — https://costgoat.com/pricing/openai-transcription
- [DIY 33] faster-whisper | GitHub – SYSTRAN — https://github.com/SYSTRAN/faster-whisper
- [DIY 34] Whisper.cpp vs faster-whisper 2026 (WhisperX, distil-whisper) | PromptQuorum — https://www.promptquorum.com/power-local-llm/local-whisper-stt-comparison-2026
- [DIY 35] 2025 Edge Speech-to-Text Model Benchmark | Ionio — https://www.ionio.ai/blog/2025-edge-speech-to-text-model-benchmark-whisper-vs-competitors
- [DIY 36] NVIDIA Speech AI Models Deliver Industry-Leading Accuracy | NVIDIA Technical Blog — https://developer.nvidia.com/blog/nvidia-speech-ai-models-deliver-industry-leading-accuracy-and-performance/
- [DIY 37] The Top Open Source Speech-to-Text (STT) Models in 2025 | Modal — https://modal.com/blog/open-source-stt
- [DIY 38] RealtimeSTT | GitHub – KoljaB — https://github.com/KoljaB/RealtimeSTT
- [DIY 39] lightning-whisper-mlx | GitHub – mustafaaljadery — https://github.com/mustafaaljadery/lightning-whisper-mlx
- [DIY 40] mlx-audio | GitHub – Blaizzy — https://github.com/Blaizzy/mlx-audio
- [DIY 41] Lightning-SimulWhisper | GitHub – altalt-org — https://github.com/altalt-org/Lightning-SimulWhisper
- [DIY 42] Streaming with Whisper in MLX vs. Faster-Whisper | Wei Lu (Medium) — https://medium.com/@GenerationAI/streaming-with-whisper-in-mlx-vs-faster-whisper-vs-insanely-fast-whisper-37cebcfc4d27
- [DIY 43] Realtime transcription | OpenAI API — https://developers.openai.com/api/docs/guides/realtime-transcription
- [DIY 44] GPT-4o Transcribe Diarize Model | OpenAI API — https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize
- [DIY 45] Best Speech to Text APIs 2025 (Pricing per Minute) | VocaFuse — https://vocafuse.com/blog/best-speech-to-text-api-comparison-2025/
- [DIY 46] Azure Speech-to-Text: The Real Cost | BrassTranscripts — https://brasstranscripts.com/blog/azure-speech-services-pricing-2025-microsoft-ecosystem-costs
- [DIY 47] Pricing for our Speech API services | Speechmatics — https://www.speechmatics.com/pricing
- [DIY 48] Microsoft Azure Speech Recognition vs. Rev AI | Rev — https://www.rev.com/resources/microsoft-azure-speech-recognition-vs-rev-ai-speech-to-text-api
- [DIY 55] Azure OpenAI Realtime API — transcribe model retirements (June 2026) | Microsoft Q&A — https://learn.microsoft.com/en-us/answers/questions/5864686/azure-openai-realtime-api-gpt-4o-transcribe-diariz

### GD report (`Meeting Transcription and AI Agents - GD Report.md`)

- [GD 4] GitHub – Zackriya-Solutions/meetily (privacy-first AI meeting assistant; source of the "4x faster" claim) — https://github.com/Zackriya-Solutions/meetily
- [GD 5] GitHub – paberr/ownscribe (local-first transcription + summarization CLI; faster-whisper definition & ~6–10 GB VRAM figures) — https://github.com/paberr/ownscribe
- [GD 28] Best open source api for speech to text transcriptions … | Reddit r/LocalLLaMA (whisper.cpp HW-accel discussion) — https://www.reddit.com/r/LocalLLaMA/comments/1rybql4/best_open_source_api_for_speech_to_text/
- [GD 32] collabora/WhisperLive — A nearly-live implementation of OpenAI's Whisper | GitHub — https://github.com/collabora/WhisperLive
