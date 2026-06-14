"""Voice-activity detection and utterance segmentation for the live pipeline.

VAD owns utterance boundaries (never fixed time-slicing, which cuts words and
wrecks WER): detect speech -> buffer the utterance -> on trailing silence,
finalize. :func:`segment_utterances` turns an async stream of audio blocks into
an async stream of ``(utterance_samples, start_ms)`` pairs that the streaming STT
engine transcribes one at a time.

Two detectors behind a tiny protocol:

* :class:`EnergyVAD` — dependency-free RMS-threshold VAD. The default; great for
  clean/loud meeting audio and fully deterministic (so tests need no models).
* :class:`SileroVAD` — neural VAD (accurate on noisy audio); optional, lazy.

See the ``hearing-live-pipeline`` skill for the rationale and the latency budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Optional, Protocol, runtime_checkable

import numpy as np

from hearing.capture import rms_energy

#: Default trailing-silence (ms) that marks a turn end.
DEFAULT_SILENCE_MS: int = 700
#: Minimum speech (ms) for an utterance to be worth transcribing.
DEFAULT_MIN_SPEECH_MS: int = 200
#: Force-flush an utterance that runs this long without a silence (ms).
DEFAULT_MAX_UTTERANCE_MS: int = 30_000


@runtime_checkable
class VAD(Protocol):
    """Decides whether a block of audio contains speech."""

    def is_speech(self, block: np.ndarray, sample_rate: int) -> bool:
        """True if ``block`` (mono float32) contains speech."""
        ...


@dataclass
class EnergyVAD:
    """RMS-energy threshold VAD — dependency-free default.

    A block counts as speech when its RMS energy exceeds ``threshold``. Simple
    and deterministic; for noisy real-world audio prefer :class:`SileroVAD`.
    ``threshold`` is in the same units as the float audio (roughly [-1, 1]).
    """

    threshold: float = 0.01

    def is_speech(self, block: np.ndarray, sample_rate: int) -> bool:
        """True if the block's RMS energy is above ``threshold``."""
        return rms_energy(np.asarray(block, dtype="float32")) >= self.threshold


@dataclass
class SileroVAD:
    """Neural VAD via silero-vad (optional, lazy). Accurate on noisy audio.

    Requires ``pip install silero-vad`` (or torch.hub). Falls back with an
    informative error if unavailable; :class:`EnergyVAD` needs no dependencies.
    """

    speech_prob_threshold: float = 0.5

    def __post_init__(self) -> None:
        self._model = None

    def _ensure_model(self):  # pragma: no cover - needs torch/silero
        if self._model is None:
            try:
                from silero_vad import load_silero_vad
            except ImportError as e:
                raise ImportError(
                    "SileroVAD needs silero-vad. Install with: pip install silero-vad\n"
                    "or use EnergyVAD (the dependency-free default)."
                ) from e
            self._model = load_silero_vad()
        return self._model

    def is_speech(self, block: np.ndarray, sample_rate: int) -> bool:  # pragma: no cover
        """True if silero's speech probability for the block exceeds the threshold."""
        import torch

        model = self._ensure_model()
        tensor = torch.from_numpy(np.ascontiguousarray(block, dtype="float32"))
        prob = float(model(tensor, sample_rate).item())
        return prob >= self.speech_prob_threshold


async def segment_utterances(
    frames: AsyncIterator[np.ndarray],
    *,
    sample_rate: int,
    vad: Optional[VAD] = None,
    silence_ms: int = DEFAULT_SILENCE_MS,
    min_speech_ms: int = DEFAULT_MIN_SPEECH_MS,
    max_utterance_ms: int = DEFAULT_MAX_UTTERANCE_MS,
) -> AsyncIterator[tuple[np.ndarray, int]]:
    """Group an async stream of audio blocks into utterances.

    Yields ``(utterance_samples, start_ms)`` once per finalized utterance:
    speech accumulates into a buffer; after ``silence_ms`` of trailing silence
    (or ``max_utterance_ms`` of continuous speech) the buffer is emitted with its
    start offset (integer ms from the beginning of the stream). Utterances with
    less than ``min_speech_ms`` of actual speech are dropped as noise.
    """
    vad = vad or EnergyVAD()
    buf: list[np.ndarray] = []
    in_speech = False
    trailing_silence_ms = 0.0
    speech_ms = 0.0
    consumed = 0  # absolute samples consumed so far
    start_sample = 0

    def _emit() -> Optional[tuple[np.ndarray, int]]:
        if buf and speech_ms >= min_speech_ms:
            return np.concatenate(buf), int(round(start_sample / sample_rate * 1000))
        return None

    async for block in frames:
        block = np.asarray(block, dtype="float32")
        block_ms = len(block) / sample_rate * 1000
        is_speech = vad.is_speech(block, sample_rate)

        if is_speech:
            if not in_speech:
                in_speech, buf, trailing_silence_ms, speech_ms = True, [], 0.0, 0.0
                start_sample = consumed
            buf.append(block)
            speech_ms += block_ms
            trailing_silence_ms = 0.0
        elif in_speech:
            buf.append(block)  # keep a little trailing silence for the decoder
            trailing_silence_ms += block_ms
            if trailing_silence_ms >= silence_ms:
                emitted = _emit()
                if emitted is not None:
                    yield emitted
                in_speech, buf = False, []

        consumed += len(block)
        if in_speech and (consumed - start_sample) / sample_rate * 1000 >= max_utterance_ms:
            emitted = _emit()
            if emitted is not None:
                yield emitted
            in_speech, buf = False, []

    if in_speech:  # flush the final utterance at end-of-stream
        emitted = _emit()
        if emitted is not None:
            yield emitted
