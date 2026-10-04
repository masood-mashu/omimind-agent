"""
main.py - FastAPI Application Server for OmiMind Ambient Voice Intelligence
Exposes REST endpoints for Qdrant vector memory, Lyzr agent synthesis, and frontend UI.
"""
import json
import logging
import os
import re
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agents.orchestrator import OmiMindOrchestrator
from backend.config import settings
from backend.mock_data import DEMO_MEETINGS

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Voice Intelligence powered by Omi ambient audio, Qdrant vector memory, and Lyzr multi-agent framework.",
    version=settings.app_version
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "ALLOWED_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000"
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Structured Error Handling Handlers ──────────────────────────────────────

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Structured response for HTTP exceptions with full backward compatibility."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else "HTTP Exception",
                "status_code": exc.status_code,
                "timestamp": time.time()
            },
            "detail": exc.detail
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Structured response for 422 payload schema validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload schema",
                "status_code": 422,
                "details": exc.errors(),
                "timestamp": time.time()
            },
            "detail": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback handler for uncaught server errors."""
    logger.exception("Unhandled exception while serving %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
                "status_code": 500,
                "timestamp": time.time()
            },
            "detail": "Internal server error"
        }
    )

# ─── Security & Telemetry Middleware ──────────────────────────────────────────

@app.middleware("http")
async def security_and_telemetry_middleware(request: Request, call_next):
    """
    Security & Observability Middleware:
    1. If `API_SECRET_KEY` is configured in Settings, enforces Bearer/x-api-key on non-exempt routes.
    2. Injects telemetry headers: `X-Response-Time` and `X-Content-Type-Options`.
    """
    protected_paths = {
        "/api/forget", "/api/memory", "/api/seed",
        "/api/omi-webhook", "/omi/conversation", "/omi/realtime", "/ask"
    }
    if request.url.path in protected_paths:
        secret = settings.api_secret_key
        if not secret:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": {
                        "code": "PROTECTION_NOT_CONFIGURED",
                        "message": "This endpoint is disabled until API_SECRET_KEY is configured.",
                        "status_code": 503,
                        "timestamp": time.time()
                    },
                    "detail": "Protected endpoint unavailable"
                }
            )
        else:
            x_api_key = request.headers.get("x-api-key")
            auth_header = request.headers.get("authorization", "")
            bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else None
            token = x_api_key or bearer_token
            if token != secret:
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Invalid or missing API key. Provide x-api-key or Bearer token.",
                            "status_code": 401,
                            "timestamp": time.time()
                        },
                        "detail": "Unauthorized"
                    }
                )

    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

# Initialize persistent orchestrator
orchestrator = OmiMindOrchestrator(storage_path="./qdrant_storage")

# Active processed sessions cache
processed_cache: dict[str, Any] = {}

class ProcessRequest(BaseModel):
    meeting_id: str

class CustomVoiceRequest(BaseModel):
    title: str = "Live Omi Voice Memo"
    speaker: str = "User"
    transcript: str

class QueryRequest(BaseModel):
    question: str
    limit: int = Field(default=4, ge=1, le=20)

class OmiWebhookRequest(BaseModel):
    """Native Omi device webhook payload format."""
    session_id: str | None = None
    segments: list[dict[str, Any]] | None = None
    # Also accept flat transcript format
    transcript: str | None = None
    speaker: str | None = "Omi User"

# â”€â”€â”€ Helper: parse raw transcript blocks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def parse_transcript(transcript: str, default_speaker: str = "User") -> tuple[list[dict], set]:
    raw_blocks = re.split(r"\n+", transcript.strip())
    speaker_pattern = re.compile(r"^(?:\[([\d\:\.]+)\]\s*)?([A-Z][A-Za-z0-9\s\.\(\)\-_]{1,35}):\s*(.+)$")
    lines = []
    detected_speakers = set()
    current_speaker = default_speaker

    for block in raw_blocks:
        block_str = block.strip()
        if not block_str:
            continue
        m = speaker_pattern.match(block_str)
        if m:
            timestamp_match = m.group(1)
            current_speaker = m.group(2).strip()
            content = m.group(3).strip()
            detected_speakers.add(current_speaker)
            timestamp_str = timestamp_match if timestamp_match else time.strftime("%H:%M:%S", time.gmtime())
        else:
            content = block_str
            timestamp_str = time.strftime("%H:%M:%S", time.gmtime())

        sentences = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"'\-])", content)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 3:
                lines.append({
                    "speaker": current_speaker,
                    "timestamp_str": timestamp_str,
                    "text": s_clean
                })

    return lines, detected_speakers

# â”€â”€â”€ Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/health")
def health():
    stats = orchestrator.memory.get_stats()
    return {
        "status": "healthy",
        "service": "omimind-agent",
        "version": "2.0.0",
        "tech_stack": {
            "voice": "Omi Wearable Webhook / Mic Ingestion",
            "vector_database": "Qdrant Vector DB",
            "agent_orchestration": "Lyzr Multi-Agent Swarm"
        },
        "qdrant_stats": stats
    }

@app.get("/api/meetings")
def get_meetings():
    meetings_list = []
    for m in DEMO_MEETINGS.values():
        meetings_list.append({
            "id": m["id"],
            "title": m["title"],
            "category": m["category"],
            "duration": m["duration"],
            "participants": m["participants"],
            "turns_count": len(m["lines"])
        })
    return {"meetings": meetings_list}

@app.post("/api/process")
def process_meeting(req: ProcessRequest):
    if req.meeting_id not in DEMO_MEETINGS:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting = DEMO_MEETINGS[req.meeting_id]
    session_id = str(meeting["id"])
    title = str(meeting["title"])
    transcript_lines: list[dict[str, Any]] = meeting.get("lines", [])  # type: ignore[assignment]
    dossier = orchestrator.process_session(
        session_id=session_id,
        title=title,
        transcript_lines=transcript_lines
    )
    processed_cache[session_id] = dossier
    return dossier

# â”€â”€â”€ SSE Streaming Pipeline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _stream_pipeline(session_id: str, title: str, lines: list[dict]) -> AsyncGenerator[str, None]:
    """Yields SSE events for each agent stage so the frontend can animate them."""

    def sse(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    # Agent 1: Memory / Qdrant indexing
    yield sse({"agent": "MemoryAgent", "status": "running",
                "message": f"Indexing {len(lines)} utterances into Qdrant vector store..."})

    indexed_points = []
    for i, line in enumerate(lines):
        p_id = orchestrator.memory.index_utterance(
            session_id=session_id,
            speaker=line.get("speaker", "Speaker"),
            text=line.get("text", ""),
            timestamp=float(i * 15),
            timestamp_str=line.get("timestamp_str", f"00:{i*15:02d}"),
            topic=line.get("topic", "general"),
            urgency=line.get("urgency", "normal")
        )
        indexed_points.append(p_id)

    yield sse({"agent": "MemoryAgent", "status": "done",
                "message": f"{len(indexed_points)} vectors stored in omi_ambient_memory collection.",
                "count": len(indexed_points)})

    # Agent 2: Action extraction
    yield sse({"agent": "ActionExtractor", "status": "running",
                "message": "Scanning transcript for verbal commitments, deadlines, and urgency signals..."})

    action_items = orchestrator.extractor.extract_from_transcript(lines)

    yield sse({"agent": "ActionExtractor", "status": "done",
                "message": f"{len(action_items)} action item{'s' if len(action_items) != 1 else ''} extracted with assignees and due dates.",
                "count": len(action_items)})

    # Agent 3: Executive synthesis
    yield sse({"agent": "ExecutiveSynthesizer", "status": "running",
                "message": "Building dynamic executive briefing from decisions and risks..."})

    summary = orchestrator.synthesizer.synthesize_meeting(title, lines)
    decisions_found = len([d for d in summary.get("key_decisions", []) if "Consensus" not in d])
    risks_found = len([r for r in summary.get("risks_and_blockers", []) if "No critical" not in r])

    yield sse({"agent": "ExecutiveSynthesizer", "status": "done",
                "message": f"{decisions_found} decision{'s' if decisions_found != 1 else ''} confirmed, {risks_found} risk{'s' if risks_found != 1 else ''} flagged.",
                "count": decisions_found})

    # Agent 4: Task dispatch
    yield sse({"agent": "TaskDispatcher", "status": "running",
                "message": "Drafting executive follow-up email and generating Jira tickets..."})

    email_draft = orchestrator.dispatcher.generate_followup_email(summary, action_items)
    jira_tickets = orchestrator.dispatcher.generate_jira_tickets(action_items)

    yield sse({"agent": "TaskDispatcher", "status": "done",
                "message": f"Email drafted for {len(summary.get('participants', []))} recipients. {len(jira_tickets)} Jira ticket{'s' if len(jira_tickets) != 1 else ''} created.",
                "count": len(jira_tickets)})

    # Agent 5: Calendar Scheduling
    yield sse({"agent": "CalendarScheduler", "status": "running",
                "message": "Extracting meeting commitments and generating calendar links..."})

    calendar_events = orchestrator.scheduler.extract_calendar_events(lines)

    yield sse({"agent": "CalendarScheduler", "status": "done",
                "message": f"{len(calendar_events)} calendar event{'s' if len(calendar_events) != 1 else ''} detected with Google Meet/iCal links.",
                "count": len(calendar_events)})

    # Final: complete dossier
    dossier = {
        "session_id": session_id,
        "title": title,
        "indexed_vectors_count": len(indexed_points),
        "summary": summary,
        "action_items": action_items,
        "email_draft": email_draft,
        "jira_tickets": jira_tickets,
        "calendar_events": calendar_events
    }
    processed_cache[session_id] = dossier
    yield sse({"type": "complete", "dossier": dossier})

@app.post("/api/process-stream")
async def process_meeting_stream(req: ProcessRequest):
    if req.meeting_id not in DEMO_MEETINGS:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting = DEMO_MEETINGS[req.meeting_id]
    session_id = str(meeting["id"])
    title = str(meeting["title"])
    lines: list[dict] = meeting.get("lines", [])  # type: ignore[assignment]
    return StreamingResponse(
        _stream_pipeline(session_id, title, lines),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.post("/api/custom-voice-stream")
async def ingest_custom_voice_stream(req: CustomVoiceRequest):
    session_id = f"voice_{uuid.uuid4().hex[:8]}"
    lines, detected_speakers = parse_transcript(req.transcript, req.speaker)
    if not lines:
        lines = [{"speaker": req.speaker, "timestamp_str": "00:01", "text": req.transcript}]
    title = req.title
    if title == "Live Omi Voice Memo" and len(detected_speakers) > 1:
        title = "Multi-Stakeholder Operational Sync"
    return StreamingResponse(
        _stream_pipeline(session_id, title, lines),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

# â”€â”€â”€ Original non-streaming endpoints (kept for backward compat) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.post("/api/custom-voice")
def ingest_custom_voice(req: CustomVoiceRequest):
    session_id = f"voice_{uuid.uuid4().hex[:8]}"
    lines, detected_speakers = parse_transcript(req.transcript, req.speaker)
    if not lines:
        lines = [{"speaker": req.speaker, "timestamp_str": "00:01", "text": req.transcript}]
    title = req.title
    if title == "Live Omi Voice Memo" and len(detected_speakers) > 1:
        title = "Multi-Stakeholder Operational Sync"
    dossier = orchestrator.process_session(session_id=session_id, title=title, transcript_lines=lines)
    processed_cache[session_id] = dossier
    return dossier

# â”€â”€â”€ Omi Native Webhook â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.post("/api/omi-webhook")
def omi_webhook(req: OmiWebhookRequest):
    """
    Native Omi device webhook endpoint.
    Accepts Omi's standard segment payload or a flat transcript string.
    Configure your Omi app to POST to: https://omimind-agent.vercel.app/api/omi-webhook
    """
    session_id = req.session_id or f"omi_{uuid.uuid4().hex[:8]}"

    if req.segments:
        # Native Omi format: {"segments": [{"speaker": "...", "text": "...", "start": 0.0}]}
        lines = []
        for seg in req.segments:
            text = seg.get("text", "").strip()
            if len(text) > 3:
                start_sec = int(seg.get("start", 0))
                lines.append({
                    "speaker": seg.get("speaker", req.speaker or "Omi User"),
                    "timestamp_str": f"{start_sec // 60:02d}:{start_sec % 60:02d}",
                    "text": text
                })
    elif req.transcript:
        lines, _ = parse_transcript(req.transcript, req.speaker or "Omi User")
    else:
        raise HTTPException(status_code=400, detail="Provide either 'segments' or 'transcript'")

    if not lines:
        raise HTTPException(status_code=400, detail="No valid utterances found in payload")

    dossier = orchestrator.process_session(
        session_id=session_id,
        title="Omi Live Session",
        transcript_lines=lines
    )
    processed_cache[session_id] = dossier
    return {"status": "indexed", "session_id": session_id, "vectors": dossier["indexed_vectors_count"]}

# â”€â”€â”€ Seed endpoint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.post("/api/seed")
def seed_demo_data():
    """Pre-seed all 3 demo meetings into Qdrant so memory is non-empty on first load."""
    seeded = []
    for m_id, meeting in DEMO_MEETINGS.items():
        orchestrator.process_session(
            session_id=meeting["id"],
            title=meeting["title"],
            transcript_lines=meeting["lines"]
        )
        seeded.append(m_id)
    stats = orchestrator.memory.get_stats()
    return {"seeded": seeded, "qdrant_stats": stats}

@app.post("/api/query")
def query_memory(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return orchestrator.query_semantic_memory(query=req.question, limit=req.limit)

# ─── Official Hackathon Guide Endpoints (Lyzr × Qdrant × Omi) ────────────────

@app.post("/omi/conversation")
def omi_conversation_webhook(uid: str = "default_user", payload: dict[str, Any] = Body(...)):
    """
    Official Guide Endpoint: Fires after an Omi conversation ends.
    Ingests full transcript segments, structured overview, and indexes to Qdrant.
    """
    segments = payload.get("transcript_segments", [])
    overview = (payload.get("structured") or {}).get("overview", "")
    lines = []
    for s in segments:
        text = s.get("text", "").strip()
        if text:
            lines.append({
                "speaker": s.get("speaker", "Speaker"),
                "text": text,
                "timestamp_str": time.strftime("%H:%M:%S", time.gmtime())
            })
    if not lines and overview:
        lines = [{"speaker": "Overview", "text": overview, "timestamp_str": "00:00"}]

    if lines:
        dossier = orchestrator.process_session(
            session_id=f"conv_{uid}_{int(time.time())}",
            title=payload.get("structured", {}).get("title", f"Omi Memory ({uid})"),
            transcript_lines=lines
        )
        return {"status": "ok", "vectors_count": dossier["indexed_vectors_count"]}
    return {"status": "empty"}

@app.post("/omi/realtime")
def omi_realtime_webhook(uid: str = "default_user", session_id: str = "", payload: Any = Body(...)):
    """
    Official Guide Endpoint: Real-time transcript stream chunks from Omi device.
    """
    segments = payload if isinstance(payload, list) else payload.get("segments", [])
    indexed = 0
    for s in segments:
        t = s.get("text", "").strip()
        if t:
            try:
                timestamp = float(s.get("start", 0))
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail="Segment start must be numeric") from exc
            orchestrator.memory.index_utterance(
                session_id=session_id or f"realtime_{uid}",
                speaker=s.get("speaker", "Omi User"),
                text=t,
                timestamp=timestamp,
                timestamp_str="live"
            )
            indexed += 1
    return {"status": "ok", "indexed": indexed}

@app.post("/ask")
def official_ask_endpoint(body: dict[str, Any] = Body(...)):
    """
    Official Guide Endpoint: Retrieves memories from Qdrant and calls Lyzr agent synthesis.
    """
    uid = body.get("uid", "default_user")
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        limit = int(body.get("k", 5))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="k must be an integer between 1 and 20") from exc
    if not 1 <= limit <= 20:
        raise HTTPException(status_code=422, detail="k must be an integer between 1 and 20")

    recall_res = orchestrator.query_semantic_memory(query=question, limit=limit)
    matches = recall_res.get("matches", [])
    context = [f"[{m.get('speaker', 'Speaker')}]: {m.get('text', '')}" for m in matches]

    # Live Lyzr Agent Studio integration (Section 7 of Official Hackathon Guide)
    lyzr_api_key = os.environ.get("LYZR_API_KEY")
    lyzr_agent_id = os.environ.get("LYZR_AGENT_ID")
    lyzr_answer = None

    if lyzr_api_key and lyzr_agent_id:
        try:
            import httpx
            ctx_text = "\n".join("- " + c for c in context) or "none"
            lyzr_resp = httpx.post(
                "https://agent-prod.studio.lyzr.ai/v3/inference/chat/",
                headers={"Content-Type": "application/json", "x-api-key": lyzr_api_key},
                json={
                    "user_id": os.environ.get("LYZR_USER_ID", uid),
                    "agent_id": lyzr_agent_id,
                    "session_id": f"{lyzr_agent_id}-{uid}",
                    "message": f"CONTEXT:\n{ctx_text}\n\nQUESTION: {question}",
                },
                timeout=30.0
            )
            if lyzr_resp.status_code == 200:
                lyzr_answer = lyzr_resp.json().get("response")
        except Exception:
            logger.exception("Lyzr Studio API fallback")

    synthesis = orchestrator.synthesizer.synthesize(
        title=f"Memory Retrieval ({uid})",
        transcript_lines=[{"speaker": m.get("speaker", "Speaker"), "text": m.get("text", ""), "timestamp_str": m.get("timestamp_str", "00:00")} for m in matches]
    )

    final_answer = lyzr_answer or synthesis.get("executive_summary", "No relevant context found.")

    return {
        "answer": final_answer,
        "source": "lyzr_studio_cloud" if lyzr_answer else "lyzr_local_swarm",
        "context": context,
        "action_items": synthesis.get("action_items", []),
        "key_decisions": synthesis.get("key_decisions", [])
    }

@app.post("/api/forget")
@app.delete("/api/memory")
def forget_memory(session_id: str | None = None, point_id: str | None = None):
    """
    Privacy-First Knowledge Control: Deletes specific memory points or entire sessions from Qdrant.
    """
    if not session_id and point_id is None:
        raise HTTPException(status_code=400, detail="Provide session_id or point_id")
    deleted = orchestrator.memory.delete_memory(session_id=session_id, point_id=point_id)
    return {"status": "deleted" if deleted else "not_found", "session_id": session_id, "point_id": point_id}

# â”€â”€â”€ Frontend static files â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)

