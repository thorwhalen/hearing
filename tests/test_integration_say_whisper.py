"""End-to-end integration: synthesize speech with macOS `say`, transcribe it.

Auto-skips unless faster-whisper is installed AND the macOS `say` command is
available, so CI (which installs only dev extras) stays green. Run locally with
``pip install 'hearing[whisper]'`` to exercise the real STT path.
"""

import shutil
import subprocess

import pytest

faster_whisper = pytest.importorskip("faster_whisper")
SAY = shutil.which("say")
if SAY is None:  # pragma: no cover - non-macOS
    pytest.skip("macOS `say` command not available", allow_module_level=True)


@pytest.fixture
def spoken_phrase(tmp_path):
    """Generate an AIFF of a known phrase via macOS text-to-speech."""
    phrase = "the quick brown fox jumps over the lazy dog"
    out = tmp_path / "phrase.aiff"
    subprocess.run([SAY, "-o", str(out), phrase], check=True)
    return out, phrase


def test_transcribe_real_audio_with_tiny_model(spoken_phrase):
    out, phrase = spoken_phrase
    from hearing import transcribe
    from hearing.stt import FasterWhisperSTT

    transcript = transcribe(
        str(out), engine=FasterWhisperSTT(model_size="tiny"), split=False, language="en"
    )
    text = transcript.text.lower()
    # tiny model isn't perfect; require a few content words to land.
    hits = sum(w in text for w in ["quick", "brown", "fox", "lazy", "dog", "jump"])
    assert hits >= 3, f"weak transcription: {text!r}"
    assert transcript.duration_ms > 0


def test_live_pipeline_real_whisper(tmp_path):
    """Stream a real two-voice meeting through the live loop and check me/them."""
    import asyncio
    import subprocess

    import numpy as np
    import soundfile as sf

    from hearing.capture import StreamingFileCapture
    from hearing.pipeline import live_transcribe
    from hearing.stt import FasterWhisperSTT
    from hearing.types import ME, THEM, Channel

    def voice(text, v, name):
        p = tmp_path / name
        subprocess.run([SAY, "-v", v, "-o", str(p), text], check=True)
        d, sr = sf.read(str(p), dtype="float32")
        return (d.mean(1) if d.ndim == 2 else d), sr

    me, sr = voice("Let's ship the release on Friday.", "Samantha", "me.aiff")
    them, _ = voice("Sounds good, I will prepare the notes.", "Daniel", "them.aiff")
    gap = np.zeros(int(0.8 * sr), dtype="float32")
    mic = np.concatenate([me, gap, np.zeros(len(them), dtype="float32")])
    system = np.concatenate([np.zeros(len(me), dtype="float32"), gap, them])
    path = tmp_path / "meeting.wav"
    sf.write(str(path), np.stack([mic, system], axis=1), sr)

    async def run():
        source = StreamingFileCapture(path, block_ms=200)
        engine = FasterWhisperSTT(model_size="tiny")
        return [seg async for seg in live_transcribe(source=source, engine=engine)]

    segs = asyncio.run(run())
    assert segs, "live pipeline produced no segments"
    assert all(s.meta.get("final") for s in segs)
    assert {s.channel for s in segs} <= {Channel.MIC, Channel.SYSTEM}
    assert {s.speaker for s in segs} <= {ME, THEM}
    assert any(s.speaker == ME for s in segs) and any(s.speaker == THEM for s in segs)
