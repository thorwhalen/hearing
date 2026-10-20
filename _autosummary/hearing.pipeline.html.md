# hearing.pipeline

Pipeline assembly — compose the four concerns by dependency injection.

This is where progressive disclosure lives: `transcribe("meeting.wav")` is a
one-liner with smart defaults, while the engine, diarizer, agent, channel
routing, and persistence are all optional keyword-only arguments. The same
shape powers the live path (`live_transcribe`); only the *source* and the
*trigger cadence* differ (milestone 2).

See the `hearing-architecture` skill — this module is the thin orchestrator it
describes; swapping any one component touches only the assembly call.

### Functions

| [`live_transcribe`](#hearing.pipeline.live_transcribe)(\*, source[, engine, ...])      | Stream FINALIZED segments as a meeting unfolds (the live path).                                                       |
|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| [`summarize`](#hearing.pipeline.summarize)(source, \*[, agent, context, model])  | Transcribe (if needed) then run an agent to produce meeting notes.                                                    |
| [`transcribe`](#hearing.pipeline.transcribe)(source, \*[, engine, diarizer, ...]) | Transcribe an audio source to a [`Transcript`](hearing.types.html.md#hearing.types.Transcript). |

### *async* hearing.pipeline.live_transcribe(, source, engine=None, diarizer=None, agent=None, audio_queue_max=50, segment_queue_max=100)

Stream FINALIZED segments as a meeting unfolds (the live path).

Same components as [`transcribe()`](#hearing.pipeline.transcribe) — only the *source* (a streaming
[`CaptureSource`](hearing.interfaces.html.md#hearing.interfaces.CaptureSource) instead of a file) and the trigger
cadence (VAD utterance turn-ends instead of run-once) change. The
`STTEngine` and `AgentConsumer` interfaces are unchanged.

Each channel is demuxed onto its own bounded queue and driven through
`engine.stream_transcribe` as an independent async task, so a slow agent
never stalls capture (backpressure) and the channel “me vs them” label rides
every segment. Diarization defaults to the free channel trick; the agent’s
`on_segment` is fired fire-and-forget. Yields segments as utterances finalize.

See the `hearing-live-pipeline` skill.

### hearing.pipeline.summarize(source, , agent=None, context=None, model=None, \*\*transcribe_kwargs)

Transcribe (if needed) then run an agent to produce meeting notes.

Accepts an audio source or an already-built `Transcript`. Builds the
default agent (Claude if available, else the offline extractive fallback)
when none is injected.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### hearing.pipeline.transcribe(source, , engine=None, diarizer=None, agent=None, language=None, split=True, mic_channels=(0,), system_channels=(1,), record=None)

Transcribe an audio source to a [`Transcript`](hearing.types.html.md#hearing.types.Transcript).

The one-liner `transcribe("meeting.wav")` works with all defaults: the
default local engine (faster-whisper), automatic channel splitting when the
file is multi-channel, and the free “me vs them” channel-trick diarizer.

* **Parameters:**
  * **source** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`CaptureSource`](hearing.interfaces.html.md#hearing.interfaces.CaptureSource)) – a file path or any [`CaptureSource`](hearing.interfaces.html.md#hearing.interfaces.CaptureSource).
  * **engine** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`STTEngine`](hearing.interfaces.html.md#hearing.interfaces.STTEngine)]) – STT engine (default: faster-whisper). Inject any `STTEngine`.
  * **diarizer** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Diarizer`](hearing.interfaces.html.md#hearing.interfaces.Diarizer)]) – speaker labeller. `None` -> the channel trick is applied
    automatically when channel info is present (mic=”me”, system=”them”).
    Inject a `PyannoteDiarizer` to separate individual remote speakers.
  * **agent** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`AgentConsumer`](hearing.interfaces.html.md#hearing.interfaces.AgentConsumer)]) – optional `AgentConsumer` run over the finished transcript
    (batch). Its output is stored under `transcript.meta['insight']`.
  * **language** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – force a language code (e.g. “en”); `None` = auto-detect.
  * **split** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – split mic/system channels when the source is multi-channel.
  * **system_channels** ([`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`int`](https://docs.python.org/3/builtins/functions.html#int)]) – column indices for the channel split.
  * **record** – optional `MutableMapping` store (e.g. a dol store) or
    [`MeetingStore`](hearing.storage.html.md#hearing.storage.MeetingStore) to persist the transcript JSON
    (with the agent’s insight) under key `"<source>.transcript.json"`,
    i.e. meeting id `<source file name>`; `hearing.context.meeting_retriever`
    reads those back as the next meeting’s context.
* **Return type:**
  [`Transcript`](hearing.types.html.md#hearing.types.Transcript)
* **Returns:**
  A `Transcript` (iterable/len-able, so it stands in for a sequence
  of segments). Segments carry text, span, channel, and speaker.
