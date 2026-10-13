# hearing.types

Shared data model for the hearing pipeline.

This is the SSOT data spine that every concern (capture, STT, diarization,
agents) speaks. A transcript is *standoff interval annotation* over the audio:
segments reference the audio by time (a [`TimeSpan`](#hearing.types.TimeSpan)) and never carry the
samples themselves. Time is integer milliseconds — never bare float seconds —
so it is accumulation-safe, hashable, and round-trippable.

See the `hearing-architecture` skill for the rationale behind every choice
here, and the `annotation-systems` skill for the standoff-annotation theory.

### Functions

| [`merge_segments`](#hearing.types.merge_segments)(\*segment_groups)   | Merge several segment sequences into one list ordered by start time.   |
|-------------------------------------------------------------------------------------|------------------------------------------------------------------------|

### Classes

| [`Channel`](#hearing.types.Channel)(\*values)                             | Which capture channel a segment came from.                              |
|------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`TimeSpan`](#hearing.types.TimeSpan)(start_ms, end_ms)                    | A half-open interval `[start_ms, end_ms)` in integer milliseconds.      |
| [`Transcript`](#hearing.types.Transcript)([segments, sample_rate, meta])     | A finished transcript: an ordered collection of segments plus metadata. |
| [`TranscriptSegment`](#hearing.types.TranscriptSegment)(text, span[, channel, ...]) | The data spine — a standoff interval annotation over the audio.         |
| [`Word`](#hearing.types.Word)(text, span[, confidence])                | Optional word-level timing (WhisperX / `word_timestamps=True`).         |

### *class* hearing.types.Channel(\*values)

Bases: [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Enum`](https://docs.python.org/3/library/enum.html#enum.Enum)

Which capture channel a segment came from.

The channel *is* the “me vs them” signal, for free: `MIC` is the local
user, `SYSTEM` is everyone else (audio that came out of the speakers).
`MIXED` is a single-channel / unknown source.

### *class* hearing.types.TimeSpan(start_ms, end_ms)

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
  [`TimeSpan`](#hearing.types.TimeSpan)

### *class* hearing.types.Transcript(segments=(), sample_rate=None, meta=<factory>)

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
  [`Transcript`](#hearing.types.Transcript)

### *class* hearing.types.TranscriptSegment(text, span, channel=Channel.MIXED, speaker=None, confidence=None, words=(), meta=<factory>)

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
  [`TranscriptSegment`](#hearing.types.TranscriptSegment)

#### with_speaker(speaker)

Return a copy carrying a speaker label (frozen -> copy, don’t mutate).

* **Return type:**
  [`TranscriptSegment`](#hearing.types.TranscriptSegment)

### *class* hearing.types.Word(text, span, confidence=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Optional word-level timing (WhisperX / `word_timestamps=True`).

Lets an agent trigger on a keyword mid-utterance instead of waiting for the
end of a turn. Purely optional metadata on a [`TranscriptSegment`](#hearing.types.TranscriptSegment).

### hearing.types.merge_segments(\*segment_groups)

Merge several segment sequences into one list ordered by start time.

Used when transcribing the mic and system channels separately and then
interleaving them back into a single chronological transcript.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`TranscriptSegment`](#hearing.types.TranscriptSegment)]
