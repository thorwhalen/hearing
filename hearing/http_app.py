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


def transcript_to_payload(transcript: Transcript, *, meeting_id: str, title: str) -> dict:
    """Serialize a :class:`Transcript` to the frontend's meeting+segments shape."""
    segments = []
    for i, s in enumerate(transcript.segments):
        segments.append(
            {
                "id": str(uuid.uuid5(_SEGMENT_NS, f"{meeting_id}:{i}")),
                "meetingId": meeting_id,
                "speaker": s.speaker or s.channel.value,
                "side": _side(s.speaker, s.channel),
                "channel": s.channel.value,
                "startMs": s.span.start_ms,
                "endMs": s.span.end_ms,
                "text": s.text.strip(),
                "confidence": s.confidence,
                "isFinal": bool(s.meta.get("final", True)),
            }
        )
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

    return app


# Module-level app for `uvicorn hearing.http_app:app`.
app = create_app()
