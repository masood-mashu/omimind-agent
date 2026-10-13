"""Authenticated Omi connection management and connection-scoped webhooks."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException

from backend.auth import AuthenticatedUser, get_current_user, verify_omi_webhook
from backend.config import settings
from backend.schemas.api_models import MAX_SEGMENT_TEXT_LENGTH, MAX_SEGMENTS_COUNT, MAX_SPEAKER_LENGTH
from backend.shared import cache_processed, orchestrator, parse_transcript
from backend.tenant_store import tenant_store
from backend.webhook_inbox import default_webhook_inbox
from backend.webhook_store import PayloadConflictError

router = APIRouter(tags=["Omi Connections"])


@router.post("/api/omi/connections/pair/start")
def start_pairing(user: AuthenticatedUser = Depends(get_current_user)):
    pair = tenant_store.start_pairing(user.uid)
    pair["webhook_paths"] = {
        "conversation": f"/omi/conversation/{pair['connection_token']}",
        "realtime": f"/omi/realtime/{pair['connection_token']}",
    }
    return pair


@router.post("/api/omi/connections/pair/complete")
def complete_pairing(payload: dict[str, Any], user: AuthenticatedUser = Depends(get_current_user)):
    omi_user_id = str(payload.get("omi_user_id", "")).strip()
    code = str(payload.get("pairing_code", "")).strip()
    if not omi_user_id or not code:
        raise HTTPException(status_code=422, detail="omi_user_id and pairing_code are required.")
    proof = str(payload.get("proof_signature", "")).strip()
    if proof and settings.omi_webhook_secret:
        expected = hmac.new(settings.omi_webhook_secret.encode(), f"{code}.{omi_user_id}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(proof.removeprefix("sha256="), expected):
            raise HTTPException(status_code=401, detail="Invalid Omi pairing proof.")
    try:
        return tenant_store.complete_pairing(user.uid, code, omi_user_id, str(payload.get("device_label", "")).strip() or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/omi/connections")
def list_connections(user: AuthenticatedUser = Depends(get_current_user)):
    return {"connections": tenant_store.list_connections(user.uid)}


@router.post("/api/omi/connections/{connection_id}/rotate")
def rotate_connection(connection_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    try:
        result = tenant_store.rotate_connection(user.uid, connection_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Omi connection not found") from exc
    result["webhook_paths"] = {
        "conversation": f"/omi/conversation/{result['connection_token']}",
        "realtime": f"/omi/realtime/{result['connection_token']}",
    }
    return result


@router.delete("/api/omi/connections/{connection_id}")
def delete_connection(connection_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    if not tenant_store.delete_connection(user.uid, connection_id):
        raise HTTPException(status_code=404, detail="Omi connection not found")
    return {"success": True}


@router.post("/omi/pairing/proof/{connection_token}", status_code=202)
async def pairing_proof(
    connection_token: str,
    payload: dict[str, Any],
    _verified: AuthenticatedUser = Depends(verify_omi_webhook),
):
    """One-time signed Omi callback for mobile clients that cannot call Supabase directly."""
    connection = tenant_store.resolve_pending_connection(connection_token)
    if not connection:
        raise HTTPException(status_code=401, detail="Unknown or expired Omi pairing token.")
    omi_user_id = str(payload.get("omi_user_id") or payload.get("uid") or "").strip()
    code = str(payload.get("pairing_code") or "").strip()
    if not omi_user_id or not code:
        raise HTTPException(status_code=422, detail="Signed pairing proof requires omi_user_id and pairing_code.")
    try:
        result = tenant_store.complete_pairing(connection["owner_id"], code, omi_user_id, str(payload.get("device_label") or "").strip() or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "paired", "connection_id": result["id"]}


def _lines(payload: Any) -> list[dict[str, str]]:
    if isinstance(payload, list):
        segments = payload
    elif isinstance(payload, dict):
        segments = payload.get("transcript_segments") or payload.get("segments") or []
        raw_text = payload.get("transcript") or payload.get("text")
        if raw_text and not segments:
            parsed, _ = parse_transcript(str(raw_text), "Omi User")
            return parsed
    else:
        segments = []
    if len(segments) > MAX_SEGMENTS_COUNT:
        raise HTTPException(status_code=422, detail=f"Segments count exceeds limit of {MAX_SEGMENTS_COUNT}")
    result = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text", "")).strip()
        if text:
            result.append({
                "speaker": str(segment.get("speaker", "Omi User"))[:MAX_SPEAKER_LENGTH],
                "text": text[:MAX_SEGMENT_TEXT_LENGTH],
                "timestamp_str": time.strftime("%H:%M:%S", time.gmtime()),
            })
    return result


def _claim(connection: dict[str, Any], payload: Any, event_id: str | None, session_id: str):
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    try:
        return default_webhook_inbox.record_incoming_event(
            event_id=event_id,
            payload_hash=payload_hash,
            uid=connection["owner_id"],
            session_id=session_id,
            payload=payload,
        )
    except PayloadConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _synthesize(session_id: str, owner_id: str, lines: list[dict[str, str]], title: str):
    run_id = None
    try:
        run_id = tenant_store.create_run(owner_id, session_id, title)
        tenant_store.append_event(owner_id, run_id, {"type": "run_started", "status": "running", "session_id": session_id, "title": title, "execution_source": "actual_backend"})
        retrieved_context = orchestrator.memory.search_memory(
            query=f"Meeting intelligence for {title}",
            limit=min(8, max(1, len(lines))),
            uid=owner_id,
        )
        traces = asyncio.run(orchestrator.swarm.run(uid=owner_id, title=title, transcript=lines, retrieved_context=retrieved_context))
        for trace in traces:
            tenant_store.append_event(owner_id, run_id, {
                "type": "agent_output",
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
        manager = next((trace for trace in traces if trace.role == "manager"), None)
        manager_text = manager.result.text if manager and manager.provider == "lyzr_studio_cloud" else ""
        manager_provider = manager.provider if manager else "unconfigured"
        manager_error = manager.result.error if manager else "Manager trace unavailable"
        summary, action_items = orchestrator.reconcile_meeting_intelligence(
            lyzr_text=manager_text,
            title=title,
            transcript_lines=lines,
        )
        dossier = {
            "session_id": session_id,
            "title": title,
            "indexed_vectors_count": 0,
            "summary": summary,
            "action_items": action_items,
            "email_draft": orchestrator.dispatcher.generate_followup_email(summary, action_items),
            "jira_tickets": orchestrator.dispatcher.generate_jira_tickets(action_items),
            "calendar_events": orchestrator.scheduler.extract_calendar_events(lines),
            "transcript_lines": lines,
            "reasoning": {
                "provider": manager_provider,
                "agent_id": manager.agent_id if manager else None,
                "response": manager_text,
                "error": manager_error,
                "agents": [{"role": trace.role, "agent_id": trace.agent_id, "status": trace.status, "provider": trace.provider, "execution_source": trace.execution_source, "latency_ms": trace.latency_ms, "output": trace.result.text, "error": trace.result.error} for trace in traces],
            },
        }
        cache_processed(session_id, dossier, owner_id)
        tenant_store.complete_run(owner_id, run_id, dossier, provider=manager_provider, transcript_lines=lines)
    except Exception as exc:
        if run_id:
            try:
                tenant_store.fail_run(owner_id, run_id, str(exc))
            except Exception:
                pass


@router.post("/omi/conversation/{connection_token}", status_code=202)
async def conversation_webhook(
    connection_token: str,
    background_tasks: BackgroundTasks,
    payload: Any = Body(...),
):
    connection = tenant_store.resolve_connection(connection_token)
    if not connection:
        raise HTTPException(status_code=401, detail="Unknown or revoked Omi connection.")
    lines = _lines(payload)
    if not lines:
        return {"status": "empty"}
    event_id = None
    if isinstance(payload, dict):
        event_id = payload.get("id") or payload.get("event_id") or payload.get("conversation_id")
    event_id = str(event_id or "") or None
    session_id = f"omi_{connection['owner_id']}_{uuid.uuid4().hex[:12]}"
    duplicate, record = _claim(connection, payload, event_id, session_id)
    if duplicate:
        return {"status": "duplicate", "event_id": event_id, "session_id": record["session_id"]}
    try:
        for index, line in enumerate(lines):
            orchestrator.memory.index_utterance(session_id=session_id, speaker=line["speaker"], text=line["text"], timestamp=float(index * 15), timestamp_str=line["timestamp_str"], topic="omi_webhook", urgency="normal", uid=connection["owner_id"])
        default_webhook_inbox.mark_completed(record["event_key"])
        tenant_store.touch_connection(connection["id"])
    except Exception as exc:
        default_webhook_inbox.mark_failed(record["event_key"], str(exc))
        raise HTTPException(status_code=500, detail="Failed to persist Omi conversation.") from exc
    title = (payload.get("structured") or {}).get("title", "Omi Conversation") if isinstance(payload, dict) else "Omi Conversation"
    background_tasks.add_task(_synthesize, session_id, connection["owner_id"], lines, title)
    return {"status": "accepted", "event_id": event_id, "session_id": session_id}


@router.post("/omi/realtime/{connection_token}", status_code=202)
async def realtime_webhook(
    connection_token: str,
    payload: Any = Body(...),
    session_id: str = "",
):
    connection = tenant_store.resolve_connection(connection_token)
    if not connection:
        raise HTTPException(status_code=401, detail="Unknown or revoked Omi connection.")
    lines = _lines(payload)
    if not lines:
        return {"status": "empty"}
    event_id = None
    if isinstance(payload, dict):
        event_id = payload.get("id") or payload.get("event_id") or payload.get("chunk_id")
    actual_session = session_id or f"realtime_{connection['owner_id']}_{uuid.uuid4().hex[:12]}"
    duplicate, record = _claim(connection, payload, str(event_id) if event_id else None, actual_session)
    if duplicate:
        return {"status": "duplicate", "session_id": record["session_id"]}
    try:
        for index, line in enumerate(lines):
            orchestrator.memory.index_utterance(session_id=actual_session, speaker=line["speaker"], text=line["text"], timestamp=float(index * 15), timestamp_str=line["timestamp_str"], topic="omi_realtime", urgency="normal", uid=connection["owner_id"])
        default_webhook_inbox.mark_completed(record["event_key"])
        tenant_store.touch_connection(connection["id"])
    except Exception as exc:
        default_webhook_inbox.mark_failed(record["event_key"], str(exc))
        raise HTTPException(status_code=500, detail="Failed to persist Omi realtime transcript.") from exc
    return {"status": "accepted", "session_id": actual_session, "indexed_queued": len(lines)}
