# Key links — macOS audio capture

The repos/docs worth opening when implementing or debugging capture.

## Virtual loopback driver (Approach A)
- **BlackHole** — https://github.com/ExistentialAudio/BlackHole
  GPL-3.0 virtual audio loopback driver (2ch/16ch/64ch). `brew install blackhole-2ch`.
  README covers Multi-Output + Aggregate setup and the clock/Drift-Correction rules.
- **BlackHole + Python (Medium, Mehdi Samadi)** —
  https://medium.com/@mehsamadi/how-to-record-mac-system-audio-using-python-and-blackhole-a45d06eaad0f
  End-to-end walkthrough of recording system audio in Python via BlackHole.

## Core Audio taps (Approach B, macOS 14.2+)
- **Apple — Capturing system audio with Core Audio taps** —
  https://developer.apple.com/documentation/CoreAudio/capturing-system-audio-with-core-audio-taps
  The first-party API (`AudioHardwareCreateProcessTap`); pre-mixer capture; permissions.
- **AudioTee (makeusabrew/audiotee)** — https://github.com/makeusabrew/audiotee
  Open-source Swift CLI that streams system audio as raw PCM to stdout. Shell out and
  read stdout from Python. Companion writeup:
  https://stronglytyped.uk/articles/audiotee-capture-system-audio-output-macos
  (`AudioTee.js` Node/EventEmitter wrapper exists for JS/TS frontends.)

## What NOT to do
- **PyObjC issue #647** — https://github.com/ronaldoussoren/pyobjc/issues/647
  Evidence that driving ScreenCaptureKit from Python via PyObjC is broken
  (`SCStreamErrorDomain -3805`, callback never fires). Shell out to Swift instead.

## Python capture libraries
- **python-sounddevice** — https://python-sounddevice.readthedocs.io/
  PortAudio bindings; `InputStream`, `query_devices()`, `mapping=` channel selection,
  numpy frames×channels blocks. Default backend for this project.
- **soundcard** — https://github.com/bastibe/SoundCard
  Explicit channel-map recording (`record(..., channels=[0,1,2,3])`).
- **PyAudio** — https://people.csail.mit.edu/hubert/pyaudio/
  Lower-level PortAudio; what the existing POC uses (`channels=N` on the aggregate).
- **ffmpeg avfoundation** — https://ffmpeg.org/ffmpeg-devices.html#avfoundation
  `ffmpeg -f avfoundation`; reads the aggregate but cannot grab system audio on its own
  (needs BlackHole as the source).

## Production references (from the GD report)
- **Meetily** — local-first meeting assistant; dual-VAD "Me"/"Them" channel split
  (mic vs system). Tracked in issue #337.
- **ownscribe** — macOS CLI using Core Audio taps for system audio + optional mic,
  feeding PyAnnote + WhisperX.
