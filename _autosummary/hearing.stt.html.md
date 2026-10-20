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

Engines by friendly name ([`ENGINE_ALIASES`](#hearing.stt.ENGINE_ALIASES), used by [`get_engine()`](#hearing.stt.get_engine) and the
CLI’s `--engine`):

- `whisper` — faster-whisper, local, any CPU/GPU (default; `hearing[whisper]`)
- `openai` — OpenAI transcription API (`hearing[openai]`, `OPENAI_API_KEY`)
- `deepgram` — Deepgram Nova-3 (`hearing[deepgram]`, `DEEPGRAM_API_KEY`)
- `mlx` / `parakeet` — Whisper / Parakeet-TDT on Apple Silicon (`hearing[mlx]`)
- `whisperx` — WhisperX, aligned words + optional diarization (`hearing[whisperx]`)

The last three are scribed backends that hearing itself contributes
([`hearing.backends`](hearing.backends.html.md#module-hearing.backends)); they are registered with scribed on first use.

### Module Attributes

| [`DEFAULT_BACKEND`](#hearing.stt.DEFAULT_BACKEND)        | Default scribed backend id for local transcription.                             |
|-------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`ENGINE_ALIASES`](#hearing.stt.ENGINE_ALIASES)         | Friendly engine name -> scribed backend id (the SSOT for `get_engine`/the CLI). |
| [`WHISPER_SIZED_BACKENDS`](#hearing.stt.WHISPER_SIZED_BACKENDS) | Backends whose `model` accepts a bare whisper size ("base", "small", ...).      |
| [`ENGINE_NAMES`](#hearing.stt.ENGINE_NAMES)           | Engine names shown in help and error messages (one per backend).                |

### Functions

| [`DeepgramSTT`](#hearing.stt.DeepgramSTT)(\*[, model])           | Deepgram (cloud) engine — Nova-3 by default; `model="nova-2"` etc.                                                        |
|-------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [`FasterWhisperSTT`](#hearing.stt.FasterWhisperSTT)(\*[, model_size]) | Backward-compatible constructor for the local engine (returns a `ScribedSTT`).                                            |
| [`MLXSTT`](#hearing.stt.MLXSTT)(\*[, model, mlx_backend])   | Apple-Silicon (MLX) engine: mlx-whisper by default, or `mlx_backend="parakeet-mlx"`.                                      |
| [`OpenAISTT`](#hearing.stt.OpenAISTT)(\*\*kwargs)              | Backward-compatible constructor for the OpenAI engine (returns a `ScribedSTT`).                                           |
| [`WhisperXSTT`](#hearing.stt.WhisperXSTT)(\*[, model, diarize])  | WhisperX engine: aligned word timestamps, plus pyannote speakers if `diarize`.                                            |
| [`default_engine`](#hearing.stt.default_engine)(\*\*kwargs)         | Return the project's default STT engine (scribed faster-whisper).                                                         |
| [`get_engine`](#hearing.stt.get_engine)([name])                 | Build a scribed-backed STT engine by friendly name (see [`ENGINE_ALIASES`](#hearing.stt.ENGINE_ALIASES)). |

### Classes

| [`ScribedSTT`](#hearing.stt.ScribedSTT)([backend, model_size, language, ...])   | An `STTEngine` backed by scribed — the single engine hearing now uses.   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|

### hearing.stt.DEFAULT_BACKEND *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'faster-whisper'*

Default scribed backend id for local transcription.

### hearing.stt.DeepgramSTT(, model=None, \*\*kwargs)

Deepgram (cloud) engine — Nova-3 by default; `model="nova-2"` etc. swaps it.

Batch goes to Deepgram’s pre-recorded REST API (via scribed’s deepgram backend);
the live path is scribed’s VAD-segmented stream over that batch call. Needs
`pip install 'hearing[deepgram]'` and `DEEPGRAM_API_KEY`.

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)

### hearing.stt.ENGINE_ALIASES *: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= {'cloud': 'openai', 'deepgram': 'deepgram', 'faster-whisper': 'faster-whisper', 'local': 'faster-whisper', 'mlx': 'mlx-whisper', 'mlx-whisper': 'mlx-whisper', 'nova': 'deepgram', 'openai': 'openai', 'parakeet': 'parakeet-mlx', 'parakeet-mlx': 'parakeet-mlx', 'whisper': 'faster-whisper', 'whisperx': 'whisperx'}*

Friendly engine name -> scribed backend id (the SSOT for `get_engine`/the CLI).
Any other registered scribed backend id is accepted as-is.

### hearing.stt.ENGINE_NAMES *= ('whisper', 'openai', 'deepgram', 'mlx', 'parakeet', 'whisperx')*

Engine names shown in help and error messages (one per backend).

### hearing.stt.FasterWhisperSTT(, model_size=None, \*\*kwargs)

Backward-compatible constructor for the local engine (returns a `ScribedSTT`).

Retained so existing call sites (`FasterWhisperSTT(model_size="tiny")`) keep
working now that the engines are centralized in scribed.

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)

### hearing.stt.MLXSTT(, model=None, mlx_backend='mlx-whisper', \*\*kwargs)

Apple-Silicon (MLX) engine: mlx-whisper by default, or `mlx_backend="parakeet-mlx"`.

`model` is a Hugging Face repo id or (mlx-whisper) a bare Whisper size such as
`"small"`. Needs macOS on Apple Silicon and `pip install 'hearing[mlx]'`.

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)

### hearing.stt.OpenAISTT(\*\*kwargs)

Backward-compatible constructor for the OpenAI engine (returns a `ScribedSTT`).

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)

### *class* hearing.stt.ScribedSTT(backend='faster-whisper', model_size=None, language=None, vad=None, options=dict())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An `STTEngine` backed by scribed — the single engine hearing now uses.

* **Parameters:**
  * **backend** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – scribed backend id (`"faster-whisper"` default, `"openai"`, …).
  * **model_size** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – optional model override forwarded to the backend (e.g. `"tiny"`).
  * **language** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – force a language code; `None` => auto-detect.
  * **vad** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`VAD`](hearing.vad.html.md#hearing.vad.VAD)]) – utterance segmenter for `stream_transcribe` (default: scribed EnergyVAD).
  * **options** ([`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – extra backend kwargs forwarded on every call (e.g.
    `{"diarize": True}` for WhisperX/Deepgram); see the backend’s
    `param_map` for what it accepts.

#### *async* stream_transcribe(frames, , sample_rate)

Stream finalized segments as utterances complete (via scribed’s live path).

* **Return type:**
  [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)[[`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)]

#### transcribe(audio, , sample_rate, language=None)

Transcribe a whole mono clip via scribed; return ordered hearing segments.

* **Return type:**
  [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)]

### hearing.stt.WHISPER_SIZED_BACKENDS *= frozenset({'faster-whisper', 'mlx-whisper', 'whisperx'})*

Backends whose `model` accepts a bare whisper size (“base”, “small”, …).

### hearing.stt.WhisperXSTT(, model=None, diarize=False, \*\*kwargs)

WhisperX engine: aligned word timestamps, plus pyannote speakers if `diarize`.

Needs `pip install 'hearing[whisperx]'`; `diarize=True` also needs a
Hugging Face token in `HF_TOKEN`.

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)

### hearing.stt.default_engine(\*\*kwargs)

Return the project’s default STT engine (scribed faster-whisper).

Tests and quick runs typically pass `model_size="tiny"`.

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)

### hearing.stt.get_engine(name='whisper', \*\*kwargs)

Build a scribed-backed STT engine by friendly name (see [`ENGINE_ALIASES`](#hearing.stt.ENGINE_ALIASES)).

`"whisper"` -> faster-whisper, `"openai"`, `"deepgram"`, `"mlx"` ->
mlx-whisper, `"parakeet"` -> parakeet-mlx, `"whisperx"`. Any other
registered scribed backend id works too. `kwargs` go to [`ScribedSTT`](#hearing.stt.ScribedSTT).

```pycon
>>> get_engine("mlx").backend
'mlx-whisper'
```

* **Return type:**
  [`ScribedSTT`](#hearing.stt.ScribedSTT)
