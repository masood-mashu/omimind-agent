"""
memory.py - Qdrant vector memory search, grounding, and privacy purge endpoints
"""
import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse

from backend.mock_data import DEMO_MEETINGS
from backend.schemas.api_models import QueryRequest
from backend.shared import orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Memory & Recall"])


@router.get("/api/meetings")
def get_meetings():
    """List preset demo meetings available for offline ingestion and testing."""
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


@router.post("/api/seed")
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


@router.post("/api/query")
def query_memory(req: QueryRequest):
    """Hybrid semantic vector search over ambient conversational memory."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    stats = orchestrator.memory.get_stats()
    if stats.get("embedding_health", {}).get("status") != "ready":
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "EMBEDDING_SERVICE_DEGRADED",
                    "message": "Semantic memory search is temporarily unavailable.",
                    "status_code": 503,
                },
                "detail": "Semantic embedding provider unavailable",
            },
        )

    try:
        res = orchestrator.query_semantic_memory(query=req.question, limit=req.limit, uid=req.uid)
        return res
    except Exception as exc:
        logger.error(f"Query memory error: {exc}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "RETRIEVAL_FAILED",
                    "message": "Failed to retrieve memories from vector database.",
                    "status_code": 503,
                },
                "detail": "Vector retrieval failed",
            },
        )


@router.post("/ask")
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

    stats = orchestrator.memory.get_stats()
    if stats.get("embedding_health", {}).get("status") != "ready":
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "EMBEDDING_SERVICE_DEGRADED",
                    "message": "Semantic memory search is temporarily unavailable.",
                    "status_code": 503,
                },
                "detail": "Semantic embedding provider unavailable",
            },
        )

    try:
        recall_res = orchestrator.query_semantic_memory(query=question, limit=limit, uid=uid)
    except Exception as exc:
        logger.error(f"Ask query error: {exc}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "RETRIEVAL_FAILED",
                    "message": "Failed to retrieve memories from vector database.",
                    "status_code": 503,
                },
                "detail": "Vector retrieval failed",
            },
        )

    matches = recall_res.get("matches", [])
    context = [f"[{m.get('speaker', 'Speaker')}]: {m.get('text', '')}" for m in matches]

    lyzr_result = orchestrator.lyzr.reason(uid=uid, question=question, context=matches)

    synthesis = orchestrator.synthesizer.synthesize(
        title=f"Memory Retrieval ({uid})",
        transcript_lines=[{"speaker": m.get("speaker", "Speaker"), "text": m.get("text", ""), "timestamp_str": m.get("timestamp_str", "00:00")} for m in matches]
    )

    final_answer = lyzr_result.text or synthesis.get("executive_summary", "No relevant context found.")

    return {
        "answer": final_answer,
        "source": lyzr_result.provider,
        "context": context,
        "reasoning_error": lyzr_result.error,
        "action_items": synthesis.get("action_items", []),
        "key_decisions": synthesis.get("key_decisions", [])
    }


@router.post("/api/forget")
@router.delete("/api/memory")
def forget_memory(session_id: str | None = None, point_id: str | None = None):
    """
    Privacy-First Knowledge Control: Deletes specific memory points or entire sessions from Qdrant.
    """
    if not session_id and point_id is None:
        raise HTTPException(status_code=400, detail="Provide session_id or point_id")
    deleted = orchestrator.memory.delete_memory(session_id=session_id, point_id=point_id)
    return {"status": "deleted" if deleted else "not_found", "session_id": session_id, "point_id": point_id}
