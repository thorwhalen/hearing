# hearing.interfaces

Facade Protocols for the four pipeline concerns.

Every engine/component is dependency-injected as one of these; the pipeline
depends only on these interfaces, never on a concrete engine. Implementers
satisfy them *structurally* (`typing.Protocol`) — they do not subclass.

This is the contract the `hearing-architecture` skill defines and that every
other `hearing-*` concern implements against.

### Classes

| [`AgentConsumer`](#hearing.interfaces.AgentConsumer)(\*args, \*\*kwargs)   | Consumes the (labeled) transcript stream and does things.          |
|--------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`CaptureSource`](#hearing.interfaces.CaptureSource)(\*args, \*\*kwargs)   | Audio source — the ONLY thing that differs between batch and live. |
| [`Diarizer`](#hearing.interfaces.Diarizer)(\*args, \*\*kwargs)        | Labels who spoke — enriches segments with `.speaker`.              |
| [`STTEngine`](#hearing.interfaces.STTEngine)(\*args, \*\*kwargs)       | Speech-to-text.                                                    |

### *class* hearing.interfaces.AgentConsumer(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Consumes the (labeled) transcript stream and does things.

Running notes, suggested questions, RAG over related docs, post-meeting
summaries. Defaults to Claude but stays pluggable (see the `claude-api`
skill for model ids / pricing / tool use).

#### *async* on_segment(segment)

Called per finalized segment (live). Return an optional insight.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

#### *async* on_window(window)

Called on a window/turn or the whole transcript (batch).

Return an optional insight (summary, action items, a suggested
question, a surfaced document, …).

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### *class* hearing.interfaces.CaptureSource(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Audio source — the ONLY thing that differs between batch and live.

Yields `(channel, frames)` so mic and system audio stay on separate
channels all the way down. A batch implementation reads a file; a live
implementation reads a device/tap.

#### astream()

Live / async: yield `(channel, frames)` blocks until stopped.

* **Return type:**
  [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Channel`](hearing.types.html.md#hearing.types.Channel), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

#### frames()

Batch / sync: yield `(channel, frames[n_samples])` blocks to EOF.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Channel`](hearing.types.html.md#hearing.types.Channel), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

### *class* hearing.interfaces.Diarizer(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Labels who spoke — enriches segments with `.speaker`.

May use the audio (pyannote) or just the channel (the channel trick).
Identity resolution (`spk_0` -> `"Alice"`) is an optional further step
behind the same interface.

#### assign_speakers(segments, , audio=None, sample_rate=None)

Yield segments with `.speaker` populated (enrich-by-copy).

* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)]

### *class* hearing.interfaces.STTEngine(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Speech-to-text.

`transcribe` is the batch one-liner; `stream_transcribe` is the live
variant. Both yield [`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment) — same shape,
same spine. The rest of the architecture never names a concrete engine.

#### *async* stream_transcribe(frames, , sample_rate)

Live: yield interim then finalized segments as audio arrives.

Mark interim vs final via `meta` (e.g. `meta['final']`). See the
`hearing-live-pipeline` skill — this is the milestone-2 entry point.

* **Return type:**
  [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)[[`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)]

#### transcribe(audio, , sample_rate, language=None)

Batch: whole clip in (float32 mono ndarray), segments out.

* **Return type:**
  [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)]
