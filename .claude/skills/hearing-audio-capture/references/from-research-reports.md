# Audio capture — extracted research (June 2026)

Curated slices from the two project reports. `[n]` markers match the DIY report's
REFERENCES section; the matching URLs are appended at the bottom. `[GD]` marks the
AI-agents ("GD") report.

---

## From the DIY pipeline report — "Concern 1: Audio capture on macOS (the hard part)"
(DIY report, lines 82–108)

The challenge is capturing **system audio** (other participants coming out of your
speakers), not just the mic. As of 2025–2026 there are two robust approaches.

### Approach A — BlackHole + Aggregate Device (proven, today)
**BlackHole** (`ExistentialAudio/BlackHole`, GPL-3.0) is a virtual audio loopback
driver, available in 2ch / 16ch / 64ch variants (`brew install blackhole-2ch`) [8].
macOS doesn't let apps capture output audio directly, so you loop it back. Steps:
1. Install BlackHole.
2. In **Audio MIDI Setup**, create a **Multi-Output Device** = your real output +
   BlackHole (so you still hear audio while it's captured). The Built-in Output must be
   the top/clock device; enable Drift Correction on the others [8].
3. Set that Multi-Output Device as system Sound Output → system audio now flows into
   BlackHole.
4. Create an **Aggregate Device** = microphone + BlackHole.
5. In Python, open the Aggregate Device and read all channels.

Crucially, **an aggregate device does not mix** — mic and system audio land on separate
channels [8][30]. So you can build an aggregate where mic = channels 1–2 and
BlackHole/system = channels 3–4, record all channels, and slice them apart. All devices
in an aggregate must share a sample rate (don't use AirPods as clock) [8].

### Approach B — Core Audio taps via AudioTee (native, macOS 14.2+)
macOS 14.2 (Dec 2023) introduced **Core Audio taps** (`AudioHardwareCreateProcessTap`).
Apple's docs: "Use a Core Audio tap to capture outgoing audio from a process or group of
processes" [9]. Taps capture pre-mixer audio (clean regardless of volume) and require
Screen Recording / system-audio permission. **AudioTee** (`makeusabrew/audiotee`) is an
open-source Swift CLI that streams system audio as raw PCM to stdout — ideal for piping
into Python [31]. There's a Node wrapper (**AudioTee.js**) with an EventEmitter
interface; the author's stated use case is "pipe system audio to a NodeJS process which
in turn relays it to a real-time ASR service" [31]. Note: combined mic+system in one
AudioTee binary is not yet shipped (only the author's private fork), so for
separate-channel mic+system *today*, the BlackHole+Aggregate route is the proven path.

**ScreenCaptureKit** (macOS 12.3+, mic capture added in 15+) also captures system audio,
but driving it from Python via PyObjC is effectively broken — PyObjC issue #647 (macOS
15, PyObjC 11.0) reports `SCStreamErrorDomain Code=-3805` (connectionInvalid) or the
audio callback never firing [32]. So shell out to a Swift binary rather than driving SCK
directly from Python.

### Python capture libraries
- **sounddevice** (PortAudio): open an InputStream on the Aggregate Device, read all
  channels as a NumPy frames×channels array, slice columns (`data[:, 0:2]` = mic,
  `data[:, 2:4]` = system). Supports a `mapping` argument to select channels.
- **soundcard**: supports an explicit channel map, e.g.
  `record(samplerate=48000, channels=[0,1,2,3], ...)`.
- **PyAudio**: lower-level, works with `channels=N` on the aggregate.
- **ffmpeg `-f avfoundation`**: can capture the aggregate device; note avfoundation
  alone won't grab system audio (it needs BlackHole as the source).

### iOS capture
iOS forbids third-party capture of other apps'/call audio. Mic-only for third parties;
**ReplayKit** records only your *own* app's audio; iOS 18.1 native call recording is
first-party and region-locked [27][28]. A DIY iPhone pipeline realistically means
mic/room capture or relaying audio to a Mac.

### Summary framing (DIY report, line 8)
> The hard part on macOS is **system-audio capture**: use BlackHole + an Aggregate
> Device (proven) or Core Audio taps via AudioTee (native, macOS 14.2+) [8][9]. Keep mic
> and system audio as separate channels — that channel split is itself the elegant way
> to know when *you* are speaking.

---

## From the GD report — local-first architectural profiles
(GD report, lines 86–88)

- **Meetily**: self-hosted local-first meeting assistant; captures system-level audio
  directly from macOS/Windows/Linux. To address speaker attribution, its roadmap focuses
  on **dual Voice Activity Detection (VAD) to process microphone input and system output
  as separate channels**, labeling segments as **"Me" (local microphone)** or **"Them"
  (system audio)** in real time. (This is the channel-split "me vs them" trick in
  production.)
- **ownscribe**: macOS native CLI using PyAnnote + WhisperX. Rather than virtual audio
  drivers, it **leverages macOS Core Audio Taps (introduced in macOS 14.2) to capture
  system audio directly from the speaker output, optionally mixing in local microphone
  input** — the production example of Approach B.

(Meetily's "Me"/"Them" dual-VAD is also tracked in its issue #337.)

---

## Reference URLs (matching the [n] markers above)

- [8] BlackHole — GitHub, ExistentialAudio: https://github.com/ExistentialAudio/BlackHole
- [9] Capturing system audio with Core Audio taps — Apple Developer:
  https://developer.apple.com/documentation/CoreAudio/capturing-system-audio-with-core-audio-taps
- [27] Best AI Note Taking Apps for iPhone 2026 — CFAI: https://cfai.io/tools/ai-note-taker-for-iphone/
- [28] How to record a phone call on iPhone — Soundcore:
  https://www.soundcore.com/blogs/voice-recorder/how-to-record-a-phone-call-on-iphone
- [30] How to Record Mac System Audio Using Python and BlackHole — Mehdi Samadi (Medium):
  https://medium.com/@mehsamadi/how-to-record-mac-system-audio-using-python-and-blackhole-a45d06eaad0f
- [31] AudioTee: capture system audio output on macOS — Strongly Typed:
  https://stronglytyped.uk/articles/audiotee-capture-system-audio-output-macos
- [32] Failed to Capture System Audio with ScreenCaptureKit on macOS 15 (Issue #647) — pyobjc GitHub:
  https://github.com/ronaldoussoren/pyobjc/issues/647
