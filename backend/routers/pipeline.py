import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from agents.lyzr_client import LyzrResult
from backend.auth import AuthenticatedUser, get_current_user
from backend.mock_data import DEMO_MEETINGS
from backend.schemas.api_models import CustomVoiceRequest, ProcessRequest
from backend.shared import cache_processed, orchestrator, parse_transcript
from backend.tenant_store import tenant_store

logger = logging.getLogger("omimind.pipeline")
router = APIRouter(tags=["pipeline"])


def _process_sync_swarm(session_id: str, title: str, lines: list[dict], uid: str) -> dict[str, Any]:
    run_id = tenant_store.create_run(uid, session_id, title)
    try:
        tenant_store.append_event(uid, run_id, {"type": "run_started", "status": "running", "session_id": session_id, "title": title, "execution_source": "actual_backend"})
        indexed_points = [
            orchestrator.memory.index_utterance(
                session_id=session_id,
                speaker=line.get("speaker", "Speaker"),
                text=line.get("text", ""),
                timestamp=float(index * 15),
                timestamp_str=line.get("timestamp_str", f"00:{index * 15:02d}"),
                topic=line.get("topic", "general"),
                urgency=line.get("urgency", "normal"),
                uid=uid,
            )
            for index, line in enumerate(lines)
        ]
        context = orchestrator.memory.search_memory(query=f"Meeting intelligence for {title}", limit=min(8, max(1, len(lines))), uid=uid)
        traces = asyncio.run(orchestrator.swarm.run(uid=uid, title=title, transcript=lines, retrieved_context=context))
        for trace in traces:
            tenant_store.append_event(uid, run_id, {
                "type": "agent_output", "role": trace.role, "agent": trace.role,
                "agent_id": trace.agent_id, "status": trace.status, "provider": trace.provider,
                "execution_source": trace.execution_source, "latency_ms": trace.latency_ms,
                "started_at": trace.started_at, "completed_at": trace.completed_at,
                "input_summary": trace.input_summary, "evidence_ids": trace.evidence_ids or [],
                "output": trace.result.text[:3000] if trace.result.text else None, "error": trace.result.error,
            })
        manager = next((trace for trace in traces if trace.role == "manager"), None)
        manager_text = manager.result.text if manager and manager.provider == "lyzr_studio_cloud" else ""
        summary, action_items = orchestrator.reconcile_meeting_intelligence(lyzr_text=manager_text, title=title, transcript_lines=lines)
        provider = manager.provider if manager else "unconfigured"
        dossier = {
            "session_id": session_id, "title": title, "indexed_vectors_count": len(indexed_points),
            "summary": summary, "action_items": action_items,
            "email_draft": orchestrator.dispatcher.generate_followup_email(summary, action_items),
            "jira_tickets": orchestrator.dispatcher.generate_jira_tickets(action_items),
            "calendar_events": orchestrator.scheduler.extract_calendar_events(lines),
            "transcript_lines": lines,
            "reasoning": {"provider": provider, "agent_id": manager.agent_id if manager else None, "response": manager_text, "error": manager.result.error if manager else "Manager trace unavailable", "agents": [{"role": trace.role, "agent_id": trace.agent_id, "status": trace.status, "provider": trace.provider, "execution_source": trace.execution_source, "latency_ms": trace.latency_ms, "output": trace.result.text, "error": trace.result.error} for trace in traces]},
        }
        tenant_store.complete_run(uid, run_id, dossier, provider=provider, transcript_lines=lines)
        cache_processed(session_id, dossier, uid)
        return dossier
    except Exception as exc:
        tenant_store.fail_run(uid, run_id, str(exc))
        raise


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
        dossier = _process_sync_swarm(session_id, title, transcript_lines, user.uid)
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
    uid: str = "",
) -> AsyncGenerator[str, None]:
    """Yields SSE events for each agent stage so the frontend can animate them."""

    def sse(data: dict) -> str:
        data.setdefault("execution_source", "actual_backend")
        return f"data: {json.dumps(data)}\n\n"

    run_id = tenant_store.create_run(uid, session_id, title)

    def emit(data: dict[str, Any]) -> str:
        data.setdefault("run_id", run_id)
        data.setdefault("execution_source", "actual_backend")
        tenant_store.append_event(uid, run_id, data)
        return sse(data)

    try:
        yield emit({"type": "run_started", "status": "running", "session_id": session_id, "title": title, "message": "Meeting run started."})
        emb_health = getattr(orchestrator.memory.embedding_model, "check_health", lambda: {"status": "ready"})()
        if emb_health.get("status") != "ready":
            yield emit({
                "type": "error",
                "stage": 1,
                "agent": "MemoryAgent",
                "stage_name": "Qdrant Memory Indexing",
                "status": "error",
                "message": "Semantic embedding provider is currently degraded or unavailable.",
            })
            tenant_store.fail_run(uid, run_id, "Semantic embedding provider unavailable")
            return

        # Stage 1: Memory / Qdrant indexing
        yield emit({
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

        yield emit({
            "stage": 1,
            "agent": "MemoryAgent",
            "stage_name": "Qdrant Memory Indexing",
            "status": "done",
            "message": f"{len(indexed_points)} vectors stored in {orchestrator.memory.collection_name} collection.",
            "count": len(indexed_points),
        })

        # Stage 2: Qdrant Retrieval
        yield emit({
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
        yield emit({
            "stage": 2,
            "agent": "QdrantRetrieval",
            "stage_name": "Qdrant Retrieval",
            "status": "done",
            "message": f"{len(retrieved_context)} relevant transcript memories retrieved.",
            "count": len(retrieved_context),
        })

        # Stage 3: observable role-specific Lyzr swarm.
        yield emit({
            "stage": 3,
            "agent": "LyzrSwarm",
            "stage_name": "Lyzr multi-agent reasoning",
            "status": "running",
            "message": "Running memory recall, meeting analysis, action extraction, manager synthesis, and follow-up planning.",
            "provider": "pending",
        })
        traces = []
        for role in ("memory_recall", "meeting_analyst", "action_extractor", "manager", "followup_planner"):
            yield emit({"type": "agent_started", "stage": 3, "role": role, "agent": role, "status": "running", "message": f"Starting {role.replace('_', ' ').title()} agent."})
        async for trace in orchestrator.swarm.stream(uid=uid, title=title, transcript=lines, retrieved_context=retrieved_context):
            traces.append(trace)
            yield emit({
                "type": "agent_output",
                "stage": 3,
                "role": trace.role,
                "agent": trace.role,
                "agent_id": trace.agent_id,
                "status": trace.status,
                "provider": trace.provider,
                "execution_source": trace.execution_source,
                "started_at": trace.started_at,
                "completed_at": trace.completed_at,
                "latency_ms": trace.latency_ms,
                "input_summary": trace.input_summary,
                "evidence_ids": trace.evidence_ids or [],
                "output": trace.result.text[:3000] if trace.result.text else None,
                "error": trace.result.error,
            })
            yield emit({
                "type": "agent_completed" if trace.status == "completed" else "agent_failed",
                "stage": 3,
                "role": trace.role,
                "agent": trace.role,
                "agent_id": trace.agent_id,
                "status": trace.status,
                "provider": trace.provider,
                "execution_source": trace.execution_source,
                "latency_ms": trace.latency_ms,
                "output": trace.result.text[:3000] if trace.result.text else None,
                "error": trace.result.error,
                "message": f"{trace.role.replace('_', ' ').title()} {trace.status} via {trace.provider}.",
            })
        trace_by_role = {trace.role: trace for trace in traces}
        manager_trace = trace_by_role.get("manager")
        lyzr_result = manager_trace.result if manager_trace else LyzrResult(text="", provider="unconfigured", agent_id=None, error="Manager trace unavailable")
        manager_text = lyzr_result.text if hasattr(lyzr_result, "text") and lyzr_result.provider == "lyzr_studio_cloud" else ""
        manager_provider = lyzr_result.provider if hasattr(lyzr_result, "provider") else "deterministic_fallback"
        manager_agent_id = lyzr_result.agent_id if hasattr(lyzr_result, "agent_id") else None
        manager_error = lyzr_result.error if hasattr(lyzr_result, "error") else "Manager trace unavailable"
        swarm_ok = manager_provider == "lyzr_studio_cloud"
        yield emit({"type": "agent_completed" if swarm_ok else "agent_failed", "stage": 3, "agent": "LyzrSwarm", "status": "completed" if swarm_ok else "failed", "provider": manager_provider, "execution_source": "actual_backend" if swarm_ok else "deterministic_fallback", "error": None if swarm_ok else manager_error, "message": "Lyzr swarm trace complete." if swarm_ok else "Lyzr provider unavailable; deterministic fallback is clearly marked."})

        # Stage 4: Deterministic Normalization & Validation
        yield emit({
            "stage": 4,
            "agent": "ActionExtractor",
            "stage_name": "Deterministic Normalization & Validation",
            "status": "running",
            "message": "Normalizing multi-agent outputs, verbal commitments, and Jira schemas...",
        })

        summary, action_items = orchestrator.reconcile_meeting_intelligence(
            lyzr_text=manager_text,
            title=title,
            transcript_lines=lines,
        )
        decisions_found = len([d for d in summary.get("key_decisions", []) if "Consensus" not in d])
        risks_found = len([r for r in summary.get("risks_and_blockers", []) if "No critical" not in r])

        yield emit({
            "stage": 4,
            "agent": "ActionExtractor",
            "stage_name": "Deterministic Normalization & Validation",
            "status": "done",
            "message": f"{len(action_items)} action item{'s' if len(action_items) != 1 else ''} validated, {decisions_found} decision{'s' if decisions_found != 1 else ''} confirmed, {risks_found} risk{'s' if risks_found != 1 else ''} flagged.",
            "count": len(action_items),
        })

        # Stage 5: User-controlled Draft Outputs
        yield emit({
            "stage": 5,
            "agent": "TaskDispatcher",
            "stage_name": "User-controlled Draft Outputs",
            "status": "running",
            "message": "Preparing draft outputs (follow-up email, Jira tickets, calendar invites)...",
        })

        email_draft = orchestrator.dispatcher.generate_followup_email(summary, action_items)
        jira_tickets = orchestrator.dispatcher.generate_jira_tickets(action_items)
        calendar_events = orchestrator.scheduler.extract_calendar_events(lines)

        yield emit({
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
                "provider": manager_provider,
                "agent_id": manager_agent_id,
                "response": manager_text,
                "error": manager_error,
                "agents": [
                    {"role": trace.role, "agent_id": trace.agent_id, "status": trace.status, "provider": trace.provider, "execution_source": trace.execution_source, "latency_ms": trace.latency_ms, "started_at": trace.started_at, "completed_at": trace.completed_at, "input_summary": trace.input_summary, "evidence_ids": trace.evidence_ids or [], "output": trace.result.text, "error": trace.result.error}
                    for trace in traces
                ],
            },
        }
        dossier["transcript_lines"] = lines
        cache_processed(session_id, dossier, uid)
        tenant_store.complete_run(uid, run_id, dossier, provider=manager_provider, transcript_lines=lines)
        yield emit({"type": "pipeline_completed", "status": "completed", "dossier": dossier})

    except Exception as exc:
        try:
            tenant_store.fail_run(uid, run_id, str(exc))
        except Exception:
            logger.exception("Failed to persist failed pipeline run %s", run_id)
        logger.error(f"Pipeline execution failed: {exc}")
        try:
            yield emit({
                "type": "error",
                "agent": "PipelineCoordinator",
                "status": "error",
                "message": "Pipeline processing failed during execution.",
                "detail": "Memory or processing service encountered an error.",
            })
        except Exception:
            logger.exception("Failed to persist pipeline error event %s", run_id)


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
    dossier = _process_sync_swarm(session_id, title, lines, user.uid)
    return dossier
