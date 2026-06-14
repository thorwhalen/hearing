"""Context stores and retrieval (RAG) for context-connected agents.

An agent with no context is just a chatbot — the point of ``hearing`` is agents
*bound to a meeting and a project*, drawing on accumulated knowledge (prior
takeaways, the codebase, research reports). This module provides the retrieval
side behind a tiny :class:`Retriever` Protocol so the backend is swappable and
testable with a fake (per the ``hearing-agents`` skill).

The default :class:`KeywordRetriever` is a dependency-free TF-IDF retriever —
good enough to wire context-connection end-to-end and fully deterministic for
tests. Swap in an embedding/vector backend (Qdrant + LlamaIndex, or the user's
own local store — check ``my-packages`` / ``python-storage``) behind the same
Protocol when you need semantic recall.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Protocol, Sequence, Union, runtime_checkable

import numpy as np

#: A batch embedder: maps texts to equal-length float vectors.
EmbedFn = Callable[[Sequence[str]], Sequence[Sequence[float]]]

_DOC_EXTENSIONS = (".txt", ".md", ".markdown")


@dataclass(frozen=True)
class Chunk:
    """A retrieved piece of context: the text plus where it came from."""

    text: str
    title: str = ""
    source: str = ""
    score: float = 0.0


@runtime_checkable
class Retriever(Protocol):
    """Retrieves project/meeting context relevant to a query (RAG)."""

    async def search(self, query: str, *, k: int = 4) -> Sequence[Chunk]:
        """Return up to ``k`` chunks most relevant to ``query``."""
        ...


@runtime_checkable
class WebSearch(Protocol):
    """Brings outside information in — one targeted query, ``k`` results."""

    async def search(self, query: str, *, k: int = 3) -> Sequence[Chunk]:
        """Return up to ``k`` web results as chunks (title/body/url)."""
        ...


_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _coerce_chunks(docs) -> list[Chunk]:
    """Normalize a dict / list of strings|Chunks|dicts into a list of Chunks."""
    if isinstance(docs, Mapping):
        return [Chunk(text=str(v), title=str(name)) for name, v in docs.items()]
    out: list[Chunk] = []
    for d in docs:
        if isinstance(d, Chunk):
            out.append(d)
        elif isinstance(d, str):
            out.append(Chunk(text=d))
        elif isinstance(d, Mapping):
            out.append(Chunk(text=str(d.get("text", "")), title=str(d.get("title", "")), source=str(d.get("source", ""))))
    return out


class KeywordRetriever:
    """Dependency-free TF-IDF retriever over a small in-memory corpus.

    >>> import asyncio
    >>> r = KeywordRetriever({"db": "We will use PostgreSQL.", "ui": "React frontend."})
    >>> hits = asyncio.run(r.search("which database?"))
    >>> hits[0].title
    'db'
    """

    def __init__(self, docs: Union[Mapping[str, str], Sequence]):
        self._chunks = _coerce_chunks(docs)
        self._doc_tokens = [_tokens(f"{c.title} {c.text}") for c in self._chunks]
        n = len(self._chunks) or 1
        df: Counter = Counter()
        for toks in self._doc_tokens:
            df.update(set(toks))
        # smoothed idf so common words don't dominate
        self._idf = {w: math.log((n + 1) / (c + 1)) + 1.0 for w, c in df.items()}

    async def search(self, query: str, *, k: int = 4) -> list[Chunk]:
        """Return the top-``k`` chunks by TF-IDF overlap with ``query``."""
        q_terms = set(_tokens(query))
        if not q_terms or not self._chunks:
            return []
        scored: list[tuple[float, Chunk]] = []
        for chunk, toks in zip(self._chunks, self._doc_tokens):
            if not toks:
                continue
            tf = Counter(toks)
            score = sum(tf[w] * self._idf.get(w, 0.0) for w in q_terms)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            Chunk(text=c.text, title=c.title, source=c.source, score=round(s, 4))
            for s, c in scored[:k]
        ]


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """L2-normalize each row so a dot product equals cosine similarity."""
    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class EmbeddingRetriever:
    """Semantic retriever: ranks chunks by cosine similarity of embeddings.

    The corpus is embedded once at construction; ``search`` embeds the query and
    returns the nearest chunks. The embedder is injected (``embed=``) so it is
    backend-agnostic and testable with a deterministic fake — use
    :func:`openai_embedder` for real semantic recall.

    >>> import asyncio
    >>> fake = lambda texts: [[t.lower().count("db"), t.lower().count("ui")] for t in texts]
    >>> r = EmbeddingRetriever({"a": "db db", "b": "ui ui"}, embed=fake)
    >>> asyncio.run(r.search("db"))[0].title
    'a'
    """

    def __init__(self, docs: Union[Mapping[str, str], Sequence], *, embed: EmbedFn):
        self._chunks = _coerce_chunks(docs)
        self._embed = embed
        texts = [f"{c.title}\n{c.text}" for c in self._chunks]
        self._matrix = (
            _normalize_rows(np.asarray(embed(texts), dtype="float64"))
            if texts
            else np.zeros((0, 0))
        )

    async def search(self, query: str, *, k: int = 4) -> list[Chunk]:
        """Return the top-``k`` chunks by cosine similarity to ``query``."""
        if not self._chunks:
            return []
        # embedding may hit the network — keep the event loop free
        q = await asyncio.to_thread(self._embed, [query])
        qv = _normalize_rows(np.asarray(q, dtype="float64"))[0]
        sims = self._matrix @ qv
        order = np.argsort(-sims)[:k]
        return [
            Chunk(
                text=self._chunks[i].text,
                title=self._chunks[i].title,
                source=self._chunks[i].source,
                score=round(float(sims[i]), 4),
            )
            for i in order
            if sims[i] > 0
        ]


def openai_embedder(
    *, model: str = "text-embedding-3-small", api_key: Optional[str] = None, client=None
) -> EmbedFn:
    """Return an :data:`EmbedFn` backed by the OpenAI embeddings API.

    Needs ``pip install 'hearing[openai]'`` and ``OPENAI_API_KEY`` (or pass
    ``api_key=`` / inject ``client=`` for tests).
    """

    def embed(texts: Sequence[str]) -> list[list[float]]:
        c = client
        if c is None:
            import openai

            c = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        resp = c.embeddings.create(model=model, input=list(texts))
        return [d.embedding for d in resp.data]

    return embed


def build_embedding_retriever(
    source: Union[str, Path, Mapping, Sequence], *, embed: Optional[EmbedFn] = None
) -> EmbeddingRetriever:
    """Build an :class:`EmbeddingRetriever` (default embedder: OpenAI) from a
    dict, a list, or a folder of ``.md``/``.txt`` docs (same source forms as
    :func:`build_retriever`)."""
    kw = build_retriever(source)  # reuse the source -> chunks logic
    return EmbeddingRetriever(kw._chunks, embed=embed or openai_embedder())


def build_retriever(source: Union[str, Path, Mapping, Sequence]) -> KeywordRetriever:
    """Build a :class:`KeywordRetriever` from a dict, a list, or a folder/file.

    A path to a directory indexes its ``.txt``/``.md`` files (keyed by stem); a
    path to a single file indexes that file; a Mapping/Sequence is used directly.
    """
    if isinstance(source, (str, Path)):
        root = Path(source)
        docs: dict[str, str] = {}
        if root.is_dir():
            for p in sorted(root.rglob("*")):
                if p.is_file() and p.suffix.lower() in _DOC_EXTENSIONS:
                    docs[p.stem] = p.read_text(encoding="utf-8", errors="ignore")
        elif root.is_file():
            docs[root.stem] = root.read_text(encoding="utf-8", errors="ignore")
        return KeywordRetriever(docs)
    return KeywordRetriever(source)
