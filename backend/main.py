"""
main.py - FastAPI Application Server for OmiMind Ambient Voice Intelligence
Exposes REST endpoints for Qdrant vector memory, Lyzr agent synthesis, and frontend UI.
"""
import os
import re
import uuid
import time
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.orchestrator import OmiMindOrchestrator
from agents.memory_agent import QdrantMemoryAgent
from agents.action_extractor import LyzrActionExtractor
from agents.executive_synth import LyzrExecutiveSynthesizer
from agents.task_dispatcher import LyzrTaskDispatcher
from backend.mock_data import DEMO_MEETINGS

app = FastAPI(
    title="OmiMind - Ambient Voice Memory & Multi-Agent Chief of Staff",
    description="Voice Intelligence powered by Omi ambient audio, Qdrant vector memory, and Lyzr multi-agent framework.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize persistent orchestrator
orchestrator = OmiMindOrchestrator(storage_path="./qdrant_storage")

# Active processed sessions cache
processed_cache: Dict[str, Any] = {}

class ProcessRequest(BaseModel):
    meeting_id: str

class CustomVoiceRequest(BaseModel):
    title: str = "Live Omi Voice Memo"
    speaker: str = "User"
    transcript: str

class QueryRequest(BaseModel):
    question: str
    limit: Optional[int] = 4

class OmiWebhookRequest(BaseModel):
    """Native Omi device webhook payload format."""
    session_id: Optional[str] = None
    segments: Optional[List[Dict[str, Any]]] = None
    # Also accept flat transcript format
    transcript: Optional[str] = None
    speaker: Optional[str] = "Omi User"

# â”€â”€â”€ Helper: parse raw transcript blocks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def parse_transcript(transcript: str, default_speaker: str = "User") -> tuple[List[Dict], set]:
    raw_blocks = re.split(r"\n+", transcript.strip())
    speaker_pattern = re.compile(r"^([A-Z][A-Za-z0-9\s\.\(\)\-_]{1,35}):\s*(.+)$")
    lines = []
    detected_speakers = set()
    current_speaker = default_speaker

    for block in raw_blocks:
        block_str = block.strip()
        if not block_str:
            continue
        m = speaker_pattern.match(block_str)
        if m:
            current_speaker = m.group(1).strip()
            content = m.group(2).strip()
            detected_speakers.add(current_speaker)
        else:
            content = block_str

        sentences = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"'\-])", content)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 3:
                lines.append({
                    "speaker": current_speaker,
                    "timestamp_str": time.strftime("%H:%M:%S", time.gmtime()),
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
    for m_id, m in DEMO_MEETINGS.items():
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
    dossier = orchestrator.process_session(
        session_id=meeting["id"],
        title=meeting["title"],
        transcript_lines=meeting["lines"]
    )
    processed_cache[meeting["id"]] = dossier
    return dossier

# â”€â”€â”€ SSE Streaming Pipeline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _stream_pipeline(session_id: str, title: str, lines: List[Dict]) -> AsyncGenerator[str, None]:
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

    # Final: complete dossier
    dossier = {
        "session_id": session_id,
        "title": title,
        "indexed_vectors_count": len(indexed_points),
        "summary": summary,
        "action_items": action_items,
        "email_draft": email_draft,
        "jira_tickets": jira_tickets
    }
    processed_cache[session_id] = dossier
    yield sse({"type": "complete", "dossier": dossier})

@app.post("/api/process-stream")
async def process_meeting_stream(req: ProcessRequest):
    if req.meeting_id not in DEMO_MEETINGS:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting = DEMO_MEETINGS[req.meeting_id]
    return StreamingResponse(
        _stream_pipeline(meeting["id"], meeting["title"], meeting["lines"]),
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
    return orchestrator.query_semantic_memory(query=req.question, limit=req.limit or 4)

# â”€â”€â”€ Frontend static files â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)

