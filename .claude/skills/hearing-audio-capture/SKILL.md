---
name: hearing-audio-capture
description: Use when capturing audio for meeting transcription on macOS (and the iOS limits) — getting BOTH the microphone AND system audio (the other participants coming out of your speakers) into a Python pipeline. Triggers on system audio capture, loopback, BlackHole, Aggregate Device, Multi-Output Device, Audio MIDI Setup, Core Audio taps, AudioHardwareCreateProcessTap, AudioTee, ScreenCaptureKit, SCStream, PyObjC SCK -3805, sounddevice InputStream, soundcard, PyAudio, ffmpeg avfoundation, channel slicing / mapping, "record what I hear", "capture the meeting audio", separate mic vs system channels, the "me vs them" channel trick, virtual audio driver, sample-rate / clock / drift mismatch, screen-recording permission for audio, and iOS/iPhone call/app audio recording restrictions (ReplayKit, iOS 18.1 call recording).
---

# Hearing — Audio Capture (macOS)

Audio capture is the hardest layer of the meeting pipeline. The OS does **not** let an app read another app's output directly, so capturing **system audio** (the other participants) requires either a virtual loopback driver or a Core Audio tap. This skill covers both behind one interface and the one insight that makes everything downstream easier.

## The core abstraction

A capture source is **anything that yields `(Channel, frames)` tuples at a known sample rate**, behind a small `Protocol` — `CaptureSource` in `hearing/interfaces.py`. Each yield tags its mono frame buffer with the `Channel` it came from, so mic and system stay on **separate** channels all the way down. Keep the interface format-agnostic and inject the backend (BlackHole/Aggregate, AudioTee, mic-only). Frames flow out; STT, diarization, and the agent consume them. See [[hearing-architecture]] for how the concerns wire together. The `Channel` enum and the shared types come from `hearing/types.py` (defined by [[hearing-architecture]]) — import them, don't redefine.

```python
from typing import Any, Protocol, AsyncIterator, Iterator, runtime_checkable

from hearing.types import Channel  # MIC / SYSTEM / MIXED — defined in hearing/types.py

@runtime_checkable
class CaptureSource(Protocol):
    """A pluggable audio source. Backends: BlackHole+Aggregate, AudioTee, mic-only.

    Yields ``(channel, frames)`` so mic and system audio stay on separate
    channels. `frames` is a mono float32 sample buffer for that channel.
    """
    sample_rate: int

    def frames(self) -> Iterator[tuple[Channel, "Any"]]: ...        # batch / sync
    def astream(self) -> AsyncIterator[tuple[Channel, "Any"]]: ...   # live / async
```

The batch implementation is `ChannelSplitFileCapture` (in `hearing/capture.py`), with channel-handling helpers `load_audio`, `to_mono`, `resample`, `to_mono_16k`, `split_channels(data, *, mic_channels=(0,), system_channels=(1,)) -> dict[Channel, ndarray]`, and `rms_energy`.

## THE KEY INSIGHT — keep mic and system on SEPARATE channels

Do **not** mix mic and system audio into one mono stream. If the mic is on channels 1–2 and system audio on channels 3–4, then **which channel has energy tells you who is speaking**: mic-energy ⇒ *you* ("Me"), system-energy ⇒ *the others* ("Them"). This channel split is a cheap, deterministic first-pass speaker separation — Meetily ships exactly this as dual-VAD "Me"/"Them" labeling [GD]. Hand the per-channel signal off to [[hearing-diarization]], which refines "Them" into individual speakers and uses the channel label as a strong prior. **Never collapse the channels before diarization has seen them.**

## Decision table — which capture approach

| Need | Use | Why |
|------|-----|-----|
| Separate mic + system channels **today**, batch or live | **BlackHole + Aggregate Device** (A) | Proven; an aggregate does not mix, so channels stay split [8][30] |
| Native, no driver install, clean pre-mixer system audio (macOS 14.2+) | **Core Audio taps via AudioTee CLI** (B) | First-party API; AudioTee pipes raw PCM to stdout [9][31] |
| System audio only, you don't need the mic | AudioTee, or BlackHole as input | — |
| Mic only (no system audio) | `sounddevice` / PyAudio on default input | Simplest; what the current POC does |
| ❌ Drive ScreenCaptureKit from Python via PyObjC | **Don't** | Effectively broken: `SCStreamErrorDomain -3805`, callback never fires [32] |

Two non-negotiables:
1. **Never drive ScreenCaptureKit from Python via PyObjC.** Shell out to a Swift binary (AudioTee) instead [32].
2. **All devices in an Aggregate must share one sample rate.** Mismatched clocks (e.g. AirPods as clock device) cause glitches/dropouts. Pin the built-in output as clock and enable Drift Correction on the others [8].

---

## Approach A — BlackHole + Aggregate Device (proven, today)

**BlackHole** (`ExistentialAudio/BlackHole`, GPL-3.0) is a virtual loopback driver in 2ch / 16ch / 64ch variants [8]. You route system output *into* it, then read it back in Python alongside the mic.

**One-time setup (guide the user through this — see `check_requirements` pattern below):**
1. `brew install blackhole-2ch`
2. Open **Audio MIDI Setup** → create a **Multi-Output Device** = real output (e.g. Built-in/Speakers) **+** BlackHole 2ch. *Reason: you still hear the audio while it's captured.* Put **Built-in Output at the top as the clock/master**; enable **Drift Correction** on BlackHole [8].
3. **System Settings → Sound → Output** → select that Multi-Output Device. Now system audio flows into BlackHole.
4. Back in Audio MIDI Setup → create an **Aggregate Device** = your **microphone** + **BlackHole 2ch**. Order matters: it fixes the channel layout (mic = ch 1–2, BlackHole/system = ch 3–4). Same sample rate on both.
5. In Python, open the **Aggregate Device**, read all 4 channels, slice columns.

```python
# sounddevice: open the Aggregate Device, read all channels, slice mic vs system.
import sounddevice as sd
import numpy as np

def find_device(name_substr: str) -> int:
    """Return the device index whose name contains `name_substr` (case-insensitive)."""
    for idx, dev in enumerate(sd.query_devices()):
        if name_substr.lower() in dev["name"].lower():
            return idx
    raise LookupError(f"No audio device matching {name_substr!r}. Run sd.query_devices().")

def capture_blocks(
    *,
    device_name: str = "Aggregate",
    sample_rate: int = 48_000,   # match the Aggregate's rate; no magic constants elsewhere
    block_frames: int = 4_800,   # 100 ms at 48 kHz
    mic_channels: tuple[int, ...] = (0, 1),     # ch 1–2 = local mic  -> "Me"
    system_channels: tuple[int, ...] = (2, 3),  # ch 3–4 = BlackHole  -> "Them"
):
    """Yield (data, mic_slice, system_slice) blocks. data is float32 frames×channels."""
    device = find_device(device_name)
    n_ch = max(*mic_channels, *system_channels) + 1
    with sd.InputStream(
        device=device, channels=n_ch, samplerate=sample_rate,
        blocksize=block_frames, dtype="float32",
    ) as stream:
        while True:
            data, overflowed = stream.read(block_frames)   # (block_frames, n_ch)
            mic = data[:, list(mic_channels)]               # the "me vs them" trick:
            system = data[:, list(system_channels)]         # column slicing splits speakers
            yield data, mic, system
```

Backend notes: **soundcard** takes an explicit channel map (`mic.record(numframes, channels=[0,1,2,3])`); **PyAudio** opens with `channels=N` on the aggregate (lower-level, what the current POC uses); **ffmpeg `-f avfoundation`** can read the aggregate but **avfoundation alone cannot grab system audio** — it still needs BlackHole as the source. Default to `sounddevice` for the `mapping=`/column-slice ergonomics.

## Approach B — Core Audio taps via AudioTee (native, macOS 14.2+)

macOS 14.2 introduced **Core Audio taps** (`AudioHardwareCreateProcessTap`): "capture outgoing audio from a process or group of processes" [9]. Taps grab **pre-mixer** audio (clean regardless of system volume) and require **Screen Recording / system-audio permission**. ownscribe uses exactly this — taps to capture speaker output, optionally mixing in the mic [GD].

**AudioTee** (`makeusabrew/audiotee`) is an open-source Swift CLI that streams system audio as **raw PCM to stdout** — built to pipe into another process for real-time ASR [31]. So: **shell out to the binary and read its stdout** rather than touching PyObjC.

```python
# Shell out to the AudioTee Swift binary; read raw PCM blocks from stdout.
import asyncio, numpy as np

async def audiotee_blocks(
    *,
    binary: str = "audiotee",     # path to the prebuilt Swift CLI (inject, no magic path)
    sample_rate: int = 48_000,
    n_channels: int = 2,
    block_frames: int = 4_800,
    dtype: np.dtype = np.dtype("<i2"),   # adjust to AudioTee's emitted format
):
    """Async-yield system-audio blocks (frames×channels) from AudioTee stdout."""
    bytes_per_block = block_frames * n_channels * dtype.itemsize
    proc = await asyncio.create_subprocess_exec(
        binary, stdout=asyncio.subprocess.PIPE,
    )
    try:
        while True:
            raw = await proc.stdout.readexactly(bytes_per_block)
            yield np.frombuffer(raw, dtype=dtype).reshape(-1, n_channels)
    finally:
        proc.terminate()
        await proc.wait()
```

**Caveat (June 2026):** a single AudioTee binary emitting **combined mic+system** is not shipped (only the author's private fork) [31]. So for *separate-channel* mic+system **today**, Approach A (BlackHole+Aggregate) is the proven path. With taps you'd capture system audio via AudioTee and the mic via a normal `sounddevice` input, then keep them as two logical channels yourself. There is an `AudioTee.js` Node wrapper (EventEmitter) if a JS/TS frontend needs the same stream [31].

## iOS — know the hard limits up front

- **No third-party capture of other apps' or call audio.** iOS sandboxing forbids it. A third-party app gets **mic only** [27].
- **ReplayKit** records only *your own app's* audio, not the system or other apps.
- **iOS 18.1 native call recording** is **first-party (Apple Phone app) and region-locked** [28] — not something a third-party library can rely on.
- Practical DIY iPhone pipeline = **mic/room capture**, or **relay audio to a Mac** that does the real capture. Set expectations accordingly; don't promise system-audio capture on iOS.

## check_requirements pattern (progressive disclosure + DI)

Per the project's UX rules: be ready out of the box, but when a backend's prerequisites are missing, **detect and guide dynamically** rather than failing cryptically. Expose `backend=` as a keyword-only argument (DI) defaulting to the proven path.

```python
def check_requirements(*, backend: str = "blackhole") -> list[str]:
    """Return human-readable, actionable setup steps for missing prerequisites.

    Empty list ⇒ ready to capture.
    """
    problems: list[str] = []
    import shutil
    if backend == "blackhole":
        import sounddevice as sd
        names = " ".join(d["name"].lower() for d in sd.query_devices())
        if "blackhole" not in names:
            problems.append(
                "BlackHole not found. Install: `brew install blackhole-2ch` "
                "(https://github.com/ExistentialAudio/BlackHole)."
            )
        if "aggregate" not in names:
            problems.append(
                "No Aggregate Device. Open Audio MIDI Setup → create an Aggregate "
                "Device = your mic + BlackHole 2ch (same sample rate). Also create a "
                "Multi-Output Device (real output + BlackHole) and select it as System "
                "Sound Output so you still hear audio while capturing."
            )
    elif backend == "audiotee":
        if shutil.which("audiotee") is None:
            problems.append(
                "AudioTee CLI not found. Build/install from "
                "https://github.com/makeusabrew/audiotee and ensure it's on PATH. "
                "Grant Screen Recording permission in System Settings → Privacy & Security."
            )
    return problems
```

CLI/HTTP/UI wrappers around these functions belong to the global **python-dispatching** skill (`argh`); persisting recorded audio/transcripts belongs to **python-storage** (dol stores); streaming generator hygiene to **python-iterables**.

## Pitfalls (call these out in review)

1. **Mixing channels too early** — destroys the free "Me"/"Them" signal. Slice, don't sum.
2. **Sample-rate / clock mismatch** in the Aggregate — pin built-in output as clock, Drift Correction on the rest [8].
3. **Driving ScreenCaptureKit via PyObjC** — broken (`-3805`); shell out to Swift [32].
4. **Forgetting the Multi-Output Device** — set BlackHole alone as output and *you* go deaf during the meeting. Always pair with a Multi-Output so you still hear.
5. **Hardcoding device indices** — they reorder when devices connect/disconnect. Resolve by name substring at runtime (`find_device`).
6. **Promising iOS system/call capture** — not possible for third parties; mic-only.

## References

- `references/from-research-reports.md` — the curated capture passages from the DIY and GD reports with `[n]` citations and URLs.
- `references/key-links.md` — the essential repos/docs (BlackHole, Apple Core Audio taps, AudioTee, PyObjC issue #647, sounddevice).
