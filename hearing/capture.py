"""Audio capture and channel handling for the hearing pipeline.

This module owns turning an audio *source* into per-channel float arrays, and the
all-important **channel split**: mic and system audio are kept on separate channels
so that "who is local" is known for free (see the ``hearing-diarization`` skill for
what we do with that, and ``hearing-audio-capture`` for the macOS mechanics —
BlackHole + Aggregate Device, or Core Audio taps).

The generic, channel-agnostic conditioning (decode, down-mix, resample, energy) now
lives in :mod:`scribed.audio` and is re-exported here for backward compatibility —
hearing owns only the multi-channel / "me vs them" concerns.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Iterator, Optional, Sequence

import numpy as np

# Generic audio conditioning is centralized in scribed; re-exported for callers
# that still import these names from hearing.capture.
from scribed.audio import (  # noqa: F401
    STT_SAMPLE_RATE,
    load_audio,
    resample,
    rms_energy,
    to_mono,
    to_mono_16k,
)

from hearing.types import Channel


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
        out[Channel.SYSTEM] = (
            data[:, sys_idx].mean(axis=1).astype("float32", copy=False)
        )
    # If neither mapping matched (unexpected channel layout), fall back to mixed.
    if not out:
        out[Channel.MIXED] = to_mono(data)
    return out


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

    async def astream(self) -> AsyncIterator[tuple[Channel, np.ndarray]]:
        """Stream the file's channels in one shot (whole clip per channel).

        Provided so a file satisfies the async ``CaptureSource`` too; for a
        realistic block-by-block live simulation use :class:`StreamingFileCapture`.
        """
        for channel, samples in self.channels().items():
            yield channel, samples


@dataclass
class StreamingFileCapture:
    """A *streaming* :class:`~hearing.interfaces.CaptureSource` over a file.

    Yields ``(channel, block)`` in ``block_ms`` chunks, time-ordered across
    channels, so the live pipeline can be exercised end-to-end without a mic or
    BlackHole. With ``realtime=True`` it paces playback in real time (for demos);
    the default streams as fast as possible (for tests).
    """

    path: str | Path
    block_ms: int = 200
    realtime: bool = False
    mic_channels: Sequence[int] = (0,)
    system_channels: Sequence[int] = (1,)
    sample_rate: int = field(init=False, default=STT_SAMPLE_RATE)

    def __post_init__(self) -> None:
        data, sr = load_audio(self.path)
        self.sample_rate = sr
        self._channels = split_channels(
            data, mic_channels=self.mic_channels, system_channels=self.system_channels
        )

    def channels(self) -> dict[Channel, np.ndarray]:
        """The per-channel mono arrays at the file's native sample rate."""
        return self._channels

    def frames(self) -> Iterator[tuple[Channel, np.ndarray]]:
        """Batch view: whole clip per channel."""
        yield from self._channels.items()

    async def astream(self) -> AsyncIterator[tuple[Channel, np.ndarray]]:
        """Yield ``(channel, block)`` blocks, all channels per time step."""
        block = max(1, int(self.block_ms / 1000 * self.sample_rate))
        n = max((len(a) for a in self._channels.values()), default=0)
        for start in range(0, n, block):
            for channel, samples in self._channels.items():
                blk = samples[start : start + block]
                if blk.size:
                    yield channel, blk
            if self.realtime:
                await asyncio.sleep(self.block_ms / 1000)


@dataclass
class DeviceCapture:
    """Live macOS capture from an audio *device* (the milestone-2 capture source).

    Point this at an **Aggregate Device** that combines your microphone and
    BlackHole (so mic and system audio land on separate, non-mixed channels —
    see the ``hearing-audio-capture`` skill for the Audio MIDI Setup). Reads
    multi-channel blocks and splits them into mic/system channels.

    Requires ``pip install 'hearing[capture]'`` (sounddevice). Needs real audio
    hardware to exercise; constructing it is cheap (the device opens in
    ``astream``). For a hardware-free run of the live loop, use
    :class:`StreamingFileCapture`.
    """

    device: Optional[int | str] = None
    block_ms: int = 200
    mic_channels: Sequence[int] = (0, 1)
    system_channels: Sequence[int] = (2, 3)
    sample_rate: int = 48_000
    channels_count: int = 4

    @staticmethod
    def list_devices():  # pragma: no cover - needs sounddevice + hardware
        """Return available audio devices (helps pick the Aggregate Device)."""
        import sounddevice as sd

        return sd.query_devices()

    async def astream(
        self,
    ) -> AsyncIterator[tuple[Channel, np.ndarray]]:  # pragma: no cover
        """Open the device and yield ``(channel, block)`` blocks until cancelled."""
        try:
            import sounddevice as sd
        except ImportError as e:
            raise ImportError(
                "DeviceCapture needs sounddevice. Install with: pip install 'hearing[capture]'\n"
                "and configure a BlackHole + Aggregate Device (see hearing-audio-capture). "
                "For a hardware-free run, use StreamingFileCapture."
            ) from e
        loop = asyncio.get_event_loop()
        block = max(1, int(self.block_ms / 1000 * self.sample_rate))
        with sd.InputStream(
            device=self.device,
            channels=self.channels_count,
            samplerate=self.sample_rate,
            dtype="float32",
            blocksize=block,
        ) as stream:
            while True:
                data, _overflowed = await loop.run_in_executor(None, stream.read, block)
                chans = split_channels(
                    np.asarray(data),
                    mic_channels=self.mic_channels,
                    system_channels=self.system_channels,
                )
                for channel, samples in chans.items():
                    yield channel, samples
