"""Tests for the scribed-backed STT engine (the hearing -> scribed bridge).

hearing's STT is now a thin adapter over scribed. These verify the wrapper maps
scribed's ``Segment`` spine onto hearing's ``TranscriptSegment`` (batch and live),
and the ``get_engine`` factory — using a model-free fake scribed backend (no model,
no network). The engine-specific mapping (e.g. OpenAI verbose_json) is tested in
scribed itself, where those backends now live.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager

import numpy as np
import pytest

import scribed
from scribed import registry
from scribed.testing import FakeTranscriber, speech_silence_stream

from hearing.stt import (
    FasterWhisperSTT,
    OpenAISTT,
    ScribedSTT,
    default_engine,
    get_engine,
)
from hearing.types import Channel, TimeSpan, TranscriptSegment

pytest.importorskip("soundfile")  # ScribedSTT encodes utterances to wav bytes


@contextmanager
def _registered(backend_id: str, adapter):
    """Temporarily register a fake scribed backend, cleaning up the registry after."""
    registry.register_backend(
        backend_id, {"name": backend_id, "id": backend_id}, adapter=adapter
    )
    try:
        yield
    finally:
        registry._registry.pop(backend_id, None)
        scribed.services._handles.pop(backend_id, None)


def test_get_engine_maps_to_scribed_backends():
    assert isinstance(get_engine("whisper"), ScribedSTT)
    assert get_engine("whisper").backend == "faster-whisper"
    assert get_engine("openai").backend == "openai"
    with pytest.raises(ValueError):
        get_engine("nope")


def test_compat_constructors_return_scribed_stt():
    fw = FasterWhisperSTT(model_size="tiny")
    assert fw.backend == "faster-whisper" and fw.model_size == "tiny"
    assert OpenAISTT().backend == "openai"
    assert default_engine().backend == "faster-whisper"


def test_scribed_stt_maps_segments_to_hearing_spine():
    with _registered("fake-batch", FakeTranscriber(texts=["hello world"])):
        segs = ScribedSTT(backend="fake-batch").transcribe(
            np.ones(16_000, dtype="float32"), sample_rate=16_000
        )
    assert [s.text for s in segs] == ["hello world"]
    seg = segs[0]
    assert isinstance(seg, TranscriptSegment)
    assert isinstance(seg.span, TimeSpan) and seg.span.start_ms == 0
    assert seg.channel is Channel.MIXED  # generic STT -> hearing's MIXED default
    assert seg.meta["final"] is True  # batch segments are final


def test_scribed_stt_empty_audio_is_empty():
    fake = FakeTranscriber(texts=["x"])
    with _registered("fake-empty", fake):
        out = ScribedSTT(backend="fake-empty").transcribe(
            np.zeros(0, dtype="float32"), sample_rate=16_000
        )
    assert out == [] and fake.calls == 0  # no audio -> no scribed call


def test_scribed_stt_stream_yields_finalized_hearing_segments():
    with _registered("fake-stream", FakeTranscriber(texts=["one", "two"])):
        engine = ScribedSTT(backend="fake-stream")

        async def run():
            src = speech_silence_stream(n_utterances=2)
            return [
                s
                async for s in engine.stream_transcribe(
                    src.__aiter__(), sample_rate=16_000
                )
            ]

        segs = asyncio.run(run())
    assert [s.text for s in segs] == ["one", "two"]
    assert all(isinstance(s, TranscriptSegment) for s in segs)
    assert all(s.meta.get("final") for s in segs)  # finalized utterances
