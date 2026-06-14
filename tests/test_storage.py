"""Tests for transcript persistence (MeetingStore + JSON round-trip)."""

from hearing.storage import (
    MeetingStore,
    get_store,
    transcript_from_json,
    transcript_to_json,
)
from hearing.types import ME, THEM, Channel, TimeSpan, Transcript, TranscriptSegment


def _meeting() -> Transcript:
    return Transcript(
        [
            TranscriptSegment("hello", TimeSpan(0, 1000), Channel.MIC, ME, confidence=0.9),
            TranscriptSegment("hi there", TimeSpan(1000, 2000), Channel.SYSTEM, THEM),
        ],
        sample_rate=16_000,
        meta={"source": "x.wav"},
    )


def test_transcript_json_round_trip():
    t = _meeting()
    back = transcript_from_json(transcript_to_json(t))
    assert back.text == t.text
    assert back.sample_rate == 16_000
    assert [s.channel for s in back] == [Channel.MIC, Channel.SYSTEM]
    assert [s.speaker for s in back] == [ME, THEM]
    assert back.segments[0].span == TimeSpan(0, 1000)


def test_meeting_store_in_memory_dict():
    store = MeetingStore({})
    key = store.save("m1", _meeting())
    assert key == "m1.transcript.json"
    assert "m1" in store and len(store) == 1
    assert store.load("m1").text == "hello hi there"
    assert list(store) == ["m1"]


def test_meeting_store_filesystem_fallback(tmp_path):
    store = MeetingStore(str(tmp_path))  # no dol needed: _FileTextStore fallback
    store.save("alpha", _meeting())
    store.save("beta", _meeting())
    assert sorted(store) == ["alpha", "beta"]
    # a fresh store over the same dir sees the persisted files
    reopened = MeetingStore(str(tmp_path))
    assert reopened.load("alpha").text == "hello hi there"


def test_get_store_none_is_dict():
    assert get_store(None) == {}
