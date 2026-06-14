# STT engine — key external links

Curated entry points for implementing each engine behind the `hearing` STT facade.
Versions/pricing are volatile (June 2026 snapshot) — verify before pinning.

## Local engines

- **faster-whisper** — https://github.com/SYSTRAN/faster-whisper
  CTranslate2 backend, int8 quantization. The practical self-host default; `WhisperModel(...).transcribe(...)`.
- **WhisperX** — https://github.com/m-bain/whisperX
  faster-whisper + wav2vec2 forced alignment (word timestamps) + pyannote diarization. ~70x realtime. Best for multi-speaker meetings. (~22K stars, actively maintained 2026.)
- **whisper.cpp** — https://github.com/ggml-org/whisper.cpp
  C/C++ port; Metal / CUDA / Vulkan; large-v3-turbo at low VRAM. For CPU/edge/embedding.
- **OpenAI Whisper (reference)** — https://github.com/openai/whisper
  Accuracy anchor (large-v3). Batch only; no native streaming/diarization.
- **distil-whisper** — https://github.com/huggingface/distil-whisper
  distil-large-v3: ~6x faster, ~49% smaller, ~1% WER cost.
- **NVIDIA Parakeet / Canary (NeMo)** — https://github.com/NVIDIA/NeMo
  Parakeet-TDT-0.6B v2/v3 (fast+accurate, MLX on Apple Silicon); Canary-1B-v2 (max accuracy).
- **Moonshine** — https://github.com/usefulsensors/moonshine
  Small streaming-oriented model; a RealtimeSTT backend.

## Apple Silicon / MLX

- **lightning-whisper-mlx** — https://github.com/mustafaaljadery/lightning-whisper-mlx
  "10x faster than whisper.cpp, 4x faster than current MLX Whisper."
- **mlx-audio** — https://github.com/Blaizzy/mlx-audio
  Whisper, Parakeet, VibeVoice-ASR (speaker labels), streaming on Apple Silicon.
- **Lightning-SimulWhisper** — https://github.com/altalt-org/Lightning-SimulWhisper
  MLX + CoreML; medium / large-v3-turbo in real time on M2.

## Streaming building blocks (owned by hearing-live-pipeline)

- **RealtimeSTT** — https://github.com/KoljaB/RealtimeSTT
  Batteries-included low-latency: VAD + selectable engines (faster-whisper default, whisper.cpp, Parakeet, Moonshine). Most batteries-included starting point.
- **WhisperLive** — https://github.com/collabora/WhisperLive
  Production WebSocket server; faster-whisper / TensorRT-LLM / OpenVINO backends; optional pyannote speaker ID.
- **whisper_streaming / SimulStreaming** — https://github.com/ufal/whisper_streaming
  LocalAgreement / AlignAtt streaming policies.

## Cloud APIs

- **OpenAI realtime transcription** — https://developers.openai.com/api/docs/guides/realtime-transcription
- **OpenAI gpt-4o-transcribe-diarize** — https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize
- **Deepgram Nova-3** — https://developers.deepgram.com/ (streaming-first, ~300 ms P50)
- **AssemblyAI Universal** — https://www.assemblyai.com/docs (cheapest batch, LeMUR)
- **Google Cloud STT (Chirp)** — https://cloud.google.com/speech-to-text/docs
- **Azure Speech** — https://learn.microsoft.com/azure/ai-services/speech-service/
- **Speechmatics** — https://docs.speechmatics.com/
- **Rev.ai** — https://docs.rev.ai/

## User's local facade (prefer over new deps)

- **`oa`** — `/Users/thorwhalen/Dropbox/py/proj/t/oa`
  `oa.audio.transcribe(audio_file_path, *, model="whisper-1", response_format=...)` returns a
  standardized `{'text', 'segments', ...}` dict. Wrap this for the OpenAI cloud adapter. Also
  has `transcription_to_srt`, `text_to_speech`. Check `oa.openai_specs` for current model ids/pricing.
