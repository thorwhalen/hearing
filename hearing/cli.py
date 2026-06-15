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
    engine: str = "whisper",
    model: str = "base",
    language: Optional[str] = None,
    split: bool = True,
    diarize: bool = True,
    out: Optional[str] = None,
    fmt: str = "text",
    save: Optional[str] = None,
) -> Optional[str]:
    """Transcribe an audio file to text or JSON.

    Args:
        path: audio file (wav/flac/aiff/...; convert mp3/m4a with ffmpeg first).
        engine: STT engine — "whisper" (local faster-whisper) or "openai" (cloud).
        model: whisper model size (tiny/base/small/medium/large-v3/...); local only.
        language: force a language code (e.g. "en"); omit to auto-detect.
        split: split mic/system channels for multi-channel files (me vs them).
        diarize: apply the channel-trick "me vs them" labelling.
        out: write to this path (.json -> JSON, else formatted text); else stdout.
        fmt: stdout/text format — "text" or "json".
        save: persist the transcript to this store/folder (keyed by the file stem),
            so post-meeting agents can load the full transcript later.
    """
    from hearing import transcribe as _transcribe
    from hearing.diarize import ChannelTrickDiarizer
    from hearing.stt import get_engine

    stt = get_engine("openai") if engine == "openai" else get_engine("whisper", model_size=model)
    transcript = _transcribe(
        path,
        engine=stt,
        diarizer=ChannelTrickDiarizer() if diarize else None,
        language=language,
        split=split,
    )

    if save:
        from hearing.storage import MeetingStore

        key = MeetingStore(save).save(Path(path).stem, transcript)
        print(f"saved transcript as {key} in {save}", file=sys.stderr)

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
    context_dir: Optional[str] = None,
    retriever: str = "keyword",
    web_search: bool = False,
    transcribe_model: str = "base",
    split: bool = True,
) -> Optional[str]:
    """Transcribe a meeting and produce AI notes (summary, actions, questions).

    Args:
        path: audio file to transcribe and analyze.
        agent: "auto" (Claude if available, else offline extractive), "claude",
            or "extractive" (deterministic, no API key needed).
        model: Claude model id (only used by the claude/auto agent).
        context: optional literal context string to connect the agent.
        context_dir: a folder/file of .txt/.md context docs (prior takeaways,
            project notes); the agent does RAG over it (context-connected).
        retriever: "keyword" (TF-IDF, offline) or "embedding" (OpenAI semantic;
            needs hearing[openai] + OPENAI_API_KEY). Only used with context_dir.
        web_search: also bring in Wikipedia fact context (key-free) for the agent.
        transcribe_model: whisper model size used for transcription.
        split: split mic/system channels (me vs them).
    """
    from hearing.agents import build_default_agent
    from hearing.pipeline import summarize as _summarize
    from hearing.stt import FasterWhisperSTT

    retr = None
    if context_dir:
        if retriever == "embedding":
            from hearing.context import build_embedding_retriever

            retr = build_embedding_retriever(context_dir)
        else:
            from hearing.context import build_retriever

            retr = build_retriever(context_dir)
    web = None
    if web_search:
        from hearing.context import WikipediaSearch

        web = WikipediaSearch()
    chosen = build_default_agent(
        context=context, model=model, prefer=agent, retriever=retr, web_search=web
    )
    return _summarize(
        path,
        agent=chosen,
        engine=FasterWhisperSTT(model_size=transcribe_model),
        split=split,
    )


def meetings(store: str, *, show: Optional[str] = None) -> str:
    """List transcripts saved in a store (or print one with --show ID).

    Args:
        store: the store/folder a transcript was saved to (`transcribe --save`).
        show: a meeting id to print (formatted transcript) instead of listing.
    """
    from hearing.storage import MeetingStore

    ms = MeetingStore(store)
    if show:
        return ms.load(show).formatted()
    ids = list(ms)
    return "\n".join(ids) if ids else "(no meetings stored)"


def live(
    path: Optional[str] = None,
    *,
    model: str = "base",
    device: Optional[str] = None,
    block_ms: int = 200,
    realtime: bool = False,
) -> None:
    """Run the LIVE streaming pipeline, printing segments as utterances finalize.

    Args:
        path: stream this audio FILE through the live loop (great for a demo /
            no hardware). Omit to capture from an audio DEVICE instead.
        model: whisper model size for the streaming STT.
        device: audio device index/name for live capture (an Aggregate Device
            with mic + BlackHole; see the hearing-audio-capture skill).
        block_ms: streaming block size in milliseconds.
        realtime: when streaming a file, pace it in real time (else as-fast-as).
    """
    import asyncio

    from hearing.capture import DeviceCapture, StreamingFileCapture
    from hearing.pipeline import live_transcribe
    from hearing.stt import FasterWhisperSTT
    from hearing.types import _ms_to_clock

    engine = FasterWhisperSTT(model_size=model)
    if path:
        source = StreamingFileCapture(path, block_ms=block_ms, realtime=realtime)
    else:
        source = DeviceCapture(device=device, block_ms=block_ms)
        print("Listening (Ctrl+C to stop)…", file=sys.stderr)

    async def _run() -> None:
        async for seg in live_transcribe(source=source, engine=engine):
            who = seg.speaker or seg.channel.value
            print(f"[{_ms_to_clock(seg.span.start_ms)}] {who}: {seg.text.strip()}", flush=True)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:  # pragma: no cover
        print("\nstopped.", file=sys.stderr)


def serve(*, host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Serve the HTTP API (FastAPI) the frontend talks to.

    Args:
        host: bind address.
        port: bind port.
        reload: auto-reload on code changes (dev).
    """
    try:
        import uvicorn
    except ImportError:  # pragma: no cover - guidance path
        print("`hearing serve` needs the http extra: pip install 'hearing[http]'", file=sys.stderr)
        raise SystemExit(1)
    import importlib.util
    from pathlib import Path

    spec = importlib.util.find_spec("hearing.http_app")
    dist = Path(spec.origin).resolve().parents[1] / "frontend" / "dist" if spec and spec.origin else None
    if dist and dist.is_dir():
        print(f"hearing — open the app at http://{host}:{port}  (API + UI; docs at /docs)", file=sys.stderr)
    else:
        print(
            f"hearing API on http://{host}:{port}  (docs at /docs). UI not built — run "
            "`cd frontend && npm install && npm run build`, or use the dev server "
            "(`npm run dev`).",
            file=sys.stderr,
        )
    uvicorn.run("hearing.http_app:app", host=host, port=port, reload=reload)


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
    from argh.assembling import NameMappingPolicy

    parser = argh.ArghParser(description="hearing — meeting transcription & AI agents")
    # BY_NAME_IF_KWONLY: positional params stay positional (optional when they have
    # a default, e.g. `hearing live [FILE]`); keyword-only params become --options.
    argh.add_commands(
        parser,
        [transcribe, summarize, live, serve, meetings, info],
        name_mapping_policy=NameMappingPolicy.BY_NAME_IF_KWONLY,
    )
    parser.dispatch(argv)


if __name__ == "__main__":
    main()
