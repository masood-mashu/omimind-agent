"""
main.py - FastAPI Application Server for OmiMind Ambient Voice Intelligence
Exposes REST endpoints for Qdrant vector memory, Lyzr agent synthesis, and frontend UI.
"""
import os
import re
import uuid
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.orchestrator import OmiMindOrchestrator
from backend.mock_data import DEMO_MEETINGS

app = FastAPI(
    title="OmiMind - Ambient Voice Memory & Multi-Agent Chief of Staff",
    description="Voice Intelligence powered by Omi ambient audio, Qdrant vector memory, and Lyzr multi-agent framework.",
    version="1.0.0"
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

@app.get("/health")
def health():
    stats = orchestrator.memory.get_stats()
    return {
        "status": "healthy",
        "service": "omimind-agent",
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

@app.post("/api/custom-voice")
def ingest_custom_voice(req: CustomVoiceRequest):
    session_id = f"voice_{uuid.uuid4().hex[:8]}"
    
    # Intelligently parse multi-speaker transcripts or single speaker streams
    raw_blocks = re.split(r"\n+", req.transcript.strip())
    speaker_pattern = re.compile(r"^([A-Z][A-Za-z0-9\s\.\(\)\-_]{1,35}):\s*(.+)$")

    lines = []
    detected_speakers = set()
    current_speaker = req.speaker

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

        # Split sentences preserving abbreviations
        sentences = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"\'\-])", content)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 3:
                lines.append({
                    "speaker": current_speaker,
                    "timestamp_str": time.strftime("%H:%M:%S", time.gmtime()),
                    "text": s_clean
                })

    if not lines:
        lines = [{"speaker": req.speaker, "timestamp_str": "00:01", "text": req.transcript}]

    # Adapt title if generic and multiple stakeholders were identified
    title = req.title
    if title == "Live Omi Voice Memo" and len(detected_speakers) > 1:
        title = "Multi-Stakeholder Operational Sync"

    dossier = orchestrator.process_session(
        session_id=session_id,
        title=title,
        transcript_lines=lines
    )
    processed_cache[session_id] = dossier
    return dossier

@app.post("/api/query")
def query_memory(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return orchestrator.query_semantic_memory(query=req.question, limit=req.limit or 4)

# Mount frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)
