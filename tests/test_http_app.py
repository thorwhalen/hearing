"""Tests for the HTTP layer (FastAPI TestClient + an injected fake STT engine)."""

import io
import json

import numpy as np
import pytest

pytest.importorskip("fastapi")
soundfile = pytest.importorskip("soundfile")

from fastapi.testclient import TestClient  # noqa: E402

from hearing.http_app import create_app, transcript_to_payload  # noqa: E402
from hearing.types import ME, Channel, TimeSpan, Transcript, TranscriptSegment  # noqa: E402


class FakeSTT:
    """Deterministic engine: one segment per call, text encodes loudness."""

    def transcribe(self, audio, *, sample_rate, language=None):
        loud = float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
        return [TranscriptSegment(f"e={loud:.2f}", TimeSpan(0, 1000))]

    async def stream_transcribe(self, frames, *, sample_rate):  # pragma: no cover
        raise NotImplementedError
        yield


class FakeStreamingSTT:
    """Streaming engine: one finalized segment per VAD utterance."""

    def transcribe(self, audio, *, sample_rate, language=None):
        return [TranscriptSegment("x", TimeSpan(0, 500))]

    async def stream_transcribe(self, frames, *, sample_rate):
        from hearing.vad import segment_utterances

        async for utt, start_ms in segment_utterances(frames, sample_rate=sample_rate):
            yield TranscriptSegment(
                f"utt@{start_ms}", TimeSpan(start_ms, start_ms + len(utt) * 1000 // sample_rate), meta={"final": True}
            )


def _stereo_wav_bytes() -> bytes:
    sr = 16_000
    stereo = np.zeros((sr, 2), dtype="float32")
    stereo[:, 0] = 0.5  # mic = me (loud)
    stereo[:, 1] = 0.1  # system = them (quiet)
    buf = io.BytesIO()
    soundfile.write(buf, stereo, sr, format="WAV")
    return buf.getvalue()


def test_health():
    client = TestClient(create_app(engine=FakeSTT()))
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and "version" in body


def test_transcribe_endpoint_returns_frontend_shape():
    client = TestClient(create_app(engine=FakeSTT()))
    files = {"file": ("meeting.wav", _stereo_wav_bytes(), "audio/wav")}
    r = client.post("/api/transcribe", files=files, data={"title": "Sync"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["meeting"]["title"] == "Sync"
    assert body["meeting"]["segmentCount"] == 2
    sides = {s["side"] for s in body["segments"]}
    assert sides == {"me", "them"}  # channel split -> me/them lanes
    fields = set(body["segments"][0])
    assert {"id", "meetingId", "speaker", "side", "startMs", "endMs", "text", "isFinal"} <= fields


def test_transcribe_with_summary_uses_injected_agent():
    from hearing.agents import ExtractiveAgent

    client = TestClient(create_app(engine=FakeSTT(), agent=ExtractiveAgent()))
    files = {"file": ("meeting.wav", _stereo_wav_bytes(), "audio/wav")}
    r = client.post("/api/transcribe", files=files, data={"summarize": "true"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "summary" in body and "Summary" in body["summary"]


def test_transcribe_stream_emits_ndjson_segments():
    client = TestClient(create_app(engine=FakeStreamingSTT()))
    files = {"file": ("meeting.wav", _stereo_wav_bytes(), "audio/wav")}
    with client.stream("POST", "/api/transcribe/stream", files=files) as r:
        assert r.status_code == 200
        msgs = [json.loads(line) for line in r.iter_lines() if line.strip()]
    types = [m["type"] for m in msgs]
    assert types[0] == "meeting" and types[-1] == "done"
    segs = [m["segment"] for m in msgs if m["type"] == "segment"]
    assert len(segs) >= 2  # mic + system channels each finalize an utterance
    assert {s["side"] for s in segs} == {"me", "them"}
    assert all(s["isFinal"] for s in segs)


def test_transcript_to_payload_unit():
    t = Transcript([TranscriptSegment("hi", TimeSpan(0, 1000), Channel.MIC, ME)])
    payload = transcript_to_payload(t, meeting_id="m1", title="T")
    seg = payload["segments"][0]
    assert seg["side"] == "me" and seg["meetingId"] == "m1" and seg["isFinal"] is True
    assert payload["meeting"]["durationMs"] == 1000
