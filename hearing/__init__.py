"""hearing — pluggable meeting transcription & context-aware AI agents.

A small, composable toolkit for capturing, transcribing, and reasoning over
meeting audio. Four swappable concerns compose into one pipeline by dependency
injection: audio **capture** (mic + system audio on separate channels) ->
**STT** engine facade (local or cloud) -> optional **diarization** / speaker-id
(the mic-vs-system channel split gives "me vs them" for free) -> an **agent**
layer that consumes the transcript (batch or live).

Progressive disclosure — the one-liner just works::

    from hearing import transcribe
    transcript = transcribe("meeting.wav")
    print(transcript.formatted())

…while engine selection, diarization, agents, channel routing, and the live
loop are all optional keyword-only arguments.

The architecture and the per-concern guidance live in the project's agent skills
(``.claude/skills/hearing*``); start with the ``hearing`` skill.
"""

from __future__ import annotations

from hearing.pipeline import live_transcribe, summarize, transcribe
from hearing.types import (
    ME,
    THEM,
    Channel,
    SpeakerLabel,
    TimeSpan,
    Transcript,
    TranscriptSegment,
    Word,
)

try:  # version from installed metadata; falls back for source checkouts
    from importlib.metadata import version as _version

    __version__ = _version("hearing")
except Exception:  # pragma: no cover
    __version__ = "0.0.2"

__all__ = [
    "transcribe",
    "live_transcribe",
    "summarize",
    "Transcript",
    "TranscriptSegment",
    "TimeSpan",
    "Word",
    "Channel",
    "SpeakerLabel",
    "ME",
    "THEM",
    "__version__",
]
