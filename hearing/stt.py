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

Engines by friendly name (:data:`ENGINE_ALIASES`, used by :func:`get_engine` and the
CLI's ``--engine``):

- ``whisper`` — faster-whisper, local, any CPU/GPU (default; ``hearing[whisper]``)
- ``openai`` — OpenAI transcription API (``hearing[openai]``, ``OPENAI_API_KEY``)
- ``deepgram`` — Deepgram Nova-3 (``hearing[deepgram]``, ``DEEPGRAM_API_KEY``)
- ``mlx`` / ``parakeet`` — Whisper / Parakeet-TDT on Apple Silicon (``hearing[mlx]``)
- ``whisperx`` — WhisperX, aligned words + optional diarization (``hearing[whisperx]``)

All of them are scribed backends; hearing only maps friendly names onto them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Mapping, Optional, Sequence

import numpy as np
import scribed
from scribed.audio import STT_SAMPLE_RATE, to_mono_16k, to_wav_bytes

from hearing.types import Channel, TimeSpan, TranscriptSegment, Word

if TYPE_CHECKING:  # avoid importing optional/heavy modules at import time
    from scribed.base import Segment as ScribedSegment

    from hearing.vad import VAD

#: Default scribed backend id for local transcription.
DEFAULT_BACKEND: str = "faster-whisper"

#: Friendly engine name -> scribed backend id (the SSOT for ``get_engine``/the CLI).
#: Any other registered scribed backend id is accepted as-is.
ENGINE_ALIASES: Dict[str, str] = {
    "whisper": "faster-whisper",
    "faster-whisper": "faster-whisper",
    "local": "faster-whisper",
    "openai": "openai",
    "cloud": "openai",
    "deepgram": "deepgram",
    "nova": "deepgram",
    "mlx": "mlx-whisper",
    "mlx-whisper": "mlx-whisper",
    "parakeet": "parakeet-mlx",
    "parakeet-mlx": "parakeet-mlx",
    "whisperx": "whisperx",
}

#: Backends whose ``model`` accepts a bare whisper size ("base", "small", ...).
WHISPER_SIZED_BACKENDS = frozenset({"faster-whisper", "mlx-whisper", "whisperx"})

#: Engine names shown in help and error messages (one per backend).
ENGINE_NAMES = ("whisper", "openai", "deepgram", "mlx", "parakeet", "whisperx")


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
        options: extra backend kwargs forwarded on every call (e.g.
            ``{"diarize": True}`` for WhisperX/Deepgram); see the backend's
            ``param_map`` for what it accepts.
    """

    backend: str = DEFAULT_BACKEND
    model_size: Optional[str] = None
    language: Optional[str] = None
    vad: Optional["VAD"] = None
    options: Mapping[str, Any] = field(default_factory=dict)

    def _kwargs(self, language: Optional[str]) -> dict:
        """Build scribed transcribe kwargs (options + model + language)."""
        kw: dict = dict(self.options)
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
    """Build a scribed-backed STT engine by friendly name (see :data:`ENGINE_ALIASES`).

    ``"whisper"`` -> faster-whisper, ``"openai"``, ``"deepgram"``, ``"mlx"`` ->
    mlx-whisper, ``"parakeet"`` -> parakeet-mlx, ``"whisperx"``. Any other
    registered scribed backend id works too. ``kwargs`` go to :class:`ScribedSTT`.

    >>> get_engine("mlx").backend
    'mlx-whisper'
    """
    key = name.lower()
    backend = ENGINE_ALIASES.get(key)
    if backend is None and key in scribed.list_backends():
        backend = key
    if backend is None:
        raise ValueError(
            f"Unknown STT engine {name!r}; use one of {', '.join(ENGINE_NAMES)} "
            "(or any scribed backend id)."
        )
    return ScribedSTT(backend=backend, **kwargs)


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


def DeepgramSTT(*, model: Optional[str] = None, **kwargs) -> ScribedSTT:
    """Deepgram (cloud) engine — Nova-3 by default; ``model="nova-2"`` etc. swaps it.

    Batch goes to Deepgram's pre-recorded REST API (via scribed's deepgram backend);
    the live path is scribed's VAD-segmented stream over that batch call. Needs
    ``pip install 'hearing[deepgram]'`` and ``DEEPGRAM_API_KEY``.
    """
    return ScribedSTT(backend="deepgram", model_size=model, **kwargs)


def MLXSTT(
    *, model: Optional[str] = None, mlx_backend: str = "mlx-whisper", **kwargs
) -> ScribedSTT:
    """Apple-Silicon (MLX) engine: mlx-whisper by default, or ``mlx_backend="parakeet-mlx"``.

    ``model`` is a Hugging Face repo id or (mlx-whisper) a bare Whisper size such as
    ``"small"``. Needs macOS on Apple Silicon and ``pip install 'hearing[mlx]'``.
    """
    if mlx_backend not in ("mlx-whisper", "parakeet-mlx"):
        raise ValueError(
            f"Unknown MLX backend {mlx_backend!r}; use 'mlx-whisper' or 'parakeet-mlx'."
        )
    return ScribedSTT(backend=mlx_backend, model_size=model, **kwargs)


def WhisperXSTT(
    *, model: Optional[str] = None, diarize: bool = False, **kwargs
) -> ScribedSTT:
    """WhisperX engine: aligned word timestamps, plus pyannote speakers if ``diarize``.

    Needs ``pip install 'hearing[whisperx]'``; ``diarize=True`` also needs a
    Hugging Face token in ``HF_TOKEN``.
    """
    options = {**kwargs.pop("options", {}), "diarize": diarize}
    return ScribedSTT(backend="whisperx", model_size=model, options=options, **kwargs)
