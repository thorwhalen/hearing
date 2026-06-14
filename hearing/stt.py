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
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Sequence

import numpy as np

from hearing.capture import STT_SAMPLE_RATE, resample
from hearing.types import TimeSpan, TranscriptSegment, Word

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
    ) -> AsyncIterator[TranscriptSegment]:  # pragma: no cover - live milestone
        """Live transcription is the milestone-2 path; see hearing-live-pipeline.

        The batch ``transcribe`` is fully implemented and tested. Streaming
        (VAD-based utterance finalization, partial vs final segments) belongs to
        the live milestone and a streaming-oriented backend (RealtimeSTT,
        WhisperLive, the OpenAI Realtime API). Implement against this signature.
        """
        raise NotImplementedError(
            "stream_transcribe is the live milestone. See the hearing-live-pipeline "
            "skill; the batch path (transcribe) works today."
        )
        yield  # pragma: no cover - makes this an async generator


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
