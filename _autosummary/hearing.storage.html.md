# hearing.storage

Transcript persistence via key-value stores (python-storage / `dol`).

A transcript is standoff annotation data — persist the *whole* transcript (not
just a rolling window) so post-meeting agents see everything (see the
`hearing-agents` and `annotation-systems` skills). [`MeetingStore`](#hearing.storage.MeetingStore)
saves/loads transcripts as JSON keyed by meeting id, over any
`MutableMapping` — a plain dict (tests), a `dol` store (e.g. `TextFiles`),
or the dependency-free filesystem fallback here. Meeting audio, being large binary
blobs, goes to a *separate* bytes store (`MeetingStore(..., recordings=...)`).

### Functions

| [`get_bytes_store`](#hearing.storage.get_bytes_store)([path])        | Return a bytes-valued `MutableMapping` (for recordings).                                                      |
|---------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| [`get_store`](#hearing.storage.get_store)([path])              | Return a string-valued `MutableMapping` for transcripts.                                                      |
| [`transcript_from_json`](#hearing.storage.transcript_from_json)(s)        | Reconstruct a `Transcript` from [`transcript_to_json()`](#hearing.storage.transcript_to_json) output. |
| [`transcript_to_json`](#hearing.storage.transcript_to_json)(transcript) | Serialize a `Transcript` to a JSON string (round-trippable).                                                  |

### Classes

| [`MeetingStore`](#hearing.storage.MeetingStore)([store, recordings])   | Save/load transcripts keyed by meeting id, over any text MutableMapping.   |
|--------------------------------------------------------------------------------------|----------------------------------------------------------------------------|

### *class* hearing.storage.MeetingStore(store=None, , recordings=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Save/load transcripts keyed by meeting id, over any text MutableMapping.

```pycon
>>> store = MeetingStore({})                       # in-memory
>>> from hearing.types import Transcript, TranscriptSegment, TimeSpan
>>> _ = store.save("m1", Transcript([TranscriptSegment("hi", TimeSpan(0, 500))]))
>>> store.load("m1").text
'hi'
>>> list(store)
['m1']
```

Recordings (the meeting audio) live in a separate bytes store, given as
`recordings` (a `MutableMapping` or a directory), under `<meeting id>` plus
the audio’s extension when the id does not already end with it:

```pycon
>>> store = MeetingStore({}, recordings={})
>>> store.save_recording("m1", b"RIFF...", ext=".wav")
'm1.wav'
>>> store.recording("m1")
b'RIFF...'
```

#### load(meeting_id)

Load the transcript stored under `meeting_id`.

* **Return type:**
  [`Transcript`](hearing.types.html.md#hearing.types.Transcript)

#### meeting_ids()

Sorted ids of stored meetings.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

#### recording(meeting_id)

The meeting’s audio bytes, as stored by [`save_recording()`](#hearing.storage.MeetingStore.save_recording).

* **Return type:**
  [`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes)

#### recording_key(meeting_id)

The key of the meeting’s recording (`KeyError` if there is none).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### save(meeting_id, transcript)

Persist `transcript` under `meeting_id`; return the storage key.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### save_recording(meeting_id, audio, , ext='')

Store the meeting’s audio bytes; return the key (`<id><ext>`).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### hearing.storage.get_bytes_store(path=None)

Return a bytes-valued `MutableMapping` (for recordings).

`None` -> an in-memory dict; a path -> a `dol.Files` store if `dol` is
installed, else the dependency-free `_FileBytesStore` over that directory.

* **Return type:**
  [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)

### hearing.storage.get_store(path=None)

Return a string-valued `MutableMapping` for transcripts.

`None` -> an in-memory dict. A path -> a `dol.TextFiles` store if `dol`
is installed (`pip install 'hearing[storage]'`), else the dependency-free
`_FileTextStore` over that directory.

* **Return type:**
  [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)

### hearing.storage.transcript_from_json(s)

Reconstruct a `Transcript` from [`transcript_to_json()`](#hearing.storage.transcript_to_json) output.

* **Return type:**
  [`Transcript`](hearing.types.html.md#hearing.types.Transcript)

### hearing.storage.transcript_to_json(transcript)

Serialize a `Transcript` to a JSON string (round-trippable).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
