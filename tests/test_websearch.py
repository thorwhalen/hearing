"""Tests for the WebSearch backends (Wikipedia + Callable), no network."""

import asyncio
import json

from hearing.agents import ClaudeAgent
from hearing.context import CallableWebSearch, WikipediaSearch

# A canned Wikipedia API response (action=query&list=search).
_WIKI_JSON = json.dumps(
    {
        "query": {
            "search": [
                {"title": "PostgreSQL", "snippet": "<span class=\"searchmatch\">PostgreSQL</span> is a free database &amp; system."},
                {"title": "SQLite", "snippet": "SQLite is a C-language library."},
            ]
        }
    }
).encode("utf-8")


def test_wikipedia_search_parses_hits_with_injected_fetch():
    ws = WikipediaSearch(fetch=lambda url: _WIKI_JSON)
    hits = asyncio.run(ws.search("which database?", k=2))
    assert [h.title for h in hits] == ["PostgreSQL", "SQLite"]
    # HTML tags stripped, entities unescaped
    assert hits[0].text == "PostgreSQL is a free database & system."
    assert hits[0].source == "https://en.wikipedia.org/wiki/PostgreSQL"


def test_wikipedia_search_builds_query_url():
    ws = WikipediaSearch()
    url = ws._query_url("who is Ada Lovelace", 3)
    assert "en.wikipedia.org/w/api.php" in url
    assert "srsearch=who+is+Ada+Lovelace" in url and "srlimit=3" in url


def test_wikipedia_empty_query_returns_empty():
    ws = WikipediaSearch(fetch=lambda url: _WIKI_JSON)
    assert asyncio.run(ws.search("   ")) == []


def test_callable_web_search_coerces_results():
    ws = CallableWebSearch(fn=lambda q, k: [{"title": "T", "text": "body", "source": "u"}])
    hits = asyncio.run(ws.search("q"))
    assert hits[0].title == "T" and hits[0].text == "body"


def test_agent_assembles_web_context_from_wikipedia():
    agent = ClaudeAgent(web_search=WikipediaSearch(fetch=lambda url: _WIKI_JSON))
    ctx = asyncio.run(agent._assemble_context("database choice"))
    assert "web: PostgreSQL" in ctx and "https://en.wikipedia.org/wiki/PostgreSQL" in ctx
