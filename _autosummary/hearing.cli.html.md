# hearing.cli

Command-line interface for hearing, dispatched with `cw`.

Surfaces the Python facades (`transcribe`, `summarize`) as subcommands — it does
not reimplement them (the facades are the SSOT; see the `python-dispatching`
and `hearing-architecture` skills). Installed as the `hearing` console
script:

```default
hearing transcribe meeting.wav
hearing transcribe meeting.wav --model small --out notes.json
hearing transcribe meeting.wav --engine deepgram   # or openai / mlx / parakeet / whisperx
hearing summarize meeting.wav            # transcribe + AI meeting notes
hearing info                             # check what's installed/available
```

### Functions

| [`info`](#hearing.cli.info)()                                            | Report which optional components are installed and what's missing.         |
|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`live`](#hearing.cli.live)([path, engine, model, device, ...])          | Run the LIVE streaming pipeline, printing segments as utterances finalize. |
| [`main`](#hearing.cli.main)([argv])                                      | Entry point for the `hearing` console script.                              |
| [`meetings`](#hearing.cli.meetings)(store, \*[, show])                       | List transcripts saved in a store (or print one with --show ID).           |
| [`serve`](#hearing.cli.serve)(\*[, host, port, reload])                   | Serve the HTTP API (FastAPI) the frontend talks to.                        |
| [`summarize`](#hearing.cli.summarize)(path, \*[, agent, model, context, ...]) | Transcribe a meeting and produce AI notes (summary, actions, questions).   |
| [`transcribe`](#hearing.cli.transcribe)(path, \*[, engine, model, ...])        | Transcribe an audio file to text or JSON.                                  |

### hearing.cli.info()

Report which optional components are installed and what’s missing.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### hearing.cli.live(path=None, , engine='whisper', model=None, device=None, block_ms=200, realtime=False)

Run the LIVE streaming pipeline, printing segments as utterances finalize.

* **Parameters:**
  * **path** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – stream this audio FILE through the live loop (great for a demo /
    no hardware). Omit to capture from an audio DEVICE instead.
  * **engine** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – STT engine (same choices as `transcribe --engine`); engines
    without native streaming are fed VAD-segmented utterances.
  * **model** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – STT model override (omit for the engine’s default).
  * **device** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – audio device index/name for live capture (an Aggregate Device
    with mic + BlackHole; see the hearing-audio-capture skill).
  * **block_ms** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – streaming block size in milliseconds.
  * **realtime** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – when streaming a file, pace it in real time (else as-fast-as).
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### hearing.cli.main(argv=None)

Entry point for the `hearing` console script.

`cw.run` *returns* the exit code (argh’s `parser.dispatch` exited by
itself), so the `SystemExit` here is what makes `hearing no-such-command`
exit 2.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### hearing.cli.meetings(store, , show=None)

List transcripts saved in a store (or print one with –show ID).

* **Parameters:**
  * **store** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the store/folder a transcript was saved to (`transcribe --save`).
  * **show** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – a meeting id to print (formatted transcript) instead of listing.
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### hearing.cli.serve(, host='127.0.0.1', port=8000, reload=False)

Serve the HTTP API (FastAPI) the frontend talks to.

* **Parameters:**
  * **host** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – bind address.
  * **port** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – bind port.
  * **reload** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – auto-reload on code changes (dev).
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### hearing.cli.summarize(path, , agent='auto', model=None, context=None, context_dir=None, retriever='keyword', web_search=False, engine='whisper', transcribe_model=None, split=True)

Transcribe a meeting and produce AI notes (summary, actions, questions).

* **Parameters:**
  * **path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – audio file to transcribe and analyze.
  * **agent** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – “auto” (Claude if available, else offline extractive), “claude”,
    or “extractive” (deterministic, no API key needed).
  * **model** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Claude model id (only used by the claude/auto agent).
  * **context** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – optional literal context string to connect the agent.
  * **context_dir** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – a folder/file of .txt/.md context docs (prior takeaways,
    project notes); the agent does RAG over it (context-connected).
  * **retriever** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – “keyword” (TF-IDF, offline) or “embedding” (OpenAI semantic;
    needs hearing[openai] + OPENAI_API_KEY). Only used with context_dir.
  * **web_search** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – also bring in Wikipedia fact context (key-free) for the agent.
  * **engine** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – STT engine (same choices as `transcribe --engine`).
  * **transcribe_model** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – STT model override (omit for the engine’s default).
  * **split** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – split mic/system channels (me vs them).
* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### hearing.cli.transcribe(path, , engine='whisper', model=None, language=None, split=True, diarize=True, out=None, fmt='text', save=None)

Transcribe an audio file to text or JSON.

* **Parameters:**
  * **path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – audio file (wav/flac/aiff/…; convert mp3/m4a with ffmpeg first).
  * **engine** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – STT engine — “whisper” (local faster-whisper, default), “openai”
    (cloud), “deepgram” (cloud, Nova-3), “mlx” (Whisper on Apple Silicon),
    “parakeet” (Parakeet-TDT on Apple Silicon), or “whisperx” (aligned words).
  * **model** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – engine model override — a whisper size (tiny/base/small/large-v3/…)
    for whisper/mlx/whisperx, a model name for cloud engines (e.g.
    “nova-3”); omit for the engine’s default.
  * **language** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – force a language code (e.g. “en”); omit to auto-detect.
  * **split** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – split mic/system channels for multi-channel files (me vs them).
  * **diarize** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – apply the channel-trick “me vs them” labelling.
  * **out** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – write to this path (.json -> JSON, else formatted text); else stdout.
  * **fmt** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – stdout/text format — “text” or “json”.
  * **save** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – persist the transcript to this store/folder (keyed by the file stem),
    so post-meeting agents can load the full transcript later.
* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
