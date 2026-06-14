"""Tests for the shared data model (the TranscriptSegment spine)."""

from hearing.types import (
    ME,
    THEM,
    Channel,
    TimeSpan,
    Transcript,
    TranscriptSegment,
    merge_segments,
)


def test_timespan_duration_and_from_seconds():
    assert TimeSpan(0, 1500).duration_ms == 1500
    assert TimeSpan.from_seconds(1.2, 3.4) == TimeSpan(1200, 3400)


def test_segment_enrich_by_copy_is_immutable():
    seg = TranscriptSegment("hi", TimeSpan(0, 500))
    labelled = seg.with_speaker(ME).with_channel(Channel.MIC)
    assert labelled.speaker == ME
    assert labelled.channel is Channel.MIC
    # original untouched (frozen / enrich-by-copy)
    assert seg.speaker is None
    assert seg.channel is Channel.MIXED


def test_transcript_text_speakers_and_jsonable():
    t = Transcript(
        [
            TranscriptSegment("hello", TimeSpan(0, 1000), Channel.MIC, ME),
            TranscriptSegment("hi there", TimeSpan(1000, 2000), Channel.SYSTEM, THEM),
        ]
    )
    assert t.text == "hello hi there"
    assert t.duration_ms == 2000
    assert t.speakers == {ME, THEM}
    js = t.to_jsonable()
    assert js[0]["channel"] == "mic" and js[0]["speaker"] == "me"
    assert js[1]["start_ms"] == 1000


def test_transcript_accepts_any_sequence():
    # a list is normalized to a tuple internally
    t = Transcript([TranscriptSegment("x", TimeSpan(0, 10))])
    assert isinstance(t.segments, tuple) and len(t) == 1


def test_formatted_includes_speaker_and_clock():
    t = Transcript([TranscriptSegment("yo", TimeSpan(65_000, 66_000), speaker=ME)])
    line = t.formatted()
    assert "00:01:05" in line and "me:" in line and "yo" in line


def test_merge_segments_orders_by_start():
    a = [TranscriptSegment("second", TimeSpan(1000, 2000))]
    b = [TranscriptSegment("first", TimeSpan(0, 1000))]
    merged = merge_segments(a, b)
    assert [s.text for s in merged] == ["first", "second"]
