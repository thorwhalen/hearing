---
name: hearing-stt
description: Use when choosing, wiring, swapping, or benchmarking a speech-to-text (STT/ASR) engine behind the hearing project's transcription facade — the pluggable layer that turns audio into segments so the rest of the architecture never names a specific engine. Triggers on transcribe(audio)->segments, ASR engine selection, Whisper / whisper.cpp / faster-whisper / WhisperX / distil-whisper, NVIDIA Parakeet-TDT / Canary, Moonshine, Apple-Silicon MLX paths (lightning-whisper-mlx, mlx-audio, Lightning-SimulWhisper), cloud STT APIs (OpenAI gpt-4o-transcribe / -mini / gpt-realtime-whisper / gpt-4o-transcribe-diarize, Deepgram Nova-3, AssemblyAI Universal, Google Chirp, Azure Speech, Speechmatics, Rev), per-minute STT pricing, local-vs-cloud / on-device decision, WER tolerance, concurrency, self-hosting break-even (~100k min/month), CTranslate2 / int8 quantization, model-name versioning and the ~June-2026 OpenAI transcribe retirements, and "which engine should I use for meeting transcription". Diarization (who-spoke-when) is a SEPARATE concern — see hearing-diarization.
---

# Hearing STT Engine Facade

The pluggable speech-to-text layer for the `hearing` project. The whole point: **the rest of the architecture must not know which engine runs.** Everything downstream (diarization, the agent loop, storage, UI) consumes `TranscriptSegment`s, never an engine SDK. Get the facade right and you can swap a local Whisper for a cloud API by changing one config string.

## The core abstraction (non-negotiable)

**One Protocol, two methods, the shared data spine for I/O.** The Protocol is named `STTEngine` and the data types — `TranscriptSegment` and `TimeSpan` (integer-millisecond spans) — are **imported from `hearing.types`** (defined by [[hearing-architecture]]). This skill does **not** define its own segment dataclass and does **not** use float-second spans in the data spine. Define it once, depend on it everywhere.

```python
"""STT engine facade: audio in, time-stamped segments out, engine-agnostic."""
from collections.abc import AsyncIterator, Sequence
from typing import Any, Optional, Protocol

# The data spine is owned by hearing.types — never redefine it here.
from hearing.types import TranscriptSegment, TimeSpan, Word

class STTEngine(Protocol):
    """Batch + streaming STT. Implement one or both; raise NotImplementedError otherwise."""
    def transcribe(self, audio: Any, *, sample_rate: int,
                   language: Optional[str] = None) -> Sequence[TranscriptSegment]:
        """Whole-clip batch transcription (float32 mono ndarray in) -> segments."""
    async def stream_transcribe(self, frames: AsyncIterator[Any], *,
                                sample_rate: int) -> AsyncIterator[TranscriptSegment]:
        """Incremental transcription; yields interim then finalized segments as audio arrives."""
```

`TranscriptSegment` carries `text` + `span: TimeSpan` (required) plus optional `channel`, `speaker`, `confidence`, `words`, `meta`. `TimeSpan` is `[start_ms, end_ms)` in **integer milliseconds** — STT engines emit float seconds, so convert at the adapter boundary with `TimeSpan.from_seconds(start, end)`. Never let bare float seconds into the spine.

Rules that keep the facade clean:

1. **`TranscriptSegment` is the SSOT contract** (imported from `hearing.types`, never redefined here). Every engine adapter maps its native output into `TranscriptSegment`, converting timestamps via `TimeSpan.from_seconds`. The spine aligns with `pyannote.core.Segment`/`Annotation` and the [[annotation-systems]] `(reference, metadata)` model so transcripts, alignment, and diarization share one timeline. Use **integer-millisecond spans consistently** — pick one origin (audio start) and never mix float seconds into the spine.
2. **`speaker` is NOT the engine's job.** Engines transcribe; diarization assigns speakers. Leave `speaker=None` and let [[hearing-diarization]] fill it (channel-split "me vs them" + pyannote on the system channel). Exception: cloud models with *built-in* diarization (`gpt-4o-transcribe-diarize`, Deepgram/AssemblyAI add-ons) may populate it — keep that an engine capability flag, not an assumption.
3. **Model name is config, never hardcoded.** Keyword-only `model=` with a smart default per engine; no magic strings buried in calls. Some OpenAI transcribe versions retire **~June 2026** — a one-line config swap must suffice. No magic numbers (sample rate, chunk size, beam size) — all keyword-only with defaults.
4. **Adapter per engine, behind the Protocol** (same discipline as annotation-systems' I/O adapters). Each adapter is a small module: `_local_faster_whisper.py`, `_cloud_openai.py`, etc. A `get_engine(name, **kw)` factory (dependency injection) is the only place that imports engine SDKs. Lazy-import heavy deps inside the adapter so installing one engine doesn't drag in all of them.
5. **Reuse the user's `oa` package for the OpenAI cloud path** — `oa.audio.transcribe(audio_file_path, *, model=...)` already returns a standardized `{'text', 'segments'}` dict (`/Users/thorwhalen/Dropbox/py/proj/t/oa`). Wrap it, don't reimplement. Check [[my-packages]] / [[local-package-ecosystem]] before adding any new dependency.

## Streaming is a different shape — don't force it through `transcribe`

Batch returns a finite `Sequence[TranscriptSegment]`; streaming yields over time and re-emits revised partials. Keep them as two methods (above) and let async generators carry backpressure. The streaming pipeline (VAD chunking, RealtimeSTT, WhisperLive, the `asyncio.Queue` to the agent) is owned by **[[hearing-live-pipeline]]** — this skill only fixes the *engine* contract. Use [[python-iterables]] for the generator/streaming discipline.

## Engine decision table (batch-first, then live)

| Need | Pick | Why |
|---|---|---|
| **Practical local default (self-host)** | **faster-whisper** (CTranslate2, int8) | ~4x faster, far lower VRAM than reference Whisper; base of most tools [DIY 33] |
| **Multi-speaker MEETINGS (the sweet spot)** | **WhisperX** (faster-whisper + wav2vec2 word align + pyannote diarization) | Word-level timestamps + speaker labels + long-audio handling in one pass; ~70x realtime [DIY 34] |
| Reference accuracy anchor | OpenAI **Whisper large-v3** | 99 langs; batch only, no native streaming/diarization, 25 MB API file cap (DIY Whisper prose) |
| Embedding / CPU / low-VRAM edge | **whisper.cpp** | C/C++, Metal + CUDA + Vulkan; large-v3-turbo at low VRAM [DIY 34] |
| Speed with ~1% WER cost | **distil-whisper** (distil-large-v3) | ~6x faster, ~49% smaller [35] |
| Fastest accurate local | **NVIDIA Parakeet-TDT 0.6B v2/v3** | ~6.05% WER (v2), huge RTFx; v3 = 25 EU langs; runs on Apple Silicon via MLX [36][37] |
| Max local accuracy (slower) | **NVIDIA Canary-1B-v2** | "outperforms Whisper-large-v3", RTFx ~749 [37] |
| Streaming/edge small model | **Moonshine** | RealtimeSTT backend [38] |
| **Apple Silicon (M2+) real-time** | **lightning-whisper-mlx** / **mlx-audio** / **Lightning-SimulWhisper** | MLX/CoreML; medium & large-v3-turbo in real time on M2; plain MLX streaming was weak on M1 [39][40][41][42] |
| Cheapest cloud BATCH | **AssemblyAI Universal-2** | $0.0025/min; $50 free (~185 hrs); LeMUR [DIY 5] |
| Lowest-latency cloud STREAMING | **Deepgram Nova-3** | streaming-first, ~300 ms P50; $200 free credit [DIY 4] |
| Managed cloud + built-in diarization | **OpenAI gpt-4o-transcribe-diarize** | speakers without running pyannote yourself [44] |

## Pricing — Cloud STT (per minute / per hour), June 2026

| Provider / model | Batch $/min | Streaming $/min | ~$/hour | Free tier | Diarization |
|---|---|---|---|---|---|
| **AssemblyAI Universal-2** | $0.0025 (U-3 Pro $0.0035) | via Universal-3 | $0.15 batch | $50 (~185 hrs) | Add-on |
| **Deepgram Nova-3** | $0.0043 | $0.0077 | $0.258 / $0.462 | $200 (~45k min) | Add-on |
| **OpenAI gpt-4o-mini-transcribe** | $0.003 | — | $0.18 | ~$5 | No |
| **OpenAI gpt-4o-transcribe** | $0.006 | $0.017 (gpt-realtime-whisper) | $0.36 | ~$5 | Diarize variant (same $/min) |
| **Azure Speech** | ~$0.006 | ~$0.017 | ~$1.00 RT | 5 hrs | Yes |
| **Speechmatics Ursa** | ~$0.004–0.012 | similar | ~$0.24+ | 8 hrs/mo | Yes |
| **Google STT (Chirp)** | ~$0.016–0.024 | ~$0.024 | ~$1.44 | 60 min/mo | Yes |
| **Rev.ai** | ~$0.02 | available | ~$1.20 | trial | Yes |
| **Local (Whisper / Parakeet / WhisperX …)** | $0 (compute) | $0 (compute) | electricity | unlimited | via pyannote/WhisperX |

Vendor WER headlines are clean-audio, single-speaker (Nova-3 ~5.26%, Parakeet v2 ~6.05%). Real meetings (overlap, crosstalk, jargon) are mid-teens+ (Nova-3 ~18.3% on a hard set). **Local Whisper large-v3 / turbo needs roughly 6–10 GB VRAM; use int8 (faster-whisper) or whisper.cpp to fit smaller machines** [GD 5] (GD Hardware/VRAM section).

## Staged plan & decision thresholds

- **Stage 0 (today):** use MacWhisper Pro / Krisp / Granola to have transcripts while you build.
- **Stage 1 (highest value/effort):** batch DIY — capture mic ch1-2 + system ch3-4, run **WhisperX** on the system channel for diarized transcript, tag mic as "me." Facade the STT call so cloud swaps in later.
- **Stage 2:** live streaming via RealtimeSTT (faster-whisper or Parakeet-MLX) + silero-vad → see [[hearing-live-pipeline]].
- **Stage 3:** agent loop consumes finalized segments; add OpenAI Realtime / Deepgram streaming only if local latency/accuracy insufficient.

**When to leave local for cloud (decide per stage, not globally):**

- **Stay local** if Apple-Silicon latency is acceptable (M2+ runs medium/turbo in real time) AND you're cost-sensitive / privacy-bound (only local keeps audio on-device).
- **Switch a stage to cloud** when WER on *your* meetings exceeds tolerance, or you need more than a couple of concurrent streams (concurrency, not accuracy, is the usual trigger).
- **Self-host on a GPU** at sustained **~100k+ min/month** — per-minute cloud stops being cheaper [DIY 6].
- Prefer **Deepgram** for low-latency streaming, **AssemblyAI** for cheapest batch, **OpenAI gpt-4o-transcribe-diarize** for managed diarization.

## Concrete patterns

**Cloud OpenAI adapter via the `oa` facade** (no new deps):

```python
def _openai_segments(audio_path, *, model: str = "gpt-4o-transcribe",
                     language: str | None = None) -> Iterable[TranscriptSegment]:
    from oa.audio import transcribe  # lazy import; model is config, not hardcoded
    resp = transcribe(audio_path, model=model, response_format="verbose_json",
                      language=language)
    for s in resp.get("segments", []):
        # float seconds -> integer-ms TimeSpan at the adapter boundary
        yield TranscriptSegment(text=s["text"].strip(),
                                span=TimeSpan.from_seconds(s["start"], s["end"]))
```

**Local faster-whisper adapter** (the default self-host engine — implemented as `FasterWhisperSTT` in `hearing.stt`, with lazy CTranslate2 model load and `compute_type="int8"`):

```python
def _faster_whisper_segments(audio_path, *, model: str = "large-v3",
                             compute_type: str = "int8",
                             beam_size: int = 5,
                             language: str | None = None) -> Iterable[TranscriptSegment]:
    from faster_whisper import WhisperModel  # lazy import
    m = WhisperModel(model, compute_type=compute_type)  # cache the model across calls
    segs, _info = m.transcribe(audio_path, beam_size=beam_size, language=language,
                               word_timestamps=True)
    for s in segs:
        words = tuple(Word(w.word, TimeSpan.from_seconds(w.start, w.end))
                      for w in (s.words or ()))
        yield TranscriptSegment(text=s.text.strip(),
                                span=TimeSpan.from_seconds(s.start, s.end),
                                confidence=getattr(s, "avg_logprob", None), words=words)
```

**Factory (the only place SDKs are named) + capability flags:**

```python
_ENGINES = {  # name -> (callable, supports_streaming, emits_speaker)
    "faster-whisper": (_faster_whisper_segments, False, False),
    "whisperx":       (_whisperx_segments,       False, True),   # bundles diarization
    "openai":         (_openai_segments,         False, False),
    "openai-diarize": (_openai_diarize_segments, False, True),
    "deepgram":       (_deepgram_segments,       True,  False),
}

def get_engine(name: str = "faster-whisper", /, **kw):
    """Dependency-injection factory: resolve an engine by config name."""
    try:
        fn, *_caps = _ENGINES[name]
    except KeyError:
        raise ValueError(f"unknown STT engine {name!r}; have {sorted(_ENGINES)}")
    return partial(fn, **kw)
```

Storage of recordings/transcripts → dol stores per [[python-storage]]. CLI/HTTP wrappers (`argh`) → [[python-dispatching]]. The agent that consumes segments defaults to Claude but stays pluggable → [[claude-api]].

## Pitfalls (call these out in review)

1. **Hardcoded model strings** — break on the ~June-2026 OpenAI retirements; force a code change to swap engines. Always config.
2. **Engine emitting `speaker`** outside the few cloud diarize models — couples STT to diarization; breaks the channel-split design.
3. **Forcing streaming through the batch method** — different shapes; keep two methods.
4. **Eager-importing every engine SDK** at module load — installing one engine shouldn't require torch+CTranslate2+pyannote+vendor SDKs all at once. Lazy-import in adapters.
5. **Trusting vendor WER** for meeting quality — benchmark on *your* audio before committing a stage to cloud.
6. **Mixing time origins / float vs ms** across engines — the spine is integer-ms `TimeSpan`; convert engine float seconds at the adapter boundary with `TimeSpan.from_seconds` and never let bare float seconds leak downstream. Mismatched timelines corrupt alignment and diarization merges.
7. **Reaching for a new PyPI lib** before checking `oa` and [[my-packages]].

## References

`references/from-research-reports.md` — the STT slices of the two June-2026 research reports (engine survey, full pricing table, staged thresholds, VRAM, caveats) with `[n]` citations and URLs. `references/key-links.md` — curated engine repos/docs with one-line annotations.
