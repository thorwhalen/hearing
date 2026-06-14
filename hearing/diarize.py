"""Diarization and speaker labelling for the hearing pipeline.

Two ideas, one interface (:class:`~hearing.interfaces.Diarizer`):

1. **The channel trick (default, free).** Because capture keeps the mic and the
   system audio on *separate channels*, we already know who is local: the
   ``MIC`` channel is "me", the ``SYSTEM`` channel is the remote participants.
   :class:`ChannelTrickDiarizer` just maps channel -> speaker. No model, no
   audio, no error from overlap on the local side. This beats voice
   fingerprinting for the "is it me?" question.

2. **Real diarization (the upgrade).** To separate *multiple remote* speakers
   you need acoustic diarization. :class:`PyannoteDiarizer` wraps
   ``pyannote.audio`` and runs only on the system channel. A diarized transcript
   is standoff interval annotation with a speaker tier — see the
   ``annotation-systems`` skill.

See the ``hearing-diarization`` skill for the full landscape (pyannote vs NeMo
vs WhisperX vs SpeechBrain, DER numbers, enrollment).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

from hearing.types import ME, THEM, Channel, SpeakerLabel, TranscriptSegment


@dataclass
class ChannelTrickDiarizer:
    """Label speakers from the capture channel — the free, reliable default.

    ``MIC`` -> ``me_label`` (the local user), ``SYSTEM`` -> ``them_label`` (a
    remote participant). Segments already carrying a speaker, or coming from a
    ``MIXED`` channel, are passed through unchanged (there is nothing to infer).

    This is the architecture's default diarizer whenever channel information is
    present. To distinguish *individual* remote speakers, compose this with (or
    replace it by) :class:`PyannoteDiarizer`.
    """

    me_label: SpeakerLabel = ME
    them_label: SpeakerLabel = THEM

    def assign_speakers(
        self,
        segments: Iterable[TranscriptSegment],
        *,
        audio: Optional[np.ndarray] = None,  # unused; kept for interface parity
        sample_rate: Optional[int] = None,
    ) -> Iterable[TranscriptSegment]:
        """Yield segments with ``.speaker`` set from their ``.channel``."""
        for seg in segments:
            if seg.speaker is not None:
                yield seg
            elif seg.channel is Channel.MIC:
                yield seg.with_speaker(self.me_label)
            elif seg.channel is Channel.SYSTEM:
                yield seg.with_speaker(self.them_label)
            else:
                yield seg  # MIXED: unknown, leave for a real diarizer


@dataclass
class PyannoteDiarizer:
    """Acoustic diarization via ``pyannote.audio`` (the upgrade path).

    Runs the pretrained pipeline over the audio, then assigns each segment the
    speaker whose diarized turn overlaps it most. Intended to run on the
    *system* channel only (the mic channel is already known to be "me").

    Requires ``pip install hearing[diarize]`` and a Hugging Face token with the
    pyannote model licenses accepted. This implementation is provided for the
    diarization milestone; it is import-guarded so the package works without it.
    """

    model: str = "pyannote/speaker-diarization-3.1"
    hf_token: Optional[str] = None
    speaker_prefix: str = "spk_"

    def _pipeline(self):
        try:
            from pyannote.audio import Pipeline
        except ImportError as e:  # pragma: no cover - guidance path
            raise ImportError(
                "PyannoteDiarizer needs pyannote.audio. Install with:\n"
                "    pip install hearing[diarize]\n"
                "and accept the model license at hf.co, passing hf_token=.\n"
                "Tip: the ChannelTrickDiarizer needs none of this and already "
                "gives you 'me vs them' for free."
            ) from e
        import os

        token = self.hf_token or os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
        return Pipeline.from_pretrained(self.model, use_auth_token=token)

    def assign_speakers(
        self,
        segments: Iterable[TranscriptSegment],
        *,
        audio: Optional[np.ndarray] = None,
        sample_rate: Optional[int] = None,
    ) -> Iterable[TranscriptSegment]:  # pragma: no cover - needs model + token
        """Yield segments labelled with the most-overlapping diarized speaker."""
        segments = list(segments)
        if audio is None or sample_rate is None:
            # Nothing to run on; fall back to the channel trick.
            yield from ChannelTrickDiarizer().assign_speakers(segments)
            return

        pipeline = self._pipeline()
        diarization = pipeline(
            {"waveform": _as_torch(audio), "sample_rate": sample_rate}
        )
        turns = [
            (int(t.start * 1000), int(t.end * 1000), f"{self.speaker_prefix}{label}")
            for t, _, label in diarization.itertracks(yield_label=True)
        ]
        for seg in segments:
            if seg.speaker is not None:
                yield seg
                continue
            label = _best_overlap(seg.span.start_ms, seg.span.end_ms, turns)
            yield seg.with_speaker(label) if label else seg


def _as_torch(audio: np.ndarray):  # pragma: no cover - needs torch
    """Shape a mono float array as the ``(1, n)`` torch tensor pyannote wants."""
    import torch

    return torch.from_numpy(np.ascontiguousarray(audio)).float().unsqueeze(0)


def _best_overlap(
    start_ms: int, end_ms: int, turns: list[tuple[int, int, str]]
) -> Optional[str]:
    """Return the label of the diarized turn with the largest overlap, if any."""
    best_label, best_overlap = None, 0
    for t_start, t_end, label in turns:
        overlap = max(0, min(end_ms, t_end) - max(start_ms, t_start))
        if overlap > best_overlap:
            best_label, best_overlap = label, overlap
    return best_label
