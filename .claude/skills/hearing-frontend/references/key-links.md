# Key links — hearing-frontend

The most useful external repos/docs for building the hearing TS/React frontend.
One line each.

## The user's own stack (read these FIRST)

- **zodal** (local) — `/Users/thorwhalen/Dropbox/py/proj/i/_zodals/zodal/README.md` — schema-driven UI/state/data from one Zod v4 schema; `defineCollection()`, content-metadata bifurcation.
- **zodal-ui-shadcn** (local) — `/Users/thorwhalen/Dropbox/py/proj/i/_zodals/zodal-ui-shadcn/README.md` — renderer registry mapping Zod types → shadcn React components.
- **acture** (local) — `/Users/thorwhalen/Dropbox/py/proj/i/acture/README.md` — command-dispatch: one command → palette + hotkeys + AI tool + MCP + tests + Python client.
- **zodal-ecosystem** (global skill) — where zodal code lives, the `DataProvider<T>` contract, adding store adapters / UI renderers.
- **Zod v4** — https://zod.dev — the schema library both zodal and acture build on.

## Live transcript streaming references (study the pattern, not necessarily adopt)

- **LiveKit Agents docs** — https://docs.livekit.io/agents/ — server-side agent participants; `lk.transcription` text-stream topic that client UIs subscribe to.
- **LiveKit multi-user transcriber example** — https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py — per-participant `AgentSession` + STT; the reference for per-speaker streaming.
- **Pipecat transcriptions** — https://docs.pipecat.ai/api-reference/server/utilities/turn-management/transcriptions — `on_user_turn_stopped` / `on_assistant_turn_stopped` turn events (finalized-turn payloads).
- **RAG in a real-time voice agent (LiveKit)** — https://medium.com/@jorge.jarne/lessons-from-implementing-rag-in-a-real-time-voice-agent-livekit-43f0689bf565 — offload vector search to a separate task; cache results; append chunks to the prompt.
- **MDN — Server-Sent Events / EventSource** — https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events — the simplest server→client push for transcript/feedback streams.

## Open-source overlay apps to study (the floating-copilot UX)

- **Hyprnote / anarlog** — https://github.com/fastrepl/anarlog — local-first notetaker, system-audio capture, MCP server. Closest to hearing's goal.
- **Meetily** — https://github.com/Zackriya-Solutions/meetily — Tauri, 100% local, mic+system audio, pluggable AI.
- **Pluely** — https://github.com/iamsrikanthnani/pluely — ~10 MB Tauri copilot overlay; separates system audio from mic.
- **Natively** — https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant — local RAG + dual audio + meeting history.
- **Glass / Cluely comparison** — https://hyperlush.com/cluely-vs-glass/ — context on the copilot-overlay product category.
