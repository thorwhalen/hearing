# Key links — diarization & speaker attribution

Curated external repos/docs for this domain. Verified current June 2026.

## Diarization pipelines
- **pyannote.audio** — https://github.com/pyannote/pyannote-audio — gold-standard open-source diarization. v4.x. Use pipeline `pyannote/speaker-diarization-community-1` (open, gated on HF). MIT code; model weights need an HF token + accepting terms.
- **pyannote.core** — https://github.com/pyannote/pyannote-core — the `Segment` / `Timeline` / `Annotation` data model. The right in-memory representation for diarization output (also cited by the global annotation-systems skill).
- **pyannote.metrics** — https://github.com/pyannote/pyannote-metrics — DER / JER evaluation.
- **WhisperX** — https://github.com/m-bain/whisperX — faster-whisper + pyannote, bundled transcription + word-level alignment + diarization in one call. Best fit for the Stage-1 batch path (run on the system channel).
- **NVIDIA NeMo (speaker tasks)** — https://github.com/NVIDIA/NeMo — Sortformer / MSDD diarization; production scale on NVIDIA GPUs; some configs cap ~4 speakers. Not the Apple-Silicon default for this project.

## Enrollment / speaker embeddings (for "me" fallback or named remotes)
- **SpeechBrain** — https://github.com/speechbrain/speechbrain — ECAPA-TDNN / x-vector speaker embeddings + verification building blocks. Use for voice enrollment when channel split is unavailable.

## VAD (for the channel-energy "me vs them" pass)
- **silero-vad** — https://github.com/snakers4/silero-vad — neural VAD, accurate; preferred over bare RMS energy.
- **py-webrtcvad** — https://github.com/wiseman/py-webrtcvad — lightweight WebRTC VAD.

## Reference implementations to study (dual-channel "Me/Them" attribution)
- **Meetily** — https://github.com/Zackriya-Solutions/meetily — dual-VAD "Me"/"Them" labeling from mic vs system channels; 100% local.
- **anarlog (ex-Hyprnote)** — https://github.com/fastrepl/anarlog — local-first notetaker with speaker ID + system-audio capture; closest reference to hearing's goal.

## Interval data structures (joining turns to transcript spans)
- **intervaltree** — https://github.com/chaimleib/intervaltree — Apache-2.0; overlap queries when merging diarization turns with transcript word spans.
