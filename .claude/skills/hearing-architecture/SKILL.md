---
name: hearing-architecture
description: Use when designing, wiring, or modifying the hearing project's pipeline architecture — the SSOT for HOW the four layers (audio capture, STT, diarization/speaker-ID, agents) compose by dependency injection. Triggers on capture source, channel split, mic vs system audio, STT engine facade, transcribe(audio)->segments, streaming transcription, diarization interface, speaker label, TranscriptSegment, agent consumer, pipeline assembly, batch vs live, recipe-style composition, swap/substitute a component, Protocol/dataclass contracts, asyncio.Queue between stages, backpressure/decoupling, progressive disclosure of the pipeline, and any "how do the hearing-* skills fit together" or "what's the shared data model" question. This is the contract every other hearing-* skill (hearing-audio-capture, hearing-stt, hearing-diarization, hearing-agents) implements against.
---

# hearing Architecture

The SSOT for how the four layers of the `hearing` project wire together. Read this before touching any pipeline code; sibling skills ([[hearing-audio-capture]], [[hearing-stt]], [[hearing-diarization]], [[hearing-agents]]) implement the contracts defined here.

## The core abstraction: four separable concerns, one data spine

The pipeline decomposes into **four swappable concerns, each behind a clear interface** [DIY]:

```
capture  ──audio frames──▶  STT  ──segments──▶  diarization  ──labeled segments──▶  agents
(mic+system,                (pluggable          (who spoke                          (consume
 channel-split)              facade)             when/who)                           the stream)
```

**The one non-negotiable principle:** the *only* difference between **batch** and **live** is (a) the **source** (a file vs a streaming sink) and (b) the **trigger cadence** (run-once vs VAD/timer-driven loop). Everything downstream — the segment shape, the diarization interface, the agent contract — is identical. Do not build two pipelines. Build one pipeline parameterized by its source and trigger.

| | Source | Trigger | STT call | Agent cadence |
|---|---|---|---|---|
| **Batch** | `meeting.wav` (file) | run once | `transcribe(audio)` | after full transcript (or per segment) |
| **Live** | streaming capture sink | VAD turn-end / timer | `stream_transcribe(frames)` | on each finalized segment |

Everything is **composition + dependency injection**, never baked together. A pipeline is assembled from components that satisfy the Protocols below; you add/remove/substitute one without touching the rest (see "Recipe-style assembly").

## Non-negotiable design rules

1. **Facade each concern behind a Protocol** (`typing.Protocol`, structural — implementers don't subclass). The rest of the system depends on the *interface*, never a concrete engine. This is the whole point: swap Whisper for Deepgram, pyannote for the channel trick, Claude for a local LLM, by changing one line of assembly.
2. **`TranscriptSegment` is the data spine.** Every concern speaks it. It is a frozen dataclass; it is standoff interval annotation (see annotation-systems) — segments reference the audio by time, they don't contain it.
3. **Rational/integer time, never bare floats.** Times are integer milliseconds (or `(value, rate)` ticks), not float seconds. Float time accumulates error and breaks equality/round-trips. This is a day-one commitment (annotation-systems rule 2).
4. **Channel is first-class, not an afterthought.** Mic and system audio are *separate channels* and stay separate as far downstream as possible — the channel itself tells you "me vs them" for free (the channel trick, below), which is more reliable than voice fingerprinting [DIY].
5. **Stages are decoupled async tasks joined by queues.** Capture, STT, diarization, and agent run as separate `asyncio` tasks communicating over `asyncio.Queue`. A slow LLM call must never stall audio capture (backpressure/decoupling) [DIY]. This is the idiomatic-Python equivalent of Pipecat's frame pipeline and LiveKit's room model [GD] — synthesize it, don't import a framework.
6. **Progressive disclosure.** `transcribe("meeting.wav")` must work as a one-liner with smart defaults. Channel routing, engine selection, recording, and the live loop are all *optional keyword-only arguments*. Simple things simple; complex things possible.
7. **Keyword-only beyond the source.** The first positional arg is the thing being transcribed (path/source). Everything else (`engine=`, `diarizer=`, `agent=`, `channels=`, ...) is keyword-only. No magic numbers — cadence, thresholds, chunk sizes live in config dataclasses or kwargs.

## The shared data model (SSOT — every hearing-* skill imports these)

Define these in `hearing/types.py` (module docstring required). They are the contract.

```python
"""Shared data model for the hearing pipeline: the TranscriptSegment spine,
channel/speaker labels, and the time representation every concern speaks."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional


class Channel(str, Enum):
    """Which capture channel a segment came from. The channel *is* the
    'me vs them' signal: MIC = the local user, SYSTEM = remote participants."""
    MIC = "mic"        # the local user ("me")
    SYSTEM = "system"  # everyone else (came out of the speakers)
    MIXED = "mixed"    # single-channel / unknown source


# Speaker labels are open strings, not an enum: diarization invents
# "spk_0", "spk_1"; identification may resolve them to "me", "Alice".
SpeakerLabel = str
ME: SpeakerLabel = "me"  # canonical label for the local user


@dataclass(frozen=True, slots=True)
class TimeSpan:
    """A half-open interval [start_ms, end_ms) in integer milliseconds.
    Integer time, never float seconds — accumulation-safe and hashable."""
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """The data spine. A standoff interval annotation over the audio:
    it references the audio by `span` (it does not carry the samples).

    Required: text + span. Everything else is optional metadata that a
    concern *enriches* — STT sets text/span/confidence; diarization sets
    speaker; capture sets channel. Pass it through the pipeline, don't rebuild it.
    """
    text: str
    span: TimeSpan
    channel: Channel = Channel.MIXED
    speaker: Optional[SpeakerLabel] = None
    confidence: Optional[float] = None
    words: tuple["Word", ...] = ()          # optional word-level timing
    meta: Mapping[str, object] = field(default_factory=dict)  # provenance, engine id

    def with_speaker(self, speaker: SpeakerLabel) -> "TranscriptSegment":
        """Return a copy carrying a speaker label (frozen → copy, don't mutate)."""
        from dataclasses import replace
        return replace(self, speaker=speaker)


@dataclass(frozen=True, slots=True)
class Word:
    """Optional word-level timing (WhisperX / word_timestamps=True). Lets the
    agent trigger on a keyword mid-utterance instead of waiting for turn-end."""
    text: str
    span: TimeSpan
    confidence: Optional[float] = None
```

Why these choices: frozen + `slots=True` makes segments cheap, hashable, and safe to fan out to multiple consumers; `with_speaker`/`dataclasses.replace` is the enrich-by-copy pattern; `meta` carries provenance (which engine produced this) per annotation-systems rule 5. Storage of segments/recordings is **out of scope here** — use dol stores (see python-storage); transcripts persist as standoff annotations, never floats.

## The four facade Protocols (the contracts)

Define in `hearing/interfaces.py`. Implementers satisfy these structurally — they never import or subclass them.

```python
"""Facade Protocols for the four pipeline concerns. Every engine/component
is dependency-injected as one of these; the pipeline depends only on these."""
from __future__ import annotations
from typing import Protocol, Iterable, Iterator, AsyncIterator, Sequence, Optional
import numpy as np
from hearing.types import TranscriptSegment, Channel


# ── Concern 1: capture ──────────────────────────────────────────────
class CaptureSource(Protocol):
    """Audio source. The ONLY thing that differs batch vs live.
    Yields (channel, frames) so mic and system stay on separate channels
    all the way down. Batch impl reads a file; live impl reads a device/tap."""
    sample_rate: int

    def frames(self) -> Iterator[tuple[Channel, np.ndarray]]:
        """Batch / sync: yield (channel, frames[n_samples]) blocks to EOF."""
        ...

    def astream(self) -> AsyncIterator[tuple[Channel, np.ndarray]]:
        """Live / async: yield (channel, frames) blocks until stopped."""
        ...


# ── Concern 2: STT (the pluggable facade) ───────────────────────────
class STTEngine(Protocol):
    """Speech-to-text. `transcribe` is the batch one-liner; `stream_transcribe`
    is the live variant. Both yield TranscriptSegments — same shape, same spine."""

    def transcribe(
        self, audio: np.ndarray, *, sample_rate: int, language: Optional[str] = None
    ) -> Sequence[TranscriptSegment]:
        """Batch: whole clip in, segments out."""
        ...

    async def stream_transcribe(
        self, frames: AsyncIterator[np.ndarray], *, sample_rate: int
    ) -> AsyncIterator[TranscriptSegment]:
        """Live: yields interim then finalized segments as audio arrives.
        Mark interim vs final via meta (e.g. meta['final'])."""
        ...


# ── Concern 3: diarization / speaker-id (separate concern) ──────────
class Diarizer(Protocol):
    """Labels who spoke. Enriches segments with `.speaker`. May use audio
    (pyannote) or just the channel (the channel trick). Identity resolution
    (spk_0 -> 'Alice') is an optional further step, same interface."""

    def assign_speakers(
        self,
        segments: Iterable[TranscriptSegment],
        *,
        audio: Optional[np.ndarray] = None,
        sample_rate: Optional[int] = None,
    ) -> Iterable[TranscriptSegment]:
        """Yield segments with `.speaker` populated (enrich-by-copy)."""
        ...


# ── Concern 4: agent layer ──────────────────────────────────────────
class AgentConsumer(Protocol):
    """Consumes the (labeled) transcript stream and does things — running
    notes, suggested questions, RAG over related docs. Defaults to Claude
    but stays pluggable (see claude-api for model ids/pricing)."""

    async def on_segment(self, segment: TranscriptSegment) -> Optional[str]:
        """Called per finalized segment (live). Return optional surfaced insight."""
        ...

    async def on_window(
        self, window: Sequence[TranscriptSegment]
    ) -> Optional[str]:
        """Called on a window/turn or whole transcript (batch). Return insight."""
        ...
```

These improve on the POC's Protocols (`AudioRecorder`/`Transcriber`/`AIAgent` in `meeting_assistant.py`): the POC is **mic-only, returns bare `str` not segments, has no diarization, no channel concept, and OpenAI-baked**. Keep its clean Protocol+dataclass+DI structure; fix exactly those gaps.

## The channel trick (why channel is first-class)

Because capture keeps **mic on one channel and system audio on another** (BlackHole + Aggregate Device, or a Core Audio tap [DIY]), you know "who's local" for free: the MIC channel = you (`ME`), the SYSTEM channel = remote participants. So:

- Tag every segment with its `Channel` at capture time.
- Treat the MIC channel as a **known speaker** (`speaker=ME`) — no diarization needed.
- Run real diarization only on the **SYSTEM** channel to separate remote speakers.

This is simpler and more reliable than voice fingerprinting/enrollment [DIY]. A channel-aware `Diarizer` implementation is the default; pyannote-based diarization is the upgrade. See [[hearing-audio-capture]] (channel split) and [[hearing-diarization]].

## Recipe-style assembly (composition + DI)

The pipeline is a thin orchestrator that takes the four components as injected dependencies. Swapping one touches nothing else.

```python
"""Pipeline assembly: compose the four concerns by dependency injection.
Progressive disclosure — transcribe(path) just works; everything else is kwargs."""

# ---- the one-liner (batch, all defaults) -------------------------------
from hearing import transcribe
segments = transcribe("meeting.wav")            # -> list[TranscriptSegment]

# ---- swap the STT engine (one line) ------------------------------------
from hearing.engines import DeepgramSTT
segments = transcribe("meeting.wav", engine=DeepgramSTT())

# ---- add diarization + an agent, still batch ---------------------------
from hearing.diarize import PyannoteDiarizer
from hearing.agents import ClaudeAgent          # defaults to Claude; see claude-api
segments = transcribe(
    "meeting.wav",
    engine=DeepgramSTT(),
    diarizer=PyannoteDiarizer(),
    agent=ClaudeAgent(),
)

# ---- go LIVE: same components, only source + trigger change ------------
from hearing import live_transcribe
from hearing.capture import ChannelSplitCapture  # mic=ch0, system=ch1
async for segment in live_transcribe(
    source=ChannelSplitCapture(),                # the source is the only real change
    engine=DeepgramSTT(),                        # same engine facade
    diarizer=ChannelTrickDiarizer(),             # cheap: channel == speaker hint
    agent=ClaudeAgent(),                         # same agent facade
    trigger="vad",                               # cadence: vad turn-end | "timer"
):
    ...  # segment already carries text, span, channel, speaker
```

`transcribe`/`live_transcribe` are the facades. Their signature is `transcribe(source, *, engine=DefaultSTT(), diarizer=None, agent=None, record=None, language=None)` — first positional is the source, the rest keyword-only with smart defaults (rule 7). `record=` (a dol store) optionally persists audio/segments; `None` means don't.

### The orchestrator shape (batch and live share it)

```python
async def _run_pipeline(source, *, engine, diarizer, agent, trigger):
    """One pipeline. Batch = run source.frames() once; live = loop source.astream()
    with VAD/timer. Stages are decoupled async tasks joined by queues so a slow
    agent never stalls capture (backpressure)."""
    seg_q: asyncio.Queue[TranscriptSegment] = asyncio.Queue()

    async def capture_and_stt():
        async for channel, frames in source.astream():
            async for seg in engine.stream_transcribe(_frames_of(channel), sample_rate=source.sample_rate):
                if seg.meta.get("final"):                 # act on finalized segments only
                    await seg_q.put(seg.with_channel(channel))

    async def label_and_consume():
        while True:
            seg = await seg_q.get()
            seg = next(iter(diarizer.assign_speakers([seg]))) if diarizer else seg
            if agent:
                asyncio.create_task(agent.on_segment(seg))  # fire-and-forget; don't block
            yield seg

    # run capture and consumption as separate tasks (decoupling)
    ...
```

The generator/streaming idioms (yield finalized segments, fan out, fire-and-forget the agent) follow python-iterables. Act on **finalized** segments (after VAD turn-end) to avoid churning on partial text; word-level timestamps let the agent trigger on a keyword mid-utterance [DIY].

## How to add / remove / substitute a component

| Want to... | Do this | Touches |
|---|---|---|
| Use a different STT engine | write a class satisfying `STTEngine`, pass `engine=` | one assembly line |
| Run fully local (no cloud) | inject a local `STTEngine` (faster-whisper) + `ChannelTrickDiarizer` | assembly only |
| Add speaker diarization | pass `diarizer=PyannoteDiarizer()` | assembly only |
| Drop the agent | pass `agent=None` (the default) | nothing else |
| Swap Claude for a local LLM | write an `AgentConsumer`, pass `agent=` | one line (see claude-api for the default) |
| Go batch → live | change `source` + add `trigger="vad"`; reuse engine/diarizer/agent | source + trigger only |
| Persist transcripts/recordings | pass `record=<dol store>` | assembly only (python-storage) |

If a change forces edits in more than one concern, the interface is wrong — fix the Protocol, don't leak a concrete type across the boundary.

## Interfaces to the outside (CLI / HTTP / UI)

The Python facades (`transcribe`, `live_transcribe`) are the SSOT. Surface them, don't reimplement them:

- **CLI** via `argh`: `transcribe` → `hearing transcribe meeting.wav --engine deepgram`. See python-dispatching.
- **HTTP / UI**: wrap the same facades; the frontend is TS (Zod/zustand). Keep display concerns out of the data model (annotation-systems pitfall 5).

## What this skill does NOT decide (delegate)

- **Engine internals, model choice, WER/latency tradeoffs** → [[hearing-stt]] (and claude-api for the agent LLM).
- **macOS capture mechanics** (BlackHole, Aggregate Device, Core Audio taps, `sounddevice` channel slicing) → [[hearing-audio-capture]].
- **Diarization algorithms / pyannote / identity enrollment** → [[hearing-diarization]].
- **Agent behaviors / RAG / tool use / prompts** → [[hearing-agents]] + claude-api.
- **Transcript & audio persistence** (dol stores, standoff annotation storage) → python-storage + annotation-systems.
- **Find existing local packages before reaching for PyPI** → my-packages / local-package-ecosystem.

## References

Source extracts (with citation markers and URLs) in `references/from-research-reports.md`. Key external repos/docs in `references/key-links.md`. `[DIY]` = the DIY macOS pipeline report; `[GD]` = the AI-agents architecture (GD) report — both in `misc/docs/`.
