"""ClaudeAgent's live on_segment behaviours: cadence, question trigger, skip-while-busy, NONE (#5, part 3). Offline."""

import asyncio
from types import SimpleNamespace as NS

import pytest

from hearing.agents import LIVE_NOTHING, ClaudeAgent
from hearing.context import Chunk
from hearing.types import Channel, TimeSpan, TranscriptSegment


def _seg(text, speaker="them", t=0):
    return TranscriptSegment(text=text, span=TimeSpan(t, t + 1000), channel=Channel.SYSTEM, speaker=speaker)


class Client:
    def __init__(self, *texts, stop="end_turn"):
        self.texts, self.requests, self.messages = list(texts), [], self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return NS(stop_reason="end_turn", content=[NS(type="text", text=self.texts.pop(0))])


def _feed(agent, texts):
    return [asyncio.run(agent.on_segment(_seg(t, t=i * 1000))) for i, t in enumerate(texts)]


def test_live_is_off_by_default_and_costs_nothing():
    client = Client()
    assert _feed(ClaudeAgent(client=client), ["a", "b", "c", "d", "e"]) == [None] * 5
    assert client.requests == []


def test_live_runs_every_n_segments_over_the_recent_window():
    client = Client("[note] They chose Postgres.", LIVE_NOTHING)
    agent = ClaudeAgent(client=client, live=("notes",), live_every=2, live_window=3)
    out = _feed(agent, ["we discussed options", "we chose postgres", "lunch", "ok then"])
    assert out == [None, "[note] They chose Postgres.", None, None]  # NONE comes back as None
    assert len(client.requests) == 2
    system, user = client.requests[0]["system"], client.requests[1]["messages"][0]["content"]
    assert "[note]" in system and "[question]" not in system
    assert "we discussed options" not in user and "lunch" in user  # window of 3


def test_a_question_triggers_at_once_when_questions_are_on():
    client = Client("[question] Ask which region they host in.")
    agent = ClaudeAgent(client=client, live=("questions", "factcheck"), live_every=10)
    assert _feed(agent, ["where do you host it?"]) == ["[question] Ask which region they host in."]
    assert "[fact-check]" in client.requests[0]["system"]


def test_factcheck_uses_the_tool_loop_when_web_search_is_attached():
    class Web:
        async def search(self, query, *, k=3):
            return [Chunk(text="Postgres 17 shipped in 2024.", title="news")]

    calls = [
        NS(stop_reason="tool_use", content=[NS(type="tool_use", id="t1", name="web_search", input={"query": "postgres 17 release"})]),
        NS(stop_reason="end_turn", content=[NS(type="text", text="[fact-check] Postgres 17 shipped in 2024, not 2026.")]),
    ]
    client = NS(requests=[])
    client.messages = NS(create=lambda **kw: (client.requests.append(kw), calls.pop(0))[1])
    agent = ClaudeAgent(client=client, web_search=Web(), live=("factcheck",), live_every=1)
    assert _feed(agent, ["postgres 17 came out in 2026"]) == ["[fact-check] Postgres 17 shipped in 2024, not 2026."]
    assert client.requests[0]["tools"][0]["name"] == "web_search"


def test_ticks_while_a_live_call_is_in_flight_are_skipped():
    agent = ClaudeAgent(client=Client("[note] x"), live=("notes",), live_every=1)

    async def run():
        gate = asyncio.Event()
        original = agent._analyze_sync

        def slow(*a, **kw):
            asyncio.run_coroutine_threadsafe(gate.wait(), loop).result()
            return original(*a, **kw)

        agent._analyze_sync = slow
        loop = asyncio.get_running_loop()
        first = asyncio.create_task(agent.on_segment(_seg("one")))
        await asyncio.sleep(0.05)
        second = await agent.on_segment(_seg("two"))
        gate.set()
        return await first, second

    assert asyncio.run(run()) == ("[note] x", None)


def test_unknown_live_behaviour_is_refused():
    with pytest.raises(ValueError, match="unknown live"):
        ClaudeAgent(live=("gossip",))
