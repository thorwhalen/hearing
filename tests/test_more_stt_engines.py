"""Tests for the Deepgram, MLX (mlx-whisper / parakeet-mlx) and WhisperX engines.

Offline only: every engine SDK is a fake module injected with
``monkeypatch.setitem(sys.modules, ...)`` — no network, no model downloads, no
MLX/torch install. Audio is tiny synthetic numpy. The fakes record what they were
called with, so the tests pin both directions of each adapter: what hearing sends
to the engine, and how the engine's native result lands on hearing's spine.
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

import hearing.backends as hb
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
        hb.register_backends()
        monkeypatch.setitem(registry._registry[backend_id], "adapter", None)
        monkeypatch.delitem(scribed.services._handles, backend_id, raising=False)

    return _fresh


@pytest.fixture
def apple_silicon(monkeypatch):
    monkeypatch.setattr(hb, "is_apple_silicon", lambda: True)


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


def test_register_backends_is_idempotent_and_non_clobbering():
    calls = []
    fake_registry = types.SimpleNamespace(
        list_backends=lambda: ["whisperx"],  # pretend scribed already ships whisperx
        register_backend=lambda bid, config: calls.append((bid, config)),
    )
    added = hb.register_backends(registry=fake_registry)
    assert added == ["mlx-whisper", "parakeet-mlx"]
    assert all(c["module_path"].startswith("hearing.backends.") for _, c in calls)
    assert hb.register_backends(["whisperx"], registry=fake_registry) == []


def test_apple_silicon_detection():
    assert hb.is_apple_silicon(system=lambda: "Darwin", machine=lambda: "arm64")
    assert not hb.is_apple_silicon(system=lambda: "Darwin", machine=lambda: "x86_64")
    assert not hb.is_apple_silicon(system=lambda: "Linux", machine=lambda: "aarch64")


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
# MLX: mlx-whisper (primary) and parakeet-mlx
# ---------------------------------------------------------------------------

WHISPER_RESULT = {
    "text": " hi there",
    "language": "en",
    "segments": [
        {
            "start": 0.0,
            "end": 1.0,
            "text": " hi there",
            "avg_logprob": -0.1,
            "words": [
                {"word": " hi", "start": 0.0, "end": 0.4, "probability": 0.9},
                {"word": " there", "start": 0.4, "end": 1.0, "probability": 0.8},
            ],
        }
    ],
}


@pytest.fixture
def fake_mlx_whisper(monkeypatch, fresh):
    calls = []

    def transcribe(audio, **kwargs):
        calls.append((audio, kwargs))
        return WHISPER_RESULT

    monkeypatch.setitem(
        sys.modules, "mlx_whisper", _module("mlx_whisper", transcribe=transcribe)
    )
    fresh("mlx-whisper")
    return calls


def test_mlx_refuses_off_apple_silicon(monkeypatch, fake_mlx_whisper):
    monkeypatch.setattr(hb, "is_apple_silicon", lambda: False)
    with pytest.raises(RuntimeError, match="Apple Silicon"):
        MLXSTT().transcribe(ONE_SECOND, sample_rate=SR)
    assert fake_mlx_whisper == []  # never reached the engine


def test_mlx_missing_package_points_to_the_extra(monkeypatch, apple_silicon, fresh):
    monkeypatch.setitem(sys.modules, "mlx_whisper", None)  # import -> ImportError
    fresh("mlx-whisper")
    with pytest.raises(ImportError, match=r"hearing\[mlx\]"):
        MLXSTT().transcribe(ONE_SECOND, sample_rate=SR)


def test_mlx_whisper_batch(apple_silicon, fake_mlx_whisper):
    segs = MLXSTT(language="en").transcribe(ONE_SECOND, sample_rate=SR)
    assert [s.text for s in segs] == ["hi there"]
    assert [w.text for w in segs[0].words] == ["hi", "there"]
    assert segs[0].span.end_ms == 1000 and 0 < segs[0].confidence < 1
    audio, kwargs = fake_mlx_whisper[0]
    assert isinstance(audio, np.ndarray) and audio.dtype == np.float32
    assert audio.shape == (SR,)  # decoded to 16 kHz mono, no ffmpeg/file path
    assert kwargs["path_or_hf_repo"] == "mlx-community/whisper-large-v3-turbo"
    assert kwargs["language"] == "en"


def test_mlx_whisper_resolves_bare_sizes(apple_silicon, fake_mlx_whisper):
    MLXSTT(model="small").transcribe(ONE_SECOND, sample_rate=SR)
    assert (
        fake_mlx_whisper[0][1]["path_or_hf_repo"] == "mlx-community/whisper-small-mlx"
    )


def test_mlx_live_path(apple_silicon, fake_mlx_whisper):
    engine = get_engine("mlx")

    async def run():
        src = speech_silence_stream(n_utterances=2)
        return [
            s async for s in engine.stream_transcribe(src.__aiter__(), sample_rate=SR)
        ]

    assert [s.text for s in asyncio.run(run())] == ["hi there", "hi there"]


def test_parakeet_mlx_batch(monkeypatch, apple_silicon, fresh):
    loaded, paths = [], []

    class _Model:
        def transcribe(self, path):
            paths.append(path)
            sentence = types.SimpleNamespace(text=" bonjour", start=0.2, end=0.8)
            return types.SimpleNamespace(text=" bonjour", sentences=[sentence])

    def from_pretrained(repo):
        loaded.append(repo)
        return _Model()

    monkeypatch.setitem(
        sys.modules,
        "parakeet_mlx",
        _module("parakeet_mlx", from_pretrained=from_pretrained),
    )
    fresh("parakeet-mlx")
    engine = MLXSTT(mlx_backend="parakeet-mlx")
    segs = engine.transcribe(ONE_SECOND, sample_rate=SR)
    engine.transcribe(ONE_SECOND, sample_rate=SR)
    assert [s.text for s in segs] == ["bonjour"]
    assert (segs[0].span.start_ms, segs[0].span.end_ms) == (200, 800)
    assert loaded == ["mlx-community/parakeet-tdt-0.6b-v3"]  # model cached
    assert all(p.endswith(".wav") for p in paths)


# ---------------------------------------------------------------------------
# WhisperX
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_whisperx(monkeypatch, fresh):
    log = {"load_model": [], "align": 0, "diarize": []}

    class _Asr:
        def transcribe(self, audio, *, batch_size, language):
            log["audio"] = audio
            return {
                "language": "en",
                "segments": [{"start": 0.0, "end": 1.0, "text": " hi there"}],
            }

    def load_model(model, device, *, compute_type, language):
        log["load_model"].append((model, device, compute_type, language))
        return _Asr()

    def align(segments, model, metadata, audio, device, return_char_alignments):
        log["align"] += 1
        return {
            "segments": [
                {
                    **segments[0],
                    "words": [
                        {"word": "hi", "start": 0.0, "end": 0.3, "score": 0.9},
                        {"word": "there", "start": 0.3, "end": 1.0, "score": 0.7},
                    ],
                }
            ]
        }

    class DiarizationPipeline:
        def __init__(self, *, use_auth_token, device):
            log["diarize"].append(use_auth_token)

        def __call__(self, audio, *, min_speakers, max_speakers):
            return "turns"

    def assign_word_speakers(turns, result):
        assert turns == "turns"
        for seg in result["segments"]:
            seg["speaker"] = "SPEAKER_00"
        return result

    monkeypatch.setitem(
        sys.modules,
        "whisperx",
        _module(
            "whisperx",
            load_model=load_model,
            load_align_model=lambda language_code, device: ("align-model", {}),
            align=align,
            DiarizationPipeline=DiarizationPipeline,
            assign_word_speakers=assign_word_speakers,
        ),
    )
    monkeypatch.setitem(sys.modules, "torch", None)  # no torch -> cpu
    fresh("whisperx")
    return log


def test_whisperx_transcribes_and_aligns(fake_whisperx):
    engine = WhisperXSTT()
    segs = engine.transcribe(ONE_SECOND, sample_rate=SR)
    engine.transcribe(ONE_SECOND, sample_rate=SR)
    assert [s.text for s in segs] == ["hi there"]
    assert [w.text for w in segs[0].words] == ["hi", "there"]
    assert segs[0].speaker is None  # diarization off by default
    assert fake_whisperx["load_model"] == [("large-v3", "cpu", "int8", None)]  # cached
    assert fake_whisperx["align"] == 2 and fake_whisperx["diarize"] == []
    assert fake_whisperx["audio"].dtype == np.float32


def test_whisperx_diarizes_with_a_token(monkeypatch, fake_whisperx):
    monkeypatch.setenv("HF_TOKEN", "hf-test")
    segs = WhisperXSTT(diarize=True).transcribe(ONE_SECOND, sample_rate=SR)
    assert segs[0].speaker == "SPEAKER_00"
    assert fake_whisperx["diarize"] == ["hf-test"]


def test_whisperx_diarize_without_token_is_informative(monkeypatch, fake_whisperx):
    import scribed.credentials as creds

    for var in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(creds, "_soft_load_dotenv", lambda: None)
    with pytest.raises(RuntimeError, match="HF_TOKEN"):
        WhisperXSTT(diarize=True).transcribe(ONE_SECOND, sample_rate=SR)


def test_whisperx_missing_package_points_to_the_extra(monkeypatch, fresh):
    monkeypatch.setitem(sys.modules, "whisperx", None)
    fresh("whisperx")
    with pytest.raises(ImportError, match=r"hearing\[whisperx\]"):
        WhisperXSTT().transcribe(ONE_SECOND, sample_rate=SR)


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
