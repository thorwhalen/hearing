---
name: hearing
description: The project-manager / orchestrator ENTRY POINT for the "hearing" project (thorwhalen/hearing — the pluggable macOS meeting-transcription + context-connected AI-agent library). Owns the vision, the milestone roadmap (batch first, live additive), the GitHub-as-memory workflow, and project status, and it ROUTES every task to the right hearing-* sub-skill or global skill. Triggers on PM / orchestration / routing questions: "which skill owns this", "which part do I work on", "route this task", "how does the hearing project fit together", "what should I build next / where do I start", the roadmap / milestones / batch-vs-live ordering, "project status / where things stand", scaffold the package / project structure, set up the repo's issues / discussions / ROADMAP, and any top-level "work on the hearing project" framing. For DEEP design contracts — the four swappable layers wiring, the shared segment data model, Protocol seams, batch/live unification — route to [[hearing-architecture]] instead. Routes to the hearing-* sub-skills (hearing-architecture, hearing-audio-capture, hearing-stt, hearing-diarization, hearing-agents, hearing-live-pipeline, hearing-frontend) and to the relevant global skills rather than duplicating them.
---

# hearing — project orchestrator

`hearing` is a **pluggable, dependency-injection-wired pipeline** that turns a meeting into a diarized, speaker-attributed transcript and runs **context-connected AI agents** over it — in **batch** (post-meeting) first, then **live** (in-meeting) as a purely additive second milestone. macOS-first. Python backend (CLI via `argh`, optional HTTP), TS/React frontend.

This is the **routing / project-management** skill. It tells you the vision, the build order, and **which sibling skill owns the task in front of you**. Read the owning skill before writing code; do not re-derive its contracts here.

## The vision in one breath

> `transcribe("meeting.wav")` is a one-liner. Everything else — system-audio capture, diarization, me/them labels, keeping the recording, live streaming, the agent copilot — is **optional, swappable, and injected**. Simple things stay one-liner-simple; complex things stay possible behind keyword-only kwargs.

## Architecture: four swappable layers, one data spine

The pipeline decomposes into **four separable concerns, each behind a Protocol, wired by composition + DI** (not baked together) [DIY]:

```
audio capture ──frames──▶ STT facade ──segments──▶ diarization ──labeled segments──▶ agents
(mic + system,            (local OR cloud,         (who-spoke-when;                   (consume the
 SEPARATE channels)        batch OR streaming)      "me vs them" falls out             transcript →
                                                    of the channel split)              feedback)
```

**The one non-negotiable principle:** the *only* difference between **batch** and **live** is (a) the **source** (a file vs a streaming sink) and (b) the **trigger cadence** (run-once vs VAD/timer loop). The segment shape, the diarization interface, and the agent contract are **identical**. Build one pipeline parameterized by source + trigger — never two. ([[hearing-architecture]] is the SSOT for how the four layers compose.)

**The channel trick (the project's cheapest win):** keep mic and system audio on *separate channels* (mic ch 1-2, system ch 3-4). That split gives you "me vs them" speaker attribution **for free** — no voice model — and lets you diarize only the system channel for the remote participants [DIY]. ([[hearing-audio-capture]], [[hearing-diarization]].)

## Milestone roadmap (the PM heart — build in THIS order)

### MILESTONE 1 — the BATCH path (build this first; highest value/effort ratio)

Reliably **record a meeting → transcribe to a file with diarization + me/them labels → optionally keep the recording → run context-connected agents over the result post-meeting.** This exercises the *whole stack except live streaming* and is achievable end-to-end without any real-time machinery [DIY: "Stage 1 — Batch DIY (highest value/effort ratio)"].

Order of work inside Milestone 1:
1. **Capture** mic+system on separate channels (BlackHole + Aggregate Device, or AudioTee) → [[hearing-audio-capture]].
2. **STT facade** `transcribe(audio) -> Iterable[Segment]`, swappable engine → [[hearing-stt]].
3. **Diarization** on the system channel; tag the mic channel as "me" → [[hearing-diarization]].
4. **Agents** over the finished transcript: summary, action items, decisions, follow-up research → [[hearing-agents]].
5. **Storage**: transcript + (optional) recording behind `dol` stores → global **python-storage**.
6. **CLI**: `argh`-dispatched `transcribe`, `record`, `agents` commands → global **python-dispatching**.

### MILESTONE 2 — the LIVE path (additive — do NOT start until Milestone 1 works)

Streaming STT + VAD-based utterance finalization + low-latency in-meeting agent feedback. **The whole architectural payoff: live is purely additive.** You **swap the batch capture source and segment sink for streaming ones, and attach the same agents to the live queue. The STT Protocol and the agent Protocol do not change.** If going live forces an edit to the STT or agent interface, the seam is in the wrong place — stop and fix the seam, don't fork the pipeline. → [[hearing-live-pipeline]].

> **Why batch first?** It de-risks every layer (capture, engine choice, diarization, agent prompts, storage) against a *stationary* target before adding the hard real-time constraints (latency budget, partial-vs-final segments, backpressure). Each batch layer is then reused verbatim under streaming.

### Frontend — spans both milestones

The TS/React UI (transcript viewer, agent-feedback panel, live copilot overlay) is for a **frontend novice** — explain JS/TS choices, prefer declarative/schema-driven UI. → [[hearing-frontend]].

## ROUTING TABLE — which skill owns the task in front of you

### Route to a sibling hearing-* skill

| The task is about… | Read & follow |
|---|---|
| **How the four layers wire together** by composition + DI; the shared `Segment`/data model; pipeline assembly; "what's the contract"; batch-vs-live unification | **[[hearing-architecture]]** (SSOT — read before any pipeline code) |
| **Getting audio in** on macOS: system-audio capture, BlackHole / Aggregate Device / AudioTee / Core Audio taps / ScreenCaptureKit, the mic-vs-system channel split, sample-rate/clock drift, iOS limits | **[[hearing-audio-capture]]** (the hardest layer) |
| **Turning audio into text**: the pluggable STT engine facade `transcribe(audio)->segments`, local vs cloud, Whisper/faster-whisper/WhisperX/Parakeet/MLX, Deepgram/AssemblyAI/OpenAI pricing, WER/concurrency/self-host break-even, model-name versioning | **[[hearing-stt]]** (streaming variant lives in [[hearing-live-pipeline]]) |
| **Who spoke when** (anonymous Speaker 1/2 = diarization) vs **which real person** (identification); the channel trick for "me"; pyannote/NeMo/WhisperX; feeding speaker labels into the prompt | **[[hearing-diarization]]** |
| **The agent / copilot layer** — the project's actual point: summaries, action items, decisions, follow-up research (batch); running notes, suggested questions, surfaced docs, fact-checks (live); the agent Protocol; pluggable LLM backend | **[[hearing-agents]]** |
| **Going live / real-time** (Milestone 2): streaming STT, VAD/utterance finalization, partial vs final, `asyncio.Queue` decoupling, latency budget, low-latency in-meeting feedback | **[[hearing-live-pipeline]]** |
| **The TS/React frontend**: transcript view, copilot overlay, agent panel, schema-driven UI (zodal/acture), how the Python backend feeds the UI — for a frontend novice | **[[hearing-frontend]]** |

### Route to a GLOBAL skill (don't duplicate these — they're the source of truth)

| The task is about… | Use the global skill |
|---|---|
| Modeling the transcript/diarization as **standoff interval annotation** (segments, speaker turns, rational/integer time — never bare floats) | **annotation-systems** |
| Exposing Python code as **CLI (`argh`) / HTTP / UI** | **python-dispatching** |
| **Storing** transcripts, recordings, audio behind dict-like stores | **python-storage** (`dol`) |
| **Streaming / async generators / queues / iterables** | **python-iterables** |
| **Claude model ids, pricing, tool use, caching** — the agent layer defaults to Claude but stays pluggable | **claude-api** (never answer LLM model/pricing questions from memory) |
| The agents' **follow-up / deep-research mode** | **deep-research** |
| The **schema-driven TS/React frontend** under the hood: zodal collections, `acture` commands, the transcript viewer & copilot UI patterns (the project-specific framing lives in [[hearing-frontend]]; cross-check the local zodal & acture READMEs) | **zodal-ecosystem** |
| Finding the user's **existing local packages** (e.g. `oa`, `dol`, `zodal`, `acture`) **BEFORE** adding a PyPI dep | **my-packages** + **local-package-ecosystem** |
| The **dev workflow** (issues as journal, alignment check before new work) | **github-memory** + **prework-alignment** |
| **Scaffolding** the package / project structure | **setup-py-project** + **python-project-structure** |

**Rule of thumb:** if a sibling skill names the concept in its description, it owns the contract — go there. If a *global* skill owns the technique (annotation modeling, dispatch, storage, LLM specifics), route there rather than re-deriving it in a hearing-* skill.

## GitHub-as-memory workflow (repo: thorwhalen/hearing, wads-managed CI)

Follow the global **github-memory** skill; for this repo specifically:

- **Issues = the running dev journal.** Open a **roadmap epic** issue (the two milestones + the per-layer breakdown above) and **one issue per layer** (capture, STT, diarization, agents, live, frontend). Journal decisions and progress in issue comments as you go.
- **Discussions = design rationale / decision records.** Capture "why this engine", "why batch first", "why the channel trick over voice-ID", etc., as durable Discussions.
- **`misc/docs/ROADMAP.md` = the committed plan** (mirror the Milestone 1/2 ordering above so it survives outside skills).
- **`misc/docs/` = research reports.** The two reports already there (DIY pipeline + GD agents) are the primary source for the whole project; cite them, don't re-research.
- Run **prework-alignment** before opening a new framed task (check open issues / PRs / branches first).
- **Privacy:** never write local absolute paths, the POC's private location, or secrets into issues/PRs/commits.

## Status — where things stand (this pass)

- **Repo:** `thorwhalen/hearing`, wads-managed CI.
- **Skills authored:** this orchestrator plus the seven hearing-* siblings.
- **Package skeleton scaffolded + a working BATCH path exists.** The `hearing` package has `interfaces.py`/`types.py` (the Protocol seams + segment data model), `capture.py`, `stt.py`, `diarize.py`, `agents.py`, `pipeline.py`, `cli.py`, plus a `tests/` suite. Milestone 1 batch is end-to-end runnable: `transcribe()` (default engine **faster-whisper**, with automatic channel-split "me vs them" and the `ChannelTrickDiarizer`), the agent layer (`ClaudeAgent` with an offline `ExtractiveAgent` fallback), and an **`argh` CLI** exposing `hearing transcribe / summarize / info`. The root `__init__` exposes the `transcribe(...)` one-liner.
- **Still TODO:** Milestone 2 (the live/streaming path → [[hearing-live-pipeline]]) and the TS/React frontend (→ [[hearing-frontend]]) are NOT yet started.
- **The POC is reference-only.** A prior mic-only proof-of-concept exists at a private path (not in this repo, do not depend on it). It has *good Protocol/dataclass bones* — `AudioRecorder` / `Transcriber` / `AIAgent` Protocols, `TranscriptSegment` dataclass, an `asyncio.Queue` agent loop — but it is **mic-only (1 channel), OpenAI/whisper-based via langchain, with NO system-audio capture, NO channel split, and NO diarization.** Borrow its *shape* (the Protocol seams are right); replace its *substance* (the engine lock-in and single-channel capture are exactly what this architecture removes). Prefer the user's local packages over its `langchain`/`pyaudio` deps — check **my-packages** first.

## Coding principles for this project (apply throughout)

Favor functional over OOP; when OOP, SOLID. **Facades** (the STT/agent layers), **SSOT** ([[hearing-architecture]] owns the contracts), **Dependency Injection** (inject backends, don't hardcode). Keyword-only args beyond the 3rd position; no magic numbers (config/kwargs). Progressive disclosure end to end. `collections.abc` interfaces + `dataclasses` for data; small focused helpers (inner if used once, `_prefix` if module-private, no prefix if cross-module reusable). Every module needs a docstring.

## References

`references/from-research-reports.md` — the vision, four-concern decomposition, and **staged roadmap** extracts from the two reports (with `[n]` citation markers + URLs). `references/key-links.md` — the reference projects (anarlog/Hyprnote, Meetily) and frameworks (Pipecat, LiveKit) to study before scaffolding. Deeper per-layer extracts live in each sibling skill's own `references/`.
