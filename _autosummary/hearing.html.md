# hearing

hearing — pluggable meeting transcription & context-aware AI agents.

A small, composable toolkit for capturing, transcribing, and reasoning over
meeting audio. Four swappable concerns compose into one pipeline by dependency
injection: audio **capture** (mic + system audio on separate channels) ->
**STT** engine facade (local or cloud) -> optional **diarization** / speaker-id
(the mic-vs-system channel split gives “me vs them” for free) -> an **agent**
layer that consumes the transcript (batch or live).

Progressive disclosure — the one-liner just works:

```default
from hearing import transcribe
transcript = transcribe("meeting.wav")
print(transcript.formatted())
```

…while engine selection, diarization, agents, channel routing, and the live
loop are all optional keyword-only arguments.

The architecture and the per-concern guidance live in the project’s agent skills
(`.claude/skills/hearing*`); start with the `hearing` skill.

### Functions

| [`transcribe`](#hearing.transcribe)(source, \*[, engine, diarizer, ...])   | Transcribe an audio source to a [`Transcript`](hearing.types.html.md#hearing.types.Transcript).   |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [`live_transcribe`](#hearing.live_transcribe)(\*, source[, engine, ...])        | Stream FINALIZED segments as a meeting unfolds (the live path).                                                         |
| [`summarize`](#hearing.summarize)(source, \*[, agent, context, model])    | Transcribe (if needed) then run an agent to produce meeting notes.                                                      |

### Classes

| [`Transcript`](#hearing.Transcript)([segments, sample_rate, meta])     | A finished transcript: an ordered collection of segments plus metadata.   |
|------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`TranscriptSegment`](#hearing.TranscriptSegment)(text, span[, channel, ...]) | The data spine — a standoff interval annotation over the audio.           |
| [`TimeSpan`](#hearing.TimeSpan)(start_ms, end_ms)                    | A half-open interval `[start_ms, end_ms)` in integer milliseconds.        |
| [`Word`](#hearing.Word)(text, span[, confidence])                | Optional word-level timing (WhisperX / `word_timestamps=True`).           |
| [`Channel`](#hearing.Channel)(\*values)                             | Which capture channel a segment came from.                                |
| [`SpeakerLabel`](#hearing.SpeakerLabel)                                  |                                                                           |

### *class* hearing.Channel(\*values)

Bases: [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Enum`](https://docs.python.org/3/library/enum.html#enum.Enum)

Which capture channel a segment came from.

The channel *is* the “me vs them” signal, for free: `MIC` is the local
user, `SYSTEM` is everyone else (audio that came out of the speakers).
`MIXED` is a single-channel / unknown source.

### hearing.SpeakerLabel

alias of [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* hearing.TimeSpan(start_ms, end_ms)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A half-open interval `[start_ms, end_ms)` in integer milliseconds.

Integer time, never float seconds — accumulation-safe and hashable.

```pycon
>>> TimeSpan(0, 1500).duration_ms
1500
```

#### *property* duration_ms *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Length of the interval in milliseconds.

#### *classmethod* from_seconds(start, end)

Build a span from float seconds (e.g. from an STT engine).

* **Return type:**
  [`TimeSpan`](hearing.types.html.md#hearing.types.TimeSpan)

### *class* hearing.Transcript(segments=(), sample_rate=None, meta=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A finished transcript: an ordered collection of segments plus metadata.

Iterable and `len`-able, so it stands in for a `Sequence` of segments
wherever the architecture’s facades return “segments”. Adds convenience
accessors the CLI/agents need.

```pycon
>>> t = Transcript((TranscriptSegment("a", TimeSpan(0, 1000), speaker=ME),
...                  TranscriptSegment("b", TimeSpan(1000, 2000), speaker=THEM)))
>>> t.text
'a b'
>>> len(t)
2
>>> sorted(t.speakers)
['me', 'them']
```

#### *property* duration_ms *: [int](https://docs.python.org/3/builtins/functions.html#int)*

End of the last segment, or 0 if empty.

#### formatted(, speakers=True, timestamps=True)

Render as a human-readable transcript, one line per segment.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### *property* speakers *: [set](https://docs.python.org/3/builtins/stdtypes.html#set)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

The distinct speaker labels present (ignoring `None`).

#### *property* text *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

All segment texts joined by a single space.

#### to_jsonable()

A plain `list[dict]` ready for `json.dumps` (segments only).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

#### with_meta(\*\*kw)

Return a copy with extra metadata merged in.

* **Return type:**
  [`Transcript`](hearing.types.html.md#hearing.types.Transcript)

### *class* hearing.TranscriptSegment(text, span, channel=Channel.MIXED, speaker=None, confidence=None, words=(), meta=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The data spine — a standoff interval annotation over the audio.

Required fields are `text` and `span`. Everything else is optional
metadata that a concern *enriches*: STT sets `text`/`span`/
`confidence`; capture sets `channel`; diarization sets `speaker`.
Segments are frozen — enrich by copying (`with_speaker`/`with_channel`),
never mutate.

```pycon
>>> seg = TranscriptSegment("hello", TimeSpan(0, 500))
>>> seg.with_speaker(ME).speaker
'me'
>>> seg.text
'hello'
```

#### with_channel(channel)

Return a copy carrying a channel label (frozen -> copy, don’t mutate).

* **Return type:**
  [`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)

#### with_speaker(speaker)

Return a copy carrying a speaker label (frozen -> copy, don’t mutate).

* **Return type:**
  [`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)

### *class* hearing.Word(text, span, confidence=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Optional word-level timing (WhisperX / `word_timestamps=True`).

Lets an agent trigger on a keyword mid-utterance instead of waiting for the
end of a turn. Purely optional metadata on a [`TranscriptSegment`](#hearing.TranscriptSegment).

### *async* hearing.live_transcribe(, source, engine=None, diarizer=None, agent=None, audio_queue_max=50, segment_queue_max=100)

Stream FINALIZED segments as a meeting unfolds (the live path).

Same components as [`transcribe()`](#hearing.transcribe) — only the *source* (a streaming
[`CaptureSource`](hearing.interfaces.html.md#hearing.interfaces.CaptureSource) instead of a file) and the trigger
cadence (VAD utterance turn-ends instead of run-once) change. The
`STTEngine` and `AgentConsumer` interfaces are unchanged.

Each channel is demuxed onto its own bounded queue and driven through
`engine.stream_transcribe` as an independent async task, so a slow agent
never stalls capture (backpressure) and the channel “me vs them” label rides
every segment. Diarization defaults to the free channel trick; the agent’s
`on_segment` is fired fire-and-forget. Yields segments as utterances finalize.

See the `hearing-live-pipeline` skill.

### hearing.summarize(source, , agent=None, context=None, model=None, \*\*transcribe_kwargs)

Transcribe (if needed) then run an agent to produce meeting notes.

Accepts an audio source or an already-built [`Transcript`](#hearing.Transcript). Builds the
default agent (Claude if available, else the offline extractive fallback)
when none is injected.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### hearing.transcribe(source, , engine=None, diarizer=None, agent=None, language=None, split=True, mic_channels=(0,), system_channels=(1,), record=None)

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
  * **record** – optional `MutableMapping` store (e.g. a dol store) to persist
    the transcript JSON under key `"<source>.transcript.json"`.
* **Return type:**
  [`Transcript`](hearing.types.html.md#hearing.types.Transcript)
* **Returns:**
  A [`Transcript`](#hearing.Transcript) (iterable/len-able, so it stands in for a sequence
  of segments). Segments carry text, span, channel, and speaker.

### Modules

| [`agents`](hearing.agents.html.md#module-hearing.agents)         | The agent / "copilot" layer — the actual point of the hearing project.          |
|---------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`capture`](hearing.capture.html.md#module-hearing.capture)       | Audio capture and channel handling for the hearing pipeline.                    |
| [`cli`](hearing.cli.html.md#module-hearing.cli)               | Command-line interface for hearing, dispatched with `cw`.                       |
| [`context`](hearing.context.html.md#module-hearing.context)       | Context stores and retrieval (RAG) for context-connected agents.                |
| [`diarize`](hearing.diarize.html.md#module-hearing.diarize)       | Diarization and speaker labelling for the hearing pipeline.                     |
| [`interfaces`](hearing.interfaces.html.md#module-hearing.interfaces) | Facade Protocols for the four pipeline concerns.                                |
| [`pipeline`](hearing.pipeline.html.md#module-hearing.pipeline)     | Pipeline assembly — compose the four concerns by dependency injection.          |
| [`storage`](hearing.storage.html.md#module-hearing.storage)       | Transcript persistence via key-value stores (python-storage / `dol`).           |
| [`stt`](hearing.stt.html.md#module-hearing.stt)               | Speech-to-text for hearing — now backed by the scribed transcription façade.    |
| [`types`](hearing.types.html.md#module-hearing.types)           | Shared data model for the hearing pipeline.                                     |
| [`vad`](hearing.vad.html.md#module-hearing.vad)               | Voice-activity detection and utterance segmentation — re-exported from scribed. |
