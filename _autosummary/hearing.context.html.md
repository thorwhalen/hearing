# hearing.context

Context stores and retrieval (RAG) for context-connected agents.

An agent with no context is just a chatbot — the point of `hearing` is agents
*bound to a meeting and a project*, drawing on accumulated knowledge (prior
takeaways, the codebase, research reports). This module provides the retrieval
side behind a tiny [`Retriever`](#hearing.context.Retriever) Protocol so the backend is swappable and
testable with a fake (per the `hearing-agents` skill).

The default [`KeywordRetriever`](#hearing.context.KeywordRetriever) is a dependency-free TF-IDF retriever —
good enough to wire context-connection end-to-end and fully deterministic for
tests. Swap in an embedding/vector backend (Qdrant + LlamaIndex, or the user’s
own local store — check `my-packages` / `python-storage`) behind the same
Protocol when you need semantic recall.

### Module Attributes

| [`EmbedFn`](#hearing.context.EmbedFn)   | maps texts to equal-length float vectors.   |
|------------------------------------------------------------|---------------------------------------------|

### Functions

| [`build_embedding_retriever`](#hearing.context.build_embedding_retriever)(source, \*[, embed])   | Build an [`EmbeddingRetriever`](#hearing.context.EmbeddingRetriever) (default embedder: OpenAI) from a dict, a list, or a folder of `.md`/`.txt` docs (same source forms as [`build_retriever()`](#hearing.context.build_retriever)).   |
|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`build_retriever`](#hearing.context.build_retriever)(source)                          | Build a [`KeywordRetriever`](#hearing.context.KeywordRetriever) from a dict, a list, or a folder/file.                                                                                                                                           |
| [`openai_embedder`](#hearing.context.openai_embedder)(\*[, model, api_key, client])    | Return an [`EmbedFn`](#hearing.context.EmbedFn) backed by the OpenAI embeddings API.                                                                                                                                                    |

### Classes

| [`CallableWebSearch`](#hearing.context.CallableWebSearch)(fn)                   | Adapt any callable into a [`WebSearch`](#hearing.context.WebSearch) (for custom backends/tests).    |
|------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| [`Chunk`](#hearing.context.Chunk)(text[, title, source, score])     | A retrieved piece of context: the text plus where it came from.                                                      |
| [`EmbeddingRetriever`](#hearing.context.EmbeddingRetriever)(docs, \*, embed)     | Semantic retriever: ranks chunks by cosine similarity of embeddings.                                                 |
| [`KeywordRetriever`](#hearing.context.KeywordRetriever)(docs)                  | Dependency-free TF-IDF retriever over a small in-memory corpus.                                                      |
| [`Retriever`](#hearing.context.Retriever)(\*args, \*\*kwargs)           | Retrieves project/meeting context relevant to a query (RAG).                                                         |
| [`WebSearch`](#hearing.context.WebSearch)(\*args, \*\*kwargs)           | Brings outside information in — one targeted query, `k` results.                                                     |
| [`WikipediaSearch`](#hearing.context.WikipediaSearch)([lang, timeout, fetch]) | Key-free, dependency-free [`WebSearch`](#hearing.context.WebSearch) over Wikipedia (stdlib urllib). |

### *class* hearing.context.CallableWebSearch(fn)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Adapt any callable into a [`WebSearch`](#hearing.context.WebSearch) (for custom backends/tests).

`fn(query, k)` may return Chunks, strings, or dicts (coerced), and may be
sync or async.

### *class* hearing.context.Chunk(text, title='', source='', score=0.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A retrieved piece of context: the text plus where it came from.

### hearing.context.EmbedFn

maps texts to equal-length float vectors.

* **Type:**
  A batch embedder

alias of `Callable`[[[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]], [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`float`](https://docs.python.org/3/builtins/functions.html#float)]]]

### *class* hearing.context.EmbeddingRetriever(docs, , embed)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Semantic retriever: ranks chunks by cosine similarity of embeddings.

The corpus is embedded once at construction; `search` embeds the query and
returns the nearest chunks. The embedder is injected (`embed=`) so it is
backend-agnostic and testable with a deterministic fake — use
[`openai_embedder()`](#hearing.context.openai_embedder) for real semantic recall.

```pycon
>>> import asyncio
>>> fake = lambda texts: [[t.lower().count("db"), t.lower().count("ui")] for t in texts]
>>> r = EmbeddingRetriever({"a": "db db", "b": "ui ui"}, embed=fake)
>>> asyncio.run(r.search("db"))[0].title
'a'
```

#### *async* search(query, , k=4)

Return the top-`k` chunks by cosine similarity to `query`.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Chunk`](#hearing.context.Chunk)]

### *class* hearing.context.KeywordRetriever(docs)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Dependency-free TF-IDF retriever over a small in-memory corpus.

```pycon
>>> import asyncio
>>> r = KeywordRetriever({"db": "We will use PostgreSQL.", "ui": "React frontend."})
>>> hits = asyncio.run(r.search("postgresql migration"))
>>> hits[0].title
'db'
```

Matching is purely lexical, so a query sharing no token with the corpus
retrieves nothing — use [`EmbeddingRetriever`](#hearing.context.EmbeddingRetriever) for semantic recall.

```pycon
>>> asyncio.run(r.search("which database?"))
[]
```

#### *async* search(query, , k=4)

Return the top-`k` chunks by TF-IDF overlap with `query`.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Chunk`](#hearing.context.Chunk)]

### *class* hearing.context.Retriever(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Retrieves project/meeting context relevant to a query (RAG).

#### *async* search(query, , k=4)

Return up to `k` chunks most relevant to `query`.

* **Return type:**
  [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`Chunk`](#hearing.context.Chunk)]

### *class* hearing.context.WebSearch(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Brings outside information in — one targeted query, `k` results.

#### *async* search(query, , k=3)

Return up to `k` web results as chunks (title/body/url).

* **Return type:**
  [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`Chunk`](#hearing.context.Chunk)]

### *class* hearing.context.WikipediaSearch(lang='en', timeout=8.0, fetch=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Key-free, dependency-free [`WebSearch`](#hearing.context.WebSearch) over Wikipedia (stdlib urllib).

Ideal for the live fact-check / “who is X / what is Y” use: one targeted
query, a few result snippets with source URLs. The HTTP `fetch` is
injectable so tests need no network.

#### *async* search(query, , k=3)

Return up to `k` Wikipedia search hits as chunks (title/snippet/url).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Chunk`](#hearing.context.Chunk)]

### hearing.context.build_embedding_retriever(source, , embed=None)

Build an [`EmbeddingRetriever`](#hearing.context.EmbeddingRetriever) (default embedder: OpenAI) from a
dict, a list, or a folder of `.md`/`.txt` docs (same source forms as
[`build_retriever()`](#hearing.context.build_retriever)).

* **Return type:**
  [`EmbeddingRetriever`](#hearing.context.EmbeddingRetriever)

### hearing.context.build_retriever(source)

Build a [`KeywordRetriever`](#hearing.context.KeywordRetriever) from a dict, a list, or a folder/file.

A path to a directory indexes its `.txt`/`.md` files (keyed by stem); a
path to a single file indexes that file; a Mapping/Sequence is used directly.

* **Return type:**
  [`KeywordRetriever`](#hearing.context.KeywordRetriever)

### hearing.context.openai_embedder(, model='text-embedding-3-small', api_key=None, client=None)

Return an [`EmbedFn`](#hearing.context.EmbedFn) backed by the OpenAI embeddings API.

Needs `pip install 'hearing[openai]'` and `OPENAI_API_KEY` (or pass
`api_key=` / inject `client=` for tests).

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]], [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`float`](https://docs.python.org/3/builtins/functions.html#float)]]]
