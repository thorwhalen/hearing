"""Tests for the HTTP layer (FastAPI TestClient + an injected fake STT engine)."""

import io

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


def test_transcript_to_payload_unit():
    t = Transcript([TranscriptSegment("hi", TimeSpan(0, 1000), Channel.MIC, ME)])
    payload = transcript_to_payload(t, meeting_id="m1", title="T")
    seg = payload["segments"][0]
    assert seg["side"] == "me" and seg["meetingId"] == "m1" and seg["isFinal"] is True
    assert payload["meeting"]["durationMs"] == 1000
