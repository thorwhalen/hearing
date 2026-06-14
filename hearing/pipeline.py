"""Pipeline assembly — compose the four concerns by dependency injection.

This is where progressive disclosure lives: ``transcribe("meeting.wav")`` is a
one-liner with smart defaults, while the engine, diarizer, agent, channel
routing, and persistence are all optional keyword-only arguments. The same
shape powers the live path (``live_transcribe``); only the *source* and the
*trigger cadence* differ (milestone 2).

See the ``hearing-architecture`` skill — this module is the thin orchestrator it
describes; swapping any one component touches only the assembly call.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from hearing.capture import ChannelSplitFileCapture, to_mono
from hearing.diarize import ChannelTrickDiarizer
from hearing.interfaces import AgentConsumer, CaptureSource, Diarizer, STTEngine
from hearing.types import Channel, Transcript, TranscriptSegment, merge_segments


def transcribe(
    source: str | Path | CaptureSource,
    *,
    engine: Optional[STTEngine] = None,
    diarizer: Optional[Diarizer] = None,
    agent: Optional[AgentConsumer] = None,
    language: Optional[str] = None,
    split: bool = True,
    mic_channels: Sequence[int] = (0,),
    system_channels: Sequence[int] = (1,),
    record=None,
) -> Transcript:
    """Transcribe an audio source to a :class:`~hearing.types.Transcript`.

    The one-liner ``transcribe("meeting.wav")`` works with all defaults: the
    default local engine (faster-whisper), automatic channel splitting when the
    file is multi-channel, and the free "me vs them" channel-trick diarizer.

    Args:
        source: a file path or any :class:`~hearing.interfaces.CaptureSource`.
        engine: STT engine (default: faster-whisper). Inject any ``STTEngine``.
        diarizer: speaker labeller. ``None`` -> the channel trick is applied
            automatically when channel info is present (mic="me", system="them").
            Inject a ``PyannoteDiarizer`` to separate individual remote speakers.
        agent: optional ``AgentConsumer`` run over the finished transcript
            (batch). Its output is stored under ``transcript.meta['insight']``.
        language: force a language code (e.g. "en"); ``None`` = auto-detect.
        split: split mic/system channels when the source is multi-channel.
        mic_channels / system_channels: column indices for the channel split.
        record: optional ``MutableMapping`` store (e.g. a dol store) to persist
            the transcript JSON under key ``"<source>.transcript.json"``.

    Returns:
        A :class:`Transcript` (iterable/len-able, so it stands in for a sequence
        of segments). Segments carry text, span, channel, and speaker.
    """
    engine = engine or _default_engine()
    channels, native_sr = _source_channels(
        source, split=split, mic_channels=mic_channels, system_channels=system_channels
    )

    groups: list[list[TranscriptSegment]] = []
    for channel, samples in channels.items():
        segs = list(engine.transcribe(samples, sample_rate=native_sr, language=language))
        groups.append([s.with_channel(channel) for s in segs])
    segments = merge_segments(*groups)

    # Default diarization: the free channel trick whenever channels are known.
    if diarizer is None and any(s.channel is not Channel.MIXED for s in segments):
        diarizer = ChannelTrickDiarizer()
    if diarizer is not None:
        segments = list(diarizer.assign_speakers(segments, sample_rate=native_sr))

    transcript = Transcript(
        tuple(segments),
        sample_rate=native_sr,
        meta={
            "source": str(getattr(source, "path", source)),
            "channels": [c.value for c in channels],
        },
    )

    if agent is not None:
        insight = asyncio.run(agent.on_window(transcript.segments))
        transcript = transcript.with_meta(insight=insight)

    if record is not None:
        _persist(transcript, source, record)

    return transcript


async def live_transcribe(
    *,
    source: CaptureSource,
    engine: Optional[STTEngine] = None,
    diarizer: Optional[Diarizer] = None,
    agent: Optional[AgentConsumer] = None,
    trigger: str = "vad",
):  # pragma: no cover - live milestone
    """Stream finalized segments as a meeting unfolds (milestone 2).

    Same components as :func:`transcribe`; only the *source* (a streaming sink
    instead of a file) and the *trigger cadence* change. Implementing this is
    the live milestone — see the ``hearing-live-pipeline`` skill. The batch path
    works today.
    """
    raise NotImplementedError(
        "live_transcribe is the live milestone (streaming STT + VAD finalization). "
        "See the hearing-live-pipeline skill. The batch transcribe() works now."
    )
    yield  # pragma: no cover - marks this as an async generator


def summarize(
    source: str | Path | CaptureSource | Transcript,
    *,
    agent: Optional[AgentConsumer] = None,
    context: Optional[str] = None,
    model: Optional[str] = None,
    **transcribe_kwargs,
) -> Optional[str]:
    """Transcribe (if needed) then run an agent to produce meeting notes.

    Accepts an audio source or an already-built :class:`Transcript`. Builds the
    default agent (Claude if available, else the offline extractive fallback)
    when none is injected.
    """
    from hearing.agents import summarize_transcript

    if not isinstance(source, Transcript):
        source = transcribe(source, **transcribe_kwargs)
    return summarize_transcript(source, agent=agent, context=context, model=model)


# ── internals ────────────────────────────────────────────────────────────────
def _default_engine() -> STTEngine:
    """The project default STT engine (lazy import keeps package import light)."""
    from hearing.stt import default_engine

    return default_engine()


def _source_channels(
    source, *, split: bool, mic_channels, system_channels
) -> tuple[dict[Channel, np.ndarray], int]:
    """Resolve any source to ``({channel: mono_array}, native_sample_rate)``."""
    if isinstance(source, (str, Path)):
        cap = ChannelSplitFileCapture(
            source, mic_channels=mic_channels, system_channels=system_channels
        )
        chans = cap.channels()
        if not split and (Channel.MIC in chans or Channel.SYSTEM in chans):
            # Collapse the split back to a single mixed channel.
            mixed = sum(chans.values()) / max(len(chans), 1)
            return {Channel.MIXED: mixed.astype("float32")}, cap.sample_rate
        return chans, cap.sample_rate

    if hasattr(source, "channels"):  # a capture source exposing channels()
        return source.channels(), int(source.sample_rate)

    if isinstance(source, CaptureSource) or hasattr(source, "frames"):
        sr = int(getattr(source, "sample_rate", 16_000))
        collected: dict[Channel, list[np.ndarray]] = {}
        for channel, frames in source.frames():
            collected.setdefault(channel, []).append(to_mono(np.asarray(frames)))
        return {c: np.concatenate(parts) for c, parts in collected.items()}, sr

    raise TypeError(
        f"Unsupported source {type(source)!r}; pass a file path or a CaptureSource."
    )


def _persist(transcript: Transcript, source, record) -> None:
    """Store the transcript JSON in a MutableMapping (e.g. a dol store)."""
    import json

    key = f"{Path(str(getattr(source, 'path', source))).name}.transcript.json"
    try:
        record[key] = json.dumps(transcript.to_jsonable(), indent=2)
    except Exception:  # pragma: no cover - store may want bytes
        record[key] = json.dumps(transcript.to_jsonable(), indent=2).encode("utf-8")
