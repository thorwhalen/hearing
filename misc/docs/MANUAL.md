# hearing — user manual

How to operate **hearing**, the meeting transcription + AI-copilot app. This file
is the source of truth; the same content is shown in the app under **Help / ⌘?**.

---

## 1. The 30-second version

- **Just record:** click the big **● Record** button. It captures your
  microphone and, when you press **■ Stop**, transcribes it. Nothing is lost.
- **Already have a file?** drop it on the page (or use **Choose File**).
- **Cheap by default:** the defaults use the **local** speech-to-text engine
  (free, on-device, no API key) with **AI notes off** and **live off**. Turn the
  paid/AI features on in **Settings (⚙)** when you want them. (Web search is a
  CLI option — `summarize --web-search`.)

> **Important — mic vs. "the other people".** A *web browser can only record your
> microphone*, not the other participants' audio coming out of your speakers. So
> the in-app Record button gives you a **mic-only** ("me") recording. To capture
> **both sides** (the "me vs them" channel split that makes this project special)
> you record the meeting with the native path — see §5.

---

## 2. The buttons

| Control | What it does | Cost |
|---|---|---|
| **● Record** | Start capturing your microphone. | free (local STT) |
| **■ Stop** | Stop and transcribe the recording. | free (local STT) |
| **Choose File** / drag-drop | Transcribe an existing audio file (any format; mp3/m4a/webm are converted automatically). | free (local STT) |
| **AI notes** ☐ | Also produce a summary / decisions / action items. | uses Claude (needs a key) |
| **Live stream** ☐ | Show transcript segments as they finalize instead of all-at-once. | free (local STT) |
| **Search** | Filter the transcript. | free |
| **⌘K** | Command palette (export transcript as md/srt/json, etc.). | free |
| **⚙ Settings** | Change engine, model, what's on by default, and the API base URL. | — |
| **Help / ⌘?** | This manual. | — |

While recording, a red **● recording…** indicator shows, along with the options
that will be applied when you stop (engine, AI notes, live) — change them in
Settings before recording if you want different ones.

---

## 3. Settings (and what each costs)

Open **⚙ Settings**. Everything persists in your browser. Defaults are the
**least expensive** option — nothing leaves your machine and no API is called.

| Setting | Default | Notes |
|---|---|---|
| **STT engine** | `whisper` (local) | `whisper` = on-device faster-whisper, **free**. `openai` = cloud, needs `OPENAI_API_KEY` on the backend + `hearing[openai]`. |
| **Whisper model** | `base` | bigger = more accurate, slower (`tiny`→`large-v3`). Local engine only. |
| **AI notes** | off | Claude summary/actions/decisions. Needs `ANTHROPIC_API_KEY` on the backend. |
| **Live stream** | off | Stream finalized segments as they arrive. |
| **API base URL** | (same origin) | Where the UI sends requests. **Leave blank** when the UI and backend are on the same host. Set to `http://localhost:8000` when the UI is served from the server but you want it to use **your local** backend (see §4). |

> Web search (pulling Wikipedia fact context into the notes, key-free) is
> currently a **CLI** option: `hearing summarize meeting.wav --web-search`.

---

## 4. Running it — and the "server hosts it, my Mac runs it" mode

`hearing` has two parts: a **backend** (Python, does the heavy lifting — STT,
agents) and a **frontend** (this web UI). The frontend talks to the backend over
HTTP, so they don't have to be on the same machine.

### A. All local (simplest)
```bash
pip install 'hearing[whisper,agents,http]'
hearing serve                 # backend API on http://127.0.0.1:8000
cd frontend && npm install && npm run dev   # UI on http://localhost:5173
```
Open the UI; leave **API base URL** blank (the dev server proxies `/api` to the
backend). Everything runs on your Mac.

### B. UI on the server, compute on your Mac  ← the recommended setup
The web UI is hosted at **thorwhalen.com/hearing** (so you can open it from any
browser, and only you can see it). But the **heavy processing runs on your own
machine** — the server stores and runs *nothing* expensive.

How it works: the server only serves the static UI. In **⚙ Settings**, set
**API base URL = `http://localhost:8000`**. Then run the backend locally:
```bash
hearing serve --port 8000
```
Now the page (served from the server) sends its `/api` calls to **your laptop's**
`hearing serve`. STT, models, your audio, and any API keys stay on your Mac;
the server is just delivering the page. (Browsers permit an HTTPS page to call
`http://localhost`, and the local backend allows the cross-origin call.)

This is exactly "I get the code when I click it, and it runs on my local
resources" — the server is a delivery mechanism, not a compute host.

---

## 5. Capturing both sides of a meeting (the "me vs them" channel split)

Browsers can't record system audio, so to capture the *other* participants you
record at the OS level and feed `hearing` a multi-channel file:

1. Install a virtual audio device — **BlackHole** (`brew install blackhole-2ch`)
   — and make an **Aggregate Device** (mic + BlackHole) in *Audio MIDI Setup* so
   your mic lands on one channel and system audio on another. (Full steps: the
   `hearing-audio-capture` skill / `misc/docs/` reports.)
2. Record that device to a file (any recorder, or a future `hearing` device
   capture), then:
   ```bash
   hearing transcribe meeting.wav            # mic = "me", system = "them", for free
   hearing summarize  meeting.wav            # + AI notes
   ```
`hearing` splits the channels and labels **me** vs **them** automatically — no
diarization model needed for "is it me?".

---

## 6. Command-line reference

```bash
hearing transcribe FILE [--engine whisper|openai] [--model base] [--save DIR] [--out notes.json]
hearing summarize  FILE [--agent auto|claude|extractive] [--context-dir DIR] [--retriever keyword|embedding] [--web-search]
hearing live       FILE              # stream finalized segments as they complete
hearing serve      [--port 8000]     # the HTTP API the web UI uses
hearing meetings   DIR [--show ID]   # list/print transcripts saved with --save
hearing info                         # what's installed / available
```

---

## 7. Troubleshooting

- **"start `hearing serve`" in the header / requests fail** → the backend isn't
  reachable. Run `hearing serve`, and check the **API base URL** in Settings.
- **No transcription / engine error** → install the local engine:
  `pip install 'hearing[whisper]'`. For the cloud engine: `hearing[openai]` +
  `OPENAI_API_KEY`.
- **AI notes empty / error** → needs `hearing[agents]` + `ANTHROPIC_API_KEY`, or
  switch the agent to the offline **extractive** mode.
- **Mic record does nothing** → grant the browser microphone permission.
- **Recorded audio won't transcribe** → the backend needs `ffmpeg` on PATH to
  decode browser (webm/opus) recordings; install it (`brew install ffmpeg`).
- **Only one speaker ("me") shows** → that's expected for a browser mic
  recording; use the native channel-split path (§5) for me-vs-them.
