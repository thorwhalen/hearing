"""ProcessTapCapture: the pcmtap capture source, run against a fake tap (no hardware)."""

import asyncio
from dataclasses import dataclass

import numpy as np
import pytest

from hearing.capture import ProcessTapCapture
from hearing.types import Channel


@dataclass
class _Format:
    sample_rate: int
    channels: int


class _FakeTap:
    """What pcmtap.Tap looks like from outside: a context manager iterating float32 bytes."""

    def __init__(self, chunks, fmt, seen):
        self._chunks, self.format, self._seen = chunks, fmt, seen

    def __enter__(self):
        self._seen["opened"] = True
        return self

    def __exit__(self, *exc):
        self._seen["closed"] = True

    def __iter__(self):
        return iter(self._chunks)


def _capture(chunks, *, rate=1000, channels=2, **kw):
    seen = {}

    def factory(app, **options):
        seen.update(app=app, **options)
        return _FakeTap(chunks, _Format(rate, channels), seen)

    return ProcessTapCapture(tap_factory=factory, **kw), seen


def _drain(capture):
    async def run():
        return [item async for item in capture.astream()]

    return asyncio.run(run())


def test_yields_the_system_channel_as_mono_blocks_and_passes_the_options():
    stereo = np.tile(np.array([[0.2, 0.4]], dtype="<f4"), (500, 1))  # 500 frames, mean 0.3
    cap, seen = _capture(
        [stereo.tobytes(), stereo.tobytes()],
        app="zoom.us",
        mute=True,
        block_ms=300,
    )
    blocks = _drain(cap)
    assert seen["app"] == "zoom.us" and seen["mute"] is True and seen["exclude"] is False
    assert seen["opened"] and seen["closed"]
    assert cap.sample_rate == 1000
    assert [ch for ch, _ in blocks] == [Channel.SYSTEM] * 4
    assert [len(b) for _, b in blocks] == [300, 300, 300, 100]  # last block is the flushed remainder
    assert np.allclose(blocks[0][1], 0.3)


def test_a_chunk_boundary_in_the_middle_of_a_block_loses_nothing():
    mono = np.arange(10, dtype="<f4").reshape(-1, 1)
    cap, _ = _capture([mono[:3].tobytes(), mono[3:].tobytes()], channels=1, block_ms=400)
    joined = np.concatenate([b for _, b in _drain(cap)])
    assert np.array_equal(joined, np.arange(10, dtype="float32"))


def test_without_pcmtap_it_says_how_to_get_it(monkeypatch):
    import builtins

    real = builtins.__import__

    def refuse(name, *a, **k):
        if name == "pcmtap":
            raise ImportError(name)
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", refuse)
    with pytest.raises(ImportError, match=r"hearing\[tap\]"):
        _drain(ProcessTapCapture())
