"""ClaudeAgent's tool-use loop over injected retrieval / web search, with a scripted client (#5). Offline."""

import asyncio
from types import SimpleNamespace as NS

from hearing.agents import ClaudeAgent
from hearing.context import Chunk
from hearing.types import Channel, TimeSpan, TranscriptSegment


def _seg(text, speaker="them"):
    return TranscriptSegment(text=text, span=TimeSpan(0, 1000), channel=Channel.SYSTEM, speaker=speaker)


def _text(t):
    return NS(type="text", text=t)


def _call(id_, name, query):
    return NS(type="tool_use", id=id_, name=name, input={"query": query})


class ScriptedClient:
    """Plays back messages and records every request (a fake anthropic client)."""

    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.replies.pop(0)


class Lookup:
    def __init__(self, chunks, fail=False):
        self.chunks, self.fail, self.queries = chunks, fail, []

    async def search(self, query, *, k=3):
        self.queries.append((query, k))
        if self.fail:
            raise TimeoutError("slow")
        return self.chunks


def test_claude_searches_context_and_web_then_answers():
    client = ScriptedClient(
        NS(stop_reason="tool_use", content=[
            _text("Checking."),
            _call("t1", "search_context", "database decision"),
            _call("t2", "web_search", "Postgres 17 release"),
        ]),
        NS(stop_reason="end_turn", content=[_text("## Summary\nThey kept Postgres.")]),
    )
    retriever = Lookup([Chunk(text="Postgres was chosen in May.", title="takeaways-0512")])
    web = Lookup([Chunk(text="Postgres 17 shipped.", title="news", source="https://example.org/pg")])
    agent = ClaudeAgent(client=client, retriever=retriever, web_search=web)
    out = asyncio.run(agent.on_window([_seg("are we still on Postgres?")]))
    assert out == "## Summary\nThey kept Postgres."
    first, second = client.requests
    assert {t["name"] for t in first["tools"]} == {"search_context", "web_search"}
    assert "tool_choice" not in first
    assert web.queries == [("Postgres 17 release", 3)]  # the web only on request
    results = second["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["t1", "t2"]  # all results in one user turn
    assert "Postgres was chosen in May." in results[0]["content"]
    assert "https://example.org/pg" in results[1]["content"]
    assert second["messages"][-2]["role"] == "assistant"


def test_rounds_are_bounded_and_repeats_are_cached_and_failures_reported():
    looping = NS(stop_reason="tool_use", content=[_call("t", "web_search", "same thing")])
    client = ScriptedClient(looping, looping, NS(stop_reason="end_turn", content=[_text("done")]))
    web = Lookup([], fail=True)
    agent = ClaudeAgent(client=client, web_search=web, max_tool_rounds=2)
    assert asyncio.run(agent.on_window([_seg("hello")])) == "done"
    assert client.requests[-1]["tool_choice"] == {"type": "none"}
    assert client.requests[1]["messages"][-1]["content"][0]["is_error"] is True
    ok = Lookup([Chunk(text="x", title="t")])
    cached = ClaudeAgent(client=ScriptedClient(looping, looping, NS(stop_reason="end_turn", content=[_text("ok")])), web_search=ok)
    asyncio.run(cached.on_window([_seg("hello")]))
    assert len(ok.queries) == 1  # the same query twice hits the cache


def test_without_backends_or_with_tool_use_off_it_is_one_plain_call():
    client = ScriptedClient(NS(stop_reason="end_turn", content=[_text("plain")]))
    assert asyncio.run(ClaudeAgent(client=client).on_window([_seg("hi")])) == "plain"
    assert "tools" not in client.requests[0]
    web = Lookup([Chunk(text="ctx", title="w")])
    client = ScriptedClient(NS(stop_reason="end_turn", content=[_text("prefetched")]))
    asyncio.run(ClaudeAgent(client=client, web_search=web, tool_use=False).on_window([_seg("hi")]))
    assert "tools" not in client.requests[0] and "[web: w]" in client.requests[0]["messages"][0]["content"]
