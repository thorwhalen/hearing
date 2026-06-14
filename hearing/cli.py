"""Command-line interface for hearing, dispatched with `argh`.

Surfaces the Python facades (`transcribe`, `summarize`) as subcommands — it does
not reimplement them (the facades are the SSOT; see the ``python-dispatching``
and ``hearing-architecture`` skills). Installed as the ``hearing`` console
script::

    hearing transcribe meeting.wav
    hearing transcribe meeting.wav --model small --out notes.json
    hearing summarize meeting.wav            # transcribe + AI meeting notes
    hearing info                             # check what's installed/available
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional


def transcribe(
    path: str,
    *,
    model: str = "base",
    language: Optional[str] = None,
    split: bool = True,
    diarize: bool = True,
    out: Optional[str] = None,
    fmt: str = "text",
) -> Optional[str]:
    """Transcribe an audio file to text or JSON.

    Args:
        path: audio file (wav/flac/aiff/...; convert mp3/m4a with ffmpeg first).
        model: whisper model size (tiny/base/small/medium/large-v3/...).
        language: force a language code (e.g. "en"); omit to auto-detect.
        split: split mic/system channels for multi-channel files (me vs them).
        diarize: apply the channel-trick "me vs them" labelling.
        out: write to this path (.json -> JSON, else formatted text); else stdout.
        fmt: stdout/text format — "text" or "json".
    """
    from hearing import transcribe as _transcribe
    from hearing.diarize import ChannelTrickDiarizer
    from hearing.stt import FasterWhisperSTT

    transcript = _transcribe(
        path,
        engine=FasterWhisperSTT(model_size=model),
        diarizer=ChannelTrickDiarizer() if diarize else None,
        language=language,
        split=split,
    )

    if out:
        out_path = Path(out)
        if out_path.suffix == ".json":
            out_path.write_text(json.dumps(transcript.to_jsonable(), indent=2))
        else:
            out_path.write_text(transcript.formatted())
        print(f"Wrote {len(transcript)} segments to {out_path}", file=sys.stderr)
        return None

    if fmt == "json":
        return json.dumps(transcript.to_jsonable(), indent=2)
    return transcript.formatted()


def summarize(
    path: str,
    *,
    agent: str = "auto",
    model: Optional[str] = None,
    context: Optional[str] = None,
    transcribe_model: str = "base",
    split: bool = True,
) -> Optional[str]:
    """Transcribe a meeting and produce AI notes (summary, actions, questions).

    Args:
        path: audio file to transcribe and analyze.
        agent: "auto" (Claude if available, else offline extractive), "claude",
            or "extractive" (deterministic, no API key needed).
        model: Claude model id (only used by the claude/auto agent).
        context: optional context to connect the agent to a project/meeting.
        transcribe_model: whisper model size used for transcription.
        split: split mic/system channels (me vs them).
    """
    from hearing.agents import build_default_agent
    from hearing.pipeline import summarize as _summarize
    from hearing.stt import FasterWhisperSTT

    chosen = build_default_agent(context=context, model=model, prefer=agent)
    return _summarize(
        path,
        agent=chosen,
        engine=FasterWhisperSTT(model_size=transcribe_model),
        split=split,
    )


def info() -> str:
    """Report which optional components are installed and what's missing."""
    lines = ["hearing — component availability:"]
    lines.append(_check("soundfile", "audio file reading"))
    lines.append(_check("soxr", "high-quality resampling (optional; linear fallback)"))
    lines.append(_check("faster_whisper", "default local STT engine  [hearing[whisper]]"))
    lines.append(_check("anthropic", "Claude agent backend          [hearing[agents]]"))
    lines.append(_check("pyannote.audio", "speaker diarization          [hearing[diarize]]"))
    import os

    key = "set" if os.getenv("ANTHROPIC_API_KEY") else "NOT set"
    lines.append(f"  ANTHROPIC_API_KEY: {key}")
    lines.append("  (system-audio capture on macOS needs BlackHole or Core Audio")
    lines.append("   taps — see the hearing-audio-capture skill.)")
    return "\n".join(lines)


def _check(module: str, what: str) -> str:
    """One availability line for `info`."""
    import importlib.util

    try:
        # find_spec raises (not returns None) when a parent package is missing,
        # e.g. "pyannote.audio" with no "pyannote" installed — treat as absent.
        found = importlib.util.find_spec(module.replace("-", "_")) is not None
    except ModuleNotFoundError:
        found = False
    return f"  [{'x' if found else ' '}] {module:<16} {what}"


def main(argv=None) -> None:
    """Entry point for the ``hearing`` console script."""
    try:
        import argh
    except ImportError:  # pragma: no cover - argh is a core dependency
        print("hearing CLI needs `argh` (pip install argh).", file=sys.stderr)
        raise SystemExit(1)
    parser = argh.ArghParser(description="hearing — meeting transcription & AI agents")
    argh.add_commands(parser, [transcribe, summarize, info])
    parser.dispatch(argv)


if __name__ == "__main__":
    main()
