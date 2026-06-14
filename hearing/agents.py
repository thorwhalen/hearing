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
from typing import Optional, Sequence

from hearing.types import Transcript, TranscriptSegment

#: A sensible, current default Claude model for meeting analysis. Override via
#: ``model=`` (e.g. "claude-opus-4-8" for max capability). See claude-api skill.
DEFAULT_CLAUDE_MODEL: str = "claude-sonnet-4-6"

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

    def _client(self):
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

    def _analyze_sync(self, transcript_text: str) -> str:
        """Blocking Claude call; ``on_window`` runs this off the event loop."""
        user_parts = []
        if self.context:
            user_parts.append(f"Relevant context:\n{self.context}\n")
        user_parts.append(f"Transcript:\n{transcript_text}")
        message = self._client().messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": "\n".join(user_parts)}],
        )
        return "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        ).strip()

    async def on_window(self, window: Sequence[TranscriptSegment]) -> Optional[str]:
        """Analyze a whole transcript (batch) and return structured notes."""
        text = _transcript_text(window)
        if not text:
            return None
        # The SDK call is blocking; keep the event loop free (batch & live).
        return await asyncio.to_thread(self._analyze_sync, text)

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
        """Live per-segment hook: surface action-item cues immediately."""
        low = segment.text.lower()
        if any(cue in low for cue in self.action_cues):
            who = segment.speaker or segment.channel.value
            return f"[action?] {who}: {segment.text.strip()}"
        return None


def build_default_agent(
    *, context: Optional[str] = None, model: Optional[str] = None, prefer: str = "auto"
):
    """Pick the best available agent.

    ``prefer="claude"`` forces Claude; ``"extractive"`` forces the offline
    fallback; ``"auto"`` (default) uses Claude when the anthropic SDK and an API
    key are available, otherwise the dependency-free :class:`ExtractiveAgent`.
    """
    if prefer == "extractive":
        return ExtractiveAgent()
    has_claude = _anthropic_available() and bool(os.getenv("ANTHROPIC_API_KEY"))
    if prefer == "claude" or (prefer == "auto" and has_claude):
        return ClaudeAgent(model=model or DEFAULT_CLAUDE_MODEL, context=context)
    return ExtractiveAgent()


def summarize_transcript(
    transcript: Transcript | Sequence[TranscriptSegment],
    *,
    agent=None,
    context: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[str]:
    """Synchronous facade: run a (batch) agent over a transcript, return notes.

    Builds the default agent when none is injected. Usable on a transcript with
    no audio at all.
    """
    window = tuple(transcript)
    agent = agent or build_default_agent(context=context, model=model)
    return asyncio.run(agent.on_window(window))


def _anthropic_available() -> bool:
    """True if the anthropic SDK can be imported."""
    try:
        import anthropic  # noqa: F401

        return True
    except ImportError:
        return False
