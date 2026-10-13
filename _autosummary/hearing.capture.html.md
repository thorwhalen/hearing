# hearing.capture

Audio capture and channel handling for the hearing pipeline.

This module owns turning an audio *source* into per-channel float arrays, and the
all-important **channel split**: mic and system audio are kept on separate channels
so that “who is local” is known for free (see the `hearing-diarization` skill for
what we do with that, and `hearing-audio-capture` for the macOS mechanics —
BlackHole + Aggregate Device, or Core Audio taps).

The generic, channel-agnostic conditioning (decode, down-mix, resample, energy) now
lives in `scribed.audio` and is re-exported here for backward compatibility —
hearing owns only the multi-channel / “me vs them” concerns.

### Functions

| [`split_channels`](#hearing.capture.split_channels)(data, \*[, mic_channels, ...])   | Split a multi-channel array into per-`Channel` mono arrays.   |
|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------|

### Classes

| [`ChannelSplitFileCapture`](#hearing.capture.ChannelSplitFileCapture)(path[, ...])        | A batch [`CaptureSource`](hearing.interfaces.html.md#hearing.interfaces.CaptureSource) over an audio file.   |
|----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| [`DeviceCapture`](#hearing.capture.DeviceCapture)([device, block_ms, ...])      | Live macOS capture from an audio *device* (the milestone-2 capture source).                                                   |
| [`StreamingFileCapture`](#hearing.capture.StreamingFileCapture)(path[, block_ms, ...]) | A *streaming* [`CaptureSource`](hearing.interfaces.html.md#hearing.interfaces.CaptureSource) over a file.    |

### *class* hearing.capture.ChannelSplitFileCapture(path, mic_channels=(0,), system_channels=(1,))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A batch [`CaptureSource`](hearing.interfaces.html.md#hearing.interfaces.CaptureSource) over an audio file.

Reads the file once and yields `(channel, mono_frames)` for each channel
present. The live counterpart (device/tap) implements the same interface;
swapping it in is the *only* change needed to go live — see the
`hearing-live-pipeline` skill.

Typical use (needs a real audio file, so it is not run as a doctest):

```default
ChannelSplitFileCapture("meeting.wav").frames()
```

#### *async* astream()

Stream the file’s channels in one shot (whole clip per channel).

Provided so a file satisfies the async `CaptureSource` too; for a
realistic block-by-block live simulation use [`StreamingFileCapture`](#hearing.capture.StreamingFileCapture).

* **Return type:**
  [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Channel`](hearing.types.html.md#hearing.types.Channel), `ndarray`]]

#### channels()

The per-channel mono arrays at the file’s native sample rate.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`Channel`](hearing.types.html.md#hearing.types.Channel), `ndarray`]

#### frames()

Yield `(channel, mono_frames)` once per channel (whole clip).

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Channel`](hearing.types.html.md#hearing.types.Channel), `ndarray`]]

### *class* hearing.capture.DeviceCapture(device=None, block_ms=200, mic_channels=(0, 1), system_channels=(2, 3), sample_rate=48000, channels_count=4)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Live macOS capture from an audio *device* (the milestone-2 capture source).

Point this at an **Aggregate Device** that combines your microphone and
BlackHole (so mic and system audio land on separate, non-mixed channels —
see the `hearing-audio-capture` skill for the Audio MIDI Setup). Reads
multi-channel blocks and splits them into mic/system channels.

Requires `pip install 'hearing[capture]'` (sounddevice). Needs real audio
hardware to exercise; constructing it is cheap (the device opens in
`astream`). For a hardware-free run of the live loop, use
[`StreamingFileCapture`](#hearing.capture.StreamingFileCapture).

#### *async* astream()

Open the device and yield `(channel, block)` blocks until cancelled.

* **Return type:**
  [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Channel`](hearing.types.html.md#hearing.types.Channel), `ndarray`]]

#### *static* list_devices()

Return available audio devices (helps pick the Aggregate Device).

### *class* hearing.capture.StreamingFileCapture(path, block_ms=200, realtime=False, mic_channels=(0,), system_channels=(1,))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A *streaming* [`CaptureSource`](hearing.interfaces.html.md#hearing.interfaces.CaptureSource) over a file.

Yields `(channel, block)` in `block_ms` chunks, time-ordered across
channels, so the live pipeline can be exercised end-to-end without a mic or
BlackHole. With `realtime=True` it paces playback in real time (for demos);
the default streams as fast as possible (for tests).

#### *async* astream()

Yield `(channel, block)` blocks, all channels per time step.

* **Return type:**
  [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Channel`](hearing.types.html.md#hearing.types.Channel), `ndarray`]]

#### channels()

The per-channel mono arrays at the file’s native sample rate.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`Channel`](hearing.types.html.md#hearing.types.Channel), `ndarray`]

#### frames()

Batch view: whole clip per channel.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Channel`](hearing.types.html.md#hearing.types.Channel), `ndarray`]]

### hearing.capture.split_channels(data, , mic_channels=(0,), system_channels=(1,))

Split a multi-channel array into per-`Channel` mono arrays.

An aggregate device *does not mix* — mic lands on one set of channels and
system audio on another — so we can slice the columns apart. A mono file
(or single-column) has no split; it is returned as `{Channel.MIXED: ...}`.

* **Parameters:**
  * **data** (`ndarray`) – shape `(n_samples,)` or `(n_samples, n_channels)`.
  * **mic_channels** ([`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`int`](https://docs.python.org/3/builtins/functions.html#int)]) – column indices carrying the local microphone.
  * **system_channels** ([`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`int`](https://docs.python.org/3/builtins/functions.html#int)]) – column indices carrying captured system audio.
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`Channel`](hearing.types.html.md#hearing.types.Channel), `ndarray`]
* **Returns:**
  Mapping from `Channel` to a mono float32 array. Channels whose
  indices are out of range are silently omitted.
