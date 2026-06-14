---
name: hearing-live-pipeline
description: Use when building the streaming / live / real-time milestone of the hearing meeting-transcription library — turning the batch (record-then-transcribe) path into a low-latency loop that emits transcript segments as people speak. Triggers on streaming STT, real-time transcription, live captions, RealtimeSTT, whisper_streaming, SimulStreaming, WhisperLive, OpenAI Realtime API (gpt-realtime-whisper), Pipecat, LiveKit Agents, VAD / voice activity detection, silero-vad, webrtcvad, utterance / turn finalization, partial vs final segments, word-level timestamps for keyword triggers, feed_audio, asyncio.Queue decoupling, backpressure between capture/STT/diarization/agent stages, latency budget (VAD + STT + LLM TTFT + tool/RAG + transport), semantic turn detection, mid-sentence pause handling, and any task that adds a streaming capture/sink without changing the STT or agent interfaces.
---

# hearing-live-pipeline

The **streaming milestone (milestone 2)** of `hearing`: additive on top of the batch path. The whole architectural payoff is that you **swap the batch capture source and segment sink for streaming ones while the `STTEngine` and agent (`AgentConsumer`) interfaces stay byte-for-byte unchanged** ([[hearing-stt]], [[hearing-agents]], [[hearing-architecture]]). The live milestone implements the existing `STTEngine.stream_transcribe` method — it does NOT define a new Protocol. If a change to go live forces an edit to the STT or agent Protocol, the seam is in the wrong place — stop and fix the seam.

> The shared data model (`TranscriptSegment`, `TimeSpan` as integer ms, `Channel`) is defined by [[hearing-architecture]] in `hearing/types.py` — import it from there, do not redefine it.

## The core abstraction

**A live pipeline is a set of independent async stages connected by bounded `asyncio.Queue`s, each emitting `TranscriptSegment`s, where downstream stages act only on FINALIZED (turn-end) segments.**

```
capture ──audio chunks──▶ VAD/utterance ──finalized audio──▶ STT ──TranscriptSegment──▶ (diarization) ──▶ agent
  (task)      Queue          (task)            Queue        (task)        Queue            (task)      (task)
```

The batch path is `audio frames -> STTEngine.transcribe() -> Iterable[TranscriptSegment]`. The live path is `STTEngine.stream_transcribe(frames, *, sample_rate) -> AsyncIterator[TranscriptSegment]` — the *same* `TranscriptSegment` flowing through a queue instead of a return value. Reuse the `TranscriptSegment` dataclass verbatim; do not add fields. Finalization is signalled by `meta['final']` (the SSOT convention from [[hearing-architecture]]); partials have it falsy. Optional word-level timestamps live in `meta` too (e.g. `meta['words']`). Model the transcript itself with the **annotation-systems** global skill (standoff intervals, rational/integer time, never bare floats).

## Non-negotiable principles

1. **Stages are separate async tasks joined by bounded queues — never one big coroutine.** A slow LLM/RAG call must never stall audio capture. Bounded queues (`asyncio.Queue(maxsize=N)`) give you backpressure for free: a wedged consumer eventually blocks its producer instead of growing memory without limit. Capture is the one stage that must NEVER block — if its queue is full, drop or downsample, never `await put()` indefinitely on the capture path.

2. **Act on FINALIZED segments, not partials.** A segment is finalized when `seg.meta.get('final')` is truthy; partial/interim text (falsy `meta['final']`) churns word-by-word and will make an agent thrash. Trigger agent work (notes, suggested questions, RAG) on turn-end. Use partials only for (a) live captions UI and (b) word-level keyword spotting mid-utterance. (The frontend's `isFinal` maps from `meta['final']` — see [[hearing-frontend]].)

3. **VAD owns utterance boundaries, not fixed chunking.** The canonical loop is **VAD detect speech -> buffer the utterance -> on silence/turn-end transcribe the buffer -> emit one FINALIZED `TranscriptSegment`.** Fixed time-slicing cuts words in half and wrecks WER; only send meaningful speech to STT.

4. **Keep the STT call behind the same facade as batch.** The streaming engine is an implementation detail injected into the pipeline. `feed_audio()`-style engines, WebSocket engines, and the managed OpenAI Realtime session all hide behind the one `STTEngine.stream_transcribe(frames, *, sample_rate)` method that yields `TranscriptSegment`s — there is no separate streaming Protocol. This is what lets you A/B local vs cloud per-stage (Stage 3 of the staged plan).

5. **The channel split gives "me vs them" for free — preserve it into the live path.** The BlackHole+Aggregate capture keeps mic on one channel, system audio on another. Carry that `Channel` label on every `TranscriptSegment` before diarization even runs ([[hearing-diarization]] / [[hearing-audio-capture]]). Don't re-derive identity you already have.

## Streaming STT building blocks (decision table)

| Library | Transport / API | VAD | Engines | Speaker ID | Pick it when |
|---|---|---|---|---|---|
| **RealtimeSTT** (`KoljaB/RealtimeSTT`) [1] | in-proc Python; mic OR `feed_audio()` | WebRTC + Silero (both) | faster-whisper default; whisper.cpp, Parakeet, Moonshine via extras | no | **Default / most batteries-included.** Fastest path to a working live POC; callbacks for realtime text; wake words. |
| **whisper_streaming** (`ufal/whisper_streaming`) [2] | in-proc; long-form | implicit (LocalAgreement) | faster-whisper, mlx-whisper, OpenAI API | no | Long uninterrupted speech; you want the **LocalAgreement** stabilization policy. Superseded by SimulStreaming. |
| **SimulStreaming** (same author) [2] | in-proc | AlignAtt policy | whisper-family | no | Lower latency than whisper_streaming; **AlignAtt** attention-based emission policy. |
| **WhisperLive** (`collabora/WhisperLive`) [3] | WebSocket server + clients | server-side | faster-whisper, TensorRT-LLM, OpenVINO | optional online pyannote (cosine-sim clustering) | You want a **GPU server** + thin browser/iOS clients, word-level timestamps, custom vocab, built-in live speaker ID. |
| **OpenAI Realtime API** (`gpt-realtime-whisper`) [4] | managed WebSocket/WebRTC | server-side | hosted | needs `gpt-4o-transcribe-diarize` | Latency/accuracy of local is insufficient and you accept cloud + per-minute cost. **Incremental deltas; caveats below.** |

VAD-only building blocks (chunking layer): **silero-vad** (neural, accurate, ~1 file, recommended default) vs **webrtcvad** (C, ultra-light, lower accuracy on noisy meeting audio) [5]. RealtimeSTT and Pipecat both wrap Silero by default.

**Orchestration frameworks** (use instead of hand-rolling the queue graph when you want batteries): **Pipecat** (`pipecat-ai/pipecat`) — frame-based pipeline, `Transport.in -> VADProcessor(Silero) -> STTService -> custom FrameProcessor`; intercept `TranscriptionFrame` and `asyncio.create_task` fire-and-forget to the agent [6][7]. **LiveKit Agents** — WebRTC room model, spawns an isolated `AgentSession` per participant for true multi-channel transcription, publishes back over the `lk.transcription` stream [6][8]. For `hearing`'s single-machine macOS capture, a hand-rolled `asyncio.Queue` graph (below) is lighter than either; reach for Pipecat/LiveKit only when you need multi-participant WebRTC.

## OpenAI Realtime API caveats (verified June 2026)

- Model: `gpt-realtime-whisper`; session `type: "transcription"`.
- Deltas arrive on `conversation.item.input_audio_transcription.delta`; finals on `conversation.item.input_audio_transcription.completed`. **Match by `item_id`** — cross-turn completion ordering is NOT guaranteed.
- Deltas may **lag until end of turn** in practice — don't assume true word-by-word.
- For diarization you need `gpt-4o-transcribe-diarize` (separate model). Some older transcribe model versions are slated for retirement ~June 2026 — keep the model name a config value, never a literal [4].

## Latency budget model

Cumulative end-to-end latency of the live loop:

```
L_total ≈ L_vad + L_stt + L_llm_ttft + L_tool/rag + L_tts + L_transport
```

| Term | What | Typical |
|---|---|---|
| `L_vad` | VAD turn-end decision | ~100–500 ms |
| `L_stt` | streaming STT processing | ~100 ms–2 s (chunk-size dependent) |
| `L_llm_ttft` | LLM time-to-first-token, streaming | ~few hundred ms (see **claude-api** for model TTFT/pricing) |
| `L_tool/rag` | tool call / vector retrieval | tens of ms – seconds (offload async, cache!) |
| `L_tts` | TTS time-to-first-chunk (only if voice reply) | ~hundreds of ms |
| `L_transport` | WebRTC/WS routing | ~tens of ms |

Streaming targets **hundreds of ms to ~1–2 s** end-to-end; heavy un-optimized RAG or on-device embeddings push past ~2 s and cause conversational overlap [6][7]. For "surface a doc / take a note" tasks the budget is forgiving; for live captions keep the STT chunk small. **Semantic turn detection beats naive VAD:** plain VAD fires on mid-sentence thinking pauses (premature triggers); a small classifier over the partial transcript decides whether the utterance is structurally complete before signaling the agent [6]. Adopt it once naive-VAD false turn-ends become annoying.

## Canonical hand-rolled pipeline (Python)

Progressive disclosure: the simple thing is one function returning an async iterator of finalized segments; the complex things (engine choice, queue sizes, VAD params) are keyword-only with smart defaults. Stages are small focused functions; the `STTEngine` is injected (DI), not constructed inside, and the live path drives its `stream_transcribe` method.

```python
"""Live transcription pipeline: decoupled async stages over bounded queues.

Swaps the batch capture/sink for streaming; the TranscriptSegment dataclass and
the agent interface are unchanged from the batch path.
"""
from __future__ import annotations
import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from hearing.types import TranscriptSegment  # reused verbatim from the batch path


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    sample_rate: int = 16_000
    audio_queue_max: int = 50        # backpressure bound, capture->vad
    segment_queue_max: int = 100     # backpressure bound, stt->agent
    vad_silence_ms: int = 700        # turn-end after this much trailing silence


async def transcribe_stream(
    capture: AsyncIterator[bytes],
    stt: "STTEngine",                       # injected; hides RealtimeSTT/WhisperLive/OpenAI
    *,
    vad: "Vad | None" = None,               # default: silero
    config: PipelineConfig = PipelineConfig(),
) -> AsyncIterator[TranscriptSegment]:
    """Yield FINALIZED TranscriptSegments as utterances complete. The whole live
    milestone in one entry point; stages run as separate tasks so a slow consumer
    never stalls capture (bounded queues apply backpressure)."""
    vad = vad or _default_silero_vad()
    audio_q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=config.audio_queue_max)
    seg_q: asyncio.Queue[TranscriptSegment | None] = asyncio.Queue(maxsize=config.segment_queue_max)

    async def capture_task() -> None:
        async for chunk in capture:
            try:
                audio_q.put_nowait(chunk)      # NEVER block capture
            except asyncio.QueueFull:
                pass                            # drop oldest-policy lives here
        await audio_q.put(b"")                  # sentinel

    async def vad_stt_task() -> None:
        # VAD -> buffer utterance -> on turn-end stream_transcribe -> emit FINAL segments
        async for utterance in vad.utterances(audio_q, silence_ms=config.vad_silence_ms):
            async for seg in stt.stream_transcribe(utterance, sample_rate=config.sample_rate):
                if seg.meta.get("final"):       # downstream acts only on finalized turns
                    await seg_q.put(seg)
        await seg_q.put(None)                   # sentinel

    tasks = [asyncio.create_task(capture_task()), asyncio.create_task(vad_stt_task())]
    try:
        while (seg := await seg_q.get()) is not None:
            yield seg
    finally:
        for t in tasks:
            t.cancel()
```

Agent consumer (fire-and-forget so the agent can never stall the stream — mirror Pipecat's pattern [7]):

```python
async def run_agent_loop(segments: AsyncIterator[TranscriptSegment], agent: "AgentConsumer") -> None:
    async for seg in segments:                 # already FINALIZED (seg.meta['final'] truthy)
        asyncio.create_task(_safe(agent.on_segment, seg))   # don't await -> no backpressure onto STT

async def _safe(fn: Callable, seg: TranscriptSegment) -> None:
    try:
        await fn(seg)
    except Exception as exc:                    # agent/RAG failure must not crash the media stream
        # log via the project's error decorator; see CLAUDE.md "separate error concerns"
        ...
```

Generator/async-iterator hygiene (sentinels, `aclose`, never leaking tasks): follow the **python-iterables** global skill.

## Word-level mid-utterance triggers

When you need a keyword to fire *before* turn-end (e.g. "action item", a person's name), enable word timestamps (`word_timestamps=True` on Whisper-family, or WhisperX) and scan the partial/interim stream for the token; fire the agent on the *word event* while still emitting the FINALIZED segment normally at turn-end. Keep this opt-in (keyword-only `on_keyword=` callback), off by default.

## Staged rollout (where this milestone sits)

- **Stage 1 (done): batch DIY** — BlackHole+Aggregate capture, WhisperX+pyannote after the meeting. Facade the STT call. ([[hearing-stt]])
- **Stage 2 (this skill): live streaming** — add RealtimeSTT (faster-whisper or Parakeet-MLX) + silero-vad; emit finalized utterances to an `asyncio.Queue`; channel split = instant "me vs them".
- **Stage 3: agent loop** — consume the queue; post-utterance triggers (notes, questions, RAG) ([[hearing-agents]]). Add OpenAI Realtime / Deepgram streaming only if local latency/accuracy is insufficient.

**Decision threshold:** stay local while Apple-Silicon latency is acceptable (M2+ runs medium/turbo near real time); switch a stage to cloud streaming (Deepgram for latency, OpenAI Realtime for managed diarization) when WER on real meetings exceeds tolerance or you need several concurrent streams.

## CLI / interface surface

Expose the live loop via `argh` (`hearing live --engine realtimestt --vad silero`); HTTP/WS for a captions UI; see the **python-dispatching** global skill. Persist recordings/transcripts through `dol` stores (**python-storage**). The agent layer defaults to Claude but stays pluggable — model ids/pricing/tool-use in the **claude-api** global skill. Before reaching for any of these PyPI libs, check the user's own ecosystem first (**my-packages** / **local-package-ecosystem**).

## Common pitfalls

1. **One mega-coroutine** doing capture+STT+agent — first slow LLM call stalls audio. Split into tasks + queues.
2. **Unbounded queues** — a wedged agent silently eats memory. Always `maxsize=`.
3. **Awaiting the agent on the STT path** — couples STT latency to agent latency. Fire-and-forget.
4. **Acting on partials** — agent thrashes on word-by-word churn. Act only when `seg.meta.get('final')` is truthy.
5. **Fixed time-slice chunking** instead of VAD utterances — cuts words, tanks WER.
6. **Hard-coding the streaming engine** instead of injecting the `STTEngine` (and driving `stream_transcribe`) — breaks the local/cloud A/B and the "interfaces unchanged" payoff.
7. **Re-deriving "me vs them"** with fingerprinting when the channel split already told you.
8. **Bare-float timestamps** — use integer ms / rational time (annotation-systems).

## References

`references/from-research-reports.md` — condensed source passages with citations + URLs.
`references/key-links.md` — the canonical repos/docs for streaming STT and pipeline frameworks.
