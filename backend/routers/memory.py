"""
memory.py - Qdrant vector memory search, grounding, and privacy purge endpoints
Protected by server-side user authentication and tenant isolation.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.auth import AuthenticatedUser, get_current_user
from backend.mock_data import DEMO_MEETINGS
from backend.schemas.api_models import QueryRequest
from backend.shared import (
    get_processed_for_user,
    iter_processed_for_user,
    orchestrator,
    processed_cache_owners,
)

logger = logging.getLogger("omimind.memory")
router = APIRouter(tags=["Memory & Recall"])


@router.get("/api/meetings")
def get_meetings(user: AuthenticatedUser = Depends(get_current_user)):
    """List preset demo meetings available for offline ingestion and testing."""
    meetings_list = []
    for m in DEMO_MEETINGS.values():
        meetings_list.append({
            "id": m["id"],
            "title": m["title"],
            "category": m["category"],
            "duration": m["duration"],
            "participants": m["participants"],
            "turns_count": len(m["lines"]),
            "processed": processed_cache_owners.get(m["id"]) == user.uid,
        })
    return {"meetings": meetings_list}


@router.get("/api/meetings/{meeting_id}")
def get_meeting_detail(meeting_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve full meeting details including transcript lines and any cached dossier."""
    if meeting_id not in DEMO_MEETINGS:
        raise HTTPException(status_code=404, detail="Meeting not found")
    m = DEMO_MEETINGS[meeting_id]
    cached = get_processed_for_user(meeting_id, user.uid)
    return {
        "id": m["id"],
        "title": m["title"],
        "category": m["category"],
        "duration": m["duration"],
        "participants": m["participants"],
        "lines": m.get("lines", []),
        "processed": cached is not None,
        "dossier": cached,
    }


@router.get("/api/memories")
def get_recent_memories(
    limit: int = 30,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    List recent memories stored in Qdrant ambient memory.
    Scoped strictly to the authenticated user identity.
    """
    bounded_limit = min(100, max(1, limit))
    memories = orchestrator.memory.get_recent_memories(limit=bounded_limit, uid=user.uid)
    return {"memories": memories, "count": len(memories)}


@router.get("/api/actions")
def get_all_actions(user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve all extracted action items across processed meetings."""
    actions = []
    for m_id, dossier in iter_processed_for_user(user.uid):
        if "action_items" in dossier:
            for item in dossier.get("action_items", []):
                act = dict(item)
                act["source_meeting"] = dossier.get("title", m_id)
                act["session_id"] = m_id
                actions.append(act)
    return {"actions": actions, "count": len(actions)}


@router.post("/api/ask")
def ask_memory_endpoint(
    req: QueryRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Conversational Ask endpoint:
    Retrieves grounded memories from Qdrant and synthesizes answers via Lyzr Agent Studio.
    Enforces tenant isolation using the authenticated user identity.
    """
    question = req.question.strip()
    if not question:
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
        recall_res = orchestrator.query_semantic_memory(query=question, limit=req.limit, uid=user.uid)
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
    lyzr_result = orchestrator.lyzr.reason(uid=user.uid, question=question, context=matches)

    if lyzr_result.text and lyzr_result.text.strip():
        final_answer = lyzr_result.text.strip()
        source_provider = lyzr_result.provider
    else:
        final_answer = recall_res.get("answer", "No direct conversational records found in Qdrant.")
        source_provider = "deterministic_fallback" if lyzr_result.provider != "lyzr_studio_cloud" else lyzr_result.provider

    return {
        "question": question,
        "answer": final_answer,
        "source": source_provider,
        "agent_id": lyzr_result.agent_id or "6ac2646b367124ed07f49bdd",
        "matches": matches,
        "relevance_top": recall_res.get("relevance_top", 0.0),
        "reasoning_error": lyzr_result.error,
        "grounded_count": len(matches),
    }


@router.post("/api/seed")
def seed_demo_data(user: AuthenticatedUser = Depends(get_current_user)):
    """Pre-seed all 3 demo meetings into Qdrant under authenticated UID."""
    seeded = []
    for m_id, meeting in DEMO_MEETINGS.items():
        orchestrator.process_session(
            session_id=meeting["id"],
            title=meeting["title"],
            transcript_lines=meeting["lines"],
            uid=user.uid,
            index_memory=True,
        )
        seeded.append(m_id)
    stats = orchestrator.memory.get_stats()
    return {"seeded": seeded, "qdrant_stats": stats}


@router.post("/api/query")
def query_memory(
    req: QueryRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Hybrid semantic vector search over ambient conversational memory.
    Always scopes vector search strictly to the authenticated UID.
    """
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
        res = orchestrator.query_semantic_memory(query=req.question, limit=req.limit, uid=user.uid)
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
def official_ask_endpoint(
    body: dict[str, Any] = Body(...),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Official Guide Endpoint: Retrieves memories from Qdrant and calls Lyzr agent synthesis.
    Scoped strictly to the authenticated server-side UID.
    """
    question = str(body.get("question", "")).strip()
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
        recall_res = orchestrator.query_semantic_memory(query=question, limit=limit, uid=user.uid)
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

    lyzr_result = orchestrator.lyzr.reason(uid=user.uid, question=question, context=matches)

    synthesis = orchestrator.synthesizer.synthesize(
        title=f"Memory Retrieval ({user.uid})",
        transcript_lines=[
            {"speaker": m.get("speaker", "Speaker"), "text": m.get("text", ""), "timestamp_str": m.get("timestamp_str", "00:00")}
            for m in matches
        ],
    )

    final_answer = lyzr_result.text or synthesis.get("executive_summary", "No relevant context found.")
    source_provider = lyzr_result.provider if (lyzr_result.text and lyzr_result.provider == "lyzr_studio_cloud") else "deterministic_fallback"

    return {
        "answer": final_answer,
        "source": source_provider,
        "context": context,
        "reasoning_error": lyzr_result.error,
        "action_items": synthesis.get("action_items", []),
        "key_decisions": synthesis.get("key_decisions", []),
    }


@router.post("/api/forget")
@router.delete("/api/memory")
async def forget_memory(
    request: Request,
    session_id: str | None = None,
    point_id: str | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Privacy-First Knowledge Control: Deletes specific memory points or entire sessions from Qdrant.
    Enforces strict ownership checks; rejects deletion when a target belongs to another user.
    """
    target_session_id = session_id
    target_point_id = point_id
    if not target_session_id and target_point_id is None:
        try:
            body = await request.json()
            if isinstance(body, dict):
                target_session_id = body.get("session_id")
                target_point_id = body.get("point_id")
        except Exception:
            pass

    if not target_session_id and target_point_id is None:
        raise HTTPException(status_code=400, detail="Provide session_id or point_id")

    try:
        deleted = orchestrator.memory.delete_memory(
            session_id=target_session_id, point_id=target_point_id, uid=user.uid
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Cannot delete memory belonging to another user.") from exc

    return {"status": "deleted" if deleted else "not_found", "session_id": target_session_id, "point_id": target_point_id}
