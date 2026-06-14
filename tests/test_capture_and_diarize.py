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
