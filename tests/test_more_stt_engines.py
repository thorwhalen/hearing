"""Tests for hearing's engine selection (aliases, constructors), Deepgram and the CLI.

Offline only: the Deepgram SDK is a fake module injected with
``monkeypatch.setitem(sys.modules, ...)`` — no network, no model downloads. The
MLX and WhisperX adapters live in scribed and are tested there.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import types

import numpy as np
import pytest

import scribed
from scribed import registry
from scribed.testing import speech_silence_stream

from hearing.stt import (
    ENGINE_ALIASES,
    ENGINE_NAMES,
    DeepgramSTT,
    MLXSTT,
    ScribedSTT,
    WhisperXSTT,
    get_engine,
)
from hearing.types import TranscriptSegment

pytest.importorskip("soundfile")  # ScribedSTT encodes utterances to wav bytes

SR = 16_000
ONE_SECOND = (0.1 * np.sin(np.linspace(0, 440 * 2 * np.pi, SR))).astype("float32")


@pytest.fixture
def fresh(monkeypatch):
    """Return a function that drops scribed's cached adapter for a backend id.

    scribed caches one adapter (and its client/models) per backend; each test
    gets a fresh one so injected fakes are honoured, and the cache is restored
    afterwards by monkeypatch.
    """

    def _fresh(backend_id: str) -> None:
        monkeypatch.setitem(registry._registry[backend_id], "adapter", None)
        monkeypatch.delitem(scribed.services._handles, backend_id, raising=False)

    return _fresh


def _module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# ---------------------------------------------------------------------------
# Selection: get_engine, constructors, registration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, backend",
    [
        ("deepgram", "deepgram"),
        ("mlx", "mlx-whisper"),
        ("parakeet", "parakeet-mlx"),
        ("whisperx", "whisperx"),
        ("WhisperX", "whisperx"),
    ],
)
def test_get_engine_selects_new_engines(name, backend):
    engine = get_engine(name)
    assert isinstance(engine, ScribedSTT) and engine.backend == backend


def test_every_listed_engine_name_resolves():
    assert set(ENGINE_NAMES) <= set(ENGINE_ALIASES)
    for name in ENGINE_NAMES:
        get_engine(name)


def test_unknown_engine_error_lists_the_choices():
    with pytest.raises(ValueError, match="deepgram.*mlx.*whisperx"):
        get_engine("nope")


def test_constructors_keep_the_model_swappable():
    assert DeepgramSTT().backend == "deepgram"
    assert DeepgramSTT(model="nova-2").model_size == "nova-2"
    assert MLXSTT().backend == "mlx-whisper"
    assert MLXSTT(mlx_backend="parakeet-mlx", model="x/y").backend == "parakeet-mlx"
    with pytest.raises(ValueError, match="MLX backend"):
        MLXSTT(mlx_backend="coreml")
    wx = WhisperXSTT(diarize=True, model="small")
    assert wx.backend == "whisperx" and wx.options == {"diarize": True}
    assert wx._kwargs(None) == {"diarize": True, "model": "small"}


# ---------------------------------------------------------------------------
# Deepgram (scribed's backend, fake SDK/transport)
# ---------------------------------------------------------------------------

DEEPGRAM_RESPONSE = {
    "metadata": {"detected_language": "en"},
    "results": {
        "channels": [{"alternatives": [{"transcript": "hello there", "words": []}]}],
        "utterances": [
            {
                "transcript": "hello there",
                "start": 0.1,
                "end": 0.9,
                "confidence": 0.97,
                "speaker": 0,
                "words": [
                    {
                        "word": "hello",
                        "punctuated_word": "Hello",
                        "start": 0.1,
                        "end": 0.5,
                        "confidence": 0.98,
                        "speaker": 0,
                    },
                    {
                        "word": "there",
                        "start": 0.5,
                        "end": 0.9,
                        "confidence": 0.96,
                        "speaker": 0,
                    },
                ],
            }
        ],
    },
}


@pytest.fixture
def fake_deepgram(monkeypatch, fresh):
    """A fake ``deepgram`` SDK whose REST call records its payload and options."""
    sent = {}

    class PrerecordedOptions(dict):
        def __init__(self, **kw):
            super().__init__(**kw)

    class _Rest:
        def v(self, version):
            sent["version"] = version
            return self

        def transcribe_file(self, payload, options):
            sent.setdefault("calls", []).append((payload, options))
            return DEEPGRAM_RESPONSE

    class DeepgramClient:
        def __init__(self, key):
            sent["key"] = key
            self.listen = types.SimpleNamespace(rest=_Rest())

    monkeypatch.setitem(
        sys.modules,
        "deepgram",
        _module(
            "deepgram",
            DeepgramClient=DeepgramClient,
            PrerecordedOptions=PrerecordedOptions,
        ),
    )
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    fresh("deepgram")
    return sent


def test_deepgram_batch_maps_to_hearing_segments(fake_deepgram):
    segs = DeepgramSTT().transcribe(ONE_SECOND, sample_rate=SR)
    assert [s.text for s in segs] == ["hello there"]
    seg = segs[0]
    assert isinstance(seg, TranscriptSegment)
    assert (seg.span.start_ms, seg.span.end_ms) == (100, 900)
    assert seg.speaker == "0"  # Deepgram's built-in diarization label, as a str
    assert [w.text for w in seg.words] == ["Hello", "there"]
    payload, options = fake_deepgram["calls"][0]
    assert fake_deepgram["key"] == "test-key"
    assert payload["buffer"][:4] == b"RIFF"  # wav bytes, not a file path
    assert options["model"] == "nova-3"  # the default model


def test_deepgram_model_is_a_keyword(fake_deepgram):
    DeepgramSTT(model="nova-2", language="en").transcribe(ONE_SECOND, sample_rate=SR)
    _payload, options = fake_deepgram["calls"][0]
    assert options["model"] == "nova-2" and options["language"] == "en"


def test_deepgram_live_goes_through_vad_segmented_stream(fake_deepgram):
    engine = get_engine("deepgram")

    async def run():
        src = speech_silence_stream(n_utterances=2)
        return [
            s async for s in engine.stream_transcribe(src.__aiter__(), sample_rate=SR)
        ]

    segs = asyncio.run(run())
    assert [s.text for s in segs] == ["hello there", "hello there"]  # one per utterance
    assert all(s.meta["final"] for s in segs)
    assert segs[1].span.start_ms > segs[0].span.start_ms  # offset to stream time
    assert len(fake_deepgram["calls"]) == 2


def test_deepgram_missing_key_is_informative(monkeypatch, fake_deepgram):
    import scribed.credentials as creds

    monkeypatch.delenv("DEEPGRAM_API_KEY")
    monkeypatch.setattr(creds, "_soft_load_dotenv", lambda: None)
    with pytest.raises(creds.MissingCredentialError, match="DEEPGRAM_API_KEY"):
        DeepgramSTT().transcribe(ONE_SECOND, sample_rate=SR)


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", ["transcribe", "live", "summarize"])
def test_cli_engine_option(command):
    proc = subprocess.run(
        [sys.executable, "-m", "hearing.cli", command, "--help"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0
    assert "--engine ENGINE" in proc.stdout


def test_cli_transcribe_help_lists_engines():
    from hearing import cli

    for name in ENGINE_NAMES:
        assert f'"{name}"' in cli.transcribe.__doc__


def test_cli_transcribe_routes_engine_and_model(monkeypatch):
    from hearing import cli
    import hearing
    import hearing.stt

    seen = {}

    def fake_get_engine(name, **kwargs):
        seen.update(name=name, **kwargs)
        return "ENGINE"

    class _Transcript:
        def formatted(self):
            return "ok"

    monkeypatch.setattr(hearing.stt, "get_engine", fake_get_engine)
    monkeypatch.setattr(hearing, "transcribe", lambda path, **kw: _Transcript())
    assert cli.transcribe("x.wav", engine="deepgram", model="nova-2") == "ok"
    assert seen == {"name": "deepgram", "model_size": "nova-2"}
