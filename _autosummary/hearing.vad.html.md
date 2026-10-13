# hearing.vad

Voice-activity detection and utterance segmentation — re-exported from scribed.

The VAD logic (energy/neural detectors + utterance segmentation) is now owned by
`scribed.vad` so it can be shared across every scribed consumer. hearing keeps
this module as the stable import path; the names below are scribed’s.

See the `hearing-live-pipeline` skill for the rationale and the latency budget.

### Functions

| [`segment_utterances`](#hearing.vad.segment_utterances)(frames, \*, sample_rate[, ...])   | Group an async stream of audio blocks into utterances.   |
|-------------------------------------------------------------------------------------------------------|----------------------------------------------------------|

### Classes

| [`VAD`](#hearing.vad.VAD)(\*args, \*\*kwargs)            | Decides whether a block of audio contains speech.       |
|-------------------------------------------------------------------------------------|---------------------------------------------------------|
| [`EnergyVAD`](#hearing.vad.EnergyVAD)([threshold])             | RMS-energy threshold VAD — the dependency-free default. |
| [`SileroVAD`](#hearing.vad.SileroVAD)([speech_prob_threshold]) | Neural VAD via silero-vad (optional, lazy).             |

### *class* hearing.vad.EnergyVAD(threshold=0.01)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

RMS-energy threshold VAD — the dependency-free default.

A block counts as speech when its RMS energy exceeds `threshold` (in the same
units as the float audio, roughly `[-1, 1]`). Simple and deterministic; for
noisy real-world audio prefer [`SileroVAD`](#hearing.vad.SileroVAD).

#### is_speech(block, sample_rate)

True if the block’s RMS energy is above `threshold`.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### *class* hearing.vad.SileroVAD(speech_prob_threshold=0.5)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Neural VAD via silero-vad (optional, lazy). Accurate on noisy audio.

Requires `pip install silero-vad` (or torch.hub). Raises an informative error
if unavailable; [`EnergyVAD`](#hearing.vad.EnergyVAD) needs no dependencies.

#### is_speech(block, sample_rate)

True if silero’s speech probability for the block exceeds the threshold.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### *class* hearing.vad.VAD(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Decides whether a block of audio contains speech.

#### is_speech(block, sample_rate)

True if `block` (mono float32) contains speech.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### *async* hearing.vad.segment_utterances(frames, , sample_rate, vad=None, silence_ms=700, min_speech_ms=200, max_utterance_ms=30000)

Group an async stream of audio blocks into utterances.

Yields `(utterance_samples, start_ms)` once per finalized utterance: speech
accumulates into a buffer; after `silence_ms` of trailing silence (or
`max_utterance_ms` of continuous speech) the buffer is emitted with its start
offset (integer ms from the beginning of the stream). Utterances with less than
`min_speech_ms` of actual speech are dropped as noise. `sample_rate` is the
rate of the incoming blocks (used only for the ms arithmetic).

* **Return type:**
  [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)[[`Tuple`](https://docs.python.org/3/library/typing.html#typing.Tuple)[`ndarray`, [`int`](https://docs.python.org/3/builtins/functions.html#int)]]
