"""Facade Protocols for the four pipeline concerns.

Every engine/component is dependency-injected as one of these; the pipeline
depends only on these interfaces, never on a concrete engine. Implementers
satisfy them *structurally* (``typing.Protocol``) — they do not subclass.

This is the contract the ``hearing-architecture`` skill defines and that every
other ``hearing-*`` concern implements against.
"""

from __future__ import annotations

from typing import (
    Any,
    AsyncIterator,
    Iterable,
    Iterator,
    Optional,
    Protocol,
    Sequence,
    runtime_checkable,
)

from hearing.types import Channel, TranscriptSegment


# ── Concern 1: capture ───────────────────────────────────────────────────────
@runtime_checkable
class CaptureSource(Protocol):
    """Audio source — the ONLY thing that differs between batch and live.

    Yields ``(channel, frames)`` so mic and system audio stay on separate
    channels all the way down. A batch implementation reads a file; a live
    implementation reads a device/tap.
    """

    sample_rate: int

    def frames(self) -> Iterator[tuple[Channel, "Any"]]:
        """Batch / sync: yield ``(channel, frames[n_samples])`` blocks to EOF."""
        ...

    def astream(self) -> AsyncIterator[tuple[Channel, "Any"]]:
        """Live / async: yield ``(channel, frames)`` blocks until stopped."""
        ...


# ── Concern 2: STT (the pluggable facade) ────────────────────────────────────
@runtime_checkable
class STTEngine(Protocol):
    """Speech-to-text.

    ``transcribe`` is the batch one-liner; ``stream_transcribe`` is the live
    variant. Both yield :class:`~hearing.types.TranscriptSegment` — same shape,
    same spine. The rest of the architecture never names a concrete engine.
    """

    def transcribe(
        self, audio: "Any", *, sample_rate: int, language: Optional[str] = None
    ) -> Sequence[TranscriptSegment]:
        """Batch: whole clip in (float32 mono ndarray), segments out."""
        ...

    async def stream_transcribe(
        self, frames: AsyncIterator["Any"], *, sample_rate: int
    ) -> AsyncIterator[TranscriptSegment]:
        """Live: yield interim then finalized segments as audio arrives.

        Mark interim vs final via ``meta`` (e.g. ``meta['final']``). See the
        ``hearing-live-pipeline`` skill — this is the milestone-2 entry point.
        """
        ...


# ── Concern 3: diarization / speaker-id (separate concern) ────────────────────
@runtime_checkable
class Diarizer(Protocol):
    """Labels who spoke — enriches segments with ``.speaker``.

    May use the audio (pyannote) or just the channel (the channel trick).
    Identity resolution (``spk_0`` -> ``"Alice"``) is an optional further step
    behind the same interface.
    """

    def assign_speakers(
        self,
        segments: Iterable[TranscriptSegment],
        *,
        audio: Optional["Any"] = None,
        sample_rate: Optional[int] = None,
    ) -> Iterable[TranscriptSegment]:
        """Yield segments with ``.speaker`` populated (enrich-by-copy)."""
        ...


# ── Concern 4: agent layer ───────────────────────────────────────────────────
@runtime_checkable
class AgentConsumer(Protocol):
    """Consumes the (labeled) transcript stream and does things.

    Running notes, suggested questions, RAG over related docs, post-meeting
    summaries. Defaults to Claude but stays pluggable (see the ``claude-api``
    skill for model ids / pricing / tool use).
    """

    async def on_segment(self, segment: TranscriptSegment) -> Optional[str]:
        """Called per finalized segment (live). Return an optional insight."""
        ...

    async def on_window(self, window: Sequence[TranscriptSegment]) -> Optional[str]:
        """Called on a window/turn or the whole transcript (batch).

        Return an optional insight (summary, action items, a suggested
        question, a surfaced document, ...).
        """
        ...
