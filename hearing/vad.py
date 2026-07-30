"""Voice-activity detection and utterance segmentation — re-exported from scribed.

The VAD logic (energy/neural detectors + utterance segmentation) is now owned by
:mod:`scribed.vad` so it can be shared across every scribed consumer. hearing keeps
this module as the stable import path; the names below are scribed's.

See the ``hearing-live-pipeline`` skill for the rationale and the latency budget.
"""

from __future__ import annotations

from scribed.vad import (  # noqa: F401
    DEFAULT_MAX_UTTERANCE_MS,
    DEFAULT_MIN_SPEECH_MS,
    DEFAULT_SILENCE_MS,
    VAD,
    EnergyVAD,
    SileroVAD,
    segment_utterances,
)

__all__ = [
    "VAD",
    "EnergyVAD",
    "SileroVAD",
    "segment_utterances",
    "DEFAULT_SILENCE_MS",
    "DEFAULT_MIN_SPEECH_MS",
    "DEFAULT_MAX_UTTERANCE_MS",
]
