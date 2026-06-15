"""Test the ffmpeg fallback in load_audio (decodes formats libsndfile can't)."""

import shutil
import subprocess

import numpy as np
import pytest

soundfile = pytest.importorskip("soundfile")

from hearing.capture import load_audio  # noqa: E402

FFMPEG = shutil.which("ffmpeg")


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not on PATH")
def test_load_audio_reads_m4a_via_ffmpeg_fallback(tmp_path):
    sr = 16_000
    tone = (0.2 * np.sin(np.linspace(0, 300, sr))).astype("float32")
    wav = tmp_path / "a.wav"
    soundfile.write(str(wav), tone, sr)
    # m4a/AAC is NOT readable by libsndfile -> forces the ffmpeg fallback path.
    m4a = tmp_path / "a.m4a"
    subprocess.run([FFMPEG, "-y", "-i", str(wav), str(m4a)], check=True, capture_output=True)

    data, got_sr = load_audio(str(m4a))
    assert got_sr > 0
    assert data.shape[0] > 0  # decoded some samples
