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
    audio_queue_max: int = 50,
    segment_queue_max: int = 100,
):
    """Stream FINALIZED segments as a meeting unfolds (the live path).

    Same components as :func:`transcribe` — only the *source* (a streaming
    :class:`~hearing.interfaces.CaptureSource` instead of a file) and the trigger
    cadence (VAD utterance turn-ends instead of run-once) change. The
    ``STTEngine`` and ``AgentConsumer`` interfaces are unchanged.

    Each channel is demuxed onto its own bounded queue and driven through
    ``engine.stream_transcribe`` as an independent async task, so a slow agent
    never stalls capture (backpressure) and the channel "me vs them" label rides
    every segment. Diarization defaults to the free channel trick; the agent's
    ``on_segment`` is fired fire-and-forget. Yields segments as utterances finalize.

    See the ``hearing-live-pipeline`` skill.
    """
    engine = engine or _default_engine()
    seg_q: asyncio.Queue = asyncio.Queue(maxsize=segment_queue_max)
    chan_queues: dict[Channel, asyncio.Queue] = {}
    stt_tasks: list[asyncio.Task] = []
    agent_tasks: list[asyncio.Task] = []
    sample_rate = int(getattr(source, "sample_rate", 16_000))

    async def _channel_frames(q: asyncio.Queue):
        while True:
            blk = await q.get()
            if blk is None:  # end-of-channel sentinel
                return
            yield blk

    async def _stt_for_channel(channel: Channel, q: asyncio.Queue) -> None:
        default_diar = ChannelTrickDiarizer()
        async for seg in engine.stream_transcribe(
            _channel_frames(q), sample_rate=sample_rate
        ):
            if not seg.meta.get("final"):  # downstream acts only on finalized turns
                continue
            seg = seg.with_channel(channel)
            if diarizer is not None:
                seg = next(iter(diarizer.assign_speakers([seg], sample_rate=sample_rate)))
            elif channel is not Channel.MIXED:
                seg = next(iter(default_diar.assign_speakers([seg])))
            if agent is not None:
                agent_tasks.append(asyncio.create_task(_safe_on_segment(agent, seg)))
            await seg_q.put(seg)

    async def _router() -> None:
        async for channel, frames in source.astream():
            q = chan_queues.get(channel)
            if q is None:  # spin up a per-channel STT task on first sight
                q = asyncio.Queue(maxsize=audio_queue_max)
                chan_queues[channel] = q
                stt_tasks.append(asyncio.create_task(_stt_for_channel(channel, q)))
            await q.put(np.asarray(frames))  # backpressure to the source
        for q in chan_queues.values():
            await q.put(None)  # sentinel each channel

    async def _supervisor() -> None:
        await _router()
        if stt_tasks:
            await asyncio.gather(*stt_tasks, return_exceptions=True)
        if agent_tasks:
            await asyncio.gather(*agent_tasks, return_exceptions=True)
        await seg_q.put(None)  # final sentinel

    sup = asyncio.create_task(_supervisor())
    try:
        while True:
            seg = await seg_q.get()
            if seg is None:
                break
            yield seg
    finally:
        sup.cancel()
        for t in [*stt_tasks, *agent_tasks]:
            t.cancel()


async def _safe_on_segment(agent: AgentConsumer, seg: TranscriptSegment) -> None:
    """Run ``agent.on_segment`` without letting a failure crash the stream."""
    try:
        await agent.on_segment(seg)
    except Exception:  # noqa: BLE001 - agent/RAG failure must not kill capture
        pass


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
