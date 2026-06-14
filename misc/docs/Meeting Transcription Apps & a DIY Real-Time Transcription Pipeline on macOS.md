# Meeting Transcription Apps & a DIY Real-Time Transcription Pipeline on macOS

*Author: Thor Whalen — June 14, 2026*

## TL;DR
- For free/freemium meeting transcription on a Mac, the best picks are **Granola** (bot-free, unlimited free meetings, 14–30 day history cap), **Krisp** (unlimited free transcription, bot-free), **tl;dv** and **Fathom** (most generous free recording tiers), and **Otter.ai** (300 free min/month, 30-min cap per conversation [1]). ChatGPT's own Record mode is paid-only, English-first, and has no speaker diarization [2][3].
- For a DIY pipeline, treat the **STT engine as a pluggable facade**: behind it sit local models (Whisper / faster-whisper / WhisperX / Parakeet on Apple Silicon via MLX) or cloud APIs — Deepgram Nova-3 at **$0.0043/min batch / $0.0077/min streaming** [4], AssemblyAI Universal-2 at **$0.0025/min ($0.15/hr)** [5], OpenAI gpt-4o-transcribe at **$0.006/min** [6]. Diarization is a separate concern (pyannote.audio 3.1) [7].
- The hard part on macOS is **system-audio capture**: use BlackHole + an Aggregate Device (proven) or Core Audio taps via AudioTee (native, macOS 14.2+) [8][9]. Keep mic and system audio as separate channels — that channel split is itself the elegant way to know when *you* are speaking.

---

# TOPIC 1: Free / Freemium Meeting Transcription Apps

## The ChatGPT Record-mode baseline
ChatGPT Record mode is a macOS-desktop-app feature that records, transcribes, and summarizes meetings, producing an editable "canvas" with summary, key points, and action items [2]. It requires a paid plan (it launched on Team and rolled out to Plus/Pro) [3][10]. It captures mic + system audio, works across any meeting platform (it captures device audio, no bot). Recording length is currently capped at **4 hours (240 minutes) per session** [2] (early reviews reported a 120-minute cap [10], so this appears to have increased). Key limitations: it **works best in English** [2], and at launch it had **no speaker diarization** — it can distinguish multiple speakers as generic "Speaker 1" labels but several hands-on reviews found it produced a single merged transcript [3][11]. Raw audio is deleted after transcription; transcripts may be used to train models unless you opt out (except Business/Enterprise/Edu) [2].

## What matters for transcription specifically
The dimensions you care about: accuracy, platform coverage, system-audio vs mic capture, diarization (separating speakers), speaker identification (knowing *who*), languages, live vs post-meeting, and free-tier caps.

### The major players

**Otter.ai** — **300 transcription minutes/month free, 30-min cap per conversation, 3 lifetime imports** [1][12]. Real-time transcription, speaker labels, AI chat (Otter AI Chat). Joins Zoom/Meet/Teams as a bot. Strong English accuracy (~95% in clean audio in one side-by-side test [13]). Pro is **1,200 min/month at $8.33/mo annual ($16.99 monthly)** [1]. Best-supported languages: English, Spanish, French, Japanese.

**Fireflies.ai** — Free tier with **800 minutes storage**, unlimited transcription but limited AI [14]. 100+ languages. Joins as a bot, broad CRM integrations (50+ native, 7,000+ via Zapier), AskFred AI chat [14]. Pro from ~$10/mo. Best for integration-heavy workflows.

**tl;dv** — Very generous free tier: unlimited recordings + transcripts, video recording included, 30+ languages, unlimited basic summaries, plus a few AI/multi-meeting reports [15]. Joins Zoom/Meet/Teams. CRM auto-fill on paid.

**Fathom** — Most generous free tier on volume: **unlimited recordings, transcription, and storage; AI summaries capped at ~5 meetings/month** [14]. 28 languages. Bot-based. Paid from ~$15/user/mo. Great free entry point for individuals.

**Granola** — Bot-free; captures device audio (mic + system audio) directly, works with every platform [16]. Free ("Basic") plan now includes **unlimited meetings and AI notes**; the catch is **meeting history limited to 14–30 days** [16][17]. Transcribes in real time, deletes audio immediately (transcript only). Independent testing put accuracy ~90–92%, ahead of Otter's tested ~85–88% [18]. macOS/Windows/iOS. **Business $14/user/mo** unlocks unlimited history + integrations (Slack, Notion, HubSpot) [16]. An older 25-lifetime-meeting cap was replaced by the unlimited-meetings model [17].

**Read.ai** — Bot-free desktop/mobile capture available; indexes meetings alongside Gmail/Slack/Teams [19]. Free tier with limited meetings.

**Avoma** — Revenue-team focused; free tier is genuinely limited (free 14-day trial of paid) [20]. Paid Plus ~$49/user/mo. Conversation intelligence, coaching.

**Krisp** — Bot-free, built on its noise-cancellation. **Free plan includes UNLIMITED transcription**, plus 60 minutes/day of noise cancellation, 2 AI summaries/day, and 7-day history [21][22]. Works with any app (sets itself as mic/speaker), so no per-platform integration needed. Strong accuracy because audio is denoised first. Pro ~$16/mo (or ~$8/mo annual) for unlimited summaries [21]. One of the strongest genuinely-useful free tiers.

**Microsoft Teams built-in** — Live transcription + captions with speaker attribution; recording + transcript stored; requires appropriate M365 license. Teams meetings only.

**Google Meet built-in** — Live captions free; "transcripts" and Gemini "take notes for me" require Workspace tiers. Meet only.

**Zoom built-in** — Audio transcript / AI Companion summaries; plan-dependent. Zoom only.

**MacWhisper** — Local, on-device (OpenAI Whisper + now NVIDIA Parakeet). **Free tier: Tiny/Base models, unlimited file transcription**; Pro **€59/~$69 one-time** adds Large-v3/Turbo, batch, speaker diarization, real-time transcription from mic OR system audio, and meeting recording (Zoom/Teams/Webex, etc.) [23][24]. 100% on-device; ~30x realtime on Apple Silicon [25].

**Superwhisper** — Local real-time dictation app (Whisper on Apple Silicon), **$249.99 lifetime or ~$8.49/mo** [26]. More a dictation tool than a meeting-notes tool.

### iOS / iPhone reality
This is genuinely limited. **iOS does not allow third-party apps to capture other apps' audio or VoIP/phone-call audio** (sandbox restriction) [27]. Third-party apps (Otter, Notta, etc.) can only use the microphone — i.e., record room audio on speakerphone [27]. What works natively: Apple's **iOS 18 / 18.1 call recording + transcription** in the Phone and FaceTime apps (region-restricted — unavailable in the EU — and both parties are auto-notified) [28], plus on-device transcription in **Voice Memos** and **Notes** (iPhone 12+, supported languages only) [29]. Granola has an iOS app that caches audio and transcribes after the meeting [16]. Net: on iPhone, expect mic/room capture or first-party Apple features, not silent system-audio capture.

## COMPARISON TABLE — Free/Freemium meeting transcription apps

| App | Transcription quality | Platform coverage | System audio capture | Diarization | Speaker ID | Live vs post | Free tier cap | Notable other features | Paid from |
|---|---|---|---|---|---|---|---|---|---|
| **ChatGPT Record** | High (English) | Any (device audio, no bot) | Yes (mic+system) | Generic labels only | No | Live transcript + post summary | Paid only | Canvas summary, action items, chat over notes | Plus/Team plan |
| **Otter.ai** | High in clean audio (~95%) | Zoom/Meet/Teams (bot) | Via bot/app | Yes | Partial (label/tag) | Live | 300 min/mo, 30-min/convo, 3 imports | AI chat, slide capture | $8.33/mo annual |
| **Fireflies.ai** | Good (90–93%) | Broad + uploads (bot) | Via bot | Yes | Yes | Post (live captions limited) | 800 min storage | 100+ langs, CRM, AskFred | ~$10/mo |
| **tl;dv** | Good | Zoom/Meet/Teams (bot) | Via bot | Yes | Yes | Live+post | Unlimited recordings/transcripts | Video, clips, 30+ langs | paid tiers |
| **Fathom** | Good (~92%) | Zoom/Meet/Teams (bot) | Via bot | Yes | Yes | Live+post | Unlimited rec/transcript; 5 AI summaries/mo | Highlights, 28 langs | ~$15/mo |
| **Granola** | ~90–92% | Any (device audio, bot-free) | Yes | Limited | No | Live + post | Unlimited meetings; 14–30 day history | Notes enhancement, chat, templates | $14/user/mo |
| **Krisp** | Strong (denoised) | Any app (bot-free) | Yes | Yes | Partial | Live | UNLIMITED transcription; 60 min/day NC; 2 summaries/day | Best-in-class noise cancellation | ~$8/mo annual |
| **Read.ai** | Good | Zoom/Meet/Teams + bot-free | Yes | Yes | Yes | Live+post | Limited meetings | Cross-app indexing | paid |
| **Avoma** | Good | Zoom/Meet/Teams (bot) | Via bot | Yes | Yes | Post | Very limited (trial) | Revenue intelligence, coaching | ~$49/user/mo |
| **MS Teams built-in** | Good | Teams only | N/A (native) | Yes | Yes | Live | With license | Native captions/recording | M365 |
| **Google Meet built-in** | Good | Meet only | N/A (native) | Partial | Partial | Live captions | Captions free; transcript paid | Gemini notes | Workspace |
| **Zoom built-in** | Good | Zoom only | N/A (native) | Yes | Yes | Live/post | Plan-dependent | AI Companion summary | Zoom paid |
| **MacWhisper** | Very high (Large-v3) | Any (records app/system audio) | Yes (Pro) | Yes (Pro) | Manual labels | Both | Free: Tiny/Base, unlimited files | On-device, Parakeet, YouTube URL | €59/~$69 once |
| **Superwhisper** | High | Dictation (system-wide) | Limited | No | No | Live (dictation) | Limited free | Custom modes, multi-model | $249.99 once / ~$8.49 mo |

**Bottom line for Topic 1:** If you want genuinely free + useful and don't mind rotating: **Krisp** (unlimited transcription, bot-free) and **Granola** (unlimited meetings — just export before history expires) are the strongest. **tl;dv** and **Fathom** give the most generous recording volume. For on-device privacy with no caps, **MacWhisper** (one-time purchase) is the best value. ChatGPT Record is only worth it if you already pay for ChatGPT and live in that ecosystem — its weak diarization is a real gap.

---

# TOPIC 2: Building Your Own Transcription + Real-Time Agent Pipeline

Architecturally this decomposes into four separable concerns, each swappable behind a clear interface:
1. **Audio capture** (mic + system audio) → produces audio frames
2. **STT engine** (the pluggable facade) → local or cloud, batch or streaming → produces text
3. **Diarization / speaker ID** (separate concern) → labels who spoke
4. **Agent layer** → consumes the transcript stream and does things

## Concern 1 — Audio capture on macOS (the hard part)

The challenge is capturing **system audio** (other participants coming out of your speakers), not just the mic. As of 2025-2026 there are two robust approaches.

### Approach A — BlackHole + Aggregate Device (proven, today)
**BlackHole** (`ExistentialAudio/BlackHole`, GPL-3.0) is a virtual audio loopback driver, available in 2ch / 16ch / 64ch variants (`brew install blackhole-2ch`) [8]. macOS doesn't let apps capture output audio directly, so you loop it back. Steps:
1. Install BlackHole.
2. In **Audio MIDI Setup**, create a **Multi-Output Device** = your real output + BlackHole (so you still hear audio while it's captured). The Built-in Output must be the top/clock device; enable Drift Correction on the others [8].
3. Set that Multi-Output Device as system Sound Output → system audio now flows into BlackHole.
4. Create an **Aggregate Device** = microphone + BlackHole.
5. In Python, open the Aggregate Device and read all channels.

Crucially, **an aggregate device does not mix** — mic and system audio land on separate channels [8][30]. So you can build an aggregate where mic = channels 1–2 and BlackHole/system = channels 3–4, record all channels, and slice them apart. All devices in an aggregate must share a sample rate (don't use AirPods as clock) [8].

### Approach B — Core Audio taps via AudioTee (native, macOS 14.2+)
macOS 14.2 (Dec 2023) introduced **Core Audio taps** (`AudioHardwareCreateProcessTap`). Apple's docs: "Use a Core Audio tap to capture outgoing audio from a process or group of processes" [9]. Taps capture pre-mixer audio (clean regardless of volume) and require Screen Recording / system-audio permission. **AudioTee** (`makeusabrew/audiotee`) is an open-source Swift CLI that streams system audio as raw PCM to stdout — ideal for piping into Python [31]. There's a Node wrapper (**AudioTee.js**) with an EventEmitter interface; the author's stated use case is "pipe system audio to a NodeJS process which in turn relays it to a real-time ASR service" [31]. Note: combined mic+system in one AudioTee binary is not yet shipped (only the author's private fork), so for separate-channel mic+system *today*, the BlackHole+Aggregate route is the proven path.

**ScreenCaptureKit** (macOS 12.3+, mic capture added in 15+) also captures system audio, but driving it from Python via PyObjC is effectively broken — PyObjC issue #647 (macOS 15, PyObjC 11.0) reports `SCStreamErrorDomain Code=-3805` (connectionInvalid) or the audio callback never firing [32]. So shell out to a Swift binary rather than driving SCK directly from Python.

### Python capture libraries
- **sounddevice** (PortAudio): open an InputStream on the Aggregate Device, read all channels as a NumPy frames×channels array, slice columns (`data[:, 0:2]` = mic, `data[:, 2:4]` = system). Supports a `mapping` argument to select channels.
- **soundcard**: supports an explicit channel map, e.g. `record(samplerate=48000, channels=[0,1,2,3], ...)`.
- **PyAudio**: lower-level, works with `channels=N` on the aggregate.
- **ffmpeg `-f avfoundation`**: can capture the aggregate device; note avfoundation alone won't grab system audio (it needs BlackHole as the source).

### iOS capture
As above: iOS forbids third-party capture of other apps'/call audio. Mic-only for third parties; **ReplayKit** records only your *own* app's audio; iOS 18.1 native call recording is first-party and region-locked [27][28]. A DIY iPhone pipeline realistically means mic/room capture or relaying audio to a Mac.

## Concern 2 — The STT engine (pluggable facade)

Because you'll facade this behind a clear interface (`transcribe(audio) -> segments` plus a streaming variant), the rest of the architecture doesn't care which engine sits behind it. Survey of options:

### Local / open-source (free, cost compute)
- **OpenAI Whisper** — the reference model, 99 languages, batch-oriented (no native streaming, no native diarization, 25 MB API file limit). Large-v3 is the accuracy anchor.
- **whisper.cpp** — C/C++ port, runs well on CPU and Apple Metal; good for embedding.
- **faster-whisper** (CTranslate2) — the practical default for self-hosting; much faster + lower memory than reference Whisper; int8 quantization; the base for many tools [33].
- **WhisperX** — built on faster-whisper, adds **word-level timestamps + speaker diarization** (via pyannote) and better long-audio handling [34]. The right pick for multi-speaker meeting transcription.
- **distil-whisper** (distil-large-v3) — ~6x faster, ~49% smaller, within ~1% WER of Whisper [35]. Great when speed matters.
- **NVIDIA Parakeet** (TDT 0.6B v2/v3) — exceptionally fast and accurate. Parakeet-TDT-0.6B-v2 reached **6.05% WER** on the Hugging Face Open ASR Leaderboard at an RTFx of 3386 (batch 128) [36]; v3 reports ~6.32% WER covering 25 European languages [37]. (A late-2025 Open ASR Leaderboard paper ranks v2 around 10th across all decoder types, so "leaderboard-topping" claims are version- and date-sensitive [37].) Runs on Apple Silicon via MLX; now supported in MacWhisper.
- **NVIDIA Canary** — accuracy-focused; Canary-1B-v2 "outperforms Whisper-large-v3" at an RTFx of ~749 [37]. Slower than Parakeet but very accurate.
- **Moonshine** — small streaming-oriented model for edge/real-time; available as a RealtimeSTT backend [38].
- **Apple Silicon / MLX paths**: **lightning-whisper-mlx** ("10x faster than Whisper CPP, 4x faster than current MLX Whisper implementation") [39]; **mlx-audio** (Whisper, Parakeet, VibeVoice-ASR with speaker labels, streaming) [40]; and **Lightning-SimulWhisper** (MLX + CoreML, ~15x decoder / ~18x encoder speedup, runs medium/large-v3-turbo in real time on M2) [41]. Note one benchmark found plain MLX Whisper streaming disappointing on an M1 Air [42] — Apple-Silicon real-time streaming is comfortable from ~M2 up.

### Cloud STT APIs
- **OpenAI** — Whisper API and gpt-4o-transcribe at **$0.006/min**; gpt-4o-mini-transcribe at **$0.003/min**; new streaming model **gpt-realtime-whisper at $0.017/min** over the Realtime API (WebSocket/WebRTC) [6][43]. **gpt-4o-transcribe-diarize** adds built-in diarization; the plain transcribe models do *not* diarize [44]. ~$5 free credit.
- **Deepgram Nova-3** — streaming-first; **$0.0043/min batch, $0.0077/min streaming**; ~5.26% median WER (vendor) / ~18.3% on a hard third-party set; ~300 ms P50 latency; **$200 free credit (~45,000 min)** [4]. Diarization priced separately.
- **AssemblyAI Universal** — cheapest per-minute batch (**Universal-2 $0.0025/min / $0.15/hr**; Universal-3 Pro $0.0035/min); streaming via Universal-3; LeMUR for AI over audio; **$50 free credit (~185 hours)** [5].
- **Google Cloud Speech-to-Text** (Chirp) — ~$0.024/min streaming; 100+ languages; first 60 min/month free [45].
- **Azure Speech** — ~$0.017/min real-time, ~$0.006/min batch; 140+ languages; 5 free hours [46].
- **Speechmatics** (Ursa) — ~$0.004–0.012/min depending on commit; strong multilingual/accents; 8 free hours/month [47].
- **Rev.ai** — ~$0.02/min (some Standard tiers cheaper); good developer SDKs [48].

### How good is STT today?
SOTA WER on clean English is roughly **5–6%** (Nova-3 ~5.26% [4], Parakeet v2 ~6.05% [36]). On hard, noisy, accented audio, real-world WER rises to the mid-teens or higher across all models (Nova-3 ~18.3% on a tough third-party set [4]). For meetings (overlap, crosstalk, jargon), expect noticeably worse than the clean-audio headline. Diarization and custom vocabulary matter as much as the base model.

## PRICING TABLE — Cloud STT (per-minute / per-hour)

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

## Concern 3 — Diarization (separation) vs identification (who)
- **Diarization** = "who spoke when" — partitioning audio into anonymous Speaker 1 / Speaker 2 segments. **Identification** = attaching real identities (recognizing *your* voice).
- **Open-source diarization**: **pyannote.audio 3.1** is the gold standard (DER ~18.8% on AMI, ~21.7% on DIHARD III; Python, Linux/macOS) — its newer "community-1" pipeline brings significant improvement in speaker counting and assignment [7][49]. **NVIDIA NeMo** (Sortformer/MSDD) is strong at production scale on NVIDIA GPUs but caps at ~4 speakers in some configs [50]. **WhisperX** bundles pyannote for combined transcription+diarization [34]. **SpeechBrain** offers speaker-embedding/verification building blocks [51].
- **Knowing when *you* specifically talk** — two approaches:
  1. **Voice fingerprinting / enrollment** — enroll your voice embedding (SpeechBrain/pyannote), then match segments. More work, error-prone with overlap.
  2. **The channel trick (elegant)** — since the BlackHole+Aggregate setup keeps your **mic** on one channel and **system audio** (everyone else) on another, you already know who's local: just measure which channel has energy. The mic channel = you; the system channel = remote participants [8][30]. This is almost certainly what ChatGPT Record's "detect the local mic source" intuition amounts to — and it's far simpler and more reliable than fingerprinting. Run diarization on the *system* channel to separate the remote speakers, and treat the *mic* channel as a known speaker ("me").

## Concern 4 — Live / streaming + the real-time agent loop

### Streaming STT building blocks (Python)
- **RealtimeSTT** (`KoljaB/RealtimeSTT`) — robust low-latency library: VAD (WebRTC + Silero), wake words, selectable engines via extras (faster-whisper default, plus whisper.cpp, Parakeet, Moonshine, etc.), callbacks for realtime text. Can take mic input or fed audio chunks (`feed_audio`) [38]. The most batteries-included starting point.
- **whisper_streaming** (`ufal/whisper_streaming`) — long-form streaming with a LocalAgreement policy; multiple backends (faster-whisper, mlx-whisper, OpenAI API). Being superseded by **SimulStreaming** (faster, AlignAtt policy) by the same author [52].
- **WhisperLive** (`collabora/WhisperLive`) — near-live Whisper over WebSocket; faster-whisper/TensorRT/OpenVINO backends; optional real-time speaker ID via pyannote embeddings (online cosine-similarity clustering); browser + iOS clients [53].
- **VAD for chunking** — **silero-vad** (neural, accurate) and **webrtcvad** (lightweight). VAD detects speech boundaries so you only send meaningful chunks to STT; pattern is VAD → buffer utterance → transcribe → emit [54].
- **OpenAI Realtime API** — managed streaming transcription session (`type: "transcription"`, model `gpt-realtime-whisper`) over WebSocket/WebRTC, returning incremental deltas [43]. Caveats: deltas may lag until end of turn; for diarization you need `gpt-4o-transcribe-diarize`; some older transcribe model versions are slated for retirement around June 2026 [44][55].

### Piping the transcript into an agent
At the architecture level: the streaming STT emits incremental/final segments onto a queue (`asyncio.Queue` or similar). An agent consumer reads finalized utterances and triggers actions — running notes, suggested questions, RAG over related docs. Integration points / considerations:
- **Granularity**: act on *finalized* segments (after VAD turn-end) to avoid churning on partial text; word-level timestamps (WhisperX / Whisper `word_timestamps=True`) let you trigger on keywords mid-utterance [54].
- **Latency budget**: streaming STT adds a few hundred ms to ~1–2 s; the LLM call adds more. For "surface a doc" tasks that's fine; for live captions keep the STT chunk small.
- **Backpressure / decoupling**: keep capture, STT, diarization, and agent as separate async tasks so a slow LLM call never stalls audio capture.
- **Speaker context**: feed the channel-derived "me vs them" label plus diarization labels into the agent prompt so it knows who asked what.

### Existing open-source projects to study or fork
- **Hyprnote** (now also **anarlog**, `fastrepl/anarlog`, MIT) — local-first meeting notetaker; real-time transcription with local (Whisper/Parakeet) or cloud STT, speaker ID, captures system audio from any app, MCP server so Claude/ChatGPT can read/write notes [56]. Excellent reference for your exact goal.
- **Meetily** (`Zackriya-Solutions/meetily`, MIT) — Rust/Tauri, 100% local, Parakeet/Whisper live transcription, **captures microphone + system audio simultaneously** with intelligent ducking, Ollama summarization, pluggable AI (local/BYOK/hosted) [57]. 234k+ downloads.
- **Glass** (open-source Cluely alternative) and **Pluely** (`iamsrikanthnani/pluely`, Tauri, ~10 MB) — real-time meeting "copilot" overlays; Pluely separates system audio from mic and does live STT (Whisper) feeding an LLM [58][59]. **Natively** (`Natively-AI-assistant`) adds local RAG + dual audio channels + meeting history [60]. Good references for the live-agent overlay pattern.
- **Vibe**, **Amical**, **Prismical** — other open-source local transcription/notetaker apps worth a look [61].
- **huggingface/speech-to-speech** — full cascaded STT→LLM→TTS pipeline with MLX optimizations for Mac (parakeet-tdt default STT) [62], if you ever want the voice-response loop.

## Recommendations (staged)

**Stage 0 — Use an app while you build.** Run **Krisp** (unlimited free transcription) or **Granola** (export notes before the history window expires) so you have working transcripts today. If privacy/on-device matters, buy **MacWhisper Pro** (~$69 once) for diarized local file transcription.

**Stage 1 — Batch DIY (highest value/effort ratio).** Capture with **BlackHole + Aggregate Device** (mic ch 1-2, system ch 3-4) via **sounddevice**. After the meeting, run **WhisperX** (faster-whisper + pyannote) on the system channel for a diarized transcript; tag the mic channel as "me." This gets you diarized, speaker-attributed transcripts entirely on-device. Facade the STT call so you can swap in a cloud API later.

**Stage 2 — Live streaming.** Add **RealtimeSTT** (faster-whisper or Parakeet-MLX backend) + **silero-vad**; emit finalized utterances to an `asyncio.Queue`. Use the channel split for instant "me vs them."

**Stage 3 — Agent loop.** Consume the queue in your agent framework; start with post-utterance triggers (notes, suggested questions, RAG). Add the **OpenAI Realtime API** or **Deepgram streaming** only if local latency/accuracy is insufficient.

**Decision thresholds:** Stay local if Apple-Silicon latency is acceptable (M2+ handles medium/turbo in real time) and cost-sensitivity is high. Switch a stage to cloud STT when WER on your meetings exceeds tolerance or you need more than a couple of concurrent streams; at sustained high volume (~100k+ min/month) self-hosting on a GPU becomes cheaper than per-minute cloud [6]. Prefer **Deepgram** for low-latency streaming, **AssemblyAI** for cheapest batch, **OpenAI gpt-4o-transcribe-diarize** if you want managed diarization.

## Caveats
- Free-tier limits change frequently; figures reflect early-to-mid 2026 reporting and several come from vendor/SEO blogs — verify current caps before committing.
- "Bot-free" (Granola, Krisp) ≠ "local": those still process audio in the cloud. Only **MacWhisper / Meetily / Hyprnote** keep audio fully on-device.
- Recording consent is your responsibility; laws vary and Otter faced a 2025 consent-related class action [12].
- macOS may silently resample virtual-device audio; aggregate devices need matching sample rates [8].
- WER headline numbers are clean-audio, single-speaker, often vendor-reported; real meeting accuracy is lower.
- Some OpenAI transcribe model versions are scheduled for retirement around June 2026 — design the facade to swap model names easily [55].

---

## REFERENCES

1. [Pricing | Otter.ai](https://otter.ai/pricing)
2. [ChatGPT Record | OpenAI Help Center](https://help.openai.com/en/articles/11487532-chatgpt-record)
3. [How to Use ChatGPT Record Mode to Get Meeting Transcripts | Tactiq](https://tactiq.io/learn/how-to-use-chatgpt-record-mode-to-get-meeting-transcripts)
4. [Deepgram Pricing 2026: Nova-3 Breakdown | BrassTranscripts](https://brasstranscripts.com/blog/deepgram-pricing-per-minute-2025-real-time-vs-batch)
5. [Speech-to-Text API Pricing (June 2026) | BuildMVPFast](https://www.buildmvpfast.com/api-costs/transcription)
6. [OpenAI Transcription & Whisper API Pricing Calculator | Costgoat](https://costgoat.com/pricing/openai-transcription)
7. [Best Speaker Diarization Tools 2026 | VexaScribe](https://novascribe.ai/compare/best-speaker-diarization-tools)
8. [BlackHole | GitHub – ExistentialAudio](https://github.com/ExistentialAudio/BlackHole)
9. [Capturing system audio with Core Audio taps | Apple Developer](https://developer.apple.com/documentation/CoreAudio/capturing-system-audio-with-core-audio-taps)
10. [ChatGPT Record Mode for Meetings: My Honest Review | tl;dv](https://tldv.io/blog/chatgpt-record-mode-for-meetings/)
11. [ChatGPT Record Review | Jamie](https://www.meetjamie.ai/blog/chatgpt-record)
12. [Otter.ai Free vs Pro | AFFiNE](https://affine.pro/blog/otter-ai-free-vs-pro)
13. [Otter vs Fireflies vs Fathom: AI Meeting Note Tools Compared (2025) | Index.dev](https://www.index.dev/blog/otter-vs-fireflies-vs-fathom-ai-meeting-notes-comparison)
14. [Meeting note tool pricing: Granola vs. Fireflies vs. Fathom vs. Otter | Granola](https://www.granola.ai/blog/meeting-note-tool-pricing-granola-vs-fireflies-fathom-otter)
15. [Krisp AI: An Honest Review & 6 Alternatives (tl;dv free plan comparison)](https://tldv.io/blog/krisp-alternatives/)
16. [Granola free vs. paid: What features are included in each plan? | Granola](https://www.granola.ai/blog/granola-free-vs-paid-features-each-plan)
17. [Granola AI Notes: The Ultimate Guide | Gardenee Blog](https://agmazon.com/blog/articles/technology/202605/granola-ai-note-en.html)
18. [Granola — AI Meeting Notepad and Summary Tool 2026 | SwitchTools](https://www.switchtools.io/tool/granola)
19. [Best Fathom AI Alternatives | Read AI](https://www.read.ai/articles/best-fathom-ai-alternatives-for-ai-meeting-assistants-and-note-takers)
20. [The 10 Best Fathom Alternatives in 2025 | Krisp](https://krisp.ai/blog/fathom-alternatives/)
21. [Krisp Pricing March 2026 (Free) — Plans & Limits | HamsterStack](https://hamsterstack.com/pricing/krisp/)
22. [Krisp AI 2026: AI Noise Cancellation & Voice Enhancement | Max Productive AI](https://max-productive.ai/ai-tools/krisp-ai/)
23. [MacWhisper Pricing 2026 | Voibe Resources](https://www.getvoibe.com/resources/macwhisper-pricing/)
24. [MacWhisper — Jordi Bruin (Gumroad)](https://goodsnooze.gumroad.com/l/macwhisper)
25. [MacWhisper Review 2026 | ToolChase](https://toolchase.com/tool/macwhisper/)
26. [Superwhisper Pricing 2026 | Speakmac](https://www.speakmac.app/blog/speakmac-vs-superwhisper-comparison)
27. [Best AI Note Taking Apps for iPhone 2026 | CFAI](https://cfai.io/tools/ai-note-taker-for-iphone/)
28. [How to record a phone call on iPhone | Soundcore](https://www.soundcore.com/blogs/voice-recorder/how-to-record-a-phone-call-on-iphone)
29. [Record and transcribe audio in Notes on iPhone | Apple Support](https://support.apple.com/guide/iphone/record-and-transcribe-audio-iphbe11247b5/ios)
30. [How to Record Mac System Audio Using Python and BlackHole | Mehdi Samadi (Medium)](https://medium.com/@mehsamadi/how-to-record-mac-system-audio-using-python-and-blackhole-a45d06eaad0f)
31. [AudioTee: capture system audio output on macOS | Strongly Typed](https://stronglytyped.uk/articles/audiotee-capture-system-audio-output-macos)
32. [Failed to Capture System Audio with ScreenCaptureKit on macOS 15 (Issue #647) | pyobjc GitHub](https://github.com/ronaldoussoren/pyobjc/issues/647)
33. [faster-whisper | GitHub – SYSTRAN](https://github.com/SYSTRAN/faster-whisper)
34. [Whisper.cpp vs faster-whisper 2026 (WhisperX, distil-whisper) | PromptQuorum](https://www.promptquorum.com/power-local-llm/local-whisper-stt-comparison-2026)
35. [2025 Edge Speech-to-Text Model Benchmark | Ionio](https://www.ionio.ai/blog/2025-edge-speech-to-text-model-benchmark-whisper-vs-competitors)
36. [NVIDIA Speech AI Models Deliver Industry-Leading Accuracy | NVIDIA Technical Blog](https://developer.nvidia.com/blog/nvidia-speech-ai-models-deliver-industry-leading-accuracy-and-performance/)
37. [The Top Open Source Speech-to-Text (STT) Models in 2025 | Modal](https://modal.com/blog/open-source-stt)
38. [RealtimeSTT | GitHub – KoljaB](https://github.com/KoljaB/RealtimeSTT)
39. [lightning-whisper-mlx | GitHub – mustafaaljadery](https://github.com/mustafaaljadery/lightning-whisper-mlx)
40. [mlx-audio | GitHub – Blaizzy](https://github.com/Blaizzy/mlx-audio)
41. [Lightning-SimulWhisper | GitHub – altalt-org](https://github.com/altalt-org/Lightning-SimulWhisper)
42. [Streaming with Whisper in MLX vs. Faster-Whisper | Wei Lu (Medium)](https://medium.com/@GenerationAI/streaming-with-whisper-in-mlx-vs-faster-whisper-vs-insanely-fast-whisper-37cebcfc4d27)
43. [Realtime transcription | OpenAI API](https://developers.openai.com/api/docs/guides/realtime-transcription)
44. [GPT-4o Transcribe Diarize Model | OpenAI API](https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize)
45. [Best Speech to Text APIs 2025 (Pricing per Minute) | VocaFuse](https://vocafuse.com/blog/best-speech-to-text-api-comparison-2025/)
46. [Azure Speech-to-Text: The Real Cost | BrassTranscripts](https://brasstranscripts.com/blog/azure-speech-services-pricing-2025-microsoft-ecosystem-costs)
47. [Pricing for our Speech API services | Speechmatics](https://www.speechmatics.com/pricing)
48. [Microsoft Azure Speech Recognition vs. Rev AI | Rev](https://www.rev.com/resources/microsoft-azure-speech-recognition-vs-rev-ai-speech-to-text-api)
49. [Comparing state-of-the-art speaker diarization frameworks: Pyannote vs Nemo | La Javaness (Medium)](https://lajavaness.medium.com/comparing-state-of-the-art-speaker-diarization-frameworks-pyannote-vs-nemo-31a191c6300)
50. [An Investigation Into Bengali Speaker Diarization (NeMo Sortformer notes) | arXiv](https://arxiv.org/pdf/2603.03158)
51. [Top Free & Open-source Speaker Diarization APIs and SDKs | Picovoice](https://picovoice.ai/blog/top-speaker-diarization-apis-and-sdks/)
52. [whisper_streaming | GitHub – ufal](https://github.com/ufal/whisper_streaming)
53. [WhisperLive | GitHub – collabora](https://github.com/collabora/WhisperLive)
54. [Possible to use Whisper for real-time / streaming tasks? (Discussion #2) | openai/whisper GitHub](https://github.com/openai/whisper/discussions/2)
55. [Azure OpenAI Realtime API — transcribe model retirements (June 2026) | Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5864686/azure-openai-realtime-api-gpt-4o-transcribe-diariz)
56. [anarlog (formerly Hyprnote) | GitHub – fastrepl](https://github.com/fastrepl/anarlog)
57. [Meetily | GitHub – Zackriya-Solutions](https://github.com/Zackriya-Solutions/meetily)
58. [Cluely vs Glass and Open Source Marketing | Hyperlush](https://hyperlush.com/cluely-vs-glass/)
59. [Pluely | GitHub – iamsrikanthnani](https://github.com/iamsrikanthnani/pluely)
60. [Natively — open-source AI meeting assistant | GitHub](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant)
61. [4 Best Open Source Meetily Alternatives in 2026 | OpenAlternative](https://openalternative.co/alternatives/meetily)
62. [Mac OS and MLX Optimizations | huggingface/speech-to-speech (DeepWiki)](https://deepwiki.com/huggingface/speech-to-speech/7.3-mac-os-and-mlx-optimizations)