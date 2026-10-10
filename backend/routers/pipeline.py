import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from backend.auth import AuthenticatedUser, get_current_user
from backend.mock_data import DEMO_MEETINGS
from backend.schemas.api_models import CustomVoiceRequest, ProcessRequest
from backend.shared import cache_processed, orchestrator, parse_transcript

logger = logging.getLogger("omimind.pipeline")
router = APIRouter(tags=["pipeline"])


@router.post("/api/process")
def process_meeting(req: ProcessRequest, user: AuthenticatedUser = Depends(get_current_user)):
    if req.meeting_id not in DEMO_MEETINGS:
        raise HTTPException(status_code=404, detail="Meeting not found")

    stats = orchestrator.memory.get_stats()
    if stats.get("embedding_health", {}).get("status") != "ready":
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "EMBEDDING_SERVICE_DEGRADED",
                    "message": "Semantic memory or embedding provider is currently degraded or unavailable.",
                    "status_code": 503,
                },
                "detail": "Semantic embedding provider unavailable",
            },
        )

    meeting = DEMO_MEETINGS[req.meeting_id]
    session_id = str(meeting["id"])
    title = str(meeting["title"])
    transcript_lines: list[dict[str, Any]] = meeting.get("lines", [])
    try:
        dossier = orchestrator.process_session(
            session_id=session_id,
            title=title,
            transcript_lines=transcript_lines,
            uid=user.uid,
            index_memory=True,
        )
        cache_processed(session_id, dossier, user.uid)
        return dossier
    except Exception as exc:
        logger.error(f"Process meeting error: {exc}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "PROCESSING_FAILED",
                    "message": "Failed to process meeting due to memory backend error.",
                    "status_code": 503,
                },
                "detail": "Processing failed due to memory backend error",
            },
        )


async def _stream_pipeline(
    session_id: str,
    title: str,
    lines: list[dict],
    uid: str = "default_user",
) -> AsyncGenerator[str, None]:
    """Yields SSE events for each agent stage so the frontend can animate them."""

    def sse(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    try:
        emb_health = getattr(orchestrator.memory.embedding_model, "check_health", lambda: {"status": "ready"})()
        if emb_health.get("status") != "ready":
            yield sse({
                "type": "error",
                "stage": 1,
                "agent": "MemoryAgent",
                "stage_name": "Qdrant Memory Indexing",
                "status": "error",
                "message": "Semantic embedding provider is currently degraded or unavailable.",
            })
            return

        # Stage 1: Memory / Qdrant indexing
        yield sse({
            "stage": 1,
            "agent": "MemoryAgent",
            "stage_name": "Qdrant Memory Indexing",
            "status": "running",
            "message": f"Indexing {len(lines)} utterances into persistent Qdrant vector store...",
        })

        indexed_points = []
        for i, line in enumerate(lines):
            p_id = orchestrator.memory.index_utterance(
                session_id=session_id,
                speaker=line.get("speaker", "Speaker"),
                text=line.get("text", ""),
                timestamp=float(i * 15),
                timestamp_str=line.get("timestamp_str", f"00:{i*15:02d}"),
                topic=line.get("topic", "general"),
                urgency=line.get("urgency", "normal"),
                uid=uid,
            )
            indexed_points.append(p_id)

        yield sse({
            "stage": 1,
            "agent": "MemoryAgent",
            "stage_name": "Qdrant Memory Indexing",
            "status": "done",
            "message": f"{len(indexed_points)} vectors stored in {orchestrator.memory.collection_name} collection.",
            "count": len(indexed_points),
        })

        # Stage 2: Qdrant Retrieval
        yield sse({
            "stage": 2,
            "agent": "QdrantRetrieval",
            "stage_name": "Qdrant Retrieval",
            "status": "running",
            "message": "Retrieving relevant meeting context from persistent Qdrant memory...",
        })
        retrieved_context = orchestrator.memory.search_memory(
            query=f"Meeting intelligence for {title}",
            limit=min(8, max(1, len(lines))),
            uid=uid,
        )
        yield sse({
            "stage": 2,
            "agent": "QdrantRetrieval",
            "stage_name": "Qdrant Retrieval",
            "status": "done",
            "message": f"{len(retrieved_context)} relevant transcript memories retrieved.",
            "count": len(retrieved_context),
        })

        # Stage 3: Lyzr Manager Reasoning (Non-blocking async call)
        yield sse({
            "stage": 3,
            "agent": "LyzrManager",
            "stage_name": "Configured Lyzr Manager",
            "status": "running",
            "message": "Invoking Configured Lyzr Manager (delegation depends on Lyzr Studio configuration)...",
        })
        lyzr_result = await orchestrator.lyzr.areason(
            uid=uid,
            question="Produce grounded meeting intelligence from the supplied transcript context.",
            context=retrieved_context,
        )
        yield sse({
            "stage": 3,
            "agent": "LyzrManager",
            "stage_name": "Configured Lyzr Manager",
            "status": "done",
            "message": f"Reasoning provider: {lyzr_result.provider}.",
            "provider": lyzr_result.provider,
            "error": lyzr_result.error,
        })

        # Stage 4: Deterministic Normalization & Validation
        yield sse({
            "stage": 4,
            "agent": "ActionExtractor",
            "stage_name": "Deterministic Normalization & Validation",
            "status": "running",
            "message": "Normalizing multi-agent outputs, verbal commitments, and Jira schemas...",
        })

        summary, action_items = orchestrator.reconcile_meeting_intelligence(
            lyzr_text=lyzr_result.text if lyzr_result.provider == "lyzr_studio_cloud" else "",
            title=title,
            transcript_lines=lines,
        )
        decisions_found = len([d for d in summary.get("key_decisions", []) if "Consensus" not in d])
        risks_found = len([r for r in summary.get("risks_and_blockers", []) if "No critical" not in r])

        yield sse({
            "stage": 4,
            "agent": "ActionExtractor",
            "stage_name": "Deterministic Normalization & Validation",
            "status": "done",
            "message": f"{len(action_items)} action item{'s' if len(action_items) != 1 else ''} validated, {decisions_found} decision{'s' if decisions_found != 1 else ''} confirmed, {risks_found} risk{'s' if risks_found != 1 else ''} flagged.",
            "count": len(action_items),
        })

        # Stage 5: User-controlled Draft Outputs
        yield sse({
            "stage": 5,
            "agent": "TaskDispatcher",
            "stage_name": "User-controlled Draft Outputs",
            "status": "running",
            "message": "Preparing draft outputs (follow-up email, Jira tickets, calendar invites)...",
        })

        email_draft = orchestrator.dispatcher.generate_followup_email(summary, action_items)
        jira_tickets = orchestrator.dispatcher.generate_jira_tickets(action_items)
        calendar_events = orchestrator.scheduler.extract_calendar_events(lines)

        yield sse({
            "stage": 5,
            "agent": "TaskDispatcher",
            "stage_name": "User-controlled Draft Outputs",
            "status": "done",
            "message": f"Drafts prepared: Email, {len(jira_tickets)} Jira ticket{'s' if len(jira_tickets) != 1 else ''}, {len(calendar_events)} calendar event{'s' if len(calendar_events) != 1 else ''}.",
            "count": len(jira_tickets),
        })

        # Final: complete dossier
        dossier = {
            "session_id": session_id,
            "title": title,
            "indexed_vectors_count": len(indexed_points),
            "summary": summary,
            "action_items": action_items,
            "email_draft": email_draft,
            "jira_tickets": jira_tickets,
            "calendar_events": calendar_events,
            "reasoning": {
                "provider": lyzr_result.provider,
                "agent_id": lyzr_result.agent_id,
                "response": lyzr_result.text,
                "error": lyzr_result.error,
            },
        }
        cache_processed(session_id, dossier, uid)
        yield sse({"type": "complete", "dossier": dossier})

    except Exception as exc:
        logger.error(f"Pipeline execution failed: {exc}")
        yield sse({
            "type": "error",
            "agent": "PipelineCoordinator",
            "status": "error",
            "message": "Pipeline processing failed during execution.",
            "detail": "Memory or processing service encountered an error.",
        })


@router.post("/api/process-stream")
async def process_meeting_stream(req: ProcessRequest, user: AuthenticatedUser = Depends(get_current_user)):
    if req.meeting_id not in DEMO_MEETINGS:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting = DEMO_MEETINGS[req.meeting_id]
    session_id = str(meeting["id"])
    title = str(meeting["title"])
    lines: list[dict] = meeting.get("lines", [])
    return StreamingResponse(
        _stream_pipeline(session_id, title, lines, uid=user.uid),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/custom-voice-stream")
async def ingest_custom_voice_stream(req: CustomVoiceRequest, user: AuthenticatedUser = Depends(get_current_user)):
    session_id = f"voice_{uuid.uuid4().hex[:8]}"
    lines, detected_speakers = parse_transcript(req.transcript, req.speaker)
    if not lines:
        lines = [{"speaker": req.speaker, "timestamp_str": "00:01", "text": req.transcript}]
    title = req.title
    if title == "Live Omi Voice Memo" and len(detected_speakers) > 1:
        title = "Multi-Stakeholder Operational Sync"
    return StreamingResponse(
        _stream_pipeline(session_id, title, lines, uid=user.uid),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/custom-voice")
def ingest_custom_voice(req: CustomVoiceRequest, user: AuthenticatedUser = Depends(get_current_user)):
    session_id = f"voice_{uuid.uuid4().hex[:8]}"
    lines, detected_speakers = parse_transcript(req.transcript, req.speaker)
    if not lines:
        lines = [{"speaker": req.speaker, "timestamp_str": "00:01", "text": req.transcript}]
    title = req.title
    if title == "Live Omi Voice Memo" and len(detected_speakers) > 1:
        title = "Multi-Stakeholder Operational Sync"
    dossier = orchestrator.process_session(
        session_id=session_id,
        title=title,
        transcript_lines=lines,
        uid=user.uid,
        index_memory=True,
    )
    cache_processed(session_id, dossier, user.uid)
    return dossier
