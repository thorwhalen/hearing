---
name: hearing-diarization
description: Use when working on speaker attribution in the "hearing" meeting-transcription library — turning a transcript into a who-spoke-when, speaker-labeled (diarized) transcript, separating remote participants, and deciding which library to run. Triggers on diarization, speaker diarization, who spoke when, speaker labels, Speaker 1/Speaker 2, speaker turns, speaker segmentation, speaker attribution, "me vs them", local vs remote speaker, channel energy / channel trick, dual VAD, speaker identification, voice fingerprinting, voice enrollment, speaker embedding, pyannote.audio, pyannote community-1, speaker-diarization-3.1, NVIDIA NeMo Sortformer/MSDD, WhisperX diarize, SpeechBrain ECAPA/x-vector, DER (diarization error rate), or feeding speaker labels into the agent prompt. Distinguish from raw transcription (that is hearing-stt) and from audio capture/channel layout (that is hearing-audio-capture).
---

# Hearing — Diarization & Speaker Attribution

How "hearing" answers **who spoke when**. Diarization turns a flat transcript into speaker-labeled turns; this skill covers the elegant channel-derived shortcut, the open-source diarizer landscape, and how speaker labels flow into the shared data model and the agent prompt.

## The two problems — keep them distinct

| Term | Question | Output | How hearing gets it |
|---|---|---|---|
| **Diarization** | who spoke *when* | anonymous `Speaker 1 / Speaker 2 …` turns over time | run a diarizer on the **system channel** |
| **Identification** | *which real person* is this | named identities (`"Alice"`, `"me"`) | the **channel trick** for "me"; optional enrollment for named remotes |

Diarization is anonymous and required. Identification is harder and mostly optional — and for the one identity that matters most (you), hearing gets it **for free** without any voice model.

## THE core idea — the channel trick (do this first, before reaching for a model)

[[hearing-audio-capture]] keeps **your mic on one channel** and **system audio (everyone else) on another** (BlackHole + Aggregate Device, or Core Audio taps — mic ch 1–2, system ch 3–4). So you already know who is local **for free**: measure per-channel energy.

- **Mic channel has energy → speaker is `"me"`** (a known, named speaker).
- **System channel has energy → a remote participant.**

This is simpler and more reliable than voice fingerprinting and is what ChatGPT Record's "detect the local mic source" / Meetily's dual-VAD "Me"/"Them" labeling amounts to [8][GD 30]. **Non-negotiable pipeline shape:**

1. Split the recording into `mic` and `system` mono channels.
2. Compute per-channel speech activity (energy threshold, or a real VAD: `silero-vad` neural / `webrtcvad` lightweight) → gives "me vs them" intervals *without any diarization model*.
3. **Run the diarizer on the `system` channel ONLY** to separate the remote speakers into `Speaker 1 / Speaker 2 …`.
4. Treat the `mic` channel as a single known speaker `"me"`; merge its intervals into the same timeline.

Running diarization on a single-speaker mic channel wastes compute and invites false splits. Running it on the *system* channel is where it earns its keep. The energy/VAD pass is the cheap, robust source of truth for the local/remote split — don't fingerprint your own voice when the wiring already tells you.

### When you only have one mixed channel (degraded mode)
If capture wasn't channel-split (single-source recording, or live before the split lands), fall back to diarizing the whole mix and, if you need "me", **voice enrollment**: enroll your embedding once (SpeechBrain ECAPA-TDNN or pyannote), then cosine-match segments [51]. Flag this path as lower-accuracy — overlap and crosstalk make it error-prone. Prefer the channel trick whenever the dual-channel capture is available.

## A diarized transcript IS a standoff interval annotation — model it that way

This is the load-bearing design decision. **Read the global `annotation-systems` skill** and follow it; do not invent a bespoke representation. The mapping:

- A diarized transcript = **standoff annotation**: speaker labels live *beside* the audio/transcript, referencing it by time interval, never inlined.
- Each turn is an **`(interval, speaker_label)` pair** — the `(reference, metadata)` primitive. Speaker is one **tier** on the timeline (transcript text is another tier; word timestamps a third).
- **Rational time, never floats** — integer milliseconds or `RationalTime(value, rate)`. pyannote's `Segment`/`Timeline`/`Annotation` (`pyannote.core`, MIT) is the gold-standard in-memory model; floats there are an interchange-boundary concession, snap to ms at storage.
- The idiomatic Python surface is **`Mapping`-like**: keys are intervals, values are `{speaker, source, confidence, provenance}`.
- Always store **provenance**: which diarizer + version + pipeline produced each label, and whether the speaker came from `channel` (me) or `diarizer` (remote). You will want to audit "why is this turn labeled Speaker 2?".

The shared data model is **not redefined here** — diarization writes into the same `TranscriptSegment` spine that [[hearing-architecture]] defines in `hearing.types`. A segment is a standoff annotation over the audio; diarization's whole job is to fill in its `speaker` field. Times are integer milliseconds (`TimeSpan`), never floats. Segments are frozen, so you **enrich by copy** with `.with_speaker(...)` — never mutate:

```python
from hearing.types import TranscriptSegment, TimeSpan, Channel, ME, THEM

# A segment STT produced, tagged with its capture channel but not yet a speaker:
seg = TranscriptSegment("Can you send the Q3 numbers?", TimeSpan(0, 1500), channel=Channel.MIC)

labeled = seg.with_speaker(ME)   # -> a new frozen copy; seg is untouched
labeled.speaker                  # "me"
labeled.span.start_ms            # 0  (integer ms — TimeSpan, never float seconds)
```

Provenance (which diarizer + version produced a label, and whether it came from the channel or an acoustic model) rides on the segment's `meta` mapping. Every diarizer satisfies one structural contract — the `Diarizer` Protocol from `hearing.interfaces` — so the pipeline never names a concrete engine:

```python
from typing import Iterable, Optional, Protocol, runtime_checkable
from hearing.types import TranscriptSegment

@runtime_checkable
class Diarizer(Protocol):
    """Labels who spoke — enriches segments with ``.speaker`` (enrich-by-copy)."""
    def assign_speakers(
        self,
        segments: Iterable[TranscriptSegment],
        *,
        audio: Optional["Any"] = None,        # the channel trick ignores this
        sample_rate: Optional[int] = None,
    ) -> Iterable[TranscriptSegment]:
        ...
```

## Library decision table (June 2026)

| Library | What it is | Pick it when | Watch out |
|---|---|---|---|
| **pyannote.audio** (MIT, **v4.x**) | Gold-standard diarization pipeline | Default for hearing. Run `pyannote/speaker-diarization-community-1` (newer, much better speaker counting/assignment than the legacy `3.1`) [7][49] | Pipeline weights are gated on Hugging Face — needs an HF token + accepting model terms. `community-1` is open; `precision-2` is a paid hosted service |
| **WhisperX** (BSD-ish) | faster-whisper + pyannote, bundled transcribe **and** diarize with word-level alignment | You want one call that returns word-timestamped, speaker-labeled text on a file [34] | Pulls in pyannote anyway (same HF gating). Great fit for the Stage-1 batch path |
| **NVIDIA NeMo** Sortformer / MSDD (Apache-2.0) | Production-scale diarization on NVIDIA GPUs | You have CUDA and big batch volume [50] | Some configs cap at ~4 speakers; NVIDIA-GPU oriented — not the Apple-Silicon default for this Mac-first project |
| **SpeechBrain** (Apache-2.0) | Speaker-embedding / verification building blocks (ECAPA-TDNN, x-vector) | You need **enrollment / fingerprinting** (named remotes or the single-channel "me" fallback), not a full pipeline [51] | It's components, not a turnkey diarizer — you assemble clustering yourself |

**Default for hearing:** channel trick for "me/them" + **pyannote `community-1`** (or **WhisperX** when you want transcription bundled) on the system channel, on-device on Apple Silicon. Facade the diarizer call behind a `Protocol` so NeMo/cloud can be swapped in later (Dependency Injection — same pattern [[hearing-stt]] uses for the STT engine).

## Concrete patterns

**The channel trick — `ChannelTrickDiarizer` (the free, reliable default).** No model, no audio: it reads each segment's capture channel and copies in a speaker label. `MIC` → `me_label` (`ME` = `"me"`), `SYSTEM` → `them_label` (`THEM` = `"them"`). Segments that already carry a speaker, or come from a `MIXED` channel, pass through unchanged — there is nothing to infer. This *is* `hearing.diarize.ChannelTrickDiarizer`:

```python
from dataclasses import dataclass
from typing import Iterable, Optional
import numpy as np
from hearing.types import ME, THEM, Channel, SpeakerLabel, TranscriptSegment

@dataclass
class ChannelTrickDiarizer:
    """Label speakers from the capture channel — the free, reliable default."""
    me_label: SpeakerLabel = ME       # "me"
    them_label: SpeakerLabel = THEM   # "them"

    def assign_speakers(
        self,
        segments: Iterable[TranscriptSegment],
        *,
        audio: Optional[np.ndarray] = None,   # unused; kept for interface parity
        sample_rate: Optional[int] = None,
    ) -> Iterable[TranscriptSegment]:
        """Yield segments with ``.speaker`` set from their ``.channel`` (enrich-by-copy)."""
        for seg in segments:
            if seg.speaker is not None:
                yield seg                                   # already labeled
            elif seg.channel is Channel.MIC:
                yield seg.with_speaker(self.me_label)       # local user
            elif seg.channel is Channel.SYSTEM:
                yield seg.with_speaker(self.them_label)     # remote participant
            else:
                yield seg                                   # MIXED: leave for a real diarizer
```
It is a generator (see `python-iterables`), so live mode consumes labeled segments as they finalize, and `me_label`/`them_label` are keyword-configurable, not magic constants. The channel energy / VAD pass that decides *which* channel is active lives in capture ([[hearing-audio-capture]]); by the time segments reach the diarizer they already carry a `Channel`, so the local/remote split is a pure channel→label mapping here.

**The upgrade — `PyannoteDiarizer` on the system channel.** To separate *multiple remote* speakers you need acoustic diarization. `hearing.diarize.PyannoteDiarizer` wraps `pyannote.audio` (default model `pyannote/speaker-diarization-3.1`; `community-1` is the recommended upgrade per the decision table above), runs the pipeline over the audio, and assigns each segment the diarized speaker whose turn overlaps it most. Run it on the **system channel only** — the mic channel is already known to be `"me"`:

```python
from hearing.diarize import PyannoteDiarizer

diarizer = PyannoteDiarizer(
    model="pyannote/speaker-diarization-3.1",  # or "...community-1"; gated weights
    hf_token=hf_token,                          # inject, never hardcode
    speaker_prefix="spk_",                      # "SPEAKER_00" -> "spk_SPEAKER_00"
)

# segments: STT output for the SYSTEM channel; audio: that channel's float32 mono ndarray
for seg in diarizer.assign_speakers(segments, audio=system_audio, sample_rate=sr):
    seg.speaker  # "spk_..." for each remote speaker; pre-labeled segments pass through
```
Internally it snaps pyannote's float-second turn boundaries to integer ms, then `_best_overlap` picks the most-overlapping turn per segment and `.with_speaker(...)` writes it in. If no audio is supplied it falls back to the `ChannelTrickDiarizer`. Both diarizers satisfy the same `Diarizer` Protocol, so the pipeline swaps one for the other by dependency injection (same pattern [[hearing-stt]] uses for the STT engine).

**Merging into one timeline:** mic-channel segments labeled `"me"` (from `ChannelTrickDiarizer`) + system-channel segments labeled by the acoustic diarizer share one integer-ms time axis — `hearing.types.merge_segments` interleaves them by start time. Resolve overlap by source priority (channel `"me"` wins for the mic interval) or keep both as overlapping segments (`annotation-systems` allows overlap by design — that *is* crosstalk, real signal). Use an interval tree (`intervaltree`, Apache-2.0) for overlap queries when joining diarized segments to transcript word spans.

## Feeding speaker labels into the agent

The agent ([[hearing-agents]]) needs to know *who asked what*. Per the GD report's integration guidance, **feed the channel-derived "me vs them" label plus the diarization labels into the agent prompt** so it can attribute questions and action items. Render the merged timeline as speaker-prefixed lines:

```
[me]        Can you send the Q3 numbers?
[Speaker 1] Sure, I'll drop them in the channel after this.
[Speaker 2] And can we get the forecast too?
```

This is also the natural unit for triggering: act on **finalized** segments (after the VAD/diarizer commits one), not partial text, so the agent doesn't churn. Live mode emits finalized, speaker-labeled `TranscriptSegment`s onto the async queue described in [[hearing-architecture]].

## Evaluation & quality

- **DER (Diarization Error Rate)** is the standard metric (miss + false-alarm + confusion). Reference points from the reports: pyannote ~18.8% DER on AMI, ~21.7% on DIHARD III; `community-1` improves speaker counting/assignment over `3.1` [7][49]. Use `pyannote.metrics` (DER, JER) for evaluation.
- **Meetings are the hard case** — overlap, crosstalk, jargon push real-world numbers worse than clean-audio headlines. The channel split *structurally removes* the hardest confusion (me-vs-everyone), which is exactly why it beats a single mixed-channel diarizer here.
- **Disagreement is signal** (per `annotation-systems`): preserve overlapping turns rather than forcing one speaker per instant.

## Storage

Persist diarization output through the dol-based stores from [[hearing-architecture]] (see `python-storage`): a segments store keyed by recording id, values serialized speaker-labeled `TranscriptSegment` lists (e.g. via `Transcript.to_jsonable`). Keep diarization **standoff** from the audio and from the transcript text so each can be recomputed independently (re-diarize with a better model without re-transcribing).

## References

`references/from-research-reports.md` — the diarization passages from both source reports with `[n]` citation markers and matching URLs. `references/key-links.md` — curated repos/docs (pyannote, WhisperX, NeMo, SpeechBrain). For the deep annotation-modeling theory (standoff, rational time, interval trees, Allen's algebra, tiers), load the global **annotation-systems** skill rather than duplicating it here.
