"""Shared data model for the hearing pipeline.

This is the SSOT data spine that every concern (capture, STT, diarization,
agents) speaks. A transcript is *standoff interval annotation* over the audio:
segments reference the audio by time (a :class:`TimeSpan`) and never carry the
samples themselves. Time is integer milliseconds — never bare float seconds —
so it is accumulation-safe, hashable, and round-trippable.

See the ``hearing-architecture`` skill for the rationale behind every choice
here, and the ``annotation-systems`` skill for the standoff-annotation theory.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Mapping, Optional, Sequence


class Channel(str, Enum):
    """Which capture channel a segment came from.

    The channel *is* the "me vs them" signal, for free: ``MIC`` is the local
    user, ``SYSTEM`` is everyone else (audio that came out of the speakers).
    ``MIXED`` is a single-channel / unknown source.
    """

    MIC = "mic"  # the local user ("me")
    SYSTEM = "system"  # remote participants (came out of the speakers)
    MIXED = "mixed"  # single-channel / unknown source


# Speaker labels are open strings, not an enum: diarization invents "spk_0",
# "spk_1"; identification may later resolve them to "me", "Alice", ...
SpeakerLabel = str
ME: SpeakerLabel = "me"  # canonical label for the local user
THEM: SpeakerLabel = "them"  # canonical label for "a remote participant"


@dataclass(frozen=True, slots=True)
class TimeSpan:
    """A half-open interval ``[start_ms, end_ms)`` in integer milliseconds.

    Integer time, never float seconds — accumulation-safe and hashable.

    >>> TimeSpan(0, 1500).duration_ms
    1500
    """

    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        """Length of the interval in milliseconds."""
        return self.end_ms - self.start_ms

    @classmethod
    def from_seconds(cls, start: float, end: float) -> "TimeSpan":
        """Build a span from float seconds (e.g. from an STT engine)."""
        return cls(int(round(start * 1000)), int(round(end * 1000)))


@dataclass(frozen=True, slots=True)
class Word:
    """Optional word-level timing (WhisperX / ``word_timestamps=True``).

    Lets an agent trigger on a keyword mid-utterance instead of waiting for the
    end of a turn. Purely optional metadata on a :class:`TranscriptSegment`.
    """

    text: str
    span: TimeSpan
    confidence: Optional[float] = None


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """The data spine — a standoff interval annotation over the audio.

    Required fields are ``text`` and ``span``. Everything else is optional
    metadata that a concern *enriches*: STT sets ``text``/``span``/
    ``confidence``; capture sets ``channel``; diarization sets ``speaker``.
    Segments are frozen — enrich by copying (``with_speaker``/``with_channel``),
    never mutate.

    >>> seg = TranscriptSegment("hello", TimeSpan(0, 500))
    >>> seg.with_speaker(ME).speaker
    'me'
    >>> seg.text
    'hello'
    """

    text: str
    span: TimeSpan
    channel: Channel = Channel.MIXED
    speaker: Optional[SpeakerLabel] = None
    confidence: Optional[float] = None
    words: tuple[Word, ...] = ()  # optional word-level timing
    meta: Mapping[str, object] = field(default_factory=dict)  # provenance, engine id

    def with_speaker(self, speaker: SpeakerLabel) -> "TranscriptSegment":
        """Return a copy carrying a speaker label (frozen -> copy, don't mutate)."""
        return replace(self, speaker=speaker)

    def with_channel(self, channel: Channel) -> "TranscriptSegment":
        """Return a copy carrying a channel label (frozen -> copy, don't mutate)."""
        return replace(self, channel=channel)


@dataclass(frozen=True, slots=True)
class Transcript:
    """A finished transcript: an ordered collection of segments plus metadata.

    Iterable and ``len``-able, so it stands in for a ``Sequence`` of segments
    wherever the architecture's facades return "segments". Adds convenience
    accessors the CLI/agents need.

    >>> t = Transcript((TranscriptSegment("a", TimeSpan(0, 1000), speaker=ME),
    ...                  TranscriptSegment("b", TimeSpan(1000, 2000), speaker=THEM)))
    >>> t.text
    'a b'
    >>> len(t)
    2
    >>> sorted(t.speakers)
    ['me', 'them']
    """

    segments: tuple[TranscriptSegment, ...] = ()
    sample_rate: Optional[int] = None
    meta: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Accept any sequence; normalize to a tuple (frozen -> object.__setattr__).
        if not isinstance(self.segments, tuple):
            object.__setattr__(self, "segments", tuple(self.segments))

    def __iter__(self):
        return iter(self.segments)

    def __len__(self) -> int:
        return len(self.segments)

    def __getitem__(self, i):
        return self.segments[i]

    @property
    def text(self) -> str:
        """All segment texts joined by a single space."""
        return " ".join(s.text.strip() for s in self.segments if s.text.strip())

    @property
    def duration_ms(self) -> int:
        """End of the last segment, or 0 if empty."""
        return max((s.span.end_ms for s in self.segments), default=0)

    @property
    def speakers(self) -> set[SpeakerLabel]:
        """The distinct speaker labels present (ignoring ``None``)."""
        return {s.speaker for s in self.segments if s.speaker is not None}

    def with_meta(self, **kw: object) -> "Transcript":
        """Return a copy with extra metadata merged in."""
        return replace(self, meta={**self.meta, **kw})

    def formatted(self, *, speakers: bool = True, timestamps: bool = True) -> str:
        """Render as a human-readable transcript, one line per segment."""
        lines = []
        for s in self.segments:
            prefix = ""
            if timestamps:
                prefix += f"[{_ms_to_clock(s.span.start_ms)}] "
            if speakers and s.speaker is not None:
                prefix += f"{s.speaker}: "
            lines.append(f"{prefix}{s.text.strip()}")
        return "\n".join(lines)

    def to_jsonable(self) -> list[dict]:
        """A plain ``list[dict]`` ready for ``json.dumps`` (segments only)."""
        return [
            {
                "text": s.text,
                "start_ms": s.span.start_ms,
                "end_ms": s.span.end_ms,
                "channel": s.channel.value,
                "speaker": s.speaker,
                "confidence": s.confidence,
            }
            for s in self.segments
        ]


def _ms_to_clock(ms: int) -> str:
    """Format milliseconds as ``HH:MM:SS`` (helper for ``Transcript.formatted``)."""
    total_s = ms // 1000
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def merge_segments(*segment_groups: Sequence[TranscriptSegment]) -> list[TranscriptSegment]:
    """Merge several segment sequences into one list ordered by start time.

    Used when transcribing the mic and system channels separately and then
    interleaving them back into a single chronological transcript.
    """
    merged = [seg for group in segment_groups for seg in group]
    merged.sort(key=lambda s: (s.span.start_ms, s.span.end_ms))
    return merged
