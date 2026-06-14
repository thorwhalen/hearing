---
name: hearing-agents
description: Use when building the agent / "copilot" layer of the hearing meeting-transcription project — the thing that consumes a transcript and produces feedback (summaries, action items, decisions, follow-up research in batch; running notes, suggested questions, relevant docs, fact-checks live). Triggers on agent layer, meeting copilot, post-meeting summary, action items, decision extraction, follow-up research, live notes, suggested questions, real-time RAG, fact-check, queue consumer, asyncio.Queue of utterances, finalized segments, FrameProcessor, Pipecat, LiveKit Agents, RealTimeAgentPipeline, non-blocking transcript intercept, backpressure / decoupling the LLM from capture, feeding me/them + diarization labels into the prompt, vector store over meeting context, LlamaIndex, Qdrant, web search during a meeting, deep-research follow-up, SimpleLLMAgent, pluggable LLM backend, batch-vs-live unification. The agent defaults to Claude but stays pluggable.
---

# Hearing — Agent Layer

The agent layer is **the point of the project**. STT and the pipeline ([[hearing-stt]], [[hearing-live-pipeline]]) exist to feed it. This skill covers how agents consume a transcript and emit feedback.

## The one unification (build everything around this)

**The SAME agent interface serves batch and live.** The canonical agent facade is the `AgentConsumer` Protocol (defined in `hearing/interfaces.py`) with exactly two async methods, `on_segment` (live, per finalized segment) and `on_window` (batch / a window or the whole transcript), each returning an optional insight. The only differences between batch and live are (1) the **source** (a complete file vs. finalized segments arriving off a queue) and (2) which method fires (`on_window` once vs. `on_segment` repeatedly).

The segments these methods consume are `TranscriptSegment`s from the shared data model — `TranscriptSegment`, `TimeSpan` (integer milliseconds, never float seconds), `Channel`, etc. — defined by [[hearing-architecture]] in `hearing/types.py`. **Import them from `hearing.types`; never redefine a segment/utterance type here.**

```python
from typing import Optional, Protocol, Sequence, runtime_checkable

from hearing.types import TranscriptSegment   # the shared spine — never redefine

@runtime_checkable
class AgentConsumer(Protocol):
    """The pluggable agent facade. The one interface batch and live both satisfy."""

    async def on_segment(self, segment: TranscriptSegment) -> Optional[str]:
        """Live: called per finalized segment. Return an optional insight."""
        ...

    async def on_window(self, window: Sequence[TranscriptSegment]) -> Optional[str]:
        """Batch: called on a window/turn or the whole transcript. Return an optional insight."""
        ...
```

- **Batch** = call `on_window` ONCE with the full transcript. Drives summaries, action items, decisions, follow-up research.
- **Live** = call `on_segment` as each new finalized segment lands (and optionally `on_window` on a debounced window of recent segments). Drives running notes, suggested questions, surfaced docs, fact-checks.
- The agent body does NOT know which mode it's in. The **runner** (batch loop vs. queue consumer) owns the difference. This is the open-closed boundary: add an agent without touching the runner; add a mode without touching the agent.

**Return shape.** The Protocol's contract is the minimal `Optional[str]` insight. A richer structured return (a `Feedback`-style value — `kind` / `body` / `refs` / `confidence` discriminating note / question / doc-ref / fact-check / summary) is an *optional* convention a sink can adopt, not part of the `AgentConsumer` Protocol name or signature. Concrete impls live in `hearing/agents.py`: `ClaudeAgent` (default — anthropic SDK, model `"claude-sonnet-4-6"`, with a `context` field for context-connection) and `ExtractiveAgent` (deterministic, dependency-free offline fallback); pick one with `build_default_agent(prefer="auto"|"claude"|"extractive")`, and `summarize_transcript(...)` is the batch one-liner.

**LLM specifics live elsewhere.** Model ids, pricing, tool-use schemas, structured output, the `web_search` server tool, streaming, prompt caching — all of that belongs to the global **claude-api** skill. Read it before writing any `messages.create` / tool-definition / model-id code. This layer defaults to Claude (latest most-capable) but stays pluggable behind `LLMClient` (the user also has local `oa` for OpenAI — check **my-packages** before reaching for a vendor SDK directly).

## Batch vs. live decision table

| Concern | Batch (post-meeting) | Live (during meeting) |
|---|---|---|
| Source | transcript file / store (see python-storage) | `asyncio.Queue[TranscriptSegment]` off the pipeline |
| Trigger | once, on meeting end | per finalized utterance, or every N seconds, or on keyword |
| Latency budget | seconds–minutes; run deep models | sub-second to a few seconds; never stall capture |
| Typical agents | summary, action items, decisions, deep-research follow-up | running notes, suggested questions, doc surfacing, fact-check |
| Failure mode | retry the whole pass | drop/skip a tick; never crash the audio stream |
| Web search | deep-research mode (many queries, synthesized) — see **deep-research** | single targeted query on a triggered entity |

## Non-negotiable principles (live mode)

1. **Act on FINALIZED segments, not partials.** Trigger agents on VAD turn-end utterances. Partial/interim text churns — the agent re-reasons over text that's about to change. (Word-level timestamps from WhisperX let you *peek* for keyword spotting mid-utterance, but commit actions only on finalize.) See [[hearing-stt]].
2. **The agent must NEVER block capture.** A slow LLM call cannot stall audio capture, STT, or diarization. Decouple with `asyncio.create_task` (fire-and-forget) for the agent route, and keep capture/STT/diarization/agent as separate async tasks communicating via queues. This is Pipecat's `FrameProcessor` rule and the report's explicit "backpressure / decoupling" requirement.
3. **Feed speaker identity into the prompt.** Pass the channel-derived `me` vs. `them` label AND diarization labels so the agent knows *who asked what* ("the other party asked X" vs. "you said Y"). The channel trick (mic = me, system = them) is cheaper and more reliable than fingerprinting — see [[hearing-diarization]].
4. **Offload retrieval; cache it.** Vector search and web search run in a separate async task. Cache results to avoid redundant expensive lookups when the same entity recurs. RAG latency must not block the transcript stream.
5. **Context-connected, always.** Every agent is bound to a meeting AND a project. It can draw on accumulated knowledge (prior meetings' takeaways, the project codebase, research reports) AND pull outside info via web search. An agent with no context is just a chatbot.
6. **Coalesce / debounce live triggers.** Don't fire an agent on every one-word utterance. Debounce on a time window or a token threshold, or trigger on turn-boundary events (`on_user_turn_stopped`-style). Otherwise you burn tokens and produce noise.

## The queue-consumer pattern (live runner)

This is the heart of live mode. The pipeline emits finalized `TranscriptSegment`s onto a queue; the runner consumes them, accumulates a window, debounces, and dispatches agents non-blockingly.

```python
import asyncio
from typing import Sequence
from hearing.interfaces import AgentConsumer
from hearing.types import TranscriptSegment

async def live_runner(
    queue: "asyncio.Queue[TranscriptSegment]",
    agents: "Sequence[AgentConsumer]",
    sink: "FeedbackSink",
    *,
    debounce_s: float = 8.0,          # config, not magic number
    min_new_segments: int = 2,
):
    """Consume finalized segments; fire agents on a debounced cadence.

    Capture/STT/diarization run as OTHER tasks. This loop never touches audio.
    """
    window: tuple[TranscriptSegment, ...] = ()
    pending = 0
    last_fire = 0.0
    loop = asyncio.get_running_loop()
    while True:
        seg = await queue.get()                  # blocks on transcript, not on LLM
        window = (*window, seg)                  # accumulated context grows
        pending += 1
        for agent in agents:                     # per-segment hook, fire-and-forget
            asyncio.create_task(_run_segment(agent, seg, sink))
        now = loop.time()
        if pending >= min_new_segments and (now - last_fire) >= debounce_s:
            last_fire, pending = now, 0
            for agent in agents:                 # debounced window hook
                asyncio.create_task(_run_window(agent, window, sink))

async def _run_segment(agent: "AgentConsumer", seg: TranscriptSegment, sink: "FeedbackSink"):
    try:
        if (insight := await agent.on_segment(seg)) is not None:
            await sink.emit(insight)
    except Exception as e:                        # isolate failure; never crash the stream
        await sink.emit(f"{agent!r}: {e}")

async def _run_window(agent: "AgentConsumer", window: Sequence[TranscriptSegment], sink: "FeedbackSink"):
    try:
        if (insight := await agent.on_window(window)) is not None:
            await sink.emit(insight)
    except Exception as e:
        await sink.emit(f"{agent!r}: {e}")
```

`FeedbackSink` is a `Protocol` (`async def emit(self, insight)`) — route to a UI overlay (TS frontend), a notes file, or stdout. Keep it injected so the same runner serves any surface. (If you adopt the richer structured `Feedback` return convention, the sink accepts that value instead of a bare `str`.)

The **batch runner** is trivially the same shape — one `on_window` call over the complete transcript:

```python
async def batch_runner(
    transcript: "Sequence[TranscriptSegment]", agents, sink: "FeedbackSink"
):
    for agent in agents:                          # transcript is already complete
        if (insight := await agent.on_window(transcript)) is not None:
            await sink.emit(insight)
```

## Study/fork material — frameworks (don't reinvent the wire)

The reports name two frameworks for the live wire. Read their pattern, fork selectively; you likely don't need the full TTS/WebRTC stack for a notetaker.

- **Pipecat** (`pipecat-ai/pipecat`, Python, Daily) — frame-based pipeline; audio/text/images flow as `Frame`s through `FrameProcessor`s. The key pattern to steal: a custom `FrameProcessor` that intercepts `TranscriptionFrame` and **fire-and-forgets** to your agent without blocking the pipeline (see `references/`). Also exposes turn events (`on_user_turn_stopped`) ideal for batched-segment dispatch. Use when you want precise control over a linear frame pipeline.
- **LiveKit Agents** (`livekit/agents`, Python) — WebRTC room model; agents are server-side participants. For multi-speaker, a supervisor spawns one `AgentSession` per participant with its own VAD + STT, publishing transcripts on the `lk.transcription` stream. Use when you need production WebRTC media routing / multi-participant rooms / telephony. Heavier than a local notetaker needs.

**For hearing specifically:** the BlackHole channel split already gives you me/them for free, so you usually do NOT need LiveKit's per-participant room model. A lightweight asyncio queue + Pipecat-style non-blocking intercept is the right altitude. Reach for these frameworks' *patterns*, not necessarily their runtimes.

## Study/fork material — apps (closest to the goal)

- **anarlog** (formerly Hyprnote, `fastrepl/anarlog`, MIT) — local-first notetaker, real-time transcription, speaker ID, system-audio capture, **MCP server so Claude/ChatGPT can read/write notes**. Closest reference to hearing's goal; study its agent/notes boundary and MCP surface.
- **Meetily** (`Zackriya-Solutions/meetily`, MIT) — 100% local, mic+system capture, Ollama summarization, **pluggable AI (local / BYOK / hosted)** — study its provider abstraction for `LLMClient`.
- **Pluely** / **Natively** — live "copilot" overlay pattern (separate system/mic audio → live STT → LLM); Natively adds local RAG + meeting history. Study the overlay UX and the RAG-over-history wiring.

## RAG over project context

The agent's context-connection is RAG over the project: prior meetings' takeaways, the codebase, research reports. Pattern from the report (LiveKit + Qdrant + LlamaIndex):

1. Index project context into a vector store. **Qdrant** (vector DB) + **LlamaIndex** (data framework) is the report's stack; check **my-packages** / **python-storage** first — the user may already have a local store/embedding wrapper, and a `dol`-style key-value store (see python-storage) can back simpler cases.
2. On a triggered utterance, vectorize it, match against the collection, append retrieved chunks to the LLM prompt dynamically.
3. **Offload retrieval to a separate async task and cache** — never block the transcript stream; cache by query so recurring entities don't re-query.

Keep retrieval behind a `Retriever` Protocol (`async def search(self, query, *, k=...) -> Sequence[Chunk]`) injected into the agent (e.g. feeding `ClaudeAgent.context`), so the vector backend is swappable and testable with a fake.

## Web search (bringing the outside in)

Two modes, both behind a `WebSearch` Protocol:

- **Live, targeted** — one query on a triggered entity (a name, product, claim). For fact-check / "who is X" agents. The POC's heuristic (scan response for "look up / latest / who is" then extract a query) is a crude trigger; prefer **letting the LLM decide via tool use** (Claude's server-side `web_search` tool — see **claude-api**) over string-matching.
- **Batch, deep** — the follow-up-research mode: many queries, fetched sources, adversarial verification, synthesized cited report. This is exactly the **deep-research** global skill's job — delegate to it rather than hand-rolling a research loop.

## What to keep / fix from the POC's `SimpleLLMAgent`

(`priv/apps/meeting_assistant.py` — clean Protocol/dataclass scaffolding, but mic-only, OpenAI/LangChain, no channel-split.)

**Keep:** the `Protocol` interfaces (`AIAgent.analyze`), dataclass configs, dependency injection in the orchestrator, the separate `_audio_pipeline` / `_agent_pipeline` async tasks, the bounded context window (`deque(maxlen=...)`), and the LLM-interaction logging (great for evals/debugging).

**Fix / replace:**
- **No speaker identity.** `TranscriptSegment` has no speaker field — add `speaker` + `is_me` (channel-derived) and put it in the prompt.
- **Web-search trigger is string-matching** (`_should_search` scans for "search"/"latest"). Replace with LLM tool-use (claude-api) so the model decides and forms the query.
- **Fixed-interval polling** (`analysis_interval` sleep) churns and re-sends overlapping context. Move to **queue-driven + debounced** finalized-utterance triggers.
- **Vendor lock-in** (`langchain_openai.ChatOpenAI`). Hide behind `LLMClient`; default to Claude.
- **No RAG / no project context** — the agent only sees the rolling window. Wire project context in (e.g. via `ClaudeAgent.context`) + a `Retriever`.
- **Buffer = context window only.** `deque(maxlen=N)` silently drops history the summary agent needs. Persist the full transcript (standoff transcript storage — see annotation-systems and python-storage); use a window only for the live *trigger* prompt.

## Latency budget (live)

End-to-end live latency ≈ VAD turn-end + STT + LLM time-to-first-token + tool/RAG/web + transport. The report models tool/RAG retrieval as the dominant *variable* cost — un-optimized RAG or heavy on-device embeddings push past comfortable bounds. Mitigations: act on finalized turns (not every partial), offload + cache retrieval, stream LLM tokens, and use semantic turn-detection (don't fire on mid-sentence pauses). For "surface a doc / running note" tasks a few seconds is fine; only live captions need a tight STT chunk.

## CLI / interface

Expose batch and live runners via `argh` per **python-dispatching** (`hearing agents summarize <meeting>`, `hearing agents live`). Keep the agent set configurable (which agents, debounce, model) via kwargs/config, never hardcoded. Frontend overlay is TS — the `FeedbackSink` is the seam between Python agents and the UI.

## references/

- `references/from-research-reports.md` — the agent-pipeline slices of the DIY and GD reports (Pipecat `RealTimeAgentPipeline` snippet, LiveKit room/RAG diagrams, latency model, OSS apps to fork), with `[n]` markers and matching URLs.
- `references/key-links.md` — curated repos/docs (Pipecat, LiveKit Agents, anarlog, Meetily, Qdrant/LlamaIndex) with one-line annotations.
