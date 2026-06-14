"""Transcript persistence via key-value stores (python-storage / ``dol``).

A transcript is standoff annotation data — persist the *whole* transcript (not
just a rolling window) so post-meeting agents see everything (see the
``hearing-agents`` and ``annotation-systems`` skills). :class:`MeetingStore`
saves/loads transcripts as JSON keyed by meeting id, over any
``MutableMapping`` — a plain dict (tests), a ``dol`` store (e.g. ``TextFiles``),
or the dependency-free filesystem fallback here.
"""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from pathlib import Path
from typing import Iterator, Optional, Union

from hearing.types import Channel, TimeSpan, Transcript, TranscriptSegment


def transcript_to_json(transcript: Transcript) -> str:
    """Serialize a :class:`Transcript` to a JSON string (round-trippable)."""
    return json.dumps(
        {
            "sample_rate": transcript.sample_rate,
            "meta": dict(transcript.meta),
            "segments": transcript.to_jsonable(),
        },
        indent=2,
    )


def transcript_from_json(s: Union[str, bytes]) -> Transcript:
    """Reconstruct a :class:`Transcript` from :func:`transcript_to_json` output."""
    if isinstance(s, bytes):
        s = s.decode("utf-8")
    d = json.loads(s)
    segments = tuple(
        TranscriptSegment(
            text=x["text"],
            span=TimeSpan(int(x["start_ms"]), int(x["end_ms"])),
            channel=Channel(x.get("channel", "mixed")),
            speaker=x.get("speaker"),
            confidence=x.get("confidence"),
        )
        for x in d.get("segments", [])
    )
    return Transcript(segments, sample_rate=d.get("sample_rate"), meta=dict(d.get("meta", {})))


class _FileTextStore(MutableMapping):
    """A tiny ``dol``-less filesystem text store (one file per key in a dir)."""

    def __init__(self, root: Union[str, Path]):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / key

    def __getitem__(self, key: str) -> str:
        p = self._path(key)
        if not p.exists():
            raise KeyError(key)
        return p.read_text(encoding="utf-8")

    def __setitem__(self, key: str, value) -> None:
        self._path(key).write_text(
            value if isinstance(value, str) else value.decode("utf-8"), encoding="utf-8"
        )

    def __delitem__(self, key: str) -> None:
        p = self._path(key)
        if not p.exists():
            raise KeyError(key)
        p.unlink()

    def __iter__(self) -> Iterator[str]:
        return (p.name for p in self.root.iterdir() if p.is_file())

    def __len__(self) -> int:
        return sum(1 for _ in iter(self))


def get_store(path: Optional[Union[str, Path]] = None) -> MutableMapping:
    """Return a string-valued ``MutableMapping`` for transcripts.

    ``None`` -> an in-memory dict. A path -> a ``dol.TextFiles`` store if ``dol``
    is installed (``pip install 'hearing[storage]'``), else the dependency-free
    :class:`_FileTextStore` over that directory.
    """
    if path is None:
        return {}
    try:
        from dol import TextFiles

        return TextFiles(str(path))
    except Exception:  # dol absent or incompatible — fall back to the local store
        return _FileTextStore(path)


class MeetingStore:
    """Save/load transcripts keyed by meeting id, over any text MutableMapping.

    >>> store = MeetingStore({})                       # in-memory
    >>> from hearing.types import Transcript, TranscriptSegment, TimeSpan
    >>> _ = store.save("m1", Transcript([TranscriptSegment("hi", TimeSpan(0, 500))]))
    >>> store.load("m1").text
    'hi'
    >>> list(store)
    ['m1']
    """

    suffix = ".transcript.json"

    def __init__(self, store: Optional[Union[MutableMapping, str, Path]] = None):
        if store is None or isinstance(store, (str, Path)):
            self.store: MutableMapping = get_store(store)
        else:
            self.store = store

    def _key(self, meeting_id: str) -> str:
        return f"{meeting_id}{self.suffix}"

    def save(self, meeting_id: str, transcript: Transcript) -> str:
        """Persist ``transcript`` under ``meeting_id``; return the storage key."""
        key = self._key(meeting_id)
        self.store[key] = transcript_to_json(transcript)
        return key

    def load(self, meeting_id: str) -> Transcript:
        """Load the transcript stored under ``meeting_id``."""
        return transcript_from_json(self.store[self._key(meeting_id)])

    def meeting_ids(self) -> list[str]:
        """Sorted ids of stored meetings."""
        n = len(self.suffix)
        return sorted(k[:-n] for k in self.store if str(k).endswith(self.suffix))

    def __iter__(self) -> Iterator[str]:
        return iter(self.meeting_ids())

    def __len__(self) -> int:
        return len(self.meeting_ids())

    def __contains__(self, meeting_id: str) -> bool:
        return self._key(meeting_id) in self.store
