"""Live-pipeline orchestration tests (streaming a file; fake streaming STT).

Verifies the live loop end-to-end without a mic or a heavy model: per-channel
demux, "me vs them" labelling on finalized segments, and fire-and-forget agent
dispatch. A real-whisper live run lives in ``test_integration_say_whisper.py``.
"""

import asyncio

import numpy as np
import pytest

from hearing.pipeline import live_transcribe
from hearing.types import ME, THEM, Channel, TimeSpan, TranscriptSegment
from hearing.vad import segment_utterances

soundfile = pytest.importorskip("soundfile")


class FakeStreamingSTT:
    """STTEngine whose stream_transcribe emits one finalized segment per VAD utterance."""

    def transcribe(self, audio, *, sample_rate, language=None):
        return [TranscriptSegment("x", TimeSpan(0, 500))]

    async def stream_transcribe(self, frames, *, sample_rate):
        async for utt, start_ms in segment_utterances(frames, sample_rate=sample_rate):
            dur = int(len(utt) / sample_rate * 1000)
            yield TranscriptSegment(
                f"utt@{start_ms}", TimeSpan(start_ms, start_ms + dur), meta={"final": True}
            )


class RecordingAgent:
    def __init__(self):
        self.segs = []

    async def on_segment(self, seg):
        self.segs.append(seg)
        return None

    async def on_window(self, window):  # pragma: no cover
        return None


@pytest.fixture
def two_turn_stereo(tmp_path):
    """Stereo file: mic speaks 0.0-0.5s (ch0), system speaks 0.7-1.2s (ch1)."""
    sr = 16_000

    def tone(n):
        return (0.3 * np.sin(np.linspace(0, 60, n))).astype("float32")

    def sil(n):
        return np.zeros(n, dtype="float32")

    half = sr // 2
    mic = np.concatenate([tone(half), sil(int(1.5 * sr))])
    system = np.concatenate([sil(int(0.7 * sr)), tone(half), sil(int(0.8 * sr))])
    n = max(len(mic), len(system))
    mic = np.pad(mic, (0, n - len(mic)))
    system = np.pad(system, (0, n - len(system)))
    path = tmp_path / "meeting.wav"
    soundfile.write(str(path), np.stack([mic, system], axis=1), sr)
    return str(path)


def _run_live(source, **kw):
    async def run():
        return [seg async for seg in live_transcribe(source=source, **kw)]

    return asyncio.run(run())


def test_live_streams_finalized_me_them_and_fires_agent(two_turn_stereo):
    from hearing.capture import StreamingFileCapture

    agent = RecordingAgent()
    source = StreamingFileCapture(two_turn_stereo, block_ms=100)
    segs = _run_live(source, engine=FakeStreamingSTT(), agent=agent)

    assert len(segs) == 2
    assert all(s.meta.get("final") for s in segs)
    assert {s.channel for s in segs} == {Channel.MIC, Channel.SYSTEM}
    assert {s.speaker for s in segs} == {ME, THEM}
    # the agent was invoked (fire-and-forget) for every finalized segment
    assert len(agent.segs) == 2


def test_live_without_agent_still_yields_segments(two_turn_stereo):
    from hearing.capture import StreamingFileCapture

    source = StreamingFileCapture(two_turn_stereo, block_ms=100)
    segs = _run_live(source, engine=FakeStreamingSTT())
    assert len(segs) == 2
