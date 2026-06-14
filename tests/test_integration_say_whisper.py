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
