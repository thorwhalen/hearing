"""Speech-to-text for hearing — now backed by the scribed transcription façade.

hearing no longer implements its own STT engines. It consumes **scribed** (one
façade over many engines) and adapts scribed's normalized ``Transcript``/``Segment``
spine to hearing's :class:`~hearing.types.TranscriptSegment` data model. The rest of
the architecture still sees only the :class:`~hearing.interfaces.STTEngine` Protocol:
``transcribe(audio) -> segments`` and ``stream_transcribe(frames) -> segments``.

The default engine is scribed's faster-whisper backend (local, fast). Swap engines by
changing the scribed ``backend=`` (e.g. ``"openai"``) — nothing downstream changes.
See scribed's ``scribed-choose-backend`` skill for the full engine landscape, pricing,
and the local-vs-cloud decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncIterator, Optional, Sequence

import numpy as np
import scribed
from scribed.audio import STT_SAMPLE_RATE, to_mono_16k, to_wav_bytes

from hearing.types import Channel, TimeSpan, TranscriptSegment, Word

if TYPE_CHECKING:  # avoid importing optional/heavy modules at import time
    from scribed.base import Segment as ScribedSegment

    from hearing.vad import VAD

#: Default scribed backend id for local transcription.
DEFAULT_BACKEND: str = "faster-whisper"


def _to_hearing_segment(
    seg: "ScribedSegment", *, final: Optional[bool] = None
) -> TranscriptSegment:
    """Adapt a scribed ``Segment`` to hearing's ``TranscriptSegment`` (spine bridge).

    Both are integer-millisecond standoff segments; this maps the (different) span
    and channel types and carries ``is_final`` onto hearing's ``meta['final']``.
    """
    span = (
        TimeSpan(seg.span.start_ms, seg.span.end_ms)
        if seg.span is not None
        else TimeSpan(0, 0)
    )
    words = tuple(
        Word(
            w.text,
            TimeSpan(w.span.start_ms, w.span.end_ms)
            if w.span is not None
            else TimeSpan(0, 0),
            w.confidence,
        )
        for w in seg.words
    )
    channel = Channel(seg.channel.value) if seg.channel is not None else Channel.MIXED
    meta = dict(seg.meta)
    meta["final"] = seg.is_final if final is None else final
    return TranscriptSegment(
        text=seg.text,
        span=span,
        channel=channel,
        speaker=seg.speaker,
        confidence=seg.confidence,
        words=words,
        meta=meta,
    )


@dataclass
class _FramesSource:
    """Wrap hearing's async frame iterator as a scribed ``AudioSource``."""

    frames: AsyncIterator[np.ndarray]
    sample_rate: int

    def __aiter__(self) -> AsyncIterator[np.ndarray]:
        return self.frames


@dataclass
class ScribedSTT:
    """An ``STTEngine`` backed by scribed — the single engine hearing now uses.

    Args:
        backend: scribed backend id (``"faster-whisper"`` default, ``"openai"``, ...).
        model_size: optional model override forwarded to the backend (e.g. ``"tiny"``).
        language: force a language code; ``None`` => auto-detect.
        vad: utterance segmenter for ``stream_transcribe`` (default: scribed EnergyVAD).
    """

    backend: str = DEFAULT_BACKEND
    model_size: Optional[str] = None
    language: Optional[str] = None
    vad: Optional["VAD"] = None

    def _kwargs(self, language: Optional[str]) -> dict:
        """Build scribed transcribe kwargs (model + language) from this engine's config."""
        kw: dict = {}
        if self.model_size is not None:
            kw["model"] = self.model_size
        lang = language if language is not None else self.language
        if lang is not None:
            kw["language"] = lang
        return kw

    def transcribe(
        self, audio: np.ndarray, *, sample_rate: int, language: Optional[str] = None
    ) -> Sequence[TranscriptSegment]:
        """Transcribe a whole mono clip via scribed; return ordered hearing segments."""
        mono16 = to_mono_16k(np.asarray(audio), sample_rate, target=STT_SAMPLE_RATE)
        if mono16.size == 0:
            return []
        wav = to_wav_bytes(mono16, STT_SAMPLE_RATE)
        transcript = scribed.services[self.backend].transcribe(
            wav, **self._kwargs(language)
        )
        return [_to_hearing_segment(s) for s in transcript.segments]

    async def stream_transcribe(
        self, frames: AsyncIterator[np.ndarray], *, sample_rate: int
    ) -> AsyncIterator[TranscriptSegment]:
        """Stream finalized segments as utterances complete (via scribed's live path)."""
        source = _FramesSource(frames=frames, sample_rate=sample_rate)
        agen = scribed.services[self.backend].transcribe_live(
            source, vad=self.vad, **self._kwargs(None)
        )
        async for seg in agen:
            yield _to_hearing_segment(seg)


def get_engine(name: str = "whisper", **kwargs) -> ScribedSTT:
    """Build a scribed-backed STT engine by friendly name.

    ``"whisper"``/``"faster-whisper"``/``"local"`` -> faster-whisper; ``"openai"``/
    ``"cloud"`` -> openai. Any other registered scribed backend id works too.
    """
    key = name.lower()
    if key in ("whisper", "faster-whisper", "local"):
        return ScribedSTT(backend="faster-whisper", **kwargs)
    if key in ("openai", "cloud"):
        return ScribedSTT(backend="openai", **kwargs)
    if key in scribed.list_backends():
        return ScribedSTT(backend=key, **kwargs)
    raise ValueError(f"Unknown STT engine {name!r}; use 'whisper' or 'openai'.")


def default_engine(**kwargs) -> ScribedSTT:
    """Return the project's default STT engine (scribed faster-whisper).

    Tests and quick runs typically pass ``model_size="tiny"``.
    """
    return ScribedSTT(backend=DEFAULT_BACKEND, **kwargs)


def FasterWhisperSTT(*, model_size: Optional[str] = None, **kwargs) -> ScribedSTT:
    """Backward-compatible constructor for the local engine (returns a ``ScribedSTT``).

    Retained so existing call sites (``FasterWhisperSTT(model_size="tiny")``) keep
    working now that the engines are centralized in scribed.
    """
    return ScribedSTT(backend="faster-whisper", model_size=model_size, **kwargs)


def OpenAISTT(**kwargs) -> ScribedSTT:
    """Backward-compatible constructor for the OpenAI engine (returns a ``ScribedSTT``)."""
    return ScribedSTT(backend="openai", **kwargs)
