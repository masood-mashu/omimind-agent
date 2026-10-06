"""
webhooks.py - Omi Wearable device webhooks and conversation ingestion endpoints
"""
import time
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException

from backend.schemas.api_models import OmiWebhookRequest
from backend.shared import orchestrator, parse_transcript, processed_cache

router = APIRouter(tags=["Omi Webhooks"])


def _process_omi_webhook(session_id: str, lines: list[dict[str, Any]]) -> None:
    dossier = orchestrator.process_session(
        session_id=session_id,
        title="Omi Live Session",
        transcript_lines=lines,
    )
    processed_cache[session_id] = dossier


@router.post("/api/omi-webhook")
def omi_webhook(req: OmiWebhookRequest, background_tasks: BackgroundTasks):
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

    # Synchronous index to guarantee Qdrant persistence in serverless environments
    for i, line in enumerate(lines):
        orchestrator.memory.index_utterance(
            session_id=session_id,
            speaker=line.get("speaker", "Omi User"),
            text=line.get("text", ""),
            timestamp=float(i * 15),
            timestamp_str=line.get("timestamp_str", "live"),
            topic="omi_webhook",
            urgency="normal",
            uid="default_user",
        )

    background_tasks.add_task(_process_omi_webhook, session_id, lines)
    return {"status": "accepted", "session_id": session_id, "vectors_queued": len(lines)}


def _process_omi_conversation(uid: str, lines: list[dict[str, Any]], title: str) -> None:
    dossier = orchestrator.process_session(
        session_id=f"conv_{uid}_{int(time.time())}",
        title=title,
        transcript_lines=lines,
        uid=uid,
    )
    processed_cache[dossier["session_id"]] = dossier


def _extract_lines_from_payload(payload: Any) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    overview = ""
    segments = []

    if isinstance(payload, list):
        segments = payload
    elif isinstance(payload, dict):
        segments = payload.get("transcript_segments") or payload.get("segments") or []
        overview = (payload.get("structured") or {}).get("overview", "")
        raw_text = payload.get("transcript") or payload.get("text") or (payload.get("conversation") or {}).get("transcript")
        if raw_text and not segments:
            parsed_lines, _ = parse_transcript(str(raw_text), "Omi User")
            lines.extend(parsed_lines)

    for s in segments:
        now_ts = time.strftime("%H:%M:%S", time.gmtime())
        if isinstance(s, dict):
            text = s.get("text", "").strip()
            if text:
                lines.append({
                    "speaker": s.get("speaker", "Omi User"),
                    "text": text,
                    "timestamp_str": now_ts,
                })
        elif isinstance(s, str) and s.strip():
            lines.append({
                "speaker": "Omi User",
                "text": s.strip(),
                "timestamp_str": now_ts,
            })

    if not lines and overview:
        lines = [{"speaker": "Overview", "text": overview, "timestamp_str": "00:00"}]
    return lines


@router.post("/omi/conversation")
def omi_conversation_webhook(
    background_tasks: BackgroundTasks,
    uid: str = "default_user",
    payload: Any = Body(...),
):
    """
    Official Guide Endpoint: Fires after an Omi conversation ends.
    Ingests full transcript segments, structured overview, and indexes to Qdrant.
    """
    lines = _extract_lines_from_payload(payload)
    if not lines:
        return {"status": "empty"}

    structured = (payload if isinstance(payload, dict) else {}).get("structured") or {}
    sess_id = f"conv_{uid}_{int(time.time())}"
    # Direct synchronous index to guarantee persistence in serverless environments
    for i, line in enumerate(lines):
        orchestrator.memory.index_utterance(
            session_id=sess_id,
            speaker=line.get("speaker", "Speaker"),
            text=line.get("text", ""),
            timestamp=float(i * 15),
            timestamp_str=line.get("timestamp_str", "live"),
            topic="omi_conversation",
            urgency="normal",
            uid=uid,
        )
        # Also index under default_user if uid is custom, so website search box immediately finds it
        if uid != "default_user":
            orchestrator.memory.index_utterance(
                session_id=sess_id,
                speaker=line.get("speaker", "Speaker"),
                text=line.get("text", ""),
                timestamp=float(i * 15),
                timestamp_str=line.get("timestamp_str", "live"),
                topic="omi_conversation",
                urgency="normal",
                uid="default_user",
            )

    background_tasks.add_task(
        _process_omi_conversation,
        uid,
        lines,
        structured.get("title", f"Omi Memory ({uid})"),
    )
    return {"status": "accepted", "queued_segments": len(lines), "uid": uid}


def _index_omi_realtime(uid: str, session_id: str, segments: list[dict[str, Any]]) -> None:
    for s in segments:
        if isinstance(s, dict):
            t = s.get("text", "").strip()
            if t:
                orchestrator.memory.index_utterance(
                    session_id=session_id or f"realtime_{uid}",
                    speaker=s.get("speaker", "Omi User"),
                    text=t,
                    timestamp=float(s.get("start", 0)),
                    timestamp_str="live",
                    uid=uid,
                )
                if uid != "default_user":
                    orchestrator.memory.index_utterance(
                        session_id=session_id or f"realtime_{uid}",
                        speaker=s.get("speaker", "Omi User"),
                        text=t,
                        timestamp=float(s.get("start", 0)),
                        timestamp_str="live",
                        uid="default_user",
                    )


@router.post("/omi/realtime")
def omi_realtime_webhook(
    background_tasks: BackgroundTasks,
    uid: str = "default_user",
    session_id: str = "",
    payload: Any = Body(...),
):
    """
    Official Guide Endpoint: Real-time transcript stream chunks from Omi device.
    """
    segments = payload if isinstance(payload, list) else (payload.get("segments", []) if isinstance(payload, dict) else [])
    indexed = 0
    actual_session = session_id or f"realtime_{uid}"
    for s in segments:
        if isinstance(s, dict):
            t = s.get("text", "").strip()
            if t:
                try:
                    start_val = float(s.get("start", 0))
                except (TypeError, ValueError) as exc:
                    raise HTTPException(status_code=422, detail="Segment start must be numeric") from exc
                orchestrator.memory.index_utterance(
                    session_id=actual_session,
                    speaker=s.get("speaker", "Omi User"),
                    text=t,
                    timestamp=start_val,
                    timestamp_str="live",
                    uid=uid,
                )
                if uid != "default_user":
                    orchestrator.memory.index_utterance(
                        session_id=actual_session,
                        speaker=s.get("speaker", "Omi User"),
                        text=t,
                        timestamp=start_val,
                        timestamp_str="live",
                        uid="default_user",
                    )
                indexed += 1
    return {"status": "accepted", "indexed_queued": indexed}
