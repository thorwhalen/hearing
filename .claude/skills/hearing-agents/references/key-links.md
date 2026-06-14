# Key links — Agent layer

Curated external repos/docs most worth opening when building the hearing agent layer. Verify versions/APIs at use time (these were current as of June 2026).

## Live-wire frameworks (study the pattern, fork selectively)
- **Pipecat** — https://github.com/pipecat-ai/pipecat — frame-based Python pipeline; the `FrameProcessor` non-blocking transcript-intercept pattern is the canonical "don't stall capture" wiring. Docs: https://docs.pipecat.ai
- **Pipecat turn management / transcriptions** — https://docs.pipecat.ai/api-reference/server/utilities/turn-management/transcriptions — `on_user_turn_stopped` events for batched-segment dispatch.
- **LiveKit Agents** — https://github.com/livekit/agents — WebRTC room model, agents as server-side participants. Heavier than a local notetaker needs; reach for it only if you need multi-participant rooms / telephony.
- **LiveKit multi-user transcriber example** — https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py — per-participant `AgentSession` pattern.

## Apps closest to the goal (fork material)
- **anarlog** (formerly Hyprnote) — https://github.com/fastrepl/anarlog — MIT, local-first notetaker, speaker ID, system-audio capture, MCP server for Claude/ChatGPT to read/write notes. Closest reference.
- **Meetily** — https://github.com/Zackriya-Solutions/meetily — MIT, 100% local, mic+system capture, pluggable AI (local/BYOK/hosted). Study the provider abstraction.
- **Pluely** — https://github.com/iamsrikanthnani/pluely — live copilot overlay; system/mic separation → live STT → LLM.
- **Natively** — https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant — overlay + local RAG + meeting history.
- **ownscribe** — https://github.com/paberr/ownscribe — local-first transcription + summarization CLI; pluggable AI.

## RAG over project context
- **Qdrant** — https://qdrant.tech — vector DB used in the report's real-time RAG stack.
- **LlamaIndex** — https://docs.llamaindex.ai — data framework for indexing/retrieval over project context.
- **Real-time RAG lessons (LiveKit)** — https://medium.com/@jorge.jarne/lessons-from-implementing-rag-in-a-real-time-voice-agent-livekit-43f0689bf565 — the "offload retrieval to async task + cache" guidance.
  - NOTE: check **my-packages** / **python-storage** before adding Qdrant/LlamaIndex — the user may already have a local embedding/store wrapper, and a `dol`-style KV store covers simpler cases.

## LLM backend (defer to claude-api skill)
- The agent defaults to Claude but stays pluggable behind an `LLMClient` Protocol. Model ids, pricing, tool use, the server-side `web_search` tool, streaming, structured output, prompt caching — all live in the global **claude-api** skill. Do not hardcode model ids or tool schemas here.
- **deep-research** (global skill) — owns the batch follow-up-research mode (fan-out search, fetch, adversarial verify, cited synthesis). Delegate rather than hand-rolling a research loop.
