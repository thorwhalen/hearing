"""Audio capture and channel handling for the hearing pipeline.

This module owns turning an audio *source* into per-channel float arrays, and
the all-important **channel split**: mic and system audio are kept on separate
channels so that "who is local" is known for free (see the ``hearing-diarization``
skill for what we do with that, and ``hearing-audio-capture`` for the macOS
mechanics of producing such a multi-channel stream — BlackHole + Aggregate
Device, or Core Audio taps).

For the batch milestone this reads a (possibly multi-channel) file. The live
milestone swaps in a streaming :class:`~hearing.interfaces.CaptureSource`
without changing anything downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Sequence

import numpy as np

from hearing.types import Channel

#: STT engines expect 16 kHz mono float32; this is the canonical target rate.
STT_SAMPLE_RATE: int = 16_000


def load_audio(path: str | Path, *, always_2d: bool = True) -> tuple[np.ndarray, int]:
    """Load an audio file as float32 samples plus its native sample rate.

    Args:
        path: Path to any libsndfile-readable file (wav, flac, aiff, ogg, ...).
            For mp3/m4a, convert first (ffmpeg) — see ``hearing-audio-capture``.
        always_2d: If True, always return shape ``(n_samples, n_channels)``.

    Returns:
        ``(data, sample_rate)`` where ``data`` is float32 in roughly [-1, 1].
    """
    try:
        import soundfile as sf
    except ImportError as e:  # pragma: no cover - guidance path
        raise ImportError(
            "Reading audio needs `soundfile`. Install with: pip install soundfile\n"
            "(it bundles libsndfile). See the hearing-audio-capture skill."
        ) from e
    data, sr = sf.read(str(path), dtype="float32", always_2d=always_2d)
    return data, int(sr)


def to_mono(data: np.ndarray) -> np.ndarray:
    """Down-mix to mono by averaging channels. 1-D input is returned as-is."""
    if data.ndim == 2:
        return data.mean(axis=1).astype("float32", copy=False)
    return data.astype("float32", copy=False)


def resample(mono: np.ndarray, sr: int, target: int = STT_SAMPLE_RATE) -> np.ndarray:
    """Resample a mono float array to ``target`` Hz.

    Prefers `soxr` (fast, high quality); falls back to linear interpolation so
    the package still works without it (good enough for tiny/base STT models).
    """
    if sr == target:
        return mono.astype("float32", copy=False)
    try:
        import soxr

        return soxr.resample(mono, sr, target).astype("float32", copy=False)
    except ImportError:
        n_out = int(round(len(mono) * target / sr))
        if n_out <= 0:
            return np.zeros(0, dtype="float32")
        x_old = np.arange(len(mono))
        x_new = np.linspace(0, len(mono), n_out, endpoint=False)
        return np.interp(x_new, x_old, mono).astype("float32")


def to_mono_16k(data: np.ndarray, sr: int, *, target: int = STT_SAMPLE_RATE) -> np.ndarray:
    """Convenience: down-mix to mono and resample to the STT target rate."""
    return resample(to_mono(data), sr, target)


def split_channels(
    data: np.ndarray,
    *,
    mic_channels: Sequence[int] = (0,),
    system_channels: Sequence[int] = (1,),
) -> dict[Channel, np.ndarray]:
    """Split a multi-channel array into per-:class:`Channel` mono arrays.

    An aggregate device *does not mix* — mic lands on one set of channels and
    system audio on another — so we can slice the columns apart. A mono file
    (or single-column) has no split; it is returned as ``{Channel.MIXED: ...}``.

    Args:
        data: shape ``(n_samples,)`` or ``(n_samples, n_channels)``.
        mic_channels: column indices carrying the local microphone.
        system_channels: column indices carrying captured system audio.

    Returns:
        Mapping from :class:`Channel` to a mono float32 array. Channels whose
        indices are out of range are silently omitted.
    """
    if data.ndim == 1 or data.shape[1] == 1:
        return {Channel.MIXED: to_mono(data)}

    n_ch = data.shape[1]
    out: dict[Channel, np.ndarray] = {}
    mic_idx = [i for i in mic_channels if 0 <= i < n_ch]
    sys_idx = [i for i in system_channels if 0 <= i < n_ch]
    if mic_idx:
        out[Channel.MIC] = data[:, mic_idx].mean(axis=1).astype("float32", copy=False)
    if sys_idx:
        out[Channel.SYSTEM] = data[:, sys_idx].mean(axis=1).astype("float32", copy=False)
    # If neither mapping matched (unexpected channel layout), fall back to mixed.
    if not out:
        out[Channel.MIXED] = to_mono(data)
    return out


def rms_energy(samples: np.ndarray) -> float:
    """Root-mean-square energy of a sample buffer (0.0 for empty)."""
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype="float64"))))


@dataclass
class ChannelSplitFileCapture:
    """A batch :class:`~hearing.interfaces.CaptureSource` over an audio file.

    Reads the file once and yields ``(channel, mono_frames)`` for each channel
    present. The live counterpart (device/tap) implements the same interface;
    swapping it in is the *only* change needed to go live — see the
    ``hearing-live-pipeline`` skill.

    >>> # ChannelSplitFileCapture("meeting.wav").frames()  # doctest: +SKIP
    """

    path: str | Path
    mic_channels: Sequence[int] = (0,)
    system_channels: Sequence[int] = (1,)
    sample_rate: int = field(init=False, default=STT_SAMPLE_RATE)

    def __post_init__(self) -> None:
        self._data, self._native_sr = load_audio(self.path)
        self.sample_rate = self._native_sr

    def channels(self) -> dict[Channel, np.ndarray]:
        """The per-channel mono arrays at the file's native sample rate."""
        return split_channels(
            self._data,
            mic_channels=self.mic_channels,
            system_channels=self.system_channels,
        )

    def frames(self) -> Iterator[tuple[Channel, np.ndarray]]:
        """Yield ``(channel, mono_frames)`` once per channel (whole clip)."""
        for channel, samples in self.channels().items():
            yield channel, samples

    def astream(self):  # pragma: no cover - live milestone
        """Live streaming is the milestone-2 path; see hearing-live-pipeline."""
        raise NotImplementedError(
            "Streaming capture is the live milestone. Use frames() for batch, "
            "or implement a device/tap CaptureSource (see hearing-live-pipeline)."
        )
