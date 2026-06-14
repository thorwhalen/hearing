"""Runnable end-to-end demo of the hearing batch pipeline (macOS).

Synthesizes a two-speaker "meeting" with the macOS ``say`` command — one voice
on the mic channel ("me"), another on the system channel ("them") — then runs
the full batch path: channel-split capture -> faster-whisper STT -> the free
"me vs them" channel-trick diarizer -> a meeting-notes agent.

Run it::

    pip install 'hearing[whisper,agents]'   # faster-whisper + anthropic
    python examples/demo_meeting.py          # uses Claude if ANTHROPIC_API_KEY is set

No microphone or BlackHole needed — the audio is generated on the fly. This is
exactly what ``tests/test_integration_say_whisper.py`` exercises, fleshed out
into a story you can read.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from hearing import transcribe
from hearing.agents import build_default_agent
from hearing.pipeline import summarize
from hearing.stt import FasterWhisperSTT

ME_LINE = (
    "Hi everyone, thanks for joining the planning sync. "
    "I'll own the API design and send a draft by Friday. "
    "What is our deadline for the launch?"
)
THEM_LINE = (
    "Thanks. The launch deadline is the end of the month. "
    "Let's decide on the database. I think we should use Postgres for this project."
)


def _say(text: str, voice: str, out: Path) -> np.ndarray:
    """Render `text` in macOS voice `voice` to a mono float array."""
    say = shutil.which("say")
    if say is None:
        raise SystemExit("This demo needs the macOS `say` command.")
    subprocess.run([say, "-v", voice, "-o", str(out), text], check=True)
    data, _ = sf.read(str(out), dtype="float32")
    return data.mean(axis=1) if data.ndim == 2 else data


def build_meeting(workdir: Path) -> Path:
    """Make a stereo meeting.wav: ch0 = me (turn 1), ch1 = them (turn 2)."""
    sr = 22_050
    me = _say(ME_LINE, "Samantha", workdir / "me.aiff")
    them = _say(THEM_LINE, "Daniel", workdir / "them.aiff")
    gap = np.zeros(int(0.4 * sr), dtype="float32")
    mic = np.concatenate([me, gap, np.zeros(len(them), dtype="float32")])
    system = np.concatenate([np.zeros(len(me), dtype="float32"), gap, them])
    path = workdir / "meeting.wav"
    sf.write(str(path), np.stack([mic, system], axis=1), sr)
    return path


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        meeting = build_meeting(Path(tmp))
        print(f"# synthesized {meeting} (ch0=mic/me, ch1=system/them)\n")

        print("# 1) transcribe — channel split labels me vs them for free")
        transcript = transcribe(meeting, engine=FasterWhisperSTT(model_size="base"))
        print(transcript.formatted())

        print("\n# 2) AI meeting notes (Claude if available, else offline extractive)")
        agent = build_default_agent(context="Project: a new launch. Sync meeting.")
        print(summarize(transcript, agent=agent))


if __name__ == "__main__":
    main()
