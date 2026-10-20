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
from typing import Any, Callable, Iterable, Optional

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
    speaker whose diarized turn overlaps it most. It runs on the *system* channel
    only: ``MIC`` segments are labelled ``me_label`` for free (the channel trick),
    and the model is not run at all when there is nothing left to diarize. Pass
    the system-channel audio as ``audio`` (``transcribe`` does).

    Requires ``pip install hearing[diarize]`` and a Hugging Face token with the
    pyannote model licenses accepted. The import is guarded so the package works
    without it. ``pipeline`` is the seam: any callable
    ``({"waveform", "sample_rate"}) -> annotation`` (an object with
    ``itertracks(yield_label=True)``) replaces the pretrained model, which is how
    this is tested without a model or a token.
    """

    model: str = "pyannote/speaker-diarization-3.1"
    hf_token: Optional[str] = None
    speaker_prefix: str = "spk_"
    me_label: SpeakerLabel = ME
    pipeline: Optional[Callable[[dict], Any]] = None

    def _pipeline(self):
        if self.pipeline is not None:
            return self.pipeline
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
        try:  # pyannote.audio >= 4 renamed the argument
            return Pipeline.from_pretrained(self.model, token=token)
        except TypeError:  # pragma: no cover - older pyannote
            return Pipeline.from_pretrained(self.model, use_auth_token=token)

    def assign_speakers(
        self,
        segments: Iterable[TranscriptSegment],
        *,
        audio: Optional[np.ndarray] = None,
        sample_rate: Optional[int] = None,
    ) -> Iterable[TranscriptSegment]:
        """Yield segments labelled: mic -> me, others -> most-overlapping diarized speaker."""
        segments = [
            s.with_speaker(self.me_label)
            if s.speaker is None and s.channel is Channel.MIC
            else s
            for s in segments
        ]
        todo = [s for s in segments if s.speaker is None]
        if not todo or audio is None or sample_rate is None:
            # Nothing to diarize, or nothing to run on: the channel trick for the rest.
            yield from ChannelTrickDiarizer(me_label=self.me_label).assign_speakers(segments)
            return

        diarization = self._pipeline()(
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


def _as_torch(audio: np.ndarray):
    """Shape a mono float array as the ``(1, n)`` waveform pyannote wants.

    A torch tensor when torch is installed (it is, with ``hearing[diarize]``), else the
    equivalent numpy array, so an injected ``pipeline`` can run without torch.
    """
    wave = np.ascontiguousarray(audio, dtype=np.float32)[None, :]
    try:
        import torch
    except ImportError:
        return wave
    return torch.from_numpy(wave)


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
