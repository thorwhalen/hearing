"""Pipeline orchestration tests using an injected fake STT engine.

These verify the *composition* — channel splitting, channel tagging, the free
"me vs them" labelling, segment merging, and agent wiring — without needing a
real (heavy) STT model. A real model is exercised in
``test_integration_say_whisper.py`` (auto-skipped when unavailable).
"""

import numpy as np
import pytest

from hearing.pipeline import transcribe
from hearing.types import ME, THEM, Channel, TimeSpan, Transcript, TranscriptSegment

soundfile = pytest.importorskip("soundfile")


class FakeSTT:
    """A deterministic STTEngine: returns one segment per call.

    The text encodes how loud the clip was, so the mic vs system segments are
    distinguishable in assertions.
    """

    def transcribe(self, audio, *, sample_rate, language=None):
        loud = float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
        return [TranscriptSegment(f"energy={loud:.2f}", TimeSpan(0, 1000))]

    async def stream_transcribe(self, frames, *, sample_rate):  # pragma: no cover
        raise NotImplementedError
        yield


@pytest.fixture
def stereo_file(tmp_path):
    """A 1s stereo wav: loud mic (ch0), quiet system (ch1)."""
    sr = 16_000
    stereo = np.zeros((sr, 2), dtype="float32")
    stereo[:, 0] = 0.5  # mic = "me", loud
    stereo[:, 1] = 0.1  # system = "them", quiet
    path = tmp_path / "meeting.wav"
    soundfile.write(str(path), stereo, sr)
    return str(path)


def test_transcribe_splits_channels_and_labels_me_them(stereo_file):
    t = transcribe(stereo_file, engine=FakeSTT())
    assert isinstance(t, Transcript)
    assert len(t) == 2
    by_channel = {s.channel: s for s in t}
    assert set(by_channel) == {Channel.MIC, Channel.SYSTEM}
    # the free channel-trick diarizer ran by default
    assert by_channel[Channel.MIC].speaker == ME
    assert by_channel[Channel.SYSTEM].speaker == THEM
    # mic was louder than system
    assert by_channel[Channel.MIC].text != by_channel[Channel.SYSTEM].text


def test_transcribe_split_false_collapses_to_mixed(stereo_file):
    t = transcribe(stereo_file, engine=FakeSTT(), split=False)
    assert len(t) == 1
    assert t[0].channel is Channel.MIXED
    assert t[0].speaker is None  # nothing to infer from a mixed channel


def test_transcribe_runs_agent_and_stores_insight(stereo_file):
    class FakeAgent:
        async def on_window(self, window):
            return f"{len(window)} segments analyzed"

        async def on_segment(self, segment):  # pragma: no cover
            return None

    t = transcribe(stereo_file, engine=FakeSTT(), agent=FakeAgent())
    assert t.meta["insight"] == "2 segments analyzed"
