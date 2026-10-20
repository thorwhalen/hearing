"""The agent / "copilot" layer — the actual point of the hearing project.

An agent consumes a (speaker-labelled) transcript and produces feedback. The
*same* :class:`~hearing.interfaces.AgentConsumer` interface serves both modes;
only *when* and *what granularity* it consumes differs:

* **batch** — ``on_window(whole_transcript)`` -> summary, action items,
  decisions, open questions, follow-up research (post-meeting).
* **live** — ``on_segment(finalized_segment)`` -> running notes, suggested
  questions, surfaced docs, fact-checks (as the meeting unfolds).

Agents are meant to be *context-connected*: bound to a meeting/project and able
to draw on accumulated knowledge (prior takeaways, the codebase, research
reports) and live web search. The ``context`` field is that hook.

The default backend is Claude (latest/most capable) but stays pluggable — see
the ``claude-api`` skill for model ids, pricing, tool use, and structured
output, and the ``hearing-agents`` skill for the queue-consumer pattern, RAG,
and the batch≡live unification.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional, Sequence

from hearing.types import Transcript, TranscriptSegment

if TYPE_CHECKING:  # retrieval backends are injected; avoid importing at module load
    from hearing.context import Retriever, WebSearch

#: A sensible, current default Claude model for meeting analysis. Override via
#: ``model=`` (e.g. "claude-opus-4-8" for max capability). See claude-api skill.
DEFAULT_CLAUDE_MODEL: str = "claude-sonnet-4-6"

#: Tool-use rounds a batch analysis may spend before it must answer.
DEFAULT_MAX_TOOL_ROUNDS = 4
#: Tools the agent offers Claude, by which injected backend serves them.
_TOOL_SPECS = {
    "search_context": (
        "retriever",
        "Search the meeting's project context (prior meetings' takeaways, project "
        "notes, research reports) for passages relevant to a query. Use it to check "
        "what was decided or known before this meeting.",
    ),
    "web_search": (
        "web_search",
        "Search the web for a specific fact or entity mentioned in the meeting "
        "(follow-up research or a fact-check). One focused query per call.",
    ),
}

_DEFAULT_SYSTEM_PROMPT = """\
You are a meeting assistant. Given a (speaker-labelled) transcript, produce a \
concise, well-structured analysis with these sections, omitting any that don't \
apply:

## Summary
2-4 sentences capturing what the meeting was about and its outcome.

## Decisions
Bullet points of decisions that were made.

## Action items
Bullet points as "- [owner] action" when an owner is identifiable, else "- action".

## Open questions / follow-ups
Bullet points of unresolved questions or things worth researching afterwards.

Be faithful to the transcript; do not invent facts. Speakers labelled "me" are \
the local user; "them"/"spk_*" are remote participants.\
"""


def _transcript_text(window: Sequence[TranscriptSegment]) -> str:
    """Render a window of segments as ``speaker: text`` lines for a prompt."""
    lines = []
    for s in window:
        who = s.speaker or s.channel.value
        text = s.text.strip()
        if text:
            lines.append(f"{who}: {text}")
    return "\n".join(lines)


@dataclass
class ClaudeAgent:
    """Context-connected meeting agent backed by Claude (the default).

    Args:
        model: Claude model id (see the ``claude-api`` skill).
        context: optional context to connect the agent to a meeting/project —
            prior takeaways, project notes, etc. Prepended to the prompt.
        system_prompt: override the default meeting-assistant instructions.
        max_tokens: output cap.
    """

    model: str = DEFAULT_CLAUDE_MODEL
    context: Optional[str] = None
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT
    max_tokens: int = 1024
    api_key: Optional[str] = None
    retriever: Optional["Retriever"] = None  # RAG over project/meeting context
    web_search: Optional["WebSearch"] = None  # bring outside info in
    retrieve_k: int = 4
    web_k: int = 3
    client: Any = None  # an injected client (anything with .messages.create), e.g. a fake
    tool_use: bool = True  # let Claude query the retriever / web search itself
    max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS
    _tool_cache: dict = field(default_factory=dict, repr=False, compare=False)

    def _client(self):
        if self.client is not None:
            return self.client
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover - guidance path
            raise ImportError(
                "ClaudeAgent needs the anthropic SDK. Install with:\n"
                "    pip install 'hearing[agents]'\n"
                "or inject a different AgentConsumer (e.g. ExtractiveAgent, which "
                "needs no API key or deps)."
            ) from e
        key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Set it, pass api_key=, or use "
                "ExtractiveAgent for an offline, dependency-free fallback."
            )
        return anthropic.Anthropic(api_key=key)

    async def _assemble_context(self, query: str, *, include_web: bool = True) -> str:
        """Gather the agent's context: static context + RAG + web search.

        Retrieval is async and offloaded so it never blocks the stream; results
        for the meeting transcript become part of the prompt's context block.
        """
        parts: list[str] = []
        if self.context:
            parts.append(self.context.strip())
        if self.retriever is not None:
            chunks = await self.retriever.search(query, k=self.retrieve_k)
            for c in chunks:
                label = c.title or c.source or "context"
                parts.append(f"[{label}] {c.text.strip()}")
        if include_web and self.web_search is not None:
            results = await self.web_search.search(query, k=self.web_k)
            for c in results:
                src = f" ({c.source})" if c.source else ""
                parts.append(f"[web: {c.title or 'result'}{src}] {c.text.strip()}")
        return "\n\n".join(parts)

    def _analyze_sync(self, transcript_text: str, context_text: str = "") -> str:
        """Blocking Claude call; ``on_window`` runs this off the event loop."""
        message = self._client().messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[_user_turn(transcript_text, context_text)],
        )
        return _text_of(message)

    def _tools(self) -> list[dict]:
        """The tool definitions for the backends this agent was given."""
        return [
            {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            }
            for name, (backend, description) in _TOOL_SPECS.items()
            if getattr(self, backend) is not None
        ]

    async def _run_tool(self, name: str, tool_input: dict) -> tuple[str, bool]:
        """One tool call, answered from the cache when the same query recurs; ``(text, is_error)``."""
        query = str((tool_input or {}).get("query") or "").strip()
        if name not in _TOOL_SPECS or not query:
            return f"unknown tool or empty query: {name}", True
        key = (name, query.lower())
        if key not in self._tool_cache:
            backend = getattr(self, _TOOL_SPECS[name][0])
            k = self.retrieve_k if name == "search_context" else self.web_k
            try:
                chunks = await backend.search(query, k=k)
            except Exception as e:  # a failed lookup is the model's to handle, not a crash
                return f"{name} failed: {type(e).__name__}: {e}", True
            self._tool_cache[key] = "\n\n".join(
                f"[{c.title or c.source or 'result'}]"
                + (f" ({c.source})" if c.source and c.title else "")
                + f" {c.text.strip()}"
                for c in chunks
            ) or "no results"
        return self._tool_cache[key], False

    async def _analyze_with_tools(self, transcript_text: str, context_text: str) -> str:
        """The manual tool-use loop: Claude may search context / the web, then answers."""
        client, tools = self._client(), self._tools()
        messages: list[dict] = [_user_turn(transcript_text, context_text)]
        for round_ in range(self.max_tool_rounds + 1):
            last = round_ == self.max_tool_rounds
            kwargs = dict(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=messages,
                tools=tools,
            )
            if last:  # out of rounds: answer with what has been gathered
                kwargs["tool_choice"] = {"type": "none"}
            message = await asyncio.to_thread(client.messages.create, **kwargs)
            if getattr(message, "stop_reason", None) != "tool_use" or last:
                return _text_of(message)
            calls = [b for b in message.content if getattr(b, "type", "") == "tool_use"]
            results = await asyncio.gather(*(self._run_tool(b.name, b.input) for b in calls))
            messages.append({"role": "assistant", "content": message.content})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": b.id,
                            "content": text,
                            **({"is_error": True} if error else {}),
                        }
                        for b, (text, error) in zip(calls, results)
                    ],
                }
            )
        return ""  # pragma: no cover - the last round always returns

    async def on_window(self, window: Sequence[TranscriptSegment]) -> Optional[str]:
        """Analyze a whole transcript (batch) and return structured notes."""
        text = _transcript_text(window)
        if not text:
            return None
        if self.tool_use and self._tools():
            # Claude asks for what it needs; the static context and a first
            # retrieval still go in up front, the web only on request.
            context_text = await self._assemble_context(text, include_web=False)
            return await self._analyze_with_tools(text, context_text) or None
        context_text = await self._assemble_context(text)
        # The SDK call is blocking; keep the event loop free (batch & live).
        return await asyncio.to_thread(self._analyze_sync, text, context_text)

    async def on_segment(self, segment: TranscriptSegment) -> Optional[str]:
        """Live per-segment hook (milestone 2). No-op in the batch milestone."""
        return None


@dataclass
class ExtractiveAgent:
    """Deterministic, dependency-free fallback agent (no API, no network).

    Produces a usable summary by extraction/heuristics so the app always does
    *something* offline and tests stay deterministic. Detects naive action
    items (imperative / commitment cues) and open questions (``?``).
    """

    max_key_points: int = 5
    #: cues that hint a segment is an action item / commitment
    action_cues: tuple[str, ...] = (
        "let's",
        "we should",
        "i'll",
        "we'll",
        "need to",
        "action",
        "todo",
        "to do",
        "follow up",
        "next step",
        "assign",
        "by friday",
        "by monday",
        "deadline",
    )

    async def on_window(self, window: Sequence[TranscriptSegment]) -> Optional[str]:
        """Return a deterministic extractive summary of the window."""
        segs = [s for s in window if s.text.strip()]
        if not segs:
            return None
        speakers = sorted({s.speaker or s.channel.value for s in segs})
        total_ms = max((s.span.end_ms for s in segs), default=0)
        actions, questions = [], []
        for s in segs:
            low = s.text.lower()
            who = s.speaker or s.channel.value
            if any(cue in low for cue in self.action_cues):
                actions.append(f"- [{who}] {s.text.strip()}")
            for sentence in re.split(r"(?<=[.?!])\s+", s.text.strip()):
                if sentence.endswith("?"):
                    questions.append(f"- ({who}) {sentence.strip()}")
        key_points = sorted(segs, key=lambda s: len(s.text), reverse=True)
        key_points = key_points[: self.max_key_points]
        key_points.sort(key=lambda s: s.span.start_ms)

        out = ["## Summary (extractive — offline fallback)"]
        out.append(
            f"{len(segs)} segments, {len(speakers)} speaker(s) "
            f"({', '.join(speakers)}), ~{total_ms // 1000}s."
        )
        out.append("\n## Key points")
        out += [f"- {s.text.strip()}" for s in key_points]
        if actions:
            out.append("\n## Possible action items")
            out += actions[:10]
        if questions:
            out.append("\n## Open questions")
            out += questions[:10]
        return "\n".join(out)

    async def on_segment(self, segment: TranscriptSegment) -> Optional[str]:
        """Live per-segment hook: surface questions and action-item cues."""
        text = segment.text.strip()
        low = text.lower()
        who = segment.speaker or segment.channel.value
        if text.endswith("?"):
            return f"Suggested follow-up to {who}'s question: {text}"
        if any(cue in low for cue in self.action_cues):
            return f"Possible action item ({who}): {text}"
        return None


def _user_turn(transcript_text: str, context_text: str = "") -> dict:
    parts = []
    if context_text:
        parts.append(f"Relevant context:\n{context_text}\n")
    parts.append(f"Transcript:\n{transcript_text}")
    return {"role": "user", "content": "\n".join(parts)}


def _text_of(message) -> str:
    return "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ).strip()


def build_default_agent(
    *,
    context: Optional[str] = None,
    model: Optional[str] = None,
    prefer: str = "auto",
    retriever: Optional["Retriever"] = None,
    web_search: Optional["WebSearch"] = None,
    history=None,
):
    """Pick the best available agent.

    ``prefer="claude"`` forces Claude; ``"extractive"`` forces the offline
    fallback; ``"auto"`` (default) uses Claude when the anthropic SDK and an API
    key are available, otherwise the dependency-free :class:`ExtractiveAgent`.
    A ``retriever``/``web_search`` make the Claude agent context-connected;
    ``history`` (a :class:`~hearing.storage.MeetingStore` or the mapping
    ``transcribe(record=...)`` fills) adds prior meetings' takeaways to the retriever.
    """
    if history is not None:
        from hearing.context import CombinedRetriever, meeting_retriever

        retriever = CombinedRetriever(retriever, meeting_retriever(history))
    if prefer == "extractive":
        return ExtractiveAgent()
    has_claude = _anthropic_available() and bool(os.getenv("ANTHROPIC_API_KEY"))
    if prefer == "claude" or (prefer == "auto" and has_claude):
        return ClaudeAgent(
            model=model or DEFAULT_CLAUDE_MODEL,
            context=context,
            retriever=retriever,
            web_search=web_search,
        )
    return ExtractiveAgent()


def summarize_transcript(
    transcript: Transcript | Sequence[TranscriptSegment],
    *,
    agent=None,
    context: Optional[str] = None,
    model: Optional[str] = None,
    retriever: Optional["Retriever"] = None,
    web_search: Optional["WebSearch"] = None,
    history=None,
) -> Optional[str]:
    """Synchronous facade: run a (batch) agent over a transcript, return notes.

    Builds the default agent when none is injected (context-connected when a
    ``retriever``/``web_search`` is supplied). Usable on a transcript with no
    audio at all.
    """
    window = tuple(transcript)
    agent = agent or build_default_agent(
        context=context,
        model=model,
        retriever=retriever,
        web_search=web_search,
        history=history,
    )
    return asyncio.run(agent.on_window(window))


def _anthropic_available() -> bool:
    """True if the anthropic SDK can be imported."""
    try:
        import anthropic  # noqa: F401

        return True
    except ImportError:
        return False
