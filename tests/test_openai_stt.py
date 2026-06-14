"""Tests for the OpenAI cloud STT engine (with an injected fake client)."""

import numpy as np
import pytest

from hearing.stt import FasterWhisperSTT, OpenAISTT, get_engine
from hearing.types import TimeSpan

pytest.importorskip("soundfile")  # OpenAISTT writes a temp wav


class _Seg:
    def __init__(self, start, end, text):
        self.start, self.end, self.text = start, end, text


class _Resp:
    def __init__(self, segments=None, text=""):
        self.segments = segments
        self.text = text


class _FakeClient:
    """Mimics ``openai.OpenAI`` enough for OpenAISTT (no network)."""

    def __init__(self, resp):
        self._resp = resp
        captured = {}
        self.captured = captured

        class _Transcriptions:
            def create(_self, **kw):
                captured.update(kw)
                return resp

        class _Audio:
            transcriptions = _Transcriptions()

        self.audio = _Audio()


def test_openai_stt_maps_verbose_json_segments():
    resp = _Resp(segments=[_Seg(0.0, 1.5, "hello"), _Seg(1.5, 3.0, "world")], text="hello world")
    engine = OpenAISTT(client=_FakeClient(resp))
    segs = engine.transcribe(np.ones(16_000, dtype="float32"), sample_rate=16_000)
    assert [s.text for s in segs] == ["hello", "world"]
    assert segs[0].span == TimeSpan(0, 1500) and segs[1].span == TimeSpan(1500, 3000)
    assert segs[0].meta["engine"] == "openai"


def test_openai_stt_falls_back_to_single_text():
    engine = OpenAISTT(client=_FakeClient(_Resp(segments=None, text="just text")))
    segs = engine.transcribe(np.ones(16_000, dtype="float32"), sample_rate=16_000)
    assert len(segs) == 1 and segs[0].text == "just text"
    assert segs[0].span.start_ms == 0 and segs[0].span.end_ms == 1000  # 1s of audio


def test_openai_stt_empty_audio_is_empty():
    engine = OpenAISTT(client=_FakeClient(_Resp(text="x")))
    assert engine.transcribe(np.zeros(0, dtype="float32"), sample_rate=16_000) == []


def test_openai_stt_requires_key(monkeypatch):
    # exercises the no-client _get_client() path (regression: os.getenv must work)
    pytest.importorskip("openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OpenAISTT()._get_client()


def test_get_engine_factory():
    assert isinstance(get_engine("whisper"), FasterWhisperSTT)
    assert isinstance(get_engine("openai"), OpenAISTT)
    with pytest.raises(ValueError):
        get_engine("nope")
