"""
webhooks.py - Omi Wearable device webhooks and conversation ingestion endpoints
Hardened for tenant isolation, constant-time verification, idempotency, and collision protection.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import time
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException

from backend.auth import AuthenticatedUser, verify_omi_webhook
from backend.schemas.api_models import (
    MAX_SEGMENT_TEXT_LENGTH,
    MAX_SEGMENTS_COUNT,
    MAX_SPEAKER_LENGTH,
    MAX_TIMESTAMP_SECONDS,
    MAX_TRANSCRIPT_LENGTH,
    OmiWebhookRequest,
)
from backend.shared import cache_processed, orchestrator, parse_transcript, register_wearable_uid
from backend.webhook_inbox import default_webhook_inbox

logger = logging.getLogger("omimind.webhooks")
router = APIRouter(tags=["Omi Webhooks"])


def _process_omi_webhook_synthesis(session_id: str, lines: list[dict[str, Any]], uid: str = "default_user") -> None:
    try:
        dossier = orchestrator.process_session(
            session_id=session_id,
            title="Omi Live Session",
            transcript_lines=lines,
            uid=uid,
            index_memory=False,
        )
        cache_processed(session_id, dossier, uid)
    except Exception as exc:
        logger.error(f"Background synthesis of Omi webhook failed: {exc}")


@router.post("/api/omi-webhook", status_code=202)
def omi_webhook(
    req: OmiWebhookRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(verify_omi_webhook),
):
    """
    Native Omi device webhook endpoint.
    Protected by verified webhook credentials; derives server-side user identity.
    Accepts Omi's standard segment payload or a flat transcript string.
    Guarantees persistence into SQLite inbox and vector storage before acknowledging with HTTP 202.
    """
    event_id = req.event_id or req.session_id
    session_id = req.session_id or req.event_id or f"omi_{uuid.uuid4().hex[:8]}"
    uid = user.uid

    if req.segments:
        if len(req.segments) > MAX_SEGMENTS_COUNT:
            raise HTTPException(status_code=422, detail=f"Segments count exceeds limit of {MAX_SEGMENTS_COUNT}")
        lines = []
        for seg in req.segments:
            text = str(seg.get("text", "")).strip()
            if len(text) > 3:
                start_sec = int(seg.get("start", 0))
                lines.append({
                    "speaker": str(seg.get("speaker", req.speaker or "Omi User"))[:MAX_SPEAKER_LENGTH],
                    "timestamp_str": f"{start_sec // 60:02d}:{start_sec % 60:02d}",
                    "text": text[:MAX_SEGMENT_TEXT_LENGTH],
                })
    elif req.transcript:
        lines, _ = parse_transcript(req.transcript[:MAX_TRANSCRIPT_LENGTH], req.speaker or "Omi User")
    else:
        raise HTTPException(status_code=400, detail="Provide either 'segments' or 'transcript'")

    if not lines:
        raise HTTPException(status_code=400, detail="No valid utterances found in payload")

    payload_dict = req.model_dump(mode="json")
    payload_hash = hashlib.sha256(
        json.dumps(payload_dict, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    # 1. Check and record in durable inbox before processing
    is_dup, record = default_webhook_inbox.record_incoming_event(
        event_id=event_id,
        payload_hash=payload_hash,
        uid=uid,
        session_id=session_id,
        payload=payload_dict,
    )
    if is_dup:
        return {
            "status": "duplicate",
            "message": "Webhook event already processed",
            "session_id": record["session_id"],
            "vectors_queued": 0,
        }

    # 2. Synchronous persistence before acknowledgement: index utterances
    try:
        for i, line in enumerate(lines):
            orchestrator.memory.index_utterance(
                session_id=session_id,
                speaker=line.get("speaker", req.speaker or "Omi User"),
                text=line.get("text", ""),
                timestamp=float(i * 15),
                timestamp_str=line.get("timestamp_str", "live"),
                topic="omi_webhook",
                urgency="normal",
                uid=uid,
            )
        default_webhook_inbox.mark_completed(record["event_key"])
    except Exception as exc:
        default_webhook_inbox.mark_failed(record["event_key"], str(exc))
        logger.error(f"Failed to persist webhook utterances: {exc}")
        raise HTTPException(status_code=500, detail="Failed to persist webhook utterances") from exc

    # 3. Schedule background executive synthesis dossier generation (index_memory=False to prevent duplicate vectors)
    background_tasks.add_task(_process_omi_webhook_synthesis, session_id, lines, uid)
    return {"status": "accepted", "session_id": session_id, "vectors_queued": len(lines)}


def _process_omi_conversation(session_id: str, uid: str, lines: list[dict[str, Any]], title: str) -> None:
    try:
        # Utterances were already indexed synchronously; skip re-indexing (index_memory=False)
        dossier = orchestrator.process_session(
            session_id=session_id,
            title=title,
            transcript_lines=lines,
            uid=uid,
            index_memory=False,
        )
        cache_processed(dossier["session_id"], dossier, uid)
    except Exception as exc:
        logger.error(f"Failed to produce background conversation dossier: {exc}")


def _extract_lines_from_payload(payload: Any) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    overview = ""
    segments: list[Any] = []

    if isinstance(payload, list):
        segments = payload
    elif isinstance(payload, dict):
        segments = payload.get("transcript_segments") or payload.get("segments") or []
        overview = (payload.get("structured") or {}).get("overview", "")
        raw_text = payload.get("transcript") or payload.get("text") or (payload.get("conversation") or {}).get("transcript")
        if raw_text and not segments:
            parsed_lines, _ = parse_transcript(str(raw_text)[:MAX_TRANSCRIPT_LENGTH], "Omi User")
            lines.extend(parsed_lines)

    if len(segments) > MAX_SEGMENTS_COUNT:
        raise HTTPException(status_code=422, detail=f"Segments count exceeds limit of {MAX_SEGMENTS_COUNT}")

    for s in segments:
        now_ts = time.strftime("%H:%M:%S", time.gmtime())
        if isinstance(s, dict):
            text = str(s.get("text", "")).strip()
            if text:
                lines.append({
                    "speaker": str(s.get("speaker", "Omi User"))[:MAX_SPEAKER_LENGTH],
                    "text": text[:MAX_SEGMENT_TEXT_LENGTH],
                    "timestamp_str": now_ts,
                })
        elif isinstance(s, str) and s.strip():
            lines.append({
                "speaker": "Omi User",
                "text": s.strip()[:MAX_SEGMENT_TEXT_LENGTH],
                "timestamp_str": now_ts,
            })

    if not lines and overview:
        lines = [{"speaker": "Overview", "text": overview[:MAX_SEGMENT_TEXT_LENGTH], "timestamp_str": "00:00"}]
    return lines


def _index_realtime_segments(segments: list[Any], session_id: str, uid: str) -> int:
    indexed = 0
    for segment in segments:
        if not isinstance(segment, dict):
            raise HTTPException(status_code=422, detail="Each segment must be a JSON object")

        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        try:
            start_val = float(segment.get("start", 0))
            if math.isnan(start_val) or math.isinf(start_val) or start_val < 0.0 or start_val > MAX_TIMESTAMP_SECONDS:
                raise HTTPException(status_code=422, detail="Segment start must be non-negative and valid timestamp")
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Segment start must be numeric") from exc

        orchestrator.memory.index_utterance(
            session_id=session_id,
            speaker=str(segment.get("speaker", "Omi User"))[:MAX_SPEAKER_LENGTH],
            text=text[:MAX_SEGMENT_TEXT_LENGTH],
            timestamp=start_val,
            timestamp_str="live",
            uid=uid,
        )
        indexed += 1
    return indexed


@router.post("/omi/conversation")
def omi_conversation_webhook(
    background_tasks: BackgroundTasks,
    payload: Any = Body(...),
    user: AuthenticatedUser = Depends(verify_omi_webhook),
):
    """
    Official Guide Endpoint: Fires after an Omi conversation ends.
    Ingests transcript segments and guarantees single-pass indexing under authenticated UID.
    Includes idempotency protection and collision-safe session identifiers.
    """
    # Dynamically register incoming wearable identity
    register_wearable_uid(user.uid)

    # Validate and normalize before recording an event as processed.
    event_id = None
    if isinstance(payload, dict):
        event_id = payload.get("id") or payload.get("event_id") or payload.get("conversation_id")

    lines = _extract_lines_from_payload(payload)
    if not lines:
        return {"status": "empty"}

    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    sess_id = f"conv_{user.uid}_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    is_dup, record = default_webhook_inbox.record_incoming_event(
        event_id=str(event_id) if event_id else None,
        payload_hash=payload_hash,
        uid=user.uid,
        session_id=sess_id,
        payload=payload,
    )
    if is_dup:
        return {
            "status": "duplicate",
            "message": "Conversation event already processed",
            "event_id": str(event_id) if event_id else None,
        }

    structured = (payload if isinstance(payload, dict) else {}).get("structured") or {}

    # Direct synchronous indexing to guarantee persistence before webhook acknowledges
    try:
        for i, line in enumerate(lines):
            orchestrator.memory.index_utterance(
                session_id=sess_id,
                speaker=line.get("speaker", "Speaker"),
                text=line.get("text", ""),
                timestamp=float(i * 15),
                timestamp_str=line.get("timestamp_str", "live"),
                topic="omi_conversation",
                urgency="normal",
                uid=user.uid,
            )
        default_webhook_inbox.mark_completed(record["event_key"])
    except Exception as exc:
        default_webhook_inbox.mark_failed(record["event_key"], str(exc))
        logger.error(f"Failed to persist conversation utterances: {exc}")
        raise HTTPException(status_code=500, detail="Failed to persist conversation utterances") from exc

    # Background task for executive synthesis with index_memory=False to avoid double-indexing
    background_tasks.add_task(
        _process_omi_conversation,
        sess_id,
        user.uid,
        lines,
        structured.get("title", f"Omi Memory ({user.uid})"),
    )
    return {"status": "accepted", "queued_segments": len(lines), "uid": user.uid}


def _extract_realtime_segments(payload: Any) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("segments", [])
    return []


def _extract_realtime_event_id(payload: Any) -> str | None:
    if isinstance(payload, dict):
        val = payload.get("id") or payload.get("event_id") or payload.get("chunk_id")
        return str(val) if val else None
    return None


@router.post("/omi/realtime")
def omi_realtime_webhook(
    background_tasks: BackgroundTasks,
    payload: Any = Body(...),
    session_id: str = "",
    user: AuthenticatedUser = Depends(verify_omi_webhook),
):
    """
    Official Guide Endpoint: Real-time transcript stream chunks from Omi device.
    Strictly validates segment timestamps and isolates points to authenticated user identity.
    """
    segments = _extract_realtime_segments(payload)
    if len(segments) > MAX_SEGMENTS_COUNT:
        raise HTTPException(status_code=422, detail=f"Segments count exceeds limit of {MAX_SEGMENTS_COUNT}")

    actual_session = session_id or f"realtime_{user.uid}_{uuid.uuid4().hex[:8]}"
    register_wearable_uid(user.uid)
    payload_event_id = _extract_realtime_event_id(payload)
    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    is_dup, record = default_webhook_inbox.record_incoming_event(
        event_id=payload_event_id,
        payload_hash=payload_hash,
        uid=user.uid,
        session_id=actual_session,
        payload=payload,
    )
    if is_dup:
        return {"status": "duplicate", "session_id": record["session_id"], "indexed_queued": 0}

    try:
        indexed = _index_realtime_segments(segments, actual_session, user.uid)
        default_webhook_inbox.mark_completed(record["event_key"])
    except HTTPException:
        default_webhook_inbox.mark_failed(record["event_key"], "Realtime payload validation failed")
        raise
    except Exception as exc:
        default_webhook_inbox.mark_failed(record["event_key"], str(exc))
        logger.error(f"Failed to persist realtime webhook segments: {exc}")
        raise HTTPException(status_code=500, detail="Failed to persist realtime webhook segments") from exc

    return {"status": "accepted", "indexed_queued": indexed}
