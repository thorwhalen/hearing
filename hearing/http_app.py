"""HTTP layer over the hearing facades (FastAPI).

Surfaces the same Python facades the CLI uses (``transcribe`` / ``summarize``) as
REST endpoints, serialized to exactly the shape the TypeScript frontend's zodal
schema expects (see the ``hearing-frontend`` skill). The facades stay the SSOT;
this module only adapts transport — per the ``python-dispatching`` skill.

Run it with ``hearing serve`` (uvicorn) or ``uvicorn hearing.http_app:app``.

Endpoints:
- ``GET  /api/health``     — liveness + version.
- ``POST /api/transcribe`` — multipart audio upload -> a meeting + its diarized
  segments (and an optional AI summary).

Note: this module imports FastAPI at import time (it is the ``http`` extra), and
deliberately does NOT use ``from __future__ import annotations`` — FastAPI needs
real annotation objects, not stringized forward refs, to build its request models.
"""

import asyncio
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from hearing.types import ME, Channel, Transcript

try:
    from fastapi import FastAPI, File, Form, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
except ImportError as e:  # pragma: no cover - guidance path
    raise ImportError(
        "The HTTP layer needs FastAPI. Install with: pip install 'hearing[http]'"
    ) from e

# Stable IDs derived deterministically from (meeting_id, index) so re-fetching the
# same transcript yields stable segment ids (handy as React list keys).
_SEGMENT_NS = uuid.UUID("e9b1c0de-0000-4000-8000-000000000000")


def _side(speaker: Optional[str], channel: Channel) -> str:
    """Map a segment to the frontend's me/them lane.

    "me" when it came from the mic channel or is labelled as the local user;
    "them" otherwise (a single MIXED channel has no real side and falls to "them").
    """
    if channel is Channel.MIC or speaker == ME:
        return "me"
    return "them"


def segment_to_dict(seg, *, meeting_id: str, index: int) -> dict:
    """Serialize one :class:`~hearing.types.TranscriptSegment` to the UI shape."""
    return {
        "id": str(uuid.uuid5(_SEGMENT_NS, f"{meeting_id}:{index}")),
        "meetingId": meeting_id,
        "speaker": seg.speaker or seg.channel.value,
        "side": _side(seg.speaker, seg.channel),
        "channel": seg.channel.value,
        "startMs": seg.span.start_ms,
        "endMs": seg.span.end_ms,
        "text": seg.text.strip(),
        "confidence": seg.confidence,
        "isFinal": bool(seg.meta.get("final", True)),
    }


def transcript_to_payload(transcript: Transcript, *, meeting_id: str, title: str) -> dict:
    """Serialize a :class:`Transcript` to the frontend's meeting+segments shape."""
    segments = [
        segment_to_dict(s, meeting_id=meeting_id, index=i)
        for i, s in enumerate(transcript.segments)
    ]
    participants = sorted({seg["speaker"] for seg in segments})
    return {
        "meeting": {
            "id": meeting_id,
            "title": title,
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "durationMs": transcript.duration_ms,
            "participants": participants,
            "segmentCount": len(segments),
        },
        "segments": segments,
    }


def create_app(*, engine=None, agent=None, cors_origins: Optional[list] = None) -> FastAPI:
    """Build the FastAPI app.

    Args:
        engine: an :class:`~hearing.interfaces.STTEngine` for all requests (inject
            a fake/cheap engine in tests). ``None`` -> the default faster-whisper
            engine, built lazily on first request.
        agent: an :class:`~hearing.interfaces.AgentConsumer` for ``summarize=true``
            requests. ``None`` -> the default agent (Claude if available, else the
            offline extractive fallback).
        cors_origins: allowed CORS origins (default ``["*"]`` for local dev).
    """
    app = FastAPI(title="hearing", summary="Meeting transcription & AI agents")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.engine = engine
    app.state.agent = agent

    def _engine():
        if app.state.engine is None:
            from hearing.stt import default_engine

            app.state.engine = default_engine()
        return app.state.engine

    @app.get("/api/health")
    def health() -> dict:
        from hearing import __version__

        return {"status": "ok", "version": __version__}

    @app.post("/api/transcribe")
    async def transcribe_endpoint(
        file: UploadFile = File(...),
        title: str = Form("Untitled meeting"),
        language: Optional[str] = Form(None),
        split: bool = Form(True),
        summarize: bool = Form(False),
    ) -> dict:
        """Transcribe an uploaded audio file; optionally attach an AI summary."""
        from hearing.pipeline import transcribe

        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(await file.read())
            tmp.flush()
            # transcribe() is blocking (STT) — run it off the event loop so the
            # server stays responsive. Don't pass agent= here (its sync path uses
            # asyncio.run, which can't run inside this loop); await the agent below.
            transcript = await asyncio.to_thread(
                transcribe, tmp.name, engine=_engine(), language=language, split=split
            )

        meeting_id = str(uuid.uuid4())
        payload = transcript_to_payload(transcript, meeting_id=meeting_id, title=title)
        if summarize:
            from hearing.agents import build_default_agent

            agent = app.state.agent or build_default_agent()
            payload["summary"] = await agent.on_window(transcript.segments)
        return payload

    @app.post("/api/transcribe/stream")
    async def transcribe_stream(
        file: UploadFile = File(...),
        title: str = Form("Untitled meeting"),
    ):
        """Stream finalized segments as NDJSON as the live pipeline produces them.

        Each line is a JSON object: ``{"type":"meeting",...}`` first, then one
        ``{"type":"segment","segment":{...}}`` per finalized utterance, then
        ``{"type":"done","count":N}``. The browser reads the response body
        incrementally (fetch + ReadableStream) and appends rows live — the
        server→client push the frontend skill calls for.
        """
        import json
        import os

        data = await file.read()
        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        meeting_id = str(uuid.uuid4())

        async def gen():
            from hearing.agents import ExtractiveAgent
            from hearing.capture import StreamingFileCapture
            from hearing.pipeline import live_transcribe

            # The live agent runs per finalized segment and may surface feedback.
            # Default to the fast, offline ExtractiveAgent so the panel populates
            # without a per-segment LLM call; inject a richer agent via create_app.
            live_agent = app.state.agent or ExtractiveAgent()

            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            try:
                tmp.write(data)
                tmp.flush()
                tmp.close()
                yield json.dumps(
                    {"type": "meeting", "meeting": {"id": meeting_id, "title": title}}
                ) + "\n"
                source = StreamingFileCapture(tmp.name, block_ms=200)
                i = 0
                async for seg in live_transcribe(source=source, engine=_engine()):
                    seg_dict = segment_to_dict(seg, meeting_id=meeting_id, index=i)
                    yield json.dumps({"type": "segment", "segment": seg_dict}) + "\n"
                    note = await live_agent.on_segment(seg)
                    if note:
                        kind = "suggested_question" if seg.text.strip().endswith("?") else "note"
                        feedback = {
                            "id": str(uuid.uuid5(_SEGMENT_NS, f"{meeting_id}:fb:{i}")),
                            "meetingId": meeting_id,
                            "kind": kind,
                            "atMs": seg.span.end_ms,
                            "triggeredBy": seg_dict["id"],
                            "title": "Suggested question" if kind == "suggested_question" else "Note",
                            "body": note,
                        }
                        yield json.dumps({"type": "feedback", "feedback": feedback}) + "\n"
                    i += 1
                yield json.dumps({"type": "done", "count": i}) + "\n"
            finally:
                os.unlink(tmp.name)

        return StreamingResponse(gen(), media_type="application/x-ndjson")

    return app


# Module-level app for `uvicorn hearing.http_app:app`.
app = create_app()
