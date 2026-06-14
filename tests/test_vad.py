"""Tests for VAD and utterance segmentation (the live pipeline's chunker)."""

import asyncio

import numpy as np

from hearing.vad import EnergyVAD, segment_utterances


def _speech(n: int, amp: float = 0.3) -> np.ndarray:
    return (amp * np.sin(np.linspace(0, 60, n))).astype("float32")


def _silence(n: int) -> np.ndarray:
    return np.zeros(n, dtype="float32")


async def _agen(blocks):
    for b in blocks:
        yield b


def _collect(blocks, **kw):
    async def run():
        return [(u, s) async for u, s in segment_utterances(_agen(blocks), **kw)]

    return asyncio.run(run())


def test_energy_vad_distinguishes_speech_from_silence():
    vad = EnergyVAD()
    assert vad.is_speech(_speech(1600), 16_000) is True
    assert vad.is_speech(_silence(1600), 16_000) is False


def test_segment_utterances_finds_two_turns():
    sr = 16_000
    blk = sr // 10  # 100 ms blocks
    blocks = (
        [_speech(blk)] * 5
        + [_silence(blk)] * 8  # >700ms silence -> finalize turn 1
        + [_speech(blk)] * 5
        + [_silence(blk)] * 8  # finalize turn 2
    )
    utts = _collect(blocks, sample_rate=sr, silence_ms=700, min_speech_ms=200)
    assert len(utts) == 2
    starts = [s for _, s in utts]
    assert starts[0] == 0
    assert starts[1] > 1000  # second turn begins after the first turn + its silence


def test_segment_utterances_drops_too_short_noise():
    sr = 16_000
    blk = sr // 10
    blocks = [_speech(blk)] + [_silence(blk)] * 8  # only 100ms speech < min 200ms
    utts = _collect(blocks, sample_rate=sr, silence_ms=700, min_speech_ms=200)
    assert len(utts) == 0


def test_segment_utterances_flushes_final_turn_at_eos():
    sr = 16_000
    blk = sr // 10
    blocks = [_speech(blk)] * 4  # speech to end, no trailing silence
    utts = _collect(blocks, sample_rate=sr, silence_ms=700, min_speech_ms=200)
    assert len(utts) == 1 and utts[0][1] == 0
