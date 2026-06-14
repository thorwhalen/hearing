"""Speech-to-text engines behind the hearing STT facade.

The rest of the architecture only ever sees the
:class:`~hearing.interfaces.STTEngine` Protocol: ``transcribe(audio) -> segments``.
Swap the engine (local Whisper for cloud Deepgram, say) by changing one line of
assembly — nothing downstream knows or cares. See the ``hearing-stt`` skill for
the full engine landscape, the per-minute pricing table, and the local-vs-cloud
decision thresholds.

The default engine is :class:`FasterWhisperSTT` (faster-whisper / CTranslate2):
fast, CPU-friendly via int8, no PyTorch, runs well on Apple Silicon. Heavy deps
are optional — ``transcribe`` raises an informative error telling you what to
``pip install`` if the engine isn't available.
"""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, AsyncIterator, Optional, Sequence

import numpy as np

from hearing.capture import STT_SAMPLE_RATE, resample
from hearing.types import TimeSpan, TranscriptSegment, Word

if TYPE_CHECKING:  # avoid importing the vad module at package import time
    from hearing.vad import VAD

#: Default local model. "base" balances speed/quality; tests use "tiny".
DEFAULT_WHISPER_MODEL: str = "base"


@dataclass
class FasterWhisperSTT:
    """Local STT via `faster-whisper` (CTranslate2) — the default engine.

    Args:
        model_size: whisper size name ("tiny", "base", "small", "medium",
            "large-v3", "large-v3-turbo", ...) or a CTranslate2 model path.
        device: "cpu", "cuda", or "auto".
        compute_type: "int8" (default, lean) / "int8_float16" / "float16" / ...
        word_timestamps: emit per-:class:`Word` timing (enables mid-utterance
            keyword triggers in the agent layer).

    The model is loaded lazily on first use (``functools.cached_property``), so
    constructing the engine is cheap and import-time stays light.
    """

    model_size: str = DEFAULT_WHISPER_MODEL
    device: str = "cpu"
    compute_type: str = "int8"
    word_timestamps: bool = False
    vad_filter: bool = True  # drop non-speech; reduces hallucinated text
    beam_size: int = 5
    vad: Optional["VAD"] = None  # utterance segmenter for stream_transcribe (default: EnergyVAD)
    _engine_id: str = field(init=False, default="faster-whisper")

    @functools.cached_property
    def _model(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:  # pragma: no cover - guidance path
            raise ImportError(
                "The default STT engine needs faster-whisper. Install with:\n"
                "    pip install 'hearing[whisper]'\n"
                "or inject a different STTEngine (e.g. a cloud engine). See the "
                "hearing-stt skill for options."
            ) from e
        return WhisperModel(
            self.model_size, device=self.device, compute_type=self.compute_type
        )

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        sample_rate: int,
        language: Optional[str] = None,
    ) -> Sequence[TranscriptSegment]:
        """Transcribe a whole mono clip; return ordered segments.

        ``audio`` is a 1-D float array. It is resampled to 16 kHz if needed, so
        callers may pass native-rate audio.
        """
        mono16 = resample(_as_mono(audio), sample_rate, STT_SAMPLE_RATE)
        if mono16.size == 0:
            return []
        segments, info = self._model.transcribe(
            mono16,
            language=language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            word_timestamps=self.word_timestamps,
        )
        detected = getattr(info, "language", language)
        out: list[TranscriptSegment] = []
        for s in segments:
            text = (s.text or "").strip()
            if not text:
                continue
            words: tuple[Word, ...] = ()
            if self.word_timestamps and getattr(s, "words", None):
                words = tuple(
                    Word(
                        text=w.word.strip(),
                        span=TimeSpan.from_seconds(w.start, w.end),
                        confidence=getattr(w, "probability", None),
                    )
                    for w in s.words
                )
            out.append(
                TranscriptSegment(
                    text=text,
                    span=TimeSpan.from_seconds(s.start, s.end),
                    confidence=_logprob_to_conf(getattr(s, "avg_logprob", None)),
                    words=words,
                    meta={"engine": self._engine_id, "language": detected},
                )
            )
        return out

    async def stream_transcribe(
        self, frames: AsyncIterator[np.ndarray], *, sample_rate: int
    ) -> AsyncIterator[TranscriptSegment]:
        """Stream finalized segments as utterances complete (the live path).

        Delegates to :func:`vad_stream_transcribe`: VAD groups frames into
        utterances; each is transcribed with the batch ``transcribe`` and emitted
        as a FINALIZED segment. Same Protocol method, same ``TranscriptSegment``
        spine as batch — the live milestone adds no new interface.
        """
        async for seg in vad_stream_transcribe(self, frames, sample_rate=sample_rate, vad=self.vad):
            yield seg


@dataclass
class OpenAISTT:
    """Cloud STT via the OpenAI transcription API — a drop-in ``STTEngine``.

    Demonstrates the facade's payoff: swap the local engine for a cloud one by
    changing the injected ``engine=`` — nothing downstream changes. Defaults to
    ``whisper-1`` (returns segment timestamps via ``verbose_json``); ``gpt-4o-
    transcribe`` returns higher-quality text but as a single segment.

    Needs ``pip install 'hearing[openai]'`` and ``OPENAI_API_KEY`` (or pass
    ``api_key=`` / inject a ``client=`` for tests). See the hearing-stt skill for
    the per-minute pricing and the local-vs-cloud decision.
    """

    model: str = "whisper-1"
    api_key: Optional[str] = None
    language: Optional[str] = None
    vad: Optional["VAD"] = None
    client: Optional[object] = None  # inject a client (tests); else built lazily
    _engine_id: str = field(init=False, default="openai")
    _built: Optional[object] = field(init=False, default=None, repr=False)

    def _get_client(self):
        if self.client is not None:
            return self.client
        if self._built is None:
            try:
                import openai
            except ImportError as e:  # pragma: no cover - guidance path
                raise ImportError(
                    "OpenAISTT needs the openai SDK. Install with:\n"
                    "    pip install 'hearing[openai]'\n"
                    "or inject a different STTEngine. See the hearing-stt skill."
                ) from e
            key = self.api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. Set it, pass api_key=, or use the "
                    "local FasterWhisperSTT engine."
                )
            self._built = openai.OpenAI(api_key=key)
        return self._built

    def transcribe(
        self, audio: np.ndarray, *, sample_rate: int, language: Optional[str] = None
    ) -> Sequence[TranscriptSegment]:
        """Transcribe a mono clip via the OpenAI API; return ordered segments."""
        import tempfile

        import soundfile as sf

        mono16 = resample(_as_mono(audio), sample_rate, STT_SAMPLE_RATE)
        if mono16.size == 0:
            return []
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            sf.write(tmp.name, mono16, STT_SAMPLE_RATE, format="WAV")
            with open(tmp.name, "rb") as f:
                resp = self._get_client().audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    language=language or self.language,
                    response_format="verbose_json",
                )
        return self._segments_from_response(resp, total_ms=int(len(mono16) / STT_SAMPLE_RATE * 1000))

    def _segments_from_response(self, resp, *, total_ms: int) -> list[TranscriptSegment]:
        """Map an OpenAI verbose_json response to TranscriptSegments."""
        raw_segments = getattr(resp, "segments", None)
        out: list[TranscriptSegment] = []
        if raw_segments:
            for s in raw_segments:
                text = (_attr(s, "text") or "").strip()
                if not text:
                    continue
                out.append(
                    TranscriptSegment(
                        text=text,
                        span=TimeSpan.from_seconds(_attr(s, "start", 0.0), _attr(s, "end", 0.0)),
                        meta={"engine": self._engine_id, "model": self.model},
                    )
                )
            return out
        text = (_attr(resp, "text") or "").strip()  # gpt-4o-transcribe: single text
        if text:
            out.append(
                TranscriptSegment(
                    text=text,
                    span=TimeSpan(0, total_ms),
                    meta={"engine": self._engine_id, "model": self.model},
                )
            )
        return out

    async def stream_transcribe(
        self, frames: AsyncIterator[np.ndarray], *, sample_rate: int
    ) -> AsyncIterator[TranscriptSegment]:
        """Live path: VAD utterance finalization, same as the local engine."""
        async for seg in vad_stream_transcribe(self, frames, sample_rate=sample_rate, vad=self.vad):
            yield seg


async def vad_stream_transcribe(engine, frames, *, sample_rate: int, vad=None):
    """Shared live wrapper: VAD -> utterance -> ``engine.transcribe`` -> FINAL segment.

    Both :class:`FasterWhisperSTT` and :class:`OpenAISTT` stream through this, so
    the VAD/finalization logic lives in one place. Spans are offset to absolute
    stream time and marked ``meta['final'] = True``.
    """
    from hearing.vad import segment_utterances

    async for utterance, start_ms in segment_utterances(frames, sample_rate=sample_rate, vad=vad):
        for seg in engine.transcribe(utterance, sample_rate=sample_rate):
            yield replace(
                seg,
                span=TimeSpan(seg.span.start_ms + start_ms, seg.span.end_ms + start_ms),
                meta={**dict(seg.meta), "final": True},
            )


def get_engine(name: str = "whisper", **kwargs):
    """Build an STT engine by name: ``"whisper"``/``"faster-whisper"`` or ``"openai"``."""
    key = name.lower()
    if key in ("whisper", "faster-whisper", "local"):
        return FasterWhisperSTT(**kwargs)
    if key in ("openai", "cloud"):
        return OpenAISTT(**kwargs)
    raise ValueError(f"Unknown STT engine {name!r}; use 'whisper' or 'openai'.")


def _attr(obj, name: str, default=None):
    """Read ``name`` from an object attribute or a mapping key."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def default_engine(**kwargs) -> FasterWhisperSTT:
    """Return the project's default STT engine (faster-whisper).

    Tests and quick runs typically pass ``model_size="tiny"``.
    """
    return FasterWhisperSTT(**kwargs)


def _as_mono(audio: np.ndarray) -> np.ndarray:
    """Coerce input to a 1-D float32 mono array."""
    audio = np.asarray(audio)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return audio.astype("float32", copy=False)


def _logprob_to_conf(avg_logprob: Optional[float]) -> Optional[float]:
    """Map whisper's average log-prob to a rough 0..1 confidence (or None)."""
    if avg_logprob is None:
        return None
    return float(np.clip(np.exp(avg_logprob), 0.0, 1.0))
