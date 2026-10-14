"""Extra scribed backends that hearing contributes: Apple-Silicon MLX and WhisperX.

hearing's STT runs through scribed (see :mod:`hearing.stt`). scribed already ships
the cloud engines (OpenAI, Deepgram, AssemblyAI, ...) and faster-whisper; the
engines below are not in scribed yet, so hearing provides them as **scribed
plugins**, registered at runtime with :func:`scribed.register_backend`:

- ``mlx-whisper`` — Whisper on Apple Silicon via MLX (``pip install 'hearing[mlx]'``)
- ``parakeet-mlx`` — NVIDIA Parakeet-TDT on Apple Silicon via MLX (same extra)
- ``whisperx`` — WhisperX: batched Whisper + word alignment + optional pyannote
  diarization (``pip install 'hearing[whisperx]'``)

Each backend is a subpackage laid out exactly like a ``scribed.backends.<id>``
package (``config.py`` with ``BACKEND_CONFIG``, ``adapter.py`` with ``Adapter``),
so it can move into scribed verbatim. Registration is lazy and non-clobbering:
:func:`register_backends` only adds an id scribed does not already provide, so
once scribed ships one of these, scribed's own implementation wins.

Nothing here imports an engine SDK at import time; the adapters import it on first
transcription and raise an informative error (naming the extra) when it is absent,
or — for the MLX engines — when not running on Apple Silicon.
"""

from __future__ import annotations

import importlib
import math
import platform
from typing import Any, Callable, Dict, Iterable, List, Optional

#: Subpackages of this package that are scribed backends (backend id -> module).
BACKEND_MODULES: Dict[str, str] = {
    "mlx-whisper": "hearing.backends.mlx_whisper",
    "parakeet-mlx": "hearing.backends.parakeet_mlx",
    "whisperx": "hearing.backends.whisperx",
}


def backend_config(backend_id: str) -> dict:
    """The ``BACKEND_CONFIG`` of one of hearing's backends (no SDK import)."""
    module = importlib.import_module(f"{BACKEND_MODULES[backend_id]}.config")
    return module.BACKEND_CONFIG


def register_backends(
    backend_ids: Optional[Iterable[str]] = None, *, registry: Any = None
) -> List[str]:
    """Register hearing's backends with scribed's registry; return the ids added.

    Idempotent and non-clobbering: an id scribed already knows is left alone.
    The adapter itself is loaded lazily by scribed (from ``module_path``).

    Args:
        backend_ids: which backends to register (default: all of them).
        registry: the scribed registry module (injectable for tests).
    """
    if registry is None:
        from scribed import registry
    known = set(registry.list_backends())
    added = []
    for bid in backend_ids or BACKEND_MODULES:
        if bid in known:
            continue
        config = {**backend_config(bid), "module_path": BACKEND_MODULES[bid]}
        registry.register_backend(bid, config)
        added.append(bid)
    return added


# ---------------------------------------------------------------------------
# Guards shared by the adapters
# ---------------------------------------------------------------------------


def is_apple_silicon(
    *,
    system: Callable[[], str] = platform.system,
    machine: Callable[[], str] = platform.machine,
) -> bool:
    """True on macOS running on an ARM (M-series) CPU — where MLX works."""
    return system() == "Darwin" and machine() in ("arm64", "aarch64")


def require_apple_silicon(engine: str, *, check: Callable[[], bool] = None) -> None:
    """Raise an informative ``RuntimeError`` unless running on Apple Silicon."""
    if not (check or is_apple_silicon)():
        raise RuntimeError(
            f"The {engine!r} STT engine runs on Apple Silicon (macOS on M-series) "
            f"only — MLX has no backend for {platform.system()}/{platform.machine()}. "
            "Use the 'whisper' (faster-whisper, any CPU/GPU) or a cloud engine "
            "('openai', 'deepgram') instead."
        )


def require_module(module_name: str, *, engine: str, extra: str) -> Any:
    """Import ``module_name`` or raise an ``ImportError`` that names the extra."""
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(
            f"The {engine!r} STT engine needs the {module_name!r} package: "
            f"pip install 'hearing[{extra}]'\nOriginal error: {e}"
        ) from e


def to_waveform_16k(audio: Any) -> Any:
    """Decode any scribed audio input to a float32 mono 16 kHz numpy array.

    Whisper-family engines accept such an array directly, which avoids their
    ffmpeg-based file loading (hearing hands utterances over as WAV bytes).
    """
    import numpy as np
    from scribed.audio import STT_SAMPLE_RATE, to_mono_16k
    from scribed.util import to_waveform

    data, sr = to_waveform(audio, sample_rate=STT_SAMPLE_RATE)
    mono = to_mono_16k(np.asarray(data, dtype="float32"), sr, target=STT_SAMPLE_RATE)
    return np.asarray(mono, dtype="float32")


# ---------------------------------------------------------------------------
# Whisper-style result dict -> scribed segments (shared by mlx-whisper, WhisperX)
# ---------------------------------------------------------------------------


def logprob_to_confidence(avg_logprob: Optional[float]) -> Optional[float]:
    """Map Whisper's average log-probability to a rough ``[0, 1]`` confidence."""
    if avg_logprob is None:
        return None
    try:
        return math.exp(float(avg_logprob))
    except (TypeError, ValueError, OverflowError):
        return None


def whisper_result_to_segments(result: dict) -> list:
    """Build scribed ``Segment``\\ s from an openai-whisper-style result dict.

    Handles both mlx-whisper (word ``probability``) and WhisperX (word ``score``,
    optional ``speaker`` on segments and words). Times are float seconds.

    >>> segs = whisper_result_to_segments({"segments": [
    ...     {"start": 0.0, "end": 1.5, "text": " hi there",
    ...      "words": [{"word": " hi", "start": 0.0, "end": 0.4, "probability": 0.9}]}
    ... ]})
    >>> segs[0].text, segs[0].span.end_ms, segs[0].words[0].text
    ('hi there', 1500, 'hi')
    """
    from scribed.make_backend import make_segment, make_word

    def _word(w: dict):
        conf = w.get("probability", w.get("score"))
        return make_word(
            (w.get("word") or "").strip(),
            start=w.get("start"),
            end=w.get("end"),
            confidence=conf,
            speaker=w.get("speaker"),
        )

    return [
        make_segment(
            (s.get("text") or "").strip(),
            start=s.get("start"),
            end=s.get("end"),
            confidence=logprob_to_confidence(s.get("avg_logprob")),
            speaker=s.get("speaker"),
            words=[_word(w) for w in (s.get("words") or [])],
        )
        for s in result.get("segments") or []
    ]
