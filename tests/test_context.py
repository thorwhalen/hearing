"""Tests for context retrieval (RAG) and context-connected agent assembly."""

import asyncio

from hearing.agents import ClaudeAgent
from hearing.context import Chunk, KeywordRetriever, build_retriever


def test_keyword_retriever_ranks_relevant_doc_first():
    r = KeywordRetriever(
        {
            "db": "We decided to use PostgreSQL as the project database.",
            "ui": "The frontend is built with React and zod.",
            "ops": "Deployment runs on a Hetzner server with Caddy.",
        }
    )
    hits = asyncio.run(r.search("which database did we choose?", k=2))
    assert hits and hits[0].title == "db"
    assert hits[0].score > 0


def test_keyword_retriever_empty_on_no_overlap():
    r = KeywordRetriever({"a": "apples and oranges"})
    assert asyncio.run(r.search("quantum chromodynamics")) == []


def test_build_retriever_from_directory(tmp_path):
    (tmp_path / "notes.md").write_text("The launch deadline is end of month.")
    (tmp_path / "team.txt").write_text("Alice owns the API; Bob owns the UI.")
    (tmp_path / "ignore.bin").write_bytes(b"\x00\x01")  # non-text: skipped
    r = build_retriever(str(tmp_path))
    hits = asyncio.run(r.search("who owns the API?", k=1))
    assert hits and hits[0].title == "team"


def test_claude_agent_assembles_context_from_retriever_and_web():
    class FakeRetriever:
        async def search(self, query, *, k=4):
            return [Chunk(text="Postgres was chosen.", title="db")]

    class FakeWeb:
        async def search(self, query, *, k=3):
            return [Chunk(text="Postgres 17 released.", title="news", source="https://ex.com")]

    agent = ClaudeAgent(context="Project Apollo.", retriever=FakeRetriever(), web_search=FakeWeb())
    ctx = asyncio.run(agent._assemble_context("postgres database decision"))
    assert "Project Apollo." in ctx
    assert "[db] Postgres was chosen." in ctx
    assert "web: news" in ctx and "https://ex.com" in ctx
