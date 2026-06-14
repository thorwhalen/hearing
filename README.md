# hearing

Pluggable meeting transcription & context-connected AI agents — batch today, live next.

`hearing` captures, transcribes, and reasons over meeting audio as four small,
**swappable** concerns wired by composition, not baked together:

```
capture ──audio──▶ STT ──segments──▶ diarization ──labeled──▶ agents
(mic + system,     (local or          (who spoke              (summaries, actions,
 separate channels) cloud, pluggable)  when / "me vs them")     live notes, research)
```

The one-liner just works; everything else is an optional keyword argument.

```python
from hearing import transcribe
transcript = transcribe("meeting.wav")     # -> Transcript (list of segments)
print(transcript.formatted())
```

## Install

```bash
pip install hearing                 # core: data model, channel split, CLI
pip install 'hearing[whisper]'      # + default local STT engine (faster-whisper)
pip install 'hearing[agents]'       # + Claude-backed agent layer
pip install 'hearing[all]'          # whisper + agents
pip install 'hearing[diarize]'      # + pyannote (separate individual remote speakers)
```

## What works today (the batch milestone)

Give it a recording and get back a **speaker-labelled transcript** plus optional
**AI meeting notes**. If the file has the mic on one channel and the system audio
(everyone else) on another, you get "me vs them" labelling *for free* — no
diarization model, no voice enrollment — because the channel itself tells you
who is local.

```bash
hearing transcribe meeting.wav                      # diarized transcript to stdout
hearing transcribe meeting.wav --model small --out notes.json
hearing summarize  meeting.wav                      # transcribe + AI notes (Claude)
hearing summarize  meeting.wav --agent extractive   # offline, no API key needed
hearing info                                        # what's installed / available
```

Example transcript + Claude summary (from `examples/demo_meeting.py`, which
synthesizes a two-speaker meeting with macOS `say` — no mic needed):

```
[00:00:00] me:   Hi everyone, thanks for joining the planning sync. I'll own the
                 API design and send a draft by Friday. What is our deadline...
[00:00:08] them: Thanks. The launch deadline is the end of the month. Let's
                 decide on the database. I think we should use Postgres...

## Decisions
- PostgreSQL selected as the database for the project.
## Action items
- [me] Own the API design and send a draft by Friday.
## Open questions / follow-ups
- Confirm the exact end-of-month launch deadline.
```

### Composition (dependency injection)

Every concern is a `typing.Protocol`; swap one by changing a single argument.

```python
from hearing import transcribe
from hearing.stt import FasterWhisperSTT
from hearing.diarize import ChannelTrickDiarizer, PyannoteDiarizer
from hearing.agents import ClaudeAgent, ExtractiveAgent

transcribe(
    "meeting.wav",
    engine=FasterWhisperSTT(model_size="small"),  # or a cloud engine you write
    diarizer=PyannoteDiarizer(),                   # upgrade from the channel trick
    agent=ClaudeAgent(context="prior meeting takeaways..."),  # or ExtractiveAgent()
)
```

The shared data spine is `hearing.types.TranscriptSegment` — a frozen, standoff
interval annotation (time is **integer milliseconds**, never float). See
`hearing/interfaces.py` for the four facade Protocols (`CaptureSource`,
`STTEngine`, `Diarizer`, `AgentConsumer`).

## Capturing the audio (macOS)

`hearing` reads multi-channel audio files and splits the channels. To get a
recording with mic on one channel and system audio (the other participants) on
another, use **BlackHole + an Aggregate Device** or **Core Audio taps** — the
mechanics, the channel layout, and the iOS limits are documented in the
`hearing-audio-capture` agent skill (`.claude/skills/hearing-audio-capture/`).
Live device capture is the next milestone; today you bring a recording.

## Not yet (designed, on the roadmap)

- **Live / streaming** path (VAD-based utterance finalization, low-latency
  in-meeting agent feedback). The architecture is additive — see
  `hearing-live-pipeline`. Tracked in [`misc/docs/ROADMAP.md`](misc/docs/ROADMAP.md).
- **TypeScript frontend** (schema-driven transcript viewer + copilot overlay
  with zodal/acture) — see `hearing-frontend`.

## Architecture & development

This project is developed with a suite of agent **skills** under
`.claude/skills/` — start with the `hearing` skill (the project-manager /
orchestrator), which routes to the per-concern skills (`hearing-architecture`,
`hearing-audio-capture`, `hearing-stt`, `hearing-diarization`, `hearing-agents`,
`hearing-live-pipeline`, `hearing-frontend`). The two research reports the design
is grounded in are in `misc/docs/`.

## License

MIT
