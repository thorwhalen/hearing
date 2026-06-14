"""Tests for context retrieval (RAG) and context-connected agent assembly."""

import asyncio
import os

import pytest

from hearing.agents import ClaudeAgent
from hearing.context import (
    Chunk,
    EmbeddingRetriever,
    KeywordRetriever,
    build_embedding_retriever,
    build_retriever,
    openai_embedder,
)

# A deterministic, network-free embedder: count occurrences of a fixed vocabulary.
_VOCAB = ["database", "postgres", "react", "frontend", "server", "deploy"]


def _fake_embed(texts):
    return [[float(t.lower().count(w)) for w in _VOCAB] for t in texts]


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


def test_embedding_retriever_ranks_by_cosine():
    r = EmbeddingRetriever(
        {
            "db": "We use the PostgreSQL database for storage.",
            "ui": "The React frontend lives here.",
            "ops": "Deploy on a server.",
        },
        embed=_fake_embed,
    )
    hits = asyncio.run(r.search("which database did we choose?", k=2))
    assert hits and hits[0].title == "db" and hits[0].score > 0


def test_embedding_retriever_empty_corpus():
    r = EmbeddingRetriever({}, embed=lambda t: [])
    assert asyncio.run(r.search("anything")) == []


def test_build_embedding_retriever_from_dir_with_injected_embed(tmp_path):
    (tmp_path / "db.md").write_text("PostgreSQL database notes.")
    (tmp_path / "ui.md").write_text("React frontend notes.")
    r = build_embedding_retriever(str(tmp_path), embed=_fake_embed)
    hits = asyncio.run(r.search("database", k=1))
    assert hits and hits[0].title == "db"


def test_openai_embedder_live():
    pytest.importorskip("openai")
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("no OPENAI_API_KEY")
    r = EmbeddingRetriever(
        {"db": "We chose PostgreSQL for storage.", "cal": "The picnic is on Saturday."},
        embed=openai_embedder(),
    )
    hits = asyncio.run(r.search("what database are we using?", k=1))
    assert hits and hits[0].title == "db"  # semantic match, no shared keywords


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
