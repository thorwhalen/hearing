# Diarization — extracted source passages

Curated slices from the two June-2026 research reports in `hearing/misc/docs/`, kept to the diarization-relevant material with original `[n]` citation markers. Reference URLs for those markers are listed at the bottom.

## From the DIY pipeline report — "Concern 3: Diarization (separation) vs identification (who)" (lines 151–156)

> - **Diarization** = "who spoke when" — partitioning audio into anonymous Speaker 1 / Speaker 2 segments. **Identification** = attaching real identities (recognizing *your* voice).
> - **Open-source diarization**: **pyannote.audio 3.1** is the gold standard (DER ~18.8% on AMI, ~21.7% on DIHARD III; Python, Linux/macOS) — its newer "community-1" pipeline brings significant improvement in speaker counting and assignment [7][49]. **NVIDIA NeMo** (Sortformer/MSDD) is strong at production scale on NVIDIA GPUs but caps at ~4 speakers in some configs [50]. **WhisperX** bundles pyannote for combined transcription+diarization [34]. **SpeechBrain** offers speaker-embedding/verification building blocks [51].
> - **Knowing when *you* specifically talk** — two approaches:
>   1. **Voice fingerprinting / enrollment** — enroll your voice embedding (SpeechBrain/pyannote), then match segments. More work, error-prone with overlap.
>   2. **The channel trick (elegant)** — since the BlackHole+Aggregate setup keeps your **mic** on one channel and **system audio** (everyone else) on another, you already know who's local: just measure which channel has energy. The mic channel = you; the system channel = remote participants [8][DIY 30]. This is almost certainly what ChatGPT Record's "detect the local mic source" intuition amounts to — and it's far simpler and more reliable than fingerprinting. Run diarization on the *system* channel to separate the remote speakers, and treat the *mic* channel as a known speaker ("me").

### Related (Concern 4 / staged recommendations)

> **Stage 1 — Batch DIY.** Capture with BlackHole + Aggregate Device (mic ch 1-2, system ch 3-4). After the meeting, run **WhisperX** (faster-whisper + pyannote) on the system channel for a diarized transcript; tag the mic channel as "me." (lines 185)

> **Speaker context**: feed the channel-derived "me vs them" label plus diarization labels into the agent prompt so it knows who asked what. (line 172)

> SOTA WER on clean English is ~5–6%... For meetings (overlap, crosstalk, jargon), expect noticeably worse than the clean-audio headline. **Diarization and custom vocabulary matter as much as the base model.** (line 135)

VAD building blocks for the channel-energy / dual-VAD pass: **silero-vad** (neural, accurate) and **webrtcvad** (lightweight) [54] (line 164).

## From the GD report — local-first profiles & multi-participant

> **Meetily**: ...To address speaker attribution, Meetily's development roadmap focuses on **dual Voice Activity Detection (VAD) to process microphone input and system output as separate channels, labeling segments as "Me" (local microphone) or "Them" (system audio) in real-time** [GD 30]. (line 86)

> **ownscribe**: macOS native CLI using **PyAnnote and WhisperX** (faster-whisper + CTranslate2) for on-device transcription and speaker diarization; captures system audio via Core Audio Taps, optionally mixing in local microphone input. (local-first profiles)

> **LiveKit** multi-participant: for multi-user scenarios, LiveKit Agents spawns an isolated `AgentSession` per participant identity, each with its own VAD + STT plugin, transcribing each participant's audio stream **without mixing it with other room members**, then publishing transcripts back on the unified `lk.transcription` topic [GD 38][GD 47][GD 48]. (line 184) — the per-participant analogue of the channel trick when audio already arrives pre-separated.

## Reference URLs (matching the markers above)

- **[7]** Best Speaker Diarization Tools 2026 | VexaScribe — https://novascribe.ai/compare/best-speaker-diarization-tools
- **[8]** BlackHole | GitHub – ExistentialAudio — https://github.com/ExistentialAudio/BlackHole
- **[DIY 30]** How to Record Mac System Audio Using Python and BlackHole | Mehdi Samadi (Medium) — https://medium.com/@mehsamadi/how-to-record-mac-system-audio-using-python-and-blackhole-a45d06eaad0f
- **[GD 30]** Selective Input/Output Audio Capture + Muted-Mic Awareness · Issue #337 · Zackriya-Solutions/meetily — https://github.com/Zackriya-Solutions/meeting-minutes/issues/337
- **[34]** Whisper.cpp vs faster-whisper 2026 (WhisperX, distil-whisper) | PromptQuorum — https://www.promptquorum.com/power-local-llm/local-whisper-stt-comparison-2026
- **[DIY 38]** RealtimeSTT | GitHub – KoljaB — https://github.com/KoljaB/RealtimeSTT
- **[GD 38]** Introduction | LiveKit Documentation — https://docs.livekit.io/agents/
- **[GD 47]** Transcription text streams not generated for more than one participant · Issue #3657 · livekit/agents (GitHub) — https://github.com/livekit/agents/issues/3657
- **[GD 48]** agents/examples/other/transcription/multi-user-transcriber.py · livekit/agents (GitHub) — https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py
- **[49]** Comparing state-of-the-art speaker diarization frameworks: Pyannote vs Nemo | La Javaness (Medium) — https://lajavaness.medium.com/comparing-state-of-the-art-speaker-diarization-frameworks-pyannote-vs-nemo-31a191c6300
- **[50]** An Investigation Into Bengali Speaker Diarization (NeMo Sortformer notes) | arXiv — https://arxiv.org/pdf/2603.03158
- **[51]** Top Free & Open-source Speaker Diarization APIs and SDKs | Picovoice — https://picovoice.ai/blog/top-speaker-diarization-apis-and-sdks/
- **[54]** Possible to use Whisper for real-time / streaming tasks? (Discussion #2) | openai/whisper GitHub — https://github.com/openai/whisper/discussions/2

## Note on volatile specifics (verified June 2026)

The reports cite **pyannote.audio 3.1**; as of June 2026 the package is at **v4.x** and the recommended open pipeline is **`pyannote/speaker-diarization-community-1`** (legacy `pyannote/speaker-diarization-3.1` still works; `pyannote/speaker-diarization-precision-2` is a paid hosted service). Pipeline weights are gated on Hugging Face and require an access token plus accepting the model terms. The DER figures quoted above are from the 3.1 era; `community-1` improves speaker counting/assignment.
