"""Tests for channel handling (capture) and the channel-trick diarizer."""

import numpy as np

from hearing.capture import resample, rms_energy, split_channels, to_mono
from hearing.diarize import ChannelTrickDiarizer
from hearing.types import ME, THEM, Channel, TimeSpan, TranscriptSegment


def test_split_channels_stereo_to_mic_and_system():
    n = 100
    stereo = np.zeros((n, 2), dtype="float32")
    stereo[:, 0] = 0.5  # mic
    stereo[:, 1] = 0.1  # system
    chans = split_channels(stereo, mic_channels=(0,), system_channels=(1,))
    assert set(chans) == {Channel.MIC, Channel.SYSTEM}
    assert np.allclose(chans[Channel.MIC], 0.5)
    assert np.allclose(chans[Channel.SYSTEM], 0.1)


def test_split_channels_mono_is_mixed():
    mono = np.ones((50,), dtype="float32")
    chans = split_channels(mono)
    assert set(chans) == {Channel.MIXED}


def test_to_mono_averages_columns():
    data = np.array([[0.0, 1.0], [1.0, 1.0]], dtype="float32")
    assert np.allclose(to_mono(data), [0.5, 1.0])


def test_resample_changes_length_proportionally():
    sr_in, sr_out = 8000, 16000
    x = np.sin(np.linspace(0, 6.28, sr_in)).astype("float32")
    y = resample(x, sr_in, sr_out)
    assert abs(len(y) - 2 * len(x)) <= 2  # ~doubled


def test_rms_energy_zero_for_silence():
    assert rms_energy(np.zeros(10, dtype="float32")) == 0.0
    assert rms_energy(np.ones(10, dtype="float32")) > 0


def test_channel_trick_labels_me_and_them():
    segs = [
        TranscriptSegment("hi", TimeSpan(0, 1000), Channel.MIC),
        TranscriptSegment("hello", TimeSpan(1000, 2000), Channel.SYSTEM),
        TranscriptSegment("?", TimeSpan(2000, 3000), Channel.MIXED),
    ]
    out = list(ChannelTrickDiarizer().assign_speakers(segs))
    assert out[0].speaker == ME
    assert out[1].speaker == THEM
    assert out[2].speaker is None  # MIXED: nothing to infer


def test_channel_trick_preserves_existing_speaker():
    seg = TranscriptSegment("x", TimeSpan(0, 1), Channel.SYSTEM, speaker="Alice")
    out = list(ChannelTrickDiarizer().assign_speakers([seg]))
    assert out[0].speaker == "Alice"


# --- PyannoteDiarizer against a fake pipeline (#4): no model, no token -------------------


class _FakeAnnotation:
    def __init__(self, tracks):
        self._tracks = tracks

    def itertracks(self, yield_label=False):
        for start, end, label in self._tracks:
            yield _Turn(start, end), None, label


class _Turn:
    def __init__(self, start, end):
        self.start, self.end = start, end


def _seg(text, start, end, channel):
    from hearing.types import TimeSpan, TranscriptSegment

    return TranscriptSegment(text, TimeSpan(start, end), channel=channel)


def test_pyannote_diarizes_system_only_and_keeps_mic_as_me():
    import numpy as np

    from hearing.diarize import PyannoteDiarizer
    from hearing.types import Channel

    calls = []

    def pipeline(inp):
        calls.append(inp["sample_rate"])
        return _FakeAnnotation([(0.0, 1.0, "A"), (1.0, 2.0, "B")])

    segs = [
        _seg("hi", 0, 900, Channel.SYSTEM),
        _seg("me", 900, 1000, Channel.MIC),
        _seg("yo", 1100, 1900, Channel.SYSTEM),
    ]
    out = list(
        PyannoteDiarizer(pipeline=pipeline).assign_speakers(
            segs, audio=np.zeros(16000, dtype=np.float32), sample_rate=16000
        )
    )
    assert [s.speaker for s in out] == ["spk_A", "me", "spk_B"]
    assert calls == [16000]


def test_pyannote_skips_the_model_when_only_the_mic_spoke():
    import numpy as np

    from hearing.diarize import PyannoteDiarizer
    from hearing.types import Channel

    def boom(inp):  # pragma: no cover - must not run
        raise AssertionError("pipeline ran with nothing to diarize")

    out = list(
        PyannoteDiarizer(pipeline=boom).assign_speakers(
            [_seg("me", 0, 500, Channel.MIC)], audio=np.zeros(8), sample_rate=16000
        )
    )
    assert out[0].speaker == "me"


def test_pyannote_without_audio_falls_back_to_channel_trick():
    from hearing.diarize import PyannoteDiarizer
    from hearing.types import Channel

    out = list(PyannoteDiarizer().assign_speakers([_seg("x", 0, 10, Channel.SYSTEM)]))
    assert out[0].speaker == "them"
