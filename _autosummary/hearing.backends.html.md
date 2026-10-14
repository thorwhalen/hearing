# hearing.backends

Extra scribed backends that hearing contributes: Apple-Silicon MLX and WhisperX.

hearing’s STT runs through scribed (see [`hearing.stt`](hearing.stt.html.md#module-hearing.stt)). scribed already ships
the cloud engines (OpenAI, Deepgram, AssemblyAI, …) and faster-whisper; the
engines below are not in scribed yet, so hearing provides them as \*\*scribed
plugins\*\*, registered at runtime with `scribed.register_backend()`:

- `mlx-whisper` — Whisper on Apple Silicon via MLX (`pip install 'hearing[mlx]'`)
- `parakeet-mlx` — NVIDIA Parakeet-TDT on Apple Silicon via MLX (same extra)
- `whisperx` — WhisperX: batched Whisper + word alignment + optional pyannote
  diarization (`pip install 'hearing[whisperx]'`)

Each backend is a subpackage laid out exactly like a `scribed.backends.<id>`
package (`config.py` with `BACKEND_CONFIG`, `adapter.py` with `Adapter`),
so it can move into scribed verbatim. Registration is lazy and non-clobbering:
[`register_backends()`](#hearing.backends.register_backends) only adds an id scribed does not already provide, so
once scribed ships one of these, scribed’s own implementation wins.

Nothing here imports an engine SDK at import time; the adapters import it on first
transcription and raise an informative error (naming the extra) when it is absent,
or — for the MLX engines — when not running on Apple Silicon.

### Module Attributes

| [`BACKEND_MODULES`](#hearing.backends.BACKEND_MODULES)   | Subpackages of this package that are scribed backends (backend id -> module).   |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------|

### Functions

| [`backend_config`](#hearing.backends.backend_config)(backend_id)                     | The `BACKEND_CONFIG` of one of hearing's backends (no SDK import).         |
|-------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`is_apple_silicon`](#hearing.backends.is_apple_silicon)(\*[, system, machine])        | True on macOS running on an ARM (M-series) CPU — where MLX works.          |
| [`logprob_to_confidence`](#hearing.backends.logprob_to_confidence)(avg_logprob)             | Map Whisper's average log-probability to a rough `[0, 1]` confidence.      |
| [`register_backends`](#hearing.backends.register_backends)([backend_ids, registry])     | Register hearing's backends with scribed's registry; return the ids added. |
| [`require_apple_silicon`](#hearing.backends.require_apple_silicon)(engine, \*[, check])     | Raise an informative `RuntimeError` unless running on Apple Silicon.       |
| [`require_module`](#hearing.backends.require_module)(module_name, \*, engine, extra) | Import `module_name` or raise an `ImportError` that names the extra.       |
| [`to_waveform_16k`](#hearing.backends.to_waveform_16k)(audio)                         | Decode any scribed audio input to a float32 mono 16 kHz numpy array.       |
| [`whisper_result_to_segments`](#hearing.backends.whisper_result_to_segments)(result)             | Build scribed `Segment`s from an openai-whisper-style result dict.         |

### hearing.backends.BACKEND_MODULES *: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= {'mlx-whisper': 'hearing.backends.mlx_whisper', 'parakeet-mlx': 'hearing.backends.parakeet_mlx', 'whisperx': 'hearing.backends.whisperx'}*

Subpackages of this package that are scribed backends (backend id -> module).

### hearing.backends.backend_config(backend_id)

The `BACKEND_CONFIG` of one of hearing’s backends (no SDK import).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### hearing.backends.is_apple_silicon(\*, system=<function system>, machine=<function machine>)

True on macOS running on an ARM (M-series) CPU — where MLX works.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### hearing.backends.logprob_to_confidence(avg_logprob)

Map Whisper’s average log-probability to a rough `[0, 1]` confidence.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`float`](https://docs.python.org/3/builtins/functions.html#float)]

### hearing.backends.register_backends(backend_ids=None, , registry=None)

Register hearing’s backends with scribed’s registry; return the ids added.

Idempotent and non-clobbering: an id scribed already knows is left alone.
The adapter itself is loaded lazily by scribed (from `module_path`).

* **Parameters:**
  * **backend_ids** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]) – which backends to register (default: all of them).
  * **registry** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – the scribed registry module (injectable for tests).
* **Return type:**
  [`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### hearing.backends.require_apple_silicon(engine, , check=None)

Raise an informative `RuntimeError` unless running on Apple Silicon.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### hearing.backends.require_module(module_name, , engine, extra)

Import `module_name` or raise an `ImportError` that names the extra.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### hearing.backends.to_waveform_16k(audio)

Decode any scribed audio input to a float32 mono 16 kHz numpy array.

Whisper-family engines accept such an array directly, which avoids their
ffmpeg-based file loading (hearing hands utterances over as WAV bytes).

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### hearing.backends.whisper_result_to_segments(result)

Build scribed `Segment`s from an openai-whisper-style result dict.

Handles both mlx-whisper (word `probability`) and WhisperX (word `score`,
optional `speaker` on segments and words). Times are float seconds.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)

```pycon
>>> segs = whisper_result_to_segments({"segments": [
...     {"start": 0.0, "end": 1.5, "text": " hi there",
...      "words": [{"word": " hi", "start": 0.0, "end": 0.4, "probability": 0.9}]}
... ]})
>>> segs[0].text, segs[0].span.end_ms, segs[0].words[0].text
('hi there', 1500, 'hi')
```

### Modules

| [`mlx_whisper`](hearing.backends.mlx_whisper.html.md#module-hearing.backends.mlx_whisper)   | mlx-whisper (Whisper on Apple Silicon via MLX) backend for scribed, from hearing.                |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [`parakeet_mlx`](hearing.backends.parakeet_mlx.html.md#module-hearing.backends.parakeet_mlx) | parakeet-mlx (NVIDIA Parakeet-TDT on Apple Silicon via MLX) backend for scribed, from hearing.   |
| [`whisperx`](hearing.backends.whisperx.html.md#module-hearing.backends.whisperx)         | WhisperX (batched Whisper + alignment + optional diarization) backend for scribed, from hearing. |
