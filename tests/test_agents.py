"""Tests for the agent layer (the deterministic offline fallback)."""

import asyncio

from hearing.agents import ExtractiveAgent, build_default_agent, summarize_transcript
from hearing.types import ME, THEM, Channel, TimeSpan, Transcript, TranscriptSegment


def _meeting() -> Transcript:
    return Transcript(
        [
            TranscriptSegment("Welcome everyone to the planning sync.", TimeSpan(0, 3000), Channel.MIC, ME),
            TranscriptSegment("I'll send the report by Friday.", TimeSpan(3000, 6000), Channel.MIC, ME),
            TranscriptSegment("What is the budget for this quarter?", TimeSpan(6000, 9000), Channel.SYSTEM, THEM),
        ]
    )


def test_extractive_agent_produces_sections_and_detects_cues():
    notes = asyncio.run(ExtractiveAgent().on_window(_meeting().segments))
    assert "## Summary" in notes
    assert "## Key points" in notes
    # "I'll ... by Friday" is an action cue
    assert "action items" in notes.lower()
    assert "Friday" in notes
    # the "?" sentence is an open question
    assert "Open questions" in notes
    assert "budget" in notes


def test_extractive_agent_on_segment_flags_actions():
    seg = TranscriptSegment("Let's follow up next week.", TimeSpan(0, 2000), speaker=ME)
    out = asyncio.run(ExtractiveAgent().on_segment(seg))
    assert out is not None and "action" in out.lower()


def test_extractive_agent_empty_window_is_none():
    assert asyncio.run(ExtractiveAgent().on_window(())) is None


def test_build_default_agent_extractive_is_forced():
    agent = build_default_agent(prefer="extractive")
    assert isinstance(agent, ExtractiveAgent)


def test_summarize_transcript_with_explicit_extractive_agent():
    notes = summarize_transcript(_meeting(), agent=ExtractiveAgent())
    assert notes and "Summary" in notes
