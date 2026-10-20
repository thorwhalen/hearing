# hearing.diarize

Diarization and speaker labelling for the hearing pipeline.

Two ideas, one interface ([`Diarizer`](hearing.interfaces.html.md#hearing.interfaces.Diarizer)):

1. **The channel trick (default, free).** Because capture keeps the mic and the
   system audio on *separate channels*, we already know who is local: the
   `MIC` channel is “me”, the `SYSTEM` channel is the remote participants.
   [`ChannelTrickDiarizer`](#hearing.diarize.ChannelTrickDiarizer) just maps channel -> speaker. No model, no
   > audio, no error from overlap on the local side. This beats voice
   > fingerprinting for the “is it me?” question.
2. **Real diarization (the upgrade).** To separate *multiple remote* speakers
   you need acoustic diarization. [`PyannoteDiarizer`](#hearing.diarize.PyannoteDiarizer) wraps
   `pyannote.audio` and runs only on the system channel. A diarized transcript
   is standoff interval annotation with a speaker tier — see the
   `annotation-systems` skill.

See the `hearing-diarization` skill for the full landscape (pyannote vs NeMo
vs WhisperX vs SpeechBrain, DER numbers, enrollment).

### Classes

| [`ChannelTrickDiarizer`](#hearing.diarize.ChannelTrickDiarizer)([me_label, them_label])   | Label speakers from the capture channel — the free, reliable default.   |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`PyannoteDiarizer`](#hearing.diarize.PyannoteDiarizer)([model, hf_token, ...])       | Acoustic diarization via `pyannote.audio` (the upgrade path).           |

### *class* hearing.diarize.ChannelTrickDiarizer(me_label='me', them_label='them')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Label speakers from the capture channel — the free, reliable default.

`MIC` -> `me_label` (the local user), `SYSTEM` -> `them_label` (a
remote participant). Segments already carrying a speaker, or coming from a
`MIXED` channel, are passed through unchanged (there is nothing to infer).

This is the architecture’s default diarizer whenever channel information is
present. To distinguish *individual* remote speakers, compose this with (or
replace it by) [`PyannoteDiarizer`](#hearing.diarize.PyannoteDiarizer).

#### assign_speakers(segments, , audio=None, sample_rate=None)

Yield segments with `.speaker` set from their `.channel`.

* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)]

### *class* hearing.diarize.PyannoteDiarizer(model='pyannote/speaker-diarization-3.1', hf_token=None, speaker_prefix='spk_', me_label='me', pipeline=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Acoustic diarization via `pyannote.audio` (the upgrade path).

Runs the pretrained pipeline over the audio, then assigns each segment the
speaker whose diarized turn overlaps it most. It runs on the *system* channel
only: `MIC` segments are labelled `me_label` for free (the channel trick),
and the model is not run at all when there is nothing left to diarize. Pass
the system-channel audio as `audio` (`transcribe` does).

Requires `pip install hearing[diarize]` and a Hugging Face token with the
pyannote model licenses accepted. The import is guarded so the package works
without it. `pipeline` is the seam: any callable
`({"waveform", "sample_rate"}) -> annotation` (an object with
`itertracks(yield_label=True)`) replaces the pretrained model, which is how
this is tested without a model or a token.

#### assign_speakers(segments, , audio=None, sample_rate=None)

Yield segments labelled: mic -> me, others -> most-overlapping diarized speaker.

* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`TranscriptSegment`](hearing.types.html.md#hearing.types.TranscriptSegment)]
