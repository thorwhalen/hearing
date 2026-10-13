# hearing.stt

Speech-to-text for hearing — now backed by the scribed transcription façade.

hearing no longer implements its own STT engines. It consumes **scribed** (one
façade over many engines) and adapts scribed’s normalized `Transcript`/`Segment`
spine to hearing’s [`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment) data model. The rest of
the architecture still sees only the [`STTEngine`](hearing.interfaces.html.md#hearing.interfaces.STTEngine) Protocol:
`transcribe(audio) -> segments` and `stream_transcribe(frames) -> segments`.

The default engine is scribed’s faster-whisper backend (local, fast). Swap engines by
changing the scribed `backend=` (e.g. `"openai"`) — nothing downstream changes.
See scribed’s `scribed-choose-backend` skill for the full engine landscape, pricing,
and the local-vs-cloud decision.

### Module Attributes

| [`DEFAULT_BACKEND`](#hearing.stt.DEFAULT_BACKEND)   | Default scribed backend id for local transcription.   |
|--------------------------------------------------------------------|-------------------------------------------------------|

### Functions

| [`FasterWhisperSTT`](#hearing.stt.FasterWhisperSTT)(\*[, model_size])   | Backward-compatible constructor for the local engine (returns a `ScribedSTT`).   |
|---------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`OpenAISTT`](#hearing.stt.OpenAISTT)(\*\*kwargs)                | Backward-compatible constructor for the OpenAI engine (returns a `ScribedSTT`).  |
| [`default_engine`](#hearing.stt.default_engine)(\*\*kwargs)           | Return the project's default STT engine (scribed faster-whisper).                |
| [`get_engine`](#hearing.stt.get_engine)([name])                   | Build a scribed-backed STT engine by friendly name.                              |

### Classes

| [`ScribedSTT`](#hearing.stt.ScribedSTT)([backend, model_size, language, vad])   | An `STTEngine` backed by scribed — the single engine hearing now uses.   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|

### hearing.stt.DEFAULT_BACKEND *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'faster-whisper'*

Default scribed backend id for local transcription.

### hearing.stt.FasterWhisperSTT(, model_size=None, \*\*kwargs)

Backward-compatible constructor for the local engine (returns a `ScribedSTT`).

Retained so existing call sites (`FasterWhisperSTT(model_size="tiny")`) keep
working now that the engines are centralized in scribed.

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)

### hearing.stt.OpenAISTT(\*\*kwargs)

Backward-compatible constructor for the OpenAI engine (returns a `ScribedSTT`).

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)

### *class* hearing.stt.ScribedSTT(backend='faster-whisper', model_size=None, language=None, vad=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An `STTEngine` backed by scribed — the single engine hearing now uses.

* **Parameters:**
  * **backend** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – scribed backend id (`"faster-whisper"` default, `"openai"`, …).
  * **model_size** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – optional model override forwarded to the backend (e.g. `"tiny"`).
  * **language** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – force a language code; `None` => auto-detect.
  * **vad** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`VAD`](hearing.vad.html.md#hearing.vad.VAD)]) – utterance segmenter for `stream_transcribe` (default: scribed EnergyVAD).

#### *async* stream_transcribe(frames, , sample_rate)

Stream finalized segments as utterances complete (via scribed’s live path).

* **Return type:**
  [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)[[`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)]

#### transcribe(audio, , sample_rate, language=None)

Transcribe a whole mono clip via scribed; return ordered hearing segments.

* **Return type:**
  [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)]

### hearing.stt.default_engine(\*\*kwargs)

Return the project’s default STT engine (scribed faster-whisper).

Tests and quick runs typically pass `model_size="tiny"`.

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)

### hearing.stt.get_engine(name='whisper', \*\*kwargs)

Build a scribed-backed STT engine by friendly name.

`"whisper"`/`"faster-whisper"`/`"local"` -> faster-whisper; `"openai"`/
`"cloud"` -> openai. Any other registered scribed backend id works too.

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)
